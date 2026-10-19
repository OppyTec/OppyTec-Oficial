"""
oppytec-backend/src/modules/analytics/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para Resumen Ejecutivo y Varianza de Food Cost.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExecutiveSummaryRequest(BaseModel):
    """Parámetros del período para calcular el reporte ejecutivo de control de pérdidas."""

    model_config = ConfigDict(extra="forbid")

    theoretical_cost: Decimal = Field(..., ge=Decimal("0"))
    opening_inventory: Decimal = Field(..., ge=Decimal("0"))
    purchases: Decimal = Field(..., ge=Decimal("0"))
    closing_inventory: Decimal = Field(..., ge=Decimal("0"))
    net_sales: Decimal = Field(..., gt=Decimal("0"))
    alert_threshold_pp: Decimal = Field(default=Decimal("2.00"), ge=Decimal("0"))


class ExecutiveSummaryResponse(BaseModel):
    """KPIs ejecutivos de Food Cost teórico vs real, varianza y rotación de inventario."""

    model_config = ConfigDict(extra="forbid")

    theoretical_pct: Decimal
    actual_pct: Decimal
    variance_pp: Decimal
    turnover: Decimal
    alert: bool


class FoodCostVarianceRequest(BaseModel):
    """Solicitud de cálculo puntual de varianza de Food Cost en puntos porcentuales."""

    model_config = ConfigDict(extra="forbid")

    theoretical_cost: Decimal = Field(..., ge=Decimal("0"))
    opening_inventory: Decimal = Field(..., ge=Decimal("0"))
    purchases: Decimal = Field(..., ge=Decimal("0"))
    closing_inventory: Decimal = Field(..., ge=Decimal("0"))
    net_sales: Decimal = Field(..., gt=Decimal("0"))


class FoodCostVarianceResponse(BaseModel):
    """Varianza entre Food Cost real y teórico en `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    theoretical_pct: Decimal
    actual_pct: Decimal
    variance_pp: Decimal
