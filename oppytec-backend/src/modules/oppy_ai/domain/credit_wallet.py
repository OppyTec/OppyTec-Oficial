"""
Economía de Paquetes de Créditos Acumulables sin Caducidad (`src/modules/oppy_ai/domain/credit_wallet.py`).
- Todos los cálculos usan exclusivamente `decimal.Decimal` (cero `float`).
- Los paquetes de créditos son independientes del plan base, 100% acumulables (`1000 + 10000 = 11000`)
  y sin fecha de vencimiento (`expires_in_days = None`).
- El Propietario distribuye cuotas a la billetera de cada trabajador (`WorkerCreditWalletState`)
  y controla el interruptor `is_oppyfy_enabled`, cupos máximos y políticas de cuota.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

_TWO_DECIMALS = Decimal("0.01")


@dataclass(frozen=True)
class CreditPackageSpec:
    """Especificación de un paquete de créditos comprable sin caducidad (`expires_in_days=None`)."""

    package_id: uuid.UUID
    slug: str
    name: str
    credit_amount: Decimal
    price_clp: Decimal
    price_usd: Decimal
    expires_in_days: int | None = None

    def __post_init__(self) -> None:
        if self.credit_amount <= Decimal("0.00"):
            raise ValueError("CreditPackageSpec.credit_amount must be strictly positive.")
        if self.expires_in_days is not None:
            raise ValueError(
                "OppyFy credit packages never expire by policy (expires_in_days must be None)."
            )


@dataclass(frozen=True)
class WorkerQuotaPolicy:
    """
    Política de cuota y cupos por trabajador configurables por el Propietario del Tenant:
    - `max_daily_credits`: límite máximo de créditos que el trabajador puede consumir en 24 horas.
    - `max_per_query_credits`: límite de costo máximo por consulta individual.
    - `assigned_credit_ceiling`: tope total acumulado permitido en el ciclo de trabajo.
    """

    max_daily_credits: Decimal | None = None
    max_per_query_credits: Decimal | None = None
    assigned_credit_ceiling: Decimal | None = None

    def __post_init__(self) -> None:
        if self.max_daily_credits is not None and self.max_daily_credits <= Decimal("0.00"):
            raise ValueError("WorkerQuotaPolicy.max_daily_credits must be positive.")
        if self.max_per_query_credits is not None and self.max_per_query_credits <= Decimal("0.00"):
            raise ValueError("WorkerQuotaPolicy.max_per_query_credits must be positive.")
        if self.assigned_credit_ceiling is not None and self.assigned_credit_ceiling <= Decimal("0.00"):
            raise ValueError("WorkerQuotaPolicy.assigned_credit_ceiling must be positive.")


@dataclass(frozen=True)
class HoldingCreditPool:
    """Bolsa acumulable de créditos del Holding/Tenant sin caducidad mensual."""

    holding_id: uuid.UUID
    total_purchased_credits: Decimal
    allocated_to_workers_credits: Decimal

    @property
    def unallocated_credits(self) -> Decimal:
        """Saldo remanente en la bolsa del Holding disponible para asignar a trabajadores."""
        return (self.total_purchased_credits - self.allocated_to_workers_credits).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        )


@dataclass(frozen=True)
class WorkerCreditWalletState:
    """Estado inmutable de la billetera individual de un trabajador (`OppyfyWorkerCreditWallet`)."""

    user_id: int
    allocated_credits: Decimal
    consumed_credits: Decimal
    is_oppyfy_enabled: bool = True
    assigned_credit_ceiling: Decimal | None = None

    @property
    def remaining_credits(self) -> Decimal:
        """Créditos disponibles actuales del trabajador."""
        return (self.allocated_credits - self.consumed_credits).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        )

    @property
    def is_ceiling_reached(self) -> bool:
        """Indica si el trabajador ha alcanzado su techo asignado de créditos."""
        if self.assigned_credit_ceiling is None:
            return False
        return self.consumed_credits >= self.assigned_credit_ceiling


@dataclass(frozen=True)
class CreditDeductionResult:
    """Resultado de evaluación y descuento atómico de créditos por consulta."""

    allowed: bool
    reason_code: str
    deducted_credits: Decimal
    updated_wallet: WorkerCreditWalletState


def calculate_wallet_balance(
    current_balance: Decimal,
    added_credits: Decimal,
) -> Decimal:
    """
    Calcula el nuevo balance acumulable:
    `balance nuevo = balance actual + créditos de paquetes comprados`.
    """
    if current_balance < Decimal("0.00"):
        raise ValueError("Current credit balance cannot be negative.")
    if added_credits < Decimal("0.00"):
        raise ValueError("Added credits cannot be negative.")
    return (current_balance + added_credits).quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)


def stack_credit_packages(
    current_balance: Decimal,
    purchased_packages: Sequence[Any],
) -> Decimal:
    """
    Suma inmediatamente paquetes de créditos comprados al saldo remanente actual sin caducidad:
    ej. `1000 + 10000 = 11000.00`. Compatible con `CreditPackageSpec` y `AiCreditPack`.
    """
    if current_balance < Decimal("0.00"):
        raise ValueError("Current credit balance cannot be negative.")

    added = Decimal("0.00")
    for pkg in purchased_packages:
        amount = getattr(pkg, "total_credits", getattr(pkg, "credit_amount", None))
        if amount is None:
            raise TypeError("Object in purchased_packages must have credit_amount or total_credits.")
        added += Decimal(str(amount))

    return calculate_wallet_balance(current_balance, added)


def allocate_credits_to_worker(
    pool: HoldingCreditPool,
    wallet: WorkerCreditWalletState,
    amount_to_allocate: Decimal,
) -> tuple[HoldingCreditPool, WorkerCreditWalletState]:
    """
    Transfiere créditos desde la bolsa del Holding (`HoldingCreditPool`) hacia la billetera
    individual del trabajador (`WorkerCreditWalletState`).
    """
    quantized_amount = amount_to_allocate.quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)
    if quantized_amount <= Decimal("0.00"):
        raise ValueError("Allocation amount must be greater than Decimal('0.00').")
    if quantized_amount > pool.unallocated_credits:
        raise ValueError("Insufficient unallocated credits in HoldingCreditPool.")

    updated_pool = HoldingCreditPool(
        holding_id=pool.holding_id,
        total_purchased_credits=pool.total_purchased_credits,
        allocated_to_workers_credits=(pool.allocated_to_workers_credits + quantized_amount).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        ),
    )
    updated_wallet = WorkerCreditWalletState(
        user_id=wallet.user_id,
        allocated_credits=(wallet.allocated_credits + quantized_amount).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        ),
        consumed_credits=wallet.consumed_credits,
        is_oppyfy_enabled=wallet.is_oppyfy_enabled,
        assigned_credit_ceiling=wallet.assigned_credit_ceiling,
    )
    return updated_pool, updated_wallet


def check_worker_quota_policy(
    wallet: WorkerCreditWalletState,
    credits_to_deduct: Decimal,
    *,
    quota_policy: WorkerQuotaPolicy | None = None,
    daily_consumed_credits: Decimal = Decimal("0.00"),
) -> tuple[bool, str | None]:
    """
    Verifica si una deducción cumple con las políticas de cuota y cupos asignados al trabajador.
    """
    effective_ceiling = wallet.assigned_credit_ceiling
    if effective_ceiling is None and quota_policy is not None:
        effective_ceiling = quota_policy.assigned_credit_ceiling

    if effective_ceiling is not None:
        if (wallet.consumed_credits + credits_to_deduct) > effective_ceiling:
            return False, "WORKER_CREDIT_CEILING_EXCEEDED"

    if quota_policy is not None:
        if (
            quota_policy.max_per_query_credits is not None
            and credits_to_deduct > quota_policy.max_per_query_credits
        ):
            return False, "EXCEEDS_PER_QUERY_QUOTA"

        if (
            quota_policy.max_daily_credits is not None
            and (daily_consumed_credits + credits_to_deduct) > quota_policy.max_daily_credits
        ):
            return False, "EXCEEDS_DAILY_QUOTA"

    return True, None


def deduct_worker_credits(
    wallet: WorkerCreditWalletState,
    credits_to_deduct: Decimal,
    *,
    quota_policy: WorkerQuotaPolicy | None = None,
    daily_consumed_credits: Decimal = Decimal("0.00"),
) -> CreditDeductionResult:
    """
    Verifica `is_oppyfy_enabled`, saldo disponible y políticas de cuota antes de
    descontar atómicamente los créditos con precisión `Decimal`.
    """
    quantized_cost = credits_to_deduct.quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)
    if quantized_cost < Decimal("0.00"):
        raise ValueError("credits_to_deduct cannot be negative.")

    if not wallet.is_oppyfy_enabled:
        return CreditDeductionResult(
            allowed=False,
            reason_code="OPPYFY_DISABLED_FOR_WORKER",
            deducted_credits=Decimal("0.00"),
            updated_wallet=wallet,
        )

    if wallet.remaining_credits < quantized_cost:
        return CreditDeductionResult(
            allowed=False,
            reason_code="INSUFFICIENT_WORKER_CREDITS",
            deducted_credits=Decimal("0.00"),
            updated_wallet=wallet,
        )

    quota_ok, quota_reason = check_worker_quota_policy(
        wallet,
        quantized_cost,
        quota_policy=quota_policy,
        daily_consumed_credits=daily_consumed_credits,
    )
    if not quota_ok:
        return CreditDeductionResult(
            allowed=False,
            reason_code=quota_reason or "QUOTA_POLICY_VIOLATION",
            deducted_credits=Decimal("0.00"),
            updated_wallet=wallet,
        )

    new_wallet = WorkerCreditWalletState(
        user_id=wallet.user_id,
        allocated_credits=wallet.allocated_credits,
        consumed_credits=(wallet.consumed_credits + quantized_cost).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        ),
        is_oppyfy_enabled=wallet.is_oppyfy_enabled,
        assigned_credit_ceiling=wallet.assigned_credit_ceiling,
    )
    return CreditDeductionResult(
        allowed=True,
        reason_code="CREDITS_DEDUCTED_OK",
        deducted_credits=quantized_cost,
        updated_wallet=new_wallet,
    )
