"""
oppytec-backend/tests/unit/modules/test_invoices_services.py
Pruebas unitarias de servicios de aplicación para el Módulo de Facturas y Contabilidad:
- InvoiceService: Creación, recálculos matemáticos con Decimal (Neto + IVA = Total con tolerancia 1 CLP).
- SupplierAliasService: Memoria asociativa de productos con catálogo y resolución de nombres.
- InvoiceIngestionService: Traspaso a existencias físicas de cocina con factor de empaque y costo unitario.
- PriceDriftService: Detección y semaforización de sobreprecios contra historial.
- DTEExportService: Generación y formato de libros contables para SII Chile (F29 CSV), QuickBooks, Xero, Odoo.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.invoices.application.schemas import (
    DashboardStatsDTO,
    InvoiceCreateDTO,
    InvoiceLineItemCreateDTO,
    InvoiceLineItemUpdateDTO,
    InvoiceUpdateDTO,
)
from src.modules.invoices.application.services import (
    DTEExportService,
    InvoiceIngestionService,
    InvoiceService,
    PriceDriftService,
    SupplierAliasService,
)
from src.modules.invoices.domain.entities import (
    Invoice,
    InvoiceAuditFlag,
    InvoiceLineItem,
    SupplierProductAlias,
)
from src.modules.invoices.domain.exceptions import (
    InvalidInvoiceStatusTransitionError,
    InvoiceDomainError,
)
from src.modules.invoices.domain.value_objects import (
    AuditRuleCode,
    AuditSeverity,
    DTEType,
    InvoiceStatus,
    MatchStatus,
    TaxId,
)


@pytest.fixture
def mock_invoice_repo():
    repo = MagicMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.list = AsyncMock()
    repo.count = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_alias_repo():
    repo = MagicMock()
    repo.find_by_vendor_name = AsyncMock()
    repo.save_alias = AsyncMock()
    repo.list_by_supplier = AsyncMock()
    return repo


@pytest.fixture
def invoice_services(mock_invoice_repo, mock_alias_repo):
    alias_svc = SupplierAliasService(mock_alias_repo)
    drift_svc = PriceDriftService()
    ingest_svc = InvoiceIngestionService(mock_invoice_repo)
    inv_svc = InvoiceService(mock_invoice_repo, alias_svc, drift_svc, ingest_svc)
    return inv_svc, alias_svc, drift_svc, ingest_svc


@pytest.mark.asyncio
async def test_create_invoice_and_recalculate_totals(invoice_services, mock_invoice_repo):
    inv_svc, _, _, _ = invoice_services
    mock_invoice_repo.save.side_effect = lambda inv: inv

    dto = InvoiceCreateDTO(
        vendor_name="DISTRIBUIDORA ALIMENTOS SA",
        vendor_tax_id="76123456-0",
        invoice_number="FAC-10023",
        lines=[
            InvoiceLineItemCreateDTO(
                raw_description="CARNE MOLIDA VACUNO ESPECIAL",
                quantity=Decimal("10.0000"),
                unit_price=Decimal("5000.0000"),
                line_total=Decimal("50000.0000"),
                packaging_factor=Decimal("1.0000"),
            ),
            InvoiceLineItemCreateDTO(
                raw_description="ACEITE MARAVILLA 5L",
                quantity=Decimal("2.0000"),
                unit_price=Decimal("10000.0000"),
                line_total=Decimal("20000.0000"),
                packaging_factor=Decimal("5.0000"),
            ),
        ],
    )

    created = await inv_svc.create_invoice(
        tenant_id=str(uuid4()),
        dto=dto,
    )

    assert created.vendor_name == "DISTRIBUIDORA ALIMENTOS SA"
    assert created.invoice_number == "FAC-10023"
    assert created.net_amount == Decimal("70000.0000")
    assert created.tax_amount == Decimal("13300.0000")  # 19% de 70000
    assert created.total_amount == Decimal("83300.0000")
    assert len(created.lines) == 2
    # Verificación de existencias físicas
    # Línea 2: 2 bidones de 5L con factor 5.0 => 10 unidades de inventario
    assert created.lines[1].calculated_stock_qty == Decimal("10.0000")
    assert created.lines[1].inventory_unit_cost == Decimal("2000.0000")


@pytest.mark.asyncio
async def test_supplier_alias_learning_and_matching(invoice_services, mock_alias_repo):
    _, alias_svc, _, _ = invoice_services
    tenant_id = str(uuid4())
    supplier_id = uuid4()
    catalog_item_id = uuid4()

    # 1. Simular que no existe y aprender
    mock_alias_repo.find_by_vendor_name.return_value = None
    mock_alias_repo.save_alias.side_effect = lambda al: al

    learned = await alias_svc.learn_alias(
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        raw_vendor_name="PECHUGA DESHUESADA 20KG",
        catalog_item_id=catalog_item_id,
        default_packaging_factor=Decimal("20.0000"),
        default_inventory_unit="kg",
    )

    assert learned.catalog_item_id == catalog_item_id
    assert learned.default_packaging_factor == Decimal("20.0000")
    assert learned.default_inventory_unit == "kg"
    assert learned.times_used == 1

    # 2. Simular resolución posterior con el alias guardado
    mock_alias_repo.find_by_vendor_name.return_value = learned
    mock_session = AsyncMock()

    m_status, cat_id, conf, factor, unit = await alias_svc.resolve_line_match(
        session=mock_session,
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        raw_description="PECHUGA DESHUESADA 20KG",
    )

    assert m_status == MatchStatus.EXACT_ALIAS
    assert cat_id == catalog_item_id
    assert conf == Decimal("1.0000")
    assert factor == Decimal("20.0000")
    assert unit == "kg"


@pytest.mark.asyncio
async def test_invoice_stock_ingestion(invoice_services, mock_invoice_repo):
    _, _, _, ingest_svc = invoice_services
    invoice_id = uuid4()
    bodega_id = uuid4()

    mock_invoice = Invoice(
        id=invoice_id,
        vendor_name="PROVEEDOR CENTRAL",
        vendor_tax_id=TaxId("76543210-3"),
        invoice_number="FAC-8899",
        lines=[
            InvoiceLineItem(
                raw_description="CAJA TOMATES 18KG",
                quantity=Decimal("3.0000"),
                unit_price=Decimal("18000.0000"),
                line_total=Decimal("54000.0000"),
                packaging_factor=Decimal("18.0000"),
                inventory_unit="kg",
            )
        ],
    )
    mock_invoice_repo.get_by_id.return_value = mock_invoice
    mock_invoice_repo.save.side_effect = lambda inv: inv
    mock_session = AsyncMock()

    ingested = await ingest_svc.auto_ingest_to_inventory(
        session=mock_session,
        tenant_id=str(uuid4()),
        invoice_id=invoice_id,
        bodega_id=bodega_id,
        user_id=1,
    )

    assert ingested.is_confirmed_to_inventory is True
    assert ingested.status == InvoiceStatus.CONFIRMED_STOCK
    assert ingested.confirmed_bodega_id == bodega_id
    # Stock físico = 3 cajas * 18 kg = 54 kg
    assert ingested.lines[0].calculated_stock_qty == Decimal("54.0000")
    # Costo unitario = 54000 / 54 = 1000 CLP / kg
    assert ingested.lines[0].inventory_unit_cost == Decimal("1000.0000")

    # Intentar re-ingresar debe fallar
    with pytest.raises(InvalidInvoiceStatusTransitionError):
        await ingest_svc.auto_ingest_to_inventory(
            session=mock_session,
            tenant_id=str(uuid4()),
            invoice_id=invoice_id,
            bodega_id=bodega_id,
        )


def test_price_drift_service():
    drift_svc = PriceDriftService()

    # Caso 1: Variación normal (< 10%)
    drift_normal = drift_svc.calculate_drift(
        new_unit_cost=Decimal("1050.0000"),
        historical_unit_cost=Decimal("1000.0000"),
    )
    assert drift_normal.is_drift is False
    assert drift_normal.severity == AuditSeverity.INFO

    # Caso 2: Advertencia (15%)
    drift_warning = drift_svc.calculate_drift(
        new_unit_cost=Decimal("1150.0000"),
        historical_unit_cost=Decimal("1000.0000"),
    )
    assert drift_warning.is_drift is True
    assert drift_warning.severity == AuditSeverity.WARNING

    # Caso 3: Crítico (30%)
    drift_critical = drift_svc.calculate_drift(
        new_unit_cost=Decimal("1300.0000"),
        historical_unit_cost=Decimal("1000.0000"),
    )
    assert drift_critical.is_critical is True
    assert drift_critical.severity == AuditSeverity.CRITICAL

    flag = drift_svc.check_and_create_audit_flag(
        invoice_id=uuid4(),
        raw_description="ACEITE DE OLIVA 5L",
        drift=drift_critical,
    )
    assert flag is not None
    assert flag.severity == AuditSeverity.CRITICAL
    assert flag.rule_code == AuditRuleCode.PRICE_DRIFT_HIGH
    assert "30" in flag.message


def test_dte_export_service():
    invoices = [
        Invoice(
            id=uuid4(),
            vendor_name="HARINAS DEL SUR LTDA",
            vendor_tax_id=TaxId("77889900-0"),
            invoice_number="FAC-456",
            invoice_date=datetime(2026, 11, 4, 12, 0, tzinfo=UTC),
            due_date=datetime(2026, 11, 24, 12, 0, tzinfo=UTC),
            net_amount=Decimal("100000.0000"),
            tax_amount=Decimal("19000.0000"),
            total_amount=Decimal("119000.0000"),
            dte_type=DTEType.FACTURA_ELECTRONICA,
            status=InvoiceStatus.APPROVED,
        )
    ]

    # 1. Export SII CSV
    sii_csv = DTEExportService.export_sii_csv(invoices)
    assert "Tipo DTE;Folio Documento;RUT Proveedor" in sii_csv
    assert "33;FAC-456;77.889.900-0;HARINAS DEL SUR LTDA" in sii_csv
    assert "100000.00;19000.00;119000.00" in sii_csv

    # 2. Export QuickBooks CSV
    qb_csv = DTEExportService.export_quickbooks_csv(invoices)
    assert "Vendor,Invoice Number,Date,Due Date" in qb_csv
    assert "HARINAS DEL SUR LTDA,FAC-456" in qb_csv

    # 3. Export Xero CSV
    xero_csv = DTEExportService.export_xero_csv(invoices)
    assert "*ContactName,*InvoiceNumber,*InvoiceDate" in xero_csv
    assert "HARINAS DEL SUR LTDA,FAC-456" in xero_csv

    # 4. Export Odoo CSV
    odoo_csv = DTEExportService.export_odoo_csv(invoices)
    assert "partner_id/name,ref,invoice_date" in odoo_csv
    assert "HARINAS DEL SUR LTDA,FAC-456" in odoo_csv


@pytest.mark.asyncio
async def test_invoice_creation_and_fx_conversion_bcch(invoice_services, mock_invoice_repo):
    """Verifica que una factura en USD o EUR adopta la tasa oficial BCCh y realiza conversión Decimal exacta."""
    inv_svc, _, _, _ = invoice_services
    mock_invoice_repo.save.side_effect = lambda inv: inv

    # 1. Factura en USD sin exchange_rate explícito -> adquiere BCCh oficial (950.00000000)
    dto_usd = InvoiceCreateDTO(
        vendor_name="GLOBAL FOODS CORP",
        vendor_tax_id="55667788-3",
        invoice_number="USD-9901",
        currency="USD",
        lines=[
            InvoiceLineItemCreateDTO(
                raw_description="IMPORT SPECIAL GRAINS",
                quantity=Decimal("100.0000"),
                unit_price=Decimal("12.5000"),
                line_total=Decimal("1250.0000"),
            )
        ],
        net_amount=Decimal("1250.0000"),
        tax_amount=Decimal("237.5000"),
        total_amount=Decimal("1487.5000"),
    )

    created_usd = await inv_svc.create_invoice(tenant_id="tenant_alpha", dto=dto_usd)
    assert created_usd.currency == "USD"
    assert created_usd.exchange_rate == Decimal("950.00000000")

    # 2. Conversión a CLP con Decimal estricto
    clp_total = inv_svc.convert_amount_to_clp(created_usd.total_amount, "USD")
    # 1487.5000 * 950 = 1413125 CLP (sin coma flotante)
    assert clp_total == Decimal("1413125")
    assert isinstance(clp_total, Decimal)

    # 3. Conversión de EUR a CLP con tasa BCCh (1035.50000000)
    eur_amount = Decimal("200.00")
    clp_eur = inv_svc.convert_amount_to_clp(eur_amount, "EUR")
    # 200 * 1035.5 = 207100 CLP
    assert clp_eur == Decimal("207100")


def test_price_drift_multi_currency_fx():
    """Verifica que PriceDriftService convierte new_currency a historical_currency usando FX BCCh."""
    drift_svc = PriceDriftService()

    # Histórico en CLP = 9,500 CLP por kg
    # Nuevo precio en USD = 11.00 USD por kg (11 * 950 = 10,450 CLP, alza de 10%)
    drift = drift_svc.calculate_drift(
        new_unit_cost=Decimal("11.0000"),
        historical_unit_cost=Decimal("9500.0000"),
        new_currency="USD",
        historical_currency="CLP",
    )

    assert drift.new_price == Decimal("10450")
    assert drift.last_price == Decimal("9500.0000")
    assert drift.is_drift is True
    assert drift.severity == AuditSeverity.WARNING  # 10% de variación

    # Con tasa personalizada (ej: USD a CLP 1000.0000) y alza crítica >= 25% (12.50 * 1000 = 12500 vs 9500 = 31.57%)
    drift_custom = drift_svc.calculate_drift(
        new_unit_cost=Decimal("12.5000"),
        historical_unit_cost=Decimal("9500.0000"),
        new_currency="USD",
        historical_currency="CLP",
        exchange_rate=Decimal("1000.0000"),
    )
    assert drift_custom.new_price == Decimal("12500.0000")
    assert drift_custom.is_critical is True
    assert drift_custom.severity == AuditSeverity.CRITICAL


@pytest.mark.asyncio
async def test_update_invoice_currency_fx(invoice_services, mock_invoice_repo):
    """Verifica que actualizar la moneda a EUR resuelva la tasa oficial BCCh."""
    inv_svc, _, _, _ = invoice_services
    existing_inv = Invoice(
        id=uuid4(),
        tenant_id="tenant_beta",
        vendor_name="IMPORTS EU",
        vendor_tax_id=TaxId("76111222-8"),
        invoice_number="INV-EUR-01",
        currency="CLP",
        exchange_rate=Decimal("1.0000"),
        net_amount=Decimal("10000.0000"),
        tax_amount=Decimal("1900.0000"),
        total_amount=Decimal("11900.0000"),
        dte_type=DTEType.FACTURA_ELECTRONICA,
        status=InvoiceStatus.PENDING,
    )
    mock_invoice_repo.get_by_id.return_value = existing_inv
    mock_invoice_repo.save.side_effect = lambda inv: inv

    updated = await inv_svc.update_invoice(
        invoice_id=existing_inv.id,
        dto=InvoiceUpdateDTO(currency="EUR"),
    )

    assert updated.currency == "EUR"
    assert updated.exchange_rate == Decimal("1035.50000000")

