"""
Vector Red Team 10 (`tests/security_redteam/test_10_resilience_chaos_and_circuit_breakers.py`):
- Ingeniería del Caos en `RedisCircuitBreaker`: apertura del circuito tras fallos consecutivos o latencia `> 50 ms`,
  devolviendo fallback en `< 50 ms` sin arrojar HTTP 500.
- `SlidingWindowRateLimiter`: bloqueo HTTP 429 con cabecera `Retry-After` y `X-RateLimit-Remaining: 0` al superar la cuota.
- Escudo Anti-Anomalías Cambiarias (*FX Drift Circuit Breaker*): cuarentena automática (`FX_ANOMALY_QUARANTINED`)
  ante variaciones `> 8.0%` sin confirmación secundaria ni override manual.
- Inmutabilidad Append-Only de las bitácoras de auditoría: rechazo HTTP 403 (`AUDIT_APPEND_ONLY_VIOLATION`) ante `DELETE`.
"""
from __future__ import annotations

import time
from decimal import Decimal

import httpx
import pytest

from src.core.fx.anomaly_guard import evaluate_fx_rate_drift
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.redis import RedisCircuitBreaker
from src.core.security import create_access_token

pytestmark = pytest.mark.security_redteam


async def test_redis_circuit_breaker_opens_on_outage_and_returns_fallback_under_50ms() -> None:
    """
    Simula una caída total de Redis (`ConnectionError`): tras `failure_threshold=3` fallos,
    `RedisCircuitBreaker` pasa a estado `OPEN` y responde inmediatamente con el `fallback_value` en `< 50 ms`.
    """
    breaker = RedisCircuitBreaker(
        failure_threshold=3,
        max_latency_ms=50.0,
        recovery_timeout_seconds=30.0,
    )
    assert breaker.state == "CLOSED"

    async def _failing_redis_op() -> str:
        raise ConnectionError("Simulated Redis cluster outage")

    for _ in range(3):
        val = await breaker.execute_or_fallback(_failing_redis_op, "SAFE_FALLBACK")
        assert val == "SAFE_FALLBACK"

    assert breaker.state == "OPEN"

    started = time.perf_counter()
    fast_fallback = await breaker.execute_or_fallback(_failing_redis_op, "OPEN_FAST_FALLBACK")
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    assert fast_fallback == "OPEN_FAST_FALLBACK"
    assert elapsed_ms < 50.0


async def test_sliding_window_rate_limiter_enforces_http_429_and_retry_after_header(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que 5 intentos de login seguidos bajo el perfil `auth` (`5 req / 60s`) permitan los primeros 5
    y bloqueen el 6º intento con HTTP 429, `Retry-After` y `error_code == 'RATE_LIMIT_EXCEEDED'`.
    """
    clear_revoked_sessions()
    limiter = get_rate_limiter()
    limiter.reset()

    for _ in range(5):
        resp = await async_client.post(
            "/api/v1/auth/login",
            headers={"X-Forwarded-For": "198.51.100.77"},
            json={"username_or_email": "unknown@oppytec.com", "password": "WrongPassword123!"},
        )
        assert resp.status_code == 401

    throttled = await async_client.post(
        "/api/v1/auth/login",
        headers={"X-Forwarded-For": "198.51.100.77"},
        json={"username_or_email": "unknown@oppytec.com", "password": "WrongPassword123!"},
    )
    assert throttled.status_code == 429
    assert "Retry-After" in throttled.headers
    assert int(throttled.headers["Retry-After"]) >= 1
    assert throttled.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
    limiter.reset()


def test_fx_anomaly_circuit_breaker_quarantines_swings_above_8_percent() -> None:
    """
    Verifica que una variación cambiaria `> 8.0%` sin confirmación secundaria ni override manual
    active el Circuit Breaker (`is_quarantined=True`, `FX_ANOMALY_QUARANTINED`) y preserve la tasa previa.
    """
    prev_rate = Decimal("950.00000000")
    spike_rate = Decimal("1150.00000000")  # +21.05% swing

    quarantined = evaluate_fx_rate_drift(
        "USD/CLP",
        previous_rate=prev_rate,
        candidate_rate=spike_rate,
        confirmed_by_secondary_source=False,
        is_manual_override=False,
    )
    assert quarantined.is_quarantined is True
    assert quarantined.effective_rate == prev_rate
    assert quarantined.action_taken == "FX_ANOMALY_QUARANTINED"
    assert quarantined.alert_message is not None

    # Con override manual explícito del SuperUser se acepta la nueva tasa
    manual_ok = evaluate_fx_rate_drift(
        "USD/CLP",
        previous_rate=prev_rate,
        candidate_rate=spike_rate,
        is_manual_override=True,
    )
    assert manual_ok.is_quarantined is False
    assert manual_ok.effective_rate == spike_rate
    assert manual_ok.action_taken == "MANUAL_SUPERUSER_OVERRIDE"


async def test_append_only_audit_log_rejects_delete_with_http_403(
    async_client: httpx.AsyncClient,
) -> None:
    """Verifica que incluso un token con permisos de auditoría reciba HTTP 403 al intentar borrar un evento."""
    clear_revoked_sessions()
    get_rate_limiter().reset()

    token = create_access_token(
        user_id=1,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=0,
        is_superuser_god=True,
        is_global_staff=True,
        role_grants=["audit.activity_ledger.read", "audit.activity_ledger.append"],
        accessible_tenants=["tenant_rest_a"],
    )
    del_resp = await async_client.delete(
        "/api/v1/audit/activity/evt-99999",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tenant_rest_a",
        },
    )
    assert del_resp.status_code == 403
    assert del_resp.json()["error_code"] == "AUDIT_APPEND_ONLY_VIOLATION"
