"""
oppytec-backend/src/modules/audit/application/__init__.py
Servicio Append-Only estricto para el Doble Libro de Auditoría Forense.
"""
from __future__ import annotations

from src.modules.audit.application.audit_service import AppendOnlyAuditService

__all__ = ["AppendOnlyAuditService"]
