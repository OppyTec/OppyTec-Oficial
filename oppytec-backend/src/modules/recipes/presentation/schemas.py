"""
oppytec-backend/src/modules/recipes/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para Escandallos Recursivos y Simulación de Margen.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


class RecipeLinePayload(BaseModel):
    """Línea de un escandallo: insumo (`ingredient_id`) o sub-receta (`sub_recipe_id`)."""

    model_config = ConfigDict(extra="forbid")

    quantity: Decimal = Field(..., gt=Decimal("0"))
    ingredient_id: int | None = Field(default=None, gt=0)
    sub_recipe_id: int | None = Field(default=None, gt=0)
    waste_pct: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), lt=Decimal("100"))
    unit_cost: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class EscandalloCreateRequest(BaseModel):
    """Creación o actualización de una receta/escandallo con cálculo recursivo en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=2, max_length=160)
    yield_portions: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    net_price: Decimal = Field(..., gt=Decimal("0"))
    lines: list[RecipeLinePayload] = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def _sanitize_recipe_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="name")


class EscandalloCostResponse(BaseModel):
    """Reporte de costeo recursivo de una receta: costo por porción, Food Cost % y margen."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: int
    name: str
    portion_cost: Decimal
    net_price: Decimal
    food_cost_pct: Decimal
    margin_amount: Decimal
    margin_pct: Decimal


class MarginSimulationRequest(BaseModel):
    """Simulación de margen y Food Cost % ante cambios de precio o costo de receta."""

    model_config = ConfigDict(extra="forbid")

    portion_cost: Decimal = Field(..., ge=Decimal("0"))
    proposed_net_price: Decimal = Field(..., gt=Decimal("0"))


class MarginSimulationResponse(BaseModel):
    """Resultado de la simulación de margen en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    portion_cost: Decimal
    proposed_net_price: Decimal
    food_cost_pct: Decimal
    margin_amount: Decimal
    margin_pct: Decimal
