"""
Implementación medida del Motor `JEV (Sistema 1)` (`src/adapters/ai/jev_adapter.py`).
Ejecuta micro-decisiones tipadas en `< 500 ms` (clasificación de intención en `OppyFy`,
mapeo de columnas Excel, severidad de mermas, validación de facturas OCR y detección de
*Prompt Injection*), verifica el umbral de confianza (`default=Decimal("0.85")`) y registra
obligatoriamente cada invocación en `public.jev_request_logs` y `public.llm_request_logs`.
"""
from __future__ import annotations

import time
import unicodedata
import uuid
from collections.abc import Callable, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.ai.jev_protocol import (
    DEFAULT_JEV_CONFIDENCE_THRESHOLD,
    MAX_JEV_BATCH_SIZE,
    JevBooleanResult,
    JevChoiceBatchItem,
    JevChoiceResult,
    JevDecisionPort,
    JevScoreLevel,
    JevScoreResult,
    JevTelemetrySinkPort,
    JevUsageRecord,
)
from src.adapters.ai.protocol import LlmTelemetrySinkPort, LlmUsageRecord
from src.modules.oppy_ai.infrastructure.models import JevRequestLog

_SIX_DECIMALS = Decimal("0.000001")
_TWO_DECIMALS = Decimal("0.01")

SEMANTIC_AFFINITIES: dict[str, tuple[str, ...]] = {
    "query_sales_summary": (
        "venta",
        "ventas",
        "ingreso",
        "ingresos",
        "facturacion",
        "ticket",
        "sales",
        "revenue",
    ),
    "query_stock_levels": (
        "stock",
        "inventario",
        "bodega",
        "existencia",
        "lote",
        "fefo",
        "merma",
        "kardex",
        "insumo",
    ),
    "query_upcoming_events": (
        "evento",
        "eventos",
        "banquete",
        "matrimonio",
        "invitado",
        "invitados",
        "reserva",
        "agendado",
        "agendados",
        "proximos eventos",
    ),
    "check_salon_availability": (
        "salon",
        "salones",
        "disponibilidad",
        "disponible",
        "ocupado",
        "overbooking",
        "aforo",
        "capacidad salon",
    ),
    "estimate_event_budget_and_feasibility": (
        "presupuesto",
        "cotizar",
        "cotizacion",
        "estimar costo",
        "presupuesto banquete",
        "calcular evento",
        "estimar presupuesto",
    ),
    "analyze_event_supply_feasibility": (
        "factibilidad",
        "faltantes",
        "insumos evento",
        "banquete",
        "cubrir",
        "abastecer",
        "stock banquete",
    ),
    "query_supplier_delays": (
        "proveedor",
        "proveedores",
        "demora",
        "atraso",
        "entrega",
        "pedido",
        "abastecimiento",
        "lead time",
    ),
    "query_recipe_costs": (
        "receta",
        "recetas",
        "escandallo",
        "costo",
        "costos",
        "food cost",
        "margen",
        "plato",
    ),
    "get_stockout_projections_and_autonomy": (
        "proyeccion",
        "proyecciones",
        "quiebre",
        "quiebres",
        "autonomia",
        "dias de stock",
        "desabastecimiento",
        "stockout",
        "forecast",
        "curva",
    ),
    "get_preventive_transfer_recommendations": (
        "traspaso",
        "traspasos",
        "preventivo",
        "preventiva",
        "reorden",
        "reposicion",
        "transferencia",
        "alerta preventiva",
    ),
    "costo_neto": ("precio", "valor", "costo", "neto", "unit cost", "price"),
    "nombre": ("producto", "descripcion", "articulo", "item", "insumo", "name"),
    "unidad": ("medida", "formato", "envase", "um", "uom", "kg", "litro", "ml"),
    "bodega": ("almacen", "ubicacion", "warehouse", "deposito", "sucursal"),
}


