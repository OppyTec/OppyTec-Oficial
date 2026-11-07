"""
oppytec-backend/tests/unit/test_fefo_security_redteam.py
Auditoría Ofensiva Red Team y Verificación de Seguridad para el Simulador FEFO:
1. RBAC 3 Niveles:
   - Rechazo 401 a peticiones sin autenticación.
   - Rechazo 403 con GLOBAL_STAFF_REQUIRED a tokens de inquilino (is_global_staff=False).
   - Segregación estricta entre platform_admin.sandbox.access (solo lectura) y manage (mutaciones).
2. Blindaje Anti-IDOR Multi-Tenant:
   - Validación estricta de whitelist para esquemas aislados (tenant_qa_lab, tenant_sandbox_fefo, prefijo tenant_qa_*).
   - Rechazo 400 con ISOLATED_SCHEMA_REQUIRED para esquemas reales o 'public' en mutaciones destructivas.
3. Guardrails de Entorno Canónico Fail-Fast:
   - En 'production': Mutaciones físicas (dry_run=False) bloqueadas incondicionalmente con 403 PRODUCTION_MUTATION_FORBIDDEN.
   - En 'staging': Mutaciones físicas (dry_run=False) exigen confirmación obligatoria con 400 STAGING_CONFIRMATION_REQUIRED.
   - Admitidas en staging con confirmStagingAction=True o cabecera X-Sandbox-Confirm-Staging: true.
4. Bounds Checking & Prevención de DoS por Overflow:
   - Offset acotado estrictamente en [-30, +60] días.
   - Rechazo 422 ante desbordamientos temporales (ej. -31, 61, 999999999).
   - Aceptación en frontera válida [-30, +60].
5. Integridad de Esquemas Pydantic v2:
   - extra='forbid' contra inyecciones de atributos espurios.
"""
from __future__ import annotations

import httpx
import pytest

from src.core.config import get_settings
from src.core.guards.rbac_dependencies import clear_revoked_sessions
from src.core.security import create_access_token
from src.modules.tenancy.presentation.sandbox_router import get_sandbox_service

pytestmark = pytest.mark.unit


def _make_token_headers(
    permissions: list[str],
    user_id: int = 1,
    is_global_staff: bool = True,
    is_superuser_god: bool = False,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
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
    clear_revoked_sessions()
    service = get_sandbox_service()
    service.reset()


# ============================================================================
# 1. PRUEBAS RBAC 3 NIVELES (V1 - V3)
# ============================================================================


@pytest.mark.asyncio
async def test_fefo_endpoints_require_authentication(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que los 3 endpoints FEFO rechacen peticiones no autenticadas con HTTP 401."""
    endpoints = [
        ("/api/v1/platform-admin/sandbox/fefo/simulate", {"tenantSchema": "tenant_qa_lab", "offsetDays": 0}),
        ("/api/v1/platform-admin/sandbox/fefo/shift", {"tenantSchema": "tenant_qa_lab", "offsetDays": 0, "dryRun": True}),
        ("/api/v1/platform-admin/sandbox/fefo/sync-today", {"tenantSchema": "tenant_qa_lab", "dryRun": True}),
    ]
    for url, payload in endpoints:
        res = await async_client.post(url, json=payload)
        assert res.status_code == 401, f"Endpoint {url} debió responder 401"


@pytest.mark.asyncio
async def test_fefo_endpoints_reject_tenant_scoped_tokens(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que un token de inquilino (is_global_staff=False) sea bloqueado
    con HTTP 403 y error_code 'GLOBAL_STAFF_REQUIRED' en todos los endpoints FEFO.
    """
    tenant_headers = _make_token_headers(
        permissions=["platform_admin.sandbox.access", "platform_admin.sandbox.manage"],
        is_global_staff=False,
    )
    endpoints = [
        ("/api/v1/platform-admin/sandbox/fefo/simulate", {"tenantSchema": "tenant_qa_lab", "offsetDays": 0}),
        ("/api/v1/platform-admin/sandbox/fefo/shift", {"tenantSchema": "tenant_qa_lab", "offsetDays": 0, "dryRun": True}),
        ("/api/v1/platform-admin/sandbox/fefo/sync-today", {"tenantSchema": "tenant_qa_lab", "dryRun": True}),
    ]
    for url, payload in endpoints:
        res = await async_client.post(url, headers=tenant_headers, json=payload)
        assert res.status_code == 403, f"Endpoint {url} debió responder 403 a token de inquilino"
        assert res.json()["error_code"] == "GLOBAL_STAFF_REQUIRED"


@pytest.mark.asyncio
async def test_fefo_read_only_token_cannot_execute_mutations(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que el permiso platform_admin.sandbox.access permita /fefo/simulate
    pero rechace /fefo/shift y /fefo/sync-today con HTTP 403.
    """
    read_headers = _make_token_headers(["platform_admin.sandbox.access"])

    # /fefo/simulate -> 200 OK
    res_sim = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=read_headers,
        json={"tenantSchema": "tenant_qa_lab", "offsetDays": 0},
    )
    assert res_sim.status_code == 200

    # /fefo/shift -> 403 Forbidden
    res_shift = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=read_headers,
        json={"tenantSchema": "tenant_qa_lab", "offsetDays": 0, "dryRun": True},
    )
    assert res_shift.status_code == 403

    # /fefo/sync-today -> 403 Forbidden
    res_sync = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=read_headers,
        json={"tenantSchema": "tenant_qa_lab", "dryRun": True},
    )
    assert res_sync.status_code == 403


# ============================================================================
# 2. PRUEBAS BLINDAJE ANTI-IDOR MULTI-TENANT (V4)
# ============================================================================


@pytest.mark.asyncio
async def test_fefo_mutations_block_non_isolated_and_public_schemas(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que las mutaciones físicas (dry_run=False) sobre esquemas reales
    o 'public' sean rechazadas con HTTP 400 e ISOLATED_SCHEMA_REQUIRED.
    """
    manage_headers = _make_token_headers(["platform_admin.sandbox.manage"])
    forbidden_schemas = ["public", "tenant_cliente_real_acme", "tenant_produccion_cava", "tenant_master"]

    for schema in forbidden_schemas:
        # /fefo/shift
        res_shift = await async_client.post(
            "/api/v1/platform-admin/sandbox/fefo/shift",
            headers=manage_headers,
            json={"tenantSchema": schema, "offsetDays": 5, "dryRun": False},
        )
        assert res_shift.status_code == 400
        assert res_shift.json()["error_code"] == "ISOLATED_SCHEMA_REQUIRED"

        # /fefo/sync-today
        res_sync = await async_client.post(
            "/api/v1/platform-admin/sandbox/fefo/sync-today",
            headers=manage_headers,
            json={"tenantSchema": schema, "dryRun": False},
        )
        assert res_sync.status_code == 400
        assert res_sync.json()["error_code"] == "ISOLATED_SCHEMA_REQUIRED"


@pytest.mark.asyncio
async def test_fefo_mutations_allowed_on_whitelisted_isolated_schemas(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que esquemas en whitelist (tenant_qa_lab, tenant_sandbox_fefo, tenant_qa_*) sean autorizados."""
    manage_headers = _make_token_headers(["platform_admin.sandbox.manage"])
    allowed_schemas = ["tenant_qa_lab", "tenant_sandbox_fefo", "tenant_qa_automation", "tenant_sandbox_unit"]

    for schema in allowed_schemas:
        res = await async_client.post(
            "/api/v1/platform-admin/sandbox/fefo/shift",
            headers=manage_headers,
            json={"tenantSchema": schema, "offsetDays": 3, "dryRun": False},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "applied"


# ============================================================================
# 3. PRUEBAS GUARDRAIL DE PRODUCCIÓN Y STAGING (V5 - V6)
# ============================================================================


@pytest.mark.asyncio
async def test_fefo_production_mutation_strictly_forbidden(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que en 'production', mutaciones físicas (dryRun=False) sean bloqueadas con 403."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    manage_headers = _make_token_headers(["platform_admin.sandbox.manage"])

    # 1. /fefo/shift
    res_shift = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=manage_headers,
        json={"tenantSchema": "tenant_qa_lab", "offsetDays": 5, "dryRun": False},
    )
    assert res_shift.status_code == 403
    assert res_shift.json()["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"

    # 2. /fefo/sync-today
    res_sync = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=manage_headers,
        json={"tenantSchema": "tenant_qa_lab", "dryRun": False},
    )
    assert res_sync.status_code == 403
    assert res_sync.json()["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"


@pytest.mark.asyncio
async def test_fefo_staging_mutation_requires_confirmation(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que en 'staging', mutaciones sin confirmación fallen con 400 y con confirmación pasen."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    manage_headers = _make_token_headers(["platform_admin.sandbox.manage"])

    # 1. Sin confirmación -> 400
    res_unconf = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=manage_headers,
        json={"tenantSchema": "tenant_qa_lab", "offsetDays": 5, "dryRun": False, "confirmStagingAction": False},
    )
    assert res_unconf.status_code == 400
    assert res_unconf.json()["error_code"] == "STAGING_CONFIRMATION_REQUIRED"

    # 2. Con confirmación en payload -> 200
    res_conf_payload = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=manage_headers,
        json={"tenantSchema": "tenant_qa_lab", "offsetDays": 5, "dryRun": False, "confirmStagingAction": True},
    )
    assert res_conf_payload.status_code == 200

    # 3. Con confirmación en cabecera -> 200
    res_conf_header = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers={**manage_headers, "X-Sandbox-Confirm-Staging": "true"},
        json={"tenantSchema": "tenant_qa_lab", "offsetDays": 5, "dryRun": False},
    )
    assert res_conf_header.status_code == 200


# ============================================================================
# 4. BOUNDS CHECKING: OFFSET [-30, +60] DÍAS & ANTI-OVERFLOW (V7)
# ============================================================================


@pytest.mark.asyncio
async def test_fefo_offset_bounds_checking_limits(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que el desplazamiento temporal esté estrictamente acotado en [-30, +60] días:
    - offsetDays < -30 (ej. -31, -100) -> HTTP 422
    - offsetDays > 60 (ej. 61, 999999999) -> HTTP 422
    - Fronteras válidas: -30, 0, 60 -> HTTP 200
    """
    access_headers = _make_token_headers(["platform_admin.sandbox.access"])

    # 1. Fuera de rango inferior
    for bad_low in [-31, -100, -1000]:
        res = await async_client.post(
            "/api/v1/platform-admin/sandbox/fefo/simulate",
            headers=access_headers,
            json={"tenantSchema": "tenant_qa_lab", "offsetDays": bad_low},
        )
        assert res.status_code == 422, f"offsetDays={bad_low} debió ser rechazado con 422"

    # 2. Fuera de rango superior (prevención de OverflowError DoS)
    for bad_high in [61, 100, 999999999]:
        res = await async_client.post(
            "/api/v1/platform-admin/sandbox/fefo/simulate",
            headers=access_headers,
            json={"tenantSchema": "tenant_qa_lab", "offsetDays": bad_high},
        )
        assert res.status_code == 422, f"offsetDays={bad_high} debió ser rechazado con 422"

    # 3. Fronteras válidas exactas
    for valid_offset in [-30, 0, 60]:
        res = await async_client.post(
            "/api/v1/platform-admin/sandbox/fefo/simulate",
            headers=access_headers,
            json={"tenantSchema": "tenant_qa_lab", "offsetDays": valid_offset},
        )
        assert res.status_code == 200, f"offsetDays={valid_offset} debió ser aceptado con 200"


# ============================================================================
# 5. INTEGRIDAD DE ESQUEMAS PYDANTIC V2 EXTRA='FORBID' (V8)
# ============================================================================


@pytest.mark.asyncio
async def test_fefo_extra_attributes_forbidden(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica el rechazo HTTP 422 ante inyección de atributos no declarados en el modelo."""
    access_headers = _make_token_headers(["platform_admin.sandbox.access"])
    res = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=access_headers,
        json={"tenantSchema": "tenant_qa_lab", "offsetDays": 0, "maliciousInjection": "true"},
    )
    assert res.status_code == 422
