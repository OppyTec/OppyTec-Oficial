"""
oppytec-backend/tests/unit/test_sandbox_observability_and_environments.py
Batería de Pruebas Unitarias de Entornos y Observabilidad para la Consola "Lab & QA Sandbox":
1. Blindaje Fail-Fast de los 5 entornos canónicos (local, preview, ci, staging, production):
   - Bloqueo 403 de mutaciones reales (dryRun=False) en 'production' (Mock Data y FEFO Shift).
   - Requerimiento de confirmación estricta (400) para mutaciones en 'staging' vía payload o cabecera X-Sandbox-Confirm-Staging.
   - Preservación de simulaciones de lectura (dryRun=True) en todos los entornos sin restricciones destructivas.
   - Aislamiento de esquemas: bloqueo 400 para esquemas no autorizados (ej. public, tenant_prod).
2. Trazabilidad OpenTelemetry y Observabilidad 4-Pilares:
   - Propagación bidireccional de `X-Trace-ID` y W3C `traceparent` desde el cliente FastAPI.
   - Preservación de correlación de traza distribuida en la respuesta HTTP.
   - Registro de estado de mutación permitida según política de entorno.
"""
from __future__ import annotations

import json
import math
from datetime import UTC, datetime

import httpx
import pytest

from src.core.config import get_settings
from src.core.guards.rbac_dependencies import clear_revoked_sessions
from src.core.security import create_access_token
from src.modules.tenancy.presentation.sandbox_router import get_sandbox_service

pytestmark = pytest.mark.unit


