"""
oppytec-backend/src/modules/events/application/services.py
Servicios de Aplicación Transaccionales para el Módulo de Eventos, Salones y Consumo de Inventario:
- `SalonService`: CRUD de salones, validación de áreas operativas y recálculo automático de precio bruto con IVA.
- `EventService`:
  * Listado y detalle de eventos.
  * Agendamiento con validación atómica anti-overbooking (`EventTimeSlot.overlaps`).
  * Edición restringida a eventos no ejecutados y no cancelados.
  * Cancelación y reactivación condicional a slot horario libre.
  * Ejecución transaccional y rebaje de inventario en Kardex (`registro_stock`, `evento_consumos_kardex`).
  * Banner analítico de faltantes (`get_faltantes_analytics`).
  * Emisión de eventos WebSockets en tiempo real vía Redis Pub/Sub (`events.changed`, `salones.changed`).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from opentelemetry import trace

from src.core.observability import trace_span
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.events.domain.exceptions import (
    EventAlreadyCancelledError,
    EventAlreadyExecutedError,
    EventNotFoundError,
    EventOverbookingError,
    EventsDomainError,
    EventStatusTransitionError,
    SalonNotFoundError,
)
from src.modules.events.domain.value_objects import EventTimeSlot
from src.modules.events.presentation.schemas import (
    CommittedStockEventRef,
    CommittedStockItemOut,
    CommittedStockSummaryResponse,
    EventAlertInsumoDeficit,
    EventAlertOut,
    EventExecutionResultSchema,
    EventFaltanteItemOut,
    EventFaltantesResponse,
    EventoComboOut,
    EventoConsumoKardexOut,
    EventoCreate,
    EventoItemOut,
    EventoListItemOut,
    EventoOut,
    EventoRecetaOut,
    EventoReverseResultSchema,
    EventoTrabajadorOut,
    EventoUpdate,
    SalonCreate,
    SalonOut,
    SalonUpdate,
)

logger = logging.getLogger("oppytec.events.services")
tracer = trace.get_tracer("oppytec.events.services")


class InventoryServiceProtocol(Protocol):
    """Protocolo desacoplado para interacción con Kardex e Inventario."""

    def register_movement(
        self,
        *,
        producto_id: int,
        bodega_id: int,
        movement_type: str,
        quantity: Decimal,
        unit_cost: Decimal = Decimal(0),
        actor_user_id: int = 1,
        documento_referencia: str | None = None,
        tenant_id: str | None = None,
        **kwargs: Any,
    ) -> Any: ...

    def get_stock_balance(self, producto_id: int, bodega_id: int) -> Decimal: ...


@dataclass
class _FallbackKardexEntry:
    id: int
    costo_unitario_ppp: Decimal
    unit_cost: Decimal


class _InMemoryInventoryFallback:
    """Implementación de respaldo para inventario si InventoryService no se inyecta."""

    def __init__(self) -> None:
        self._balances: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0.0000"))
        self._next_id = 1

    def register_movement(
        self,
        *,
        producto_id: int,
        bodega_id: int,
        movement_type: str,
        quantity: Decimal,
        unit_cost: Decimal = Decimal("0.00"),
        actor_user_id: int = 1,
        documento_referencia: str | None = None,
        tenant_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        entry_id = self._next_id
        self._next_id += 1
        m_type = str(movement_type).strip().upper()
        if m_type in {"ENTRADA", "COMPRA", "AJUSTE_POSITIVO", "TRASPASO_IN", "AJUSTE_EVENTO_REVERSA"}:
            self._balances[(producto_id, bodega_id)] += quantity
        else:
            self._balances[(producto_id, bodega_id)] -= quantity
        return _FallbackKardexEntry(
            id=entry_id,
            costo_unitario_ppp=unit_cost,
            unit_cost=unit_cost,
        )

    def get_stock_balance(self, producto_id: int, bodega_id: int) -> Decimal:
        return self._balances[(producto_id, bodega_id)]


def _format_tenant_key(tenant_id: str | UUID | None) -> str:
    """Normaliza el tenant_id a string para claves de indexación en memoria."""
    if not tenant_id:
        return "tenant_default"
    cleaned = str(tenant_id).strip().lower().replace("-", "_")
    if not cleaned.startswith("tenant_"):
        cleaned = f"tenant_{cleaned}"
    return cleaned


def _parse_tenant_uuid(tenant_id: str | UUID | None) -> UUID | None:
    """Extrae un UUID opcional de tenant_id si cumple formato."""
    if not tenant_id:
        return None
    if isinstance(tenant_id, UUID):
        return tenant_id
    raw = str(tenant_id).replace("tenant_", "").replace("_", "-")
    with suppress(Exception):
        return UUID(raw)
    return None


def _dispatch_realtime_notification(
    *,
    event_type: str,
    tenant_id: str | UUID | None,
    required_permission: str,
    query_keys_to_invalidate: list[list[str]],
    payload: dict[str, Any],
) -> None:
    """Emite un evento de notificación en tiempo real a Redis sin bloquear ejecución."""
    try:
        publisher = get_realtime_publisher()
        envelope = RealtimeEventEnvelope(
            event_type=event_type,
            tenant_id=_parse_tenant_uuid(tenant_id),
            required_permission=required_permission,
            query_keys_to_invalidate=query_keys_to_invalidate,
            payload=payload,
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(publisher.publish_event(envelope))
        except RuntimeError:
            with suppress(Exception):
                asyncio.run(publisher.publish_event(envelope))
    except Exception as exc:  # pragma: no cover
        logger.debug("Realtime dispatch bypassed: %s", exc)


# ============================================================================
# SALON SERVICE
# ============================================================================


class SalonService:
    """
    Servicio de Aplicación para Salones y Espacios Físicos.
    Garantiza consistencia arancelaria, cálculo de IVA (19% por defecto)
    y validación de dependencias operativas.
    """

    def __init__(self) -> None:
        # Estructura: {tenant_key: {salon_id: SalonOut}}
        self._salones: dict[str, dict[UUID, SalonOut]] = defaultdict(dict)
        self._deleted_ids: dict[str, set[UUID]] = defaultdict(set)

    def reset(self) -> None:
        """Limpia el estado en memoria para aislamiento entre tests."""
        self._salones.clear()
        self._deleted_ids.clear()

    @staticmethod
    def calculate_precio_bruto(
        precio_neto: Decimal,
        iva_porcentaje: Decimal = Decimal("19.00"),
    ) -> Decimal:
        """Calcula el precio bruto a partir del neto aplicando el porcentaje de IVA."""
        factor = Decimal("1.00") + (iva_porcentaje / Decimal("100.00"))
        return (precio_neto * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def list_salones(
        self,
        tenant_id: str | UUID | None = None,
        area_operativa_id: int | None = None,
    ) -> list[SalonOut]:
        """Lista los salones activos filtrables por área operativa."""
        t_key = _format_tenant_key(tenant_id)
        salones_map = self._salones[t_key]
        deleted = self._deleted_ids[t_key]

        result: list[SalonOut] = []
        for s in salones_map.values():
            if s.id in deleted:
                continue
            if area_operativa_id is not None:
                if area_operativa_id not in (s.areas_operativas_ids or []):
                    continue
            result.append(s)

        return sorted(result, key=lambda x: x.nombre.lower())

    def get_salon_by_id(
        self,
        tenant_id: str | UUID | None,
        salon_id: UUID,
    ) -> SalonOut:
        """Obtiene un salón por su UUID o lanza SalonNotFoundError."""
        t_key = _format_tenant_key(tenant_id)
        if salon_id in self._deleted_ids[t_key] or salon_id not in self._salones[t_key]:
            raise SalonNotFoundError(
                f"Salón {salon_id} no encontrado en el tenant {tenant_id}.",
                context={"salon_id": str(salon_id), "tenant_id": str(tenant_id)},
            )
        return self._salones[t_key][salon_id]

    def create_salon(
        self,
        tenant_id: str | UUID | None,
        data: SalonCreate,
    ) -> SalonOut:
        """Registra un nuevo salón con cálculo automático de precio bruto con IVA."""
        with trace_span(
            "events.salon.create",
            attributes={"tenant_id": str(tenant_id), "nombre": data.nombre},
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            t_key = _format_tenant_key(tenant_id)
            salon_id = uuid4()
            span_attrs["salon_id"] = str(salon_id)
            now = datetime.now(UTC)

            # Cálculo de precio bruto si no se proporcionó o para garantizar consistencia
            neto = data.precio_neto.quantize(Decimal("0.01"))
            iva = data.iva_porcentaje.quantize(Decimal("0.01"))
            if data.precio_bruto is not None and data.precio_bruto > Decimal("0.00"):
                bruto = data.precio_bruto.quantize(Decimal("0.01"))
            else:
                bruto = self.calculate_precio_bruto(neto, iva)

            salon = SalonOut(
                id=salon_id,
                nombre=data.nombre.strip(),
                capacidad_personas=data.capacidad_personas,
                precio_neto=neto,
                iva_porcentaje=iva,
                precio_bruto=bruto,
                notas=data.notas,
                estado=data.estado,
                color=data.color,
                areas_operativas_ids=list(data.areas_operativas_ids or []),
                created_at=now,
                updated_at=now,
            )

            self._salones[t_key][salon_id] = salon

            _dispatch_realtime_notification(
                event_type="events.salones.changed",
                tenant_id=tenant_id,
                required_permission="events.salones.read",
                query_keys_to_invalidate=[["salones"], ["events"]],
                payload={"action": "created", "salon_id": str(salon_id)},
            )

            return salon

    def update_salon(
        self,
        tenant_id: str | UUID | None,
        salon_id: UUID,
        data: SalonUpdate,
    ) -> SalonOut:
        """Actualiza atributos de un salón existente y recalcula IVA si corresponde."""
        with trace_span(
            "events.salon.update",
            attributes={"tenant_id": str(tenant_id), "salon_id": str(salon_id)},
            tracer_name="oppytec.events.services",
        ):
            salon = self.get_salon_by_id(tenant_id, salon_id)
            t_key = _format_tenant_key(tenant_id)

            nombre = data.nombre.strip() if data.nombre is not None else salon.nombre
            capacidad = data.capacidad_personas if data.capacidad_personas is not None else salon.capacidad_personas
            neto = data.precio_neto.quantize(Decimal("0.01")) if data.precio_neto is not None else salon.precio_neto
            iva = data.iva_porcentaje.quantize(Decimal("0.01")) if data.iva_porcentaje is not None else salon.iva_porcentaje

            if data.precio_bruto is not None:
                bruto = data.precio_bruto.quantize(Decimal("0.01"))
            elif data.precio_neto is not None or data.iva_porcentaje is not None:
                bruto = self.calculate_precio_bruto(neto, iva)
            else:
                bruto = salon.precio_bruto

            notas = data.notas if data.notas is not None else salon.notas
            estado = data.estado if data.estado is not None else salon.estado
            color = data.color if data.color is not None else salon.color
            areas = list(data.areas_operativas_ids) if data.areas_operativas_ids is not None else salon.areas_operativas_ids

            updated_salon = SalonOut(
                id=salon_id,
                nombre=nombre,
                capacidad_personas=capacidad,
                precio_neto=neto,
                iva_porcentaje=iva,
                precio_bruto=bruto,
                notas=notas,
                estado=estado,
                color=color,
                areas_operativas_ids=areas,
                created_at=salon.created_at,
                updated_at=datetime.now(UTC),
            )

            self._salones[t_key][salon_id] = updated_salon

            _dispatch_realtime_notification(
                event_type="events.salones.changed",
                tenant_id=tenant_id,
                required_permission="events.salones.read",
                query_keys_to_invalidate=[["salones"], ["events"]],
                payload={"action": "updated", "salon_id": str(salon_id)},
            )

            return updated_salon

    def delete_salon(
        self,
        tenant_id: str | UUID | None,
        salon_id: UUID,
    ) -> bool:
        """Soft-delete de un salón verificando que exista."""
        with trace_span(
            "events.salon.delete",
            attributes={"tenant_id": str(tenant_id), "salon_id": str(salon_id)},
            tracer_name="oppytec.events.services",
        ):
            # Valida existencia
            self.get_salon_by_id(tenant_id, salon_id)
            t_key = _format_tenant_key(tenant_id)
            self._deleted_ids[t_key].add(salon_id)

            _dispatch_realtime_notification(
                event_type="events.salones.changed",
                tenant_id=tenant_id,
                required_permission="events.salones.read",
                query_keys_to_invalidate=[["salones"], ["events"]],
                payload={"action": "deleted", "salon_id": str(salon_id)},
            )

            return True


# ============================================================================
# EVENT SERVICE
# ============================================================================


class EventService:
    """
    Servicio de Aplicación Transaccional para Eventos y Banquetes.
    Coordina la persistencia del Agregado Raíz `Evento`, control de anti-overbooking
    estricto por franjas horarias en salones, ejecución atómica con rebaje en Kardex
    y cálculo de quiebres de inventario predictivo.
    """

    def __init__(
        self,
        inventory: InventoryServiceProtocol | Any = None,
        salon_service: SalonService | None = None,
    ) -> None:
        if inventory is not None:
            self._inventory = inventory
        else:
            try:
                from src.modules.inventory.application.inventory_service import InventoryService
                self._inventory = InventoryService()
            except Exception:
                self._inventory = _InMemoryInventoryFallback()
        self._salon_service = salon_service or SalonService()

        # Almacenamiento en memoria: {tenant_key: {event_id: EventoOut}}
        self._events: dict[str, dict[UUID, EventoOut]] = defaultdict(dict)
        self._deleted_ids: dict[str, set[UUID]] = defaultdict(set)

        # Catálogo en memoria de recetas: {receta_id: list[(producto_id, cantidad)]}
        self._recipe_specs: dict[int, list[tuple[int, Decimal]]] = {}
        # Catálogo en memoria de combos: {combo_id: list[(producto_id, cantidad)]}
        self._combo_specs: dict[int, list[tuple[int, Decimal]]] = {}
        # Catálogo en memoria de sub-recetas en combos: {combo_id: list[(receta_id, porciones_en_combo)]}
        self._combo_recipe_specs: dict[int, list[tuple[int, int]]] = {}
        # Costos unitarios estimados para Kardex
        self._product_costs: dict[int, Decimal] = {}

    def reset(self) -> None:
        """Limpia el estado en memoria para aislamiento entre tests."""
        self._events.clear()
        self._deleted_ids.clear()
        self._recipe_specs.clear()
        self._combo_specs.clear()
        self._combo_recipe_specs.clear()
        self._product_costs.clear()

    def set_inventory(self, inventory: InventoryServiceProtocol | Any) -> None:
        """Permite inyectar o sustituir la instancia del servicio de inventario/kardex."""
        self._inventory = inventory

    def register_recipe_ingredients(
        self,
        receta_id: int,
        ingredients: list[tuple[int, Decimal]],
    ) -> None:
        """Registra la receta y sus ingredientes para desglose BOM al ejecutar eventos."""
        self._recipe_specs[receta_id] = ingredients

    def register_combo_components(
        self,
        combo_id: int,
        components: list[tuple[int, Decimal]],
    ) -> None:
        """Registra componentes de un combo comercial (ítems directos)."""
        self._combo_specs[combo_id] = components

    def register_combo_recipes(
        self,
        combo_id: int,
        recipes: list[tuple[int, int]],
    ) -> None:
        """Registra recetas gastronómicas contenidas en un combo comercial."""
        self._combo_recipe_specs[combo_id] = recipes

    def set_product_cost(self, producto_id: int, cost: Decimal) -> None:
        """Registra el costo unitario de un producto."""
        self._product_costs[producto_id] = cost

    def _validate_anti_overbooking(
        self,
        tenant_id: str | UUID | None,
        salon_id: UUID | None,
        fecha: date,
        hora_inicio: time | None,
        hora_fin: time | None,
        exclude_event_id: UUID | None = None,
    ) -> None:
        """
        Valida que el salón no presente conflictos de overbooking temporal.
        Si las horas son inconsistentes (fin <= inicio), lanza InvalidEventTimeSlotError.
        Si hay solapamiento con otro evento activo en el mismo salón y fecha, lanza EventOverbookingError.
        """
        slot = EventTimeSlot(fecha=fecha, hora_inicio=hora_inicio, hora_fin=hora_fin)
        if salon_id is None:
            # Evento sin salón asignado no genera conflicto físico en salón
            return
        t_key = _format_tenant_key(tenant_id)
        active_events = [
            e
            for e in self._events[t_key].values()
            if e.id not in self._deleted_ids[t_key]
            and e.salon_id == salon_id
            and not e.cancelado
            and e.id != exclude_event_id
        ]

        for other in active_events:
            other_slot = EventTimeSlot(
                fecha=other.fecha,
                hora_inicio=other.hora_inicio,
                hora_fin=other.hora_fin,
            )
            if slot.overlaps(other_slot):
                raise EventOverbookingError(
                    f"El salón ya está reservado para la fecha {fecha} en el horario indicado (conflicto con evento '{other.nombre}').",
                    context={
                        "salon_id": str(salon_id),
                        "fecha": str(fecha),
                        "conflicting_event_id": str(other.id),
                        "conflicting_event_name": other.nombre,
                    },
                )

    def list_events(
        self,
        tenant_id: str | UUID | None = None,
        estado: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        salon_id: UUID | None = None,
        area_operativa_id: int | None = None,
    ) -> list[EventoListItemOut]:
        """Lista eventos aplicando filtros de estado, rango de fechas y salón."""
        t_key = _format_tenant_key(tenant_id)
        events_map = self._events[t_key]
        deleted = self._deleted_ids[t_key]

        result: list[EventoListItemOut] = []
        for e in events_map.values():
            if e.id in deleted:
                continue
            if estado:
                st = estado.strip().upper()
                if st == "PROXIMOS":
                    if e.cancelado or e.ejecutado:
                        continue
                elif st == "FINALIZADOS":
                    if not e.ejecutado:
                        continue
                elif st == "CANCELADOS":
                    if not e.cancelado:
                        continue
                elif e.estado.upper() != st:
                    continue
            if fecha_desde and e.fecha < fecha_desde:
                continue
            if fecha_hasta and e.fecha > fecha_hasta:
                continue
            if salon_id and e.salon_id != salon_id:
                continue

            result.append(
                EventoListItemOut(
                    id=e.id,
                    nombre=e.nombre,
                    titular=e.titular,
                    tipo_evento=e.tipo_evento,
                    salon_id=e.salon_id,
                    salon_nombre=e.salon_nombre,
                    lugar=e.lugar,
                    fecha=e.fecha,
                    hora_inicio=e.hora_inicio,
                    hora_fin=e.hora_fin,
                    cantidad_personas=e.cantidad_personas,
                    estado=e.estado,
                    color=e.color,
                    ejecutado=e.ejecutado,
                    cancelado=e.cancelado,
                    encargado_id=e.encargado_id,
                    valor_publico=e.valor_publico,
                    items_count=len(e.items),
                    recetas_count=len(e.recetas),
                    combos_count=len(e.combos),
                    trabajadores_count=len(e.trabajadores),
                )
            )

        return sorted(result, key=lambda x: (x.fecha, x.hora_inicio or time.min))

    def get_event_by_id(
        self,
        tenant_id: str | UUID | None,
        event_id: UUID,
    ) -> EventoOut:
        """Obtiene un evento por su UUID o lanza EventNotFoundError."""
        t_key = _format_tenant_key(tenant_id)
        if event_id in self._deleted_ids[t_key] or event_id not in self._events[t_key]:
            raise EventNotFoundError(
                f"Evento {event_id} no encontrado en el tenant {tenant_id}.",
                context={"event_id": str(event_id), "tenant_id": str(tenant_id)},
            )
        return self._events[t_key][event_id]

    def create_event(
        self,
        tenant_id: str | UUID | None,
        data: EventoCreate,
        current_user_id: int | None = None,
    ) -> EventoOut:
        """Crea un nuevo evento con validación anti-overbooking y asignación de sub-entidades."""
        with trace_span(
            "events.create",
            attributes={
                "tenant_id": str(tenant_id),
                "salon_id": str(data.salon_id) if data.salon_id else None,
                "nombre": data.nombre,
                "fecha": str(data.fecha),
            },
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            # 1. Validación estricta anti-overbooking
            self._validate_anti_overbooking(
                tenant_id=tenant_id,
                salon_id=data.salon_id,
                fecha=data.fecha,
                hora_inicio=data.hora_inicio,
                hora_fin=data.hora_fin,
            )

            # 2. Nombre del salón para respuesta rápida
            salon_nombre: str | None = None
            if data.salon_id is not None:
                with suppress(Exception):
                    s = self._salon_service.get_salon_by_id(tenant_id, data.salon_id)
                    salon_nombre = s.nombre
                    if s.capacidad_personas and data.cantidad_personas > s.capacidad_personas:
                        logger.warning(
                            "Aforo excedido: personas=%s > capacidad=%s en salon=%s",
                            data.cantidad_personas,
                            s.capacidad_personas,
                            data.salon_id,
                        )

            event_id = uuid4()
            span_attrs["event_id"] = str(event_id)
            now = datetime.now(UTC)
            t_key = _format_tenant_key(tenant_id)

            # 3. Sub-entidades mapeadas
            items_out: list[EventoItemOut] = []
            for item in data.items:
                items_out.append(
                    EventoItemOut(
                        id=item.id or uuid4(),
                        evento_id=event_id,
                        producto_id=item.producto_id,
                        bodega_id=item.bodega_id,
                        cantidad=item.cantidad.quantize(Decimal("0.0001")),
                        costo_unitario_estimado=item.costo_unitario_estimado.quantize(Decimal("0.01")),
                        notas=item.notas,
                    )
                )

            recetas_out: list[EventoRecetaOut] = []
            for r in data.recetas:
                recetas_out.append(
                    EventoRecetaOut(
                        id=r.id or uuid4(),
                        evento_id=event_id,
                        receta_id=r.receta_id,
                        bodega_id=r.bodega_id,
                        porciones=r.porciones,
                        notas=r.notas,
                    )
                )

            combos_out: list[EventoComboOut] = []
            for c in data.combos:
                combos_out.append(
                    EventoComboOut(
                        id=c.id or uuid4(),
                        evento_id=event_id,
                        combo_id=c.combo_id,
                        bodega_id=c.bodega_id,
                        cantidad=c.cantidad,
                        notas=c.notas,
                    )
                )

            trabajadores_out: list[EventoTrabajadorOut] = []
            for tr in data.trabajadores:
                trabajadores_out.append(
                    EventoTrabajadorOut(
                        id=tr.id or uuid4(),
                        evento_id=event_id,
                        usuario_id=tr.usuario_id,
                        rol_evento=tr.rol_evento,
                        horas_asignadas=tr.horas_asignadas.quantize(Decimal("0.01")),
                    )
                )

            evento = EventoOut(
                id=event_id,
                nombre=data.nombre.strip(),
                titular=data.titular.strip() if data.titular else None,
                tipo_evento=data.tipo_evento,
                salon_id=data.salon_id,
                salon_nombre=salon_nombre,
                lugar=data.lugar,
                fecha=data.fecha,
                hora_inicio=data.hora_inicio,
                hora_fin=data.hora_fin,
                cantidad_personas=data.cantidad_personas,
                estado=data.estado.upper(),
                color=data.color,
                ejecutado=False,
                cancelado=False,
                ejecutado_at=None,
                cancelado_at=None,
                motivo_cancelacion=None,
                encargado_id=data.encargado_id,
                created_by_user_id=current_user_id,
                valor_publico=data.valor_publico.quantize(Decimal("0.01")),
                notas=data.notas,
                nota_personal=data.nota_personal,
                nota_equipo=data.nota_equipo,
                nota_visible=data.nota_visible,
                items=items_out,
                recetas=recetas_out,
                combos=combos_out,
                trabajadores=trabajadores_out,
                consumos_kardex=[],
                created_at=now,
                updated_at=now,
            )

            self._events[t_key][event_id] = evento

            _dispatch_realtime_notification(
                event_type="events.events.changed",
                tenant_id=tenant_id,
                required_permission="events.events.read",
                query_keys_to_invalidate=[["events"], ["events_faltantes"], ["events", "committed-stock"], ["events", "alerts"]],
                payload={"action": "created", "event_id": str(event_id)},
            )

            return evento

    def update_event(
        self,
        tenant_id: str | UUID | None,
        event_id: UUID,
        data: EventoUpdate,
        current_user_id: int | None = None,
    ) -> EventoOut:
        """Actualiza un evento existente. Bloqueado si ya fue ejecutado o cancelado."""
        with trace_span(
            "events.update",
            attributes={"tenant_id": str(tenant_id), "event_id": str(event_id)},
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            evento = self.get_event_by_id(tenant_id, event_id)
            if evento.salon_id:
                span_attrs["salon_id"] = str(evento.salon_id)
            if evento.ejecutado:
                raise EventAlreadyExecutedError(
                    f"El evento {event_id} ya fue ejecutado y no admite modificaciones.",
                    context={"event_id": str(event_id)},
                )
            if evento.cancelado:
                raise EventAlreadyCancelledError(
                    f"El evento {event_id} se encuentra cancelado. Debe reactivarlo antes de editarlo.",
                    context={"event_id": str(event_id)},
                )

            # Chequeo de colisión si cambia fecha, horario o salón
            new_salon_id = data.salon_id if data.salon_id is not None else evento.salon_id
            new_fecha = data.fecha if data.fecha is not None else evento.fecha
            new_hora_inicio = data.hora_inicio if data.hora_inicio is not None else evento.hora_inicio
            new_hora_fin = data.hora_fin if data.hora_fin is not None else evento.hora_fin

            self._validate_anti_overbooking(
                tenant_id=tenant_id,
                salon_id=new_salon_id,
                fecha=new_fecha,
                hora_inicio=new_hora_inicio,
                hora_fin=new_hora_fin,
                exclude_event_id=event_id,
            )

            salon_nombre = evento.salon_nombre
            if data.salon_id is not None:
                with suppress(Exception):
                    s = self._salon_service.get_salon_by_id(tenant_id, data.salon_id)
                    salon_nombre = s.nombre

            t_key = _format_tenant_key(tenant_id)

            items_out = evento.items
            if data.items is not None:
                items_out = [
                    EventoItemOut(
                        id=it.id or uuid4(),
                        evento_id=event_id,
                        producto_id=it.producto_id,
                        bodega_id=it.bodega_id,
                        cantidad=it.cantidad.quantize(Decimal("0.0001")),
                        costo_unitario_estimado=it.costo_unitario_estimado.quantize(Decimal("0.01")),
                        notas=it.notas,
                    )
                    for it in data.items
                ]

            recetas_out = evento.recetas
            if data.recetas is not None:
                recetas_out = [
                    EventoRecetaOut(
                        id=r.id or uuid4(),
                        evento_id=event_id,
                        receta_id=r.receta_id,
                        bodega_id=r.bodega_id,
                        porciones=r.porciones,
                        notas=r.notas,
                    )
                    for r in data.recetas
                ]

            combos_out = evento.combos
            if data.combos is not None:
                combos_out = [
                    EventoComboOut(
                        id=c.id or uuid4(),
                        evento_id=event_id,
                        combo_id=c.combo_id,
                        bodega_id=c.bodega_id,
                        cantidad=c.cantidad,
                        notas=c.notas,
                    )
                    for c in data.combos
                ]

            trabajadores_out = evento.trabajadores
            if data.trabajadores is not None:
                trabajadores_out = [
                    EventoTrabajadorOut(
                        id=tr.id or uuid4(),
                        evento_id=event_id,
                        usuario_id=tr.usuario_id,
                        rol_evento=tr.rol_evento,
                        horas_asignadas=tr.horas_asignadas.quantize(Decimal("0.01")),
                    )
                    for tr in data.trabajadores
                ]

            updated_event = EventoOut(
                id=event_id,
                nombre=data.nombre.strip() if data.nombre is not None else evento.nombre,
                titular=data.titular.strip() if data.titular is not None else evento.titular,
                tipo_evento=data.tipo_evento if data.tipo_evento is not None else evento.tipo_evento,
                salon_id=new_salon_id,
                salon_nombre=salon_nombre,
                lugar=data.lugar if data.lugar is not None else evento.lugar,
                fecha=new_fecha,
                hora_inicio=new_hora_inicio,
                hora_fin=new_hora_fin,
                cantidad_personas=data.cantidad_personas if data.cantidad_personas is not None else evento.cantidad_personas,
                estado=data.estado.upper() if data.estado is not None else evento.estado,
                color=data.color if data.color is not None else evento.color,
                ejecutado=evento.ejecutado,
                cancelado=evento.cancelado,
                ejecutado_at=evento.ejecutado_at,
                cancelado_at=evento.cancelado_at,
                motivo_cancelacion=evento.motivo_cancelacion,
                encargado_id=data.encargado_id if data.encargado_id is not None else evento.encargado_id,
                created_by_user_id=evento.created_by_user_id,
                valor_publico=data.valor_publico.quantize(Decimal("0.01")) if data.valor_publico is not None else evento.valor_publico,
                notas=data.notas if data.notas is not None else evento.notas,
                nota_personal=data.nota_personal if data.nota_personal is not None else evento.nota_personal,
                nota_equipo=data.nota_equipo if data.nota_equipo is not None else evento.nota_equipo,
                nota_visible=data.nota_visible if data.nota_visible is not None else evento.nota_visible,
                items=items_out,
                recetas=recetas_out,
                combos=combos_out,
                trabajadores=trabajadores_out,
                consumos_kardex=evento.consumos_kardex,
                created_at=evento.created_at,
                updated_at=datetime.now(UTC),
            )

            self._events[t_key][event_id] = updated_event

            _dispatch_realtime_notification(
                event_type="events.events.changed",
                tenant_id=tenant_id,
                required_permission="events.events.read",
                query_keys_to_invalidate=[["events"], ["events_faltantes"], ["events", "committed-stock"], ["events", "alerts"]],
                payload={"action": "updated", "event_id": str(event_id)},
            )

            return updated_event

    def delete_event(
        self,
        tenant_id: str | UUID | None,
        event_id: UUID,
    ) -> bool:
        """Elimina un evento si no ha sido ejecutado."""
        with trace_span(
            "events.delete",
            attributes={"tenant_id": str(tenant_id), "event_id": str(event_id)},
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            evento = self.get_event_by_id(tenant_id, event_id)
            if evento.salon_id:
                span_attrs["salon_id"] = str(evento.salon_id)
            if evento.ejecutado:
                raise EventAlreadyExecutedError(
                    f"No es posible eliminar el evento {event_id} porque ya fue ejecutado en Kardex.",
                    context={"event_id": str(event_id)},
                )

            t_key = _format_tenant_key(tenant_id)
            self._deleted_ids[t_key].add(event_id)

            _dispatch_realtime_notification(
                event_type="events.events.changed",
                tenant_id=tenant_id,
                required_permission="events.events.read",
                query_keys_to_invalidate=[["events"], ["events_faltantes"], ["events", "committed-stock"], ["events", "alerts"]],
                payload={"action": "deleted", "event_id": str(event_id)},
            )

            return True

    def cancel_event(
        self,
        tenant_id: str | UUID | None,
        event_id: UUID,
        motivo: str | None = None,
        current_user_id: int | None = None,
    ) -> EventoOut:
        """Cancela un evento agendado."""
        with trace_span(
            "events.cancel",
            attributes={
                "tenant_id": str(tenant_id),
                "event_id": str(event_id),
                "motivo": motivo,
            },
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            evento = self.get_event_by_id(tenant_id, event_id)
            if evento.salon_id:
                span_attrs["salon_id"] = str(evento.salon_id)
            if evento.ejecutado:
                raise EventAlreadyExecutedError(
                    f"No se puede cancelar el evento {event_id} porque ya fue ejecutado.",
                    context={"event_id": str(event_id)},
                )
            if evento.cancelado:
                raise EventAlreadyCancelledError(
                    f"El evento {event_id} ya se encuentra cancelado.",
                    context={"event_id": str(event_id)},
                )

            now = datetime.now(UTC)
            t_key = _format_tenant_key(tenant_id)

            cancelled = EventoOut(
                id=evento.id,
                nombre=evento.nombre,
                titular=evento.titular,
                tipo_evento=evento.tipo_evento,
                salon_id=evento.salon_id,
                salon_nombre=evento.salon_nombre,
                lugar=evento.lugar,
                fecha=evento.fecha,
                hora_inicio=evento.hora_inicio,
                hora_fin=evento.hora_fin,
                cantidad_personas=evento.cantidad_personas,
                estado="CANCELADO",
                color=evento.color,
                ejecutado=evento.ejecutado,
                cancelado=True,
                ejecutado_at=evento.ejecutado_at,
                cancelado_at=now,
                motivo_cancelacion=motivo,
                encargado_id=evento.encargado_id,
                created_by_user_id=evento.created_by_user_id,
                valor_publico=evento.valor_publico,
                notas=evento.notas,
                nota_personal=evento.nota_personal,
                nota_equipo=evento.nota_equipo,
                nota_visible=evento.nota_visible,
                items=evento.items,
                recetas=evento.recetas,
                combos=evento.combos,
                trabajadores=evento.trabajadores,
                consumos_kardex=evento.consumos_kardex,
                created_at=evento.created_at,
                updated_at=now,
            )

            self._events[t_key][event_id] = cancelled

            _dispatch_realtime_notification(
                event_type="events.events.changed",
                tenant_id=tenant_id,
                required_permission="events.events.read",
                query_keys_to_invalidate=[["events"], ["events_faltantes"], ["events", "committed-stock"], ["events", "alerts"]],
                payload={"action": "cancelled", "event_id": str(event_id)},
            )

            return cancelled

    def reactivate_event(
        self,
        tenant_id: str | UUID | None,
        event_id: UUID,
        current_user_id: int | None = None,
    ) -> EventoOut:
        """Reactiva un evento cancelado verificando que la franja horaria esté disponible."""
        with trace_span(
            "events.reactivate",
            attributes={"tenant_id": str(tenant_id), "event_id": str(event_id)},
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            evento = self.get_event_by_id(tenant_id, event_id)
            if evento.salon_id:
                span_attrs["salon_id"] = str(evento.salon_id)
            if evento.ejecutado:
                raise EventAlreadyExecutedError(
                    f"El evento {event_id} ya fue ejecutado.",
                    context={"event_id": str(event_id)},
                )
            if not evento.cancelado:
                raise EventStatusTransitionError(
                    f"El evento {event_id} no está cancelado, por lo que no puede ser reactivado.",
                    context={"event_id": str(event_id)},
                )

            # Verificar disponibilidad actual del salón
            self._validate_anti_overbooking(
                tenant_id=tenant_id,
                salon_id=evento.salon_id,
                fecha=evento.fecha,
                hora_inicio=evento.hora_inicio,
                hora_fin=evento.hora_fin,
                exclude_event_id=event_id,
            )

            now = datetime.now(UTC)
            t_key = _format_tenant_key(tenant_id)

            reactivated = EventoOut(
                id=evento.id,
                nombre=evento.nombre,
                titular=evento.titular,
                tipo_evento=evento.tipo_evento,
                salon_id=evento.salon_id,
                salon_nombre=evento.salon_nombre,
                lugar=evento.lugar,
                fecha=evento.fecha,
                hora_inicio=evento.hora_inicio,
                hora_fin=evento.hora_fin,
                cantidad_personas=evento.cantidad_personas,
                estado="AGENDADO",
                color=evento.color,
                ejecutado=False,
                cancelado=False,
                ejecutado_at=None,
                cancelado_at=None,
                motivo_cancelacion=None,
                encargado_id=evento.encargado_id,
                created_by_user_id=evento.created_by_user_id,
                valor_publico=evento.valor_publico,
                notas=evento.notas,
                nota_personal=evento.nota_personal,
                nota_equipo=evento.nota_equipo,
                nota_visible=evento.nota_visible,
                items=evento.items,
                recetas=evento.recetas,
                combos=evento.combos,
                trabajadores=evento.trabajadores,
                consumos_kardex=evento.consumos_kardex,
                created_at=evento.created_at,
                updated_at=now,
            )

            self._events[t_key][event_id] = reactivated

            _dispatch_realtime_notification(
                event_type="events.events.changed",
                tenant_id=tenant_id,
                required_permission="events.events.read",
                query_keys_to_invalidate=[["events"], ["events_faltantes"], ["events", "committed-stock"], ["events", "alerts"]],
                payload={"action": "reactivated", "event_id": str(event_id)},
            )

            return reactivated

    def execute_event(
        self,
        tenant_id: str | UUID | None,
        event_id: UUID,
        current_user_id: int | None = None,
    ) -> EventExecutionResultSchema:
        """
        Ejecuta transaccionalmente el evento en Kardex:
        1. Valida que no esté ejecutado ni cancelado.
        2. Descuenta del inventario los insumos directos (`CONSUMO_EVENTO`).
        3. Desglosa recetas gastronómicas y descuenta sus ingredientes.
        4. Desglosa combos comerciales (ítems directos y sub-recetas recursivas).
        5. Asienta los movimientos en `evento_consumos_kardex`.
        6. Marca el evento como ejecutado y finalizado.
        """
        with trace_span(
            "events.execute",
            attributes={"tenant_id": str(tenant_id), "event_id": str(event_id)},
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            evento = self.get_event_by_id(tenant_id, event_id)
            if evento.salon_id:
                span_attrs["salon_id"] = str(evento.salon_id)
            if evento.ejecutado:
                raise EventAlreadyExecutedError(
                    f"El evento {event_id} ya fue ejecutado previamente en Kardex.",
                    context={"event_id": str(event_id)},
                )
            if evento.cancelado:
                raise EventAlreadyCancelledError(
                    f"El evento {event_id} se encuentra cancelado y no puede ser ejecutado.",
                    context={"event_id": str(event_id)},
                )

            now = datetime.now(UTC)
            actor_id = current_user_id or 1
            consumos_out: list[EventoConsumoKardexOut] = []
            costo_total_acumulado = Decimal("0.00")

            def _register_consumption(
                prod_id: int,
                bod_id: int,
                cant: Decimal,
                ref_doc: str,
                orig_tipo: str,
                orig_id: int | None,
                costo_referencia: Decimal | None = None,
            ) -> None:
                nonlocal costo_total_acumulado
                costo_u = self._product_costs.get(prod_id, costo_referencia or Decimal("0.00"))
                try:
                    entry = self._inventory.register_movement(
                        producto_id=prod_id,
                        bodega_id=bod_id,
                        movement_type="CONSUMO_EVENTO",
                        quantity=cant,
                        unit_cost=costo_u,
                        actor_user_id=actor_id,
                        documento_referencia=ref_doc,
                        tenant_id=str(tenant_id) if tenant_id else None,
                    )
                except Exception:
                    # Fallback de compatibilidad si el inventario solo acepta CONSUMO
                    entry = self._inventory.register_movement(
                        producto_id=prod_id,
                        bodega_id=bod_id,
                        movement_type="CONSUMO",
                        quantity=cant,
                        unit_cost=costo_u,
                        actor_user_id=actor_id,
                        documento_referencia=ref_doc,
                        tenant_id=str(tenant_id) if tenant_id else None,
                    )

                kardex_ppp = getattr(entry, "costo_unitario_ppp", Decimal("0.00"))
                kardex_cost = getattr(entry, "unit_cost", Decimal("0.00"))
                if kardex_ppp > Decimal("0.00"):
                    unit_cost_ppp = kardex_ppp
                elif kardex_cost > Decimal("0.00"):
                    unit_cost_ppp = kardex_cost
                else:
                    unit_cost_ppp = costo_u

                consumo = EventoConsumoKardexOut(
                    id=uuid4(),
                    evento_id=event_id,
                    kardex_movement_id=entry.id,
                    producto_id=prod_id,
                    bodega_id=bod_id,
                    cantidad_consumida=cant,
                    costo_unitario_ppp=unit_cost_ppp,
                    origen_tipo=orig_tipo,
                    origen_id=orig_id,
                )
                consumos_out.append(consumo)
                costo_total_acumulado += (cant * unit_cost_ppp).quantize(Decimal("0.01"))

            # 1. Consumos de Ítems directos
            for item in evento.items:
                _register_consumption(
                    prod_id=item.producto_id,
                    bod_id=item.bodega_id,
                    cant=item.cantidad,
                    ref_doc=f"EVENTO-{event_id}",
                    orig_tipo="DIRECTO",
                    orig_id=None,
                    costo_referencia=item.costo_unitario_estimado,
                )

            # 2. Consumos de Recetas Gastronómicas
            for receta in evento.recetas:
                ingredients = self._recipe_specs.get(receta.receta_id, [])
                bodega_target = receta.bodega_id or 1
                for prod_id, cant_unitaria in ingredients:
                    cant_total = (cant_unitaria * Decimal(receta.porciones)).quantize(Decimal("0.0001"))
                    _register_consumption(
                        prod_id=prod_id,
                        bod_id=bodega_target,
                        cant=cant_total,
                        ref_doc=f"EVENTO-{event_id}-RECETA-{receta.receta_id}",
                        orig_tipo="RECETA",
                        orig_id=receta.receta_id,
                    )

            # 3. Consumos de Combos Comerciales (ítems directos + sub-recetas recursivas)
            for combo in evento.combos:
                bodega_target = combo.bodega_id or 1
                # 3a. Componentes directos del combo
                components = self._combo_specs.get(combo.combo_id, [])
                for prod_id, cant_unitaria in components:
                    cant_total = (cant_unitaria * Decimal(combo.cantidad)).quantize(Decimal("0.0001"))
                    _register_consumption(
                        prod_id=prod_id,
                        bod_id=bodega_target,
                        cant=cant_total,
                        ref_doc=f"EVENTO-{event_id}-COMBO-{combo.combo_id}",
                        orig_tipo="COMBO",
                        orig_id=combo.combo_id,
                    )
                # 3b. Sub-recetas contenidas en el combo
                for sub_receta_id, porc_en_combo in self._combo_recipe_specs.get(combo.combo_id, []):
                    porc_totales = porc_en_combo * combo.cantidad
                    for prod_id, cant_unitaria in self._recipe_specs.get(sub_receta_id, []):
                        cant_total = (cant_unitaria * Decimal(porc_totales)).quantize(Decimal("0.0001"))
                        _register_consumption(
                            prod_id=prod_id,
                            bod_id=bodega_target,
                            cant=cant_total,
                            ref_doc=f"EVENTO-{event_id}-COMBO-{combo.combo_id}-RECETA-{sub_receta_id}",
                            orig_tipo="COMBO",
                            orig_id=combo.combo_id,
                        )

            # 4. Actualización del evento a EJECUTADO
            t_key = _format_tenant_key(tenant_id)
            updated_event = EventoOut(
                id=evento.id,
                nombre=evento.nombre,
                titular=evento.titular,
                tipo_evento=evento.tipo_evento,
                salon_id=evento.salon_id,
                salon_nombre=evento.salon_nombre,
                lugar=evento.lugar,
                fecha=evento.fecha,
                hora_inicio=evento.hora_inicio,
                hora_fin=evento.hora_fin,
                cantidad_personas=evento.cantidad_personas,
                estado="EJECUTADO",
                color=evento.color,
                ejecutado=True,
                cancelado=False,
                ejecutado_at=now,
                cancelado_at=None,
                motivo_cancelacion=None,
                encargado_id=evento.encargado_id,
                created_by_user_id=evento.created_by_user_id,
                valor_publico=evento.valor_publico,
                notas=evento.notas,
                nota_personal=evento.nota_personal,
                nota_equipo=evento.nota_equipo,
                nota_visible=evento.nota_visible,
                items=evento.items,
                recetas=evento.recetas,
                combos=evento.combos,
                trabajadores=evento.trabajadores,
                consumos_kardex=consumos_out,
                created_at=evento.created_at,
                updated_at=now,
            )

            self._events[t_key][event_id] = updated_event

            _dispatch_realtime_notification(
                event_type="events.events.changed",
                tenant_id=tenant_id,
                required_permission="events.events.read",
                query_keys_to_invalidate=[["events"], ["inventory"], ["events_faltantes"], ["events", "committed-stock"], ["events", "alerts"]],
                payload={"action": "executed", "event_id": str(event_id)},
            )

            span_attrs["total_movimientos_kardex"] = len(consumos_out)
            span_attrs["costo_total_consumido"] = str(costo_total_acumulado)

            return EventExecutionResultSchema(
                evento_id=event_id,
                ejecutado=True,
                ejecutado_at=now,
                total_movimientos_kardex=len(consumos_out),
                costo_total_consumido=costo_total_acumulado,
                consumos=consumos_out,
            )

    def reverse_event(
        self,
        tenant_id: str | UUID | None,
        event_id: UUID,
        motivo: str,
        current_user_id: int | None = None,
    ) -> EventoReverseResultSchema:
        """
        Revierte compensatoriamente un evento previamente ejecutado en Kardex:
        1. Valida que el evento exista y esté ejecutado.
        2. Prohíbe revertir si ya fue cancelado o revertido previamente.
        3. Para cada consumo en `evento.consumos_kardex`, registra un movimiento compensatorio
           inmutable con tipo `AJUSTE_EVENTO_REVERSA`, reingresando exactamente las unidades
           deducidas al Kardex con el mismo costo PPP.
        4. Transiciona el evento a estado CANCELADO registrando el motivo y la auditoría.
        5. Emite notificación en tiempo real a Redis Pub/Sub para invalidación de caché.
        """
        with trace_span(
            "events.reversal",
            attributes={
                "tenant_id": str(tenant_id),
                "event_id": str(event_id),
                "motivo": motivo,
            },
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            evento = self.get_event_by_id(tenant_id, event_id)
            if evento.salon_id:
                span_attrs["salon_id"] = str(evento.salon_id)
            if not evento.ejecutado:
                raise EventStatusTransitionError(
                    f"No es posible revertir el evento {event_id} porque aún no ha sido ejecutado en Kardex.",
                    context={"event_id": str(event_id)},
                )
            if evento.cancelado:
                raise EventAlreadyCancelledError(
                    f"El evento {event_id} ya fue cancelado o revertido previamente.",
                    context={"event_id": str(event_id)},
                )

            clean_motivo = (motivo or "").strip()
            if not clean_motivo:
                raise EventsDomainError("Debe especificar un motivo descriptivo para revertir el evento.")

            now = datetime.now(UTC)
            actor_id = current_user_id or 1
            t_key = _format_tenant_key(tenant_id)

            total_movimientos = 0
            total_unidades = Decimal("0.0000")
            costo_total_revertido = Decimal("0.00")

            # Generación de asientos compensatorios en Kardex (Append-Only)
            for consumo in evento.consumos_kardex:
                costo_ppp = consumo.costo_unitario_ppp
                try:
                    self._inventory.register_movement(
                        producto_id=consumo.producto_id,
                        bodega_id=consumo.bodega_id,
                        movement_type="AJUSTE_EVENTO_REVERSA",
                        quantity=consumo.cantidad_consumida,
                        unit_cost=costo_ppp,
                        actor_user_id=actor_id,
                        documento_referencia=f"REVERSA-EVENTO-{event_id} | {clean_motivo}",
                        tenant_id=str(tenant_id) if tenant_id else None,
                    )
                except Exception:
                    # Fallback a AJUSTE_POSITIVO si el backend no reconoce el tipo específico
                    self._inventory.register_movement(
                        producto_id=consumo.producto_id,
                        bodega_id=consumo.bodega_id,
                        movement_type="AJUSTE_POSITIVO",
                        quantity=consumo.cantidad_consumida,
                        unit_cost=costo_ppp,
                        actor_user_id=actor_id,
                        documento_referencia=f"REVERSA-EVENTO-{event_id} | {clean_motivo}",
                        tenant_id=str(tenant_id) if tenant_id else None,
                    )
                total_movimientos += 1
                total_unidades += consumo.cantidad_consumida
                costo_total_revertido += (consumo.cantidad_consumida * costo_ppp).quantize(Decimal("0.01"))

            # Actualización del evento a CANCELADO con auditoría
            reversed_event = EventoOut(
                id=evento.id,
                nombre=evento.nombre,
                titular=evento.titular,
                tipo_evento=evento.tipo_evento,
                salon_id=evento.salon_id,
                salon_nombre=evento.salon_nombre,
                lugar=evento.lugar,
                fecha=evento.fecha,
                hora_inicio=evento.hora_inicio,
                hora_fin=evento.hora_fin,
                cantidad_personas=evento.cantidad_personas,
                estado="CANCELADO",
                color=evento.color,
                ejecutado=evento.ejecutado,
                cancelado=True,
                ejecutado_at=evento.ejecutado_at,
                cancelado_at=now,
                motivo_cancelacion=clean_motivo,
                encargado_id=evento.encargado_id,
                created_by_user_id=evento.created_by_user_id,
                valor_publico=evento.valor_publico,
                notas=evento.notas,
                nota_personal=evento.nota_personal,
                nota_equipo=evento.nota_equipo,
                nota_visible=evento.nota_visible,
                items=evento.items,
                recetas=evento.recetas,
                combos=evento.combos,
                trabajadores=evento.trabajadores,
                consumos_kardex=evento.consumos_kardex,
                created_at=evento.created_at,
                updated_at=now,
            )

            self._events[t_key][event_id] = reversed_event

            _dispatch_realtime_notification(
                event_type="events.events.changed",
                tenant_id=tenant_id,
                required_permission="events.events.read",
                query_keys_to_invalidate=[["events"], ["inventory"], ["events_faltantes"], ["events", "committed-stock"], ["events", "alerts"]],
                payload={"action": "reversed", "event_id": str(event_id), "motivo": clean_motivo},
            )

            span_attrs["total_movimientos_revertidos"] = total_movimientos
            span_attrs["costo_total_revertido"] = str(costo_total_revertido.quantize(Decimal("0.01")))

            return EventoReverseResultSchema(
                evento_id=event_id,
                revertido=True,
                revertido_at=now,
                motivo=clean_motivo,
                total_movimientos_compensatorios=total_movimientos,
                total_unidades_reingresadas=total_unidades.quantize(Decimal("0.0001")),
                costo_total_revertido=costo_total_revertido.quantize(Decimal("0.01")),
                evento=reversed_event,
            )

    def generate_minuta_csv(
        self,
        tenant_id: str | UUID | None,
        event_id: UUID,
    ) -> str:
        """
        Genera la minuta técnica de producción y requisición de bodegas en formato CSV estructurado:
        - Ficha técnica completa del evento.
        - Minuta gastronómica (recetas y preparaciones a producir).
        - Desglose de combos comerciales.
        - Requisición consolidada de bodegas (BOM completo con stock disponible y firmas).
        - Brigada asignada.
        - Acta de conformidad y entrega/recepción.
        """
        import csv
        import io

        evento = self.get_event_by_id(tenant_id, event_id)
        output = io.StringIO()
        # UTF-8 BOM para soporte directo e impecable en Microsoft Excel
        output.write("\ufeff")
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        writer.writerow(["OPPYTEC v2.0 - MINUTA TÉCNICA DE PRODUCCIÓN Y REQUISICIÓN DE EVENTOS"])
        writer.writerow(["EMISIÓN", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")])
        writer.writerow([])

        # 1. Ficha Técnica
        writer.writerow(["[1] FICHA TÉCNICA DEL EVENTO"])
        writer.writerow(["ID Evento", str(evento.id)])
        writer.writerow(["Nombre del Evento", evento.nombre])
        writer.writerow(["Titular / Cliente", evento.titular or "Sin Titular"])
        writer.writerow(["Categoría", evento.tipo_evento])
        writer.writerow(["Salón Reservado", evento.salon_nombre or "Lugar no asignado"])
        writer.writerow(["Lugar Alternativo", evento.lugar or "N/A"])
        writer.writerow(["Fecha de Realización", str(evento.fecha)])
        writer.writerow(["Horario Programado", f"{evento.hora_inicio or '--:--'} a {evento.hora_fin or '--:--'}"])
        writer.writerow(["Cantidad de Asistentes / Comensales", evento.cantidad_personas])
        writer.writerow(["Estado Operativo", evento.estado])
        writer.writerow(["Encargado Responsable ID", evento.encargado_id or "Sin asignar"])
        writer.writerow(["Presupuesto / Valor Público", f"${evento.valor_publico:,.2f}"])
        writer.writerow(["Notas Operativas", evento.notas or ""])
        writer.writerow([])

        # 2. Minuta Gastronómica
        writer.writerow(["[2] MINUTA GASTRONÓMICA (RECETAS Y PREPARACIONES A PRODUCIR)"])
        writer.writerow(["Receta ID", "Bodega Origen", "Porciones a Producir", "Notas Técnicas"])
        if evento.recetas:
            for r in evento.recetas:
                writer.writerow([r.receta_id, r.bodega_id or "General", r.porciones, r.notas or ""])
        else:
            writer.writerow(["Sin recetas asignadas", "-", "-", "-"])
        writer.writerow([])

        # 3. Combos y Promociones
        writer.writerow(["[3] COMBOS Y PROMOCIONES COMERCIALES"])
        writer.writerow(["Combo ID", "Bodega Origen", "Cantidad", "Notas"])
        if evento.combos:
            for c in evento.combos:
                writer.writerow([c.combo_id, c.bodega_id or "General", c.cantidad, c.notas or ""])
        else:
            writer.writerow(["Sin combos asignados", "-", "-", "-"])
        writer.writerow([])

        # 4. Requisición Consolidada de Bodegas (BOM Completo)
        writer.writerow(["[4] REQUISICIÓN DE INSUMOS Y MATERIAS PRIMAS (BOM TOTAL)"])
        writer.writerow(["Producto ID", "Bodega ID", "Cantidad Requerida", "Costo Unitario PPP", "Stock Disponible", "Origen / Justificación"])

        req_by_pb: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
        origin_by_pb: dict[tuple[int, int], list[str]] = defaultdict(list)

        for it in evento.items:
            req_by_pb[(it.producto_id, it.bodega_id)] += it.cantidad
            origin_by_pb[(it.producto_id, it.bodega_id)].append(f"Insumo Directo ({it.cantidad:.4f})")

        for rec in evento.recetas:
            bod_t = rec.bodega_id or 1
            for prod_id, cant_u in self._recipe_specs.get(rec.receta_id, []):
                cant_total = cant_u * Decimal(rec.porciones)
                req_by_pb[(prod_id, bod_t)] += cant_total
                origin_by_pb[(prod_id, bod_t)].append(f"Receta #{rec.receta_id} ({rec.porciones} porc)")

        for cmb in evento.combos:
            bod_t = cmb.bodega_id or 1
            for prod_id, cant_u in self._combo_specs.get(cmb.combo_id, []):
                cant_total = cant_u * Decimal(cmb.cantidad)
                req_by_pb[(prod_id, bod_t)] += cant_total
                origin_by_pb[(prod_id, bod_t)].append(f"Combo #{cmb.combo_id} ({cmb.cantidad} unid)")
            for sub_rec_id, porc_c in self._combo_recipe_specs.get(cmb.combo_id, []):
                porc_tot = porc_c * cmb.cantidad
                for prod_id, cant_u in self._recipe_specs.get(sub_rec_id, []):
                    cant_total = cant_u * Decimal(porc_tot)
                    req_by_pb[(prod_id, bod_t)] += cant_total
                    origin_by_pb[(prod_id, bod_t)].append(f"Combo #{cmb.combo_id}->Receta #{sub_rec_id}")

        if req_by_pb:
            for (p_id, b_id), cant_req in sorted(req_by_pb.items()):
                stock_act = self._get_inventory_balance(p_id, b_id)
                costo_u = self._product_costs.get(p_id, Decimal("0.00"))
                orig_desc = " + ".join(origin_by_pb[(p_id, b_id)])
                writer.writerow([
                    p_id,
                    b_id,
                    f"{cant_req:.4f}",
                    f"${costo_u:,.2f}",
                    f"{stock_act:.4f}",
                    orig_desc,
                ])
        else:
            writer.writerow(["Sin insumos requeridos", "-", "-", "-", "-", "-"])
        writer.writerow([])

        # 5. Brigada Asignada
        writer.writerow(["[5] BRIGADA OPERATIVA Y PERSONAL ASIGNADO"])
        writer.writerow(["Usuario ID", "Rol en el Evento", "Horas Programadas"])
        if evento.trabajadores:
            for tr in evento.trabajadores:
                writer.writerow([tr.usuario_id, tr.rol_evento or "Operativo", f"{tr.horas_asignadas:.2f}"])
        else:
            writer.writerow(["Sin personal asignado", "-", "-"])
        writer.writerow([])

        # 6. Acta de Conformidad
        writer.writerow(["[6] ACTA DE CONFORMIDAD Y FIRMAS"])
        writer.writerow(["Entrega Bodega (Firma y Fecha):", "____________________________________"])
        writer.writerow(["Recepción Chef / Encargado:", "____________________________________"])
        writer.writerow([])

        return output.getvalue()

    def generate_minutas_consolidated_csv(
        self,
        tenant_id: str | UUID | None,
        event_ids: list[UUID] | None = None,
    ) -> str:
        """Genera un archivo CSV consolidado con las minutas de los eventos solicitados o todos los agendados."""
        t_key = _format_tenant_key(tenant_id)
        events_map = self._events[t_key]
        deleted = self._deleted_ids[t_key]

        if event_ids:
            target_events = [events_map[eid] for eid in event_ids if eid in events_map and eid not in deleted]
        else:
            target_events = [e for e in events_map.values() if e.id not in deleted and not e.cancelado]

        if not target_events:
            return "OPPYTEC v2.0 - MINUTA DE PRODUCCION\nNo hay eventos para exportar.\n"

        parts: list[str] = []
        for ev in target_events:
            parts.append(self.generate_minuta_csv(tenant_id, ev.id))
            parts.append("\n" + "=" * 80 + "\n\n")

        return "".join(parts)

    def _get_inventory_balance(self, producto_id: int, bodega_id: int) -> Decimal:
        """Consulta el saldo de existencias admitiendo balance() o get_stock_balance()."""
        if hasattr(self._inventory, "balance"):
            return self._inventory.balance(producto_id, bodega_id)
        if hasattr(self._inventory, "get_stock_balance"):
            return self._inventory.get_stock_balance(producto_id, bodega_id)
        return Decimal("0.0000")

    def get_faltantes_analytics(
        self,
        tenant_id: str | UUID | None,
        area_operativa_id: int | None = None,
    ) -> EventFaltantesResponse:
        """
        Analítica predictiva de quiebre de stock:
        Consolida la demanda de todos los eventos agendados futuros y la compara
        contra las existencias actuales de las bodegas, generando alertas de déficit.
        """
        with trace_span(
            "events.faltantes.compute",
            attributes={
                "tenant_id": str(tenant_id),
                "area_operativa_id": area_operativa_id,
            },
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            t_key = _format_tenant_key(tenant_id)
            events_map = self._events[t_key]
            deleted = self._deleted_ids[t_key]
            today = date.today()

            demand_by_product_bodega: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0.0000"))
            affected_events: set[UUID] = set()

            for e in events_map.values():
                if e.id in deleted or e.cancelado or e.ejecutado:
                    continue
                if e.fecha < today:
                    continue

                # Demanda por items directos
                for item in e.items:
                    demand_by_product_bodega[(item.producto_id, item.bodega_id)] += item.cantidad
                    affected_events.add(e.id)

                # Demanda por recetas
                for receta in e.recetas:
                    bodega_t = receta.bodega_id or 1
                    for prod_id, cant_u in self._recipe_specs.get(receta.receta_id, []):
                        demand_by_product_bodega[(prod_id, bodega_t)] += cant_u * Decimal(receta.porciones)
                        affected_events.add(e.id)

                # Demanda por combos (ítems directos + sub-recetas recursivas)
                for combo in e.combos:
                    bodega_t = combo.bodega_id or 1
                    for prod_id, cant_u in self._combo_specs.get(combo.combo_id, []):
                        demand_by_product_bodega[(prod_id, bodega_t)] += cant_u * Decimal(combo.cantidad)
                        affected_events.add(e.id)
                    for sub_rec_id, porc_c in self._combo_recipe_specs.get(combo.combo_id, []):
                        porc_tot = porc_c * combo.cantidad
                        for prod_id, cant_u in self._recipe_specs.get(sub_rec_id, []):
                            demand_by_product_bodega[(prod_id, bodega_t)] += cant_u * Decimal(porc_tot)
                            affected_events.add(e.id)

            faltantes_items: list[EventFaltanteItemOut] = []
            for (prod_id, bod_id), cant_req in sorted(demand_by_product_bodega.items()):
                stock_actual = self._get_inventory_balance(prod_id, bod_id)
                if stock_actual < cant_req:
                    deficit = cant_req - stock_actual
                    faltantes_items.append(
                        EventFaltanteItemOut(
                            producto_id=prod_id,
                            producto_nombre=f"Producto #{prod_id}",
                            bodega_id=bod_id,
                            bodega_nombre=f"Bodega #{bod_id}",
                            cantidad_requerida=cant_req.quantize(Decimal("0.0001")),
                            stock_actual=stock_actual.quantize(Decimal("0.0001")),
                            deficit=deficit.quantize(Decimal("0.0001")),
                            unidad_medida="UN",
                        )
                    )

            span_attrs["total_faltantes"] = len(faltantes_items)
            span_attrs["eventos_afectados_count"] = len(affected_events) if faltantes_items else 0

            return EventFaltantesResponse(
                total_faltantes=len(faltantes_items),
                items=faltantes_items,
                eventos_afectados_count=len(affected_events) if faltantes_items else 0,
                generado_at=datetime.now(UTC),
            )

    def get_committed_stock_summary(
        self,
        tenant_id: str | UUID | None,
        bodega_id: int | None = None,
    ) -> CommittedStockSummaryResponse:
        """
        Calcula la demanda futura reservada por insumo sumando todos los eventos agendados futuros:
        Stock Comprometido = sum(BOM Insumos de eventos agendados futuros)
        Saldo Libre / Disponible Real = max(0, Stock Actual - Stock Comprometido)
        Retorna el desglose por producto y bodega, eventos asociados y saldo disponible real.
        """
        with trace_span(
            "events.committed_stock.compute",
            attributes={"tenant_id": str(tenant_id), "bodega_id": str(bodega_id) if bodega_id else "all"},
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            t_key = _format_tenant_key(tenant_id)
            events_map = self._events[t_key]
            deleted = self._deleted_ids[t_key]
            today = date.today()

            # Demanda agregada por (producto_id, bodega_id) -> Decimal
            demand_by_product_bodega: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0.0000"))
            # Eventos asociados por (producto_id, bodega_id) -> dict[UUID, CommittedStockEventRef]
            events_by_item: dict[tuple[int, int], dict[UUID, CommittedStockEventRef]] = defaultdict(dict)

            for e in events_map.values():
                if e.id in deleted or e.cancelado or e.ejecutado:
                    continue
                if e.fecha < today:
                    continue

                event_local_demand: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0.0000"))

                # 1. Demanda por ítems directos
                for item in e.items:
                    if bodega_id is None or item.bodega_id == bodega_id:
                        event_local_demand[(item.producto_id, item.bodega_id)] += item.cantidad

                # 2. Demanda por recetas gastronómicas
                for receta in e.recetas:
                    bodega_t = receta.bodega_id or 1
                    if bodega_id is None or bodega_t == bodega_id:
                        for prod_id, cant_u in self._recipe_specs.get(receta.receta_id, []):
                            event_local_demand[(prod_id, bodega_t)] += cant_u * Decimal(receta.porciones)

                # 3. Demanda por combos y promociones (ítems directos + sub-recetas recursivas)
                for combo in e.combos:
                    bodega_t = combo.bodega_id or 1
                    if bodega_id is None or bodega_t == bodega_id:
                        for prod_id, cant_u in self._combo_specs.get(combo.combo_id, []):
                            event_local_demand[(prod_id, bodega_t)] += cant_u * Decimal(combo.cantidad)
                        for sub_rec_id, porc_c in self._combo_recipe_specs.get(combo.combo_id, []):
                            porc_tot = porc_c * combo.cantidad
                            for prod_id, cant_u in self._recipe_specs.get(sub_rec_id, []):
                                event_local_demand[(prod_id, bodega_t)] += cant_u * Decimal(porc_tot)

                # Acumular la demanda local del evento al mapa consolidado
                for (p_id, b_id), qty in event_local_demand.items():
                    if qty > Decimal("0.0000"):
                        demand_by_product_bodega[(p_id, b_id)] += qty
                        events_by_item[(p_id, b_id)][e.id] = CommittedStockEventRef(
                            evento_id=e.id,
                            evento_nombre=e.nombre,
                            fecha=e.fecha,
                            hora_inicio=e.hora_inicio,
                            cantidad=qty.quantize(Decimal("0.0001")),
                        )

            items_out: list[CommittedStockItemOut] = []
            for (prod_id, bod_id), stock_comprometido in sorted(demand_by_product_bodega.items()):
                stock_actual = self._get_inventory_balance(prod_id, bod_id)
                # Definición matemática: Stock Disponible Real = max(0, Stock Actual - Stock Comprometido)
                saldo_neto = stock_actual - stock_comprometido
                stock_disponible_real = max(Decimal("0.0000"), saldo_neto)

                asoc_events = list(events_by_item[(prod_id, bod_id)].values())
                asoc_events.sort(key=lambda ev: (ev.fecha, ev.hora_inicio or time.min))

                items_out.append(
                    CommittedStockItemOut(
                        producto_id=prod_id,
                        producto_nombre=f"Producto #{prod_id}",
                        bodega_id=bod_id,
                        bodega_nombre=f"Bodega #{bod_id}",
                        stock_actual=stock_actual.quantize(Decimal("0.0001")),
                        stock_comprometido=stock_comprometido.quantize(Decimal("0.0001")),
                        stock_disponible_real=stock_disponible_real.quantize(Decimal("0.0001")),
                        unidad_medida="UN",
                        eventos=asoc_events,
                    )
                )

            span_attrs["total_items"] = len(items_out)

            return CommittedStockSummaryResponse(
                total_items=len(items_out),
                items=items_out,
                generado_at=datetime.now(UTC),
            )

    def get_event_alerts(
        self,
        tenant_id: str | UUID | None,
        reference_datetime: datetime | None = None,
    ) -> list[EventAlertOut]:
        """
        Genera alertas operativas para eventos con riesgo de desabastecimiento:
        - CRITICAL: Evento agendado en < 48 horas con faltantes de stock o insumos en quiebre.
        - WARNING: Evento agendado en los próximos 14 días con quiebre proyectado o stock insuficiente.
        Retorna la lista enriquecida con severidad, horas/días restantes, insumos en déficit y nombre del evento.
        """
        with trace_span(
            "events.alerts.get",
            attributes={"tenant_id": str(tenant_id)},
            tracer_name="oppytec.events.services",
        ) as span_attrs:
            t_key = _format_tenant_key(tenant_id)
            events_map = self._events[t_key]
            deleted = self._deleted_ids[t_key]

            ref_dt = reference_datetime or datetime.now(UTC)
            ref_is_tz = ref_dt.tzinfo is not None

            active_events = [
                e for e in events_map.values()
                if e.id not in deleted and not e.cancelado and not e.ejecutado
            ]

            # Ordenar cronológicamente para evaluar consumo FIFO de eventos
            active_events.sort(key=lambda ev: (ev.fecha, ev.hora_inicio, ev.id))

            # Existencias proyectadas dinámicas a medida que se atienden los eventos
            projected_stock: dict[tuple[int, int], Decimal] = {}
            alerts: list[EventAlertOut] = []

            for e in active_events:
                event_dt = datetime.combine(e.fecha, e.hora_inicio)
                if ref_is_tz:
                    event_dt = event_dt.replace(tzinfo=ref_dt.tzinfo)

                time_delta = event_dt - ref_dt
                total_seconds = time_delta.total_seconds()
                horas_restantes = Decimal(str(round(total_seconds / 3600.0, 2)))
                dias_restantes = int(total_seconds // 86400)

                # Ventana de evaluación: próximos 14 días (336 horas)
                # Eventos con más de 2 días en el pasado sin ejecutar se omiten
                if total_seconds > 14 * 86400 or total_seconds < -86400 * 2:
                    continue

                event_demands: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0.0000"))

                # 1. Ítems directos
                for item in e.items:
                    event_demands[(item.producto_id, item.bodega_id)] += item.cantidad

                # 2. Recetas
                for receta in e.recetas:
                    bodega_t = receta.bodega_id or 1
                    for prod_id, cant_u in self._recipe_specs.get(receta.receta_id, []):
                        event_demands[(prod_id, bodega_t)] += cant_u * Decimal(receta.porciones)

                # 3. Combos
                for combo in e.combos:
                    bodega_t = combo.bodega_id or 1
                    for prod_id, cant_u in self._combo_specs.get(combo.combo_id, []):
                        event_demands[(prod_id, bodega_t)] += cant_u * Decimal(combo.cantidad)
                    for sub_rec_id, porc_c in self._combo_recipe_specs.get(combo.combo_id, []):
                        porc_tot = porc_c * combo.cantidad
                        for prod_id, cant_u in self._recipe_specs.get(sub_rec_id, []):
                            event_demands[(prod_id, bodega_t)] += cant_u * Decimal(porc_tot)

                deficits: list[EventAlertInsumoDeficit] = []
                for (p_id, b_id), cant_req in sorted(event_demands.items()):
                    stock_actual_fisico = self._get_inventory_balance(p_id, b_id)
                    if (p_id, b_id) not in projected_stock:
                        projected_stock[(p_id, b_id)] = stock_actual_fisico

                    saldo_disponible = projected_stock[(p_id, b_id)]

                    if saldo_disponible < cant_req:
                        faltante = cant_req - max(Decimal("0.0000"), saldo_disponible)
                        deficits.append(
                            EventAlertInsumoDeficit(
                                producto_id=p_id,
                                producto_nombre=f"Producto #{p_id}",
                                bodega_id=b_id,
                                bodega_nombre=f"Bodega #{b_id}",
                                cantidad_requerida=cant_req.quantize(Decimal("0.0001")),
                                stock_actual=stock_actual_fisico.quantize(Decimal("0.0001")),
                                deficit=faltante.quantize(Decimal("0.0001")),
                                unidad_medida="UN",
                            )
                        )
                        projected_stock[(p_id, b_id)] = saldo_disponible - cant_req
                    else:
                        projected_stock[(p_id, b_id)] = saldo_disponible - cant_req

                if deficits:
                    # Clasificación de severidad:
                    # CRITICAL: programado en < 48 horas
                    # WARNING: programado entre 48h y 14 días
                    severidad = "CRITICAL" if total_seconds < 48 * 3600 else "WARNING"

                    horas_display = max(Decimal("0.00"), horas_restantes)
                    dias_display = max(0, dias_restantes)

                    alerts.append(
                        EventAlertOut(
                            alerta_id=f"ALERT-EVT-{e.id}",
                            evento_id=e.id,
                            evento_nombre=e.nombre,
                            fecha_evento=e.fecha,
                            hora_inicio=e.hora_inicio,
                            severidad=severidad,
                            horas_restantes=horas_display,
                            dias_restantes=dias_display,
                            total_insumos_deficit=len(deficits),
                            insumos_deficit=deficits,
                            mensaje=(
                                f"Evento '{e.nombre}' programado para el {e.fecha.isoformat()} a las "
                                f"{e.hora_inicio.strftime('%H:%M')} ({horas_display}h restantes, severidad {severidad}) "
                                f"presenta déficit en {len(deficits)} insumo(s)."
                            ),
                            generado_at=ref_dt,
                        )
                    )

            severity_order = {"CRITICAL": 0, "WARNING": 1}
            alerts.sort(key=lambda a: (severity_order.get(a.severidad, 99), a.horas_restantes))
            span_attrs["total_alerts"] = len(alerts)

            return alerts


__all__ = [
    "EventService",
    "SalonService",
]
