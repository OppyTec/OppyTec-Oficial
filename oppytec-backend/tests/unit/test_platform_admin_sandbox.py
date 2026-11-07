"""
oppytec-backend/tests/unit/test_platform_admin_sandbox.py
Pruebas unitarias e integración en memoria para la Consola "Lab & QA Sandbox" de Platform Admin:
1. GET  /api/v1/platform-admin/sandbox/status
2. GET  /api/v1/platform-admin/sandbox/mock-data/history
3. POST /api/v1/platform-admin/sandbox/mock-data/generate (dryRun=True & dryRun=False)
4. GET  /api/v1/platform-admin/sandbox/playwright/status/{run_id}
5. POST /api/v1/platform-admin/sandbox/playwright/run
6. POST /api/v1/platform-admin/sandbox/fefo/simulate (No destructivo)
7. POST /api/v1/platform-admin/sandbox/fefo/shift
8. Cobertura RBAC Dual de 3 niveles:
   - Bloqueo 403 para tokens con scope de inquilino (GLOBAL_STAFF_REQUIRED).
   - Bloqueo 403 para tokens globales sin permisos correspondientes (access vs manage).
   - Autorización para usuarios con platform_admin.sandbox.access y platform_admin.sandbox.manage.
   - Autorización universal para superusuarios god.
"""
from __future__ import annotations

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
    hierarchy_rank: int = 10,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado para el plano global."""
    token = create_access_token(
        user_id=user_id,
        is_global_staff=is_global_staff,
        is_superuser_god=is_superuser_god,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset_sandbox_state() -> None:
    """Aísla el estado en memoria antes de cada prueba unitaria."""
    clear_revoked_sessions()
    service = get_sandbox_service()
    service.reset()


# ============================================================================
# 1. PRUEBAS DE ESTADO DEL SANDBOX
# ============================================================================


@pytest.mark.asyncio
async def test_get_sandbox_status_success(async_client: httpx.AsyncClient) -> None:
    """Verifica que un usuario con platform_admin.sandbox.access obtenga el estado del sandbox."""
    headers = _make_admin_headers(["platform_admin.sandbox.access"])
    response = await async_client.get(
        "/api/v1/platform-admin/sandbox/status", headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "active", "idle")
    assert "mock_data_generator" in data["availableTools"]
    assert "playwright_e2e_runner" in data["availableTools"]
    assert "fefo_time_warp" in data["availableTools"]
    assert "tenant_genesis" in data["isolatedTenantSchemas"]
    assert "timestamp" in data


# ============================================================================
# 2. PRUEBAS DE HISTORIAL Y GENERACIÓN DE MOCK DATA
# ============================================================================


@pytest.mark.asyncio
async def test_get_mock_data_history_success(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica la consulta del historial de mock data con permiso de lectura."""
    headers = _make_admin_headers(["platform_admin.sandbox.access"])
    response = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/history", headers=headers
    )

    assert response.status_code == 200
    history = response.json()
    assert isinstance(history, list)
    assert len(history) >= 2
    assert "tenantSchema" in history[0]
    assert "recordsSummary" in history[0]
    assert "status" in history[0]


@pytest.mark.asyncio
async def test_generate_mock_data_dry_run(async_client: httpx.AsyncClient) -> None:
    """Verifica la generación preliminar no destructiva (dryRun=True)."""
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "categories": ["catalog", "inventory_fefo"],
        "volume": "medium",
        "dryRun": True,
        "injectFefoAnomalies": False,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["dryRun"] is True
    assert data["step"] == "completed"
    assert data["percent"] == 100
    assert "catalog" in data["recordsCreated"]
    assert "inventory_fefo" in data["recordsCreated"]
    assert data["recordsCreated"]["catalog"] > 0


@pytest.mark.asyncio
async def test_generate_mock_data_real_injection_persists_in_history(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que una ejecución real (dryRun=False) guarde el registro en el historial."""
    manage_headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    read_headers = _make_admin_headers(["platform_admin.sandbox.access"])

    payload = {
        "tenantSchema": "tenant_integration_test",
        "categories": ["all"],
        "volume": "small",
        "dryRun": False,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=manage_headers,
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["dryRun"] is False
    assert response.json()["step"] == "injected_into_schema"

    # Verificar que aparece en el historial
    hist_res = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/history", headers=read_headers
    )
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert any(h["tenantSchema"] == "tenant_integration_test" for h in history)


# ============================================================================
# 3. PRUEBAS DE PLAYWRIGHT RUNNER & OBSERVABILIDAD
# ============================================================================


@pytest.mark.asyncio
async def test_get_playwright_run_status(async_client: httpx.AsyncClient) -> None:
    """Verifica la consulta de estado de una corrida Playwright."""
    headers = _make_admin_headers(["platform_admin.sandbox.access"])
    response = await async_client.get(
        "/api/v1/platform-admin/sandbox/playwright/status/run_smoke_001",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["runId"] == "run_smoke_001"
    assert data["status"] == "completed"
    assert data["totalTests"] >= 1
    assert data["passedTests"] >= 1
    assert len(data["testResults"]) >= 1
    assert len(data["rawLogs"]) >= 1


@pytest.mark.asyncio
async def test_trigger_playwright_run(async_client: httpx.AsyncClient) -> None:
    """Verifica el disparo de una suite Playwright con permiso manage."""
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "suiteId": "auth_rbac",
        "browser": "chromium",
        "headless": True,
        "workers": 2,
        "targetTenantSchema": "tenant_qa_lab",
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 202
    data = response.json()
    assert "runId" in data
    assert data["suiteId"] == "auth_rbac"
    assert data["status"] in ("queued", "running", "completed")


# ============================================================================
# 4. PRUEBAS DE SIMULADOR FEFO TIME-WARP
# ============================================================================


@pytest.mark.asyncio
async def test_simulate_fefo_warp_non_destructive(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica el cálculo no destructivo de impacto FEFO con offset de días."""
    headers = _make_admin_headers(["platform_admin.sandbox.access"])
    payload = {
        "mode": "relative_offset",
        "offsetDays": 15,
        "tenantSchema": "tenant_qa_lab",
        "dryRun": True,
        "generateSpoilageEvents": True,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert "simulationId" in data
    assert data["totalBatchesEvaluated"] > 0
    assert data["totalSpoilageRiskAmount"] >= 0.0
    assert data["currency"] == "CLP"
    assert len(data["batches"]) == data["totalBatchesEvaluated"]

    # Verificar clasificación de lotes
    for batch in data["batches"]:
        assert batch["status"] in ("optimal", "warning", "critical", "expired")
        assert "estimatedLossAmount" in batch


@pytest.mark.asyncio
async def test_apply_fefo_shift_safeguards(async_client: httpx.AsyncClient) -> None:
    """Verifica la aplicación de corrimiento temporal con salvaguarda dryRun."""
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])

    # 1. Preview Only cuando dryRun=True
    preview_res = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers,
        json={"tenantSchema": "tenant_qa_lab", "offsetDays": 30, "dryRun": True},
    )
    assert preview_res.status_code == 200
    assert preview_res.json()["status"] == "preview_only"
    assert preview_res.json()["shiftedBatchesCount"] == 0

    # 2. Aplicación efectiva cuando dryRun=False
    shift_res = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers,
        json={"tenantSchema": "tenant_qa_lab", "offsetDays": 30, "dryRun": False},
    )
    assert shift_res.status_code == 200
    assert shift_res.json()["status"] == "applied"
    assert shift_res.json()["shiftedBatchesCount"] > 0


