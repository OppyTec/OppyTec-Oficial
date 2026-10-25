"""
Pruebas de Observabilidad 4-Pilares para el Módulo de Inventario (Regla 17):
- Spans OpenTelemetry enriquecidos (tenant_id, bodega_id, items_count, transfer_uuid, user_id).
- Métricas deterministas de operaciones de inventario (InventoryOperationMetric).
- Captura limpia de excepciones de dominio en spans y logs estructurados.
- Validación de operaciones críticas:
  * inventory.movement.register
  * inventory.transfer.execute
  * inventory.count.finalize
  * inventory.count.reconcile
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.core.exceptions import (
    DomainValidationError,
    InsufficientStockError,
    TransferSameWarehouseError,
)
from src.core.observability import (
    clear_in_memory_inventory_metrics,
    get_in_memory_exporter,
    get_in_memory_inventory_metrics,
)
from src.modules.inventory.application import (
    CountItemInput,
    InventoryService,
    PhysicalCountService,
)

pytestmark = pytest.mark.unit

TENANT_TEST_ID = "tenant_obs_inv_test"


@pytest.fixture(autouse=True)
def _clean_telemetry_state() -> None:
    """Limpia el exportador de spans y las métricas antes de cada prueba."""
    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()


def test_inventory_movement_register_otel_span_and_metrics() -> None:
    """Verifica trazabilidad OTel y métricas al registrar movimiento en Kardex."""
    service = InventoryService()
    exporter = get_in_memory_exporter()

    entry = service.register_movement(
        producto_id=101,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("50.0000"),
        unit_cost=Decimal("1500.00"),
        actor_user_id=42,
        tenant_id=TENANT_TEST_ID,
    )
    assert entry.resulting_balance == Decimal("50.0000")

    # Validar span exportado
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "inventory.movement.register"
    assert span.status_code == 200
    assert span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert span.attributes["bodega_id"] == 1
    assert span.attributes["producto_id"] == 101
    assert span.attributes["movement_type"] == "ENTRADA"
    assert span.attributes["quantity"] == "50.0000"
    assert span.attributes["user_id"] == "42"
    assert span.attributes["resulting_balance"] == "50.0000"
    assert span.attributes["entry_id"] == entry.id

    # Validar métrica registrada
    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    metric = metrics[0]
    assert metric.operation == "inventory.movement.register"
    assert metric.status == "SUCCESS"
    assert metric.tenant_id == TENANT_TEST_ID
    assert metric.bodega_id == 1
    assert metric.user_id == "42"


def test_inventory_movement_register_exception_capture() -> None:
    """Verifica que excepciones de stock insuficiente sean capturadas limpiamente en el span."""
    service = InventoryService()
    exporter = get_in_memory_exporter()

    # Intentar salida sin saldo disponible
    with pytest.raises(InsufficientStockError) as exc_info:
        service.register_movement(
            producto_id=102,
            bodega_id=1,
            movement_type="SALIDA",
            quantity=Decimal("10.0000"),
            unit_cost=Decimal("2000.00"),
            actor_user_id=42,
            tenant_id=TENANT_TEST_ID,
        )

    assert exc_info.value.status_code == 409

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "inventory.movement.register"
    assert span.status_code == 409
    assert span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert span.attributes["bodega_id"] == 1

    # Validar métrica de fallo
    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    assert metrics[0].operation == "inventory.movement.register"
    assert metrics[0].status == "ERROR"


def test_inventory_transfer_bulk_otel_span_and_metrics() -> None:
    """Verifica que transfer_stock_bulk emita el span principal y spans anidados de Kardex."""
    service = InventoryService()
    exporter = get_in_memory_exporter()

    # Cargar existencias en bodega origen 1
    service.register_movement(
        producto_id=201,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("100.0000"),
        unit_cost=Decimal("1000.00"),
        actor_user_id=1,
        tenant_id=TENANT_TEST_ID,
    )
    exporter.clear()
    clear_in_memory_inventory_metrics()

    t_uuid = uuid.uuid4()
    results = service.transfer_stock_bulk(
        bodega_origen_id=1,
        bodega_destino_id=2,
        items=[{"producto_id": 201, "cantidad": "30.0000"}],
        actor_user_id=15,
        transfer_uuid=t_uuid,
        notas="Traspaso nocturno",
        tenant_id=TENANT_TEST_ID,
    )
    assert len(results) == 1
    out_mov, in_mov = results[0]
    assert out_mov.resulting_balance == Decimal("70.0000")
    assert in_mov.resulting_balance == Decimal("30.0000")

    spans = exporter.get_finished_spans()
    # Debe contener 2 movimientos (TRASPASO_OUT, TRASPASO_IN) y el span padre de transferencia
    assert len(spans) == 3
    transfer_span = next(s for s in spans if s.name == "inventory.transfer.execute")
    assert transfer_span.status_code == 200
    assert transfer_span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert transfer_span.attributes["bodega_origen_id"] == 1
    assert transfer_span.attributes["bodega_destino_id"] == 2
    assert transfer_span.attributes["items_count"] == 1
    assert transfer_span.attributes["transfer_uuid"] == str(t_uuid)
    assert transfer_span.attributes["user_id"] == "15"
    assert transfer_span.attributes["transferred_pairs_count"] == 1

    # Validar métricas acumuladas
    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 3
    transfer_metric = next(m for m in metrics if m.operation == "inventory.transfer.execute")
    assert transfer_metric.status == "SUCCESS"
    assert transfer_metric.tenant_id == TENANT_TEST_ID


def test_inventory_transfer_bulk_exception_capture_same_warehouse() -> None:
    """Verifica que el error de misma bodega sea capturado limpiamente en el span de transferencia."""
    service = InventoryService()
    exporter = get_in_memory_exporter()

    with pytest.raises(TransferSameWarehouseError):
        service.transfer_stock_bulk(
            bodega_origen_id=5,
            bodega_destino_id=5,
            items=[{"producto_id": 1, "cantidad": "5.0000"}],
            actor_user_id=10,
            tenant_id=TENANT_TEST_ID,
        )

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "inventory.transfer.execute"
    assert spans[0].status_code == 400

    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    assert metrics[0].operation == "inventory.transfer.execute"
    assert metrics[0].status == "ERROR"


def test_inventory_count_lifecycle_finalize_and_reconcile_spans() -> None:
    """Verifica trazabilidad OTel completa en finalización y reconciliación de recuentos físicos."""
    inv = InventoryService()
    # Existencia previa en bodega 3: 20 unidades
    inv.register_movement(
        producto_id=301,
        bodega_id=3,
        movement_type="ENTRADA",
        quantity=Decimal("20.0000"),
        unit_cost=Decimal("500.00"),
        actor_user_id=1,
        tenant_id=TENANT_TEST_ID,
    )

    count_svc = PhysicalCountService(inventory=inv)
    session = count_svc.start_count_session(
        bodega_id=3,
        responsable_user_id=88,
    )
    assert session.id is not None
    session_id = session.id
    count_svc.save_count_items(
        session_id,
        [
            CountItemInput(
                producto_id=301,
                stock_fisico_contado=Decimal("15.0000"),
                costo_unitario_ppp=Decimal("500.00"),
            )
        ],
    )

    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()

    # 1. Finalizar sesión (inventory.count.finalize)
    fin_session = count_svc.finalize_count_session(session_id, tenant_id=TENANT_TEST_ID)
    assert fin_session.estado == "PENDIENTE_APROBACION"

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    finalize_span = spans[0]
    assert finalize_span.name == "inventory.count.finalize"
    assert finalize_span.status_code == 200
    assert finalize_span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert finalize_span.attributes["conteo_id"] == session_id
    assert finalize_span.attributes["bodega_id"] == 3
    assert finalize_span.attributes["items_count"] == 1
    assert finalize_span.attributes["user_id"] == "88"
    assert finalize_span.attributes["estado_previo"] == "EN_PROGRESO"
    assert finalize_span.attributes["estado_nuevo"] == "PENDIENTE_APROBACION"
    assert finalize_span.attributes["discrepancies_count"] == 1

    # 2. Aprobar y reconciliar (inventory.count.reconcile)
    exporter.clear()
    clear_in_memory_inventory_metrics()

    app_session = count_svc.approve_and_reconcile(
        session_id,
        aprobador_user_id=99,
        tenant_id=TENANT_TEST_ID,
    )
    assert app_session.estado == "APROBADO"
    # El saldo debe haberse ajustado de 20 a 15
    assert inv.balance(301, 3) == Decimal("15.0000")

    rec_spans = exporter.get_finished_spans()
    # 1 movimiento de ajuste en Kardex + 1 span de reconciliación
    assert len(rec_spans) == 2
    rec_span = next(s for s in rec_spans if s.name == "inventory.count.reconcile")
    assert rec_span.status_code == 200
    assert rec_span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert rec_span.attributes["conteo_id"] == session_id
    assert rec_span.attributes["bodega_id"] == 3
    assert rec_span.attributes["user_id"] == "99"
    assert rec_span.attributes["discrepant_items_count"] == 1
    assert rec_span.attributes["estado_nuevo"] == "APROBADO"


def test_inventory_count_finalize_exception_capture() -> None:
    """Verifica captura limpia de excepción cuando se finaliza una sesión ya finalizada."""
    inv = InventoryService()
    count_svc = PhysicalCountService(inventory=inv)
    session = count_svc.start_count_session(bodega_id=1, responsable_user_id=10)
    assert session.id is not None
    session_id = session.id
    count_svc.finalize_count_session(session_id, tenant_id=TENANT_TEST_ID)

    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()

    # Intentar finalizar de nuevo
    with pytest.raises(DomainValidationError):
        count_svc.finalize_count_session(session_id, tenant_id=TENANT_TEST_ID)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "inventory.count.finalize"
    assert spans[0].status_code == 400

    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    assert metrics[0].operation == "inventory.count.finalize"
    assert metrics[0].status == "ERROR"
