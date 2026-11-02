"""
oppytec-backend/tests/unit/modules/test_events_services.py
Pruebas Unitarias y de Integración Transaccional para el Módulo de Eventos, Salones y Kardex (Fase 2).
Valida:
1. `SalonService`: CRUD, recálculo de IVA (19%), filtros por áreas operativas y soft-delete.
2. `EventService`:
   - Agendamiento y validación atómica anti-overbooking por franjas horarias (`EventTimeSlot.overlaps`).
   - Edición segura e inmunidad de eventos ya ejecutados o cancelados.
   - Cancelación y reactivación condicionada a disponibilidad de salón.
   - Ejecución transaccional en Kardex (`CONSUMO_EVENTO`), desglose BOM de recetas y combos,
     y persistencia en `evento_consumos_kardex`.
   - Banner analítico de faltantes predictivo (`get_faltantes_analytics`).
3. Enrutador FastAPI `/api/v1/events` y Guards RBAC de 3 niveles con RFC 7807 ProblemDetails.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from src.core.security import create_access_token
from src.modules.events.application.services import EventService, SalonService
from src.modules.events.domain.exceptions import (
    EventAlreadyCancelledError,
    EventAlreadyExecutedError,
    EventOverbookingError,
    EventStatusTransitionError,
    InvalidEventTimeSlotError,
    SalonNotFoundError,
)
from src.modules.events.presentation.router import (
    get_event_service,
    get_salon_service,
)
from src.modules.events.presentation.schemas import (
    EventoComboIn,
    EventoCreate,
    EventoItemIn,
    EventoRecetaIn,
    EventoTrabajadorIn,
    EventoUpdate,
    SalonCreate,
    SalonUpdate,
)
from src.modules.inventory.application.inventory_service import InventoryService

pytestmark = pytest.mark.unit

TEST_TENANT = "tenant_events_test"
TEST_HOLDING = "holding_events_test"


def _make_headers(permissions: list[str], user_id: int = 101) -> dict[str, str]:
    """Genera cabeceras con JWT autenticado y permisos RBAC de 3 niveles."""
    token = create_access_token(
        user_id=user_id,
        tenant_id=TEST_TENANT,
        holding_id=TEST_HOLDING,
        role_grants=permissions,
        accessible_tenants=[TEST_TENANT],
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TEST_TENANT,
    }


@pytest.fixture(autouse=True)
def _reset_events_state() -> None:
    """Aísla el estado en memoria antes de cada prueba unitaria."""
    salon_service = get_salon_service()
    event_service = get_event_service()
    salon_service.reset()
    event_service.reset()


# ============================================================================
# 1. PRUEBAS DE SALON SERVICE
# ============================================================================


def test_salon_crud_and_automatic_vat_calculation() -> None:
    """Verifica creación con cálculo automático de IVA al 19% y CRUD completo de salones."""
    service = SalonService()

    # 1. Alta con cálculo automático de precio bruto
    created = service.create_salon(
        tenant_id=TEST_TENANT,
        data=SalonCreate(
            nombre="Salón Los Alerces",
            capacidad_personas=120,
            precio_neto=Decimal("100000.00"),
            iva_porcentaje=Decimal("19.00"),
            notas="Salón principal con iluminación perimetral",
            areas_operativas_ids=[1, 2],
        ),
    )

    assert created.id is not None
    assert created.nombre == "Salón Los Alerces"
    assert created.capacidad_personas == 120
    assert created.precio_neto == Decimal("100000.00")
    assert created.iva_porcentaje == Decimal("19.00")
    # 100000 * 1.19 = 119000.00
    assert created.precio_bruto == Decimal("119000.00")
    assert created.areas_operativas_ids == [1, 2]

    # 2. Obtener por ID
    fetched = service.get_salon_by_id(TEST_TENANT, created.id)
    assert fetched.id == created.id

    # 3. Filtrar por área operativa
    salones_area1 = service.list_salones(TEST_TENANT, area_operativa_id=1)
    assert len(salones_area1) == 1
    assert salones_area1[0].id == created.id

    salones_area99 = service.list_salones(TEST_TENANT, area_operativa_id=99)
    assert len(salones_area99) == 0

    # 4. Actualización con recálculo de IVA
    updated = service.update_salon(
        tenant_id=TEST_TENANT,
        salon_id=created.id,
        data=SalonUpdate(
            precio_neto=Decimal("200000.00"),
        ),
    )
    # 200000 * 1.19 = 238000.00
    assert updated.precio_neto == Decimal("200000.00")
    assert updated.precio_bruto == Decimal("238000.00")

    # 5. Soft-delete
    service.delete_salon(TEST_TENANT, created.id)
    assert len(service.list_salones(TEST_TENANT)) == 0

    with pytest.raises(SalonNotFoundError):
        service.get_salon_by_id(TEST_TENANT, created.id)


def test_salon_not_found_raises_exception() -> None:
    """Verifica que solicitar un salón inexistente dispare SalonNotFoundError."""
    service = SalonService()
    non_existent = uuid4()
    with pytest.raises(SalonNotFoundError):
        service.get_salon_by_id(TEST_TENANT, non_existent)


# ============================================================================
# 2. PRUEBAS DE EVENT SERVICE: ANTI-OVERBOOKING Y CICLO DE VIDA
# ============================================================================


def test_anti_overbooking_detection_in_same_salon_and_date() -> None:
    """Valida la detección estricta de sobreventa u overbooking temporal en salones."""
    salon_srv = SalonService()
    event_srv = EventService(salon_service=salon_srv)

    salon_a = salon_srv.create_salon(
        TEST_TENANT,
        SalonCreate(nombre="Salón Diamante", capacidad_personas=80),
    )
    salon_b = salon_srv.create_salon(
        TEST_TENANT,
        SalonCreate(nombre="Salón Esmeralda", capacidad_personas=60),
    )

    target_date = date(2026, 12, 15)

    # 1. Evento 1 en Salón A de 14:00 a 18:00
    ev1 = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Boda García - Pérez",
            salon_id=salon_a.id,
            fecha=target_date,
            hora_inicio=time(14, 0),
            hora_fin=time(18, 0),
            cantidad_personas=70,
        ),
    )
    assert ev1.id is not None

    # 2. Intento de Evento 2 solapado (16:00 a 20:00) en el mismo salón A -> DEBE FALLAR 409
    with pytest.raises(EventOverbookingError) as exc_info:
        event_srv.create_event(
            TEST_TENANT,
            EventoCreate(
                nombre="Cumpleaños Infantil",
                salon_id=salon_a.id,
                fecha=target_date,
                hora_inicio=time(16, 0),
                hora_fin=time(20, 0),
            ),
        )
    assert "El salón ya está reservado" in str(exc_info.value)

    # 3. Intento de Evento día completo sin horas en el mismo salón A -> DEBE FALLAR
    with pytest.raises(EventOverbookingError):
        event_srv.create_event(
            TEST_TENANT,
            EventoCreate(
                nombre="Convención Empresarial Todo el Día",
                salon_id=salon_a.id,
                fecha=target_date,
                hora_inicio=None,
                hora_fin=None,
            ),
        )

    # 4. Evento contiguo (18:00 a 22:00) en Salón A -> DEBE PERMITIRSE (sin solapamiento)
    ev_contiguo = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Cena Nocturna",
            salon_id=salon_a.id,
            fecha=target_date,
            hora_inicio=time(18, 0),
            hora_fin=time(22, 0),
        ),
    )
    assert ev_contiguo.id is not None

    # 5. Mismo horario (14:00 a 18:00) pero en Salón B -> DEBE PERMITIRSE
    ev_salon_b = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Almuerzo Ejecutivo",
            salon_id=salon_b.id,
            fecha=target_date,
            hora_inicio=time(14, 0),
            hora_fin=time(18, 0),
        ),
    )
    assert ev_salon_b.id is not None

    # 6. Mismo horario y salón A pero al día siguiente -> DEBE PERMITIRSE
    ev_next_day = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Brunch Dominical",
            salon_id=salon_a.id,
            fecha=target_date + timedelta(days=1),
            hora_inicio=time(14, 0),
            hora_fin=time(18, 0),
        ),
    )
    assert ev_next_day.id is not None


def test_invalid_timeslot_raises_domain_error() -> None:
    """Verifica que hora_fin <= hora_inicio dispare InvalidEventTimeSlotError."""
    event_srv = EventService()
    with pytest.raises(InvalidEventTimeSlotError):
        event_srv.create_event(
            TEST_TENANT,
            EventoCreate(
                nombre="Horario Invertido",
                fecha=date(2026, 12, 10),
                hora_inicio=time(20, 0),
                hora_fin=time(18, 0),
            ),
        )


def test_event_update_and_cancellation_flow() -> None:
    """Verifica actualización, cancelación y reactivación condicionada a disponibilidad."""
    salon_srv = SalonService()
    event_srv = EventService(salon_service=salon_srv)

    salon = salon_srv.create_salon(TEST_TENANT, SalonCreate(nombre="Salón Magnolia"))
    target_date = date(2026, 11, 20)

    # 1. Crear evento
    evento = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Fiesta de Gala",
            salon_id=salon.id,
            fecha=target_date,
            hora_inicio=time(19, 0),
            hora_fin=time(23, 0),
        ),
    )

    # 2. Actualizar título y cantidad de personas
    updated = event_srv.update_event(
        TEST_TENANT,
        evento.id,
        EventoUpdate(
            nombre="Fiesta de Gala Anual",
            cantidad_personas=100,
        ),
    )
    assert updated.nombre == "Fiesta de Gala Anual"
    assert updated.cantidad_personas == 100

    # 3. Cancelar evento
    cancelled = event_srv.cancel_event(
        TEST_TENANT,
        evento.id,
        motivo="Suspensión por fuerza mayor",
    )
    assert cancelled.cancelado is True
    assert cancelled.estado == "CANCELADO"
    assert cancelled.motivo_cancelacion == "Suspensión por fuerza mayor"

    # 4. Prohibido editar un evento cancelado
    with pytest.raises(EventAlreadyCancelledError):
        event_srv.update_event(
            TEST_TENANT,
            evento.id,
            EventoUpdate(nombre="Intento de Edición"),
        )

    # 5. Como el evento está cancelado, el espacio horario quedó liberado.
    # Creamos otro evento en la misma franja
    evento_reemplazo = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Evento Remplazo",
            salon_id=salon.id,
            fecha=target_date,
            hora_inicio=time(19, 0),
            hora_fin=time(23, 0),
        ),
    )
    assert evento_reemplazo.id is not None

    # 6. Intentar reactivar el primer evento debe fallar por colisión con el de reemplazo
    with pytest.raises(EventOverbookingError):
        event_srv.reactivate_event(TEST_TENANT, evento.id)

    # 7. Cancelamos el reemplazo y ahora sí reactivamos el original
    event_srv.cancel_event(TEST_TENANT, evento_reemplazo.id)
    reactivated = event_srv.reactivate_event(TEST_TENANT, evento.id)
    assert reactivated.cancelado is False
    assert reactivated.estado == "AGENDADO"


# ============================================================================
# 3. PRUEBAS DE EJECUCIÓN TRANSACCIONAL EN KARDEX Y ANALÍTICA DE FALTANTES
# ============================================================================


def test_event_execution_deducts_kardex_with_bom_explosion() -> None:
    """Verifica rebaje atómico en Kardex de insumos directos, recetas y combos."""
    inventory = InventoryService()
    event_srv = EventService(inventory=inventory)

    # 1. Cargar stock inicial en Bodega 1
    # Prod 10 (Carne Wagyu): 50 kg a $20,000 c/u
    # Prod 20 (Vino Cabernet): 30 botellas a $8,000 c/u
    # Prod 30 (Postre Helado): 40 unidades a $2,500 c/u
    inventory.register_movement(
        producto_id=10,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("50.0000"),
        unit_cost=Decimal("20000.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )
    inventory.register_movement(
        producto_id=20,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("30.0000"),
        unit_cost=Decimal("8000.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )
    inventory.register_movement(
        producto_id=30,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("40.0000"),
        unit_cost=Decimal("2500.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )

    # 2. Configurar ficha técnica de Receta #100 ("Plato Principal Premium"):
    # Cada porción requiere 0.25 kg de Prod 10 (Carne Wagyu)
    event_srv.register_recipe_ingredients(
        receta_id=100,
        ingredients=[(10, Decimal("0.2500"))],
    )
    # Configurar Combo #200 ("Pack Banquete"):
    # Contiene 2 botellas de Prod 20 y 3 postres de Prod 30
    event_srv.register_combo_components(
        combo_id=200,
        components=[(20, Decimal("2.0000")), (30, Decimal("3.0000"))],
    )

    # 3. Crear evento con estructura mixta:
    # - Insumo directo: 5 kg de Prod 10
    # - Receta 100: 40 porciones (40 * 0.25 kg = 10 kg de Prod 10)
    # - Combo 200: 5 combos (5 * 2 = 10 botellas Prod 20; 5 * 3 = 15 postres Prod 30)
    evento = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Banquete de Fin de Año",
            fecha=date(2026, 12, 31),
            hora_inicio=time(20, 0),
            hora_fin=time(23, 59),
            items=[
                EventoItemIn(
                    producto_id=10,
                    bodega_id=1,
                    cantidad=Decimal("5.0000"),
                    costo_unitario_estimado=Decimal("20000.00"),
                ),
            ],
            recetas=[
                EventoRecetaIn(
                    receta_id=100,
                    bodega_id=1,
                    porciones=40,
                ),
            ],
            combos=[
                EventoComboIn(
                    combo_id=200,
                    bodega_id=1,
                    cantidad=5,
                ),
            ],
            trabajadores=[
                EventoTrabajadorIn(
                    usuario_id=10,
                    rol_evento="Maître de Sala",
                    horas_asignadas=Decimal("6.00"),
                ),
            ],
        ),
    )

    # 4. Ejecutar el evento en Kardex
    result = event_srv.execute_event(TEST_TENANT, evento.id, current_user_id=101)

    assert result.ejecutado is True
    assert result.total_movimientos_kardex == 4  # 1 directo + 1 ingrediente receta + 2 componentes combo
    assert len(result.consumos) == 4

    # 5. Verificar saldos resultantes en inventario tras la ejecución:
    # Prod 10: Inicial 50 - 5 (directo) - 10 (receta) = 35 kg restantes
    assert inventory.balance(10, 1) == Decimal("35.0000")
    # Prod 20: Inicial 30 - 10 (combo) = 20 botellas restantes
    assert inventory.balance(20, 1) == Decimal("20.0000")
    # Prod 30: Inicial 40 - 15 (combo) = 25 postres restantes
    assert inventory.balance(30, 1) == Decimal("25.0000")

    # 6. Verificar inmutabilidad: el evento ejecutado no admite edición ni cancelación
    with pytest.raises(EventAlreadyExecutedError):
        event_srv.update_event(TEST_TENANT, evento.id, EventoUpdate(nombre="Intento de Cambio"))

    with pytest.raises(EventAlreadyExecutedError):
        event_srv.cancel_event(TEST_TENANT, evento.id)

    with pytest.raises(EventAlreadyExecutedError):
        event_srv.delete_event(TEST_TENANT, evento.id)

    with pytest.raises(EventAlreadyExecutedError):
        event_srv.execute_event(TEST_TENANT, evento.id)


def test_faltantes_analytics_shortage_detection() -> None:
    """Verifica detección predictiva de quiebres de inventario para eventos futuros."""
    inventory = InventoryService()
    event_srv = EventService(inventory=inventory)

    future_date = date.today() + timedelta(days=10)

    # Existencia actual en Bodega 1:
    # Prod 50: 10 unidades
    inventory.register_movement(
        producto_id=50,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("10.0000"),
        unit_cost=Decimal("1000.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )

    # Agendamos Evento A que requiere 8 unidades de Prod 50
    event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Evento Mañana",
            fecha=future_date,
            items=[
                EventoItemIn(producto_id=50, bodega_id=1, cantidad=Decimal("8.0000")),
            ],
        ),
    )

    # Con solo Evento A (requerido: 8 <= stock: 10) -> Faltantes: 0
    analisis_1 = event_srv.get_faltantes_analytics(TEST_TENANT)
    assert analisis_1.total_faltantes == 0

    # Agendamos Evento B que requiere 7 unidades de Prod 50 (Demanda total: 8 + 7 = 15 > 10)
    event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Evento Tarde",
            fecha=future_date,
            items=[
                EventoItemIn(producto_id=50, bodega_id=1, cantidad=Decimal("7.0000")),
            ],
        ),
    )

    # Con Evento A + B -> Demanda 15 > Stock 10 -> Déficit: 5 unidades
    analisis_2 = event_srv.get_faltantes_analytics(TEST_TENANT)
    assert analisis_2.total_faltantes == 1
    assert analisis_2.eventos_afectados_count == 2

    item_deficit = analisis_2.items[0]
    assert item_deficit.producto_id == 50
    assert item_deficit.cantidad_requerida == Decimal("15.0000")
    assert item_deficit.stock_actual == Decimal("10.0000")
    assert item_deficit.deficit == Decimal("5.0000")


# ============================================================================
# 4. PRUEBAS DE ENRUTADOR FASTAPI Y GUARDS RBAC
# ============================================================================


@pytest.mark.asyncio
async def test_fastapi_endpoints_rbac_and_crud(async_client: httpx.AsyncClient) -> None:
    """Valida los endpoints REST de salones y eventos con RBAC de 3 niveles y respuestas normalizadas."""
    # 1. Permiso denegado sin RBAC
    unauth_headers = _make_headers([])
    resp = await async_client.get("/api/v1/events/salones", headers=unauth_headers)
    assert resp.status_code == 403

    # 2. Listar salones con permiso
    read_headers = _make_headers(["events.salones.read", "events.events.read"])
    resp = await async_client.get("/api/v1/events/salones", headers=read_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # 3. Crear salón con 'events.salones.manage'
    manage_headers = _make_headers([
        "events.salones.read",
        "events.salones.manage",
        "events.events.read",
        "events.events.create",
        "events.events.edit",
        "events.events.delete",
        "events.events.execute",
        "events.events.cancel",
    ])
    salon_payload = {
        "nombre": "Salón Real",
        "capacidad_personas": 150,
        "precio_neto": "500000.00",
        "iva_porcentaje": "19.00",
        "color": "#ec4899",
        "areas_operativas_ids": [1],
    }
    resp = await async_client.post("/api/v1/events/salones", json=salon_payload, headers=manage_headers)
    assert resp.status_code == 201
    salon_data = resp.json()
    salon_id = salon_data["id"]
    assert salon_data["precio_bruto"] == "595000.00"

    # 4. Crear evento en el salón creado
    event_payload = {
        "nombre": "Conferencia Anual",
        "salon_id": salon_id,
        "fecha": str(date(2026, 12, 20)),
        "hora_inicio": "10:00:00",
        "hora_fin": "14:00:00",
        "cantidad_personas": 120,
        "valor_publico": "750000.00",
        "items": [],
        "recetas": [],
        "combos": [],
        "trabajadores": [],
    }
    resp = await async_client.post("/api/v1/events", json=event_payload, headers=manage_headers)
    assert resp.status_code == 201
    event_data = resp.json()
    event_id = event_data["id"]
    assert event_data["nombre"] == "Conferencia Anual"

    # 5. Intento de solapamiento por API -> 409 Conflict ProblemDetails
    resp_conflict = await async_client.post("/api/v1/events", json=event_payload, headers=manage_headers)
    assert resp_conflict.status_code == 409
    problem = resp_conflict.json()
    assert problem["status"] == 409
    assert "El salón ya está reservado" in problem["detail"]

    # 6. Listar eventos
    resp_list = await async_client.get("/api/v1/events", headers=manage_headers)
    assert resp_list.status_code == 200
    events_list = resp_list.json()
    assert len(events_list) == 1
    assert events_list[0]["id"] == event_id

    # 7. Cancelar evento
    cancel_payload = {"motivo": "Cancelado por el cliente"}
    resp_cancel = await async_client.post(
        f"/api/v1/events/{event_id}/cancel",
        json=cancel_payload,
        headers=manage_headers,
    )
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["cancelado"] is True

    # 8. Reactivar evento
    resp_react = await async_client.post(
        f"/api/v1/events/{event_id}/reactivate",
        headers=manage_headers,
    )
    assert resp_react.status_code == 200
    assert resp_react.json()["cancelado"] is False

    # 9. Ejecutar evento
    resp_exec = await async_client.post(
        f"/api/v1/events/{event_id}/execute",
        headers=manage_headers,
    )
    assert resp_exec.status_code == 200
    assert resp_exec.json()["ejecutado"] is True

    # 10. Consultar banner analítico de faltantes
    resp_faltantes = await async_client.get("/api/v1/events/faltantes", headers=manage_headers)
    assert resp_faltantes.status_code == 200
    assert "total_faltantes" in resp_faltantes.json()


# ============================================================================
# 4. FASE 6: PRUEBAS DE REVERSIÓN EN KARDEX, BOM RECURSIVO Y MINUTAS
# ============================================================================


def test_event_reversal_compensatory_kardex_movements() -> None:
    """
    Verifica la reversibilidad y compensación controlada en Kardex (Fase 6.3):
    1. Carga stock inicial.
    2. Ejecuta un evento descontando en Kardex (salida neta).
    3. Revierte el evento con motivo auditado.
    4. Comprueba que las unidades se reingresen exactamente al stock con el mismo costo PPP.
    5. Invariante: No se puede volver a revertir ni reactivar un evento revertido.
    """
    inventory = InventoryService()
    event_srv = EventService(inventory=inventory)

    # 1. Stock inicial: Prod 1001 = 100 unidades a $1,500 c/u en Bodega 1
    inventory.register_movement(
        producto_id=1001,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("100.0000"),
        unit_cost=Decimal("1500.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )
    assert inventory.balance(1001, 1) == Decimal("100.0000")

    # 2. Crear evento que consume 25 unidades
    evento = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Cena de Aniversario",
            fecha=date(2026, 12, 15),
            hora_inicio=time(20, 0),
            hora_fin=time(23, 0),
            items=[
                EventoItemIn(
                    producto_id=1001,
                    bodega_id=1,
                    cantidad=Decimal("25.0000"),
                    costo_unitario_estimado=Decimal("1500.00"),
                ),
            ],
        ),
    )

    # 3. Intentar revertir antes de ejecutar debe fallar con error de transición
    with pytest.raises(EventStatusTransitionError):
        event_srv.reverse_event(TEST_TENANT, evento.id, motivo="Intento prematuro")

    # 4. Ejecutar el evento -> Saldo queda en 75
    exec_result = event_srv.execute_event(TEST_TENANT, evento.id, current_user_id=10)
    assert exec_result.ejecutado is True
    assert inventory.balance(1001, 1) == Decimal("75.0000")

    # 5. Revertir el evento ejecutado
    rev_result = event_srv.reverse_event(
        TEST_TENANT,
        evento.id,
        motivo="Cancelación por alerta meteorológica roja",
        current_user_id=20,
    )

    assert rev_result.revertido is True
    assert rev_result.total_movimientos_compensatorios == 1
    assert rev_result.total_unidades_reingresadas == Decimal("25.0000")
    assert rev_result.costo_total_revertido == Decimal("37500.00")
    assert rev_result.motivo == "Cancelación por alerta meteorológica roja"

    # 6. Saldo restituido exactamente a 100.0000 en Kardex
    assert inventory.balance(1001, 1) == Decimal("100.0000")

    # 7. Estado del evento debe ser CANCELADO
    refreshed = event_srv.get_event_by_id(TEST_TENANT, evento.id)
    assert refreshed.cancelado is True
    assert refreshed.estado == "CANCELADO"
    assert refreshed.motivo_cancelacion == "Cancelación por alerta meteorológica roja"

    # 8. No se puede revertir un evento ya cancelado / revertido
    with pytest.raises(EventAlreadyCancelledError):
        event_srv.reverse_event(TEST_TENANT, evento.id, motivo="Segundo intento")


def test_recursive_bom_with_combo_containing_recipes() -> None:
    """
    Verifica el desglose recursivo BOM (Fase 6.1):
    Un combo que contiene tanto materias primas directas como recetas astronómicas
    se descompone hasta sus ingredientes base al ejecutar el evento y en faltantes.
    """
    inventory = InventoryService()
    event_srv = EventService(inventory=inventory)

    # Prod 1 (Carbón): 20 bolsas
    # Prod 2 (Carne Asada): 30 kg
    # Prod 3 (Condimentos): 10 kg
    inventory.register_movement(
        producto_id=1,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("20.0000"),
        unit_cost=Decimal("5000.00"),
        actor_user_id=1,
    )
    inventory.register_movement(
        producto_id=2,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("30.0000"),
        unit_cost=Decimal("8000.00"),
        actor_user_id=1,
    )
    inventory.register_movement(
        producto_id=3,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("10.0000"),
        unit_cost=Decimal("2000.00"),
        actor_user_id=1,
    )

    # Receta 50 ("Plato Parrillero"): requiere 0.50 kg de Prod 2 y 0.10 kg de Prod 3
    event_srv.register_recipe_ingredients(
        receta_id=50,
        ingredients=[
            (2, Decimal("0.5000")),
            (3, Decimal("0.1000")),
        ],
    )

    # Combo 300 ("Pack Parrillero Completo"):
    # - Insumo directo: 1 bolsa de Carbón (Prod 1)
    # - Sub-receta: 4 porciones de Receta 50
    event_srv.register_combo_components(
        combo_id=300,
        components=[(1, Decimal("1.0000"))],
    )
    event_srv.register_combo_recipes(
        combo_id=300,
        recipes=[(50, 4)],
    )

    # Crear evento con 5 Combos 300:
    # Prod 1 requerido: 5 * 1 = 5 bolsas
    # Prod 2 requerido: 5 combos * 4 porciones * 0.5 kg = 10 kg
    # Prod 3 requerido: 5 combos * 4 porciones * 0.1 kg = 2 kg
    evento = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Asado Corporativo",
            fecha=date(2026, 12, 18),
            hora_inicio=time(13, 0),
            hora_fin=time(18, 0),
            combos=[
                EventoComboIn(
                    combo_id=300,
                    bodega_id=1,
                    cantidad=5,
                ),
            ],
        ),
    )

    # Analítica de faltantes antes de ejecutar
    faltantes = event_srv.get_faltantes_analytics(TEST_TENANT)
    # Stock suficiente, no debe haber faltantes
    assert faltantes.total_faltantes == 0

    # Ejecutar evento
    result = event_srv.execute_event(TEST_TENANT, evento.id, current_user_id=1)
    assert result.ejecutado is True
    # 1 componente directo + 2 ingredientes de la receta en combo = 3 movimientos
    assert result.total_movimientos_kardex == 3

    # Saldos:
    # Prod 1: 20 - 5 = 15
    assert inventory.balance(1, 1) == Decimal("15.0000")
    # Prod 2: 30 - 10 = 20
    assert inventory.balance(2, 1) == Decimal("20.0000")
    # Prod 3: 10 - 2 = 8
    assert inventory.balance(3, 1) == Decimal("8.0000")


def test_event_minuta_csv_export_and_acta() -> None:
    """
    Verifica la exportación estructurada de la Minuta Técnica de Producción y Requisición (Fase 6.4).
    Garantiza presencia de UTF-8 BOM, ficha técnica, minuta gastronómica, requisición y firmas.
    """
    event_srv = EventService()

    # Configurar receta
    event_srv.register_recipe_ingredients(
        receta_id=88,
        ingredients=[(401, Decimal("0.3500")), (402, Decimal("0.1000"))],
    )
    event_srv.set_product_cost(401, Decimal("12000.00"))
    event_srv.set_product_cost(402, Decimal("3500.00"))

    # Crear evento con todos los campos
    evento = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Banquete de Bodas González-Pérez",
            titular="María González",
            tipo_evento="MATRIMONIO",
            fecha=date(2026, 12, 22),
            hora_inicio=time(18, 30),
            hora_fin=time(23, 45),
            cantidad_personas=80,
            valor_publico=Decimal("3500000.00"),
            notas="Montaje con mantelería blanca e iluminación cálida",
            recetas=[
                EventoRecetaIn(receta_id=88, bodega_id=1, porciones=80),
            ],
            trabajadores=[
                EventoTrabajadorIn(usuario_id=5, rol_evento="Chef Principal", horas_asignadas=Decimal("8.00")),
            ],
        ),
    )

    # 1. Minuta individual
    csv_text = event_srv.generate_minuta_csv(TEST_TENANT, evento.id)

    # Verificar BOM UTF-8 (\ufeff)
    assert csv_text.startswith("\ufeff")
    # Verificar secciones
    assert "OPPYTEC v2.0 - MINUTA TÉCNICA DE PRODUCCIÓN Y REQUISICIÓN DE EVENTOS" in csv_text
    assert "[1] FICHA TÉCNICA DEL EVENTO" in csv_text
    assert "Banquete de Bodas González-Pérez" in csv_text
    assert "María González" in csv_text
    assert "MATRIMONIO" in csv_text
    assert "80" in csv_text
    assert "[2] MINUTA GASTRONÓMICA" in csv_text
    assert "[4] REQUISICIÓN DE INSUMOS Y MATERIAS PRIMAS (BOM TOTAL)" in csv_text
    assert "[5] BRIGADA OPERATIVA Y PERSONAL ASIGNADO" in csv_text
    assert "Chef Principal" in csv_text
    assert "[6] ACTA DE CONFORMIDAD Y FIRMAS" in csv_text
    assert "Entrega Bodega (Firma y Fecha)" in csv_text
    assert "Recepción Chef / Encargado" in csv_text

    # 2. Minutas consolidadas
    consolidated_csv = event_srv.generate_minutas_consolidated_csv(TEST_TENANT, [evento.id])
    assert "Banquete de Bodas González-Pérez" in consolidated_csv


@pytest.mark.asyncio
async def test_fastapi_reversal_and_minuta_endpoints(async_client: httpx.AsyncClient) -> None:
    """
    Verifica endpoints REST de reversión y descarga de minutas con validación RBAC (Fase 6).
    - POST /api/v1/events/{event_id}/reverse (RequireTenantPermission("events.events.cancel"))
    - GET /api/v1/events/{event_id}/minuta (RequireTenantPermission("events.events.read"))
    - POST /api/v1/events/export/minuta-excel (RequireTenantPermission("events.events.read"))
    """
    event_srv = get_event_service()
    event_srv.reset()

    # Crear evento para pruebas
    evento = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Gala Fin de Temporada",
            fecha=date(2026, 12, 28),
            hora_inicio=time(20, 0),
            hora_fin=time(23, 30),
            cantidad_personas=60,
        ),
    )

    client = async_client

    # 1. Probar RBAC sin permiso de lectura para minuta -> 403
    no_read_headers = _make_headers(["events.events.create"])
    resp_minuta_denied = await client.get(
        f"/api/v1/events/{evento.id}/minuta",
        headers=no_read_headers,
    )
    assert resp_minuta_denied.status_code == 403

    # 2. Probar descarga de minuta con permiso 'events.events.read' -> 200 StreamingResponse
    read_headers = _make_headers(["events.events.read"])
    resp_minuta = await client.get(
        f"/api/v1/events/{evento.id}/minuta",
        headers=read_headers,
    )
    assert resp_minuta.status_code == 200
    assert resp_minuta.headers["content-type"].startswith("text/csv")
    assert f'filename="minuta_evento_{evento.id}.csv"' in resp_minuta.headers["content-disposition"]
    assert "Gala Fin de Temporada" in resp_minuta.text

    # 3. Probar exportación consolidada -> POST /api/v1/events/export/minuta-excel
    resp_export = await client.post(
        "/api/v1/events/export/minuta-excel",
        json={"event_ids": [str(evento.id)]},
        headers=read_headers,
    )
    assert resp_export.status_code == 200
    assert resp_export.headers["content-type"].startswith("text/csv")
    assert "minuta_produccion_eventos_" in resp_export.headers["content-disposition"]
    assert "Gala Fin de Temporada" in resp_export.text

    # 4. Ejecutar el evento primero para poder revertirlo
    exec_headers = _make_headers(["events.events.execute", "events.events.cancel"])
    resp_exec = await client.post(
        f"/api/v1/events/{evento.id}/execute",
        headers=exec_headers,
    )
    assert resp_exec.status_code == 200

    # 5. Probar reversión sin permiso 'events.events.cancel' -> 403
    resp_rev_denied = await client.post(
        f"/api/v1/events/{evento.id}/reverse",
        json={"motivo": "Intento no autorizado"},
        headers=read_headers,
    )
    assert resp_rev_denied.status_code == 403

    # 6. Probar reversión exitosa con permiso 'events.events.cancel' -> 200 OK
    resp_rev = await client.post(
        f"/api/v1/events/{evento.id}/reverse",
        json={"motivo": "Anulación por fuerza mayor sanitaria"},
        headers=exec_headers,
    )
    assert resp_rev.status_code == 200
    rev_data = resp_rev.json()
    assert rev_data["revertido"] is True
    assert rev_data["motivo"] == "Anulación por fuerza mayor sanitaria"
    assert rev_data["evento"]["estado"] == "CANCELADO"
    assert rev_data["evento"]["cancelado"] is True


# ============================================================================
# 4. PRUEBAS DE STOCK COMPROMETIDO Y ALERTAS OPERATIVAS (FASE 7)
# ============================================================================


def test_committed_stock_calculation_and_available_stock_formula() -> None:
    """
    Verifica la definición matemática de existencias y demanda futura reservada (Fase 7.1):
    1. Demanda Futura Reservada: Stock Comprometido = sum(BOM Insumos de eventos futuros).
    2. Saldo Libre para Operación Diaria:
       Stock Disponible Real = max(0, Stock Actual - Stock Comprometido)
    3. Manejo de insumos directos, recetas y combos.
    4. Filtrado opcional por bodega_id y exclusión de eventos cancelados/ejecutados.
    """
    inventory = InventoryService()
    event_srv = EventService(inventory=inventory)

    # 1. Cargar stock en Kardex:
    # Prod 501 en Bodega 1: 100.0000 unidades
    # Prod 502 en Bodega 1: 10.0000 unidades (deficitario frente a la demanda)
    # Prod 503 en Bodega 2: 50.0000 unidades
    inventory.register_movement(
        producto_id=501,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("100.0000"),
        unit_cost=Decimal("1000.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )
    inventory.register_movement(
        producto_id=502,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("10.0000"),
        unit_cost=Decimal("2500.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )
    inventory.register_movement(
        producto_id=503,
        bodega_id=2,
        movement_type="ENTRADA",
        quantity=Decimal("50.0000"),
        unit_cost=Decimal("800.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )

    # Registrar especificación de receta (Receta 77: 2 unidades de Prod 501 por porción)
    event_srv.register_recipe_ingredients(
        receta_id=77,
        ingredients=[(501, Decimal("2.0000"))],
    )

    tomorrow = date.today() + timedelta(days=1)
    future_date_2 = date.today() + timedelta(days=5)

    # Evento 1: consume 30 de Prod 501 directo, y 15 de Prod 502 directo en Bodega 1
    ev1 = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Banquete Matrimonial",
            fecha=tomorrow,
            hora_inicio=time(13, 0),
            hora_fin=time(18, 0),
            items=[
                EventoItemIn(producto_id=501, bodega_id=1, cantidad=Decimal("30.0000")),
                EventoItemIn(producto_id=502, bodega_id=1, cantidad=Decimal("15.0000")),
            ],
        ),
    )

    # Evento 2: consume Receta 77 x 10 porciones (10 * 2 = 20 de Prod 501) en Bodega 1,
    # y 10 unidades de Prod 503 directo en Bodega 2
    ev2 = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Cena de Gala Corporativa",
            fecha=future_date_2,
            hora_inicio=time(20, 0),
            hora_fin=time(23, 0),
            recetas=[
                EventoRecetaIn(receta_id=77, bodega_id=1, porciones=10),
            ],
            items=[
                EventoItemIn(producto_id=503, bodega_id=2, cantidad=Decimal("10.0000")),
            ],
        ),
    )

    # 2. Consultar resumen global de stock comprometido
    summary = event_srv.get_committed_stock_summary(TEST_TENANT)
    assert summary.total_items == 3
    items_by_key = {(it.producto_id, it.bodega_id): it for it in summary.items}

    # Producto 501 en Bodega 1:
    # Stock actual = 100
    # Comprometido = 30 (ev1) + 20 (ev2) = 50
    # Stock disponible real = max(0, 100 - 50) = 50
    item_501 = items_by_key[(501, 1)]
    assert item_501.stock_actual == Decimal("100.0000")
    assert item_501.stock_comprometido == Decimal("50.0000")
    assert item_501.stock_disponible_real == Decimal("50.0000")
    assert len(item_501.eventos) == 2
    ev_ids_501 = {e.evento_id for e in item_501.eventos}
    assert ev1.id in ev_ids_501
    assert ev2.id in ev_ids_501

    # Producto 502 en Bodega 1:
    # Stock actual = 10
    # Comprometido = 15
    # Stock disponible real = max(0, 10 - 15) = 0.0000 (no negativo)
    item_502 = items_by_key[(502, 1)]
    assert item_502.stock_actual == Decimal("10.0000")
    assert item_502.stock_comprometido == Decimal("15.0000")
    assert item_502.stock_disponible_real == Decimal("0.0000")
    assert len(item_502.eventos) == 1
    assert item_502.eventos[0].evento_id == ev1.id

    # Producto 503 en Bodega 2:
    # Stock actual = 50
    # Comprometido = 10
    # Stock disponible real = max(0, 50 - 10) = 40
    item_503 = items_by_key[(503, 2)]
    assert item_503.stock_actual == Decimal("50.0000")
    assert item_503.stock_comprometido == Decimal("10.0000")
    assert item_503.stock_disponible_real == Decimal("40.0000")

    # 3. Filtrar por bodega específica (Bodega 2)
    summary_b2 = event_srv.get_committed_stock_summary(TEST_TENANT, bodega_id=2)
    assert summary_b2.total_items == 1
    assert summary_b2.items[0].producto_id == 503
    assert summary_b2.items[0].bodega_id == 2

    # 4. Cancelar Evento 2 debe liberar su stock comprometido
    event_srv.cancel_event(TEST_TENANT, ev2.id, motivo="Reprogramación")
    summary_after_cancel = event_srv.get_committed_stock_summary(TEST_TENANT)
    items_after_cancel = {(it.producto_id, it.bodega_id): it for it in summary_after_cancel.items}

    # Prod 501 ahora solo tiene comprometidas 30 unidades de ev1
    # Stock disponible real sube a: max(0, 100 - 30) = 70
    assert items_after_cancel[(501, 1)].stock_comprometido == Decimal("30.0000")
    assert items_after_cancel[(501, 1)].stock_disponible_real == Decimal("70.0000")
    # Prod 503 ya no tiene eventos activos que comprometan stock
    assert (503, 2) not in items_after_cancel


def test_event_alerts_classification_and_severities() -> None:
    """
    Verifica la clasificación de severidad y generación de alertas operativas (Fase 7.3):
    1. CRITICAL: Evento agendado en < 48 horas con quiebre de stock.
    2. WARNING: Evento agendado en los próximos 14 días con quiebre proyectado o stock insuficiente.
    3. Invariante: Eventos sin quiebre o agendados más allá de 14 días NO generan alerta.
    4. Enriquecimiento: horas restantes, días restantes, insumos en déficit y mensaje explicativo.
    """
    inventory = InventoryService()
    event_srv = EventService(inventory=inventory)

    # 1. Cargar stock parcial:
    # Prod 601: 10 unidades en Bodega 1
    # Prod 602: 5 unidades en Bodega 1
    inventory.register_movement(
        producto_id=601,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("10.0000"),
        unit_cost=Decimal("5000.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )
    inventory.register_movement(
        producto_id=602,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("5.0000"),
        unit_cost=Decimal("2000.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )

    # Timestamp de referencia fijo para verificación determinista
    ref_dt = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)

    # Evento A (CRITICAL): Agendado en 26 horas (< 48h)
    # Fecha: 2026-11-03 a las 12:00 -> 26 horas de diferencia
    # Demanda: 18 unidades de Prod 601 (stock disponible es 10 -> déficit = 8)
    ev_crit = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Banquete Urgente",
            fecha=date(2026, 11, 3),
            hora_inicio=time(12, 0),
            hora_fin=time(16, 0),
            items=[
                EventoItemIn(producto_id=601, bodega_id=1, cantidad=Decimal("18.0000")),
            ],
        ),
    )

    # Evento B (WARNING): Agendado en 5 días (~124 horas, <= 14 días)
    # Fecha: 2026-11-07 a las 14:00
    # Demanda: 12 unidades de Prod 602 (stock disponible es 5 -> déficit = 7)
    ev_warn = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Almuerzo de Directorio",
            fecha=date(2026, 11, 7),
            hora_inicio=time(14, 0),
            hora_fin=time(18, 0),
            items=[
                EventoItemIn(producto_id=602, bodega_id=1, cantidad=Decimal("12.0000")),
            ],
        ),
    )

    # Evento C (Sin déficit): Agendado en 3 días (~74 horas)
    # Demanda: 0 ítems adicionales con déficit
    ev_safe = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Conferencia de Prensa",
            fecha=date(2026, 11, 5),
            hora_inicio=time(10, 0),
            hora_fin=time(12, 0),
            items=[],
        ),
    )

    # Evento D (Fuera del horizonte de 14 días): Agendado en 30 días
    # Demanda con quiebre de stock, pero > 14 días (336h) -> NO debe alertar todavía
    ev_far = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Banquete de Año Nuevo",
            fecha=date(2026, 12, 2),
            hora_inicio=time(20, 0),
            hora_fin=time(23, 59),
            items=[
                EventoItemIn(producto_id=601, bodega_id=1, cantidad=Decimal("100.0000")),
            ],
        ),
    )

    # 2. Obtener alertas operativas con la fecha de referencia
    alerts = event_srv.get_event_alerts(TEST_TENANT, reference_datetime=ref_dt)

    # Deben existir exactamente 2 alertas (Evento A crítico y Evento B preventivo)
    assert len(alerts) == 2

    # Verificar orden: CRITICAL primero
    alert_crit = alerts[0]
    assert alert_crit.evento_id == ev_crit.id
    assert alert_crit.severidad == "CRITICAL"
    assert alert_crit.horas_restantes == Decimal("26.00")
    assert alert_crit.dias_restantes == 1
    assert alert_crit.total_insumos_deficit == 1
    assert alert_crit.insumos_deficit[0].producto_id == 601
    assert alert_crit.insumos_deficit[0].cantidad_requerida == Decimal("18.0000")
    assert alert_crit.insumos_deficit[0].stock_actual == Decimal("10.0000")
    assert alert_crit.insumos_deficit[0].deficit == Decimal("8.0000")
    assert "Banquete Urgente" in alert_crit.mensaje

    # Verificar alerta WARNING
    alert_warn = alerts[1]
    assert alert_warn.evento_id == ev_warn.id
    assert alert_warn.severidad == "WARNING"
    assert alert_warn.total_insumos_deficit == 1
    assert alert_warn.insumos_deficit[0].producto_id == 602
    assert alert_warn.insumos_deficit[0].deficit == Decimal("7.0000")
    assert "Almuerzo de Directorio" in alert_warn.mensaje

    # Los eventos Safe y Far no deben estar en la lista de alertas
    alerted_event_ids = {a.evento_id for a in alerts}
    assert ev_safe.id not in alerted_event_ids
    assert ev_far.id not in alerted_event_ids


@pytest.mark.asyncio
async def test_fastapi_endpoints_committed_stock_and_alerts(async_client: httpx.AsyncClient) -> None:
    """
    Verifica los endpoints REST de stock comprometido y alertas de eventos:
    - GET /api/v1/events/analytics/committed-stock (Guard RequireTenantPermission("events.events.read"))
    - GET /api/v1/events/alerts (Guard RequireTenantPermission("events.events.read"))
    """
    event_srv = get_event_service()
    event_srv.reset()

    # Inyectar movimiento de inventario para generar stock
    inventory = InventoryService()
    inventory.register_movement(
        producto_id=701,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("50.0000"),
        unit_cost=Decimal("1200.00"),
        actor_user_id=1,
        tenant_id=TEST_TENANT,
    )
    event_srv.set_inventory(inventory)

    # Crear evento agendado para mañana que consume 60 de Prod 701 (quiebre de 10)
    tomorrow = date.today() + timedelta(days=1)
    ev = event_srv.create_event(
        TEST_TENANT,
        EventoCreate(
            nombre="Cena Ejecutiva VIP",
            fecha=tomorrow,
            hora_inicio=time(19, 0),
            hora_fin=time(22, 0),
            items=[
                EventoItemIn(producto_id=701, bodega_id=1, cantidad=Decimal("60.0000")),
            ],
        ),
    )

    unauth_headers = _make_headers(["events.events.edit"])  # Sin read
    read_headers = _make_headers(["events.events.read"])

    # 1. GET /api/v1/events/analytics/committed-stock sin permiso -> 403
    resp_comm_403 = await async_client.get(
        "/api/v1/events/analytics/committed-stock",
        headers=unauth_headers,
    )
    assert resp_comm_403.status_code == 403

    # 2. GET /api/v1/events/analytics/committed-stock con permiso -> 200 OK
    resp_comm_200 = await async_client.get(
        "/api/v1/events/analytics/committed-stock",
        headers=read_headers,
    )
    assert resp_comm_200.status_code == 200
    comm_data = resp_comm_200.json()
    assert comm_data["total_items"] >= 1
    found_item = next(it for it in comm_data["items"] if it["producto_id"] == 701)
    assert Decimal(str(found_item["stock_actual"])) == Decimal("50.0000")
    assert Decimal(str(found_item["stock_comprometido"])) == Decimal("60.0000")
    assert Decimal(str(found_item["stock_disponible_real"])) == Decimal("0.0000")
    assert len(found_item["eventos"]) >= 1

    # 3. GET /api/v1/events/alerts sin permiso -> 403
    resp_alert_403 = await async_client.get(
        "/api/v1/events/alerts",
        headers=unauth_headers,
    )
    assert resp_alert_403.status_code == 403

    # 4. GET /api/v1/events/alerts con permiso -> 200 OK
    resp_alert_200 = await async_client.get(
        "/api/v1/events/alerts",
        headers=read_headers,
    )
    assert resp_alert_200.status_code == 200
    alerts_data = resp_alert_200.json()
    assert isinstance(alerts_data, list)
    assert len(alerts_data) >= 1
    target_alert = next(a for a in alerts_data if a["evento_id"] == str(ev.id))
    assert target_alert["severidad"] == "CRITICAL"
    assert target_alert["total_insumos_deficit"] == 1
    assert target_alert["insumos_deficit"][0]["producto_id"] == 701
    assert Decimal(str(target_alert["insumos_deficit"][0]["deficit"])) == Decimal("10.0000")