# ============================================================================
# 5. PRUEBAS DE SEGURIDAD RBAC DUAL (3 NIVELES) Y ANTI-IDOR
# ============================================================================


@pytest.mark.asyncio
async def test_rbac_denial_for_unauthenticated_request(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que peticiones sin token sean rechazadas con HTTP 401."""
    endpoints = [
        ("GET", "/api/v1/platform-admin/sandbox/status"),
        ("GET", "/api/v1/platform-admin/sandbox/mock-data/history"),
        ("POST", "/api/v1/platform-admin/sandbox/mock-data/generate"),
        ("GET", "/api/v1/platform-admin/sandbox/playwright/status/run_smoke_001"),
        ("POST", "/api/v1/platform-admin/sandbox/fefo/simulate"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = await async_client.get(path)
        else:
            res = await async_client.post(path, json={"tenantSchema": "t1"})
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_rbac_denial_for_tenant_scoped_tokens(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que un token con scope de inquilino (is_global_staff=False)
    sea bloqueado inmediatamente con HTTP 403 (GLOBAL_STAFF_REQUIRED).
    """
    tenant_token = create_access_token(
        user_id=101,
        holding_id="holding_client_01",
        tenant_id="tenant_client_01",
        is_global_staff=False,
        is_superuser_god=False,
        role_grants=["inventory.stock.read", "platform_admin.sandbox.access"],
    )
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

    # Acceso a lectura
    r1 = await async_client.get(
        "/api/v1/platform-admin/sandbox/status", headers=tenant_headers
    )
    assert r1.status_code == 403
    assert "GLOBAL_STAFF_REQUIRED" in r1.text or "global_staff_required" in r1.text

    # Acceso a mutación
    r2 = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=tenant_headers,
        json={"tenantSchema": "tenant_client_01", "dryRun": True},
    )
    assert r2.status_code == 403


@pytest.mark.asyncio
async def test_rbac_read_only_token_cannot_execute_manage_actions(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que un token con permiso de solo lectura platform_admin.sandbox.access
    no pueda ejecutar acciones que requieren platform_admin.sandbox.manage.
    """
    readonly_headers = _make_admin_headers(["platform_admin.sandbox.access"])

    # 1. Intento de generar mock data
    res_mock = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=readonly_headers,
        json={"tenantSchema": "tenant_qa", "dryRun": True},
    )
    assert res_mock.status_code == 403

    # 2. Intento de disparar corrida Playwright
    res_pw = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=readonly_headers,
        json={"suiteId": "smoke", "targetTenantSchema": "tenant_qa"},
    )
    assert res_pw.status_code == 403

    # 3. Intento de aplicar corrimiento temporal FEFO
    res_fefo = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=readonly_headers,
        json={"tenantSchema": "tenant_qa", "offsetDays": 10, "dryRun": False},
    )
    assert res_fefo.status_code == 403


@pytest.mark.asyncio
async def test_god_superuser_has_access_to_all_sandbox_endpoints(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que el superusuario god (is_superuser_god=True) tenga acceso completo a todos los endpoints."""
    god_headers = _make_admin_headers(
        permissions=[],
        is_superuser_god=True,
        hierarchy_rank=0,
    )

    r_status = await async_client.get(
        "/api/v1/platform-admin/sandbox/status", headers=god_headers
    )
    assert r_status.status_code == 200

    r_mock = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=god_headers,
        json={"tenantSchema": "tenant_god", "volume": "small", "dryRun": True},
    )
    assert r_mock.status_code == 200


# ============================================================================
# 5. PRUEBAS DE GOBERNANZA IA Y FINOPS EN SANDBOX (ETAPA 3)
# ============================================================================


