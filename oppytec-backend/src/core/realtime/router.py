"""
oppytec-backend/src/core/realtime/router.py
Endpoint único de WebSockets en Tiempo Real (`/api/v1/ws/realtime`):
- Exige token JWT válido y sesión activa (`is_deleted == False`).
- Verifica pertenencia del usuario al `tenant_id` solicitado.
- Soporta recuperación de eventos perdidos mediante `?last_event_id=<id>` (filtrados por RBAC de 3 niveles).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.core.config import get_settings
from src.core.realtime.manager import RealtimeConnectionManager, WebSocketConnectionContext
from src.core.realtime.publisher import RealtimePublisher

router = APIRouter(tags=["realtime"])

_default_manager = RealtimeConnectionManager(default_env_ns=get_settings().ENV_NAMESPACE)
_default_publisher = RealtimePublisher(_default_manager, env_ns=get_settings().ENV_NAMESPACE)


def get_realtime_manager() -> RealtimeConnectionManager:
    """Devuelve la instancia singleton de `RealtimeConnectionManager`."""
    return _default_manager


def get_realtime_publisher() -> RealtimePublisher:
    """Devuelve la instancia singleton de `RealtimePublisher`."""
    return _default_publisher


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode((segment + padding).encode("ascii"))


@dataclass(frozen=True)
class VerifiedRealtimeTokenClaims:
    """Claims verificados del token JWT para el handshake de `/api/v1/ws/realtime`."""

    user_id: int
    holding_id: UUID
    allowed_tenant_ids: frozenset[UUID]
    permissions: frozenset[str]
    assigned_bodega_ids: frozenset[int] | None
    is_deleted: bool
    is_superuser: bool
    is_holding_owner: bool


def create_realtime_jwt_token(
    *,
    user_id: int,
    holding_id: UUID,
    allowed_tenant_ids: list[UUID],
    permissions: list[str],
    assigned_bodega_ids: list[int] | None = None,
    is_deleted: bool = False,
    is_superuser: bool = False,
    is_holding_owner: bool = False,
    expires_in_seconds: int = 1800,
    secret_key: str | None = None,
) -> str:
    """
    Genera un JWT HS256 firmado para autenticar conexiones al túnel `/api/v1/ws/realtime`.
    """
    secret = secret_key or get_settings().JWT_ACCESS_SECRET_KEY.get_secret_value()
    header_bytes = json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8")
    payload_dict: dict[str, object] = {
        "sub": str(user_id),
        "holding_id": str(holding_id),
        "allowed_tenant_ids": [str(tid) for tid in allowed_tenant_ids],
        "permissions": permissions,
        "assigned_bodega_ids": assigned_bodega_ids,
        "is_deleted": is_deleted,
        "is_superuser": is_superuser,
        "is_holding_owner": is_holding_owner,
        "exp": int(time.time()) + expires_in_seconds,
    }
    payload_bytes = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
    signing_input = f"{_b64url_encode(header_bytes)}.{_b64url_encode(payload_bytes)}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def verify_realtime_jwt_token(
    token: str,
    *,
    secret_key: str | None = None,
) -> VerifiedRealtimeTokenClaims:
    """
    Valida criptográficamente el JWT HS256, su expiración y el estado `is_deleted == False`.
    """
    if not token or token.count(".") != 2:
        raise ValueError("Formato de token JWT inválido")

    secret = secret_key or get_settings().JWT_ACCESS_SECRET_KEY.get_secret_value()
    header_b64, payload_b64, sig_b64 = token.split(".")
    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    actual_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Firma de token JWT inválida")

    raw_payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError("Payload JWT malformado")

    exp_val = int(str(raw_payload.get("exp", 0)))
    if exp_val <= int(time.time()):
        raise ValueError("Token JWT expirado")

    is_deleted = bool(raw_payload.get("is_deleted", False))
    if is_deleted:
        raise PermissionError("Usuario en soft-delete (sesión revocada)")

    user_id = int(str(raw_payload["sub"]))
    holding_id = UUID(str(raw_payload["holding_id"]))
    raw_tenants = raw_payload.get("allowed_tenant_ids", [])
    allowed_tenants = frozenset(
        UUID(str(t)) for t in (raw_tenants if isinstance(raw_tenants, list) else [])
    )
    raw_perms = raw_payload.get("permissions", [])
    perms = frozenset(
        str(p).strip().lower() for p in (raw_perms if isinstance(raw_perms, list) else [])
    )
    raw_bodegas = raw_payload.get("assigned_bodega_ids")
    bodegas = (
        frozenset(int(str(b)) for b in raw_bodegas)
        if isinstance(raw_bodegas, list)
        else None
    )

    return VerifiedRealtimeTokenClaims(
        user_id=user_id,
        holding_id=holding_id,
        allowed_tenant_ids=allowed_tenants,
        permissions=perms,
        assigned_bodega_ids=bodegas,
        is_deleted=is_deleted,
        is_superuser=bool(raw_payload.get("is_superuser", False)),
        is_holding_owner=bool(raw_payload.get("is_holding_owner", False)),
    )


@router.websocket("/api/v1/ws/realtime")
async def realtime_websocket_endpoint(
    websocket: WebSocket,
    tenant_id: Annotated[UUID, Query(description="UUID de la sucursal activa")],
    token: Annotated[str | None, Query(description="Token JWT de acceso")] = None,
    last_event_id: Annotated[
        str | None,
        Query(description="Último event_id de Redis Stream recibido para catch-up tras reconexión"),
    ] = None,
) -> None:
    """
    Túnel único WebSocket `/api/v1/ws/realtime` con autenticación JWT, aislamiento por Tenant,
    filtrado RBAC de 3 niveles y catch-up desde Redis Streams (`last_event_id`).
    """
    auth_header = websocket.headers.get("authorization", "")
    resolved_token = token
    if not resolved_token and auth_header.lower().startswith("bearer "):
        resolved_token = auth_header[7:].strip()

    if not resolved_token:
        await websocket.close(code=4001, reason="MISSING_JWT_TOKEN")
        return

    try:
        claims = verify_realtime_jwt_token(resolved_token)
    except PermissionError:
        await websocket.close(code=4003, reason="SESSION_REVOKED")
        return
    except ValueError:
        await websocket.close(code=4001, reason="INVALID_OR_EXPIRED_JWT")
        return

    if (
        not claims.is_superuser
        and not claims.is_holding_owner
        and tenant_id not in claims.allowed_tenant_ids
    ):
        await websocket.close(code=4003, reason="TENANT_ACCESS_DENIED")
        return

    await websocket.accept()
    env_ns = get_settings().ENV_NAMESPACE
    conn_ctx = WebSocketConnectionContext(
        websocket=websocket,
        user_id=claims.user_id,
        holding_id=claims.holding_id,
        tenant_id=tenant_id,
        env_ns=env_ns,
        active_permissions=claims.permissions,
        assigned_bodega_ids=claims.assigned_bodega_ids,
        is_superuser=claims.is_superuser,
        is_holding_owner=claims.is_holding_owner,
    )
    manager = get_realtime_manager()
    publisher = get_realtime_publisher()
    manager.register(conn_ctx)

    try:
        if last_event_id:
            missed_events = publisher.get_catchup_events(
                claims.holding_id,
                tenant_id,
                last_event_id,
                env_ns=env_ns,
            )
            for missed in missed_events:
                if conn_ctx.can_receive_event(missed):
                    await websocket.send_json(missed.model_dump(mode="json"))

        while True:
            incoming = await websocket.receive_json()
            if isinstance(incoming, dict) and incoming.get("type") == "ping":
                await websocket.send_json({"type": "pong", "ts": int(time.time() * 1000)})
    except WebSocketDisconnect:
        manager.unregister(conn_ctx)
    except Exception:
        manager.unregister(conn_ctx)
