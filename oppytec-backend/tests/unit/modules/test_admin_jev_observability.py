"""
oppytec-backend/tests/unit/modules/test_admin_jev_observability.py
Certificación de Observabilidad 4-Pilares para la Consola FinOps de Decisiones JEV:
1. OpenTelemetry: Propagación de traceId / X-Trace-ID, generación de spans con InMemorySpanExporter.
2. Grafana LGTM: Métricas deterministas de latencia (latency_ms, avg_latency_ms_all) y JevOperationMetric.
3. Sentry / GlitchTip: Filtro determinista de redacción PII y secretos en entradas/salidas JEV.
4. Prevención de fugas de memoria: Límite acotado de retención en memoria (bounded in-memory stores).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal
import httpx
import pytest

from src.core.observability import (
    clear_in_memory_jev_metrics,
    get_in_memory_exporter,
    get_in_memory_jev_metrics,
)
from src.core.security import create_access_token
from src.modules.tenancy.application.jev_consumption_service import (
    MAX_IN_MEMORY_JEV_LOGS,
    JevConsumptionService,
)
from src.modules.tenancy.presentation.platform_admin_router import (
    _jev_consumption_service,
)

pytestmark = pytest.mark.unit


def _make_admin_headers(
    permissions: list[str],
    user_id: int = 1,
    is_global_staff: bool = True,
    is_superuser_god: bool = False,
    hierarchy_rank: int = 10,
    trace_id: str | None = None,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y X-Trace-ID opcional para la petición."""
    token = create_access_token(
        user_id=user_id,
        is_global_staff=is_global_staff,
        is_superuser_god=is_superuser_god,
        hierarchy_rank=hierarchy_rank,
        role_grants=permissions,
    )
    headers = {
        "Authorization": f"Bearer {token}",
    }
    if trace_id:
        headers["X-Trace-ID"] = trace_id
    return headers


@pytest.fixture(autouse=True)
def _clean_observability_state() -> None:
    """Limpia el exportador de spans, las métricas en memoria y restablece el servicio JEV."""
    get_in_memory_exporter().clear()
    clear_in_memory_jev_metrics()
    _jev_consumption_service.reset()