def _make_admin_headers(
    permissions: list[str],
    user_id: int = 1,
    is_global_staff: bool = True,
    is_superuser_god: bool = False,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y cabeceras opcionales."""
    token = create_access_token(
        user_id=user_id,
        is_global_staff=is_global_staff,
        is_superuser_god=is_superuser_god,
        hierarchy_rank=10,
        role_grants=permissions,
    )
    headers = {"Authorization": f"Bearer {token}"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


@pytest.fixture(autouse=True)
def _reset_sandbox_state() -> None:
    """Aísla el estado en memoria antes de cada prueba unitaria."""
    clear_revoked_sessions()
    service = get_sandbox_service()
    service.reset()


# ============================================================================
# 1. PRUEBAS DE BLINDAJE EN ENTORNO 'PRODUCTION'
# ============================================================================


@pytest.mark.asyncio
async def test_production_environment_blocks_real_mock_data_injection(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que en 'production', dryRun=False sea rechazado inmediatamente con HTTP 403."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "categories": ["catalog", "inventory_fefo"],
        "volume": "small",
        "dryRun": False,  # Mutación destructiva intentada en producción
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 403
    data = response.json()
    assert data["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"
    assert "production" in data["detail"].lower()


@pytest.mark.asyncio
async def test_production_environment_allows_dry_run_simulation(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que en 'production', dryRun=True (simulación lectura) esté permitido."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "categories": ["catalog"],
        "volume": "small",
        "dryRun": True,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["dryRun"] is True
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_production_environment_blocks_fefo_date_shift(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que en 'production', la alteración de fechas FEFO (dryRun=False) esté bloqueada."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "offsetDays": 15,
        "dryRun": False,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 403
    data = response.json()
    assert data["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"


@pytest.mark.asyncio
async def test_production_environment_requires_confirmation_for_playwright(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que en 'production', disparar Playwright requiera confirmación explícita."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    headers = _make_admin_headers(["platform_admin.sandbox.manage"])

    # Sin confirmación -> 400
    r_unconfirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json={"suiteId": "smoke", "targetTenantSchema": "tenant_qa_lab"},
    )
    assert r_unconfirmed.status_code == 400
    assert r_unconfirmed.json()["error_code"] == "PRODUCTION_CONFIRMATION_REQUIRED"

    # Con confirmación en payload -> 202
    r_confirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json={
            "suiteId": "smoke",
            "targetTenantSchema": "tenant_qa_lab",
            "confirmProductionRun": True,
        },
    )
    assert r_confirmed.status_code == 202


# ============================================================================
# 2. PRUEBAS DE BLINDAJE EN ENTORNO 'STAGING'
# ============================================================================


@pytest.mark.asyncio
async def test_staging_environment_requires_explicit_confirmation_for_mock_data(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que en 'staging', las mutaciones reales requieran confirmStagingAction."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")

    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    unconfirmed_payload = {
        "tenantSchema": "tenant_qa_lab",
        "categories": ["catalog"],
        "volume": "small",
        "dryRun": False,
        "confirmStagingAction": False,
    }

    # 1. Sin confirmación -> 400
    res_unconfirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=headers,
        json=unconfirmed_payload,
    )
    assert res_unconfirmed.status_code == 400
    assert res_unconfirmed.json()["error_code"] == "STAGING_CONFIRMATION_REQUIRED"

    # 2. Con confirmación en payload -> 200 OK
    confirmed_payload = {**unconfirmed_payload, "confirmStagingAction": True}
    res_confirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=headers,
        json=confirmed_payload,
    )
    assert res_confirmed.status_code == 200

    # 3. Con confirmación mediante cabecera HTTP -> 200 OK
    header_confirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers={**headers, "X-Sandbox-Confirm-Staging": "true"},
        json=unconfirmed_payload,
    )
    assert header_confirmed.status_code == 200


@pytest.mark.asyncio
async def test_staging_environment_requires_confirmation_for_fefo_shift(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que en 'staging', el desplazamiento FEFO real requiera confirmación."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")

    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "offsetDays": 5,
        "dryRun": False,
        "confirmStagingAction": False,
    }

    # Sin confirmación -> 400
    r_unconfirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers,
        json=payload,
    )
    assert r_unconfirmed.status_code == 400
    assert r_unconfirmed.json()["error_code"] == "STAGING_CONFIRMATION_REQUIRED"

    # Con confirmación en cabecera -> 200
    r_confirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers={**headers, "X-Sandbox-Confirm-Staging": "true"},
        json=payload,
    )
    assert r_confirmed.status_code == 200
    assert r_confirmed.json()["status"] == "applied"


# ============================================================================
# 3. PRUEBAS DE AISLAMIENTO DE ESQUEMAS MULTI-TENANT (ANTI-CONTAMINACIÓN)
# ============================================================================


@pytest.mark.asyncio
async def test_non_isolated_schema_is_blocked_for_real_injection(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que intentar inyectar datos en un esquema público o productivo no aislado
    (ej. 'public' o 'tenant_restaurante_real') sea rechazado inmediatamente con HTTP 400.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_restaurante_real_produccion",
        "categories": ["all"],
        "volume": "small",
        "dryRun": False,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "ISOLATED_SCHEMA_REQUIRED"


# ============================================================================
# 4. PRUEBAS DE OBSERVABILIDAD Y OPENTELEMETRY TRACEPARENT
# ============================================================================


@pytest.mark.asyncio
async def test_opentelemetry_trace_headers_propagation(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que:
    1. Una petición con X-Trace-ID y traceparent preserve la correlación de traza.
    2. La respuesta devuelva la cabecera X-Trace-ID idéntica a la enviada.
    """
    client_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    client_traceparent = f"00-{client_trace_id}-00f067aa0ba902b7-01"

    headers = _make_admin_headers(
        ["platform_admin.sandbox.access"],
        extra_headers={
            "X-Trace-ID": client_trace_id,
            "traceparent": client_traceparent,
        },
    )

    response = await async_client.get(
        "/api/v1/platform-admin/sandbox/status",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == client_trace_id

    data = response.json()
    assert "isMutationAllowed" in data
    assert "environmentPolicy" in data


@pytest.mark.asyncio
async def test_sandbox_status_reports_correct_policy_by_environment(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que /sandbox/status reporte isMutationAllowed=False en producción."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    headers = _make_admin_headers(["platform_admin.sandbox.access"])
    response = await async_client.get(
        "/api/v1/platform-admin/sandbox/status",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["environment"] == "production"
    assert data["isMutationAllowed"] is False
    assert data["environmentPolicy"] == "strict_read_only_protection"


# ============================================================================
# 5. SUB-PLAN 2: GUARDRAILS DE ENTORNOS Y OBSERVABILIDAD PARA FACTORY RESET Y PRESETS
# ============================================================================


@pytest.mark.asyncio
async def test_production_environment_blocks_factory_reset_mock_data(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifica que en 'production', POST /mock-data/reset falle de forma FAIL-FAST
    inmediata con HTTP 403 'PRODUCTION_MUTATION_FORBIDDEN'.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "targetPresetId": "fast-food-pollo-king",
        "confirmReset": True,
        "confirmStagingAction": True,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 403
    data = response.json()
    assert data["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"
    assert "production" in data["detail"].lower()


@pytest.mark.asyncio
async def test_staging_environment_requires_explicit_confirmation_for_factory_reset(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifica que en 'staging', POST /mock-data/reset exija confirmación explícita:
    - Sin confirmación -> 400 'STAGING_CONFIRMATION_REQUIRED'
    - Con confirmStagingAction=True en payload -> 200 OK
    - Con cabecera X-Sandbox-Confirm-Staging: true -> 200 OK
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")

    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    base_payload = {
        "tenantSchema": "tenant_qa_lab",
        "targetPresetId": "carnes-angus-cava",
        "confirmReset": True,
        "confirmStagingAction": False,
    }

    # 1. Sin confirmación de staging -> HTTP 400
    res_unconfirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json=base_payload,
    )
    assert res_unconfirmed.status_code == 400
    assert res_unconfirmed.json()["error_code"] == "STAGING_CONFIRMATION_REQUIRED"

    # 2. Con confirmStagingAction=True en body -> HTTP 200 OK
    res_confirmed_body = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json={**base_payload, "confirmStagingAction": True},
    )
    assert res_confirmed_body.status_code == 200
    data_body = res_confirmed_body.json()
    assert data_body["presetRestored"] == "carnes-angus-cava"
    assert data_body["tenantSchema"] == "tenant_qa_lab"

    # 3. Con cabecera X-Sandbox-Confirm-Staging: true -> HTTP 200 OK
    res_confirmed_header = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers={**headers, "X-Sandbox-Confirm-Staging": "true"},
        json=base_payload,
    )
    assert res_confirmed_header.status_code == 200
    assert res_confirmed_header.json()["presetRestored"] == "carnes-angus-cava"


@pytest.mark.asyncio
async def test_factory_reset_blocks_non_isolated_schema_in_all_environments(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que en cualquier entorno (local/dev/ci/staging), intentar resetear
    un esquema no aislado (ej. 'public' o 'tenant_restaurante_real') falle con HTTP 400 'ISOLATED_SCHEMA_REQUIRED'.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_restaurante_real_produccion",
        "targetPresetId": "clean-slate",
        "confirmReset": True,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "ISOLATED_SCHEMA_REQUIRED"


@pytest.mark.asyncio
async def test_factory_reset_requires_confirm_reset_flag(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que si confirmReset=False, se rechace con HTTP 400 'RESET_CONFIRMATION_REQUIRED'.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "targetPresetId": "hotel-desayuno-buffet",
        "confirmReset": False,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "RESET_CONFIRMATION_REQUIRED"


@pytest.mark.asyncio
async def test_opentelemetry_and_mock_mode_propagation_on_presets(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que GET /mock-data/presets:
    1. Propague y preserve X-Trace-ID y traceparent W3C.
    2. Registre y refleje X-OppyTec-Mock-Mode: clean en cabeceras de respuesta.
    """
    client_trace_id = "5a3169813ac8459f9ccd84368de01bfe"
    client_traceparent = f"00-{client_trace_id}-00f067aa0ba902b7-01"

    headers = _make_admin_headers(
        ["platform_admin.sandbox.access"],
        extra_headers={
            "X-Trace-ID": client_trace_id,
            "traceparent": client_traceparent,
            "X-OppyTec-Mock-Mode": "clean",
        },
    )

    response = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/presets",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == client_trace_id
    assert response.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert response.headers.get("traceparent", "").endswith("-01")
    assert response.headers.get("X-OppyTec-Mock-Mode") == "clean"

    data = response.json()
    assert "presets" in data
    assert len(data["presets"]) == 4


@pytest.mark.asyncio
async def test_opentelemetry_and_mock_mode_propagation_on_factory_reset(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que POST /mock-data/reset:
    1. Propague y devuelva X-Trace-ID y traceparent W3C.
    2. Refleje X-OppyTec-Mock-Mode: demo en cabeceras de respuesta.
    """
    client_trace_id = "1a324d6148304ad5905d2c7375d795ea"
    client_traceparent = f"00-{client_trace_id}-1122334455667788-01"

    headers = _make_admin_headers(
        ["platform_admin.sandbox.manage"],
        extra_headers={
            "X-Trace-ID": client_trace_id,
            "traceparent": client_traceparent,
            "X-OppyTec-Mock-Mode": "demo",
        },
    )

    payload = {
        "tenantSchema": "tenant_sandbox_fefo",
        "targetPresetId": "hotel-desayuno-buffet",
        "confirmReset": True,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == client_trace_id
    assert response.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert response.headers.get("traceparent", "").endswith("-01")
    assert response.headers.get("X-OppyTec-Mock-Mode") == "demo"

    data = response.json()
    assert data["presetRestored"] == "hotel-desayuno-buffet"
    assert data["tenantSchema"] == "tenant_sandbox_fefo"


@pytest.mark.asyncio
async def test_opentelemetry_headers_preserved_on_forbidden_production_error(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifica que incluso ante excepciones de dominio (HTTP 403 Forbidden en producción),
    las cabeceras X-Trace-ID, traceparent y X-OppyTec-Mock-Mode se preserven intactas
    en la respuesta devuelta por oppytec_domain_exception_handler.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    client_trace_id = "77777777777777777777777777777777"
    client_traceparent = f"00-{client_trace_id}-8888888888888888-01"

    headers = _make_admin_headers(
        ["platform_admin.sandbox.manage"],
        extra_headers={
            "X-Trace-ID": client_trace_id,
            "traceparent": client_traceparent,
            "X-OppyTec-Mock-Mode": "clean",
        },
    )

    payload = {
        "tenantSchema": "tenant_qa_lab",
        "targetPresetId": "fast-food-pollo-king",
        "confirmReset": True,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 403
    assert response.headers.get("X-Trace-ID") == client_trace_id
    assert response.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert response.headers.get("traceparent", "").endswith("-01")
    assert response.headers.get("X-OppyTec-Mock-Mode") == "clean"
    assert response.json()["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"


# ============================================================================
# 6. SUB-PLAN 3: OBSERVABILIDAD OPENTELEMETRY Y AISLAMIENTO DE ENTORNOS PARA PLAYWRIGHT
# ============================================================================


@pytest.mark.asyncio
async def test_playwright_endpoints_accept_and_propagate_traceparent_and_trace_id(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que las solicitudes a los nuevos endpoints de Playwright:
    1. GET  /api/v1/platform-admin/sandbox/playwright/catalog
    2. POST /api/v1/platform-admin/sandbox/playwright/run
    3. GET  /api/v1/platform-admin/sandbox/playwright/stream/{run_id}
    Acepten, propaguen y preserven las cabeceras W3C traceparent y X-Trace-ID de forma bidireccional.
    """
    client_trace_id = "0123456789abcdef0123456789abcdef"
    client_span_id = "fedcba9876543210"
    client_traceparent = f"00-{client_trace_id}-{client_span_id}-01"

    extra_headers = {
        "X-Trace-ID": client_trace_id,
        "traceparent": client_traceparent,
    }

    headers_access = _make_admin_headers(
        ["platform_admin.sandbox.access"],
        extra_headers=extra_headers,
    )
    headers_manage = _make_admin_headers(
        ["platform_admin.sandbox.manage"],
        extra_headers=extra_headers,
    )

    # 1. Endpoint /catalog
    res_catalog = await async_client.get(
        "/api/v1/platform-admin/sandbox/playwright/catalog",
        headers=headers_access,
    )
    assert res_catalog.status_code == 200
    assert res_catalog.headers.get("X-Trace-ID") == client_trace_id
    assert res_catalog.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert res_catalog.headers.get("traceparent", "").endswith("-01")
    data_cat = res_catalog.json()
    assert "summary" in data_cat
    assert "domains" in data_cat
    assert data_cat["summary"]["total"] >= 1

    # 2. Endpoint /run
    run_payload = {
        "scope": "domain",
        "targetId": "tenancy",
        "headless": True,
        "slowMoMs": 0,
        "browser": "chromium",
        "targetTenantSchema": "tenant_qa_lab",
    }
    res_run = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers_manage,
        json=run_payload,
    )
    assert res_run.status_code == 202
    assert res_run.headers.get("X-Trace-ID") == client_trace_id
    assert res_run.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert res_run.headers.get("traceparent", "").endswith("-01")
    data_run = res_run.json()
    assert "runId" in data_run
    assert data_run["status"] == "queued"
    assert data_run["testsQueued"] > 0
    run_id = data_run["runId"]

    # 3. Endpoint /stream/{run_id} (Server-Sent Events)
    res_stream = await async_client.get(
        f"/api/v1/platform-admin/sandbox/playwright/stream/{run_id}",
        headers=headers_access,
    )
    assert res_stream.status_code == 200
    assert res_stream.headers.get("X-Trace-ID") == client_trace_id
    assert res_stream.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert res_stream.headers.get("traceparent", "").endswith("-01")
    assert "text/event-stream" in res_stream.headers.get("content-type", "")
    assert "event: step" in res_stream.text
    assert "event: completed" in res_stream.text


@pytest.mark.asyncio
async def test_playwright_production_guardrail_fail_fast_and_confirmation_mechanisms(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifica que en entorno canónico 'production':
    1. Las peticiones de ejecución sin confirmación sean rechazadas Fail-Fast con HTTP 400
       ('PRODUCTION_CONFIRMATION_REQUIRED') tanto para corridas de dominio como de test individual.
    2. Las peticiones con confirmación en payload ('confirmProductionRun: true') sean aceptadas (HTTP 202).
    3. Las peticiones con confirmación en cabecera ('X-Sandbox-Confirm-Production: true') sean aceptadas (HTTP 202).
    4. Las cabeceras W3C traceparent y X-Trace-ID se preserven incluso en el rechazo por guardrail.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    client_trace_id = "abcdef0123456789abcdef0123456789"
    client_traceparent = f"00-{client_trace_id}-1234567890abcdef-01"

    headers = _make_admin_headers(
        ["platform_admin.sandbox.manage"],
        extra_headers={
            "X-Trace-ID": client_trace_id,
            "traceparent": client_traceparent,
        },
    )

    unconfirmed_domain_payload = {
        "scope": "domain",
        "targetId": "inventory",
        "headless": True,
        "slowMoMs": 0,
        "confirmProductionRun": False,
    }

    # 1. Rechazo de ejecución de dominio sin confirmación -> HTTP 400
    res_domain_unconfirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json=unconfirmed_domain_payload,
    )
    assert res_domain_unconfirmed.status_code == 400
    assert res_domain_unconfirmed.headers.get("X-Trace-ID") == client_trace_id
    assert res_domain_unconfirmed.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    domain_err = res_domain_unconfirmed.json()
    assert domain_err["error_code"] == "PRODUCTION_CONFIRMATION_REQUIRED"
    assert "confirmProductionRun=true" in domain_err["detail"]

    # 2. Rechazo de ejecución de test individual sin confirmación -> HTTP 400
    unconfirmed_test_payload = {
        "scope": "test",
        "targetId": "pw_inv_01_fefo_expiry",
        "headless": True,
        "slowMoMs": 0,
        "confirmProductionRun": False,
    }
    res_test_unconfirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json=unconfirmed_test_payload,
    )
    assert res_test_unconfirmed.status_code == 400
    assert res_test_unconfirmed.json()["error_code"] == "PRODUCTION_CONFIRMATION_REQUIRED"

    # 3. Aprobación mediante flag booleano en payload (confirmProductionRun=True) -> HTTP 202
    confirmed_body_payload = {
        **unconfirmed_domain_payload,
        "confirmProductionRun": True,
    }
    res_confirmed_body = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json=confirmed_body_payload,
    )
    assert res_confirmed_body.status_code == 202
    assert res_confirmed_body.headers.get("X-Trace-ID") == client_trace_id
    data_confirmed_body = res_confirmed_body.json()
    assert data_confirmed_body["status"] == "queued"
    assert data_confirmed_body["testsQueued"] > 0

    # 4. Aprobación mediante cabecera HTTP (X-Sandbox-Confirm-Production: true) -> HTTP 202
    headers_with_confirm = {
        **headers,
        "X-Sandbox-Confirm-Production": "true",
    }
    res_confirmed_header = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers_with_confirm,
        json=unconfirmed_domain_payload,
    )
    assert res_confirmed_header.status_code == 202
    assert res_confirmed_header.headers.get("X-Trace-ID") == client_trace_id
    data_confirmed_header = res_confirmed_header.json()
    assert data_confirmed_header["status"] == "queued"


@pytest.mark.asyncio
async def test_playwright_stream_sse_events_include_valid_iso_timestamps_and_p95_durations(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que el flujo de eventos Server-Sent Events (SSE) de Playwright:
    1. Emita eventos 'step' estructurados con timestamps ISO 8601 UTC estrictos.
    2. Contenga el campo 'durationMs' en cada paso (entero >= 0) para cálculo y observabilidad de percentiles SLA P95.
    3. Emita el evento 'completed' con la sumatoria de duración agregada, métricas de éxito y estado final.
    4. Permita calcular analíticamente el SLA P95 sobre el conjunto de asertos de la corrida.
    """
    headers_manage = _make_admin_headers(["platform_admin.sandbox.manage"])
    headers_access = _make_admin_headers(["platform_admin.sandbox.access"])

    # Disparar corrida para dominio 'recipes'
    run_res = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers_manage,
        json={
            "scope": "domain",
            "targetId": "recipes",
            "headless": True,
            "slowMoMs": 0,
        },
    )
    assert run_res.status_code == 202
    run_id = run_res.json()["runId"]

    # Consumir stream de eventos SSE
    stream_res = await async_client.get(
        f"/api/v1/platform-admin/sandbox/playwright/stream/{run_id}",
        headers=headers_access,
    )
    assert stream_res.status_code == 200

    raw_text = stream_res.text
    blocks = raw_text.strip().split("\n\n")
    assert len(blocks) >= 2, "El stream debe contener al menos pasos y evento completed"

    parsed_events: list[dict[str, object]] = []
    for block in blocks:
        lines = block.strip().split("\n")
        event_dict: dict[str, object] = {}
        for line in lines:
            if line.startswith("event: "):
                event_dict["event"] = line[len("event: "):].strip()
            elif line.startswith("id: "):
                event_dict["id"] = int(line[len("id: "):].strip())
            elif line.startswith("data: "):
                event_dict["data"] = json.loads(line[len("data: "):].strip())
        if event_dict:
            parsed_events.append(event_dict)

    step_events = [e for e in parsed_events if e.get("event") == "step"]
    completed_events = [e for e in parsed_events if e.get("event") == "completed"]

    assert len(step_events) >= 1, "Debe existir al menos un evento step en el stream"
    assert len(completed_events) == 1, "Debe existir exactamente un evento completed"

    durations_ms: list[int] = []
    now_utc = datetime.now(UTC)

    # Validación exhaustiva de cada evento 'step'
    for ev in step_events:
        data = ev["data"]
        assert isinstance(data, dict)
        assert "stepIndex" in data and isinstance(data["stepIndex"], int)
        assert data["stepIndex"] >= 1
        assert "testId" in data and isinstance(data["testId"], str) and len(data["testId"]) > 0
        assert "level" in data and data["level"] in ("step", "assert", "info", "warn", "error", "debug")
        assert "message" in data and isinstance(data["message"], str)

        # Validación estricta de timestamp ISO 8601 UTC
        assert "timestamp" in data
        ts_str = data["timestamp"]
        assert isinstance(ts_str, str)
        parsed_dt = datetime.fromisoformat(ts_str)
        assert parsed_dt.tzinfo is not None, "El timestamp debe incluir huso horario UTC explícito"
        delta_seconds = abs((now_utc - parsed_dt).total_seconds())
        assert delta_seconds < 300, "El timestamp no debe diferir más de 5 minutos del tiempo real"

        # Validación estricta de durationMs para observabilidad y cálculo de SLA P95
        assert "durationMs" in data
        dur = data["durationMs"]
        assert isinstance(dur, int), "durationMs debe ser un entero no negativo de milisegundos"
        assert dur >= 0, "durationMs no puede ser negativo"
        durations_ms.append(dur)

    # Validación del evento 'completed'
    completed_data = completed_events[0]["data"]
    assert isinstance(completed_data, dict)
    assert completed_data["runId"] == run_id
    assert completed_data["status"] == "completed"
    assert completed_data["totalTests"] > 0
    assert completed_data["passedTests"] == completed_data["totalTests"]
    assert completed_data["failedTests"] == 0
    assert isinstance(completed_data["durationMs"], int)
    assert completed_data["durationMs"] == sum(durations_ms)

    # Cómputo matemático determinista de Percentil SLA P95
    durations_ms.sort()
    p95_index = max(0, math.ceil(0.95 * len(durations_ms)) - 1)
    p95_value = durations_ms[p95_index]
    assert p95_value > 0, "El valor P95 calculado debe ser estrictamente positivo"
    assert p95_value <= 10000, "El valor P95 de los pasos debe mantenerse bajo el umbral SLA esperado"


@pytest.mark.asyncio
async def test_playwright_status_endpoint_preserves_opentelemetry_headers(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que el endpoint GET /playwright/status/{run_id} acepte y propague
    las cabeceras W3C traceparent y X-Trace-ID de forma simétrica.
    """
    client_trace_id = "99887766554433221100aabbccddeeff"
    client_traceparent = f"00-{client_trace_id}-fedcba9876543210-01"

    headers = _make_admin_headers(
        ["platform_admin.sandbox.access"],
        extra_headers={
            "X-Trace-ID": client_trace_id,
            "traceparent": client_traceparent,
        },
    )

    response = await async_client.get(
        "/api/v1/platform-admin/sandbox/playwright/status/run_smoke_001",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == client_trace_id
    assert response.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert response.headers.get("traceparent", "").endswith("-01")
    data = response.json()
    assert data["runId"] == "run_smoke_001"


# ============================================================================
# 7. SUB-PLAN 4: OBSERVABILIDAD OPENTELEMETRY Y AISLAMIENTO DE ENTORNOS PARA SIMULADOR FEFO
# ============================================================================


@pytest.mark.asyncio
async def test_fefo_endpoints_accept_and_propagate_traceparent_and_trace_id(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que las solicitudes a los 3 endpoints del Simulador FEFO:
    1. POST /api/v1/platform-admin/sandbox/fefo/simulate
    2. POST /api/v1/platform-admin/sandbox/fefo/shift
    3. POST /api/v1/platform-admin/sandbox/fefo/sync-today
    Acepten, propaguen y preserven las cabeceras W3C traceparent y X-Trace-ID de forma bidireccional.
    """
    client_trace_id = "fef00123456789abcdef0123456789ab"
    client_span_id = "a1b2c3d4e5f60718"
    client_traceparent = f"00-{client_trace_id}-{client_span_id}-01"

    extra_headers = {
        "X-Trace-ID": client_trace_id,
        "traceparent": client_traceparent,
    }

    headers_access = _make_admin_headers(
        ["platform_admin.sandbox.access"],
        extra_headers=extra_headers,
    )
    headers_manage = _make_admin_headers(
        ["platform_admin.sandbox.manage"],
        extra_headers=extra_headers,
    )

    # 1. Endpoint /fefo/simulate (Lectura proyectiva pura)
    simulate_payload = {
        "tenantSchema": "tenant_sandbox_fefo",
        "offsetDays": 0,
        "scenarioPreset": "WARNING",
        "currency": "CLP",
        "exchangeRate": 950.0,
        "dryRun": True,
    }
    res_simulate = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers_access,
        json=simulate_payload,
    )
    assert res_simulate.status_code == 200
    assert res_simulate.headers.get("X-Trace-ID") == client_trace_id
    assert res_simulate.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert res_simulate.headers.get("traceparent", "").endswith("-01")
    sim_data = res_simulate.json()
    assert "simulationId" in sim_data
    assert sim_data["scenarioApplied"] == "WARNING"
    assert sim_data["totalBatchesEvaluated"] == 20
    assert sim_data["criticalBatchesCount"] == 4
    assert sim_data["warningBatchesCount"] == 6
    assert sim_data["optimalBatchesCount"] == 10
    assert sim_data["totalSpoilageRiskAmount"] > 0
    assert sim_data["totalSpoilageRiskFxAmount"] is not None

    # 2. Endpoint /fefo/shift (Desplazamiento temporal con dryRun=True)
    shift_payload = {
        "tenantSchema": "tenant_sandbox_fefo",
        "offsetDays": 7,
        "dryRun": True,
        "recalculateBuffet": True,
    }
    res_shift = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers_manage,
        json=shift_payload,
    )
    assert res_shift.status_code == 200
    assert res_shift.headers.get("X-Trace-ID") == client_trace_id
    assert res_shift.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert res_shift.headers.get("traceparent", "").endswith("-01")
    shift_data = res_shift.json()
    assert shift_data["tenantSchema"] == "tenant_sandbox_fefo"
    assert shift_data["offsetDays"] == 7
    assert shift_data["status"] == "preview_only"

    # 3. Endpoint /fefo/sync-today (Sincronización quirúrgica con dryRun=True)
    sync_payload = {
        "tenantSchema": "tenant_sandbox_fefo",
        "dryRun": True,
        "recalculateBuffetLots": True,
    }
    res_sync = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers_manage,
        json=sync_payload,
    )
    assert res_sync.status_code == 200
    assert res_sync.headers.get("X-Trace-ID") == client_trace_id
    assert res_sync.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert res_sync.headers.get("traceparent", "").endswith("-01")
    sync_data = res_sync.json()
    assert sync_data["tenantSchema"] == "tenant_sandbox_fefo"
    assert sync_data["status"] == "preview_only"
    assert "baseTodayIso" in sync_data


@pytest.mark.asyncio
async def test_fefo_production_guardrail_blocks_mutations_and_allows_simulation(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifica que en entorno canónico 'production':
    1. Las mutaciones destructivas (dryRun=False) en /fefo/shift y /fefo/sync-today
       sean bloqueadas Fail-Fast con HTTP 403 ('PRODUCTION_MUTATION_FORBIDDEN').
    2. Las operaciones de sólo lectura / cálculo proyectivo (dryRun=True) estén permitidas (HTTP 200).
    3. El endpoint proyectivo /fefo/simulate esté permitido sin restricciones en producción (HTTP 200).
    4. Las cabeceras W3C traceparent y X-Trace-ID se preserven en todos los casos (incluso 403).
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    client_trace_id = "proddeadbeef00112233445566778899"
    client_traceparent = f"00-{client_trace_id}-9988776655443322-01"

    extra_headers = {
        "X-Trace-ID": client_trace_id,
        "traceparent": client_traceparent,
    }
    headers_manage = _make_admin_headers(
        ["platform_admin.sandbox.manage"],
        extra_headers=extra_headers,
    )
    headers_access = _make_admin_headers(
        ["platform_admin.sandbox.access"],
        extra_headers=extra_headers,
    )

    # 1. /fefo/shift con dryRun=False en production -> HTTP 403
    res_shift_blocked = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers_manage,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 14,
            "dryRun": False,
        },
    )
    assert res_shift_blocked.status_code == 403
    assert res_shift_blocked.headers.get("X-Trace-ID") == client_trace_id
    assert res_shift_blocked.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    shift_err = res_shift_blocked.json()
    assert shift_err["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"
    assert "production" in shift_err["detail"].lower()

    # 2. /fefo/sync-today con dryRun=False en production -> HTTP 403
    res_sync_blocked = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers_manage,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "dryRun": False,
        },
    )
    assert res_sync_blocked.status_code == 403
    assert res_sync_blocked.headers.get("X-Trace-ID") == client_trace_id
    assert res_sync_blocked.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    sync_err = res_sync_blocked.json()
    assert sync_err["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"
    assert "production" in sync_err["detail"].lower()

    # 3. /fefo/shift con dryRun=True en production -> HTTP 200 (Permitido como preview)
    res_shift_allowed = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers_manage,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 5,
            "dryRun": True,
        },
    )
    assert res_shift_allowed.status_code == 200
    assert res_shift_allowed.headers.get("X-Trace-ID") == client_trace_id
    assert res_shift_allowed.json()["status"] == "preview_only"

    # 4. /fefo/sync-today con dryRun=True en production -> HTTP 200 (Permitido como preview)
    res_sync_allowed = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers_manage,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "dryRun": True,
        },
    )
    assert res_sync_allowed.status_code == 200
    assert res_sync_allowed.headers.get("X-Trace-ID") == client_trace_id
    assert res_sync_allowed.json()["status"] == "preview_only"

    # 5. /fefo/simulate en production -> HTTP 200 (Permitido, es pura simulación analítica)
    res_sim_prod = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers_access,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 0,
            "scenarioPreset": "CRITICAL",
        },
    )
    assert res_sim_prod.status_code == 200
    assert res_sim_prod.headers.get("X-Trace-ID") == client_trace_id
    assert res_sim_prod.json()["criticalBatchesCount"] == 7
    assert res_sim_prod.json()["expiredBatchesCount"] == 3


@pytest.mark.asyncio
async def test_fefo_staging_guardrail_requires_confirmation_for_shift_and_sync_today(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifica que en entorno canónico 'staging':
    1. Las mutaciones reales (dryRun=False) sin confirmación sean rechazadas con HTTP 400
       ('STAGING_CONFIRMATION_REQUIRED') para /fefo/shift y /fefo/sync-today.
    2. La confirmación vía payload ('confirmStagingAction=True') sea aceptada con HTTP 200.
    3. La confirmación vía cabecera ('X-Sandbox-Confirm-Staging: true') sea aceptada con HTTP 200.
    4. Las operaciones no destructivas (dryRun=True) no requieran confirmación.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")

    client_trace_id = "stagingfefo0123456789abcdef0123"
    client_traceparent = f"00-{client_trace_id}-1122334455667788-01"

    headers = _make_admin_headers(
        ["platform_admin.sandbox.manage"],
        extra_headers={
            "X-Trace-ID": client_trace_id,
            "traceparent": client_traceparent,
        },
    )

    # --- FEFO SHIFT EN STAGING ---

    # 1. Shift sin confirmación -> HTTP 400
    res_shift_unconfirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 10,
            "dryRun": False,
            "confirmStagingAction": False,
        },
    )
    assert res_shift_unconfirmed.status_code == 400
    assert res_shift_unconfirmed.headers.get("X-Trace-ID") == client_trace_id
    assert res_shift_unconfirmed.json()["error_code"] == "STAGING_CONFIRMATION_REQUIRED"

    # 2. Shift con confirmación en body -> HTTP 200
    res_shift_body_confirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 10,
            "dryRun": False,
            "confirmStagingAction": True,
        },
    )
    assert res_shift_body_confirmed.status_code == 200
    assert res_shift_body_confirmed.headers.get("X-Trace-ID") == client_trace_id
    assert res_shift_body_confirmed.json()["status"] == "applied"
    assert res_shift_body_confirmed.json()["shiftedBatchesCount"] > 0

    # 3. Shift con confirmación en cabecera HTTP -> HTTP 200
    res_shift_header_confirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers={**headers, "X-Sandbox-Confirm-Staging": "true"},
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 10,
            "dryRun": False,
            "confirmStagingAction": False,
        },
    )
    assert res_shift_header_confirmed.status_code == 200
    assert res_shift_header_confirmed.json()["status"] == "applied"

    # --- FEFO SYNC-TODAY EN STAGING ---

    # 4. Sync-Today sin confirmación -> HTTP 400
    res_sync_unconfirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "dryRun": False,
            "confirmStagingAction": False,
        },
    )
    assert res_sync_unconfirmed.status_code == 400
    assert res_sync_unconfirmed.headers.get("X-Trace-ID") == client_trace_id
    assert res_sync_unconfirmed.json()["error_code"] == "STAGING_CONFIRMATION_REQUIRED"

    # 5. Sync-Today con confirmación en body -> HTTP 200
    res_sync_body_confirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "dryRun": False,
            "confirmStagingAction": True,
            "recalculateBuffetLots": True,
        },
    )
    assert res_sync_body_confirmed.status_code == 200
    assert res_sync_body_confirmed.headers.get("X-Trace-ID") == client_trace_id
    assert res_sync_body_confirmed.json()["status"] == "synchronized"
    assert res_sync_body_confirmed.json()["synchronizedBatchesCount"] == 20
    assert res_sync_body_confirmed.json()["buffetsRecalculatedCount"] == 8

    # 6. Sync-Today con confirmación en cabecera HTTP -> HTTP 200
    res_sync_header_confirmed = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers={**headers, "X-Sandbox-Confirm-Staging": "true"},
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "dryRun": False,
            "confirmStagingAction": False,
        },
    )
    assert res_sync_header_confirmed.status_code == 200
    assert res_sync_header_confirmed.json()["status"] == "synchronized"

    # 7. Operaciones con dryRun=True en staging no requieren confirmación
    res_shift_preview = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 3,
            "dryRun": True,
        },
    )
    assert res_shift_preview.status_code == 200
    assert res_shift_preview.json()["status"] == "preview_only"


