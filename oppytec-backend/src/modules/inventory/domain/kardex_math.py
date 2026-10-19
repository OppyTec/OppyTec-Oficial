"""
oppytec-backend/src/modules/inventory/domain/kardex_math.py
Matemática pura del Kardex: orden canónico de locks (ORDER BY id ASC FOR UPDATE), saldo atómico,
FEFO y umbral de aprobación de mermas. Solo `Decimal`.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.exceptions import InsufficientStockError

ZERO = Decimal(0)
ENTRY_MOVEMENTS: frozenset[str] = frozenset({"ENTRADA", "COMPRA", "AJUSTE_POSITIVO", "TRASPASO_IN"})
EXIT_MOVEMENTS: frozenset[str] = frozenset(
    {"SALIDA", "CONSUMO", "MERMA", "AJUSTE_NEGATIVO", "TRASPASO_OUT"}
)


def canonical_lock_order(ids: Iterable[int]) -> list[int]:
    """Orden determinista `ORDER BY id ASC` (sin duplicados) para evitar deadlocks en FOR UPDATE."""
    return sorted(set(ids))


def apply_movement(balance: Decimal, movement_type: str, quantity: Decimal) -> Decimal:
    """Calcula el saldo resultante; las salidas no pueden dejar saldo negativo."""
    if quantity <= ZERO:
        raise ValueError("movement quantity must be strictly positive")
    if movement_type in ENTRY_MOVEMENTS:
        return balance + quantity
    if movement_type in EXIT_MOVEMENTS:
        result = balance - quantity
        if result < ZERO:
            raise InsufficientStockError(
                "Insufficient stock for movement",
                context={"movement": movement_type},
            )
        return result
    raise ValueError(f"unknown movement type: {movement_type}")


@dataclass(frozen=True)
class StockLot:
    """Lote con vencimiento para política FEFO."""

    lot_id: int
    quantity: Decimal
    expires_on: date | None


@dataclass(frozen=True)
class LotAllocation:
    """Cantidad tomada de un lote."""

    lot_id: int
    quantity: Decimal


def fefo_allocate(lots: Sequence[StockLot], required: Decimal) -> list[LotAllocation]:
    """First-Expired-First-Out: consume primero los lotes que vencen antes (sin fecha al final)."""
    if required <= ZERO:
        raise ValueError("required quantity must be strictly positive")
    ordered = sorted(
        (lot for lot in lots if lot.quantity > ZERO),
        key=lambda lot: (lot.expires_on is None, lot.expires_on or date.max, lot.lot_id),
    )
    remaining = required
    out: list[LotAllocation] = []
    for lot in ordered:
        if remaining <= ZERO:
            break
        take = min(lot.quantity, remaining)
        out.append(LotAllocation(lot.lot_id, take))
        remaining -= take
    if remaining > ZERO:
        raise InsufficientStockError("Insufficient lots for FEFO allocation")
    return out


def waste_requires_approval(total_cost: Decimal, threshold: Decimal) -> bool:
    """Una merma cuyo costo total supera estrictamente el umbral exige aprobación."""
    return total_cost > threshold


def waste_total_cost(quantity: Decimal, unit_cost: Decimal) -> Decimal:
    """Valoración financiera de una merma."""
    return (quantity * unit_cost).quantize(Decimal("0.01"))