@pytest.mark.asyncio
async def test_playwright_run_finops_tokens_suite(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que la suite de pruebas 'finops_tokens' audite:
    1. Aislamiento multi-tenant de bolsas de créditos IA.
    2. Bitácora append-only obligatoria en public.llm_request_logs.
    3. Cero llamadas no metreadas o descontroladas a LLMs externos.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "suiteId": "finops_tokens",
        "browser": "chromium",
        "headless": True,
        "targetTenantSchema": "tenant_qa_lab",
        "workers": 2,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 202
    data = response.json()
    assert data["suiteId"] == "finops_tokens"
    assert data["status"] == "completed"
    assert data["passedTests"] == 1
    assert data["failedTests"] == 0

    # Verificación de pasos de prueba FinOps
    test_result = data["testResults"][0]
    step_titles = [s["title"] for s in test_result["steps"]]
    assert any("credit quota isolation" in st.lower() for st in step_titles)
    assert any("llm_request_logs" in st.lower() for st in step_titles)
    assert any("zero unmetered" in st.lower() for st in step_titles)

    # Verificación de logs de gobernanza
    logs_joined = " ".join(data["rawLogs"])
    assert "public.llm_request_logs" in logs_joined
    assert "ZERO" in logs_joined or "zero" in logs_joined


@pytest.mark.asyncio
async def test_generate_mock_data_finops_credits_category(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que la generación de mock data soporte la categoría 'finops_credits'
    para sembrar bolsas de crédito aisladas por inquilino.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_genesis",
        "categories": ["finops_credits"],
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
    assert data["status"] == "success"
    assert "finops_credits" in data["recordsCreated"]
    assert data["recordsCreated"]["finops_credits"] > 0


# ============================================================================
# 6. PRUEBAS DE PRESETS GASTRONÓMICOS Y FACTORY RESET
# ============================================================================


@pytest.mark.asyncio
async def test_get_gastronomic_presets_catalog(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que se listen los 4 presets gastronómicos canónicos con sus metadatos."""
    headers = _make_admin_headers(["platform_admin.sandbox.access"])
    response = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/presets",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    presets = data["presets"]
    preset_ids = [p["id"] for p in presets]
    assert "fast-food-pollo-king" in preset_ids
    assert "carnes-angus-cava" in preset_ids
    assert "hotel-desayuno-buffet" in preset_ids
    assert "clean-slate" in preset_ids

    # Verificar estructura tipada canónica en el preset Pollo King
    pollo_preset = next(p for p in presets if p["id"] == "fast-food-pollo-king")
    assert pollo_preset["code"] == "FAST-FOOD-POLLO-KING"
    assert "Pollo King" in pollo_preset["title"]
    assert pollo_preset["category"] == "fast_food"
    assert pollo_preset["iconName"] == "Flame"
    assert pollo_preset["totalSkus"] == 24
    assert pollo_preset["totalBatches"] == 48
    assert pollo_preset["totalRecipes"] == 12
    assert pollo_preset["estimatedStockValueClp"] > 0


@pytest.mark.asyncio
async def test_get_gastronomic_preset_detail_and_not_found(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica consulta de detalle por ID y manejo de error 404 para preset inexistente."""
    headers = _make_admin_headers(["platform_admin.sandbox.access"])

    # 1. Preset existente
    res = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/presets/carnes-angus-cava",
        headers=headers,
    )
    assert res.status_code == 200
    preset = res.json()
    assert preset["id"] == "carnes-angus-cava"
    assert preset["category"] == "steakhouse"
    assert preset["totalSkus"] == 30

    # 2. Preset no existente -> 404
    res_404 = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/presets/preset-inexistente",
        headers=headers,
    )
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_factory_reset_mock_data_success(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que el Factory Reset:
    1. Trunque colecciones del esquema y limpie registros previos en historial.
    2. Re-siembre los datos correspondientes al preset seleccionado.
    3. Registre la operación en la auditoría del sandbox.
    """
    manage_headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    read_headers = _make_admin_headers(["platform_admin.sandbox.access"])

    # 1. Inyectar datos previos en el esquema para verificar purga
    await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=manage_headers,
        json={"tenantSchema": "tenant_qa_lab", "volume": "small", "dryRun": False},
    )

    # 2. Ejecutar Factory Reset
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "targetPresetId": "carnes-angus-cava",
        "confirmReset": True,
    }
    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=manage_headers,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tenantSchema"] == "tenant_qa_lab"
    assert data["presetRestored"] == "carnes-angus-cava"
    assert "kardex_movements" in data["tablesTruncated"]
    assert "fefo_batches" in data["tablesTruncated"]
    assert data["recordsReseeded"]["products"] == 30
    assert data["recordsReseeded"]["fefo_batches"] == 60
    assert data["recordsReseeded"]["recipes"] == 15
    assert data["durationMs"] > 0

    # 3. Verificar que el historial del esquema contenga únicamente la entrada del reset
    hist_res = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/history",
        headers=read_headers,
    )
    assert hist_res.status_code == 200
    tenant_history = [
        h for h in hist_res.json() if h["tenantSchema"] == "tenant_qa_lab"
    ]
    assert len(tenant_history) == 1
    assert tenant_history[0]["recordsSummary"]["products"] == 30


@pytest.mark.asyncio
async def test_factory_reset_clean_slate_preset(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que el Factory Reset con el preset 'clean-slate' restablezca el entorno virgen (0 registros)."""
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_sandbox_fefo",
        "targetPresetId": "clean-slate",
        "confirmReset": True,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["presetRestored"] == "clean-slate"
    assert data["recordsReseeded"]["products"] == 0
    assert data["recordsReseeded"]["fefo_batches"] == 0
    assert data["recordsReseeded"]["recipes"] == 0


@pytest.mark.asyncio
async def test_factory_reset_requires_confirm_reset(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que omitir o enviar confirmReset=False sea rechazado con HTTP 400."""
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "targetPresetId": "fast-food-pollo-king",
        "confirmReset": False,
    }

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "RESET_CONFIRMATION_REQUIRED"


@pytest.mark.asyncio
async def test_factory_reset_guardrails_environment_protection(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica los guardrails Fail-Fast del reset en 'production' y 'staging'."""
    settings = get_settings()
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "targetPresetId": "fast-food-pollo-king",
        "confirmReset": True,
    }

    # 1. En Producción: Bloqueo incondicional con HTTP 403
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res_prod = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json=payload,
    )
    assert res_prod.status_code == 403
    assert res_prod.json()["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"

    # 2. En Staging: Requiere confirmación de staging -> 400 sin confirmación
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    res_stag_unconf = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json=payload,
    )
    assert res_stag_unconf.status_code == 400
    assert res_stag_unconf.json()["error_code"] == "STAGING_CONFIRMATION_REQUIRED"

    # Con cabecera de staging -> 200 OK
    res_stag_conf = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers={**headers, "X-Sandbox-Confirm-Staging": "true"},
        json=payload,
    )
    assert res_stag_conf.status_code == 200

    # 3. En esquema no autorizado (ej. 'public') -> 400 ISOLATED_SCHEMA_REQUIRED
    monkeypatch.setattr(settings, "ENVIRONMENT", "lab")
    res_non_iso = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json={**payload, "tenantSchema": "public"},
    )
    assert res_non_iso.status_code == 400
    assert res_non_iso.json()["error_code"] == "ISOLATED_SCHEMA_REQUIRED"


