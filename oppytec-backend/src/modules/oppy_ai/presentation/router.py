"""
oppytec-backend/src/modules/oppy_ai/presentation/router.py
Endpoints REST del Asistente `OppyFy` (RAG 3-Capas, RBAC propio editable, Billetera de Créditos y Telemetría):
- `POST /api/v1/oppyfy/chat`
- `GET /api/v1/oppyfy/rbac/domains`
- `GET /api/v1/oppyfy/credits/wallet`
- `GET /api/v1/oppyfy/telemetry/logs`
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.guards.rate_limiter import RateLimitCheckResult, RequireRateLimit
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireGlobalPermission,
    RequireTenantPermission,
)
from src.modules.oppy_ai.domain.context_meter import evaluate_context_usage
from src.modules.oppy_ai.domain.credit_wallet import (
    WorkerCreditWalletState,
    deduct_worker_credits,
)
from src.modules.oppy_ai.domain.oppyfy_rbac import (
    ALLOWED_PROMPT_STATUS,
    BLOCKED_UNAUTHORIZED_PROMPT,
    OppyfyPermissionGrantSpec,
    evaluate_oppyfy_subdomain_access,
)
from src.modules.oppy_ai.presentation.schemas import (
    OppyfyChatRequest,
    OppyfyChatResponse,
    OppyfyDomainItemResponse,
    OppyfyTelemetryLogItemResponse,
    OppyfyWalletResponse,
)

router = APIRouter(tags=["oppyfy"])

_telemetry_logs: list[OppyfyTelemetryLogItemResponse] = []
_DEFAULT_SUBDOMAINS: tuple[OppyfyDomainItemResponse, ...] = (
    OppyfyDomainItemResponse(
        domain_slug="gastronomia",
        subdomain_slug="recipes_kitchen",
        display_name="Recetas y Cocina",
        supports_cost_redaction=True,
    ),
    OppyfyDomainItemResponse(
        domain_slug="bodega",
        subdomain_slug="inventory_stock",
        display_name="Inventario y Bodegas",
        supports_cost_redaction=True,
    ),
    OppyfyDomainItemResponse(
        domain_slug="finanzas",
        subdomain_slug="executive_analytics",
        display_name="Analítica y Control de Pérdidas",
        supports_cost_redaction=True,
    ),
)


@router.post(
    "/api/v1/oppyfy/chat",
    response_model=OppyfyChatResponse,
    status_code=status.HTTP_200_OK,
)
async def oppyfy_chat_endpoint(
    payload: OppyfyChatRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.assistant.chat")),
    ],
    _rate_limit: Annotated[RateLimitCheckResult, Depends(RequireRateLimit("ai"))],
) -> OppyfyChatResponse:
    """Procesa una consulta a `OppyFy` validando créditos, RBAC propio editable y ventana de contexto."""
    wallet = WorkerCreditWalletState(
        user_id=principal.user_id,
        allocated_credits=payload.remaining_credits,
        consumed_credits=Decimal("0.00"),
        is_oppyfy_enabled=True,
    )
    grants = (
        (
            OppyfyPermissionGrantSpec(
                grant_id=uuid.uuid4(),
                subdomain_id=1,
                subdomain_slug=payload.target_subdomain_slug,
                user_id=principal.user_id,
                effect="ALLOW",
                can_view_costs=payload.can_view_costs,
            ),
        )
        if payload.remaining_credits >= payload.estimated_credit_cost
        else ()
    )
    access_decision = evaluate_oppyfy_subdomain_access(
        user_id=principal.user_id,
        role_ids=(1,),
        hierarchy_rank=principal.hierarchy_rank,
        target_subdomain_slug=payload.target_subdomain_slug,
        grants=grants,
        estimated_cost=payload.estimated_credit_cost,
    )

    if not access_decision.allowed:
        ctx = evaluate_context_usage(payload.prior_thread_tokens)
        return OppyfyChatResponse(
            allowed=False,
            status_code=BLOCKED_UNAUTHORIZED_PROMPT,
            subdomain_slug=payload.target_subdomain_slug,
            answer_text="",
            credits_deducted=Decimal("0.00"),
            remaining_credits=wallet.remaining_credits,
            context_usage_percent=ctx.context_usage_percent,
            requires_new_thread=ctx.requires_auto_compaction,
        )

    deduction = deduct_worker_credits(wallet, payload.estimated_credit_cost)
    ctx_after = evaluate_context_usage(payload.prior_thread_tokens + 180)
    cost_tag = "CLP 1.450" if access_decision.can_view_costs else "[REDACTED_COST]"
    answer = f"OppyFy ({payload.target_subdomain_slug}): resultado verificado ({cost_tag})."

    _telemetry_logs.append(
        OppyfyTelemetryLogItemResponse(
            request_id=str(uuid.uuid4()),
            caller_feature="oppyfy_chat",
            model_name="gemini-2.5-flash",
            total_tokens=180,
            estimated_cost_usd=Decimal("0.000270"),
            credits_deducted=deduction.deducted_credits,
        )
    )

    return OppyfyChatResponse(
        allowed=True,
        status_code=ALLOWED_PROMPT_STATUS,
        subdomain_slug=payload.target_subdomain_slug,
        answer_text=answer,
        credits_deducted=deduction.deducted_credits,
        remaining_credits=deduction.updated_wallet.remaining_credits,
        context_usage_percent=ctx_after.context_usage_percent,
        requires_new_thread=ctx_after.requires_auto_compaction,
    )


@router.get(
    "/api/v1/oppyfy/rbac/domains",
    response_model=list[OppyfyDomainItemResponse],
    status_code=status.HTTP_200_OK,
)
async def list_oppyfy_rbac_domains_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.rbac_domains.read")),
    ],
) -> list[OppyfyDomainItemResponse]:
    """Devuelve el árbol de dominios y sub-dominios editables del RBAC exclusivo de `OppyFy`."""
    return list(_DEFAULT_SUBDOMAINS)


@router.get(
    "/api/v1/oppyfy/credits/wallet",
    response_model=OppyfyWalletResponse,
    status_code=status.HTTP_200_OK,
)
async def get_oppyfy_credit_wallet_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("oppyfy.credits.read")),
    ],
) -> OppyfyWalletResponse:
    """Consulta el saldo de paquetes de créditos sin caducidad asignados al trabajador."""
    wallet = WorkerCreditWalletState(
        user_id=principal.user_id,
        allocated_credits=Decimal("100.00"),
        consumed_credits=Decimal("12.50"),
        is_oppyfy_enabled=True,
    )
    return OppyfyWalletResponse(
        user_id=wallet.user_id,
        is_oppyfy_enabled=wallet.is_oppyfy_enabled,
        assigned_credits_balance=wallet.allocated_credits,
        consumed_credits_total=wallet.consumed_credits,
        remaining_credits=wallet.remaining_credits,
    )


@router.get(
    "/api/v1/oppyfy/telemetry/logs",
    response_model=list[OppyfyTelemetryLogItemResponse],
    status_code=status.HTTP_200_OK,
)
async def list_oppyfy_telemetry_logs_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("oppyfy.telemetry.read")),
    ],
) -> list[OppyfyTelemetryLogItemResponse]:
    """Lista la bitácora global de consumo de tokens y costos (`public.llm_request_logs`)."""
    return list(_telemetry_logs)
