"""
oppytec-backend/src/modules/recipes/domain/entities.py
Entidades de dominio puras (Clean Architecture & DDD) para Recetas, Escandallos,
Combos Gastronómicos y Grupos de Opciones Polimórficos.
Totalmente desacopladas de infraestructura, inmutables (frozen=True) y con precisión Decimal estricta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

from src.modules.recipes.domain.exceptions import (
    InvalidOptionSelectionError,
    InvalidQuantityError,
    PolymorphicReferenceError,
)
from src.modules.recipes.domain.value_objects import (
    HUNDRED,
    ONE,
    PRECISION_COST,
    PRECISION_MONEY,
    PRECISION_PERCENTAGE,
    PRECISION_QUANTITY,
    ZERO,
    IngredientQuantity,
    OptionSelectionRule,
    ServingYield,
    _ensure_strict_decimal,
)


@dataclass(frozen=True)
class RecetaIngrediente:
    """
    Ingrediente fijo que compone el escandallo de una receta.
    Polimórfico: debe referenciar exactamente a un `producto_id` de inventario
    O a una `subreceta_id` gastronómica (XOR estricto).
    """

    cantidad: IngredientQuantity
    producto_id: int | None = None
    subreceta_id: int | None = None
    id: int | None = None
    receta_id: int | None = None
    bodega_consumo_id: int | None = None
    notas: str | None = None

    def __post_init__(self) -> None:
        has_prod = self.producto_id is not None
        has_sub = self.subreceta_id is not None
        if has_prod == has_sub:
            raise PolymorphicReferenceError(
                "RecetaIngrediente must reference exactly one target: either 'producto_id' "
                "or 'subreceta_id', not both nor neither."
            )
        if not isinstance(self.cantidad, IngredientQuantity):
            raise TypeError("cantidad must be an instance of IngredientQuantity.")

    @property
    def is_product(self) -> bool:
        """Indica si el ingrediente es un insumo físico de bodega."""
        return self.producto_id is not None

    @property
    def is_subrecipe(self) -> bool:
        """Indica si el ingrediente es una sub-receta intermedia elaborada."""
        return self.subreceta_id is not None

    @property
    def target_id(self) -> int:
        """ID unificado de la entidad referenciada."""
        if self.producto_id is not None:
            return self.producto_id
        if self.subreceta_id is not None:
            return self.subreceta_id
        raise PolymorphicReferenceError("No valid target ID found.")


@dataclass(frozen=True)
class GrupoOpcionesItem:
    """
    Elemento individual seleccionable dentro de un Grupo de Opciones.
    Polimórfico: puede ser un producto individual o una sub-receta/plato (XOR estricto).
    """

    producto_id: int | None = None
    receta_id: int | None = None
    cantidad: Decimal = field(default_factory=lambda: Decimal("1.0000"))
    es_opcion_default: bool = False
    recargo_precio: Decimal = field(default_factory=lambda: Decimal("0.00"))
    orden: int = 0
    id: int | None = None
    grupo_id: int | None = None
    nombre: str | None = None

    def __post_init__(self) -> None:
        has_prod = self.producto_id is not None
        has_rec = self.receta_id is not None
        if has_prod == has_rec:
            raise PolymorphicReferenceError(
                "GrupoOpcionesItem must reference exactly one target: either 'producto_id' "
                "or 'receta_id', not both nor neither."
            )

        dec_qty = _ensure_strict_decimal(self.cantidad, "cantidad")
        dec_surcharge = _ensure_strict_decimal(self.recargo_precio, "recargo_precio")

        if dec_qty <= ZERO:
            raise InvalidQuantityError(f"Option item quantity must be strictly greater than 0, got {dec_qty}.")
        if dec_surcharge < ZERO:
            raise ValueError(f"Option item surcharge cannot be negative, got {dec_surcharge}.")

        object.__setattr__(self, "cantidad", dec_qty.quantize(PRECISION_QUANTITY, ROUND_HALF_UP))
        object.__setattr__(self, "recargo_precio", dec_surcharge.quantize(PRECISION_MONEY, ROUND_HALF_UP))

    @property
    def is_product(self) -> bool:
        return self.producto_id is not None

    @property
    def is_recipe(self) -> bool:
        return self.receta_id is not None

    @property
    def target_id(self) -> int:
        if self.producto_id is not None:
            return self.producto_id
        if self.receta_id is not None:
            return self.receta_id
        raise PolymorphicReferenceError("No valid target ID found.")


@dataclass(frozen=True)
class GrupoOpciones:
    """
    Biblioteca o grupo configurable de modificadores/opciones para recetas o combos.
    """

    nombre: str
    regla: OptionSelectionRule = field(default_factory=OptionSelectionRule)
    id: int | None = None
    descripcion: str | None = None
    items: tuple[GrupoOpcionesItem, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise ValueError("GrupoOpciones name cannot be empty.")
        if not isinstance(self.regla, OptionSelectionRule):
            raise TypeError("regla must be an instance of OptionSelectionRule.")
        if not isinstance(self.items, tuple):
            object.__setattr__(self, "items", tuple(self.items))

    @property
    def default_items(self) -> tuple[GrupoOpcionesItem, ...]:
        """Obtiene las opciones marcadas como default para el cálculo del escandallo base."""
        return tuple(item for item in self.items if item.es_opcion_default)

    @property
    def has_default(self) -> bool:
        """Indica si el grupo contiene al menos una opción default configurada."""
        return len(self.default_items) > 0

    @property
    def item_count(self) -> int:
        return len(self.items)


@dataclass(frozen=True)
class RecetaGrupoOpcion:
    """
    Asociación Many-to-Many entre Receta y GrupoOpciones que habilita Recetas Dinámicas.
    """

    grupo_id: int
    orden: int = 0
    es_requerido: bool = True
    id: int | None = None
    receta_id: int | None = None
    grupo: GrupoOpciones | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.grupo_id, int) or isinstance(self.grupo_id, bool):
            raise TypeError("grupo_id must be an integer.")
        if self.grupo_id <= 0:
            raise ValueError("grupo_id must be a positive integer.")


@dataclass(frozen=True)
class Receta:
    """
    Ficha técnica gastronómica (escandallo o sub-receta) con cálculo de costos y márgenes.
    Auto-detecta si es dinámica ante la presencia de Grupos de Opciones.
    """

    codigo: str
    nombre: str
    id: int | None = None
    descripcion: str | None = None
    categoria_receta_id: int | None = None
    es_subreceta: bool = False
    es_dinamica: bool = False
    porciones_rendimiento: ServingYield = field(default_factory=ServingYield)
    ingredientes_fijos: tuple[RecetaIngrediente, ...] = field(default_factory=tuple)
    grupos_opciones: tuple[RecetaGrupoOpcion, ...] = field(default_factory=tuple)
    costo_total_calculado: Decimal = field(default_factory=lambda: Decimal("0.00"))
    precio_venta_neto: Decimal = field(default_factory=lambda: Decimal("0.00"))
    precio_venta_bruto: Decimal = field(default_factory=lambda: Decimal("0.00"))
    iva_porcentaje: Decimal = field(default_factory=lambda: Decimal("19.00"))
    iva_incluido: bool = True
    imagen_url: str | None = None
    preparacion: str | None = None
    video_url: str | None = None
    documento_url: str | None = None
    tiempo_preparacion_minutos: int | None = None

    def __post_init__(self) -> None:
        if not self.codigo or not self.codigo.strip():
            raise ValueError("Recipe 'codigo' cannot be empty.")
        if not self.nombre or not self.nombre.strip():
            raise ValueError("Recipe 'nombre' cannot be empty.")

        if not isinstance(self.porciones_rendimiento, ServingYield):
            raise TypeError("porciones_rendimiento must be an instance of ServingYield.")

        if not isinstance(self.ingredientes_fijos, tuple):
            object.__setattr__(self, "ingredientes_fijos", tuple(self.ingredientes_fijos))
        if not isinstance(self.grupos_opciones, tuple):
            object.__setattr__(self, "grupos_opciones", tuple(self.grupos_opciones))

        costo = _ensure_strict_decimal(self.costo_total_calculado, "costo_total_calculado")
        neto = _ensure_strict_decimal(self.precio_venta_neto, "precio_venta_neto")
        bruto = _ensure_strict_decimal(self.precio_venta_bruto, "precio_venta_bruto")
        iva = _ensure_strict_decimal(self.iva_porcentaje, "iva_porcentaje")

        if costo < ZERO:
            raise ValueError("Recipe costo_total_calculado cannot be negative.")
        if neto < ZERO:
            raise ValueError("Recipe precio_venta_neto cannot be negative.")
        if bruto < ZERO:
            raise ValueError("Recipe precio_venta_bruto cannot be negative.")
        if iva < ZERO:
            raise ValueError("Recipe iva_porcentaje cannot be negative.")

        # Consistencia de precios neto/bruto si uno de ellos es cero
        if neto > ZERO and bruto == ZERO:
            tax_factor = ONE + (iva / HUNDRED)
            bruto = (neto * tax_factor).quantize(PRECISION_MONEY, ROUND_HALF_UP)
        elif bruto > ZERO and neto == ZERO:
            tax_factor = ONE + (iva / HUNDRED)
            neto = (bruto / tax_factor).quantize(PRECISION_MONEY, ROUND_HALF_UP)

        object.__setattr__(self, "costo_total_calculado", costo.quantize(PRECISION_COST, ROUND_HALF_UP))
        object.__setattr__(self, "precio_venta_neto", neto.quantize(PRECISION_MONEY, ROUND_HALF_UP))
        object.__setattr__(self, "precio_venta_bruto", bruto.quantize(PRECISION_MONEY, ROUND_HALF_UP))
        object.__setattr__(self, "iva_porcentaje", iva.quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP))

        # Auto-detección de receta dinámica si contiene grupos de opciones asociados
        should_be_dynamic = bool(self.es_dinamica or len(self.grupos_opciones) > 0)
        object.__setattr__(self, "es_dinamica", should_be_dynamic)

    @property
    def subrecipe_ids(self) -> set[int]:
        """Conjunto de IDs de subrecetas directamente referenciadas en los ingredientes fijos."""
        return {
            ing.subreceta_id
            for ing in self.ingredientes_fijos
            if ing.subreceta_id is not None
        }

    @property
    def has_subrecipes(self) -> bool:
        return len(self.subrecipe_ids) > 0

    def costo_unitario_porcion(self) -> Decimal:
        """Costo calculado por porción individual."""
        return self.porciones_rendimiento.unit_cost(self.costo_total_calculado)

    def margin_amount(self) -> Decimal:
        """Margen bruto monetario por porción vendida contra el precio neto."""
        unit_cost = self.costo_unitario_porcion()
        return (self.precio_venta_neto - unit_cost).quantize(PRECISION_MONEY, ROUND_HALF_UP)

    def margin_pct(self) -> Decimal:
        """Margen bruto porcentual por porción vendida."""
        if self.precio_venta_neto <= ZERO:
            return ZERO
        unit_cost = self.costo_unitario_porcion()
        return ((self.precio_venta_neto - unit_cost) / self.precio_venta_neto * HUNDRED).quantize(
            PRECISION_PERCENTAGE, ROUND_HALF_UP
        )

    def food_cost_pct(self) -> Decimal:
        """Food Cost porcentual: costo por porción / precio neto * 100."""
        if self.precio_venta_neto <= ZERO:
            return ZERO
        unit_cost = self.costo_unitario_porcion()
        return (unit_cost / self.precio_venta_neto * HUNDRED).quantize(
            PRECISION_PERCENTAGE, ROUND_HALF_UP
        )


@dataclass(frozen=True)
class ComboItem:
    """
    Componente fijo integrante de un Combo comercial.
    Polimórfico: puede ser un producto directo o una receta (XOR estricto).
    """

    producto_id: int | None = None
    receta_id: int | None = None
    cantidad: Decimal = field(default_factory=lambda: Decimal("1.0000"))
    id: int | None = None
    combo_id: int | None = None

    def __post_init__(self) -> None:
        has_prod = self.producto_id is not None
        has_rec = self.receta_id is not None
        if has_prod == has_rec:
            raise PolymorphicReferenceError(
                "ComboItem must reference exactly one target: either 'producto_id' "
                "or 'receta_id', not both nor neither."
            )
        dec_qty = _ensure_strict_decimal(self.cantidad, "cantidad")
        if dec_qty <= ZERO:
            raise InvalidQuantityError(f"Combo item quantity must be strictly greater than 0, got {dec_qty}.")
        object.__setattr__(self, "cantidad", dec_qty.quantize(PRECISION_QUANTITY, ROUND_HALF_UP))

    @property
    def is_product(self) -> bool:
        return self.producto_id is not None

    @property
    def is_recipe(self) -> bool:
        return self.receta_id is not None

    @property
    def target_id(self) -> int:
        if self.producto_id is not None:
            return self.producto_id
        if self.receta_id is not None:
            return self.receta_id
        raise PolymorphicReferenceError("No valid target ID found.")


@dataclass(frozen=True)
class ComboGrupoOpcion:
    """
    Asociación Many-to-Many entre Combo y GrupoOpciones que habilita Combos Dinámicos.
    """

    grupo_id: int
    orden: int = 0
    es_requerido: bool = True
    id: int | None = None
    combo_id: int | None = None
    grupo: GrupoOpciones | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.grupo_id, int) or isinstance(self.grupo_id, bool):
            raise TypeError("grupo_id must be an integer.")
        if self.grupo_id <= 0:
            raise ValueError("grupo_id must be a positive integer.")


@dataclass(frozen=True)
class Combo:
    """
    Promoción o menú comercial gastronómico.
    Auto-detecta si es dinámico ante la presencia de Grupos de Opciones.
    """

    codigo: str
    nombre: str
    id: int | None = None
    descripcion: str | None = None
    categoria_combo_id: int | None = None
    es_dinamico: bool = False
    items_fijos: tuple[ComboItem, ...] = field(default_factory=tuple)
    grupos_opciones: tuple[ComboGrupoOpcion, ...] = field(default_factory=tuple)
    precio_venta_neto: Decimal = field(default_factory=lambda: Decimal("0.00"))
    precio_venta_bruto: Decimal = field(default_factory=lambda: Decimal("0.00"))
    iva_porcentaje: Decimal = field(default_factory=lambda: Decimal("19.00"))
    iva_incluido: bool = True
    costo_total_calculado: Decimal = field(default_factory=lambda: Decimal("0.00"))
    imagen_url: str | None = None

    def __post_init__(self) -> None:
        if not self.codigo or not self.codigo.strip():
            raise ValueError("Combo 'codigo' cannot be empty.")
        if not self.nombre or not self.nombre.strip():
            raise ValueError("Combo 'nombre' cannot be empty.")

        if not isinstance(self.items_fijos, tuple):
            object.__setattr__(self, "items_fijos", tuple(self.items_fijos))
        if not isinstance(self.grupos_opciones, tuple):
            object.__setattr__(self, "grupos_opciones", tuple(self.grupos_opciones))

        costo = _ensure_strict_decimal(self.costo_total_calculado, "costo_total_calculado")
        neto = _ensure_strict_decimal(self.precio_venta_neto, "precio_venta_neto")
        bruto = _ensure_strict_decimal(self.precio_venta_bruto, "precio_venta_bruto")
        iva = _ensure_strict_decimal(self.iva_porcentaje, "iva_porcentaje")

        if costo < ZERO:
            raise ValueError("Combo costo_total_calculado cannot be negative.")
        if neto < ZERO:
            raise ValueError("Combo precio_venta_neto cannot be negative.")
        if bruto < ZERO:
            raise ValueError("Combo precio_venta_bruto cannot be negative.")
        if iva < ZERO:
            raise ValueError("Combo iva_porcentaje cannot be negative.")

        if neto > ZERO and bruto == ZERO:
            tax_factor = ONE + (iva / HUNDRED)
            bruto = (neto * tax_factor).quantize(PRECISION_MONEY, ROUND_HALF_UP)
        elif bruto > ZERO and neto == ZERO:
            tax_factor = ONE + (iva / HUNDRED)
            neto = (bruto / tax_factor).quantize(PRECISION_MONEY, ROUND_HALF_UP)

        object.__setattr__(self, "costo_total_calculado", costo.quantize(PRECISION_COST, ROUND_HALF_UP))
        object.__setattr__(self, "precio_venta_neto", neto.quantize(PRECISION_MONEY, ROUND_HALF_UP))
        object.__setattr__(self, "precio_venta_bruto", bruto.quantize(PRECISION_MONEY, ROUND_HALF_UP))
        object.__setattr__(self, "iva_porcentaje", iva.quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP))

        should_be_dynamic = bool(self.es_dinamico or len(self.grupos_opciones) > 0)
        object.__setattr__(self, "es_dinamico", should_be_dynamic)

    def margin_amount(self) -> Decimal:
        """Margen bruto monetario total del combo."""
        return (self.precio_venta_neto - self.costo_total_calculado).quantize(PRECISION_MONEY, ROUND_HALF_UP)

    def margin_pct(self) -> Decimal:
        """Margen bruto porcentual del combo."""
        if self.precio_venta_neto <= ZERO:
            return ZERO
        return (
            (self.precio_venta_neto - self.costo_total_calculado) / self.precio_venta_neto * HUNDRED
        ).quantize(PRECISION_PERCENTAGE, ROUND_HALF_UP)

    def food_cost_pct(self) -> Decimal:
        """Food Cost porcentual del combo."""
        if self.precio_venta_neto <= ZERO:
            return ZERO
        return (self.costo_total_calculado / self.precio_venta_neto * HUNDRED).quantize(
            PRECISION_PERCENTAGE, ROUND_HALF_UP
        )


__all__ = [
    "Combo",
    "ComboGrupoOpcion",
    "ComboItem",
    "GrupoOpciones",
    "GrupoOpcionesItem",
    "Receta",
    "RecetaGrupoOpcion",
    "RecetaIngrediente",
]
