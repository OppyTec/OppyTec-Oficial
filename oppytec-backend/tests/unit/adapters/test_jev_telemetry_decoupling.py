"""
Pruebas Unitarias de Desacoplamiento de Telemetría JEV (Sistema 1)
(`tests/unit/adapters/test_jev_telemetry_decoupling.py`).

Verifica:
1. Inmutabilidad y tipado estricto de `JevUsageRecord` (cero float, Decimal, UUIDs).
2. Protocolo `JevTelemetrySinkPort` e implementaciones `InMemoryJevTelemetrySink` y `DatabaseJevTelemetrySink`.
3. Soporte de operaciones individuales y por lote (`record_jev_usage`, `record_jev_usage_batch`, `session.add_all`).
4. Adaptador `MeteredJevAdapter`:
   - Emisión dual (retrocompatibilidad `llm_request_logs` + nuevo `jev_request_logs`).
   - Acciones calibradas ('AUTO_ACCEPTED', 'FLAGGED_WARNING', 'FALLBACK_LLM').
   - Evaluación por lotes `decide_choice_batch` para importador de catálogo y facturas OCR.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.ai import (
    DEFAULT_JEV_CONFIDENCE_THRESHOLD,
    DatabaseJevTelemetrySink,
    InMemoryJevTelemetrySink,
    InMemoryTelemetrySink,
    JevChoiceBatchItem,
    JevDecisionPort,
    JevTelemetrySinkPort,
    JevUsageRecord,
    MeteredJevAdapter,
)
from src.modules.oppy_ai.infrastructure.models import JevRequestLog

pytestmark = pytest.mark.unit


def test_jev_usage_record_immutability_and_defaults() -> None:
    """Verifica que JevUsageRecord sea inmutable y posea los tipos estrictos correctos."""
    holding_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    record = JevUsageRecord(
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_pacifico",
        caller_feature="invoice_ocr",
        decision_id="CHECK_RUT_MATCH",
        decision_primitive="BOOLEAN",
        input_summary="76.123.456-7 vs 76.123.456-7",
        result_value="true",
        confidence_score=Decimal("0.9800"),
        calibrated_action="AUTO_ACCEPTED",
        model_name="jev-system1-v2",
        latency_ms=12,
    )

    assert record.holding_id == holding_id
    assert record.tenant_id == tenant_id
    assert record.tenant_schema == "tenant_pacifico"
    assert record.decision_primitive == "BOOLEAN"
    assert record.confidence_score == Decimal("0.9800")
    assert record.calibrated_action == "AUTO_ACCEPTED"
    assert record.provider_cost_usd == Decimal("0.000000")
    assert record.provider_cost_clp == Decimal("0.00")
    assert record.credits_deducted == Decimal("0.00")
    assert record.is_success is True
    assert record.error_message is None

    # Inmutabilidad estricta (frozen dataclass)
    with pytest.raises(Exception):
        record.confidence_score = Decimal("0.5000")  # type: ignore[misc]


def test_in_memory_jev_telemetry_sink_lifecycle() -> None:
    """Verifica que InMemoryJevTelemetrySink implemente JevTelemetrySinkPort y acumule registros."""
    sink = InMemoryJevTelemetrySink()
    assert isinstance(sink, JevTelemetrySinkPort)
    assert len(sink.records) == 0

    holding_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    rec1 = JevUsageRecord(
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_sur",
        caller_feature="catalog_import",
        decision_id="MAP_COL_1",
        decision_primitive="CHOICE",
        input_summary="Precio Costo",
        result_value="costo_neto",
        confidence_score=Decimal("0.9500"),
        calibrated_action="AUTO_ACCEPTED",
        model_name="jev-system1-v2",
    )
    rec2 = JevUsageRecord(
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_sur",
        caller_feature="catalog_import",
        decision_id="MAP_COL_2",
        decision_primitive="CHOICE",
        input_summary="Nombre Insumo",
        result_value="nombre",
        confidence_score=Decimal("0.9600"),
        calibrated_action="AUTO_ACCEPTED",
        model_name="jev-system1-v2",
    )

    sink.record_jev_usage(rec1)
    assert len(sink.records) == 1
    assert sink.records[0].decision_id == "MAP_COL_1"

    sink.record_jev_usage_batch([rec2])
    assert len(sink.records) == 2
    assert sink.records[1].decision_id == "MAP_COL_2"

    sink.clear()
    assert len(sink.records) == 0


@pytest.mark.asyncio
async def test_database_jev_telemetry_sink_with_async_session() -> None:
    """Verifica que DatabaseJevTelemetrySink mapee a JevRequestLog y ejecute add / add_all transaccional."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.add_all = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    sink = DatabaseJevTelemetrySink(session=mock_session)
    assert isinstance(sink, JevTelemetrySinkPort)

    holding_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    rec = JevUsageRecord(
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_norte",
        user_id=42,
        trace_id="trace-xyz-123",
        caller_feature="merma_judge",
        decision_id="MERMA_ROTURA",
        decision_primitive="SCORE",
        input_summary="Rotura de 12 botellas de vino",
        result_value="HIGH:0.78",
        confidence_score=Decimal("0.9100"),
        calibrated_action="AUTO_ACCEPTED",
        model_name="jev-system1-v2",
        estimated_tokens=15,
        provider_cost_usd=Decimal("0.000003"),
        provider_cost_clp=Decimal("0.00"),
        credits_deducted=Decimal("0.20"),
        latency_ms=8,
    )

    sink.record_jev_usage(rec)
    assert len(sink.records) == 1
    assert len(sink.pending_models) == 1
    mock_session.add.assert_called_once()
    added_model = mock_session.add.call_args[0][0]
    assert isinstance(added_model, JevRequestLog)
    assert added_model.decision_id == "MERMA_ROTURA"
    assert added_model.confidence_score == Decimal("0.9100")
    assert added_model.user_id == 42
    assert added_model.trace_id == "trace-xyz-123"

    # Batch insert
    batch_records = [
        JevUsageRecord(
            holding_id=holding_id,
            tenant_id=tenant_id,
            tenant_schema="tenant_norte",
            caller_feature="catalog_import",
            decision_id=f"BATCH_{i}",
            decision_primitive="CHOICE",
            input_summary=f"Columna {i}",
            result_value="unidad",
            confidence_score=Decimal("0.9200"),
            calibrated_action="AUTO_ACCEPTED",
            model_name="jev-system1-v2",
        )
        for i in range(3)
    ]
    sink.record_jev_usage_batch(batch_records)
    mock_session.add_all.assert_called_once()
    added_batch = mock_session.add_all.call_args[0][0]
    assert len(added_batch) == 3
    assert all(isinstance(m, JevRequestLog) for m in added_batch)

    await sink.flush()
    mock_session.flush.assert_awaited_once()
    assert len(sink.pending_models) == 0


