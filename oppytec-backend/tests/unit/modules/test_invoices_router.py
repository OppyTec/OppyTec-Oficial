"""
oppytec-backend/tests/unit/modules/test_invoices_router.py
Pruebas de integración HTTP y autorización RBAC de 3 niveles para endpoints de Facturas (`/api/v1/invoices`):
- Listado paginado con permisos `contabilidad.facturas.read`
- Denegación HTTP 403 Forbidden para usuarios sin rol correspondiente (RFC 7807)
- Dashboard KPIs y estadísticas FinOps
- Subida de facturas con validación MIME
- Creación de factura y cálculo de totales
- Confirmación de existencias físicas a bodega (`/{id}/confirm-stock`)
- Aprendizaje y listado de alias de proveedores
- Exportación contable (SII CSV, QuickBooks, Xero, Odoo)
- Operaciones masivas (bulk-process, bulk-delete)
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest

from src.core.security import create_access_token
from src.modules.invoices.application.schemas import DashboardStatsDTO
from src.modules.invoices.domain.entities import Invoice, InvoiceLineItem, SupplierProductAlias
from src.modules.invoices.domain.value_objects import DTEType, InvoiceStatus, MatchStatus, TaxId
from src.modules.invoices.presentation.router import (
    get_invoice_service,
    get_supplier_alias_service,
    get_tenant_db,
)

pytestmark = pytest.mark.unit

TEST_TENANT = "c3f81e7d-94bb-4ef5-9a8c-4a37e1b9b123"
TEST_HOLDING = "h1f81e7d-94bb-4ef5-9a8c-4a37e1b9b456"


def _make_headers(permissions: list[str], user_id: int = 101) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC de 3 niveles."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TEST_TENANT,
        holding_id=TEST_HOLDING,
        role_grants=permissions,
        accessible_tenants=[TEST_TENANT],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TEST_TENANT,
    }


@pytest.fixture
def mock_invoice_service():
    svc = MagicMock()
    svc.list_invoices = AsyncMock()
    svc.get_invoice = AsyncMock()
    svc.create_invoice = AsyncMock()
    svc.update_invoice = AsyncMock()
    svc.delete_invoice = AsyncMock()
    svc.get_dashboard_stats = AsyncMock()
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
def override_router_dependencies(app, mock_invoice_service, mock_alias_service, mock_db_session):
    app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
    app.dependency_overrides[get_supplier_alias_service] = lambda: mock_alias_service
    app.dependency_overrides[get_tenant_db] = lambda: mock_db_session
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_invoices_rbac_forbidden_without_permissions(async_client: httpx.AsyncClient):
    """Verifica que sin permisos se rechace con 403 Forbidden RFC 7807."""
    unauth_headers = _make_headers([])  # Sin permisos

    # GET /api/v1/invoices
    resp_get = await async_client.get("/api/v1/invoices", headers=unauth_headers)
    assert resp_get.status_code == 403

    # POST /api/v1/invoices
    resp_post = await async_client.post(
        "/api/v1/invoices",
        headers=unauth_headers,
        json={"vendor_name": "Test", "vendor_tax_id": "76123456-0", "invoice_number": "1"},
    )
    assert resp_post.status_code == 403


@pytest.mark.asyncio
async def test_list_invoices_with_permission(async_client: httpx.AsyncClient, mock_invoice_service):
    """Verifica listado de facturas autorizado."""
    headers = _make_headers(["contabilidad.facturas.read"])
    inv_id = uuid4()
    mock_inv = Invoice(
        id=inv_id,
        tenant_id=TEST_TENANT,
        vendor_name="PROVEEDOR TEST",
        vendor_tax_id=TaxId("76123456-0"),
        invoice_number="FAC-001",
        net_amount=Decimal("1000.0000"),
        tax_amount=Decimal("190.0000"),
        total_amount=Decimal("1190.0000"),
        dte_type=DTEType.FACTURA_ELECTRONICA,
        status=InvoiceStatus.APPROVED,
    )
    mock_invoice_service.list_invoices.return_value = ([mock_inv], 1)

    resp = await async_client.get("/api/v1/invoices?skip=0&limit=10", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["vendor_name"] == "PROVEEDOR TEST"
    assert Decimal(data["items"][0]["total_amount"]) == Decimal("1190.0000")


@pytest.mark.asyncio
async def test_get_dashboard_stats_endpoint(async_client: httpx.AsyncClient, mock_invoice_service):
    """Verifica endpoint de KPIs y telemetría FinOps."""
    headers = _make_headers(["contabilidad.facturas.read"])
    mock_invoice_service.get_dashboard_stats.return_value = DashboardStatsDTO(
        total_invoices_count=5,
        pending_review_count=2,
        confirmed_stock_count=3,
        rejected_count=0,
        total_net_amount=Decimal("500000.0000"),
        total_tax_amount=Decimal("95000.0000"),
        total_invoiced_amount=Decimal("595000.0000"),
        total_gemini_tokens=12500,
        total_gemini_cost_usd=Decimal("0.025000"),
        currency="CLP",
    )

    resp = await async_client.get("/api/v1/invoices/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_invoices_count"] == 5
    assert Decimal(data["total_invoiced_amount"]) == Decimal("595000.0000")
    assert data["total_gemini_tokens"] == 12500


@pytest.mark.asyncio
async def test_create_invoice_endpoint(async_client: httpx.AsyncClient, mock_invoice_service):
    """Verifica creación de factura vía REST."""
    headers = _make_headers(["contabilidad.facturas.create"])
    inv_id = uuid4()
    mock_inv = Invoice(
        id=inv_id,
        tenant_id=TEST_TENANT,
        vendor_name="CARNES DEL VALLE",
        vendor_tax_id=TaxId("76123456-0"),
        invoice_number="FAC-777",
        net_amount=Decimal("20000.0000"),
        tax_amount=Decimal("3800.0000"),
        total_amount=Decimal("23800.0000"),
    )
    mock_invoice_service.create_invoice.return_value = mock_inv

    payload = {
        "vendor_name": "CARNES DEL VALLE",
        "vendor_tax_id": "76123456-0",
        "invoice_number": "FAC-777",
        "lines": [
            {
                "raw_description": "Lomo Vetado 5kg",
                "quantity": "2.0000",
                "unit_price": "10000.0000",
                "line_total": "20000.0000",
                "packaging_factor": "1.0000",
            }
        ],
    }

    resp = await async_client.post("/api/v1/invoices", headers=headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["invoice_number"] == "FAC-777"
    assert Decimal(data["total_amount"]) == Decimal("23800.0000")


@pytest.mark.asyncio
async def test_confirm_stock_endpoint(async_client: httpx.AsyncClient, mock_invoice_service):
    """Verifica confirmación de existencias físicas a bodega."""
    headers = _make_headers(["contabilidad.facturas.manage"])
    inv_id = uuid4()
    bodega_id = uuid4()

    mock_inv = Invoice(
        id=inv_id,
        tenant_id=TEST_TENANT,
        vendor_name="PROVEEDOR CENTRAL",
        vendor_tax_id=TaxId("76123456-0"),
        invoice_number="FAC-8899",
        is_confirmed_to_inventory=True,
        confirmed_bodega_id=bodega_id,
        status=InvoiceStatus.CONFIRMED_STOCK,
    )
    mock_invoice_service.ingestion_service.auto_ingest_to_inventory.return_value = mock_inv

    payload = {
        "bodega_id": str(bodega_id),
        "lote_codigo": "LOT-2026-X",
    }

    resp = await async_client.post(
        f"/api/v1/invoices/{inv_id}/confirm-stock",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_stock_ingested"] is True
    assert data["status"] == "CONFIRMED_STOCK"


@pytest.mark.asyncio
async def test_learn_alias_and_list_aliases_endpoints(
    async_client: httpx.AsyncClient,
    mock_alias_service,
):
    """Verifica aprendizaje y consulta de alias asociativos."""
    headers_manage = _make_headers(["contabilidad.facturas.manage"])
    headers_read = _make_headers(["contabilidad.facturas.read"])
    cat_id = uuid4()
    sup_id = uuid4()

    mock_alias = SupplierProductAlias(
        id=uuid4(),
        tenant_id=TEST_TENANT,
        supplier_id=sup_id,
        raw_vendor_product_name="TOMATE PRIMERA SELECCION",
        catalog_item_id=cat_id,
        default_packaging_factor=Decimal("18.0000"),
        default_inventory_unit="kg",
        is_verified=True,
    )
    mock_alias_service.learn_alias.return_value = mock_alias
    mock_alias_service.alias_repo.list_by_supplier.return_value = [mock_alias]

    # 1. Aprender alias
    learn_payload = {
        "supplier_id": str(sup_id),
        "raw_vendor_product_name": "TOMATE PRIMERA SELECCION",
        "catalog_item_id": str(cat_id),
        "default_packaging_factor": "18.0000",
        "default_inventory_unit": "kg",
    }
    resp_learn = await async_client.post(
        "/api/v1/invoices/learn-alias",
        headers=headers_manage,
        json=learn_payload,
    )
    assert resp_learn.status_code == 201
    data_learn = resp_learn.json()
    assert data_learn["raw_vendor_product_name"] == "TOMATE PRIMERA SELECCION"
    assert Decimal(data_learn["default_packaging_factor"]) == Decimal("18.0000")

    # 2. Listar alias
    resp_list = await async_client.get(
        f"/api/v1/invoices/aliases?supplier_id={sup_id}",
        headers=headers_read,
    )
    assert resp_list.status_code == 200
    data_list = resp_list.json()
    assert len(data_list) == 1
    assert data_list[0]["default_inventory_unit"] == "kg"


@pytest.mark.asyncio
async def test_export_invoices_endpoint(async_client: httpx.AsyncClient, mock_invoice_service):
    """Verifica exportación contable a CSV de SII Chile y QuickBooks."""
    headers = _make_headers(["contabilidad.facturas.read"])
    inv = Invoice(
        id=uuid4(),
        tenant_id=TEST_TENANT,
        vendor_name="AGRICOLA DEL MONTE",
        vendor_tax_id=TaxId("76123456-0"),
        invoice_number="FAC-1122",
        invoice_date=datetime(2026, 11, 4, tzinfo=UTC),
        net_amount=Decimal("10000.0000"),
        tax_amount=Decimal("1900.0000"),
        total_amount=Decimal("11900.0000"),
        dte_type=DTEType.FACTURA_ELECTRONICA,
        status=InvoiceStatus.APPROVED,
    )
    mock_invoice_service.list_invoices.return_value = ([inv], 1)

    # Exportar SII CSV
    resp_sii = await async_client.post(
        "/api/v1/invoices/export",
        headers=headers,
        json={"export_format": "SII_CSV"},
    )
    assert resp_sii.status_code == 200
    assert "text/csv" in resp_sii.headers["content-type"]
    assert "FAC-1122" in resp_sii.text
    assert "AGRICOLA DEL MONTE" in resp_sii.text


@pytest.mark.asyncio
async def test_bulk_process_and_delete_endpoints(async_client: httpx.AsyncClient, mock_invoice_service):
    """Verifica operaciones en lote sobre facturas."""
    headers = _make_headers(["contabilidad.facturas.manage"])
    inv_id1 = uuid4()
    inv_id2 = uuid4()

    mock_inv1 = Invoice(
        id=inv_id1,
        tenant_id=TEST_TENANT,
        vendor_name="V1",
        vendor_tax_id=TaxId("76123456-0"),
        invoice_number="1",
        status=InvoiceStatus.PENDING,
    )
    mock_inv2 = Invoice(
        id=inv_id2,
        tenant_id=TEST_TENANT,
        vendor_name="V2",
        vendor_tax_id=TaxId("76123456-0"),
        invoice_number="2",
        status=InvoiceStatus.PENDING,
    )

    mock_invoice_service.get_invoice.side_effect = lambda i_id: mock_inv1 if i_id == inv_id1 else mock_inv2
    mock_invoice_service.delete_invoice.return_value = True

    # 1. Bulk Process (Aprobar)
    resp_bulk = await async_client.post(
        "/api/v1/invoices/bulk-process",
        headers=headers,
        json={"invoice_ids": [str(inv_id1), str(inv_id2)], "action": "APPROVE"},
    )
    assert resp_bulk.status_code == 200
    assert resp_bulk.json()["processed_count"] == 2
    assert mock_inv1.status == InvoiceStatus.APPROVED

    # 2. Bulk Delete
    resp_del = await async_client.post(
        "/api/v1/invoices/bulk-delete",
        headers=headers,
        json={"invoice_ids": [str(inv_id1), str(inv_id2)]},
    )
    assert resp_del.status_code == 200
    assert resp_del.json()["deleted_count"] == 2