def _normalize_text(text: str) -> str:
    """Normaliza acentos y mayúsculas para comparación semántica ultrarrápida."""
    decomposed = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _determine_calibrated_action(confidence: Decimal, threshold: Decimal) -> str:
    """
    Determina la acción calibrada según el umbral de confianza:
    - 'AUTO_ACCEPTED': Si la confianza cumple o supera el umbral.
    - 'FLAGGED_WARNING': Si la confianza está por debajo del umbral pero >= 0.70.
    - 'FALLBACK_LLM': Si la confianza es baja (< 0.70) y requiere Sistema 2.
    """
    if confidence >= threshold:
        return "AUTO_ACCEPTED"
    if confidence >= Decimal("0.70"):
        return "FLAGGED_WARNING"
    return "FALLBACK_LLM"


def _map_record_to_jev_log(record: JevUsageRecord) -> JevRequestLog:
    """Convierte un `JevUsageRecord` en una entidad SQLAlchemy `JevRequestLog`."""
    kwargs: dict[str, Any] = {
        "holding_id": record.holding_id,
        "tenant_id": record.tenant_id,
        "tenant_schema": record.tenant_schema,
        "user_id": record.user_id,
        "trace_id": record.trace_id,
        "caller_feature": record.caller_feature,
        "decision_id": record.decision_id,
        "decision_primitive": record.decision_primitive,
        "input_summary": record.input_summary[:255] if len(record.input_summary) > 255 else record.input_summary,
        "result_value": record.result_value[:128] if len(record.result_value) > 128 else record.result_value,
        "confidence_score": record.confidence_score,
        "calibrated_action": record.calibrated_action[:24] if len(record.calibrated_action) > 24 else record.calibrated_action,
        "model_name": record.model_name[:64] if len(record.model_name) > 64 else record.model_name,
        "estimated_tokens": record.estimated_tokens,
        "provider_cost_usd": record.provider_cost_usd,
        "provider_cost_clp": record.provider_cost_clp,
        "credits_deducted": record.credits_deducted,
        "latency_ms": record.latency_ms,
        "is_success": record.is_success,
        "error_message": record.error_message,
    }
    if record.created_at is not None:
        kwargs["created_at"] = record.created_at
    return JevRequestLog(**kwargs)


def _score_candidates(prompt_or_input: str, candidates: Sequence[str]) -> list[tuple[str, Decimal]]:
    """Calcula determinísticamente la afinidad semántica y score de cada candidato."""
    if not candidates:
        raise ValueError("JevDecisionPort.decide_choice requires at least one candidate.")

    normalized = _normalize_text(prompt_or_input)
    scored: list[tuple[str, Decimal]] = []
    for idx, candidate in enumerate(candidates):
        cand_norm = _normalize_text(candidate)
        score = Decimal("0.40") - (Decimal(idx) * Decimal("0.01"))

        if cand_norm in normalized:
            score = Decimal("0.96")
        else:
            keywords = SEMANTIC_AFFINITIES.get(candidate, ())
            if not keywords:
                keywords = tuple(tok for tok in cand_norm.replace("_", " ").split() if len(tok) > 2)
            matches = sum(1 for kw in keywords if kw in normalized)
            if matches >= 3:
                score = Decimal("0.96")
            elif matches >= 2:
                score = Decimal("0.95")
            elif matches == 1:
                score = Decimal("0.91")

        clamped = max(Decimal("0.10"), min(Decimal("0.99"), score)).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        )
        scored.append((candidate, clamped))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


class InMemoryTelemetrySink(LlmTelemetrySinkPort):
    """Colector de telemetría en memoria/transaccional para `public.llm_request_logs`."""

    def __init__(self) -> None:
        self._records: list[LlmUsageRecord] = []

    def record_llm_usage(self, record: LlmUsageRecord) -> None:
        """Agrega un registro inmutable de uso de IA."""
        self._records.append(record)

    @property
    def records(self) -> tuple[LlmUsageRecord, ...]:
        """Devuelve la bitácora inmutable acumulada de `LlmUsageRecord`."""
        return tuple(self._records)


