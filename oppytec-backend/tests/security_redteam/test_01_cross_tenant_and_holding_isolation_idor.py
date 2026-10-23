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


async def test_client_user_cannot_manipulate_or_escalate_quotas_via_mass_assignment_or_cross_holding_idor(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Certificación de Defensa en Profundidad:
    1. Ningún usuario cliente puede modificar cuotas en `PUT /api/v1/tenancy/tenants/{id}/modules-and-quotas`
       (bloqueo HTTP 403 GLOBAL_STAFF_REQUIRED).
    2. Ningún usuario cliente puede alterar planes comerciales en `POST /api/v1/tenancy/plans`
       (bloqueo HTTP 403 GLOBAL_STAFF_REQUIRED).
    3. Ningún usuario cliente puede inyectar overrides de cuota o campos no permitidos mediante Mass Assignment
       (rechazo determinista HTTP 422 por ConfigDict(extra="forbid")).
    4. Ningún usuario cliente puede espiar ni manipular cuotas de otro Holding mediante spoofing de X-Tenant-ID
       (bloqueo HTTP 403 CROSS_TENANT_ACCESS_VIOLATION).
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    # Usuario Cliente (Administrador de sucursal en holding_alpha, SIN rol de Global Staff)
    client_admin_token = create_access_token(
        user_id=505,
        holding_id="holding_alpha",
        tenant_id="tenant_alpha_hq",
        tenant_schema="tenant_alpha_hq",
        hierarchy_rank=10,
        is_holding_owner=False,
        is_superuser_god=False,
        is_global_staff=False,
        role_grants=[
            "catalog.products.read",
            "catalog.products.create",
            "tenancy.quotas.read",
            "tenancy.storage_quotas.read",
        ],
        accessible_tenants=["tenant_alpha_hq"],
    )

    client_headers = {
        "Authorization": f"Bearer {client_admin_token}",
        "X-Tenant-ID": "tenant_alpha_hq",
    }

    # 1. Intento de elevar cuotas directamente via PUT modules-and-quotas -> HTTP 403
    escalate_quota_resp = await async_client.put(
        "/api/v1/tenancy/tenants/tenant_alpha_hq/modules-and-quotas",
        headers=client_headers,
        json={
            "enabled_modules": ["catalog", "inventory", "operations", "oppy_ai"],
            "custom_max_users_override": 99999,
            "custom_storage_mb_override": 1048576,
        },
    )
    assert escalate_quota_resp.status_code == 403
    assert escalate_quota_resp.json()["error_code"] == "GLOBAL_STAFF_REQUIRED"

    # 2. Intento de manipular el catálogo global de planes comerciales -> HTTP 403
    manipulate_plan_resp = await async_client.post(
        "/api/v1/tenancy/plans",
        headers=client_headers,
        json={
            "slug": "unlimited_hacked_plan",
            "name": "Plan Ilimitado Pirata",
            "max_active_users": 50000,
            "max_products": 1000000,
            "max_storage_mb": 1048576,
        },
    )
    assert manipulate_plan_resp.status_code == 403
    assert manipulate_plan_resp.json()["error_code"] == "GLOBAL_STAFF_REQUIRED"

    # 3. Intento de Mass Assignment inyectando campos de cuotas en endpoints accesibles -> HTTP 422
    mass_assignment_resp = await async_client.post(
        "/api/v1/catalog/products",
        headers=client_headers,
        json={
            "sku": "SKU-OVERRIDE-01",
            "nombre": "Aceite Malicioso",
            "unidad_compra": "bidon",
            "unidad_almacen": "l",
            "unidad_receta": "ml",
            "factor_compra_a_almacen": "5",
            "factor_almacen_a_receta": "1000",
            "costo_compra_neto": "10000",
            "custom_max_products_override": 999999,  # Ataque de Mass Assignment
            "plan_slug": "enterprise_god_mode",       # Intento de bypass de cuotas
        },
    )
    assert mass_assignment_resp.status_code == 422
    assert "extra_forbidden" in str(mass_assignment_resp.json())

    # 4. Intento de IDOR Cross-Holding sobre el resumen de cuotas -> HTTP 403
    cross_holding_quota_resp = await async_client.get(
        "/api/v1/tenancy/quotas/summary",
        headers={
            "Authorization": f"Bearer {client_admin_token}",
            "X-Tenant-ID": "tenant_beta_branch1",  # Sucursal de otro Holding
        },
    )
    assert cross_holding_quota_resp.status_code == 403
    assert cross_holding_quota_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

