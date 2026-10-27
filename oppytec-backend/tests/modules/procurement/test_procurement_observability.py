"""
oppytec-backend/tests/modules/procurement/test_procurement_observability.py
Suite de Pruebas de Observabilidad 4-Pilares para Abastecimiento y Mermas Analíticas (Tarea 7.3 / Regla 17):
- Emisión y atributos de los spans OpenTelemetry:
  * `procurement.order.create` (tenant_id, order_id, supplier_id, bodega_id, items_count, monto_neto, monto_total)
  * `procurement.order.receive` (tenant_id, order_id, supplier_id, bodega_id, estado, receptor_user_id)
  * `inventory.waste.analytics_query` (tenant_id, bodega_id, total_perdida_ppp, items_mermados_count)
- Sanitización estricta y determinista de PII (PII scrubbing) en logs JSON, eventos Sentry/GlitchTip
  y atributos de span para datos sensibles de proveedores:
  `rut_tax_id`, `email_contacto`, `telefono`, `direccion`.
- Preservación estricta de la regla inmutable "Pollo King" en `razon_social` / `supplier_name`.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal

import httpx
import pytest
from pydantic import SecretStr

from src.core.exceptions import (
    DomainValidationError,
    ProperNounImmutabilityError,
    ResourceNotFoundError,
)
from src.core.observability import (
    REDACTED_MARKER,
    bind_tenant_telemetry_context,
    clear_in_memory_inventory_metrics,
    format_structured_log,
    get_in_memory_exporter,
    get_in_memory_inventory_metrics,
    reset_tenant_telemetry_context,
    scrub_sentry_event,
    scrub_telemetry_payload,
)
from src.core.security import create_access_token
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.application.merma_analytics_service import (
    MermaAnalyticsService,
)
from src.modules.inventory.presentation.router import _merma_analytics_service
from src.modules.procurement.application.procurement_service import (
    ProcurementService,
)
from src.modules.procurement.application.supplier_service import (
    SupplierService,
)
from src.modules.procurement.presentation.router import (
    _procurement_service,
    _supplier_service,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

TENANT_OBS_ID = "tenant_obs_procurement_test"
HOLDING_OBS_ID = "holding_obs_procurement_test"


@pytest.fixture(autouse=True)
def _clean_observability_and_procurement_state() -> None:
    """Limpia el exportador de spans, métricas en memoria y estado de servicios antes de cada test."""
    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()
    _procurement_service.reset_in_memory_store()
    _supplier_service.reset_in_memory_store()
    _merma_analytics_service.reset_in_memory_store()
    _procurement_service.enable_in_memory_mode()
    _supplier_service.enable_in_memory_mode()
    _merma_analytics_service.enable_in_memory_mode()


def _make_auth_headers(permissions: list[str], user_id: int = 501) -> dict[str, str]:
    """Genera cabeceras HTTP autenticadas con JWT y contexto de Tenant."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TENANT_OBS_ID,
        holding_id=HOLDING_OBS_ID,
        role_grants=permissions,
        accessible_tenants=[TENANT_OBS_ID],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_OBS_ID,
        "X-Holding-ID": HOLDING_OBS_ID,
    }


# ============================================================================
# 1. SPANS OPENTELEMETRY: `procurement.order.create` Y `procurement.order.receive`
# ============================================================================


