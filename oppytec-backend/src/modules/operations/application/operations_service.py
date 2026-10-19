"""
oppytec-backend/src/modules/operations/application/operations_service.py
Ventas/consumo: explota la venta y descarga el Kardex en orden canónico de locks.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from src.modules.inventory.application.inventory_service import InventoryService, KardexEntry
from src.modules.inventory.domain.kardex_math import canonical_lock_order
from src.modules.operations.domain.pos_consumption import (
    SaleItem,
    buffet_cost_per_pax,
    explode_sale_consumption,
)


class OperationsService:
    """Procesa ventas del POS descontando insumos de la bodega."""

    def __init__(self, inventory: InventoryService) -> None:
        self._inventory = inventory

    def process_sale(
        self,
        *,
        items: Sequence[SaleItem],
        recipe_ingredients: Mapping[int, Mapping[int, Decimal]],
        ingredient_costs: Mapping[int, Decimal],
        bodega_id: int,
        actor_user_id: int,
    ) -> list[KardexEntry]:
        """Descarga insumos tomando locks en orden `id ASC`."""
        consumption = explode_sale_consumption(items, recipe_ingredients)
        entries: list[KardexEntry] = []
        for ing in canonical_lock_order(consumption):
            entries.append(
                self._inventory.register_movement(
                    producto_id=ing,
                    bodega_id=bodega_id,
                    movement_type="CONSUMO",
                    quantity=consumption[ing],
                    unit_cost=ingredient_costs.get(ing, Decimal(0)),
                    actor_user_id=actor_user_id,
                )
            )
        return entries

    @staticmethod
    def buffet_pax_cost(total_cost: Decimal, pax: int, leftover_value: Decimal = Decimal(0)) -> Decimal:
        """Costo por pax de un servicio buffet."""
        return buffet_cost_per_pax(total_cost, pax, leftover_value)
