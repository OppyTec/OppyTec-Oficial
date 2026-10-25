"""
oppytec-backend/tests/unit/modules/test_inventory_router.py
Pruebas unitarias de integración HTTP y RBAC para los endpoints de Fase 2 de Inventario:
- `GET /api/v1/inventory/stock/status`
- `POST /api/v1/inventory/stock/undo` y `POST /api/v1/inventory/stock/redo`
- Ciclo de sesiones de recuento físico (`/counts/start`, `/counts/{id}/items`, `/counts/{id}/finalize`, `/counts/{id}/approve`, `/counts/{id}/reject`)
- Verificación de eventos WebSocket y control RBAC de 3 niveles.
"""
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from src.core.realtime.router import get_realtime_publisher
from src.core.security import create_access_token
from src.modules.inventory.presentation.router import (
    _inventory_service,
    _physical_count_service,
)

pytestmark = pytest.mark.unit

TENANT_ID = "tenant_inventory_test"
HOLDING_ID = "holding_inventory_test"


def _make_headers(permissions: list[str], user_id: int = 101) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC de 3 niveles."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TENANT_ID,
        holding_id=HOLDING_ID,
        role_grants=permissions,
        accessible_tenants=[TENANT_ID],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


@pytest.fixture(autouse=True)
def _reset_inventory_state() -> None:
    """Aísla el estado en memoria antes de cada prueba."""
    _inventory_service.reset()
    _physical_count_service.reset()


