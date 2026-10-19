"""
oppytec-backend/src/modules/identity/domain/__init__.py
Capa de dominio pura para el motor de RBAC Dual de 3 niveles, jerarquía de rangos y permisos temporales JIT.
"""
from __future__ import annotations

from src.modules.identity.domain.rbac_evaluator import (
    THREE_LEVEL_PERMISSION_REGEX,
    AuthorizationDecision,
    AuthorizationLineage,
    PermissionGrantSpec,
    can_delegate_permission,
    compute_effective_permissions,
    evaluate_permission_access,
    is_grant_currently_active,
    is_valid_three_level_permission,
    validate_hierarchy_delegation,
)

__all__ = [
    "THREE_LEVEL_PERMISSION_REGEX",
    "AuthorizationDecision",
    "AuthorizationLineage",
    "PermissionGrantSpec",
    "can_delegate_permission",
    "compute_effective_permissions",
    "evaluate_permission_access",
    "is_grant_currently_active",
    "is_valid_three_level_permission",
    "validate_hierarchy_delegation",
]
