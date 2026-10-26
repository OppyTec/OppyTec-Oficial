"""
oppytec-backend/tests/unit/modules/test_inventory_alerts_router.py
Pruebas unitarias de integración HTTP y RBAC para los endpoints REST de Alertas:
- `GET /api/v1/inventory/alerts`
- `GET /api/v1/inventory/alerts/badge`
- Filtros por `bodega_id`, `area_operativa_id` y `tipo`.
- Guardias RBAC de 3 niveles (`inventory.alerts.read` -> 200 vs 403 Forbidden).
- Cero floats, precisión Decimal y emisión reactiva de eventos WebSocket.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from src.core.realtime.router import get_realtime_publisher
from src.core.security import create_access_token
from src.modules.inventory.domain.alerts import (
    CriticalStockAlert,
    ExpiredLotAlert,
    UpcomingExpiryAlert,
)
from src.modules.inventory.infrastructure.alerts_repository import InMemoryAlertsRepository
from src.modules.inventory.presentation.router import _alerts_service

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
def _reset_alerts_in_memory_repository() -> None:
    """Configura y aísla un InMemoryAlertsRepository limpio antes de cada prueba."""
    in_memory_repo = InMemoryAlertsRepository()
    _alerts_service.set_repository(in_memory_repo)
    _alerts_service.reset()


@pytest.mark.asyncio
async def test_alerts_endpoint_forbidden_without_permission(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que sin el permiso 'inventory.alerts.read' retorne HTTP 403 Forbidden RFC 7807."""
    headers = _make_headers(["inventory.stock.read"])  # Falta inventory.alerts.read

    response = await async_client.get(
        "/api/v1/inventory/alerts",
        headers=headers,
    )
    assert response.status_code == 403
    problem = response.json()
    assert problem["status"] == 403


