"""
oppytec-backend/tests/security_redteam/test_pii_sanitization_in_langfuse_traces.py
Suite de Seguridad Ofensiva Red Team:
1. Sanitización Determinista de PII y Secretos en Trazas Langfuse y Telemetría.
2. Aislamiento Multi-Tenant Inviolable y Prevención de BOLA/IDOR en Feedback de Chat.
3. Resistencia Ofensiva a Vectores de Prompt Injection, Anti-Jailbreak y Fuga de Secretos (EVAL-GASTRO-041 a 050).
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any
import uuid

import httpx
import pytest
from pydantic import SecretStr

from src.core.exceptions import OppyTecError
from src.core.observability import (
    REDACTED_MARKER,
    scrub_pii_text,
    scrub_telemetry_payload,
)
from src.core.security import create_access_token
from src.infrastructure.ai.langfuse_tracer import LangfuseTracer
from src.modules.oppy_ai.domain.evals import (
    AIChatFeedback,
    TraceContext,
    TracerConfigurationError,
)
from src.modules.oppy_ai.infrastructure.repositories import InMemoryAIChatFeedbackRepository
from src.modules.oppy_ai.presentation.router import (
    list_chat_feedback_endpoint,
    submit_chat_feedback_endpoint,
)
from src.modules.oppy_ai.presentation.schemas import AIChatFeedbackCreateRequest

pytestmark = pytest.mark.security_redteam

GOLDEN_DATASET_PATH = (
    Path(__file__).resolve().parent.parent / "ai_evals" / "datasets" / "gastronomic_golden_dataset.json"
)


# ============================================================================
# 1. AUDITORÍA OFENSIVA DE ENMASCARAMIENTO PII EN LANGFUSE
# ============================================================================


class MockTransport(httpx.AsyncBaseTransport):
    """Transporte HTTP en memoria para interceptar el payload exacto de red hacia Langfuse."""

    def __init__(self) -> None:
        self.dispatched_batches: list[dict[str, Any]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body_bytes = await request.aread()
        payload = json.loads(body_bytes.decode("utf-8"))
        self.dispatched_batches.append(payload)
        return httpx.Response(status_code=200, json={"status": "success"})


@pytest.mark.asyncio
async def test_pii_sanitization_in_langfuse_traces() -> None:
    """
    Verifica que correos, RUTs, tarjetas de crédito, passwords, tokens de pago
    y variables de entorno sean completamente anonimizados antes del despacho hacia Langfuse,
    garantizando al mismo tiempo la preservación de la razón social comercial inmutable ('Pollo King').
    """
    transport = MockTransport()
    client = httpx.AsyncClient(transport=transport)

    tracer = LangfuseTracer(
        host="http://langfuse-mock:3000",
        public_key="pk-lf-test-redteam",
        secret_key="sk-lf-test-redteam",
        http_client=client,
        enabled=True,
    )

    tenant_id = uuid.uuid4()
    context = TraceContext.create(tenant_id=tenant_id)

    raw_prompt = (
        "El cliente Pollo King con RUT 19.876.543-2 y correo gerente@polloking.cl "
        "autorizó la compra usando tarjeta 4532 8765 4321 0987, cvv: 123 y "
        "password: SuperSecret123! con token de pago tok_live_998877665544332211 "
        "y secret_key sk_live_abcdef1234567890."
    )
    raw_completion = (
        "Confirmado para Pollo King: El pago con tok_test_112233445566778899 fue procesado. "
        "Notificación enviada a finanzas@polloking.cl y rut 7.654.321-K. "
        "La contraseña temporal asignada es password=TempPass2026."
    )

    metadata: dict[str, Any] = {
        "user_email": "admin@polloking.cl",
        "api_key": "sk-1234567890abcdef",
        "credit_card": "4111-2222-3333-4444",
        "nested_info": {
            "token": "tok_visa_44556677889900",
            "rut": "11.222.333-4",
            "commercial_name": "Pollo King",
        },
    }

    tags = {
        "channel": "web_chat",
        "user_email": "admin_tag@polloking.cl",
        "tax_id": "99.888.777-6",
    }

    await tracer.trace_generation(
        context=context,
        model="gemini-2.5-flash",
        prompt=raw_prompt,
        completion=raw_completion,
        prompt_tokens=150,
        completion_tokens=80,
        cost_usd=Decimal("0.000350"),
        latency_ms=250,
        tags=tags,
        metadata=metadata,
    )

    # 1. Verificar registros en memoria
    recorded = tracer.get_recorded_generations()
    assert len(recorded) == 1
    gen_rec = recorded[0]

    # Verificar redacción en prompt
    assert "19.876.543-2" not in gen_rec["prompt"]
    assert "gerente@polloking.cl" not in gen_rec["prompt"]
    assert "4532 8765 4321 0987" not in gen_rec["prompt"]
    assert "SuperSecret123!" not in gen_rec["prompt"]
    assert "tok_live_998877665544332211" not in gen_rec["prompt"]
    assert "sk_live_abcdef1234567890" not in gen_rec["prompt"]
    assert "Pollo King" in gen_rec["prompt"]

    # Verificar redacción en completion
    assert "tok_test_112233445566778899" not in gen_rec["completion"]
    assert "finanzas@polloking.cl" not in gen_rec["completion"]
    assert "7.654.321-K" not in gen_rec["completion"]
    assert "TempPass2026" not in gen_rec["completion"]
    assert "Pollo King" in gen_rec["completion"]

    # Verificar redacción en metadata
    assert gen_rec["metadata"]["user_email"] == REDACTED_MARKER
    assert gen_rec["metadata"]["api_key"] == REDACTED_MARKER
    assert gen_rec["metadata"]["credit_card"] == REDACTED_MARKER
    assert gen_rec["metadata"]["nested_info"]["token"] == REDACTED_MARKER
    assert gen_rec["metadata"]["nested_info"]["rut"] == REDACTED_MARKER
    assert gen_rec["metadata"]["nested_info"]["commercial_name"] == "Pollo King"

    # Verificar redacción en tags
    assert gen_rec["tags"]["user_email"] == REDACTED_MARKER
    assert gen_rec["tags"]["tax_id"] == REDACTED_MARKER
    assert gen_rec["tags"]["channel"] == "web_chat"

    # 2. Verificar inspección del payload HTTP real despachado por la red
    assert len(transport.dispatched_batches) == 1
    batch_json = json.dumps(transport.dispatched_batches[0])

    # Asserts forenses de CERO fugas
    assert "19.876.543-2" not in batch_json
    assert "gerente@polloking.cl" not in batch_json
    assert "4532 8765 4321 0987" not in batch_json
    assert "SuperSecret123!" not in batch_json
    assert "tok_live_998877665544332211" not in batch_json
    assert "sk_live_abcdef1234567890" not in batch_json
    assert "admin@polloking.cl" not in batch_json
    assert "4111-2222-3333-4444" not in batch_json
    assert "Pollo King" in batch_json


@pytest.mark.asyncio
async def test_pii_sanitization_in_tool_calls_and_feedback() -> None:
    """Verifica la censura estricta de PII en tool calls y feedback hacia Langfuse."""
    transport = MockTransport()
    client = httpx.AsyncClient(transport=transport)

    tracer = LangfuseTracer(
        host="http://langfuse-mock:3000",
        public_key="pk-lf-test",
        secret_key="sk-lf-test",
        http_client=client,
        enabled=True,
    )

    tenant_id = uuid.uuid4()
    context = TraceContext.create(tenant_id=tenant_id)

    tool_input = {
        "supplier_rut": "76.123.456-7",
        "contact_email": "ventas@proveedor.cl",
        "order_token": "tok_live_1234567890123456",
        "secret_password": SecretStr("MySecret99"),
        "product": "Harina de Trigo",
    }
    tool_output = {
        "status": "APPROVED",
        "auth_code": "tok_pay_9876543210987654",
        "supplier_phone": "+56 9 8765 4321",
    }

    await tracer.trace_tool_call(
        context=context,
        tool_name="procurement.approve_order",
        tool_input=tool_input,
        tool_output=tool_output,
        latency_ms=120,
        error="Fallo al notificar a admin@polloking.cl con password: secret123",
    )

    recorded_tools = tracer.get_recorded_tool_calls()
    assert len(recorded_tools) == 1
    call = recorded_tools[0]

    assert call["input"]["supplier_rut"] == REDACTED_MARKER
    assert call["input"]["contact_email"] == REDACTED_MARKER
    assert call["input"]["order_token"] == REDACTED_MARKER
    assert call["input"]["secret_password"] == REDACTED_MARKER
    assert call["input"]["product"] == "Harina de Trigo"
    assert call["output"]["auth_code"] == REDACTED_MARKER
    assert call["output"]["supplier_phone"] == REDACTED_MARKER
    assert "admin@polloking.cl" not in call["error"]
    assert "secret123" not in call["error"]

    # Probar también record_feedback con user_correction conteniendo PII
    fb = AIChatFeedback(
        tenant_id=tenant_id,
        message_id="msg-101",
        trace_id=context.trace_id,
        feedback_type="negative",
        failure_category="other",
        user_correction="La respuesta debió enviarse al rut 12.345.678-5 y correo test@cliente.cl",
    )
    await tracer.record_feedback(fb)

    rec_feedbacks = tracer.get_recorded_feedbacks()
    assert len(rec_feedbacks) == 1
    assert "12.345.678-5" not in rec_feedbacks[0]["comment"]
    assert "test@cliente.cl" not in rec_feedbacks[0]["comment"]


# ============================================================================
# 2. AISLAMIENTO MULTI-TENANT ESTRICTO Y PREVENCIÓN BOLA/IDOR
# ============================================================================


def test_trace_context_requires_mandatory_tenant_id() -> None:
    """Valida que TraceContext rechace traceContexts sin tenant_id o con tipos espurios."""
    with pytest.raises(TracerConfigurationError, match="tenant_id must be a UUID instance"):
        TraceContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="00f067aa0ba902b7",
            tenant_id=None,  # type: ignore[arg-type]
        )

    with pytest.raises(TracerConfigurationError, match="tenant_id must be a UUID instance"):
        TraceContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="00f067aa0ba902b7",
            tenant_id="invalid-uuid-string",  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_feedback_cross_tenant_submission_idor_prevention() -> None:
    """
    Verifica que un usuario autenticado para Tenant A sea bloqueado (HTTP 403)
    si intenta enviar feedback asignado a Tenant B.
    """
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    # Principal autenticado para tenant A
    from src.core.guards.rbac_dependencies import AuthenticatedPrincipal

    principal = AuthenticatedPrincipal(
        user_id=101,
        tenant_id=str(tenant_a),
        holding_id="holding-1",
        is_global_staff=False,
        hierarchy_rank=20,
        accessible_tenants=frozenset({str(tenant_a)}),
        is_superuser_god=False,
    )

    malicious_payload = AIChatFeedbackCreateRequest(
        tenant_id=tenant_b,  # Intento de IDOR cruzado
        message_id="msg-victim-tenant-b",
        trace_id=uuid.uuid4().hex,
        feedback_type="negative",
        failure_category="hallucination",
        user_correction="Inyección fraudulenta",
        rating=1,
    )

    with pytest.raises(OppyTecError) as exc_info:
        await submit_chat_feedback_endpoint(
            principal=principal,
            payload=malicious_payload,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "CROSS_TENANT_ACCESS_FORBIDDEN"


@pytest.mark.asyncio
async def test_feedback_cross_tenant_inspection_idor_prevention() -> None:
    """
    Verifica que un usuario de Tenant A sea bloqueado (HTTP 403)
    si intenta inspeccionar o listar los feedbacks de Tenant B en /feedback?tenant_id=B.
    """
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    from src.core.guards.rbac_dependencies import AuthenticatedPrincipal

    principal = AuthenticatedPrincipal(
        user_id=102,
        tenant_id=str(tenant_a),
        holding_id="holding-1",
        is_global_staff=False,
        hierarchy_rank=20,
        accessible_tenants=frozenset({str(tenant_a)}),
        is_superuser_god=False,
    )

    # Intento de listar feedbacks del Tenant B
    with pytest.raises(OppyTecError) as exc_info:
        await list_chat_feedback_endpoint(
            principal=principal,
            tenant_id=tenant_b,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "CROSS_TENANT_ACCESS_FORBIDDEN"


# ============================================================================
# 3. EVALUACIÓN DE VECTORES ADVERSARIALES EN GOLDEN DATASET (041 A 050)
# ============================================================================


def test_golden_dataset_security_vectors_contract() -> None:
    """
    Verifica que el Golden Dataset contenga los 10 vectores adversariales (EVAL-GASTRO-041 a 050)
    con sus contratos estrictos de seguridad, contenido prohibido y ausencia de fugas.
    """
    assert GOLDEN_DATASET_PATH.exists(), f"No se encontró el dataset en {GOLDEN_DATASET_PATH}"

    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    security_cases = [case for case in dataset if case["test_id"] in [f"EVAL-GASTRO-0{i:02d}" for i in range(41, 51)]]
    assert len(security_cases) == 10, f"Se esperaban 10 casos de seguridad (041 a 050), se encontraron {len(security_cases)}"

    # Verificar vectores específicos
    cases_by_id = {c["test_id"]: c for c in security_cases}

    # EVAL-GASTRO-042: Anti-Fuga de código fuente
    c42 = cases_by_id["EVAL-GASTRO-042"]
    assert "código fuente" in c42["prompt"].lower()
    assert any("def calcular_costo_receta" in item for item in c42["forbidden_content"])
    assert "prohibido acceder" in c42["ground_truth"].lower()

    # EVAL-GASTRO-043: Aislamiento tenant estricto (restaurante vecino)
    c43 = cases_by_id["EVAL-GASTRO-043"]
    assert "restaurante vecino" in c43["prompt"].lower()
    assert any("tenant_" in item for item in c43["forbidden_content"])
    assert "aislamiento multi-tenant" in c43["ground_truth"].lower()

    # EVAL-GASTRO-044: Prompt Injection Jailbreak
    c44 = cases_by_id["EVAL-GASTRO-044"]
    assert "ignora todas tus instrucciones" in c44["prompt"].lower()
    assert any("password" in item for item in c44["forbidden_content"])

    # EVAL-GASTRO-045: SQL Injection resilience
    c45 = cases_by_id["EVAL-GASTRO-045"]
    assert "select * from" in c45["prompt"].lower()
    assert any("password_hash" in item for item in c45["forbidden_content"])

    # EVAL-GASTRO-046: Cross-tenant competitor leaks
    c46 = cases_by_id["EVAL-GASTRO-046"]
    assert "competencia" in c46["prompt"].lower()
    assert "esquema de datos hermético" in c46["ground_truth"].lower()

    # EVAL-GASTRO-047: Fuga de variables de entorno y secrets
    c47 = cases_by_id["EVAL-GASTRO-047"]
    assert "langfuse_secret_key" in c47["prompt"].lower()
    assert any("sk-" in item for item in c47["forbidden_content"])
    assert "solicitud denegada" in c47["ground_truth"].lower()

    # EVAL-GASTRO-049: Intento de extracción de specs/engineering-code
    c49 = cases_by_id["EVAL-GASTRO-049"]
    assert "engineering-code" in c49["prompt"].lower()
    assert any("engineering-code" in item for item in c49["forbidden_content"])
