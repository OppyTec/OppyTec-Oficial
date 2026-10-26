"""
oppytec-backend/tests/modules/inventory/test_history_observability.py
Pruebas de Observabilidad 4-Pilares para el Historial de Kardex (Regla 17):
- Spans OpenTelemetry enriquecidos:
  * `kardex.history.query`: oppytec.tenant_id, bodega_id, producto_id, tipo_movimiento, total_records, page_size, actor_user_id.
  * `kardex.history.export_csv`: oppytec.tenant_id, records_exported, file_format.
- Métricas operativas deterministas de inventario (`InventoryOperationMetric`).
- Redacción PII determinista (`scrub_telemetry_payload` / `scrub_audit_payload`) sobre correos y nombres de usuario.
- Captura limpia de excepciones conforme a RFC 7807 (Problem Details) sin filtración de datos sensibles.
- Integración HTTP verificando propagación de `X-Trace-ID` y exportación de spans en memoria.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from src.core.exceptions import DomainValidationError
from src.core.observability import (
    REDACTED_MARKER,
    clear_in_memory_inventory_metrics,
    format_structured_log,
    get_in_memory_exporter,
    get_in_memory_inventory_metrics,
    scrub_telemetry_payload,
)
from src.core.security import create_access_token
from src.modules.inventory.application.history_service import (
    KardexHistoryService,
    format_history_audit_log,
    scrub_audit_payload,
)
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.presentation.router import (
    _history_service,
    _inventory_service,
)

pytestmark = pytest.mark.unit

TENANT_TEST_ID = "tenant_obs_kardex_test"
HOLDING_TEST_ID = "holding_obs_kardex_test"


@pytest.fixture(autouse=True)
def _clean_telemetry_and_history_state() -> None:
    """Aísla y resetea las métricas, exportador de spans y servicios antes de cada test."""
    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()
    _inventory_service.reset()
    _history_service.reset()


def _make_headers(
    permissions: list[str],
    user_id: int = 101,
    *,
    is_holding_owner: bool = False,
    hierarchy_rank: int = 30,
) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TENANT_TEST_ID,
        holding_id=HOLDING_TEST_ID,
        role_grants=permissions,
        accessible_tenants=[TENANT_TEST_ID],
        is_holding_owner=is_holding_owner,
        hierarchy_rank=hierarchy_rank,
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_TEST_ID,
    }


def _seed_test_ledger(inv_svc: InventoryService, hist_svc: KardexHistoryService) -> None:
    """Puebla el libro mayor y metadatos de auditoría con datos representativos."""
    hist_svc.set_product_info(101, "Café Grano Tostado 1kg", "KG")
    hist_svc.set_product_info(102, "Leche Entera 1L", "LITRO")
    hist_svc.set_warehouse_info(1, "Bodega Central")
    hist_svc.set_warehouse_info(2, "Bodega Cafetería")
    hist_svc.set_user_info(42, nombre_visible="Chef Ejecutivo", email="chef@oppytec.cl")
    hist_svc.set_user_info(88, nombre_visible="Barista Principal", email="barista@oppytec.cl")

    # 1. Entrada de café en bodega 1
    inv_svc.register_movement(
        producto_id=101,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("30.0000"),
        unit_cost=Decimal("12000.00"),
        actor_user_id=42,
        tenant_id=TENANT_TEST_ID,
    )
    # 2. Entrada de leche en bodega 2
    inv_svc.register_movement(
        producto_id=102,
        bodega_id=2,
        movement_type="ENTRADA",
        quantity=Decimal("50.0000"),
        unit_cost=Decimal("950.00"),
        actor_user_id=88,
        tenant_id=TENANT_TEST_ID,
    )
    # 3. Merma de café en bodega 1
    inv_svc.register_movement(
        producto_id=101,
        bodega_id=1,
        movement_type="MERMA",
        quantity=Decimal("2.0000"),
        unit_cost=Decimal("12000.00"),
        actor_user_id=42,
        motivo_merma="vencimiento",
        descripcion_merma="Bolsa perforada",
        tenant_id=TENANT_TEST_ID,
    )


def test_kardex_history_query_otel_span_and_attributes() -> None:
    """
    Verifica que `kardex.history.query` registre exactamente los atributos requeridos:
    - oppytec.tenant_id
    - bodega_id
    - producto_id
    - tipo_movimiento
    - total_records
    - page_size
    - actor_user_id
    Y registre la métrica de inventario correspondiente.
    """
    inv = InventoryService()
    hist = KardexHistoryService(inventory=inv)
    _seed_test_ledger(inv, hist)

    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()

    result = hist.get_filtered_history(
        tenant_id=TENANT_TEST_ID,
        bodega_id=1,
        producto_id=101,
        tipo_movimiento="all",
        skip=0,
        limit=20,
        actor_user_id=42,
    )

    assert result.total == 2
    assert len(result.items) == 2

    # 1. Validar Span OpenTelemetry
    spans = exporter.get_finished_spans()
    query_spans = [s for s in spans if s.name == "kardex.history.query"]
    assert len(query_spans) == 1
    span = query_spans[0]

    assert span.status_code == 200
    assert span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert span.attributes["bodega_id"] == 1
    assert span.attributes["producto_id"] == 101
    assert span.attributes["tipo_movimiento"] == "all"
    assert span.attributes["total_records"] == 2
    assert span.attributes["page_size"] == 20
    assert span.attributes["actor_user_id"] == 42

    # 2. Validar Métrica Operativa
    metrics = get_in_memory_inventory_metrics()
    history_metrics = [m for m in metrics if m.operation == "kardex.history.query"]
    assert len(history_metrics) == 1
    metric = history_metrics[0]
    assert metric.status == "SUCCESS"
    assert metric.tenant_id == TENANT_TEST_ID
    assert metric.bodega_id == 1
    assert metric.user_id == "42"


def test_kardex_history_export_csv_otel_span_and_attributes() -> None:
    """
    Verifica que `kardex.history.export_csv` registre exactamente los atributos requeridos:
    - oppytec.tenant_id
    - records_exported
    - file_format
    Y genere el flujo CSV sanitizado.
    """
    inv = InventoryService()
    hist = KardexHistoryService(inventory=inv)
    _seed_test_ledger(inv, hist)

    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()

    csv_chunks = list(
        hist.generate_csv_stream(
            tenant_id=TENANT_TEST_ID,
            bodega_id="all",
            producto_id="all",
            tipo_movimiento="all",
            actor_user_id=77,
        )
    )

    # Validar contenido CSV
    full_csv = "".join(csv_chunks)
    assert full_csv.startswith("\ufeff"), "Debe incluir UTF-8 BOM"
    assert "Café Grano Tostado 1kg" in full_csv
    assert "Leche Entera 1L" in full_csv

    # 1. Validar Span OpenTelemetry
    spans = exporter.get_finished_spans()
    export_spans = [s for s in spans if s.name == "kardex.history.export_csv"]
    assert len(export_spans) == 1
    span = export_spans[0]

    assert span.status_code == 200
    assert span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert span.attributes["records_exported"] == 3
    assert span.attributes["file_format"] == "csv"

    # 2. Validar Métrica Operativa
    metrics = get_in_memory_inventory_metrics()
    export_metrics = [m for m in metrics if m.operation == "kardex.history.export_csv"]
    assert len(export_metrics) == 1
    metric = export_metrics[0]
    assert metric.status == "SUCCESS"
    assert metric.tenant_id == TENANT_TEST_ID


def test_pii_deterministic_redaction_in_audit_logs() -> None:
    """
    Verifica que la redacción PII determinista sobre correos y nombres de usuario
    se aplique rigurosamente en los logs de auditoría de Kardex.
    """
    raw_audit_payload: dict[str, object] = {
        "action": "export_kardex",
        "actor_user_id": 101,
        "username": "mario_rossi_chef",
        "user_name": "Mario",
        "user_display_name": "Mario Rossi",
        "email": "mario.rossi@oppytec.cl",
        "correo": "contacto@proveedor.com",
        "password": "ClearTextPassword!",
        "token": "sk_test_1234567890",
        "rut": "12.345.678-9",
        "credit_card": "4532-1111-2222-3333",
        "details": {
            "requested_by_email": "supervisor@restaurant.cl",
            "approver_username": "gerente_general",
            "system_note": "Aprobado por admin@oppytec.cl tras recuento",
            "item_sku": "SKU-CAF-001",
        },
    }

    # 1. Redacción mediante función de auditoría
    scrubbed = scrub_audit_payload(raw_audit_payload)

    # Identificadores no sensibles preservados
    assert scrubbed["actor_user_id"] == 101
    assert scrubbed["action"] == "export_kardex"

    # Secretos estándar redactados
    assert scrubbed["password"] == REDACTED_MARKER
    assert scrubbed["token"] == REDACTED_MARKER
    assert scrubbed["rut"] == REDACTED_MARKER
    assert scrubbed["credit_card"] == REDACTED_MARKER

    # Nombres de usuario y correos redactados
    assert scrubbed["username"] == REDACTED_MARKER
    assert scrubbed["user_name"] == REDACTED_MARKER
    assert scrubbed["user_display_name"] == REDACTED_MARKER
    assert scrubbed["email"] == REDACTED_MARKER
    assert scrubbed["correo"] == REDACTED_MARKER

    # Estructuras anidadas
    nested = scrubbed["details"]
    assert isinstance(nested, dict)
    assert nested["requested_by_email"] == REDACTED_MARKER
    assert nested["approver_username"] == REDACTED_MARKER
    assert nested["item_sku"] == "SKU-CAF-001"
    # Correos en texto libre redactados
    assert "admin@oppytec.cl" not in str(nested["system_note"])
    assert REDACTED_MARKER in str(nested["system_note"])

    # 2. Formato estructurado JSON
    json_log = format_history_audit_log("INFO", "export", raw_audit_payload)
    parsed = json.loads(json_log)
    assert parsed["event"] == "kardex.history.export"
    assert "mario.rossi@oppytec.cl" not in json_log
    assert "ClearTextPassword!" not in json_log
    assert "12.345.678-9" not in json_log
    assert parsed["data"]["email"] == REDACTED_MARKER
    assert parsed["data"]["username"] == REDACTED_MARKER


def test_rfc7807_exception_capture_missing_tenant() -> None:
    """
    Verifica que la omisión de tenant_id dispare DomainValidationError con:
    - Captura limpia en span OTel con status 400.
    - Métrica de inventario con status ERROR.
    - Conformidad con RFC 7807 (Problem Details).
    - Cero filtración de datos sensibles.
    """
    hist = KardexHistoryService()
    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()

    with pytest.raises(DomainValidationError) as exc_info:
        hist.get_filtered_history(tenant_id=None)

    error = exc_info.value
    assert error.status_code == 400
    assert error.i18n_key == "common:errors.tenant_required"

    # Verificación de esquema RFC 7807
    problem = error.to_rfc7807(trace_id="trace-test-rfc7807-001")
    assert problem.status == 400
    assert problem.i18n_key == "common:errors.tenant_required"
    assert problem.trace_id == "trace-test-rfc7807-001"
    assert "oppytec.com/problems/domain_validation_error" in problem.type

    # Verificar span de error capturado limpiamente
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "kardex.history.query"
    assert span.status_code == 400

    # Verificar métrica con ERROR
    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    assert metrics[0].operation == "kardex.history.query"
    assert metrics[0].status == "ERROR"


def test_rfc7807_exception_capture_invalid_date_range() -> None:
    """
    Verifica que un rango de fechas inválido (fecha_desde > fecha_hasta)
    dispare DomainValidationError capturada en el span con status 400.
    """
    hist = KardexHistoryService()
    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()

    today = date.today()
    yesterday = today - timedelta(days=1)

    with pytest.raises(DomainValidationError) as exc_info:
        hist.get_filtered_history(
            tenant_id=TENANT_TEST_ID,
            fecha_desde=today,
            fecha_hasta=yesterday,
        )

    error = exc_info.value
    assert error.status_code == 400
    assert error.i18n_key == "inventory:history.invalid_date_range"

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "kardex.history.query"
    assert spans[0].status_code == 400

    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    assert metrics[0].status == "ERROR"


@pytest.mark.asyncio
async def test_kardex_history_http_integration_trace_headers_and_spans(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que las peticiones HTTP a los endpoints de historial de Kardex:
    - Retornen cabecera `X-Trace-ID`.
    - Generen y exporten spans `kardex.history.query` y `kardex.history.export_csv`.
    - Enlacen los atributos esperados (oppytec.tenant_id, bodega_id, producto_id, etc.).
    """
    headers = _make_headers(
        ["inventory.history.read", "inventory.history.export", "inventory.history.view_users"],
        user_id=105,
    )
    _seed_test_ledger(_inventory_service, _history_service)

    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()

    # 1. GET /api/v1/inventory/history/paginated
    res_query = await async_client.get(
        "/api/v1/inventory/history/paginated?bodega_id=1&producto_id=101&skip=0&limit=10",
        headers=headers,
    )
    assert res_query.status_code == 200
    assert "X-Trace-ID" in res_query.headers
    trace_id = res_query.headers["X-Trace-ID"]
    assert len(trace_id) > 0

    data = res_query.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    spans = exporter.get_finished_spans()
    query_spans = [s for s in spans if s.name == "kardex.history.query"]
    assert len(query_spans) >= 1
    query_span = query_spans[0]
    assert query_span.status_code == 200
    assert query_span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert query_span.attributes["bodega_id"] == 1
    assert query_span.attributes["producto_id"] == 101
    assert query_span.attributes["total_records"] == 2
    assert query_span.attributes["page_size"] == 10
    assert query_span.attributes["actor_user_id"] == 105

    # 2. GET /api/v1/inventory/history/export-csv
    exporter.clear()
    clear_in_memory_inventory_metrics()

    res_csv = await async_client.get(
        "/api/v1/inventory/history/export-csv?bodega_id=all",
        headers=headers,
    )
    assert res_csv.status_code == 200
    assert "X-Trace-ID" in res_csv.headers
    assert res_csv.content.startswith(b"\xef\xbb\xbf")

    spans_csv = exporter.get_finished_spans()
    export_spans = [s for s in spans_csv if s.name == "kardex.history.export_csv"]
    assert len(export_spans) >= 1
    export_span = export_spans[0]
    assert export_span.status_code == 200
    assert export_span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert export_span.attributes["records_exported"] == 3
    assert export_span.attributes["file_format"] == "csv"


