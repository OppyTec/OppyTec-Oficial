"""
oppytec-backend/src/modules/analytics/domain/kpi_formulas.py
KPIs ejecutivos en `Decimal`: Food Cost teórico vs real, varianza de mermas, rotación y proyección.
"""
from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal(0)
HUNDRED = Decimal(100)
PCT = Decimal("0.01")


def theoretical_food_cost_pct(theoretical_cost: Decimal, net_sales: Decimal) -> Decimal:
    """Food Cost teórico % (según escandallos) sobre ventas netas."""
    if net_sales <= ZERO:
        raise ValueError("net sales must be positive")
    return (theoretical_cost / net_sales * HUNDRED).quantize(PCT, ROUND_HALF_UP)


def actual_food_cost(opening: Decimal, purchases: Decimal, closing: Decimal) -> Decimal:
    """Consumo real = inventario inicial + compras - inventario final."""
    return opening + purchases - closing


def actual_food_cost_pct(opening: Decimal, purchases: Decimal, closing: Decimal, net_sales: Decimal) -> Decimal:
    """Food Cost real %."""
    return theoretical_food_cost_pct(actual_food_cost(opening, purchases, closing), net_sales)


def food_cost_variance_pct(theoretical_pct: Decimal, actual_pct: Decimal) -> Decimal:
    """Desviación real - teórico en puntos porcentuales (positivo = pérdida)."""
    return actual_pct - theoretical_pct


def waste_variance(actual_waste: Decimal, expected_waste: Decimal) -> Decimal:
    """Varianza de mermas (real - esperado)."""
    return actual_waste - expected_waste


def inventory_turnover(cogs: Decimal, avg_inventory_value: Decimal) -> Decimal:
    """Rotación = costo de ventas / inventario promedio."""
    if avg_inventory_value <= ZERO:
        raise ValueError("average inventory must be positive")
    return (cogs / avg_inventory_value).quantize(PCT, ROUND_HALF_UP)


def days_of_inventory(turnover: Decimal, days_in_period: int = 30) -> Decimal:
    """Días de inventario = días del período / rotación."""
    if turnover <= ZERO:
        raise ValueError("turnover must be positive")
    return (Decimal(days_in_period) / turnover).quantize(PCT, ROUND_HALF_UP)


def project_linear(history: Sequence[Decimal], periods_ahead: int) -> Decimal:
    """Proyección lineal simple: último valor + pendiente media * periodos."""
    if len(history) < 2:
        raise ValueError("at least two data points required")
    slope = (history[-1] - history[0]) / Decimal(len(history) - 1)
    return (history[-1] + slope * Decimal(periods_ahead)).quantize(PCT, ROUND_HALF_UP)
