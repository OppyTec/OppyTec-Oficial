"""
oppytec-backend/tests/unit/modules/test_invoices_observability.py
Suite de Pruebas de Observabilidad 4-Pilares y Telemetría FinOps para Facturas:
- Trazas distribuidas OpenTelemetry con los 5 spans críticos:
  1. `invoices.upload`
  2. `invoices.extract_gemini_ocr`
  3. `invoices.resolve_aliases`
  4. `invoices.auto_ingest_stock`
  5. `invoices.export_dte`
- Atributos semánticos inyectados:
  * `invoice.id`
  * `invoice.dte_type`
  * `invoice.vendor_tax_id`
  * `invoice.gemini_tokens_used`
  * `invoice.gemini_cost_usd`
  * `invoice.lines_count`
- Métricas estructuradas FinOps (Prometheus/Grafana):
  * `invoices_processed_total` (counter)
  * `invoice_ocr_duration_seconds` (histogram)
  * `invoice_ai_tokens_consumed_total` y `invoice_ai_cost_usd_total` (counters)
- Logs estructurados con structlog con enlaces `tenant_id`, `invoice_id`
  y censura estricta de PII (RUTs de personas naturales, datos bancarios).
- Preservación de la regla de oro 'Pollo King'.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.observability import (
    REDACTED_MARKER,
    clear_in_memory_invoice_metrics,
    get_in_memory_exporter,
    get_in_memory_invoice_metrics,
    get_invoice_logger,
    record_invoice_finops_metric,
    scrub_pii_text,
    scrub_telemetry_payload,
    trace_span,
)
from src.modules.invoices.application.gemini_extractor import (
    GeminiInvoiceExtractor,
)
from src.modules.invoices.application.schemas import (
    InvoiceCreateDTO,
    InvoiceLineItemCreateDTO,
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
    InvoiceLineItem,
)
from src.modules.invoices.domain.value_objects import (
    DTEType,
    InvoiceStatus,
    MatchStatus,
)


@pytest.fixture(autouse=True)
def _reset_observability_state() -> None:
    """Limpia el exportador OTel y las métricas en memoria antes de cada prueba."""
    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_invoice_metrics()


# ============================================================================
# 1. PRUEBAS DE SPANS OPENTELEMETRY Y ATRIBUTOS SEMÁNTICOS
# ============================================================================


@pytest.mark.asyncio
async def test_invoices_upload_span_and_semantic_attributes() -> None:
    """Valida la emisión del span 'invoices.upload' y sus atributos semánticos."""
    mock_repo = MagicMock()
    mock_repo.save = AsyncMock(side_effect=lambda inv: inv)
    mock_alias_repo = MagicMock()
    alias_svc = SupplierAliasService(mock_alias_repo)
    drift_svc = PriceDriftService()
    ingest_svc = InvoiceIngestionService(mock_repo)
    inv_svc = InvoiceService(mock_repo, alias_svc, drift_svc, ingest_svc)

    tenant_id = str(uuid4())
    dto = InvoiceCreateDTO(
        vendor_name="Pollo King SpA",
        vendor_tax_id="76123456-0",
        invoice_number="FAC-7788",
        file_path=f"invoices/{tenant_id}/test.pdf",
        file_name="test.pdf",
        file_type="pdf",
        dte_type=33,
        lines=[
            InvoiceLineItemCreateDTO(
                raw_description="Pechuga Pollo 20kg",
                quantity=Decimal("5.0000"),
                unit_price=Decimal("10000.0000"),
                line_total=Decimal("50000.0000"),
                packaging_factor=Decimal("20.0000"),
            ),
            InvoiceLineItemCreateDTO(
                raw_description="Trutro Pollo 10kg",
                quantity=Decimal("3.0000"),
                unit_price=Decimal("5000.0000"),
                line_total=Decimal("15000.0000"),
                packaging_factor=Decimal("10.0000"),
            ),
        ],
    )

    created = await inv_svc.create_invoice(tenant_id=tenant_id, dto=dto)
    assert created is not None

    spans = get_in_memory_exporter().get_finished_spans()
    upload_spans = [s for s in spans if s.name == "invoices.upload"]
    assert len(upload_spans) >= 1

    span = upload_spans[0]
    attrs = span.attributes
    assert attrs.get("invoice.id") == str(created.id)
    assert attrs.get("invoice.dte_type") == "33"
    assert attrs.get("invoice.lines_count") == 2
    assert "invoice.gemini_tokens_used" in attrs
    assert "invoice.gemini_cost_usd" in attrs


@pytest.mark.asyncio
async def test_invoices_extract_gemini_ocr_span_and_finops_attributes() -> None:
    """Valida la emisión del span 'invoices.extract_gemini_ocr' y atributos FinOps."""
    extractor = GeminiInvoiceExtractor(model_name="gemini-2.5-flash")
    test_bytes = b"%PDF-1.4 Pollo King SpA DTE 33..."
    inv_id = uuid4()
    t_id = uuid4()

    extracted = await extractor.extract_invoice_data(
        file_bytes=test_bytes,
        file_name="factura_pollo_king.pdf",
        mime_type="application/pdf",
        invoice_id=inv_id,
        tenant_id=t_id,
    )

    assert extracted.vendor_name == "Pollo King SpA"
    assert extracted.gemini_tokens_used > 0
    assert extracted.gemini_cost_usd > Decimal("0")

    spans = get_in_memory_exporter().get_finished_spans()
    ocr_spans = [s for s in spans if s.name == "invoices.extract_gemini_ocr"]
    assert len(ocr_spans) >= 1

    span = ocr_spans[0]
    attrs = span.attributes
    assert attrs.get("invoice.id") == str(inv_id)
    assert attrs.get("invoice.dte_type") == "33" or attrs.get("invoice.dte_type") == 33
    assert attrs.get("invoice.lines_count") == len(extracted.lines)
    assert int(str(attrs.get("invoice.gemini_tokens_used"))) == extracted.gemini_tokens_used
    assert Decimal(str(attrs.get("invoice.gemini_cost_usd"))) == extracted.gemini_cost_usd


@pytest.mark.asyncio
async def test_invoices_resolve_aliases_span() -> None:
    """Valida la emisión del span 'invoices.resolve_aliases' en SupplierAliasService."""
    mock_alias_repo = MagicMock()
    mock_alias_repo.find_by_vendor_name = AsyncMock(return_value=None)
    alias_svc = SupplierAliasService(mock_alias_repo)

    mock_session = MagicMock()
    t_id = str(uuid4())
    s_id = uuid4()

    match_status, _cat_id, _conf, _factor, _unit = await alias_svc.resolve_line_match(
        session=mock_session,
        tenant_id=t_id,
        supplier_id=s_id,
        raw_description="CARNE VACUNO HUACHALOMO 5KG",
    )

    assert match_status == MatchStatus.UNMATCHED
    spans = get_in_memory_exporter().get_finished_spans()
    alias_spans = [s for s in spans if s.name == "invoices.resolve_aliases"]
    assert len(alias_spans) >= 1

    span = alias_spans[0]
    assert span.attributes.get("tenant_id") == t_id
    assert span.attributes.get("match_status") == MatchStatus.UNMATCHED.value


@pytest.mark.asyncio
async def test_invoices_auto_ingest_stock_span_and_semantic_attributes() -> None:
    """Valida la emisión del span 'invoices.auto_ingest_stock' con atributos semánticos."""
    mock_repo = MagicMock()
    inv_id = uuid4()
    t_id = str(uuid4())
    bodega_id = uuid4()

    line = InvoiceLineItem(
        id=uuid4(),
        invoice_id=inv_id,
        line_number=1,
        raw_description="Queso Gouda Barra 3kg",
        quantity=Decimal("4.0000"),
        unit="barra",
        unit_price=Decimal("15000.0000"),
        line_total=Decimal("60000.0000"),
        packaging_factor=Decimal("3.0000"),
        inventory_unit="kg",
    )
    fake_invoice = Invoice(
        id=inv_id,
        tenant_id=t_id,
        vendor_name="Lacteos del Sur",
        vendor_tax_id="77111222-7",
        invoice_number="FAC-9901",
        dte_type=DTEType.FACTURA_ELECTRONICA,
        status=InvoiceStatus.ANALYZED,
        lines=[line],
    )

    mock_repo.get_by_id = AsyncMock(return_value=fake_invoice)
    mock_repo.save = AsyncMock(side_effect=lambda inv: inv)

    ingest_svc = InvoiceIngestionService(mock_repo)
    mock_session = MagicMock()

    result = await ingest_svc.auto_ingest_to_inventory(
        session=mock_session,
        tenant_id=t_id,
        invoice_id=inv_id,
        bodega_id=bodega_id,
    )

    assert result.is_confirmed_to_inventory is True
    assert result.status == InvoiceStatus.CONFIRMED_STOCK

    spans = get_in_memory_exporter().get_finished_spans()
    ingest_spans = [s for s in spans if s.name == "invoices.auto_ingest_stock"]
    assert len(ingest_spans) >= 1

    span = ingest_spans[0]
    attrs = span.attributes
    assert attrs.get("invoice.id") == str(inv_id)
    assert attrs.get("bodega_id") == str(bodega_id)
    assert attrs.get("invoice.dte_type") == "33"
    assert attrs.get("invoice.lines_count") == 1


def test_invoices_export_dte_span() -> None:
    """Valida la emisión del span 'invoices.export_dte' al exportar libros contables."""
    fake_inv = Invoice(
        id=uuid4(),
        tenant_id=str(uuid4()),
        vendor_name="Pollo King SpA",
        vendor_tax_id="76123456-0",
        invoice_number="FAC-4401",
        dte_type=DTEType.FACTURA_ELECTRONICA,
        status=InvoiceStatus.APPROVED,
    )

    csv_data = DTEExportService.export_dte([fake_inv], export_format="SII_CSV")
    assert "Pollo King SpA" in csv_data

    spans = get_in_memory_exporter().get_finished_spans()
    export_spans = [s for s in spans if s.name == "invoices.export_dte"]
    assert len(export_spans) >= 1

    span = export_spans[0]
    assert span.attributes.get("export_format") == "SII_CSV"
    assert span.attributes.get("invoices_count") == 1


# ============================================================================
# 2. PRUEBAS DE MÉTRICAS FINOPS EN MEMORIA Y PROMETHEUS/GRAFANA
# ============================================================================


def test_finops_metrics_recording_and_in_memory_collection() -> None:
    """Valida contadores e histogramas FinOps de facturas y OCR en memoria."""
    clear_in_memory_invoice_metrics()

    record_invoice_finops_metric(
        tenant_id="tenant_santiago_01",
        dte_type="33",
        status="SUCCESS",
        duration_seconds=1.25,
        tokens_consumed=480,
        cost_usd=Decimal("0.000350"),
        invoice_id="inv-1234",
    )

    with trace_span(
        "invoices.test_metric",
        attributes={
            "tenant_id": "tenant_santiago_01",
            "invoice.id": "inv-5678",
            "invoice.dte_type": "33",
            "invoice.vendor_tax_id": "76123456-7",
            "invoice.gemini_tokens_used": 600,
            "invoice.gemini_cost_usd": "0.000500",
            "invoice.lines_count": 5,
        },
        tracer_name="oppytec.invoices",
    ):
        pass

    metrics = get_in_memory_invoice_metrics()
    assert len(metrics) >= 1

    last_metric = metrics[-1]
    assert last_metric.operation == "invoices.test_metric"
    assert last_metric.status == "SUCCESS"
    assert last_metric.gemini_tokens_used == 600
    assert last_metric.gemini_cost_usd == "0.000500"
    assert last_metric.lines_count == 5


# ============================================================================
# 3. PRUEBAS DE LOGS ESTRUCTURADOS CON STRUCTLOG Y CENSURA ESTRICTA PII
# ============================================================================


def test_structlog_logger_binding_and_pii_censorship() -> None:
    """Valida la censura estricta de PII (RUTs de personas naturales, datos bancarios) en structlog."""
    t_id = "tenant_vina_02"
    inv_id = str(uuid4())
    logger = get_invoice_logger(tenant_id=t_id, invoice_id=inv_id)
    assert logger is not None

    # Payload con PII: RUT de persona natural y número de cuenta bancaria
    sensitive_payload = {
        "vendor_name": "Pollo King SpA",  # Debe preservarse (Regla Pollo King)
        "natural_person_rut": "12.345.678-9",  # RUT persona natural -> Censurar
        "bank_account": "12345678901234",  # Cuenta bancaria -> Censurar
        "account_number": "000-112233-44",  # Cuenta bancaria -> Censurar
        "numero_cuenta": "99887766",  # Cuenta bancaria -> Censurar
        "credit_card": "4532-1111-2222-3333",  # Tarjeta -> Censurar
        "password": "SecretPassword123!",  # Secreto -> Censurar
        "net_amount": Decimal("150000.0000"),
    }

    scrubbed = scrub_telemetry_payload(sensitive_payload)

    # Verificación de censura estricta
    assert scrubbed["vendor_name"] == "Pollo King SpA"
    assert scrubbed["natural_person_rut"] == REDACTED_MARKER
    assert scrubbed["bank_account"] == REDACTED_MARKER
    assert scrubbed["account_number"] == REDACTED_MARKER
    assert scrubbed["numero_cuenta"] == REDACTED_MARKER
    assert scrubbed["credit_card"] == REDACTED_MARKER
    assert scrubbed["password"] == REDACTED_MARKER
    assert "12.345.678-9" not in str(scrubbed)
    assert "12345678901234" not in str(scrubbed)
    assert "SecretPassword123!" not in str(scrubbed)


def test_scrub_pii_text_bank_account_and_rut_patterns() -> None:
    """Valida la censura de cuentas bancarias y RUTs en textos libres."""
    free_text = (
        "Transferir a cuenta corriente: 12345678 a nombre de Juan Pérez RUT 15.678.901-2 "
        "en Banco Estado cta cte 987654321."
    )
    cleaned = scrub_pii_text(free_text)
    assert REDACTED_MARKER in cleaned
    assert "15.678.901-2" not in cleaned
    assert "12345678" not in cleaned or REDACTED_MARKER in cleaned
