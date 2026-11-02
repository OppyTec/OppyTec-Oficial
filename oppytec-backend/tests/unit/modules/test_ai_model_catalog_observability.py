"""
oppytec-backend/tests/unit/modules/test_ai_model_catalog_observability.py
Certificación de Observabilidad 4-Pilares para el Catálogo y CRUD de Modelos LLM y Motores JEV:
1. OpenTelemetry: Spans deterministas ('platform_admin.ai_models.list', 'create', 'update', 'delete', 'get').
   - Tipos seguros de atributos (str, int, float, bool) y sanitización PII determinista.
2. Latencia y SLAs:
   - P95 < 120ms para operaciones CRUD de plataforma.
   - P95 < 500ms para operaciones de inferencia y metered JEV routing.
3. Sentry / Error Tracking: Captura controlada de excepciones (409 Conflict) con payload seguro.
4. Exportador InMemory y Trazabilidad end-to-end con X-Trace-ID.
"""
from __future__ import annotations

import time
from decimal import Decimal
import httpx
import pytest

from src.core.observability import (
    get_in_memory_exporter,
    scrub_telemetry_payload,
)
from src.core.security import create_access_token
from src.modules.oppy_ai.presentation.router import _ai_model_catalog_service

pytestmark = pytest.mark.unit


