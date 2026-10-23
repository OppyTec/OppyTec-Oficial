"""
oppytec-backend/src/modules/tenancy/presentation/router.py
Endpoints REST de Multi-Tenancy, Holdings, Entidades Legales, Sucursales, Planes Comerciales,
Usuarios Clientes, Impersonación de Soporte y Gobernabilidad de Cuotas (6 recursos + Storage R2):
- `POST /api/v1/tenancy/holdings` y `GET /api/v1/tenancy/holdings`
- `POST /api/v1/tenancy/legal-entities` y `GET /api/v1/tenancy/legal-entities`
- `POST /api/v1/tenancy/tenants`, `GET /api/v1/tenancy/tenants` y `PUT /api/v1/tenancy/tenants/{tenant_id}/modules-and-quotas`
- `GET /api/v1/tenancy/plans` y `POST /api/v1/tenancy/plans`
- `GET /api/v1/tenancy/client-users`, `POST /api/v1/tenancy/client-users`, `POST /api/v1/tenancy/client-users/{user_id}/soft-delete` y `POST /api/v1/tenancy/client-users/{user_id}/restore`
- `POST /api/v1/tenancy/admin/impersonate`
- `GET /api/v1/tenancy/quotas/seats`, `GET /api/v1/tenancy/quotas/storage` y `GET /api/v1/tenancy/quotas/summary`
"""
from __future__ import annotations

import contextlib
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.bootstrap import DEFAULT_SYSTEM_PLANS, PLAN_BASICO_10_MODULES, TENANT_BASE_ROLES
from src.core.database import validate_tenant_schema_name
from src.core.exceptions import (
    CrossTenantAccessError,
    PermissionDeniedError,
    QuotaExceededError,
    ResourceNotFoundError,
    SecurityValidationError,
)
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireGlobalPermission,
    RequireTenantPermission,
    restore_revoked_user_session,
    revoke_session_token,
)
from src.core.observability import (
    emit_plan_audit_log,
    emit_quota_audit_log,
    emit_tenant_provisioning_audit_log,
    record_quota_semaphore_metric,
)
from src.core.redis import get_redis_client
from src.core.security import create_access_token, hash_password
from src.modules.identity.application.session_killswitch import SessionKillSwitchService
from src.modules.identity.presentation.router import (
    _CLIENT_USERS_STORE,
    _GLOBAL_USERS_STORE,
)
from src.modules.tenancy.domain.quotas import (
    ClientUserSeatState,
    QuotaResourceType,
    TenantHierarchyAssignment,
    evaluate_resource_capacity_quota,
    evaluate_seat_quota_for_new_or_restored_user,
    evaluate_storage_quota_bytes,
    validate_holding_legal_entity_tenant_cardinality,
)
from src.modules.tenancy.presentation.schemas import (
    AdminImpersonateRequest,
    AdminImpersonateResponse,
    ClientUserAdminResponse,
    ClientUserCreateRequest,
    HoldingCreateRequest,
    HoldingResponse,
    LegalEntityCreateRequest,
    LegalEntityResponse,
    ResourceQuotaItemResponse,
    SeatQuotaStatusResponse,
    StorageQuotaStatusResponse,
    SystemPlanResponse,
    SystemPlanUpsertRequest,
    TenancyDashboardSummaryResponse,
    TenantCreateRequest,
    TenantModulesAndQuotasUpdateRequest,
    TenantQuotaSummaryResponse,
    TenantResponse,
)

router = APIRouter(tags=["tenancy"])

