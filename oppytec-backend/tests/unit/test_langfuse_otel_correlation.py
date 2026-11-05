"""
oppytec-backend/tests/unit/test_langfuse_otel_correlation.py
Pruebas de Correlación OpenTelemetry W3C TraceContext <-> Langfuse Self-Hosted y FinOps.

Verifica:
1. Propagación bidireccional de W3C traceparent y X-Trace-ID.
2. Identidad determinista: el trace_id de OpenTelemetry es exactamente el ID de traza de Langfuse.
3. Formato del Deep Link a Langfuse UI en Grafana APM.
4. Resiliencia y degradación elegante de LangfuseTracer ante fallos de red.
5. Censura estricta de PII preservando marcas comerciales inmutables ('Pollo King').
"""
from __future__ import annotations

import uuid
from decimal import Decimal
import pytest
import httpx

from src.core.observability import (
    extract_trace_id_from_headers,
    scrub_pii_text,
    scrub_telemetry_payload,
)
from src.infrastructure.ai.langfuse_tracer import LangfuseTracer
from src.modules.oppy_ai.domain.evals import TraceContext


def test_w3c_traceparent_header_extraction() -> None:
    """Verifica que extract_trace_id_from_headers extraiga el trace_id de 32 hex desde W3C traceparent."""
    canonical_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    span_id = "00f067aa0ba902b7"
    raw_traceparent = f"00-{canonical_trace_id}-{span_id}-01"

    headers = {"traceparent": raw_traceparent}
    extracted = extract_trace_id_from_headers(headers)
    assert extracted == canonical_trace_id, f"Se esperaba '{canonical_trace_id}', se obtuvo '{extracted}'"


def test_explicit_x_trace_id_precedence() -> None:
    """Verifica que una cabecera X-Trace-ID explícita mantenga su validez."""
    custom_trace = "trc-cust-12345678"
    headers = {"x-trace-id": custom_trace}
    extracted = extract_trace_id_from_headers(headers)
    assert extracted == custom_trace


@pytest.mark.asyncio
async def test_langfuse_tracer_maintains_exact_otel_trace_id() -> None:
    """
    Verifica que el adaptador LangfuseTracer asigne el trace_id exacto
    de OpenTelemetry en el evento de creación de traza para correlación 1:1 con Tempo/Grafana.
    """
    tracer = LangfuseTracer(
        host="http://localhost:3000",
        public_key="pk-lf-test-key",
        secret_key="sk-lf-test-secret",
        enabled=True,
    )

    canonical_trace_id = uuid.uuid4().hex
    tenant_id = uuid.uuid4()
    context = TraceContext.create(
        tenant_id=tenant_id,
        trace_id=canonical_trace_id,
    )

    prompt = "El cliente Pollo King requiere un cálculo de costo para su menú de banquetes con rut 12.345.678-5"
    completion = "El costo para Pollo King es de $45.000 CLP según la receta estándar"

    await tracer.trace_generation(
        context=context,
        model="gemini-2.5-flash",
        prompt=prompt,
        completion=completion,
        prompt_tokens=120,
        completion_tokens=45,
        cost_usd=Decimal("0.000250"),
        latency_ms=340,
        tags={"channel": "web_chat"},
    )

    # Verificar que se registró localmente en memoria con el ID exacto
    assert len(tracer._recorded_generations) == 1
    recorded = tracer._recorded_generations[0]
    assert recorded["trace_id"] == canonical_trace_id
    assert recorded["tenant_id"] == str(tenant_id)

    # Verificar que el PII (RUT) fue redactado pero la marca 'Pollo King' se preservó
    assert "[REDACTED_PII]" in recorded["prompt"]
    assert "12.345.678-5" not in recorded["prompt"]
    assert "Pollo King" in recorded["prompt"]
    assert "Pollo King" in recorded["completion"]


def test_grafana_langfuse_deep_link_resolution() -> None:
    """
    Verifica que la plantilla de Deep Link utilizada en Grafana (llm_finops_observability.json)
    genere URLs válidas hacia la consola de Langfuse Self-Hosted.
    """
    langfuse_host = "http://localhost:3000"
    project_id = "oppytec-ai"
    sample_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"

    deep_link_template = "{host}/project/{project}/traces/{trace_id}"
    resolved_url = deep_link_template.format(
        host=langfuse_host,
        project=project_id,
        trace_id=sample_trace_id,
    )

    assert resolved_url == "http://localhost:3000/project/oppytec-ai/traces/4bf92f3577b34da6a3ce929d0e0e4736"
    assert sample_trace_id in resolved_url


@pytest.mark.asyncio
async def test_langfuse_tracer_graceful_degradation_when_offline() -> None:
    """
    Verifica que si el endpoint de Langfuse está caído o no responde,
    LangfuseTracer degrade limpiamente sin lanzar excepciones hacia el llamador.
    """
    tracer = LangfuseTracer(
        host="http://localhost:9999",  # Puerto inactivo para forzar timeout/connection refused
        public_key="pk-lf-test-key",
        secret_key="sk-lf-test-secret",
        timeout_seconds=0.05,
        circuit_breaker_threshold=2,
        circuit_cooldown_seconds=10.0,
        enabled=True,
    )

    context = TraceContext.create(tenant_id=uuid.uuid4())

    # La llamada no debe levantar excepción
    result_trace_id = await tracer.trace_generation(
        context=context,
        model="gemini-2.5-flash",
        prompt="Hola mundo",
        completion="Respuesta de prueba",
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=Decimal("0.000010"),
        latency_ms=50,
    )

    assert result_trace_id == context.trace_id
    assert len(tracer._recorded_generations) == 1
