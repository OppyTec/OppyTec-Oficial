"""
oppytec-backend/src/modules/audit/domain/__init__.py
Entidades inmutables para el Doble Libro de Auditoría Forense (`RbacAuditEntry`, `ActivityAuditEntry`).
"""
from __future__ import annotations

from src.modules.audit.domain.entities import (
    ActivityAuditEntry,
    RbacAuditEntry,
    create_activity_audit_entry,
    create_rbac_audit_entry,
)

__all__ = [
    "ActivityAuditEntry",
    "RbacAuditEntry",
    "create_activity_audit_entry",
    "create_rbac_audit_entry",
]
