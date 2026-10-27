"""
oppytec-backend/src/modules/procurement/infrastructure/models.py
Modelos SQLAlchemy 2.0 de Abastecimiento, Compras, Proveedores y Facturas (`TenantBase`):
- `Proveedor` (`translatable = False` — regla "Pollo King": razón social jamás se traduce)
- `ProductoProveedor`, `Compra`, `CompraItem`, `CompraIncidencia`, `Invoice`.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import ClassVar

from sqlalchemy import (
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
)
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models_base import AuditTimestampsMixin, TenantBase
from src.shared.soft_delete_mixin import SoftDeleteMixin


class Proveedor(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """
    Proveedor comercial (`translatable = False` — regla "Pollo King":
    su nombre o razón social permanece idéntico en Español e Inglés).
    """

    __tablename__ = "proveedores"
    translatable: ClassVar[bool] = False

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rut_tax_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    razon_social: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    nombre_fantasia: Mapped[str | None] = mapped_column(String(180), default=None, nullable=True)
    email_contacto: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), default=None, nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True)
    lead_time_dias: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    estado: Mapped[str] = mapped_column(String(32), default="ACTIVO", nullable=False)
    notas: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)


class ProductoProveedor(TenantBase, AuditTimestampsMixin):
    """Acuerdo de suministro y último precio pactado (`Decimal(14, 2)`) entre `Producto` y `Proveedor`."""

    __tablename__ = "producto_proveedores"
    __table_args__ = (UniqueConstraint("producto_id", "proveedor_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proveedor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proveedores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo_proveedor: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True)
    ultimo_costo_neto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    tiempo_entrega_dias: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    es_proveedor_principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Compra(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Orden de compra y recepción de mercadería con montos en `Decimal(14, 2)`."""

    __tablename__ = "compras"
    __table_args__ = (
        Index("ix_compras_proveedor_estado", "proveedor_id", "estado"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_orden: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    proveedor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proveedores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bodega_destino_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bodegas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(String(32), default="BORRADOR", nullable=False, index=True)
    moneda: Mapped[str] = mapped_column(String(10), default="CLP", nullable=False)
    tasa_fx_aplicada: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        default=Decimal("1.00000000"),
        nullable=False,
    )
    monto_neto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    monto_impuestos: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    monto_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    fecha_entrega_comprometida: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    fecha_recepcion_real: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    notas: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
    solicitante_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    receptor_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)


class CompraItem(TenantBase, AuditTimestampsMixin):
    """Línea de detalle de una `Compra` (`Decimal(12, 4)` para cantidades y `Decimal(14, 2)` para costos)."""

    __tablename__ = "compra_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    compra_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad_solicitada: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    cantidad_recibida: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    costo_unitario_neto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    subtotal_linea: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    lote_codigo: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date, default=None, nullable=True)


class CompraIncidencia(TenantBase, AuditTimestampsMixin):
    """Incidencia o discrepancia registrada durante la recepción de una compra."""

    __tablename__ = "compra_incidencias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    compra_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    compra_item_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("compra_items.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
        index=True,
    )
    tipo_incidencia: Mapped[str] = mapped_column(String(50), nullable=False)
    cantidad_afectada: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    monto_disputa: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    resolucion: Mapped[str] = mapped_column(
        String(50),
        default="PENDIENTE",
        nullable=False,
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    foto_evidencia_url: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True)
    registrado_por_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)


class Invoice(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Factura tributaria recibida (conciliada con `Compra` o procesada por OCR/JEV)."""

    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("proveedor_id", "folio_factura"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proveedor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proveedores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    compra_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("compras.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
    )
    folio_factura: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    moneda: Mapped[str] = mapped_column(String(10), default="CLP", nullable=False)
    monto_neto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monto_iva: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    estado_pago: Mapped[str] = mapped_column(String(32), default="PENDIENTE", nullable=False)