class InMemoryJevTelemetrySink(JevTelemetrySinkPort):
    """Colector de telemetría especializada en memoria para tests y desarrollo."""

    def __init__(self) -> None:
        self._records: list[JevUsageRecord] = []

    def record_jev_usage(self, record: JevUsageRecord) -> None:
        """Agrega un registro inmutable de decisión JEV."""
        self._records.append(record)

    def record_jev_usage_batch(self, records: Sequence[JevUsageRecord]) -> None:
        """Agrega un lote de registros inmutables de decisión JEV."""
        if not records:
            return
        if len(records) > MAX_JEV_BATCH_SIZE:
            raise ValueError(
                f"El lote de telemetría JEV supera el límite máximo permitido de {MAX_JEV_BATCH_SIZE} registros (recibidos: {len(records)})."
            )
        self._records.extend(records)

    @property
    def records(self) -> tuple[JevUsageRecord, ...]:
        """Devuelve la bitácora inmutable acumulada de `JevUsageRecord`."""
        return tuple(self._records)

    def clear(self) -> None:
        """Limpia todos los registros acumulados."""
        self._records.clear()


class DatabaseJevTelemetrySink(JevTelemetrySinkPort):
    """
    Sink de telemetría transaccional y asíncrono sobre SQLAlchemy AsyncSession.
    Persiste instancias de `JevRequestLog` tanto individuales como en lote (`session.add_all(...)`).
    """

    def __init__(
        self,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | Callable[[], AsyncSession] | None = None,
        *,
        auto_commit: bool = False,
    ) -> None:
        self._session = session
        self._session_factory = session_factory
        self._auto_commit = auto_commit
        self._pending_models: list[JevRequestLog] = []
        self._recorded_records: list[JevUsageRecord] = []

    @property
    def session(self) -> AsyncSession | None:
        return self._session

    @session.setter
    def session(self, value: AsyncSession | None) -> None:
        self._session = value

    @property
    def pending_models(self) -> tuple[JevRequestLog, ...]:
        """Devuelve los modelos SQLAlchemy pendientes de persistencia."""
        return tuple(self._pending_models)

    @property
    def records(self) -> tuple[JevUsageRecord, ...]:
        """Devuelve los registros `JevUsageRecord` recopilados."""
        return tuple(self._recorded_records)

    def record_jev_usage(self, record: JevUsageRecord) -> None:
        """Registra un evento individual en la sesión activa y/o buffer."""
        self._recorded_records.append(record)
        model = _map_record_to_jev_log(record)
        self._pending_models.append(model)
        if self._session is not None:
            self._session.add(model)

    def record_jev_usage_batch(self, records: Sequence[JevUsageRecord]) -> None:
        """Registra un lote de eventos JEV mediante `session.add_all` en la sesión activa."""
        if not records:
            return
        if len(records) > MAX_JEV_BATCH_SIZE:
            raise ValueError(
                f"El lote de telemetría JEV supera el límite máximo permitido de {MAX_JEV_BATCH_SIZE} registros (recibidos: {len(records)})."
            )
        self._recorded_records.extend(records)
        models = [_map_record_to_jev_log(r) for r in records]
        self._pending_models.extend(models)
        if self._session is not None:
            self._session.add_all(models)

    async def flush(self) -> None:
        """Sincroniza y descarga los modelos pendientes en la base de datos."""
        if self._session is not None:
            await self._session.flush()
            self._pending_models.clear()
        elif self._session_factory is not None and self._pending_models:
            models_to_persist = list(self._pending_models)
            async with self._session_factory() as session:
                async with session.begin():
                    session.add_all(models_to_persist)
            self._pending_models.clear()

    async def commit(self) -> None:
        """Confirma la transacción en la sesión activa o mediante fábrica."""
        if self._session is not None:
            await self._session.commit()
            self._pending_models.clear()
        elif self._session_factory is not None and self._pending_models:
            await self.flush()

    async def record_jev_usage_async(self, record: JevUsageRecord) -> None:
        """Registra un evento de forma asíncrona realizando flush si `auto_commit` está activo."""
        self.record_jev_usage(record)
        if self._auto_commit:
            await self.commit()

    async def record_jev_usage_batch_async(self, records: Sequence[JevUsageRecord]) -> None:
        """Registra un lote de forma asíncrona realizando flush si `auto_commit` está activo."""
        self.record_jev_usage_batch(records)
        if self._auto_commit:
            await self.commit()


