"""
oppytec-backend/tests/unit/test_mock_data_manager.py
Pruebas unitarias co-creadas 1:1 para el Gestor Central de Mock Data vs Clean Slate (ADR-022):
1. Carga y validación de `oppytec-backend/fixtures/mock_data_backup.json` (`load_mock_data_backup`).
2. Purga integral a Clean Slate (`purge_all_runtime_mock_stores`) en routers y servicios en memoria.
3. Preservación exclusiva del SuperUser Génesis (`OppyTec.Admin@gmail.com` / `oppytec2026`),
   los 3 planes base (`DEFAULT_SYSTEM_PLANS`) y los 5 roles base (`TENANT_BASE_ROLES`).
4. Restauración bajo demanda (`restore_runtime_mock_stores`) desde el respaldo JSON.
5. Filtrado por cabecera `X-OppyTec-Mock-Mode: clean` en endpoints de Tenancy y Platform Admin.
6. Integración con `/api/v1/platform-admin/sandbox/mock-data/backup`, `reset` y `generate`.
"""
from __future__ import annotations

from collections.abc import Generator

import httpx
import pytest

from src.core.bootstrap import DEFAULT_SYSTEM_PLANS, TENANT_BASE_ROLES
from src.core.mock_data_manager import (
    is_clean_slate_active,
    load_mock_data_backup,
    purge_all_runtime_mock_stores,
    reset_default_demo_stores,
    restore_runtime_mock_stores,
)
from src.core.security import create_access_token
from src.modules.catalog.presentation.router import (
    _brands_store,
    _categories_store,
    _container_types_store,
    _products_store,
)
from src.modules.identity.presentation.router import (
    _CLIENT_USERS_STORE,
    _GLOBAL_USERS_STORE,
    _custom_roles,
    _match_store_user,
)
from src.modules.oppy_ai.presentation.router import (
    _permission_grants_store,
    _worker_wallets_store,
)
from src.modules.tenancy.presentation.router import (
    _holdings_store,
    _legal_entities_store,
    _plans_store,
    _tenants_store,
)
from src.modules.tenancy.presentation.sandbox_router import (
    _sandbox_service,
    get_sandbox_service,
)

pytestmark = pytest.mark.unit


def _make_global_admin_headers(
    mock_mode: str | None = None,
) -> dict[str, str]:
    token = create_access_token(
        user_id=1,
        is_global_staff=True,
        is_superuser_god=True,
        hierarchy_rank=0,
        role_grants=[
            "platform_admin.sandbox.access",
            "platform_admin.sandbox.manage",
            "platform_admin.tokens.read",
            "tenancy.holdings.read",
            "tenancy.legal_entities.read",
            "tenancy.tenants.read",
            "tenancy.client_users.read",
            "tenancy.dashboard.read",
        ],
    )
    headers = {"Authorization": f"Bearer {token}"}
    if mock_mode is not None:
        headers["X-OppyTec-Mock-Mode"] = mock_mode
    return headers


@pytest.fixture(autouse=True)
def _isolate_runtime_stores() -> Generator[None, None, None]:
    """Garantiza que cada test inicie y finalice con los stores demo por defecto restaurados."""
    get_sandbox_service().reset()
    yield
    get_sandbox_service().reset()


def test_load_mock_data_backup_structure_and_immutability() -> None:
    """Valida que `load_mock_data_backup()` cargue el JSON de respaldo y retorne copias aisladas."""
    backup = load_mock_data_backup()
    assert "metadata" in backup
    assert "postgresql_pre_clean_snapshot" in backup
    assert "backend_modules" in backup

    mods = backup["backend_modules"]
    assert "tenancy_router" in mods
    assert "identity_router" in mods
    assert "catalog_router" in mods
    assert "oppy_ai_router" in mods
    assert "sandbox_service" in mods

    # Verificar que mutar la copia retornada no contamine el caché interno
    backup["metadata"]["backup_version"] = "mutated"
    fresh_backup = load_mock_data_backup()
    assert "backup_version" not in fresh_backup["metadata"]


def test_purge_all_runtime_mock_stores_preserves_only_genesis_and_base_catalog() -> None:
    """
    Verifica que `purge_all_runtime_mock_stores()` vacíe todos los datos mock/demostrativos
    y preserve exclusivamente el SuperUser `OppyTec.Admin@gmail.com` (`oppytec2026`),
    los 3 planes base y los 5 roles base.
    """
    purged = purge_all_runtime_mock_stores()
    assert is_clean_slate_active() is True
    assert purged["holdings"] >= 2
    assert purged["tenants"] >= 2

    # 1. Tenancy stores vacíos excepto los 3 planes base
    assert len(_holdings_store) == 0
    assert len(_legal_entities_store) == 0
    assert len(_tenants_store) == 0
    assert set(_plans_store.keys()) == {p.slug for p in DEFAULT_SYSTEM_PLANS}

    # 2. Identity stores: 0 client_users y únicamente SuperUser Génesis en _GLOBAL_USERS_STORE
    assert len(_CLIENT_USERS_STORE) == 0
    assert list(_GLOBAL_USERS_STORE.keys()) == [1]
    genesis = _GLOBAL_USERS_STORE[1]
    assert genesis["email"] == "OppyTec.Admin@gmail.com"
    assert genesis["username"] == "oppytec.admin"
    assert genesis["is_superuser"] is True
    assert genesis["is_global_admin"] is True
    assert (
        _match_store_user(_GLOBAL_USERS_STORE, "oppytec.admin@gmail.com", "oppytec2026")
        is not None
    )
    assert set(_custom_roles.keys()) == {r.slug for r in TENANT_BASE_ROLES}

    # 3. Catalog, OppyAI y Sandbox stores vacíos
    assert len(_products_store) == 0
    assert len(_categories_store) == 0
    assert len(_brands_store) == 0
    assert len(_container_types_store) == 0
    assert len(_worker_wallets_store) == 0
    assert len(_permission_grants_store) == 0
    assert len(_sandbox_service._history_ring_buffer) == 0