_holdings_store: dict[str, HoldingResponse] = {
    "holding_genesis": HoldingResponse(
        holding_id="holding_genesis",
        name="Holding Principal Génesis",
        plan_slug="basic",
        max_active_users=5,
        max_storage_mb=512,
        custom_max_users_override=None,
        custom_max_products_override=None,
        custom_max_suppliers_override=None,
        custom_max_recipes_override=None,
        custom_max_combos_override=None,
        custom_storage_mb_override=None,
    ),
    "holding_pacifico": HoldingResponse(
        holding_id="holding_pacifico",
        name="Grupo Gastronómico Pacífico SpA",
        plan_slug="starter",
        max_active_users=10,
        max_storage_mb=2048,
        custom_max_users_override=None,
        custom_max_products_override=None,
        custom_max_suppliers_override=None,
        custom_max_recipes_override=None,
        custom_max_combos_override=None,
        custom_storage_mb_override=None,
    ),
}
_legal_entities_store: dict[str, LegalEntityResponse] = {
    "le_genesis": LegalEntityResponse(
        entity_id="le_genesis",
        holding_id="holding_genesis",
        tax_id="76.000.000-1",
        legal_name="OppyTec SaaS SpA",
        legal_address="Av. Providencia 1200, Santiago",
    ),
    "le_pacifico": LegalEntityResponse(
        entity_id="le_pacifico",
        holding_id="holding_pacifico",
        tax_id="77.123.456-K",
        legal_name="Inversiones Gastronómicas Pacífico SpA",
        legal_address="Costanera Center 2400, Santiago",
    ),
}
_tenants_store: dict[str, TenantResponse] = {
    "tenant_genesis": TenantResponse(
        tenant_id="tenant_genesis",
        holding_id="holding_genesis",
        legal_entity_id="le_genesis",
        schema_name="tenant_genesis",
        display_name="Local Central Génesis",
        base_currency="CLP",
        enabled_modules=list(PLAN_BASICO_10_MODULES),
        custom_max_users_override=None,
        custom_max_products_override=None,
        custom_max_suppliers_override=None,
        custom_max_recipes_override=None,
        custom_max_combos_override=None,
        custom_storage_mb_override=None,
    ),
    "tenant_pacifico_centro": TenantResponse(
        tenant_id="tenant_pacifico_centro",
        holding_id="holding_pacifico",
        legal_entity_id="le_pacifico",
        schema_name="tenant_pacifico_centro",
        display_name="Sucursal Pacífico Centro",
        base_currency="CLP",
        enabled_modules=list(PLAN_BASICO_10_MODULES),
        custom_max_users_override=None,
        custom_max_products_override=None,
        custom_max_suppliers_override=None,
        custom_max_recipes_override=None,
        custom_max_combos_override=None,
        custom_storage_mb_override=None,
    ),
}
_plans_store: dict[str, SystemPlanResponse] = {
    plan.slug: SystemPlanResponse(
        slug=plan.slug,
        name=plan.name,
        max_active_users=plan.max_active_users,
        max_products=plan.max_products,
        max_suppliers=plan.max_suppliers,
        max_recipes=plan.max_recipes,
        max_combos=plan.max_combos,
        max_storage_mb=plan.max_storage_mb,
        included_modules=list(plan.included_modules),
        anchor_currency="CLP",
        price_clp=plan.price_clp,
        price_usd=plan.price_usd,
        price_eur=plan.price_eur,
        price_brl=plan.price_brl,
        auto_convert_fx=True,
    )
    for plan in DEFAULT_SYSTEM_PLANS
}
_ROLE_RANK_MAP: dict[str, int] = {r.slug: r.hierarchy_rank for r in TENANT_BASE_ROLES}


def _resolve_plan_for_holding(holding: HoldingResponse | None) -> SystemPlanResponse:
    """Obtiene el `SystemPlanResponse` asociado al Holding o el Plan Básico por defecto."""
    if holding is not None and holding.plan_slug in _plans_store:
        return _plans_store[holding.plan_slug]
    return _plans_store["basic"]


@router.get(
    "/api/v1/tenancy/plans",
    response_model=list[SystemPlanResponse],
    status_code=status.HTTP_200_OK,
)
async def list_system_plans_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.plans.read")),
    ],
) -> list[SystemPlanResponse]:
    """Lista los Planes Comerciales (`public.system_plans`) con sus 6 cuotas y precios multi-moneda."""
    return list(_plans_store.values())


