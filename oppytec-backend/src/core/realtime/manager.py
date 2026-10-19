"""
oppytec-backend/src/core/realtime/manager.py
Gestor de Conexiones WebSocket (`RealtimeConnectionManager`) aislado por canal
`rt:{env_ns}:{holding_id}:{tenant_id}` con filtrado RBAC de 3 niveles en servidor
y desconexión inmediata ante el Kill-Switch `SESSION_REVOKED` (soft-delete).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from src.core.realtime.schemas import (
    RealtimeEventEnvelope,
    build_realtime_channel,
    validate_three_level_permission_code,
)

KILL_SWITCH_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "SESSION_REVOKED",
        "rbac.session_revoked_soft_delete",
    }
)


class WebSocketTransportProtocol(Protocol):
    """Protocolo mínimo de transporte WebSocket compatible con FastAPI/Starlette y dobles de prueba."""

    async def send_json(self, data: dict[str, object]) -> None:
        """Envía un frame JSON hacia el cliente conectado."""

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        """Cierra la conexión WebSocket con código estándar o de aplicación."""


@dataclass(frozen=True)
class WebSocketConnectionContext:
    """Contexto de seguridad Zero-Trust asociado a una conexión WebSocket activa."""

    websocket: WebSocketTransportProtocol
    user_id: int
    holding_id: UUID | None
    tenant_id: UUID | None
    env_ns: str = "default"
    active_permissions: frozenset[str] = field(default_factory=frozenset)
    assigned_bodega_ids: frozenset[int] | None = None
    is_superuser: bool = False
    is_holding_owner: bool = False

    @property
    def channel(self) -> str:
        """Canal Redis Pub/Sub asignado a esta conexión."""
        return build_realtime_channel(self.env_ns, self.holding_id, self.tenant_id)

    def has_permission(self, required_permission: str | None) -> bool:
        """
        Verifica en O(1) si la conexión posee el permiso RBAC de 3 niveles `<modulo>.<submodulo>.<funcion>`.
        """
        if required_permission is None:
            return True
        if self.is_superuser or self.is_holding_owner or "*.*.*" in self.active_permissions:
            return True

        normalized = validate_three_level_permission_code(required_permission)
        if normalized in self.active_permissions:
            return True

        module_name, submodule_name, _ = normalized.split(".")
        return (
            f"{module_name}.{submodule_name}.*" in self.active_permissions
            or f"{module_name}.*.*" in self.active_permissions
        )

    def can_receive_event(self, envelope: RealtimeEventEnvelope) -> bool:
        """
        Evalúa todas las reglas de aislamiento Multi-Tenant, destinatario, bodega y RBAC de 3 niveles.
        """
        # 1. Aislamiento estricto por Holding y Tenant
        if envelope.tenant_id is not None and self.tenant_id != envelope.tenant_id:
            return False
        if envelope.holding_id is not None and self.holding_id != envelope.holding_id:
            return False
        if envelope.tenant_id is None and self.tenant_id is not None and not self.is_superuser:
            return False

        # 2. Filtro por usuarios destinatarios específicos (ej. notificación personal o kill-switch)
        if (
            envelope.target_user_ids is not None
            and self.user_id not in envelope.target_user_ids
        ):
            return False

        # 3. Filtro por Bodega / Área operativa asignada
        if (
            envelope.target_bodega_id is not None
            and not self.is_superuser
            and not self.is_holding_owner
            and self.assigned_bodega_ids is not None
            and envelope.target_bodega_id not in self.assigned_bodega_ids
        ):
            return False

        # 4. Los eventos de Kill-Switch dirigidos al usuario siempre se entregan para cerrar su sesión
        if envelope.event_type in KILL_SWITCH_EVENT_TYPES:
            return True

        # 5. Filtro RBAC de 3 niveles en servidor
        return self.has_permission(envelope.required_permission)


class RealtimeConnectionManager:
    """
    Administrador de conexiones WebSocket por worker aislado por canal `rt:{env_ns}:{holding_id}:{tenant_id}`.
    """

    def __init__(self, default_env_ns: str = "default") -> None:
        self._default_env_ns = default_env_ns
        self._channels: dict[str, list[WebSocketConnectionContext]] = {}

    def register(self, context: WebSocketConnectionContext) -> str:
        """Registra una conexión autenticada en su canal aislado `rt:{env_ns}:{holding_id}:{tenant_id}`."""
        channel = context.channel
        bucket = self._channels.setdefault(channel, [])
        if context not in bucket:
            bucket.append(context)
        return channel

    def unregister(self, context: WebSocketConnectionContext) -> None:
        """Elimina una conexión al desconectarse el cliente o tras ejecutar un Kill-Switch."""
        channel = context.channel
        bucket = self._channels.get(channel)
        if not bucket:
            return
        self._channels[channel] = [conn for conn in bucket if conn != context]
        if not self._channels[channel]:
            del self._channels[channel]

    def get_channel_connections(self, channel: str) -> list[WebSocketConnectionContext]:
        """Devuelve la lista de conexiones activas en un canal específico."""
        return list(self._channels.get(channel, []))

    async def broadcast_envelope(
        self,
        envelope: RealtimeEventEnvelope,
        *,
        env_ns: str | None = None,
    ) -> int:
        """
        Transmite un `RealtimeEventEnvelope` únicamente a las conexiones del canal correspondiente
        que superen el filtro RBAC de 3 niveles.
        Si el evento es `SESSION_REVOKED`, envía la orden de cierre y desconecta inmediatamente el socket (`code=4003`).
        Devuelve el número de clientes que recibieron el frame.
        """
        resolved_ns = env_ns or self._default_env_ns
        channel = build_realtime_channel(resolved_ns, envelope.holding_id, envelope.tenant_id)
        connections = list(self._channels.get(channel, []))
        delivered_count = 0
        serialized = envelope.model_dump(mode="json")

        for conn in connections:
            if not conn.can_receive_event(envelope):
                continue
            try:
                await conn.websocket.send_json(serialized)
                delivered_count += 1
                if envelope.event_type in KILL_SWITCH_EVENT_TYPES:
                    await conn.websocket.close(code=4003, reason="SESSION_REVOKED")
                    self.unregister(conn)
            except Exception:
                self.unregister(conn)

        return delivered_count

    async def revoke_user_sessions(
        self,
        user_id: int,
        holding_id: UUID,
        tenant_id: UUID,
        *,
        env_ns: str | None = None,
        trace_id: str = "kill-switch-soft-delete",
    ) -> int:
        """
        Ejecuta el Kill-Switch en tiempo real cerrando en el acto todas las sesiones WebSocket
        del trabajador que pasó a `soft-delete` (`is_deleted = True`).
        """
        kill_envelope = RealtimeEventEnvelope(
            event_id="0-0",
            event_type="SESSION_REVOKED",
            holding_id=holding_id,
            tenant_id=tenant_id,
            target_user_ids=[user_id],
            query_keys_to_invalidate=[["auth", "permissions", str(tenant_id)]],
            payload={"reason": "USER_SOFT_DELETED", "user_id": user_id},
            trace_id=trace_id,
        )
        return await self.broadcast_envelope(kill_envelope, env_ns=env_ns)
