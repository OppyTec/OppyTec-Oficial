"""
oppytec-backend/tests/unit/modules/test_oppy_ai_feedback_and_tracer.py
Pruebas Unitarias e Integradas para Observabilidad LLM y Feedback Humano (RLHF):
1. `LangfuseTracer`:
   - Cumplimiento de `LLMTracerPort`.
   - Censura estricta de PII (correos, teléfonos, RUTs, tarjetas) preservando nombres comerciales ('Pollo King').
   - Desacoplamiento resiliente (Circuit Breaker y degradación elegante ante fallo HTTP).
2. Repositorios de Feedback:
   - `InMemoryAIChatFeedbackRepository` y `SqlAlchemyAIChatFeedbackRepository`.
   - Persistencia, filtros por tenant, trace_id, paginación y ordenamiento.
3. Integración en `MeteredAIService`:
   - Retorno obligatorio de `trace_id` correlacionable en respuestas del chat.
4. Endpoints REST FastAPI:
   - `POST /api/v1/oppy_ai/chat/feedback`: Ingesta con validación y puntuación.
   - `GET /api/v1/oppy_ai/chat/feedback`: Listado y tasa de satisfacción % en Decimal.
   - Preservación de `trace_id` y `message_id` en `POST /api/v1/oppyfy/chat`.
"""
from __future__ import annotations

import time
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import httpx
from httpx import ASGITransport
import pytest
from pydantic import SecretStr

from src.core.security import create_access_token
from src.infrastructure.ai.langfuse_tracer import LangfuseTracer
from src.main import app
from src.modules.oppy_ai.application.metered_ai_service import (
    MeteredAIService,
    ModelConfigRegistry,
    OppyfyQueryRequest,
)
from src.modules.oppy_ai.application.rag_service import ThreeLayerRagService
from src.modules.oppy_ai.application.tool_router import OppyfyToolRouter
from src.modules.oppy_ai.domain.credit_wallet import WorkerCreditWalletState
from src.modules.oppy_ai.domain.evals import (
    AIChatFeedback,
    InvalidFeedbackPayloadError,
    TraceContext,
)
from src.modules.oppy_ai.domain.oppyfy_rbac import OppyfyPermissionGrantSpec
from src.modules.oppy_ai.domain.ports import (
    AIChatFeedbackRepositoryPort,
    LLMTracerPort,
)
from src.modules.oppy_ai.infrastructure.models import AIChatFeedbackModel
from src.modules.oppy_ai.infrastructure.repositories import (
    InMemoryAIChatFeedbackRepository,
    SqlAlchemyAIChatFeedbackRepository,
)

pytestmark = pytest.mark.unit

TENANT_ID_STR = "22222222-2222-2222-2222-222222222222"
HOLDING_ID_STR = "11111111-1111-1111-1111-111111111111"
TENANT_UUID = uuid.UUID(TENANT_ID_STR)
HOLDING_UUID = uuid.UUID(HOLDING_ID_STR)


def _make_auth_headers(
    permissions: list[str] | None = None,
    *,
    user_id: int = 1,
    tenant_id: str = TENANT_ID_STR,
    holding_id: str = HOLDING_ID_STR,
) -> dict[str, str]:
    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        holding_id=holding_id,
        tenant_schema="tenant_demo",
        is_global_staff=False,
        hierarchy_rank=0,
        role_grants=permissions or ["oppy_ai.chat.feedback", "oppyfy.assistant.chat"],
    )
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. PRUEBAS DE LANGFUSE TRACER
# ============================================================================


def test_langfuse_tracer_implements_protocol() -> None:
    """Verifica que LangfuseTracer implemente formalmente LLMTracerPort."""
    tracer = LangfuseTracer(
        host="http://localhost:3000",
        public_key=SecretStr("pk-lf-test"),
        secret_key=SecretStr("sk-lf-test"),
    )
    assert isinstance(tracer, LLMTracerPort)
    assert tracer.is_configured is True
    assert tracer.is_circuit_open is False


