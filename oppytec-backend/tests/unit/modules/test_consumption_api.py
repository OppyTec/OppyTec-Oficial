"""
oppytec-backend/tests/unit/modules/test_consumption_api.py
Suite de pruebas unitarias y de integración REST para la Fase 2 de Consumo,
Manos Libres y Buffet Inteligente:
- Registro batch de consumo y explosión de recetas a Kardex.
- Verificación de que el saldo de stock descuenta con asiento inmutable.
- Detección de stock insuficiente arrojando error 409 ProblemDetails.
- Anulación y reversión transaccional en Kardex.
- Merma directa de lotes vencidos desde modal de contingencia.
- CRUD de plantillas de consumo rápido.
- Sesiones de Buffet Inteligente, cálculo de costo por Pax y liquidación.
- Comandos de Cocina por Voz / Manos Libres.
- Guardias RBAC de 3 niveles y control de acceso estricto.
"""
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from src.core.observability import get_in_memory_exporter
from src.core.security import create_access_token
from src.modules.inventory.presentation.router import _inventory_service
from src.modules.operations.domain.consumption_math import (
    RecipeIngredientItem,
    RecipeSpec,
)
from src.modules.operations.presentation.router import (
    _buffet_service,
    _consumption_service,
    _voice_kitchen_service,
)

pytestmark = pytest.mark.unit

TENANT_ID = "tenant_consumption_test"
HOLDING_ID = "holding_consumption_test"


def _make_headers(permissions: list[str], user_id: int = 201) -> dict[str, str]:
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
def _reset_operations_and_inventory_state() -> None:
    """Aísla el estado en memoria antes de cada prueba."""
    _inventory_service.reset()
    _consumption_service.reset()
    _buffet_service.reset()
    _voice_kitchen_service.reset()
    get_in_memory_exporter().clear()


