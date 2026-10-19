"""
oppytec-backend/src/modules/operations/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para Ventas POS, Buffet por Pax y Eventos.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


class PosSaleItemPayload(BaseModel):
    """Ítem vendido en el punto de venta (receta y cantidad de porciones en `Decimal`)."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: int = Field(..., gt=0)
    portions: Decimal = Field(..., gt=Decimal("0"))


class PosSaleProcessRequest(BaseModel):
    """Solicitud de registro de venta POS con explosión de insumos en orden canónico de locks."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int = Field(..., gt=0)
    items: list[PosSaleItemPayload] = Field(..., min_length=1)
    recipe_ingredients: dict[int, dict[int, Decimal]] = Field(..., min_length=1)
    ingredient_costs: dict[int, Decimal] = Field(default_factory=dict)


class PosSaleProcessResponse(BaseModel):
    """Resultado de procesar una venta POS y descargar el Kardex."""

    model_config = ConfigDict(extra="forbid")

    bodega_id: int
    movements_registered: int
    consumed_by_ingredient: dict[int, Decimal]


class BuffetCostRequest(BaseModel):
    """Cálculo de costo por comensal (`pax`) de un servicio de Buffet."""

    model_config = ConfigDict(extra="forbid")

    service_name: str = Field(..., min_length=2, max_length=150)
    total_buffet_cost: Decimal = Field(..., ge=Decimal("0"))
    pax: int = Field(..., gt=0)
    leftover_value: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))

    @field_validator("service_name")
    @classmethod
    def _sanitize_service_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="service_name")


class BuffetCostResponse(BaseModel):
    """Costo neto por comensal (`pax`) calculado en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    service_name: str
    pax: int
    total_buffet_cost: Decimal
    leftover_value: Decimal
    cost_per_pax: Decimal


class CateringEventRequest(BaseModel):
    """Cotización y registro de un evento gastronómico / banquetería."""

    model_config = ConfigDict(extra="forbid")

    event_name: str = Field(..., min_length=2, max_length=160)
    attendees_pax: int = Field(..., gt=0)
    food_cost_per_pax: Decimal = Field(..., ge=Decimal("0"))
    net_price_per_pax: Decimal = Field(..., gt=Decimal("0"))

    @field_validator("event_name")
    @classmethod
    def _sanitize_event_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="event_name")


class CateringEventResponse(BaseModel):
    """Resumen económico de un evento gastronómico en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    event_name: str
    attendees_pax: int
    total_food_cost: Decimal
    total_net_revenue: Decimal
    gross_margin: Decimal