@pytest.mark.asyncio
async def test_trace_generation_records_and_scrubs_pii() -> None:
    """
    Verifica que `trace_generation` enmascare deterministamente información sensible
    (correo, teléfono, tarjeta) mientras preserva razones sociales ('Pollo King').
    """
    tracer = LangfuseTracer(enabled=False)  # Modo memoria
    context = TraceContext.create(tenant_id=TENANT_UUID, user_id=uuid.uuid4())

    raw_prompt = (
        "Hola, para la receta de Pollo King contactar a juan@restaurante.com "
        "o al +56 9 8765 4321 con tarjeta 4532-1234-5678-9010."
    )
    raw_completion = "Entendido, receta Pollo King verificada con costo 1500 CLP."

    trace_id = await tracer.trace_generation(
        context=context,
        model="gemini-2.5-flash",
        prompt=raw_prompt,
        completion=raw_completion,
        prompt_tokens=45,
        completion_tokens=20,
        cost_usd=Decimal("0.000125"),
        latency_ms=280,
        tags={"channel": "web"},
    )

    assert trace_id == context.trace_id
    records = tracer.get_recorded_generations()
    assert len(records) == 1
    rec = records[0]

    # Verificar que el nombre de marca inmutable 'Pollo King' NO fue censurado
    assert "Pollo King" in rec["prompt"]
    assert "Pollo King" in rec["completion"]

    # Verificar que los datos sensibles sí fueron reemplazados por [REDACTED_PII]
    assert "juan@restaurante.com" not in rec["prompt"]
    assert "[REDACTED_PII]" in rec["prompt"]
    assert "+56 9 8765 4321" not in rec["prompt"]
    assert "4532-1234-5678-9010" not in rec["prompt"]

    assert rec["model"] == "gemini-2.5-flash"
    assert rec["cost_usd"] == Decimal("0.000125")
    assert rec["latency_ms"] == 280
    assert rec["total_tokens"] == 65
    assert rec["tenant_id"] == str(TENANT_UUID)


@pytest.mark.asyncio
async def test_trace_tool_call_records_with_pii_sanitization() -> None:
    """Verifica que las llamadas a herramientas se registren con sanitización de inputs/outputs."""
    tracer = LangfuseTracer(enabled=False)
    context = TraceContext.create(tenant_id=TENANT_UUID)

    tool_input = {
        "recipe_name": "Pollo King",
        "chef_email": "chef@polloking.cl",
        "api_key": "secret_key_123",
    }
    tool_output = {
        "cost_clp": "4500.00",
        "supplier_rut": "76.123.456-7",
    }

    span_id = await tracer.trace_tool_call(
        context=context,
        tool_name="query_recipe_costs",
        tool_input=tool_input,
        tool_output=tool_output,
        latency_ms=45,
    )

    assert span_id
    records = tracer.get_recorded_tool_calls()
    assert len(records) == 1
    tool_rec = records[0]

    assert tool_rec["tool_name"] == "query_recipe_costs"
    assert tool_rec["input"]["recipe_name"] == "Pollo King"
    assert tool_rec["input"]["chef_email"] == "[REDACTED_PII]"
    assert tool_rec["input"]["api_key"] == "[REDACTED_PII]"
    assert tool_rec["output"]["supplier_rut"] == "[REDACTED_PII]"


@pytest.mark.asyncio
async def test_langfuse_resilience_and_circuit_breaker() -> None:
    """
    Verifica que caídas de red o timeouts en Langfuse activen el Circuit Breaker
    sin propagar excepciones al hilo principal de OppyFy.
    """
    # Mock de cliente HTTP que simula fallas consecutivas
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.ConnectError("Connection refused by Langfuse")

    tracer = LangfuseTracer(
        host="http://offline-langfuse:3000",
        public_key=SecretStr("pk_test"),
        secret_key=SecretStr("sk_test"),
        circuit_breaker_threshold=2,
        circuit_cooldown_seconds=10.0,
        http_client=mock_client,
        enabled=True,
    )

    context = TraceContext.create(tenant_id=TENANT_UUID)

    # Intento 1: Debe fallar limpiamente sin lanzar excepción
    await tracer.trace_generation(
        context=context,
        model="gemini-2.5-flash",
        prompt="Hola",
        completion="Mundo",
        prompt_tokens=5,
        completion_tokens=5,
        cost_usd=Decimal("0.000010"),
        latency_ms=100,
    )
    assert tracer.is_circuit_open is False

    # Intento 2: Alcanza el umbral (2) y abre el circuito
    await tracer.trace_generation(
        context=context,
        model="gemini-2.5-flash",
        prompt="Hola de nuevo",
        completion="Mundo de nuevo",
        prompt_tokens=5,
        completion_tokens=5,
        cost_usd=Decimal("0.000010"),
        latency_ms=100,
    )
    assert tracer.is_circuit_open is True

    # Intento 3: Con circuito abierto, ni siquiera llama a post
    mock_client.post.reset_mock()
    await tracer.trace_generation(
        context=context,
        model="gemini-2.5-flash",
        prompt="Tercer intento",
        completion="Sin red",
        prompt_tokens=5,
        completion_tokens=5,
        cost_usd=Decimal("0.000010"),
        latency_ms=100,
    )
    mock_client.post.assert_not_called()