@pytest.mark.asyncio
async def test_fefo_mutations_block_non_isolated_schemas_in_all_environments(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que en cualquier entorno:
    1. Las mutaciones reales (dryRun=False) en esquemas NO aislados (ej. 'public', 'tenant_restaurante_real', 'tenant_produccion')
       sean rechazadas con HTTP 400 ('ISOLATED_SCHEMA_REQUIRED') tanto en /fefo/shift como en /fefo/sync-today.
    2. Las mutaciones reales en esquemas aislados autorizados ('tenant_qa_lab', 'tenant_sandbox_fefo',
       'tenant_qa_custom', 'tenant_genesis') sean admitidas con HTTP 200.
    3. Las simulaciones/previews (dryRun=True) sobre esquemas no aislados no disparen el guardrail de mutación destructiva.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])

    non_isolated_schemas = [
        "public",
        "tenant_restaurante_real_produccion",
        "tenant_holding_master_prod",
        "tenant_contabilidad_oficial",
    ]

    for non_iso in non_isolated_schemas:
        # /fefo/shift con dryRun=False -> 400
        res_shift_bad = await async_client.post(
            "/api/v1/platform-admin/sandbox/fefo/shift",
            headers=headers,
            json={
                "tenantSchema": non_iso,
                "offsetDays": 5,
                "dryRun": False,
            },
        )
        assert res_shift_bad.status_code == 400
        assert res_shift_bad.json()["error_code"] == "ISOLATED_SCHEMA_REQUIRED"

        # /fefo/sync-today con dryRun=False -> 400
        res_sync_bad = await async_client.post(
            "/api/v1/platform-admin/sandbox/fefo/sync-today",
            headers=headers,
            json={
                "tenantSchema": non_iso,
                "dryRun": False,
            },
        )
        assert res_sync_bad.status_code == 400
        assert res_sync_bad.json()["error_code"] == "ISOLATED_SCHEMA_REQUIRED"

        # /fefo/shift con dryRun=True -> 200 (Permitido preview no destructivo)
        res_shift_ok_dry = await async_client.post(
            "/api/v1/platform-admin/sandbox/fefo/shift",
            headers=headers,
            json={
                "tenantSchema": non_iso,
                "offsetDays": 5,
                "dryRun": True,
            },
        )
        assert res_shift_ok_dry.status_code == 200
        assert res_shift_ok_dry.json()["status"] == "preview_only"

    # Esquemas aislados válidos autorizados:
    authorized_isolated_schemas = [
        "tenant_qa_lab",
        "tenant_sandbox_fefo",
        "tenant_genesis",
        "tenant_qa_automated_01",
        "tenant_sandbox_test_lab",
    ]

    for auth_iso in authorized_isolated_schemas:
        res_shift_auth = await async_client.post(
            "/api/v1/platform-admin/sandbox/fefo/shift",
            headers=headers,
            json={
                "tenantSchema": auth_iso,
                "offsetDays": 3,
                "dryRun": False,
            },
        )
        assert res_shift_auth.status_code == 200
        assert res_shift_auth.json()["status"] == "applied"


