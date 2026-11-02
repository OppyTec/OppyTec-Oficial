"""
Módulo de Herramientas Operativas Deterministas de OppyFy (JEV Layer 2).
"""
from __future__ import annotations

from src.modules.oppy_ai.application.operational_tools.canvas_tools import (
    render_canvas_chart,
    render_canvas_table,
)
from src.modules.oppy_ai.application.operational_tools.events_tools import (
    OPPYFY_EVENT_TOOL_SCHEMAS,
    analyze_event_supply_feasibility,
    check_salon_availability,
    estimate_event_budget_and_feasibility,
    query_upcoming_events,
)
from src.modules.oppy_ai.application.operational_tools.inventory_tools import (
    get_expiring_batches_fefo,
    get_stock_health_and_reorder_alerts,
)
from src.modules.oppy_ai.application.operational_tools.procurement_tools import (
    build_optimal_purchase_order_draft,
    evaluate_supplier_lead_times_and_price_drift,
)
from src.modules.oppy_ai.application.operational_tools.projection_tools import (
    get_preventive_transfer_recommendations,
    get_stockout_projections_and_autonomy,
)
from src.modules.oppy_ai.application.operational_tools.waste_tools import (
    analyze_waste_and_merma_impact,
    get_sales_and_food_cost_variance,
)

__all__ = [
    "OPPYFY_EVENT_TOOL_SCHEMAS",
    "analyze_event_supply_feasibility",
    "analyze_waste_and_merma_impact",
    "build_optimal_purchase_order_draft",
    "check_salon_availability",
    "estimate_event_budget_and_feasibility",
    "evaluate_supplier_lead_times_and_price_drift",
    "get_expiring_batches_fefo",
    "get_preventive_transfer_recommendations",
    "get_sales_and_food_cost_variance",
    "get_stock_health_and_reorder_alerts",
    "get_stockout_projections_and_autonomy",
    "query_upcoming_events",
    "render_canvas_chart",
    "render_canvas_table",
]
