"""
oppytec-backend/src/modules/inventory/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para Kardex, Toma de Inventario y Mermas.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


class KardexMovementCreateRequest(BaseModel):
    """Registro atómico de movimiento de Kardex por bodega."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    bodega_id: int = Field(..., gt=0)
    movement_type: Literal["ENTRADA", "SALIDA", "MERMA", "CONSUMO", "AJUSTE_POSITIVO"]
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_cost: Decimal = Field(..., ge=Decimal("0"))


class KardexMovementResponse(BaseModel):
    """Movimiento inmutable registrado en el Kardex con saldo resultante."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int
    bodega_id: int
    movement_type: str
    quantity: Decimal
    resulting_balance: Decimal
    unit_cost: Decimal
    actor_user_id: int


class InventoryCountItemRequest(BaseModel):
    """Ítem de conteo físico de inventario en bodega."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    counted_quantity: Decimal = Field(..., ge=Decimal("0"))
    unit_cost: Decimal = Field(..., ge=Decimal("0"))


class InventoryCountSubmitRequest(BaseModel):
    """Envío de toma física de inventario con bloqueo canónico `ORDER BY id ASC`."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int = Field(..., gt=0)
    items: list[InventoryCountItemRequest] = Field(..., min_length=1)


class InventoryCountResponse(BaseModel):
    """Resultado de conciliar una toma física de inventario en orden canónico de locks."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int
    locked_product_ids_asc: list[int]
    processed_items: int


class MermaReportRequest(BaseModel):
    """Reporte de merma operativa en bodega o cocina."""

    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., gt=0)
    bodega_id: int = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_cost: Decimal = Field(..., ge=Decimal("0"))
    reason: str = Field(..., min_length=4, max_length=300)

    @field_validator("reason")
    @classmethod
    def _sanitize_merma_reason(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="reason")


class MermaApproveRequest(BaseModel):
    """Solicitud de aprobación de una merma pendiente por un supervisor distinto del reportante."""

    model_config = ConfigDict(extra="forbid")

    unit_cost: Decimal = Field(..., ge=Decimal("0"))


class MermaResponse(BaseModel):
    """Estado de un registro de merma (`PENDIENTE`, `APROBADA`, `RECHAZADA`)."""

    model_config = ConfigDict(extra="forbid")

    waste_id: int
    producto_id: int
    bodega_id: int
    quantity: Decimal
    total_cost: Decimal
    reason: str
    reporter_user_id: int
    status: str
