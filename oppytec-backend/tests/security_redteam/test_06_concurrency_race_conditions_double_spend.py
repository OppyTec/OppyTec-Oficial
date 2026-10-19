"""
Vector Red Team 06 (`tests/security_redteam/test_06_concurrency_race_conditions_double_spend.py`):
- Orden canónico de bloqueos (`ORDER BY id ASC FOR UPDATE`) para prevención determinista de Deadlocks.
- Guardia contra condición de carrera en deducción concurrente de stock de bodega (`InsufficientStockError`).
- Guardia contra doble gasto (*double-spend*) en billetera de créditos de `OppyFy` (`WorkerCreditWalletState`).
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import httpx
import pytest

from src.core.exceptions import InsufficientStockError
from src.core.guards import clear_revoked_sessions, get_rate_limiter
from src.core.security import create_access_token
from src.modules.inventory.application.inventory_service import InventoryService
from src.modules.inventory.domain.kardex_math import canonical_lock_order
from src.modules.oppy_ai.domain.credit_wallet import (
    WorkerCreditWalletState,
    deduct_worker_credits,
)

pytestmark = pytest.mark.security_redteam


def test_canonical_lock_ordering_prevents_ab_ba_deadlocks() -> None:
    """
    Verifica que dos transacciones concurrentes que solicitan los mismos productos en orden inverso
    (`[90, 10, 50, 10]` vs `[10, 50, 90]`) adquieran el lock exactamente en el mismo orden ascendente `[10, 50, 90]`.
    """
    tx_a_order = canonical_lock_order([90, 10, 50, 10, 30])
    tx_b_order = canonical_lock_order([30, 50, 90, 10])
    assert tx_a_order == [10, 30, 50, 90]
    assert tx_a_order == tx_b_order
    assert InventoryService.lock_order([400, 12, 99, 12]) == [12, 99, 400]


async def test_concurrent_stock_deduction_race_condition_blocks_overdraft() -> None:
    """
    Simula 10 corrutinas concurrentes intentando descontar `3.00 kg` cada una de una bodega que solo
    tiene `10.00 kg` de saldo inicial. Exactamente 3 deben tener éxito (`9.00 kg` consumidos, `1.00 kg` remanente)
    y las 7 restantes deben ser rechazadas con `InsufficientStockError` (cero saldos negativos).
    """
    service = InventoryService()
    lock = asyncio.Lock()

    service.register_movement(
        producto_id=700,
        bodega_id=1,
        movement_type="ENTRADA",
        quantity=Decimal("10.00"),
        unit_cost=Decimal("5000.00"),
        actor_user_id=1,
    )

    async def _attempt_withdrawal(worker_id: int) -> bool:
        async with lock:
            try:
                service.register_movement(
                    producto_id=700,
                    bodega_id=1,
                    movement_type="SALIDA",
                    quantity=Decimal("3.00"),
                    unit_cost=Decimal("5000.00"),
                    actor_user_id=worker_id,
                )
                return True
            except InsufficientStockError:
                return False

    outcomes = await asyncio.gather(*(_attempt_withdrawal(i) for i in range(10)))
    assert outcomes.count(True) == 3
    assert outcomes.count(False) == 7
    assert service.balance(700, 1) == Decimal("1.00")


async def test_concurrent_oppyfy_credit_wallet_double_spend_prevention(
    async_client: httpx.AsyncClient,
) -> None:
    """
    Verifica que una billetera con `10.00` créditos asignados sometida a 8 cobros concurrentes de `3.00`
    créditos solo autorice 3 cobros (`9.00` consumidos, `1.00` remanente) y rechace los 5 restantes
    con `INSUFFICIENT_WORKER_CREDITS`, sin permitir jamás saldo negativo.
    """
    clear_revoked_sessions()
    get_rate_limiter().reset()

    wallet = WorkerCreditWalletState(
        user_id=601,
        allocated_credits=Decimal("10.00"),
        consumed_credits=Decimal("0.00"),
        is_oppyfy_enabled=True,
    )
    wallet_lock = asyncio.Lock()

    async def _try_spend_credits() -> bool:
        nonlocal wallet
        async with wallet_lock:
            res = deduct_worker_credits(wallet, Decimal("3.00"))
            if res.allowed:
                wallet = res.updated_wallet
                return True
            return False

    results = await asyncio.gather(*(_try_spend_credits() for _ in range(8)))
    assert results.count(True) == 3
    assert results.count(False) == 5
    assert wallet.consumed_credits == Decimal("9.00")
    assert wallet.remaining_credits == Decimal("1.00")

    # Verificar también vía HTTP `/api/v1/inventory/counts` que devuelve `locked_product_ids_asc`
    token = create_access_token(
        user_id=601,
        holding_id="holding_01",
        tenant_id="tenant_rest_a",
        hierarchy_rank=20,
        role_grants=["inventory.counts.submit"],
        accessible_tenants=["tenant_rest_a"],
    )
    count_resp = await async_client.post(
        "/api/v1/inventory/counts",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tenant_rest_a",
        },
        json={
            "bodega_id": 1,
            "items": [
                {"producto_id": 99, "counted_quantity": "5", "unit_cost": "1000"},
                {"producto_id": 12, "counted_quantity": "8", "unit_cost": "1000"},
                {"producto_id": 45, "counted_quantity": "3", "unit_cost": "1000"},
            ],
        },
    )
    assert count_resp.status_code == 200
    assert count_resp.json()["locked_product_ids_asc"] == [12, 45, 99]