def test_metered_jev_adapter_dual_telemetry_emission() -> None:
    """Verifica que MeteredJevAdapter emita sincrónicamente tanto a LlmUsageRecord como a JevUsageRecord."""
    legacy_sink = InMemoryTelemetrySink()
    jev_sink = InMemoryJevTelemetrySink()

    adapter = MeteredJevAdapter(
        telemetry_sink=legacy_sink,
        jev_telemetry_sink=jev_sink,
    )
    assert isinstance(adapter, JevDecisionPort)

    holding_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    # 1. decide_boolean (auto accepted)
    bool_res = adapter.decide_boolean(
        decision_id="OCR_INVOICE_CHECK",
        prompt_or_input="Coca Cola Lata 350ml | Coca-Cola 350ml Lata",
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_centro",
        user_id=1,
        caller_feature="invoice_ocr",
    )
    assert bool_res.value is True
    assert bool_res.meets_threshold is True
    assert bool_res.usage_record.engine_tier == "SYSTEM_1_JEV"
    assert bool_res.jev_record is not None
    assert bool_res.jev_record.decision_primitive == "BOOLEAN"
    assert bool_res.jev_record.result_value == "true"
    assert bool_res.jev_record.calibrated_action == "AUTO_ACCEPTED"

    # 2. decide_choice (auto accepted)
    choice_res = adapter.decide_choice(
        decision_id="TOOL_INTENT",
        prompt_or_input="Quiero ver el resumen de ventas de hoy",
        candidates=("query_sales_summary", "query_stock_levels", "query_upcoming_events"),
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_centro",
        user_id=1,
        caller_feature="oppyfy_router",
    )
    assert choice_res.value == "query_sales_summary"
    assert choice_res.jev_record is not None
    assert choice_res.jev_record.decision_primitive == "CHOICE"
    assert choice_res.jev_record.calibrated_action == "AUTO_ACCEPTED"

    # 3. decide_score
    score_res = adapter.decide_score(
        decision_id="MERMA_EVAL",
        prompt_or_input="Monto critico y fraude detectado en recepcion",
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_centro",
        user_id=1,
        caller_feature="merma_judge",
    )
    assert score_res.level == "CRITICAL"
    assert score_res.jev_record is not None
    assert score_res.jev_record.decision_primitive == "SCORE"
    assert score_res.jev_record.result_value.startswith("CRITICAL:")

    # Sinks recibieron todas las emisiones
    assert len(legacy_sink.records) == 3
    assert len(jev_sink.records) == 3
    assert len(adapter.emitted_jev_logs) == 3
    assert len(adapter.emitted_logs) == 3


