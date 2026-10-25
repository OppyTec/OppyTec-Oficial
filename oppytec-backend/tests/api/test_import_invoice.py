"""
oppytec-backend/tests/api/test_import_invoice.py
Pruebas para el módulo de Ingesta Inteligente de Facturas (PDF y XML DTE):
- POST /api/v1/inventory/import/parse-invoice:
  * Validación de magic bytes reales (rechazo de ejecutables ELF/MZ con EXECUTABLE_SPOOFING_BLOCKED)
  * Aceptación y parseo de PDF con extracción de metadatos y líneas heurísticas
  * Aceptación y parseo de XML DTE con extracción de RUT, Razón Social, Folio, Montos y Detalle
- POST /api/v1/inventory/import/confirm-invoice:
  * Integración con catálogo (producto existente y nuevo con create_if_missing=True)
  * Registro atómico de movimientos de entrada en Kardex por bodega
"""
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from src.core.security import create_access_token

pytestmark = pytest.mark.unit

TENANT_ID = "tenant_invoice_import_test"


def _headers(permissions: list[str]) -> dict[str, str]:
    token = create_access_token(
        user_id=303,
        tenant_id=TENANT_ID,
        holding_id="holding_invoices",
        role_grants=permissions,
        accessible_tenants=[TENANT_ID],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


@pytest.mark.asyncio
async def test_parse_invoice_blocks_executables(async_client: httpx.AsyncClient) -> None:
    """Verifica que ejecutables (.exe con 'MZ' o ELF con '\\x7fELF') sean bloqueados con HTTP 422."""
    headers = _headers(["inventory.import.parse"])

    # 1. Payload ejecutable ELF
    elf_content = b"\x7fELF\x02\x01\x01\x00malicious_code_here"
    files = {"file": ("factura.pdf", elf_content, "application/pdf")}
    resp = await async_client.post(
        "/api/v1/inventory/import/parse-invoice",
        headers=headers,
        files=files,
    )
    assert resp.status_code == 422
    err = resp.json()
    assert err["error_code"] == "EXECUTABLE_SPOOFING_BLOCKED"

    # 2. Payload ejecutable Windows MZ
    mz_content = b"MZ\x90\x00\x03\x00\x00\x00malicious_pe"
    files_mz = {"file": ("factura.xml", mz_content, "application/xml")}
    resp_mz = await async_client.post(
        "/api/v1/inventory/import/parse-invoice",
        headers=headers,
        files=files_mz,
    )
    assert resp_mz.status_code == 422
    assert resp_mz.json()["error_code"] == "EXECUTABLE_SPOOFING_BLOCKED"


@pytest.mark.asyncio
async def test_parse_invoice_pdf_success(async_client: httpx.AsyncClient) -> None:
    """Verifica que un archivo PDF válido sea aceptado y devuelva metadatos y líneas extraídas."""
    headers = _headers(["inventory.import.parse"])

    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    files = {"file": ("factura_proveedor_123.pdf", pdf_content, "application/pdf")}

    resp = await async_client.post(
        "/api/v1/inventory/import/parse-invoice",
        headers=headers,
        files=files,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["mime_type"] == "application/pdf"
    assert data["filename"] == "factura_proveedor_123.pdf"
    assert data["rut_proveedor"] != ""
    assert data["razon_social"] != ""
    assert len(data["lines"]) >= 1
    assert Decimal(data["monto_total"]) > Decimal("0")


@pytest.mark.asyncio
async def test_parse_invoice_xml_dte_success(async_client: httpx.AsyncClient) -> None:
    """Verifica la extracción de metadatos y líneas desde un XML DTE chileno."""
    headers = _headers(["inventory.import.parse"])

    xml_dte = (
        b"<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>\n"
        b"<DTE version=\"1.0\">\n"
        b"  <Documento ID=\"F12345T33\">\n"
        b"    <Encabezado>\n"
        b"      <IdDoc>\n"
        b"        <TipoDTE>33</TipoDTE>\n"
        b"        <Folio>12345</Folio>\n"
        b"      </IdDoc>\n"
        b"      <Emisor>\n"
        b"        <RUTEmisor>76.999.888-5</RUTEmisor>\n"
        b"        <RznSoc>Distribuidora Del Sur SpA</RznSoc>\n"
        b"      </Emisor>\n"
        b"      <Totales>\n"
        b"        <MntNeto>50000</MntNeto>\n"
        b"        <IVA>9500</IVA>\n"
        b"        <MntTotal>59500</MntTotal>\n"
        b"      </Totales>\n"
        b"    </Encabezado>\n"
        b"    <Detalle>\n"
        b"      <NroLinDet>1</NroLinDet>\n"
        b"      <NmbItem>Lomo Vetado Vacuno 1kg</NmbItem>\n"
        b"      <QtyItem>5</QtyItem>\n"
        b"      <PrcItem>10000</PrcItem>\n"
        b"      <MontoItem>50000</MontoItem>\n"
        b"    </Detalle>\n"
        b"  </Documento>\n"
        b"</DTE>"
    )

    files = {"file": ("factura_33_12345.xml", xml_dte, "application/xml")}
    resp = await async_client.post(
        "/api/v1/inventory/import/parse-invoice",
        headers=headers,
        files=files,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["mime_type"] == "application/xml"
    assert data["folio"] == "12345"
    assert data["rut_proveedor"] == "76.999.888-5"
    assert data["razon_social"] == "Distribuidora Del Sur SpA"
    assert Decimal(data["monto_neto"]) == Decimal("50000.00")
    assert Decimal(data["monto_iva"]) == Decimal("9500.00")
    assert Decimal(data["monto_total"]) == Decimal("59500.00")

    assert len(data["lines"]) == 1
    line1 = data["lines"][0]
    assert line1["descripcion"] == "Lomo Vetado Vacuno 1kg"
    assert Decimal(line1["cantidad"]) == Decimal("5")
    assert Decimal(line1["precio_unitario"]) == Decimal("10000")
    assert Decimal(line1["total_linea"]) == Decimal("50000")


@pytest.mark.asyncio
async def test_confirm_invoice_integrates_with_catalog_and_kardex(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica confirmación de factura: creación de productos y movimientos en Kardex."""
    headers = _headers(["inventory.import.confirm", "catalog.products.create"])

    # 1. Crear primero un producto previo en el catálogo
    prod_resp = await async_client.post(
        "/api/v1/catalog/products",
        headers=_headers(["catalog.products.create"]),
        json={
            "nombre": "Mantequilla con Sal 250g",
            "sku": "MAN-SAL-001",
            "costo_unitario": "1500.00",
            "precio_venta": "2200.00",
        },
    )
    assert prod_resp.status_code == 201
    existing_prod_id = prod_resp.json()["id"]

    # 2. Confirmar factura con 1 producto existente y 1 producto nuevo (create_if_missing=True)
    payload = {
        "supplier": {
            "rut": "76.999.888-5",
            "nombre": "Distribuidora Del Sur SpA",
        },
        "bodega_id": 1,
        "folio": "F-9901",
        "items": [
            {
                "producto_id": existing_prod_id,
                "descripcion": "Mantequilla con Sal 250g",
                "cantidad": "20.0000",
                "costo_unitario": "1450.00",
                "create_if_missing": False,
            },
            {
                "producto_id": None,
                "descripcion": "Crema de Leche 1L",
                "cantidad": "10.0000",
                "costo_unitario": "2800.00",
                "create_if_missing": True,
                "sku": "CRE-LEC-001",
            },
        ],
    }

    resp = await async_client.post(
        "/api/v1/inventory/import/confirm-invoice",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["folio"] == "F-9901"
    assert data["processed_items"] == 2
    assert len(data["kardex_movements"]) == 2
    # Costo total registrado: 20 * 1450 + 10 * 2800 = 29000 + 28000 = 57000
    assert Decimal(data["total_registered_cost"]) == Decimal("57000.00")

    # Verificar que los movimientos de Kardex son de tipo 'ENTRADA'
    for m in data["kardex_movements"]:
        assert m["movement_type"] == "ENTRADA"
        assert m["bodega_id"] == 1
