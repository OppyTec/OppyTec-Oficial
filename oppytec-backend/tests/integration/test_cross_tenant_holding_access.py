"""
Pruebas de Integración de Acceso Multi-Sucursal dentro de un Holding (`tests/integration/test_cross_tenant_holding_access.py`).

Verifica:
1. Un Propietario de Holding o personal transversal con `accessible_tenants=["tenant_rest_a", "tenant_hotel_b"]`
   puede operar en ambas sucursales (`tenant_rest_a` y `tenant_hotel_b`) alternando la cabecera `X-Tenant-ID`.
2. Cualquier petición hacia una sucursal ajena al Holding (`tenant_external_c`) es bloqueada en el acto con
   HTTP 403 (`CrossTenantAccessError` / `CROSS_TENANT_ACCESS_VIOLATION`).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.core.exceptions import CrossTenantAccessError
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.main import create_app
from src.modules.tenancy.application.schema_provisioner import TenantSchemaProvisioner

pytestmark = pytest.mark.integration


def test_holding_owner_and_transversal_staff_cross_tenant_access_and_external_rejection() -> None:
    """
    Verifica que un token con `accessible_tenants=["tenant_rest_a", "tenant_hotel_b"]` opere
    válidamente en `tenant_rest_a` y `tenant_hotel_b` vía `X-Tenant-ID`, pero reciba HTTP 403
    (`CrossTenantAccessError`) al intentar acceder a `tenant_external_c`.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    provisioner = TenantSchemaProvisioner()
    provisioner.provision_tenant_schema(
        holding_id="holding_gastro_sur",
        legal_entity_id="le_rest_a",
        tenant_id="tenant_rest_a",
        schema_name="tenant_rest_a",
    )
    provisioner.provision_tenant_schema(
        holding_id="holding_gastro_sur",
        legal_entity_id="le_hotel_b",
        tenant_id="tenant_hotel_b",
        schema_name="tenant_hotel_b",
    )
    provisioner.provision_tenant_schema(
        holding_id="holding_external_rival",
        legal_entity_id="le_external_c",
        tenant_id="tenant_external_c",
        schema_name="tenant_external_c",
    )

    # El provisioner permite acceso a las 2 sucursales del mismo Holding y bloquea la sucursal externa
    assert (
        provisioner.assert_same_holding_access(
            user_holding_id="holding_gastro_sur",
            target_tenant_id="tenant_rest_a",
        ).schema_name
        == "tenant_rest_a"
    )
    assert (
        provisioner.assert_same_holding_access(
            user_holding_id="holding_gastro_sur",
            target_tenant_id="tenant_hotel_b",
        ).schema_name
        == "tenant_hotel_b"
    )
    with pytest.raises(CrossTenantAccessError):
        provisioner.assert_same_holding_access(
            user_holding_id="holding_gastro_sur",
            target_tenant_id="tenant_external_c",
        )

    app = create_app()

    # Emitimos token de Holding Owner / Chef Corporativo transversal para `tenant_rest_a` y `tenant_hotel_b`
    holding_token = create_access_token(
        user_id=501,
        holding_id="holding_gastro_sur",
        tenant_id="tenant_rest_a",
        hierarchy_rank=10,
        is_holding_owner=True,
        contracted_modules=["catalog", "tenancy", "analytics"],
        role_grants=[
            "catalog.products.read",
            "tenancy.quotas.read",
            "tenancy.storage_quotas.read",
            "analytics.executive_summary.read",
        ],
        accessible_tenants=["tenant_rest_a", "tenant_hotel_b"],
    )

    with TestClient(app) as client:
        # 1. Operación en `tenant_rest_a` -> HTTP 200
        resp_rest_a = client.get(
            "/api/v1/tenancy/quotas/storage",
            headers={
                "Authorization": f"Bearer {holding_token}",
                "X-Tenant-ID": "tenant_rest_a",
            },
        )
        assert resp_rest_a.status_code == 200
        assert resp_rest_a.json()["tenant_id"] == "tenant_rest_a"

        # 2. Operación en `tenant_hotel_b` con el mismo token transversal -> HTTP 200
        resp_hotel_b = client.get(
            "/api/v1/tenancy/quotas/storage",
            headers={
                "Authorization": f"Bearer {holding_token}",
                "X-Tenant-ID": "tenant_hotel_b",
            },
        )
        assert resp_hotel_b.status_code == 200
        assert resp_hotel_b.json()["tenant_id"] == "tenant_hotel_b"

        exec_hotel_b = client.get(
            "/api/v1/analytics/executive-summary",
            headers={
                "Authorization": f"Bearer {holding_token}",
                "X-Tenant-ID": "tenant_hotel_b",
            },
        )
        assert exec_hotel_b.status_code == 200

        # 3. Intento de acceder a `tenant_external_c` (fuera del Holding) -> HTTP 403 (`CrossTenantAccessError`)
        for forbidden_endpoint in (
            "/api/v1/catalog/products",
            "/api/v1/tenancy/quotas/storage",
            "/api/v1/analytics/executive-summary",
        ):
            forbidden_resp = client.get(
                forbidden_endpoint,
                headers={
                    "Authorization": f"Bearer {holding_token}",
                    "X-Tenant-ID": "tenant_external_c",
                },
            )
            assert forbidden_resp.status_code == 403
            body = forbidden_resp.json()
            assert body["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"
            assert body["status"] == 403
