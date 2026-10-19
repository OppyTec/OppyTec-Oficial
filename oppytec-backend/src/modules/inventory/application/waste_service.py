"""
oppytec-backend/src/modules/inventory/application/waste_service.py
Registro de mermas con flujo de aprobación cuando el costo supera el umbral configurado.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.exceptions import PermissionDeniedError
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.domain.kardex_math import waste_requires_approval, waste_total_cost


@dataclass
class WasteRecord:
    """Merma con estado de aprobación."""

    waste_id: int
    producto_id: int
    bodega_id: int
    quantity: Decimal
    total_cost: Decimal
    reason: str
    reporter_user_id: int
    status: str


class WasteService:
    """Mermas bajo umbral se aplican de inmediato; sobre umbral quedan PENDIENTE hasta aprobar."""

    def __init__(self, inventory: InventoryService, approval_threshold: Decimal) -> None:
        self._inventory = inventory
        self._threshold = approval_threshold
        self._wastes: dict[int, WasteRecord] = {}
        self._seq = 0

    def report_waste(
        self,
        *,
        producto_id: int,
        bodega_id: int,
        quantity: Decimal,
        unit_cost: Decimal,
        reason: str,
        reporter_user_id: int,
    ) -> WasteRecord:
        """Reporta una merma; aplica al Kardex solo si no requiere aprobación."""
        total = waste_total_cost(quantity, unit_cost)
        self._seq += 1
        pending = waste_requires_approval(total, self._threshold)
        record = WasteRecord(
            self._seq, producto_id, bodega_id, quantity, total, reason, reporter_user_id,
            "PENDIENTE" if pending else "APROBADA",
        )
        if not pending:
            self._apply(record, unit_cost)
        self._wastes[record.waste_id] = record
        return record

    def approve(self, waste_id: int, approver_user_id: int, unit_cost: Decimal) -> WasteRecord:
        """Aprueba una merma pendiente; el aprobador no puede ser quien la reportó."""
        record = self._wastes[waste_id]
        if record.reporter_user_id == approver_user_id:
            raise PermissionDeniedError("Reporter cannot approve own waste")
        if record.status == "PENDIENTE":
            self._apply(record, unit_cost)
            record.status = "APROBADA"
        return record

    def reject(self, waste_id: int) -> WasteRecord:
        """Rechaza una merma pendiente sin tocar el Kardex."""
        record = self._wastes[waste_id]
        if record.status == "PENDIENTE":
            record.status = "RECHAZADA"
        return record

    def _apply(self, record: WasteRecord, unit_cost: Decimal) -> None:
        self._inventory.register_movement(
            producto_id=record.producto_id,
            bodega_id=record.bodega_id,
            movement_type="MERMA",
            quantity=record.quantity,
            unit_cost=unit_cost,
            actor_user_id=record.reporter_user_id,
        )
