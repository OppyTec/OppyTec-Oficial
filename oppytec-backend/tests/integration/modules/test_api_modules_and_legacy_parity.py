"""
Pruebas de Integración End-to-End de los 10 Módulos y Paridad Matemática 100% con `OppyTec-Legacy`
(`tests/integration/modules/test_api_modules_and_legacy_parity.py`).

Verifica los 10 routers (`identity`, `tenancy`, `audit`, `catalog`, `inventory`, `recipes`,
`procurement`, `operations`, `analytics`, `oppy_ai`) con precisión `Decimal` exacta:
- Conversión de unidades en 3 capas (`Compra -> Almacén -> Porción/Receta`).
- Costeo recursivo de escandallos (sub-recetas + merma técnica) y simulación de margen / Food Cost %.
- Movimientos Kardex Append-Only, toma física con orden canónico (`ORDER BY id ASC`) y umbral de aprobación de mermas con segregación de funciones.
- Órdenes de compra con nombre comercial inmutable (`"Pollo King"`), conciliación de 3 vías (`OC vs Recepción vs Factura`) y validación Magic Bytes en OCR.
- Explosión de ventas POS, Buffet por comensal (`pax`) descontando sobrante reutilizable y eventos de banquetería.
- Resumen ejecutivo de control de pérdidas y varianza de Food Cost en puntos porcentuales.
- Billetera de créditos `OppyFy` sin caducidad, redacción dinámica de costos (`[REDACTED_COST]` vs costo visible) y bitácora global `llm_request_logs`.
"""
from __future__ import annotations

import base64
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.core.config import get_settings
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.main import create_app

pytestmark = pytest.mark.integration

_ALL_CONTRACTED_MODULES: list[str] = [
    "catalog",
    "inventory",
    "recipes",
    "procurement",
    "operations",
    "analytics",
    "oppyfy",
    "audit",
    "settings",
    "tenancy",
]

_OPERATOR_GRANTS: list[str] = [
    "catalog.products.create",
    "catalog.products.read",
    "catalog.units.convert",
    "catalog.products.import_excel",
    "catalog.media.upload",
    "inventory.kardex.write",
    "inventory.kardex.read",
    "inventory.counts.submit",
    "inventory.mermas.create",
    "inventory.mermas.approve",
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
    "audit.rbac_ledger.append",
    "audit.activity_ledger.read",
    "audit.activity_ledger.append",
    "tenancy.quotas.read",
    "tenancy.storage_quotas.read",
    "settings.roles.read",
    "settings.roles.manage",
    "settings.rbac.delegate_subordinates",
]