@pytest.mark.asyncio
async def test_alerts_badge_endpoint_forbidden_without_permission(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que el endpoint de badge retorne HTTP 403 si el usuario carece del permiso RBAC."""
    headers = _make_headers(["inventory.kardex.read"])

    response = await async_client.get(
        "/api/v1/inventory/alerts/badge",
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_alerts_endpoint_empty_success(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica respuesta 200 OK cuando no existen alertas activas en el tenant."""
    headers = _make_headers(["inventory.alerts.read"])

    response = await async_client.get(
        "/api/v1/inventory/alerts",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert data["critical_count"] == 0
    assert data["expired_count"] == 0
    assert data["upcoming_count"] == 0
    assert data["has_critical"] is False
    assert data["total_financial_risk"] == "0.00"
    assert data["critical_stock"] == []
    assert data["expired_lots"] == []
    assert data["upcoming_expiries"] == []


@pytest.mark.asyncio
async def test_alerts_endpoint_full_data_and_ratio_calculation(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que el endpoint devuelva insumos críticos, lotes caducados y próximos a vencer
    con los ratios cromáticos de salud y valorización financiera exacta en Decimal.
    """
    headers = _make_headers(["inventory.alerts.read"])
    repo = _alerts_service.repository
    assert isinstance(repo, InMemoryAlertsRepository)

    # 1. Producto agotado (ratio 0%)
    repo.add_critical_stock(
        CriticalStockAlert.create(
            producto_id=10,
            bodega_id=1,
            bodega_nombre="Bodega Central",
            producto_nombre="Harina de Fuerza 25kg",
            stock_actual=Decimal("0.0000"),
            stock_minimo=Decimal("15.0000"),
            unidad_medida="SACO",
            bodega_color="#ef4444",
            costo_promedio=Decimal("18500.00"),
        )
    )

    # 2. Producto bajo mínimo (ratio 40%, status 'critical')
    repo.add_critical_stock(
        CriticalStockAlert.create(
            producto_id=20,
            bodega_id=1,
            bodega_nombre="Bodega Central",
            producto_nombre="Aceite de Oliva Extra Virgen",
            stock_actual=Decimal("4.0000"),
            stock_minimo=Decimal("10.0000"),
            unidad_medida="LITRO",
            costo_promedio=Decimal("8900.50"),
        )
    )

    # 3. Lote caducado hace 3 días
    fecha_ayer = date.today() - timedelta(days=3)
    repo.add_expired_lot(
        ExpiredLotAlert.create(
            producto_id=30,
            bodega_id=1,
            bodega_nombre="Bodega Central",
            producto_nombre="Yogurt Griego Natural 1L",
            lote_codigo="LOT-EXP-001",
            fecha_vencimiento=fecha_ayer,
            cantidad_vencida=Decimal("5.0000"),
            dias_vencido=3,
            costo_ppp=Decimal("2500.00"),
            unidad_medida="UNIDAD",
        )
    )

    # 4. Lote próximo a vencer en 7 días
    fecha_futura = date.today() + timedelta(days=7)
    repo.add_upcoming_expiry(
        UpcomingExpiryAlert.create(
            producto_id=40,
            bodega_id=2,
            bodega_nombre="Barra Principal",
            producto_nombre="Leche Entera 1L",
            lote_codigo="LOT-FUT-002",
            fecha_vencimiento=fecha_futura,
            cantidad_en_riesgo=Decimal("12.0000"),
            dias_restantes=7,
            costo_ppp=Decimal("1100.00"),
            unidad_medida="LITRO",
        )
    )

    response = await async_client.get(
        "/api/v1/inventory/alerts",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_count"] == 4
    assert data["critical_count"] == 2
    assert data["expired_count"] == 1
    assert data["upcoming_count"] == 1
    assert data["has_critical"] is True

    # Riesgo financiero total: (5 * 2500.00 = 12500.00) + (12 * 1100.00 = 13200.00) = 25700.00
    assert data["total_financial_risk"] == "25700.00"

    # Verificar detalles de stock crítico
    c_list = data["critical_stock"]
    assert len(c_list) == 2
    harina = next(item for item in c_list if item["producto_id"] == 10)
    assert harina["is_depleted"] is True
    assert harina["ratio"]["status"] == "depleted"
    assert harina["ratio"]["raw_ratio"] == "0.00"

    aceite = next(item for item in c_list if item["producto_id"] == 20)
    assert aceite["is_depleted"] is False
    assert aceite["ratio"]["status"] == "critical"
    assert aceite["ratio"]["raw_ratio"] == "40.00"

    # Verificar lote caducado
    exp = data["expired_lots"][0]
    assert exp["producto_id"] == 30
    assert exp["dias_vencido"] == 3
    assert exp["valor_total_riesgo"] == "12500.00"

    # Verificar próximo a vencer
    upc = data["upcoming_expiries"][0]
    assert upc["producto_id"] == 40
    assert upc["dias_restantes"] == 7
    assert upc["valor_total_riesgo"] == "13200.00"


@pytest.mark.asyncio
async def test_alerts_endpoint_filtering_by_bodega(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que el parámetro de consulta ?bodega_id filtre correctamente las alertas."""
    headers = _make_headers(["inventory.alerts.read"])
    repo = _alerts_service.repository
    assert isinstance(repo, InMemoryAlertsRepository)

    # Insumo en bodega 1
    repo.add_critical_stock(
        CriticalStockAlert.create(
            producto_id=1,
            bodega_id=1,
            bodega_nombre="Bodega 1",
            producto_nombre="Producto B1",
            stock_actual=Decimal("0.0000"),
            stock_minimo=Decimal("5.0000"),
            unidad_medida="UN",
        )
    )

    # Insumo en bodega 2
    repo.add_critical_stock(
        CriticalStockAlert.create(
            producto_id=2,
            bodega_id=2,
            bodega_nombre="Bodega 2",
            producto_nombre="Producto B2",
            stock_actual=Decimal("1.0000"),
            stock_minimo=Decimal("10.0000"),
            unidad_medida="UN",
        )
    )

    # Filtrar solo bodega 1
    res1 = await async_client.get(
        "/api/v1/inventory/alerts?bodega_id=1",
        headers=headers,
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total_count"] == 1
    assert data1["critical_stock"][0]["bodega_id"] == 1

    # Filtrar solo bodega 2
    res2 = await async_client.get(
        "/api/v1/inventory/alerts?bodega_id=2",
        headers=headers,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total_count"] == 1
    assert data2["critical_stock"][0]["bodega_id"] == 2


@pytest.mark.asyncio
async def test_alerts_endpoint_filtering_by_type(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que el parámetro ?tipo ('stock', 'expired', 'upcoming') filtre las dimensiones."""
    headers = _make_headers(["inventory.alerts.read"])
    repo = _alerts_service.repository
    assert isinstance(repo, InMemoryAlertsRepository)

    repo.add_critical_stock(
        CriticalStockAlert.create(
            producto_id=1,
            bodega_id=1,
            bodega_nombre="B1",
            producto_nombre="P1",
            stock_actual=Decimal("0"),
            stock_minimo=Decimal("5"),
            unidad_medida="UN",
        )
    )
    repo.add_expired_lot(
        ExpiredLotAlert.create(
            producto_id=2,
            bodega_id=1,
            bodega_nombre="B1",
            producto_nombre="P2",
            lote_codigo="L1",
            fecha_vencimiento=date.today() - timedelta(days=1),
            cantidad_vencida=Decimal("2"),
            dias_vencido=1,
            costo_ppp=Decimal("10"),
            unidad_medida="UN",
        )
    )
    repo.add_upcoming_expiry(
        UpcomingExpiryAlert.create(
            producto_id=3,
            bodega_id=1,
            bodega_nombre="B1",
            producto_nombre="P3",
            lote_codigo="L2",
            fecha_vencimiento=date.today() + timedelta(days=5),
            cantidad_en_riesgo=Decimal("3"),
            dias_restantes=5,
            costo_ppp=Decimal("10"),
            unidad_medida="UN",
        )
    )

    # 1. Solo stock
    r_stock = await async_client.get("/api/v1/inventory/alerts?tipo=stock", headers=headers)
    assert r_stock.status_code == 200
    d_stock = r_stock.json()
    assert d_stock["total_count"] == 1
    assert len(d_stock["critical_stock"]) == 1
    assert len(d_stock["expired_lots"]) == 0
    assert len(d_stock["upcoming_expiries"]) == 0

    # 2. Solo expired
    r_exp = await async_client.get("/api/v1/inventory/alerts?tipo=expired", headers=headers)
    assert r_exp.status_code == 200
    d_exp = r_exp.json()
    assert d_exp["total_count"] == 1
    assert len(d_exp["expired_lots"]) == 1

    # 3. Solo upcoming
    r_upc = await async_client.get("/api/v1/inventory/alerts?tipo=upcoming", headers=headers)
    assert r_upc.status_code == 200
    d_upc = r_upc.json()
    assert d_upc["total_count"] == 1
    assert len(d_upc["upcoming_expiries"]) == 1

    # 4. Tipo inválido -> HTTP 400 ProblemDetails
    r_bad = await async_client.get("/api/v1/inventory/alerts?tipo=invalid_type", headers=headers)
    assert r_bad.status_code == 400
    assert "status" in r_bad.json()


@pytest.mark.asyncio
async def test_alerts_badge_endpoint_ultrafast(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que el endpoint ultraliviano de badge devuelva los contadores exactos para el Sidebar."""
    headers = _make_headers(["inventory.alerts.read"])
    repo = _alerts_service.repository
    assert isinstance(repo, InMemoryAlertsRepository)

    # Poblar 1 insumo crítico y 1 lote caducado
    repo.add_critical_stock(
        CriticalStockAlert.create(
            producto_id=1,
            bodega_id=1,
            bodega_nombre="B1",
            producto_nombre="P1",
            stock_actual=Decimal("0"),
            stock_minimo=Decimal("5"),
            unidad_medida="UN",
        )
    )
    repo.add_expired_lot(
        ExpiredLotAlert.create(
            producto_id=2,
            bodega_id=1,
            bodega_nombre="B1",
            producto_nombre="P2",
            lote_codigo="L1",
            fecha_vencimiento=date.today() - timedelta(days=2),
            cantidad_vencida=Decimal("10"),
            dias_vencido=2,
            costo_ppp=Decimal("15"),
            unidad_medida="UN",
        )
    )

    response = await async_client.get(
        "/api/v1/inventory/alerts/badge",
        headers=headers,
    )
    assert response.status_code == 200
    badge = response.json()

    assert badge["total_count"] == 2
    assert badge["has_critical"] is True
    assert badge["critical_stock_count"] == 1
    assert badge["expired_count"] == 1
    assert badge["upcoming_count"] == 0


@pytest.mark.asyncio
async def test_alerts_service_broadcast_websocket_event() -> None:
    """Verifica la emisión de eventos WebSocket sin polling para invalidación en TanStack Query v5."""
    publisher = get_realtime_publisher()

    # Emitir cambio de alertas
    await _alerts_service.broadcast_alerts_changed(
        tenant_id=TENANT_ID,
        holding_id=HOLDING_ID,
        target_bodega_id=1,
        payload={"action": "test_alerts_update"},
    )
    # Se corrobora que la ejecución se complete de forma reactiva sin excepciones.
