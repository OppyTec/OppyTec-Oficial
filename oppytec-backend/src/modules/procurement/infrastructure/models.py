"""
oppytec-backend/src/modules/procurement/infrastructure/models.py
Modelos SQLAlchemy 2.0 de Abastecimiento y Facturas (`TenantBase`):
- `Proveedor` (`translatable = False` — regla "Pollo King": razón social jamás se traduce)
- `ProductoProveedor`, `Compra`, `CompraItem`, `Invoice`.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import ClassVar

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
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
    lead_time_dias: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


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


class Compra(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Orden de compra y recepción de mercadería con montos en `Decimal(14, 2)`."""

    __tablename__ = "compras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
