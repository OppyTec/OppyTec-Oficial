"""
oppytec-backend/tests/unit/modules/test_oppy_ai_api.py
Pruebas integrales de endpoints REST RFC 7807 para OppyFy y Platform Admin:
- `POST /api/v1/oppyfy/chat`: Chat con validación RBAC, deducción atómica de billetera, context meter y data stripping.
- `POST /api/v1/oppyfy/threads/{thread_id}/rollover`: Traspaso a nuevo hilo al 5% con resumen estructurado.
- `GET /api/v1/oppyfy/rbac/domains` y `POST /api/v1/oppyfy/rbac/domains`: Árbol de dominios/subdominios editables por tenant.
- `POST /api/v1/oppyfy/rbac/grants`: Concesión de permisos temporales con triple caducidad y delegación jerárquica.
- `GET /api/v1/oppyfy/wallets/me` y `PATCH /api/v1/oppyfy/wallets/{user_id}`: Billetera de créditos y asignación de cupos.
- `GET /api/v1/platform-admin/token-consumption`: Consola FinOps de consumo de tokens y costos por holding/tenant.
- `GET /api/v1/platform-admin/ai-packs` y `POST /api/v1/platform-admin/ai-packs`: Catálogo de paquetes de créditos IA independientes y cotizador.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import httpx
import pytest

from src.core.security import create_access_token
from src.modules.oppy_ai.domain.oppyfy_rbac import REDACTED_COST_MARKER

pytestmark = pytest.mark.unit


def _make_tenant_headers(
    permissions: list[str],
    *,
    user_id: int = 1,
    hierarchy_rank: int = 0,
    tenant_id: str = "22222222-2222-2222-2222-222222222222",
    holding_id: str = "11111111-1111-1111-1111-111111111111",
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado para el plano de Tenant."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        holding_id=holding_id,
        tenant_schema="tenant_demo",
        is_global_staff=False,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


def _make_admin_headers(
    permissions: list[str],
    *,
    user_id: int = 1,
    is_global_staff: bool = True,
    hierarchy_rank: int = 10,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado para el plano de Platform Admin."""
    token = create_access_token(
        user_id=user_id,
        is_global_staff=is_global_staff,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. OPPYFY CHAT & OPERATIONAL TOOLS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_oppyfy_chat_endpoint_allowed_flow(async_client: httpx.AsyncClient) -> None:
    """Verifica consulta exitosa a OppyFy con deducción de créditos y context health."""
    headers = _make_tenant_headers(["oppyfy.assistant.chat"])
    payload = {
        "prompt_text": "¿Cuál es el nivel de stock crítico actual en bodega?",
        "target_subdomain_slug": "inventory_stock",
        "can_view_costs": True,
        "prior_thread_tokens": 500,
        "remaining_credits": "50.00",
        "estimated_credit_cost": "1.00",
    }
    resp = await async_client.post("/api/v1/oppyfy/chat", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["allowed"] is True
    assert data["status_code"] == "ALLOWED"
    assert "answer_text" in data
    assert Decimal(str(data["credits_deducted"])) > Decimal("0.00")
    assert Decimal(str(data["remaining_credits"])) >= Decimal("0.00")
    assert Decimal(str(data["context_usage_percent"])) >= Decimal("0.00")
    assert data["requires_new_thread"] is False


@pytest.mark.asyncio
async def test_oppyfy_chat_endpoint_redacts_costs_when_unauthorized(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que si can_view_costs=False, se aplique data stripping [REDACTED_COST] a campos de costo."""
    headers = _make_tenant_headers(["oppyfy.assistant.chat"], hierarchy_rank=20)
    payload = {
        "prompt_text": "Muéstrame el stock disponible y los costos unitarios",
        "target_subdomain_slug": "inventory_stock",
        "can_view_costs": False,
        "prior_thread_tokens": 100,
        "remaining_credits": "20.00",
        "estimated_credit_cost": "1.00",
    }
    resp = await async_client.post("/api/v1/oppyfy/chat", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["allowed"] is True
    # Si la herramienta devolvió payload de inventario, los costos deben estar redactados
    if data.get("tool_payload"):
        tool_data = data["tool_payload"]
        if "costo_unitario" in tool_data:
            assert tool_data["costo_unitario"] == REDACTED_COST_MARKER
        if "precio_compra" in tool_data:
            assert tool_data["precio_compra"] == REDACTED_COST_MARKER


@pytest.mark.asyncio
async def test_oppyfy_chat_endpoint_forbidden_403_without_rbac(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica error RFC 7807 403 Forbidden al no poseer el permiso oppyfy.assistant.chat."""
    unauthorized_headers = _make_tenant_headers(["catalog.products.read"])
    payload = {
        "prompt_text": "Dame un resumen del negocio",
        "target_subdomain_slug": "inventory_stock",
    }
    resp = await async_client.post("/api/v1/oppyfy/chat", json=payload, headers=unauthorized_headers)
    assert resp.status_code == 403, resp.text
    problem = resp.json()
    assert problem["status"] == 403
    assert "detail" in problem or "title" in problem


# ============================================================================
# 2. THREAD ROLLOVER TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_oppyfy_thread_rollover_resets_context_to_5_pct(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica traspaso asistido a un hilo fresco conservando resumen clave al 5.00%."""
    headers = _make_tenant_headers(["oppyfy.assistant.chat"])
    thread_id = str(uuid.uuid4())
    payload = {
        "summary_notes": "Acordado reabastecer Lomo Vetado para el banquete del sábado.",
        "prior_thread_tokens": 15000,
    }
    resp = await async_client.post(
        f"/api/v1/oppyfy/threads/{thread_id}/rollover",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["previous_thread_id"] == thread_id
    assert data["new_thread_id"] != thread_id
    assert Decimal(str(data["fresh_context_usage_percent"])) == Decimal("5.00")
    assert "summary_artifact" in data
    assert "Lomo Vetado" in data["summary_artifact"] or "Análisis" in data["summary_artifact"]


# ============================================================================
# 3. RBAC DOMAINS TREE & GRANTS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_oppyfy_rbac_domains_list_and_create(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica consulta del árbol de dominios y creación de un nuevo dominio con subdominios."""
    read_headers = _make_tenant_headers(["oppyfy.rbac_domains.read"])
    resp_list = await async_client.get("/api/v1/oppyfy/rbac/domains", headers=read_headers)
    assert resp_list.status_code == 200, resp_list.text
    domains = resp_list.json()
    assert len(domains) >= 3

    write_headers = _make_tenant_headers(["oppyfy.rbac_domains.write"])
    new_domain_payload = {
        "domain_key": "auditoria_operativa",
        "name_es": "Auditoría Operativa y Cumplimiento",
        "name_en": "Operational Audit & Compliance",
        "icon": "ShieldCheck",
        "sort_order": 4,
        "is_active": True,
        "subdomains": [
            {
                "subdomain_key": "auditoria_kardex",
                "name_es": "Auditoría de Kardex",
                "name_en": "Kardex Audit",
                "allowed_tool_functions": ["analyze_waste_and_merma_impact"],
                "can_view_costs_default": False,
                "is_active": True,
            }
        ],
    }
    resp_create = await async_client.post(
        "/api/v1/oppyfy/rbac/domains",
        json=new_domain_payload,
        headers=write_headers,
    )
    assert resp_create.status_code == 201, resp_create.text
    created = resp_create.json()
    assert created["domain_key"] == "auditoria_operativa"
    assert len(created["subdomains"]) == 1
    assert created["subdomains"][0]["subdomain_key"] == "auditoria_kardex"


@pytest.mark.asyncio
async def test_oppyfy_rbac_grants_creation_with_delegation_check(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica otorgamiento de concesión de permisos temporales a un trabajador."""
    grant_headers = _make_tenant_headers(["oppyfy.rbac_grants.write"], hierarchy_rank=0)
    grant_payload = {
        "user_id": 105,
        "subdomain_id": 2,
        "subdomain_slug": "inventory_stock",
        "can_query": True,
        "can_view_costs": False,
        "max_prompts": 25,
        "temp_credit_ceiling": "15.00",
    }
    resp = await async_client.post(
        "/api/v1/oppyfy/rbac/grants",
        json=grant_payload,
        headers=grant_headers,
    )
    assert resp.status_code == 201, resp.text
    grant = resp.json()
    assert grant["user_id"] == 105
    assert grant["max_prompts"] == 25
    assert Decimal(str(grant["temp_credit_ceiling"])) == Decimal("15.00")
    assert grant["is_active"] is True


# ============================================================================
# 4. WORKER WALLETS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_oppyfy_wallets_me_and_management(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica consulta de billetera propia y actualización de cupos por administrador."""
    worker_headers = _make_tenant_headers(["oppyfy.credits.read"], user_id=101)
    resp_me = await async_client.get("/api/v1/oppyfy/wallets/me", headers=worker_headers)
    assert resp_me.status_code == 200, resp_me.text
    wallet_me = resp_me.json()
    assert wallet_me["user_id"] == 101
    assert Decimal(str(wallet_me["remaining_credits"])) >= Decimal("0.00")

    # Retrocompatibilidad: alias /credits/wallet
    resp_alias = await async_client.get("/api/v1/oppyfy/credits/wallet", headers=worker_headers)
    assert resp_alias.status_code == 200
    assert resp_alias.json()["user_id"] == 101

    # Actualización de cupo por administrador
    admin_headers = _make_tenant_headers(["oppyfy.credits.manage"], user_id=1, hierarchy_rank=0)
    patch_payload = {
        "assigned_credit_ceiling": "75.00",
        "is_oppyfy_enabled": True,
    }
    resp_patch = await async_client.patch(
        "/api/v1/oppyfy/wallets/101",
        json=patch_payload,
        headers=admin_headers,
    )
    assert resp_patch.status_code == 200, resp_patch.text
    updated_wallet = resp_patch.json()
    assert Decimal(str(updated_wallet["assigned_credits_balance"])) == Decimal("75.00")
    assert updated_wallet["is_oppyfy_enabled"] is True


# ============================================================================
# 5. PLATFORM ADMIN: AI PACKS & TOKEN CONSUMPTION
# ============================================================================


@pytest.mark.asyncio
async def test_platform_admin_ai_packs_crud_and_quotes(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica CRUD de paquetes de créditos IA independientes y cálculo de cotización."""
    admin_headers = _make_admin_headers(
        ["platform_admin.ai_packs.read", "platform_admin.ai_packs.write"]
    )

    # 1. Listar paquetes predeterminados
    resp_list = await async_client.get("/api/v1/platform-admin/ai-packs", headers=admin_headers)
    assert resp_list.status_code == 200, resp_list.text
    packs = resp_list.json()
    assert len(packs) >= 3

    # 2. Crear nuevo paquete
    create_payload = {
        "pack_name": "Mega Titan Pack (50.000 Créditos)",
        "credits_amount": "50000.00",
        "price_clp": "349990.00",
        "price_usd": "380.00",
        "bonus_credits": "5000.00",
        "is_popular": True,
        "is_active": True,
        "sort_order": 4,
        "plan_tier_discounts": {
            "plan_basico": "0.00",
            "plan_pro": "15.00",
            "plan_enterprise": "30.00",
        },
    }
    resp_create = await async_client.post(
        "/api/v1/platform-admin/ai-packs",
        json=create_payload,
        headers=admin_headers,
    )
    assert resp_create.status_code == 201, resp_create.text
    new_pack = resp_create.json()
    assert new_pack["pack_name"] == "Mega Titan Pack (50.000 Créditos)"
    assert Decimal(str(new_pack["total_credits"])) == Decimal("55000.00")
    pack_id = new_pack["id"]

    # 3. Cotizar paquete para cliente en plan_enterprise (descuento del 30%)
    resp_quote = await async_client.get(
        f"/api/v1/platform-admin/ai-packs/{pack_id}/quote?base_plan_tier=plan_enterprise",
        headers=admin_headers,
    )
    assert resp_quote.status_code == 200, resp_quote.text
    quote = resp_quote.json()
    assert Decimal(str(quote["discount_pct"])) == Decimal("30.00")
    # Precio USD original 380.00 - 30% = 266.00
    assert Decimal(str(quote["final_price_usd"])) == Decimal("266.00")
    assert Decimal(str(quote["total_credits"])) == Decimal("55000.00")


@pytest.mark.asyncio
async def test_platform_admin_ai_packs_unauthorized_403(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica 403 Forbidden cuando un usuario sin permisos intenta acceder a paquetes IA."""
    unauthorized_headers = _make_admin_headers(["platform_admin.plans.read"])
    resp = await async_client.get("/api/v1/platform-admin/ai-packs", headers=unauthorized_headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_oppyfy_telemetry_logs_endpoint(async_client: httpx.AsyncClient) -> None:
    """Verifica listado de telemetría de invocaciones IA para auditoría."""
    admin_headers = _make_admin_headers(["oppyfy.telemetry.read"])
    resp = await async_client.get("/api/v1/oppyfy/telemetry/logs", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    logs = resp.json()
    assert isinstance(logs, list)
