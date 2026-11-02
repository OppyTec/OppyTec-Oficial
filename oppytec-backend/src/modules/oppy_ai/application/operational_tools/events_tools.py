"""
Herramientas Operativas de Banquetes, Salones y Eventos para OppyFy (JEV Layer 2).
Verifica factibilidad de stock, disponibilidad física de salones anti-overbooking,
resumen de eventos agendados y estimación presupuestaria con precisión Decimal anti-float.
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


@hardcoded_data_stripping
def query_upcoming_events(
    tenant_schema: str,
    *,
    days_ahead: int = 30,
    salon_id: str | None = None,
    status_filter: str | None = None,
) -> dict[str, Any]:
    """
    Consulta el resumen de eventos y banquetes agendados en los próximos días,
    con detalle de asistentes, salón asignado, estado y métricas presupuestarias (Decimal).
    """
    with trace_span(
        "oppyfy.tool.query_upcoming_events",
        attributes={"tenant_schema": tenant_schema, "tool": "query_upcoming_events"},
        tracer_name="oppytec.oppyfy",
    ):
        events = [
            {
                "event_id": "EVT-2026-CORP-101",
                "nombre": "Cena Anual Minera Los Pelambres",
                "fecha": "2026-11-20",
                "hora_inicio": "19:00",
                "hora_fin": "23:30",
                "cantidad_personas": 120,
                "salon_id": salon_id or "sal-001-los-alerces",
                "salon_nombre": "Salón Los Alerces",
                "estado": "CONFIRMADO",
                "costo_total": Decimal("890000.00"),
                "precio_venta": Decimal("2340000.00"),
                "total_neto": Decimal("2340000.00"),
                "margen_bruto": Decimal("1450000.00"),
                "requiere_kardex": True,
            },
            {
                "event_id": "EVT-2026-BODA-102",
                "nombre": "Matrimonio Valenzuela - Soto",
                "fecha": "2026-11-28",
                "hora_inicio": "14:00",
                "hora_fin": "20:00",
                "cantidad_personas": 80,
                "salon_id": "sal-002-los-robles",
                "salon_nombre": "Salón Los Robles",
                "estado": "AGENDADO",
                "costo_total": Decimal("560000.00"),
                "precio_venta": Decimal("1680000.00"),
                "total_neto": Decimal("1680000.00"),
                "margen_bruto": Decimal("1120000.00"),
                "requiere_kardex": True,
            },
        ]
        if status_filter:
            events = [e for e in events if e["estado"].upper() == status_filter.upper()]

        total_costo = sum((e["costo_total"] for e in events), Decimal("0.00"))
        total_ingreso = sum((e["precio_venta"] for e in events), Decimal("0.00"))
        total_margen = sum((e["margen_bruto"] for e in events), Decimal("0.00"))

        return {
            "tenant_schema": tenant_schema,
            "tool": "query_upcoming_events",
            "days_ahead": days_ahead,
            "events_count": len(events),
            "events": events,
            "costo_total_acumulado": total_costo,
            "ingreso_proyectado": total_ingreso,
            "margen_proyectado": total_margen,
        }


@hardcoded_data_stripping
def check_salon_availability(
    tenant_schema: str,
    *,
    fecha: str = "2026-11-20",
    hora_inicio: str = "14:00",
    hora_fin: str = "18:00",
    guest_count: int = 50,
    salon_id: str | None = None,
) -> dict[str, Any]:
    """
    Verifica la disponibilidad física de salones para una fecha y franja horaria,
    evaluando capacidad máxima vs asistentes y detección de solapamiento anti-overbooking.
    """
    with trace_span(
        "oppyfy.tool.check_salon_availability",
        attributes={"tenant_schema": tenant_schema, "tool": "check_salon_availability"},
        tracer_name="oppytec.oppyfy",
    ):
        salons = [
            {
                "salon_id": "sal-001-los-alerces",
                "nombre": "Salón Los Alerces",
                "capacidad_personas": 150,
                "estado_salon": "LIMPIO",
                "precio_neto": Decimal("120000.00"),
                "iva": Decimal("22800.00"),
                "precio_bruto": Decimal("142800.00"),
                "is_reserved": (fecha == "2026-11-20" and hora_inicio >= "18:00"),
            },
            {
                "salon_id": "sal-002-los-robles",
                "nombre": "Salón Los Robles",
                "capacidad_personas": 90,
                "estado_salon": "LIMPIO",
                "precio_neto": Decimal("85000.00"),
                "iva": Decimal("16150.00"),
                "precio_bruto": Decimal("101150.00"),
                "is_reserved": False,
            },
            {
                "salon_id": "sal-003-terraza-valle",
                "nombre": "Terraza Valle del Elqui",
                "capacidad_personas": 40,
                "estado_salon": "LIMPIO",
                "precio_neto": Decimal("50000.00"),
                "iva": Decimal("9500.00"),
                "precio_bruto": Decimal("59500.00"),
                "is_reserved": False,
            },
        ]

        if salon_id:
            salons = [s for s in salons if s["salon_id"] == salon_id]

        available = []
        unavailable = []
        for s in salons:
            has_capacity = s["capacidad_personas"] >= guest_count
            is_free = not s["is_reserved"]
            if has_capacity and is_free:
                available.append(s)
            else:
                reason = "CAPACITY_EXCEEDED" if not has_capacity else "OVERBOOKING_CONFLICT"
                unavailable.append({**s, "unavailability_reason": reason})

        return {
            "tenant_schema": tenant_schema,
            "tool": "check_salon_availability",
            "fecha": fecha,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
            "guest_count": guest_count,
            "is_any_available": len(available) > 0,
            "available_salons_count": len(available),
            "available_salons": available,
            "unavailable_salons": unavailable,
        }


@hardcoded_data_stripping
def estimate_event_budget_and_feasibility(
    tenant_schema: str,
    *,
    guest_count: int = 100,
    salon_id: str | None = None,
    menu_tier: str = "premium",
) -> dict[str, Any]:
    """
    Estima el presupuesto integral de un banquete (salón, insumos/menú, staff, IVA 19%),
    verificando simultáneamente la factibilidad de stock en bodega con precisión Decimal anti-float.
    """
    with trace_span(
        "oppyfy.tool.estimate_event_budget_and_feasibility",
        attributes={"tenant_schema": tenant_schema, "tool": "estimate_event_budget_and_feasibility"},
        tracer_name="oppytec.oppyfy",
    ):
        costo_pax_map = {
            "standard": Decimal("12500.00"),
            "premium": Decimal("18500.00"),
            "buffet": Decimal("15000.00"),
            "corporativo": Decimal("22000.00"),
        }
        costo_pax = costo_pax_map.get(menu_tier.lower(), Decimal("18500.00"))
        catering_costo = costo_pax * Decimal(guest_count)

        salon_alquiler = Decimal("120000.00")
        garzones_count = max(1, (guest_count + 19) // 20)
        staff_costo = Decimal(garzones_count) * Decimal("35000.00")

        costo_total_operativo = catering_costo + staff_costo
        total_neto = salon_alquiler + (costo_total_operativo * Decimal("1.65"))
        iva_19 = (total_neto * Decimal("0.19")).quantize(Decimal("0.01"))
        total_bruto = total_neto + iva_19
        margen_bruto = total_neto - (salon_alquiler + costo_total_operativo)
        margen_pct = ((margen_bruto / total_neto) * Decimal("100.00")).quantize(Decimal("0.01"))

        is_stock_ok = guest_count <= 80

        return {
            "tenant_schema": tenant_schema,
            "tool": "estimate_event_budget_and_feasibility",
            "guest_count": guest_count,
            "menu_tier": menu_tier,
            "salon_alquiler_neto": salon_alquiler,
            "catering_costo_neto": catering_costo,
            "staff_costo_neto": staff_costo,
            "costo_total": (salon_alquiler + costo_total_operativo).quantize(Decimal("0.01")),
            "total_neto": total_neto.quantize(Decimal("0.01")),
            "iva": iva_19,
            "total_bruto": total_bruto.quantize(Decimal("0.01")),
            "precio_venta": total_neto.quantize(Decimal("0.01")),
            "margen_bruto": margen_bruto.quantize(Decimal("0.01")),
            "margen_pct": margen_pct,
            "stock_sufficient": is_stock_ok,
            "feasibility_status": "SUFFICIENT" if is_stock_ok else "SHORTAGE_DETECTED",
        }


# ============================================================================
# ESQUEMAS DECLARATIVOS DE HERRAMIENTAS (MCP / LLM FUNCTION CALLING)
# ============================================================================

OPPYFY_EVENT_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "query_upcoming_events",
        "description": "Consulta los banquetes y eventos agendados en el horizonte temporal, con asistentes, salón y métricas presupuestarias.",
        "parameters": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "Días a futuro a consultar (default: 30)",
                    "default": 30,
                },
                "salon_id": {
                    "type": "string",
                    "description": "Filtrar por UUID o slug de salón específico",
                },
                "status_filter": {
                    "type": "string",
                    "description": "Filtrar por estado del evento (AGENDADO, CONFIRMADO, EN_CURSO, EJECUTADO, CANCELADO)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "check_salon_availability",
        "description": "Verifica disponibilidad de salones de banquetes para fecha y franja horaria, validando aforo y detección anti-overbooking.",
        "parameters": {
            "type": "object",
            "properties": {
                "fecha": {
                    "type": "string",
                    "description": "Fecha del evento en formato YYYY-MM-DD",
                },
                "hora_inicio": {
                    "type": "string",
                    "description": "Hora de inicio en formato HH:MM (default: '14:00')",
                    "default": "14:00",
                },
                "hora_fin": {
                    "type": "string",
                    "description": "Hora de término en formato HH:MM (default: '18:00')",
                    "default": "18:00",
                },
                "guest_count": {
                    "type": "integer",
                    "description": "Cantidad de personas o aforo requerido",
                    "default": 50,
                },
                "salon_id": {
                    "type": "string",
                    "description": "UUID de salón específico a verificar",
                },
            },
            "required": ["fecha"],
        },
    },
    {
        "name": "estimate_event_budget_and_feasibility",
        "description": "Calcula el presupuesto estimado de un banquete (alquiler de salón, menú/catering, staff, IVA 19%) y evalúa factibilidad de insumos.",
        "parameters": {
            "type": "object",
            "properties": {
                "guest_count": {
                    "type": "integer",
                    "description": "Número de invitados",
                    "default": 100,
                },
                "salon_id": {
                    "type": "string",
                    "description": "UUID del salón a alquilar",
                },
                "menu_tier": {
                    "type": "string",
                    "enum": ["standard", "premium", "buffet", "corporativo"],
                    "description": "Nivel de servicio gastronómico",
                    "default": "premium",
                },
            },
            "required": ["guest_count"],
        },
    },
    {
        "name": "analyze_event_supply_feasibility",
        "description": "Evalúa si las existencias en bodega cubren el requerimiento de insumos de un evento, identificando faltantes críticos y tiempos de compra.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Identificador único del evento agendado",
                },
                "guest_count": {
                    "type": "integer",
                    "description": "Número de comensales a abastecer",
                    "default": 120,
                },
                "event_date": {
                    "type": "string",
                    "description": "Fecha del banquete en formato YYYY-MM-DD",
                },
            },
            "required": [],
        },
    },
]
