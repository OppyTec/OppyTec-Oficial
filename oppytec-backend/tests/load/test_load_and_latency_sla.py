r"""
Pruebas de Ráfaga Concurrente, Throughput (>= 500 RPS) y SLA de Latencia (P95 <= 120ms)
(`tests/load/test_load_and_latency_sla.py`).

Valida mediante `asyncio.gather` contra `async_client` (`httpx.ASGITransport`):
1. Operaciones críticas de stock, conversión de unidades y ventas POS cumplen P95 <= 120 ms.
2. Consultas de analítica ejecutiva y varianza de Food Cost cumplen P95 <= 800 ms.
3. Throughput concurrente proyectado >= 500 RPS con `0` respuestas `HTTP 500`.
"""
from __future__ import annotations

import httpx
import pytest

from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from tests.load.locustfile import (
    DEFAULT_LOAD_PROFILE,
    TASK_WEIGHTS,
    run_burst_load_simulation,
)

pytestmark = pytest.mark.load


@pytest.mark.asyncio
async def test_stock_and_sales_burst_meets_p95_120ms_and_500_rps_sla(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Ejecuta una ráfaga concurrente de 75 operaciones críticas de stock, conversión y ventas POS,
    verificando $P_{95} \\le 120\\text{ ms}$, `0` errores `HTTP 5xx` y throughput $\\ge 500\\text{ RPS}$.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    assert DEFAULT_LOAD_PROFILE.target_rps == 500
    assert DEFAULT_LOAD_PROFILE.p95_stock_sla_ms == 120.0
    assert sum(TASK_WEIGHTS.values()) == 100

    token = create_access_token(
        user_id=801,
        holding_id="holding_load_sla",
        tenant_id="tenant_load_sla",
        hierarchy_rank=15,
        contracted_modules=["catalog", "inventory", "operations", "analytics"],
        role_grants=[
            "catalog.units.convert",
            "inventory.kardex.write",
            "inventory.kardex.read",
            "operations.sales.create",
            "analytics.executive_summary.read",
            "analytics.food_cost.read",
        ],
        accessible_tenants=["tenant_load_sla"],
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "tenant_load_sla",
    }

    # Warm-up request para inicializar rutas y cachés en memoria
    warmup = await async_client.get("/api/v1/health")
    assert warmup.status_code == 200

    metrics = await run_burst_load_simulation(
        async_client,
        headers,
        concurrency=75,
        mode="stock_and_sales",
    )

    assert metrics.total_requests == 75
    assert metrics.http_5xx_count == 0
    assert metrics.failed_requests == 0
    assert metrics.p95_latency_ms <= DEFAULT_LOAD_PROFILE.p95_stock_sla_ms
    assert metrics.projected_rps >= float(DEFAULT_LOAD_PROFILE.target_rps)


@pytest.mark.asyncio
async def test_analytics_burst_meets_p95_800ms_and_zero_5xx_sla(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Ejecuta una ráfaga concurrente de 50 consultas ejecutivas de analítica y varianza de Food Cost,
    verificando $P_{95} \\le 800\\text{ ms}$ y `0` respuestas `HTTP 5xx`.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    token = create_access_token(
        user_id=802,
        holding_id="holding_load_sla",
        tenant_id="tenant_load_sla",
        hierarchy_rank=10,
        contracted_modules=["analytics"],
        role_grants=[
            "analytics.executive_summary.read",
            "analytics.food_cost.read",
        ],
        accessible_tenants=["tenant_load_sla"],
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "tenant_load_sla",
    }

    metrics = await run_burst_load_simulation(
        async_client,
        headers,
        concurrency=50,
        mode="analytics",
    )

    assert metrics.total_requests == 50
    assert metrics.http_5xx_count == 0
    assert metrics.failed_requests == 0
    assert metrics.p95_latency_ms <= DEFAULT_LOAD_PROFILE.p95_analytics_sla_ms