@router.post(
    "/api/v1/tenancy/plans",
    response_model=SystemPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_system_plan_endpoint(
    payload: SystemPlanUpsertRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.plans.manage")),
    ],
) -> SystemPlanResponse:
    """Crea o actualiza un Plan Comercial con límites paramétricos de usuarios, productos, proveedores, recetas, combos y disco."""
    plan = SystemPlanResponse(
        slug=payload.slug,
        name=payload.name,
        max_active_users=payload.max_active_users,
        max_products=payload.max_products,
        max_suppliers=payload.max_suppliers,
        max_recipes=payload.max_recipes,
        max_combos=payload.max_combos,
        max_storage_mb=payload.max_storage_mb,
        included_modules=list(payload.included_modules) or list(PLAN_BASICO_10_MODULES),
        anchor_currency=payload.anchor_currency,
        price_clp=payload.price_clp,
        price_usd=payload.price_usd,
        price_eur=payload.price_eur,
        price_brl=payload.price_brl,
        auto_convert_fx=payload.auto_convert_fx,
    )
    _plans_store[payload.slug] = plan
    emit_plan_audit_log(
        "upsert",
        payload.slug,
        {
            "name": payload.name,
            "max_active_users": payload.max_active_users,
            "max_products": payload.max_products,
            "max_storage_mb": payload.max_storage_mb,
        },
    )
    return plan


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
        custom_max_users_override=payload.custom_max_users_override,
        custom_max_products_override=payload.custom_max_products_override,
        custom_max_suppliers_override=payload.custom_max_suppliers_override,
        custom_max_recipes_override=payload.custom_max_recipes_override,
        custom_max_combos_override=payload.custom_max_combos_override,
        custom_storage_mb_override=payload.custom_storage_mb_override,
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

    # Validar que la entidad legal pertenezca al holding
    if payload.legal_entity_id and payload.legal_entity_id in _legal_entities_store:
        le_record = _legal_entities_store[payload.legal_entity_id]
        if le_record.holding_id != payload.holding_id:
            raise CrossTenantAccessError(
                f"Legal entity '{payload.legal_entity_id}' belongs to another holding.",
                i18n_key="tenancy:errors.cross_holding_legal_entity",
            )

    # Validar cardinalidad estricta Holding -> LegalEntity (1:1) -> Tenant
    current_assignments: list[TenantHierarchyAssignment] = []
    for t in _tenants_store.values():
        current_assignments.append(
            TenantHierarchyAssignment(
                holding_id=t.holding_id,
                legal_entity_id=t.legal_entity_id or f"le_{t.tenant_id}",
                tenant_id=t.tenant_id,
                schema_name=t.schema_name,
            )
        )

    tenant_id = f"t_{uuid.uuid4().hex[:10]}"
    if payload.legal_entity_id:
        new_assignment = TenantHierarchyAssignment(
            holding_id=payload.holding_id,
            legal_entity_id=payload.legal_entity_id,
            tenant_id=tenant_id,
            schema_name=schema_name,
        )
        is_cardinality_valid, violation_reason = validate_holding_legal_entity_tenant_cardinality(
            [*current_assignments, new_assignment]
        )
        if not is_cardinality_valid:
            raise SecurityValidationError(
                f"Cardinality violation: {violation_reason}",
                error_code=violation_reason,
                i18n_key=f"tenancy:errors.{violation_reason.lower()}",
            )
    else:
        if any(t.schema_name == schema_name for t in _tenants_store.values()):
            raise SecurityValidationError(
                "Duplicate tenant schema",
                error_code="DUPLICATE_TENANT_SCHEMA",
                i18n_key="tenancy:errors.duplicate_tenant_schema",
            )

    holding = _holdings_store.get(payload.holding_id)
    plan = _resolve_plan_for_holding(holding)
    resolved_modules = (
        list(payload.enabled_modules)
        if payload.enabled_modules is not None
        else list(plan.included_modules)
    )
    record = TenantResponse(
        tenant_id=tenant_id,
        holding_id=payload.holding_id,
        legal_entity_id=payload.legal_entity_id,
        schema_name=schema_name,
        display_name=payload.display_name,
        base_currency=payload.base_currency.upper(),
        enabled_modules=resolved_modules,
        custom_max_users_override=payload.custom_max_users_override,
        custom_max_products_override=payload.custom_max_products_override,
        custom_max_suppliers_override=payload.custom_max_suppliers_override,
        custom_max_recipes_override=payload.custom_max_recipes_override,
        custom_max_combos_override=payload.custom_max_combos_override,
        custom_storage_mb_override=payload.custom_storage_mb_override,
    )
    _tenants_store[tenant_id] = record
    emit_tenant_provisioning_audit_log(
        "provision",
        tenant_id,
        payload.holding_id,
        schema_name,
        {
            "display_name": payload.display_name,
            "base_currency": payload.base_currency.upper(),
            "enabled_modules": resolved_modules,
        },
    )
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


