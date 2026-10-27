"""
Primitiva de Dominio para los Paquetes de Créditos IA (`src/modules/oppy_ai/domain/ai_credit_packs.py`).
- Configurados en el Panel Administrador de OppyTec de forma independiente pero combinables con los planes base.
- Regla Inmutable: Créditos acumulables sin caducidad (`expires_in_days = None`).
- Cálculo de bonificaciones, descuentos por nivel de plan base SaaS contratado, y costo unitario por crédito en `Decimal`.
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

_TWO_DECIMALS = Decimal("0.01")
_SIX_DECIMALS = Decimal("0.000001")


@dataclass(frozen=True)
class AiCreditPack:
    """
    Entidad de dominio que representa un Paquete de Créditos IA independiente.
    Permite asociar descuentos según el plan base del cliente (`plan_tier_discounts`).
    """

    pack_id: uuid.UUID
    slug: str
    name: str
    credit_amount: Decimal
    price_clp: Decimal
    price_usd: Decimal
    bonus_credits: Decimal = Decimal("0.00")
    is_active: bool = True
    plan_tier_discounts: Mapping[str, Decimal] = field(default_factory=dict)
    expires_in_days: int | None = None

    def __post_init__(self) -> None:
        if self.credit_amount <= Decimal("0.00"):
            raise ValueError("AiCreditPack.credit_amount must be strictly positive.")
        if self.price_clp < Decimal("0.00") or self.price_usd < Decimal("0.00"):
            raise ValueError("AiCreditPack prices cannot be negative.")
        if self.bonus_credits < Decimal("0.00"):
            raise ValueError("AiCreditPack.bonus_credits cannot be negative.")
        if self.expires_in_days is not None:
            raise ValueError(
                "OppyFy AI credit packages never expire by policy (expires_in_days must be None)."
            )

    @property
    def total_credits(self) -> Decimal:
        """Total efectivo de créditos otorgados (monto base + bono)."""
        return (self.credit_amount + self.bonus_credits).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        )

    @property
    def cost_per_credit_usd(self) -> Decimal:
        """Costo unitario por crédito en USD."""
        return (self.price_usd / self.total_credits).quantize(
            _SIX_DECIMALS, rounding=ROUND_HALF_UP
        )

    @property
    def cost_per_credit_clp(self) -> Decimal:
        """Costo unitario por crédito en CLP."""
        return (self.price_clp / self.total_credits).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        )

    def calculate_effective_price(
        self,
        base_plan_tier: str | None = None,
        *,
        currency: str = "USD",
    ) -> Decimal:
        """
        Calcula el precio comercial final aplicando el descuento según el plan base SaaS contratado
        (ej. `plan_basico`: 0%, `plan_pro`: 10%, `plan_enterprise`: 20%).
        """
        base_price = self.price_usd if currency.upper() == "USD" else self.price_clp
        if not base_plan_tier:
            return base_price.quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)

        discount_percent = self.plan_tier_discounts.get(
            base_plan_tier.lower().strip(), Decimal("0.00")
        )
        if discount_percent <= Decimal("0.00"):
            return base_price.quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)

        capped_discount = min(Decimal("100.00"), max(Decimal("0.00"), discount_percent))
        multiplier = (Decimal("100.00") - capped_discount) / Decimal("100.00")
        discounted = base_price * multiplier
        return discounted.quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)


def evaluate_pack_plan_match(
    pack: AiCreditPack,
    base_plan_tier: str | None,
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Evalúa la compatibilidad entre un paquete de créditos IA y el plan base contratado:
    Retorna `(descuento_porcentual, precio_final_usd, precio_final_clp)`.
    """
    tier_key = base_plan_tier.lower().strip() if base_plan_tier else ""
    discount = pack.plan_tier_discounts.get(tier_key, Decimal("0.00"))
    final_usd = pack.calculate_effective_price(base_plan_tier, currency="USD")
    final_clp = pack.calculate_effective_price(base_plan_tier, currency="CLP")
    return discount, final_usd, final_clp


def stack_ai_credit_packs(
    current_balance: Decimal,
    purchased_packs: Sequence[AiCreditPack],
) -> Decimal:
    """
    Acumula inmediatamente el total de créditos de los paquetes comprados al saldo remanente actual.
    Regla de paridad: `1000 + 10000 = 11000.00`.
    """
    if current_balance < Decimal("0.00"):
        raise ValueError("Current credit balance cannot be negative.")

    added = sum((pkg.total_credits for pkg in purchased_packs), start=Decimal("0.00"))
    return (current_balance + added).quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)
