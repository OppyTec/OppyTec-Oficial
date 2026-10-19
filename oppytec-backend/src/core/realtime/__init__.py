"""
oppytec-backend/src/core/realtime/__init__.py
Exportaciones públicas del Motor de Tiempo Real con WebSockets (`/api/v1/ws/realtime`).
"""
from __future__ import annotations

from src.core.realtime.manager import (
    KILL_SWITCH_EVENT_TYPES,
    RealtimeConnectionManager,
    WebSocketConnectionContext,
    WebSocketTransportProtocol,
)
from src.core.realtime.publisher import (
    AsyncRedisPubSubStreamProtocol,
    RealtimePublisher,
)
from src.core.realtime.router import (
    VerifiedRealtimeTokenClaims,
    create_realtime_jwt_token,
    get_realtime_manager,
    get_realtime_publisher,
    realtime_websocket_endpoint,
    router,
    verify_realtime_jwt_token,
)
from src.core.realtime.schemas import (
    THREE_LEVEL_PERMISSION_REGEX,
    HighlightEffectType,
    RealtimeEventEnvelope,
    build_realtime_channel,
    build_realtime_stream_key,
    parse_stream_event_id,
    validate_three_level_permission_code,
)

__all__ = [
    "KILL_SWITCH_EVENT_TYPES",
    "THREE_LEVEL_PERMISSION_REGEX",
    "AsyncRedisPubSubStreamProtocol",
    "HighlightEffectType",
    "RealtimeConnectionManager",
    "RealtimeEventEnvelope",
    "RealtimePublisher",
    "VerifiedRealtimeTokenClaims",
    "WebSocketConnectionContext",
    "WebSocketTransportProtocol",
    "build_realtime_channel",
    "build_realtime_stream_key",
    "create_realtime_jwt_token",
    "get_realtime_manager",
    "get_realtime_publisher",
    "parse_stream_event_id",
    "realtime_websocket_endpoint",
    "router",
    "validate_three_level_permission_code",
    "verify_realtime_jwt_token",
]