@pytest.mark.asyncio
async def test_batch_consumption_success_with_recipe_explosion(async_client: httpx.AsyncClient) -> None:
    """Verifica consumo batch mixto con producto directo y receta explotada a Kardex."""
    headers = _make_headers(
        [
            "consumption.register.create",
            "consumption.register.read",
            "inventory.kardex.write",
            "inventory.stock.read",
        ]
    )

    bodega_id = 1

    # 1. Cargar stock inicial en Kardex
    # Producto 101 (Harina): 50.0000 kg
    # Producto 102 (Aceite): 20.0000 L
    # Producto 201 (Bebida lata): 30.0000 UN
    _inventory_service.register_movement(
        producto_id=101,
        bodega_id=bodega_id,
        movement_type="ENTRADA",
        quantity=Decimal("50.0000"),
        unit_cost=Decimal("1200.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )
    _inventory_service.register_movement(
        producto_id=102,
        bodega_id=bodega_id,
        movement_type="ENTRADA",
        quantity=Decimal("20.0000"),
        unit_cost=Decimal("2500.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )
    _inventory_service.register_movement(
        producto_id=201,
        bodega_id=bodega_id,
        movement_type="ENTRADA",
        quantity=Decimal("30.0000"),
        unit_cost=Decimal("800.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )

    # 2. Registrar especificación de receta en el servicio: Receta 10 (Pizza Masa)
    # 1 pizza requiere 0.5 kg de harina (101) y 0.1 L de aceite (102)
    _consumption_service.register_recipe_spec(
        recipe_id=10,
        spec=RecipeSpec(
            recipe_id=10,
            yield_portions=Decimal(1),
            ingredients=[
                RecipeIngredientItem(ingredient_id=101, quantity=Decimal("0.5000")),
                RecipeIngredientItem(ingredient_id=102, quantity=Decimal("0.1000")),
            ],
        ),
    )

    # 3. Registrar consumo batch: 4 pizzas (receta 10) y 5 bebidas (producto 201)
    payload = {
        "bodega_id": bodega_id,
        "items": [
            {
                "tipo_item": "RECETA",
                "item_id": 10,
                "cantidad": "4.0000",
                "costo_unitario_ppp": "850.00",
            },
            {
                "tipo_item": "PRODUCTO",
                "item_id": 201,
                "cantidad": "5.0000",
                "costo_unitario_ppp": "800.00",
            },
        ],
        "tipo_origen": "MANUAL_TERMINAL",
        "notas": "Consumo turno tarde cocina",
    }

    resp = await async_client.post("/api/v1/operations/consumption", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["codigo_folio"].startswith("CONS-")
    assert data["bodega_id"] == bodega_id
    assert len(data["items"]) == 2
    assert Decimal(data["costo_total"]) == Decimal("7400.00")  # (4 * 850) + (5 * 800) = 3400 + 4000 = 7400.00

    # 4. Verificar que el Kardex y balances de stock fueron descontados con exactitud
    # Harina (101): 50.0000 - (4 * 0.5) = 48.0000
    # Aceite (102): 20.0000 - (4 * 0.1) = 19.6000
    # Bebida (201): 30.0000 - 5.0000 = 25.0000
    assert _inventory_service.balance(101, bodega_id) == Decimal("48.0000")
    assert _inventory_service.balance(102, bodega_id) == Decimal("19.6000")
    assert _inventory_service.balance(201, bodega_id) == Decimal("25.0000")


@pytest.mark.asyncio
async def test_batch_consumption_insufficient_stock_raises_409(async_client: httpx.AsyncClient) -> None:
    """Verifica que intentar descontar existencias sin stock suficiente arroje HTTP 409 ProblemDetails."""
    headers = _make_headers(["consumption.register.create"])
    bodega_id = 1

    # Solo cargamos 5 unidades de stock
    _inventory_service.register_movement(
        producto_id=301,
        bodega_id=bodega_id,
        movement_type="ENTRADA",
        quantity=Decimal("5.0000"),
        unit_cost=Decimal("1000.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )

    # Intentar consumir 10 unidades debe fallar
    payload = {
        "bodega_id": bodega_id,
        "items": [
            {
                "tipo_item": "PRODUCTO",
                "item_id": 301,
                "cantidad": "10.0000",
            }
        ],
    }

    resp = await async_client.post("/api/v1/operations/consumption", headers=headers, json=payload)
    assert resp.status_code == 409
    error_data = resp.json()
    assert error_data["error_code"] == "INSUFFICIENT_STOCK"
    # El stock original debe mantenerse intacto (5.0000)
    assert _inventory_service.balance(301, bodega_id) == Decimal("5.0000")


@pytest.mark.asyncio
async def test_consumption_history_detail_and_update(async_client: httpx.AsyncClient) -> None:
    """Verifica historial cronológico paginado, consulta de detalle y actualización de notas."""
    headers = _make_headers(
        [
            "consumption.register.create",
            "consumption.register.read",
            "consumption.register.update",
        ]
    )

    # 1. Alimentar stock y registrar consumo
    _inventory_service.register_movement(
        producto_id=401,
        bodega_id=2,
        movement_type="ENTRADA",
        quantity=Decimal("100.0000"),
        unit_cost=Decimal("500.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )
    reg_resp = await async_client.post(
        "/api/v1/operations/consumption",
        headers=headers,
        json={
            "bodega_id": 2,
            "items": [{"tipo_item": "PRODUCTO", "item_id": 401, "cantidad": "12.0000"}],
            "notas": "Notas originales",
        },
    )
    assert reg_resp.status_code == 201
    record_id = reg_resp.json()["id"]

    # 2. Consultar historial
    hist_resp = await async_client.get(
        "/api/v1/operations/consumption/history?bodega_id=2",
        headers=headers,
    )
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["total"] == 1
    assert hist_data["items"][0]["id"] == record_id

    # 3. Consultar detalle
    det_resp = await async_client.get(
        f"/api/v1/operations/consumption/{record_id}",
        headers=headers,
    )
    assert det_resp.status_code == 200
    assert det_resp.json()["notas"] == "Notas originales"

    # 4. Actualizar notas
    upd_resp = await async_client.put(
        f"/api/v1/operations/consumption/{record_id}",
        headers=headers,
        json={"notas": "Notas corregidas por supervisor"},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["notas"] == "Notas corregidas por supervisor"


@pytest.mark.asyncio
async def test_delete_and_reverse_consumption_in_kardex(async_client: httpx.AsyncClient) -> None:
    """Verifica la anulación transaccional completa con restitución de existencias en Kardex."""
    headers = _make_headers(
        [
            "consumption.register.create",
            "consumption.register.delete",
            "consumption.register.read",
        ]
    )
    bodega_id = 1

    # 1. Cargar stock y registrar consumo de 15 unidades
    _inventory_service.register_movement(
        producto_id=501,
        bodega_id=bodega_id,
        movement_type="ENTRADA",
        quantity=Decimal("30.0000"),
        unit_cost=Decimal("1500.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )
    reg_resp = await async_client.post(
        "/api/v1/operations/consumption",
        headers=headers,
        json={
            "bodega_id": bodega_id,
            "items": [{"tipo_item": "PRODUCTO", "item_id": 501, "cantidad": "15.0000"}],
        },
    )
    record_id = reg_resp.json()["id"]
    assert _inventory_service.balance(501, bodega_id) == Decimal("15.0000")

    # 2. Anular / revertir consumo
    del_resp = await async_client.delete(
        f"/api/v1/operations/consumption/{record_id}?reason=Error+de+digitacion",
        headers=headers,
    )
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["is_undone"] is True

    # 3. Verificar que el saldo en Kardex retornó a 30.0000
    assert _inventory_service.balance(501, bodega_id) == Decimal("30.0000")

    # 4. Intentar anular de nuevo debe fallar
    repeat_del = await async_client.delete(
        f"/api/v1/operations/consumption/{record_id}",
        headers=headers,
    )
    assert repeat_del.status_code == 400


@pytest.mark.asyncio
async def test_merma_expired_stock_endpoint(async_client: httpx.AsyncClient) -> None:
    """Verifica merma directa de lotes vencidos desde el modal de contingencia."""
    headers = _make_headers(["consumption.register.create"])
    bodega_id = 1

    _inventory_service.register_movement(
        producto_id=601,
        bodega_id=bodega_id,
        movement_type="ENTRADA",
        quantity=Decimal("20.0000"),
        unit_cost=Decimal("2000.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )

    payload = {
        "producto_id": 601,
        "bodega_id": bodega_id,
        "quantity": "4.0000",
        "lote_codigo": "LOT-VENCIDO-2026",
        "fecha_vencimiento": "2026-10-01",
        "motivo": "CADUCIDAD_VISTA_CONSUMO",
        "unit_cost": "2000.00",
        "descripcion": "Merma autorizada por jefe de cocina",
    }

    resp = await async_client.post("/api/v1/operations/consumption/merma-expired", headers=headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["movement_type"] == "MERMA"
    assert Decimal(data["quantity"]) == Decimal("4.0000")
    assert Decimal(data["resulting_balance"]) == Decimal("16.0000")
    assert _inventory_service.balance(601, bodega_id) == Decimal("16.0000")


@pytest.mark.asyncio
async def test_consumption_templates_crud(async_client: httpx.AsyncClient) -> None:
    """Verifica creación y consulta de plantillas de consumo rápido."""
    headers = _make_headers(
        [
            "consumption.register.create",
            "consumption.register.read",
        ]
    )

    # 1. Crear plantilla
    payload = {
        "slug": "turno-tarde-barra",
        "nombre": "Turno Tarde Barra Coctelería",
        "descripcion": "Insumos recurrentes de tragos y gaseosas",
        "is_public": True,
        "columnas_count": 8,
        "sort_mode": "alpha_asc",
        "product_ids": [101, 102, 201],
    }
    create_resp = await async_client.post("/api/v1/operations/consumption/templates", headers=headers, json=payload)
    assert create_resp.status_code == 201
    created_tmpl = create_resp.json()
    assert created_tmpl["slug"] == "turno-tarde-barra"
    assert created_tmpl["product_ids"] == [101, 102, 201]

    # 2. Listar plantillas
    list_resp = await async_client.get("/api/v1/operations/consumption/templates", headers=headers)
    assert list_resp.status_code == 200
    tmpls = list_resp.json()
    assert len(tmpls) == 1
    assert tmpls[0]["slug"] == "turno-tarde-barra"


@pytest.mark.asyncio
async def test_buffet_lifecycle_and_pax_cost_reconciliation(async_client: httpx.AsyncClient) -> None:
    """Verifica apertura, actualización y conciliación contable de Buffet con cálculo de costo por Pax."""
    headers = _make_headers(
        [
            "consumption.buffet.manage",
            "consumption.buffet.approve",
        ]
    )
    bodega_id = 3

    # 1. Alimentar stock para insumos de buffet
    # Producto 701 (Huevos revueltos kg): 20 kg
    # Producto 702 (Tostadas UN): 100 UN
    _inventory_service.register_movement(
        producto_id=701,
        bodega_id=bodega_id,
        movement_type="ENTRADA",
        quantity=Decimal("20.0000"),
        unit_cost=Decimal("3000.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )
    _inventory_service.register_movement(
        producto_id=702,
        bodega_id=bodega_id,
        movement_type="ENTRADA",
        quantity=Decimal("100.0000"),
        unit_cost=Decimal("200.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )

    # 2. Iniciar sesión de buffet con 1 estación de desayuno
    start_payload = {
        "bodega_id": bodega_id,
        "tipo_servicio": "DESAYUNO",
        "estaciones": [
            {
                "nombre": "Estación Calientes",
                "orden": 1,
                "items": [
                    {
                        "item_id": 701,
                        "tipo_item": "PRODUCTO",
                        "cantidad_montada": "10.0000",
                        "costo_unitario_ppp": "3000.00",
                    },
                    {
                        "item_id": 702,
                        "tipo_item": "PRODUCTO",
                        "cantidad_montada": "50.0000",
                        "costo_unitario_ppp": "200.00",
                    },
                ],
            }
        ],
    }
    start_resp = await async_client.post("/api/v1/operations/buffet/sessions/start", headers=headers, json=start_payload)
    assert start_resp.status_code == 201
    session_data = start_resp.json()
    session_id = session_data["id"]
    station_id = session_data["stations"][0]["id"]
    # Costo total inicial de montaje: (10 * 3000) + (50 * 200) = 30000 + 10000 = 40000.00
    assert Decimal(session_data["costo_total_montaje"]) == Decimal("40000.00")

    # 3. Actualizar conteo de fin de servicio: sobrantes y mermas
    # Huevos 701: 10 montados, 2 sobrante, 1 merma => neto consumido = 7
    # Tostadas 702: 50 montadas, 10 sobrante, 0 merma => neto consumido = 40
    update_payload = {
        "stations": [
            {
                "station_id": station_id,
                "items": [
                    {
                        "item_id": 701,
                        "cantidad_montada": "10.0000",
                        "cantidad_sobrante": "2.0000",
                        "cantidad_merma": "1.0000",
                        "costo_unitario_ppp": "3000.00",
                    },
                    {
                        "item_id": 702,
                        "cantidad_montada": "50.0000",
                        "cantidad_sobrante": "10.0000",
                        "cantidad_merma": "0.0000",
                        "costo_unitario_ppp": "200.00",
                    },
                ],
            }
        ]
    }
    upd_resp = await async_client.put(
        f"/api/v1/operations/buffet/sessions/{session_id}/items",
        headers=headers,
        json=update_payload,
    )
    assert upd_resp.status_code == 200

    # 4. Liquidar y conciliar sesión de buffet:
    # 80 comensales (pax), valor sobrante reutilizable = 5000.00
    # Montaje total = 40000.00
    # Costo neto por Pax = (40000.00 - 5000.00) / 80 = 35000.00 / 80 = 437.50
    finalize_payload = {
        "pax": 80,
        "leftover_reusable_value": "5000.00",
    }
    fin_resp = await async_client.post(
        f"/api/v1/operations/buffet/sessions/{session_id}/finalize",
        headers=headers,
        json=finalize_payload,
    )
    assert fin_resp.status_code == 200
    fin_data = fin_resp.json()
    assert fin_data["estado"] == "CONCILIADA"
    assert fin_data["pax_comensales"] == 80
    assert Decimal(fin_data["costo_neto_pax"]) == Decimal("437.50")

    # 5. Verificar que el Kardex descontó consumo neto (7 kg de huevos) y mermas (1 kg de huevos)
    # Huevos 701: 20 iniciales - 7 consumidos - 1 merma = 12 restantes
    # Tostadas 702: 100 iniciales - 40 consumidas = 60 restantes
    assert _inventory_service.balance(701, bodega_id) == Decimal("12.0000")
    assert _inventory_service.balance(702, bodega_id) == Decimal("60.0000")


@pytest.mark.asyncio
async def test_voice_kitchen_orders_lifecycle(async_client: httpx.AsyncClient) -> None:
    """Verifica registro, confirmación y ejecución transaccional de pedidos por voz."""
    headers = _make_headers(
        [
            "consumption.handsfree.manage",
            "consumption.handsfree.use",
            "consumption.register.create",
        ]
    )
    bodega_id = 1

    # 1. Alimentar stock
    _inventory_service.register_movement(
        producto_id=801,
        bodega_id=bodega_id,
        movement_type="ENTRADA",
        quantity=Decimal("50.0000"),
        unit_cost=Decimal("1500.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )

    # 2. Crear estación de voz
    st_resp = await async_client.post(
        "/api/v1/operations/voice/stations",
        headers=headers,
        json={
            "nombre_estacion": "Estación Carnes Grill",
            "voice_command": "GRILL_01",
        },
    )
    assert st_resp.status_code == 201
    station_id = st_resp.json()["id"]

    # 3. Registrar orden verbal en estado PENDIENTE
    voice_payload = {
        "station_id": station_id,
        "texto_transcrito": "Oppy registrar salida de dos hamburguesas grill",
        "accion_detectada": "CONSUMO",
        "confianza_ia": "0.9850",
        "items_interpretados": [
            {
                "tipo_item": "PRODUCTO",
                "item_id": 801,
                "cantidad": "2.0000",
                "costo_unitario_ppp": "1500.00",
            }
        ],
    }
    reg_resp = await async_client.post("/api/v1/operations/voice/orders", headers=headers, json=voice_payload)
    assert reg_resp.status_code == 201
    order_data = reg_resp.json()
    order_id = order_data["id"]
    assert order_data["estado"] == "PENDIENTE"

    # 4. Confirmar orden verbal (ejecuta consumo en Kardex)
    conf_resp = await async_client.post(
        f"/api/v1/operations/voice/orders/{order_id}/confirm",
        headers=headers,
        json={"bodega_id": bodega_id},
    )
    assert conf_resp.status_code == 200
    assert conf_resp.json()["estado"] == "EJECUTADO"
    assert conf_resp.json()["consumption_record_id"] is not None

    # Verificar que el stock descontó 2 unidades (50 - 2 = 48)
    assert _inventory_service.balance(801, bodega_id) == Decimal("48.0000")

    # 5. Registrar y rechazar orden verbal errónea
    err_order_resp = await async_client.post(
        "/api/v1/operations/voice/orders",
        headers=headers,
        json={
            "station_id": station_id,
            "texto_transcrito": "Ruido ininteligible en cocina",
            "items_interpretados": [],
        },
    )
    err_order_id = err_order_resp.json()["id"]

    rej_resp = await async_client.post(
        f"/api/v1/operations/voice/orders/{err_order_id}/reject",
        headers=headers,
    )
    assert rej_resp.status_code == 200
    assert rej_resp.json()["estado"] == "RECHAZADO"


@pytest.mark.asyncio
async def test_rbac_denial_on_operations_consumption_endpoints(async_client: httpx.AsyncClient) -> None:
    """Verifica que usuarios sin permisos RBAC de 3 niveles sean rechazados con HTTP 403."""
    # Token sin permisos de consumo
    unauthorized_headers = _make_headers(["analytics.dashboard.read"])

    # 1. Intento de registrar consumo sin `consumption.register.create`
    resp1 = await async_client.post(
        "/api/v1/operations/consumption",
        headers=unauthorized_headers,
        json={
            "bodega_id": 1,
            "items": [{"tipo_item": "PRODUCTO", "item_id": 101, "cantidad": "1.0000"}],
        },
    )
    assert resp1.status_code == 403

    # 2. Intento de abrir sesión de buffet sin `consumption.buffet.manage`
    resp2 = await async_client.post(
        "/api/v1/operations/buffet/sessions/start",
        headers=unauthorized_headers,
        json={"bodega_id": 1, "tipo_servicio": "DESAYUNO"},
    )
    assert resp2.status_code == 403

    # 3. Intento de enviar orden verbal sin `consumption.handsfree.use`
    resp3 = await async_client.post(
        "/api/v1/operations/voice/orders",
        headers=unauthorized_headers,
        json={"station_id": 1, "texto_transcrito": "Comando prueba"},
    )
    assert resp3.status_code == 403


@pytest.mark.asyncio
async def test_observability_opentelemetry_spans_on_consumption_operations(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que las operaciones de consumo, buffet y voz emitan spans OpenTelemetry con atributos."""
    headers = _make_headers([
        "consumption.register.create",
        "consumption.buffet.manage",
        "consumption.buffet.approve",
        "consumption.handsfree.manage",
        "consumption.handsfree.use",
    ])

    # 1. Sembrar stock y registrar consumo
    _inventory_service.register_movement(
        producto_id=501,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("50.0000"),
        unit_cost=Decimal("1200.00"),
        actor_user_id=999,
        tenant_id=TENANT_ID,
    )

    c_resp = await async_client.post(
        "/api/v1/operations/consumption",
        headers=headers,
        json={
            "bodega_id": 1,
            "items": [{"tipo_item": "PRODUCTO", "item_id": 501, "cantidad": "5.0000"}],
            "tipo_origen": "MANUAL_TERMINAL",
        },
    )
    assert c_resp.status_code == 201

    # 2. Registrar sesión buffet, agregar ítems y liquidar
    b_resp = await async_client.post(
        "/api/v1/operations/buffet/sessions/start",
        headers=headers,
        json={
            "bodega_id": 1,
            "tipo_servicio": "ALMUERZO",
            "estaciones": [
                {
                    "nombre": "Calientes",
                    "items": [
                        {
                            "tipo_item": "PRODUCTO",
                            "item_id": 501,
                            "cantidad_montada": "10.0000",
                            "cantidad_sobrante": "2.0000",
                            "costo_unitario_ppp": "1200.00",
                        }
                    ],
                }
            ],
        },
    )
    assert b_resp.status_code == 201
    buffet_id = b_resp.json()["id"]

    fin_resp = await async_client.post(
        f"/api/v1/operations/buffet/sessions/{buffet_id}/finalize",
        headers=headers,
        json={"pax": 20, "leftover_reusable_value": "2400.00"},
    )
    assert fin_resp.status_code == 200

    # 3. Crear estación de voz, registrar orden verbal y confirmarla
    st_resp = await async_client.post(
        "/api/v1/operations/voice/stations",
        headers=headers,
        json={"nombre_estacion": "Parrilla Central", "voice_command": "parrilla"},
    )
    station_id = st_resp.json()["id"]

    vo_resp = await async_client.post(
        "/api/v1/operations/voice/orders",
        headers=headers,
        json={
            "station_id": station_id,
            "texto_transcrito": "Descontar 2 kilos de carne",
            "confianza_ia": "0.9800",
            "items_interpretados": [
                {"tipo_item": "PRODUCTO", "item_id": 501, "cantidad": "2.0000"}
            ],
        },
    )
    assert vo_resp.status_code == 201
    order_id = vo_resp.json()["id"]

    conf_resp = await async_client.post(
        f"/api/v1/operations/voice/orders/{order_id}/confirm",
        headers=headers,
        json={"bodega_id": 1},
    )
    assert conf_resp.status_code == 200

    # 4. Validar existencia y atributos de spans en InMemorySpanExporter
    spans = get_in_memory_exporter().get_finished_spans()
    span_names = [s.name for s in spans]

    assert "consumption.batch.process" in span_names
    assert "buffet.session.finalize" in span_names
    assert "voice.order.register" in span_names
    assert "voice.order.confirm" in span_names

    # Validar atributos de spans
    consumption_span = next(s for s in spans if s.name == "consumption.batch.process")
    assert consumption_span.attributes.get("tenant_id") == TENANT_ID
    assert consumption_span.attributes.get("bodega_id") == 1

    buffet_span = next(s for s in spans if s.name == "buffet.session.finalize")
    assert buffet_span.attributes.get("pax") == 20
    assert buffet_span.attributes.get("session_id") == buffet_id

    voice_span = next(s for s in spans if s.name == "voice.order.register")
    assert voice_span.attributes.get("station_id") == station_id
    assert voice_span.attributes.get("confidence_score") == 0.98

