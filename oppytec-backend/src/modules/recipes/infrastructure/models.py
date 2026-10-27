"""
oppytec-backend/src/modules/recipes/infrastructure/models.py
Modelos SQLAlchemy 2.0 de Escandallos, Recetas, Combos y Opciones Dinámicas (`TenantBase`):
- `CategoriaReceta`, `CategoriaCombo`
- `Receta`, `RecetaIngrediente`
- `GrupoOpciones`, `GrupoOpcionesItem`, `RecetaGrupoOpcion`
- `Combo`, `ComboItem`, `ComboGrupoOpcion`
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from src.shared.models_base import (
    AuditTimestampsMixin,
    TenantBase,
    TranslatableI18nMixin,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin


class CategoriaReceta(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Categoría clasificatoria de recetas y escandallos (ej. Entradas, Fondos, Postres, Coctelería)."""

    __tablename__ = "categorias_recetas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    color: Mapped[str | None] = mapped_column(String(32), default="#f59e0b", nullable=True)
    icono: Mapped[str | None] = mapped_column(String(64), default="ChefHat", nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    recetas: Mapped[list[Receta]] = relationship(
        "Receta",
        back_populates="categoria",
        foreign_keys="[Receta.categoria_receta_id]",
    )


class CategoriaCombo(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Categoría clasificatoria de promociones y combos comerciales."""

    __tablename__ = "categorias_combos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    color: Mapped[str | None] = mapped_column(String(32), default="#ec4899", nullable=True)
    icono: Mapped[str | None] = mapped_column(String(64), default="Boxes", nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    combos: Mapped[list[Combo]] = relationship(
        "Combo",
        back_populates="categoria",
        foreign_keys="[Combo.categoria_combo_id]",
    )


class Receta(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """
    Ficha técnica gastronómica (escandallo estándar, sub-receta o receta dinámica).
    Maneja rendimientos, costos base calculados y precios de venta estrictamente con `Decimal`.
    """

    __tablename__ = "recetas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria_receta_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("categorias_recetas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    es_subreceta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    es_dinamica: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
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
    precio_venta_neto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    precio_venta_bruto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    iva_porcentaje: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("19.00"),
        nullable=False,
    )
    iva_incluido: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    imagen_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    preparacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    documento_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tiempo_preparacion_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    categoria: Mapped[CategoriaReceta | None] = relationship(
        "CategoriaReceta",
        back_populates="recetas",
        foreign_keys=[categoria_receta_id],
    )
    ingredientes: Mapped[list[RecetaIngrediente]] = relationship(
        "RecetaIngrediente",
        back_populates="receta",
        cascade="all, delete-orphan",
        foreign_keys="[RecetaIngrediente.receta_id]",
    )
    grupos_opciones: Mapped[list[RecetaGrupoOpcion]] = relationship(
        "RecetaGrupoOpcion",
        back_populates="receta",
        cascade="all, delete-orphan",
        order_by="RecetaGrupoOpcion.orden",
    )


class RecetaIngrediente(TenantBase, AuditTimestampsMixin):
    """
    Ingrediente fijo (`Producto` del catálogo o sub-`Receta`) del escandallo base.
    Aplica merma técnica porcentual en `Decimal(6, 2)`.
    """

    __tablename__ = "receta_ingredientes"
    __table_args__ = (
        CheckConstraint(
            "((producto_id IS NOT NULL AND subreceta_id IS NULL) OR "
            "(producto_id IS NULL AND subreceta_id IS NOT NULL))",
            name="ck_receta_ingredientes_origen_exclusivo",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receta_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recetas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
        index=True,
    )
    subreceta_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("recetas.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
        index=True,
    )
    cantidad_receta: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    porcentaje_merma: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    bodega_consumo_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("bodegas.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
    )
    notas: Mapped[str | None] = mapped_column(String(255), nullable=True)

    receta: Mapped[Receta] = relationship(
        "Receta",
        back_populates="ingredientes",
        foreign_keys=[receta_id],
    )
    subreceta: Mapped[Receta | None] = relationship(
        "Receta",
        foreign_keys=[subreceta_id],
    )


class GrupoOpciones(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """
    Biblioteca de grupos de modificadores u opciones intercambiables para recetas y combos
    (ej. Elección de Guarnición, Término de la Carne, Tamaño de Bebida).
    """

    __tablename__ = "grupos_opciones"
    __table_args__ = (
        CheckConstraint(
            "seleccion_minima >= 0 AND seleccion_maxima >= seleccion_minima",
            name="ck_grupos_opciones_rango_seleccion",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    seleccion_minima: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    seleccion_maxima: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    permite_repetir: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Compatibilidad con contratos y tests legacy que referencian min/max_selecciones
    min_selecciones = synonym("seleccion_minima")
    max_selecciones = synonym("seleccion_maxima")

    items: Mapped[list[GrupoOpcionesItem]] = relationship(
        "GrupoOpcionesItem",
        back_populates="grupo",
        cascade="all, delete-orphan",
        order_by="GrupoOpcionesItem.orden",
    )
    recetas_asociadas: Mapped[list[RecetaGrupoOpcion]] = relationship(
        "RecetaGrupoOpcion",
        back_populates="grupo",
        cascade="all, delete-orphan",
    )
    combos_asociados: Mapped[list[ComboGrupoOpcion]] = relationship(
        "ComboGrupoOpcion",
        back_populates="grupo",
        cascade="all, delete-orphan",
    )


class GrupoOpcionesItem(TenantBase, AuditTimestampsMixin):
    """
    Opción específica seleccionable dentro de un `GrupoOpciones` con recargo en `Decimal(14, 2)`.
    Polimórfica: referencia a un `Producto` del catálogo o a una `Receta` (sub-receta/plato).
    """

    __tablename__ = "grupo_opciones_items"
    __table_args__ = (
        CheckConstraint(
            "((producto_id IS NOT NULL AND receta_id IS NULL) OR "
            "(producto_id IS NULL AND receta_id IS NOT NULL))",
            name="ck_grupo_opciones_items_origen_exclusivo",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grupo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("grupos_opciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
        index=True,
    )
    receta_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("recetas.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
        index=True,
    )
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("1.0000"),
        nullable=False,
    )
    es_opcion_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recargo_precio: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    grupo: Mapped[GrupoOpciones] = relationship(
        "GrupoOpciones",
        back_populates="items",
    )
    receta: Mapped[Receta | None] = relationship(
        "Receta",
        foreign_keys=[receta_id],
    )


class RecetaGrupoOpcion(TenantBase, AuditTimestampsMixin):
    """
    Asociación Many-to-Many entre `Receta` y `GrupoOpciones` que define recetas dinámicas.
    """

    __tablename__ = "receta_grupos_opciones"
    __table_args__ = (
        UniqueConstraint("receta_id", "grupo_id", name="uq_receta_grupos_opciones_receta_grupo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receta_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recetas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grupo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("grupos_opciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    es_requerido: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    receta: Mapped[Receta] = relationship(
        "Receta",
        back_populates="grupos_opciones",
    )
    grupo: Mapped[GrupoOpciones] = relationship(
        "GrupoOpciones",
        back_populates="recetas_asociadas",
    )


class Combo(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """
    Paquete gastronómico o promoción comercial (estático o dinámico con grupos de opciones).
    """

    __tablename__ = "combos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria_combo_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("categorias_combos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    es_dinamico: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    precio_venta_neto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    precio_venta_bruto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    iva_porcentaje: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("19.00"),
        nullable=False,
    )
    iva_incluido: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    costo_total_calculado: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    imagen_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    categoria: Mapped[CategoriaCombo | None] = relationship(
        "CategoriaCombo",
        back_populates="combos",
        foreign_keys=[categoria_combo_id],
    )
    items: Mapped[list[ComboItem]] = relationship(
        "ComboItem",
        back_populates="combo",
        cascade="all, delete-orphan",
    )
    grupos_opciones: Mapped[list[ComboGrupoOpcion]] = relationship(
        "ComboGrupoOpcion",
        back_populates="combo",
        cascade="all, delete-orphan",
        order_by="ComboGrupoOpcion.orden",
    )


class ComboItem(TenantBase, AuditTimestampsMixin):
    """
    Componente fijo de un `Combo`.
    Polimórfico: referencia a un `Producto` o a una `Receta`.
    """

    __tablename__ = "combo_items"
    __table_args__ = (
        CheckConstraint(
            "((producto_id IS NOT NULL AND receta_id IS NULL) OR "
            "(producto_id IS NULL AND receta_id IS NOT NULL))",
            name="ck_combo_items_origen_exclusivo",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    combo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("combos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("productos.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
        index=True,
    )
    receta_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("recetas.id", ondelete="RESTRICT"),
        default=None,
        nullable=True,
        index=True,
    )
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("1.0000"),
        nullable=False,
    )

    combo: Mapped[Combo] = relationship(
        "Combo",
        back_populates="items",
    )
    receta: Mapped[Receta | None] = relationship(
        "Receta",
        foreign_keys=[receta_id],
    )


class ComboGrupoOpcion(TenantBase, AuditTimestampsMixin):
    """
    Asociación Many-to-Many entre `Combo` y `GrupoOpciones` que define combos dinámicos.
    """

    __tablename__ = "combo_grupos_opciones"
    __table_args__ = (
        UniqueConstraint("combo_id", "grupo_id", name="uq_combo_grupos_opciones_combo_grupo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    combo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("combos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grupo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("grupos_opciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    es_requerido: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    combo: Mapped[Combo] = relationship(
        "Combo",
        back_populates="grupos_opciones",
    )
    grupo: Mapped[GrupoOpciones] = relationship(
        "GrupoOpciones",
        back_populates="combos_asociados",
    )
