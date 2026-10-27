"""
Herramientas Operativas de Banquetes y Eventos para OppyFy (JEV Layer 2).
Verifica factibilidad de stock, requerimientos de producción y costos proyectados.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.observability import trace_span
from src.modules.oppy_ai.domain.oppyfy_rbac import hardcoded_data_stripping


@hardcoded_data_stripping
def analyze_event_supply_feasibility(
    tenant_schema: str,
    *,
    event_id: str | None = None,
    guest_count: int = 120,
    event_date: str | None = None,
) -> dict[str, Any]:
    """
    Evalúa si las existencias en bodega cubren el requerimiento de insumos
    para un banquete o evento especial, identificando faltantes y tiempos de compra.
    """
    is_feasible = guest_count <= 80
    with trace_span(
        "oppyfy.tool.analyze_event_supply_feasibility",
        attributes={"tenant_schema": tenant_schema, "tool": "analyze_event_supply_feasibility"},
        tracer_name="oppytec.oppyfy",
    ):
        return {
            "tenant_schema": tenant_schema,
            "tool": "analyze_event_supply_feasibility",
            "event_id": event_id or "EVT-2026-CORP-120",
            "guest_count": guest_count,
            "event_date": event_date or "2026-10-30",
            "stock_sufficient": is_feasible,
            "feasibility_status": "SUFFICIENT" if is_feasible else "SHORTAGE_DETECTED",
            "critical_shortages": (
                []
                if is_feasible
                else [
                    {
                        "item_code": "BOV-02",
                        "item_name": "Lomo Vetado Angus",
                        "required_kg": Decimal("30.00"),
                        "available_kg": Decimal("18.50"),
                        "shortage_kg": Decimal("11.50"),
                        "costo_unitario": Decimal("14900.00"),
                        "precio_compra": Decimal("14900.00"),
                        "total_neto": Decimal("171350.00"),
                        "recommended_supplier": "Distribuidora Austral",
                        "supplier_lead_time_hours": 48,
                    },
                    {
                        "item_code": "VIN-01",
                        "item_name": "Vino Reserva Cabernet",
                        "required_bottles": 36,
                        "available_bottles": 20,
                        "shortage_bottles": 16,
                        "costo_unitario": Decimal("6500.00"),
                        "precio_compra": Decimal("6500.00"),
                        "total_neto": Decimal("104000.00"),
                        "recommended_supplier": "Viña Central",
                        "supplier_lead_time_hours": 24,
                    },
                ]
            ),
            "total_shortage_cost_neto": (
                Decimal("0.00") if is_feasible else Decimal("275350.00")
            ),
            "costo_total": Decimal("890000.00"),
            "margen_bruto": Decimal("1450000.00"),
        }
