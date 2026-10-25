"""
oppytec-backend/src/modules/inventory/domain/exceptions.py
Excepciones de dominio puro para el Módulo de Inventario (Clean Architecture y RFC 7807).
"""
from __future__ import annotations

from src.core.exceptions import (
    InsufficientStockError,
    InvalidMovementTypeError,
    NegativeStockNotAllowedError,
    OppyTecError,
    TransferSameWarehouseError,
)


class InventoryDomainError(OppyTecError):
    """Excepción base para violaciones de reglas de negocio en inventario."""

    default_status_code = 400
    default_error_code = "INVENTORY_DOMAIN_ERROR"
    default_i18n_key = "inventory:errors.domain_error"
    default_title = "Inventory Domain Error"


__all__ = [
    "InsufficientStockError",
    "InvalidMovementTypeError",
    "InventoryDomainError",
    "NegativeStockNotAllowedError",
    "TransferSameWarehouseError",
]