@pytest.mark.asyncio
async def test_fefo_simulation_presets_observability_and_loss_math(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que POST /fefo/simulate evalúe y reporte con exactitud matemática
    los 3 escenarios calibrados y la conversión de moneda extranjera (FX):
    1. HEALTHY: 90% óptimo, 10% advertencia, 0% crítico, 0% expirado, 0 CLP de merma.
    2. WARNING: 50% óptimo, 30% advertencia, 20% crítico, 0% expirado, merma controlada.
    3. CRITICAL: 25% óptimo, 25% advertencia, 35% crítico, 15% expirado, merma severa.
    4. Conversión FX precisa a centésimos de dólar (USD).
    5. Preservación simétrica de trazas OpenTelemetry X-Trace-ID y traceparent.
    """
    client_trace_id = "fef05cenar105001122334455667788"
    client_traceparent = f"00-{client_trace_id}-2233445566778899-01"

    headers = _make_admin_headers(
        ["platform_admin.sandbox.access"],
        extra_headers={
            "X-Trace-ID": client_trace_id,
            "traceparent": client_traceparent,
        },
    )

    fx_rate = 920.0

    # 1. Escenario HEALTHY
    res_healthy = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 0,
            "scenarioPreset": "HEALTHY",
            "currency": "CLP",
            "exchangeRate": fx_rate,
        },
    )
    assert res_healthy.status_code == 200
    assert res_healthy.headers.get("X-Trace-ID") == client_trace_id
    d_h = res_healthy.json()
    assert d_h["scenarioApplied"] == "HEALTHY"
    assert d_h["totalBatchesEvaluated"] == 20
    assert d_h["optimalBatchesCount"] == 18
    assert d_h["warningBatchesCount"] == 2
    assert d_h["criticalBatchesCount"] == 0
    assert d_h["expiredBatchesCount"] == 0
    assert d_h["totalSpoilageRiskAmount"] == 0.0
    assert d_h["totalSpoilageRiskFxAmount"] == 0.0

    # 2. Escenario WARNING (Base en offset 0)
    res_warning = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 0,
            "scenarioPreset": "WARNING",
            "currency": "CLP",
            "exchangeRate": fx_rate,
        },
    )
    assert res_warning.status_code == 200
    d_w = res_warning.json()
    assert d_w["scenarioApplied"] == "WARNING"
    assert d_w["totalBatchesEvaluated"] == 20
    assert d_w["optimalBatchesCount"] == 10
    assert d_w["warningBatchesCount"] == 6
    assert d_w["criticalBatchesCount"] == 4
    assert d_w["expiredBatchesCount"] == 0
    assert d_w["totalSpoilageRiskAmount"] > 0.0
    assert d_w["totalSpoilageRiskFxAmount"] == round(d_w["totalSpoilageRiskAmount"] / fx_rate, 2)

    # 3. Escenario CRITICAL (Base en offset 0)
    res_critical = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 0,
            "scenarioPreset": "CRITICAL",
            "currency": "CLP",
            "exchangeRate": fx_rate,
            "generateSpoilageEvents": True,
        },
    )
    assert res_critical.status_code == 200
    d_c = res_critical.json()
    assert d_c["scenarioApplied"] == "CRITICAL"
    assert d_c["totalBatchesEvaluated"] == 20
    assert d_c["optimalBatchesCount"] == 5
    assert d_c["warningBatchesCount"] == 5
    assert d_c["criticalBatchesCount"] == 7
    assert d_c["expiredBatchesCount"] == 3
    assert d_c["totalSpoilageRiskAmount"] > d_w["totalSpoilageRiskAmount"]
    assert d_c["totalSpoilageRiskFxAmount"] == round(d_c["totalSpoilageRiskAmount"] / fx_rate, 2)
    assert d_c["alertsCreated"] == 10  # 7 critical + 3 expired

    # 4. Proyección Dinámica con Time-Travel (Offset prospectivo +14 días en WARNING)
    res_warp = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "offsetDays": 14,
            "scenarioPreset": "WARNING",
            "currency": "CLP",
            "exchangeRate": fx_rate,
        },
    )
    assert res_warp.status_code == 200
    d_warp = res_warp.json()
    # Con +14 días de desfase, los lotes críticos originales caducan (expiredBatchesCount > 0)
    assert d_warp["expiredBatchesCount"] >= 4
    assert d_warp["totalSpoilageRiskAmount"] > d_w["totalSpoilageRiskAmount"]


@pytest.mark.asyncio
async def test_fefo_traceparent_preserved_on_all_error_responses(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifica que ante cualquier condición de error / rechazo por guardrail en FEFO
    (403 Forbidden en producción, 400 Bad Request en staging sin confirmación, o 400 esquema no aislado),
    la respuesta HTTP RFC 7807 conserve incondicionalmente las cabeceras W3C traceparent y X-Trace-ID.
    """
    client_trace_id = "err0rtrace1234567890abcdef012345"
    client_traceparent = f"00-{client_trace_id}-aabbccddeeff0011-01"

    headers = _make_admin_headers(
        ["platform_admin.sandbox.manage"],
        extra_headers={
            "X-Trace-ID": client_trace_id,
            "traceparent": client_traceparent,
        },
    )

    # Caso A: 400 por esquema no aislado
    res_err_schema = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers,
        json={
            "tenantSchema": "tenant_produccion_no_aislado",
            "offsetDays": 5,
            "dryRun": False,
        },
    )
    assert res_err_schema.status_code == 400
    assert res_err_schema.headers.get("X-Trace-ID") == client_trace_id
    assert res_err_schema.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert res_err_schema.json()["error_code"] == "ISOLATED_SCHEMA_REQUIRED"

    # Caso B: 400 por confirmación faltante en staging
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    res_err_staging = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "dryRun": False,
            "confirmStagingAction": False,
        },
    )
    assert res_err_staging.status_code == 400
    assert res_err_staging.headers.get("X-Trace-ID") == client_trace_id
    assert res_err_staging.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert res_err_staging.json()["error_code"] == "STAGING_CONFIRMATION_REQUIRED"

    # Caso C: 403 por mutación prohibida en producción
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res_err_prod = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "dryRun": False,
        },
    )
    assert res_err_prod.status_code == 403
    assert res_err_prod.headers.get("X-Trace-ID") == client_trace_id
    assert res_err_prod.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert res_err_prod.json()["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"


@pytest.mark.asyncio
async def test_opentelemetry_and_mock_mode_propagation_on_mock_data_backup(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que GET /api/v1/platform-admin/sandbox/mock-data/backup:
    1. Emita su trace_span OpenTelemetry ('platform_admin_sandbox.mock_data.backup') y preserve X-Trace-ID / traceparent.
    2. Refleje X-OppyTec-Mock-Mode ('clean' / 'demo') en las cabeceras de respuesta.
    3. Retorne el respaldo canónico mock_data_backup.json con holdings, tenants, clientUsers y plans.
    """
    client_trace_id = "bac400123456789abcdef0123456789a"
    client_traceparent = f"00-{client_trace_id}-1122334455667788-01"

    headers = _make_admin_headers(
        ["platform_admin.sandbox.access"],
        extra_headers={
            "X-Trace-ID": client_trace_id,
            "traceparent": client_traceparent,
            "X-OppyTec-Mock-Mode": "clean",
        },
    )

    response = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/backup",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == client_trace_id
    assert response.headers.get("traceparent", "").startswith(f"00-{client_trace_id}-")
    assert response.headers.get("traceparent", "").endswith("-01")
    assert response.headers.get("X-OppyTec-Mock-Mode") == "clean"

    data = response.json()
    assert "metadata" in data
    assert "postgresql_pre_clean_snapshot" in data
    assert "backend_modules" in data
    assert "tenancy_router" in data["backend_modules"]




