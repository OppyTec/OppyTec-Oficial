"""
oppytec-backend/src/modules/operations/domain/pos_consumption.py
Explosión de insumos por venta (POS) y costo por pax de buffet, solo `Decimal`.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal(0)


@dataclass(frozen=True)
class SaleItem:
    """Ítem vendido: receta y cantidad de porciones."""

    recipe_id: int
    portions: Decimal


def explode_sale_consumption(
    items: Sequence[SaleItem],
    recipe_ingredients: Mapping[int, Mapping[int, Decimal]],
) -> dict[int, Decimal]:
    """
    Explota cada venta a consumo por insumo. `recipe_ingredients[recipe_id][ingredient_id]` es la
    cantidad (ya aplanada, por porción) de insumo consumida.
    """
    totals: dict[int, Decimal] = {}
    for item in items:
        if item.portions <= ZERO:
            raise ValueError("portions must be positive")
        for ing, qty in recipe_ingredients[item.recipe_id].items():
            totals[ing] = totals.get(ing, ZERO) + qty * item.portions
    return totals


def buffet_cost_per_pax(total_buffet_cost: Decimal, pax: int, leftover_value: Decimal = ZERO) -> Decimal:
    """Costo por pax = (costo de producción - valor de sobrante reutilizable) / pax."""
    if pax <= 0:
        raise ValueError("pax must be positive")
    return ((total_buffet_cost - leftover_value) / Decimal(pax)).quantize(Decimal("0.01"), ROUND_HALF_UP)