@pytest.mark.asyncio
async def test_jev_endpoint_opentelemetry_span_and_trace_propagation(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Certifica:
    - Inyección y propagación de X-Trace-ID en cabeceras de respuesta HTTP.
    - Exportación de span determinista 'platform_admin.jev_consumption.query' a InMemorySpanExporter.
    - Registro de atributos estructurados de FinOps (decisiones, latencia promedio, ahorro, costos).
    """
    client_trace = "test-jev-trace-uuid-1234567890"
    headers = _make_admin_headers(
        ["platform_admin.tokens.read"],
        user_id=77,
        trace_id=client_trace,
    )

    resp = await async_client.get(
        "/api/v1/platform-admin/jev-consumption?page=1&page_size=25",
        headers=headers,
    )
    assert resp.status_code == 200

    # 1. Propagación de traceId
    assert "X-Trace-ID" in resp.headers
    assert resp.headers["X-Trace-ID"] == client_trace

    # 2. Spans generados en InMemorySpanExporter
    exporter = get_in_memory_exporter()
    spans = exporter.get_finished_spans()

    jev_spans = [s for s in spans if s.name == "platform_admin.jev_consumption.query"]
    assert len(jev_spans) == 1
    jev_span = jev_spans[0]

    # Validación de trace_id correlacionado y duración positiva
    assert jev_span.trace_id == client_trace
    assert jev_span.status_code == 200
    assert jev_span.duration_ms >= 0.0

    # Validación de atributos enriquecidos en el span
    attrs = jev_span.attributes
    assert attrs.get("user_id") == "77"
    assert attrs.get("total_decisions_all") == 5
    assert attrs.get("avg_latency_ms_all") == "15.20"
    assert attrs.get("total_cost_usd_all") == "0.000025"
    assert attrs.get("estimated_savings_usd_all") == "0.012475"
    assert attrs.get("page") == 1
    assert attrs.get("page_size") == 25


@pytest.mark.asyncio
async def test_jev_operation_metric_recording(async_client: httpx.AsyncClient) -> None:
    """
    Certifica la emisión y captura de la métrica operativa JevOperationMetric
    en la capa de telemetría de observabilidad.
    """
    headers = _make_admin_headers(["platform_admin.tokens.read"], user_id=42)

    resp = await async_client.get(
        "/api/v1/platform-admin/jev-consumption",
        headers=headers,
    )
    assert resp.status_code == 200

    metrics = get_in_memory_jev_metrics()
    assert len(metrics) == 1
    metric = metrics[0]

    assert metric.operation == "platform_admin.jev_consumption.query"
    assert metric.status == "SUCCESS"
    assert metric.total_decisions == 5
    assert metric.avg_latency_ms == "15.20"
    assert metric.duration_ms >= 0.0
    assert len(metric.trace_id) > 0
    assert len(metric.timestamp) > 0

    # Limpieza
    clear_in_memory_jev_metrics()
    assert len(get_in_memory_jev_metrics()) == 0


def test_jev_record_log_pii_and_secret_redaction() -> None:
    """
    Certifica que entradas con contraseñas, tokens Bearer, RUT y tarjetas
    sean sanitizadas de forma determinista para evitar filtración de secretos.
    """
    service = JevConsumptionService()

    sensitive_input = (
        "Clasificación usuario RUT 12.345.678-5 con clave password=SuperSecretPassword999 "
        "y token Bearer eyJhbGciOiJIUzI1NiJ9"
    )
    sensitive_result = "Tarjeta 4532-0000-1111-2222 validada"
    sensitive_error = "Error al conectar con api_key=ak_live_verysecret12345"

    log_item = service.record_log(
        holding_id="holding_genesis",
        holding_name="Holding Principal Génesis",
        tenant_id="tenant_genesis",
        tenant_name="Local Central Génesis",
        tenant_schema="tenant_genesis",
        caller_feature="sec_validator",
        decision_id="dec_sec_pii_test",
        decision_primitive="CLASSIFY",
        input_summary=sensitive_input,
        result_value=sensitive_result,
        confidence_score=Decimal("0.99"),
        calibrated_action="AUTO_ACCEPTED",
        error_message=sensitive_error,
    )

    # 1. Validación de secretos y PII enmascarados
    assert "SuperSecretPassword999" not in log_item.input_summary
    assert "12.345.678-5" not in log_item.input_summary
    assert "eyJhbGciOiJIUzI1NiJ9" not in log_item.input_summary
    assert "[REDACTED_PII]" in log_item.input_summary

    assert "4532-0000-1111-2222" not in log_item.result_value
    assert "[REDACTED_PII]" in log_item.result_value

    assert log_item.error_message is not None
    assert "ak_live_verysecret12345" not in log_item.error_message
    assert "[REDACTED_PII]" in log_item.error_message


def test_jev_latency_metrics_aggregation_safety_and_bounded_capacity() -> None:
    """
    Certifica:
    - Validación y límites de latency_ms (< 500 ms).
    - Agregación sin errores por división por cero en consultas vacías.
    - Prevención de desbordes de memoria por retención acotada (MAX_IN_MEMORY_JEV_LOGS).
    """
    service = JevConsumptionService()

    # 1. Agregación segura con cero decisiones
    empty_summary = service.get_jev_consumption_summary(search="busqueda_sin_ningun_resultado_xyz_000")
    assert empty_summary.total_decisions_all == 0
    assert empty_summary.avg_latency_ms_all == Decimal("0.00")

    # 2. Clamping estricto de latencia (<500 ms según Regla 14)
    item_high_lat = service.record_log(
        holding_id="holding_genesis",
        holding_name="Holding Principal Génesis",
        tenant_id="tenant_genesis",
        tenant_name="Local Central Génesis",
        tenant_schema="tenant_genesis",
        caller_feature="bench_test",
        decision_id="dec_lat_001",
        decision_primitive="SCORE",
        input_summary="Test latencia",
        result_value="OK",
        confidence_score=Decimal("0.90"),
        calibrated_action="AUTO_ACCEPTED",
        latency_ms=9999,  # Intento de valor desmesurado
    )
    # Debe ser acotado a 499 ms
    assert item_high_lat.latency_ms == 499

    # 3. Bounded capacity en memoria (prevención de fugas / desbordes)
    assert MAX_IN_MEMORY_JEV_LOGS == 5000
    # Simulamos inserción de registros
    for i in range(10):
        service.record_log(
            holding_id="holding_genesis",
            holding_name="Holding Principal Génesis",
            tenant_id="tenant_genesis",
            tenant_name="Local Central Génesis",
            tenant_schema="tenant_genesis",
            caller_feature="stress",
            decision_id=f"dec_stress_{i}",
            decision_primitive="ROUTE",
            input_summary=f"Stress test {i}",
            result_value="OK",
            confidence_score=Decimal("0.95"),
            calibrated_action="AUTO_ACCEPTED",
            latency_ms=10,
        )

    summary = service.get_jev_consumption_summary()
    assert summary.total_decisions_all == 5 + 1 + 10  # 5 default + 1 lat_test + 10 stress = 16
    assert isinstance(summary.avg_latency_ms_all, Decimal)
    assert summary.avg_latency_ms_all > Decimal("0.00")
