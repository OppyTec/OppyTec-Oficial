"""
oppytec-backend/src/modules/recipes/application/recipe_costing_service.py
Orquesta el costeo de escandallos con costos vigentes de insumos y reporta Food Cost % y margen.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.modules.recipes.domain.escandallo_calculator import (
    Recipe,
    food_cost_pct,
    margin_amount,
    margin_pct,
    recipe_portion_cost,
)


@dataclass(frozen=True)
class CostingReport:
    """Resultado de costeo de una receta frente a su precio neto de venta."""

    recipe_id: int
    portion_cost: Decimal
    net_price: Decimal
    food_cost_pct: Decimal
    margin_amount: Decimal
    margin_pct: Decimal


class RecipeCostingService:
    """Mantiene el set de recetas y costos de insumos, y calcula reportes de costeo."""

    def __init__(self) -> None:
        self._recipes: dict[int, Recipe] = {}
        self._ingredient_costs: dict[int, Decimal] = {}

    def upsert_recipe(self, recipe: Recipe) -> None:
        """Registra o reemplaza una receta."""
        self._recipes[recipe.recipe_id] = recipe

    def set_ingredient_cost(self, ingredient_id: int, unit_cost: Decimal) -> None:
        """Actualiza el costo por unidad de receta de un insumo (p. ej. tras un PPP)."""
        self._ingredient_costs[ingredient_id] = unit_cost

    def cost_report(self, recipe_id: int, net_price: Decimal) -> CostingReport:
        """Calcula costo por porción, Food Cost % y margen."""
        cost = recipe_portion_cost(recipe_id, self._recipes, self._ingredient_costs)
        return CostingReport(
            recipe_id,
            cost,
            net_price,
            food_cost_pct(cost, net_price),
            margin_amount(cost, net_price),
            margin_pct(cost, net_price),
        )
