"""
Pruebas de Observabilidad 4-Pilares para el Módulo de Alertas de Inventario (Regla 17):
- Spans OpenTelemetry enriquecidos (oppytec.tenant_id, bodega_ids, area_operativa_id, filter_type,
  total_alerts_count, critical_count, expired_count, total_financial_risk, has_critical).
- Spans ultralivianos para badges (inventory.alerts.badge).
- Spans y eventos reactivos WebSocket (inventory.alerts.broadcast).
- Redacción PII determinista (scrub_telemetry_payload) garantizando CERO fuga de secretos o credenciales.
- Captura limpia de excepciones de dominio con mapeo RFC 7807 (DomainValidationError -> HTTP 400).
- Registro determinista de métricas operativas de inventario y KPI analítico de alertas.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from src.core.exceptions import DomainValidationError
from src.core.observability import (
    clear_in_memory_alerts_metrics,
    clear_in_memory_inventory_metrics,
    get_in_memory_alerts_metrics,
    get_in_memory_exporter,
    get_in_memory_inventory_metrics,
    scrub_telemetry_payload,
)
from src.core.security import create_access_token
from src.modules.inventory.application.alerts_service import InventoryAlertsService
from src.modules.inventory.domain.alerts import (
    CriticalStockAlert,
    ExpiredLotAlert,
    UpcomingExpiryAlert,
)
from src.modules.inventory.infrastructure.alerts_repository import InMemoryAlertsRepository
from src.modules.inventory.presentation.router import _alerts_service

pytestmark = pytest.mark.unit

TENANT_TEST_ID = "tenant_obs_alerts_test"
HOLDING_TEST_ID = "holding_obs_alerts_test"


@pytest.fixture(autouse=True)
def _clean_telemetry_and_repository_state() -> None:
    """Aísla y resetea las métricas, exportador de spans y repositorio en memoria antes de cada test."""
    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()
    clear_in_memory_alerts_metrics()
    _alerts_service.set_repository(InMemoryAlertsRepository())
    _alerts_service.reset()


def _make_headers(permissions: list[str], user_id: int = 202) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC para endpoints de alertas."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TENANT_TEST_ID,
        holding_id=HOLDING_TEST_ID,
        role_grants=permissions,
        accessible_tenants=[TENANT_TEST_ID],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_TEST_ID,
    }


def _seed_test_alerts(repo: InMemoryAlertsRepository) -> None:
    """Puebla el repositorio de alertas en memoria con datos representativos."""
    # 1. Producto agotado
    repo.add_critical_stock(
        CriticalStockAlert.create(
            producto_id=101,
            bodega_id=1,
            bodega_nombre="Bodega Principal",
            producto_nombre="Café Grano Tostado 1kg",
            stock_actual=Decimal("0.0000"),
            stock_minimo=Decimal("10.0000"),
            unidad_medida="KG",
            costo_promedio=Decimal("12500.00"),
        )
    )
    # 2. Producto bajo mínimo
    repo.add_critical_stock(
        CriticalStockAlert.create(
            producto_id=102,
            bodega_id=2,
            bodega_nombre="Bodega Secundaria",
            producto_nombre="Leche Entera 1L",
            stock_actual=Decimal("3.0000"),
            stock_minimo=Decimal("15.0000"),
            unidad_medida="LITRO",
            costo_promedio=Decimal("950.00"),
        )
    )
    # 3. Lote caducado hace 2 días
    repo.add_expired_lot(
        ExpiredLotAlert.create(
            producto_id=103,
            bodega_id=1,
            bodega_nombre="Bodega Principal",
            producto_nombre="Queso Parmesano 500g",
            lote_codigo="LOT-PARM-001",
            fecha_vencimiento=date.today() - timedelta(days=2),
            cantidad_vencida=Decimal("8.0000"),
            dias_vencido=2,
            costo_ppp=Decimal("4500.00"),
            unidad_medida="UNIDAD",
        )
    )
    # 4. Lote próximo a vencer en 5 días
    repo.add_upcoming_expiry(
        UpcomingExpiryAlert.create(
            producto_id=104,
            bodega_id=2,
            bodega_nombre="Bodega Secundaria",
            producto_nombre="Mantequilla sin sal 250g",
            lote_codigo="LOT-MANT-002",
            fecha_vencimiento=date.today() + timedelta(days=5),
            cantidad_en_riesgo=Decimal("12.0000"),
            dias_restantes=5,
            costo_ppp=Decimal("1800.00"),
            unidad_medida="UNIDAD",
        )
    )


@pytest.mark.asyncio
async def test_alerts_fetch_span_and_metrics() -> None:
    """Verifica trazabilidad OTel 'inventory.alerts.fetch', enriquecimiento de atributos y métricas operativas."""
    repo = InMemoryAlertsRepository()
    _seed_test_alerts(repo)
    service = InventoryAlertsService(repository=repo)
    exporter = get_in_memory_exporter()

    summary = await service.get_alerts(
        tenant_id=TENANT_TEST_ID,
        bodega_ids=[1, 2],
        area_operativa_id=4,
        filter_type="all",
        upcoming_days=30,
    )

    assert summary.total_count == 4
    assert summary.critical_count == 2
    assert summary.expired_count == 1
    assert summary.upcoming_count == 1
    assert summary.has_critical is True
    assert summary.total_financial_risk > Decimal("0.00")

    # 1. Validar Span OpenTelemetry exportado
    spans = exporter.get_finished_spans()
    fetch_spans = [s for s in spans if s.name == "inventory.alerts.fetch"]
    assert len(fetch_spans) == 1
    span = fetch_spans[0]

    assert span.status_code == 200
    assert span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert span.attributes["bodega_ids"] == "[1, 2]"
    assert span.attributes["area_operativa_id"] == 4
    assert span.attributes["filter_type"] == "all"
    assert span.attributes["total_alerts_count"] == 4
    assert span.attributes["critical_count"] == 2
    assert span.attributes["expired_count"] == 1
    assert span.attributes["upcoming_count"] == 1
    assert span.attributes["total_financial_risk"] == str(summary.total_financial_risk)
    assert span.attributes["has_critical"] is True

    # 2. Validar métrica de operación de inventario
    op_metrics = get_in_memory_inventory_metrics()
    alert_op_metrics = [m for m in op_metrics if m.operation == "inventory.alerts.fetch"]
    assert len(alert_op_metrics) == 1
    op_metric = alert_op_metrics[0]
    assert op_metric.status == "SUCCESS"
    assert op_metric.tenant_id == TENANT_TEST_ID

    # 3. Validar métrica operativa de resumen de alertas (KPI analítico)
    alert_metrics = get_in_memory_alerts_metrics()
    assert len(alert_metrics) == 1
    al_metric = alert_metrics[0]
    assert al_metric.tenant_id == TENANT_TEST_ID
    assert al_metric.total_alerts_count == 4
    assert al_metric.critical_count == 2
    assert al_metric.expired_count == 1
    assert al_metric.upcoming_count == 1
    assert al_metric.total_financial_risk == str(summary.total_financial_risk)
    assert al_metric.has_critical is True


@pytest.mark.asyncio
async def test_alerts_badge_span_and_metrics() -> None:
    """Verifica trazabilidad ultraliviana 'inventory.alerts.badge' para el Sidebar institucional."""
    repo = InMemoryAlertsRepository()
    _seed_test_alerts(repo)
    service = InventoryAlertsService(repository=repo)
    exporter = get_in_memory_exporter()

    badge = await service.get_badge_summary(
        tenant_id=TENANT_TEST_ID,
        bodega_ids=[1],
        area_operativa_id=2,
    )

    assert badge.total_count == 2  # 1 stock crítico + 1 expirado en bodega 1
    assert badge.has_critical is True

    # 1. Validar Span OpenTelemetry exportado
    spans = exporter.get_finished_spans()
    badge_spans = [s for s in spans if s.name == "inventory.alerts.badge"]
    assert len(badge_spans) == 1
    span = badge_spans[0]

    assert span.status_code == 200
    assert span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert span.attributes["total_count"] == badge.total_count
    assert span.attributes["has_critical"] is True
    assert span.attributes["bodega_ids"] == "[1]"
    assert span.attributes["bodega_id"] == 1

    # 2. Validar métrica operativa
    op_metrics = get_in_memory_inventory_metrics()
    badge_op_metrics = [m for m in op_metrics if m.operation == "inventory.alerts.badge"]
    assert len(badge_op_metrics) == 1
    assert badge_op_metrics[0].status == "SUCCESS"
    assert badge_op_metrics[0].tenant_id == TENANT_TEST_ID
    assert badge_op_metrics[0].bodega_id == 1


@pytest.mark.asyncio
async def test_alerts_broadcast_span_and_metrics() -> None:
    """Verifica la emisión de eventos de invalidación WebSocket y el span 'inventory.alerts.broadcast'."""
    service = InventoryAlertsService()
    exporter = get_in_memory_exporter()

    await service.broadcast_alerts_changed(
        tenant_id=TENANT_TEST_ID,
        holding_id=HOLDING_TEST_ID,
        target_bodega_id=3,
        payload={"action": "recount_completed"},
    )

    spans = exporter.get_finished_spans()
    broadcast_spans = [s for s in spans if s.name == "inventory.alerts.broadcast"]
    assert len(broadcast_spans) == 1
    span = broadcast_spans[0]

    assert span.status_code == 200
    assert span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert span.attributes["target_bodega_id"] == 3
    assert span.attributes["event_type"] == "inventory.alerts.changed"
    assert span.attributes["published"] is True

    op_metrics = get_in_memory_inventory_metrics()
    broadcast_op = [m for m in op_metrics if m.operation == "inventory.alerts.broadcast"]
    assert len(broadcast_op) == 1
    assert broadcast_op[0].status == "SUCCESS"
    assert broadcast_op[0].tenant_id == TENANT_TEST_ID
    assert broadcast_op[0].bodega_id == 3


@pytest.mark.asyncio
async def test_alerts_broadcast_pii_redaction_and_data_protection() -> None:
    """Verifica que scrub_telemetry_payload redacte deterministamente credenciales y PII en broadcasts."""
    service = InventoryAlertsService()
    exporter = get_in_memory_exporter()

    sensitive_payload: dict[str, object] = {
        "action": "urgent_reorder",
        "secret_token": "Bearer sk-live-super-secret-9999",
        "password": "my_master_password_!",
        "rut": "12.345.678-9",
        "credit_card": "4111-2222-3333-4444",
        "safe_reference": "REF-ORD-10023",
    }

    # Verificar función pura determinista
    scrubbed = scrub_telemetry_payload(sensitive_payload)
    assert scrubbed["secret_token"] == "[REDACTED_PII]"
    assert scrubbed["password"] == "[REDACTED_PII]"
    assert scrubbed["rut"] == "[REDACTED_PII]"
    assert scrubbed["credit_card"] == "[REDACTED_PII]"
    assert scrubbed["safe_reference"] == "REF-ORD-10023"

    # Emitir broadcast con payload sensible y verificar que el span y atributos no contengan fugas
    await service.broadcast_alerts_changed(
        tenant_id=TENANT_TEST_ID,
        holding_id=HOLDING_TEST_ID,
        target_bodega_id=1,
        payload=sensitive_payload,
    )

    spans = exporter.get_finished_spans()
    span = spans[-1]
    serialized_span = str(span.attributes)
    assert "sk-live-super-secret-9999" not in serialized_span
    assert "my_master_password_!" not in serialized_span
    assert "4111-2222-3333-4444" not in serialized_span


@pytest.mark.asyncio
async def test_alerts_fetch_missing_tenant_rfc7807_exception_capture() -> None:
    """Verifica que omitir tenant_id dispare DomainValidationError con captura limpia en span OTel y RFC 7807."""
    service = InventoryAlertsService()
    exporter = get_in_memory_exporter()

    with pytest.raises(DomainValidationError) as exc_info:
        await service.get_alerts(tenant_id=None)

    error = exc_info.value
    assert error.status_code == 400
    assert error.i18n_key == "common:errors.tenant_required"

    # Convertir a RFC 7807 problem details
    problem = error.to_rfc7807(trace_id="test-trace-001")
    assert problem.status == 400
    assert problem.i18n_key == "common:errors.tenant_required"
    assert problem.trace_id == "test-trace-001"

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "inventory.alerts.fetch"
    assert span.status_code == 400

    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    assert metrics[0].operation == "inventory.alerts.fetch"
    assert metrics[0].status == "ERROR"


@pytest.mark.asyncio
async def test_alerts_fetch_invalid_filter_type_rfc7807_exception_capture() -> None:
    """Verifica captura limpia y RFC 7807 ante tipos de filtro no admitidos."""
    service = InventoryAlertsService()
    exporter = get_in_memory_exporter()

    with pytest.raises(DomainValidationError) as exc_info:
        await service.get_alerts(
            tenant_id=TENANT_TEST_ID,
            filter_type="invalid_filtro_desconocido",
        )

    error = exc_info.value
    assert error.status_code == 400
    assert error.i18n_key == "inventory:alerts.invalid_filter_type"

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "inventory.alerts.fetch"
    assert spans[0].status_code == 400

    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    assert metrics[0].status == "ERROR"


@pytest.mark.asyncio
async def test_alerts_fetch_invalid_upcoming_days_rfc7807_exception_capture() -> None:
    """Verifica captura limpia y RFC 7807 cuando upcoming_days es menor a 1."""
    service = InventoryAlertsService()
    exporter = get_in_memory_exporter()

    with pytest.raises(DomainValidationError) as exc_info:
        await service.get_alerts(
            tenant_id=TENANT_TEST_ID,
            upcoming_days=-5,
        )

    error = exc_info.value
    assert error.status_code == 400
    assert error.i18n_key == "inventory:alerts.invalid_upcoming_days"

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "inventory.alerts.fetch"
    assert spans[0].status_code == 400

    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    assert metrics[0].status == "ERROR"


@pytest.mark.asyncio
async def test_alerts_badge_missing_tenant_rfc7807_exception_capture() -> None:
    """Verifica captura limpia en get_badge_summary ante tenant_id nulo."""
    service = InventoryAlertsService()
    exporter = get_in_memory_exporter()

    with pytest.raises(DomainValidationError) as exc_info:
        await service.get_badge_summary(tenant_id=None)

    assert exc_info.value.status_code == 400
    assert exc_info.value.i18n_key == "common:errors.tenant_required"

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "inventory.alerts.badge"
    assert spans[0].status_code == 400


@pytest.mark.asyncio
async def test_alerts_http_integration_trace_id_and_spans(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que las peticiones HTTP a los endpoints de alertas inyecten X-Trace-ID
    en la cabecera de respuesta y exporten los spans a InMemorySpanExporter.
    """
    headers = _make_headers(["inventory.alerts.read"])
    exporter = get_in_memory_exporter()
    exporter.clear()

    # 1. Llamada a GET /api/v1/inventory/alerts
    resp_alerts = await async_client.get(
        "/api/v1/inventory/alerts?tipo=all",
        headers=headers,
    )
    assert resp_alerts.status_code == 200
    assert "X-Trace-ID" in resp_alerts.headers
    trace_id_1 = resp_alerts.headers["X-Trace-ID"]
    assert len(trace_id_1) > 0

    # 2. Llamada a GET /api/v1/inventory/alerts/badge
    resp_badge = await async_client.get(
        "/api/v1/inventory/alerts/badge",
        headers=headers,
    )
    assert resp_badge.status_code == 200
    assert "X-Trace-ID" in resp_badge.headers

    # 3. Validar que los spans fueron exportados
    spans = exporter.get_finished_spans()
    fetch_spans = [s for s in spans if s.name == "inventory.alerts.fetch"]
    badge_spans = [s for s in spans if s.name == "inventory.alerts.badge"]
    assert len(fetch_spans) >= 1
    assert len(badge_spans) >= 1
    assert fetch_spans[0].status_code == 200
    assert badge_spans[0].status_code == 200
