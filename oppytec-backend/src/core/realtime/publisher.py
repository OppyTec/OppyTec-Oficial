"""
oppytec-backend/src/core/realtime/publisher.py
Publicador Dual de Tiempo Real (Redis Pub/Sub + Redis Stream con buffer circular)
para recuperación determinista (`catch-up`) mediante `last_event_id` tras micro-cortes Wi-Fi en móviles.
"""
from __future__ import annotations

import contextlib
import time
from collections import deque
from typing import Protocol
from uuid import UUID

from src.core.realtime.manager import RealtimeConnectionManager
from src.core.realtime.schemas import (
    RealtimeEventEnvelope,
    build_realtime_channel,
    build_realtime_stream_key,
    parse_stream_event_id,
)


class AsyncRedisPubSubStreamProtocol(Protocol):
    """Protocolo opcional para cliente Redis asíncrono con soporte Pub/Sub y Streams."""

    async def publish(self, channel: str, message: str) -> int:
        """Publica un mensaje JSON en un canal Redis Pub/Sub."""

    async def xadd(
        self,
        name: str,
        fields: dict[str, str],
        maxlen: int | None = None,
    ) -> str:
        """Agrega una entrada al Redis Stream con límite circular `maxlen`."""


class RealtimePublisher:
    """
    Publicador de eventos en tiempo real con:
    1. Generación monotónica de `event_id` compatible con Redis Streams (`"<ms>-<seq>"`).
    2. Buffer circular (`maxlen`) por canal `rt:{env_ns}:{holding_id}:{tenant_id}:stream` para catch-up.
    3. Despacho dual a Redis Pub/Sub + `RealtimeConnectionManager` con degradación elegante si Redis cae.
    """

    def __init__(
        self,
        connection_manager: RealtimeConnectionManager,
        *,
        env_ns: str = "default",
        stream_maxlen: int = 250,
        redis_bus: AsyncRedisPubSubStreamProtocol | None = None,
    ) -> None:
        self._manager = connection_manager
        self._env_ns = env_ns
        self._stream_maxlen = stream_maxlen
        self._redis_bus = redis_bus
        self._stream_buffers: dict[str, deque[RealtimeEventEnvelope]] = {}
        self._published_channels: list[tuple[str, str]] = []
        self._last_ms: int = 0
        self._seq: int = 0

    def _next_stream_event_id(self) -> str:
        """Genera un identificador secuencial estrictamente creciente `"<timestamp_ms>-<seq>"`."""
        now_ms = int(time.time() * 1000)
        if now_ms == self._last_ms:
            self._seq += 1
        else:
            if now_ms < self._last_ms:
                now_ms = self._last_ms
                self._seq += 1
            else:
                self._last_ms = now_ms
                self._seq = 0
        return f"{now_ms}-{self._seq}"

    @property
    def published_channels(self) -> list[tuple[str, str]]:
        """Historial de `(channel, event_id)` publicados para trazabilidad y pruebas."""
        return list(self._published_channels)

    async def publish_event(
        self,
        envelope: RealtimeEventEnvelope,
        *,
        env_ns: str | None = None,
    ) -> RealtimeEventEnvelope:
        """
        Asigna un `event_id` de stream, persiste en el buffer circular de catch-up,
        publica en Redis Pub/Sub (si está configurado) y despacha a las conexiones del worker.
        """
        resolved_ns = env_ns or self._env_ns
        channel = build_realtime_channel(resolved_ns, envelope.holding_id, envelope.tenant_id)
        stream_key = build_realtime_stream_key(resolved_ns, envelope.holding_id, envelope.tenant_id)

        assigned_id = (
            envelope.event_id
            if envelope.event_id and envelope.event_id != "0-0"
            else self._next_stream_event_id()
        )
        final_envelope = envelope.model_copy(update={"event_id": assigned_id})
        payload_json = final_envelope.model_dump_json()

        buffer = self._stream_buffers.get(stream_key)
        if buffer is None:
            buffer = deque(maxlen=self._stream_maxlen)
            self._stream_buffers[stream_key] = buffer
        buffer.append(final_envelope)

        if self._redis_bus is not None:
            with contextlib.suppress(Exception):
                await self._redis_bus.xadd(
                    stream_key,
                    {"envelope": payload_json},
                    maxlen=self._stream_maxlen,
                )
                await self._redis_bus.publish(channel, payload_json)

        self._published_channels.append((channel, assigned_id))
        await self._manager.broadcast_envelope(final_envelope, env_ns=resolved_ns)
        return final_envelope

    def get_catchup_events(
        self,
        holding_id: UUID | None,
        tenant_id: UUID | None,
        last_event_id: str,
        *,
        env_ns: str | None = None,
    ) -> list[RealtimeEventEnvelope]:
        """
        Recupera desde el Redis Stream / buffer circular todos los eventos posteriores a `last_event_id`
        para ese `holding_id` y `tenant_id`.
        """
        resolved_ns = env_ns or self._env_ns
        stream_key = build_realtime_stream_key(resolved_ns, holding_id, tenant_id)
        buffer = self._stream_buffers.get(stream_key)
        if not buffer:
            return []

        last_tuple = parse_stream_event_id(last_event_id)
        missed: list[RealtimeEventEnvelope] = []
        for item in buffer:
            if parse_stream_event_id(item.event_id) > last_tuple:
                missed.append(item)
        return missed
