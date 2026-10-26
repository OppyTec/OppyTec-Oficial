"""Capa de aplicación del módulo inventory."""
from __future__ import annotations

from src.modules.inventory.application.history_service import KardexHistoryService
from src.modules.inventory.application.inventory_service import (
    InventoryService,
    KardexEntry,
    LotStatusResult,
    StockStatusResult,
)
from src.modules.inventory.application.physical_count_service import (
    CountItemInput,
    PhysicalCountService,
)
from src.modules.inventory.application.waste_service import WasteRecord, WasteService

__all__ = [
    "CountItemInput",
    "InventoryService",
    "KardexEntry",
    "KardexHistoryService",
    "LotStatusResult",
    "PhysicalCountService",
    "StockStatusResult",
    "WasteRecord",
    "WasteService",
]
