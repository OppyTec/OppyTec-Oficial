"""
Flujo E2E 04: Toma Física Canónica, Declaración/Aprobación de Mermas, Impacto en Food Cost y Auditoría
(`tests/e2e/test_e2e_04_merma_declaration_approval_and_audit.py`).

Recorre el flujo completo de control de pérdidas:
1. Toma física de inventario verificando el orden canónico anti-deadlock `ORDER BY producto_id ASC` (`/api/v1/inventory/counts`).
2. Declaración de merma bajo umbral (`<= 50.000`, aprobada automáticamente) y sobre umbral (`> 50.000`, queda `PENDIENTE`) en `/api/v1/inventory/mermas`.
3. Segregación de funciones: rechazo HTTP 403 cuando el mismo reportante intenta aprobar su propia merma, y aprobación exitosa (`APROBADA`) por un supervisor distinto en `/api/v1/inventory/mermas/{id}/approve`.
4. Impacto en varianza de Food Cost (`/api/v1/analytics/food-cost-variance`) y resumen ejecutivo de control de pérdidas (`/api/v1/analytics/executive-summary`).
5. Trazabilidad en el libro forense de actividad (`/api/v1/audit/activity`).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.main import create_app

pytestmark = pytest.mark.e2e


def test_e2e_04_merma_declaration_segregation_of_duties_analytics_and_audit() -> None:
    """
    Verifica extremo a extremo el flujo de conteo físico, mermas bajo/sobre umbral, segregación de funciones,
    impacto en Food Cost Variance y registro forense.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()
    app = create_app()

    reporter_token = create_access_token(
        user_id=411,
        holding_id="holding_e2e_04",
        tenant_id="tenant_e2e_04",
        hierarchy_rank=25,
        contracted_modules=["inventory", "analytics", "audit"],
        role_grants=[
            "inventory.counts.submit",
            "inventory.mermas.create",
            "inventory.mermas.approve",
            "inventory.kardex.read",
            "analytics.food_cost.read",
            "analytics.executive_summary.read",
            "audit.activity_ledger.append",
            "audit.activity_ledger.read",
        ],
        accessible_tenants=["tenant_e2e_04"],
    )
    supervisor_token = create_access_token(
        user_id=412,
        holding_id="holding_e2e_04",
        tenant_id="tenant_e2e_04",
        hierarchy_rank=15,
        contracted_modules=["inventory", "analytics", "audit"],
        role_grants=[
            "inventory.mermas.approve",
            "analytics.food_cost.read",
            "analytics.executive_summary.read",
            "audit.activity_ledger.append",
            "audit.activity_ledger.read",
        ],
        accessible_tenants=["tenant_e2e_04"],
    )
    reporter_headers = {
        "Authorization": f"Bearer {reporter_token}",
        "X-Tenant-ID": "tenant_e2e_04",
    }
    supervisor_headers = {
        "Authorization": f"Bearer {supervisor_token}",
        "X-Tenant-ID": "tenant_e2e_04",
    }

    with TestClient(app) as client:
        # 1. Conteo físico enviando IDs desordenados (`990, 910, 950`) -> bloquea en orden canónico `[910, 950, 990]`
        count_resp = client.post(
            "/api/v1/inventory/counts",
            headers=reporter_headers,
            json={
                "bodega_id": 4,
                "items": [
                    {"producto_id": 990, "counted_quantity": "12", "unit_cost": "4000"},
                    {"producto_id": 910, "counted_quantity": "25", "unit_cost": "10000"},
                    {"producto_id": 950, "counted_quantity": "15", "unit_cost": "2000"},
                ],
            },
        )
        assert count_resp.status_code == 200
        assert count_resp.json()["locked_product_ids_asc"] == [910, 950, 990]

        # 2. Merma bajo umbral (`2 * 10.000 = 20.000 <= 50.000`) -> se aprueba automáticamente (`APROBADA`)
        low_merma = client.post(
            "/api/v1/inventory/mermas",
            headers=reporter_headers,
            json={
                "producto_id": 910,
                "bodega_id": 4,
                "quantity": "2",
                "unit_cost": "10000",
                "reason": "Porcionado con exceso de grasa en cocina fría",
            },
        )
        assert low_merma.status_code == 201
        assert low_merma.json()["status"] == "APROBADA"
        assert Decimal(low_merma.json()["total_cost"]) == Decimal("20000.00")

        # 3. Merma sobre umbral (`8 * 10.000 = 80.000 > 50.000`) -> queda `PENDIENTE`
        high_merma = client.post(
            "/api/v1/inventory/mermas",
            headers=reporter_headers,
            json={
                "producto_id": 910,
                "bodega_id": 4,
                "quantity": "8",
                "unit_cost": "10000",
                "reason": "Corte de cadena de frío en recepción nocturna",
            },
        )
        assert high_merma.status_code == 201
        high_merma_data = high_merma.json()
        assert high_merma_data["status"] == "PENDIENTE"
        assert Decimal(high_merma_data["total_cost"]) == Decimal("80000.00")
        waste_id = int(high_merma_data["waste_id"])

        # Intento de auto-aprobación por el mismo usuario (`user_id=411`) -> bloqueado con HTTP 403
        self_approve = client.post(
            f"/api/v1/inventory/mermas/{waste_id}/approve",
            headers=reporter_headers,
            json={"unit_cost": "10000"},
        )
        assert self_approve.status_code == 403

        # Aprobación por supervisor distinto (`user_id=412`) -> `APROBADA`
        sup_approve = client.post(
            f"/api/v1/inventory/mermas/{waste_id}/approve",
            headers=supervisor_headers,
            json={"unit_cost": "10000"},
        )
        assert sup_approve.status_code == 200
        assert sup_approve.json()["status"] == "APROBADA"

        # 4. Impacto en Varianza de Food Cost y Resumen Ejecutivo de Control de Pérdidas
        variance_resp = client.post(
            "/api/v1/analytics/food-cost-variance",
            headers=supervisor_headers,
            json={
                "theoretical_cost": "300000",
                "opening_inventory": "150000",
                "purchases": "380000",
                "closing_inventory": "150000",
                "net_sales": "1000000",
            },
        )
        assert variance_resp.status_code == 200
        assert Decimal(variance_resp.json()["theoretical_pct"]) == Decimal("30.00")
        assert Decimal(variance_resp.json()["actual_pct"]) == Decimal("38.00")
        assert Decimal(variance_resp.json()["variance_pp"]) == Decimal("8.00")

        exec_resp = client.post(
            "/api/v1/analytics/executive-summary",
            headers=supervisor_headers,
            json={
                "theoretical_cost": "300000",
                "opening_inventory": "150000",
                "purchases": "380000",
                "closing_inventory": "150000",
                "net_sales": "1000000",
                "alert_threshold_pp": "2.50",
            },
        )
        assert exec_resp.status_code == 200
        assert exec_resp.json()["alert"] is True
        assert Decimal(exec_resp.json()["variance_pp"]) == Decimal("8.00")

        # 5. Registro forense en `/api/v1/audit/activity`
        audit_post = client.post(
            "/api/v1/audit/activity",
            headers=supervisor_headers,
            json={
                "action_code": "inventory.mermas.approve",
                "resource_type": "merma",
                "resource_id": str(waste_id),
                "before_state": {"status": "PENDIENTE"},
                "after_state": {"status": "APROBADA", "total_cost": "80000.00"},
                "scope": "tenant",
            },
        )
        assert audit_post.status_code == 201
        event_uuid = str(audit_post.json()["event_uuid"])

        audit_list = client.get("/api/v1/audit/activity", headers=supervisor_headers)
        assert audit_list.status_code == 200
        assert any(e["event_uuid"] == event_uuid for e in audit_list.json())
