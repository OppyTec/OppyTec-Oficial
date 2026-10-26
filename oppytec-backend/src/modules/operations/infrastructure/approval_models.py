"""
oppytec-backend/src/modules/operations/infrastructure/approval_models.py
Modelos SQLAlchemy 2.0 de Solicitudes de Aprobación y Matriz de Gobernanza (`TenantBase`):
- `SolicitudAprobacionModel` (tabla `solicitudes_aprobacion`)
- `NotificationMatrixRuleModel` (tabla `notification_matrix_rules`)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models_base import (
    AuditTimestampsMixin,
    JSONDictType,
    TenantBase,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin


class SolicitudAprobacionModel(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """
    Solicitud de aprobación operacional y de gobernanza multi-tenant.
    Almacena eventos de aprobación para inventario, mermas, compras, consumo buffet y equipo.
    """

    __tablename__ = "solicitudes_aprobacion"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(30),
        default="pendiente",
        server_default="pendiente",
        nullable=False,
    )
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    bodega_id: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True)
    area_operativa_id: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True)
    detalles: Mapped[dict[str, Any]] = mapped_column(JSONDictType, default=dict, nullable=False)
    resuelto_por: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
    resuelto_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None, nullable=True)

    __table_args__ = (
        Index("ix_solicitudes_aprobacion_estado_created_at", "estado", "created_at"),
        Index("ix_solicitudes_aprobacion_tipo_estado", "tipo", "estado"),
        Index("ix_solicitudes_aprobacion_area_bodega", "area_operativa_id", "bodega_id"),
    )


class NotificationMatrixRuleModel(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """
    Regla de la matriz de gobernanza y despacho de notificaciones por cargo y tipo de solicitud.
    Configura qué roles/cargos reciben alertas in-app, correo, push y cuáles tienen potestad de aprobación.
    """

    __tablename__ = "notification_matrix_rules"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    cargo: Mapped[str] = mapped_column(String(64), nullable=False)
    tipo_solicitud: Mapped[str] = mapped_column(String(50), nullable=False)
    canal_in_app: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    canal_email: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    canal_push: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    es_aprobador: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    __table_args__ = (
        UniqueConstraint("cargo", "tipo_solicitud", name="uq_notification_matrix_rules_cargo_tipo_solicitud"),
    )
