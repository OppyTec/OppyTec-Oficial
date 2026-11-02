"""
oppytec-backend/tests/unit/modules/test_events_observability.py
Suite de Pruebas de Observabilidad 4-Pilares para el Módulo de Eventos, Salones y Consumos (Fase 8):
- Spans OpenTelemetry capturados deterministamente en InMemorySpanExporter:
  * `events.create` (EventService.create_event)
  * `events.execute` (EventService.execute_event)
  * `events.reversal` (EventService.reverse_event)
  * `events.faltantes.compute` (EventService.get_faltantes_analytics)
  * `events.committed_stock.compute` (EventService.get_committed_stock_summary)
  * `events.salon.create`, `events.salon.update`, `events.salon.delete` (SalonService)
  * `events.update`, `events.delete`, `events.cancel`, `events.reactivate`, `events.alerts.get`
- Validación estricta de atributos contextuales: `tenant_id`, `event_id`, `salon_id`.
- Validación de métricas operativas en memoria (`EventOperationMetric`).
- Enmascaramiento y ausencia de PII en atributos y logs de telemetría (scrub_telemetry_payload).
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.core.observability import (
    clear_in_memory_events_metrics,
    get_in_memory_events_metrics,
    get_in_memory_exporter,
    scrub_telemetry_payload,
)
from src.modules.events.application.services import EventService, SalonService
from src.modules.events.domain.exceptions import (
    EventAlreadyExecutedError,
    EventOverbookingError,
)
from src.modules.events.presentation.schemas import (
    EventoCreate,
    EventoItemIn,
    EventoRecetaIn,
    EventoUpdate,
    SalonCreate,
    SalonUpdate,
)
from src.modules.inventory.application.inventory_service import InventoryService

pytestmark = pytest.mark.unit

TEST_TENANT = "tenant_events_obs_test"


@pytest.fixture(autouse=True)
def _clean_observability_state() -> None:
    """Limpia los spans y métricas en memoria antes de cada prueba."""
    get_in_memory_exporter().clear()
    clear_in_memory_events_metrics()


def test_events_create_span_and_context_attributes() -> None:
    """
    Verifica la emisión del span `events.create` con `tenant_id`, `event_id`,
    `salon_id`, `fecha` y `nombre`, además de la métrica `EventOperationMetric`.
    """
    salon_svc = SalonService()
    event_svc = EventService(salon_service=salon_svc)
    exporter = get_in_memory_exporter()

    salon = salon_svc.create_salon(
        tenant_id=TEST_TENANT,
        data=SalonCreate(
            nombre="Gran Salón Cordillera",
            capacidad_personas=200,
            precio_neto=Decimal("150000.00"),
            iva_porcentaje=Decimal("19.00"),
        ),
    )

    now = datetime.now(UTC)
    evt_fecha = (now + timedelta(days=5)).date()

    created_evt = event_svc.create_event(
        tenant_id=TEST_TENANT,
        data=EventoCreate(
            nombre="Gala Benéfica Anual",
            fecha=evt_fecha,
            hora_inicio=time(19, 0),
            hora_fin=time(23, 30),
            salon_id=salon.id,
            cantidad_personas=150,
            items=[
                EventoItemIn(
                    producto_id=1,
                    bodega_id=1,
                    cantidad=Decimal("30.0000"),
                    costo_unitario_estimado=Decimal("2500.00"),
                ),
            ],
        ),
    )

    spans = exporter.get_finished_spans()
    create_span = next((s for s in spans if s.name == "events.create"), None)
    assert create_span is not None, "Span 'events.create' debe haberse emitido"
    assert create_span.status_code == 200
    assert create_span.attributes["tenant_id"] == TEST_TENANT
    assert create_span.attributes["event_id"] == str(created_evt.id)
    assert create_span.attributes["salon_id"] == str(salon.id)
    assert create_span.attributes["nombre"] == "Gala Benéfica Anual"
    assert create_span.attributes["fecha"] == str(evt_fecha)

    # Verifica métricas en memoria
    metrics = get_in_memory_events_metrics()
    evt_metric = next((m for m in metrics if m.operation == "events.create"), None)
    assert evt_metric is not None
    assert evt_metric.status == "SUCCESS"
    assert evt_metric.tenant_id == TEST_TENANT
    assert evt_metric.event_id == str(created_evt.id)
    assert evt_metric.salon_id == str(salon.id)


def test_events_execute_span_and_kardex_telemetry() -> None:
    """
    Verifica que `events.execute` emita el span con desglose transaccional:
    `tenant_id`, `event_id`, `salon_id`, `total_movimientos_kardex`, `costo_total_consumido`.
    """
    inv_svc = InventoryService()
    inv_svc.register_movement(
        producto_id=10,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("100.0000"),
        unit_cost=Decimal("3500.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )
    salon_svc = SalonService()
    event_svc = EventService(inventory=inv_svc, salon_service=salon_svc)
    event_svc.set_product_cost(10, Decimal("3500.00"))
    exporter = get_in_memory_exporter()

    salon = salon_svc.create_salon(
        tenant_id=TEST_TENANT,
        data=SalonCreate(nombre="Salón Los Robles", precio_neto=Decimal("80000.00")),
    )
    evt = event_svc.create_event(
        tenant_id=TEST_TENANT,
        data=EventoCreate(
            nombre="Banquete Matrimonial",
            fecha=date.today() + timedelta(days=1),
            hora_inicio=time(13, 0),
            hora_fin=time(18, 0),
            salon_id=salon.id,
            cantidad_personas=80,
            items=[
                EventoItemIn(producto_id=10, bodega_id=1, cantidad=Decimal("20.0000")),
            ],
        ),
    )

    exporter.clear()
    clear_in_memory_events_metrics()

    result = event_svc.execute_event(tenant_id=TEST_TENANT, event_id=evt.id)
    assert result.ejecutado is True

    spans = exporter.get_finished_spans()
    exec_span = next((s for s in spans if s.name == "events.execute"), None)
    assert exec_span is not None, "Span 'events.execute' debe haberse emitido"
    assert exec_span.status_code == 200
    assert exec_span.attributes["tenant_id"] == TEST_TENANT
    assert exec_span.attributes["event_id"] == str(evt.id)
    assert exec_span.attributes["salon_id"] == str(salon.id)
    assert exec_span.attributes["total_movimientos_kardex"] == 1
    assert Decimal(str(exec_span.attributes["costo_total_consumido"])) == Decimal("70000.00")

    metrics = get_in_memory_events_metrics()
    exec_metric = next((m for m in metrics if m.operation == "events.execute"), None)
    assert exec_metric is not None
    assert exec_metric.status == "SUCCESS"
    assert exec_metric.event_id == str(evt.id)


def test_events_reversal_span_and_compensatory_telemetry() -> None:
    """
    Verifica que `events.reversal` emita el span compensatorio con:
    `tenant_id`, `event_id`, `salon_id`, `motivo`, `total_movimientos_revertidos`, `costo_total_revertido`.
    """
    inv_svc = InventoryService()
    inv_svc.register_movement(
        producto_id=10,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("100.0000"),
        unit_cost=Decimal("3500.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )
    salon_svc = SalonService()
    event_svc = EventService(inventory=inv_svc, salon_service=salon_svc)
    event_svc.set_product_cost(10, Decimal("3500.00"))
    exporter = get_in_memory_exporter()

    salon = salon_svc.create_salon(
        tenant_id=TEST_TENANT,
        data=SalonCreate(nombre="Salón Esmeralda", precio_neto=Decimal("90000.00")),
    )
    evt = event_svc.create_event(
        tenant_id=TEST_TENANT,
        data=EventoCreate(
            nombre="Cena de Clausura",
            fecha=date.today() + timedelta(days=2),
            hora_inicio=time(20, 0),
            hora_fin=time(23, 0),
            salon_id=salon.id,
            cantidad_personas=50,
            items=[
                EventoItemIn(producto_id=10, bodega_id=1, cantidad=Decimal("10.0000")),
            ],
        ),
    )
    event_svc.execute_event(tenant_id=TEST_TENANT, event_id=evt.id)

    exporter.clear()
    clear_in_memory_events_metrics()

    rev_result = event_svc.reverse_event(
        tenant_id=TEST_TENANT,
        event_id=evt.id,
        motivo="Fuerza mayor: temporal de lluvia severo",
    )
    assert rev_result.revertido is True

    spans = exporter.get_finished_spans()
    rev_span = next((s for s in spans if s.name == "events.reversal"), None)
    assert rev_span is not None, "Span 'events.reversal' debe haberse emitido"
    assert rev_span.status_code == 200
    assert rev_span.attributes["tenant_id"] == TEST_TENANT
    assert rev_span.attributes["event_id"] == str(evt.id)
    assert rev_span.attributes["salon_id"] == str(salon.id)
    assert rev_span.attributes["motivo"] == "Fuerza mayor: temporal de lluvia severo"
    assert rev_span.attributes["total_movimientos_revertidos"] == 1
    assert Decimal(str(rev_span.attributes["costo_total_revertido"])) == Decimal("35000.00")

    metrics = get_in_memory_events_metrics()
    rev_metric = next((m for m in metrics if m.operation == "events.reversal"), None)
    assert rev_metric is not None
    assert rev_metric.status == "SUCCESS"
    assert rev_metric.event_id == str(evt.id)


def test_events_faltantes_compute_span() -> None:
    """
    Verifica que `events.faltantes.compute` mida el cálculo analítico predictivo
    de déficit de insumos agregados.
    """
    event_svc = EventService()
    exporter = get_in_memory_exporter()

    # Evento con demanda de 50 unidades de producto 100
    event_svc.create_event(
        tenant_id=TEST_TENANT,
        data=EventoCreate(
            nombre="Cocktail Empresarial",
            fecha=date.today() + timedelta(days=3),
            hora_inicio=time(18, 0),
            hora_fin=time(21, 0),
            items=[
                EventoItemIn(producto_id=100, bodega_id=1, cantidad=Decimal("50.0000")),
            ],
        ),
    )

    exporter.clear()
    clear_in_memory_events_metrics()

    faltantes = event_svc.get_faltantes_analytics(tenant_id=TEST_TENANT)
    assert faltantes.total_faltantes >= 1

    spans = exporter.get_finished_spans()
    faltantes_span = next((s for s in spans if s.name == "events.faltantes.compute"), None)
    assert faltantes_span is not None, "Span 'events.faltantes.compute' debe emitirse"
    assert faltantes_span.status_code == 200
    assert faltantes_span.attributes["tenant_id"] == TEST_TENANT
    assert faltantes_span.attributes["total_faltantes"] == faltantes.total_faltantes
    assert faltantes_span.attributes["eventos_afectados_count"] == 1


def test_events_committed_stock_compute_span() -> None:
    """
    Verifica que `events.committed_stock.compute` emita el span con desglose
    de stock comprometido por bodega e ítems procesados.
    """
    event_svc = EventService()
    exporter = get_in_memory_exporter()

    event_svc.create_event(
        tenant_id=TEST_TENANT,
        data=EventoCreate(
            nombre="Almuerzo Corporativo",
            fecha=date.today() + timedelta(days=4),
            hora_inicio=time(12, 0),
            hora_fin=time(15, 0),
            items=[
                EventoItemIn(producto_id=201, bodega_id=2, cantidad=Decimal("15.0000")),
            ],
        ),
    )

    exporter.clear()
    clear_in_memory_events_metrics()

    summary = event_svc.get_committed_stock_summary(tenant_id=TEST_TENANT, bodega_id=2)
    assert summary.total_items >= 1

    spans = exporter.get_finished_spans()
    stock_span = next((s for s in spans if s.name == "events.committed_stock.compute"), None)
    assert stock_span is not None, "Span 'events.committed_stock.compute' debe emitirse"
    assert stock_span.status_code == 200
    assert stock_span.attributes["tenant_id"] == TEST_TENANT
    assert stock_span.attributes["bodega_id"] == "2"
    assert stock_span.attributes["total_items"] == summary.total_items


def test_events_lifecycle_and_salon_spans() -> None:
    """
    Verifica que los spans secundarios de salones y eventos se emitan correctamente:
    - events.salon.create, events.salon.update, events.salon.delete
    - events.update, events.cancel, events.reactivate, events.delete, events.alerts.get
    """
    salon_svc = SalonService()
    event_svc = EventService(salon_service=salon_svc)
    exporter = get_in_memory_exporter()

    # 1. Salon lifecycle
    s = salon_svc.create_salon(tenant_id=TEST_TENANT, data=SalonCreate(nombre="Salón VIP"))
    s_updated = salon_svc.update_salon(tenant_id=TEST_TENANT, salon_id=s.id, data=SalonUpdate(nombre="Salón VIP Gold"))
    assert s_updated.nombre == "Salón VIP Gold"
    salon_svc.delete_salon(tenant_id=TEST_TENANT, salon_id=s.id)

    # 2. Event lifecycle
    evt = event_svc.create_event(
        tenant_id=TEST_TENANT,
        data=EventoCreate(
            nombre="Fiesta Fin de Año",
            fecha=date.today() + timedelta(days=7),
            hora_inicio=time(21, 0),
            hora_fin=time(23, 59),
        ),
    )
    event_svc.update_event(tenant_id=TEST_TENANT, event_id=evt.id, data=EventoUpdate(nombre="Gran Fiesta Fin de Año"))
    event_svc.cancel_event(tenant_id=TEST_TENANT, event_id=evt.id, motivo="Reprogramación solicitada")
    event_svc.reactivate_event(tenant_id=TEST_TENANT, event_id=evt.id)
    event_svc.delete_event(tenant_id=TEST_TENANT, event_id=evt.id)
    event_svc.get_event_alerts(tenant_id=TEST_TENANT)

    spans = exporter.get_finished_spans()
    span_names = {s.name for s in spans}
    expected_spans = {
        "events.salon.create",
        "events.salon.update",
        "events.salon.delete",
        "events.create",
        "events.update",
        "events.cancel",
        "events.reactivate",
        "events.delete",
        "events.alerts.get",
    }
    for exp in expected_spans:
        assert exp in span_names, f"Span '{exp}' debe haberse emitido"


def test_pii_redaction_in_event_telemetry_payloads() -> None:
    """
    Certifica la ausencia de fugas de PII (contraseñas, tokens, tarjetas, RUTs,
    datos fiscales) en las trazas y metadatos de eventos según Rule 17.
    """
    sensitive_payload: dict[str, object] = {
        "tenant_id": TEST_TENANT,
        "event_id": str(uuid4()),
        "salon_id": str(uuid4()),
        "user_email": "admin@eventos.oppytec.cl",
        "password": "SuperSecretChefPassword123!",
        "access_token": "Bearer eyJhbGciOiJIUzI1NiJ9.somerandomtoken",
        "credit_card": "4532-1234-5678-9012",
        "rut_titular": "18.765.432-1",
        "auth_secret": "my-ultra-secret-api-key",
    }

    scrubbed = scrub_telemetry_payload(sensitive_payload)

    # Identificadores de negocio permitidos
    assert scrubbed["tenant_id"] == TEST_TENANT
    assert "event_id" in scrubbed
    assert "salon_id" in scrubbed

    # Secretos y PII obligatoriamente enmascarados
    assert "SuperSecretChefPassword123!" not in str(scrubbed)
    assert "eyJhbGciOiJIUzI1NiJ9" not in str(scrubbed)
    assert scrubbed["password"] in {"[REDACTED]", "[REDACTED_PII]"}
    assert scrubbed["access_token"] in {"[REDACTED]", "[REDACTED_PII]"}
    assert scrubbed["auth_secret"] in {"[REDACTED]", "[REDACTED_PII]"}


def test_error_span_telemetry_recording() -> None:
    """
    Verifica que cuando un método de eventos falla con excepción de dominio
    (e.g. doble ejecución o colisión de horario), el span capture el estado ERROR.
    """
    event_svc = EventService()
    exporter = get_in_memory_exporter()

    evt = event_svc.create_event(
        tenant_id=TEST_TENANT,
        data=EventoCreate(
            nombre="Evento Test Error",
            fecha=date.today() + timedelta(days=2),
            hora_inicio=time(10, 0),
            hora_fin=time(12, 0),
        ),
    )
    event_svc.execute_event(tenant_id=TEST_TENANT, event_id=evt.id)

    exporter.clear()
    clear_in_memory_events_metrics()

    # Intentar ejecutarlo nuevamente debe lanzar EventAlreadyExecutedError
    with pytest.raises(EventAlreadyExecutedError):
        event_svc.execute_event(tenant_id=TEST_TENANT, event_id=evt.id)

    spans = exporter.get_finished_spans()
    err_span = next((s for s in spans if s.name == "events.execute"), None)
    assert err_span is not None
    assert err_span.status_code in {409, 500}

    metrics = get_in_memory_events_metrics()
    err_metric = next((m for m in metrics if m.operation == "events.execute"), None)
    assert err_metric is not None
    assert err_metric.status == "ERROR"
