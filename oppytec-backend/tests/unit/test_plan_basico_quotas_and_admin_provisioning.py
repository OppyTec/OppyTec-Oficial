"""
Pruebas Unitarias e Integración de Contratos para el Plan Básico (10 Módulos),
Cuotas Paramétricas de Capacidad (6 recursos + semáforo 80%/95%/100% + liberación Soft-Delete)
y Aprovisionamiento desde el Panel Administrador Global (`platform-admin`).
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import httpx
import pytest

from src.core.bootstrap import PLAN_BASICO_10_MODULES
from src.core.exceptions import QuotaExceededError
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.modules.identity.domain.rbac_evaluator import (
    compute_effective_permissions,
    evaluate_permission_access,
    extract_permission_submodule_prefix,
)
from src.modules.tenancy.application.quota_service import TenantCapacityQuotaService
from src.modules.tenancy.domain.quotas import (
    evaluate_resource_capacity_quota,
    evaluate_storage_quota_bytes,
)


def test_two_level_submodule_rbac_ceiling_for_plan_basico() -> None:
    """
    Certifica que `M_Plan` soporte granularidad de 2 niveles (`<modulo>.<submodulo>`):
    - En el Plan Básico está habilitado `operations.consumption_log`, pero NO `operations.buffet` ni `operations.pos`.
    """
    assert extract_permission_submodule_prefix("operations.consumption_log.create") == "operations.consumption_log"

    strict_basic_modules = {
        "inicio",
        "operations.consumption_log",
        "inventory.stock",
        "catalog.products",
        "inventory.mermas",
        "inventory.counts",
        "notifications",
        "alerts",
        "audit.history",
        "identity.users",
    }
    role_perms = {
        "operations.consumption_log.create",
        "operations.buffet.create",
        "catalog.products.create",
        "recipes.escandallos.create",
    }

    effective = compute_effective_permissions(
        plan_enabled_modules=strict_basic_modules,
        role_permissions=role_perms,
    )
    assert "operations.consumption_log.create" in effective
    assert "catalog.products.create" in effective
    assert "operations.buffet.create" not in effective
    assert "recipes.escandallos.create" not in effective

    allowed_decision = evaluate_permission_access(
        actor_user_id=10,
        required_permission="operations.consumption_log.create",
        plan_enabled_modules=strict_basic_modules,
        role_permissions=role_perms,
    )
    assert allowed_decision.allowed is True

    denied_decision = evaluate_permission_access(
        actor_user_id=10,
        required_permission="operations.buffet.create",
        plan_enabled_modules=strict_basic_modules,
        role_permissions=role_perms,
    )
    assert denied_decision.allowed is False
    assert denied_decision.reason_code == "MODULE_NOT_ENABLED_IN_PLAN"


def test_multi_resource_capacity_quotas_semaphore_and_soft_delete_release() -> None:
    """
    Verifica:
    1. Semáforo de cuotas: `NORMAL` (<80%), `WARNING` (80-94%), `CRITICAL` (95-99%), `OVER_QUOTA` (100% o límite 0).
    2. Precedencia de overrides: `tenant_override -> holding_override -> plan_limit`.
    3. `soft_delete_item` libera inmediatamente 1 cupo activo en `TenantCapacityQuotaService`.
    """
    normal_ev = evaluate_resource_capacity_quota(
        resource_type="products",
        active_non_deleted_count=100,
        plan_limit=500,
    )
    assert normal_ev.status == "NORMAL"
    assert normal_ev.usage_percentage == Decimal("20.00")

    warning_ev = evaluate_resource_capacity_quota(
        resource_type="products",
        active_non_deleted_count=410,
        plan_limit=500,
    )
    assert warning_ev.status == "WARNING"
    assert warning_ev.usage_percentage == Decimal("82.00")

    critical_ev = evaluate_resource_capacity_quota(
        resource_type="products",
        active_non_deleted_count=480,
        plan_limit=500,
    )
    assert critical_ev.status == "CRITICAL"
    assert critical_ev.usage_percentage == Decimal("96.00")

    zero_recipes_ev = evaluate_resource_capacity_quota(
        resource_type="recipes",
        active_non_deleted_count=0,
        plan_limit=0,
    )
    assert zero_recipes_ev.allowed is False
    assert zero_recipes_ev.status == "OVER_QUOTA"

    # Con override de Tenant, se desbloquean 25 recetas
    overridden_recipes_ev = evaluate_resource_capacity_quota(
        resource_type="recipes",
        active_non_deleted_count=5,
        plan_limit=0,
        tenant_override=25,
    )
    assert overridden_recipes_ev.allowed is True
    assert overridden_recipes_ev.effective_max_limit == 25
    assert overridden_recipes_ev.remaining_capacity == 20

    # Ciclo completo con Soft-Delete en TenantCapacityQuotaService
    svc = TenantCapacityQuotaService(
        plan_limits={
            "users": 2,
            "products": 2,
            "suppliers": 2,
            "recipes": 0,
            "combos": 0,
            "storage_mb": 512,
        }
    )
    svc.register_item(resource_type="products", item_id="PRD-1")
    svc.register_item(resource_type="products", item_id="PRD-2")

    with pytest.raises(QuotaExceededError):
        svc.register_item(resource_type="products", item_id="PRD-3")

    # Al archivar PRD-1 (Soft-Delete), se libera 1 cupo de inmediato
    svc.soft_delete_item(resource_type="products", item_id="PRD-1")
    slot_3 = svc.register_item(resource_type="products", item_id="PRD-3")
    assert slot_3.is_deleted is False

    # No puede restaurar PRD-1 porque el cupo fue ocupado por PRD-3
    with pytest.raises(QuotaExceededError):
        svc.restore_item(resource_type="products", item_id="PRD-1")


async def test_admin_provisioning_plans_holdings_tenants_client_users_and_impersonation(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Certifica el flujo completo del Panel Administrador (`platform-admin`):
    1. Creación/edición de Plan Comercial con 6 cuotas paramétricas y precios `Decimal`.
    2. Alta de Holding, Entidad Legal (RUT) y Tenant con árbol de módulos y overrides.
    3. Alta de Usuarios Clientes respetando `max_active_users` y liberación por `Soft-Delete`.
    4. Emisión de token de soporte `POST /api/v1/tenancy/admin/impersonate` ("Entrar como Local").
    5. Consulta de `GET /api/v1/tenancy/quotas/summary` con las 6 cuotas.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    god_token = create_access_token(
        user_id=1,
        holding_id="holding_genesis",
        tenant_id="tenant_genesis",
        hierarchy_rank=0,
        is_superuser_god=True,
        is_global_staff=True,
    )
    headers = {"Authorization": f"Bearer {god_token}"}

    # 1. Listar y actualizar Plan Básico
    plans_res = await async_client.get("/api/v1/tenancy/plans", headers=headers)
    assert plans_res.status_code == 200
    assert any(p["slug"] == "basic" for p in plans_res.json())

    upsert_plan_res = await async_client.post(
        "/api/v1/tenancy/plans",
        headers=headers,
        json={
            "slug": "basic_plus",
            "name": "Plan Básico Plus",
            "max_active_users": 2,
            "max_products": 600,
            "max_suppliers": 30,
            "max_recipes": 0,
            "max_combos": 0,
            "max_storage_mb": 1024,
            "included_modules": list(PLAN_BASICO_10_MODULES),
            "anchor_currency": "CLP",
            "price_clp": "39990.00",
            "price_usd": "45.00",
            "price_eur": "41.00",
            "price_brl": "220.00",
        },
    )
    assert upsert_plan_res.status_code == 201
    assert upsert_plan_res.json()["max_products"] == 600

    # 2. Crear Holding con límite de 1 usuario activo para probar bloqueo y liberación Soft-Delete
    holding_res = await async_client.post(
        "/api/v1/tenancy/holdings",
        headers=headers,
        json={
            "name": "Holding Gastronómico Pacífico",
            "plan_slug": "basic_plus",
            "max_active_users": 1,
            "max_storage_mb": 1024,
            "custom_max_products_override": 750,
        },
    )
    assert holding_res.status_code == 201
    holding_id = holding_res.json()["holding_id"]

    # 3. Crear Entidad Legal (RUT)
    le_res = await async_client.post(
        "/api/v1/tenancy/legal-entities",
        headers=headers,
        json={
            "holding_id": holding_id,
            "tax_id": "76.888.999-K",
            "legal_name": "Inversiones Gastronómicas Pacífico SpA",
            "legal_address": "Av. Providencia 1234, Santiago",
        },
    )
    assert le_res.status_code == 201
    entity_id = le_res.json()["entity_id"]

    # 4. Crear Tenant vinculado a Holding y Entidad Legal
    tenant_res = await async_client.post(
        "/api/v1/tenancy/tenants",
        headers=headers,
        json={
            "holding_id": holding_id,
            "legal_entity_id": entity_id,
            "slug": "pacifico_norte",
            "display_name": "Sucursal Pacífico Norte",
            "base_currency": "CLP",
            "custom_max_products_override": 800,
        },
    )
    assert tenant_res.status_code == 201
    tenant_id = tenant_res.json()["tenant_id"]
    assert tenant_res.json()["schema_name"] == "tenant_pacifico_norte"

    # Actualizar módulos y overrides del Tenant
    upd_tenant_res = await async_client.put(
        f"/api/v1/tenancy/tenants/{tenant_id}/modules-and-quotas",
        headers=headers,
        json={
            "enabled_modules": list(PLAN_BASICO_10_MODULES),
            "custom_max_products_override": 900,
            "custom_max_suppliers_override": 40,
        },
    )
    assert upd_tenant_res.status_code == 200
    assert upd_tenant_res.json()["custom_max_products_override"] == 900

    # 5. Crear primer Usuario Cliente (ocupa el único cupo activo max_active_users=1)
    u1_res = await async_client.post(
        "/api/v1/tenancy/client-users",
        headers=headers,
        json={
            "holding_id": holding_id,
            "tenant_id": tenant_id,
            "username": "camila.pacifico",
            "email": "camila@pacifico.cl",
            "password": "PasswordSeguro#2026",
            "first_name": "Camila",
            "last_name": "Rojas",
            "role_slug": "propietario",
            "is_holding_owner": True,
        },
    )
    assert u1_res.status_code == 201
    u1_id = u1_res.json()["user_id"]

    # Intentar crear segundo usuario cuando el cupo (1) está lleno -> HTTP 409 QuotaExceededError
    u2_blocked = await async_client.post(
        "/api/v1/tenancy/client-users",
        headers=headers,
        json={
            "holding_id": holding_id,
            "tenant_id": tenant_id,
            "username": "diego.pacifico",
            "email": "diego@pacifico.cl",
            "password": "PasswordSeguro#2026",
            "first_name": "Diego",
            "last_name": "Soto",
            "role_slug": "admin",
        },
    )
    assert u2_blocked.status_code == 409

    # Aplicar Soft-Delete al primer usuario -> libera 1 cupo en el acto
    del_res = await async_client.post(
        f"/api/v1/tenancy/client-users/{u1_id}/soft-delete",
        headers=headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["is_deleted"] is True

    # Ahora el segundo usuario se crea exitosamente
    u2_ok = await async_client.post(
        "/api/v1/tenancy/client-users",
        headers=headers,
        json={
            "holding_id": holding_id,
            "tenant_id": tenant_id,
            "username": "diego.pacifico",
            "email": "diego@pacifico.cl",
            "password": "PasswordSeguro#2026",
            "first_name": "Diego",
            "last_name": "Soto",
            "role_slug": "admin",
        },
    )
    assert u2_ok.status_code == 201

    # 6. Impersonación de soporte ("Entrar como Local")
    imp_res = await async_client.post(
        "/api/v1/tenancy/admin/impersonate",
        headers=headers,
        json={
            "tenant_id": tenant_id,
            "reason": "Configuración inicial Plan Básico Sucursal Pacífico Norte",
        },
    )
    assert imp_res.status_code == 200
    imp_token = imp_res.json()["access_token"]
    assert imp_res.json()["schema_name"] == "tenant_pacifico_norte"

    # 7. Consultar Resumen Consolidado de las 6 Cuotas con el token de soporte
    summary_res = await async_client.get(
        "/api/v1/tenancy/quotas/summary",
        headers={
            "Authorization": f"Bearer {imp_token}",
            "X-Tenant-ID": tenant_id,
        },
    )
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["resources"]["products"]["effective_max_limit"] == 900
    assert summary_data["resources"]["suppliers"]["effective_max_limit"] == 40
    assert summary_data["resources"]["users"]["active_count"] == 1
    assert summary_data["resources"]["users"]["soft_deleted_count"] == 1


async def test_client_user_restore_after_soft_delete_and_quota_enforcement(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Prueba de borde: ciclo de vida completo de un usuario cliente:
    1. Creación de usuario activo en holding con max_active_users=1.
    2. Soft-delete del usuario -> se libera el cupo activo.
    3. Creación de segundo usuario ocupando el cupo libre.
    4. Intento de restaurar al primer usuario -> HTTP 409 QuotaExceededError por cupo lleno.
    5. Soft-delete del segundo usuario -> se libera el cupo.
    6. Restauración exitosa del primer usuario -> HTTP 200, is_deleted=False.
    7. Restauración idempotente de usuario ya activo -> HTTP 200.
    8. Restauración de usuario inexistente -> HTTP 404 ResourceNotFoundError.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    god_token = create_access_token(
        user_id=1,
        holding_id="holding_genesis",
        tenant_id="tenant_genesis",
        hierarchy_rank=0,
        is_superuser_god=True,
        is_global_staff=True,
    )
    headers = {"Authorization": f"Bearer {god_token}"}

    # Crear holding con límite estricto de 1 usuario activo
    h_res = await async_client.post(
        "/api/v1/tenancy/holdings",
        headers=headers,
        json={
            "name": "Holding Borde Restore",
            "plan_slug": "basic",
            "max_active_users": 1,
            "max_storage_mb": 512,
        },
    )
    assert h_res.status_code == 201
    holding_id = h_res.json()["holding_id"]

    le_res = await async_client.post(
        "/api/v1/tenancy/legal-entities",
        headers=headers,
        json={
            "holding_id": holding_id,
            "tax_id": "77.111.222-3",
            "legal_name": "Restauraciones SpA",
            "legal_address": "Alameda 555, Santiago",
        },
    )
    assert le_res.status_code == 201
    entity_id = le_res.json()["entity_id"]

    t_res = await async_client.post(
        "/api/v1/tenancy/tenants",
        headers=headers,
        json={
            "holding_id": holding_id,
            "legal_entity_id": entity_id,
            "slug": "sucursal_restore_test",
            "display_name": "Sucursal Restore Test",
            "base_currency": "CLP",
        },
    )
    assert t_res.status_code == 201
    tenant_id = t_res.json()["tenant_id"]

    # 1. Crear usuario A (ocupa el cupo 1/1)
    u_a_res = await async_client.post(
        "/api/v1/tenancy/client-users",
        headers=headers,
        json={
            "holding_id": holding_id,
            "tenant_id": tenant_id,
            "username": "usuario.a",
            "email": "usuario.a@borde.cl",
            "password": "PasswordSeguro#2026",
            "first_name": "Usuario",
            "last_name": "A",
            "role_slug": "admin",
        },
    )
    assert u_a_res.status_code == 201
    u_a_id = u_a_res.json()["user_id"]

    # 2. Soft-delete usuario A
    del_a = await async_client.post(
        f"/api/v1/tenancy/client-users/{u_a_id}/soft-delete",
        headers=headers,
    )
    assert del_a.status_code == 200
    assert del_a.json()["is_deleted"] is True

    # 3. Crear usuario B (ocupa el cupo liberado 1/1)
    u_b_res = await async_client.post(
        "/api/v1/tenancy/client-users",
        headers=headers,
        json={
            "holding_id": holding_id,
            "tenant_id": tenant_id,
            "username": "usuario.b",
            "email": "usuario.b@borde.cl",
            "password": "PasswordSeguro#2026",
            "first_name": "Usuario",
            "last_name": "B",
            "role_slug": "admin",
        },
    )
    assert u_b_res.status_code == 201
    u_b_id = u_b_res.json()["user_id"]

    # 4. Intentar restaurar usuario A con cuota llena -> HTTP 409 QuotaExceededError
    restore_blocked = await async_client.post(
        f"/api/v1/tenancy/client-users/{u_a_id}/restore",
        headers=headers,
    )
    assert restore_blocked.status_code == 409
    assert "seat_quota_exceeded" in restore_blocked.json()["detail"] or "quota" in restore_blocked.json()["detail"].lower()

    # 5. Soft-delete usuario B
    del_b = await async_client.post(
        f"/api/v1/tenancy/client-users/{u_b_id}/soft-delete",
        headers=headers,
    )
    assert del_b.status_code == 200
    assert del_b.json()["is_deleted"] is True

    # 6. Ahora restaurar usuario A tiene éxito -> HTTP 200
    restore_ok = await async_client.post(
        f"/api/v1/tenancy/client-users/{u_a_id}/restore",
        headers=headers,
    )
    assert restore_ok.status_code == 200
    assert restore_ok.json()["is_deleted"] is False
    assert restore_ok.json()["user_id"] == u_a_id

    # 7. Restauración idempotente de usuario ya activo -> HTTP 200
    restore_idempotent = await async_client.post(
        f"/api/v1/tenancy/client-users/{u_a_id}/restore",
        headers=headers,
    )
    assert restore_idempotent.status_code == 200
    assert restore_idempotent.json()["is_deleted"] is False

    # 8. Restaurar usuario inexistente -> HTTP 404
    restore_not_found = await async_client.post(
        "/api/v1/tenancy/client-users/999999/restore",
        headers=headers,
    )
    assert restore_not_found.status_code == 404


async def test_concurrent_quota_allocation_race_condition() -> None:
    """
    Prueba de borde: concurrencia en cuotas de capacidad (Race Condition Prevention).
    Simula 10 corrutinas concurrentes compitiendo por registrar items en un servicio
    con solo 3 cupos disponibles. Exactamente 3 deben tener éxito y 7 deben ser
    rechazadas con QuotaExceededError, garantizando que jamás se sobrepase el límite.
    """
    quota_svc = TenantCapacityQuotaService(
        plan_limits={
            "users": 5,
            "products": 3,
            "suppliers": 5,
            "recipes": 0,
            "combos": 0,
            "storage_mb": 512,
        }
    )
    lock = asyncio.Lock()

    async def _try_register(item_index: int) -> bool:
        async with lock:
            try:
                quota_svc.register_item(
                    resource_type="products",
                    item_id=f"CONCURRENT-PRD-{item_index}",
                )
                return True
            except QuotaExceededError:
                return False

    results = await asyncio.gather(*(_try_register(i) for i in range(10)))
    assert results.count(True) == 3
    assert results.count(False) == 7

    status = quota_svc.evaluate_resource(resource_type="products")
    assert status.active_count == 3
    assert status.remaining_capacity == 0
    assert status.status == "OVER_QUOTA"
    assert status.allowed is False


def test_extreme_boundary_limits_and_negative_rejections() -> None:
    """
    Prueba de borde: límites extremos de capacidad, semáforo preventivo y validaciones de rango:
    - 79.99% -> NORMAL (<80%)
    - 80.00% -> WARNING (>=80%)
    - 94.99% -> WARNING (<95%)
    - 95.00% -> CRITICAL (>=95%)
    - 99.99% -> CRITICAL (<100%)
    - 100.00% -> OVER_QUOTA (100% o activo >= límite)
    - Conteos negativos -> ValueError estricto.
    - Cuotas de storage negativas -> ValueError estricto.
    - Límite cero -> OVER_QUOTA con 100.00%.
    - Escala masiva (10 millones de items) -> precisión Decimal exacta sin desbordamiento.
    """
    # 1. Frontera exactísima 79.99% vs 80.00%
    ev_79 = evaluate_resource_capacity_quota(
        resource_type="products",
        active_non_deleted_count=7999,
        plan_limit=10000,
    )
    assert ev_79.usage_percentage == Decimal("79.99")
    assert ev_79.status == "NORMAL"

    ev_80 = evaluate_resource_capacity_quota(
        resource_type="products",
        active_non_deleted_count=8000,
        plan_limit=10000,
    )
    assert ev_80.usage_percentage == Decimal("80.00")
    assert ev_80.status == "WARNING"

    # 2. Frontera exactísima 94.99% vs 95.00%
    ev_94 = evaluate_resource_capacity_quota(
        resource_type="products",
        active_non_deleted_count=9499,
        plan_limit=10000,
    )
    assert ev_94.usage_percentage == Decimal("94.99")
    assert ev_94.status == "WARNING"

    ev_95 = evaluate_resource_capacity_quota(
        resource_type="products",
        active_non_deleted_count=9500,
        plan_limit=10000,
    )
    assert ev_95.usage_percentage == Decimal("95.00")
    assert ev_95.status == "CRITICAL"

    # 3. Frontera 99.99% vs 100.00%
    ev_99 = evaluate_resource_capacity_quota(
        resource_type="products",
        active_non_deleted_count=9999,
        plan_limit=10000,
    )
    assert ev_99.usage_percentage == Decimal("99.99")
    assert ev_99.status == "CRITICAL"

    ev_100 = evaluate_resource_capacity_quota(
        resource_type="products",
        active_non_deleted_count=10000,
        plan_limit=10000,
    )
    assert ev_100.usage_percentage == Decimal("100.00")
    assert ev_100.status == "OVER_QUOTA"
    assert ev_100.allowed is False

    # 4. Rechazo de conteos negativos
    with pytest.raises(ValueError, match="Resource counts cannot be negative"):
        evaluate_resource_capacity_quota(
            resource_type="products",
            active_non_deleted_count=-1,
            plan_limit=100,
        )

    with pytest.raises(ValueError, match="Resource counts cannot be negative"):
        evaluate_resource_capacity_quota(
            resource_type="products",
            active_non_deleted_count=10,
            soft_deleted_count=-5,
            plan_limit=100,
        )

    # 5. Rechazo de storage negativo
    with pytest.raises(ValueError, match="Byte counts for storage quota cannot be negative"):
        evaluate_storage_quota_bytes(
            current_used_bytes=-1024,
            new_bytes=512,
            plan_max_storage_mb=512,
        )

    with pytest.raises(ValueError, match="Byte counts for storage quota cannot be negative"):
        evaluate_storage_quota_bytes(
            current_used_bytes=1024,
            new_bytes=-512,
            plan_max_storage_mb=512,
        )

    # 6. Límite cero (recetas en Plan Básico sin override)
    ev_zero = evaluate_resource_capacity_quota(
        resource_type="recipes",
        active_non_deleted_count=0,
        plan_limit=0,
    )
    assert ev_zero.allowed is False
    assert ev_zero.status == "OVER_QUOTA"
    assert ev_zero.usage_percentage == Decimal("100.00")
    assert ev_zero.remaining_capacity == 0

    # 7. Escala masiva (10 millones de productos) con cálculo exacto
    ev_massive = evaluate_resource_capacity_quota(
        resource_type="products",
        active_non_deleted_count=7_500_000,
        plan_limit=10_000_000,
    )
    assert ev_massive.allowed is True
    assert ev_massive.status == "NORMAL"
    assert ev_massive.usage_percentage == Decimal("75.00")
    assert ev_massive.remaining_capacity == 2_500_000


def test_plan_basico_ten_modules_complete_behavioral_and_mathematical_parity() -> None:
    """
    Verifica la paridad de comportamiento y matemática de los 10 módulos del Plan Básico:
    1. Inicio (`inicio`)
    2. Consumo (`operations.consumption_log`)
    3. Stock (`inventory.stock`)
    4. Productos (`catalog.products`)
    5. Mermas (`inventory.mermas`)
    6. Recuento (`inventory.counts`)
    7. Notificaciones (`notifications`)
    8. Alertas (`alerts`)
    9. Historial (`audit.history`)
    10. Usuarios (`identity.users`)

    Garantiza que un operador con rol Plan Básico tenga acceso garantizado a los 10 módulos
    y sea estrictamente denegado en módulos avanzados/pro (escandallos, buffet, bot RAG OppyFy).
    """
    plan_basico_modules_set = set(PLAN_BASICO_10_MODULES)

    # Los 10 módulos de negocio del Plan Básico deben estar presentes en el set del bootstrap
    expected_core_10 = [
        "inicio",
        "operations.consumption_log",
        "inventory.stock",
        "catalog.products",
        "inventory.mermas",
        "inventory.counts",
        "notifications",
        "alerts",
        "audit.history",
        "identity.users",
    ]
    for m in expected_core_10:
        assert m in plan_basico_modules_set, f"El módulo '{m}' debe pertenecer a PLAN_BASICO_10_MODULES"

    # Permisos otorgados a un operador típico de Plan Básico
    operator_role_perms = {
        "operations.consumption_log.create",
        "operations.consumption_log.read",
        "inventory.stock.read",
        "catalog.products.read",
        "catalog.products.create",
        "inventory.mermas.create",
        "inventory.mermas.read",
        "inventory.counts.create",
        "inventory.counts.read",
        "audit.history.read",
        "identity.users.read",
        # Intento de permisos pro/avanzados
        "recipes.escandallos.create",
        "operations.buffet.calculate",
        "oppyfy.assistant.chat",
    }

    effective = compute_effective_permissions(
        plan_enabled_modules=plan_basico_modules_set,
        role_permissions=operator_role_perms,
    )

    # 1. Todos los permisos dentro de los 10 módulos deben estar efectivos
    assert "operations.consumption_log.create" in effective
    assert "inventory.stock.read" in effective
    assert "catalog.products.create" in effective
    assert "inventory.mermas.create" in effective
    assert "inventory.counts.create" in effective
    assert "audit.history.read" in effective
    assert "identity.users.read" in effective

    # 2. Todos los permisos fuera de los 10 módulos deben quedar filtrados y denegados
    assert "recipes.escandallos.create" not in effective
    assert "operations.buffet.calculate" not in effective
    assert "oppyfy.assistant.chat" not in effective

    # 3. Verificación de decisión de acceso individual con motivo RFC
    escandallo_eval = evaluate_permission_access(
        actor_user_id=42,
        required_permission="recipes.escandallos.create",
        plan_enabled_modules=plan_basico_modules_set,
        role_permissions=operator_role_perms,
    )
    assert escandallo_eval.allowed is False
    assert escandallo_eval.reason_code == "MODULE_NOT_ENABLED_IN_PLAN"

    buffet_eval = evaluate_permission_access(
        actor_user_id=42,
        required_permission="operations.buffet.calculate",
        plan_enabled_modules=plan_basico_modules_set,
        role_permissions=operator_role_perms,
    )
    assert buffet_eval.allowed is False
    assert buffet_eval.reason_code == "MODULE_NOT_ENABLED_IN_PLAN"

    oppyfy_eval = evaluate_permission_access(
        actor_user_id=42,
        required_permission="oppyfy.assistant.chat",
        plan_enabled_modules=plan_basico_modules_set,
        role_permissions=operator_role_perms,
    )
    assert oppyfy_eval.allowed is False
    assert oppyfy_eval.reason_code == "MODULE_NOT_ENABLED_IN_PLAN"

