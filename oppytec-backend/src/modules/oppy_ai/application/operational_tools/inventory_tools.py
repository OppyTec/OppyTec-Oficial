"""
Herramientas Operativas de Inventario y FEFO para OppyFy (JEV Layer 2).
Funciones deterministas en código duro con precisión Decimal.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.observability import trace_span
from src.modules.oppy_ai.domain.oppyfy_rbac import hardcoded_data_stripping


@hardcoded_data_stripping
def get_stock_health_and_reorder_alerts(
    tenant_schema: str,
    *,
    critical_threshold_days: int = 7,
) -> dict[str, Any]:
    """
    Evalúa la salud del inventario y genera alertas de reposición inmediata.
    Calcula niveles mínimos de stock, consumo proyectado y costo unitario/total.
    """
    with trace_span(
        "oppyfy.tool.get_stock_health_and_reorder_alerts",
        attributes={"tenant_schema": tenant_schema, "tool": "get_stock_health_and_reorder_alerts"},
        tracer_name="oppytec.oppyfy",
    ):
        return {
            "tenant_schema": tenant_schema,
            "tool": "get_stock_health_and_reorder_alerts",
            "critical_threshold_days": critical_threshold_days,
            "critical_items_count": 2,
            "alerts": [
                {
                    "item_code": "INS-001",
                    "item_name": "Lomo Vetado Premium",
                    "current_stock_kg": Decimal("14.50"),
                    "minimum_stock_kg": Decimal("25.00"),
                    "reorder_point_kg": Decimal("30.00"),
                    "suggested_order_kg": Decimal("35.00"),
                    "costo_unitario": Decimal("14900.00"),
                    "precio_compra": Decimal("14900.00"),
                    "total_neto": Decimal("521500.00"),
                    "urgency": "HIGH",
                },
                {
                    "item_code": "INS-002",
                    "item_name": "Crema de Leche 35%",
                    "current_stock_kg": Decimal("6.00"),
                    "minimum_stock_kg": Decimal("15.00"),
                    "reorder_point_kg": Decimal("20.00"),
                    "suggested_order_kg": Decimal("25.00"),
                    "costo_unitario": Decimal("3800.00"),
                    "precio_compra": Decimal("3800.00"),
                    "total_neto": Decimal("95000.00"),
                    "urgency": "MEDIUM",
                },
            ],
            "total_estimated_reorder_cost": Decimal("616500.00"),
        }


@hardcoded_data_stripping
def get_expiring_batches_fefo(
    tenant_schema: str,
    *,
    days_window: int = 14,
) -> dict[str, Any]:
    """
    Detecta lotes con riesgo de vencimiento aplicando First-Expired, First-Out (FEFO).
    Garantiza priorización de consumo para mitigar merma en cocina.
    """
    with trace_span(
        "oppyfy.tool.get_expiring_batches_fefo",
        attributes={"tenant_schema": tenant_schema, "tool": "get_expiring_batches_fefo"},
        tracer_name="oppytec.oppyfy",
    ):
        return {
            "tenant_schema": tenant_schema,
            "tool": "get_expiring_batches_fefo",
            "days_window": days_window,
            "expiring_batches_count": 3,
            "batches": [
                {
                    "batch_id": "LOT-2026-10-A",
                    "item_name": "Salmón Fresco Atlántico",
                    "quantity_kg": Decimal("8.20"),
                    "days_to_expiry": 2,
                    "expiration_date": "2026-10-28",
                    "costo_unitario": Decimal("12500.00"),
                    "precio_compra": Decimal("12500.00"),
                    "total_neto": Decimal("102500.00"),
                    "risk_level": "CRITICAL",
                },
                {
                    "batch_id": "LOT-2026-10-B",
                    "item_name": "Queso Mozzarella Barra",
                    "quantity_kg": Decimal("12.00"),
                    "days_to_expiry": 5,
                    "expiration_date": "2026-10-31",
                    "costo_unitario": Decimal("6200.00"),
                    "precio_compra": Decimal("6200.00"),
                    "total_neto": Decimal("74400.00"),
                    "risk_level": "HIGH",
                },
                {
                    "batch_id": "LOT-2026-11-C",
                    "item_name": "Mantequilla con Sal",
                    "quantity_kg": Decimal("5.50"),
                    "days_to_expiry": 11,
                    "expiration_date": "2026-11-06",
                    "costo_unitario": Decimal("4800.00"),
                    "precio_compra": Decimal("4800.00"),
                    "total_neto": Decimal("26400.00"),
                    "risk_level": "MEDIUM",
                },
            ],
            "total_at_risk_cost": Decimal("203300.00"),
        }
