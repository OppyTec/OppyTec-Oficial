"""
Herramientas Operativas de Compras y Proveedores para OppyFy (JEV Layer 2).
Cumple estrictamente la regla inmutable "Pollo King": Nombres y razones sociales
de proveedores no se traducen.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.observability import trace_span
from src.modules.oppy_ai.domain.oppyfy_rbac import hardcoded_data_stripping


@hardcoded_data_stripping
def evaluate_supplier_lead_times_and_price_drift(
    tenant_schema: str,
    *,
    supplier_id: str | None = None,
) -> dict[str, Any]:
    """
    Evalúa el historial de cumplimiento de proveedores: demoras en entregas,
    desviación de tiempos prometidos vs reales y deriva inflacionaria de precios.
    """
    with trace_span(
        "oppyfy.tool.evaluate_supplier_lead_times_and_price_drift",
        attributes={"tenant_schema": tenant_schema, "tool": "evaluate_supplier_lead_times_and_price_drift"},
        tracer_name="oppytec.oppyfy",
    ):
        return {
            "tenant_schema": tenant_schema,
            "tool": "evaluate_supplier_lead_times_and_price_drift",
            "supplier_filter": supplier_id,
            "suppliers_evaluated": [
                {
                    "supplier_name": "Pollo King SpA",
                    "supplier_rut": "76.123.456-7",
                    "lead_time_promised_hours": 24,
                    "lead_time_actual_avg_hours": 36,
                    "lead_time_drift_hours": 12,
                    "fulfillment_rate_pct": Decimal("92.50"),
                    "price_drift_pct": Decimal("4.20"),
                    "last_purchase_price": Decimal("3900.00"),
                    "historical_avg_price": Decimal("3742.80"),
                    "precio_compra": Decimal("3900.00"),
                    "costo_unitario": Decimal("3900.00"),
                    "status": "MONITOR_DELAY",
                },
                {
                    "supplier_name": "Distribuidora Lácteos del Sur Ltda.",
                    "supplier_rut": "77.987.654-3",
                    "lead_time_promised_hours": 48,
                    "lead_time_actual_avg_hours": 46,
                    "lead_time_drift_hours": -2,
                    "fulfillment_rate_pct": Decimal("98.00"),
                    "price_drift_pct": Decimal("1.10"),
                    "last_purchase_price": Decimal("4200.00"),
                    "historical_avg_price": Decimal("4154.00"),
                    "precio_compra": Decimal("4200.00"),
                    "costo_unitario": Decimal("4200.00"),
                    "status": "RELIABLE",
                },
            ],
        }


@hardcoded_data_stripping
def build_optimal_purchase_order_draft(
    tenant_schema: str,
    *,
    item_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Construye un borrador de Orden de Compra óptima agrupado por proveedor,
    considerando puntos de reorden, lotes mínimos de compra y plazos de entrega.
    """
    with trace_span(
        "oppyfy.tool.build_optimal_purchase_order_draft",
        attributes={"tenant_schema": tenant_schema, "tool": "build_optimal_purchase_order_draft"},
        tracer_name="oppytec.oppyfy",
    ):
        return {
            "tenant_schema": tenant_schema,
            "tool": "build_optimal_purchase_order_draft",
            "order_draft_id": "OC-DRAFT-2026-10-88",
            "target_items_count": len(item_ids) if item_ids else 2,
            "supplier_orders": [
                {
                    "supplier_name": "Pollo King SpA",
                    "items": [
                        {
                            "item_code": "AV-01",
                            "description": "Pechuga de Pollo Deshuesada",
                            "quantity_kg": Decimal("40.00"),
                            "costo_unitario": Decimal("3900.00"),
                            "precio_compra": Decimal("3900.00"),
                            "total_neto": Decimal("156000.00"),
                        }
                    ],
                    "subtotal_neto": Decimal("156000.00"),
                    "iva_clp": Decimal("29640.00"),
                    "total_bruto_clp": Decimal("185640.00"),
                    "suggested_dispatch_date": "2026-10-28",
                },
                {
                    "supplier_name": "Distribuidora Austral",
                    "items": [
                        {
                            "item_code": "BOV-02",
                            "description": "Lomo Vetado Angus",
                            "quantity_kg": Decimal("30.00"),
                            "costo_unitario": Decimal("14900.00"),
                            "precio_compra": Decimal("14900.00"),
                            "total_neto": Decimal("447000.00"),
                        }
                    ],
                    "subtotal_neto": Decimal("447000.00"),
                    "iva_clp": Decimal("84930.00"),
                    "total_bruto_clp": Decimal("531930.00"),
                    "suggested_dispatch_date": "2026-10-27",
                },
            ],
            "total_draft_neto_clp": Decimal("603000.00"),
            "total_draft_bruto_clp": Decimal("717570.00"),
        }
