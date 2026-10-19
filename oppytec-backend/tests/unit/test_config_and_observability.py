"""
oppytec-backend/tests/unit/test_config_and_observability.py
Pruebas unitarias deterministas en Co-Creación 1:1 para:
1. Settings (src/core/config.py): 5 entornos, SecretStr, entropía Shannon, Cross-Environment Guard,
   sinkhole de correo, is_openapi_enabled y configuración de pool.
2. Observability (src/core/observability.py): scrub_telemetry_payload recursivo, propagación de X-Trace-ID,
   W3C traceparent, contexto Multi-Tenant y spans en memoria con ObservabilityMiddleware.
"""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from src.core.config import EnvironmentType, Settings, calculate_shannon_entropy
from src.core.observability import (
    REDACTED_MARKER,
    ObservabilityMiddleware,
    bind_tenant_telemetry_context,
    extract_trace_id_from_headers,
    format_structured_log,
    get_current_trace_id,
    get_in_memory_exporter,
    get_tenant_telemetry_context,
    reset_tenant_telemetry_context,
    scrub_telemetry_payload,
)


def test_default_local_settings_and_secretstr_enforcement() -> None:
    """Verifica que Settings cargue valores seguros en local y que todos los secretos sean SecretStr."""
    settings = Settings()
    assert settings.ENVIRONMENT == "local"
    assert settings.ENV_NAMESPACE == "default"
    assert settings.is_openapi_enabled is True
    assert settings.DB_POOL_CLASS == "AsyncAdaptedQueuePool"
    assert settings.DB_POOL_SIZE == 40
    assert settings.DB_MAX_OVERFLOW == 20
    assert settings.DB_STATEMENT_CACHE_SIZE == 0

    for attr in (
        "SECRET_KEY",
        "JWT_ACCESS_SECRET_KEY",
        "JWT_REFRESH_SECRET_KEY",
        "SUPERUSER_GENESIS_PASSWORD",
        "GEMINI_API_KEY",
        "JEV_API_KEY",
        "R2_SECRET_ACCESS_KEY",
        "DATABASE_URL",
        "REDIS_URL",
    ):
        val = getattr(settings, attr)
        assert isinstance(val, SecretStr), f"{attr} debe ser SecretStr"
        assert "**********" in str(val)


def test_shannon_entropy_and_short_secret_rejected_fail_fast() -> None:
    """Verifica que claves cortas (< 32) o de baja entropía sean rechazadas en el milisegundo 0."""
    assert calculate_shannon_entropy("aaaaaaaaaa") == 0.0
    assert calculate_shannon_entropy("oppytec_v2_dev_secret_key_9x8B7v6N5m4L3k2J1h0G!@#") > 4.0

    with pytest.raises(ValidationError, match="Fail-Fast Security Error"):
        Settings(
            SECRET_KEY=SecretStr("short_key"),
        )

    with pytest.raises(ValidationError, match="Fail-Fast Security Error"):
        Settings(
            JWT_ACCESS_SECRET_KEY=SecretStr("a" * 40),
        )


@pytest.mark.parametrize("env_name", ["local", "preview", "ci"])
def test_cross_environment_guard_blocks_prod_and_staging_hosts(
    env_name: EnvironmentType,
) -> None:
    """Verifica que local, preview y ci lancen ValueError si apuntan a prod. o staging."""
    with pytest.raises(ValidationError, match="CrossEnvironmentViolation"):
        Settings(
            ENVIRONMENT=env_name,
            DATABASE_URL=SecretStr("postgresql+asyncpg://u:p@prod.db.oppytec.com:5432/oppytec"),
        )

    with pytest.raises(ValidationError, match="CrossEnvironmentViolation"):
        Settings(
            ENVIRONMENT=env_name,
            REDIS_URL=SecretStr("redis://staging.redis.oppytec.com:6379/0"),
        )


def test_production_openapi_disabled_and_strict_boundaries() -> None:
    """Verifica que en production is_openapi_enabled sea False y prohíba mailpit/local storage."""
    prod_settings = Settings(
        ENVIRONMENT="production",
        DATABASE_URL=SecretStr("postgresql+asyncpg://u:p@db-ha.internal:5432/oppytec_live"),
        REDIS_URL=SecretStr("redis://redis-ha.internal:6379/0"),
        ALLOWED_ORIGINS=["https://app.oppytec.com"],
        STORAGE_PROVIDER="r2",
        EMAIL_PROVIDER="resend",
    )
    assert prod_settings.is_openapi_enabled is False

    # En production no se permite mailpit ni console_mock
    with pytest.raises(ValidationError, match="EMAIL_PROVIDER"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL=SecretStr("postgresql+asyncpg://u:p@db-ha.internal:5432/oppytec_live"),
            REDIS_URL=SecretStr("redis://redis-ha.internal:6379/0"),
            ALLOWED_ORIGINS=["https://app.oppytec.com"],
            STORAGE_PROVIDER="r2",
            EMAIL_PROVIDER="mailpit",
        )

    # En production no se permite origen http:// ni localhost
    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL=SecretStr("postgresql+asyncpg://u:p@db-ha.internal:5432/oppytec_live"),
            REDIS_URL=SecretStr("redis://redis-ha.internal:6379/0"),
            ALLOWED_ORIGINS=["http://localhost:5173"],
            STORAGE_PROVIDER="r2",
            EMAIL_PROVIDER="resend",
        )


