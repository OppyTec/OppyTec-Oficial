"""
oppytec-backend/tests/unit/modules/test_invoices_ai_and_tools.py
Pruebas unitarias para la Etapa 3 del módulo de Facturas y Contabilidad:
- Extractor multimodal Gemini (GeminiInvoiceExtractor) para DTEs chilenos.
- Medición de tokens y cálculo FinOps de costo en USD en `public.llm_request_logs`.
- Desacoplamiento de factores de empaque (packaging_factor) y validación RUT Módulo 11.
- Servicio `process_invoice` en InvoiceService.
- Herramientas operativas deterministas de OppyFy (`query_invoices_summary`, `get_supplier_price_drift_alerts`).
- Redacción RBAC en código duro (`[REDACTED_COST]`) y regla inmutable "Pollo King".
- Enrutamiento JEV en `OppyfyToolRouter`.
"""
from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.adapters.ai.jev_adapter import InMemoryTelemetrySink
from src.adapters.ai.jev_protocol import JevChoiceResult, JevDecisionPort
from src.modules.invoices.application.gemini_extractor import (
    ExtractedInvoiceData,
    GeminiInvoiceExtractor,
)
from src.modules.invoices.application.services import (
    InvoiceIngestionService,
    InvoiceService,
    PriceDriftService,
    SupplierAliasService,
)
from src.modules.invoices.domain.entities import Invoice
from src.modules.invoices.domain.value_objects import (
    InvoiceStatus,
    TaxId,
)
from src.modules.oppy_ai.application.operational_tools.invoice_tools import (
    get_supplier_price_drift_alerts,
    query_invoices_summary,
)
from src.modules.oppy_ai.application.tool_router import (
    HARD_CODED_TOOL_CATALOG,
    OppyfyToolRouter,
)
from src.modules.oppy_ai.domain.oppyfy_rbac import REDACTED_COST_MARKER

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_gemini_invoice_extractor_chilean_dte():
    """Verifica la extracción multimodal con GeminiInvoiceExtractor para un DTE chileno."""
    sink = InMemoryTelemetrySink()
    extractor = GeminiInvoiceExtractor(
        api_key="test_stub_key",
        model_name="gemini-2.5-flash",
        telemetry_sink=sink,
    )

    dummy_pdf_bytes = b"%PDF-1.4 Mock invoice content for Pollo King SpA with RUT 76.123.456-0"
    file_name = "factura_pollo_king_33.pdf"

    extracted: ExtractedInvoiceData = await extractor.extract_invoice_data(
        file_bytes=dummy_pdf_bytes,
        file_name=file_name,
        mime_type="application/pdf",
        tenant_schema="tenant_demo",
    )

    # 1. Verificación de invariante "Pollo King": no traducir nombres de proveedores
    assert "Pollo King" in extracted.vendor_name or "Distribuidora" in extracted.vendor_name

    # 2. Verificación de RUT chileno válido (Módulo 11)
    tax_id = TaxId(extracted.vendor_tax_id)
    assert tax_id.is_chilean is True
    assert tax_id.clean_tax_id == extracted.vendor_tax_id

    # 3. Verificación de DTE y montos
    assert extracted.dte_type == 33
    assert extracted.currency == "CLP"
    assert isinstance(extracted.net_amount, Decimal)
    assert isinstance(extracted.tax_amount, Decimal)
    assert isinstance(extracted.total_amount, Decimal)
    assert extracted.total_amount == extracted.net_amount + extracted.tax_amount

    # 4. Verificación de líneas y factor de empaque
    assert len(extracted.lines) >= 1
    for line in extracted.lines:
        assert isinstance(line.quantity, Decimal)
        assert isinstance(line.unit_price, Decimal)
        assert isinstance(line.line_total, Decimal)
        assert isinstance(line.packaging_factor, Decimal)
        assert line.packaging_factor > Decimal("0.0000")
        assert line.packaging_description is not None

    # 5. Verificación de telemetría FinOps en `llm_request_logs`
    assert extracted.gemini_tokens_used > 0
    assert isinstance(extracted.gemini_cost_usd, Decimal)
    assert extracted.gemini_cost_usd > Decimal("0.000000")

    records = sink.records
    assert len(records) == 1
    assert records[0].engine_tier == "SYSTEM_2_LLM"
    assert records[0].caller_feature == "invoice_multimodal_extractor"
    assert records[0].total_tokens == extracted.gemini_tokens_used
    assert records[0].provider_cost_usd == extracted.gemini_cost_usd


