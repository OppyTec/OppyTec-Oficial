"""
oppytec-backend/src/modules/audit/application/audit_service.py
Servicio de aplicación *Append-Only* estricto para la bitácora forense RBAC y de Actividad.
Prohíbe explícitamente cualquier operación `update` o `delete` sobre registros de auditoría.
"""
from __future__ import annotations

from src.core.exceptions import PermissionDeniedError
from src.modules.audit.domain.entities import (
    ActivityAuditEntry,
    AuditScopeType,
    RbacAuditEntry,
    create_activity_audit_entry,
    create_rbac_audit_entry,
)


class AppendOnlyAuditService:
    """
    Servicio Append-Only del Doble Libro de Auditoría Forense (`public` y `tenant_*`).
    Solo admite inserción de eventos; cualquier intento de modificar o eliminar lanza `PermissionDeniedError`.
    """

    def __init__(self) -> None:
        self._rbac_ledger: list[RbacAuditEntry] = []
        self._activity_ledger: list[ActivityAuditEntry] = []

    def append_rbac_change(
        self,
        *,
        actor_user_id: int,
        target_user_id: int | None,
        action_type: str,
        permission_or_role: str,
        before_state: dict[str, object] | None = None,
        after_state: dict[str, object] | None = None,
        scope: AuditScopeType = "tenant",
    ) -> RbacAuditEntry:
        """Agrega un evento inmutable al libro `audit_rbac_changes`."""
        entry = create_rbac_audit_entry(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action_type=action_type,
            permission_or_role=permission_or_role,
            before_state=before_state,
            after_state=after_state,
            scope=scope,
        )
        self._rbac_ledger.append(entry)
        return entry

    def append_activity_event(
        self,
        *,
        actor_user_id: int,
        action_code: str,
        resource_type: str,
        resource_id: str,
        before_state: dict[str, object] | None = None,
        after_state: dict[str, object] | None = None,
        authorization_lineage: dict[str, object] | None = None,
        scope: AuditScopeType = "tenant",
    ) -> ActivityAuditEntry:
        """Agrega un evento inmutable con `authorization_lineage` al libro `audit_activity_log`."""
        entry = create_activity_audit_entry(
            actor_user_id=actor_user_id,
            action_code=action_code,
            resource_type=resource_type,
            resource_id=resource_id,
            before_state=before_state,
            after_state=after_state,
            authorization_lineage=authorization_lineage,
            scope=scope,
        )
        self._activity_ledger.append(entry)
        return entry

    def list_rbac_entries(self, *, scope: AuditScopeType | None = None) -> tuple[RbacAuditEntry, ...]:
        """Devuelve una tupla inmutable de las entradas RBAC registradas."""
        if scope is None:
            return tuple(self._rbac_ledger)
        return tuple(e for e in self._rbac_ledger if e.scope == scope)

    def list_activity_entries(
        self,
        *,
        scope: AuditScopeType | None = None,
    ) -> tuple[ActivityAuditEntry, ...]:
        """Devuelve una tupla inmutable de las entradas de actividad registradas."""
        if scope is None:
            return tuple(self._activity_ledger)
        return tuple(e for e in self._activity_ledger if e.scope == scope)

    def update_entry(self, event_uuid: str, *_args: object, **_kwargs: object) -> None:
        """Bloqueador de seguridad: el libro de auditoría es estrictamente Append-Only."""
        raise PermissionDeniedError(
            f"AppendOnlyViolation: Audit entry '{event_uuid}' is immutable and cannot be updated.",
            i18n_key="audit:errors.append_only_immutable",
            error_code="AUDIT_APPEND_ONLY_VIOLATION",
        )

    def delete_entry(self, event_uuid: str, *_args: object, **_kwargs: object) -> None:
        """Bloqueador de seguridad: el libro de auditoría jamás permite borrado físico ni lógico."""
        raise PermissionDeniedError(
            f"AppendOnlyViolation: Audit entry '{event_uuid}' is immutable and cannot be deleted.",
            i18n_key="audit:errors.append_only_immutable",
            error_code="AUDIT_APPEND_ONLY_VIOLATION",
        )
