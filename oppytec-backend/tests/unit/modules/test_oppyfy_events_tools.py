"""
Pruebas Unitarias de Integración de Herramientas de Banquetes y Eventos en OppyFy y Motor JEV
(`tests/unit/modules/test_oppyfy_events_tools.py`).

Verifica:
1. Ejecución determinista de herramientas operativas de banquetes (`query_upcoming_events`,
   `check_salon_availability`, `estimate_event_budget_and_feasibility`, `analyze_event_supply_feasibility`)
   con 100% Decimal anti-float.
2. Redacción física estricta de campos de costo financiero (`[REDACTED_COST]`) cuando `can_view_costs=False`
   y preservación de Decimal exacto cuando `can_view_costs=True`.
3. Clasificación JEV (Sistema 1) de intención semántica hacia herramientas de eventos con confianza >= 0.85.
4. Integración E2E en `MeteredAIService` con deducción atómica de créditos, auditoría RBAC y FinOps logs.
5. Validación estructural de los esquemas declarativos `OPPYFY_EVENT_TOOL_SCHEMAS`.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest

from src.adapters.ai.jev_adapter import (
    InMemoryJevTelemetrySink,
    InMemoryTelemetrySink,
    MeteredJevAdapter,
)
from src.adapters.ai.jev_protocol import JevChoiceResult
from src.adapters.ai.protocol import LLMProviderPort, LlmUsageRecord
from src.core.observability import clear_in_memory_oppyfy_metrics, get_in_memory_exporter
from src.modules.oppy_ai.application.metered_ai_service import (
    MeteredAIService,
    OppyfyQueryRequest,
)
from src.modules.oppy_ai.application.operational_tools import (
    OPPYFY_EVENT_TOOL_SCHEMAS,
    analyze_event_supply_feasibility,
    check_salon_availability,
    estimate_event_budget_and_feasibility,
    query_upcoming_events,
)
from src.modules.oppy_ai.application.rag_service import (
    InMemoryRedisSemanticCache,
    ThreeLayerRagService,
)
from src.modules.oppy_ai.application.tool_router import OppyfyToolRouter
from src.modules.oppy_ai.domain.credit_wallet import WorkerCreditWalletState
from src.modules.oppy_ai.domain.oppyfy_rbac import (
    ALLOWED_PROMPT_STATUS,
    OppyfyPermissionGrantSpec,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_telemetry() -> None:
    get_in_memory_exporter().clear()
    clear_in_memory_oppyfy_metrics()


class DummyLLMProvider(LLMProviderPort):
    """Proveedor LLM simulado para pruebas de integración con OppyFy."""

    def __init__(self, response_text: str = "Respuesta generada por OppyFy con datos de eventos.") -> None:
        self.response_text = response_text
        self.invocations: list[dict[str, Any]] = []

    def generate_minimalist_response(
        self,
        *,
        holding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tenant_schema: str,
        user_id: int,
        caller_feature: str,
        user_prompt: str,
        compact_context_payload: dict[str, str | int | Decimal | bool | list[str]],
        language_code: str = "es",
        brand_name: str = "OppyFy",
        thread_id: uuid.UUID | None = None,
    ) -> tuple[str, LlmUsageRecord]:
        rec = LlmUsageRecord(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema=tenant_schema,
            user_id=user_id,
            engine_tier="SYSTEM_2_LLM",
            caller_feature=caller_feature,
            model_name="gemini-3.8-flash",
            input_tokens=175,
            cached_tokens=0,
            output_tokens=60,
            provider_cost_usd=Decimal("0.000030"),
            provider_cost_clp=Decimal("28.50"),
            credits_deducted=Decimal("1.00"),
            request_duration_ms=110,
            thread_id=thread_id,
            api_success=True,
        )
        self.invocations.append({"prompt": user_prompt, "context": compact_context_payload})
        return self.response_text, rec


def test_events_tools_determinism_and_types() -> None:
    """Verifica que las 4 herramientas operativas de eventos retornen tipos consistentes y 100% Decimal."""
    schema = "tenant_test_events"

    # 1. query_upcoming_events
    events_data = query_upcoming_events(schema, days_ahead=30)
    assert events_data["tool"] == "query_upcoming_events"
    assert events_data["events_count"] >= 2
    assert isinstance(events_data["costo_total_acumulado"], Decimal)
    assert isinstance(events_data["ingreso_proyectado"], Decimal)
    assert isinstance(events_data["margen_proyectado"], Decimal)

    for ev in events_data["events"]:
        assert isinstance(ev["costo_total"], Decimal)
        assert isinstance(ev["precio_venta"], Decimal)
        assert isinstance(ev["margen_bruto"], Decimal)
        assert ev["estado"] in ("AGENDADO", "CONFIRMADO", "EN_CURSO", "EJECUTADO", "CANCELADO")

    # 2. check_salon_availability
    avail_data = check_salon_availability(schema, fecha="2026-11-20", hora_inicio="14:00", hora_fin="18:00", guest_count=60)
    assert avail_data["tool"] == "check_salon_availability"
    assert avail_data["is_any_available"] is True
    assert avail_data["available_salons_count"] >= 1
    for s in avail_data["available_salons"]:
        assert isinstance(s["precio_neto"], Decimal)
        assert isinstance(s["iva"], Decimal)
        assert isinstance(s["precio_bruto"], Decimal)
        assert s["capacidad_personas"] >= 60

    # 3. estimate_event_budget_and_feasibility
    budget_data = estimate_event_budget_and_feasibility(schema, guest_count=100, menu_tier="premium")
    assert budget_data["tool"] == "estimate_event_budget_and_feasibility"
    assert budget_data["guest_count"] == 100
    assert isinstance(budget_data["salon_alquiler_neto"], Decimal)
    assert isinstance(budget_data["catering_costo_neto"], Decimal)
    assert isinstance(budget_data["staff_costo_neto"], Decimal)
    assert isinstance(budget_data["total_neto"], Decimal)
    assert isinstance(budget_data["iva"], Decimal)
    assert isinstance(budget_data["total_bruto"], Decimal)
    assert isinstance(budget_data["margen_bruto"], Decimal)
    assert isinstance(budget_data["margen_pct"], Decimal)
    assert budget_data["feasibility_status"] == "SHORTAGE_DETECTED"  # > 80 pax

    # 4. analyze_event_supply_feasibility
    feasibility_ok = analyze_event_supply_feasibility(schema, guest_count=50)
    assert feasibility_ok["stock_sufficient"] is True
    assert feasibility_ok["feasibility_status"] == "SUFFICIENT"
    assert len(feasibility_ok["critical_shortages"]) == 0


def test_hardcoded_cost_redaction_in_events_tools() -> None:
    """Verifica que tool_router redacte físicamente los costos financieros cuando can_view_costs=False."""
    jev_adapter = MeteredJevAdapter()
    router = OppyfyToolRouter(jev_port=jev_adapter)
    schema = "tenant_test_events"

    choice_mock = JevChoiceResult(
        decision_id="OPPYFY_TOOL_ROUTER_INTENT",
        value="estimate_event_budget_and_feasibility",
        confidence=Decimal("0.96"),
        threshold=Decimal("0.85"),
        meets_threshold=True,
        fallback_required=False,
        alternatives=(),
        usage_record=None,  # type: ignore[arg-type]
    )

    # 1. Ejecución con can_view_costs=False (Redacción estricta)
    res_redacted = router.execute_hardcoded_tool(
        "estimate_event_budget_and_feasibility",
        tenant_schema=schema,
        can_view_costs=False,
        jev_choice=choice_mock,
    )
    assert res_redacted.costs_redacted is True
    payload = res_redacted.sanitized_payload
    assert payload["salon_alquiler_neto"] == "[REDACTED_COST]"
    assert payload["catering_costo_neto"] == "[REDACTED_COST]"
    assert payload["staff_costo_neto"] == "[REDACTED_COST]"
    assert payload["costo_total"] == "[REDACTED_COST]"
    assert payload["total_neto"] == "[REDACTED_COST]"
    assert payload["iva"] == "[REDACTED_COST]"
    assert payload["total_bruto"] == "[REDACTED_COST]"
    assert payload["margen_bruto"] == "[REDACTED_COST]"

    # Datos operativos no financieros permanecen visibles
    assert payload["guest_count"] == 100
    assert payload["menu_tier"] == "premium"
    assert payload["feasibility_status"] == "SHORTAGE_DETECTED"

    # 2. Ejecución con can_view_costs=True (Preservación de Decimal exacto)
    res_allowed = router.execute_hardcoded_tool(
        "estimate_event_budget_and_feasibility",
        tenant_schema=schema,
        can_view_costs=True,
        jev_choice=choice_mock,
    )
    assert res_allowed.costs_redacted is False
    payload_allowed = res_allowed.sanitized_payload
    assert isinstance(payload_allowed["salon_alquiler_neto"], Decimal)
    assert isinstance(payload_allowed["total_neto"], Decimal)
    assert isinstance(payload_allowed["total_bruto"], Decimal)
    assert isinstance(payload_allowed["margen_bruto"], Decimal)


def test_jev_intent_classification_routes_to_events_tools() -> None:
    """Verifica que MeteredJevAdapter clasifique intenciones semánticas hacia las herramientas de eventos."""
    jev = MeteredJevAdapter()
    h_id = uuid.uuid4()
    t_id = uuid.uuid4()
    schema = "tenant_test_events"

    # A. Consulta de eventos próximos
    res_upcoming = jev.decide_choice(
        decision_id="TOOL_ROUTE",
        prompt_or_input="¿Cuáles son los próximos eventos agendados y banquetes confirmados?",
        candidates=(
            "query_sales_summary",
            "query_stock_levels",
            "query_upcoming_events",
            "check_salon_availability",
        ),
        holding_id=h_id,
        tenant_id=t_id,
        tenant_schema=schema,
        user_id=1,
        caller_feature="test_events",
    )
    assert res_upcoming.value == "query_upcoming_events"
    assert res_upcoming.confidence >= Decimal("0.85")

    # B. Consulta de disponibilidad de salones
    res_salon = jev.decide_choice(
        decision_id="TOOL_ROUTE",
        prompt_or_input="Verifica la disponibilidad de salones libres y aforo para un evento el 20 de noviembre",
        candidates=(
            "query_stock_levels",
            "query_upcoming_events",
            "check_salon_availability",
            "estimate_event_budget_and_feasibility",
        ),
        holding_id=h_id,
        tenant_id=t_id,
        tenant_schema=schema,
        user_id=1,
        caller_feature="test_events",
    )
    assert res_salon.value == "check_salon_availability"
    assert res_salon.confidence >= Decimal("0.85")

    # C. Cotización / Presupuesto de banquete
    res_budget = jev.decide_choice(
        decision_id="TOOL_ROUTE",
        prompt_or_input="Cotizar presupuesto para un evento corporativo de 100 personas",
        candidates=(
            "query_sales_summary",
            "check_salon_availability",
            "estimate_event_budget_and_feasibility",
            "analyze_event_supply_feasibility",
        ),
        holding_id=h_id,
        tenant_id=t_id,
        tenant_schema=schema,
        user_id=1,
        caller_feature="test_events",
    )
    assert res_budget.value == "estimate_event_budget_and_feasibility"
    assert res_budget.confidence >= Decimal("0.85")

    # D. Factibilidad de insumos / stock para banquete
    res_stock = jev.decide_choice(
        decision_id="TOOL_ROUTE",
        prompt_or_input="Evaluar la factibilidad de insumos en bodega para cubrir el banquete de 120 personas",
        candidates=(
            "query_stock_levels",
            "analyze_event_supply_feasibility",
            "estimate_event_budget_and_feasibility",
        ),
        holding_id=h_id,
        tenant_id=t_id,
        tenant_schema=schema,
        user_id=1,
        caller_feature="test_events",
    )
    assert res_stock.value == "analyze_event_supply_feasibility"
    assert res_stock.confidence >= Decimal("0.85")


def test_metered_ai_service_full_query_with_events_and_finops() -> None:
    """Verifica el flujo E2E en MeteredAIService para una consulta de eventos con FinOps y deducción de créditos."""
    jev_adapter = MeteredJevAdapter()
    tool_router = OppyfyToolRouter(jev_port=jev_adapter)
    rag_service = ThreeLayerRagService(semantic_cache=InMemoryRedisSemanticCache())
    llm_sink = InMemoryTelemetrySink()
    llm_provider = DummyLLMProvider()

    metered_service = MeteredAIService(
        jev_port=jev_adapter,
        llm_port=llm_provider,
        rag_service=rag_service,
        tool_router=tool_router,
        telemetry_sink=llm_sink,
    )

    holding_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    user_id = 77

    wallet = WorkerCreditWalletState(
        user_id=user_id,
        allocated_credits=Decimal("150.00"),
        consumed_credits=Decimal("15.00"),
        is_oppyfy_enabled=True,
    )

    grant = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=3,
        subdomain_slug="abastecimiento_y_eventos",
        user_id=user_id,
        effect="ALLOW",
        can_query=True,
        can_view_costs=False,
    )

    req = OppyfyQueryRequest(
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_demo_events",
        user_id=user_id,
        role_ids=(1,),
        hierarchy_rank=2,
        prompt_text="¿Cuáles son los eventos agendados y banquetes confirmados para este mes?",
        wallet=wallet,
        grants=(grant,),
        subdomain_id_by_slug={"abastecimiento_y_eventos": 3},
        thread_id=thread_id,
        prior_thread_tokens=150,
        estimated_credit_cost=Decimal("1.00"),
    )

    response = metered_service.execute_oppyfy_query(req)

    # 1. Verifica estado de respuesta y herramienta enrutada
    assert response.allowed is True
    assert response.status_code == ALLOWED_PROMPT_STATUS
    assert response.routed_tool == "query_upcoming_events"
    assert response.tool_execution is not None
    assert response.tool_execution.costs_redacted is True

    # 2. Verifica deducción atómica de créditos (1.00 generación + 0.20 JEV firewall + 0.20 JEV router)
    assert response.credits_deducted == Decimal("1.40")
    assert response.updated_wallet.consumed_credits == Decimal("16.40")
    assert response.updated_wallet.remaining_credits == Decimal("133.60")

    # 3. Verifica telemetría FinOps obligatoria
    assert len(response.llm_usage_records) == 3
    assert any(rec.engine_tier == "SYSTEM_1_JEV" for rec in response.llm_usage_records)
    assert any(rec.engine_tier == "SYSTEM_2_LLM" for rec in response.llm_usage_records)
    assert len(llm_sink.records) == 3


def test_oppyfy_event_tool_schemas_specification() -> None:
    """Verifica que los esquemas declarativos de herramientas cumplan el formato estándar MCP / OpenAPI."""
    assert len(OPPYFY_EVENT_TOOL_SCHEMAS) == 4
    tool_names = {t["name"] for t in OPPYFY_EVENT_TOOL_SCHEMAS}
    expected_names = {
        "query_upcoming_events",
        "check_salon_availability",
        "estimate_event_budget_and_feasibility",
        "analyze_event_supply_feasibility",
    }
    assert tool_names == expected_names

    for schema in OPPYFY_EVENT_TOOL_SCHEMAS:
        assert "name" in schema
        assert "description" in schema
        assert len(schema["description"]) > 10
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"
        assert "properties" in schema["parameters"]
        assert "required" in schema["parameters"]
