"""
Vector Red Team 15 (`tests/security_redteam/test_15_procurement_offensive_security_and_rbac.py`):
Auditoría Ofensiva de Ciberseguridad, Aislamiento Multi-Tenant, Prevención Anti-IDOR y Guardias RBAC de 3 Niveles en Procurement y Mermas:
1. Prevención estricta de IDOR Cross-Tenant en Proveedores (/suppliers/{id}, /products).
2. Prevención estricta de IDOR Cross-Tenant en Órdenes de Compra (/orders/{id}, /receive, /cancel, /incidences).
3. Aislamiento Cross-Tenant estricto en Analítica e Historial de Mermas (/inventory/mermas/analytics, /history).
4. Validación exhaustiva de Guardias RBAC de 3 Niveles (procurement.suppliers.read, procurement.suppliers.manage,
   procurement.orders.read, procurement.orders.create, procurement.orders.receive, procurement.orders.cancel,
   procurement.dashboard.view, inventory.mermas.view): Denegación 403 RFC 7807 (ProblemDetails).
5. Evaluación de Explicit Denies y Revocación Dinámica en RBAC.
6. Bloqueo de Mass Assignment / Parameter Pollution (ConfigDict extra="forbid") en esquemas de Procurement.
7. Preservación estricta de la regla inmutable "Pollo King" ante intentos de alteración maliciosa de razón social.
8. Bloqueo determinista de vectores XSS y políglotas en campos de texto libre (notas, motivos, descripciones).
9. Prevención de Inyección SQL (SQLi) en parámetros de ruta y filtros de consulta.
10. Rechazo de Floats, Valores Negativos y comprobación de precisión Decimal(14, 2).
11. Verificación de Magic Bytes en ingesta de Facturas OCR contra archivos maliciosos camuflados.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
import pytest

from src.core.exceptions import (
    CrossTenantAccessError,
    ProperNounImmutabilityError,
    SecurityValidationError,
)
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.modules.inventory.presentation.router import (
    _inventory_service,
    _merma_analytics_service,
    _waste_service,
)
from src.modules.procurement.domain.entities import Supplier
from src.modules.procurement.domain.value_objects import MoneyAmount, RutTaxId
from src.modules.procurement.presentation.router import (
    _procurement_service,
    _supplier_service,
)

pytestmark = pytest.mark.security_redteam

TENANT_ALPHA = "tenant_alpha_santiago"
TENANT_BETA = "tenant_beta_valparaiso"
HOLDING_ID = "holding_pollogold"


def _create_token(
    user_id: int,
    tenant_id: str,
    permissions: list[str],
    *,
    hierarchy_rank: int = 20,
    explicit_denies: list[str] | None = None,
    accessible_tenants: list[str] | None = None,
    contracted_modules: list[str] | None = None,
) -> str:
    """Genera token JWT firmado con contexto de tenant y permisos RBAC."""
    return create_access_token(
        user_id=user_id,
        holding_id=HOLDING_ID,
        tenant_id=tenant_id,
        tenant_schema=tenant_id,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
        explicit_denies=explicit_denies or [],
        accessible_tenants=accessible_tenants or [tenant_id],
        contracted_modules=contracted_modules or ["procurement", "inventory", "catalog"],
    )


def _make_headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


@pytest.fixture(autouse=True)
def _reset_test_environment() -> None:
    clear_revoked_sessions()
    get_rate_limiter().reset()
    _procurement_service.reset_in_memory_store()
    _supplier_service.reset_in_memory_store()
    _merma_analytics_service.reset_in_memory_store()
    _procurement_service.enable_in_memory_mode()
    _supplier_service.enable_in_memory_mode()
    _merma_analytics_service.enable_in_memory_mode()
    _inventory_service.reset()
    _waste_service._wastes.clear()
    _waste_service._seq = 0


# ============================================================================
# VECTOR 1: IDOR CROSS-TENANT EN PROVEEDORES Y CATÁLOGO
# ============================================================================


@pytest.mark.asyncio
async def test_cross_tenant_idor_on_suppliers_and_catalog_strictly_blocked(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que un usuario del Tenant Beta jamás pueda leer, modificar, eliminar
    ni alterar el catálogo de un proveedor perteneciente al Tenant Alpha.
    """
    token_alpha = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.suppliers.read", "procurement.suppliers.manage"],
    )
    headers_alpha = _make_headers(token_alpha, TENANT_ALPHA)

    token_beta = _create_token(
        user_id=202,
        tenant_id=TENANT_BETA,
        permissions=["procurement.suppliers.read", "procurement.suppliers.manage"],
    )
    headers_beta = _make_headers(token_beta, TENANT_BETA)

    # 1. Tenant Alpha crea un proveedor legítimo (RUT válido con Módulo 11)
    create_resp = await async_client.post(
        "/api/v1/procurement/suppliers",
        headers=headers_alpha,
        json={
            "rut_tax_id": "76.111.222-8",
            "razon_social": "Distribuidora Avícola Alpha SpA",
            "nombre_fantasia": "Avícola Alpha",
            "email_contacto": "ventas@avicolaalpha.cl",
            "lead_time_dias": 2,
        },
    )
    assert create_resp.status_code == 201
    supplier_alpha_id = create_resp.json()["id"]

    # Tenant Alpha carga un producto en su catálogo
    cat_create_resp = await async_client.post(
        f"/api/v1/procurement/suppliers/{supplier_alpha_id}/products",
        headers=headers_alpha,
        json={
            "items": [
                {
                    "producto_id": 10,
                    "precio_pactado": "4500.00",
                    "codigo_producto_proveedor": "ALPHA-10",
                    "tiempo_entrega_dias": 2,
                    "es_proveedor_principal": True,
                }
            ]
        },
    )
    assert cat_create_resp.status_code == 200

    # 2. Tenant Beta intenta leer el proveedor de Alpha (IDOR Read) -> HTTP 403
    get_resp = await async_client.get(
        f"/api/v1/procurement/suppliers/{supplier_alpha_id}",
        headers=headers_beta,
    )
    assert get_resp.status_code == 403
    assert get_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 3. Tenant Beta intenta actualizar el proveedor de Alpha (IDOR Update) -> HTTP 403
    update_resp = await async_client.put(
        f"/api/v1/procurement/suppliers/{supplier_alpha_id}",
        headers=headers_beta,
        json={"email_contacto": "hacked@attacker-beta.com"},
    )
    assert update_resp.status_code == 403
    assert update_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 4. Tenant Beta intenta ver el catálogo pactado de Alpha (IDOR Catalog Read) -> HTTP 403
    cat_get_resp = await async_client.get(
        f"/api/v1/procurement/suppliers/{supplier_alpha_id}/products",
        headers=headers_beta,
    )
    assert cat_get_resp.status_code == 403
    assert cat_get_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 5. Tenant Beta intenta sobreescribir el catálogo de Alpha (IDOR Catalog Write) -> HTTP 403
    cat_put_resp = await async_client.post(
        f"/api/v1/procurement/suppliers/{supplier_alpha_id}/products",
        headers=headers_beta,
        json={
            "items": [
                {
                    "producto_id": 10,
                    "precio_pactado": "1.00",
                    "codigo_producto_proveedor": "EXPLOIT-10",
                }
            ]
        },
    )
    assert cat_put_resp.status_code == 403
    assert cat_put_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 6. Tenant Beta intenta eliminar el proveedor de Alpha (IDOR Delete) -> HTTP 403
    del_resp = await async_client.delete(
        f"/api/v1/procurement/suppliers/{supplier_alpha_id}",
        headers=headers_beta,
    )
    assert del_resp.status_code == 403
    assert del_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 7. Listar proveedores desde Tenant Beta NO debe filtrar ni exponer el proveedor de Alpha
    list_beta = await async_client.get("/api/v1/procurement/suppliers", headers=headers_beta)
    assert list_beta.status_code == 200
    assert not any(s["id"] == supplier_alpha_id for s in list_beta.json())


