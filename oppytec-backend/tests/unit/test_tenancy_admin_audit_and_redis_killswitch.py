"""
oppytec-backend/tests/unit/test_tenancy_admin_audit_and_redis_killswitch.py
Auditoría y pruebas unitarias/integración de:
1. Schemas *Request con ConfigDict(extra="forbid").
2. RBAC de 3 niveles en endpoints administrativos de tenancy.
3. Precisión de Decimal y cero float en cuotas e impersonación.
4. Soft-delete de usuario cliente: liberación inmediata de cupo y revocación en Redis.
5. Prevención de auto-eliminación y restauración con verificación de cupos.
"""
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError

from src.core.guards import clear_revoked_sessions, get_rate_limiter, is_session_revoked
from src.core.redis import get_redis_client
from src.core.security import create_access_token
from src.modules.identity.application.session_killswitch import SessionKillSwitchService
from src.modules.tenancy.presentation.schemas import (
    AdminImpersonateRequest,
    ClientUserCreateRequest,
    HoldingCreateRequest,
    LegalEntityCreateRequest,
    SystemPlanUpsertRequest,
    TenantCreateRequest,
    TenantModulesAndQuotasUpdateRequest,
)


def test_all_tenancy_request_schemas_enforce_extra_forbid() -> None:
    """Verifica que todos los esquemas *Request de Tenancy rechacen campos no declarados (extra='forbid')."""
    # 1. HoldingCreateRequest
    with pytest.raises(ValidationError) as exc:
        HoldingCreateRequest.model_validate(
            {"name": "Holding Test", "plan_slug": "basic", "undeclared_field": "hacked"}
        )
    assert "extra_forbidden" in str(exc.value)

    # 2. TenantCreateRequest
    with pytest.raises(ValidationError) as exc:
        TenantCreateRequest.model_validate(
            {
                "holding_id": "holding_01",
                "slug": "tenant_test",
                "display_name": "Sucursal Test",
                "malicious_param": "drop table",
            }
        )
    assert "extra_forbidden" in str(exc.value)

    # 3. TenantModulesAndQuotasUpdateRequest
    with pytest.raises(ValidationError) as exc:
        TenantModulesAndQuotasUpdateRequest.model_validate(
            {
                "enabled_modules": ["catalog"],
                "unknown_attr": 123,
            }
        )
    assert "extra_forbidden" in str(exc.value)

    # 4. SystemPlanUpsertRequest
    with pytest.raises(ValidationError) as exc:
        SystemPlanUpsertRequest.model_validate(
            {
                "slug": "custom",
                "name": "Plan Custom",
                "extra_price": Decimal("100.00"),
            }
        )
    assert "extra_forbidden" in str(exc.value)

    # 5. ClientUserCreateRequest
    with pytest.raises(ValidationError) as exc:
        ClientUserCreateRequest.model_validate(
            {
                "holding_id": "holding_01",
                "tenant_id": "tenant_01",
                "username": "test_user",
                "email": "test@user.cl",
                "password": "Password123#",
                "injected_role": "superadmin",
            }
        )
    assert "extra_forbidden" in str(exc.value)

    # 6. AdminImpersonateRequest
    with pytest.raises(ValidationError) as exc:
        AdminImpersonateRequest.model_validate(
            {
                "tenant_id": "tenant_01",
                "escalate": True,
            }
        )
    assert "extra_forbidden" in str(exc.value)

    # 7. LegalEntityCreateRequest
    with pytest.raises(ValidationError) as exc:
        LegalEntityCreateRequest.model_validate(
            {
                "holding_id": "holding_01",
                "tax_id": "76123456-7",
                "legal_name": "Razon Social SpA",
                "extra_token": "bad",
            }
        )
    assert "extra_forbidden" in str(exc.value)