@router.put(
    "/api/v1/tenancy/tenants/{tenant_id}/modules-and-quotas",
    response_model=TenantResponse,
    status_code=status.HTTP_200_OK,
)
async def update_tenant_modules_and_quotas_endpoint(
    tenant_id: str,
    payload: TenantModulesAndQuotasUpdateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.tenants.provision")),
    ],
) -> TenantResponse:
    """Actualiza el árbol de módulos/submódulos habilitados y los overrides de cuota de un Tenant."""
    existing = _tenants_store.get(tenant_id)
    if existing is None:
        raise ResourceNotFoundError(
            f"Tenant '{tenant_id}' not found.",
            i18n_key="tenancy:errors.tenant_not_found",
        )
    updated = TenantResponse(
        tenant_id=existing.tenant_id,
        holding_id=existing.holding_id,
        legal_entity_id=existing.legal_entity_id,
        schema_name=existing.schema_name,
        display_name=existing.display_name,
        base_currency=existing.base_currency,
        enabled_modules=list(payload.enabled_modules),
        custom_max_users_override=payload.custom_max_users_override,
        custom_max_products_override=payload.custom_max_products_override,
        custom_max_suppliers_override=payload.custom_max_suppliers_override,
        custom_max_recipes_override=payload.custom_max_recipes_override,
        custom_max_combos_override=payload.custom_max_combos_override,
        custom_storage_mb_override=payload.custom_storage_mb_override,
    )
    _tenants_store[tenant_id] = updated
    return updated


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
        legal_address=payload.legal_address,
        is_active=True,
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
    "/api/v1/tenancy/client-users",
    response_model=list[ClientUserAdminResponse],
    status_code=status.HTTP_200_OK,
)
async def list_client_users_admin_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.client_users.read")),
    ],
) -> list[ClientUserAdminResponse]:
    """Lista los usuarios clientes creados en `public.client_users`."""
    results: list[ClientUserAdminResponse] = []
    for uid, entry in _CLIENT_USERS_STORE.items():
        results.append(
            ClientUserAdminResponse(
                user_id=uid,
                holding_id=str(entry.get("holding_id", "holding_default")),
                tenant_id=str(entry.get("tenant_id", "tenant_default")),
                username=str(entry.get("username", f"user_{uid}")),
                email=str(entry.get("email", f"user_{uid}@cliente.cl")),
                first_name=str(entry.get("first_name", "Operador")),
                last_name=str(entry.get("last_name", "Cliente")),
                role_slug=str(entry.get("role", "admin")),
                hierarchy_rank=int(str(entry.get("hierarchy_rank", 10))),
                is_holding_owner=bool(entry.get("is_holding_owner", False)),
                is_deleted=bool(entry.get("is_deleted", False)),
            )
        )
    return results


