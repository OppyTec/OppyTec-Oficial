"""
oppytec-backend/src/modules/audit/domain/entities.py
Entidades de dominio inmutables (`frozen=True`) para el Doble Libro de Auditoría Forense:
1. `RbacAuditEntry` (`audit_rbac_changes` / `global_audit_rbac_changes`)
2. `ActivityAuditEntry` (`audit_activity_log` / `global_audit_activity_log` con `authorization_lineage`)
Cero dependencias de infraestructura y prohibido mutar una vez creadas.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

AuditScopeType = Literal["public", "tenant"]


@dataclass(frozen=True)
class RbacAuditEntry:
    """Registro forense inmutable de cambios de roles, usuarios y concesiones temporales JIT."""

    event_uuid: str
    scope: AuditScopeType
    created_at: datetime
    actor_user_id: int
    target_user_id: int | None
    action_type: str
    permission_or_role: str
    before_state: dict[str, object] = field(default_factory=dict)
    after_state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ActivityAuditEntry:
    """
    Registro forense inmutable de operaciones de negocio con evidencia Antes/Después
    y huella de autorización `authorization_lineage`.
    """

    event_uuid: str
    scope: AuditScopeType
    created_at: datetime
    actor_user_id: int
    action_code: str
    resource_type: str
    resource_id: str
    before_state: dict[str, object] = field(default_factory=dict)
    after_state: dict[str, object] = field(default_factory=dict)
    authorization_lineage: dict[str, object] = field(default_factory=dict)


def create_rbac_audit_entry(
    *,
    actor_user_id: int,
    target_user_id: int | None,
    action_type: str,
    permission_or_role: str,
    before_state: dict[str, object] | None = None,
    after_state: dict[str, object] | None = None,
    scope: AuditScopeType = "tenant",
    created_at: datetime | None = None,
) -> RbacAuditEntry:
    """Crea una instancia inmutable `RbacAuditEntry` copiando defensivamente los diccionarios de estado."""
    return RbacAuditEntry(
        event_uuid=str(uuid.uuid4()),
        scope=scope,
        created_at=created_at or datetime.now(UTC),
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action_type=action_type.strip(),
        permission_or_role=permission_or_role.strip(),
        before_state=dict(before_state or {}),
        after_state=dict(after_state or {}),
    )


def create_activity_audit_entry(
    *,
    actor_user_id: int,
    action_code: str,
    resource_type: str,
    resource_id: str,
    before_state: dict[str, object] | None = None,
    after_state: dict[str, object] | None = None,
    authorization_lineage: dict[str, object] | None = None,
    scope: AuditScopeType = "tenant",
    created_at: datetime | None = None,
) -> ActivityAuditEntry:
    """Crea una instancia inmutable `ActivityAuditEntry` con `authorization_lineage`."""
    return ActivityAuditEntry(
        event_uuid=str(uuid.uuid4()),
        scope=scope,
        created_at=created_at or datetime.now(UTC),
        actor_user_id=actor_user_id,
        action_code=action_code.strip(),
        resource_type=resource_type.strip(),
        resource_id=str(resource_id).strip(),
        before_state=dict(before_state or {}),
        after_state=dict(after_state or {}),
        authorization_lineage=dict(authorization_lineage or {}),
    )
