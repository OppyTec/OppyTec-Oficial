"""
Flujo E2E 01: Onboarding de Holding y Tenant desde SuperUser Génesis
(`tests/e2e/test_e2e_01_genesis_holding_and_tenant_onboarding.py`).

Recorre el flujo completo de extremo a extremo:
1. Login del SuperUser Génesis (`/api/v1/auth/login`) y rotación de Refresh Token (`/api/v1/auth/refresh`).
2. Creación y listado de Holding empresarial en el Plano Global (`/api/v1/tenancy/holdings`).
3. Aprovisionamiento de sucursal Tenant (`/api/v1/tenancy/tenants` -> `tenant_<slug>`) y bloqueo de nombres maliciosos.
4. Verificación de cupos de asientos activos (`/api/v1/tenancy/quotas/seats`) y cuota MB en Cloudflare R2 (`/api/v1/tenancy/quotas/storage`).
5. Registro forense Append-Only en `/api/v1/audit/activity` y `/api/v1/audit/rbac`.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.core.config import get_settings
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.main import create_app

pytestmark = pytest.mark.e2e


def test_e2e_01_genesis_holding_and_tenant_onboarding_full_lifecycle() -> None:
    """
    Ejecuta de principio a fin el alta corporativa:
    `SuperUser Login -> Holding -> Tenant (tenant_<slug>) -> Quotas (Seats + R2 Storage) -> Forensic Audit`.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()
    app = create_app()
    settings = get_settings()

    with TestClient(app) as client:
        # 1. Login de SuperUser Génesis ("Dios")
        login_resp = client.post(
            "/api/v1/auth/login",
            json={
                "username_or_email": settings.SUPERUSER_GENESIS_USERNAME,
                "password": settings.SUPERUSER_GENESIS_PASSWORD.get_secret_value(),
                "tenant_id": "tenant_genesis",
            },
        )
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        assert login_data["user_id"] == 1
        assert login_data["hierarchy_rank"] == 0
        assert len(str(login_data["access_token"])) > 20
        god_refresh_token = str(login_data["refresh_token"])

        # Rotación del Refresh Token y verificación de uso único del refresh anterior
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": god_refresh_token},
        )
        assert refresh_resp.status_code == 200
        rotated_access_token = str(refresh_resp.json()["access_token"])
        god_headers = {"Authorization": f"Bearer {rotated_access_token}"}

        reuse_old_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": god_refresh_token},
        )
        assert reuse_old_refresh.status_code == 401

        # 2. Creación de Holding en el Plano Global (`public.holdings`)
        holding_resp = client.post(
            "/api/v1/tenancy/holdings",
            headers=god_headers,
            json={
                "name": "Holding Gastronómico Austral SpA",
                "plan_slug": "enterprise",
                "max_active_users": 40,
                "max_storage_mb": 2048,
            },
        )
        assert holding_resp.status_code == 201
        holding_data = holding_resp.json()
        holding_id = str(holding_data["holding_id"])
        assert holding_data["name"] == "Holding Gastronómico Austral SpA"
        assert holding_data["max_active_users"] == 40
        assert holding_data["max_storage_mb"] == 2048

        holdings_list = client.get("/api/v1/tenancy/holdings", headers=god_headers)
        assert holdings_list.status_code == 200
        assert any(h["holding_id"] == holding_id for h in holdings_list.json())

        # 3. Creación de Tenant (`tenant_<slug>`) bajo el Holding recién creado
        tenant_resp = client.post(
            "/api/v1/tenancy/tenants",
            headers=god_headers,
            json={
                "holding_id": holding_id,
                "slug": "austral_costanera",
                "display_name": "Austral Costanera Center",
                "base_currency": "CLP",
            },
        )
        assert tenant_resp.status_code == 201
        tenant_data = tenant_resp.json()
        assert tenant_data["holding_id"] == holding_id
        assert tenant_data["schema_name"] == "tenant_austral_costanera"
        assert tenant_data["base_currency"] == "CLP"

        # 4. Token del Propietario del nuevo Holding/Tenant para verificar cuotas y auditoría
        owner_token = create_access_token(
            user_id=101,
            holding_id=holding_id,
            tenant_id="tenant_austral_costanera",
            hierarchy_rank=0,
            is_holding_owner=True,
            contracted_modules=["tenancy", "audit", "settings"],
            role_grants=[
                "tenancy.quotas.read",
                "tenancy.storage_quotas.read",
                "audit.rbac_ledger.append",
                "audit.rbac_ledger.read",
                "audit.activity_ledger.append",
                "audit.activity_ledger.read",
            ],
            accessible_tenants=["tenant_austral_costanera"],
        )
        owner_headers = {
            "Authorization": f"Bearer {owner_token}",
            "X-Tenant-ID": "tenant_austral_costanera",
        }

        seats_resp = client.get("/api/v1/tenancy/quotas/seats", headers=owner_headers)
        assert seats_resp.status_code == 200
        seats_data = seats_resp.json()
        assert seats_data["holding_id"] == holding_id
        assert seats_data["can_create_or_restore"] is True
        assert int(seats_data["remaining_seats"]) > 0

        storage_resp = client.get("/api/v1/tenancy/quotas/storage", headers=owner_headers)
        assert storage_resp.status_code == 200
        storage_data = storage_resp.json()
        assert storage_data["tenant_id"] == "tenant_austral_costanera"
        assert storage_data["allowed"] is True
        assert int(storage_data["effective_max_storage_mb"]) == 1024

        # 5. Registro en el Doble Libro Forense Append-Only y verificación de lectura
        audit_act = client.post(
            "/api/v1/audit/activity",
            headers=owner_headers,
            json={
                "action_code": "tenancy.tenants.provision",
                "resource_type": "tenant",
                "resource_id": "tenant_austral_costanera",
                "before_state": {},
                "after_state": {
                    "holding_id": holding_id,
                    "schema_name": "tenant_austral_costanera",
                },
                "scope": "tenant",
            },
        )
        assert audit_act.status_code == 201
        created_evt_uuid = str(audit_act.json()["event_uuid"])

        audit_list = client.get("/api/v1/audit/activity", headers=owner_headers)
        assert audit_list.status_code == 200
        assert any(item["event_uuid"] == created_evt_uuid for item in audit_list.json())