@pytest.mark.asyncio
async def test_gemini_invoice_extractor_finops_formula_precision():
    """Verifica la precisión matemática estricta (cero floats) del cálculo de costos FinOps."""
    sink = InMemoryTelemetrySink()
    in_cost_rate = Decimal("0.150000")
    out_cost_rate = Decimal("0.600000")

    extractor = GeminiInvoiceExtractor(
        api_key="test_stub_key",
        telemetry_sink=sink,
        input_cost_per_1m_usd=in_cost_rate,
        output_cost_per_1m_usd=out_cost_rate,
    )

    custom_payload = {
        "vendor_name": "Agroinsumos del Norte SpA",
        "vendor_tax_id": "76.456.789-7",
        "invoice_number": "FOLIO-9999",
        "dte_type": 33,
        "net_amount": "100000.0000",
        "tax_amount": "19000.0000",
        "total_amount": "119000.0000",
        "lines": [
            {
                "line_number": 1,
                "raw_description": "Caja de Tomates x 18 kg",
                "quantity": "2.0000",
                "unit": "caja",
                "unit_price": "50000.0000",
                "line_total": "100000.0000",
                "vat_rate": "19.00",
                "packaging_description": "Caja x 18 kg",
                "packaging_factor": "18.0000",
            }
        ],
    }
    encoded = json.dumps(custom_payload).encode("utf-8")

    result = await extractor.extract_invoice_data(
        file_bytes=encoded,
        file_name="factura_agro.json",
        mime_type="application/json",
    )

    assert result.vendor_name == "Agroinsumos del Norte SpA"
    assert result.vendor_tax_id == "76456789-7"
    assert result.lines[0].packaging_factor == Decimal("18.0000")
    assert result.lines[0].packaging_description == "Caja x 18 kg"

    # Verificar que el registro de telemetría coincide exactamente
    log = sink.records[0]
    expected_cost = (
        (Decimal(log.input_tokens) * in_cost_rate) + (Decimal(log.output_tokens) * out_cost_rate)
    ) / Decimal("1000000")
    expected_cost = expected_cost.quantize(Decimal("0.000001"))
    assert log.provider_cost_usd == expected_cost
    assert result.gemini_cost_usd == expected_cost


