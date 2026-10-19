"""
oppytec-backend/src/modules/recipes/domain/escandallo_calculator.py
Costeo recursivo de escandallos en `Decimal`: ingredientes, sub-recetas, combos, grupos de opciones,
Food Cost % y margen. Detecta ciclos. Prohibido `float`.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

COST_QUANT = Decimal("0.0001")
PCT_QUANT = Decimal("0.01")
ZERO = Decimal(0)
HUNDRED = Decimal(100)


class RecipeCycleError(ValueError):
    """Una receta se referencia a sí misma directa o indirectamente."""


@dataclass(frozen=True)
class RecipeLine:
    """Línea de un escandallo: ingrediente (`ingredient_id`) o sub-receta (`sub_recipe_id`)."""

    quantity: Decimal
    ingredient_id: int | None = None
    sub_recipe_id: int | None = None
    waste_pct: Decimal = ZERO


@dataclass(frozen=True)
class OptionGroup:
    """Grupo de opciones: se cuesta la opción elegida (cantidad de selecciones por recipe_id)."""

    options: Mapping[int, Decimal]
    selected_recipe_ids: Sequence[int] = field(default_factory=tuple)


@dataclass(frozen=True)
class Recipe:
    """Escandallo con yield (porciones), líneas y grupos de opciones."""

    recipe_id: int
    lines: Sequence[RecipeLine]
    yield_portions: Decimal = Decimal(1)
    option_groups: Sequence[OptionGroup] = field(default_factory=tuple)


def _q(value: Decimal) -> Decimal:
    return value.quantize(COST_QUANT, ROUND_HALF_UP)


def recipe_total_cost(
    recipe_id: int,
    recipes: Mapping[int, Recipe],
    ingredient_costs: Mapping[int, Decimal],
    _stack: tuple[int, ...] = (),
) -> Decimal:
    """Costo total del lote de la receta (antes de dividir por yield), recursivo."""
    if recipe_id in _stack:
        raise RecipeCycleError(f"cycle detected: {(*_stack, recipe_id)}")
    recipe = recipes[recipe_id]
    stack = (*_stack, recipe_id)
    total = ZERO
    for line in recipe.lines:
        if line.ingredient_id is not None:
            unit = ingredient_costs[line.ingredient_id]
        elif line.sub_recipe_id is not None:
            unit = recipe_portion_cost(line.sub_recipe_id, recipes, ingredient_costs, stack)
        else:
            raise ValueError("line requires ingredient_id or sub_recipe_id")
        gross = line.quantity * (Decimal(1) + line.waste_pct / HUNDRED)
        total += unit * gross
    for group in recipe.option_groups:
        for sel in group.selected_recipe_ids:
            if sel not in group.options:
                raise ValueError("selected option not in group")
            total += recipe_portion_cost(sel, recipes, ingredient_costs, stack) * group.options[sel]
    return _q(total)


def recipe_portion_cost(
    recipe_id: int,
    recipes: Mapping[int, Recipe],
    ingredient_costs: Mapping[int, Decimal],
    _stack: tuple[int, ...] = (),
) -> Decimal:
    """Costo por porción = costo total / yield."""
    recipe = recipes[recipe_id]
    if recipe.yield_portions <= ZERO:
        raise ValueError("yield must be positive")
    return _q(recipe_total_cost(recipe_id, recipes, ingredient_costs, _stack) / recipe.yield_portions)


def combo_cost(
    component_recipe_ids: Sequence[int],
    recipes: Mapping[int, Recipe],
    ingredient_costs: Mapping[int, Decimal],
) -> Decimal:
    """Un combo suma el costo por porción de cada componente."""
    return _q(sum((recipe_portion_cost(r, recipes, ingredient_costs) for r in component_recipe_ids), ZERO))


def food_cost_pct(cost: Decimal, net_price: Decimal) -> Decimal:
    """Food Cost % = costo / precio neto * 100."""
    if net_price <= ZERO:
        raise ValueError("net price must be positive")
    return (cost / net_price * HUNDRED).quantize(PCT_QUANT, ROUND_HALF_UP)


def margin_amount(cost: Decimal, net_price: Decimal) -> Decimal:
    """Margen bruto absoluto."""
    return _q(net_price - cost)


def margin_pct(cost: Decimal, net_price: Decimal) -> Decimal:
    """Margen bruto % = (precio - costo) / precio * 100."""
    if net_price <= ZERO:
        raise ValueError("net price must be positive")
    return ((net_price - cost) / net_price * HUNDRED).quantize(PCT_QUANT, ROUND_HALF_UP)