def test_catalog_recipes_and_inventory_legacy_mathematical_parity() -> None:
    """
    Verifica paridad matemática 100% con `OppyTec-Legacy` en:
    1. `catalog`: conversión de 3 capas (`Compra -> Almacén -> Porción/Receta`) en `Decimal`.
    2. `recipes`: escandallo recursivo (sub-receta salsa + insumo principal con `%` merma) y simulador de margen.
    3. `inventory`: Kardex, conteo con bloqueo canónico `ASC` y flujo de merma sobre umbral (`> 50.000`) aprobado por supervisor distinto.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()
    app = create_app()

    operator_token = create_access_token(
        user_id=301,
        holding_id="holding_parity",
        tenant_id="tenant_parity",
        hierarchy_rank=20,
        contracted_modules=_ALL_CONTRACTED_MODULES,
        role_grants=_OPERATOR_GRANTS,
        accessible_tenants=["tenant_parity"],
    )
    supervisor_token = create_access_token(
        user_id=302,
        holding_id="holding_parity",
        tenant_id="tenant_parity",
        hierarchy_rank=10,
        contracted_modules=_ALL_CONTRACTED_MODULES,
        role_grants=_OPERATOR_GRANTS,
        accessible_tenants=["tenant_parity"],
    )
    op_headers = {
        "Authorization": f"Bearer {operator_token}",
        "X-Tenant-ID": "tenant_parity",
    }
    sup_headers = {
        "Authorization": f"Bearer {supervisor_token}",
        "X-Tenant-ID": "tenant_parity",
    }

    with TestClient(app) as client:
        # 1. Catalog: Conversión de 3 capas (Caja 12 kg a CLP 96.000 -> Almacén: 1 kg a CLP 8.000 -> Receta: 1 g a CLP 8)
        conv_resp = client.post(
            "/api/v1/catalog/units/convert",
            headers=op_headers,
            json={
                "cantidad_compra": "3",
                "costo_compra_neto": "96000",
                "factor_compra_a_almacen": "12",
                "factor_almacen_a_receta": "1000",
            },
        )
        assert conv_resp.status_code == 200
        conv_data = conv_resp.json()
        assert Decimal(conv_data["cantidad_almacen"]) == Decimal("36.0000")
        assert Decimal(conv_data["cantidad_receta"]) == Decimal("36000.0000")
        assert Decimal(conv_data["costo_unitario_almacen"]) == Decimal("8000.0000")
        assert Decimal(conv_data["costo_unitario_receta"]) == Decimal("8.0000")

        prod_resp = client.post(
            "/api/v1/catalog/products",
            headers=op_headers,
            json={
                "sku": "CAR-LOMO-01",
                "nombre": "Filete de Res",
                "marca_comercial": "Pollo King",
                "unidad_compra": "caja",
                "unidad_almacen": "kg",
                "unidad_receta": "g",
                "factor_compra_a_almacen": "12",
                "factor_almacen_a_receta": "1000",
                "costo_compra_neto": "96000",
            },
        )
        assert prod_resp.status_code == 201
        prod_data = prod_resp.json()
        assert prod_data["marca_comercial"] == "Pollo King"
        assert Decimal(prod_data["costo_unitario_almacen"]) == Decimal("8000.0000")
        assert Decimal(prod_data["costo_unitario_receta"]) == Decimal("8.0000")

        list_prod = client.get("/api/v1/catalog/products", headers=op_headers)
        assert list_prod.status_code == 200
        assert len(list_prod.json()) >= 1

        # 2. Recipes: Sub-receta base (`recipe_id=501`, rinde 2 porciones, costo total 2.000 -> 1.000 por porción)
        sub_resp = client.post(
            "/api/v1/recipes/escandallos",
            headers=op_headers,
            json={
                "recipe_id": 501,
                "name": "Salsa Demi-Glace Base",
                "yield_portions": "2",
                "net_price": "4000",
                "lines": [
                    {
                        "ingredient_id": 9001,
                        "quantity": "0.50",
                        "unit_cost": "4000",
                        "waste_pct": "0",
                    }
                ],
            },
        )
        assert sub_resp.status_code == 201
        assert Decimal(sub_resp.json()["portion_cost"]) == Decimal("1000.0000")

        # Receta principal (`recipe_id=502`) que usa 1 porción de la sub-receta `501` (costo 1.000)
        # + 0.20 kg de Filete con 25% de merma técnica (`0.20 * (1 + 0.25) = 0.25 kg` * 8.000 = 2.000)
        # Costo total por porción = 1.000 + 2.000 = 3.000. Precio venta neto = 10.000 -> Food Cost = 30.00%
        main_resp = client.post(
            "/api/v1/recipes/escandallos",
            headers=op_headers,
            json={
                "recipe_id": 502,
                "name": "Filete Mignon con Demi-Glace",
                "yield_portions": "1",
                "net_price": "10000",
                "lines": [
                    {
                        "sub_recipe_id": 501,
                        "quantity": "1",
                        "unit_cost": "0",
                        "waste_pct": "0",
                    },
                    {
                        "ingredient_id": 9002,
                        "quantity": "0.20",
                        "unit_cost": "8000",
                        "waste_pct": "25",
                    },
                ],
            },
        )
        assert main_resp.status_code == 201
        main_data = main_resp.json()
        assert Decimal(main_data["portion_cost"]) == Decimal("3000.0000")
        assert Decimal(main_data["food_cost_pct"]) == Decimal("30.00")
        assert Decimal(main_data["margin_amount"]) == Decimal("7000.00")
        assert Decimal(main_data["margin_pct"]) == Decimal("70.00")

        sim_resp = client.post(
            "/api/v1/recipes/simulate-margin",
            headers=op_headers,
            json={
                "portion_cost": "3000",
                "proposed_net_price": "12000",
            },
        )
        assert sim_resp.status_code == 200
        sim_data = sim_resp.json()
        assert Decimal(sim_data["food_cost_pct"]) == Decimal("25.00")
        assert Decimal(sim_data["margin_amount"]) == Decimal("9000.00")
        assert Decimal(sim_data["margin_pct"]) == Decimal("75.00")

        # 3. Inventory: Movimientos Kardex, conteo físico ordenado `ASC` y flujo de aprobación de merma
        kardex_in = client.post(
            "/api/v1/inventory/kardex/movements",
            headers=op_headers,
            json={
                "producto_id": 701,
                "bodega_id": 2,
                "movement_type": "ENTRADA",
                "quantity": "20",
                "unit_cost": "8000",
            },
        )
        assert kardex_in.status_code == 201
        assert Decimal(kardex_in.json()["resulting_balance"]) == Decimal("20")

        kardex_out = client.post(
            "/api/v1/inventory/kardex/movements",
            headers=op_headers,
            json={
                "producto_id": 701,
                "bodega_id": 2,
                "movement_type": "SALIDA",
                "quantity": "5",
                "unit_cost": "8000",
            },
        )
        assert kardex_out.status_code == 201
        assert Decimal(kardex_out.json()["resulting_balance"]) == Decimal("15")

        count_resp = client.post(
            "/api/v1/inventory/counts",
            headers=op_headers,
            json={
                "bodega_id": 2,
                "items": [
                    {"producto_id": 750, "counted_quantity": "8", "unit_cost": "1500"},
                    {"producto_id": 701, "counted_quantity": "18", "unit_cost": "8000"},
                    {"producto_id": 710, "counted_quantity": "12", "unit_cost": "3200"},
                ],
            },
        )
        assert count_resp.status_code == 200
        assert count_resp.json()["locked_product_ids_asc"] == [701, 710, 750]

        # Merma de alto valor (`10 * 8.000 = 80.000 > 50.000`) -> queda `PENDIENTE`
        merma_create = client.post(
            "/api/v1/inventory/mermas",
            headers=op_headers,
            json={
                "producto_id": 701,
                "bodega_id": 2,
                "quantity": "10",
                "unit_cost": "8000",
                "reason": "Rotura de compresor en cámara frigorífica principal",
            },
        )
        assert merma_create.status_code == 201
        merma_body = merma_create.json()
        assert merma_body["status"] == "PENDIENTE"
        assert Decimal(merma_body["total_cost"]) == Decimal("80000.00")
        waste_id = int(merma_body["waste_id"])

        # Aprobación por supervisor distinto (`user_id=302 != reporter 301`) -> `APROBADA`
        merma_approve = client.post(
            f"/api/v1/inventory/mermas/{waste_id}/approve",
            headers=sup_headers,
            json={"unit_cost": "8000"},
        )
        assert merma_approve.status_code == 200
        assert merma_approve.json()["status"] == "APROBADA"


def test_procurement_operations_analytics_oppyfy_audit_tenancy_and_identity_e2e() -> None:
    """
    Verifica extremo a extremo los módulos `procurement`, `operations`, `analytics`,
    `oppy_ai` (`OppyFy`), `audit`, `tenancy` e `identity`.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()
    app = create_app()

    operator_token = create_access_token(
        user_id=401,
        holding_id="holding_parity",
        tenant_id="tenant_parity",
        hierarchy_rank=15,
        contracted_modules=_ALL_CONTRACTED_MODULES,
        role_grants=_OPERATOR_GRANTS,
        accessible_tenants=["tenant_parity"],
    )
    op_headers = {
        "Authorization": f"Bearer {operator_token}",
        "X-Tenant-ID": "tenant_parity",
    }

    with TestClient(app) as client:
        # 1. Procurement: OC con preservación histórica de `"Pollo King"`, conciliación 3 vías y OCR PDF
        po_first = client.post(
            "/api/v1/procurement/orders",
            headers=op_headers,
            json={
                "po_number": "OC-PARITY-100",
                "supplier_id": 888,
                "supplier_name": "Pollo King",
                "lines": [
                    {"producto_id": 701, "quantity": "15", "unit_cost": "8000"},
                    {"producto_id": 710, "quantity": "10", "unit_cost": "3000"},
                ],
            },
        )
        assert po_first.status_code == 201
        assert po_first.json()["supplier_name"] == "Pollo King"
        assert Decimal(po_first.json()["net_total"]) == Decimal("150000.00")

        # Conciliación exacta (`MATCHED`) y conciliación con discrepancia (`MISMATCH`)
        rec_match = client.post(
            "/api/v1/procurement/receptions/reconcile",
            headers=op_headers,
            json={
                "po_number": "OC-PARITY-100",
                "order_lines": [{"producto_id": 701, "quantity": "15", "unit_cost": "8000"}],
                "receipt_lines": [{"producto_id": 701, "quantity": "15", "unit_cost": "8000"}],
                "invoice_lines": [{"producto_id": 701, "quantity": "15", "unit_cost": "8000"}],
            },
        )
        assert rec_match.status_code == 200
        assert rec_match.json()["status"] == "MATCHED"
        assert Decimal(rec_match.json()["invoice_total_diff"]) == Decimal("0.00")

        rec_diff = client.post(
            "/api/v1/procurement/receptions/reconcile",
            headers=op_headers,
            json={
                "po_number": "OC-PARITY-100",
                "order_lines": [{"producto_id": 701, "quantity": "15", "unit_cost": "8000"}],
                "receipt_lines": [{"producto_id": 701, "quantity": "12", "unit_cost": "8000"}],
                "invoice_lines": [{"producto_id": 701, "quantity": "15", "unit_cost": "8000"}],
            },
        )
        assert rec_diff.status_code == 200
        assert rec_diff.json()["status"] != "MATCHED"
        assert Decimal(rec_diff.json()[" invoice_total_diff".strip()]) == Decimal("24000.00")

        pdf_b64 = base64.b64encode(b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n").decode("ascii")
        ocr_resp = client.post(
            "/api/v1/procurement/invoices/ocr",
            headers=op_headers,
            json={
                "po_number": "OC-PARITY-100",
                "filename": "factura_pollo_king.pdf",
                "content_base64": pdf_b64,
            },
        )
        assert ocr_resp.status_code == 200
        assert ocr_resp.json()["verified_mime_type"] == "application/pdf"

        # 2. Operations: Explosión de venta POS, Buffet por Pax y Evento de Banquetería
        pos_resp = client.post(
            "/api/v1/operations/sales",
            headers=op_headers,
            json={
                "bodega_id": 2,
                "items": [{"recipe_id": 502, "portions": "4"}],
                "recipe_ingredients": {"502": {"701": "0.25", "710": "0.10"}},
            },
        )
        assert pos_resp.status_code == 201
        consumed = pos_resp.json()["consumed_by_ingredient"]
        assert Decimal(consumed["701"]) == Decimal("1.0000")
        assert Decimal(consumed["710"]) == Decimal("0.4000")

        buffet_resp = client.post(
            "/api/v1/operations/buffet",
            headers=op_headers,
            json={
                "service_name": "Buffet Corporativo Almuerzo",
                "total_buffet_cost": "420000",
                "pax": 80,
                "leftover_value": "60000",
            },
        )
        assert buffet_resp.status_code == 200
        assert Decimal(buffet_resp.json()["cost_per_pax"]) == Decimal("4500.00")

        event_resp = client.post(
            "/api/v1/operations/events",
            headers=op_headers,
            json={
                "event_name": "Cena Anual Directorio",
                "attendees_pax": 120,
                "food_cost_per_pax": "8500",
                "net_price_per_pax": "25000",
            },
        )
        assert event_resp.status_code == 201
        assert Decimal(event_resp.json()["total_food_cost"]) == Decimal("1020000.00")
        assert Decimal(event_resp.json()["total_net_revenue"]) == Decimal("3000000.00")
        assert Decimal(event_resp.json()["gross_margin"]) == Decimal("1980000.00")

        # 3. Analytics: Resumen Ejecutivo y Varianza de Food Cost
        variance_resp = client.post(
            "/api/v1/analytics/food-cost-variance",
            headers=op_headers,
            json={
                "theoretical_cost": "280000",
                "opening_inventory": "100000",
                "purchases": "315000",
                "closing_inventory": "100000",
                "net_sales": "1000000",
            },
        )
        assert variance_resp.status_code == 200
        var_data = variance_resp.json()
        assert Decimal(var_data["theoretical_pct"]) == Decimal("28.00")
        assert Decimal(var_data["actual_pct"]) == Decimal("31.50")
        assert Decimal(var_data["variance_pp"]) == Decimal("3.50")

        # 4. OppyFy (`oppy_ai`): Billetera de créditos, dominios RBAC y chat con/sin permiso de ver costos
        wallet_resp = client.get("/api/v1/oppyfy/credits/wallet", headers=op_headers)
        assert wallet_resp.status_code == 200
        assert Decimal(wallet_resp.json()["remaining_credits"]) == Decimal("87.50")

        domains_resp = client.get("/api/v1/oppyfy/rbac/domains", headers=op_headers)
        assert domains_resp.status_code == 200
        assert len(domains_resp.json()) == 3

        chat_redacted = client.post(
            "/api/v1/oppyfy/chat",
            headers=op_headers,
            json={
                "prompt_text": "¿Cómo preparar Filete Mignon con Demi-Glace?",
                "target_subdomain_slug": "recipes_kitchen",
                "can_view_costs": False,
                "estimated_credit_cost": "2.50",
                "remaining_credits": "50.00",
            },
        )
        assert chat_redacted.status_code == 200
        assert chat_redacted.json()["allowed"] is True
        assert "[REDACTED_COST]" in chat_redacted.json()["answer_text"]
        assert Decimal(chat_redacted.json()["remaining_credits"]) == Decimal("47.50")

        chat_with_cost = client.post(
            "/api/v1/oppyfy/chat",
            headers=op_headers,
            json={
                "prompt_text": "¿Cuál es el costo por porción del Filete Mignon?",
                "target_subdomain_slug": "recipes_kitchen",
                "can_view_costs": True,
                "estimated_credit_cost": "2.50",
                "remaining_credits": "47.50",
            },
        )
        assert chat_with_cost.status_code == 200
        assert "CLP 1.450" in chat_with_cost.json()["answer_text"]
        assert Decimal(chat_with_cost.json()["remaining_credits"]) == Decimal("45.00")

        # 5. Audit: Doble libro forense Append-Only (RBAC + Actividad) e inmutabilidad ante DELETE
        rbac_audit_post = client.post(
            "/api/v1/audit/rbac",
            headers=op_headers,
            json={
                "target_user_id": 450,
                "action_type": "GRANT_ISSUED",
                "permission_or_role": "inventory.mermas.approve",
                "before_state": {"granted": False},
                "after_state": {"granted": True},
                "scope": "tenant",
            },
        )
        assert rbac_audit_post.status_code == 201

        act_audit_post = client.post(
            "/api/v1/audit/activity",
            headers=op_headers,
            json={
                "action_code": "recipes.escandallos.write",
                "resource_type": "recipe",
                "resource_id": "502",
                "before_state": {},
                "after_state": {"portion_cost": "3000.0000"},
                "scope": "tenant",
            },
        )
        assert act_audit_post.status_code == 201
        evt_uuid = act_audit_post.json()["event_uuid"]

        del_attempt = client.delete(f"/api/v1/audit/activity/{evt_uuid}", headers=op_headers)
        assert del_attempt.status_code == 403
        assert del_attempt.json()["error_code"] == "AUDIT_APPEND_ONLY_VIOLATION"

        # 6. Identity & Tenancy (Plano Global con SuperUser Génesis): Login, Holdings, Tenants y Telemetría LLM
        settings = get_settings()
        login_resp = client.post(
            "/api/v1/auth/login",
            json={
                "username_or_email": settings.SUPERUSER_GENESIS_USERNAME,
                "password": settings.SUPERUSER_GENESIS_PASSWORD.get_secret_value(),
                "tenant_id": "tenant_genesis",
            },
        )
        assert login_resp.status_code == 200
        god_access_token = login_resp.json()["access_token"]
        god_headers = {"Authorization": f"Bearer {god_access_token}"}

        holding_resp = client.post(
            "/api/v1/tenancy/holdings",
            headers=god_headers,
            json={
                "name": "Grupo Gastronómico Andino",
                "plan_slug": "enterprise",
                "max_active_users": 50,
                "max_storage_mb": 4096,
            },
        )
        assert holding_resp.status_code == 201
        created_holding_id = holding_resp.json()["holding_id"]

        tenant_resp = client.post(
            "/api/v1/tenancy/tenants",
            headers=god_headers,
            json={
                "holding_id": created_holding_id,
                "slug": "andino_flagship",
                "display_name": "Andino Flagship Vitacura",
                "base_currency": "CLP",
            },
        )
        assert tenant_resp.status_code == 201
        assert tenant_resp.json()["schema_name"] == "tenant_andino_flagship"

        telemetry_resp = client.get("/api/v1/oppyfy/telemetry/logs", headers=god_headers)
        assert telemetry_resp.status_code == 200
        assert len(telemetry_resp.json()) >= 2

        jit_resp = client.post(
            "/api/v1/identity/grants/jit",
            headers=op_headers,
            json={
                "target_user_id": 499,
                "target_rank": 30,
                "permission_code": "inventory.mermas.approve",
                "effect": "ALLOW",
                "reason": "Delegación temporal por turno nocturno de inventario",
                "max_uses": 3,
            },
        )
        assert jit_resp.status_code == 201
        assert jit_resp.json()["permission_code"] == "inventory.mermas.approve"
