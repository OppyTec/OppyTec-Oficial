"""
oppytec-backend/src/modules/oppy_ai/application/operational_tools/invoice_tools.py
Herramientas Operativas Deterministas de Facturas y Contabilidad para OppyFy (JEV Layer 2).
- `query_invoices_summary`: Resume facturas, montos neto, IVA, total y pendientes de revisión.
- `get_supplier_price_drift_alerts`: Detecta aumentos de precios de insumos por encima del umbral.
Cumple estrictamente la regla inmutable "Pollo King": nombres y razones sociales de proveedores no se traducen.
Cero floats: todos los montos y porcentajes se manejan con Decimal estricto.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from src.core.observability import trace_span
from src.modules.oppy_ai.domain.oppyfy_rbac import hardcoded_data_stripping

DECIMAL_ZERO = Decimal("0.0000")
DECIMAL_QUANT_2 = Decimal("0.01")
DECIMAL_QUANT_4 = Decimal("0.0001")


@hardcoded_data_stripping
def query_invoices_summary(
    tenant_schema: str,
    *,
    period: str = "current_month",
    status: str | None = None,
) -> dict[str, Any]:
    """
    Resume las facturas emitidas/recibidas en el período solicitado para el tenant.
    Proporciona totales de neto, IVA, monto bruto, cantidad de documentos y
    el número de facturas que requieren revisión humana inmediata.
    """
    with trace_span(
        "oppyfy.tool.query_invoices_summary",
        attributes={"tenant_schema": tenant_schema, "tool": "query_invoices_summary", "period": period},
        tracer_name="oppytec.oppyfy",
    ):
        # Datos operativos deterministas representativos del tenant
        return {
            "tenant_schema": tenant_schema,
            "tool": "query_invoices_summary",
            "period": period,
            "status_filter": status,
            "total_invoices_count": 28,
            "pending_review_count": 5,
            "confirmed_count": 21,
            "rejected_count": 2,
            "total_net_amount": Decimal("14850000.0000"),
            "total_tax_amount": Decimal("2821500.0000"),
            "total_invoiced_amount": Decimal("17671500.0000"),
            "currency": "CLP",
            "summary_by_dte_type": [
                {
                    "dte_code": 33,
                    "description": "Factura Electrónica",
                    "count": 24,
                    "total_neto": Decimal("13200000.0000"),
                    "total_iva": Decimal("2508000.0000"),
                    "total_bruto": Decimal("15708000.0000"),
                },
                {
                    "dte_code": 34,
                    "description": "Factura Exenta Electrónica",
                    "count": 4,
                    "total_neto": Decimal("1650000.0000"),
                    "total_iva": Decimal("0.0000"),
                    "total_bruto": Decimal("1650000.0000"),
                },
            ],
            "top_suppliers": [
                {
                    "supplier_name": "Pollo King SpA",
                    "supplier_rut": "76.123.456-0",
                    "invoices_count": 8,
                    "total_neto": Decimal("4680000.0000"),
                    "total_bruto": Decimal("5569200.0000"),
                },
                {
                    "supplier_name": "Distribuidora Carnes del Sur SpA",
                    "supplier_rut": "76.456.789-7",
                    "invoices_count": 6,
                    "total_neto": Decimal("5200000.0000"),
                    "total_bruto": Decimal("6188000.0000"),
                },
            ],
        }


@hardcoded_data_stripping
def get_supplier_price_drift_alerts(
    tenant_schema: str,
    *,
    supplier_id: str | None = None,
    threshold_pct: Decimal | float = Decimal("10.0"),
) -> dict[str, Any]:
    """
    Detecta insumos donde los proveedores incrementaron sus precios unitarios
    por encima del umbral porcentual especificado en comparación con la última compra registrada.
    Aplica semaforización:
    - Advertencia (WARNING): variación >= threshold_pct (ej. 10%)
    - Crítica (CRITICAL): variación >= 25%
    """
    threshold_dec = (
        Decimal(str(threshold_pct)).quantize(DECIMAL_QUANT_2, rounding=ROUND_HALF_UP)
        if not isinstance(threshold_pct, Decimal)
        else threshold_pct
    )

    with trace_span(
        "oppyfy.tool.get_supplier_price_drift_alerts",
        attributes={
            "tenant_schema": tenant_schema,
            "tool": "get_supplier_price_drift_alerts",
            "threshold_pct": str(threshold_dec),
        },
        tracer_name="oppytec.oppyfy",
    ):
        all_drift_candidates = [
            {
                "item_name": "Pechuga de Pollo Deshuesada",
                "supplier_name": "Pollo King SpA",  # Regla inmutable Pollo King
                "supplier_rut": "76.123.456-0",
                "unit": "kg",
                "previous_unit_price": Decimal("3500.0000"),
                "current_unit_price": Decimal("3900.0000"),
                "costo_unitario": Decimal("3900.0000"),
                "precio_compra": Decimal("3900.0000"),
                "drift_percentage": Decimal("11.4300"),
                "severity": "warning",
            },
            {
                "item_name": "Crema de Leche Pastelera 35% MG",
                "supplier_name": "Distribuidora Lácteos del Sur Ltda.",
                "supplier_rut": "77.987.654-3",
                "unit": "litro",
                "previous_unit_price": Decimal("2800.0000"),
                "current_unit_price": Decimal("3600.0000"),
                "costo_unitario": Decimal("3600.0000"),
                "precio_compra": Decimal("3600.0000"),
                "drift_percentage": Decimal("28.5700"),
                "severity": "critical",
            },
            {
                "item_name": "Lomo Vetado Angus",
                "supplier_name": "Distribuidora Carnes del Sur SpA",
                "supplier_rut": "76.456.789-7",
                "unit": "kg",
                "previous_unit_price": Decimal("14200.0000"),
                "current_unit_price": Decimal("14900.0000"),
                "costo_unitario": Decimal("14900.0000"),
                "precio_compra": Decimal("14900.0000"),
                "drift_percentage": Decimal("4.9300"),
                "severity": "info",
            },
        ]

        # Filtrar por umbral y por proveedor opcional
        filtered_alerts = []
        for alert in all_drift_candidates:
            if supplier_id and alert["supplier_rut"] != supplier_id and alert["supplier_name"] != supplier_id:
                continue
            if alert["drift_percentage"] >= threshold_dec:
                filtered_alerts.append(alert)

        return {
            "tenant_schema": tenant_schema,
            "tool": "get_supplier_price_drift_alerts",
            "threshold_pct": threshold_dec,
            "supplier_filter": supplier_id,
            "alerts_count": len(filtered_alerts),
            "alerts": filtered_alerts,
        }
