"""
oppytec-backend/src/modules/tenancy/presentation/holding_hub_router.py
Router FastAPI para Holding Hub Enterprise en OppyTec v2.0:
- Prefix: `/api/v1/holding-hub`
- Tags: `["holding-hub"]`
- Endpoints:
  1. `GET /summary`: KPIs consolidados, balance de IA, seguridad y sucursales.
  2. `GET /tenants`: Tarjetas de sucursales con consumo IA y estado operativo.
  3. `GET /daily-credit-usage`: Serie temporal continua para Recharts (7, 14, 30 días, filtrable por tenant_id).
  4. `PUT /credit-distribution`: Asignación de créditos (shared vs allocated) con validación de techo.
  5. `POST /purchase-credits`: Compra de créditos IA en Decimal con registro de compra.
  6. `POST /change-plan`: Cambio/upgrade de plan comercial corporativo.
  7. `GET /benchmarking`: Ranking cross-tenant por ventas, rotación de stock y % de merma.

Seguridad:
- RBAC Dual de 3 niveles: `holding.hub.view`, `holding.plans.manage`, `holding.credits.distribute`.
- Autenticación de usuario cliente con Kill-Switch.
- Aislamiento multi-tenant / multi-holding absoluto (anti-IDOR).
- Inyección de `holding_id` desde header `X-Holding-ID` o desde claims del token JWT.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_public_db_session
from src.core.exceptions import (
    CrossTenantAccessError,
    PermissionDeniedError,
)
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireHoldingPermission,
)
from src.core.observability import enrich_sentry_telemetry_context, trace_span
from src.modules.oppy_ai.application.holding_briefing_service import (
    HoldingBriefingService,
)
from src.modules.tenancy.application.holding_hub_service import (
    HoldingHubService,
    parse_uuid_safely,
)
from src.modules.tenancy.presentation.schemas_holding_hub import (
    HoldingBenchmarkingResponse,
    HoldingBriefingResponse,
    HoldingCreditDistributionRequest,
    HoldingCreditDistributionResponse,
    HoldingDailyCreditUsageItem,
    HoldingHubSummaryResponse,
    HoldingPlanChangeRequest,
    HoldingPlanChangeResponse,
    HoldingPurchaseCreditsRequest,
    HoldingPurchaseCreditsResponse,
    HoldingTenantCardResponse,
)

logger = logging.getLogger("oppytec.tenancy.holding_hub_router")

router = APIRouter(
    prefix="/api/v1/holding-hub",
    tags=["holding-hub"],
)


async def get_holding_hub_service(
    session: Annotated[AsyncSession, Depends(get_public_db_session)],
) -> HoldingHubService:
    """Inyección de dependencias para `HoldingHubService` con sesión de base de datos `public`."""
    return HoldingHubService(session=session)


def _resolve_effective_holding_id(
    principal: AuthenticatedPrincipal,
    header_holding_id: str | None = None,
) -> uuid.UUID:
    """Extrae y valida el `holding_id` efectivo asegurando aislamiento multi-holding estricto."""
    if (
        not principal.is_superuser_god
        and header_holding_id
        and principal.holding_id
        and header_holding_id != principal.holding_id
    ):
        raise CrossTenantAccessError(
            f"Cross-holding access denied: user {principal.user_id} is not authorized for holding '{header_holding_id}'.",
            i18n_key="tenancy:errors.cross_holding_forbidden",
            status_code=403,
        )
    raw_id = header_holding_id or principal.holding_id
    if not raw_id:
        raise PermissionDeniedError(
            "Missing holding context (neither X-Holding-ID header nor token holding_id provided).",
            i18n_key="tenancy:errors.missing_holding_context",
            status_code=403,
        )
    return parse_uuid_safely(raw_id)


def _extract_principal_role(principal: AuthenticatedPrincipal) -> str:
    """Extrae el rol del usuario para telemetría Sentry y OTel."""
    if principal.is_holding_owner:
        return "holding_owner"
    if principal.is_superuser_god:
        return "superuser"
    if principal.is_global_staff:
        return "global_staff"
    raw_role = principal.authorization_lineage.get("role")
    if raw_role:
        return str(raw_role)
    return f"rank_{principal.hierarchy_rank}"


# =============================================================================
# 1. GET /summary
# =============================================================================


@router.get(
    "/summary",
    response_model=HoldingHubSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_holding_summary_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireHoldingPermission("holding.hub.view")),
    ],
    service: Annotated[HoldingHubService, Depends(get_holding_hub_service)],
    x_holding_id: Annotated[str | None, Header(alias="X-Holding-ID")] = None,
) -> HoldingHubSummaryResponse:
    """
    Retorna el resumen ejecutivo del Holding Hub Enterprise:
    KPIs consolidados de ventas, inventario, merma, saldo de IA, semáforo de seguridad y sucursales.
    """
    holding_id = _resolve_effective_holding_id(principal, x_holding_id)
    user_role = _extract_principal_role(principal)
    enrich_sentry_telemetry_context(
        holding_id=str(holding_id),
        tenant_id=principal.tenant_id,
        user_role=user_role,
        user_id=str(principal.user_id),
    )
    with trace_span(
        "holding_hub.get_summary",
        attributes={
            "holding.id": str(holding_id),
            "holding_id": str(holding_id),
            "user_id": str(principal.user_id),
            "user_role": user_role,
            "tenant_id": principal.tenant_id or "",
        },
        tracer_name="oppytec.tenancy.holding_hub",
    ):
        return await service.get_holding_summary(holding_id)


# =============================================================================
# 2. GET /tenants
# =============================================================================


@router.get(
    "/tenants",
    response_model=list[HoldingTenantCardResponse],
    status_code=status.HTTP_200_OK,
)
async def get_holding_tenants_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireHoldingPermission("holding.hub.view")),
    ],
    service: Annotated[HoldingHubService, Depends(get_holding_hub_service)],
    x_holding_id: Annotated[str | None, Header(alias="X-Holding-ID")] = None,
) -> list[HoldingTenantCardResponse]:
    """Retorna las tarjetas de sucursales con telemetría de IA, cupos y estado operativo."""
    holding_id = _resolve_effective_holding_id(principal, x_holding_id)
    user_role = _extract_principal_role(principal)
    enrich_sentry_telemetry_context(
        holding_id=str(holding_id),
        tenant_id=principal.tenant_id,
        user_role=user_role,
        user_id=str(principal.user_id),
    )
    with trace_span(
        "holding_hub.get_tenants",
        attributes={
            "holding.id": str(holding_id),
            "holding_id": str(holding_id),
            "user_id": str(principal.user_id),
            "user_role": user_role,
            "tenant_id": principal.tenant_id or "",
        },
        tracer_name="oppytec.tenancy.holding_hub",
    ):
        return await service.get_holding_tenants(holding_id)


# =============================================================================
# 3. GET /daily-credit-usage
# =============================================================================


@router.get(
    "/daily-credit-usage",
    response_model=list[HoldingDailyCreditUsageItem],
    status_code=status.HTTP_200_OK,
)
async def get_daily_credit_usage_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireHoldingPermission("holding.hub.view")),
    ],
    service: Annotated[HoldingHubService, Depends(get_holding_hub_service)],
    days: int = Query(default=30, ge=1, le=90, description="Días de serie temporal a consultar (7, 14, 30)"),
    tenant_id: str | None = Query(default=None, description="Filtro opcional por UUID de sucursal específica"),
    x_holding_id: Annotated[str | None, Header(alias="X-Holding-ID")] = None,
) -> list[HoldingDailyCreditUsageItem]:
    """Retorna la serie temporal continua de consumo de IA día a día para gráficas Recharts."""
    holding_id = _resolve_effective_holding_id(principal, x_holding_id)
    tenant_uuid = parse_uuid_safely(tenant_id) if tenant_id else None
    user_role = _extract_principal_role(principal)
    enrich_sentry_telemetry_context(
        holding_id=str(holding_id),
        tenant_id=str(tenant_uuid) if tenant_uuid else principal.tenant_id,
        user_role=user_role,
        user_id=str(principal.user_id),
    )

    with trace_span(
        "holding_hub.daily_credit_usage",
        attributes={
            "holding.id": str(holding_id),
            "holding_id": str(holding_id),
            "days": days,
            "tenant_id": str(tenant_uuid) if tenant_uuid else (principal.tenant_id or ""),
            "user_id": str(principal.user_id),
            "user_role": user_role,
        },
        tracer_name="oppytec.tenancy.holding_hub",
    ):
        return await service.get_daily_credit_usage(
            holding_id=holding_id,
            days=days,
            tenant_id=tenant_uuid,
        )


# =============================================================================
# 4. PUT /credit-distribution
# =============================================================================


@router.put(
    "/credit-distribution",
    response_model=HoldingCreditDistributionResponse,
    status_code=status.HTTP_200_OK,
)
async def update_credit_distribution_endpoint(
    payload: HoldingCreditDistributionRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireHoldingPermission("holding.credits.distribute")),
    ],
    service: Annotated[HoldingHubService, Depends(get_holding_hub_service)],
    x_holding_id: Annotated[str | None, Header(alias="X-Holding-ID")] = None,
) -> HoldingCreditDistributionResponse:
    """Configura el modo de distribución de créditos (shared vs allocated) y actualiza los cupos por sucursal."""
    holding_id = _resolve_effective_holding_id(principal, x_holding_id)
    user_role = _extract_principal_role(principal)
    enrich_sentry_telemetry_context(
        holding_id=str(holding_id),
        tenant_id=principal.tenant_id,
        user_role=user_role,
        user_id=str(principal.user_id),
    )
    with trace_span(
        "holding_hub.update_distribution",
        attributes={
            "holding.id": str(holding_id),
            "holding_id": str(holding_id),
            "mode": payload.distribution_mode.value,
            "distribution_mode": payload.distribution_mode.value,
            "tenants.count": len(payload.allocations),
            "user_id": str(principal.user_id),
            "user_role": user_role,
            "tenant_id": principal.tenant_id or "",
        },
        tracer_name="oppytec.tenancy.holding_hub",
    ):
        return await service.update_credit_distribution(holding_id, payload)


# =============================================================================
# 5. POST /purchase-credits
# =============================================================================


@router.post(
    "/purchase-credits",
    response_model=HoldingPurchaseCreditsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def purchase_credits_endpoint(
    payload: HoldingPurchaseCreditsRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireHoldingPermission("holding.credits.distribute")),
    ],
    service: Annotated[HoldingHubService, Depends(get_holding_hub_service)],
    x_holding_id: Annotated[str | None, Header(alias="X-Holding-ID")] = None,
) -> HoldingPurchaseCreditsResponse:
    """Recarga de bolsa corporativa de créditos IA con cálculo en Decimal y registro de auditoría."""
    holding_id = _resolve_effective_holding_id(principal, x_holding_id)
    user_role = _extract_principal_role(principal)
    enrich_sentry_telemetry_context(
        holding_id=str(holding_id),
        tenant_id=principal.tenant_id,
        user_role=user_role,
        user_id=str(principal.user_id),
    )

    # Validación anti-IDOR: el holding_id del payload debe corresponder al holding autorizado
    payload_holding_uuid = parse_uuid_safely(payload.holding_id)
    if not principal.is_superuser_god and payload_holding_uuid != holding_id:
        raise CrossTenantAccessError(
            f"Cross-holding access denied: payload holding_id '{payload.holding_id}' does not match authorized holding.",
            i18n_key="tenancy:errors.cross_holding_forbidden",
            status_code=403,
        )

    with trace_span(
        "holding_hub.purchase_credits",
        attributes={
            "holding.id": str(holding_id),
            "holding_id": str(holding_id),
            "credits.purchased": payload.credits_amount,
            "credits_amount": payload.credits_amount,
            "currency": payload.currency,
            "user_id": str(principal.user_id),
            "user_role": user_role,
            "tenant_id": principal.tenant_id or "",
        },
        tracer_name="oppytec.tenancy.holding_hub",
    ):
        return await service.purchase_credits(
            holding_id=holding_id,
            request=payload,
            user_id=principal.user_id,
        )


# =============================================================================
# 6. POST /change-plan
# =============================================================================


@router.post(
    "/change-plan",
    response_model=HoldingPlanChangeResponse,
    status_code=status.HTTP_200_OK,
)
async def change_holding_plan_endpoint(
    payload: HoldingPlanChangeRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireHoldingPermission("holding.plans.manage")),
    ],
    service: Annotated[HoldingHubService, Depends(get_holding_hub_service)],
    x_holding_id: Annotated[str | None, Header(alias="X-Holding-ID")] = None,
) -> HoldingPlanChangeResponse:
    """Cambio o upgrade de plan comercial corporativo."""
    holding_id = _resolve_effective_holding_id(principal, x_holding_id)
    user_role = _extract_principal_role(principal)
    enrich_sentry_telemetry_context(
        holding_id=str(holding_id),
        tenant_id=principal.tenant_id,
        user_role=user_role,
        user_id=str(principal.user_id),
    )

    # Validación anti-IDOR
    payload_holding_uuid = parse_uuid_safely(payload.holding_id)
    if not principal.is_superuser_god and payload_holding_uuid != holding_id:
        raise CrossTenantAccessError(
            f"Cross-holding access denied: payload holding_id '{payload.holding_id}' does not match authorized holding.",
            i18n_key="tenancy:errors.cross_holding_forbidden",
            status_code=403,
        )

    with trace_span(
        "holding_hub.change_plan",
        attributes={
            "holding.id": str(holding_id),
            "holding_id": str(holding_id),
            "new_plan_slug": payload.new_plan_slug,
            "user_id": str(principal.user_id),
            "user_role": user_role,
            "tenant_id": principal.tenant_id or "",
        },
        tracer_name="oppytec.tenancy.holding_hub",
    ):
        return await service.change_holding_plan(holding_id, payload)


# =============================================================================
# 7. GET /benchmarking
# =============================================================================


@router.get(
    "/benchmarking",
    response_model=HoldingBenchmarkingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_holding_benchmarking_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireHoldingPermission("holding.hub.view")),
    ],
    service: Annotated[HoldingHubService, Depends(get_holding_hub_service)],
    x_holding_id: Annotated[str | None, Header(alias="X-Holding-ID")] = None,
) -> HoldingBenchmarkingResponse:
    """Ranking y análisis comparativo (Benchmarking) entre sucursales del Holding gastronómico."""
    holding_id = _resolve_effective_holding_id(principal, x_holding_id)
    user_role = _extract_principal_role(principal)
    enrich_sentry_telemetry_context(
        holding_id=str(holding_id),
        tenant_id=principal.tenant_id,
        user_role=user_role,
        user_id=str(principal.user_id),
    )
    with trace_span(
        "holding_hub.benchmarking",
        attributes={
            "holding.id": str(holding_id),
            "holding_id": str(holding_id),
            "user_id": str(principal.user_id),
            "user_role": user_role,
            "tenant_id": principal.tenant_id or "",
        },
        tracer_name="oppytec.tenancy.holding_hub",
    ):
        return await service.get_holding_benchmarking(holding_id)


# =============================================================================
# 8. GET /ai-briefing
# =============================================================================


@router.get(
    "/ai-briefing",
    response_model=HoldingBriefingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_holding_ai_briefing_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireHoldingPermission("holding.hub.view")),
    ],
    service: Annotated[HoldingHubService, Depends(get_holding_hub_service)],
    session: Annotated[AsyncSession, Depends(get_public_db_session)],
    x_holding_id: Annotated[str | None, Header(alias="X-Holding-ID")] = None,
) -> HoldingBriefingResponse:
    """
    Retorna el resumen ejecutivo corporativo generado por IA OppyFy (Oppy Daily Holding Briefing):
    Sintetiza ventas consolidadas, tendencias de merma por local y proyección de Safety Cap (burn rate).
    """
    holding_id = _resolve_effective_holding_id(principal, x_holding_id)
    user_role = _extract_principal_role(principal)
    enrich_sentry_telemetry_context(
        holding_id=str(holding_id),
        tenant_id=principal.tenant_id,
        user_role=user_role,
        user_id=str(principal.user_id),
    )
    with trace_span(
        "holding_hub.ai_briefing",
        attributes={
            "holding.id": str(holding_id),
            "holding_id": str(holding_id),
            "user_id": str(principal.user_id),
            "user_role": user_role,
            "tenant_id": principal.tenant_id or "",
        },
        tracer_name="oppytec.tenancy.holding_hub",
    ):
        summary = await service.get_holding_summary(holding_id)
        briefing_service = HoldingBriefingService()
        return await briefing_service.generate_holding_briefing_async(
            holding_id=holding_id,
            summary=summary,
            session=session,
            user_id=principal.user_id,
        )

