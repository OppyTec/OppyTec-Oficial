"""
Vector Red Team 01 (`tests/security_redteam/test_01_cross_tenant_and_holding_isolation_idor.py`):
- IDOR Horizontal entre sucursales (`tenant_rest_a` intentando leer/escribir en `tenant_rest_b`).
- IDOR Transversal entre Holdings (`holding_alpha` intentando operar sobre `holding_beta`).
- Spoofing de cabecera `X-Tenant-ID` fuera de `accessible_tenants` del JWT.
- Inyección SQL en nombres de esquema (`tenant_a; DROP SCHEMA public--`) bloqueada en `validate_tenant_schema_name` y en `POST /api/v1/tenancy/tenants`.
"""
from __future__ import annotations

import httpx
import pytest

from src.core.database import validate_tenant_schema_name
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.modules.tenancy.application.schema_provisioner import TenantSchemaProvisioner

pytestmark = pytest.mark.security_redteam


async def test_horizontal_cross_tenant_idor_blocked_across_endpoints(
    async_client: httpx.AsyncClient,
) -> None:
    """Un trabajador autenticado en `tenant_rest_a` recibe HTTP 403 al inyectar `X-Tenant-ID: tenant_rest_b`."""
    clear_revoked_sessions()
    get_rate_limiter().reset()

    token_tenant_a = create_access_token(
        user_id=101,
        holding_id="holding_alpha",
        tenant_id="tenant_rest_a",
        tenant_schema="tenant_rest_a",
        hierarchy_rank=20,
        role_grants=[
            "catalog.products.read",
            "catalog.products.create",
            "inventory.kardex.read",
            "tenancy.quotas.read",
        ],
        accessible_tenants=["tenant_rest_a"],
    )

    spoofed_headers = {
        "Authorization": f"Bearer {token_tenant_a}",
        "X-Tenant-ID": "tenant_rest_b",
    }

    for path in (
        "/api/v1/catalog/products",
        "/api/v1/inventory/kardex/movements",
        "/api/v1/tenancy/quotas/seats",
    ):
        resp = await async_client.get(path, headers=spoofed_headers)
        assert resp.status_code == 403, f"Expected 403 on {path}, got {resp.status_code}"
        body = resp.json()
        assert body["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"
        assert body["i18n_key"] == "tenancy:errors.cross_tenant_forbidden"


async def test_cross_holding_idor_and_global_plane_isolation(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Un Propietario de Holding (`holding_alpha`, `is_holding_owner=True`) solo puede acceder a sus sucursales
    autorizadas (`accessible_tenants`) y jamás a sucursales de `holding_beta` ni al Plano Global (`public.*`).
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    holding_alpha_owner_token = create_access_token(
        user_id=202,
        holding_id="holding_alpha",
        tenant_id="tenant_alpha_hq",
        hierarchy_rank=0,
        is_holding_owner=True,
        is_superuser_god=False,
        is_global_staff=False,
        contracted_modules=["catalog"],
        accessible_tenants=["tenant_alpha_hq", "tenant_alpha_branch2"],
    )

    # Acceso legítimo a su propia sucursal secundaria dentro de holding_alpha
    ok_resp = await async_client.get(
        "/api/v1/catalog/products",
        headers={
            "Authorization": f"Bearer {holding_alpha_owner_token}",
            "X-Tenant-ID": "tenant_alpha_branch2",
        },
    )
    assert ok_resp.status_code == 200

    # Intento de IDOR hacia una sucursal de otro Holding (`tenant_beta_hq`)
    cross_holding_resp = await async_client.get(
        "/api/v1/catalog/products",
        headers={
            "Authorization": f"Bearer {holding_alpha_owner_token}",
            "X-Tenant-ID": "tenant_beta_hq",
        },
    )
    assert cross_holding_resp.status_code == 403
    assert cross_holding_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # Intento de escalar al Plano Global (`public.holdings`) con token de cliente
    global_plane_resp = await async_client.get(
        "/api/v1/tenancy/holdings",
        headers={"Authorization": f"Bearer {holding_alpha_owner_token}"},
    )
    assert global_plane_resp.status_code == 403
    assert global_plane_resp.json()["error_code"] == "GLOBAL_STAFF_REQUIRED"


def test_schema_name_sql_injection_rejected_by_validator_and_provisioner() -> None:
    """Verifica que cualquier intento de inyección SQL en `schema_name` sea rechazado determinísticamente."""
    assert validate_tenant_schema_name("tenant_pollo_king_01") == "tenant_pollo_king_01"

    malicious_schemas = (
        "tenant_a; DROP SCHEMA public CASCADE--",
        'tenant_a"; SET ROLE postgres; --',
        "public",
        "pg_catalog",
        "tenant_UPPERCASE",
        "tenant_../etc/passwd",
        "tenant_a' OR '1'='1",
        "tenant_" + ("x" * 70),
    )
    for bad_schema in malicious_schemas:
        with pytest.raises(ValueError, match="TenantSchemaValidationError"):
            validate_tenant_schema_name(bad_schema)

    provisioner = TenantSchemaProvisioner()
    with pytest.raises(ValueError, match="TenantSchemaValidationError"):
        provisioner.provision_tenant_schema(
            holding_id="holding_01",
            legal_entity_id="le_01",
            tenant_id="tenant_evil",
            schema_name="tenant_a; DROP SCHEMA public--",
        )