def test_calibrated_actions_warning_and_fallback() -> None:
    """Verifica que las micro-decisiones con baja confianza o ambiguas calibren FLAGGED_WARNING o FALLBACK_LLM."""
    jev_sink = InMemoryJevTelemetrySink()
    adapter = MeteredJevAdapter(jev_telemetry_sink=jev_sink)

    holding_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    # Entrada ambigua ("tal vez ok") -> confianza ~0.62 < 0.70 -> FALLBACK_LLM
    ambiguous_res = adapter.decide_boolean(
        decision_id="AMBIGUOUS_TEST",
        prompt_or_input="tal vez sea este producto",
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_centro",
        user_id=5,
        caller_feature="invoice_ocr",
        threshold=Decimal("0.85"),
    )
    assert ambiguous_res.meets_threshold is False
    assert ambiguous_res.fallback_required is True
    assert ambiguous_res.jev_record is not None
    assert ambiguous_res.jev_record.calibrated_action == "FALLBACK_LLM"


def test_metered_jev_adapter_batch_evaluation() -> None:
    """Verifica decide_choice_batch para importación de columnas o mapeos masivos en catálogo."""
    legacy_sink = InMemoryTelemetrySink()
    jev_sink = InMemoryJevTelemetrySink()

    adapter = MeteredJevAdapter(
        telemetry_sink=legacy_sink,
        jev_telemetry_sink=jev_sink,
    )

    holding_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    candidates = ("nombre", "costo_neto", "unidad", "bodega")

    batch_items = [
        JevChoiceBatchItem(
            decision_id="COL_1",
            prompt_or_input="Descripción del Artículo",
            candidates=candidates,
        ),
        JevChoiceBatchItem(
            decision_id="COL_2",
            prompt_or_input="Precio Unitario Neto",
            candidates=candidates,
        ),
        JevChoiceBatchItem(
            decision_id="COL_3",
            prompt_or_input="Formato Envase Unidad",
            candidates=candidates,
        ),
        JevChoiceBatchItem(
            decision_id="COL_4",
            prompt_or_input="Ubicación Almacén Bodega",
            candidates=candidates,
        ),
    ]

    results = adapter.decide_choice_batch(
        items=batch_items,
        holding_id=holding_id,
        tenant_id=tenant_id,
        tenant_schema="tenant_batch",
        user_id=10,
        caller_feature="catalog_importer",
    )

    assert len(results) == 4
    assert results[0].value == "nombre"
    assert results[1].value == "costo_neto"
    assert results[2].value == "unidad"
    assert results[3].value == "bodega"

    for r in results:
        assert r.meets_threshold is True
        assert r.jev_record is not None
        assert r.jev_record.decision_primitive == "CHOICE"
        assert r.jev_record.calibrated_action == "AUTO_ACCEPTED"

    # Verificación de telemetría en lote
    assert len(jev_sink.records) == 4
    assert len(legacy_sink.records) == 4
    assert len(adapter.emitted_jev_logs) == 4


def test_retrocompatibility_default_initialization() -> None:
    """Verifica que instanciar MeteredJevAdapter sin jev_telemetry_sink funcione sin romper código previo."""
    # Como lo inicializan módulos existentes:
    adapter = MeteredJevAdapter()
    assert adapter.jev_telemetry_sink is not None
    assert isinstance(adapter.jev_telemetry_sink, InMemoryJevTelemetrySink)

    res = adapter.decide_boolean(
        decision_id="SECURITY_GUARDRAIL_CHECK",
        prompt_or_input="SELECT * FROM pg_catalog",
        holding_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        tenant_schema="tenant_test",
        user_id=1,
        caller_feature="guardrail",
    )
    assert res.value is True  # Detecta inyección
    assert res.jev_record is not None
    assert res.jev_record.calibrated_action == "AUTO_ACCEPTED"
    assert len(adapter.emitted_jev_logs) == 1
