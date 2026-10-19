"""
Flujo E2E 02: Compra, Factura OCR, Conciliación de 3 Vías e Ingreso a Kardex
(`tests/e2e/test_e2e_02_purchase_reception_to_kardex_stock.py`).

Recorre el flujo completo de abastecimiento a bodega:
1. Conversión de unidades en 3 capas (`Compra -> Almacén -> Porción/Receta`) en `/api/v1/catalog/units/convert`.
2. Alta de producto en catálogo con marca comercial protegida `"Pollo King"` (`/api/v1/catalog/products`).
3. Emisión de Orden de Compra preservando `"Pollo King"` (`/api/v1/procurement/orders`).
4. Ingesta de factura OCR validando *Magic Bytes* PDF (`/api/v1/procurement/invoices/ocr`).
5. Conciliación de 3 vías (`OC vs Recepción vs Factura`) tanto `MATCHED` como `MISMATCH` (`/api/v1/procurement/receptions/reconcile`).
6. Ingreso efectivo a Kardex (`ENTRADA`) y verificación del libro mayor (`/api/v1/inventory/kardex/movements`).
"""
from __future__ import annotations

import base64
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.main import create_app

pytestmark = pytest.mark.e2e


def test_e2e_02_purchase_reception_ocr_reconciliation_and_kardex_entry() -> None:
    """
    Verifica extremo a extremo el ciclo de abastecimiento con precisión `Decimal` 100% paritaria con Legacy.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()
    app = create_app()

    buyer_token = create_access_token(
        user_id=210,
        holding_id="holding_e2e_02",
        tenant_id="tenant_e2e_02",
        hierarchy_rank=15,
        contracted_modules=["catalog", "procurement", "inventory"],
        role_grants=[
            "catalog.units.convert",
            "catalog.products.create",
            "catalog.products.read",
            "procurement.orders.create",
            "procurement.orders.read",
            "procurement.invoices.ocr",
            "procurement.receptions.reconcile",
            "inventory.kardex.write",
            "inventory.kardex.read",
        ],
        accessible_tenants=["tenant_e2e_02"],
    )
    headers = {
        "Authorization": f"Bearer {buyer_token}",
        "X-Tenant-ID": "tenant_e2e_02",
    }

    with TestClient(app) as client:
        # 1. Conversión de unidades en 3 capas: 5 cajas de 10 kg a CLP 60.000 c/u -> 50 kg a CLP 6.000/kg -> 50.000 g a CLP 6/g
        conv_resp = client.post(
            "/api/v1/catalog/units/convert",
            headers=headers,
            json={
                "cantidad_compra": "5",
                "costo_compra_neto": "60000",
                "factor_compra_a_almacen": "10",
                "factor_almacen_a_receta": "1000",
            },
        )
        assert conv_resp.status_code == 200
        conv_data = conv_resp.json()
        assert Decimal(conv_data["cantidad_almacen"]) == Decimal("50.0000")
        assert Decimal(conv_data["cantidad_receta"]) == Decimal("50000.0000")
        assert Decimal(conv_data["costo_unitario_almacen"]) == Decimal("6000.0000")
        assert Decimal(conv_data["costo_unitario_receta"]) == Decimal("6.0000")

        # 2. Alta de insumo con marca comercial protegida `"Pollo King"`
        prod_resp = client.post(
            "/api/v1/catalog/products",
            headers=headers,
            json={
                "sku": "PK-PECHUGA-10KG",
                "nombre": "Pechuga Deshuesada",
                "marca_comercial": "Pollo King",
                "unidad_compra": "caja",
                "unidad_almacen": "kg",
                "unidad_receta": "g",
                "factor_compra_a_almacen": "10",
                "factor_almacen_a_receta": "1000",
                "costo_compra_neto": "60000",
            },
        )
        assert prod_resp.status_code == 201
        prod_body = prod_resp.json()
        producto_id = int(prod_body["product_id"])
        assert prod_body["marca_comercial"] == "Pollo King"
        assert Decimal(prod_body["costo_unitario_almacen"]) == Decimal("6000.0000")

        # 3. Creación de Orden de Compra para `"Pollo King"` por 50 kg a CLP 6.000/kg = CLP 300.000
        po_resp = client.post(
            "/api/v1/procurement/orders",
            headers=headers,
            json={
                "po_number": "OC-E2E-2026-002",
                "supplier_id": 901,
                "supplier_name": "Pollo King",
                "lines": [
                    {
                        "producto_id": producto_id,
                        "quantity": "50",
                        "unit_cost": "6000",
                    }
                ],
            },
        )
        assert po_resp.status_code == 201
        po_body = po_resp.json()
        assert po_body["supplier_name"] == "Pollo King"
        assert Decimal(po_body["net_total"]) == Decimal("300000.00")

        # 4. Ingesta de factura OCR con Magic Bytes `%PDF-1.7` válidos
        valid_pdf_b64 = base64.b64encode(b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n").decode("ascii")
        ocr_resp = client.post(
            "/api/v1/procurement/invoices/ocr",
            headers=headers,
            json={
                "po_number": "OC-E2E-2026-002",
                "filename": "factura_electronica_pollo_king.pdf",
                "content_base64": valid_pdf_b64,
            },
        )
        assert ocr_resp.status_code == 200
        assert ocr_resp.json()["verified_mime_type"] == "application/pdf"
        assert int(ocr_resp.json()["extracted_lines"]) >= 1

        # 5. Conciliación de 3 vías: caso con discrepancia (`MISMATCH`) y caso exacto (`MATCHED`)
        reconcile_mismatch = client.post(
            "/api/v1/procurement/receptions/reconcile",
            headers=headers,
            json={
                "po_number": "OC-E2E-2026-002",
                "order_lines": [{"producto_id": producto_id, "quantity": "50", "unit_cost": "6000"}],
                "receipt_lines": [{"producto_id": producto_id, "quantity": "45", "unit_cost": "6000"}],
                "invoice_lines": [{"producto_id": producto_id, "quantity": "50", "unit_cost": "6000"}],
            },
        )
        assert reconcile_mismatch.status_code == 200
        assert reconcile_mismatch.json()["status"] != "MATCHED"
        assert Decimal(reconcile_mismatch.json()["invoice_total_diff"]) == Decimal("30000.00")

        reconcile_matched = client.post(
            "/api/v1/procurement/receptions/reconcile",
            headers=headers,
            json={
                "po_number": "OC-E2E-2026-002",
                "order_lines": [{"producto_id": producto_id, "quantity": "50", "unit_cost": "6000"}],
                "receipt_lines": [{"producto_id": producto_id, "quantity": "50", "unit_cost": "6000"}],
                "invoice_lines": [{"producto_id": producto_id, "quantity": "50", "unit_cost": "6000"}],
            },
        )
        assert reconcile_matched.status_code == 200
        assert reconcile_matched.json()["status"] == "MATCHED"
        assert Decimal(reconcile_matched.json()["invoice_total_diff"]) == Decimal("0.00")

        # 6. Ingreso a Kardex tras recepción conforme (`ENTRADA` de 50 kg en bodega 10)
        kardex_entry = client.post(
            "/api/v1/inventory/kardex/movements",
            headers=headers,
            json={
                "producto_id": producto_id,
                "bodega_id": 10,
                "movement_type": "ENTRADA",
                "quantity": "50",
                "unit_cost": "6000",
            },
        )
        assert kardex_entry.status_code == 201
        assert Decimal(kardex_entry.json()["resulting_balance"]) == Decimal("50")

        kardex_ledger = client.get("/api/v1/inventory/kardex/movements", headers=headers)
        assert kardex_ledger.status_code == 200
        assert any(
            int(m["producto_id"]) == producto_id and int(m["bodega_id"]) == 10
            for m in kardex_ledger.json()
        )
