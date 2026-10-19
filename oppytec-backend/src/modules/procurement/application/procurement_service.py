"""
oppytec-backend/src/modules/procurement/application/procurement_service.py
Ciclo de compras: OC -> Recepción -> Factura con conciliación y proveedores inmutables.
"""
from __future__ import annotations

from collections.abc import Sequence

from src.modules.procurement.domain.reconciliation import (
    DocLine,
    ReconciliationResult,
    assert_supplier_name_immutable,
    reconcile_three_way,
)


class ProcurementService:
    """Mantiene proveedores y documentos de compra por número de OC."""

    def __init__(self) -> None:
        self._suppliers: dict[int, str] = {}
        self._orders: dict[str, Sequence[DocLine]] = {}
        self._receipts: dict[str, list[DocLine]] = {}

    def register_supplier(self, supplier_id: int, name: str) -> None:
        """Alta de proveedor (el nombre queda inmutable)."""
        self._suppliers[supplier_id] = name

    def rename_supplier(self, supplier_id: int, new_name: str) -> None:
        """Cualquier renombrado automático/traducción es rechazado."""
        assert_supplier_name_immutable(self._suppliers[supplier_id], new_name)

    def supplier_name(self, supplier_id: int) -> str:
        """Nombre original del proveedor."""
        return self._suppliers[supplier_id]

    def create_order(self, po_number: str, lines: Sequence[DocLine]) -> None:
        """Registra una orden de compra."""
        self._orders[po_number] = tuple(lines)
        self._receipts.setdefault(po_number, [])

    def receive(self, po_number: str, lines: Sequence[DocLine]) -> None:
        """Registra una recepción (parcial o total)."""
        self._receipts[po_number].extend(lines)

    def reconcile_invoice(
        self, po_number: str, invoice: Sequence[DocLine]
    ) -> ReconciliationResult:
        """Concilia la factura contra OC y recepciones acumuladas."""
        return reconcile_three_way(self._orders[po_number], self._receipts[po_number], invoice)
