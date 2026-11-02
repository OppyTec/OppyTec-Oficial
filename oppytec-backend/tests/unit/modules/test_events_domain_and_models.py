"""
oppytec-backend/tests/unit/modules/test_events_domain_and_models.py
Pruebas Unitarias de Arquitectura DDD, Value Objects, Agregado Raíz y Modelos SQLAlchemy
para el Módulo de Eventos, Salones y Consumo de Inventario (Fase 1).
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import uuid4

import pytest

from src.modules.events.domain.entities import (
    Evento,
    EventoCombo,
    EventoConsumoKardex,
    EventoItem,
    EventoReceta,
    EventoTrabajador,
    Salon as DomainSalon,
)
from src.modules.events.domain.exceptions import (
    EventAlreadyCancelledError,
    EventAlreadyExecutedError,
    EventItemNotFoundError,
    EventOverbookingError,
    EventsDomainError,
    InvalidEventTimeSlotError,
    InvalidMoneyAmountError,
    SalonCapacityExceededError,
)
from src.modules.events.domain.value_objects import (
    EventStatus,
    EventTimeSlot,
    ItemQuantity,
    MoneyAmount,
    SalonCapacity,
    SalonState,
)
from src.modules.events.infrastructure.models import (
    Evento as SqlEvento,
    EventoCombo as SqlEventoCombo,
    EventoConsumoKardex as SqlEventoConsumoKardex,
    EventoItem as SqlEventoItem,
    EventoReceta as SqlEventoReceta,
    EventoTrabajador as SqlEventoTrabajador,
    Salon as SqlSalon,
    SalonAreaOperativa as SqlSalonAreaOperativa,
)
from src.shared.models_base import AuditTimestampsMixin, TenantBase, TranslatableI18nMixin
from src.shared.soft_delete_mixin import SoftDeleteMixin

pytestmark = pytest.mark.unit


def test_event_status_and_salon_state_parsing() -> None:
    """Verifica que los enums de estado parseen aliases case-insensitive."""
    assert EventStatus.from_str("agendado") == EventStatus.AGENDADO
    assert EventStatus.from_str("CONFIRMADO") == EventStatus.CONFIRMADO
    assert EventStatus.from_str("en curso") == EventStatus.EN_CURSO
    assert EventStatus.from_str("finalizado") == EventStatus.EJECUTADO
    assert EventStatus.from_str("cancelado") == EventStatus.CANCELADO

    assert SalonState.from_str("limpio") == SalonState.LIMPIO
    assert SalonState.from_str("ACTIVO") == SalonState.LIMPIO
    assert SalonState.from_str("en_uso") == SalonState.EN_USO
    assert SalonState.from_str("mantenimiento") == SalonState.MANTENIMIENTO
    assert SalonState.from_str("sucio") == SalonState.SUCIO


def test_event_time_slot_validation_and_overlap() -> None:
    """Valida la consistencia de horarios y detección exacta de solapamiento."""
    today = date(2026, 11, 15)

    # Error si hora_fin <= hora_inicio
    with pytest.raises(InvalidEventTimeSlotError):
        EventTimeSlot(fecha=today, hora_inicio=time(18, 0), hora_fin=time(17, 30))

    with pytest.raises(InvalidEventTimeSlotError):
        EventTimeSlot(fecha=today, hora_inicio=time(18, 0), hora_fin=time(18, 0))

    slot1 = EventTimeSlot(fecha=today, hora_inicio=time(14, 0), hora_fin=time(18, 0))
    slot2_overlap = EventTimeSlot(fecha=today, hora_inicio=time(17, 0), hora_fin=time(21, 0))
    slot3_disjoint = EventTimeSlot(fecha=today, hora_inicio=time(18, 0), hora_fin=time(22, 0))
    slot_diff_date = EventTimeSlot(fecha=date(2026, 11, 16), hora_inicio=time(14, 0), hora_fin=time(18, 0))

    assert slot1.overlaps(slot2_overlap) is True
    assert slot2_overlap.overlaps(slot1) is True
    # Intervalos semi-abiertos no solapan si el fin coincide con el inicio del siguiente
    assert slot1.overlaps(slot3_disjoint) is False
    assert slot1.overlaps(slot_diff_date) is False

    # Día completo sin horas definidas solapa todo el día
    slot_fullday = EventTimeSlot(fecha=today)
    assert slot_fullday.overlaps(slot1) is True


def test_salon_capacity_validation() -> None:
    """Verifica aforo y excepciones ante sobrecapacidad."""
    cap = SalonCapacity(max_personas=100)
    assert cap.can_accommodate(80) is True
    assert cap.can_accommodate(100) is True
    assert cap.can_accommodate(101) is False

    cap.assert_can_accommodate(95)
    with pytest.raises(SalonCapacityExceededError):
        cap.assert_can_accommodate(105)

    # Capacidad ilimitada (0)
    cap_unlimited = SalonCapacity(max_personas=0)
    assert cap_unlimited.can_accommodate(5000) is True


def test_money_amount_precision_and_vat_calculations() -> None:
    """Verifica cálculo de IVA y precisión monetaria con Decimal."""
    neto = MoneyAmount(Decimal("100000.00"))
    bruto = neto.with_vat(Decimal("19.00"))
    assert bruto.amount == Decimal("119000.00")

    recalculated_neto = bruto.without_vat(Decimal("19.00"))
    assert recalculated_neto.amount == Decimal("100000.00")

    suma = neto + MoneyAmount(Decimal("25000.00"))
    assert suma.amount == Decimal("125000.00")

    with pytest.raises(InvalidMoneyAmountError):
        MoneyAmount(Decimal("-10.00"))


def test_item_quantity_validation() -> None:
    """Verifica validación de cantidad mayor a cero."""
    qty = ItemQuantity(Decimal("12.5"))
    assert qty.quantity == Decimal("12.5000")

    with pytest.raises(ValueError):
        ItemQuantity(Decimal("0.0000"))


def test_domain_salon_lifecycle_and_pricing() -> None:
    """Verifica entidad de dominio Salon."""
    salon = DomainSalon(
        id=uuid4(),
        nombre="Salón Los Alerces",
        capacidad=SalonCapacity(150),
        precio_neto=MoneyAmount(Decimal("500000.00")),
        iva_porcentaje=Decimal("19.00"),
    )
    assert salon.precio_bruto.amount == Decimal("595000.00")
    assert salon.estado == SalonState.LIMPIO

    salon.marcar_en_uso()
    assert salon.estado == SalonState.EN_USO
    salon.marcar_sucio()
    assert salon.estado == SalonState.SUCIO
    salon.marcar_mantenimiento()
    assert salon.estado == SalonState.MANTENIMIENTO
    salon.marcar_limpio()
    assert salon.estado == SalonState.LIMPIO

    salon.actualizar_aranceles(MoneyAmount(Decimal("600000.00")), Decimal("19.00"))
    assert salon.precio_bruto.amount == Decimal("714000.00")


def test_evento_aggregate_lifecycle_transitions() -> None:
    """Verifica transiciones de estado del agregado Evento y sus invariantes."""
    evento_id = uuid4()
    salon_id = uuid4()
    today = date(2026, 12, 1)
    slot = EventTimeSlot(fecha=today, hora_inicio=time(19, 0), hora_fin=time(23, 30))

    evento = Evento(
        id=evento_id,
        nombre="Cena de Fin de Año",
        time_slot=slot,
        salon_id=salon_id,
        cantidad_personas=80,
    )

    assert evento.estado == EventStatus.AGENDADO
    assert evento.ejecutado is False
    assert evento.cancelado is False

    evento.confirmar()
    assert evento.estado == EventStatus.CONFIRMADO

    evento.iniciar()
    assert evento.estado == EventStatus.EN_CURSO

    # Ejecutar
    evento.ejecutar()
    assert evento.ejecutado is True
    assert evento.estado == EventStatus.EJECUTADO
    assert evento.ejecutado_at is not None

    # No se puede volver a ejecutar
    with pytest.raises(EventAlreadyExecutedError):
        evento.ejecutar()

    # No se puede cancelar un evento ya ejecutado
    with pytest.raises(EventAlreadyExecutedError):
        evento.cancelar("Cliente canceló")


def test_evento_aggregate_cancellation_invariants() -> None:
    """Verifica cancelación de evento y bloqueo de ejecución."""
    evento = Evento(
        id=uuid4(),
        nombre="Bautizo Familiar",
        time_slot=EventTimeSlot(fecha=date(2026, 12, 5)),
        salon_id=uuid4(),
    )

    evento.cancelar("Fuerza mayor")
    assert evento.cancelado is True
    assert evento.estado == EventStatus.CANCELADO
    assert evento.motivo_cancelacion == "Fuerza mayor"
    assert evento.cancelado_at is not None

    with pytest.raises(EventAlreadyCancelledError):
        evento.cancelar("Otro motivo")

    with pytest.raises(EventAlreadyCancelledError):
        evento.ejecutar()


def test_evento_anti_overbooking_detection() -> None:
    """Verifica detección de colisión temporal en el mismo salón."""
    salon_a = uuid4()
    salon_b = uuid4()
    today = date(2026, 11, 20)

    ev1 = Evento(
        id=uuid4(),
        nombre="Matrimonio Pérez",
        time_slot=EventTimeSlot(fecha=today, hora_inicio=time(13, 0), hora_fin=time(18, 0)),
        salon_id=salon_a,
    )

    # Mismo salón, horario solapado
    ev2_collision = Evento(
        id=uuid4(),
        nombre="Graduación",
        time_slot=EventTimeSlot(fecha=today, hora_inicio=time(16, 0), hora_fin=time(21, 0)),
        salon_id=salon_a,
    )

    # Distinto salón -> no colisiona
    ev3_other_salon = Evento(
        id=uuid4(),
        nombre="Congreso Médico",
        time_slot=EventTimeSlot(fecha=today, hora_inicio=time(14, 0), hora_fin=time(17, 0)),
        salon_id=salon_b,
    )

    assert ev1.verificar_solapamiento(ev2_collision) is True
    assert ev1.verificar_solapamiento(ev3_other_salon) is False

    with pytest.raises(EventOverbookingError):
        ev1.assert_no_colision([ev2_collision])

    # Si ev2 está cancelado, no debe colisionar
    ev2_collision.cancelar("Suspendido")
    assert ev1.verificar_solapamiento(ev2_collision) is False


def test_evento_items_recipes_combos_and_staff_management() -> None:
    """Verifica agregado de insumos, recetas, combos y asignación de personal."""
    evento = Evento(
        id=uuid4(),
        nombre="Gala Anual Corporativa",
        time_slot=EventTimeSlot(fecha=date(2026, 12, 10)),
        salon_id=uuid4(),
    )

    # Agregar insumo directo
    item1 = evento.agregar_item(
        producto_id=101,
        bodega_id=1,
        cantidad=ItemQuantity(Decimal("5.5000")),
        costo_unitario_estimado=MoneyAmount(Decimal("3200.00")),
        notas="Carne de res premium",
    )
    assert len(evento.items) == 1
    assert item1.cantidad.quantity == Decimal("5.5000")

    # Acumulación sobre el mismo producto/bodega
    evento.agregar_item(producto_id=101, bodega_id=1, cantidad=ItemQuantity(Decimal("2.5000")))
    assert len(evento.items) == 1
    assert item1.cantidad.quantity == Decimal("8.0000")

    # Agregar recetas y combos
    rec1 = evento.agregar_receta(receta_id=205, porciones=50, bodega_id=1)
    assert len(evento.recetas) == 1
    assert rec1.porciones == 50

    cmb1 = evento.agregar_combo(combo_id=302, cantidad=10, bodega_id=1)
    assert len(evento.combos) == 1
    assert cmb1.cantidad == 10

    # Asignar trabajador
    trab = evento.asignar_trabajador(usuario_id=12, rol_evento="Maitre", horas_asignadas=Decimal("6.00"))
    assert len(evento.trabajadores) == 1
    assert trab.rol_evento == "Maitre"

    # Remover ítems
    evento.remover_item(item1.id)
    assert len(evento.items) == 0

    with pytest.raises(EventItemNotFoundError):
        evento.remover_item(uuid4())


def test_sqlalchemy_models_architecture_and_tenant_base() -> None:
    """Verifica que todos los modelos SQLAlchemy hereden estrictamente de TenantBase y mixins."""
    models = [
        SqlSalon,
        SqlSalonAreaOperativa,
        SqlEvento,
        SqlEventoItem,
        SqlEventoReceta,
        SqlEventoCombo,
        SqlEventoTrabajador,
        SqlEventoConsumoKardex,
    ]

    for model_cls in models:
        assert issubclass(model_cls, TenantBase), f"{model_cls.__name__} debe heredar de TenantBase"
        assert model_cls.__tablename__ in TenantBase.metadata.tables, (
            f"Tabla {model_cls.__tablename__} no registrada en TenantBase.metadata"
        )

    # Modelos auditables
    auditable_models = [
        SqlSalon,
        SqlEvento,
        SqlEventoItem,
        SqlEventoReceta,
        SqlEventoCombo,
        SqlEventoTrabajador,
        SqlEventoConsumoKardex,
    ]
    for model_cls in auditable_models:
        assert issubclass(model_cls, AuditTimestampsMixin), (
            f"{model_cls.__name__} debe heredar de AuditTimestampsMixin"
        )

    # Modelos con SoftDelete y Translatable
    assert issubclass(SqlSalon, SoftDeleteMixin)
    assert issubclass(SqlSalon, TranslatableI18nMixin)
    assert issubclass(SqlEvento, SoftDeleteMixin)
    assert issubclass(SqlEvento, TranslatableI18nMixin)


def test_sqlalchemy_salon_and_evento_instantiation() -> None:
    """Verifica instanciación de modelos SQLAlchemy y compatibilidad con synonyms."""
    now = datetime.now(UTC)
    salon = SqlSalon(
        nombre="Salón Imperial",
        capacidad_personas=200,
        precio_neto=Decimal("800000.00"),
        iva_porcentaje=Decimal("19.00"),
        precio_bruto=Decimal("952000.00"),
        estado="limpio",
    )
    salon.set_localized_text("en", "Imperial Hall")
    assert salon.get_localized_text("en", salon.nombre) == "Imperial Hall"

    evento = SqlEvento(
        nombre="Matrimonio González",
        fecha=date(2026, 12, 20),
        hora_inicio=time(18, 0),
        hora_fin=time(23, 59),
        cantidad_personas=150,
        valor_publico=Decimal("4500000.00"),
    )
    # Verificación de synonyms
    assert evento.nombre_evento == "Matrimonio González"
    assert evento.cantidad_invitados == 150
    assert evento.asistentes_confirmados == 150
    assert evento.presupuesto_acordado == Decimal("4500000.00")
    assert evento.fecha_inicio == datetime(2026, 12, 20, 18, 0)
