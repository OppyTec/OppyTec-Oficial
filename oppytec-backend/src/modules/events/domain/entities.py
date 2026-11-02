"""
oppytec-backend/src/modules/events/domain/entities.py
Entidades de dominio puro y Agregado Raíz para el Módulo de Eventos, Salones y Banquetes.
Desacopladas de ORM / Base de datos según DDD y Clean Architecture.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from src.modules.events.domain.exceptions import (
    EventAlreadyCancelledError,
    EventAlreadyExecutedError,
    EventItemNotFoundError,
    EventOverbookingError,
    EventStatusTransitionError,
)
from src.modules.events.domain.value_objects import (
    EventStatus,
    EventTimeSlot,
    ItemQuantity,
    MoneyAmount,
    SalonCapacity,
    SalonState,
)


@dataclass
class Salon:
    """Entidad Salón: Espacio físico donde se ejecutan recepciones, banquetes y eventos."""

    id: UUID
    nombre: str
    capacidad: SalonCapacity
    precio_neto: MoneyAmount
    iva_porcentaje: Decimal = Decimal("19.00")
    precio_bruto: MoneyAmount = field(default_factory=lambda: MoneyAmount(Decimal("0.00")))
    estado: SalonState = SalonState.LIMPIO
    color: str = "#ec4899"
    notas: str | None = None
    areas_operativas_ids: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.precio_bruto.amount == Decimal("0.00") and self.precio_neto.amount > Decimal("0.00"):
            self.precio_bruto = self.precio_neto.with_vat(self.iva_porcentaje)

    def actualizar_aranceles(
        self,
        precio_neto: MoneyAmount,
        iva_porcentaje: Decimal = Decimal("19.00"),
    ) -> None:
        """Actualiza el precio neto y re-calcula el precio bruto con IVA."""
        self.precio_neto = precio_neto
        self.iva_porcentaje = iva_porcentaje
        self.precio_bruto = precio_neto.with_vat(iva_porcentaje)

    def marcar_limpio(self) -> None:
        self.estado = SalonState.LIMPIO

    def marcar_en_uso(self) -> None:
        self.estado = SalonState.EN_USO

    def marcar_mantenimiento(self) -> None:
        self.estado = SalonState.MANTENIMIENTO

    def marcar_sucio(self) -> None:
        self.estado = SalonState.SUCIO


@dataclass
class EventoItem:
    """Entidad de línea para insumos directos extraídos de una bodega."""

    id: UUID
    evento_id: UUID
    producto_id: int
    bodega_id: int
    cantidad: ItemQuantity
    costo_unitario_estimado: MoneyAmount = field(default_factory=lambda: MoneyAmount(Decimal("0.00")))
    notas: str | None = None


@dataclass
class EventoReceta:
    """Entidad de línea para recetas o preparaciones gastronómicas."""

    id: UUID
    evento_id: UUID
    receta_id: int
    bodega_id: int | None = None
    porciones: int = 1
    notas: str | None = None

    def __post_init__(self) -> None:
        if self.porciones <= 0:
            raise ValueError("Las porciones de la receta deben ser mayores a cero.")


@dataclass
class EventoCombo:
    """Entidad de línea para combos o promociones asignadas."""

    id: UUID
    evento_id: UUID
    combo_id: int
    bodega_id: int | None = None
    cantidad: int = 1
    notas: str | None = None

    def __post_init__(self) -> None:
        if self.cantidad <= 0:
            raise ValueError("La cantidad del combo debe ser mayor a cero.")


@dataclass
class EventoTrabajador:
    """Entidad de asignación de brigada/personal operativo para el evento."""

    id: UUID
    evento_id: UUID
    usuario_id: int
    rol_evento: str | None = None
    horas_asignadas: Decimal = Decimal("0.00")


@dataclass
class EventoConsumoKardex:
    """Registro inmutable de trazabilidad de consumo de Kardex generado al ejecutar."""

    id: UUID
    evento_id: UUID
    kardex_movement_id: int
    producto_id: int
    bodega_id: int
    cantidad_consumida: Decimal
    costo_unitario_ppp: Decimal
    origen_tipo: str = "DIRECTO"  # DIRECTO, RECETA, COMBO
    origen_id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Evento:
    """
    Agregado Raíz del Módulo de Eventos.
    Encapsula el ciclo de vida, la asignación de insumos/recetas/combos/trabajadores,
    la regla de anti-overbooking y la ejecución transaccional.
    """

    id: UUID
    nombre: str
    time_slot: EventTimeSlot
    tipo_evento: str = "GENERAL"
    salon_id: UUID | None = None
    titular: str | None = None
    lugar: str | None = None
    cantidad_personas: int = 0
    estado: EventStatus = EventStatus.AGENDADO
    color: str = "#ec4899"
    ejecutado: bool = False
    cancelado: bool = False
    ejecutado_at: datetime | None = None
    cancelado_at: datetime | None = None
    motivo_cancelacion: str | None = None
    encargado_id: int | None = None
    created_by_user_id: int | None = None
    valor_publico: MoneyAmount = field(default_factory=lambda: MoneyAmount(Decimal("0.00")))
    notas: str | None = None
    nota_personal: str | None = None
    nota_equipo: str | None = None
    nota_visible: str | None = None

    items: list[EventoItem] = field(default_factory=list)
    recetas: list[EventoReceta] = field(default_factory=list)
    combos: list[EventoCombo] = field(default_factory=list)
    trabajadores: list[EventoTrabajador] = field(default_factory=list)
    consumos_kardex: list[EventoConsumoKardex] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # Reglas de Ciclo de Vida
    # -------------------------------------------------------------------------

    def confirmar(self) -> None:
        """Transiciona de AGENDADO a CONFIRMADO."""
        if self.ejecutado:
            raise EventAlreadyExecutedError("No se puede confirmar un evento ya ejecutado.")
        if self.cancelado:
            raise EventAlreadyCancelledError("No se puede confirmar un evento cancelado.")
        self.estado = EventStatus.CONFIRMADO

    def iniciar(self) -> None:
        """Pasa el evento a EN_CURSO."""
        if self.ejecutado:
            raise EventAlreadyExecutedError("No se puede iniciar un evento ya ejecutado.")
        if self.cancelado:
            raise EventAlreadyCancelledError("No se puede iniciar un evento cancelado.")
        self.estado = EventStatus.EN_CURSO

    def ejecutar(self, executed_at: datetime | None = None) -> None:
        """
        Marca el evento como ejecutado tras descontar en Kardex.
        Invariante: No se puede ejecutar un evento cancelado o previamente ejecutado.
        """
        if self.ejecutado:
            raise EventAlreadyExecutedError(
                f"El evento '{self.nombre}' ya fue ejecutado el {self.ejecutado_at}."
            )
        if self.cancelado:
            raise EventAlreadyCancelledError(
                f"No es posible ejecutar el evento cancelado '{self.nombre}'."
            )

        self.ejecutado = True
        self.estado = EventStatus.EJECUTADO
        self.ejecutado_at = executed_at or datetime.now(UTC)

    def cancelar(self, motivo: str, cancelled_at: datetime | None = None) -> None:
        """
        Cancela el evento registrando motivo y timestamp.
        Invariante: No se puede cancelar un evento ya ejecutado.
        """
        if self.ejecutado:
            raise EventAlreadyExecutedError(
                f"No se puede cancelar el evento '{self.nombre}' porque ya fue ejecutado en Kardex."
            )
        if self.cancelado:
            raise EventAlreadyCancelledError(f"El evento '{self.nombre}' ya está cancelado.")

        self.cancelado = True
        self.estado = EventStatus.CANCELADO
        self.cancelado_at = cancelled_at or datetime.now(UTC)
        self.motivo_cancelacion = motivo.strip()

    def revertir(self, motivo: str, reversed_at: datetime | None = None) -> None:
        """
        Revierte un evento previamente ejecutado en Kardex, generando anulación compensatoria.
        Invariante: Solo se puede revertir un evento que ya fue ejecutado previamente.
        """
        if not self.ejecutado:
            raise EventStatusTransitionError(
                f"No se puede revertir el evento '{self.nombre}' porque no ha sido ejecutado en Kardex."
            )
        if self.cancelado:
            raise EventAlreadyCancelledError(
                f"El evento '{self.nombre}' ya fue revertido o cancelado previamente."
            )

        self.cancelado = True
        self.estado = EventStatus.CANCELADO
        self.cancelado_at = reversed_at or datetime.now(UTC)
        self.motivo_cancelacion = motivo.strip()

    # -------------------------------------------------------------------------
    # Reglas de Validación de Capacidad y Sobreventa
    # -------------------------------------------------------------------------

    def validar_capacidad(self, salon: Salon) -> None:
        """Verifica que el aforo de asistentes quepa en la capacidad del salón."""
        salon.capacidad.assert_can_accommodate(self.cantidad_personas)

    def verificar_solapamiento(self, otro: Evento) -> bool:
        """
        Verifica si colisiona en fecha/hora y salón con otro evento.
        Los eventos cancelados jamás generan colisión.
        Eventos sin salón asignado no colisionan por espacio físico.
        """
        if self.cancelado or otro.cancelado:
            return False
        if self.id == otro.id:
            return False
        if self.salon_id is None or otro.salon_id is None:
            return False
        if self.salon_id != otro.salon_id:
            return False

        return self.time_slot.overlaps(otro.time_slot)

    def assert_no_colision(self, otros: list[Evento]) -> None:
        """Lanza `EventOverbookingError` si colisiona con algún evento activo en la lista."""
        for otro in otros:
            if self.verificar_solapamiento(otro):
                raise EventOverbookingError(
                    f"Colisión de salón: El evento '{self.nombre}' se solapa con '{otro.nombre}' "
                    f"en la franja {self.time_slot.fecha} {self.time_slot.hora_inicio}-{self.time_slot.hora_fin}.",
                    context={
                        "evento_id": str(self.id),
                        "colision_evento_id": str(otro.id),
                        "salon_id": str(self.salon_id),
                    },
                )

    # -------------------------------------------------------------------------
    # Gestión de Insumos, Recetas, Combos y Personal
    # -------------------------------------------------------------------------

    def agregar_item(
        self,
        producto_id: int,
        bodega_id: int,
        cantidad: ItemQuantity,
        costo_unitario_estimado: MoneyAmount | None = None,
        notas: str | None = None,
    ) -> EventoItem:
        """Agrega un insumo directo o actualiza cantidad si ya existe."""
        if self.ejecutado:
            raise EventAlreadyExecutedError("No se pueden alterar ítems de un evento ya ejecutado.")

        for item in self.items:
            if item.producto_id == producto_id and item.bodega_id == bodega_id:
                # Actualizar cantidad acumulativa
                nueva_cant = ItemQuantity(item.cantidad.quantity + cantidad.quantity)
                item.cantidad = nueva_cant
                if notas:
                    item.notas = notas
                return item

        nuevo_item = EventoItem(
            id=uuid4(),
            evento_id=self.id,
            producto_id=producto_id,
            bodega_id=bodega_id,
            cantidad=cantidad,
            costo_unitario_estimado=costo_unitario_estimado or MoneyAmount.zero(),
            notas=notas,
        )
        self.items.append(nuevo_item)
        return nuevo_item

    def remover_item(self, item_id: UUID) -> None:
        if self.ejecutado:
            raise EventAlreadyExecutedError("No se pueden alterar ítems de un evento ya ejecutado.")
        initial_len = len(self.items)
        self.items = [i for i in self.items if i.id != item_id]
        if len(self.items) == initial_len:
            raise EventItemNotFoundError(f"Ítem con id {item_id} no encontrado en el evento.")

    def agregar_receta(
        self,
        receta_id: int,
        porciones: int = 1,
        bodega_id: int | None = None,
        notas: str | None = None,
    ) -> EventoReceta:
        if self.ejecutado:
            raise EventAlreadyExecutedError("No se pueden alterar recetas de un evento ya ejecutado.")

        for rec in self.recetas:
            if rec.receta_id == receta_id and rec.bodega_id == bodega_id:
                rec.porciones += porciones
                return rec

        nueva_rec = EventoReceta(
            id=uuid4(),
            evento_id=self.id,
            receta_id=receta_id,
            bodega_id=bodega_id,
            porciones=porciones,
            notas=notas,
        )
        self.recetas.append(nueva_rec)
        return nueva_rec

    def remover_receta(self, receta_evento_id: UUID) -> None:
        if self.ejecutado:
            raise EventAlreadyExecutedError("No se pueden alterar recetas de un evento ya ejecutado.")
        initial_len = len(self.recetas)
        self.recetas = [r for r in self.recetas if r.id != receta_evento_id]
        if len(self.recetas) == initial_len:
            raise EventItemNotFoundError(f"Receta de evento con id {receta_evento_id} no encontrada.")

    def agregar_combo(
        self,
        combo_id: int,
        cantidad: int = 1,
        bodega_id: int | None = None,
        notas: str | None = None,
    ) -> EventoCombo:
        if self.ejecutado:
            raise EventAlreadyExecutedError("No se pueden alterar combos de un evento ya ejecutado.")

        for cmb in self.combos:
            if cmb.combo_id == combo_id and cmb.bodega_id == bodega_id:
                cmb.cantidad += cantidad
                return cmb

        nuevo_cmb = EventoCombo(
            id=uuid4(),
            evento_id=self.id,
            combo_id=combo_id,
            bodega_id=bodega_id,
            cantidad=cantidad,
            notas=notas,
        )
        self.combos.append(nuevo_cmb)
        return nuevo_cmb

    def remover_combo(self, combo_evento_id: UUID) -> None:
        if self.ejecutado:
            raise EventAlreadyExecutedError("No se pueden alterar combos de un evento ya ejecutado.")
        initial_len = len(self.combos)
        self.combos = [c for c in self.combos if c.id != combo_evento_id]
        if len(self.combos) == initial_len:
            raise EventItemNotFoundError(f"Combo de evento con id {combo_evento_id} no encontrado.")

    def asignar_trabajador(
        self,
        usuario_id: int,
        rol_evento: str | None = None,
        horas_asignadas: Decimal = Decimal("0.00"),
    ) -> EventoTrabajador:
        if self.ejecutado:
            raise EventAlreadyExecutedError("No se puede asignar personal a un evento ya ejecutado.")

        for trab in self.trabajadores:
            if trab.usuario_id == usuario_id:
                trab.rol_evento = rol_evento
                trab.horas_asignadas = horas_asignadas
                return trab

        nuevo_trab = EventoTrabajador(
            id=uuid4(),
            evento_id=self.id,
            usuario_id=usuario_id,
            rol_evento=rol_evento,
            horas_asignadas=horas_asignadas,
        )
        self.trabajadores.append(nuevo_trab)
        return nuevo_trab

    def remover_trabajador(self, usuario_id: int) -> None:
        if self.ejecutado:
            raise EventAlreadyExecutedError("No se puede desasignar personal de un evento ya ejecutado.")
        self.trabajadores = [t for t in self.trabajadores if t.usuario_id != usuario_id]


__all__ = [
    "Evento",
    "EventoCombo",
    "EventoConsumoKardex",
    "EventoItem",
    "EventoReceta",
    "EventoTrabajador",
    "Salon",
]
