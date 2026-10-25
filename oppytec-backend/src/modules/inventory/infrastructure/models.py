"""
oppytec-backend/src/modules/inventory/infrastructure/models.py
Modelos SQLAlchemy 2.0 de Inventario (`TenantBase`):
- `Bodega`, `AreaOperativa`, `ProductoBodega`
- `RegistroStock` (Kardex estrictamente Append-Only sin `SoftDeleteMixin`)
- `StockTransfer` (Transferencias de stock entre bodegas)
- `ConteoInventario`, `ConteoItem`, `Merma`, `SolicitudAprobacion`.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
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
    """Saldo consolidado y parámetros de almacenamiento de un `Producto` en una `Bodega` (`UNIQUE(producto_id, bodega_id)`)."""

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
    stock_minimo: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    stock_maximo: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        default=None,
        nullable=True,
    )
    punto_reorden: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        default=None,
        nullable=True,
    )
    pasillo: Mapped[str | None] = mapped_column(
        String(20),
        default=None,
        nullable=True,
    )
    estante: Mapped[str | None] = mapped_column(
        String(20),
        default=None,
        nullable=True,
    )
    nivel: Mapped[str | None] = mapped_column(
        String(20),
        default=None,
        nullable=True,
    )


class RegistroStock(TenantBase):
    """
    Libro mayor Kardex de movimientos de stock (`registro_stock`).
    Estrictamente Append-Only e inmutable (sin `SoftDeleteMixin`).
    """

    __tablename__ = "registro_stock"
    __table_args__ = (
        Index("ix_registro_stock_bodega_producto", "bodega_id", "producto_id"),
        Index("ix_registro_stock_created_tipo", "created_at", "tipo_movimiento"),
        Index("ix_registro_stock_transfer_id", "transfer_id"),
    )

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
    costo_unitario_ppp: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    costo_total_movimiento: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    lote_codigo: Mapped[str | None] = mapped_column(
        String(64),
        default=None,
        nullable=True,
    )
    fecha_vencimiento_lote: Mapped[date | None] = mapped_column(
        Date,
        default=None,
        nullable=True,
    )
    transfer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        default=None,
        nullable=True,
    )
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    referencia_documento: Mapped[str | None] = mapped_column(
        String(128),
        default=None,
        nullable=True,
    )


class StockTransfer(TenantBase, AuditTimestampsMixin):
    """
    Transferencia de stock física/lógica entre bodegas dentro del tenant.
    Registra ciclo de vida: SOLICITADA -> EN_TRANSITO -> RECIBIDA / CANCELADA.
    """

    __tablename__ = "stock_transfers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transfer_uuid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    bodega_origen_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bodega_destino_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    estado: Mapped[str] = mapped_column(String(32), default="SOLICITADA", nullable=False)
    solicitante_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    despachador_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    receptor_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)


class ConteoInventario(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Cabecera de toma física de inventario en una bodega o área operativa."""

    __tablename__ = "conteos_inventario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bodega_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    area_operativa_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("areas_operativas.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
        index=True,
    )
    estado: Mapped[str] = mapped_column(String(32), default="EN_PROCESO", nullable=False)
    responsable_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    aprobador_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )


class ConteoItem(TenantBase, AuditTimestampsMixin):
    """Línea de detalle de un conteo físico de inventario con valorización de diferencias y lotes."""

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
    lote_codigo: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date, default=None, nullable=True)
    costo_unitario_ppp: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    valorizacion_diferencia: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )


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
