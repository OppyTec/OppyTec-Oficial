"""
Flujo E2E 05: Gestión de Roles, Delegación Temporal JIT, Asistente OppyFy y Trazabilidad Forense
(`tests/e2e/test_e2e_05_rbac_delegation_jit_and_forensic_trace.py`).

Recorre el flujo completo de seguridad RBAC, IA `OppyFy` e inmutabilidad de auditoría:
1. Listado y creación de rol personalizado respetando la Ley 1 de `hierarchy_rank` (`/api/v1/identity/roles`).
2. Emisión de concesión temporal Just-In-Time (`/api/v1/identity/grants/jit`).
3. Consulta de billetera de créditos sin caducidad (`/api/v1/oppyfy/credits/wallet`) y dominios RBAC (`/api/v1/oppyfy/rbac/domains`).
4. Chat con `OppyFy` verificando redacción dinámica `[REDACTED_COST]` cuando `can_view_costs=False` y visibilidad completa cuando `can_view_costs=True` (`/api/v1/oppyfy/chat`).
5. Verificación de telemetría global en `llm_request_logs` (`/api/v1/oppyfy/telemetry/logs`) y bloqueo HTTP 403 (`AUDIT_APPEND_ONLY_VIOLATION`) ante intento de `DELETE` en `/api/v1/audit/activity/{uuid}`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.core.config import get_settings
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.main import create_app

pytestmark = pytest.mark.e2e


def test_e2e_05_rbac_roles_jit_delegation_oppyfy_redaction_and_append_only_audit() -> None:
    """
    Verifica extremo a extremo la delegación RBAC/JIT, el asistente `OppyFy` con protección de costos y
    la bitácora forense Append-Only.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()
    app = create_app()
    settings = get_settings()

    admin_token = create_access_token(
        user_id=510,
        holding_id="holding_e2e_05",
        tenant_id="tenant_e2e_05",
        hierarchy_rank=10,
        contracted_modules=["settings", "oppyfy", "audit", "inventory"],
        role_grants=[
            "settings.roles.read",
            "settings.roles.manage",
            "settings.rbac.delegate_subordinates",
            "inventory.mermas.approve",
            "oppyfy.assistant.chat",
            "oppyfy.rbac_domains.read",
            "oppyfy.credits.read",
            "audit.rbac_ledger.append",
            "audit.rbac_ledger.read",
            "audit.activity_ledger.append",
            "audit.activity_ledger.read",
        ],
        accessible_tenants=["tenant_e2e_05"],
    )
    admin_headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Tenant-ID": "tenant_e2e_05",
    }

    with TestClient(app) as client:
        # 1. Listado de roles base y creación de un nuevo rol subordinado (`hierarchy_rank=25 > actor_rank=10`)
        roles_list = client.get("/api/v1/identity/roles", headers=admin_headers)
        assert roles_list.status_code == 200
        assert len(roles_list.json()) >= 1

        new_role_resp = client.post(
            "/api/v1/identity/roles",
            headers=admin_headers,
            json={
                "slug": "auditor_turno_noche",
                "name": "Auditor de Turno Nocturno",
                "hierarchy_rank": 25,
                "permissions": ["inventory.mermas.approve"],
            },
        )
        assert new_role_resp.status_code == 201
        assert new_role_resp.json()["slug"] == "auditor_turno_noche"

        # 2. Delegación temporal JIT hacia un subordinado (`target_rank=30 > actor_rank=10`)
        jit_resp = client.post(
            "/api/v1/identity/grants/jit",
            headers=admin_headers,
            json={
                "target_user_id": 599,
                "target_rank": 30,
                "permission_code": "inventory.mermas.approve",
                "effect": "ALLOW",
                "reason": "Cierre de inventario extraordinario fin de mes",
                "max_uses": 2,
            },
        )
        assert jit_resp.status_code == 201
        jit_data = jit_resp.json()
        assert jit_data["user_id"] == 599
        assert jit_data["permission_code"] == "inventory.mermas.approve"
        assert jit_data["max_uses"] == 2

        # 3. Billetera de créditos `OppyFy` y dominios RBAC
        wallet_resp = client.get("/api/v1/oppyfy/credits/wallet", headers=admin_headers)
        assert wallet_resp.status_code == 200
        assert Decimal(wallet_resp.json()["remaining_credits"]) == Decimal("87.50")

        domains_resp = client.get("/api/v1/oppyfy/rbac/domains", headers=admin_headers)
        assert domains_resp.status_code == 200
        assert len(domains_resp.json()) == 3

        # 4. Chat `OppyFy`: sin permiso de ver costos (`[REDACTED_COST]`) vs con permiso de ver costos
        chat_redacted = client.post(
            "/api/v1/oppyfy/chat",
            headers=admin_headers,
            json={
                "prompt_text": "Dame la receta estándar del Lomo Saltado",
                "target_subdomain_slug": "recipes_kitchen",
                "can_view_costs": False,
                "estimated_credit_cost": "3.00",
                "remaining_credits": "60.00",
            },
        )
        assert chat_redacted.status_code == 200
        assert "[REDACTED_COST]" in chat_redacted.json()["answer_text"]
        assert Decimal(chat_redacted.json()["remaining_credits"]) == Decimal("57.00")

        chat_visible = client.post(
            "/api/v1/oppyfy/chat",
            headers=admin_headers,
            json={
                "prompt_text": "Dame el costo unitario del Lomo Saltado",
                "target_subdomain_slug": "recipes_kitchen",
                "can_view_costs": True,
                "estimated_credit_cost": "3.00",
                "remaining_credits": "57.00",
            },
        )
        assert chat_visible.status_code == 200
        assert "CLP 1.450" in chat_visible.json()["answer_text"]
        assert Decimal(chat_visible.json()["remaining_credits"]) == Decimal("54.00")

        # 5. Verificación de `llm_request_logs` con SuperUser Génesis y bloqueo de DELETE en auditoría
        login_resp = client.post(
            "/api/v1/auth/login",
            json={
                "username_or_email": settings.SUPERUSER_GENESIS_USERNAME,
                "password": settings.SUPERUSER_GENESIS_PASSWORD.get_secret_value(),
                "tenant_id": "tenant_genesis",
            },
        )
        assert login_resp.status_code == 200
        god_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        telemetry_resp = client.get("/api/v1/oppyfy/telemetry/logs", headers=god_headers)
        assert telemetry_resp.status_code == 200
        assert len(telemetry_resp.json()) >= 2

        rbac_audit = client.post(
            "/api/v1/audit/rbac",
            headers=admin_headers,
            json={
                "target_user_id": 599,
                "action_type": "JIT_GRANT_ISSUED",
                "permission_or_role": "inventory.mermas.approve",
                "before_state": {"granted": False},
                "after_state": {"granted": True, "max_uses": 2},
                "scope": "tenant",
            },
        )
        assert rbac_audit.status_code == 201

        act_audit = client.post(
            "/api/v1/audit/activity",
            headers=admin_headers,
            json={
                "action_code": "oppyfy.assistant.chat",
                "resource_type": "oppyfy_session",
                "resource_id": "sess_510",
                "before_state": {"remaining_credits": "60.00"},
                "after_state": {"remaining_credits": "54.00"},
                "scope": "tenant",
            },
        )
        assert act_audit.status_code == 201
        evt_uuid = str(act_audit.json()["event_uuid"])

        delete_resp = client.delete(f"/api/v1/audit/activity/{evt_uuid}", headers=admin_headers)
        assert delete_resp.status_code == 403
        assert delete_resp.json()["error_code"] == "AUDIT_APPEND_ONLY_VIOLATION"
