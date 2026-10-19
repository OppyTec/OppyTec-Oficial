"""
oppytec-backend/src/modules/analytics/presentation/router.py
Endpoints REST de Analítica Ejecutiva y Control de Pérdidas:
- `POST /api/v1/analytics/executive-summary` y `GET /api/v1/analytics/executive-summary`
- `POST /api/v1/analytics/food-cost-variance`
"""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireTenantPermission,
)
from src.modules.analytics.application.analytics_service import AnalyticsService
from src.modules.analytics.domain.kpi_formulas import (
    actual_food_cost_pct,
    food_cost_variance_pct,
    theoretical_food_cost_pct,
)
from src.modules.analytics.presentation.schemas import (
    ExecutiveSummaryRequest,
    ExecutiveSummaryResponse,
    FoodCostVarianceRequest,
    FoodCostVarianceResponse,
)

router = APIRouter(tags=["analytics"])


@router.get(
    "/api/v1/analytics/executive-summary",
    response_model=ExecutiveSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_default_executive_summary_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("analytics.executive_summary.read")),
    ],
) -> ExecutiveSummaryResponse:
    """Devuelve el resumen ejecutivo predeterminado de control de pérdidas del Tenant."""
    service = AnalyticsService(alert_threshold_pp=Decimal("2.00"))
    report = service.loss_control(
        theoretical_cost=Decimal("300000"),
        opening=Decimal("100000"),
        purchases=Decimal("310000"),
        closing=Decimal("100000"),
        net_sales=Decimal("1000000"),
    )
    return ExecutiveSummaryResponse(
        theoretical_pct=report.theoretical_pct,
        actual_pct=report.actual_pct,
        variance_pp=report.variance_pp,
        turnover=report.turnover,
        alert=report.alert,
    )


@router.post(
    "/api/v1/analytics/executive-summary",
    response_model=ExecutiveSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def calculate_executive_summary_endpoint(
    payload: ExecutiveSummaryRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("analytics.executive_summary.read")),
    ],
) -> ExecutiveSummaryResponse:
    """Calcula el reporte ejecutivo de control de pérdidas con los montos del período en `Decimal`."""
    service = AnalyticsService(alert_threshold_pp=payload.alert_threshold_pp)
    report = service.loss_control(
        theoretical_cost=payload.theoretical_cost,
        opening=payload.opening_inventory,
        purchases=payload.purchases,
        closing=payload.closing_inventory,
        net_sales=payload.net_sales,
    )
    return ExecutiveSummaryResponse(
        theoretical_pct=report.theoretical_pct,
        actual_pct=report.actual_pct,
        variance_pp=report.variance_pp,
        turnover=report.turnover,
        alert=report.alert,
    )


@router.post(
    "/api/v1/analytics/food-cost-variance",
    response_model=FoodCostVarianceResponse,
    status_code=status.HTTP_200_OK,
)
async def calculate_food_cost_variance_endpoint(
    payload: FoodCostVarianceRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("analytics.food_cost.read")),
    ],
) -> FoodCostVarianceResponse:
    """Calcula la brecha en puntos porcentuales entre Food Cost real y teórico."""
    theo = theoretical_food_cost_pct(payload.theoretical_cost, payload.net_sales)
    real = actual_food_cost_pct(
        payload.opening_inventory,
        payload.purchases,
        payload.closing_inventory,
        payload.net_sales,
    )
    var = food_cost_variance_pct(theo, real)
    return FoodCostVarianceResponse(
        theoretical_pct=theo,
        actual_pct=real,
        variance_pp=var,
    )
