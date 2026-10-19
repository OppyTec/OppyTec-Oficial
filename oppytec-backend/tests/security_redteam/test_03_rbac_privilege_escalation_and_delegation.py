"""
Vector Red Team 03 (`tests/security_redteam/test_03_rbac_privilege_escalation_and_delegation.py`):
- Ley 1 (Anti-Escalamiento de Rango): `actor_rank >= target_rank` bloqueado tanto en roles como en delegación JIT.
- Ley 2 (Techo de Cristal / Grant Ceiling): prohibido delegar un permiso que el actor no posee efectivamente.
- Precedencia `DENY` explícito sobre cualquier `ALLOW` de rol o concesión temporal JIT.
- Bloqueo por módulo no contratado en el Plan Comercial (`MODULE_NOT_IN_SUBSCRIPTION_PLAN`).
"""
from __future__ import annotations

import httpx
import pytest

from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.modules.identity.domain.rbac_evaluator import evaluate_effective_permission

pytestmark = pytest.mark.security_redteam


async def test_hierarchy_rank_escalation_blocked_on_role_and_jit_endpoints(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Un Jefe de Bodega (`hierarchy_rank=20`) NO puede crear/modificar un rol con `hierarchy_rank <= 20`
    ni emitir un permiso JIT a un par (`rank=20`) o superior (`rank=10`).
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    rank20_token = create_access_token(
        user_id=301,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=20,
        role_grants=[
            "settings.roles.manage",
            "settings.rbac.delegate_subordinates",
            "inventory.mermas.approve",
        ],
        accessible_tenants=["tenant_rest_a"],
    )
    headers = {
        "Authorization": f"Bearer {rank20_token}",
        "X-Tenant-ID": "tenant_rest_a",
    }

    # 1. Intento de crear un rol con rango superior (10) o igual (20) -> HTTP 403
    for forbidden_rank in (0, 10, 20):
        role_resp = await async_client.post(
            "/api/v1/identity/roles",
            headers=headers,
            json={
                "slug": f"escalated_role_{forbidden_rank}",
                "name": "Rol Escalado",
                "hierarchy_rank": forbidden_rank,
                "permissions": ["inventory.mermas.approve"],
            },
        )
        assert role_resp.status_code == 403
        assert role_resp.json()["error_code"] == "HIERARCHY_RANK_VIOLATION"

    # 2. Intento de delegar JIT a un usuario de rango igual (20) o superior (10) -> HTTP 403
    jit_same_rank = await async_client.post(
        "/api/v1/identity/grants/jit",
        headers=headers,
        json={
            "target_user_id": 302,
            "target_rank": 20,
            "permission_code": "inventory.mermas.approve",
            "effect": "ALLOW",
            "reason": "Intento de auto-delegación lateral entre pares",
            "max_uses": 1,
        },
    )
    assert jit_same_rank.status_code == 403
    assert jit_same_rank.json()["error_code"] == "HIERARCHY_RANK_VIOLATION"


async def test_grant_ceiling_blocks_delegating_unowned_permission(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Ley 2 (Techo de Cristal): Un Administrador (`rank=10`) no puede delegar a un subordinado (`rank=30`)
    un permiso que él mismo no posee en sus `effective_permissions`.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    admin_token = create_access_token(
        user_id=310,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=10,
        role_grants=[
            "settings.rbac.delegate_subordinates",
            "inventory.kardex.read",
        ],
        accessible_tenants=["tenant_rest_a"],
    )
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Tenant-ID": "tenant_rest_a",
    }

    ceiling_resp = await async_client.post(
        "/api/v1/identity/grants/jit",
        headers=headers,
        json={
            "target_user_id": 350,
            "target_rank": 30,
            "permission_code": "procurement.orders.approve",
            "effect": "ALLOW",
            "reason": "Intento de otorgar permiso que el actor no posee",
            "max_uses": 1,
        },
    )
    assert ceiling_resp.status_code == 403
    assert ceiling_resp.json()["error_code"] == "GRANT_CEILING_EXCEEDED"


async def test_explicit_deny_and_uncontracted_plan_module_override_allow_grants(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que:
    1. Un `DENY` explícito prevalezca sobre `role_grants` y `temp_grants`.
    2. Un módulo ausente en `contracted_modules` sea denegado con `MODULE_NOT_ENABLED_IN_PLAN`.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    # 1. Precedencia de explicit_denies en endpoint HTTP
    denied_token = create_access_token(
        user_id=320,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=20,
        contracted_modules=["catalog"],
        role_grants=["catalog.products.read"],
        temp_grants=["catalog.products.read"],
        explicit_denies=["catalog.products.read"],
        accessible_tenants=["tenant_rest_a"],
    )
    deny_resp = await async_client.get(
        "/api/v1/catalog/products",
        headers={
            "Authorization": f"Bearer {denied_token}",
            "X-Tenant-ID": "tenant_rest_a",
        },
    )
    assert deny_resp.status_code == 403
    assert deny_resp.json()["error_code"] == "EXPLICIT_DENY_GRANT"

    # 2. Módulo no contratado en el plan comercial (`analytics` no incluido en `contracted_modules`)
    uncontracted_token = create_access_token(
        user_id=321,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=10,
        contracted_modules=["catalog", "inventory"],
        role_grants=["analytics.executive_summary.read"],
        accessible_tenants=["tenant_rest_a"],
    )
    plan_resp = await async_client.post(
        "/api/v1/analytics/executive-summary",
        headers={
            "Authorization": f"Bearer {uncontracted_token}",
            "X-Tenant-ID": "tenant_rest_a",
        },
        json={
            "theoretical_cost": "100000",
            "opening_inventory": "50000",
            "purchases": "100000",
            "closing_inventory": "50000",
            "net_sales": "300000",
        },
    )
    assert plan_resp.status_code == 403
    assert plan_resp.json()["error_code"] == "MODULE_NOT_ENABLED_IN_PLAN"

    # 3. Incluso el Propietario del Holding (`is_holding_owner=True`) está acotado por los módulos de su Plan
    owner_decision = evaluate_effective_permission(
        required_permission="oppyfy.assistant.chat",
        contracted_modules=frozenset({"catalog", "inventory"}),
        role_grants=frozenset(),
        temp_grants=frozenset(),
        explicit_denies=frozenset(),
        actor_user_id=10,
        is_holding_owner=True,
        is_superuser_god=False,
    )
    assert owner_decision.allowed is False
    assert owner_decision.reason_code == "MODULE_NOT_ENABLED_IN_PLAN"
