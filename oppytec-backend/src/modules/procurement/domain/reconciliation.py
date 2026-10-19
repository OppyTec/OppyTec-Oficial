"""
oppytec-backend/src/modules/procurement/domain/reconciliation.py
Conciliación de 3 vías (Orden de Compra vs Recepción vs Factura) en `Decimal`.
El nombre del proveedor es un nombre propio inmutable (ej. "Pollo King").
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from src.core.exceptions import ProperNounImmutabilityError

ZERO = Decimal(0)


class MatchStatus(StrEnum):
    """Resultado de la conciliación."""

    MATCHED = "MATCHED"
    PARTIAL_RECEIPT = "PARTIAL_RECEIPT"
    OVER_RECEIPT = "OVER_RECEIPT"
    PRICE_MISMATCH = "PRICE_MISMATCH"
    INVOICE_MISMATCH = "INVOICE_MISMATCH"


@dataclass(frozen=True)
class DocLine:
    """Línea de documento: cantidad y costo unitario neto."""

    producto_id: int
    quantity: Decimal
    unit_cost: Decimal


@dataclass(frozen=True)
class ReconciliationResult:
    """Estado y diferencias por producto."""

    status: MatchStatus
    quantity_diffs: Mapping[int, Decimal]
    invoice_total_diff: Decimal


def _qty(lines: Sequence[DocLine]) -> dict[int, Decimal]:
    out: dict[int, Decimal] = {}
    for ln in lines:
        out[ln.producto_id] = out.get(ln.producto_id, ZERO) + ln.quantity
    return out


def document_total(lines: Sequence[DocLine]) -> Decimal:
    """Total neto de un documento."""
    return sum((ln.quantity * ln.unit_cost for ln in lines), ZERO)


def reconcile_three_way(
    order: Sequence[DocLine],
    receipt: Sequence[DocLine],
    invoice: Sequence[DocLine],
    tolerance: Decimal = ZERO,
) -> ReconciliationResult:
    """Concilia OC vs Recepción vs Factura. Cantidades facturadas deben igualar lo recibido."""
    ordered, received, invoiced = _qty(order), _qty(receipt), _qty(invoice)
    products = set(ordered) | set(received) | set(invoiced)
    diffs = {p: received.get(p, ZERO) - ordered.get(p, ZERO) for p in products}
    invoice_diff = document_total(invoice) - document_total(receipt)
    prices_oc = {ln.producto_id: ln.unit_cost for ln in order}
    price_bad = any(
        ln.producto_id in prices_oc and abs(ln.unit_cost - prices_oc[ln.producto_id]) > tolerance
        for ln in invoice
    )
    if any(invoiced.get(p, ZERO) != received.get(p, ZERO) for p in products):
        status = MatchStatus.INVOICE_MISMATCH
    elif any(d > ZERO for d in diffs.values()):
        status = MatchStatus.OVER_RECEIPT
    elif price_bad:
        status = MatchStatus.PRICE_MISMATCH
    elif any(d < ZERO for d in diffs.values()):
        status = MatchStatus.PARTIAL_RECEIPT
    else:
        status = MatchStatus.MATCHED
    return ReconciliationResult(status, diffs, invoice_diff)


def assert_supplier_name_immutable(current_name: str, proposed_name: str) -> None:
    """Un nombre de proveedor ("Pollo King") nunca se traduce ni se reescribe automáticamente."""
    if current_name != proposed_name:
        raise ProperNounImmutabilityError(
            f"Supplier name '{current_name}' is an immutable proper noun",
            context={"table": "proveedores"},
        )