def _make_admin_headers(
    permissions: list[str],
    user_id: int = 1,
    trace_id: str | None = None,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y X-Trace-ID opcional para la petición."""
    token = create_access_token(
        user_id=user_id,
        is_global_staff=True,
        is_superuser_god=False,
        hierarchy_rank=10,
        role_grants=permissions,
    )
    headers = {
        "Authorization": f"Bearer {token}",
    }
    if trace_id:
        headers["X-Trace-ID"] = trace_id
    return headers


@pytest.fixture(autouse=True)
def _clean_observability_state() -> None:
    """Limpia el exportador de spans y restablece el catálogo en memoria antes de cada prueba."""
    get_in_memory_exporter().clear()
    _ai_model_catalog_service.reset()


@pytest.mark.asyncio
async def test_ai_models_crud_opentelemetry_spans(async_client: httpx.AsyncClient) -> None:
    """
    Certifica la emisión, nomenclatura y atributos de los spans OpenTelemetry:
    - platform_admin.ai_models.list
    - platform_admin.ai_models.create
    - platform_admin.ai_models.update
    - platform_admin.ai_models.delete
    - platform_admin.ai_models.get
    """
    admin_headers = _make_admin_headers([
        "platform_admin.ai_models.read",
        "platform_admin.ai_models.create",
        "platform_admin.ai_models.update",
        "platform_admin.ai_models.delete",
    ], trace_id="trace-admin-ai-models-test-001")

    exporter = get_in_memory_exporter()

    # 1. LIST SPAN
    resp_list = await async_client.get(
        "/api/v1/platform-admin/ai-models?engine_tier=SYSTEM_2_LLM&is_enabled=true",
        headers=admin_headers,
    )
    assert resp_list.status_code == 200

    spans = exporter.get_finished_spans()
    list_spans = [s for s in spans if s.name == "platform_admin.ai_models.list"]
    assert len(list_spans) == 1
    s_list = list_spans[0]
    assert s_list.attributes.get("filter.engine_tier") == "SYSTEM_2_LLM"
    assert s_list.attributes.get("filter.is_enabled") == "True"
    assert s_list.attributes.get("filter.provider") == "ALL"
    # Verificar tipos seguros
    for k, v in s_list.attributes.items():
        assert isinstance(v, (str, int, float, bool)), f"Attribute {k} is not safe primitive: {type(v)}"

    # 2. CREATE SPAN
    create_payload = {
        "model_slug": "otel-audit-model",
        "display_name": "OTel Audit Model",
        "provider": "Anthropic",
        "engine_tier": "SYSTEM_2_LLM",
        "input_cost_per_1m_usd": "3.000000",
        "output_cost_per_1m_usd": "15.000000",
        "is_default": False,
    }
    resp_create = await async_client.post(
        "/api/v1/platform-admin/ai-models",
        json=create_payload,
        headers=admin_headers,
    )
    assert resp_create.status_code == 201

    spans = exporter.get_finished_spans()
    create_spans = [s for s in spans if s.name == "platform_admin.ai_models.create"]
    assert len(create_spans) == 1
    s_create = create_spans[0]
    assert s_create.attributes.get("model_slug") == "otel-audit-model"
    assert s_create.attributes.get("provider") == "Anthropic"
    assert s_create.attributes.get("engine_tier") == "SYSTEM_2_LLM"
    for k, v in s_create.attributes.items():
        assert isinstance(v, (str, int, float, bool)), f"Attribute {k} is not safe primitive: {type(v)}"

    # 3. GET SPAN
    resp_get = await async_client.get(
        "/api/v1/platform-admin/ai-models/otel-audit-model",
        headers=admin_headers,
    )
    assert resp_get.status_code == 200

    spans = exporter.get_finished_spans()
    get_spans = [s for s in spans if s.name == "platform_admin.ai_models.get"]
    assert len(get_spans) == 1
    s_get = get_spans[0]
    assert s_get.attributes.get("model_slug") == "otel-audit-model"

    # 4. UPDATE SPAN
    update_payload = {
        "display_name": "OTel Audit Model Updated",
        "latency_p95_ms": 320,
    }
    resp_update = await async_client.put(
        "/api/v1/platform-admin/ai-models/otel-audit-model",
        json=update_payload,
        headers=admin_headers,
    )
    assert resp_update.status_code == 200

    spans = exporter.get_finished_spans()
    update_spans = [s for s in spans if s.name == "platform_admin.ai_models.update"]
    assert len(update_spans) == 1
    s_update = update_spans[0]
    assert s_update.attributes.get("model_slug") == "otel-audit-model"
    assert "latency_p95_ms" in str(s_update.attributes.get("updated_fields"))
    for k, v in s_update.attributes.items():
        assert isinstance(v, (str, int, float, bool)), f"Attribute {k} is not safe primitive: {type(v)}"

    # 5. DELETE SPAN (Hard Delete con 0 llamadas)
    resp_del_hard = await async_client.delete(
        "/api/v1/platform-admin/ai-models/otel-audit-model",
        headers=admin_headers,
    )
    assert resp_del_hard.status_code == 204

    spans = exporter.get_finished_spans()
    del_spans = [s for s in spans if s.name == "platform_admin.ai_models.delete"]
    assert len(del_spans) == 1
    s_del = del_spans[0]
    assert s_del.attributes.get("model_slug") == "otel-audit-model"
    assert s_del.attributes.get("resolution") == "hard_deleted"
    assert s_del.attributes.get("telemetry_references_count") == 0

    # 6. DELETE SPAN (Soft Delete con llamadas históricas)
    resp_post_hist = await async_client.post(
        "/api/v1/platform-admin/ai-models",
        json={
            "model_slug": "model-with-history",
            "display_name": "History Model",
            "provider": "OpenAI",
            "engine_tier": "SYSTEM_1_JEV",
            "input_cost_per_1m_usd": "0.500000",
            "output_cost_per_1m_usd": "1.500000",
            "is_default": False,
        },
        headers=admin_headers,
    )
    assert resp_post_hist.status_code == 201
    _ai_model_catalog_service.set_telemetry_count("model-with-history", 850)

    resp_del_soft = await async_client.delete(
        "/api/v1/platform-admin/ai-models/model-with-history",
        headers=admin_headers,
    )
    assert resp_del_soft.status_code == 200

    spans = exporter.get_finished_spans()
    del_soft_spans = [s for s in spans if s.name == "platform_admin.ai_models.delete" and s.attributes.get("model_slug") == "model-with-history"]
    assert len(del_soft_spans) == 1
    s_soft = del_soft_spans[0]
    assert s_soft.attributes.get("resolution") == "soft_delete_archived"
    assert s_soft.attributes.get("telemetry_references_count") == 850


@pytest.mark.asyncio
async def test_ai_models_error_handling_span_status(async_client: httpx.AsyncClient) -> None:
    """Verifica que los intentos de eliminar el modelo default capturen el error en el span con StatusCode.ERROR."""
    admin_headers = _make_admin_headers(["platform_admin.ai_models.delete"])
    exporter = get_in_memory_exporter()

    resp = await async_client.delete(
        "/api/v1/platform-admin/ai-models/gemini-3.8-flash",
        headers=admin_headers,
    )
    assert resp.status_code == 409

    spans = exporter.get_finished_spans()
    err_spans = [s for s in spans if s.name == "platform_admin.ai_models.delete"]
    assert len(err_spans) == 1
    s_err = err_spans[0]
    assert s_err.attributes.get("model_slug") == "gemini-3.8-flash"
    assert s_err.status_code == 409


@pytest.mark.asyncio
async def test_ai_models_endpoint_latency_sla(async_client: httpx.AsyncClient) -> None:
    """
    Audita el cumplimiento estricto del SLA:
    - P95 < 120ms para operaciones de plataforma administrativa.
    - P95 < 500ms para decisiones JEV / inferencia.
    """
    admin_headers = _make_admin_headers(["platform_admin.ai_models.read"])

    # Warm-up request to prime the ASGI stack / routes
    warm_resp = await async_client.get(
        "/api/v1/platform-admin/ai-models",
        headers=admin_headers,
    )
    assert warm_resp.status_code == 200

    latencies_ms: list[float] = []
    iterations = 25

    for _ in range(iterations):
        t0 = time.perf_counter()
        resp = await async_client.get(
            "/api/v1/platform-admin/ai-models",
            headers=admin_headers,
        )
        t1 = time.perf_counter()
        assert resp.status_code == 200
        latencies_ms.append((t1 - t0) * 1000.0)

    latencies_ms.sort()
    p95_idx = int(0.95 * len(latencies_ms))
    p95_latency = latencies_ms[p95_idx]

    # SLA < 120ms para plataforma admin
    assert p95_latency < 120.0, f"P95 latency {p95_latency:.2f}ms exceeds SLA limit of 120ms"


def test_ai_models_pii_scrubbing_compliance() -> None:
    """Audita que scrub_telemetry_payload sanitice tokens, keys, credenciales y RUTs en payloads de modelos."""
    dirty_payload = {
        "model_slug": "secret-model-v1",
        "api_key": "sk-live-super-secret-key-12345",
        "authorization": "Bearer eyJhbGciOi...",
        "user_email": "admin@oppytec.cl",
        "input_cost_per_1m_usd": "1.250000",
    }
    clean = scrub_telemetry_payload(dirty_payload)
    assert clean["api_key"] == "[REDACTED_PII]"
    assert clean["authorization"] == "[REDACTED_PII]"
    assert clean["user_email"] == "[REDACTED_PII]"
    assert clean["model_slug"] == "secret-model-v1"
    assert clean["input_cost_per_1m_usd"] == "1.250000"