async def test_procurement_order_create_and_receive_otel_spans_and_metrics() -> None:
    """
    Certifica que `create_order` y `receive_goods` emitan los spans distribuidos
    `procurement.order.create` y `procurement.order.receive` con los atributos:
    - `tenant_id` / `oppytec.tenant_id`
    - `order_id`
    - `supplier_id`
    - `bodega_id`
    Y registren las métricas operativas deterministas correspondientes.
    """
    inv_service = InventoryService()
    proc_service = ProcurementService(inventory_service=inv_service, use_in_memory=True)
    exporter = get_in_memory_exporter()

    # 1. Crear orden de compra -> span `procurement.order.create`
    order = await proc_service.create_order(
        None,
        {
            "numero_orden": "OC-OBS-2026-0001",
            "proveedor_id": 77,
            "supplier_name": "Pollo King",
            "bodega_destino_id": 4,
            "estado": "SOLICITADA",
            "items": [
                {
                    "producto_id": 301,
                    "cantidad_solicitada": Decimal("25.0000"),
                    "costo_unitario_neto": Decimal("4000.00"),
                }
            ],
        },
        user_id=88,
        tenant_id=TENANT_OBS_ID,
    )
    order_id = order["id"]
    assert order_id is not None

    spans = exporter.get_finished_spans()
    create_spans = [s for s in spans if s.name == "procurement.order.create"]
    assert len(create_spans) == 1
    c_span = create_spans[0]

    assert c_span.status_code == 200
    assert c_span.attributes["tenant_id"] == TENANT_OBS_ID
    assert c_span.attributes["oppytec.tenant_id"] == TENANT_OBS_ID
    assert c_span.attributes["order_id"] == order_id
    assert c_span.attributes["supplier_id"] == 77
    assert c_span.attributes["bodega_id"] == 4
    assert c_span.attributes["numero_orden"] == "OC-OBS-2026-0001"
    assert c_span.attributes["items_count"] == 1
    assert c_span.attributes["supplier_name"] == "Pollo King"
    assert c_span.attributes["razon_social"] == "Pollo King"
    assert c_span.attributes["user_id"] == "88"

    metrics = get_in_memory_inventory_metrics()
    create_metrics = [m for m in metrics if m.operation == "procurement.order.create"]
    assert len(create_metrics) == 1
    assert create_metrics[0].status == "SUCCESS"
    assert create_metrics[0].tenant_id == TENANT_OBS_ID
    assert create_metrics[0].bodega_id == 4
    assert create_metrics[0].user_id == "88"

    # 2. Recepcionar mercadería -> span `procurement.order.receive` + span hijo `inventory.movement.register`
    exporter.clear()
    clear_in_memory_inventory_metrics()

    received_order = await proc_service.receive_goods(
        None,
        order_id=order_id,
        items_received=[
            {
                "producto_id": 301,
                "cantidad_recibida": Decimal("25.0000"),
                "costo_unitario_neto": Decimal("4000.00"),
                "lote_codigo": "LOTE-PK-OBS-01",
            }
        ],
        user_id=99,
        tenant_id=TENANT_OBS_ID,
    )
    assert received_order["estado"] == "RECIBIDA_TOTAL"

    rec_spans = exporter.get_finished_spans()
    receive_spans = [s for s in rec_spans if s.name == "procurement.order.receive"]
    kardex_spans = [s for s in rec_spans if s.name == "inventory.movement.register"]
    assert len(receive_spans) == 1
    assert len(kardex_spans) == 1

    r_span = receive_spans[0]
    assert r_span.status_code == 200
    assert r_span.attributes["tenant_id"] == TENANT_OBS_ID
    assert r_span.attributes["oppytec.tenant_id"] == TENANT_OBS_ID
    assert r_span.attributes["order_id"] == order_id
    assert r_span.attributes["supplier_id"] == 77
    assert r_span.attributes["bodega_id"] == 4
    assert r_span.attributes["estado"] == "RECIBIDA_TOTAL"
    assert r_span.attributes["receptor_user_id"] == 99
    assert r_span.attributes["supplier_name"] == "Pollo King"

    k_span = kardex_spans[0]
    assert k_span.attributes["tenant_id"] == TENANT_OBS_ID
    assert k_span.attributes["bodega_id"] == 4
    assert k_span.attributes["movement_type"] == "COMPRA"

    rec_metrics = get_in_memory_inventory_metrics()
    r_metric = next(m for m in rec_metrics if m.operation == "procurement.order.receive")
    assert r_metric.status == "SUCCESS"
    assert r_metric.tenant_id == TENANT_OBS_ID
    assert r_metric.bodega_id == 4
    assert r_metric.user_id == "99"


async def test_procurement_spans_exception_capture_on_domain_errors() -> None:
    """Verifica que errores de validación y recursos no encontrados marquen el span en estado ERROR."""
    proc_service = ProcurementService(use_in_memory=True)
    exporter = get_in_memory_exporter()

    # 1. Crear orden sin ítems -> DomainValidationError (status 400)
    with pytest.raises(DomainValidationError):
        await proc_service.create_order(
            None,
            {
                "proveedor_id": 10,
                "bodega_destino_id": 2,
                "items": [],
            },
            user_id=50,
            tenant_id=TENANT_OBS_ID,
        )

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "procurement.order.create"
    assert spans[0].status_code == 400
    assert spans[0].attributes["tenant_id"] == TENANT_OBS_ID
    assert spans[0].attributes["supplier_id"] == 10
    assert spans[0].attributes["bodega_id"] == 2

    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    assert metrics[0].operation == "procurement.order.create"
    assert metrics[0].status == "ERROR"

    # 2. Recepcionar orden inexistente -> ResourceNotFoundError (status 404)
    exporter.clear()
    clear_in_memory_inventory_metrics()

    with pytest.raises(ResourceNotFoundError):
        await proc_service.receive_goods(
            None,
            order_id=99999,
            items_received=[{"producto_id": 1, "cantidad_recibida": Decimal("5.0000")}],
            user_id=50,
            tenant_id=TENANT_OBS_ID,
        )

    spans_rec = exporter.get_finished_spans()
    assert len(spans_rec) == 1
    assert spans_rec[0].name == "procurement.order.receive"
    assert spans_rec[0].status_code == 404
    assert spans_rec[0].attributes["order_id"] == 99999
    assert spans_rec[0].attributes["tenant_id"] == TENANT_OBS_ID


# ============================================================================
# 2. SPAN OPENTELEMETRY: `inventory.waste.analytics_query`
# ============================================================================


async def test_inventory_waste_analytics_query_otel_span_and_attributes() -> None:
    """
    Certifica que `MermaAnalyticsService.get_analytics` emita el span
    `inventory.waste.analytics_query` con `tenant_id`, `bodega_id`,
    `total_perdida_ppp`, `items_mermados_count` y `mermas_pendientes_aprobacion`.
    """
    analytics_service = MermaAnalyticsService(use_in_memory=True)
    analytics_service.register_in_memory_merma({
        "id": 1,
        "producto_id": 501,
        "bodega_id": 3,
        "cantidad": Decimal("4.0000"),
        "costo_total": Decimal("18000.00"),
        "motivo": "VENCIMIENTO",
        "estado_aprobacion": "APROBADA",
        "categoria_id": 10,
        "categoria_nombre": "Aves",
        "fecha_merma": date.today().isoformat(),
    })
    analytics_service.register_in_memory_merma({
        "id": 2,
        "producto_id": 502,
        "bodega_id": 3,
        "cantidad": Decimal("2.0000"),
        "costo_total": Decimal("7000.00"),
        "motivo": "DETERIORO",
        "estado_aprobacion": "PENDIENTE",
        "categoria_id": 10,
        "categoria_nombre": "Aves",
        "fecha_merma": date.today().isoformat(),
    })

    exporter = get_in_memory_exporter()
    exporter.clear()
    clear_in_memory_inventory_metrics()

    tokens = bind_tenant_telemetry_context(
        trace_id="trace-waste-analytics-0001",
        tenant_id=TENANT_OBS_ID,
        holding_id=HOLDING_OBS_ID,
    )
    try:
        result = await analytics_service.get_analytics(
            None,
            bodega_id=3,
        )
    finally:
        reset_tenant_telemetry_context(tokens)

    assert result["total_perdida_ppp"] == Decimal("25000.00")
    assert result["items_mermados_count"] == 2
    assert result["mermas_pendientes_aprobacion"] == 1

    spans = exporter.get_finished_spans()
    waste_spans = [s for s in spans if s.name == "inventory.waste.analytics_query"]
    assert len(waste_spans) == 1
    w_span = waste_spans[0]

    assert w_span.status_code == 200
    assert w_span.trace_id == "trace-waste-analytics-0001"
    assert w_span.attributes["tenant_id"] == TENANT_OBS_ID
    assert w_span.attributes["oppytec.tenant_id"] == TENANT_OBS_ID
    assert w_span.attributes["bodega_id"] == 3
    assert w_span.attributes["total_perdida_ppp"] == "25000.00"
    assert w_span.attributes["items_mermados_count"] == 2
    assert w_span.attributes["mermas_pendientes_aprobacion"] == 1

    metrics = get_in_memory_inventory_metrics()
    assert len(metrics) == 1
    assert metrics[0].operation == "inventory.waste.analytics_query"
    assert metrics[0].status == "SUCCESS"
    assert metrics[0].tenant_id == TENANT_OBS_ID
    assert metrics[0].bodega_id == 3


# ============================================================================
# 3. SANITIZACIÓN ESTRICTA DE PII (PII SCRUBBING) Y REGLA "POLLO KING"
# ============================================================================


async def test_supplier_pii_scrubbing_in_logs_spans_and_sentry_preserving_pollo_king(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Verifica y certifica el enmascaramiento determinista de PII de proveedores:
    - `rut_tax_id` -> `[REDACTED_PII]`
    - `email_contacto` -> `[REDACTED_PII]`
    - `telefono` -> `[REDACTED_PII]`
    - `direccion` -> `[REDACTED_PII]`
    tanto en logs estructurados JSON, eventos Sentry/GlitchTip y atributos de span OTel,
    sin alterar jamás la razón social inmutable "Pollo King".
    """
    raw_supplier_data: dict[str, object] = {
        "rut_tax_id": "76.543.210-3",
        "razon_social": "Pollo King",
        "nombre_fantasia": "Pollo King SpA",
        "email_contacto": "contacto@polloking.cl",
        "telefono": "+56911223344",
        "direccion": "Av. Providencia 1234, Santiago",
        "api_secret": SecretStr("sk_live_polloking_secret"),
        "notas": "Contacto directo: ventas@polloking.cl, RUT 76.543.210-3, móvil +56911223344 con Pollo King",
    }

    # 1. Validar `scrub_telemetry_payload` directo
    scrubbed = scrub_telemetry_payload(raw_supplier_data)
    assert scrubbed["rut_tax_id"] == REDACTED_MARKER
    assert scrubbed["email_contacto"] == REDACTED_MARKER
    assert scrubbed["telefono"] == REDACTED_MARKER
    assert scrubbed["direccion"] == REDACTED_MARKER
    assert scrubbed["api_secret"] == REDACTED_MARKER
    # Regla "Pollo King" intacta
    assert scrubbed["razon_social"] == "Pollo King"
    assert scrubbed["nombre_fantasia"] == "Pollo King SpA"
    # Patrones PII en texto libre redactados sin alterar "Pollo King"
    notas_scrubbed = str(scrubbed["notas"])
    assert "ventas@polloking.cl" not in notas_scrubbed
    assert "76.543.210-3" not in notas_scrubbed
    assert "+56911223344" not in notas_scrubbed
    assert "Pollo King" in notas_scrubbed

    # 2. Validar hook `scrub_sentry_event` para Sentry / GlitchTip
    sentry_event: dict[str, object] = {
        "event_id": "sentry-evt-001",
        "platform": "python",
        "request": {
            "url": "https://api.oppytec.com/api/v1/procurement/suppliers",
            "headers": {
                "Authorization": "Bearer jwt_secret_token",
                "X-Tenant-ID": TENANT_OBS_ID,
            },
            "data": raw_supplier_data,
        },
        "extra": {
            "supplier_snapshot": {
                "rut_tax_id": "76.543.210-3",
                "email_contacto": "finanzas@polloking.cl",
                "telefono": "+56999887766",
                "direccion": "Calle Industrial 999",
                "razon_social": "Pollo King",
            }
        },
    }
    clean_sentry = scrub_sentry_event(sentry_event)
    serialized_sentry = json.dumps(clean_sentry, ensure_ascii=False)
    assert "76.543.210-3" not in serialized_sentry
    assert "contacto@polloking.cl" not in serialized_sentry
    assert "finanzas@polloking.cl" not in serialized_sentry
    assert "+56911223344" not in serialized_sentry
    assert "+56999887766" not in serialized_sentry
    assert "Av. Providencia 1234" not in serialized_sentry
    assert "Calle Industrial 999" not in serialized_sentry
    assert "jwt_secret_token" not in serialized_sentry
    assert "Pollo King" in serialized_sentry

    # 3. Validar log estructurado en alta de proveedor (`SupplierService.create_supplier`)
    supplier_svc = SupplierService(use_in_memory=True)
    with caplog.at_level(logging.INFO, logger="oppytec.procurement.supplier_service"):
        created_supplier = await supplier_svc.create_supplier(
            None,
            {
                "rut_tax_id": "76.543.210-3",
                "razon_social": "Pollo King",
                "nombre_fantasia": "Pollo King SpA",
                "email_contacto": "contacto@polloking.cl",
                "telefono": "+56911223344",
                "direccion": "Av. Providencia 1234",
            },
        )
    # El dominio retorna la entidad íntegra al llamador autorizado
    assert created_supplier["razon_social"] == "Pollo King"
    assert created_supplier["rut_tax_id"] == "76.543.210-3"

    # Pero en los logs emitidos a Grafana Loki, el PII está 100% enmascarado
    supplier_logs = [r.message for r in caplog.records if "procurement.supplier.create" in r.message]
    assert len(supplier_logs) >= 1
    parsed_log = json.loads(supplier_logs[-1])
    assert parsed_log["data"]["razon_social"] == "Pollo King"
    assert parsed_log["data"]["rut_tax_id"] == REDACTED_MARKER
    assert parsed_log["data"]["email_contacto"] == REDACTED_MARKER
    assert parsed_log["data"]["telefono"] == REDACTED_MARKER
    assert parsed_log["data"]["direccion"] == REDACTED_MARKER
    assert "76.543.210-3" not in supplier_logs[-1]
    assert "contacto@polloking.cl" not in supplier_logs[-1]
    assert "+56911223344" not in supplier_logs[-1]
    assert "Av. Providencia 1234" not in supplier_logs[-1]

    # Verificar que la regla "Pollo King" sigue bloqueando intentos de traducción
    with pytest.raises(ProperNounImmutabilityError):
        await supplier_svc.update_supplier(
            None,
            created_supplier["id"],
            {"razon_social": "Chicken King Translated"},
        )

    # 4. Validar enmascaramiento PII en atributos de span `procurement.order.create`
    exporter = get_in_memory_exporter()
    exporter.clear()
    proc_svc = ProcurementService(use_in_memory=True)

    await proc_svc.create_order(
        None,
        {
            "proveedor_id": created_supplier["id"],
            "supplier_name": "Pollo King",
            "rut_tax_id": "76.543.210-3",
            "email_contacto": "contacto@polloking.cl",
            "telefono": "+56911223344",
            "direccion": "Av. Providencia 1234",
            "bodega_destino_id": 1,
            "items": [
                {
                    "producto_id": 10,
                    "cantidad_solicitada": Decimal("5.0000"),
                    "costo_unitario_neto": Decimal("3500.00"),
                }
            ],
        },
        user_id=70,
        tenant_id=TENANT_OBS_ID,
    )

    spans = exporter.get_finished_spans()
    order_span = next(s for s in spans if s.name == "procurement.order.create")
    assert order_span.attributes["rut_tax_id"] == REDACTED_MARKER
    assert order_span.attributes["email_contacto"] == REDACTED_MARKER
    assert order_span.attributes["telefono"] == REDACTED_MARKER
    assert order_span.attributes["direccion"] == REDACTED_MARKER
    assert order_span.attributes["supplier_name"] == "Pollo King"
    assert order_span.attributes["razon_social"] == "Pollo King"

    raw_attrs_str = str(order_span.attributes)
    assert "76.543.210-3" not in raw_attrs_str
    assert "contacto@polloking.cl" not in raw_attrs_str
    assert "+56911223344" not in raw_attrs_str
    assert "Av. Providencia 1234" not in raw_attrs_str


# ============================================================================
# 4. INTEGRACIÓN HTTP EXTREMO A EXTREMO (FastAPI AsyncClient + Spans + X-Trace-ID)
# ============================================================================


async def test_http_endpoints_emit_procurement_and_waste_analytics_spans(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que los endpoints REST de Abastecimiento y Mermas Analíticas
    propaguen `X-Trace-ID` y exporten los spans `procurement.order.create`,
    `procurement.order.receive` e `inventory.waste.analytics_query`.
    """
    headers = _make_auth_headers(
        [
            "procurement.orders.create",
            "procurement.orders.receive",
            "procurement.orders.read",
            "inventory.mermas.create",
            "inventory.mermas.view",
        ],
        user_id=501,
    )
    exporter = get_in_memory_exporter()
    exporter.clear()

    # 1. POST /api/v1/procurement/orders -> `procurement.order.create`
    create_resp = await async_client.post(
        "/api/v1/procurement/orders",
        headers=headers,
        json={
            "numero_orden": "OC-HTTP-OBS-01",
            "proveedor_id": 12,
            "supplier_name": "Pollo King",
            "bodega_destino_id": 2,
            "estado": "SOLICITADA",
            "items": [
                {
                    "producto_id": 50,
                    "cantidad_solicitada": "10.0000",
                    "costo_unitario_neto": "2500.00",
                }
            ],
        },
    )
    assert create_resp.status_code == 201
    assert "X-Trace-ID" in create_resp.headers
    order_id = create_resp.json()["id"]

    # 2. POST /api/v1/procurement/orders/{order_id}/receive -> `procurement.order.receive`
    receive_resp = await async_client.post(
        f"/api/v1/procurement/orders/{order_id}/receive",
        headers=headers,
        json={
            "items": [
                {
                    "producto_id": 50,
                    "cantidad_recibida": "10.0000",
                    "lote_codigo": "L-HTTP-01",
                }
            ]
        },
    )
    assert receive_resp.status_code == 200
    assert "X-Trace-ID" in receive_resp.headers

    # 3. GET /api/v1/inventory/mermas/analytics -> `inventory.waste.analytics_query`
    analytics_resp = await async_client.get(
        "/api/v1/inventory/mermas/analytics?bodega_id=2",
        headers=headers,
    )
    assert analytics_resp.status_code == 200
    assert "X-Trace-ID" in analytics_resp.headers

    spans = exporter.get_finished_spans()
    span_names = [s.name for s in spans]
    assert "procurement.order.create" in span_names
    assert "procurement.order.receive" in span_names
    assert "inventory.waste.analytics_query" in span_names

    c_span = next(s for s in spans if s.name == "procurement.order.create")
    assert c_span.attributes["tenant_id"] == TENANT_OBS_ID
    assert c_span.attributes["order_id"] == order_id
    assert c_span.attributes["supplier_id"] == 12
    assert c_span.attributes["bodega_id"] == 2

    r_span = next(s for s in spans if s.name == "procurement.order.receive")
    assert r_span.attributes["tenant_id"] == TENANT_OBS_ID
    assert r_span.attributes["order_id"] == order_id
    assert r_span.attributes["supplier_id"] == 12
    assert r_span.attributes["bodega_id"] == 2

    w_span = next(s for s in spans if s.name == "inventory.waste.analytics_query")
    assert w_span.attributes["tenant_id"] == TENANT_OBS_ID
    assert w_span.attributes["bodega_id"] == 2
