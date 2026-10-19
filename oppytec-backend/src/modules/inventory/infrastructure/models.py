"""
oppytec-backend/src/modules/inventory/infrastructure/models.py
Modelos SQLAlchemy 2.0 de Inventario (`TenantBase`):
- `Bodega`, `AreaOperativa`, `ProductoBodega`
- `RegistroStock` (Kardex estrictamente Append-Only sin `SoftDeleteMixin`)
- `ConteoInventario`, `ConteoItem`, `Merma`, `SolicitudAprobacion`.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models_base import (
    AuditTimestampsMixin,
    TenantBase,
    TranslatableI18nMixin,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin


class Bodega(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Bodega física o lógica de almacenamiento dentro del `tenant_*`."""

    __tablename__ = "bodegas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    es_principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AreaOperativa(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Área operativa (Cocina, Barra, Pastelería) asociada a una bodega."""

    __tablename__ = "areas_operativas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bodega_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)


class ProductoBodega(TenantBase, AuditTimestampsMixin):
    """Saldo consolidado de un `Producto` en una `Bodega` (`UNIQUE(producto_id, bodega_id)`)."""

    __tablename__ = "producto_bodegas"
    __table_args__ = (UniqueConstraint("producto_id", "bodega_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bodega_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_actual: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )


class RegistroStock(TenantBase):
    """
    Libro mayor Kardex de movimientos de stock (`registro_stock`).
    Estrictamente Append-Only e inmutable (sin `SoftDeleteMixin`).
    """

    __tablename__ = "registro_stock"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bodega_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo_movimiento: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    saldo_resultante: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    referencia_documento: Mapped[str | None] = mapped_column(
        String(128),
        default=None,
        nullable=True,
    )


class ConteoInventario(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Cabecera de toma física de inventario en una bodega."""

    __tablename__ = "conteos_inventario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bodega_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    estado: Mapped[str] = mapped_column(String(32), default="EN_PROCESO", nullable=False)
    responsable_user_id: Mapped[int] = mapped_column(Integer, nullable=False)


class ConteoItem(TenantBase, AuditTimestampsMixin):
    """Línea de detalle de un conteo físico de inventario (`Decimal(12, 4)`)."""

    __tablename__ = "conteo_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conteo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conteos_inventario.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    stock_sistema: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    stock_contado: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    diferencia: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)


class Merma(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Registro de pérdida o merma operativa con valoración financiera en `Decimal(14, 2)`."""

    __tablename__ = "mermas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bodega_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    costo_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    estado_aprobacion: Mapped[str] = mapped_column(String(32), default="PENDIENTE", nullable=False)
    reportado_por_user_id: Mapped[int] = mapped_column(Integer, nullable=False)


class SolicitudAprobacion(TenantBase, AuditTimestampsMixin):
    """Flujo de aprobación para mermas sobre umbral o ajustes críticos de inventario."""

    __tablename__ = "solicitudes_aprobacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merma_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("mermas.id", ondelete="CASCADE"),
        default=None,
        nullable=True,
    )
    estado: Mapped[str] = mapped_column(String(32), default="PENDIENTE", nullable=False)
    solicitante_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    aprobador_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    comentario_resolucion: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