@router.post(
    "/api/v1/tenancy/client-users",
    response_model=ClientUserAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_client_user_admin_endpoint(
    payload: ClientUserCreateRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.client_users.create")),
    ],
) -> ClientUserAdminResponse:
    """
    Crea un Usuario Cliente verificando la cuota de asientos activos (`max_active_users` + overrides)
    del Holding/Tenant y registrándolo con Argon2id para inicio de sesión inmediato.
    """
    holding = _holdings_store.get(payload.holding_id)
    tenant = _tenants_store.get(payload.tenant_id)
    plan = _resolve_plan_for_holding(holding)

    existing_seat_states = [
        ClientUserSeatState(
            user_id=uid,
            holding_id=str(rec.get("holding_id", "")),
            is_deleted=bool(rec.get("is_deleted", False)),
        )
        for uid, rec in _CLIENT_USERS_STORE.items()
        if str(rec.get("holding_id", "")) == payload.holding_id
    ]
    plan_max_users = holding.max_active_users if holding is not None else plan.max_active_users
    holding_override = holding.custom_max_users_override if holding is not None else None
    tenant_override = tenant.custom_max_users_override if tenant is not None else None

    seat_eval = evaluate_seat_quota_for_new_or_restored_user(
        existing_users=existing_seat_states,
        plan_max_active_users=plan_max_users,
        holding_override=holding_override,
        tenant_override=tenant_override,
    )
    if not seat_eval.allowed:
        record_quota_semaphore_metric(
            resource_type="users",
            status="OVER_QUOTA",
            usage_percentage=Decimal("100.00"),
            active_count=seat_eval.active_non_deleted_users,
            effective_max_limit=seat_eval.effective_max_users,
            tenant_id=payload.tenant_id,
            holding_id=payload.holding_id,
        )
        emit_quota_audit_log(
            "seat_limit_exceeded",
            "users",
            "OVER_QUOTA",
            {
                "attempted_username": payload.username,
                "email": payload.email,
                "password": payload.password,
            },
        )
        raise QuotaExceededError(
            f"Maximum active users quota reached ({seat_eval.effective_max_users}). "
            "Archive/soft-delete an inactive user or upgrade the plan.",
            i18n_key="tenancy:errors.seat_quota_exceeded",
            context={
                "active_users": seat_eval.active_non_deleted_users,
                "max_users": seat_eval.effective_max_users,
            },
        )

    next_uid = max(_CLIENT_USERS_STORE.keys(), default=100) + 1
    rank = 0 if payload.is_holding_owner else _ROLE_RANK_MAP.get(payload.role_slug, 10)
    hashed_pw = hash_password(payload.password)

    _CLIENT_USERS_STORE[next_uid] = {
        "id": next_uid,
        "username": payload.username.strip(),
        "email": payload.email.strip().lower(),
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "role": payload.role_slug,
        "hierarchy_rank": rank,
        "is_superuser": False,
        "is_global_admin": False,
        "is_holding_owner": payload.is_holding_owner,
        "is_active": True,
        "is_deleted": False,
        "tipo_usuario": "CLIENTE",
        "tenant_id": payload.tenant_id,
        "holding_id": payload.holding_id,
        "hashed_password": hashed_pw,
        "permissions": [
            "catalog.products.read",
            "catalog.products.create",
            "inventory.stock.read",
            "inventory.kardex.create",
            "inventory.counts.create",
            "inventory.mermas.create",
            "operations.sales.create",
            "tenancy.quotas.read",
            "tenancy.storage_quotas.read",
        ],
    }
    return ClientUserAdminResponse(
        user_id=next_uid,
        holding_id=payload.holding_id,
        tenant_id=payload.tenant_id,
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role_slug=payload.role_slug,
        hierarchy_rank=rank,
        is_holding_owner=payload.is_holding_owner,
        is_deleted=False,
    )


@router.post(
    "/api/v1/tenancy/client-users/{user_id}/soft-delete",
    response_model=ClientUserAdminResponse,
    status_code=status.HTTP_200_OK,
)
async def soft_delete_client_user_admin_endpoint(
    user_id: int,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.client_users.manage")),
    ],
) -> ClientUserAdminResponse:
    """Aplica `Soft-Delete` (`is_deleted = True`) a un Usuario Cliente, liberando 1 cupo del Plan y revocando su sesión en Redis."""
    record = _CLIENT_USERS_STORE.get(user_id)
    if record is None:
        raise ResourceNotFoundError(
            f"Client user {user_id} not found.",
            i18n_key="tenancy:errors.client_user_not_found",
        )
    if user_id == principal.user_id:
        raise PermissionDeniedError(
            "An actor cannot soft-delete their own active session.",
            i18n_key="auth:errors.cannot_self_delete",
        )
    record["is_deleted"] = True
    record["is_active"] = False
    revoke_session_token(user_id=user_id)
    with contextlib.suppress(Exception):
        redis_client = get_redis_client()
        killswitch = SessionKillSwitchService(redis_client=redis_client)
        await killswitch.revoke_all_user_sessions(
            user_id=user_id,
            actor_user_id=principal.user_id,
            scope="client",
        )
    return ClientUserAdminResponse(
        user_id=user_id,
        holding_id=str(record.get("holding_id", "holding_default")),
        tenant_id=str(record.get("tenant_id", "tenant_default")),
        username=str(record.get("username", f"user_{user_id}")),
        email=str(record.get("email", f"user_{user_id}@cliente.cl")),
        first_name=str(record.get("first_name", "Operador")),
        last_name=str(record.get("last_name", "Cliente")),
        role_slug=str(record.get("role", "admin")),
        hierarchy_rank=int(str(record.get("hierarchy_rank", 10))),
        is_holding_owner=bool(record.get("is_holding_owner", False)),
        is_deleted=True,
    )


