"""
oppytec-backend/tests/unit/modules/test_admin_plans_and_tokens_api.py
Suite de pruebas unitarias y de integración REST para la Fase 2 de Planes Comerciales,
Política Global SaaS y Consola FinOps de Consumo de Tokens:
- `GET /api/v1/platform-admin/plans`: listado ordenado por tier ASC y active_clients_count.
- `POST /api/v1/platform-admin/plans`: creación con auto-slug, tier y créditos IA.
- `PUT /api/v1/platform-admin/plans/{slug}`: actualización de precios y cuotas.
- `DELETE /api/v1/platform-admin/plans/{slug}`: bloqueo 409 si existen clientes asignados.
- `GET /api/v1/platform-admin/ai-credits/policy` y `PUT /api/v1/platform-admin/ai-credits/policy`: lectura y mutación de tasa de conversión.
- `GET /api/v1/platform-admin/token-consumption`: agregación jerárquica Holding -> Tenant -> Logs.
- `PATCH /api/v1/platform-admin/holdings/{id}/ai-credits` y `PATCH /api/v1/platform-admin/tenants/{id}/ai-credits`: ajuste de cupos.
- Control de acceso RBAC de 3 niveles y denegación 403 a tokens no autorizados.
"""
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from src.core.security import create_access_token
from src.modules.tenancy.presentation.platform_admin_router import (
    _admin_plans_service,
    _credit_quota_service,
    _saas_policy_service,
    _token_consumption_service,
)
from src.modules.tenancy.presentation.router import (
    _holdings_store,
    _tenants_store,
)

pytestmark = pytest.mark.unit


