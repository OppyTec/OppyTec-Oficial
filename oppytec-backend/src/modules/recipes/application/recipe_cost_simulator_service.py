"""
oppytec-backend/src/modules/recipes/application/recipe_cost_simulator_service.py
Servicio de Simulación Dinámica de Costos y Márgenes para Recetas con Opciones Personalizadas.
Permite calcular el impacto financiero de configuraciones específicas antes de la emisión de una comanda o venta POS.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

from src.modules.recipes.application.recipe_service import RecipeService
from src.modules.recipes.domain.exceptions import (
    InvalidOptionSelectionError,
    RecipeNotFoundError,
)
from src.modules.recipes.domain.value_objects import (
    HUNDRED,
    ONE,
    PRECISION_COST,
    PRECISION_MONEY,
    PRECISION_PERCENTAGE,
    ZERO,
)


@dataclass(frozen=True)
class SimulatedOptionItemDetail:
    """Detalle de una opción seleccionada en la simulación."""

    item_id: int
    grupo_id: int
    grupo_nombre: str
    nombre: str
    cantidad: Decimal
    costo_unitario: Decimal
    costo_total: Decimal
    recargo_precio: Decimal


@dataclass(frozen=True)
class SimulationResult:
    """Resultado completo de la simulación de costo dinámico."""

    recipe_id: int
    recipe_nombre: str
    base_fixed_cost: Decimal
    options_cost: Decimal
    total_cost: Decimal
    portion_cost: Decimal
    total_surcharge: Decimal
    effective_net_price: Decimal
    effective_gross_price: Decimal
    margin_amount: Decimal
    margin_pct: Decimal
    food_cost_pct: Decimal
    selected_options: tuple[SimulatedOptionItemDetail, ...] = field(default_factory=tuple)


class RecipeCostSimulatorService:
    """
    Simulador de costos para recetas y escandallos dinámicos.
    Verifica las reglas de cardinalidad del grupo y calcula el impacto en Food Cost % y margen.
    """

    def __init__(self, recipe_service: RecipeService) -> None:
        self.recipe_service = recipe_service

    def simulate_cost(
        self,
        recipe_id: int,
        selected_option_item_ids: Sequence[int],
        tenant_id: str = "default",
    ) -> SimulationResult:
        """
        Simula el costo de una receta ante una selección concreta de ítems de opciones.
        Valida restricciones de mínimo, máximo y repetición.
        """
        recipe = self.recipe_service.get_recipe(recipe_id, tenant_id)

        # Mapear los grupos de opciones de la receta
        group_map: dict[int, Any] = {}
        item_to_group: dict[int, tuple[int, Any, Any]] = {}  # item_id -> (group_id, group, item)

        for link in recipe.grupos_opciones:
            grp = self.recipe_service.option_group_service.get_option_group(link.grupo_id, tenant_id)
            group_map[grp.id] = (link, grp)
            for it in grp.items:
                if it.id is not None:
                    item_to_group[it.id] = (grp.id, grp, it)

        # Conteo de selecciones por grupo y por ítem
        group_counts: Counter[int] = Counter()
        item_counts: Counter[int] = Counter()
        simulated_options: list[SimulatedOptionItemDetail] = []
        options_total_cost = Decimal("0.00")
        total_surcharge = Decimal("0.00")

        for item_id in selected_option_item_ids:
            if item_id not in item_to_group:
                raise InvalidOptionSelectionError(
                    f"Selected option item ID {item_id} does not belong to any option group of Recipe {recipe_id}.",
                    context={"item_id": item_id, "recipe_id": recipe_id},
                )

            grp_id, grp, it = item_to_group[item_id]
            group_counts[grp_id] += 1
            item_counts[item_id] += 1

            # Verificar si permite repetir
            if item_counts[item_id] > 1 and not grp.permite_repetir:
                raise InvalidOptionSelectionError(
                    f"Option item '{it.nombre or item_id}' cannot be selected multiple times in group '{grp.nombre}'.",
                    context={"item_id": item_id, "group_id": grp_id},
                )

            # Calcular costo del ítem
            if it.producto_id is not None:
                u_cost = self.recipe_service.get_ingredient_cost(it.producto_id)
            elif it.receta_id is not None:
                sub_r = self.recipe_service.get_recipe(it.receta_id, tenant_id)
                u_cost = sub_r.costo_porcion
            else:
                u_cost = it.costo_referencial

            it_cost = (it.cantidad * u_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
            options_total_cost += it_cost
            total_surcharge += it.recargo_precio

            simulated_options.append(
                SimulatedOptionItemDetail(
                    item_id=item_id,
                    grupo_id=grp_id,
                    grupo_nombre=grp.nombre,
                    nombre=it.nombre or f"Item #{item_id}",
                    cantidad=it.cantidad,
                    costo_unitario=u_cost,
                    costo_total=it_cost,
                    recargo_precio=it.recargo_precio,
                )
            )

        # Validar cardinalidad de cada grupo asociado a la receta
        for link, grp in group_map.values():
            count = group_counts[grp.id]
            # Si el grupo es requerido o tiene selección mínima obligatoria
            if link.es_requerido and count < grp.seleccion_minima:
                raise InvalidOptionSelectionError(
                    f"Group '{grp.nombre}' requires at least {grp.seleccion_minima} selection(s), got {count}.",
                    context={"group_id": grp.id, "min": grp.seleccion_minima, "actual": count},
                )
            if count > grp.seleccion_maxima:
                raise InvalidOptionSelectionError(
                    f"Group '{grp.nombre}' allows at most {grp.seleccion_maxima} selection(s), got {count}.",
                    context={"group_id": grp.id, "max": grp.seleccion_maxima, "actual": count},
                )

        # Costo fijo de ingredientes del lote
        fixed_cost = sum(
            (ing.costo_total for ing in recipe.ingredientes_fijos),
            Decimal("0.00"),
        )

        total_lot_cost = (fixed_cost + options_total_cost).quantize(PRECISION_COST, ROUND_HALF_UP)
        yield_portions = recipe.porciones_rendimiento
        portion_cost = (total_lot_cost / yield_portions).quantize(PRECISION_COST, ROUND_HALF_UP)

        effective_net = (recipe.precio_venta_neto + total_surcharge).quantize(PRECISION_MONEY, ROUND_HALF_UP)
        tax_factor = ONE + (recipe.iva_porcentaje / HUNDRED)
        effective_gross = (effective_net * tax_factor).quantize(PRECISION_MONEY, ROUND_HALF_UP)

        margin_amount = (effective_net - portion_cost).quantize(PRECISION_MONEY, ROUND_HALF_UP)
        margin_pct = (
            ((effective_net - portion_cost) / effective_net * HUNDRED).quantize(
                PRECISION_PERCENTAGE, ROUND_HALF_UP
            )
            if effective_net > ZERO
            else ZERO
        )
        food_cost_pct = (
            (portion_cost / effective_net * HUNDRED).quantize(
                PRECISION_PERCENTAGE, ROUND_HALF_UP
            )
            if effective_net > ZERO
            else ZERO
        )

        return SimulationResult(
            recipe_id=recipe.id,
            recipe_nombre=recipe.nombre,
            base_fixed_cost=fixed_cost,
            options_cost=options_total_cost,
            total_cost=total_lot_cost,
            portion_cost=portion_cost,
            total_surcharge=total_surcharge,
            effective_net_price=effective_net,
            effective_gross_price=effective_gross,
            margin_amount=margin_amount,
            margin_pct=margin_pct,
            food_cost_pct=food_cost_pct,
            selected_options=tuple(simulated_options),
        )