@router.post(
    "/api/v1/tenancy/client-users/{user_id}/restore",
    response_model=ClientUserAdminResponse,
    status_code=status.HTTP_200_OK,
)
async def restore_client_user_admin_endpoint(
    user_id: int,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.client_users.manage")),
    ],
) -> ClientUserAdminResponse:
    """Restaura un Usuario Cliente en `Soft-Delete` (`is_deleted = False`), verificando cuota disponible de asientos."""
    record = _CLIENT_USERS_STORE.get(user_id)
    if record is None:
        raise ResourceNotFoundError(
            f"Client user {user_id} not found.",
            i18n_key="tenancy:errors.client_user_not_found",
        )
    if not record.get("is_deleted", False):
        return ClientUserAdminResponse(
            user_id=user_id,
            holding_id=str(record.get("holding_id", "holding_default")),
            tenant_id=str(record.get("tenant_id", "tenant_default")),
            username=str(record.get("username", f"user_{user_id}")),
            email=str(record.get("email", f"user_{user_id}@cliente.cl")),
            first_name=str(record.get("first_name", "Operador")),
            last_name=str(record.get("last_name", "Cliente")),
            role_slug=str(record.get("role", "admin")),
            hierarchy_rank=int(str(record.get("hierarchy_rank", 10))),
            is_holding_owner=bool(record.get("is_holding_owner", False)),
            is_deleted=False,
        )

    holding_id = str(record.get("holding_id", "holding_default"))
    holding = _holdings_store.get(holding_id)
    tenant_id = str(record.get("tenant_id", "tenant_default"))
    tenant = _tenants_store.get(tenant_id)
    plan = _resolve_plan_for_holding(holding)

    existing_seat_states = [
        ClientUserSeatState(
            user_id=uid,
            holding_id=str(rec.get("holding_id", "")),
            is_deleted=bool(rec.get("is_deleted", False)),
        )
        for uid, rec in _CLIENT_USERS_STORE.items()
        if str(rec.get("holding_id", "")) == holding_id
    ]
    plan_max_users = holding.max_active_users if holding is not None else plan.max_active_users
    holding_override = holding.custom_max_users_override if holding is not None else None
    tenant_override = tenant.custom_max_users_override if tenant is not None else None

    seat_eval = evaluate_seat_quota_for_new_or_restored_user(
        existing_users=existing_seat_states,
        plan_max_active_users=plan_max_users,
        holding_override=holding_override,
        tenant_override=tenant_override,
    )
    if not seat_eval.allowed:
        record_quota_semaphore_metric(
            resource_type="users",
            status="OVER_QUOTA",
            usage_percentage=Decimal("100.00"),
            active_count=seat_eval.active_non_deleted_users,
            effective_max_limit=seat_eval.effective_max_users,
            tenant_id=tenant_id,
            holding_id=holding_id,
        )
        emit_quota_audit_log(
            "seat_limit_exceeded_on_restore",
            "users",
            "OVER_QUOTA",
            {
                "target_user_id": user_id,
                "username": str(record.get("username", "")),
                "email": str(record.get("email", "")),
            },
        )
        raise QuotaExceededError(
            f"Cannot restore client user {user_id}. Maximum active users quota reached ({seat_eval.effective_max_users}). "
            "Archive/soft-delete an active user or upgrade the plan.",
            i18n_key="tenancy:errors.seat_quota_exceeded",
            context={
                "active_users": seat_eval.active_non_deleted_users,
                "max_users": seat_eval.effective_max_users,
            },
        )

    record["is_deleted"] = False
    record["is_active"] = True
    restore_revoked_user_session(user_id=user_id)
    with contextlib.suppress(Exception):
        redis_client = get_redis_client()
        killswitch = SessionKillSwitchService(redis_client=redis_client)
        killswitch.clear_revocation_on_restore(user_id=user_id)
    return ClientUserAdminResponse(
        user_id=user_id,
        holding_id=holding_id,
        tenant_id=tenant_id,
        username=str(record.get("username", f"user_{user_id}")),
        email=str(record.get("email", f"user_{user_id}@cliente.cl")),
        first_name=str(record.get("first_name", "Operador")),
        last_name=str(record.get("last_name", "Cliente")),
        role_slug=str(record.get("role", "admin")),
        hierarchy_rank=int(str(record.get("hierarchy_rank", 10))),
        is_holding_owner=bool(record.get("is_holding_owner", False)),
        is_deleted=False,
    )