@pytest.mark.asyncio
async def test_invoice_service_process_invoice_orchestration():
    """Verifica que InvoiceService.process_invoice coordine la extracción, aliases y recálculo."""
    inv_repo = MagicMock()
    alias_repo = MagicMock()
    alias_svc = SupplierAliasService(alias_repo)
    drift_svc = PriceDriftService()
    ingest_svc = InvoiceIngestionService(inv_repo)

    sink = InMemoryTelemetrySink()
    extractor = GeminiInvoiceExtractor(
        api_key="test_stub_key",
        telemetry_sink=sink,
    )

    inv_svc = InvoiceService(
        invoice_repo=inv_repo,
        alias_service=alias_svc,
        price_drift_service=drift_svc,
        ingestion_service=ingest_svc,
        gemini_extractor=extractor,
    )

    inv_id = uuid4()
    t_id = "c3f81e7d-94bb-4ef5-9a8c-4a37e1b9b123"
    initial_invoice = Invoice(
        id=inv_id,
        tenant_id=t_id,
        vendor_name="PROVEEDOR PENDIENTE",
        vendor_tax_id="76000000-0",
        invoice_number="PENDING-001",
        file_name="factura_pollo_king.pdf",
        status=InvoiceStatus.UPLOADED,
    )

    inv_repo.get_by_id = AsyncMock(return_value=initial_invoice)
    inv_repo.save = AsyncMock(side_effect=lambda inv: inv)
    alias_repo.find_by_vendor_name = AsyncMock(return_value=None)

    session = AsyncMock()

    processed = await inv_svc.process_invoice(
        session=session,
        invoice_id=inv_id,
        file_bytes=b"%PDF-1.4 Pollo King SpA content",
        file_name="factura_pollo_king.pdf",
        tenant_id=t_id,
    )

    assert processed.status == InvoiceStatus.ANALYZED
    assert "Pollo King" in processed.vendor_name or "Distribuidora" in processed.vendor_name
    assert processed.gemini_tokens_used > 0
    assert processed.gemini_cost_usd > Decimal("0.000000")
    assert len(processed.lines) >= 1
    # Verificar cálculo de existencias físicas
    for line in processed.lines:
        assert line.calculated_stock_qty == line.quantity * line.packaging_factor
        assert line.inventory_unit_cost > Decimal("0.0000")


def test_oppyfy_operational_tools_query_invoices_summary():
    """Verifica la herramienta determinista query_invoices_summary con y sin redacción RBAC."""
    schema = "tenant_test_1"

    # 1. Con permisos financieros (can_view_costs=True)
    full_data = query_invoices_summary(schema, period="current_month", can_view_costs=True)
    assert full_data["tenant_schema"] == schema
    assert full_data["tool"] == "query_invoices_summary"
    assert full_data["total_invoices_count"] == 28
    assert full_data["pending_review_count"] == 5
    assert isinstance(full_data["total_net_amount"], Decimal)
    assert isinstance(full_data["total_tax_amount"], Decimal)
    assert isinstance(full_data["total_invoiced_amount"], Decimal)
    assert full_data["top_suppliers"][0]["supplier_name"] == "Pollo King SpA"

    # 2. Sin permisos financieros (can_view_costs=False) -> Redacción estricta
    redacted_data = query_invoices_summary(schema, period="current_month", can_view_costs=False)
    assert redacted_data["total_net_amount"] == REDACTED_COST_MARKER
    assert redacted_data["total_tax_amount"] == REDACTED_COST_MARKER
    assert redacted_data["total_invoiced_amount"] == REDACTED_COST_MARKER
    # Nombres de proveedores NO se redactan ni traducen
    assert redacted_data["top_suppliers"][0]["supplier_name"] == "Pollo King SpA"
    assert redacted_data["top_suppliers"][0]["total_neto"] == REDACTED_COST_MARKER


def test_oppyfy_operational_tools_get_supplier_price_drift_alerts():
    """Verifica la detección de sobreprecios e inflación en get_supplier_price_drift_alerts."""
    schema = "tenant_test_1"

    # 1. Umbral del 10%: debe detectar Pechuga Pollo (+11.43%) y Crema (+28.57%)
    res_10 = get_supplier_price_drift_alerts(schema, threshold_pct=Decimal("10.0"), can_view_costs=True)
    assert res_10["alerts_count"] == 2
    names = [a["item_name"] for a in res_10["alerts"]]
    assert "Pechuga de Pollo Deshuesada" in names
    assert "Crema de Leche Pastelera 35% MG" in names

    # Severidades semafóricas
    severities = {a["item_name"]: a["severity"] for a in res_10["alerts"]}
    assert severities["Pechuga de Pollo Deshuesada"] == "warning"
    assert severities["Crema de Leche Pastelera 35% MG"] == "critical"

    # 2. Umbral alto del 20%: solo debe alertar la Crema
    res_20 = get_supplier_price_drift_alerts(schema, threshold_pct=Decimal("20.0"), can_view_costs=True)
    assert res_20["alerts_count"] == 1
    assert res_20["alerts"][0]["item_name"] == "Crema de Leche Pastelera 35% MG"

    # 3. Filtrar por proveedor
    res_supplier = get_supplier_price_drift_alerts(schema, supplier_id="76.123.456-0", can_view_costs=True)
    assert res_supplier["alerts_count"] == 1
    assert res_supplier["alerts"][0]["supplier_name"] == "Pollo King SpA"

    # 4. Redacción financiera
    redacted = get_supplier_price_drift_alerts(schema, threshold_pct=Decimal("10.0"), can_view_costs=False)
    assert redacted["alerts"][0]["costo_unitario"] == REDACTED_COST_MARKER
    assert redacted["alerts"][0]["precio_compra"] == REDACTED_COST_MARKER
    assert redacted["alerts"][0]["supplier_name"] == "Pollo King SpA"


