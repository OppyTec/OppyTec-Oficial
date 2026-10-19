"""
Vector Red Team 07 (`tests/security_redteam/test_07_information_disclosure_and_headers.py`):
- Cabeceras HTTP de seguridad obligatorias (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-Trace-ID`).
- Respuestas de error normalizadas bajo RFC 7807 (`type`, `title`, `status`, `detail`, `error_code`, `i18n_key`, `trace_id`)
  con cero filtración de stack traces (`Traceback (most recent call last)`), rutas internas o versiones de BD.
- Redacción recursiva determinista de PII y secretos (`password`, `token`, `secret`, `authorization`, `rut`, `credit_card`, `SecretStr`)
  en `scrub_telemetry_payload` y `format_structured_log`.
"""
from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from src.core.observability import (
    REDACTED_MARKER,
    format_structured_log,
    scrub_telemetry_payload,
)

pytestmark = pytest.mark.security_redteam


async def test_mandatory_security_headers_and_rfc7807_zero_stacktrace_disclosure(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que tanto respuestas 200 como errores 401/403/422 incluyan cabeceras seguras y cero stack traces."""
    health_resp = await async_client.get(
        "/api/v1/health",
        headers={"X-Trace-ID": "trace-redteam-0007-check"},
    )
    assert health_resp.status_code == 200
    assert health_resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert health_resp.headers.get("X-Frame-Options") == "DENY"
    assert health_resp.headers.get("X-Trace-ID") == "trace-redteam-0007-check"

    # Petición sin credenciales a endpoint protegido -> RFC 7807 sin stack trace
    err_resp = await async_client.get(
        "/api/v1/catalog/products",
        headers={"X-Trace-ID": "trace-redteam-0007-err"},
    )
    assert err_resp.status_code == 401
    assert err_resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert err_resp.headers.get("X-Frame-Options") == "DENY"
    assert err_resp.headers.get("X-Trace-ID") == "trace-redteam-0007-err"

    problem = err_resp.json()
    for required_field in (
        "type",
        "title",
        "status",
        "detail",
        "error_code",
        "i18n_key",
        "trace_id",
        "instance",
    ):
        assert required_field in problem, f"Missing RFC 7807 field '{required_field}'"

    raw_text = err_resp.text
    for forbidden_leak in (
        "Traceback (most recent call last)",
        "sqlalchemy.exc",
        "asyncpg",
        "/home/",
        "site-packages",
    ):
        assert forbidden_leak not in raw_text


def test_pii_and_secret_scrubbing_in_telemetry_and_structured_logs() -> None:
    """Verifica que `scrub_telemetry_payload` y `format_structured_log` redacten el 100% de campos sensibles."""
    raw_event: dict[str, object] = {
        "user_id": 42,
        "password": "PlainTextPassword123!",
        "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$secret",
        "access_token": "eyJhbGciOiJIUzI1NiJ9.payload.sig",
        "Authorization": "Bearer super_secret_jwt",
        "jwt_secret": SecretStr("top_secret_signing_key"),
        "customer_profile": {
            "name": "Restaurante El Volcán",
            "rut": "76.543.210-K",
            "credit_card": "4111-2222-3333-4444",
            "cvv": "999",
            "nested_secrets": [
                {"api_key": "sk-live-999999", "safe_metric": 150},
            ],
        },
    }

    scrubbed = scrub_telemetry_payload(raw_event)
    assert scrubbed["user_id"] == 42
    assert scrubbed["password"] == REDACTED_MARKER
    assert scrubbed["hashed_password"] == REDACTED_MARKER
    assert scrubbed["access_token"] == REDACTED_MARKER
    assert scrubbed["Authorization"] == REDACTED_MARKER
    assert scrubbed["jwt_secret"] == REDACTED_MARKER

    profile = scrubbed["customer_profile"]
    assert isinstance(profile, dict)
    assert profile["name"] == "Restaurante El Volcán"
    assert profile["rut"] == REDACTED_MARKER
    assert profile["credit_card"] == REDACTED_MARKER
    assert profile["cvv"] == REDACTED_MARKER

    log_json_str = format_structured_log("WARNING", "auth.attempt", raw_event)
    parsed_log = json.loads(log_json_str)
    assert "PlainTextPassword123!" not in log_json_str
    assert "76.543.210-K" not in log_json_str
    assert "4111-2222-3333-4444" not in log_json_str
    assert "top_secret_signing_key" not in log_json_str
    assert parsed_log["data"]["password"] == REDACTED_MARKER
