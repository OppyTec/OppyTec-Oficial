"""
oppytec-backend/src/modules/audit/infrastructure/models.py
Modelos estrictamente Append-Only para el Doble Libro de Auditoría Forense (`public` y `tenant_*`).
Prohibido heredar de `SoftDeleteMixin` o permitir `UPDATE`/`DELETE` sobre estas tablas.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models_base import JSONDictType, PublicBase, TenantBase


class GlobalAuditRbacChange(PublicBase):
    """Libro inmutable Append-Only de cambios de permisos y roles en el esquema `public`."""

    __tablename__ = "global_audit_rbac_changes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_uuid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    permission_or_role: Mapped[str] = mapped_column(String(128), nullable=False)
    before_state: Mapped[dict[str, object]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )
    after_state: Mapped[dict[str, object]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )


class GlobalAuditActivityLog(PublicBase):
    """Libro inmutable Append-Only de actividad administrativa en el esquema `public`."""

    __tablename__ = "global_audit_activity_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_uuid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    before_state: Mapped[dict[str, object]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )
    after_state: Mapped[dict[str, object]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )
    authorization_lineage: Mapped[dict[str, object]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )


class AuditRbacChange(TenantBase):
    """Libro inmutable Append-Only de delegaciones, roles y permisos JIT dentro de `tenant_*`."""

    __tablename__ = "audit_rbac_changes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_uuid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    permission_or_role: Mapped[str] = mapped_column(String(128), nullable=False)
    before_state: Mapped[dict[str, object]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )
    after_state: Mapped[dict[str, object]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )


class AuditActivityLog(TenantBase):
    """
    Libro inmutable Append-Only de acciones operativas del local (`tenant_*`),
    incluyendo `authorization_lineage` (quién otorgó el permiso usado en la operación).
    """

    __tablename__ = "audit_activity_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_uuid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    before_state: Mapped[dict[str, object]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )
    after_state: Mapped[dict[str, object]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )
    authorization_lineage: Mapped[dict[str, object]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )
