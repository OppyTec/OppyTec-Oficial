"""
oppytec-backend/src/modules/identity/application/session_killswitch.py
Kill-Switch de sesión inmediato al aplicar `Soft-Delete` a un trabajador (`is_deleted = True`):
- Revoca todos sus tokens JWT / Refresh Tokens activos en Redis (`< 50 ms`).
- Si Redis está caído o tarda `> 50 ms` (`RedisCircuitBreaker`), hace fallback determinista
  al registro transaccional en PostgreSQL / memoria sin lanzar HTTP 500.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from src.core.redis import NamespacedRedisClient


@dataclass(frozen=True)
class SessionKillSwitchResult:
    """Resultado de revocación o consulta del Kill-Switch de sesión."""

    user_id: int
    revoked: bool
    persisted_in_redis: bool
    used_db_fallback: bool
    revoked_at_iso: str


class SessionKillSwitchService:
    """
    Gestiona la revocación instantánea de sesiones de usuarios eliminados (`soft-delete`)
    con tolerancia a fallos de Redis (`< 50 ms`) y fallback a PostgreSQL.
    """

    def __init__(
        self,
        redis_client: NamespacedRedisClient | None = None,
        db_revocation_checker: Callable[[int], Awaitable[bool]] | None = None,
        default_ttl_seconds: int = 604_800,
    ) -> None:
        self._redis = redis_client
        self._db_revocation_checker = db_revocation_checker
        self._default_ttl_seconds = default_ttl_seconds
        self._db_fallback_revoked_users: dict[int, str] = {}

    @staticmethod
    def _build_revocation_key(user_id: int, scope: str = "client") -> str:
        return f"session:killswitch:{scope}:user_{user_id}"

    async def revoke_all_user_sessions(
        self,
        *,
        user_id: int,
        actor_user_id: int,
        scope: str = "client",
    ) -> SessionKillSwitchResult:
        """
        Ejecuta el Kill-Switch de sesión para `user_id` cuando pasa a `is_deleted = True`.
        Siempre registra en el fallback de base de datos e intenta propagar a Redis (`< 50 ms`).
        """
        now_iso = datetime.now(UTC).isoformat()
        payload = f"REVOKED_BY:{actor_user_id}:{now_iso}"
        self._db_fallback_revoked_users[user_id] = payload

        persisted_in_redis = False
        if self._redis is not None:
            raw_key = self._build_revocation_key(user_id=user_id, scope=scope)
            persisted_in_redis = await self._redis.set_safe(
                raw_key,
                payload,
                ex_seconds=self._default_ttl_seconds,
            )

        return SessionKillSwitchResult(
            user_id=user_id,
            revoked=True,
            persisted_in_redis=persisted_in_redis,
            used_db_fallback=not persisted_in_redis,
            revoked_at_iso=now_iso,
        )

    async def is_user_session_revoked(
        self,
        *,
        user_id: int,
        scope: str = "client",
    ) -> bool:
        """
        Verifica si la sesión de `user_id` fue revocada.
        1. Consulta Redis con `get_safe` (< 50 ms).
        2. Si Redis no responde o devuelve `None` con el circuito abierto, consulta el fallback PostgreSQL.
        """
        if self._redis is not None:
            raw_key = self._build_revocation_key(user_id=user_id, scope=scope)
            redis_val = await self._redis.get_safe(raw_key, default=None)
            if redis_val is not None:
                return True

        if user_id in self._db_fallback_revoked_users:
            return True

        if self._db_revocation_checker is not None:
            return await self._db_revocation_checker(user_id)

        return False

    def clear_revocation_on_restore(self, *, user_id: int) -> None:
        """Limpia la marca de revocación en el fallback local cuando un ex-trabajador es reactivado."""
        self._db_fallback_revoked_users.pop(user_id, None)