def test_restore_runtime_mock_stores_repopulates_from_backup() -> None:
    """Verifica que tras una purga Clean Slate, `restore_runtime_mock_stores()` restaure los datos."""
    purge_all_runtime_mock_stores()
    assert len(_holdings_store) == 0
    assert len(_categories_store) == 0

    restored = restore_runtime_mock_stores("fast-food-pollo-king")
    assert is_clean_slate_active() is False
    assert restored["holdings"] == 2
    assert restored["legal_entities"] == 2
    assert restored["tenants"] == 2
    assert restored["client_users"] == 2
    assert restored["categories"] == 3
    assert restored["brands"] == 3
    assert restored["container_types"] == 3
    assert restored["products"] > 0
    assert restored["worker_wallets"] == 2

    reset_default_demo_stores()
    assert len(_products_store) == 0


@pytest.mark.asyncio
async def test_clean_mock_mode_header_filters_demo_records_in_endpoints(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que enviar `X-OppyTec-Mock-Mode: clean` en los endpoints de Tenancy y Platform Admin
    retorne colecciones vacías y contadores en 0 cuando solo existen datos demostrativos.
    """
    clean_headers = _make_global_admin_headers(mock_mode="clean")

    holdings_res = await async_client.get(
        "/api/v1/tenancy/holdings", headers=clean_headers
    )
    assert holdings_res.status_code == 200
    assert holdings_res.json() == []

    le_res = await async_client.get(
        "/api/v1/tenancy/legal-entities", headers=clean_headers
    )
    assert le_res.status_code == 200
    assert le_res.json() == []

    tenants_res = await async_client.get(
        "/api/v1/tenancy/tenants", headers=clean_headers
    )
    assert tenants_res.status_code == 200
    assert tenants_res.json() == []

    cu_res = await async_client.get(
        "/api/v1/tenancy/client-users", headers=clean_headers
    )
    assert cu_res.status_code == 200
    assert cu_res.json() == []

    summary_res = await async_client.get(
        "/api/v1/tenancy/dashboard/summary", headers=clean_headers
    )
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["holdings"] == 0
    assert summary_data["legal_entities"] == 0
    assert summary_data["tenants"] == 0
    assert summary_data["client_users"] == 0
    assert summary_data["users"] == 1
    assert summary_data["plans"] == 3

    tokens_res = await async_client.get(
        "/api/v1/platform-admin/token-consumption", headers=clean_headers
    )
    assert tokens_res.status_code == 200
    tokens_data = tokens_res.json()
    assert tokens_data["holdings"] == []
    assert tokens_data["logs"] == []
    assert tokens_data["total_records"] == 0
    assert tokens_data["total_tokens_all"] == 0

    jev_res = await async_client.get(
        "/api/v1/platform-admin/jev-consumption", headers=clean_headers
    )
    assert jev_res.status_code == 200
    jev_data = jev_res.json()
    assert jev_data["holdings"] == []
    assert jev_data["tenants"] == []
    assert jev_data["all_logs"] == []
    assert jev_data["total_decisions_all"] == 0


@pytest.mark.asyncio
async def test_sandbox_backup_endpoint_and_clean_slate_vs_preset_reset(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica:
    1. `GET /api/v1/platform-admin/sandbox/mock-data/backup` retorna el JSON de respaldo.
    2. `POST /api/v1/platform-admin/sandbox/mock-data/reset` con `clean-slate` vacía los stores.
    3. `POST /api/v1/platform-admin/sandbox/mock-data/generate` con `dryRun=False` restaura los stores.
    """
    headers = _make_global_admin_headers()

    # 1. Endpoint de backup JSON
    backup_res = await async_client.get(
        "/api/v1/platform-admin/sandbox/mock-data/backup",
        headers=headers,
    )
    assert backup_res.status_code == 200
    backup_json = backup_res.json()
    assert "metadata" in backup_json
    assert "backend_modules" in backup_json

    # 2. Factory Reset a Clean Slate
    reset_res = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        headers=headers,
        json={
            "tenantSchema": "tenant_sandbox_fefo",
            "targetPresetId": "clean-slate",
            "confirmReset": True,
        },
    )
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["recordsReseeded"]["holdings"] == 0
    assert reset_data["recordsReseeded"]["tenants"] == 0
    assert reset_data["recordsReseeded"]["products"] == 0
    assert len(_holdings_store) == 0
    assert len(_tenants_store) == 0

    # 3. Generación real (dryRun=False) restaura los stores desde el backup
    gen_res = await async_client.post(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        headers=headers,
        json={
            "tenantSchema": "tenant_qa_lab",
            "categories": ["all"],
            "volume": "small",
            "dryRun": False,
        },
    )
    assert gen_res.status_code == 200
    assert len(_holdings_store) == 2
    assert len(_tenants_store) == 2
