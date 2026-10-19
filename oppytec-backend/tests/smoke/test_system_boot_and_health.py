"""
Smoke Test Suite (`tests/smoke/test_system_boot_and_health.py`).

Verifies:
1. Clean boot of `create_app()`.
2. `/api/v1/health` returns HTTP 200 with `status="ok"`, `environment`, `env_namespace`, `version="2.0.0"`.
3. Automatic generation and propagation of `X-Trace-ID` header.
4. OpenAPI governance: `/docs`, `/redoc`, and `/openapi.json` are enabled in `local` and return HTTP 404 when `ENVIRONMENT="production"`.
"""
from __future__ import annotations

import httpx
import pytest

from src.main import create_app

pytestmark = pytest.mark.smoke


async def test_health_endpoint_and_trace_id_generation(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifies `/api/v1/health` responds with 200, metadata, and generated `X-Trace-ID`."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200

    trace_id = response.headers.get("X-Trace-ID")
    assert trace_id is not None
    assert len(trace_id) >= 16

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["environment"] == "local"
    assert payload["env_namespace"] == "wt_p1_2"
    assert payload["version"] == "2.0.0"
    assert payload["trace_id"] == trace_id


async def test_trace_id_propagation_from_incoming_request(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifies incoming `X-Trace-ID` is preserved in the response header and payload."""
    custom_trace_id = "trace-oppytec-smoke-000123456789"
    response = await async_client.get(
        "/api/v1/health",
        headers={"X-Trace-ID": custom_trace_id},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == custom_trace_id
    assert response.json()["trace_id"] == custom_trace_id


async def test_openapi_enabled_in_non_production(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifies `/openapi.json`, `/docs`, and `/redoc` are accessible in `local`."""
    openapi_resp = await async_client.get("/openapi.json")
    docs_resp = await async_client.get("/docs")
    redoc_resp = await async_client.get("/redoc")

    assert openapi_resp.status_code == 200
    assert openapi_resp.json()["info"]["version"] == "2.0.0"
    assert docs_resp.status_code == 200
    assert redoc_resp.status_code == 200


async def test_openapi_docs_disabled_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies `/docs`, `/redoc`, and `/openapi.json` return 404 when `ENVIRONMENT='production'`."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ENV_NAMESPACE", "prod")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://prod_user:StrongProdPass#2026!@ep-oppytec-prod.us-east-2.aws.neon.tech:5432/oppytec_prod",
    )
    monkeypatch.setenv(
        "REDIS_URL",
        "rediss://default:StrongRedisPass#2026!@redis-prod.oppytec.internal:6379/0",
    )
    monkeypatch.setenv("STORAGE_PROVIDER", "r2")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://app.oppytec.com"]')

    prod_app = create_app()
    transport = httpx.ASGITransport(app=prod_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as prod_client:
        for route in ("/docs", "/redoc", "/openapi.json"):
            resp = await prod_client.get(route)
            assert resp.status_code == 404, f"Expected 404 for {route} in production, got {resp.status_code}"

        health_resp = await prod_client.get("/api/v1/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["environment"] == "production"