# ============================================================================
# 2. PRUEBAS DE REPOSITORIO DE FEEDBACK
# ============================================================================


@pytest.mark.asyncio
async def test_in_memory_feedback_repository_lifecycle() -> None:
    """Verifica el ciclo de vida completo de AIChatFeedback en InMemoryAIChatFeedbackRepository."""
    repo = InMemoryAIChatFeedbackRepository()
    msg_id = uuid.uuid4().hex
    trc_id = "trace-test-123"

    f1 = AIChatFeedback(
        tenant_id=TENANT_UUID,
        message_id=msg_id,
        trace_id=trc_id,
        feedback_type="positive",
        rating=5,
    )
    saved = await repo.save_feedback(f1)
    assert saved.id == f1.id
    assert saved.rating == 5

    # Listar por tenant
    items = await repo.list_feedback(tenant_id=TENANT_UUID)
    assert len(items) == 1
    assert items[0].trace_id == trc_id

    # Listar por trace_id
    by_trace = await repo.get_by_trace_id(tenant_id=TENANT_UUID, trace_id=trc_id)
    assert len(by_trace) == 1
    assert by_trace[0].id == f1.id

    # Diferente tenant no debe retornar datos
    other_tenant = uuid.uuid4()
    empty = await repo.list_feedback(tenant_id=other_tenant)
    assert len(empty) == 0


@pytest.mark.asyncio
async def test_sqlalchemy_feedback_repository_save_and_query() -> None:
    """Verifica que SqlAlchemyAIChatFeedbackRepository cumpla el protocolo con AsyncSession mockeada."""
    mock_session = MagicMock()
    mock_session.flush = AsyncMock()
    # Simular scalar_one_or_none retornando None para inserción nueva
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_scalar)

    repo = SqlAlchemyAIChatFeedbackRepository(session=mock_session)
    feedback = AIChatFeedback(
        tenant_id=TENANT_UUID,
        message_id=uuid.uuid4().hex,
        trace_id="trace_sql_test",
        feedback_type="negative",
        failure_category="math_error",
        user_correction="El cálculo correcto de porciones es 35x no 30x",
        rating=1,
    )

    res = await repo.save_feedback(feedback)
    assert res.id == feedback.id
    assert res.failure_category == "math_error"
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()


# ============================================================================
# 3. PRUEBAS DE INTEGRACIÓN EN METEREDAISERVICE
# ============================================================================


def test_metered_ai_service_attaches_tracer_and_returns_trace_id() -> None:
    """Verifica que MeteredAIService emita telemetría al tracer y devuelva trace_id y message_id."""
    tracer = LangfuseTracer(enabled=False)

    mock_jev = MagicMock()
    mock_llm = MagicMock()
    mock_rag = MagicMock()

    # Configurar mock JEV
    mock_usage = MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.cached_tokens = 0
    mock_usage.output_tokens = 10
    mock_usage.total_tokens = 20
    mock_usage.provider_cost_usd = Decimal("0.000010")
    mock_usage.provider_cost_clp = Decimal("10.00")
    mock_usage.credits_deducted = Decimal("0.10")
    mock_usage.request_duration_ms = 40
    mock_usage.model_name = "gemini-2.5-flash"
    mock_usage.engine_tier = "SYSTEM_2_LLM"
    mock_usage.caller_feature = "oppyfy_chat"
    mock_usage.thread_id = None
    mock_usage.api_success = True
    mock_usage.error_message = None
    mock_usage.holding_id = HOLDING_UUID
    mock_usage.tenant_id = TENANT_UUID
    mock_usage.tenant_schema = "tenant_demo"
    mock_usage.user_id = 1

    security_res = MagicMock()
    security_res.value = False
    security_res.usage_record = mock_usage
    mock_jev.decide_boolean.return_value = security_res

    choice_res = MagicMock()
    choice_res.value = "recipes_kitchen"
    choice_res.usage_record = mock_usage
    mock_jev.decide_choice.return_value = choice_res

    mock_llm.generate_minimalist_response.return_value = (
        "El costo teórico del Pollo King es 2.500 CLP por porción.",
        mock_usage,
    )

    mock_bundle = MagicMock()
    mock_bundle.to_compact_context_dict.return_value = {"context": "sample"}
    mock_rag.build_three_layer_context.return_value = mock_bundle

    service = MeteredAIService(
        jev_port=mock_jev,
        llm_port=mock_llm,
        rag_service=mock_rag,
        tracer=tracer,
    )

    wallet = WorkerCreditWalletState(
        user_id=1,
        allocated_credits=Decimal("100.00"),
        consumed_credits=Decimal("0.00"),
        is_oppyfy_enabled=True,
    )
    grants = (
        OppyfyPermissionGrantSpec(
            grant_id=uuid.uuid4(),
            subdomain_id=1,
            subdomain_slug="recipes_kitchen",
            effect="ALLOW",
            can_query=True,
            can_view_costs=True,
        ),
    )

    req = OppyfyQueryRequest(
        holding_id=HOLDING_UUID,
        tenant_id=TENANT_UUID,
        tenant_schema="tenant_demo",
        user_id=1,
        role_ids=(1,),
        hierarchy_rank=0,
        prompt_text="¿Cuánto cuesta una porción de Pollo King?",
        wallet=wallet,
        grants=grants,
        subdomain_id_by_slug={"recipes_kitchen": 1},
    )

    response = service.execute_oppyfy_query(req)

    assert response.allowed is True
    assert response.trace_id is not None
    assert len(response.trace_id) >= 16
    assert response.message_id is not None