@router.post(
    "/api/v1/tenancy/admin/impersonate",
    response_model=AdminImpersonateResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_impersonate_tenant_endpoint(
    payload: AdminImpersonateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("tenancy.tenants.impersonate")),
    ],
) -> AdminImpersonateResponse:
    """
    Emite un token temporal auditado de soporte ('Entrar como Local') acotado al `tenant_id`
    para que el SuperUser pueda inspeccionar la interfaz cliente de la sucursal.
    """
    tenant = _tenants_store.get(payload.tenant_id)
    holding_id = (
        tenant.holding_id
        if tenant is not None
        else (principal.holding_id or "holding_genesis")
    )
    schema_name = (
        tenant.schema_name
        if tenant is not None
        else (
            payload.tenant_id
            if payload.tenant_id.startswith("tenant_")
            else f"tenant_{payload.tenant_id}"
        )
    )
    support_token = create_access_token(
        user_id=principal.user_id,
        holding_id=holding_id,
        tenant_id=payload.tenant_id,
        tenant_schema=schema_name,
        hierarchy_rank=0,
        is_superuser_god=True,
        is_global_staff=True,
        accessible_tenants=[payload.tenant_id, schema_name],
    )
    return AdminImpersonateResponse(
        access_token=support_token,
        tenant_id=payload.tenant_id,
        holding_id=holding_id,
        schema_name=schema_name,
        impersonated_by_user_id=principal.user_id,
        reason=payload.reason,
    )


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
    active_client_users = sum(
        1 for u in _CLIENT_USERS_STORE.values() if not bool(u.get("is_deleted", False))
    )
    return TenancyDashboardSummaryResponse(
        holdings=len(_holdings_store),
        legal_entities=len(_legal_entities_store),
        tenants=len(_tenants_store),
        users=len(_GLOBAL_USERS_STORE),
        plans=len(_plans_store),
        client_users=active_client_users,
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
    holding = _holdings_store.get(holding_id)
    tenant = _tenants_store.get(principal.tenant_id or "")
    plan = _resolve_plan_for_holding(holding)

    existing_users = [
        ClientUserSeatState(
            user_id=uid,
            holding_id=str(rec.get("holding_id", "")),
            is_deleted=bool(rec.get("is_deleted", False)),
        )
        for uid, rec in _CLIENT_USERS_STORE.items()
        if str(rec.get("holding_id", "")) == holding_id
    ]
    plan_max = holding.max_active_users if holding is not None else plan.max_active_users
    evaluation = evaluate_seat_quota_for_new_or_restored_user(
        existing_users=existing_users,
        plan_max_active_users=plan_max,
        holding_override=holding.custom_max_users_override if holding is not None else None,
        tenant_override=tenant.custom_max_users_override if tenant is not None else None,
    )
    usage_pct = (
        (
            Decimal(evaluation.active_non_deleted_users)
            * Decimal("100")
            / Decimal(evaluation.effective_max_users)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if evaluation.effective_max_users > 0
        else Decimal("100.00")
    )
    return SeatQuotaStatusResponse(
        holding_id=holding_id,
        active_non_deleted_users=evaluation.active_non_deleted_users,
        soft_deleted_historical_users=evaluation.soft_deleted_users,
        effective_max_users=evaluation.effective_max_users,
        remaining_seats=evaluation.remaining_seats,
        usage_percentage=usage_pct,
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
    holding = _holdings_store.get(principal.holding_id or "")
    tenant = _tenants_store.get(tenant_id)

    evaluation = evaluate_storage_quota_bytes(
        current_used_bytes=0,
        new_bytes=0,
        plan_max_storage_mb=1024,
        holding_storage_override_mb=(
            holding.custom_storage_mb_override if holding is not None else None
        ),
        tenant_storage_override_mb=(
            tenant.custom_storage_mb_override if tenant is not None else None
        ),
    )
    remaining_bytes = max(
        0,
        evaluation.effective_max_storage_bytes - evaluation.current_used_bytes,
    )
    return StorageQuotaStatusResponse(
        tenant_id=tenant_id,
        current_used_bytes=evaluation.current_used_bytes,
        effective_max_storage_mb=evaluation.effective_max_storage_mb,
        effective_max_storage_bytes=evaluation.effective_max_storage_bytes,
        remaining_bytes=remaining_bytes,
        usage_percentage=evaluation.usage_percentage,
        allowed=evaluation.allowed,
    )


@router.get(
    "/api/v1/tenancy/quotas/summary",
    response_model=TenantQuotaSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_tenant_quota_summary_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("tenancy.quotas.read")),
    ],
) -> TenantQuotaSummaryResponse:
    """
    Devuelve el estado consolidado de las 6 cuotas de capacidad del Plan + Overrides
    (`users`, `products`, `suppliers`, `recipes`, `combos`, `storage_mb`) con semáforo
    preventivo (`NORMAL`, `WARNING` >= 80%, `CRITICAL` >= 95%, `OVER_QUOTA` 100%).
    """
    holding_id = principal.holding_id or "holding_default"
    tenant_id = principal.tenant_id or "tenant_default"
    holding = _holdings_store.get(holding_id)
    tenant = _tenants_store.get(tenant_id)
    plan = _resolve_plan_for_holding(holding)

    active_users = sum(
        1
        for rec in _CLIENT_USERS_STORE.values()
        if str(rec.get("holding_id", "")) == holding_id and not bool(rec.get("is_deleted", False))
    )
    deleted_users = sum(
        1
        for rec in _CLIENT_USERS_STORE.values()
        if str(rec.get("holding_id", "")) == holding_id and bool(rec.get("is_deleted", False))
    )

    spec_list: tuple[
        tuple[QuotaResourceType, int, int, int, int | None, int | None],
        ...,
    ] = (
        (
            "users",
            active_users,
            deleted_users,
            holding.max_active_users if holding is not None else plan.max_active_users,
            holding.custom_max_users_override if holding is not None else None,
            tenant.custom_max_users_override if tenant is not None else None,
        ),
        (
            "products",
            0,
            0,
            plan.max_products,
            holding.custom_max_products_override if holding is not None else None,
            tenant.custom_max_products_override if tenant is not None else None,
        ),
        (
            "suppliers",
            0,
            0,
            plan.max_suppliers,
            holding.custom_max_suppliers_override if holding is not None else None,
            tenant.custom_max_suppliers_override if tenant is not None else None,
        ),
        (
            "recipes",
            0,
            0,
            plan.max_recipes,
            holding.custom_max_recipes_override if holding is not None else None,
            tenant.custom_max_recipes_override if tenant is not None else None,
        ),
        (
            "combos",
            0,
            0,
            plan.max_combos,
            holding.custom_max_combos_override if holding is not None else None,
            tenant.custom_max_combos_override if tenant is not None else None,
        ),
        (
            "storage_mb",
            0,
            0,
            holding.max_storage_mb if holding is not None else plan.max_storage_mb,
            holding.custom_storage_mb_override if holding is not None else None,
            tenant.custom_storage_mb_override if tenant is not None else None,
        ),
    )

    resources_map: dict[QuotaResourceType, ResourceQuotaItemResponse] = {}
    for rtype, act_cnt, del_cnt, p_limit, h_ovr, t_ovr in spec_list:
        ev = evaluate_resource_capacity_quota(
            resource_type=rtype,
            active_non_deleted_count=act_cnt,
            soft_deleted_count=del_cnt,
            plan_limit=p_limit,
            holding_override=h_ovr,
            tenant_override=t_ovr,
        )
        resources_map[rtype] = ResourceQuotaItemResponse(
            resource_type=rtype,
            active_count=ev.active_count,
            soft_deleted_count=ev.soft_deleted_count,
            effective_max_limit=ev.effective_max_limit,
            remaining_capacity=ev.remaining_capacity,
            usage_percentage=ev.usage_percentage,
            status=ev.status,
            allowed=ev.allowed,
        )
        record_quota_semaphore_metric(
            resource_type=rtype,
            status=ev.status,
            usage_percentage=ev.usage_percentage,
            active_count=ev.active_count,
            effective_max_limit=ev.effective_max_limit,
            tenant_id=tenant_id,
            holding_id=holding_id,
        )

    return TenantQuotaSummaryResponse(
        holding_id=holding_id,
        tenant_id=tenant_id,
        plan_slug=plan.slug,
        resources=resources_map,
    )