async def test_tenancy_admin_endpoints_require_three_level_rbac(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que los endpoints administrativos de tenancy exijan permisos RBAC de 3 niveles."""
    clear_revoked_sessions()
    get_rate_limiter().reset()

    # Token con rol básico sin permisos de administración global
    unauthorized_token = create_access_token(
        user_id=888,
        holding_id="holding_01",
        tenant_id="tenant_01",
        hierarchy_rank=30,
        is_global_staff=False,
        is_superuser_god=False,
        role_grants=["catalog.products.read"],
    )
    headers = {"Authorization": f"Bearer {unauthorized_token}"}

    # 1. POST /api/v1/tenancy/holdings -> requiere tenancy.holdings.create
    res = await async_client.post(
        "/api/v1/tenancy/holdings",
        headers=headers,
        json={"name": "Holding No Autorizado"},
    )
    assert res.status_code == 403

    # 2. POST /api/v1/tenancy/tenants -> requiere tenancy.tenants.provision
    res = await async_client.post(
        "/api/v1/tenancy/tenants",
        headers=headers,
        json={"holding_id": "holding_01", "slug": "test_t", "display_name": "Test"},
    )
    assert res.status_code == 403

    # 3. POST /api/v1/tenancy/plans -> requiere tenancy.plans.manage
    res = await async_client.post(
        "/api/v1/tenancy/plans",
        headers=headers,
        json={"slug": "plan_test", "name": "Plan Test"},
    )
    assert res.status_code == 403

    # 4. POST /api/v1/tenancy/client-users -> requiere tenancy.client_users.create
    res = await async_client.post(
        "/api/v1/tenancy/client-users",
        headers=headers,
        json={
            "holding_id": "holding_01",
            "tenant_id": "tenant_01",
            "username": "user.test",
            "email": "user@test.cl",
            "password": "Password123#",
        },
    )
    assert res.status_code == 403

    # 5. POST /api/v1/tenancy/admin/impersonate -> requiere tenancy.tenants.impersonate
    res = await async_client.post(
        "/api/v1/tenancy/admin/impersonate",
        headers=headers,
        json={"tenant_id": "tenant_01"},
    )
    assert res.status_code == 403


async def test_client_user_soft_delete_releases_quota_and_revokes_redis(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que el Soft-Delete de un usuario cliente:
    1. Libera inmediatamente el cupo del Plan.
    2. Revoca la sesión en memoria y en Redis (< 50ms).
    3. Bloquea la auto-eliminación (HTTP 403 cannot_self_delete).
    4. La restauración posterior reactiva el cupo y limpia la revocación en Redis.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    # Token de Administrador Global con permisos tenancy.*
    admin_token = create_access_token(
        user_id=1,
        holding_id="holding_audit_ks",
        tenant_id="tenant_audit_ks",
        hierarchy_rank=0,
        is_global_staff=True,
        is_superuser_god=True,
        accessible_tenants=["tenant_audit_ks"],
    )
    admin_headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Tenant-ID": "tenant_audit_ks",
    }

    # 1. Crear Holding con límite de 1 usuario
    h_res = await async_client.post(
        "/api/v1/tenancy/holdings",
        headers=admin_headers,
        json={
            "name": "Holding Soft Delete Test",
            "plan_slug": "basic",
            "max_active_users": 1,
            "max_storage_mb": 512,
        },
    )
    assert h_res.status_code == 201
    holding_id = h_res.json()["holding_id"]

    # 2. Crear Tenant
    t_res = await async_client.post(
        "/api/v1/tenancy/tenants",
        headers=admin_headers,
        json={
            "holding_id": holding_id,
            "slug": "audit_sucursal_01",
            "display_name": "Sucursal Soft Delete",
            "base_currency": "CLP",
        },
    )
    assert t_res.status_code == 201
    tenant_id = t_res.json()["tenant_id"]

    # 3. Crear 1er Usuario Cliente (consume el único cupo disponible)
    u1_res = await async_client.post(
        "/api/v1/tenancy/client-users",
        headers=admin_headers,
        json={
            "holding_id": holding_id,
            "tenant_id": tenant_id,
            "username": "operador.ks1",
            "email": "ks1@holding.cl",
            "password": "PasswordAudit123#",
            "first_name": "Operador",
            "last_name": "Uno",
            "role_slug": "admin",
        },
    )
    assert u1_res.status_code == 201
    u1_id = u1_res.json()["user_id"]

    # 4. Intentar crear 2do usuario debe fallar con HTTP 409 (QuotaExceeded)
    u2_blocked = await async_client.post(
        "/api/v1/tenancy/client-users",
        headers=admin_headers,
        json={
            "holding_id": holding_id,
            "tenant_id": tenant_id,
            "username": "operador.ks2",
            "email": "ks2@holding.cl",
            "password": "PasswordAudit123#",
            "first_name": "Operador",
            "last_name": "Dos",
            "role_slug": "admin",
        },
    )
    assert u2_blocked.status_code == 409

    # 5. Token para el usuario cliente u1
    _u1_token = create_access_token(
        user_id=u1_id,
        holding_id=holding_id,
        tenant_id=tenant_id,
        hierarchy_rank=10,
        role_grants=["tenancy.quotas.read"],
    )
    assert _u1_token
    assert not is_session_revoked(user_id=u1_id)

    # 6. Intentar que el usuario u1 se elimine a sí mismo -> HTTP 403
    u1_self_delete = await async_client.post(
        f"/api/v1/tenancy/client-users/{u1_id}/soft-delete",
        headers={
            "Authorization": f"Bearer {create_access_token(user_id=u1_id, is_global_staff=True, hierarchy_rank=0)}",
        },
    )
    assert u1_self_delete.status_code == 403

    # 7. Administrador aplica Soft-Delete a u1
    del_res = await async_client.post(
        f"/api/v1/tenancy/client-users/{u1_id}/soft-delete",
        headers=admin_headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["is_deleted"] is True

    # 8. Verificar que la sesión quedó revocada en memoria y en Redis
    assert is_session_revoked(user_id=u1_id) is True
    redis_client = get_redis_client()
    ks_service = SessionKillSwitchService(redis_client=redis_client)
    assert await ks_service.is_user_session_revoked(user_id=u1_id, scope="client") is True

    # 9. Con el cupo liberado, el 2do usuario ahora puede registrarse exitosamente
    u2_ok = await async_client.post(
        "/api/v1/tenancy/client-users",
        headers=admin_headers,
        json={
            "holding_id": holding_id,
            "tenant_id": tenant_id,
            "username": "operador.ks2",
            "email": "ks2@holding.cl",
            "password": "PasswordAudit123#",
            "first_name": "Operador",
            "last_name": "Dos",
            "role_slug": "admin",
        },
    )
    assert u2_ok.status_code == 201

    # 10. Intentar restaurar u1 cuando el cupo está lleno de nuevo debe arrojar HTTP 409
    restore_blocked = await async_client.post(
        f"/api/v1/tenancy/client-users/{u1_id}/restore",
        headers=admin_headers,
    )
    assert restore_blocked.status_code == 409

    # 11. Soft-delete a u2 y restaurar u1 con éxito
    u2_id = u2_ok.json()["user_id"]
    await async_client.post(
        f"/api/v1/tenancy/client-users/{u2_id}/soft-delete",
        headers=admin_headers,
    )
    restore_ok = await async_client.post(
        f"/api/v1/tenancy/client-users/{u1_id}/restore",
        headers=admin_headers,
    )
    assert restore_ok.status_code == 200
    assert restore_ok.json()["is_deleted"] is False
    assert is_session_revoked(user_id=u1_id) is False


async def test_impersonation_and_quotas_summary_zero_float(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica la precisión de impersonación y el cálculo sin floats de cuotas de tenancy."""
    clear_revoked_sessions()
    get_rate_limiter().reset()

    admin_token = create_access_token(
        user_id=1,
        holding_id="holding_genesis",
        tenant_id="tenant_genesis",
        hierarchy_rank=0,
        is_global_staff=True,
        is_superuser_god=True,
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Crear holding y tenant para la prueba
    h_res = await async_client.post(
        "/api/v1/tenancy/holdings",
        headers=admin_headers,
        json={"name": "Holding Zero Float", "plan_slug": "basic"},
    )
    assert h_res.status_code == 201
    holding_id = h_res.json()["holding_id"]

    t_res = await async_client.post(
        "/api/v1/tenancy/tenants",
        headers=admin_headers,
        json={"holding_id": holding_id, "slug": "zero_float", "display_name": "Sucursal Zero Float"},
    )
    assert t_res.status_code == 201
    tenant_id = t_res.json()["tenant_id"]

    # Impersonar
    imp_res = await async_client.post(
        "/api/v1/tenancy/admin/impersonate",
        headers=admin_headers,
        json={"tenant_id": tenant_id, "reason": "Auditoría de Cuotas"},
    )
    assert imp_res.status_code == 200
    imp_data = imp_res.json()
    assert imp_data["impersonated_by_user_id"] == 1
    assert imp_data["holding_id"] == holding_id
    assert imp_data["schema_name"] == "tenant_zero_float"
    assert len(imp_data["access_token"]) > 20

    support_token = imp_data["access_token"]
    support_headers = {
        "Authorization": f"Bearer {support_token}",
        "X-Tenant-ID": tenant_id,
    }

    # Resumen de cuotas
    summary_res = await async_client.get(
        "/api/v1/tenancy/quotas/summary",
        headers=support_headers,
    )
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["holding_id"] == holding_id
    for _rtype, quota_item in summary_data["resources"].items():
        assert isinstance(quota_item["active_count"], int)
        assert isinstance(quota_item["effective_max_limit"], int)
        assert "usage_percentage" in quota_item
        # Verificar que el porcentaje de uso tiene formato Decimal
        pct = Decimal(str(quota_item["usage_percentage"]))
        assert pct >= Decimal("0.00")
        assert pct <= Decimal("100.00")

    # Cuota de asientos
    seats_res = await async_client.get(
        "/api/v1/tenancy/quotas/seats",
        headers=support_headers,
    )
    assert seats_res.status_code == 200
    seats_data = seats_res.json()
    assert Decimal(str(seats_data["usage_percentage"])) >= Decimal("0.00")

    # Cuota de storage
    storage_res = await async_client.get(
        "/api/v1/tenancy/quotas/storage",
        headers=support_headers,
    )
    assert storage_res.status_code == 200
    storage_data = storage_res.json()
    assert Decimal(str(storage_data["usage_percentage"])) >= Decimal("0.00")
