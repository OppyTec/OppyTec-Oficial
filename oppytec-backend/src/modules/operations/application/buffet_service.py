"""
oppytec-backend/src/modules/operations/application/buffet_service.py
Servicio de aplicación transaccional de Buffet Inteligente:
apertura, actualización en vivo de estaciones, costeo por Pax y liquidación a Kardex.
Cumple Regla de Oro Inviolable:
- Cero float, solo Decimal e int.
- Cero updates directos a stock sin asiento previo en Kardex.
- Integración con calculate_buffet_pax_cost.
- Eventos en tiempo real mediante get_realtime_publisher().
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import logging
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from opentelemetry import trace

from src.core.exceptions import (
    CrossTenantAccessError,
    DomainValidationError,
    ResourceNotFoundError,
)
from src.core.observability import get_tenant_telemetry_context, trace_span
from src.core.realtime.router import get_realtime_publisher
from src.core.realtime.schemas import RealtimeEventEnvelope
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.operations.domain.consumption_math import (
    BuffetPaxCost,
    PaxCount,
    calculate_buffet_pax_cost,
)

logger = logging.getLogger("oppytec.operations.buffet")
tracer = trace.get_tracer("oppytec.operations.buffet")


@dataclass
class BuffetSessionItemDTO:
    """Detalle de consumo, merma y sobrante de ítems por estación."""

    id: int
    station_id: int
    session_id: int
    tipo_item: str  # PRODUCTO | RECETA
    item_id: int
    cantidad_montada: Decimal
    cantidad_sobrante: Decimal
    cantidad_merma: Decimal
    cantidad_neta_consumida: Decimal
    costo_unitario_ppp: Decimal
    costo_total: Decimal


@dataclass
class BuffetStationDTO:
    """Estación de montaje dentro de una sesión de Buffet."""

    id: int
    session_id: int
    nombre: str
    orden: int
    peso_inicial_kg: Decimal = Decimal("0.0000")
    peso_sobrante_kg: Decimal = Decimal("0.0000")
    items: list[BuffetSessionItemDTO] = field(default_factory=list)


@dataclass
class BuffetSessionDTO:
    """Sesión activa o cerrada de servicio de Buffet."""

    id: int
    bodega_id: int
    usuario_creador_id: int
    tipo_servicio: str  # DESAYUNO | ALMUERZO | BRUNCH | EVENTO
    estado: str  # ACTIVA | CERRADA | CONCILIADA
    costo_total_montaje: Decimal = Decimal("0.00")
    valor_sobrante_reutilizable: Decimal = Decimal("0.00")
    costo_neto_pax: Decimal = Decimal("0.00")
    pax_comensales: int = 0
    area_operativa_id: int | None = None
    template_id: int | None = None
    stations: list[BuffetStationDTO] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None
    tenant_id: str | None = None


@dataclass
class BuffetTemplateDTO:
    """Plantilla de montaje de Buffet."""

    id: int
    nombre: str
    comensales_estimados: int = 100
    descripcion: str | None = None
    estaciones_json: list[dict[str, Any]] = field(default_factory=list)
    is_system: bool = False
    is_public: bool = True
    tenant_id: str | None = None


class BuffetService:
    """
    Servicio de aplicación transaccional de Buffet Inteligente.
    Gestiona el ciclo de vida de sesiones y su conciliación contable a Kardex.
    """

    def __init__(self, inventory: InventoryService) -> None:
        self._inventory = inventory
        self._sessions: dict[int, BuffetSessionDTO] = {}
        self._templates: dict[int, BuffetTemplateDTO] = {}
        self._next_session_id: int = 1
        self._next_station_id: int = 1
        self._next_item_id: int = 1
        self._next_template_id: int = 1

    def reset(self) -> None:
        """Limpia el estado en memoria para aislamiento de pruebas unitarias."""
        self._sessions.clear()
        self._templates.clear()
        self._next_session_id = 1
        self._next_station_id = 1
        self._next_item_id = 1
        self._next_template_id = 1

    @staticmethod
    def _parse_optional_uuid(val: str | None) -> UUID | None:
        if not val:
            return None
        try:
            return UUID(str(val))
        except Exception:
            return None

    def _publish_event(
        self,
        event_type: str,
        session: BuffetSessionDTO,
        holding_id: str | None = None,
    ) -> None:
        with suppress(Exception):
            publisher = get_realtime_publisher()
            import asyncio
            coro = publisher.publish_event(
                RealtimeEventEnvelope(
                    event_type=event_type,
                    holding_id=self._parse_optional_uuid(holding_id),
                    tenant_id=self._parse_optional_uuid(session.tenant_id),
                    target_bodega_id=session.bodega_id,
                    required_permission="consumption.buffet.manage",
                    query_keys_to_invalidate=[["buffet", "sessions"]],
                    payload={
                        "session_id": session.id,
                        "estado": session.estado,
                        "tipo_servicio": session.tipo_servicio,
                    },
                )
            )
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
            except RuntimeError:
                asyncio.run(coro)

    def start_buffet_session(
        self,
        *,
        bodega_id: int,
        usuario_creador_id: int,
        tipo_servicio: str = "DESAYUNO",
        area_operativa_id: int | None = None,
        template_id: int | None = None,
        estaciones: Sequence[dict[str, Any]] | None = None,
        tenant_id: str | None = None,
        holding_id: str | None = None,
    ) -> BuffetSessionDTO:
        """Abre una nueva sesión de buffet con estaciones de montaje iniciales."""
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id

        session_id = self._next_session_id
        self._next_session_id += 1

        stations_dtos: list[BuffetStationDTO] = []
        total_montaje = Decimal("0.00")

        if estaciones:
            for st in estaciones:
                st_id = self._next_station_id
                self._next_station_id += 1
                nombre = str(st.get("nombre", f"Estación {st_id}"))
                orden = int(st.get("orden", 0))
                peso_ini = Decimal(str(st.get("peso_inicial_kg", "0.0000")))

                items_dtos: list[BuffetSessionItemDTO] = []
                for it in st.get("items", []):
                    it_id = self._next_item_id
                    self._next_item_id += 1
                    t_item = str(it.get("tipo_item", "PRODUCTO")).upper()
                    prod_id = int(it["item_id"])
                    c_mont = Decimal(str(it.get("cantidad_montada", "0.0000")))
                    c_sob = Decimal(str(it.get("cantidad_sobrante", "0.0000")))
                    c_mer = Decimal(str(it.get("cantidad_merma", "0.0000")))
                    c_neta = max(Decimal(0), c_mont - c_sob - c_mer)
                    u_cost = Decimal(str(it.get("costo_unitario_ppp", "0.00")))
                    cost_tot = c_mont * u_cost
                    total_montaje += cost_tot

                    item_dto = BuffetSessionItemDTO(
                        id=it_id,
                        station_id=st_id,
                        session_id=session_id,
                        tipo_item=t_item,
                        item_id=prod_id,
                        cantidad_montada=c_mont,
                        cantidad_sobrante=c_sob,
                        cantidad_merma=c_mer,
                        cantidad_neta_consumida=c_neta,
                        costo_unitario_ppp=u_cost,
                        costo_total=cost_tot,
                    )
                    items_dtos.append(item_dto)

                station_dto = BuffetStationDTO(
                    id=st_id,
                    session_id=session_id,
                    nombre=nombre,
                    orden=orden,
                    peso_inicial_kg=peso_ini,
                    items=items_dtos,
                )
                stations_dtos.append(station_dto)

        session = BuffetSessionDTO(
            id=session_id,
            bodega_id=bodega_id,
            usuario_creador_id=usuario_creador_id,
            tipo_servicio=tipo_servicio,
            estado="ACTIVA",
            costo_total_montaje=total_montaje,
            area_operativa_id=area_operativa_id,
            template_id=template_id,
            stations=stations_dtos,
            tenant_id=resolved_tenant,
        )
        self._sessions[session_id] = session
        self._publish_event("buffet.session_changed", session, holding_id=holding_id)
        return session

    def list_buffet_sessions(
        self,
        *,
        bodega_id: int | None = None,
        estado: str | None = None,
        tenant_id: str | None = None,
    ) -> list[BuffetSessionDTO]:
        """Lista sesiones de buffet filtradas por bodega y estado."""
        results = list(self._sessions.values())
        if tenant_id:
            results = [s for s in results if s.tenant_id == tenant_id]
        if bodega_id is not None:
            results = [s for s in results if s.bodega_id == bodega_id]
        if estado is not None:
            results = [s for s in results if s.estado == estado]
        results.sort(key=lambda s: s.created_at, reverse=True)
        return results

    def get_buffet_session_detail(
        self,
        session_id: int,
        tenant_id: str | None = None,
    ) -> BuffetSessionDTO:
        """Detalle completo de una sesión de buffet."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ResourceNotFoundError(f"Buffet session {session_id} not found")
        if tenant_id and session.tenant_id and session.tenant_id != tenant_id:
            raise CrossTenantAccessError(f"Cross-tenant access denied to session {session_id}")
        return session

    def update_buffet_items(
        self,
        session_id: int,
        *,
        stations_data: Sequence[dict[str, Any]],
        tenant_id: str | None = None,
        holding_id: str | None = None,
    ) -> BuffetSessionDTO:
        """
        Actualiza en vivo el montaje, sobrantes y mermas de las estaciones de una sesión activa.
        """
        session = self.get_buffet_session_detail(session_id, tenant_id=tenant_id)
        if session.estado == "CONCILIADA":
            raise DomainValidationError("Cannot update items of an already reconciled buffet session")

        station_map = {st.id: st for st in session.stations}
        total_montaje = Decimal("0.00")

        for st_upd in stations_data:
            st_id = int(st_upd["station_id"])
            if st_id not in station_map:
                continue
            station = station_map[st_id]
            if "peso_sobrante_kg" in st_upd and st_upd["peso_sobrante_kg"] is not None:
                station.peso_sobrante_kg = Decimal(str(st_upd["peso_sobrante_kg"]))

            items_input = st_upd.get("items", [])
            existing_items_map = {it.item_id: it for it in station.items}

            for it_upd in items_input:
                prod_id = int(it_upd["item_id"])
                c_mont = Decimal(str(it_upd.get("cantidad_montada", "0.0000")))
                c_sob = Decimal(str(it_upd.get("cantidad_sobrante", "0.0000")))
                c_mer = Decimal(str(it_upd.get("cantidad_merma", "0.0000")))
                c_neta = max(Decimal(0), c_mont - c_sob - c_mer)
                u_cost = Decimal(str(it_upd.get("costo_unitario_ppp", "0.00")))
                cost_tot = c_mont * u_cost

                if prod_id in existing_items_map:
                    it_obj = existing_items_map[prod_id]
                    it_obj.cantidad_montada = c_mont
                    it_obj.cantidad_sobrante = c_sob
                    it_obj.cantidad_merma = c_mer
                    it_obj.cantidad_neta_consumida = c_neta
                    it_obj.costo_unitario_ppp = u_cost
                    it_obj.costo_total = cost_tot
                else:
                    new_it = BuffetSessionItemDTO(
                        id=self._next_item_id,
                        station_id=st_id,
                        session_id=session_id,
                        tipo_item=str(it_upd.get("tipo_item", "PRODUCTO")).upper(),
                        item_id=prod_id,
                        cantidad_montada=c_mont,
                        cantidad_sobrante=c_sob,
                        cantidad_merma=c_mer,
                        cantidad_neta_consumida=c_neta,
                        costo_unitario_ppp=u_cost,
                        costo_total=cost_tot,
                    )
                    self._next_item_id += 1
                    station.items.append(new_it)

        # Recalcular costo total de montaje de la sesión
        for st in session.stations:
            for it in st.items:
                total_montaje += it.costo_total

        session.costo_total_montaje = total_montaje
        self._publish_event("buffet.session_changed", session, holding_id=holding_id)
        return session

    def finalize_buffet_session(
        self,
        session_id: int,
        *,
        pax: int,
        leftover_reusable_value: Decimal = Decimal("0.00"),
        actor_user_id: int,
        tenant_id: str | None = None,
        holding_id: str | None = None,
    ) -> BuffetSessionDTO:
        """
        Liquida y concilia contablemente la sesión de buffet:
        1. Valida comensales (pax > 0).
        2. Costea con calculate_buffet_pax_cost(total_cost, pax, leftover).
        3. Registra consumos netos y mermas en Kardex.
        4. Transiciona sesión a 'CONCILIADA'.
        """
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id
        with trace_span(
            "buffet.session.finalize",
            attributes={
                "tenant_id": resolved_tenant or "",
                "session_id": session_id,
                "pax": pax,
                "actor_user_id": actor_user_id,
            },
            tracer_name="oppytec.operations.buffet",
        ):
            session = self.get_buffet_session_detail(session_id, tenant_id=tenant_id)
            if session.estado == "CONCILIADA":
                raise DomainValidationError("Buffet session is already finalized and reconciled")

            if pax <= 0:
                raise DomainValidationError("pax must be strictly positive for buffet reconciliation")

            # Calcular costo unitario neto por comensal
            cost_per_pax = calculate_buffet_pax_cost(
                total_montaje_cost=session.costo_total_montaje,
                pax=pax,
                leftover_reusable_value=leftover_reusable_value,
            )

            # Impactar Kardex por cada ítem consumido o mermado
            for st in session.stations:
                for it in st.items:
                    if it.cantidad_neta_consumida > Decimal(0):
                        self._inventory.register_movement(
                            producto_id=it.item_id,
                            bodega_id=session.bodega_id,
                            movement_type="CONSUMO",
                            quantity=it.cantidad_neta_consumida,
                            unit_cost=it.costo_unitario_ppp,
                            actor_user_id=actor_user_id,
                            documento_referencia=f"BUFFET_CONSUMO:{session.id}",
                            tenant_id=tenant_id or session.tenant_id,
                        )
                    if it.cantidad_merma > Decimal(0):
                        self._inventory.register_movement(
                            producto_id=it.item_id,
                            bodega_id=session.bodega_id,
                            movement_type="MERMA",
                            quantity=it.cantidad_merma,
                            unit_cost=it.costo_unitario_ppp,
                            actor_user_id=actor_user_id,
                            documento_referencia=f"BUFFET_MERMA:{session.id}",
                            tenant_id=tenant_id or session.tenant_id,
                        )

            session.pax_comensales = pax
            session.valor_sobrante_reutilizable = leftover_reusable_value
            session.costo_neto_pax = cost_per_pax.value
            session.estado = "CONCILIADA"
            session.closed_at = datetime.now(UTC)

            self._publish_event("buffet.session_changed", session, holding_id=holding_id)
            return session

    # =========================================================================
    # CRUD de Buffet Templates
    # =========================================================================

    def create_buffet_template(
        self,
        *,
        nombre: str,
        comensales_estimados: int = 100,
        descripcion: str | None = None,
        estaciones_json: list[dict[str, Any]] | None = None,
        is_system: bool = False,
        is_public: bool = True,
        tenant_id: str | None = None,
    ) -> BuffetTemplateDTO:
        """Crea una plantilla de estaciones de buffet."""
        tid = self._next_template_id
        self._next_template_id += 1

        tmpl = BuffetTemplateDTO(
            id=tid,
            nombre=nombre,
            comensales_estimados=comensales_estimados,
            descripcion=descripcion,
            estaciones_json=estaciones_json or [],
            is_system=is_system,
            is_public=is_public,
            tenant_id=tenant_id,
        )
        self._templates[tid] = tmpl
        return tmpl

    def list_buffet_templates(self, tenant_id: str | None = None) -> list[BuffetTemplateDTO]:
        """Lista plantillas de buffet disponibles."""
        results: list[BuffetTemplateDTO] = []
        for t in self._templates.values():
            if tenant_id and t.tenant_id and t.tenant_id != tenant_id and not t.is_public:
                continue
            results.append(t)
        return results

    def get_buffet_template(self, template_id: int, tenant_id: str | None = None) -> BuffetTemplateDTO:
        """Obtiene una plantilla de buffet por ID."""
        tmpl = self._templates.get(template_id)
        if tmpl is None:
            raise ResourceNotFoundError(f"Buffet template {template_id} not found")
        if tenant_id and tmpl.tenant_id and tmpl.tenant_id != tenant_id and not tmpl.is_public:
            raise CrossTenantAccessError("Cross-tenant buffet template access denied")
        return tmpl

    def update_buffet_template(
        self,
        template_id: int,
        *,
        nombre: str | None = None,
        comensales_estimados: int | None = None,
        descripcion: str | None = None,
        estaciones_json: list[dict[str, Any]] | None = None,
        is_public: bool | None = None,
        tenant_id: str | None = None,
    ) -> BuffetTemplateDTO:
        """Actualiza una plantilla de buffet."""
        tmpl = self.get_buffet_template(template_id, tenant_id=tenant_id)
        if nombre is not None:
            tmpl.nombre = nombre
        if comensales_estimados is not None:
            tmpl.comensales_estimados = comensales_estimados
        if descripcion is not None:
            tmpl.descripcion = descripcion
        if estaciones_json is not None:
            tmpl.estaciones_json = estaciones_json
        if is_public is not None:
            tmpl.is_public = is_public
        return tmpl

    def delete_buffet_template(self, template_id: int, tenant_id: str | None = None) -> None:
        """Elimina una plantilla de buffet."""
        tmpl = self.get_buffet_template(template_id, tenant_id=tenant_id)
        del self._templates[tmpl.id]