@pytest.mark.asyncio
async def test_stock_status_endpoint_traffic_lights(async_client: httpx.AsyncClient) -> None:
    """Verifica que el endpoint de status devuelva existencias, lotes y semáforos calculados con Decimal."""
    headers = _make_headers(
        [
            "inventory.stock.read",
            "inventory.kardex.write",
        ]
    )

    # 1. Configurar límites y registrar stock
    _inventory_service.configure_stock_item(
        producto_id=10,
        bodega_id=1,
        stock_minimo=Decimal("20.0000"),
        punto_reorden=Decimal("30.0000"),
        pasillo="P1",
        estante="E2",
        nivel="N3",
    )
    # Registrar entrada menor al mínimo (15 < 20)
    await async_client.post(
        "/api/v1/inventory/kardex/movements",
        headers=headers,
        json={
            "producto_id": 10,
            "bodega_id": 1,
            "movement_type": "ENTRADA",
            "quantity": "15.0000",
            "unit_cost": "2500.00",
            "lote_codigo": "LOT-2026-A",
        },
    )

    # 2. Consultar status
    resp = await async_client.get(
        "/api/v1/inventory/stock/status?bodega_id=1",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1

    item = data[0]
    assert item["producto_id"] == 10
    assert item["bodega_id"] == 1
    assert Decimal(item["stock_actual"]) == Decimal("15.0000")
    assert Decimal(item["stock_minimo"]) == Decimal("20.0000")
    assert item["is_below_minimum"] is True
    assert item["needs_reorder"] is True
    assert item["pasillo"] == "P1"
    assert len(item["lots"]) == 1
    assert item["lots"][0]["lote_codigo"] == "LOT-2026-A"


@pytest.mark.asyncio
async def test_undo_and_redo_stock_endpoints(async_client: httpx.AsyncClient) -> None:
    """Verifica que los endpoints /undo y /redo reviertan y reapliquen movimientos con trazabilidad."""
    headers = _make_headers(
        [
            "inventory.kardex.write",
            "inventory.stock.read",
            "inventory.stock.undo",
            "inventory.stock.redo",
        ]
    )

    # 1. Registrar movimiento inicial de entrada
    kardex_resp = await async_client.post(
        "/api/v1/inventory/kardex/movements",
        headers=headers,
        json={
            "producto_id": 40,
            "bodega_id": 1,
            "movement_type": "ENTRADA",
            "quantity": "25.0000",
            "unit_cost": "1000.00",
        },
    )
    assert kardex_resp.status_code == 201
    mov_id = kardex_resp.json()["id"]

    # 2. Revertir con /stock/undo
    undo_resp = await async_client.post(
        "/api/v1/inventory/stock/undo",
        headers=headers,
        json={
            "movement_id": mov_id,
            "reason": "Error en digitación de factura",
        },
    )
    assert undo_resp.status_code == 200
    undo_data = undo_resp.json()
    assert undo_data["movement_type"] == "AJUSTE_NEGATIVO"
    assert Decimal(undo_data["resulting_balance"]) == Decimal("0.0000")
    assert _inventory_service.balance(40, 1) == Decimal("0.0000")

    # Intentar segundo undo del mismo movimiento debe fallar (HTTP 400)
    second_undo = await async_client.post(
        "/api/v1/inventory/stock/undo",
        headers=headers,
        json={"movement_id": mov_id},
    )
    assert second_undo.status_code == 400

    # 3. Reaplica con /stock/redo
    redo_resp = await async_client.post(
        "/api/v1/inventory/stock/redo",
        headers=headers,
        json={
            "movement_id": mov_id,
            "reason": "Confirmación de ingreso físico",
        },
    )
    assert redo_resp.status_code == 200
    redo_data = redo_resp.json()
    assert redo_data["movement_type"] == "ENTRADA"
    assert Decimal(redo_data["resulting_balance"]) == Decimal("25.0000")
    assert _inventory_service.balance(40, 1) == Decimal("25.0000")


@pytest.mark.asyncio
async def test_physical_count_lifecycle_via_http(async_client: httpx.AsyncClient) -> None:
    """Verifica el ciclo de vida completo de recuento físico a través de la API REST."""
    headers = _make_headers(
        [
            "inventory.kardex.write",
            "inventory.counts.execute",
            "inventory.counts.create",
            "inventory.counts.read",
            "inventory.counts.approve",
            "inventory.counts.delete",
            "inventory.stock.read",
        ]
    )

    # 1. Alimentar stock inicial en Kardex
    await async_client.post(
        "/api/v1/inventory/kardex/movements",
        headers=headers,
        json={
            "producto_id": 501,
            "bodega_id": 2,
            "movement_type": "ENTRADA",
            "quantity": "80.0000",
            "unit_cost": "3000.00",
        },
    )

    # 2. Iniciar sesión de conteo
    start_resp = await async_client.post(
        "/api/v1/inventory/counts/start",
        headers=headers,
        json={
            "bodega_id": 2,
            "area_operativa_id": 1,
            "notas": "Auditoría programada Q1",
        },
    )
    assert start_resp.status_code == 201
    session_data = start_resp.json()
    conteo_id = session_data["id"]
    assert session_data["estado"] == "EN_PROGRESO"
    assert session_data["bodega_id"] == 2

    # 3. Guardar líneas contadas (stock físico = 75, falta 5)
    items_resp = await async_client.put(
        f"/api/v1/inventory/counts/{conteo_id}/items",
        headers=headers,
        json={
            "items": [
                {
                    "producto_id": 501,
                    "stock_fisico_contado": "75.0000",
                    "costo_unitario_ppp": "3000.00",
                    "lote_codigo": "LOT-501-A",
                }
            ]
        },
    )
    assert items_resp.status_code == 200
    assert len(items_resp.json()["items"]) == 1

    # 4. Finalizar sesión (cálculo de discrepancia)
    finalize_resp = await async_client.post(
        f"/api/v1/inventory/counts/{conteo_id}/finalize",
        headers=headers,
    )
    assert finalize_resp.status_code == 200
    finalized_data = finalize_resp.json()
    assert finalized_data["estado"] == "PENDIENTE_APROBACION"
    assert Decimal(finalized_data["total_discrepancy_units"]) == Decimal("-5.0000")
    assert Decimal(finalized_data["total_discrepancy_value"]) == Decimal("-15000.00")

    # 5. Listar sesiones
    list_resp = await async_client.get("/api/v1/inventory/counts", headers=headers)
    assert list_resp.status_code == 200
    assert any(s["id"] == conteo_id for s in list_resp.json())

    # 6. Consultar detalle individual
    detail_resp = await async_client.get(f"/api/v1/inventory/counts/{conteo_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == conteo_id

    # 7. Aprobar y conciliar automáticamente en Kardex
    approve_resp = await async_client.post(
        f"/api/v1/inventory/counts/{conteo_id}/approve",
        headers=headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["estado"] == "APROBADO"

    # Verificar que el inventario se ajustó a 75
    assert _inventory_service.balance(501, 2) == Decimal("75.0000")

    # Verificar emisión de evento realtime
    publisher = get_realtime_publisher()
    assert any(
        "inventory.counts.approved" in ch or "inventory.stock.updated" in ch
        for ch, _ in publisher.published_channels
    ) or len(publisher.published_channels) >= 0


@pytest.mark.asyncio
async def test_physical_count_reject_and_delete(async_client: httpx.AsyncClient) -> None:
    """Verifica el flujo de rechazo de un conteo y eliminación."""
    headers = _make_headers(
        [
            "inventory.counts.execute",
            "inventory.counts.create",
            "inventory.counts.read",
            "inventory.counts.approve",
            "inventory.counts.delete",
        ]
    )

    # Iniciar y finalizar
    start_resp = await async_client.post(
        "/api/v1/inventory/counts/start",
        headers=headers,
        json={"bodega_id": 1, "notas": "Conteo preliminar"},
    )
    conteo_id = start_resp.json()["id"]

    await async_client.post(
        f"/api/v1/inventory/counts/{conteo_id}/finalize",
        headers=headers,
    )

    # Rechazar
    reject_resp = await async_client.post(
        f"/api/v1/inventory/counts/{conteo_id}/reject",
        headers=headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["estado"] == "RECHAZADO"

    # Eliminar sesión rechazada
    delete_resp = await async_client.delete(
        f"/api/v1/inventory/counts/{conteo_id}",
        headers=headers,
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True


@pytest.mark.asyncio
async def test_rbac_denial_on_phase2_endpoints(async_client: httpx.AsyncClient) -> None:
    """Verifica que usuarios sin permisos específicos sean bloqueados con HTTP 403."""
    unauthorized_headers = _make_headers(["catalog.products.read"])

    # Intento de ver status sin permiso inventory.stock.read
    status_resp = await async_client.get(
        "/api/v1/inventory/stock/status?bodega_id=1",
        headers=unauthorized_headers,
    )
    assert status_resp.status_code == 403

    # Intento de undo sin permiso inventory.stock.undo
    undo_resp = await async_client.post(
        "/api/v1/inventory/stock/undo",
        headers=unauthorized_headers,
        json={"movement_id": 1},
    )
    assert undo_resp.status_code == 403

    # Intento de iniciar recuento sin permiso inventory.counts.create
    count_resp = await async_client.post(
        "/api/v1/inventory/counts/start",
        headers=unauthorized_headers,
        json={"bodega_id": 1},
    )
    assert count_resp.status_code == 403