@pytest.mark.asyncio
async def test_presets_and_reset_rbac_boundaries(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica el cumplimiento de RBAC dual de 3 niveles para presets y factory reset."""
    # 1. Sin autenticación -> 401
    r_unauth_presets = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/presets"
    )
    assert r_unauth_presets.status_code == 401

    r_unauth_reset = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        json={"tenantSchema": "tenant_qa_lab", "targetPresetId": "clean-slate"},
    )
    assert r_unauth_reset.status_code == 401

    # 2. Token de inquilino (tenant-scoped) -> 403 GLOBAL_STAFF_REQUIRED (Anti-IDOR)
    tenant_token = create_access_token(
        user_id=888,
        is_global_staff=False,
        role_grants=["platform_admin.sandbox.access", "platform_admin.sandbox.manage"],
    )
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}
    r_tenant = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/presets",
        headers=tenant_headers,
    )
    assert r_tenant.status_code == 403
    assert "GLOBAL_STAFF_REQUIRED" in r_tenant.text or "global_staff_required" in r_tenant.text

    r_tenant_preset_id = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/presets/carnes-angus-cava",
        headers=tenant_headers,
    )
    assert r_tenant_preset_id.status_code == 403
    assert "GLOBAL_STAFF_REQUIRED" in r_tenant_preset_id.text or "global_staff_required" in r_tenant_preset_id.text

    r_tenant_reset = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=tenant_headers,
        json={"tenantSchema": "tenant_qa_lab", "targetPresetId": "clean-slate", "confirmReset": True},
    )
    assert r_tenant_reset.status_code == 403
    assert "GLOBAL_STAFF_REQUIRED" in r_tenant_reset.text or "global_staff_required" in r_tenant_reset.text

    # 3. Permiso solo lectura (platform_admin.sandbox.access):
    # Puede consultar presets (200), pero NO ejecutar reset (403)
    read_headers = _make_admin_headers(["platform_admin.sandbox.access"])
    r_read_presets = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/presets",
        headers=read_headers,
    )
    assert r_read_presets.status_code == 200

    r_read_reset = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=read_headers,
        json={"tenantSchema": "tenant_qa_lab", "targetPresetId": "clean-slate", "confirmReset": True},
    )
    assert r_read_reset.status_code == 403


# ============================================================================
# 11. GOBERNANZA DE IA Y FINOPS: PRESERVACIÓN DE LLM_REQUEST_LOGS Y CUOTAS
# ============================================================================


@pytest.mark.asyncio
async def test_factory_reset_preserves_public_llm_request_logs(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Certificación Agente 06:
    Verifica que el Factory Reset NO purgue la tabla append-only `public.llm_request_logs`
    ni tablas de auditoría de IA, preservando la trazabilidad regulatoria inmutable.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
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
    assert response.status_code == 200
    data = response.json()

    # Validamos que ninguna tabla de IA / FinOps en public sea truncada
    truncated = data["tablesTruncated"]
    assert "public.llm_request_logs" not in truncated
    assert "llm_request_logs" not in truncated
    assert "jev_request_logs" not in truncated
    assert "oppyfy_prompt_audit_logs" not in truncated
    assert "oppyfy_rbac_audit_logs" not in truncated


@pytest.mark.asyncio
async def test_playwright_finops_tokens_governance_suite(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Certificación Agente 06:
    Verifica que la suite de orquestación Playwright 'finops_tokens' audite y certifique
    el aislamiento estricto de esquemas y la bitácora append-only de tokens.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {"suiteId": "finops_tokens"}

    response = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 202
    data = response.json()
    assert data["suiteId"] == "finops_tokens"
    assert data["status"] == "completed"
    assert data["totalTests"] == 1
    assert data["passedTests"] == 1
    assert data["failedTests"] == 0

    test_case = data["testResults"][0]
    assert test_case["suite"] == "finops_tokens"
    assert test_case["status"] == "passed"
    step_titles = [s["title"] for s in test_case["steps"]]
    assert any("llm_request_logs" in t for t in step_titles)
    assert any("credit quota" in t for t in step_titles)


@pytest.mark.asyncio
async def test_playwright_finops_domain_and_zero_credit_leak_guardrails(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Certificación Agente 06 (FinOps & Token Budget Guardrails):
    1. Encola corrida del dominio 'finops' (5 pruebas canónicas) sobre esquema aislado autorizado ('tenant_qa_lab').
    2. Bloquea de forma inmediata (HTTP 400 ISOLATED_SCHEMA_REQUIRED) cualquier intento de ejecución
       sobre esquemas no autorizados o de producción (ej. 'tenant_prod_cava_angus' o 'public').
    3. Verifica que la corrida en modo Sandbox respete los esquemas aislados sin mutar balances reales.
    4. Conecta al streaming SSE para comprobar emisión de pasos con nivel 'assert' y trazas de auditoría.
    """
    manage_headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    access_headers = _make_admin_headers(["platform_admin.sandbox.access"])

    # 1. Ejecución legítima sobre esquema aislado 'tenant_qa_lab'
    payload_valid = {
        "scope": "domain",
        "targetId": "finops",
        "targetTenantSchema": "tenant_qa_lab",
        "headless": True,
        "slowMoMs": 0,
        "browser": "chromium",
    }
    res_valid = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=manage_headers,
        json=payload_valid,
    )
    assert res_valid.status_code == 202
    data_valid = res_valid.json()
    assert data_valid["runId"].startswith("pw_run_")
    assert data_valid["status"] == "queued"
    assert data_valid["testsQueued"] == 5
    assert "finops" in data_valid["message"]

    # 2. Bloqueo estricto anti-IDOR hacia esquemas no autorizados / clientes reales
    payload_invalid_prod = {
        "scope": "domain",
        "targetId": "finops",
        "targetTenantSchema": "tenant_prod_cava_angus",
    }
    res_invalid_prod = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=manage_headers,
        json=payload_invalid_prod,
    )
    assert res_invalid_prod.status_code == 400
    assert res_invalid_prod.json()["error_code"] == "ISOLATED_SCHEMA_REQUIRED"

    # Esquema público global no autorizado para pruebas
    payload_invalid_public = {
        "scope": "test",
        "targetId": "pw_finops_01_token_discount",
        "targetTenantSchema": "public",
    }
    res_invalid_public = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=manage_headers,
        json=payload_invalid_public,
    )
    assert res_invalid_public.status_code == 400
    assert res_invalid_public.json()["error_code"] == "ISOLATED_SCHEMA_REQUIRED"

    # 3. Streaming SSE para la corrida legítima de finops
    stream_res = await async_client.get(
        f"/api/v1/platform-admin/sandbox/playwright/stream/{data_valid['runId']}",
        headers=access_headers,
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers.get("content-type", "")
    assert "event: step" in stream_res.text
    assert "event: completed" in stream_res.text
    assert "tenant_qa_lab" in stream_res.text


# ============================================================================
# 6. SUB-PLAN 3 (ETAPA 2): CONSOLA DINÁMICA DE TESTS PLAYWRIGHT
# ============================================================================


@pytest.mark.asyncio
async def test_get_playwright_catalog_success(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica la consulta del catálogo dinámico de tests Playwright (GET /catalog):
    1. Agrupación canónica en los 7 dominios oficiales.
    2. Resumen dinámico: total=38, ready=2, inProgress=2, planned=34, coverage=5.3%.
    3. Invariantes matemáticas: total == ready + inProgress + planned.
    4. Presencia de casos canónicos por estado de madurez.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.access"])
    response = await async_client.get(
        "/api/v1/platform-admin/sandbox/playwright/catalog",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "domains" in data

    summary = data["summary"]
    assert summary["total"] == 38
    assert summary["ready"] == 2
    assert summary["inProgress"] == 2
    assert summary["planned"] == 34
    assert summary["coveragePercentage"] == 5.3
    # Invariante matemática
    assert summary["total"] == summary["ready"] + summary["inProgress"] + summary["planned"]

    domains = data["domains"]
    assert len(domains) == 7
    domain_map = {d["domain"]: d for d in domains}
    expected_domains = {
        "tenancy",
        "auth_rbac",
        "inventory",
        "recipes",
        "procurement",
        "finops",
        "pos",
    }
    assert set(domain_map.keys()) == expected_domains

    # Aserción de casos específicos requeridos
    all_tests = [t for d in domains for t in d["tests"]]
    tests_by_id = {t["id"]: t for t in all_tests}

    # Pruebas ready
    assert tests_by_id["pw_tenancy_01_holding_creation"]["status"] == "ready"
    assert tests_by_id["pw_tenancy_01_holding_creation"]["lastRun"] is not None
    assert tests_by_id["pw_auth_01_login_rbac_guard"]["status"] == "ready"

    # Pruebas in_progress
    assert tests_by_id["pw_inventory_01_fefo_alerts"]["status"] == "in_progress"
    assert tests_by_id["pw_finops_01_token_discount"]["status"] == "in_progress"

    # Pruebas planned
    assert tests_by_id["pw_recipes_01_costing_ppp"]["status"] == "planned"
    assert tests_by_id["pw_procurement_01_dte_invoice"]["status"] == "planned"
    assert tests_by_id["pw_pos_01_cashier_shift"]["status"] == "planned"


@pytest.mark.asyncio
async def test_playwright_catalog_rbac_denials(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica bloqueos 401 y 403 en GET /catalog para credenciales inválidas o sin permisos."""
    catalog_url = "/api/v1/platform-admin/sandbox/playwright/catalog"

    # 1. Sin autenticación -> 401
    res_unauth = await async_client.get(catalog_url)
    assert res_unauth.status_code == 401

    # 2. Token de inquilino (no global staff) -> 403 GLOBAL_STAFF_REQUIRED
    tenant_headers = _make_admin_headers(
        permissions=["platform_admin.sandbox.access"],
        is_global_staff=False,
    )
    res_tenant = await async_client.get(catalog_url, headers=tenant_headers)
    assert res_tenant.status_code == 403
    assert res_tenant.json()["error_code"] == "GLOBAL_STAFF_REQUIRED"

    # 3. Token global sin permiso platform_admin.sandbox.access -> 403
    no_perm_headers = _make_admin_headers(permissions=["inventory.items.read"])
    res_forbidden = await async_client.get(catalog_url, headers=no_perm_headers)
    assert res_forbidden.status_code == 403
    assert res_forbidden.json()["error_code"] in (
        "GLOBAL_PERMISSION_DENIED",
        "MODULE_NOT_ENABLED_IN_PLAN",
        "NO_EXPLICIT_GRANT",
    )


@pytest.mark.asyncio
async def test_trigger_playwright_run_scopes(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica el endpoint POST /playwright/run con alcance granular:
    1. scope='domain' encolando las 6 pruebas de inventory.
    2. scope='test' encolando 1 prueba específica.
    3. scope='all' encolando la suite completa de 38 pruebas.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])

    # 1. Dominio inventory
    payload_domain = {
        "scope": "domain",
        "targetId": "inventory",
        "headless": True,
        "slowMoMs": 0,
        "browser": "chromium",
        "targetTenantSchema": "tenant_sandbox_fefo",
    }
    res_dom = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json=payload_domain,
    )
    assert res_dom.status_code == 202
    data_dom = res_dom.json()
    assert data_dom["runId"].startswith("pw_run_")
    assert data_dom["status"] == "queued"
    assert data_dom["testsQueued"] == 6
    assert "inventory" in data_dom["message"]

    # 2. Test individual
    payload_test = {
        "scope": "test",
        "targetId": "pw_tenancy_01_holding_creation",
        "headless": False,
        "slowMoMs": 100,
    }
    res_test = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json=payload_test,
    )
    assert res_test.status_code == 202
    data_test = res_test.json()
    assert data_test["testsQueued"] == 1
    assert "pw_tenancy_01_holding_creation" in data_test["message"]

    # 3. Scope all
    payload_all = {"scope": "all"}
    res_all = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json=payload_all,
    )
    assert res_all.status_code == 202
    assert res_all.json()["testsQueued"] == 38


@pytest.mark.asyncio
async def test_trigger_playwright_run_production_guardrail(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que en entorno 'production' se requiera confirmación explícita para corridas."""
    settings = get_settings()
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    payload = {
        "scope": "domain",
        "targetId": "pos",
        "confirmProductionRun": False,
    }

    # 1. Sin confirmación -> 400 Bad Request
    res_unconf = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json=payload,
    )
    assert res_unconf.status_code == 400
    assert res_unconf.json()["error_code"] == "PRODUCTION_CONFIRMATION_REQUIRED"

    # 2. Con confirmación en payload -> 202 Accepted
    res_conf_payload = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=headers,
        json={**payload, "confirmProductionRun": True},
    )
    assert res_conf_payload.status_code == 202

    # 3. Con cabecera X-Sandbox-Confirm-Production: true -> 202 Accepted
    res_conf_header = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers={**headers, "X-Sandbox-Confirm-Production": "true"},
        json=payload,
    )
    assert res_conf_header.status_code == 202


@pytest.mark.asyncio
async def test_stream_playwright_run_events_sse(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica el streaming SSE (Server-Sent Events) en tiempo real:
    GET /api/v1/platform-admin/sandbox/playwright/stream/{run_id}
    1. Cabecera text/event-stream.
    2. Emisión secuencial de eventos 'step' y evento terminal 'completed'.
    3. Presencia de asertos, métricas de duración y capturas screenshot.
    """
    manage_headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    access_headers = _make_admin_headers(["platform_admin.sandbox.access"])

    # 1. Encolar corrida
    run_res = await async_client.post(
        "/api/v1/platform-admin/sandbox/playwright/run",
        headers=manage_headers,
        json={"scope": "domain", "targetId": "tenancy", "slowMoMs": 0},
    )
    assert run_res.status_code == 202
    run_id = run_res.json()["runId"]

    # 2. Conectar al stream SSE
    stream_res = await async_client.get(
        f"/api/v1/platform-admin/sandbox/playwright/stream/{run_id}",
        headers=access_headers,
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers.get("content-type", "")

    stream_text = stream_res.text
    assert "event: step" in stream_text
    assert "event: completed" in stream_text

    # Parsear bloques SSE
    lines = stream_text.strip().split("\n")
    events_data: list[dict[str, object]] = []
    current_event_type: str | None = None

    import json
    for line in lines:
        if line.startswith("event:"):
            current_event_type = line.replace("event:", "").strip()
        elif line.startswith("data:"):
            raw_data = line.replace("data:", "").strip()
            parsed = json.loads(raw_data)
            parsed["_event"] = current_event_type
            events_data.append(parsed)

    assert len(events_data) >= 5
    step_events = [e for e in events_data if e.get("_event") == "step"]
    completed_events = [e for e in events_data if e.get("_event") == "completed"]

    assert len(step_events) >= 4
    assert len(completed_events) == 1

    # Validar campos de pasos
    for s in step_events:
        assert "stepIndex" in s
        assert "testId" in s
        assert "message" in s
        assert "level" in s
        assert "timestamp" in s
        assert "durationMs" in s

    # Validar que al menos un paso sea assert y tenga screenshotUrl
    assert any(s.get("level") == "assert" and s.get("screenshotUrl") is not None for s in step_events)

    # Validar evento terminal
    term = completed_events[0]
    assert term["status"] == "completed"
    assert term["runId"] == run_id
    assert int(term["totalTests"]) > 0


@pytest.mark.asyncio
async def test_stream_playwright_run_rbac_denials(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que el stream SSE requiera platform_admin.sandbox.access de plano global."""
    stream_url = "/api/v1/platform-admin/sandbox/playwright/stream/pw_run_test_rbac"

    # 1. Sin autenticación -> 401
    res_unauth = await async_client.get(stream_url)
    assert res_unauth.status_code == 401

    # 2. Token de inquilino -> 403
    res_tenant = await async_client.get(
        stream_url,
        headers=_make_admin_headers(
            permissions=["platform_admin.sandbox.access"],
            is_global_staff=False,
        ),
    )
    assert res_tenant.status_code == 403

    # 3. Token global sin permiso access -> 403
    res_no_perm = await async_client.get(
        stream_url,
        headers=_make_admin_headers(permissions=["finops.credits.read"]),
    )
    assert res_no_perm.status_code == 403


def test_playwright_schemas_bidirectional_and_strict_validation() -> None:
    """
    Verifica que los modelos Pydantic v2 cumplan con:
    1. extra='forbid' (rechazo de campos desconocidos).
    2. Soporte estricto camelCase y snake_case.
    3. Tipado sin 'any' y cálculos de porcentaje.
    """
    import pytest
    from pydantic import ValidationError
    from src.modules.tenancy.presentation.schemas_sandbox import (
        PlaywrightCatalogResponseSchema,
        PlaywrightCatalogSummarySchema,
        PlaywrightDomainGroupSchema,
        PlaywrightRunRequestSchema,
        PlaywrightRunTriggerResponseSchema,
        PlaywrightStreamStepEventSchema,
        PlaywrightTestItemSchema,
    )

    # 1. PlaywrightTestItemSchema
    item = PlaywrightTestItemSchema.model_validate(
        {
            "id": "pw_test_01",
            "domain": "inventory",
            "title": "Test Title",
            "description": "Test Desc",
            "status": "ready",
            "tags": ["smoke"],
            "estimatedDurationSec": 25,
            "lastRun": None,
        }
    )
    assert item.estimated_duration_sec == 25
    assert item.model_dump(by_alias=True)["estimatedDurationSec"] == 25

    # Rechazo de campos extra
    with pytest.raises(ValidationError):
        PlaywrightTestItemSchema.model_validate(
            {
                "id": "pw_test_01",
                "domain": "inventory",
                "title": "T",
                "description": "D",
                "status": "ready",
                "extraFieldForbidden": True,
            }
        )

    # 2. PlaywrightCatalogSummarySchema
    summary = PlaywrightCatalogSummarySchema.model_validate(
        {
            "total": 10,
            "ready": 5,
            "inProgress": 3,
            "planned": 2,
            "coveragePercentage": 50.0,
        }
    )
    assert summary.in_progress == 3
    assert summary.coverage_percentage == 50.0

    # 3. PlaywrightStreamStepEventSchema
    step = PlaywrightStreamStepEventSchema.model_validate(
        {
            "stepIndex": 1,
            "testId": "pw_inv_01",
            "message": "Clicking button",
            "level": "step",
            "timestamp": "2026-11-06T00:00:00Z",
            "screenshotUrl": "/path/img.png",
            "durationMs": 120,
        }
    )
    assert step.step_index == 1
    assert step.duration_ms == 120
    assert step.screenshot_url == "/path/img.png"


# ============================================================================
# 7. SUB-PLAN 4 (ETAPA 2): SIMULADOR FEFO TIME-TRAVEL & ACCIÓN QUIRÚRGICA
# ============================================================================


@pytest.mark.asyncio
async def test_fefo_simulation_four_canonical_states_and_loss_math(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica el motor matemático formal de 4 estados canónicos FEFO:
    - OPTIMAL: >= 15 días (loss_rate: 0.0)
    - WARNING: 7 a 14 días (loss_rate: 0.0)
    - CRITICAL: 1 a 6 días (loss_rate: 0.75)
    - EXPIRED: <= 0 días (loss_rate: 1.00)
    Y el cálculo monetario multimoneda con precisión decimal (CLP y USD FX).
    """
    headers = _make_admin_headers(["platform_admin.sandbox.access"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "offsetDays": 0,
        "exchangeRate": 950.0,
        "currency": "CLP",
        "dryRun": True,
    }

    res = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers,
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["totalBatchesEvaluated"] == len(data["batches"])
    assert data["currency"] == "CLP"
    assert data["targetFxCurrency"] == "USD"
    assert data["totalSpoilageRiskAmount"] >= 0.0
    assert data["totalSpoilageRiskFxAmount"] is not None

    # Verificar clasificación y matemáticas de cada lote
    calculated_total_clp = 0.0
    for b in data["batches"]:
        rem = b["daysToExpiration"]
        status = b["status"]
        canonical = b["canonicalStatus"]
        stock = b["stockQuantity"]
        cost = b["unitCost"]
        loss = b["estimatedLossAmount"]
        fx_loss = b["estimatedLossFxAmount"]
        rate = b["lossRateApplied"]

        if rem >= 15:
            assert status == "optimal" and canonical == "OPTIMAL" and rate == 0.0 and loss == 0.0
        elif rem >= 7:
            assert status == "warning" and canonical == "WARNING" and rate == 0.0 and loss == 0.0
        elif rem >= 1:
            assert status == "critical" and canonical == "CRITICAL" and rate == 0.75
            expected_loss = round(stock * cost * 0.75, 2)
            assert abs(loss - expected_loss) < 0.05
        else:
            assert status == "expired" and canonical == "EXPIRED" and rate == 1.00
            expected_loss = round(stock * cost * 1.00, 2)
            assert abs(loss - expected_loss) < 0.05

        if fx_loss is not None:
            expected_fx = round(loss / 950.0, 2)
            assert abs(fx_loss - expected_fx) < 0.05

        calculated_total_clp += loss

    assert abs(data["totalSpoilageRiskAmount"] - round(calculated_total_clp, 2)) < 0.1
    expected_total_fx = round(calculated_total_clp / 950.0, 2)
    assert abs(data["totalSpoilageRiskFxAmount"] - expected_total_fx) < 0.1


@pytest.mark.asyncio
async def test_fefo_simulation_three_demo_scenarios(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica los 3 escenarios de demostración preconfigurados:
    1. HEALTHY: 90% optimal (18), 10% warning (2), 0% critical, 0% expired -> Merma 0 CLP.
    2. WARNING: 50% optimal (10), 30% warning (6), 20% critical (4), 0% expired -> Merma > 0.
    3. CRITICAL: 25% optimal (5), 25% warning (5), 35% critical (7), 15% expired (3) -> Merma máxima y 10 alertas.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.access"])

    # 1. Escenario HEALTHY
    res_healthy = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers,
        json={"tenantSchema": "tenant_qa_lab", "scenarioPreset": "HEALTHY", "offsetDays": 0},
    )
    assert res_healthy.status_code == 200
    d_h = res_healthy.json()
    assert d_h["scenarioApplied"] == "HEALTHY"
    assert d_h["totalBatchesEvaluated"] == 20
    assert d_h["optimalBatchesCount"] == 18
    assert d_h["warningBatchesCount"] == 2
    assert d_h["criticalBatchesCount"] == 0
    assert d_h["expiredBatchesCount"] == 0
    assert d_h["totalSpoilageRiskAmount"] == 0.0

    # 2. Escenario WARNING
    res_warning = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers,
        json={"tenantSchema": "tenant_qa_lab", "scenarioPreset": "WARNING", "offsetDays": 0},
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

    # 3. Escenario CRITICAL con generación de alertas
    res_critical = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        headers=headers,
        json={
            "tenantSchema": "tenant_qa_lab",
            "scenarioPreset": "CRITICAL",
            "offsetDays": 0,
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
    assert d_c["totalSpoilageRiskAmount"] > 0.0
    assert d_c["alertsCreated"] == 10  # 7 critical + 3 expired


@pytest.mark.asyncio
async def test_fefo_shift_buffet_recalculation_and_preview(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica el corrimiento físico FEFO:
    1. dryRun=True: estado preview_only y 0 lotes alterados.
    2. dryRun=False con recalculateBuffet=True: estado applied, shiftedBatchesCount y buffetsShiftedCount.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])

    # 1. Preview Only
    res_preview = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers,
        json={"tenantSchema": "tenant_qa_lab", "offsetDays": 10, "dryRun": True},
    )
    assert res_preview.status_code == 200
    d_p = res_preview.json()
    assert d_p["status"] == "preview_only"
    assert d_p["shiftedBatchesCount"] == 0

    # 2. Applied con recálculo de buffet
    res_applied = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/shift",
        headers=headers,
        json={
            "tenantSchema": "tenant_qa_lab",
            "offsetDays": 10,
            "dryRun": False,
            "recalculateBuffet": True,
        },
    )
    assert res_applied.status_code == 200
    d_a = res_applied.json()
    assert d_a["status"] == "applied"
    assert d_a["shiftedBatchesCount"] == 5
    assert d_a["buffetsShiftedCount"] == 3
    assert d_a["offsetDays"] == 10


@pytest.mark.asyncio
async def test_fefo_sync_today_preview_and_application(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica la acción quirúrgica 'Sincronizar fechas a Hoy':
    1. dryRun=True: retorna estado preview_only y métricas proyectadas.
    2. dryRun=False: retorna estado synchronized, sincroniza 20 lotes y 8 buffets.
    3. recalculateBuffetLots=False: buffetsRecalculatedCount == 0.
    """
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])

    # 1. Dry run
    res_dry = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json={"tenantSchema": "tenant_qa_lab", "dryRun": True},
    )
    assert res_dry.status_code == 200
    d_dry = res_dry.json()
    assert d_dry["status"] == "preview_only"
    assert d_dry["synchronizedBatchesCount"] == 20
    assert d_dry["buffetsRecalculatedCount"] == 8
    assert "baseTodayIso" in d_dry

    # 2. Aplicación efectiva
    res_sync = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json={"tenantSchema": "tenant_qa_lab", "dryRun": False, "recalculateBuffetLots": True},
    )
    assert res_sync.status_code == 200
    d_sync = res_sync.json()
    assert d_sync["status"] == "synchronized"
    assert d_sync["synchronizedBatchesCount"] == 20
    assert d_sync["buffetsRecalculatedCount"] == 8

    # 3. Sin recálculo buffet
    res_no_buf = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json={"tenantSchema": "tenant_qa_lab", "dryRun": False, "recalculateBuffetLots": False},
    )
    assert res_no_buf.status_code == 200
    assert res_no_buf.json()["buffetsRecalculatedCount"] == 0


