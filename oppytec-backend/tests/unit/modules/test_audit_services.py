"""
Pruebas unitarias 1:1 para `src/modules/audit/`.
Verifica que el Doble Libro de Auditoría (`public` y `tenant_*`) sea estrictamente Append-Only sin `SoftDeleteMixin`.
"""
from __future__ import annotations

import pytest

from src.modules.audit.infrastructure.models import (
    AuditActivityLog,
    AuditRbacChange,
    GlobalAuditActivityLog,
    GlobalAuditRbacChange,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin

pytestmark = pytest.mark.unit


def test_audit_tables_are_strictly_append_only_without_soft_delete() -> None:
    """Garantiza que ninguna tabla de auditoría herede de `SoftDeleteMixin` ni tenga columna `is_deleted`."""
    for model_cls in (
        GlobalAuditRbacChange,
        GlobalAuditActivityLog,
        AuditRbacChange,
        AuditActivityLog,
    ):
        assert not issubclass(model_cls, SoftDeleteMixin)
        assert "is_deleted" not in model_cls.__table__.c

    assert GlobalAuditRbacChange.__table__.schema == "public"
    assert GlobalAuditActivityLog.__table__.schema == "public"
    assert AuditRbacChange.__table__.schema is None
    assert AuditActivityLog.__table__.schema is None

    entry = AuditActivityLog(
        actor_user_id=10,
        action_code="inventory.mermas.approve",
        resource_type="merma",
        resource_id="42",
        before_state={"estado": "PENDIENTE"},
        after_state={"estado": "APROBADA"},
        authorization_lineage={"granted_by_user_id": 1, "grant_type": "JIT"},
    )
    assert entry.authorization_lineage["grant_type"] == "JIT"
