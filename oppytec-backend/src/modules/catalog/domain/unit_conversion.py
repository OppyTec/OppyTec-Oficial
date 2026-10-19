"""
oppytec-backend/src/modules/catalog/domain/unit_conversion.py
Matemática pura de las 3 capas de unidades (compra -> almacén -> receta) y costo promedio
ponderado (PPP) en `Decimal`. Prohibido `float` e imports de infraestructura.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from src.core.exceptions import ProperNounImmutabilityError

QTY_QUANT = Decimal("0.00000001")
COST_QUANT = Decimal("0.0001")
ZERO = Decimal(0)

IMMUTABLE_PROPER_NOUN_TABLES: frozenset[str] = frozenset({"marcas", "proveedores"})


@dataclass(frozen=True)
class UnitLayers:
    """Factores de conversión de las 3 capas de unidades de un producto."""

    factor_compra_a_almacen: Decimal
    factor_almacen_a_receta: Decimal

    def __post_init__(self) -> None:
        if self.factor_compra_a_almacen <= ZERO or self.factor_almacen_a_receta <= ZERO:
            raise ValueError("unit conversion factors must be strictly positive")


def purchase_to_storage(qty_purchase: Decimal, layers: UnitLayers) -> Decimal:
    """Convierte cantidad de unidad de compra a unidad de almacén."""
    return (qty_purchase * layers.factor_compra_a_almacen).quantize(QTY_QUANT, ROUND_HALF_UP)


def storage_to_recipe(qty_storage: Decimal, layers: UnitLayers) -> Decimal:
    """Convierte cantidad de unidad de almacén a unidad de receta."""
    return (qty_storage * layers.factor_almacen_a_receta).quantize(QTY_QUANT, ROUND_HALF_UP)


def recipe_to_storage(qty_recipe: Decimal, layers: UnitLayers) -> Decimal:
    """Convierte cantidad de unidad de receta a unidad de almacén."""
    return (qty_recipe / layers.factor_almacen_a_receta).quantize(QTY_QUANT, ROUND_HALF_UP)


def purchase_to_recipe(qty_purchase: Decimal, layers: UnitLayers) -> Decimal:
    """Convierte directamente de unidad de compra a unidad de receta."""
    return (
        qty_purchase * layers.factor_compra_a_almacen * layers.factor_almacen_a_receta
    ).quantize(QTY_QUANT, ROUND_HALF_UP)


def storage_cost_from_purchase(purchase_net_cost: Decimal, layers: UnitLayers) -> Decimal:
    """Costo por unidad de almacén a partir del costo neto por unidad de compra."""
    return (purchase_net_cost / layers.factor_compra_a_almacen).quantize(COST_QUANT, ROUND_HALF_UP)


def recipe_unit_cost(storage_cost: Decimal, layers: UnitLayers) -> Decimal:
    """Costo por unidad de receta a partir del costo por unidad de almacén."""
    return (storage_cost / layers.factor_almacen_a_receta).quantize(COST_QUANT, ROUND_HALF_UP)


def weighted_average_cost(
    current_qty: Decimal,
    current_avg_cost: Decimal,
    incoming_qty: Decimal,
    incoming_unit_cost: Decimal,
) -> Decimal:
    """
    Costo Promedio Ponderado (PPP) tras una entrada:
    (stock * costo_actual + entrada * costo_entrada) / (stock + entrada).
    """
    if incoming_qty < ZERO:
        raise ValueError("incoming quantity must be non-negative")
    base_qty = max(current_qty, ZERO)
    total_qty = base_qty + incoming_qty
    if total_qty == ZERO:
        return current_avg_cost
    total_value = base_qty * current_avg_cost + incoming_qty * incoming_unit_cost
    return (total_value / total_qty).quantize(COST_QUANT, ROUND_HALF_UP)


def assert_proper_noun_not_mutated(table: str, old_name: str, new_name: str) -> None:
    """Las marcas y proveedores (ej. 'Pollo King') jamás se traducen ni se alteran por i18n."""
    if table in IMMUTABLE_PROPER_NOUN_TABLES and old_name != new_name:
        raise ProperNounImmutabilityError(
            f"Proper noun '{old_name}' in '{table}' is immutable by translation",
            context={"table": table},
        )