def test_ci_environment_blocks_external_telemetry() -> None:
    """Verifica que CI bloquee OTEL_EXPORTER='otlp' y UMAMI_ENABLED=True."""
    ci_ok = Settings(ENVIRONMENT="ci", OTEL_EXPORTER="memory", UMAMI_ENABLED=False)
    assert ci_ok.is_openapi_enabled is True

    with pytest.raises(ValidationError, match="SecurityBoundaryViolation"):
        Settings(ENVIRONMENT="ci", OTEL_EXPORTER="otlp")


def test_scrub_telemetry_payload_redacts_all_sensitive_keys_recursively() -> None:
    """Verifica que scrub_telemetry_payload redacte claves PII/SecretStr en estructuras anidadas."""
    raw_payload: dict[str, object] = {
        "event": "user_login_attempt",
        "username": "chef_central",
        "password": "MyPlainPassword123!",
        "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$hash",
        "jwt_secret": SecretStr("super_secret_value"),
        "headers": {
            "Authorization": "Bearer eyJhbGciOiJIUzI1Ni...",
            "Cookie": "refresh_token=xyz987",
            "X-Api-Key": "key_12345",
            "Accept-Language": "es",
        },
        "billing": {
            "rut": "76.123.456-7",
            "tax_id": "76123456-7",
            "credit_card": "4111-1111-1111-1234",
            "cvv": "999",
            "currency": "CLP",
        },
        "items": [
            {"name": "Lomo Vetado", "api_key": "leaked_nested_key"},
            {"token": "nested_token_value", "qty": 5},
        ],
    }

    scrubbed = scrub_telemetry_payload(raw_payload)

    assert scrubbed["username"] == "chef_central"
    assert scrubbed["password"] == REDACTED_MARKER
    assert scrubbed["hashed_password"] == REDACTED_MARKER
    assert scrubbed["jwt_secret"] == REDACTED_MARKER

    headers = scrubbed["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == REDACTED_MARKER
    assert headers["Cookie"] == REDACTED_MARKER
    assert headers["X-Api-Key"] == REDACTED_MARKER
    assert headers["Accept-Language"] == "es"

    billing = scrubbed["billing"]
    assert isinstance(billing, dict)
    assert billing["rut"] == REDACTED_MARKER
    assert billing["tax_id"] == REDACTED_MARKER
    assert billing["credit_card"] == REDACTED_MARKER
    assert billing["cvv"] == REDACTED_MARKER
    assert billing["currency"] == "CLP"

    items = scrubbed["items"]
    assert isinstance(items, list)
    assert items[0]["api_key"] == REDACTED_MARKER
    assert items[0]["name"] == "Lomo Vetado"
    assert items[1]["token"] == REDACTED_MARKER
    assert items[1]["qty"] == 5


def test_trace_id_context_and_middleware_in_memory_spans() -> None:
    """Verifica la propagación de X-Trace-ID, contexto Multi-Tenant y captura en InMemorySpanExporter."""
    exporter = get_in_memory_exporter()
    exporter.clear()

    # Verificar extracción W3C traceparent
    w3c_trace = extract_trace_id_from_headers(
        {"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"}
    )
    assert w3c_trace == "4bf92f3577b34da6a3ce929d0e0e4736"

    app = FastAPI()
    app.add_middleware(
        ObservabilityMiddleware,
        environment="ci",
        env_namespace="wt_p1_1",
        otel_exporter="memory",
    )

    @app.get("/api/v1/health")
    async def health_endpoint() -> dict[str, str]:
        ctx = get_tenant_telemetry_context()
        return {
            "trace_id": get_current_trace_id(),
            "tenant_id": ctx.tenant_id or "",
            "holding_id": ctx.holding_id or "",
            "env_namespace": ctx.env_namespace,
        }

    client = TestClient(app)
    custom_trace_id = "trace-oppytec-2026-abcd1234"
    response = client.get(
        "/api/v1/health",
        headers={
            "X-Trace-ID": custom_trace_id,
            "X-Holding-ID": "holding-uuid-001",
            "X-Tenant-ID": "tenant-uuid-002",
            "X-Tenant-Schema": "tenant_pacifico",
            "Accept-Language": "en-US",
            "X-Display-Currency": "USD",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Trace-ID"] == custom_trace_id
    body = response.json()
    assert body["trace_id"] == custom_trace_id
    assert body["tenant_id"] == "tenant-uuid-002"
    assert body["holding_id"] == "holding-uuid-001"
    assert body["env_namespace"] == "wt_p1_1"

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.trace_id == custom_trace_id
    assert span.attributes["oppytec.holding_id"] == "holding-uuid-001"
    assert span.attributes["oppytec.tenant_id"] == "tenant-uuid-002"
    assert span.attributes["oppytec.tenant_schema"] == "tenant_pacifico"
    assert span.attributes["service.namespace"] == "wt_p1_1"
    assert span.attributes["oppytec.ui_language"] == "en"
    assert span.attributes["oppytec.display_currency"] == "USD"

    # Verificar structured log JSON con redacción PII
    tokens = bind_tenant_telemetry_context(
        trace_id=custom_trace_id,
        environment="ci",
        env_namespace="wt_p1_1",
        holding_id="holding-uuid-001",
        tenant_id="tenant-uuid-002",
    )
    try:
        log_json = format_structured_log(
            "info", "stock_updated", {"sku": "CARNE-01", "secret_token": "dont_leak_me"}
        )
        parsed = json.loads(log_json)
        assert parsed["trace_id"] == custom_trace_id
        assert parsed["tenant_id"] == "tenant-uuid-002"
        assert parsed["data"]["sku"] == "CARNE-01"
        assert parsed["data"]["secret_token"] == REDACTED_MARKER
    finally:
        reset_tenant_telemetry_context(tokens)
