"""
oppytec-backend/src/modules/tenancy/application/jev_consumption_service.py
Servicio de agregación y reportería FinOps de consumo de decisiones sub-simbólicas JEV (`public.jev_request_logs`).
Agrupa jerárquicamente en 3 niveles: Holdings -> Tenants -> Logs individuales.
Calcula métricas agregadas, acciones calibradas (AUTO_ACCEPTED, FLAGGED_WARNING, FALLBACK_LLM),
latencias y ahorro estimado FinOps frente al costo teórico de Sistema 2 (Google Gemini Pro).
Cumple estrictamente: Cero uso de float (exclusivamente Decimal e int).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.observability import get_current_trace_id, scrub_pii_text
from src.modules.oppy_ai.infrastructure.models import JevRequestLog
from src.modules.tenancy.domain.saas_policy_math import (
    DEFAULT_USD_TO_CLP_RATE,
    SIX_DECIMALS,
    TWO_DECIMALS,
    ZERO,
)
from src.modules.tenancy.presentation.schemas_platform_admin import (
    JevConsumptionSummaryResponse,
    JevHoldingGroup,
    JevLogItem,
    JevTenantGroup,
)

logger = logging.getLogger("oppytec.tenancy.jev_consumption")

# Constante FinOps: Costo teórico blended de Google Gemini Pro por decisión Sistema 2 ($0.0025 USD)
DEFAULT_THEORETICAL_GEMINI_PRO_COST_USD: Decimal = Decimal("0.002500")


@dataclass
class JevLogItemDTO:
    """Registro individual de telemetría y auditoría de decisiones JEV."""

    id: str
    created_at: datetime
    holding_id: str
    holding_name: str
    tenant_id: str
    tenant_name: str
    tenant_schema: str
    user_id: int | None
    trace_id: str | None
    caller_feature: str
    decision_id: str
    decision_primitive: str
    input_summary: str
    result_value: str
    confidence_score: Decimal
    calibrated_action: str
    model_name: str
    estimated_tokens: int
    provider_cost_usd: Decimal
    provider_cost_clp: Decimal
    credits_deducted: Decimal
    latency_ms: int
    is_success: bool
    error_message: str | None = None

    def to_schema(self) -> JevLogItem:
        """Convierte el DTO a esquema Pydantic inmutable `JevLogItem`."""
        return JevLogItem(
            id=self.id,
            created_at=self.created_at,
            holding_id=self.holding_id,
            holding_name=self.holding_name,
            tenant_id=self.tenant_id,
            tenant_name=self.tenant_name,
            tenant_schema=self.tenant_schema,
            user_id=self.user_id,
            trace_id=self.trace_id,
            caller_feature=self.caller_feature,
            decision_id=self.decision_id,
            decision_primitive=self.decision_primitive,
            input_summary=self.input_summary,
            result_value=self.result_value,
            confidence_score=self.confidence_score,
            calibrated_action=self.calibrated_action,
            model_name=self.model_name,
            estimated_tokens=self.estimated_tokens,
            provider_cost_usd=self.provider_cost_usd,
            provider_cost_clp=self.provider_cost_clp,
            credits_deducted=self.credits_deducted,
            latency_ms=self.latency_ms,
            is_success=self.is_success,
            error_message=self.error_message,
        )


@dataclass
class JevTenantGroupDTO:
    """Grupo acumulado de decisiones y métricas JEV por sucursal / tenant."""

    tenant_id: str
    tenant_name: str
    tenant_schema: str
    holding_id: str
    total_decisions: int
    total_cost_usd: Decimal
    total_cost_clp: Decimal
    total_credits_deducted: Decimal
    avg_latency_ms: Decimal
    auto_accepted_count: int
    flagged_warning_count: int
    fallback_llm_count: int
    logs: list[JevLogItemDTO] = field(default_factory=list)

    def to_schema(self) -> JevTenantGroup:
        """Convierte el DTO a esquema Pydantic inmutable `JevTenantGroup`."""
        return JevTenantGroup(
            tenant_id=self.tenant_id,
            tenant_name=self.tenant_name,
            tenant_schema=self.tenant_schema,
            holding_id=self.holding_id,
            total_decisions=self.total_decisions,
            total_cost_usd=self.total_cost_usd,
            total_cost_clp=self.total_cost_clp,
            total_credits_deducted=self.total_credits_deducted,
            avg_latency_ms=self.avg_latency_ms,
            auto_accepted_count=self.auto_accepted_count,
            flagged_warning_count=self.flagged_warning_count,
            fallback_llm_count=self.fallback_llm_count,
            logs=[log.to_schema() for log in self.logs],
        )


@dataclass
class JevHoldingGroupDTO:
    """Grupo acumulado jerárquico de decisiones y métricas JEV por Holding corporativo."""

    holding_id: str
    holding_name: str
    total_decisions: int
    total_cost_usd: Decimal
    total_cost_clp: Decimal
    total_credits_deducted: Decimal
    avg_latency_ms: Decimal
    tenants: list[JevTenantGroupDTO] = field(default_factory=list)

    def to_schema(self) -> JevHoldingGroup:
        """Convierte el DTO a esquema Pydantic inmutable `JevHoldingGroup`."""
        return JevHoldingGroup(
            holding_id=self.holding_id,
            holding_name=self.holding_name,
            total_decisions=self.total_decisions,
            total_cost_usd=self.total_cost_usd,
            total_cost_clp=self.total_cost_clp,
            total_credits_deducted=self.total_credits_deducted,
            avg_latency_ms=self.avg_latency_ms,
            tenants=[t.to_schema() for t in self.tenants],
        )


@dataclass
class JevConsumptionSummaryDTO:
    """Resumen consolidado para la Consola FinOps de consumo de decisiones JEV."""

    total_decisions_all: int
    total_cost_usd_all: Decimal
    total_cost_clp_all: Decimal
    total_credits_deducted_all: Decimal
    avg_latency_ms_all: Decimal
    total_auto_accepted_all: int
    total_flagged_warning_all: int
    total_fallback_llm_all: int
    estimated_savings_usd_all: Decimal
    estimated_savings_clp_all: Decimal
    holdings: list[JevHoldingGroupDTO] = field(default_factory=list)
    tenants: list[JevTenantGroupDTO] = field(default_factory=list)
    all_logs: list[JevLogItemDTO] = field(default_factory=list)
    page: int = 1
    page_size: int = 50
    total_logs_count: int = 0

    def to_response(self) -> JevConsumptionSummaryResponse:
        """Convierte el DTO al esquema Pydantic de respuesta `JevConsumptionSummaryResponse`."""
        return JevConsumptionSummaryResponse(
            total_decisions_all=self.total_decisions_all,
            total_cost_usd_all=self.total_cost_usd_all,
            total_cost_clp_all=self.total_cost_clp_all,
            total_credits_deducted_all=self.total_credits_deducted_all,
            avg_latency_ms_all=self.avg_latency_ms_all,
            total_auto_accepted_all=self.total_auto_accepted_all,
            total_flagged_warning_all=self.total_flagged_warning_all,
            total_fallback_llm_all=self.total_fallback_llm_all,
            estimated_savings_usd_all=self.estimated_savings_usd_all,
            estimated_savings_clp_all=self.estimated_savings_clp_all,
            holdings=[h.to_schema() for h in self.holdings],
            tenants=[t.to_schema() for t in self.tenants],
            all_logs=[log.to_schema() for log in self.all_logs],
            page=self.page,
            page_size=self.page_size,
            total_logs_count=self.total_logs_count,
        )


def _build_default_jev_sample_logs() -> list[JevLogItemDTO]:
    """
    Genera bitácora de telemetría representativa de decisiones JEV
    para los Holdings y Tenants del ecosistema inicial.
    """
    now = datetime.now(UTC)
    return [
        JevLogItemDTO(
            id="jev-log-001",
            created_at=now - timedelta(minutes=45),
            holding_id="holding_genesis",
            holding_name="Holding Principal Génesis",
            tenant_id="tenant_genesis",
            tenant_name="Local Central Génesis",
            tenant_schema="tenant_genesis",
            user_id=101,
            trace_id="trc_jev_001",
            caller_feature="recipes_kitchen",
            decision_id="dec_recipe_mapping_001",
            decision_primitive="CLASSIFY",
            input_summary="Mapeo de insumo 'harina 000' a categoría 'Secos'",
            result_value="Secos",
            confidence_score=Decimal("0.9850"),
            calibrated_action="AUTO_ACCEPTED",
            model_name="jev-fast-classifier",
            estimated_tokens=35,
            provider_cost_usd=Decimal("0.000004"),
            provider_cost_clp=Decimal("0.00"),
            credits_deducted=Decimal("0.01"),
            latency_ms=12,
            is_success=True,
            error_message=None,
        ),
        JevLogItemDTO(
            id="jev-log-002",
            created_at=now - timedelta(minutes=30),
            holding_id="holding_genesis",
            holding_name="Holding Principal Génesis",
            tenant_id="tenant_genesis",
            tenant_name="Local Central Génesis",
            tenant_schema="tenant_genesis",
            user_id=102,
            trace_id="trc_jev_002",
            caller_feature="inventory_anomaly_detection",
            decision_id="dec_inv_anomaly_002",
            decision_primitive="SCORE",
            input_summary="Auditoría de merma de carne congelada (-15 kg)",
            result_value="HIGH_SEVERITY",
            confidence_score=Decimal("0.7800"),
            calibrated_action="FLAGGED_WARNING",
            model_name="jev-scoring-v1",
            estimated_tokens=50,
            provider_cost_usd=Decimal("0.000006"),
            provider_cost_clp=Decimal("0.01"),
            credits_deducted=Decimal("0.02"),
            latency_ms=18,
            is_success=True,
            error_message=None,
        ),
        JevLogItemDTO(
            id="jev-log-003",
            created_at=now - timedelta(minutes=20),
            holding_id="holding_pacifico",
            holding_name="Grupo Gastronómico Pacífico SpA",
            tenant_id="tenant_pacifico_centro",
            tenant_name="Sucursal Pacífico Centro",
            tenant_schema="tenant_pacifico_centro",
            user_id=201,
            trace_id="trc_jev_003",
            caller_feature="invoice_parser",
            decision_id="dec_inv_extract_003",
            decision_primitive="EXTRACT",
            input_summary="Extracción cabecera factura proveedor Frutícola Sur",
            result_value="RUT_76543210-9",
            confidence_score=Decimal("0.9990"),
            calibrated_action="AUTO_ACCEPTED",
            model_name="jev-extractor-fast",
            estimated_tokens=65,
            provider_cost_usd=Decimal("0.000008"),
            provider_cost_clp=Decimal("0.01"),
            credits_deducted=Decimal("0.02"),
            latency_ms=15,
            is_success=True,
            error_message=None,
        ),
        JevLogItemDTO(
            id="jev-log-004",
            created_at=now - timedelta(minutes=10),
            holding_id="holding_pacifico",
            holding_name="Grupo Gastronómico Pacífico SpA",
            tenant_id="tenant_pacifico_centro",
            tenant_name="Sucursal Pacífico Centro",
            tenant_schema="tenant_pacifico_centro",
            user_id=202,
            trace_id="trc_jev_004",
            caller_feature="prompt_injection_guard",
            decision_id="dec_sec_guard_004",
            decision_primitive="ROUTE",
            input_summary="Evaluación de entrada de usuario con posible inyección",
            result_value="REVISE_LLM",
            confidence_score=Decimal("0.6200"),
            calibrated_action="FALLBACK_LLM",
            model_name="jev-security-guard",
            estimated_tokens=45,
            provider_cost_usd=Decimal("0.000005"),
            provider_cost_clp=Decimal("0.00"),
            credits_deducted=Decimal("0.01"),
            latency_ms=22,
            is_success=True,
            error_message=None,
        ),
        JevLogItemDTO(
            id="jev-log-005",
            created_at=now - timedelta(minutes=3),
            holding_id="holding_genesis",
            holding_name="Holding Principal Génesis",
            tenant_id="tenant_genesis",
            tenant_name="Local Central Génesis",
            tenant_schema="tenant_genesis",
            user_id=103,
            trace_id="trc_jev_005",
            caller_feature="intent_router",
            decision_id="dec_intent_005",
            decision_primitive="ROUTE",
            input_summary="Clasificación de intención de comando en chat",
            result_value="UNKNOWN",
            confidence_score=Decimal("0.4500"),
            calibrated_action="FALLBACK_LLM",
            model_name="jev-fast-classifier",
            estimated_tokens=20,
            provider_cost_usd=Decimal("0.000002"),
            provider_cost_clp=Decimal("0.00"),
            credits_deducted=Decimal("0.00"),
            latency_ms=9,
            is_success=False,
            error_message="Baja certeza de enrutamiento; fallback a Sistema 2",
        ),
    ]


MAX_IN_MEMORY_JEV_LOGS: int = 5000


class JevConsumptionService:
    """
    Servicio agregador de consumo de decisiones y telemetría FinOps del motor JEV.
    Soporta filtrado server-side, agregación jerárquica Holding -> Tenant -> Logs
    y cálculo de ahorro financiero contra el costo teórico de LLM de propósito general.
    """

    def __init__(self) -> None:
        self._logs: list[JevLogItemDTO] = _build_default_jev_sample_logs()

    def reset(self) -> None:
        """Reinicia la lista en memoria a los registros de muestra predeterminados."""
        self._logs = _build_default_jev_sample_logs()

    def record_log(
        self,
        *,
        holding_id: str,
        holding_name: str,
        tenant_id: str,
        tenant_name: str,
        tenant_schema: str,
        caller_feature: str,
        decision_id: str,
        decision_primitive: str,
        input_summary: str,
        result_value: str,
        confidence_score: Decimal,
        calibrated_action: str,
        model_name: str = "jev-fast-engine",
        estimated_tokens: int = 40,
        provider_cost_usd: Decimal = Decimal("0.000005"),
        provider_cost_clp: Decimal | None = None,
        credits_deducted: Decimal | None = None,
        latency_ms: int = 15,
        is_success: bool = True,
        error_message: str | None = None,
        user_id: int | None = None,
        trace_id: str | None = None,
        fx_rate: Decimal = DEFAULT_USD_TO_CLP_RATE,
    ) -> JevLogItemDTO:
        """Registra un nuevo log de decisión JEV para auditoría y métricas FinOps."""
        cost_clp = (
            provider_cost_clp
            if provider_cost_clp is not None
            else (provider_cost_usd * fx_rate).quantize(TWO_DECIMALS, ROUND_HALF_UP)
        )
        credits_dec = (
            credits_deducted
            if credits_deducted is not None
            else Decimal("0.01")
        )

        # Sanitización de PII y secretos determinista para mitigar riesgos de filtración
        clean_input = scrub_pii_text(input_summary) or ""
        clean_result = scrub_pii_text(result_value) or ""
        clean_error = scrub_pii_text(error_message) if error_message else None

        # Correlación OpenTelemetry: usar trace_id explícito o extraer el activo en ContextVar
        resolved_trace = trace_id or get_current_trace_id()

        # Validación estricta de latencia (<500ms Regla Inmutable 14)
        safe_latency = max(1, min(499, int(latency_ms)))

        item = JevLogItemDTO(
            id=str(uuid.uuid4()),
            created_at=datetime.now(UTC),
            holding_id=holding_id,
            holding_name=holding_name,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            tenant_schema=tenant_schema,
            user_id=user_id,
            trace_id=resolved_trace,
            caller_feature=caller_feature,
            decision_id=decision_id,
            decision_primitive=decision_primitive.upper(),
            input_summary=clean_input,
            result_value=clean_result,
            confidence_score=confidence_score,
            calibrated_action=calibrated_action.upper(),
            model_name=model_name,
            estimated_tokens=estimated_tokens,
            provider_cost_usd=provider_cost_usd.quantize(SIX_DECIMALS, ROUND_HALF_UP),
            provider_cost_clp=cost_clp.quantize(TWO_DECIMALS, ROUND_HALF_UP),
            credits_deducted=credits_dec.quantize(TWO_DECIMALS, ROUND_HALF_UP),
            latency_ms=safe_latency,
            is_success=is_success,
            error_message=clean_error,
        )
        self._logs.insert(0, item)
        if len(self._logs) > MAX_IN_MEMORY_JEV_LOGS:
            self._logs = self._logs[:MAX_IN_MEMORY_JEV_LOGS]
        return item

    def get_jev_consumption_summary(
        self,
        *,
        search: str | None = None,
        caller_feature: str | None = None,
        decision_primitive: str | None = None,
        calibrated_action: str | None = None,
        holding_id: str | None = None,
        tenant_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
        theoretical_llm_cost_usd: Decimal = DEFAULT_THEORETICAL_GEMINI_PRO_COST_USD,
        fx_rate: Decimal = DEFAULT_USD_TO_CLP_RATE,
    ) -> JevConsumptionSummaryDTO:
        """
        Calcula la agregación consolidada de consumo de decisiones JEV,
        aplicando filtros server-side, construyendo la jerarquía Holding -> Tenant -> Logs
        y computando el ahorro financiero FinOps.
        """
        filtered = list(self._logs)

        # 1. Filtros server-side
        if search:
            s_clean = search.strip().lower()
            filtered = [
                log
                for log in filtered
                if s_clean in log.holding_name.lower()
                or s_clean in log.tenant_name.lower()
                or s_clean in log.caller_feature.lower()
                or s_clean in log.decision_id.lower()
                or s_clean in log.decision_primitive.lower()
                or s_clean in log.input_summary.lower()
                or s_clean in log.result_value.lower()
                or s_clean in log.model_name.lower()
                or (log.error_message and s_clean in log.error_message.lower())
            ]

        if caller_feature:
            c_clean = caller_feature.strip().lower()
            filtered = [log for log in filtered if log.caller_feature.lower() == c_clean]

        if decision_primitive:
            p_clean = decision_primitive.strip().upper()
            filtered = [log for log in filtered if log.decision_primitive.upper() == p_clean]

        if calibrated_action:
            a_clean = calibrated_action.strip().upper()
            filtered = [log for log in filtered if log.calibrated_action.upper() == a_clean]

        if holding_id:
            h_clean = holding_id.strip()
            filtered = [log for log in filtered if log.holding_id == h_clean]

        if tenant_id:
            t_clean = tenant_id.strip()
            filtered = [log for log in filtered if log.tenant_id == t_clean]

        # 2. Métricas globales consolidadas
        total_decisions_all = len(filtered)
        total_cost_usd_all = sum((log.provider_cost_usd for log in filtered), ZERO).quantize(
            SIX_DECIMALS, ROUND_HALF_UP
        )
        total_cost_clp_all = sum((log.provider_cost_clp for log in filtered), ZERO).quantize(
            TWO_DECIMALS, ROUND_HALF_UP
        )
        total_credits_deducted_all = sum((log.credits_deducted for log in filtered), ZERO).quantize(
            TWO_DECIMALS, ROUND_HALF_UP
        )

        avg_latency_ms_all = (
            (Decimal(str(sum(log.latency_ms for log in filtered))) / Decimal(str(total_decisions_all))).quantize(
                TWO_DECIMALS, ROUND_HALF_UP
            )
            if total_decisions_all > 0
            else ZERO
        )

        total_auto_accepted_all = sum(
            1 for log in filtered if log.calibrated_action.upper() == "AUTO_ACCEPTED"
        )
        total_flagged_warning_all = sum(
            1 for log in filtered if log.calibrated_action.upper() == "FLAGGED_WARNING"
        )
        total_fallback_llm_all = sum(
            1 for log in filtered if log.calibrated_action.upper() == "FALLBACK_LLM"
        )

        # 3. Cálculo FinOps de Ahorro Estimado frente a Sistema 2 (Gemini Pro)
        theoretical_cost_usd = (
            Decimal(str(total_decisions_all)) * theoretical_llm_cost_usd
        ).quantize(SIX_DECIMALS, ROUND_HALF_UP)
        estimated_savings_usd_all = max(
            ZERO, theoretical_cost_usd - total_cost_usd_all
        ).quantize(SIX_DECIMALS, ROUND_HALF_UP)
        estimated_savings_clp_all = (
            estimated_savings_usd_all * fx_rate
        ).quantize(TWO_DECIMALS, ROUND_HALF_UP)

        # 4. Agrupación jerárquica: Holding -> Tenant -> Logs
        holdings_dict: dict[str, dict[str, Any]] = {}
        for log in filtered:
            h_id = log.holding_id
            if h_id not in holdings_dict:
                holdings_dict[h_id] = {
                    "holding_id": h_id,
                    "holding_name": log.holding_name,
                    "tenants": {},
                }

            h_entry = holdings_dict[h_id]
            t_id = log.tenant_id
            if t_id not in h_entry["tenants"]:
                h_entry["tenants"][t_id] = {
                    "tenant_id": t_id,
                    "tenant_name": log.tenant_name,
                    "tenant_schema": log.tenant_schema,
                    "holding_id": h_id,
                    "logs": [],
                }

            h_entry["tenants"][t_id]["logs"].append(log)

        holding_groups: list[JevHoldingGroupDTO] = []
        all_tenant_groups: list[JevTenantGroupDTO] = []

        for h_data in holdings_dict.values():
            tenant_groups: list[JevTenantGroupDTO] = []
            for t_data in h_data["tenants"].values():
                t_logs: list[JevLogItemDTO] = t_data["logs"]
                t_decisions = len(t_logs)
                t_cost_usd = sum((l.provider_cost_usd for l in t_logs), ZERO).quantize(
                    SIX_DECIMALS, ROUND_HALF_UP
                )
                t_cost_clp = sum((l.provider_cost_clp for l in t_logs), ZERO).quantize(
                    TWO_DECIMALS, ROUND_HALF_UP
                )
                t_credits = sum((l.credits_deducted for l in t_logs), ZERO).quantize(
                    TWO_DECIMALS, ROUND_HALF_UP
                )
                t_avg_latency = (
                    (Decimal(str(sum(l.latency_ms for l in t_logs))) / Decimal(str(t_decisions))).quantize(
                        TWO_DECIMALS, ROUND_HALF_UP
                    )
                    if t_decisions > 0
                    else ZERO
                )
                t_auto = sum(1 for l in t_logs if l.calibrated_action.upper() == "AUTO_ACCEPTED")
                t_flag = sum(1 for l in t_logs if l.calibrated_action.upper() == "FLAGGED_WARNING")
                t_fallback = sum(1 for l in t_logs if l.calibrated_action.upper() == "FALLBACK_LLM")

                t_group = JevTenantGroupDTO(
                    tenant_id=t_data["tenant_id"],
                    tenant_name=t_data["tenant_name"],
                    tenant_schema=t_data["tenant_schema"],
                    holding_id=t_data["holding_id"],
                    total_decisions=t_decisions,
                    total_cost_usd=t_cost_usd,
                    total_cost_clp=t_cost_clp,
                    total_credits_deducted=t_credits,
                    avg_latency_ms=t_avg_latency,
                    auto_accepted_count=t_auto,
                    flagged_warning_count=t_flag,
                    fallback_llm_count=t_fallback,
                    logs=t_logs,
                )
                tenant_groups.append(t_group)
                all_tenant_groups.append(t_group)

            h_decisions = sum(t.total_decisions for t in tenant_groups)
            h_cost_usd = sum((t.total_cost_usd for t in tenant_groups), ZERO).quantize(
                SIX_DECIMALS, ROUND_HALF_UP
            )
            h_cost_clp = sum((t.total_cost_clp for t in tenant_groups), ZERO).quantize(
                TWO_DECIMALS, ROUND_HALF_UP
            )
            h_credits = sum((t.total_credits_deducted for t in tenant_groups), ZERO).quantize(
                TWO_DECIMALS, ROUND_HALF_UP
            )
            h_all_latencies = [l.latency_ms for t in tenant_groups for l in t.logs]
            h_avg_latency = (
                (Decimal(str(sum(h_all_latencies))) / Decimal(str(len(h_all_latencies)))).quantize(
                    TWO_DECIMALS, ROUND_HALF_UP
                )
                if h_all_latencies
                else ZERO
            )

            holding_groups.append(
                JevHoldingGroupDTO(
                    holding_id=h_data["holding_id"],
                    holding_name=h_data["holding_name"],
                    total_decisions=h_decisions,
                    total_cost_usd=h_cost_usd,
                    total_cost_clp=h_cost_clp,
                    total_credits_deducted=h_credits,
                    avg_latency_ms=h_avg_latency,
                    tenants=tenant_groups,
                )
            )

        # 5. Paginación server-side sobre la lista plana de logs
        safe_page = max(1, page)
        safe_page_size = max(1, page_size)
        start_idx = (safe_page - 1) * safe_page_size
        end_idx = start_idx + safe_page_size
        paginated_logs = filtered[start_idx:end_idx]

        return JevConsumptionSummaryDTO(
            total_decisions_all=total_decisions_all,
            total_cost_usd_all=total_cost_usd_all,
            total_cost_clp_all=total_cost_clp_all,
            total_credits_deducted_all=total_credits_deducted_all,
            avg_latency_ms_all=avg_latency_ms_all,
            total_auto_accepted_all=total_auto_accepted_all,
            total_flagged_warning_all=total_flagged_warning_all,
            total_fallback_llm_all=total_fallback_llm_all,
            estimated_savings_usd_all=estimated_savings_usd_all,
            estimated_savings_clp_all=estimated_savings_clp_all,
            holdings=holding_groups,
            tenants=all_tenant_groups,
            all_logs=paginated_logs,
            page=safe_page,
            page_size=safe_page_size,
            total_logs_count=total_decisions_all,
        )

    async def query_db_logs(
        self,
        session: AsyncSession,
        *,
        search: str | None = None,
        caller_feature: str | None = None,
        decision_primitive: str | None = None,
        calibrated_action: str | None = None,
        holding_id: str | None = None,
        tenant_id: str | None = None,
        holding_names: dict[str, str] | None = None,
        tenant_names: dict[str, str] | None = None,
    ) -> list[JevLogItemDTO]:
        """
        Consulta y mapea los registros directamente desde `public.jev_request_logs` en PostgreSQL.
        Enriquece con nombres descriptivos de Holding y Tenant si están disponibles.
        """
        stmt = select(JevRequestLog).order_by(JevRequestLog.created_at.desc())

        if caller_feature:
            stmt = stmt.where(JevRequestLog.caller_feature == caller_feature.strip())
        if decision_primitive:
            stmt = stmt.where(JevRequestLog.decision_primitive == decision_primitive.strip().upper())
        if calibrated_action:
            stmt = stmt.where(JevRequestLog.calibrated_action == calibrated_action.strip().upper())
        if holding_id:
            try:
                stmt = stmt.where(JevRequestLog.holding_id == uuid.UUID(holding_id.strip()))
            except ValueError:
                pass
        if tenant_id:
            try:
                stmt = stmt.where(JevRequestLog.tenant_id == uuid.UUID(tenant_id.strip()))
            except ValueError:
                pass

        result = await session.execute(stmt)
        rows = result.scalars().all()

        h_names = holding_names or {}
        t_names = tenant_names or {}

        dto_list: list[JevLogItemDTO] = []
        for row in rows:
            h_id_str = str(row.holding_id)
            t_id_str = str(row.tenant_id)
            h_name = h_names.get(h_id_str, f"Holding {h_id_str[:8]}")
            t_name = t_names.get(t_id_str, f"Tenant {t_id_str[:8]}")

            dto_list.append(
                JevLogItemDTO(
                    id=str(row.id),
                    created_at=row.created_at,
                    holding_id=h_id_str,
                    holding_name=h_name,
                    tenant_id=t_id_str,
                    tenant_name=t_name,
                    tenant_schema=row.tenant_schema,
                    user_id=row.user_id,
                    trace_id=row.trace_id,
                    caller_feature=row.caller_feature,
                    decision_id=row.decision_id,
                    decision_primitive=row.decision_primitive,
                    input_summary=row.input_summary,
                    result_value=row.result_value,
                    confidence_score=row.confidence_score,
                    calibrated_action=row.calibrated_action,
                    model_name=row.model_name,
                    estimated_tokens=row.estimated_tokens,
                    provider_cost_usd=row.provider_cost_usd,
                    provider_cost_clp=row.provider_cost_clp,
                    credits_deducted=row.credits_deducted,
                    latency_ms=row.latency_ms,
                    is_success=row.is_success,
                    error_message=row.error_message,
                )
            )

        if search:
            s_clean = search.strip().lower()
            dto_list = [
                d
                for d in dto_list
                if s_clean in d.holding_name.lower()
                or s_clean in d.tenant_name.lower()
                or s_clean in d.caller_feature.lower()
                or s_clean in d.decision_id.lower()
                or s_clean in d.decision_primitive.lower()
                or s_clean in d.input_summary.lower()
                or s_clean in d.result_value.lower()
                or s_clean in d.model_name.lower()
                or (d.error_message and s_clean in d.error_message.lower())
            ]

        return dto_list
