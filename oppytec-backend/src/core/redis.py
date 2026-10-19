"""
oppytec-backend/src/core/redis.py
Pool asíncrono de Redis con aislamiento por `ENV_NAMESPACE` y Circuit Breaker tolerante a fallos (< 50 ms).
Garantiza degradación elegante sin arrojar HTTP 500 si Redis cae o supera el umbral de latencia.
"""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

from redis.asyncio import ConnectionPool, Redis

from src.core.config import Settings, get_settings

T = TypeVar("T")


def build_namespaced_redis_key(
    key: str,
    namespace: str | None = None,
    environment: str | None = None,
) -> str:
    """
    Construye una clave de Redis aislada por entorno y `ENV_NAMESPACE` (Git Worktrees / PRs).
    Ejemplo: `local:wt_p2_1:session:revoked:user_42`.
    """
    cleaned_key = key.strip().lstrip(":")
    if not cleaned_key:
        raise ValueError("Redis key cannot be empty")
    settings = get_settings()
    env_val = environment or settings.ENVIRONMENT
    ns_val = namespace or settings.ENV_NAMESPACE
    return f"{env_val}:{ns_val}:{cleaned_key}"


@dataclass
class RedisCircuitBreaker:
    """
    Circuit Breaker determinista para proteger el plano crítico si Redis falla o supera 50 ms.
    Estados: `"CLOSED"` (normal), `"OPEN"` (bypass inmediato a fallback), `"HALF_OPEN"` (sonda).
    """

    failure_threshold: int = 3
    max_latency_ms: float = 50.0
    recovery_timeout_seconds: float = 15.0
    consecutive_failures: int = field(default=0, init=False)
    opened_at_monotonic: float | None = field(default=None, init=False)

    @property
    def state(self) -> str:
        """Devuelve el estado actual del circuito (`CLOSED`, `OPEN`, `HALF_OPEN`)."""
        if self.opened_at_monotonic is None:
            return "CLOSED"
        elapsed = time.monotonic() - self.opened_at_monotonic
        if elapsed >= self.recovery_timeout_seconds:
            return "HALF_OPEN"
        return "OPEN"

    def record_success(self, latency_ms: float) -> None:
        """Registra una operación exitosa o abre el circuito si la latencia excede el umbral."""
        if latency_ms > self.max_latency_ms:
            self.record_failure()
            return
        self.consecutive_failures = 0
        self.opened_at_monotonic = None

    def record_failure(self) -> None:
        """Incrementa el contador de fallos y abre el circuito al alcanzar `failure_threshold`."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.opened_at_monotonic = time.monotonic()

    async def execute_or_fallback(
        self,
        operation: Callable[[], Awaitable[T]],
        fallback_value: T,
    ) -> T:
        """
        Ejecuta `operation` midiendo latencia en milisegundos.
        Si el circuito está `OPEN` o ocurre cualquier excepción/timeout, devuelve `fallback_value`.
        """
        if self.state == "OPEN":
            return fallback_value
        started = time.perf_counter()
        try:
            result = await operation()
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            self.record_success(elapsed_ms)
            return result
        except Exception:
            self.record_failure()
            return fallback_value


class NamespacedRedisClient:
    """Cliente Redis asíncrono envuelto con `ENV_NAMESPACE` y `RedisCircuitBreaker`."""

    def __init__(
        self,
        redis_client: Redis,
        settings: Settings | None = None,
        circuit_breaker: RedisCircuitBreaker | None = None,
    ) -> None:
        self._redis = redis_client
        self._settings = settings or get_settings()
        self.circuit_breaker = circuit_breaker or RedisCircuitBreaker()

    def format_key(self, raw_key: str) -> str:
        """Formatea la clave con el prefijo de entorno y namespace."""
        return build_namespaced_redis_key(
            raw_key,
            namespace=self._settings.ENV_NAMESPACE,
            environment=self._settings.ENVIRONMENT,
        )

    async def get_safe(self, raw_key: str, default: str | None = None) -> str | None:
        """Obtiene un valor de Redis con fallback seguro si el circuito está abierto."""
        full_key = self.format_key(raw_key)

        async def _op() -> str | None:
            val: bytes | str | None = await self._redis.get(full_key)
            if val is None:
                return default
            return val.decode("utf-8") if isinstance(val, bytes) else str(val)

        return await self.circuit_breaker.execute_or_fallback(_op, default)

    async def set_safe(
        self,
        raw_key: str,
        value: str,
        ex_seconds: int = 300,
    ) -> bool:
        """Guarda un valor con TTL en Redis devolviendo `False` en degradación sin lanzar HTTP 500."""
        full_key = self.format_key(raw_key)

        async def _op() -> bool:
            await self._redis.set(full_key, value, ex=ex_seconds)
            return True

        return await self.circuit_breaker.execute_or_fallback(_op, False)


_redis_pool: ConnectionPool | None = None


def get_redis_pool(settings: Settings | None = None) -> ConnectionPool:
    """Crea o reutiliza el pool de conexiones asíncrono de Redis."""
    global _redis_pool
    if _redis_pool is None:
        resolved = settings or get_settings()
        _redis_pool = ConnectionPool.from_url(
            resolved.REDIS_URL.get_secret_value(),
            decode_responses=True,
            max_connections=50,
            socket_timeout=0.05,
            socket_connect_timeout=0.05,
        )
    return _redis_pool


def get_redis_client(settings: Settings | None = None) -> NamespacedRedisClient:
    """Devuelve un cliente Redis con namespace aislado y Circuit Breaker activo."""
    resolved = settings or get_settings()
    raw_client = Redis(connection_pool=get_redis_pool(resolved))
    return NamespacedRedisClient(redis_client=raw_client, settings=resolved)
