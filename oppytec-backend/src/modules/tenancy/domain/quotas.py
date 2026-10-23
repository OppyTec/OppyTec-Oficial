"""
oppytec-backend/src/modules/tenancy/domain/quotas.py
Reglas puras de dominio para:
1. Cardinalidad estricta `Holding -> LegalEntity (1:1) -> Tenant` y aislamiento Cross-Holding.
2. Cálculo de cupos de usuarios activos (`active_non_deleted_users < effective_max_users`),
   donde `is_deleted = True` libera el cupo en el acto.
3. Cálculo de cuota de almacenamiento en Cloudflare R2 (`current_bytes + new_bytes <= max_storage_mb * 1024 * 1024`).
Prohibido el uso de `float` e imports de infraestructura.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

BYTES_PER_MEGABYTE: int = 1024 * 1024
WARNING_USAGE_PCT_THRESHOLD: Decimal = Decimal("80.00")
CRITICAL_USAGE_PCT_THRESHOLD: Decimal = Decimal("95.00")

QuotaResourceType = Literal[
    "users",
    "products",
    "suppliers",
    "recipes",
    "combos",
    "storage_mb",
]
QuotaHealthStatus = Literal["NORMAL", "WARNING", "CRITICAL", "OVER_QUOTA"]


@dataclass(frozen=True)
class TenantHierarchyAssignment:
    """Representa una asignación `Holding -> LegalEntity (1:1) -> Tenant`."""

    holding_id: str
    legal_entity_id: str
    tenant_id: str
    schema_name: str


@dataclass(frozen=True)
class ClientUserSeatState:
    """Estado de membresía de un trabajador cliente en el Holding."""

    user_id: int
    holding_id: str
    is_deleted: bool


@dataclass(frozen=True)
class SeatQuotaEvaluation:
    """Resultado determinista de evaluar el cupo de trabajadores activos del plan."""

    allowed: bool
    active_non_deleted_users: int
    soft_deleted_users: int
    effective_max_users: int
    remaining_seats: int
    reason_code: str


@dataclass(frozen=True)
class StorageQuotaEvaluation:
    """Resultado determinista de evaluar la cuota de memoria R2 en bytes y porcentaje `Decimal`."""

    allowed: bool
    current_used_bytes: int
    new_bytes_to_add: int
    projected_used_bytes: int
    effective_max_storage_mb: int
    effective_max_storage_bytes: int
    usage_percentage: Decimal
    reason_code: str


def validate_holding_legal_entity_tenant_cardinality(
    assignments: tuple[TenantHierarchyAssignment, ...] | list[TenantHierarchyAssignment],
) -> tuple[bool, str]:
    """
    Verifica las invariantes estructurales de multi-tenancy:
    1. Relación `1:1` estricta entre `LegalEntity` y `Tenant` (una `legal_entity_id` no puede tener 2 Tenants).
    2. Unicidad de `tenant_id` y `schema_name`.
    3. Un mismo `tenant_id` jamás puede asociarse a dos `holding_id` distintos.
    """
    seen_legal_entities: dict[str, str] = {}
    seen_tenants: dict[str, str] = {}
    seen_schemas: set[str] = set()

    for item in assignments:
        existing_tenant_for_le = seen_legal_entities.get(item.legal_entity_id)
        if existing_tenant_for_le is not None and existing_tenant_for_le != item.tenant_id:
            return False, "LEGAL_ENTITY_1_TO_1_VIOLATION"
        seen_legal_entities[item.legal_entity_id] = item.tenant_id

        existing_holding_for_tenant = seen_tenants.get(item.tenant_id)
        if (
            existing_holding_for_tenant is not None
            and existing_holding_for_tenant != item.holding_id
        ):
            return False, "CROSS_HOLDING_TENANT_VIOLATION"
        seen_tenants[item.tenant_id] = item.holding_id

        if item.schema_name in seen_schemas:
            return False, "DUPLICATE_TENANT_SCHEMA"
        seen_schemas.add(item.schema_name)

    return True, "CARDINALITY_VALID"


def resolve_effective_max_users(
    *,
    plan_max_active_users: int,
    holding_override: int | None = None,
    tenant_override: int | None = None,
) -> int:
    """
    Resuelve el techo efectivo de usuarios activos con precedencia:
    `tenant_override -> holding_override -> plan_max_active_users`.
    """
    if tenant_override is not None and tenant_override > 0:
        return tenant_override
    if holding_override is not None and holding_override > 0:
        return holding_override
    return max(1, plan_max_active_users)


def evaluate_seat_quota_for_new_or_restored_user(
    *,
    existing_users: tuple[ClientUserSeatState, ...] | list[ClientUserSeatState],
    plan_max_active_users: int,
    holding_override: int | None = None,
    tenant_override: int | None = None,
) -> SeatQuotaEvaluation:
    """
    Calcula cuántos usuarios activos (`is_deleted == False`) consumen cupo en el Holding/Tenant
    y determina si hay al menos 1 cupo libre para crear o reactivar (`restore`) a un trabajador.
    Los trabajadores en `soft-delete` (`is_deleted == True`) NO consumen cupo.
    """
    effective_max = resolve_effective_max_users(
        plan_max_active_users=plan_max_active_users,
        holding_override=holding_override,
        tenant_override=tenant_override,
    )
    active_count = sum(1 for u in existing_users if not u.is_deleted)
    deleted_count = sum(1 for u in existing_users if u.is_deleted)
    allowed = active_count < effective_max
    remaining = max(0, effective_max - active_count)
    reason = "SEAT_AVAILABLE" if allowed else "PLAN_SEAT_QUOTA_EXCEEDED"

    return SeatQuotaEvaluation(
        allowed=allowed,
        active_non_deleted_users=active_count,
        soft_deleted_users=deleted_count,
        effective_max_users=effective_max,
        remaining_seats=remaining,
        reason_code=reason,
    )


def resolve_effective_max_storage_mb(
    *,
    plan_max_storage_mb: int,
    holding_storage_override_mb: int | None = None,
    tenant_storage_override_mb: int | None = None,
) -> int:
    """
    Resuelve el límite efectivo de almacenamiento en MB con precedencia:
    `tenant_storage_override_mb -> holding_storage_override_mb -> plan_max_storage_mb`.
    """
    if tenant_storage_override_mb is not None and tenant_storage_override_mb > 0:
        return tenant_storage_override_mb
    if holding_storage_override_mb is not None and holding_storage_override_mb > 0:
        return holding_storage_override_mb
    return max(1, plan_max_storage_mb)


def evaluate_storage_quota_bytes(
    *,
    current_used_bytes: int,
    new_bytes: int,
    plan_max_storage_mb: int,
    holding_storage_override_mb: int | None = None,
    tenant_storage_override_mb: int | None = None,
) -> StorageQuotaEvaluation:
    """
    Verifica matemáticamente `current_used_bytes + new_bytes <= effective_max_storage_mb * 1024 * 1024`
    y calcula el porcentaje de uso en `Decimal(6, 2)`.
    """
    if current_used_bytes < 0 or new_bytes < 0:
        raise ValueError("Byte counts for storage quota cannot be negative.")

    effective_mb = resolve_effective_max_storage_mb(
        plan_max_storage_mb=plan_max_storage_mb,
        holding_storage_override_mb=holding_storage_override_mb,
        tenant_storage_override_mb=tenant_storage_override_mb,
    )
    max_bytes = effective_mb * BYTES_PER_MEGABYTE
    projected_bytes = current_used_bytes + new_bytes
    allowed = projected_bytes <= max_bytes

    pct = (
        (Decimal(projected_bytes) * Decimal("100") / Decimal(max_bytes)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        if max_bytes > 0
        else Decimal("100.00")
    )
    return StorageQuotaEvaluation(
        allowed=allowed,
        current_used_bytes=current_used_bytes,
        new_bytes_to_add=new_bytes,
        projected_used_bytes=projected_bytes,
        effective_max_storage_mb=effective_mb,
        effective_max_storage_bytes=max_bytes,
        usage_percentage=pct,
        reason_code="STORAGE_AVAILABLE" if allowed else "STORAGE_QUOTA_EXCEEDED",
    )


@dataclass(frozen=True)
class ResourceSlotState:
    """Estado de un recurso contable (`products`, `suppliers`, `recipes`, `combos`, `users`)."""

    item_id: str
    resource_type: QuotaResourceType
    is_deleted: bool = False


@dataclass(frozen=True)
class ResourceQuotaEvaluation:
    """Evaluación unificada de cualquier cuota de capacidad del Plan + Overrides con semáforo."""

    resource_type: QuotaResourceType
    allowed: bool
    active_count: int
    soft_deleted_count: int
    effective_max_limit: int
    remaining_capacity: int
    usage_percentage: Decimal
    status: QuotaHealthStatus
    reason_code: str


def compute_quota_health_status(
    *,
    active_count: int,
    effective_max_limit: int,
    usage_percentage: Decimal,
) -> QuotaHealthStatus:
    """
    Determina el estado del semáforo de cuota:
    - `OVER_QUOTA`: `effective_max_limit == 0` o `active_count >= effective_max_limit`
    - `CRITICAL`: `95.00% <= usage_percentage < 100.00%`
    - `WARNING`: `80.00% <= usage_percentage < 95.00%`
    - `NORMAL`: `< 80.00%`
    """
    if effective_max_limit <= 0 or active_count >= effective_max_limit:
        return "OVER_QUOTA"
    if usage_percentage >= CRITICAL_USAGE_PCT_THRESHOLD:
        return "CRITICAL"
    if usage_percentage >= WARNING_USAGE_PCT_THRESHOLD:
        return "WARNING"
    return "NORMAL"


def resolve_effective_resource_limit(
    *,
    plan_limit: int,
    holding_override: int | None = None,
    tenant_override: int | None = None,
    allow_zero: bool = True,
) -> int:
    """
    Resuelve el límite efectivo de un recurso (`users`, `products`, `suppliers`, `recipes`, `combos`, `storage_mb`)
    con precedencia: `tenant_override -> holding_override -> plan_limit`.
    """
    if tenant_override is not None and tenant_override >= 0:
        return tenant_override if allow_zero else max(1, tenant_override)
    if holding_override is not None and holding_override >= 0:
        return holding_override if allow_zero else max(1, holding_override)
    return max(0, plan_limit) if allow_zero else max(1, plan_limit)


def evaluate_resource_capacity_quota(
    *,
    resource_type: QuotaResourceType,
    active_non_deleted_count: int,
    plan_limit: int,
    soft_deleted_count: int = 0,
    holding_override: int | None = None,
    tenant_override: int | None = None,
) -> ResourceQuotaEvaluation:
    """
    Evalúa la capacidad disponible para un recurso contable (`users`, `products`, `suppliers`, `recipes`, `combos`, `storage_mb`).
    Los elementos archivados (`is_deleted == True`) jamás consumen cupo activo.
    """
    if active_non_deleted_count < 0 or soft_deleted_count < 0:
        raise ValueError("Resource counts cannot be negative.")

    allow_zero = resource_type in ("recipes", "combos")
    effective_max = resolve_effective_resource_limit(
        plan_limit=plan_limit,
        holding_override=holding_override,
        tenant_override=tenant_override,
        allow_zero=allow_zero,
    )
    allowed = effective_max > 0 and active_non_deleted_count < effective_max
    remaining = max(0, effective_max - active_non_deleted_count)

    if effective_max > 0:
        pct = (
            Decimal(active_non_deleted_count) * Decimal("100") / Decimal(effective_max)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        pct = Decimal("100.00")

    health_status = compute_quota_health_status(
        active_count=active_non_deleted_count,
        effective_max_limit=effective_max,
        usage_percentage=pct,
    )
    reason = (
        f"{resource_type.upper()}_QUOTA_AVAILABLE"
        if allowed
        else f"PLAN_{resource_type.upper()}_QUOTA_EXCEEDED"
    )
    return ResourceQuotaEvaluation(
        resource_type=resource_type,
        allowed=allowed,
        active_count=active_non_deleted_count,
        soft_deleted_count=soft_deleted_count,
        effective_max_limit=effective_max,
        remaining_capacity=remaining,
        usage_percentage=pct,
        status=health_status,
        reason_code=reason,
    )