def _make_admin_headers(
    permissions: list[str],
    user_id: int = 1,
    is_global_staff: bool = True,
    is_superuser_god: bool = False,
    hierarchy_rank: int = 10,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado para el plano global / platform-admin."""
    token = create_access_token(
        user_id=user_id,
        is_global_staff=is_global_staff,
        is_superuser_god=is_superuser_god,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
    )
    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.fixture(autouse=True)
def _reset_platform_admin_state() -> None:
    """Aísla el estado en memoria antes de cada test."""
    _saas_policy_service.reset()
    _admin_plans_service.reset()
    _admin_plans_service.set_clients_stores(_holdings_store, _tenants_store)
    _credit_quota_service.reset()
    _token_consumption_service.reset()


@pytest.mark.asyncio
async def test_list_plans_endpoint_order_and_client_counts(async_client: httpx.AsyncClient) -> None:
    """Verifica que los planes comerciales se ordenen por tier ASC y calculen active_clients_count dinámico."""
    headers = _make_admin_headers(["platform_admin.plans.read"])

    resp = await async_client.get("/api/v1/platform-admin/plans", headers=headers)
    assert resp.status_code == 200, resp.text
    plans = resp.json()

    assert len(plans) >= 3
    # Verificar ordenación por tier ASC
    tiers = [p["tier"] for p in plans]
    assert tiers == sorted(tiers)

    # Buscar 'basic' y 'starter' que están asignados a holding_genesis y holding_pacifico
    plan_map = {p["slug"]: p for p in plans}
    assert "basic" in plan_map
    assert "starter" in plan_map
    assert "enterprise" in plan_map

    assert plan_map["basic"]["active_clients_count"] >= 1
    assert plan_map["starter"]["active_clients_count"] >= 1
    assert plan_map["enterprise"]["active_clients_count"] == 0

    # Validar campos extendidos
    assert plan_map["basic"]["monthly_ai_credits"] > 0
    assert plan_map["starter"]["is_popular"] is True


@pytest.mark.asyncio
async def test_create_and_update_plan_endpoint(async_client: httpx.AsyncClient) -> None:
    """Verifica la creación y actualización de un nuevo plan comercial con créditos IA y precios multi-moneda."""
    headers = _make_admin_headers(["platform_admin.plans.manage", "platform_admin.plans.read"])

    # 1. Crear nuevo plan
    create_payload = {
        "slug": "custom-bistro",
        "name": "Plan Bistró & Cafetería",
        "description": "Plan especializado para cafeterías y bistrós medianos.",
        "tier": 2,
        "monthly_ai_credits": 3500,
        "is_popular": False,
        "is_active": True,
        "max_active_users": 15,
        "max_products": 800,
        "max_suppliers": 30,
        "max_recipes": 100,
        "max_combos": 25,
        "max_storage_mb": 2048,
        "included_modules": ["catalog", "inventory", "recipes"],
        "price_clp": "55000.00",
        "price_usd": "59.00",
    }

    create_resp = await async_client.post(
        "/api/v1/platform-admin/plans",
        headers=headers,
        json=create_payload,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["slug"] == "custom-bistro"
    assert created["monthly_ai_credits"] == 3500
    assert Decimal(created["price_clp"]) == Decimal("55000.00")
    assert created["active_clients_count"] == 0

    # 2. Actualizar plan recién creado
    update_payload = {
        "name": "Plan Bistró & Cafetería Premium",
        "monthly_ai_credits": 4000,
        "is_popular": True,
        "price_clp": "59990.00",
    }
    update_resp = await async_client.put(
        "/api/v1/platform-admin/plans/custom-bistro",
        headers=headers,
        json=update_payload,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "Plan Bistró & Cafetería Premium"
    assert updated["monthly_ai_credits"] == 4000
    assert updated["is_popular"] is True
    assert Decimal(updated["price_clp"]) == Decimal("59990.00")


@pytest.mark.asyncio
async def test_delete_plan_conflict_409_when_clients_exist(async_client: httpx.AsyncClient) -> None:
    """Verifica que borrar un plan con clientes asignados arroje HTTP 409 Conflict, y uno sin clientes se elimine."""
    headers = _make_admin_headers(["platform_admin.plans.manage", "platform_admin.plans.read"])

    # 1. Intentar borrar 'basic' (tiene holding_genesis asignado) debe fallar con 409
    del_conflict_resp = await async_client.delete(
        "/api/v1/platform-admin/plans/basic",
        headers=headers,
    )
    assert del_conflict_resp.status_code == 409
    conflict_data = del_conflict_resp.json()
    assert conflict_data["error_code"] == "PLAN_IN_USE_CONFLICT"

    # 2. Borrar 'enterprise' (0 clientes asignados) debe ser exitoso
    del_ok_resp = await async_client.delete(
        "/api/v1/platform-admin/plans/enterprise",
        headers=headers,
    )
    assert del_ok_resp.status_code == 200
    assert del_ok_resp.json()["slug"] == "enterprise"

    # 3. Confirmar que ya no existe
    list_resp = await async_client.get("/api/v1/platform-admin/plans", headers=headers)
    remaining_slugs = [p["slug"] for p in list_resp.json()]
    assert "enterprise" not in remaining_slugs


@pytest.mark.asyncio
async def test_get_and_update_saas_ai_policy(async_client: httpx.AsyncClient) -> None:
    """Verifica la consulta y actualización atómica de la política global de conversión SaaS."""
    headers = _make_admin_headers(["platform_admin.plans.manage", "platform_admin.plans.read"])

    # 1. Consultar política actual
    get_resp = await async_client.get("/api/v1/platform-admin/ai-credits/policy", headers=headers)
    assert get_resp.status_code == 200
    policy = get_resp.json()
    assert policy["tokens_per_credit"] == 1000
    assert policy["default_monthly_credits"] == 2000
    assert Decimal(policy["credit_price_clp"]) == Decimal("15.00")

    # 2. Actualizar política
    upd_payload = {
        "tokens_per_credit": 1250,
        "default_monthly_credits": 3000,
        "credit_price_clp": "18.50",
        "credit_price_usd": "0.0195",
    }
    put_resp = await async_client.put(
        "/api/v1/platform-admin/ai-credits/policy",
        headers=headers,
        json=upd_payload,
    )
    assert put_resp.status_code == 200
    updated_policy = put_resp.json()
    assert updated_policy["tokens_per_credit"] == 1250
    assert updated_policy["default_monthly_credits"] == 3000
    assert Decimal(updated_policy["credit_price_clp"]) == Decimal("18.50")
    assert Decimal(updated_policy["credit_price_usd"]) == Decimal("0.0195")


@pytest.mark.asyncio
async def test_token_consumption_hierarchy_and_filters(async_client: httpx.AsyncClient) -> None:
    """Verifica la agregación jerárquica FinOps (Holdings -> Tenants -> Logs) y filtros server-side."""
    headers = _make_admin_headers(["platform_admin.tokens.read"])

    # 1. Consulta general
    resp = await async_client.get("/api/v1/platform-admin/token-consumption", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["total_records"] == 4
    assert data["total_tokens_all"] > 0
    assert len(data["holdings"]) == 2
    assert len(data["logs"]) == 4

    # Verificar jerarquía de Holding -> Tenants -> Logs
    h_pacifico = next(h for h in data["holdings"] if h["holding_id"] == "holding_pacifico")
    assert len(h_pacifico["tenants"]) == 1
    t_pacifico = h_pacifico["tenants"][0]
    assert t_pacifico["tenant_id"] == "tenant_pacifico_centro"
    assert len(t_pacifico["logs"]) == 2

    # 2. Filtro de búsqueda por modelo
    resp_model = await async_client.get(
        "/api/v1/platform-admin/token-consumption?model_name=gemini-1.5-pro",
        headers=headers,
    )
    assert resp_model.status_code == 200
    data_model = resp_model.json()
    assert data_model["total_records"] == 1
    assert data_model["logs"][0]["model_name"] == "gemini-1.5-pro"

    # 3. Filtro por estado api_success=False
    resp_failed = await async_client.get(
        "/api/v1/platform-admin/token-consumption?api_success=false",
        headers=headers,
    )
    assert resp_failed.status_code == 200
    data_failed = resp_failed.json()
    assert data_failed["total_records"] == 1
    assert data_failed["logs"][0]["api_success"] is False


@pytest.mark.asyncio
async def test_adjust_holding_and_tenant_ai_credits(async_client: httpx.AsyncClient) -> None:
    """Verifica los endpoints de ajuste de cupos de créditos para Holdings y Tenants."""
    headers = _make_admin_headers(["platform_admin.tokens.manage_quotas"])

    # 1. Ajustar cupo de Holding
    holding_resp = await async_client.patch(
        "/api/v1/platform-admin/holdings/holding_genesis/ai-credits",
        headers=headers,
        json={
            "monthly_credits": 7500,
            "distribution_mode": "per_tenant",
        },
    )
    assert holding_resp.status_code == 200, holding_resp.text
    h_data = holding_resp.json()
    assert h_data["target_id"] == "holding_genesis"
    assert h_data["monthly_credits"] == 7500
    assert h_data["distribution_mode"] == "per_tenant"

    # 2. Ajustar cupo de Tenant
    tenant_resp = await async_client.patch(
        "/api/v1/platform-admin/tenants/tenant_genesis/ai-credits",
        headers=headers,
        json={"monthly_credits": 3000},
    )
    assert tenant_resp.status_code == 200, tenant_resp.text
    t_data = tenant_resp.json()
    assert t_data["target_id"] == "tenant_genesis"
    assert t_data["monthly_credits"] == 3000


@pytest.mark.asyncio
async def test_rbac_denial_on_platform_admin_endpoints(async_client: httpx.AsyncClient) -> None:
    """Verifica que tokens no autorizados o sin permisos globales de platform_admin sean rechazados con HTTP 403."""
    # Token tenant-scoped sin permisos de platform-admin
    unauthorized_token = create_access_token(
        user_id=50,
        holding_id="holding_genesis",
        tenant_id="tenant_genesis",
        is_global_staff=False,
        is_superuser_god=False,
        role_grants=["inventory.stock.read"],
    )
    unauthorized_headers = {"Authorization": f"Bearer {unauthorized_token}"}

    # 1. Consulta de planes sin permiso
    r1 = await async_client.get("/api/v1/platform-admin/plans", headers=unauthorized_headers)
    assert r1.status_code == 403

    # 2. Consulta de política sin permiso
    r2 = await async_client.get("/api/v1/platform-admin/ai-credits/policy", headers=unauthorized_headers)
    assert r2.status_code == 403

    # 3. Consulta de consumo de tokens sin permiso
    r3 = await async_client.get("/api/v1/platform-admin/token-consumption", headers=unauthorized_headers)
    assert r3.status_code == 403

    # 4. Token con permiso de lectura intentando mutar política
    readonly_headers = _make_admin_headers(["platform_admin.plans.read"])
    r4 = await async_client.put(
        "/api/v1/platform-admin/ai-credits/policy",
        headers=readonly_headers,
        json={"tokens_per_credit": 2000},
    )
    assert r4.status_code == 403
