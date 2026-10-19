"""
oppytec-backend/src/modules/tenancy/domain/__init__.py
Capa de dominio pura para jerarquía corporativa `Holding -> LegalEntity (1:1) -> Tenant`,
cupos de usuarios activos (`Seat Quotas` con liberación instantánea por `soft-delete`)
y cuotas de memoria en Cloudflare R2 (`Storage Quotas`).
"""
from __future__ import annotations

from src.modules.tenancy.domain.quotas import (
    ClientUserSeatState,
    SeatQuotaEvaluation,
    StorageQuotaEvaluation,
    TenantHierarchyAssignment,
    evaluate_seat_quota_for_new_or_restored_user,
    evaluate_storage_quota_bytes,
    resolve_effective_max_storage_mb,
    resolve_effective_max_users,
    validate_holding_legal_entity_tenant_cardinality,
)

__all__ = [
    "ClientUserSeatState",
    "SeatQuotaEvaluation",
    "StorageQuotaEvaluation",
    "TenantHierarchyAssignment",
    "evaluate_seat_quota_for_new_or_restored_user",
    "evaluate_storage_quota_bytes",
    "resolve_effective_max_storage_mb",
    "resolve_effective_max_users",
    "validate_holding_legal_entity_tenant_cardinality",
]
