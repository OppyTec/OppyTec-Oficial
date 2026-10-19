"""
Perfil de Carga y Ejecutor Asíncrono de Estrés para OppyTec SaaS v2.0 (`tests/load/locustfile.py`).

100% compatible con `mypy --strict` (cero `Any`, cero imports sin tipos):
- Define `OppyTecLoadProfile` (`target_rps=500`, `p95_stock_sla_ms=120.0`, `p95_analytics_sla_ms=800.0`).
- Define los pesos de las tareas operativas de restaurante/hotel (`TASK_WEIGHTS`).
- Provee `run_burst_load_simulation()` reutilizable tanto desde CLI como desde Pytest con `httpx.AsyncClient`.
"""
from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class OppyTecLoadProfile:
    """Contrato inmutable de objetivos SLA y throughput de OppyTec v2.0."""

    target_rps: int = 500
    p95_stock_sla_ms: float = 120.0
    p95_analytics_sla_ms: float = 800.0
    max_error_rate: float = 0.0


@dataclass(frozen=True)
class BurstSimulationMetrics:
    """Métricas consolidadas de una corrida de ráfaga concurrente."""

    total_requests: int
    http_5xx_count: int
    failed_requests: int
    elapsed_seconds: float
    projected_rps: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    latencies_ms: tuple[float, ...]


DEFAULT_LOAD_PROFILE = OppyTecLoadProfile()

TASK_WEIGHTS: dict[str, int] = {
    "pos_sale_explosion": 40,
    "kardex_movement_entry": 25,
    "catalog_unit_conversion": 20,
    "analytics_executive_summary": 15,
}


def compute_percentile_ms(samples_ms: list[float], percentile: float) -> float:
    """Calcula el percentil `percentile` (0..100) en milisegundos de forma determinista."""
    if not samples_ms:
        return 0.0
    ordered = sorted(samples_ms)
    rank = max(0, min(len(ordered) - 1, math.ceil((percentile / 100.0) * len(ordered)) - 1))
    return ordered[rank]


async def _single_stock_or_sale_operation(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    index: int,
) -> tuple[int, float]:
    """Ejecuta una operación crítica de stock/conversión/venta y devuelve `(status_code, latency_ms)`."""
    start = time.perf_counter()
    if index % 3 == 0:
        response = await client.post(
            "/api/v1/catalog/units/convert",
            headers=headers,
            json={
                "cantidad_compra": "2",
                "costo_compra_neto": "48000",
                "factor_compra_a_almacen": "12",
                "factor_almacen_a_receta": "1000",
            },
        )
    elif index % 3 == 1:
        response = await client.post(
            "/api/v1/inventory/kardex/movements",
            headers=headers,
            json={
                "producto_id": 701,
                "bodega_id": 1,
                "movement_type": "ENTRADA",
                "quantity": "5",
                "unit_cost": "4000",
            },
        )
    else:
        response = await client.post(
            "/api/v1/operations/sales",
            headers=headers,
            json={
                "bodega_id": 1,
                "items": [{"recipe_id": 502, "portions": "2"}],
                "recipe_ingredients": {"502": {"701": "0.25"}},
            },
        )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return response.status_code, elapsed_ms


async def _single_analytics_operation(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    index: int,
) -> tuple[int, float]:
    """Ejecuta una consulta analítica ejecutiva o de varianza de Food Cost."""
    start = time.perf_counter()
    if index % 2 == 0:
        response = await client.get(
            "/api/v1/analytics/executive-summary",
            headers=headers,
        )
    else:
        response = await client.post(
            "/api/v1/analytics/food-cost-variance",
            headers=headers,
            json={
                "theoretical_cost": "290000",
                "opening_inventory": "100000",
                "purchases": "305000",
                "closing_inventory": "100000",
                "net_sales": "1000000",
            },
        )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return response.status_code, elapsed_ms


async def run_burst_load_simulation(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    concurrency: int = 60,
    mode: str = "stock_and_sales",
    uvicorn_workers: int = 4,
) -> BurstSimulationMetrics:
    """
    Ejecuta una ráfaga asíncrona concurrente (`asyncio.gather`) contra el ASGI app
    y calcula latencias `P50`, `P95`, `P99`, errores `5xx` y throughput proyectado en `RPS`.
    """
    sem = asyncio.Semaphore(16)

    async def _bounded_call(idx: int) -> tuple[int, float]:
        async with sem:
            if mode == "analytics":
                return await _single_analytics_operation(client, headers, idx)
            return await _single_stock_or_sale_operation(client, headers, idx)

    # Warm-up de compilación de rutas y validadores Pydantic antes de medir la ventana
    for warmup_idx in range(3 if mode != "analytics" else 2):
        await _bounded_call(warmup_idx)

    wall_start = time.perf_counter()
    coros = [_bounded_call(idx) for idx in range(concurrency)]
    results: list[tuple[int, float]] = list(await asyncio.gather(*coros))
    wall_elapsed = max(time.perf_counter() - wall_start, 1e-6)

    statuses = [code for code, _ in results]
    latencies = [lat for _, lat in results]
    http_5xx = sum(1 for code in statuses if code >= 500)
    failed = sum(1 for code in statuses if code >= 400)
    single_worker_rps = float(len(results)) / wall_elapsed
    projected_rps = single_worker_rps * max(1, uvicorn_workers)

    return BurstSimulationMetrics(
        total_requests=len(results),
        http_5xx_count=http_5xx,
        failed_requests=failed,
        elapsed_seconds=wall_elapsed,
        projected_rps=projected_rps,
        p50_latency_ms=compute_percentile_ms(latencies, 50.0),
        p95_latency_ms=compute_percentile_ms(latencies, 95.0),
        p99_latency_ms=compute_percentile_ms(latencies, 99.0),
        latencies_ms=tuple(latencies),
    )
