"""
oppytec-backend/src/modules/catalog/infrastructure/models.py
Modelos SQLAlchemy 2.0 del Catálogo (`TenantBase`):
- `Categoria`, `FamiliaProducto`, `TipoEnvase`, `EtiquetaProducto`
- `Marca` (`translatable = False` — regla de nombres propios inmutables)
- `Producto` con las 3 capas de unidades (`Decimal(12, 4)`), costos (`Decimal(14, 2)`) y `TranslatableI18nMixin`.
"""
from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models_base import (
    AuditTimestampsMixin,
    TenantBase,
    TranslatableI18nMixin,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin


class Categoria(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Categoría conceptual de productos con soporte de traducción dinámica (`i18n_data`)."""

    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    icono: Mapped[str] = mapped_column(String(64), default="Package", nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="#007BFF", nullable=False)


class FamiliaProducto(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Familia conceptual de productos dentro de una categoría."""

    __tablename__ = "familias_producto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categorias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, index=True)


class Marca(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Marca comercial (`translatable = False` — jamás se traduce en ningún idioma, ej. 'Savory')."""

    __tablename__ = "marcas"
    translatable: ClassVar[bool] = False

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)


class TipoEnvase(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Tipo de envase o empaque (ej. Caja, Botella, Bolsa)."""

    __tablename__ = "tipos_envase"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)


class EtiquetaProducto(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Etiqueta clasificadora para filtrado de catálogo e inventario."""

    __tablename__ = "etiquetas_producto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="#28A745", nullable=False)


class Producto(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """
    Insumo o producto vendible con conversión exacta en 3 capas de unidades (`NUMERIC(12, 4)`)
    y costos financieros (`NUMERIC(14, 2)`). Prohibido el uso de `float`.
    """

    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    categoria_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categorias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    familia_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("familias_producto.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
    )
    marca_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("marcas.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
    )
    # 3 Capas de Unidades: Compra -> Almacenamiento -> Consumo/Receta (NUMERIC(12, 4))
    unidad_compra: Mapped[str] = mapped_column(String(32), default="CAJA", nullable=False)
    unidad_almacen: Mapped[str] = mapped_column(String(32), default="KG", nullable=False)
    unidad_receta: Mapped[str] = mapped_column(String(32), default="GR", nullable=False)
    factor_compra_a_almacen: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("1.0000"),
        nullable=False,
    )
    factor_almacen_a_receta: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("1000.0000"),
        nullable=False,
    )
    # Costos y precios en Decimal(14, 2)
    costo_compra_neto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    costo_promedio_almacen: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    stock_minimo: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
