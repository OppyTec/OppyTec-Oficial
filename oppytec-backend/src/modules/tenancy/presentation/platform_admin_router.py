"""
oppytec-backend/src/modules/tenancy/presentation/platform_admin_router.py
Endpoints REST de Administración de Plataforma SaaS, Planes Comerciales y FinOps de Tokens IA:
- `/api/v1/platform-admin/plans` (GET, POST)
- `/api/v1/platform-admin/plans/{slug}` (PUT, DELETE con validación 409 de clientes activos)
- `/api/v1/platform-admin/ai-credits/policy` (GET, PUT)
- `/api/v1/platform-admin/token-consumption` (GET con agregación jerárquica Holding -> Tenant -> Logs)
- `/api/v1/platform-admin/jev-consumption` (GET con agregación jerárquica JEV Holding -> Tenant -> Logs)
- `/api/v1/platform-admin/holdings/{id}/ai-credits` (PATCH)
- `/api/v1/platform-admin/tenants/{id}/ai-credits` (PATCH)
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status

from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireGlobalPermission,
)
from src.core.mock_data_manager import DEMO_HOLDING_IDS
from src.core.observability import trace_span
from src.modules.oppy_ai.application.token_consumption_service import (
    HoldingGroupDTO,
    TenantGroupDTO,
    TokenConsumptionAggregatorService,
    TokenConsumptionSummaryDTO,
    TokenLogItemDTO,
)
from src.modules.tenancy.application.admin_plans_service import (
    AdminPlansService,
    SystemPlanDetailDTO,
)
from src.modules.tenancy.application.credit_quota_adjustment_service import (
    CreditQuotaAdjustmentService,
)
from src.modules.tenancy.application.jev_consumption_service import (
    JevConsumptionService,
    JevConsumptionSummaryDTO,
    JevHoldingGroupDTO,
    JevLogItemDTO,
    JevTenantGroupDTO,
)
from src.modules.tenancy.application.saas_policy_service import (
    SaaSAIPolicyDTO,
    SaaSPolicyService,
)
from src.modules.tenancy.presentation.router import _holdings_store, _tenants_store
from src.modules.tenancy.presentation.schemas_platform_admin import (
    CreditQuotaAdjustmentResponse,
    HoldingCreditsUpdateRequest,
    HoldingGroupResponse,
    JevConsumptionSummaryResponse,
    JevHoldingGroup,
    JevLogItem,
    JevTenantGroup,
    SaaSAIPolicyResponse,
    SaaSAIPolicyUpdateRequest,
    SystemPlanCreateRequest,
    SystemPlanDetailResponse,
    SystemPlanUpdateRequest,
    TenantCreditsUpdateRequest,
    TenantGroupResponse,
    TokenConsumptionSummaryResponse,
    TokenLogItemResponse,
)

router = APIRouter(tags=["platform_admin"])

# Servicios de aplicación singleton para administración de plataforma
_saas_policy_service = SaaSPolicyService()
_admin_plans_service = AdminPlansService()
_admin_plans_service.set_clients_stores(_holdings_store, _tenants_store)
_credit_quota_service = CreditQuotaAdjustmentService()
_token_consumption_service = TokenConsumptionAggregatorService()
_jev_consumption_service = JevConsumptionService()


# ============================================================================
# MAPPER UTILITIES
# ============================================================================


def _map_plan_dto(dto: SystemPlanDetailDTO) -> SystemPlanDetailResponse:
    return SystemPlanDetailResponse(
        slug=dto.slug,
        name=dto.name,
        tier=dto.tier,
        monthly_ai_credits=dto.monthly_ai_credits,
        description=dto.description,
        is_popular=dto.is_popular,
        is_active=dto.is_active,
        max_active_users=dto.max_active_users,
        max_products=dto.max_products,
        max_suppliers=dto.max_suppliers,
        max_recipes=dto.max_recipes,
        max_combos=dto.max_combos,
        max_storage_mb=dto.max_storage_mb,
        included_modules=dto.included_modules,
        anchor_currency=dto.anchor_currency,
        price_clp=dto.price_clp,
        price_usd=dto.price_usd,
        price_eur=dto.price_eur,
        price_brl=dto.price_brl,
        auto_convert_fx=dto.auto_convert_fx,
        active_clients_count=dto.active_clients_count,
    )


def _map_policy_dto(dto: SaaSAIPolicyDTO) -> SaaSAIPolicyResponse:
    return SaaSAIPolicyResponse(
        tokens_per_credit=dto.tokens_per_credit,
        default_monthly_credits=dto.default_monthly_credits,
        credit_price_clp=dto.credit_price_clp,
        credit_price_usd=dto.credit_price_usd,
        updated_at=dto.updated_at,
        updated_by=dto.updated_by,
    )


def _map_token_log_dto(dto: TokenLogItemDTO) -> TokenLogItemResponse:
    return TokenLogItemResponse(
        id=dto.id,
        created_at=dto.created_at,
        holding_id=dto.holding_id,
        holding_name=dto.holding_name,
        tenant_id=dto.tenant_id,
        tenant_name=dto.tenant_name,
        user_id=dto.user_id,
        user_name=dto.user_name,
        caller_feature=dto.caller_feature,
        model_name=dto.model_name,
        input_tokens=dto.input_tokens,
        output_tokens=dto.output_tokens,
        total_tokens=dto.total_tokens,
        estimated_cost_usd=dto.estimated_cost_usd,
        estimated_cost_clp=dto.estimated_cost_clp,
        credits_deducted=dto.credits_deducted,
        request_duration_ms=dto.request_duration_ms,
        api_success=dto.api_success,
        error_message=dto.error_message,
    )


def _map_tenant_group_dto(dto: TenantGroupDTO) -> TenantGroupResponse:
    return TenantGroupResponse(
        tenant_id=dto.tenant_id,
        tenant_name=dto.tenant_name,
        total_requests=dto.total_requests,
        total_tokens=dto.total_tokens,
        input_tokens=dto.input_tokens,
        output_tokens=dto.output_tokens,
        estimated_cost_usd=dto.estimated_cost_usd,
        estimated_cost_clp=dto.estimated_cost_clp,
        monthly_credit_limit=dto.monthly_credit_limit,
        credits_used=dto.credits_used,
        credits_remaining=dto.credits_remaining,
        credit_usage_pct=dto.credit_usage_pct,
        logs=[_map_token_log_dto(log_dto) for log_dto in dto.logs],
    )


def _map_holding_group_dto(dto: HoldingGroupDTO) -> HoldingGroupResponse:
    return HoldingGroupResponse(
        holding_id=dto.holding_id,
        holding_name=dto.holding_name,
        total_requests=dto.total_requests,
        total_tokens=dto.total_tokens,
        input_tokens=dto.input_tokens,
        output_tokens=dto.output_tokens,
        estimated_cost_usd=dto.estimated_cost_usd,
        estimated_cost_clp=dto.estimated_cost_clp,
        monthly_credit_limit=dto.monthly_credit_limit,
        credit_distribution_mode=dto.credit_distribution_mode,
        credits_used=dto.credits_used,
        credits_remaining=dto.credits_remaining,
        credit_usage_pct=dto.credit_usage_pct,
        tenants=[_map_tenant_group_dto(t) for t in dto.tenants],
    )


def _map_token_summary_dto(dto: TokenConsumptionSummaryDTO) -> TokenConsumptionSummaryResponse:
    return TokenConsumptionSummaryResponse(
        holdings=[_map_holding_group_dto(h) for h in dto.holdings],
        logs=[_map_token_log_dto(log_dto) for log_dto in dto.logs],
        total_records=dto.total_records,
        total_tokens_all=dto.total_tokens_all,
        total_cost_usd_all=dto.total_cost_usd_all,
        total_cost_clp_all=dto.total_cost_clp_all,
        total_credits_used_all=dto.total_credits_used_all,
        tokens_per_credit=dto.tokens_per_credit,
        page=dto.page,
        page_size=dto.page_size,
    )


def _map_jev_log_dto(dto: JevLogItemDTO) -> JevLogItem:
    return JevLogItem(
        id=dto.id,
        created_at=dto.created_at,
        holding_id=dto.holding_id,
        holding_name=dto.holding_name,
        tenant_id=dto.tenant_id,
        tenant_name=dto.tenant_name,
        tenant_schema=dto.tenant_schema,
        user_id=dto.user_id,
        trace_id=dto.trace_id,
        caller_feature=dto.caller_feature,
        decision_id=dto.decision_id,
        decision_primitive=dto.decision_primitive,
        input_summary=dto.input_summary,
        result_value=dto.result_value,
        confidence_score=dto.confidence_score,
        calibrated_action=dto.calibrated_action,
        model_name=dto.model_name,
        estimated_tokens=dto.estimated_tokens,
        provider_cost_usd=dto.provider_cost_usd,
        provider_cost_clp=dto.provider_cost_clp,
        credits_deducted=dto.credits_deducted,
        latency_ms=dto.latency_ms,
        is_success=dto.is_success,
        error_message=dto.error_message,
    )


def _map_jev_tenant_group_dto(dto: JevTenantGroupDTO) -> JevTenantGroup:
    return JevTenantGroup(
        tenant_id=dto.tenant_id,
        tenant_name=dto.tenant_name,
        tenant_schema=dto.tenant_schema,
        holding_id=dto.holding_id,
        total_decisions=dto.total_decisions,
        total_cost_usd=dto.total_cost_usd,
        total_cost_clp=dto.total_cost_clp,
        total_credits_deducted=dto.total_credits_deducted,
        avg_latency_ms=dto.avg_latency_ms,
        auto_accepted_count=dto.auto_accepted_count,
        flagged_warning_count=dto.flagged_warning_count,
        fallback_llm_count=dto.fallback_llm_count,
        logs=[_map_jev_log_dto(log_item) for log_item in dto.logs],
    )


def _map_jev_holding_group_dto(dto: JevHoldingGroupDTO) -> JevHoldingGroup:
    return JevHoldingGroup(
        holding_id=dto.holding_id,
        holding_name=dto.holding_name,
        total_decisions=dto.total_decisions,
        total_cost_usd=dto.total_cost_usd,
        total_cost_clp=dto.total_cost_clp,
        total_credits_deducted=dto.total_credits_deducted,
        avg_latency_ms=dto.avg_latency_ms,
        tenants=[_map_jev_tenant_group_dto(t) for t in dto.tenants],
    )


def _map_jev_summary_dto(dto: JevConsumptionSummaryDTO) -> JevConsumptionSummaryResponse:
    return JevConsumptionSummaryResponse(
        total_decisions_all=dto.total_decisions_all,
        total_cost_usd_all=dto.total_cost_usd_all,
        total_cost_clp_all=dto.total_cost_clp_all,
        total_credits_deducted_all=dto.total_credits_deducted_all,
        avg_latency_ms_all=dto.avg_latency_ms_all,
        total_auto_accepted_all=dto.total_auto_accepted_all,
        total_flagged_warning_all=dto.total_flagged_warning_all,
        total_fallback_llm_all=dto.total_fallback_llm_all,
        estimated_savings_usd_all=dto.estimated_savings_usd_all,
        estimated_savings_clp_all=dto.estimated_savings_clp_all,
        holdings=[_map_jev_holding_group_dto(h) for h in dto.holdings],
        tenants=[_map_jev_tenant_group_dto(t) for t in dto.tenants],
        all_logs=[_map_jev_log_dto(log_item) for log_item in dto.all_logs],
        page=dto.page,
        page_size=dto.page_size,
        total_logs_count=dto.total_logs_count,
    )


# ============================================================================
# 1. ENDPOINTS DE PLANES COMERCIALES
# ============================================================================


@router.get(
    "/api/v1/platform-admin/plans",
    response_model=list[SystemPlanDetailResponse],
    status_code=status.HTTP_200_OK,
)
async def list_admin_plans_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.plans.read")),
    ],
) -> list[SystemPlanDetailResponse]:
    """Lista el catálogo de Planes Comerciales ordenado por `tier ASC` con recuento de clientes activos."""
    plans = _admin_plans_service.list_plans()
    return [_map_plan_dto(p) for p in plans]


@router.post(
    "/api/v1/platform-admin/plans",
    response_model=SystemPlanDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_plan_endpoint(
    payload: SystemPlanCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.plans.manage")),
    ],
) -> SystemPlanDetailResponse:
    """Crea un nuevo Plan Comercial con cuotas paramétricas y créditos mensuales de IA."""
    created = _admin_plans_service.create_plan(
        payload.model_dump(),
        actor_id=principal.user_id,
    )
    return _map_plan_dto(created)


@router.put(
    "/api/v1/platform-admin/plans/{slug}",
    response_model=SystemPlanDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def update_admin_plan_endpoint(
    slug: str,
    payload: SystemPlanUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.plans.manage")),
    ],
) -> SystemPlanDetailResponse:
    """Actualiza cuotas, precios multi-moneda y módulos de un Plan Comercial existente."""
    updated = _admin_plans_service.update_plan(
        slug=slug,
        payload=payload.model_dump(exclude_unset=True),
        actor_id=principal.user_id,
    )
    return _map_plan_dto(updated)


@router.delete(
    "/api/v1/platform-admin/plans/{slug}",
    response_model=SystemPlanDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_admin_plan_endpoint(
    slug: str,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.plans.manage")),
    ],
) -> SystemPlanDetailResponse:
    """
    Elimina un Plan Comercial.
    Arroja HTTP 409 Conflict si existen Holdings o Clientes activos suscritos a él.
    """
    deleted = _admin_plans_service.delete_plan(slug=slug, actor_id=principal.user_id)
    return _map_plan_dto(deleted)


# ============================================================================
# 2. ENDPOINTS DE POLÍTICA GLOBAL SAAS (CONVERSIÓN TOKENS A CRÉDITOS IA)
# ============================================================================


@router.get(
    "/api/v1/platform-admin/ai-credits/policy",
    response_model=SaaSAIPolicyResponse,
    status_code=status.HTTP_200_OK,
)
async def get_saas_ai_policy_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.plans.read")),
    ],
) -> SaaSAIPolicyResponse:
    """Obtiene la política global de conversión de tokens y precios unitarios de créditos."""
    policy = _saas_policy_service.get_policy_config()
    return _map_policy_dto(policy)


@router.put(
    "/api/v1/platform-admin/ai-credits/policy",
    response_model=SaaSAIPolicyResponse,
    status_code=status.HTTP_200_OK,
)
async def update_saas_ai_policy_endpoint(
    payload: SaaSAIPolicyUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.plans.manage")),
    ],
) -> SaaSAIPolicyResponse:
    """Actualiza la tasa de conversión y precios unitarios emitiendo 'saas.policy_updated'."""
    updated = _saas_policy_service.update_policy_config(
        tokens_per_credit=payload.tokens_per_credit,
        default_monthly_credits=payload.default_monthly_credits,
        credit_price_clp=payload.credit_price_clp,
        credit_price_usd=payload.credit_price_usd,
        actor_id=principal.user_id,
        holding_id=principal.holding_id,
    )
    return _map_policy_dto(updated)


# ============================================================================
# 3. CONSOLA FINOPS DE CONSUMO DE TOKENS & CRÉDITOS
# ============================================================================


@router.get(
    "/api/v1/platform-admin/token-consumption",
    response_model=TokenConsumptionSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_token_consumption_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.tokens.read")),
    ],
    search: str | None = Query(default=None),
    model_name: str | None = Query(default=None),
    api_success: bool | None = Query(default=None),
    holding_id: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    x_oppytec_mock_mode: Annotated[
        str | None, Header(alias="X-OppyTec-Mock-Mode")
    ] = None,
) -> TokenConsumptionSummaryResponse:
    """Consulta agregada jerárquica de consumo de tokens y costos FinOps con filtros."""
    policy = _saas_policy_service.get_policy_config()
    is_clean_mode = (
        x_oppytec_mock_mode is not None
        and x_oppytec_mock_mode.strip().lower() == "clean"
    )
    if is_clean_mode:
        real_logs = [
            log
            for log in _token_consumption_service._logs
            if log.id >= 100 and log.holding_id not in DEMO_HOLDING_IDS
        ]
        if not real_logs:
            return TokenConsumptionSummaryResponse(
                holdings=[],
                logs=[],
                total_records=0,
                total_tokens_all=0,
                total_cost_usd_all=Decimal("0.000000"),
                total_cost_clp_all=Decimal("0.00"),
                total_credits_used_all=0,
                tokens_per_credit=policy.tokens_per_credit,
                page=page,
                page_size=page_size,
            )

    summary = _token_consumption_service.get_token_consumption_summary(
        search=search,
        model_name=model_name,
        api_success=api_success,
        holding_id=holding_id,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        tokens_per_credit=policy.tokens_per_credit,
        holding_quotas=_credit_quota_service._holding_quotas,
        tenant_quotas=_credit_quota_service._tenant_quotas,
    )
    return _map_token_summary_dto(summary)


# ============================================================================
# 4. CONSOLA FINOPS DE CONSUMO DE DECISIONES JEV
# ============================================================================


@router.get(
    "/api/v1/platform-admin/jev-consumption",
    response_model=JevConsumptionSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_jev_consumption_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.tokens.read")),
    ],
    search: str | None = Query(default=None),
    caller_feature: str | None = Query(default=None),
    decision_primitive: str | None = Query(default=None),
    calibrated_action: str | None = Query(default=None),
    holding_id: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    x_oppytec_mock_mode: Annotated[
        str | None, Header(alias="X-OppyTec-Mock-Mode")
    ] = None,
) -> JevConsumptionSummaryResponse:
    """
    Consulta agregada jerárquica de consumo de decisiones JEV,
    evaluaciones de confianza calibrada y cálculo de ahorro FinOps con filtros server-side.
    """
    is_clean_mode = (
        x_oppytec_mock_mode is not None
        and x_oppytec_mock_mode.strip().lower() == "clean"
    )
    with trace_span(
        "platform_admin.jev_consumption.query",
        attributes={
            "user_id": str(principal.user_id),
            "search": search or "",
            "caller_feature": caller_feature or "",
            "decision_primitive": decision_primitive or "",
            "calibrated_action": calibrated_action or "",
            "holding_id": holding_id or "",
            "tenant_id": tenant_id or "",
            "page": page,
            "page_size": page_size,
        },
        tracer_name="oppytec.tenancy.jev_consumption",
    ) as span_attrs:
        if is_clean_mode:
            real_jev_logs = [
                log
                for log in _jev_consumption_service._logs
                if not log.id.startswith("jev-log-00")
                and log.holding_id not in DEMO_HOLDING_IDS
            ]
            if not real_jev_logs:
                span_attrs["total_decisions_all"] = 0
                span_attrs["total_cost_usd_all"] = "0.000000"
                span_attrs["avg_latency_ms_all"] = "0.00"
                span_attrs["estimated_savings_usd_all"] = "0.000000"
                return JevConsumptionSummaryResponse(
                    total_decisions_all=0,
                    total_cost_usd_all=Decimal("0.000000"),
                    total_cost_clp_all=Decimal("0.00"),
                    total_credits_deducted_all=Decimal("0.00"),
                    avg_latency_ms_all=Decimal("0.00"),
                    total_auto_accepted_all=0,
                    total_flagged_warning_all=0,
                    total_fallback_llm_all=0,
                    estimated_savings_usd_all=Decimal("0.000000"),
                    estimated_savings_clp_all=Decimal("0.00"),
                    holdings=[],
                    tenants=[],
                    all_logs=[],
                    page=page,
                    page_size=page_size,
                    total_logs_count=0,
                )

        summary = _jev_consumption_service.get_jev_consumption_summary(
            search=search,
            caller_feature=caller_feature,
            decision_primitive=decision_primitive,
            calibrated_action=calibrated_action,
            holding_id=holding_id,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
        )
        span_attrs["total_decisions_all"] = summary.total_decisions_all
        span_attrs["total_cost_usd_all"] = str(summary.total_cost_usd_all)
        span_attrs["avg_latency_ms_all"] = str(summary.avg_latency_ms_all)
        span_attrs["estimated_savings_usd_all"] = str(summary.estimated_savings_usd_all)
        return _map_jev_summary_dto(summary)


# ============================================================================
# 5. MODALES DE AJUSTE DE CUPOS DE CRÉDITOS IA
# ============================================================================


@router.patch(
    "/api/v1/platform-admin/holdings/{id}/ai-credits",
    response_model=CreditQuotaAdjustmentResponse,
    status_code=status.HTTP_200_OK,
)
async def update_holding_ai_credits_endpoint(
    id: str,
    payload: HoldingCreditsUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.tokens.manage_quotas")),
    ],
) -> CreditQuotaAdjustmentResponse:
    """Ajusta el cupo mensual de créditos y modo de bolsa para un Holding corporativo."""
    quota = _credit_quota_service.update_holding_credits(
        holding_id=id,
        monthly_credits=payload.monthly_credits,
        distribution_mode=payload.distribution_mode,
        actor_id=principal.user_id,
    )
    return CreditQuotaAdjustmentResponse(
        target_id=quota.holding_id,
        target_type="holding",
        monthly_credits=quota.monthly_credits,
        distribution_mode=quota.distribution_mode,
        message=f"Cuota de Holding '{id}' actualizada a {quota.monthly_credits} créditos ({quota.distribution_mode})",
    )


@router.patch(
    "/api/v1/platform-admin/tenants/{id}/ai-credits",
    response_model=CreditQuotaAdjustmentResponse,
    status_code=status.HTTP_200_OK,
)
async def update_tenant_ai_credits_endpoint(
    id: str,
    payload: TenantCreditsUpdateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.tokens.manage_quotas")),
    ],
) -> CreditQuotaAdjustmentResponse:
    """Ajusta el cupo mensual individual de créditos para una sucursal específica (Tenant)."""
    quota = _credit_quota_service.update_tenant_credits(
        tenant_id=id,
        monthly_credits=payload.monthly_credits,
        actor_id=principal.user_id,
    )
    return CreditQuotaAdjustmentResponse(
        target_id=quota.tenant_id,
        target_type="tenant",
        monthly_credits=quota.monthly_credits,
        distribution_mode=None,
        message=f"Cuota de Tenant '{id}' actualizada a {quota.monthly_credits} créditos",
    )
