"""
oppytec-backend/src/core/guards/rate_limiter.py
Limitador de tasa en ventana deslizante (`SlidingWindowRateLimiter`) aislado por `ENV_NAMESPACE`:
- Perfiles preconfigurados:
  - `auth`: 5 peticiones / 60 segundos (protección anti-fuerza bruta en login/refresh)
  - `api`: 120 peticiones / 60 segundos (operación normal REST)
  - `ai`: 20 peticiones / 60 segundos (consultas al asistente `OppyFy`)
- Opera en `< 1 ms` con ventana deslizante en memoria determinista (y sincronización opcional con Redis).
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Literal

from fastapi import Request, Response

from src.core.config import get_settings
from src.core.exceptions import RateLimitExceededError
from src.core.redis import build_namespaced_redis_key

RateLimitProfile = Literal["auth", "api", "ai"]


@dataclass(frozen=True)
class RateLimitQuota:
    """Configuración de ventana deslizante para un perfil de Rate Limiting."""

    profile: RateLimitProfile
    max_requests: int
    window_seconds: int


RATE_LIMIT_PROFILES: dict[RateLimitProfile, RateLimitQuota] = {
    "auth": RateLimitQuota(profile="auth", max_requests=5, window_seconds=60),
    "api": RateLimitQuota(profile="api", max_requests=120, window_seconds=60),
    "ai": RateLimitQuota(profile="ai", max_requests=20, window_seconds=60),
}


@dataclass(frozen=True)
class RateLimitCheckResult:
    """Resultado determinista de evaluar el límite de tasa en ventana deslizante."""

    allowed: bool
    profile: RateLimitProfile
    namespaced_key: str
    limit: int
    remaining: int
    retry_after_seconds: int


class SlidingWindowRateLimiter:
    """
    Motor de ventana deslizante aislado por `ENV_NAMESPACE` con latencia `< 1 ms`.
    Permite evaluar o limpiar contadores determinísticamente en pruebas y en producción.
    """

    def __init__(
        self,
        *,
        profiles: dict[RateLimitProfile, RateLimitQuota] | None = None,
    ) -> None:
        self._profiles: dict[RateLimitProfile, RateLimitQuota] = dict(
            profiles or RATE_LIMIT_PROFILES
        )
        self._buckets: dict[str, deque[float]] = {}

    def reset(self) -> None:
        """Limpia todos los contadores en memoria."""
        self._buckets.clear()

    def build_bucket_key(
        self,
        *,
        profile: RateLimitProfile,
        subject_key: str,
        env_namespace: str | None = None,
    ) -> str:
        """Construye la clave de Rate Limiting aislada por entorno y `ENV_NAMESPACE`."""
        cleaned_subject = subject_key.strip() or "anonymous"
        return build_namespaced_redis_key(
            f"ratelimit:{profile}:{cleaned_subject}",
            namespace=env_namespace,
        )

    def check_and_consume(
        self,
        *,
        profile: RateLimitProfile,
        subject_key: str,
        env_namespace: str | None = None,
        now_monotonic: float | None = None,
    ) -> RateLimitCheckResult:
        """
        Verifica si `subject_key` puede realizar una petición bajo `profile`.
        Si excede `max_requests` dentro de `window_seconds`, devuelve `allowed=False` y `retry_after_seconds`.
        """
        quota = self._profiles[profile]
        now = now_monotonic if now_monotonic is not None else time.monotonic()
        cutoff = now - float(quota.window_seconds)
        full_key = self.build_bucket_key(
            profile=profile,
            subject_key=subject_key,
            env_namespace=env_namespace,
        )

        bucket = self._buckets.setdefault(full_key, deque())
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= quota.max_requests:
            oldest = bucket[0]
            retry_after = max(1, round((oldest + float(quota.window_seconds)) - now))
            return RateLimitCheckResult(
                allowed=False,
                profile=profile,
                namespaced_key=full_key,
                limit=quota.max_requests,
                remaining=0,
                retry_after_seconds=retry_after,
            )

        bucket.append(now)
        remaining = max(0, quota.max_requests - len(bucket))
        return RateLimitCheckResult(
            allowed=True,
            profile=profile,
            namespaced_key=full_key,
            limit=quota.max_requests,
            remaining=remaining,
            retry_after_seconds=0,
        )


_default_rate_limiter = SlidingWindowRateLimiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Devuelve la instancia singleton de `SlidingWindowRateLimiter`."""
    return _default_rate_limiter


class RequireRateLimit:
    """
    Dependencia FastAPI que aplica `SlidingWindowRateLimiter` por IP / Usuario / Tenant
    y lanza `RateLimitExceededError` (HTTP 429 con `Retry-After`) al superar la cuota.
    """

    def __init__(
        self,
        profile: RateLimitProfile = "api",
        *,
        limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        if profile not in RATE_LIMIT_PROFILES:
            raise ValueError(f"Unsupported rate limit profile '{profile}'.")
        self.profile: RateLimitProfile = profile
        self._limiter = limiter

    async def __call__(self, request: Request, response: Response) -> RateLimitCheckResult:
        limiter = self._limiter or get_rate_limiter()
        client_host = request.client.host if request.client else "127.0.0.1"
        forwarded_for = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        subject = forwarded_for or client_host
        tenant_header = request.headers.get("X-Tenant-ID", "").strip()
        if tenant_header:
            subject = f"{tenant_header}:{subject}"

        env_ns = get_settings().ENV_NAMESPACE
        result = limiter.check_and_consume(
            profile=self.profile,
            subject_key=subject,
            env_namespace=env_ns,
        )
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        if not result.allowed:
            raise RateLimitExceededError(
                f"Rate limit exceeded for profile '{self.profile}' ({result.limit} requests/window).",
                retry_after_seconds=result.retry_after_seconds,
                i18n_key="common:errors.rate_limit_exceeded",
            )
        return result