@pytest.mark.asyncio
async def test_fefo_sync_today_environment_guardrails(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verifica los guardrails Fail-Fast para 'sync-today':
    1. En 'production': dryRun=False bloqueado con 403 (PRODUCTION_MUTATION_FORBIDDEN).
    2. En 'staging': dryRun=False sin confirmación rechazado con 400 (STAGING_CONFIRMATION_REQUIRED).
    3. En 'staging': con confirmStagingAction=True o cabecera X-Sandbox-Confirm-Staging -> 200 OK.
    4. En esquema no autorizado (ej. 'public' o cliente real) -> 400 (ISOLATED_SCHEMA_REQUIRED).
    """
    settings = get_settings()
    headers = _make_admin_headers(["platform_admin.sandbox.manage"])
    payload = {
        "tenantSchema": "tenant_qa_lab",
        "dryRun": False,
    }

    # 1. Producción -> 403
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res_prod = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json=payload,
    )
    assert res_prod.status_code == 403
    assert res_prod.json()["error_code"] == "PRODUCTION_MUTATION_FORBIDDEN"

    # 2. Staging sin confirmación -> 400
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    res_stag_unconf = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json=payload,
    )
    assert res_stag_unconf.status_code == 400
    assert res_stag_unconf.json()["error_code"] == "STAGING_CONFIRMATION_REQUIRED"

    # 3. Staging con confirmación por payload -> 200
    res_stag_conf_payload = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json={**payload, "confirmStagingAction": True},
    )
    assert res_stag_conf_payload.status_code == 200

    # Staging con confirmación por cabecera -> 200
    res_stag_conf_header = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers={**headers, "X-Sandbox-Confirm-Staging": "true"},
        json=payload,
    )
    assert res_stag_conf_header.status_code == 200

    # 4. Esquema no aislado -> 400
    monkeypatch.setattr(settings, "ENVIRONMENT", "lab")
    res_non_iso = await async_client.post(
        "/api/v1/platform-admin/sandbox/fefo/sync-today",
        headers=headers,
        json={**payload, "tenantSchema": "public"},
    )
    assert res_non_iso.status_code == 400
    assert res_non_iso.json()["error_code"] == "ISOLATED_SCHEMA_REQUIRED"


@pytest.mark.asyncio
async def test_fefo_sync_today_rbac_boundaries(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica las barreras RBAC dual de 3 niveles para 'sync-today':
    1. Sin autenticación -> 401 Unauthorized.
    2. Token de inquilino (no global) -> 403 GLOBAL_STAFF_REQUIRED.
    3. Token global con solo lectura (platform_admin.sandbox.access) -> 403 Forbidden.
    4. Token global con gestión (platform_admin.sandbox.manage) -> 200 OK.
    """
    endpoint = "/api/v1/platform-admin/sandbox/fefo/sync-today"
    payload = {"tenantSchema": "tenant_qa_lab", "dryRun": True}

    # 1. Sin autenticación -> 401
    res_unauth = await async_client.post(endpoint, json=payload)
    assert res_unauth.status_code == 401

    # 2. Token de inquilino -> 403 GLOBAL_STAFF_REQUIRED
    tenant_headers = _make_admin_headers(
        permissions=["platform_admin.sandbox.manage"],
        is_global_staff=False,
    )
    res_tenant = await async_client.post(endpoint, headers=tenant_headers, json=payload)
    assert res_tenant.status_code == 403
    assert res_tenant.json()["error_code"] == "GLOBAL_STAFF_REQUIRED"

    # 3. Solo lectura -> 403
    read_headers = _make_admin_headers(permissions=["platform_admin.sandbox.access"])
    res_read = await async_client.post(endpoint, headers=read_headers, json=payload)
    assert res_read.status_code == 403

    # 4. Permiso manage -> 200 OK
    manage_headers = _make_admin_headers(permissions=["platform_admin.sandbox.manage"])
    res_manage = await async_client.post(endpoint, headers=manage_headers, json=payload)
    assert res_manage.status_code == 200


def test_fefo_schemas_strict_extra_forbid_and_serialization() -> None:
    """
    Verifica que los contratos Pydantic v2 del simulador FEFO cumplan con:
    1. extra='forbid' (rechazo estricto de campos desconocidos).
    2. Soporte estricto bidireccional camelCase y snake_case.
    """
    from pydantic import ValidationError
    from src.modules.tenancy.presentation.schemas_sandbox import (
        FefoBatchItemSchema,
        FefoShiftRequest,
        FefoSimulationRequest,
        FefoSyncTodayRequest,
    )

    # 1. FefoSimulationRequest
    req = FefoSimulationRequest.model_validate(
        {
            "offsetDays": 10,
            "tenantSchema": "tenant_qa_lab",
            "scenarioPreset": "HEALTHY",
            "exchangeRate": 980.5,
            "dryRun": True,
        }
    )
    assert req.offset_days == 10
    assert req.tenant_schema == "tenant_qa_lab"
    assert req.scenario_preset == "HEALTHY"
    assert req.exchange_rate == 980.5

    # extra='forbid'
    with pytest.raises(ValidationError):
        FefoSimulationRequest.model_validate(
            {"tenantSchema": "tenant_qa_lab", "unknownFieldForbidden": 123}
        )

    # 2. FefoShiftRequest
    shift_req = FefoShiftRequest.model_validate(
        {
            "offsetDays": 5,
            "tenantSchema": "tenant_qa_lab",
            "recalculateBuffet": True,
            "dryRun": False,
        }
    )
    assert shift_req.recalculate_buffet is True
    assert shift_req.offset_days == 5

    with pytest.raises(ValidationError):
        FefoShiftRequest.model_validate(
            {"tenantSchema": "tenant_qa_lab", "unwantedExtra": True}
        )

    # 3. FefoSyncTodayRequest
    sync_req = FefoSyncTodayRequest.model_validate(
        {
            "tenantSchema": "tenant_sandbox_fefo",
            "recalculateBuffetLots": True,
            "dryRun": True,
        }
    )
    assert sync_req.tenant_schema == "tenant_sandbox_fefo"
    assert sync_req.recalculate_buffet_lots is True

    with pytest.raises(ValidationError):
        FefoSyncTodayRequest.model_validate(
            {"tenantSchema": "tenant_qa_lab", "evilKey": "bad"}
        )

    # 4. FefoBatchItemSchema
    batch = FefoBatchItemSchema.model_validate(
        {
            "batchId": "BATCH-001",
            "productSku": "SKU-001",
            "productName": "Carne Angus",
            "originalExpiryDate": "2026-11-20",
            "simulatedExpiryDate": "2026-11-20",
            "daysToExpiration": 15,
            "status": "optimal",
            "canonicalStatus": "OPTIMAL",
            "stockQuantity": 20.0,
            "unitMeasure": "kg",
            "unitCost": 12000.0,
            "estimatedLossAmount": 0.0,
            "isBuffetBatch": False,
        }
    )
    assert batch.batch_id == "BATCH-001"
    assert batch.canonical_status == "OPTIMAL"