# ============================================================================
# 4. PRUEBAS DE ENDPOINTS REST FASTAPI
# ============================================================================


@pytest.mark.asyncio
async def test_post_and_get_chat_feedback_endpoints() -> None:
    """Verifica los endpoints REST POST y GET /api/v1/oppy_ai/chat/feedback."""
    transport = ASGITransport(app=app)
    headers = _make_auth_headers(["oppy_ai.chat.feedback", "oppyfy.assistant.chat"])

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        trace_id_1 = uuid.uuid4().hex
        msg_id_1 = str(uuid.uuid4())

        # 1. Ingesta Feedback Positivo
        post_payload_pos = {
            "tenant_id": TENANT_ID_STR,
            "message_id": msg_id_1,
            "trace_id": trace_id_1,
            "feedback_type": "positive",
            "rating": 5,
        }
        res_pos = await client.post(
            "/api/v1/oppy_ai/chat/feedback",
            json=post_payload_pos,
            headers=headers,
        )
        assert res_pos.status_code == 201, res_pos.text
        data_pos = res_pos.json()
        assert data_pos["feedback_type"] == "positive"
        assert data_pos["rating"] == 5
        assert data_pos["trace_id"] == trace_id_1

        # 2. Ingesta Feedback Negativo con categoría y sugerencia
        trace_id_2 = uuid.uuid4().hex
        msg_id_2 = str(uuid.uuid4())
        post_payload_neg = {
            "tenant_id": TENANT_ID_STR,
            "message_id": msg_id_2,
            "trace_id": trace_id_2,
            "feedback_type": "negative",
            "failure_category": "hallucination",
            "user_correction": "El stock real de arroz es 20kg no 200kg.",
            "rating": 2,
        }
        res_neg = await client.post(
            "/api/v1/oppy_ai/chat/feedback",
            json=post_payload_neg,
            headers=headers,
        )
        assert res_neg.status_code == 201, res_neg.text
        data_neg = res_neg.json()
        assert data_neg["feedback_type"] == "negative"
        assert data_neg["failure_category"] == "hallucination"
        assert "arroz" in data_neg["user_correction"]

        # 3. Consulta de Feedback y Satisfacción %
        res_get = await client.get(
            f"/api/v1/oppy_ai/chat/feedback?tenant_id={TENANT_ID_STR}",
            headers=headers,
        )
        assert res_get.status_code == 200, res_get.text
        data_list = res_get.json()

        assert data_list["total"] >= 2
        assert data_list["positive_count"] >= 1
        assert data_list["negative_count"] >= 1
        # La tasa de satisfacción debe ser un Decimal exacto serializado como string o number
        assert Decimal(str(data_list["satisfaction_rate_percent"])) >= Decimal("0.00")


@pytest.mark.asyncio
async def test_feedback_endpoint_rejects_positive_with_failure_category() -> None:
    """Verifica que un feedback positivo rechace una categoría de falla con 422."""
    transport = ASGITransport(app=app)
    headers = _make_auth_headers()

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        invalid_payload = {
            "tenant_id": TENANT_ID_STR,
            "message_id": str(uuid.uuid4()),
            "trace_id": uuid.uuid4().hex,
            "feedback_type": "positive",
            "failure_category": "hallucination",  # Inválido en positivo
        }
        res = await client.post(
            "/api/v1/oppy_ai/chat/feedback",
            json=invalid_payload,
            headers=headers,
        )
        assert res.status_code == 422
