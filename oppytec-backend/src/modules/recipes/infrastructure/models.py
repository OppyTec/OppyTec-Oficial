"""
oppytec-backend/src/modules/recipes/infrastructure/models.py
Modelos SQLAlchemy 2.0 de Escandallos y Recetas (`TenantBase`):
- `Receta`, `RecetaIngrediente`
- `Combo`, `ComboItem`
- `GrupoOpciones`, `GrupoOpcionesItem`.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models_base import (
    AuditTimestampsMixin,
    TenantBase,
    TranslatableI18nMixin,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin


class Receta(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Ficha técnica gastronómica (escandallo o sub-receta) con precios y costos en `Decimal`."""

    __tablename__ = "recetas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    es_subreceta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    porciones_rendimiento: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("1.0000"),
        nullable=False,
    )
    costo_total_calculado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    precio_venta_bruto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )


class RecetaIngrediente(TenantBase, AuditTimestampsMixin):
    """Ingrediente (`Producto` o sub-`Receta`) que compone una `Receta` con merma técnica en `Decimal`."""

    __tablename__ = "receta_ingredientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receta_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recetas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
    )
    subreceta_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("recetas.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
    )
    cantidad_receta: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    porcentaje_merma: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        default=Decimal("0.00"),
        nullable=False,
    )


class Combo(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Promoción o menú compuesto por múltiples recetas/productos."""

    __tablename__ = "combos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    precio_venta_bruto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )


class ComboItem(TenantBase, AuditTimestampsMixin):
    """Elemento integrante de un `Combo`."""

    __tablename__ = "combo_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    combo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("combos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receta_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recetas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("1.0000"),
        nullable=False,
    )


class GrupoOpciones(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Grupo de modificadores u opciones intercambiables para recetas o combos."""

    __tablename__ = "grupos_opciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    min_selecciones: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_selecciones: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class GrupoOpcionesItem(TenantBase, AuditTimestampsMixin):
    """Opción seleccionable dentro de un `GrupoOpciones` con recargo opcional en `Decimal`."""

    __tablename__ = "grupo_opciones_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grupo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("grupos_opciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recargo_precio: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