# ============================================================================
# VECTOR 2: IDOR CROSS-TENANT EN ÓRDENES DE COMPRA (CICLO COMPLETO)
# ============================================================================


@pytest.mark.asyncio
async def test_cross_tenant_idor_on_purchase_orders_lifecycle_strictly_blocked(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que un usuario del Tenant Beta jamás pueda leer, modificar, recepcionar,
    cancelar ni registrar incidencias en una orden de compra del Tenant Alpha.
    """
    token_alpha = _create_token(
        user_id=101,
        tenant_id=TENANT_ALPHA,
        permissions=[
            "procurement.orders.create",
            "procurement.orders.read",
            "procurement.orders.receive",
            "procurement.orders.cancel",
        ],
    )
    headers_alpha = _make_headers(token_alpha, TENANT_ALPHA)

    token_beta = _create_token(
        user_id=202,
        tenant_id=TENANT_BETA,
        permissions=[
            "procurement.orders.create",
            "procurement.orders.read",
            "procurement.orders.receive",
            "procurement.orders.cancel",
        ],
    )
    headers_beta = _make_headers(token_beta, TENANT_BETA)

    # 1. Tenant Alpha crea una orden de compra
    create_resp = await async_client.post(
        "/api/v1/procurement/orders",
        headers=headers_alpha,
        json={
            "numero_orden": "OC-ALPHA-2026-001",
            "proveedor_id": 1,
            "supplier_name": "Pollo King",
            "bodega_destino_id": 1,
            "estado": "SOLICITADA",
            "items": [
                {
                    "producto_id": 5,
                    "cantidad_solicitada": "50.0000",
                    "costo_unitario_neto": "3200.00",
                }
            ],
            "notas": "Orden confidencial Tenant Alpha",
        },
    )
    assert create_resp.status_code == 201
    order_alpha = create_resp.json()
    order_alpha_id = order_alpha["id"]
    po_number = order_alpha["numero_orden"]

    # 2. Tenant Beta intenta leer la orden de Alpha por ID numérico (IDOR Read) -> HTTP 403
    get_resp1 = await async_client.get(
        f"/api/v1/procurement/orders/{order_alpha_id}",
        headers=headers_beta,
    )
    assert get_resp1.status_code == 403
    assert get_resp1.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # Tenant Beta intenta leer la orden de Alpha por código PO -> HTTP 403
    get_resp2 = await async_client.get(
        f"/api/v1/procurement/orders/{po_number}",
        headers=headers_beta,
    )
    assert get_resp2.status_code == 403
    assert get_resp2.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 3. Tenant Beta intenta modificar la orden de Alpha (IDOR Update) -> HTTP 403
    put_resp = await async_client.put(
        f"/api/v1/procurement/orders/{order_alpha_id}",
        headers=headers_beta,
        json={"notas": "Alterada por Tenant Beta atacante"},
    )
    assert put_resp.status_code == 403
    assert put_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 4. Tenant Beta intenta recepcionar mercadería de Alpha (IDOR Receive) -> HTTP 403
    rec_resp = await async_client.post(
        f"/api/v1/procurement/orders/{order_alpha_id}/receive",
        headers=headers_beta,
        json={
            "items": [
                {
                    "producto_id": 5,
                    "cantidad_recibida": "50.0000",
                }
            ]
        },
    )
    assert rec_resp.status_code == 403
    assert rec_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 5. Tenant Beta intenta registrar incidencia en orden de Alpha (IDOR Incidence) -> HTTP 403
    inc_resp = await async_client.post(
        f"/api/v1/procurement/orders/{order_alpha_id}/incidences",
        headers=headers_beta,
        json={
            "tipo_incidencia": "MERCADERIA_DANADA",
            "cantidad_afectada": "5.0000",
            "monto_disputa": "16000.00",
            "descripcion": "Disputa inyectada maliciosamente por Tenant Beta",
        },
    )
    assert inc_resp.status_code == 403
    assert inc_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 6. Tenant Beta intenta cancelar la orden de Alpha (IDOR Cancel) -> HTTP 403
    cancel_resp = await async_client.post(
        f"/api/v1/procurement/orders/{order_alpha_id}/cancel",
        headers=headers_beta,
        json={"motivo": "Cancelación hostil cross-tenant"},
    )
    assert cancel_resp.status_code == 403
    assert cancel_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 7. Listar órdenes desde Tenant Beta NO debe incluir la orden de Alpha
    list_orders_beta = await async_client.get("/api/v1/procurement/orders", headers=headers_beta)
    assert list_orders_beta.status_code == 200
    assert not any(o["id"] == order_alpha_id for o in list_orders_beta.json())


# ============================================================================
# VECTOR 3: IDOR CROSS-TENANT EN ANALÍTICA E HISTORIAL DE MERMAS
# ============================================================================


@pytest.mark.asyncio
async def test_cross_tenant_idor_on_merma_analytics_and_history_isolated(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que las mermas reportadas por Tenant Alpha no impacten ni se filtren
    en los endpoints de analítica financiera ni de historial de Tenant Beta.
    """
    token_alpha = _create_token(
        user_id=110,
        tenant_id=TENANT_ALPHA,
        permissions=["inventory.mermas.create", "inventory.mermas.view"],
    )
    headers_alpha = _make_headers(token_alpha, TENANT_ALPHA)

    token_beta = _create_token(
        user_id=220,
        tenant_id=TENANT_BETA,
        permissions=["inventory.mermas.view"],
    )
    headers_beta = _make_headers(token_beta, TENANT_BETA)

    # 1. Tenant Alpha reporta una merma de alto valor
    rep_resp = await async_client.post(
        "/api/v1/inventory/mermas",
        headers=headers_alpha,
        json={
            "producto_id": 7,
            "bodega_id": 1,
            "quantity": "25.0000",
            "unit_cost": "3500.00",
            "reason": "Rotura de cadena de frío en bodega Alpha",
        },
    )
    assert rep_resp.status_code == 201

    # 2. Tenant Alpha consulta su analítica: debe ver reflejada la merma (total = 87500.00)
    analytics_alpha = await async_client.get(
        "/api/v1/inventory/mermas/analytics",
        headers=headers_alpha,
    )
    assert analytics_alpha.status_code == 200
    alpha_data = analytics_alpha.json()
    assert Decimal(str(alpha_data["total_perdida_ppp"])) == Decimal("87500.00")
    assert alpha_data["items_mermados_count"] == 1

    # 3. Tenant Beta consulta su analítica: DEBE ESTAR EN CERO (cero fuga de datos)
    analytics_beta = await async_client.get(
        "/api/v1/inventory/mermas/analytics",
        headers=headers_beta,
    )
    assert analytics_beta.status_code == 200
    beta_data = analytics_beta.json()
    assert Decimal(str(beta_data["total_perdida_ppp"])) == Decimal("0.00")
    assert beta_data["items_mermados_count"] == 0

    # 4. Tenant Beta consulta el historial de mermas: DEBE ESTAR VACÍO
    history_beta = await async_client.get(
        "/api/v1/inventory/mermas/history",
        headers=headers_beta,
    )
    assert history_beta.status_code == 200
    hist_data = history_beta.json()
    assert hist_data["total"] == 0
    assert len(hist_data["items"]) == 0


# ============================================================================
# VECTOR 4: VALIDACIÓN EXHAUSTIVA DE GUARDIAS RBAC DE 3 NIVELES (HTTP 403 RFC 7807)
# ============================================================================


@pytest.mark.asyncio
async def test_rbac_three_level_guards_strictly_enforced_with_problem_details(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que cada uno de los endpoints de Procurement y Mermas exija su permiso
    específico de 3 niveles y retorne HTTP 403 RFC 7807 (ProblemDetails) ante su ausencia.
    """
    # 1. procurement.suppliers.read
    token_no_sup_read = _create_token(
        user_id=301,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.orders.read"],
    )
    h_no_sup_read = _make_headers(token_no_sup_read, TENANT_ALPHA)

    r_sup_list = await async_client.get("/api/v1/procurement/suppliers", headers=h_no_sup_read)
    assert r_sup_list.status_code == 403
    assert r_sup_list.json()["status"] == 403
    assert r_sup_list.json()["error_code"] == "MISSING_PERMISSION"

    r_sup_detail = await async_client.get("/api/v1/procurement/suppliers/1", headers=h_no_sup_read)
    assert r_sup_detail.status_code == 403
    assert r_sup_detail.json()["error_code"] == "MISSING_PERMISSION"

    # 2. procurement.suppliers.manage
    token_only_sup_read = _create_token(
        user_id=302,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.suppliers.read"],
    )
    h_only_sup_read = _make_headers(token_only_sup_read, TENANT_ALPHA)

    r_sup_create = await async_client.post(
        "/api/v1/procurement/suppliers",
        headers=h_only_sup_read,
        json={
            "rut_tax_id": "76.999.888-8",
            "razon_social": "Proveedor No Autorizado",
        },
    )
    assert r_sup_create.status_code == 403
    assert r_sup_create.json()["error_code"] == "MISSING_PERMISSION"

    r_sup_put = await async_client.put(
        "/api/v1/procurement/suppliers/1",
        headers=h_only_sup_read,
        json={"email_contacto": "test@test.cl"},
    )
    assert r_sup_put.status_code == 403
    assert r_sup_put.json()["error_code"] == "MISSING_PERMISSION"

    r_sup_del = await async_client.delete(
        "/api/v1/procurement/suppliers/1",
        headers=h_only_sup_read,
    )
    assert r_sup_del.status_code == 403
    assert r_sup_del.json()["error_code"] == "MISSING_PERMISSION"

    r_sup_cat_update = await async_client.post(
        "/api/v1/procurement/suppliers/1/products",
        headers=h_only_sup_read,
        json={"items": [{"producto_id": 1, "precio_pactado": "1000.00"}]},
    )
    assert r_sup_cat_update.status_code == 403
    assert r_sup_cat_update.json()["error_code"] == "MISSING_PERMISSION"

    # 3. procurement.orders.read
    token_no_ord_read = _create_token(
        user_id=303,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.suppliers.read"],
    )
    h_no_ord_read = _make_headers(token_no_ord_read, TENANT_ALPHA)

    r_ord_list = await async_client.get("/api/v1/procurement/orders", headers=h_no_ord_read)
    assert r_ord_list.status_code == 403
    assert r_ord_list.json()["error_code"] == "MISSING_PERMISSION"

    r_ord_detail = await async_client.get("/api/v1/procurement/orders/1", headers=h_no_ord_read)
    assert r_ord_detail.status_code == 403
    assert r_ord_detail.json()["error_code"] == "MISSING_PERMISSION"

    # 4. procurement.orders.create
    token_only_ord_read = _create_token(
        user_id=304,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.orders.read"],
    )
    h_only_ord_read = _make_headers(token_only_ord_read, TENANT_ALPHA)

    r_ord_create = await async_client.post(
        "/api/v1/procurement/orders",
        headers=h_only_ord_read,
        json={
            "proveedor_id": 1,
            "items": [{"producto_id": 1, "cantidad_solicitada": "10.0000", "costo_unitario_neto": "500.00"}],
        },
    )
    assert r_ord_create.status_code == 403
    assert r_ord_create.json()["error_code"] == "MISSING_PERMISSION"

    r_ord_update = await async_client.put(
        "/api/v1/procurement/orders/1",
        headers=h_only_ord_read,
        json={"notas": "Modificación no autorizada"},
    )
    assert r_ord_update.status_code == 403
    assert r_ord_update.json()["error_code"] == "MISSING_PERMISSION"

    # 5. procurement.orders.receive
    r_ord_receive = await async_client.post(
        "/api/v1/procurement/orders/1/receive",
        headers=h_only_ord_read,
        json={"items": [{"producto_id": 1, "cantidad_recibida": "10.0000"}]},
    )
    assert r_ord_receive.status_code == 403
    assert r_ord_receive.json()["error_code"] == "MISSING_PERMISSION"

    # 6. procurement.orders.cancel
    r_ord_cancel = await async_client.post(
        "/api/v1/procurement/orders/1/cancel",
        headers=h_only_ord_read,
        json={"motivo": "Cancelación sin permiso"},
    )
    assert r_ord_cancel.status_code == 403
    assert r_ord_cancel.json()["error_code"] == "MISSING_PERMISSION"

    # 7. procurement.dashboard.view
    token_no_dash = _create_token(
        user_id=305,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.suppliers.read"],
    )
    h_no_dash = _make_headers(token_no_dash, TENANT_ALPHA)
    r_dash = await async_client.get("/api/v1/procurement/dashboard", headers=h_no_dash)
    assert r_dash.status_code == 403
    assert r_dash.json()["error_code"] == "MISSING_PERMISSION"

    # Acceso permitido con procurement.dashboard.view
    token_dash = _create_token(
        user_id=306,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.dashboard.view"],
    )
    h_dash = _make_headers(token_dash, TENANT_ALPHA)
    r_dash_ok = await async_client.get("/api/v1/procurement/dashboard", headers=h_dash)
    assert r_dash_ok.status_code == 200

    # 8. inventory.mermas.view
    r_merma_analytics = await async_client.get(
        "/api/v1/inventory/mermas/analytics",
        headers=h_only_ord_read,
    )
    assert r_merma_analytics.status_code == 403
    assert r_merma_analytics.json()["error_code"] == "MISSING_PERMISSION"

    r_merma_history = await async_client.get(
        "/api/v1/inventory/mermas/history",
        headers=h_only_ord_read,
    )
    assert r_merma_history.status_code == 403
    assert r_merma_history.json()["error_code"] == "MISSING_PERMISSION"


@pytest.mark.asyncio
async def test_rbac_explicit_denies_override_role_grants(async_client: httpx.AsyncClient) -> None:
    """
    Verifica que si un usuario tiene otorgado un permiso pero se le aplica un explicit deny,
    la denegación explícita prevalezca determinísticamente con HTTP 403.
    """
    token_denied = _create_token(
        user_id=310,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.orders.read", "procurement.orders.cancel"],
        explicit_denies=["procurement.orders.cancel"],
    )
    headers = _make_headers(token_denied, TENANT_ALPHA)

    # Cancelación debe ser denegada por explicit deny
    resp = await async_client.post(
        "/api/v1/procurement/orders/1/cancel",
        headers=headers,
        json={"motivo": "Intento de cancelación con permiso revocado explícitamente"},
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "EXPLICIT_DENY_GRANT"


# ============================================================================
# VECTOR 5: MASS ASSIGNMENT & PARAMETER POLLUTION (ConfigDict extra="forbid")
# ============================================================================


@pytest.mark.asyncio
async def test_mass_assignment_pollution_blocked_on_all_procurement_schemas(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que cualquier inyección de campos no autorizados (ej: 'is_admin', 'bypass_checks')
    sea bloqueada determinísticamente por Pydantic con HTTP 422 Unprocessable Entity.
    """
    token = _create_token(
        user_id=401,
        tenant_id=TENANT_ALPHA,
        permissions=[
            "procurement.suppliers.manage",
            "procurement.orders.create",
            "procurement.orders.receive",
            "procurement.orders.cancel",
        ],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. SupplierCreateRequest con Mass Assignment
    r1 = await async_client.post(
        "/api/v1/procurement/suppliers",
        headers=headers,
        json={
            "rut_tax_id": "77.123.456-9",
            "razon_social": "Proveedor Polución Test",
            "is_admin_system": True,  # Inyección
            "bypass_auth": 1,
        },
    )
    assert r1.status_code == 422
    assert "extra_forbidden" in str(r1.json())

    # 2. SupplierUpdateRequest con Mass Assignment
    r2 = await async_client.put(
        "/api/v1/procurement/suppliers/100",
        headers=headers,
        json={
            "telefono": "+56911223344",
            "role_grant_all": True,  # Inyección
        },
    )
    assert r2.status_code == 422
    assert "extra_forbidden" in str(r2.json())

    # 3. PurchaseOrderCreateRequest con Mass Assignment
    r3 = await async_client.post(
        "/api/v1/procurement/orders",
        headers=headers,
        json={
            "proveedor_id": 1,
            "items": [{"producto_id": 1, "cantidad_solicitada": "10.0000", "costo_unitario_neto": "500.00"}],
            "override_price_lock": True,  # Inyección
            "tenant_id_spoof": "tenant_other",
        },
    )
    assert r3.status_code == 422
    assert "extra_forbidden" in str(r3.json())

    # 4. ReceiveGoodsRequest con Mass Assignment
    r4 = await async_client.post(
        "/api/v1/procurement/orders/1/receive",
        headers=headers,
        json={
            "items": [{"producto_id": 1, "cantidad_recibida": "10.0000"}],
            "bypass_kardex_lock": True,  # Inyección
        },
    )
    assert r4.status_code == 422
    assert "extra_forbidden" in str(r4.json())

    # 5. CancelOrderRequest con Mass Assignment
    r5 = await async_client.post(
        "/api/v1/procurement/orders/1/cancel",
        headers=headers,
        json={
            "motivo": "Cancelación por auditoría",
            "force_unconditional_cancel": True,  # Inyección
        },
    )
    assert r5.status_code == 422
    assert "extra_forbidden" in str(r5.json())

    # 6. PurchaseIncidenceCreateRequest con Mass Assignment
    r6 = await async_client.post(
        "/api/v1/procurement/orders/1/incidences",
        headers=headers,
        json={
            "tipo_incidencia": "DIFERENCIA_PRECIO",
            "cantidad_afectada": "1.0000",
            "monto_disputa": "5000.00",
            "descripcion": "Incidencia con payload extra",
            "auto_approve_refund": True,  # Inyección
        },
    )
    assert r6.status_code == 422
    assert "extra_forbidden" in str(r6.json())


# ============================================================================
# VECTOR 6: PRESERVACIÓN DE LA INVARIANTE INMUTABLE "POLLO KING"
# ============================================================================


@pytest.mark.asyncio
async def test_proper_noun_immutability_pollo_king_enforced_against_alteration(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que la regla 'Pollo King' (translatable=False) prohíba estrictamente
    la traducción o alteración de la razón social de un proveedor protegido.
    """
    token = _create_token(
        user_id=501,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.suppliers.manage", "procurement.suppliers.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. Crear el proveedor emblemático 'Pollo King' (RUT chileno válido 76.543.210-3)
    create_resp = await async_client.post(
        "/api/v1/procurement/suppliers",
        headers=headers,
        json={
            "rut_tax_id": "76.543.210-3",
            "razon_social": "Pollo King",
            "nombre_fantasia": "Pollo King SpA",
            "email_contacto": "admin@polloking.cl",
            "lead_time_dias": 1,
        },
    )
    assert create_resp.status_code == 201
    pk_id = create_resp.json()["id"]

    # 2. Intento de traducir o alterar la razón social a inglés ('Chicken King') -> HTTP 422
    update_resp1 = await async_client.put(
        f"/api/v1/procurement/suppliers/{pk_id}",
        headers=headers,
        json={"razon_social": "Chicken King"},
    )
    assert update_resp1.status_code == 422
    assert update_resp1.json()["error_code"] == "PROPER_NOUN_IMMUTABILITY_VIOLATION"

    # 3. Intento de renombrar maliciosamente ('Pollo King Alterado') -> HTTP 422
    update_resp2 = await async_client.put(
        f"/api/v1/procurement/suppliers/{pk_id}",
        headers=headers,
        json={"razon_social": "Pollo King Alterado"},
    )
    assert update_resp2.status_code == 422
    assert update_resp2.json()["error_code"] == "PROPER_NOUN_IMMUTABILITY_VIOLATION"

    # 4. Modificar campos permitidos (ej. teléfono o notas) sin alterar la razón social -> HTTP 200
    update_ok = await async_client.put(
        f"/api/v1/procurement/suppliers/{pk_id}",
        headers=headers,
        json={"telefono": "+56987654321", "notas": "Proveedor principal auditado"},
    )
    assert update_ok.status_code == 200
    assert update_ok.json()["razon_social"] == "Pollo King"

    # 5. Validación directa en Entidad de Dominio Supplier
    sup_entity = Supplier(
        rut_tax_id=RutTaxId("76.543.210-3"),
        razon_social="Pollo King",
        id=pk_id,
    )
    assert sup_entity.translatable is False
    with pytest.raises(ProperNounImmutabilityError, match="immutable proper noun"):
        sup_entity.assert_proper_noun_immutable("El Rey del Pollo")


# ============================================================================
# VECTOR 7: RESILIENCIA CONTRA INYECCIÓN SQL (SQLi)
# ============================================================================


@pytest.mark.asyncio
async def test_sqli_payloads_in_routes_and_queries_strictly_rejected(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que payloads clásicos y apilados de SQL Injection en parámetros de ruta
    o cadenas de búsqueda sean neutralizados o rechazados con HTTP 422.
    """
    token = _create_token(
        user_id=601,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.suppliers.read", "procurement.orders.read"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. SQLi en ruta integer de proveedor
    for sqli in ("1' OR '1'='1", "1; DROP TABLE proveedores; --", "admin'--"):
        r_path = await async_client.get(
            f"/api/v1/procurement/suppliers/{sqli}",
            headers=headers,
        )
        assert r_path.status_code == 422

    # 2. SQLi en parámetro de consulta de órdenes (supplier_id integer)
    r_query = await async_client.get(
        "/api/v1/procurement/orders?supplier_id=1 UNION SELECT 1,2,3",
        headers=headers,
    )
    assert r_query.status_code == 422


# ============================================================================
# VECTOR 8: SANITIZACIÓN DETERMINISTA CONTRA CROSS-SITE SCRIPTING (XSS)
# ============================================================================


@pytest.mark.asyncio
async def test_xss_polyglots_in_procurement_text_inputs_blocked_with_422(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Comprueba que vectores XSS políglotas en campos de texto de órdenes, proveedores
    o incidencias sean interceptados determinísticamente y rechazados con HTTP 422.
    """
    token = _create_token(
        user_id=701,
        tenant_id=TENANT_ALPHA,
        permissions=[
            "procurement.suppliers.manage",
            "procurement.orders.create",
            "procurement.orders.cancel",
            "procurement.orders.receive",
        ],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. Intento de inyectar <script> en notas de proveedor -> HTTP 422
    r_xss_sup = await async_client.post(
        "/api/v1/procurement/suppliers",
        headers=headers,
        json={
            "rut_tax_id": "76.444.555-4",
            "razon_social": "Proveedor XSS Test",
            "notas": "<script>alert('XSS-SUPPLIER')</script>Nota maliciosa",
        },
    )
    assert r_xss_sup.status_code == 422
    assert r_xss_sup.json()["error_code"] == "XSS_PAYLOAD_BLOCKED"

    # 2. Intento de inyectar <img onerror> en motivo de cancelación de orden -> HTTP 422
    r_xss_cancel = await async_client.post(
        "/api/v1/procurement/orders/1/cancel",
        headers=headers,
        json={"motivo": "<img src=x onerror=alert(document.cookie)>Cancelación maliciosa"},
    )
    assert r_xss_cancel.status_code == 422
    assert r_xss_cancel.json()["error_code"] == "XSS_PAYLOAD_BLOCKED"

    # 3. Intento de inyectar <svg onload> en descripción de incidencia -> HTTP 422
    r_xss_inc = await async_client.post(
        "/api/v1/procurement/orders/1/incidences",
        headers=headers,
        json={
            "tipo_incidencia": "ROTURA",
            "cantidad_afectada": "2.0000",
            "descripcion": "<svg onload=alert(1)>Caja dañada",
        },
    )
    assert r_xss_inc.status_code == 422
    assert r_xss_inc.json()["error_code"] == "XSS_PAYLOAD_BLOCKED"

    # 4. Intento de inyectar javascript: en notas de orden de compra -> HTTP 422
    r_xss_ord = await async_client.post(
        "/api/v1/procurement/orders",
        headers=headers,
        json={
            "proveedor_id": 1,
            "items": [{"producto_id": 1, "cantidad_solicitada": "5.0000", "costo_unitario_neto": "1000.00"}],
            "notas": "javascript:alert('pwned')",
        },
    )
    assert r_xss_ord.status_code == 422
    assert r_xss_ord.json()["error_code"] == "XSS_PAYLOAD_BLOCKED"


# ============================================================================
# VECTOR 9: CERO FLOATS Y PRECISIÓN DECIMAL(14, 2)
# ============================================================================


def test_money_amount_and_decimal_boundaries() -> None:
    """Valida rechazo estricto de floats IEEE-754 y NaN en Value Objects de dinero."""
    with pytest.raises(TypeError, match="IEEE-754 float is strictly forbidden"):
        MoneyAmount(1500.50)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="NaN or infinite"):
        MoneyAmount(Decimal("NaN"))

    ma = MoneyAmount(Decimal("1500.50"), currency="CLP")
    assert str(ma) == "1500.50 CLP"


@pytest.mark.asyncio
async def test_negative_payload_values_rejected_in_procurement_orders(
    async_client: httpx.AsyncClient,
) -> None:
    """Valida que cantidades o precios negativos en órdenes sean rechazados con HTTP 422."""
    token = _create_token(
        user_id=801,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.orders.create"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # Cantidad negativa
    r_neg_qty = await async_client.post(
        "/api/v1/procurement/orders",
        headers=headers,
        json={
            "proveedor_id": 1,
            "items": [{"producto_id": 1, "cantidad_solicitada": "-10.0000", "costo_unitario_neto": "500.00"}],
        },
    )
    assert r_neg_qty.status_code == 422

    # Costo negativo
    r_neg_cost = await async_client.post(
        "/api/v1/procurement/orders",
        headers=headers,
        json={
            "proveedor_id": 1,
            "items": [{"producto_id": 1, "cantidad_solicitada": "10.0000", "costo_unitario_neto": "-500.00"}],
        },
    )
    assert r_neg_cost.status_code == 422


# ============================================================================
# VECTOR 10: MAGIC BYTES EN INGESTA DE FACTURAS OCR
# ============================================================================


@pytest.mark.asyncio
async def test_invoice_ocr_magic_bytes_enforcement(async_client: httpx.AsyncClient) -> None:
    """
    Verifica que la subida de facturas OCR valide Magic Bytes y rechace ejecutables
    o scripts camuflados como PDF/Imágenes con HTTP 422.
    """
    token = _create_token(
        user_id=901,
        tenant_id=TENANT_ALPHA,
        permissions=["procurement.invoices.ocr"],
    )
    headers = _make_headers(token, TENANT_ALPHA)

    # 1. Base64 inválido
    r_bad_b64 = await async_client.post(
        "/api/v1/procurement/invoices/ocr",
        headers=headers,
        json={
            "filename": "factura.pdf",
            "po_number": "OC-2026-001",
            "content_base64": "!!!NOT_VALID_BASE64!!!",
        },
    )
    assert r_bad_b64.status_code == 422

    # 2. Script malicioso (ELF o Bash) camuflado como PDF (base64 de '#!/bin/bash\nrm -rf /')
    fake_pdf_b64 = "IyEvYmluL2Jhc2gKcm0gLXJmIC8="
    r_bad_magic = await async_client.post(
        "/api/v1/procurement/invoices/ocr",
        headers=headers,
        json={
            "filename": "factura_camuflada.pdf",
            "po_number": "OC-2026-001",
            "content_base64": fake_pdf_b64,
        },
    )
    assert r_bad_magic.status_code == 422
    assert r_bad_magic.json()["error_code"] == "EXECUTABLE_SPOOFING_BLOCKED"
