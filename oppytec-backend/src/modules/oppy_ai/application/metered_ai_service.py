"""
Orquestador E2E Medido de `OppyFy` (`src/modules/oppy_ai/application/metered_ai_service.py`).
Ejecuta el flujo completo de una consulta a `OppyFy`:
1. Verifica `is_oppyfy_enabled` y saldo de créditos en la billetera del trabajador (`WorkerCreditWalletState`).
2. Verifica seguridad anti-inyección y clasifica intención/herramienta con `JEV (Sistema 1)`.
3. Valida el RBAC editable de `OppyFy` (`evaluate_oppyfy_subdomain_access`):
   - Si no tiene permiso, bloquea la ejecución y registra `"BLOCKED_UNAUTHORIZED_PROMPT"` en la bitácora
     de auditoría (`OppyfyPromptAuditLog`).
4. Ejecuta la herramienta en código duro (con redacción `"[REDACTED_COST]"` si `can_view_costs=False`)
   y el RAG de 3 Capas (`ThreeLayerRagService`).
5. Invoca el modelo generativo (`LLMProviderPort`), consulta tarifas vigentes en `public.ai_model_configs`,
   calcula costos en USD (`NUMERIC(14,6)`) y CLP (`NUMERIC(14,2)`), descuenta créditos atómicamente,
   actualiza el porcentaje de ventana de contexto (`evaluate_context_usage`) y persiste en `public.llm_request_logs`.
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from src.adapters.ai.jev_protocol import JevDecisionPort
from src.adapters.ai.protocol import (
    EngineTierLiteral,
    LLMProviderPort,
    LlmTelemetrySinkPort,
    LlmUsageRecord,
)
from src.core.observability import trace_span
from src.modules.oppy_ai.application.rag_service import (
    RagThreeLayerBundle,
    ThreeLayerRagService,
)
from src.modules.oppy_ai.application.tool_router import (
    HardCodedToolCode,
    OppyfyToolRouter,
    RoutedToolExecutionResult,
)
from src.modules.oppy_ai.domain.context_meter import (
    ContextHealthEvaluation,
    evaluate_context_usage,
)
from src.modules.oppy_ai.domain.credit_wallet import (
    WorkerCreditWalletState,
    deduct_worker_credits,
)
from src.modules.oppy_ai.domain.oppyfy_rbac import (
    ALLOWED_PROMPT_STATUS,
    BLOCKED_UNAUTHORIZED_PROMPT,
    OppyfyAccessDecision,
    OppyfyPermissionGrantSpec,
    evaluate_oppyfy_subdomain_access,
)

_SIX_DECIMALS = Decimal("0.000001")
_TWO_DECIMALS = Decimal("0.01")
_ONE_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class ModelTariff:
    """Tarifa de tokens por millón en USD obtenida de `public.ai_model_configs`."""

    model_slug: str
    engine_tier: str = "SYSTEM_2_LLM"
    input_cost_per_1m_usd: Decimal = Decimal("0.150000")
    cached_cost_per_1m_usd: Decimal = Decimal("0.037500")
    output_cost_per_1m_usd: Decimal = Decimal("0.600000")
    embedding_cost_per_1m_usd: Decimal = Decimal("0.000000")
    is_enabled: bool = True


DEFAULT_MODEL_TARIFFS: dict[str, ModelTariff] = {
    "gemini-1.5-flash": ModelTariff(
        model_slug="gemini-1.5-flash",
        engine_tier="SYSTEM_2_LLM",
        input_cost_per_1m_usd=Decimal("0.075000"),
        cached_cost_per_1m_usd=Decimal("0.018750"),
        output_cost_per_1m_usd=Decimal("0.300000"),
    ),
    "gemini-1.5-pro": ModelTariff(
        model_slug="gemini-1.5-pro",
        engine_tier="SYSTEM_2_LLM",
        input_cost_per_1m_usd=Decimal("1.250000"),
        cached_cost_per_1m_usd=Decimal("0.312500"),
        output_cost_per_1m_usd=Decimal("5.000000"),
    ),
    "gemini-2.5-flash": ModelTariff(
        model_slug="gemini-2.5-flash",
        engine_tier="SYSTEM_2_LLM",
        input_cost_per_1m_usd=Decimal("0.150000"),
        cached_cost_per_1m_usd=Decimal("0.037500"),
        output_cost_per_1m_usd=Decimal("0.600000"),
    ),
    "gemini-3.8-flash": ModelTariff(
        model_slug="gemini-3.8-flash",
        engine_tier="SYSTEM_2_LLM",
        input_cost_per_1m_usd=Decimal("0.150000"),
        cached_cost_per_1m_usd=Decimal("0.037500"),
        output_cost_per_1m_usd=Decimal("0.600000"),
    ),
    "text-embedding-004": ModelTariff(
        model_slug="text-embedding-004",
        engine_tier="EMBEDDING",
        input_cost_per_1m_usd=Decimal("0.000000"),
        cached_cost_per_1m_usd=Decimal("0.000000"),
        output_cost_per_1m_usd=Decimal("0.000000"),
        embedding_cost_per_1m_usd=Decimal("0.025000"),
    ),
}


class ModelConfigRegistry:
    """Registro en memoria y proveedor de tarifas vigentes de `public.ai_model_configs`."""

    def __init__(self, tariffs: Mapping[str, ModelTariff] | None = None) -> None:
        self._tariffs: dict[str, ModelTariff] = dict(DEFAULT_MODEL_TARIFFS)
        if tariffs:
            self._tariffs.update(tariffs)

    def get_tariff(self, model_slug: str) -> ModelTariff:
        """Retorna la tarifa configurada para `model_slug` o el fallback estándar."""
        normalized = model_slug.lower().strip()
        for key, tariff in self._tariffs.items():
            if key in normalized:
                return tariff
        return self._tariffs.get("gemini-2.5-flash", DEFAULT_MODEL_TARIFFS["gemini-2.5-flash"])

    def set_tariff(self, tariff: ModelTariff) -> None:
        """Actualiza o registra una tarifa para un modelo específico."""
        self._tariffs[tariff.model_slug.lower().strip()] = tariff


@dataclass(frozen=True)
class OppyfyAuditEntry:
    """Entrada inmutable para persistir en `tenant_*.oppyfy_prompt_audit_log`."""

    user_id: int
    subdomain_slug: str
    prompt_text: str
    decision_status: str
    credits_consumed: Decimal
    created_at: datetime


@dataclass(frozen=True)
class OppyfyQueryRequest:
    """Solicitud de consulta de un trabajador del Tenant hacia `OppyFy`."""

    holding_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_schema: str
    user_id: int
    role_ids: tuple[int, ...]
    hierarchy_rank: int
    prompt_text: str
    wallet: WorkerCreditWalletState
    grants: tuple[OppyfyPermissionGrantSpec, ...]
    subdomain_id_by_slug: dict[str, int]
    thread_id: uuid.UUID | None = None
    prior_thread_tokens: int = 0
    language_code: str = "es"
    brand_name: str = "OppyFy"
    estimated_credit_cost: Decimal = Decimal("1.00")
    usd_to_clp_rate: Decimal = Decimal("950.00")


@dataclass(frozen=True)
class OppyfyQueryResponse:
    """Respuesta integral E2E de `OppyFy` con auditoría RBAC, billetera, contexto % y telemetría."""

    allowed: bool
    status_code: str
    answer_text: str
    routed_tool: HardCodedToolCode | None
    subdomain_slug: str
    rbac_decision: OppyfyAccessDecision | None
    tool_execution: RoutedToolExecutionResult | None
    rag_bundle: RagThreeLayerBundle | None
    updated_wallet: WorkerCreditWalletState
    credits_deducted: Decimal
    context_health: ContextHealthEvaluation
    prompt_audit_entry: OppyfyAuditEntry
    llm_usage_records: tuple[LlmUsageRecord, ...]


class MeteredAIService:
    """
    Servicio central medido de `OppyFy`.
    Garantiza que ninguna consulta se ejecute sin créditos, sin evaluación `JEV`, sin validación
    del RBAC editable del cliente y sin registro en `public.llm_request_logs` con tarifas de `ai_model_configs`.
    """

    def __init__(
        self,
        *,
        jev_port: JevDecisionPort,
        llm_port: LLMProviderPort,
        rag_service: ThreeLayerRagService,
        tool_router: OppyfyToolRouter | None = None,
        model_registry: ModelConfigRegistry | None = None,
        telemetry_sink: LlmTelemetrySinkPort | None = None,
    ) -> None:
        self._jev = jev_port
        self._llm = llm_port
        self._rag = rag_service
        self._router = tool_router or OppyfyToolRouter(jev_port)
        self._models = model_registry or ModelConfigRegistry()
        self._sink = telemetry_sink
        self._prompt_audit_logs: list[OppyfyAuditEntry] = []
        self._emitted_usage_records: list[LlmUsageRecord] = []

    @property
    def prompt_audit_logs(self) -> tuple[OppyfyAuditEntry, ...]:
        """Bitácora acumulada de `OppyfyAuditEntry` (`ALLOWED` y `BLOCKED_UNAUTHORIZED_PROMPT`)."""
        return tuple(self._prompt_audit_logs)

    @property
    def emitted_usage_records(self) -> tuple[LlmUsageRecord, ...]:
        """Registros inmutables emitidos para `public.llm_request_logs`."""
        return tuple(self._emitted_usage_records)

    def _record_usage(self, record: LlmUsageRecord) -> None:
        """Registra en memoria y en el sink persistente de telemetría."""
        self._emitted_usage_records.append(record)
        if self._sink is not None:
            self._sink.record_llm_usage(record)

    def calculate_token_cost(
        self,
        model_slug: str,
        *,
        input_tokens: int,
        cached_tokens: int = 0,
        output_tokens: int = 0,
        usd_to_clp_rate: Decimal = Decimal("950.00"),
    ) -> tuple[Decimal, Decimal]:
        """Calcula el costo exacto en USD (NUMERIC 14,6) y CLP (NUMERIC 14,2) según ai_model_configs."""
        tariff = self._models.get_tariff(model_slug)
        cost_in = (Decimal(input_tokens) * tariff.input_cost_per_1m_usd) / _ONE_MILLION
        cost_cached = (Decimal(cached_tokens) * tariff.cached_cost_per_1m_usd) / _ONE_MILLION
        cost_out = (Decimal(output_tokens) * tariff.output_cost_per_1m_usd) / _ONE_MILLION
        cost_usd = (cost_in + cost_cached + cost_out).quantize(_SIX_DECIMALS, rounding=ROUND_HALF_UP)
        cost_clp = (cost_usd * usd_to_clp_rate).quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)
        return cost_usd, cost_clp

    def execute_oppyfy_query(
        self,
        request: OppyfyQueryRequest,
        *,
        contracted_modules: Sequence[str] | None = None,
        now: datetime | None = None,
    ) -> OppyfyQueryResponse:
        """
        Orquesta de principio a fin una consulta a `OppyFy`:
        1. Verifica `is_oppyfy_enabled` y saldo de créditos en `request.wallet`.
        2. Clasifica seguridad (`Jev.boolean`) e intención/sub-dominio (`Jev.choice`).
        3. Evalúa el RBAC editable de `OppyFy`; si es denegado, registra `"BLOCKED_UNAUTHORIZED_PROMPT"`
           sin cobrar créditos de generación ni ejecutar herramientas.
        4. Ejecuta la herramienta en código duro (redactando costos si `can_view_costs=False`) + RAG 3-Capas.
        5. Genera la respuesta minimalista estilo `Pi`, descuenta créditos y actualiza `context_usage_percent`.
        """
        timestamp = now or datetime.now(UTC)
        collected_usage: list[LlmUsageRecord] = []

        with trace_span(
            "oppyfy.query",
            attributes={
                "tenant.schema": request.tenant_schema,
                "user.id": request.user_id,
                "thread.id": str(request.thread_id) if request.thread_id else "",
            },
            tracer_name="oppytec.oppyfy",
        ) as root_attrs:
            # Paso 1: Verificar interruptor is_oppyfy_enabled y saldo de créditos antes de continuar
            if not request.wallet.is_oppyfy_enabled or (
                request.wallet.remaining_credits < request.estimated_credit_cost
            ):
                status = (
                    "OPPYFY_DISABLED_FOR_WORKER"
                    if not request.wallet.is_oppyfy_enabled
                    else "INSUFFICIENT_WORKER_CREDITS"
                )
                audit_entry = OppyfyAuditEntry(
                    user_id=request.user_id,
                    subdomain_slug="unclassified",
                    prompt_text=request.prompt_text,
                    decision_status=status,
                    credits_consumed=Decimal("0.00"),
                    created_at=timestamp,
                )
                self._prompt_audit_logs.append(audit_entry)
                root_attrs["prompt.status"] = status
                root_attrs["tokens.total"] = 0
                root_attrs["credits.deducted"] = "0.00"
                return OppyfyQueryResponse(
                    allowed=False,
                    status_code=status,
                    answer_text="",
                    routed_tool=None,
                    subdomain_slug="unclassified",
                    rbac_decision=None,
                    tool_execution=None,
                    rag_bundle=None,
                    updated_wallet=request.wallet,
                    credits_deducted=Decimal("0.00"),
                    context_health=evaluate_context_usage(request.prior_thread_tokens),
                    prompt_audit_entry=audit_entry,
                    llm_usage_records=(),
                )

            # Paso 2: Guardrail de seguridad con JEV (Sistema 1) + Clasificación de intención/herramienta
            security_check = self._jev.decide_boolean(
                decision_id="OPPYFY_PROMPT_INJECTION_GUARD",
                prompt_or_input=request.prompt_text,
                holding_id=request.holding_id,
                tenant_id=request.tenant_id,
                tenant_schema=request.tenant_schema,
                user_id=request.user_id,
                caller_feature="oppyfy_security_guard",
                thread_id=request.thread_id,
            )
            self._record_usage(security_check.usage_record)
            collected_usage.append(security_check.usage_record)

            if security_check.value:
                audit_entry = OppyfyAuditEntry(
                    user_id=request.user_id,
                    subdomain_slug="security_firewall",
                    prompt_text=request.prompt_text,
                    decision_status=BLOCKED_UNAUTHORIZED_PROMPT,
                    credits_consumed=Decimal("0.00"),
                    created_at=timestamp,
                )
                self._prompt_audit_logs.append(audit_entry)
                root_attrs["prompt.status"] = BLOCKED_UNAUTHORIZED_PROMPT
                root_attrs["tokens.total"] = sum(r.total_tokens for r in collected_usage)
                root_attrs["credits.deducted"] = "0.00"
                return OppyfyQueryResponse(
                    allowed=False,
                    status_code=BLOCKED_UNAUTHORIZED_PROMPT,
                    answer_text="",
                    routed_tool=None,
                    subdomain_slug="security_firewall",
                    rbac_decision=None,
                    tool_execution=None,
                    rag_bundle=None,
                    updated_wallet=request.wallet,
                    credits_deducted=Decimal("0.00"),
                    context_health=evaluate_context_usage(request.prior_thread_tokens),
                    prompt_audit_entry=audit_entry,
                    llm_usage_records=tuple(collected_usage),
                )

            tool_code, subdomain_slug, jev_choice = self._router.classify_tool_and_subdomain(
                user_prompt=request.prompt_text,
                holding_id=request.holding_id,
                tenant_id=request.tenant_id,
                tenant_schema=request.tenant_schema,
                user_id=request.user_id,
                thread_id=request.thread_id,
            )
            self._record_usage(jev_choice.usage_record)
            collected_usage.append(jev_choice.usage_record)

            # Paso 3: Evaluar RBAC propio y editable de OppyFy
            rbac_decision = evaluate_oppyfy_subdomain_access(
                user_id=request.user_id,
                role_ids=request.role_ids,
                hierarchy_rank=request.hierarchy_rank,
                target_subdomain_slug=subdomain_slug,
                grants=request.grants,
                estimated_cost=request.estimated_credit_cost,
                contracted_modules=contracted_modules,
                now=timestamp,
            )

            if not rbac_decision.allowed:
                audit_entry = OppyfyAuditEntry(
                    user_id=request.user_id,
                    subdomain_slug=subdomain_slug,
                    prompt_text=request.prompt_text,
                    decision_status=BLOCKED_UNAUTHORIZED_PROMPT,
                    credits_consumed=Decimal("0.00"),
                    created_at=timestamp,
                )
                self._prompt_audit_logs.append(audit_entry)
                root_attrs["prompt.status"] = BLOCKED_UNAUTHORIZED_PROMPT
                root_attrs["tokens.total"] = sum(r.total_tokens for r in collected_usage)
                root_attrs["credits.deducted"] = "0.00"
                return OppyfyQueryResponse(
                    allowed=False,
                    status_code=BLOCKED_UNAUTHORIZED_PROMPT,
                    answer_text="",
                    routed_tool=tool_code,
                    subdomain_slug=subdomain_slug,
                    rbac_decision=rbac_decision,
                    tool_execution=None,
                    rag_bundle=None,
                    updated_wallet=request.wallet,
                    credits_deducted=Decimal("0.00"),
                    context_health=evaluate_context_usage(request.prior_thread_tokens),
                    prompt_audit_entry=audit_entry,
                    llm_usage_records=tuple(collected_usage),
                )

            # Paso 4: Ejecutar herramienta en código duro (con redacción de costos si can_view_costs=False) + RAG 3 Capas
            tool_result = self._router.execute_hardcoded_tool(
                tool_code,
                tenant_schema=request.tenant_schema,
                can_view_costs=rbac_decision.can_view_costs,
                jev_choice=jev_choice,
            )
            subdomain_id = request.subdomain_id_by_slug.get(subdomain_slug, 1)
            rag_bundle = self._rag.build_three_layer_context(
                user_prompt=request.prompt_text,
                authorized_subdomain_id=subdomain_id,
                user_id=request.user_id,
                routed_tool_result=tool_result,
            )

            # Paso 5: Generar respuesta con LLM (Sistema 2), descontar créditos y calcular % de contexto
            with trace_span(
                "oppyfy.metered_ai",
                attributes={},
                tracer_name="oppytec.oppyfy",
            ) as ai_attrs:
                answer_text, llm_usage = self._llm.generate_minimalist_response(
                    holding_id=request.holding_id,
                    tenant_id=request.tenant_id,
                    tenant_schema=request.tenant_schema,
                    user_id=request.user_id,
                    caller_feature="oppyfy_chat",
                    user_prompt=request.prompt_text,
                    compact_context_payload=rag_bundle.to_compact_context_dict(),
                    language_code=request.language_code,
                    brand_name=request.brand_name,
                    thread_id=request.thread_id,
                )

                # Integrar tarifas de ai_model_configs para costo USD NUMERIC(14,6) y CLP NUMERIC(14,2)
                model_tariff = self._models.get_tariff(llm_usage.model_name)
                cost_usd, cost_clp = self.calculate_token_cost(
                    model_slug=llm_usage.model_name,
                    input_tokens=llm_usage.input_tokens,
                    cached_tokens=llm_usage.cached_tokens,
                    output_tokens=llm_usage.output_tokens,
                    usd_to_clp_rate=request.usd_to_clp_rate,
                )
                final_cost_usd = cost_usd if cost_usd > Decimal("0") else llm_usage.provider_cost_usd
                ai_attrs["provider.model"] = llm_usage.model_name
                ai_attrs["provider.cost_usd"] = f"{final_cost_usd:.6f}"
                ai_attrs["tokens.input"] = llm_usage.input_tokens
                ai_attrs["tokens.output"] = llm_usage.output_tokens

            # Re-empaquetar usage record con el costo exacto calibrado por la tarifa de BD
            calibrated_usage = LlmUsageRecord(
                holding_id=llm_usage.holding_id,
                tenant_id=llm_usage.tenant_id,
                tenant_schema=llm_usage.tenant_schema,
                user_id=llm_usage.user_id,
                engine_tier=llm_usage.engine_tier,
                caller_feature=llm_usage.caller_feature,
                model_name=llm_usage.model_name,
                input_tokens=llm_usage.input_tokens,
                cached_tokens=llm_usage.cached_tokens,
                output_tokens=llm_usage.output_tokens,
                provider_cost_usd=final_cost_usd,
                provider_cost_clp=cost_clp if cost_clp > Decimal("0") else llm_usage.provider_cost_clp,
                credits_deducted=llm_usage.credits_deducted,
                request_duration_ms=llm_usage.request_duration_ms,
                thread_id=llm_usage.thread_id,
                api_success=llm_usage.api_success,
                error_message=llm_usage.error_message,
            )
            self._record_usage(calibrated_usage)
            collected_usage.append(calibrated_usage)

            total_credits_to_deduct = sum(
                (rec.credits_deducted for rec in collected_usage),
                start=Decimal("0.00"),
            )
            deduction = deduct_worker_credits(
                request.wallet,
                min(request.wallet.remaining_credits, total_credits_to_deduct),
            )

            new_total_tokens = request.prior_thread_tokens + sum(
                rec.total_tokens for rec in collected_usage
            )
            context_health = evaluate_context_usage(new_total_tokens)

            audit_entry = OppyfyAuditEntry(
                user_id=request.user_id,
                subdomain_slug=subdomain_slug,
                prompt_text=request.prompt_text,
                decision_status=ALLOWED_PROMPT_STATUS,
                credits_consumed=deduction.deducted_credits,
                created_at=timestamp,
            )
            self._prompt_audit_logs.append(audit_entry)

            root_attrs["prompt.status"] = ALLOWED_PROMPT_STATUS
            root_attrs["tokens.total"] = sum(r.total_tokens for r in collected_usage)
            root_attrs["credits.deducted"] = f"{deduction.deducted_credits:.2f}"

            return OppyfyQueryResponse(
                allowed=True,
                status_code=ALLOWED_PROMPT_STATUS,
                answer_text=answer_text,
                routed_tool=tool_code,
                subdomain_slug=subdomain_slug,
                rbac_decision=rbac_decision,
                tool_execution=tool_result,
                rag_bundle=rag_bundle,
                updated_wallet=deduction.updated_wallet,
                credits_deducted=deduction.deducted_credits,
                context_health=context_health,
                prompt_audit_entry=audit_entry,
                llm_usage_records=tuple(collected_usage),
            )
