"""
oppytec-backend/src/shared/soft_delete_mixin.py
Mixin estandarizado de borrado lógico (`is_deleted`, `deleted_at`, `deleted_by`).
Permite liberar cupos de `max_active_users` preservando la integridad referencial e histórica.
Excluido estrictamente de las tablas Append-Only de auditoría y Kardex.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, false
from sqlalchemy.orm import Mapped, mapped_column


class SoftDeleteMixin:
    """Mixin transversal para borrado lógico auditable y reversible."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    deleted_by: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )

    def mark_soft_deleted(self, by_user_id: int) -> None:
        """Marca el registro como eliminado lógicamente registrando autor y timestamp UTC."""
        if by_user_id <= 0:
            raise ValueError("deleted_by user_id must be a positive integer")
        self.is_deleted = True
        self.deleted_at = datetime.now(UTC)
        self.deleted_by = by_user_id

    def restore_soft_deleted(self) -> None:
        """Restaura un registro eliminado lógicamente limpiando `deleted_at` y `deleted_by`."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