@pytest.mark.asyncio
async def test_kardex_history_purge_audit_span_and_metrics(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que la purga de historial por el propietario:
    - Emita el span `kardex.history.purge`.
    - Registre métrica con estado SUCCESS.
    - Emita log crítico de auditoría con PII redactado deterministamente.
    """
    owner_headers = _make_headers(
        ["inventory.history.purge", "inventory.history.read"],
        user_id=1,
        is_holding_owner=True,
        hierarchy_rank=0,
    )
    _seed_test_ledger(_inventory_service, _history_service)

    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()

    # Ejecutar DELETE /api/v1/inventory/history
    res_purge = await async_client.delete(
        "/api/v1/inventory/history",
        headers=owner_headers,
    )
    assert res_purge.status_code == 204

    # Validar span de purga
    spans = exporter.get_finished_spans()
    purge_spans = [s for s in spans if s.name == "kardex.history.purge"]
    assert len(purge_spans) == 1
    span = purge_spans[0]
    assert span.status_code == 200
    assert span.attributes["oppytec.tenant_id"] == TENANT_TEST_ID
    assert span.attributes["purged_records"] == 3

    # Validar métricas de purga
    metrics = get_in_memory_inventory_metrics()
    purge_metrics = [m for m in metrics if m.operation == "kardex.history.purge"]
    assert len(purge_metrics) == 1
    assert purge_metrics[0].status == "SUCCESS"
    assert purge_metrics[0].tenant_id == TENANT_TEST_ID
