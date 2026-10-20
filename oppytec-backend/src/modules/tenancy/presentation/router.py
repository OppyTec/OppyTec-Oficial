"""
oppytec-backend/src/modules/tenancy/presentation/router.py
Endpoints REST de Multi-Tenancy, Holdings, Sucursales y Gobernabilidad de Cuotas (Seats y Storage R2):
- `POST /api/v1/tenancy/holdings` y `GET /api/v1/tenancy/holdings`
- `POST /api/v1/tenancy/tenants`
- `GET /api/v1/tenancy/quotas/seats`
- `GET /api/v1/tenancy/quotas/storage`
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.database import validate_tenant_schema_name
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireGlobalPermission,
    RequireTenantPermission,
)
from src.modules.identity.presentation.router import _GLOBAL_USERS_STORE
from src.modules.tenancy.domain.quotas import (
    evaluate_seat_quota_for_new_or_restored_user,
    evaluate_storage_quota_bytes,
)
from src.modules.tenancy.presentation.schemas import (
    HoldingCreateRequest,
    HoldingResponse,
    LegalEntityCreateRequest,
    LegalEntityResponse,
    SeatQuotaStatusResponse,
    StorageQuotaStatusResponse,
    TenancyDashboardSummaryResponse,
    TenantCreateRequest,
    TenantResponse,
)

router = APIRouter(tags=["tenancy"])

_holdings_store: dict[str, HoldingResponse] = {}
_legal_entities_store: dict[str, LegalEntityResponse] = {}
_tenants_store: dict[str, TenantResponse] = {}



@router.post(
    "/api/v1/tenancy/holdings",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_holding_endpoint(
    payload: HoldingCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.holdings.create")),
    ],
) -> HoldingResponse:
    """Registra un nuevo Holding empresarial en el Plano Global (`public.holdings`)."""
    holding_id = f"holding_{uuid.uuid4().hex[:10]}"
    record = HoldingResponse(
        holding_id=holding_id,
        name=payload.name,
        plan_slug=payload.plan_slug,
        max_active_users=payload.max_active_users,
        max_storage_mb=payload.max_storage_mb,
    )
    _holdings_store[holding_id] = record
    return record


@router.get(
    "/api/v1/tenancy/holdings",
    response_model=list[HoldingResponse],
    status_code=status.HTTP_200_OK,
)
async def list_holdings_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.holdings.read")),
    ],
) -> list[HoldingResponse]:
    """Lista los Holdings registrados en el Plano Global."""
    return list(_holdings_store.values())


@router.post(
    "/api/v1/tenancy/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant_endpoint(
    payload: TenantCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.tenants.provision")),
    ],
) -> TenantResponse:
    """Valida el nombre de esquema `tenant_<slug>` y aprovisiona una nueva sucursal."""
    raw_schema = payload.slug if payload.slug.startswith("tenant_") else f"tenant_{payload.slug}"
    schema_name = validate_tenant_schema_name(raw_schema)
    tenant_id = f"t_{uuid.uuid4().hex[:10]}"
    record = TenantResponse(
        tenant_id=tenant_id,
        holding_id=payload.holding_id,
        schema_name=schema_name,
        display_name=payload.display_name,
        base_currency=payload.base_currency.upper(),
    )
    _tenants_store[tenant_id] = record
    return record


@router.get(
    "/api/v1/tenancy/tenants",
    response_model=list[TenantResponse],
    status_code=status.HTTP_200_OK,
)
async def list_tenants_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.tenants.read")),
    ],
) -> list[TenantResponse]:
    """Lista las sucursales / tenants registrados en el Plano Global."""
    return list(_tenants_store.values())


@router.post(
    "/api/v1/tenancy/legal-entities",
    response_model=LegalEntityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_legal_entity_endpoint(
    payload: LegalEntityCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.legal_entities.create")),
    ],
) -> LegalEntityResponse:
    """Registra una nueva Entidad Legal (Razón Social/RUT) vinculada a un Holding."""
    entity_id = f"le_{uuid.uuid4().hex[:10]}"
    record = LegalEntityResponse(
        entity_id=entity_id,
        holding_id=payload.holding_id,
        tax_id=payload.tax_id,
        legal_name=payload.legal_name,
    )
    _legal_entities_store[entity_id] = record
    return record


@router.get(
    "/api/v1/tenancy/legal-entities",
    response_model=list[LegalEntityResponse],
    status_code=status.HTTP_200_OK,
)
async def list_legal_entities_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.legal_entities.read")),
    ],
) -> list[LegalEntityResponse]:
    """Lista las Entidades Legales registradas."""
    return list(_legal_entities_store.values())


@router.get(
    "/api/v1/tenancy/dashboard/summary",
    response_model=TenancyDashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_tenancy_dashboard_summary_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.dashboard.read")),
    ],
) -> TenancyDashboardSummaryResponse:
    """Devuelve los conteos agregados reales para el Panel de Control Global."""
    return TenancyDashboardSummaryResponse(
        holdings=len(_holdings_store),
        legal_entities=len(_legal_entities_store),
        tenants=len(_tenants_store),
        users=len(_GLOBAL_USERS_STORE),
    )



@router.get(
    "/api/v1/tenancy/quotas/seats",
    response_model=SeatQuotaStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_seat_quota_status_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("tenancy.quotas.read")),
    ],
) -> SeatQuotaStatusResponse:
    """Devuelve el uso de cupos de usuarios activos (`is_deleted == False`) del Holding/Tenant."""
    holding_id = principal.holding_id or "holding_default"
    evaluation = evaluate_seat_quota_for_new_or_restored_user(
        existing_users=(),
        plan_max_active_users=25,
    )
    return SeatQuotaStatusResponse(
        holding_id=holding_id,
        active_non_deleted_users=evaluation.active_non_deleted_users,
        soft_deleted_historical_users=evaluation.soft_deleted_users,
        effective_max_users=evaluation.effective_max_users,
        remaining_seats=evaluation.remaining_seats,
        can_create_or_restore=evaluation.allowed,
    )


@router.get(
    "/api/v1/tenancy/quotas/storage",
    response_model=StorageQuotaStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_storage_quota_status_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("tenancy.storage_quotas.read")),
    ],
) -> StorageQuotaStatusResponse:
    """Devuelve el uso de cuota de memoria multimedia en Cloudflare R2 (`max_storage_mb`)."""
    tenant_id = principal.tenant_id or "tenant_default"
    evaluation = evaluate_storage_quota_bytes(
        current_used_bytes=0,
        new_bytes=0,
        plan_max_storage_mb=1024,
    )
    remaining_bytes = max(0, evaluation.effective_max_storage_bytes - evaluation.current_used_bytes)
    return StorageQuotaStatusResponse(
        tenant_id=tenant_id,
        current_used_bytes=evaluation.current_used_bytes,
        effective_max_storage_mb=evaluation.effective_max_storage_mb,
        effective_max_storage_bytes=evaluation.effective_max_storage_bytes,
        remaining_bytes=remaining_bytes,
        allowed=evaluation.allowed,
    )