def test_tool_router_catalog_and_jev_execution():
    """Verifica el registro en el catálogo y la ejecución determinista a través de OppyfyToolRouter."""
    assert "query_invoices_summary" in HARD_CODED_TOOL_CATALOG
    assert "get_supplier_price_drift_alerts" in HARD_CODED_TOOL_CATALOG

    # Simular JEV Decision Port
    mock_jev = MagicMock(spec=JevDecisionPort)
    mock_usage = MagicMock()
    mock_jev.decide_choice.return_value = JevChoiceResult(
        decision_id="OPPYFY_TOOL_ROUTER_INTENT",
        value="query_invoices_summary",
        confidence=Decimal("0.9600"),
        threshold=Decimal("0.85"),
        meets_threshold=True,
        fallback_required=False,
        alternatives=(),
        usage_record=mock_usage,
    )

    router = OppyfyToolRouter(jev_port=mock_jev)

    # 1. Clasificación JEV
    tool_code, subdomain, choice = router.classify_tool_and_subdomain(
        user_prompt="¿Cuántas facturas pendientes de revisión tenemos este mes?",
        holding_id=uuid4(),
        tenant_id=uuid4(),
        tenant_schema="tenant_demo",
        user_id=1,
    )
    assert tool_code == "query_invoices_summary"
    assert subdomain == "finanzas_y_rentabilidad"
    assert choice.confidence == Decimal("0.9600")

    # 2. Ejecución determinista autorizada con redacción
    result_redacted = router.execute_hardcoded_tool(
        tool_code="query_invoices_summary",
        tenant_schema="tenant_demo",
        can_view_costs=False,
        jev_choice=choice,
    )
    assert result_redacted.costs_redacted is True
    assert result_redacted.sanitized_payload["total_net_amount"] == REDACTED_COST_MARKER

    # 3. Ejecución de alerta de sobreprecios
    mock_jev.decide_choice.return_value = JevChoiceResult(
        decision_id="OPPYFY_TOOL_ROUTER_INTENT",
        value="get_supplier_price_drift_alerts",
        confidence=Decimal("0.9800"),
        threshold=Decimal("0.85"),
        meets_threshold=True,
        fallback_required=False,
        alternatives=(),
        usage_record=mock_usage,
    )
    tool_code_drift, _, choice_drift = router.classify_tool_and_subdomain(
        user_prompt="¿Qué proveedores nos subieron los precios más del 10%?",
        holding_id=uuid4(),
        tenant_id=uuid4(),
        tenant_schema="tenant_demo",
        user_id=1,
    )
    assert tool_code_drift == "get_supplier_price_drift_alerts"

    result_drift = router.execute_hardcoded_tool(
        tool_code="get_supplier_price_drift_alerts",
        tenant_schema="tenant_demo",
        can_view_costs=True,
        jev_choice=choice_drift,
    )
    assert result_drift.costs_redacted is False
    assert result_drift.sanitized_payload["alerts_count"] >= 1
