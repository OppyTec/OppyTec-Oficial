"""
oppytec-backend/src/modules/inventory/application/inventory_service.py
Servicio de Kardex por bodega: movimientos atómicos con saldo resultante y orden canónico de locks.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.kardex_math import apply_movement, canonical_lock_order


@dataclass(frozen=True)
class KardexEntry:
    """Movimiento append-only del Kardex."""

    producto_id: int
    bodega_id: int
    movement_type: str
    quantity: Decimal
    resulting_balance: Decimal
    unit_cost: Decimal
    actor_user_id: int


class InventoryService:
    """Kardex en memoria (contrato de aplicación); persistencia vía infraestructura."""

    def __init__(self) -> None:
        self._balances: dict[tuple[int, int], Decimal] = {}
        self._ledger: list[KardexEntry] = []

    def balance(self, producto_id: int, bodega_id: int) -> Decimal:
        """Saldo actual del producto en la bodega."""
        return self._balances.get((producto_id, bodega_id), Decimal(0))

    @staticmethod
    def lock_order(producto_ids: Iterable[int]) -> list[int]:
        """Orden en que deben bloquearse las filas (`ORDER BY id ASC FOR UPDATE`)."""
        return canonical_lock_order(producto_ids)

    def register_movement(
        self,
        *,
        producto_id: int,
        bodega_id: int,
        movement_type: str,
        quantity: Decimal,
        unit_cost: Decimal,
        actor_user_id: int,
    ) -> KardexEntry:
        """Registra un movimiento y actualiza el saldo atómicamente."""
        new_balance = apply_movement(self.balance(producto_id, bodega_id), movement_type, quantity)
        entry = KardexEntry(
            producto_id, bodega_id, movement_type, quantity, new_balance, unit_cost, actor_user_id
        )
        self._balances[(producto_id, bodega_id)] = new_balance
        self._ledger.append(entry)
        return entry

    def ledger(self) -> tuple[KardexEntry, ...]:
        """Libro mayor inmutable."""
        return tuple(self._ledger)
