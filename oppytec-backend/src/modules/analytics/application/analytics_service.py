"""
oppytec-backend/src/modules/analytics/application/analytics_service.py
Reporte ejecutivo de control de pérdidas combinando Food Cost teórico vs real.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.modules.analytics.domain.kpi_formulas import (
    actual_food_cost_pct,
    food_cost_variance_pct,
    inventory_turnover,
    theoretical_food_cost_pct,
)


@dataclass(frozen=True)
class LossControlReport:
    """KPIs de control de pérdidas de un período."""

    theoretical_pct: Decimal
    actual_pct: Decimal
    variance_pp: Decimal
    turnover: Decimal
    alert: bool


class AnalyticsService:
    """Genera reportes con umbral de alerta en puntos porcentuales."""

    def __init__(self, alert_threshold_pp: Decimal = Decimal("2.00")) -> None:
        self._threshold = alert_threshold_pp

    def loss_control(
        self,
        *,
        theoretical_cost: Decimal,
        opening: Decimal,
        purchases: Decimal,
        closing: Decimal,
        net_sales: Decimal,
    ) -> LossControlReport:
        """Compara Food Cost teórico con real y marca alerta si supera el umbral."""
        theo = theoretical_food_cost_pct(theoretical_cost, net_sales)
        real = actual_food_cost_pct(opening, purchases, closing, net_sales)
        var = food_cost_variance_pct(theo, real)
        avg_inv = (opening + closing) / Decimal(2)
        turnover = inventory_turnover(opening + purchases - closing, avg_inv)
        return LossControlReport(theo, real, var, turnover, var > self._threshold)