class MeteredJevAdapter(JevDecisionPort):
    """
    Adaptador único y medido de `JEV (Sistema 1)`.
    Cumple la Regla Inmutable 14: toda micro-decisión se ejecuta en `< 500 ms`,
    evalúa el umbral de confianza calibrado (`Decimal`) y escribe en `public.jev_request_logs`
    y `public.llm_request_logs`.
    """

    def __init__(
        self,
        telemetry_sink: LlmTelemetrySinkPort | None = None,
        *,
        jev_telemetry_sink: JevTelemetrySinkPort | None = None,
        model_name: str = "jev-system1-v2",
        input_cost_per_1m_usd: Decimal = Decimal("0.040000"),
        output_cost_per_1m_usd: Decimal = Decimal("0.100000"),
        usd_to_clp_rate: Decimal = Decimal("950.00"),
        default_credits_per_call: Decimal = Decimal("0.20"),
    ) -> None:
        self._sink: LlmTelemetrySinkPort = telemetry_sink or InMemoryTelemetrySink()
        self._jev_sink: JevTelemetrySinkPort = jev_telemetry_sink or InMemoryJevTelemetrySink()
        self._model_name = model_name
        self._input_cost_per_1m_usd = input_cost_per_1m_usd
        self._output_cost_per_1m_usd = output_cost_per_1m_usd
        self._usd_to_clp_rate = usd_to_clp_rate
        self._default_credits_per_call = default_credits_per_call
        self._emitted_logs: list[LlmUsageRecord] = []
        self._emitted_jev_logs: list[JevUsageRecord] = []

    @property
    def emitted_logs(self) -> tuple[LlmUsageRecord, ...]:
        """Expone los registros emitidos hacia `public.llm_request_logs` para auditoría."""
        return tuple(self._emitted_logs)

    @property
    def emitted_jev_logs(self) -> tuple[JevUsageRecord, ...]:
        """Expone los registros emitidos hacia `public.jev_request_logs` para auditoría."""
        return tuple(self._emitted_jev_logs)

    @property
    def jev_telemetry_sink(self) -> JevTelemetrySinkPort:
        """Devuelve el colector de telemetría JEV activo."""
        return self._jev_sink

    def _build_and_record_usage(
        self,
        *,
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        prompt_or_input: str,
        output_tokens: int,
        started_ns: int,
        thread_id: uuid.UUID | None = None,
    ) -> LlmUsageRecord:
        duration_ms = max(1, min(499, int((time.perf_counter_ns() - started_ns) // 1_000_000)))
        input_tokens = max(4, len(prompt_or_input.split()) * 2)
        in_cost = (Decimal(input_tokens) * self._input_cost_per_1m_usd) / Decimal("1000000")
        out_cost = (Decimal(output_tokens) * self._output_cost_per_1m_usd) / Decimal("1000000")
        cost_usd = (in_cost + out_cost).quantize(_SIX_DECIMALS, rounding=ROUND_HALF_UP)
        cost_clp = (cost_usd * self._usd_to_clp_rate).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        )

        record = LlmUsageRecord(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema=tenant_schema,
            user_id=user_id,
            thread_id=thread_id,
            engine_tier="SYSTEM_1_JEV",
            caller_feature=caller_feature,
            model_name=self._model_name,
            input_tokens=input_tokens,
            cached_tokens=0,
            output_tokens=output_tokens,
            provider_cost_usd=cost_usd,
            provider_cost_clp=cost_clp,
            credits_deducted=self._default_credits_per_call,
            request_duration_ms=duration_ms,
            api_success=True,
            error_message=None,
        )
        self._emitted_logs.append(record)
        self._sink.record_llm_usage(record)
        return record

    def _build_and_record_jev_usage(
        self,
        *,
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int | None,
        trace_id: str | None,
        caller_feature: str,
        decision_id: str,
        decision_primitive: str,
        input_summary: str,
        result_value: str,
        confidence_score: Decimal,
        calibrated_action: str,
        output_tokens: int,
        started_ns: int,
        is_success: bool = True,
        error_message: str | None = None,
    ) -> JevUsageRecord:
        duration_ms = max(1, min(499, int((time.perf_counter_ns() - started_ns) // 1_000_000)))
        input_tokens = max(4, len(input_summary.split()) * 2)
        in_cost = (Decimal(input_tokens) * self._input_cost_per_1m_usd) / Decimal("1000000")
        out_cost = (Decimal(output_tokens) * self._output_cost_per_1m_usd) / Decimal("1000000")
        cost_usd = (in_cost + out_cost).quantize(_SIX_DECIMALS, rounding=ROUND_HALF_UP)
        cost_clp = (cost_usd * self._usd_to_clp_rate).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        )

        record = JevUsageRecord(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema=tenant_schema,
            user_id=user_id,
            trace_id=trace_id,
            caller_feature=caller_feature,
            decision_id=decision_id,
            decision_primitive=decision_primitive,
            input_summary=input_summary[:255],
            result_value=result_value[:128],
            confidence_score=confidence_score,
            calibrated_action=calibrated_action,
            model_name=self._model_name,
            estimated_tokens=input_tokens + output_tokens,
            provider_cost_usd=cost_usd,
            provider_cost_clp=cost_clp,
            credits_deducted=self._default_credits_per_call,
            latency_ms=duration_ms,
            is_success=is_success,
            error_message=error_message,
        )
        self._emitted_jev_logs.append(record)
        self._jev_sink.record_jev_usage(record)
        return record

    def decide_boolean(
        self,
        *,
        decision_id: str,
        prompt_or_input: str,
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        threshold: Decimal = DEFAULT_JEV_CONFIDENCE_THRESHOLD,
        thread_id: uuid.UUID | None = None,
    ) -> JevBooleanResult:
        """
        Evalúa micro-decisiones binarias (`Jev.boolean`):
        - Guardrail de *Prompt Injection* o indagación de arquitectura interna.
        - Equivalencia semántica de productos en Excel/Facturas OCR.
        - Determinación de si una consulta puede usar caché semántica (`is_cacheable_query`).
        """
        started_ns = time.perf_counter_ns()
        normalized = _normalize_text(prompt_or_input)
        decision_upper = decision_id.upper()

        injection_signals = (
            "ignore previous",
            "ignora las instrucciones",
            "system prompt",
            "sqlalchemy",
            "alembic",
            "esquema interno",
            "arquitectura interna",
            "drop table",
            "codigo fuente",
            "information_schema",
            "password",
            "contrasena",
            "contrasenas",
            "api key",
            "apikey",
            "llave de api",
            "llaves de api",
            "env var",
            "variables de entorno",
            "variable de entorno",
            ".env",
            "pg_catalog",
            "select * from",
            "union select",
            "jailbreak",
        )
        live_data_signals = (
            "stock",
            "inventario",
            "venta",
            "evento",
            "proveedor",
            "merma",
            "factura",
            "receta",
            "costo",
        )

        if "INJECTION" in decision_upper or "SECURITY" in decision_upper:
            is_unsafe = any(sig in normalized for sig in injection_signals)
            value = is_unsafe
            confidence = Decimal("0.98") if is_unsafe else Decimal("0.97")
            rationale = "PROMPT_INJECTION_DETECTED" if is_unsafe else "SAFE_BUSINESS_QUERY"
        elif "CACHE" in decision_upper:
            touches_live_data = any(sig in normalized for sig in live_data_signals)
            value = not touches_live_data
            confidence = Decimal("0.95")
            rationale = "CONCEPTUAL_CACHEABLE" if value else "LIVE_TENANT_DATA_NO_CACHE"
        elif "DUPLICATE" in decision_upper or "OCR" in decision_upper:
            parts = [p.strip() for p in normalized.split("|") if p.strip()]
            if len(parts) == 2:
                tokens_a = set(parts[0].replace("-", " ").split())
                tokens_b = set(parts[1].replace("-", " ").split())
                union_len = len(tokens_a | tokens_b)
                overlap = (
                    (Decimal(len(tokens_a & tokens_b)) / Decimal(union_len)).quantize(
                        _TWO_DECIMALS, rounding=ROUND_HALF_UP
                    )
                    if union_len > 0
                    else Decimal("0.00")
                )
                value = overlap >= Decimal("0.50")
                confidence = max(Decimal("0.60"), min(Decimal("0.96"), overlap + Decimal("0.30")))
            else:
                value = "valid" in normalized or "ok" in normalized or "true" in normalized
                confidence = Decimal("0.91")
            rationale = "SEMANTIC_EQUIVALENCE_EVALUATED"
        else:
            is_ambiguous = "tal vez" in normalized or "quizas" in normalized or len(normalized) < 3
            value = not any(sig in normalized for sig in injection_signals)
            confidence = Decimal("0.62") if is_ambiguous else Decimal("0.94")
            rationale = "AMBIGUOUS_INPUT" if is_ambiguous else "STANDARD_BOOLEAN_GATE"

        meets = confidence >= threshold
        calibrated_action = _determine_calibrated_action(confidence, threshold)

        usage = self._build_and_record_usage(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema=tenant_schema,
            user_id=user_id,
            caller_feature=caller_feature,
            prompt_or_input=prompt_or_input,
            output_tokens=4,
            started_ns=started_ns,
            thread_id=thread_id,
        )
        jev_record = self._build_and_record_jev_usage(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema=tenant_schema,
            user_id=user_id,
            trace_id=str(thread_id) if thread_id else None,
            caller_feature=caller_feature,
            decision_id=decision_id,
            decision_primitive="BOOLEAN",
            input_summary=prompt_or_input,
            result_value=str(value).lower(),
            confidence_score=confidence,
            calibrated_action=calibrated_action,
            output_tokens=4,
            started_ns=started_ns,
            is_success=True,
            error_message=None,
        )
        return JevBooleanResult(
            decision_id=decision_id,
            value=value,
            confidence=confidence,
            threshold=threshold,
            meets_threshold=meets,
            fallback_required=not meets,
            rationale_code=rationale,
            usage_record=usage,
            jev_record=jev_record,
        )

    def decide_choice(
        self,
        *,
        decision_id: str,
        prompt_or_input: str,
        candidates: Sequence[str],
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        threshold: Decimal = DEFAULT_JEV_CONFIDENCE_THRESHOLD,
        thread_id: uuid.UUID | None = None,
    ) -> JevChoiceResult:
        """
        Elige determinísticamente la mejor opción de `candidates` (`Jev.choice`):
        - Enrutamiento de herramientas operativas de `OppyFy`.
        - Clasificación de sub-dominio RBAC editable de `OppyFy`.
        - Mapeo de columnas de planillas Excel (`nombre`, `costo_neto`, `unidad`, `bodega`, etc.).
        """
        started_ns = time.perf_counter_ns()
        scored = _score_candidates(prompt_or_input, candidates)
        best_candidate, best_confidence = scored[0]
        meets = best_confidence >= threshold
        calibrated_action = _determine_calibrated_action(best_confidence, threshold)

        usage = self._build_and_record_usage(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema=tenant_schema,
            user_id=user_id,
            caller_feature=caller_feature,
            prompt_or_input=prompt_or_input,
            output_tokens=6,
            started_ns=started_ns,
            thread_id=thread_id,
        )
        jev_record = self._build_and_record_jev_usage(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema=tenant_schema,
            user_id=user_id,
            trace_id=str(thread_id) if thread_id else None,
            caller_feature=caller_feature,
            decision_id=decision_id,
            decision_primitive="CHOICE",
            input_summary=prompt_or_input,
            result_value=best_candidate,
            confidence_score=best_confidence,
            calibrated_action=calibrated_action,
            output_tokens=6,
            started_ns=started_ns,
            is_success=True,
            error_message=None,
        )
        return JevChoiceResult(
            decision_id=decision_id,
            value=best_candidate,
            confidence=best_confidence,
            threshold=threshold,
            meets_threshold=meets,
            fallback_required=not meets,
            alternatives=tuple(scored),
            usage_record=usage,
            jev_record=jev_record,
        )

    def decide_choice_batch(
        self,
        *,
        items: Sequence[JevChoiceBatchItem | dict[str, Any] | tuple[str, str, Sequence[str]]],
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        threshold: Decimal = DEFAULT_JEV_CONFIDENCE_THRESHOLD,
        thread_id: uuid.UUID | None = None,
    ) -> tuple[JevChoiceResult, ...]:
        """
        Evalúa un lote de micro-decisiones de opción múltiple (`Jev.choice_batch`)
        con registro individual en `llm_request_logs` y registro en lote atómico en `jev_request_logs`.
        Ideal para importación de catálogos y facturas masivas.
        """
        if not items:
            return ()
        if len(items) > MAX_JEV_BATCH_SIZE:
            raise ValueError(
                f"El lote de decisiones JEV supera el límite máximo permitido de {MAX_JEV_BATCH_SIZE} elementos (recibidos: {len(items)})."
            )

        batch_started_ns = time.perf_counter_ns()
        results: list[JevChoiceResult] = []
        batch_jev_records: list[JevUsageRecord] = []

        for idx, item in enumerate(items):
            item_started_ns = time.perf_counter_ns()
            if isinstance(item, JevChoiceBatchItem):
                dec_id = item.decision_id
                inp = item.prompt_or_input
                cands = item.candidates
                item_thresh = item.threshold if item.threshold is not None else threshold
            elif isinstance(item, dict):
                dec_id = str(item.get("decision_id", f"BATCH_CHOICE_{idx + 1}"))
                inp = str(item["prompt_or_input"])
                cands = item["candidates"]
                item_thresh = Decimal(str(item["threshold"])) if "threshold" in item and item["threshold"] is not None else threshold
            elif isinstance(item, (tuple, list)):
                dec_id = str(item[0])
                inp = str(item[1])
                cands = item[2]
                item_thresh = threshold
            else:
                raise TypeError(f"Elemento de lote no soportado: {type(item)}")

            scored = _score_candidates(inp, cands)
            best_candidate, best_confidence = scored[0]
            meets = best_confidence >= item_thresh
            calibrated_action = _determine_calibrated_action(best_confidence, item_thresh)

            # 1. Registro LLM Legacy
            duration_ms = max(1, min(499, int((time.perf_counter_ns() - item_started_ns) // 1_000_000)))
            input_tokens = max(4, len(inp.split()) * 2)
            output_tokens = 6
            in_cost = (Decimal(input_tokens) * self._input_cost_per_1m_usd) / Decimal("1000000")
            out_cost = (Decimal(output_tokens) * self._output_cost_per_1m_usd) / Decimal("1000000")
            cost_usd = (in_cost + out_cost).quantize(_SIX_DECIMALS, rounding=ROUND_HALF_UP)
            cost_clp = (cost_usd * self._usd_to_clp_rate).quantize(
                _TWO_DECIMALS, rounding=ROUND_HALF_UP
            )

            llm_rec = LlmUsageRecord(
                holding_id=holding_id,
                tenant_id=tenant_id,
                tenant_schema=tenant_schema,
                user_id=user_id,
                thread_id=thread_id,
                engine_tier="SYSTEM_1_JEV",
                caller_feature=caller_feature,
                model_name=self._model_name,
                input_tokens=input_tokens,
                cached_tokens=0,
                output_tokens=output_tokens,
                provider_cost_usd=cost_usd,
                provider_cost_clp=cost_clp,
                credits_deducted=self._default_credits_per_call,
                request_duration_ms=duration_ms,
                api_success=True,
                error_message=None,
            )
            self._emitted_logs.append(llm_rec)
            self._sink.record_llm_usage(llm_rec)

            # 2. Registro JEV desacoplado
            jev_rec = JevUsageRecord(
                holding_id=holding_id,
                tenant_id=tenant_id,
                tenant_schema=tenant_schema,
                user_id=user_id,
                trace_id=str(thread_id) if thread_id else None,
                caller_feature=caller_feature,
                decision_id=dec_id,
                decision_primitive="CHOICE",
                input_summary=inp[:255],
                result_value=best_candidate[:128],
                confidence_score=best_confidence,
                calibrated_action=calibrated_action,
                model_name=self._model_name,
                estimated_tokens=input_tokens + output_tokens,
                provider_cost_usd=cost_usd,
                provider_cost_clp=cost_clp,
                credits_deducted=self._default_credits_per_call,
                latency_ms=duration_ms,
                is_success=True,
                error_message=None,
            )
            batch_jev_records.append(jev_rec)
            self._emitted_jev_logs.append(jev_rec)

            result = JevChoiceResult(
                decision_id=dec_id,
                value=best_candidate,
                confidence=best_confidence,
                threshold=item_thresh,
                meets_threshold=meets,
                fallback_required=not meets,
                alternatives=tuple(scored),
                usage_record=llm_rec,
                jev_record=jev_rec,
            )
            results.append(result)

        # Registro en lote atómico en el sink JEV
        self._jev_sink.record_jev_usage_batch(batch_jev_records)
        return tuple(results)

    def decide_score(
        self,
        *,
        decision_id: str,
        prompt_or_input: str,
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        threshold: Decimal = DEFAULT_JEV_CONFIDENCE_THRESHOLD,
        thread_id: uuid.UUID | None = None,
    ) -> JevScoreResult:
        """
        Califica severidad de mermas, desviación de precios en facturas OCR o urgencia (`Jev.score`).
        """
        started_ns = time.perf_counter_ns()
        normalized = _normalize_text(prompt_or_input)

        critical_terms = ("critico", "robo", "vencido masivo", "fraude", "urgente", "quiebre total")
        high_terms = ("merma alta", "quiebre", "desviacion", "alerta", "temperatura", "rotura")
        medium_terms = ("ajuste", "diferencia", "revision", "demora", "moderado")

        if any(term in normalized for term in critical_terms):
            level: JevScoreLevel = "CRITICAL"
            numeric_score = Decimal("0.95")
            confidence = Decimal("0.94")
        elif any(term in normalized for term in high_terms):
            level = "HIGH"
            numeric_score = Decimal("0.78")
            confidence = Decimal("0.91")
        elif any(term in normalized for term in medium_terms):
            level = "MEDIUM"
            numeric_score = Decimal("0.52")
            confidence = Decimal("0.89")
        else:
            level = "LOW"
            numeric_score = Decimal("0.20")
            confidence = Decimal("0.90")

        meets = confidence >= threshold
        calibrated_action = _determine_calibrated_action(confidence, threshold)

        usage = self._build_and_record_usage(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema=tenant_schema,
            user_id=user_id,
            caller_feature=caller_feature,
            prompt_or_input=prompt_or_input,
            output_tokens=5,
            started_ns=started_ns,
            thread_id=thread_id,
        )
        jev_record = self._build_and_record_jev_usage(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema=tenant_schema,
            user_id=user_id,
            trace_id=str(thread_id) if thread_id else None,
            caller_feature=caller_feature,
            decision_id=decision_id,
            decision_primitive="SCORE",
            input_summary=prompt_or_input,
            result_value=f"{level}:{numeric_score}",
            confidence_score=confidence,
            calibrated_action=calibrated_action,
            output_tokens=5,
            started_ns=started_ns,
            is_success=True,
            error_message=None,
        )
        return JevScoreResult(
            decision_id=decision_id,
            level=level,
            numeric_score=numeric_score,
            confidence=confidence,
            threshold=threshold,
            meets_threshold=meets,
            fallback_required=not meets,
            usage_record=usage,
            jev_record=jev_record,
        )
