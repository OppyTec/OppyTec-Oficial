"""
oppytec-backend/src/modules/operations/application/voice_kitchen_service.py
Servicio de aplicación para Cocina por Voz / Manos Libres.
Permite listar estaciones, registrar transcripciones de pedidos verbales,
confirmar pedidos ejecutándolos a través de ConsumptionService y descartar errores.
Cumple Regla de Oro Inviolable:
- Cero float, solo Decimal e int.
- Ejecución de consumo mediante ConsumptionService con impacto en Kardex.
- Emisión de evento WebSocket en tiempo real 'voice.order_pending'.
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
from src.modules.operations.application.consumption_service import ConsumptionService

logger = logging.getLogger("oppytec.operations.voice")
tracer = trace.get_tracer("oppytec.operations.voice")


@dataclass
class VoiceStationDTO:
    """Estación de captura de voz (cocina, barra, pastelería)."""

    id: int
    nombre_estacion: str
    voice_command: str
    area_operativa_id: int | None = None
    usuario_asignado_id: int | None = None
    is_active: bool = True
    tenant_id: str | None = None


@dataclass
class VoiceOrderLogDTO:
    """Bitácora de transcripción fonética y procesamiento de orden por voz."""

    id: int
    station_id: int
    texto_transcrito: str
    accion_detectada: str  # CONSUMO | MERMA
    confianza_ia: Decimal
    items_interpretados_json: list[dict[str, Any]]
    estado: str  # PENDIENTE | CONFIRMADO | RECHAZADO | EJECUTADO
    consumption_record_id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tenant_id: str | None = None


class VoiceKitchenService:
    """
    Servicio de aplicación para órdenes por voz manos libres.
    Integra con ConsumptionService para descontar inventario en Kardex al confirmar.
    """

    def __init__(self, consumption_service: ConsumptionService) -> None:
        self._consumption = consumption_service
        self._stations: dict[int, VoiceStationDTO] = {}
        self._orders: dict[int, VoiceOrderLogDTO] = {}
        self._next_station_id: int = 1
        self._next_order_id: int = 1

    def reset(self) -> None:
        """Limpia el estado en memoria para aislamiento de pruebas unitarias."""
        self._stations.clear()
        self._orders.clear()
        self._next_station_id = 1
        self._next_order_id = 1

    @staticmethod
    def _parse_optional_uuid(val: str | None) -> UUID | None:
        if not val:
            return None
        try:
            return UUID(str(val))
        except Exception:
            return None

    def create_voice_station(
        self,
        *,
        nombre_estacion: str,
        voice_command: str,
        area_operativa_id: int | None = None,
        usuario_asignado_id: int | None = None,
        tenant_id: str | None = None,
    ) -> VoiceStationDTO:
        """Crea y registra una estación de voz operativa."""
        st_id = self._next_station_id
        self._next_station_id += 1

        st = VoiceStationDTO(
            id=st_id,
            nombre_estacion=nombre_estacion,
            voice_command=voice_command,
            area_operativa_id=area_operativa_id,
            usuario_asignado_id=usuario_asignado_id,
            is_active=True,
            tenant_id=tenant_id,
        )
        self._stations[st_id] = st
        return st

    def list_voice_stations(
        self,
        *,
        area_operativa_id: int | None = None,
        tenant_id: str | None = None,
    ) -> list[VoiceStationDTO]:
        """Lista estaciones de cocina/barra activas."""
        results = [s for s in self._stations.values() if s.is_active]
        if tenant_id:
            results = [s for s in results if s.tenant_id == tenant_id]
        if area_operativa_id is not None:
            results = [s for s in results if s.area_operativa_id == area_operativa_id]
        return results

    def get_voice_station(self, station_id: int, tenant_id: str | None = None) -> VoiceStationDTO:
        """Obtiene una estación de voz por su ID."""
        station = self._stations.get(station_id)
        if station is None:
            raise ResourceNotFoundError(f"Voice station {station_id} not found")
        if tenant_id and station.tenant_id and station.tenant_id != tenant_id:
            raise CrossTenantAccessError("Cross-tenant voice station access denied")
        return station

    def register_voice_order(
        self,
        *,
        station_id: int,
        texto_transcrito: str,
        accion_detectada: str = "CONSUMO",
        confianza_ia: Decimal = Decimal("0.9500"),
        items_interpretados: Sequence[dict[str, Any]] | None = None,
        tenant_id: str | None = None,
        holding_id: str | None = None,
    ) -> VoiceOrderLogDTO:
        """
        Registra una transcripción verbal y análisis NLU en estado PENDIENTE.
        Emite evento 'voice.order_pending' por WebSocket.
        """
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id
        with trace_span(
            "voice.order.register",
            attributes={
                "tenant_id": resolved_tenant or "",
                "station_id": station_id,
                "confidence_score": float(confianza_ia),
                "action": accion_detectada,
            },
            tracer_name="oppytec.operations.voice",
        ):
            station = self.get_voice_station(station_id, tenant_id=tenant_id)
            order_id = self._next_order_id
            self._next_order_id += 1

            order = VoiceOrderLogDTO(
                id=order_id,
                station_id=station.id,
                texto_transcrito=texto_transcrito,
                accion_detectada=accion_detectada,
                confianza_ia=confianza_ia,
                items_interpretados_json=list(items_interpretados or []),
                estado="PENDIENTE",
                tenant_id=tenant_id or station.tenant_id,
            )
            self._orders[order_id] = order

            # Emitir evento tiempo real
            with suppress(Exception):
                publisher = get_realtime_publisher()
                import asyncio
                coro = publisher.publish_event(
                    RealtimeEventEnvelope(
                        event_type="voice.order_pending",
                        holding_id=self._parse_optional_uuid(holding_id),
                        tenant_id=self._parse_optional_uuid(order.tenant_id),
                        required_permission="consumption.handsfree.use",
                        query_keys_to_invalidate=[["voice", "orders"]],
                        payload={
                            "order_id": order.id,
                            "station_id": station.id,
                            "texto_transcrito": order.texto_transcrito,
                            "accion_detectada": order.accion_detectada,
                        },
                    )
                )
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(coro)
                except RuntimeError:
                    asyncio.run(coro)

            return order

    def get_voice_order(self, order_id: int, tenant_id: str | None = None) -> VoiceOrderLogDTO:
        """Obtiene el log de una orden de voz."""
        order = self._orders.get(order_id)
        if order is None:
            raise ResourceNotFoundError(f"Voice order {order_id} not found")
        if tenant_id and order.tenant_id and order.tenant_id != tenant_id:
            raise CrossTenantAccessError("Cross-tenant voice order access denied")
        return order

    def confirm_voice_order(
        self,
        order_id: int,
        *,
        bodega_id: int,
        actor_user_id: int,
        tenant_id: str | None = None,
        holding_id: str | None = None,
    ) -> VoiceOrderLogDTO:
        """
        Confirma y ejecuta el consumo verbal hacia ConsumptionService.
        Descuenta inventario en Kardex y actualiza la orden a 'EJECUTADO'.
        """
        resolved_tenant = tenant_id or get_tenant_telemetry_context().tenant_id
        with trace_span(
            "voice.order.confirm",
            attributes={
                "tenant_id": resolved_tenant or "",
                "order_id": order_id,
                "bodega_id": bodega_id,
                "actor_user_id": actor_user_id,
            },
            tracer_name="oppytec.operations.voice",
        ):
            order = self.get_voice_order(order_id, tenant_id=tenant_id)
            if order.estado != "PENDIENTE":
                raise DomainValidationError(f"Voice order {order_id} is not in PENDIENTE state (current: {order.estado})")

            station = self._stations.get(order.station_id)
            area_id = station.area_operativa_id if station else None

            if order.items_interpretados_json:
                consumption_record = self._consumption.process_batch_consumption(
                    bodega_id=bodega_id,
                    usuario_id=actor_user_id,
                    items=order.items_interpretados_json,
                    tipo_origen="MANOS_LIBRES_VOZ",
                    area_operativa_id=area_id,
                    notas=f"Orden verbal #{order.id}: {order.texto_transcrito}",
                    tenant_id=tenant_id or order.tenant_id,
                    holding_id=holding_id,
                )
                order.consumption_record_id = consumption_record.id

            order.estado = "EJECUTADO"
            return order

    def reject_voice_order(self, order_id: int, tenant_id: str | None = None) -> VoiceOrderLogDTO:
        """Descarta o rechaza una orden por voz errónea."""
        order = self.get_voice_order(order_id, tenant_id=tenant_id)
        if order.estado != "PENDIENTE":
            raise DomainValidationError(f"Voice order {order_id} is already resolved: {order.estado}")

        order.estado = "RECHAZADO"
        return order
