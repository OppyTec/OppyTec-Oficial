"""
Pruebas Unitarias de Integración de Proyección en el Asistente OppyFy y Motor JEV
(`tests/unit/modules/test_oppyfy_projection_tools.py`).

Verifica:
1. Ejecución determinista de herramientas de proyección (`get_stockout_projections_and_autonomy`,
   `get_preventive_transfer_recommendations`) con 100% Decimal anti-float.
2. Redacción física estricta de campos de costo (`[REDACTED_COST]`) cuando `can_view_costs=False`
   y preservación de Decimal exacto cuando `can_view_costs=True`.
3. Clasificación JEV (Sistema 1) de intención semántica hacia herramientas de proyección.
4. Integración E2E en `MeteredAIService` con deducción atómica de créditos, auditoría RBAC y FinOps logs.
5. Ingesta y búsqueda en RAG Capa 3 de la especificación funcional `specs/business-domain/projections-and-stockouts.business.spec.md`.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path
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
    ModelConfigRegistry,
    ModelTariff,
    OppyfyQueryRequest,
)
from src.modules.oppy_ai.application.operational_tools import (
    get_preventive_transfer_recommendations,
    get_stockout_projections_and_autonomy,
)
from src.modules.oppy_ai.application.rag_service import (
    BusinessSpecChunkRecord,
    InMemoryRedisSemanticCache,
    ThreeLayerRagService,
)
from src.modules.oppy_ai.application.tool_router import OppyfyToolRouter
from src.modules.oppy_ai.domain.credit_wallet import WorkerCreditWalletState
from src.modules.oppy_ai.domain.oppyfy_rbac import (
    ALLOWED_PROMPT_STATUS,
    BLOCKED_UNAUTHORIZED_PROMPT,
    OppyfyPermissionGrantSpec,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_telemetry() -> None:
    get_in_memory_exporter().clear()
    clear_in_memory_oppyfy_metrics()


class DummyLLMProvider(LLMProviderPort):
    """Proveedor LLM simulado para pruebas de integración con OppyFy."""

    def __init__(self, response_text: str = "Respuesta generada por OppyFy con datos de proyección.") -> None:
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
            input_tokens=180,
            cached_tokens=0,
            output_tokens=65,
            provider_cost_usd=Decimal("0.000035"),
            provider_cost_clp=Decimal("33.25"),
            credits_deducted=Decimal("1.00"),
            request_duration_ms=120,
            thread_id=thread_id,
            api_success=True,
        )
        self.invocations.append({"prompt": user_prompt, "context": compact_context_payload})
        return self.response_text, rec


def test_get_stockout_projections_and_autonomy_determinism_and_types() -> None:
    """Verifica que get_stockout_projections_and_autonomy entregue datos consistentes y 100% Decimal."""
    data = get_stockout_projections_and_autonomy("tenant_demo", horizon_days=30)

    assert data["tool"] == "get_stockout_projections_and_autonomy"
    assert data["horizon_days"] == 30
    assert data["critical_stockouts_count"] >= 1
    assert data["warning_stockouts_count"] >= 1
    assert len(data["projections"]) >= 3
    assert len(data["preventive_alerts"]) >= 2
    assert isinstance(data["total_at_risk_cost"], Decimal)

    for item in data["projections"]:
        assert isinstance(item["current_stock"], Decimal)
        assert isinstance(item["stock_minimo"], Decimal)
        assert isinstance(item["daily_consumption_rate"], Decimal)
        assert isinstance(item["days_of_autonomy"], Decimal)
        assert isinstance(item["costo_unitario"], Decimal)
        assert isinstance(item["costo_total_quiebre"], Decimal)
        assert item["urgency_status"] in ("critical", "warning", "normal")
        assert item["days_to_stockout"] >= 0


def test_get_preventive_transfer_recommendations_determinism_and_types() -> None:
    """Verifica que get_preventive_transfer_recommendations entregue sugerencias tipadas con Decimal."""
    data = get_preventive_transfer_recommendations("tenant_demo", horizon_days=30)

    assert data["tool"] == "get_preventive_transfer_recommendations"
    assert data["recommendations_count"] >= 1
    assert isinstance(data["total_estimated_transfer_cost"], Decimal)

    for rec in data["recommendations"]:
        assert "target_bodega" in rec
        assert "source_bodega" in rec
        assert isinstance(rec["source_available_stock"], Decimal)
        assert isinstance(rec["suggested_transfer_qty"], Decimal)
        assert isinstance(rec["costo_unitario"], Decimal)
        assert isinstance(rec["total_neto"], Decimal)
        assert rec["projected_autonomy_gained_days"] > 0
        assert "rationale" in rec


def test_hardcoded_cost_redaction_in_projection_tools() -> None:
    """Verifica que tool_router redacte físicamente los costos cuando can_view_costs=False."""
    jev_adapter = MeteredJevAdapter()
    router = OppyfyToolRouter(jev_port=jev_adapter)

    # 1. Ejecución con can_view_costs=False
    choice_mock = JevChoiceResult(
        decision_id="OPPYFY_TOOL_ROUTER_INTENT",
        value="get_stockout_projections_and_autonomy",
        confidence=Decimal("0.96"),
        threshold=Decimal("0.85"),
        meets_threshold=True,
        fallback_required=False,
        alternatives=(("get_stockout_projections_and_autonomy", Decimal("0.96")),),
        usage_record=None,  # type: ignore[arg-type]
    )

    res_redacted = router.execute_hardcoded_tool(
        "get_stockout_projections_and_autonomy",
        tenant_schema="tenant_demo",
        can_view_costs=False,
        jev_choice=choice_mock,
    )

    assert res_redacted.costs_redacted is True
    payload = res_redacted.sanitized_payload
    assert payload["total_at_risk_cost"] == "[REDACTED_COST]"

    for proj in payload["projections"]:
        assert proj["costo_unitario"] == "[REDACTED_COST]"
        assert proj["precio_compra"] == "[REDACTED_COST]"
        assert proj["total_neto"] == "[REDACTED_COST]"
        assert proj["costo_total_quiebre"] == "[REDACTED_COST]"
        assert proj["total_at_risk_cost"] == "[REDACTED_COST]"
        # Métricas operativas no financieras deben conservarse
        assert isinstance(proj["current_stock"], Decimal)
        assert isinstance(proj["days_of_autonomy"], Decimal)
        assert isinstance(proj["days_to_stockout"], int)

    # 2. Ejecución con can_view_costs=True
    res_allowed = router.execute_hardcoded_tool(
        "get_stockout_projections_and_autonomy",
        tenant_schema="tenant_demo",
        can_view_costs=True,
        jev_choice=choice_mock,
    )

    assert res_allowed.costs_redacted is False
    payload_allowed = res_allowed.sanitized_payload
    assert isinstance(payload_allowed["total_at_risk_cost"], Decimal)
    for proj in payload_allowed["projections"]:
        assert isinstance(proj["costo_unitario"], Decimal)
        assert isinstance(proj["total_at_risk_cost"], Decimal)


def test_jev_intent_classification_routes_to_projection_tools() -> None:
    """Verifica que MeteredJevAdapter clasifique preguntas sobre quiebre y proyecciones hacia la herramienta correcta."""
    jev_adapter = MeteredJevAdapter()
    holding_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    # Consulta de quiebre de stock proyectado
    res_proj = jev_adapter.decide_choice(
        decision_id="OPPYFY_TOOL_ROUTER_INTENT",
        prompt_or_input="¿Cuáles productos tienen quiebre de stock proyectado y cuántos días de autonomía les quedan?",
        candidates=(
            "query_stock_levels",
            "get_stock_health_and_reorder_alerts",
            "get_stockout_projections_and_autonomy",
            "get_preventive_transfer_recommendations",
        ),
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_demo",
        user_id=1,
        caller_feature="test_oppyfy",
    )
    assert res_proj.value == "get_stockout_projections_and_autonomy"
    assert res_proj.confidence >= Decimal("0.85")

    # Consulta de traspaso preventivo entre bodegas
    res_trf = jev_adapter.decide_choice(
        decision_id="OPPYFY_TOOL_ROUTER_INTENT",
        prompt_or_input="Recomienda un traspaso preventivo entre bodegas para mitigar desabastecimiento",
        candidates=(
            "query_stock_levels",
            "get_stock_health_and_reorder_alerts",
            "get_stockout_projections_and_autonomy",
            "get_preventive_transfer_recommendations",
        ),
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_demo",
        user_id=1,
        caller_feature="test_oppyfy",
    )
    assert res_trf.value == "get_preventive_transfer_recommendations"
    assert res_trf.confidence >= Decimal("0.85")


def test_metered_ai_service_full_query_with_projection_and_finops() -> None:
    """Verifica el flujo E2E en MeteredAIService para una consulta sobre proyecciones con FinOps y deducción de créditos."""
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
    user_id = 42

    wallet = WorkerCreditWalletState(
        user_id=user_id,
        allocated_credits=Decimal("100.00"),
        consumed_credits=Decimal("10.00"),
        is_oppyfy_enabled=True,
    )

    grant = OppyfyPermissionGrantSpec(
        grant_id=uuid.uuid4(),
        subdomain_id=4,
        subdomain_slug="proyeccion_y_quiebres",
        user_id=user_id,
        effect="ALLOW",
        can_query=True,
        can_view_costs=False,  # Sin acceso a ver costos financieros
    )

    req = OppyfyQueryRequest(
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_demo",
        user_id=user_id,
        role_ids=(1,),
        hierarchy_rank=2,
        prompt_text="¿Cuáles son los productos con quiebre de stock proyectado en los próximos 15 días y su autonomía?",
        wallet=wallet,
        grants=(grant,),
        subdomain_id_by_slug={"proyeccion_y_quiebres": 4},
        thread_id=thread_id,
        prior_thread_tokens=200,
        estimated_credit_cost=Decimal("1.00"),
    )

    response = metered_service.execute_oppyfy_query(req)

    # 1. Verifica estado de respuesta y herramienta enrutada
    assert response.allowed is True
    assert response.status_code == ALLOWED_PROMPT_STATUS
    assert response.routed_tool == "get_stockout_projections_and_autonomy"
    assert response.tool_execution is not None
    assert response.tool_execution.costs_redacted is True

    # 2. Verifica deducción atómica de créditos de la billetera (1.00 generación + 0.20 JEV firewall + 0.20 JEV router)
    assert response.credits_deducted == Decimal("1.40")
    assert response.updated_wallet.consumed_credits == Decimal("11.40")
    assert response.updated_wallet.remaining_credits == Decimal("88.60")

    # 3. Verifica telemetría FinOps obligatoria (2 invocaciones Sistema 1 JEV + 1 Sistema 2 LLM)
    assert len(response.llm_usage_records) == 3
    assert any(rec.engine_tier == "SYSTEM_1_JEV" for rec in response.llm_usage_records)
    assert any(rec.engine_tier == "SYSTEM_2_LLM" for rec in response.llm_usage_records)
    assert len(llm_sink.records) == 3
    for usage in response.llm_usage_records:
        assert isinstance(usage.provider_cost_usd, Decimal)
        assert isinstance(usage.credits_deducted, Decimal)


def test_rag_layer3_indexes_projection_business_spec(monorepo_root: Path) -> None:
    """Verifica que la especificación de negocio de proyección sea compatible con el RAG Layer 3."""
    spec_path = monorepo_root / "specs" / "business-domain" / "projections-and-stockouts.business.spec.md"
    assert spec_path.exists(), f"El archivo {spec_path} debe existir."

    content = spec_path.read_text(encoding="utf-8")
    assert "Horizontes Temporales de Proyección" in content
    assert "Días de Autonomía" in content
    assert "Primero en Vencer, Primero en Salir (FEFO)" in content
    assert "Recomendaciones de Traspaso Preventivo" in content

    # Debe registrarse limpiamente en ThreeLayerRagService
    rag_service = ThreeLayerRagService()
    rag_service.register_business_spec_chunk(
        BusinessSpecChunkRecord(
            chunk_id=uuid.uuid4(),
            spec_rel_path="specs/business-domain/projections-and-stockouts.business.spec.md",
            module_slug="projections",
            content_markdown=content,
        )
    )

    # Construcción de contexto RAG Capa 3
    bundle = rag_service.build_three_layer_context(
        user_prompt="¿Cómo se calculan los días de autonomía y la rotación FEFO en proyecciones?",
        authorized_subdomain_id=4,
        user_id=1,
        routed_tool_result=None,
    )
    assert len(bundle.layer3a_business_spec_chunks) >= 1
    assert "Horizontes Temporales de Proyección" in bundle.layer3a_business_spec_chunks[0]
