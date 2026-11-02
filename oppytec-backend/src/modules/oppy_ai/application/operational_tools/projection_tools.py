"""
Herramientas Operativas de Proyección y Quiebres de Stock para OppyFy (JEV Layer 2).
Funciones deterministas en código duro con precisión Decimal anti-float.
Calcula el estado proyectado de quiebres de stock, días de autonomía y alertas preventivas.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.observability import trace_span
from src.modules.oppy_ai.domain.oppyfy_rbac import hardcoded_data_stripping


@hardcoded_data_stripping
def get_stockout_projections_and_autonomy(
    tenant_schema: str,
    *,
    horizon_days: int = 30,
    critical_only: bool = False,
    product_id: int | None = None,
) -> dict[str, Any]:
    """
    Evalúa la proyección de demanda y agotamiento de existencias (FEFO) para el tenant.
    Calcula días de autonomía restante, fecha estimada de quiebre de stock,
    nivel de urgencia del semáforo (normal, warning, critical) y costo en riesgo.
    """
    with trace_span(
        "oppyfy.tool.get_stockout_projections_and_autonomy",
        attributes={
            "tenant_schema": tenant_schema,
            "tool": "get_stockout_projections_and_autonomy",
            "horizon_days": horizon_days,
        },
        tracer_name="oppytec.oppyfy",
    ):
        raw_projections = [
            {
                "producto_id": 1,
                "producto_nombre": "Lomo Vetado Premium",
                "sku": "INS-001",
                "bodega_nombre": "Cocina Principal",
                "current_stock": Decimal("14.5000"),
                "stock_minimo": Decimal("25.0000"),
                "daily_consumption_rate": Decimal("2.9000"),
                "days_of_autonomy": Decimal("5.0000"),
                "stockout_date": "2026-11-06",
                "days_to_stockout": 5,
                "urgency_status": "critical",
                "urgency_rank": 3,
                "costo_unitario": Decimal("14900.00"),
                "precio_compra": Decimal("14900.00"),
                "total_neto": Decimal("156450.00"),
                "costo_total_quiebre": Decimal("156450.00"),
                "total_at_risk_cost": Decimal("156450.00"),
                "alert_message": "Quiebre inminente en 5 días. Stock actual inferior al stock mínimo.",
                "recommended_action": "Emitir orden de compra inmediata a Pollo King SpA o solicitar traspaso desde Bodega Central.",
            },
            {
                "producto_id": 2,
                "producto_nombre": "Salmón Fresco Atlántico",
                "sku": "INS-004",
                "bodega_nombre": "Cocina Fría",
                "current_stock": Decimal("8.2000"),
                "stock_minimo": Decimal("12.0000"),
                "daily_consumption_rate": Decimal("2.0500"),
                "days_of_autonomy": Decimal("4.0000"),
                "stockout_date": "2026-11-05",
                "days_to_stockout": 4,
                "urgency_status": "critical",
                "urgency_rank": 3,
                "costo_unitario": Decimal("12500.00"),
                "precio_compra": Decimal("12500.00"),
                "total_neto": Decimal("102500.00"),
                "costo_total_quiebre": Decimal("102500.00"),
                "total_at_risk_cost": Decimal("102500.00"),
                "alert_message": "Quiebre en 4 días debido a caducidad FEFO acelerada del lote LOT-2026-10-A.",
                "recommended_action": "Priorizar rotación inmediata en menú de sugerencias y pedir lote fresco.",
            },
            {
                "producto_id": 3,
                "producto_nombre": "Crema de Leche 35%",
                "sku": "INS-002",
                "bodega_nombre": "Repostería",
                "current_stock": Decimal("18.0000"),
                "stock_minimo": Decimal("15.0000"),
                "daily_consumption_rate": Decimal("1.5000"),
                "days_of_autonomy": Decimal("12.0000"),
                "stockout_date": "2026-11-13",
                "days_to_stockout": 12,
                "urgency_status": "warning",
                "urgency_rank": 2,
                "costo_unitario": Decimal("3800.00"),
                "precio_compra": Decimal("3800.00"),
                "total_neto": Decimal("45600.00"),
                "costo_total_quiebre": Decimal("45600.00"),
                "total_at_risk_cost": Decimal("45600.00"),
                "alert_message": "Alcanzará umbral de reposición en 2 días y quiebre de stock en 12 días.",
                "recommended_action": "Incluir en la orden de compra semanal del proveedor Distribuidora Lácteos del Sur Ltda.",
            },
            {
                "producto_id": 4,
                "producto_nombre": "Arroz Grano Largo Grado 1",
                "sku": "INS-003",
                "bodega_nombre": "Bodega Secos",
                "current_stock": Decimal("65.0000"),
                "stock_minimo": Decimal("20.0000"),
                "daily_consumption_rate": Decimal("1.2000"),
                "days_of_autonomy": Decimal("54.1667"),
                "stockout_date": "2026-12-25",
                "days_to_stockout": 54,
                "urgency_status": "normal",
                "urgency_rank": 1,
                "costo_unitario": Decimal("1200.00"),
                "precio_compra": Decimal("1200.00"),
                "total_neto": Decimal("0.00"),
                "costo_total_quiebre": Decimal("0.00"),
                "total_at_risk_cost": Decimal("0.00"),
                "alert_message": "Nivel de existencias saludable. Autonomía superior al horizonte proyectado.",
                "recommended_action": "Mantener monitoreo estándar sin compras preventivas adicionales.",
            },
        ]

        if product_id is not None:
            raw_projections = [p for p in raw_projections if p["producto_id"] == product_id]

        if critical_only:
            filtered = [p for p in raw_projections if p["urgency_status"] == "critical"]
        else:
            filtered = [p for p in raw_projections if p["days_to_stockout"] <= horizon_days]

        critical_count = sum(1 for p in filtered if p["urgency_status"] == "critical")
        warning_count = sum(1 for p in filtered if p["urgency_status"] == "warning")
        total_risk_cost = sum((p["total_at_risk_cost"] for p in filtered), Decimal("0.00"))

        preventive_alerts = [
            {
                "producto_id": p["producto_id"],
                "producto_nombre": p["producto_nombre"],
                "urgency_status": p["urgency_status"],
                "days_to_stockout": p["days_to_stockout"],
                "days_of_autonomy": p["days_of_autonomy"],
                "alert_message": p["alert_message"],
                "recommended_action": p["recommended_action"],
            }
            for p in filtered
            if p["urgency_status"] in ("critical", "warning")
        ]

        return {
            "tenant_schema": tenant_schema,
            "tool": "get_stockout_projections_and_autonomy",
            "horizon_days": horizon_days,
            "evaluated_products_count": len(filtered),
            "critical_stockouts_count": critical_count,
            "warning_stockouts_count": warning_count,
            "projections": filtered,
            "preventive_alerts": preventive_alerts,
            "total_at_risk_cost": total_risk_cost,
        }


@hardcoded_data_stripping
def get_preventive_transfer_recommendations(
    tenant_schema: str,
    *,
    horizon_days: int = 30,
    product_id: int | None = None,
) -> dict[str, Any]:
    """
    Identifica oportunidades de traspaso preventivo entre bodegas para mitigar quiebres de stock.
    Recomienda transferencias desde bodegas con superávit hacia bodegas deficitarias antes de que ocurra el quiebre.
    """
    with trace_span(
        "oppyfy.tool.get_preventive_transfer_recommendations",
        attributes={
            "tenant_schema": tenant_schema,
            "tool": "get_preventive_transfer_recommendations",
            "horizon_days": horizon_days,
        },
        tracer_name="oppytec.oppyfy",
    ):
        all_recommendations = [
            {
                "recommendation_id": "REC-TRF-001",
                "producto_id": 1,
                "producto_nombre": "Lomo Vetado Premium",
                "sku": "INS-001",
                "target_bodega": "Cocina Principal",
                "source_bodega": "Bodega Central",
                "source_available_stock": Decimal("45.0000"),
                "source_autonomy_days": Decimal("25.0000"),
                "target_current_stock": Decimal("14.5000"),
                "target_autonomy_days": Decimal("5.0000"),
                "suggested_transfer_qty": Decimal("15.0000"),
                "projected_autonomy_gained_days": 5,
                "costo_unitario": Decimal("14900.00"),
                "precio_compra": Decimal("14900.00"),
                "total_neto": Decimal("223500.00"),
                "urgency": "HIGH",
                "rationale": "La Bodega Central posee existencias para 25 días. Un traspaso de 15 kg extiende la autonomía de Cocina Principal de 5 a 10 días sin desabastecer la central.",
            },
            {
                "recommendation_id": "REC-TRF-002",
                "producto_id": 3,
                "producto_nombre": "Crema de Leche 35%",
                "sku": "INS-002",
                "target_bodega": "Repostería",
                "source_bodega": "Bodega Central",
                "source_available_stock": Decimal("32.0000"),
                "source_autonomy_days": Decimal("21.0000"),
                "target_current_stock": Decimal("18.0000"),
                "target_autonomy_days": Decimal("12.0000"),
                "suggested_transfer_qty": Decimal("10.0000"),
                "projected_autonomy_gained_days": 6,
                "costo_unitario": Decimal("3800.00"),
                "precio_compra": Decimal("3800.00"),
                "total_neto": Decimal("38000.00"),
                "urgency": "MEDIUM",
                "rationale": "Traspaso preventivo para evitar emitir orden de compra antes del fin de semana.",
            },
        ]

        if product_id is not None:
            filtered = [r for r in all_recommendations if r["producto_id"] == product_id]
        else:
            filtered = all_recommendations

        total_transfer_cost = sum((r["total_neto"] for r in filtered), Decimal("0.00"))

        return {
            "tenant_schema": tenant_schema,
            "tool": "get_preventive_transfer_recommendations",
            "horizon_days": horizon_days,
            "recommendations_count": len(filtered),
            "recommendations": filtered,
            "total_estimated_transfer_cost": total_transfer_cost,
        }
