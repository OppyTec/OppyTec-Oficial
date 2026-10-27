"""
Servicio de Aplicación para Paquetes de Créditos IA (`src/modules/oppy_ai/application/ai_credit_packs_service.py`).
Gestiona el catálogo de paquetes de créditos de OppyFy configurables en Platform Admin (`public.ai_credit_packs`).
Reglas inmutables:
- Precios y montos exclusivamente en `Decimal(14, 2)`.
- Créditos acumulables sin caducidad (`expires_in_days = None`).
- Combinación y descuentos por nivel de plan base SaaS contratado.
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from src.core.exceptions import OppyTecError
from src.modules.oppy_ai.domain.ai_credit_packs import (
    AiCreditPack as DomainAiCreditPack,
    evaluate_pack_plan_match,
    stack_ai_credit_packs,
)

_TWO_DECIMALS = Decimal("0.01")


class AiCreditPackNotFoundError(OppyTecError):
    """Excepción RFC 7807 cuando un paquete de créditos IA no existe."""

    default_status_code = 404
    default_error_code = "OPPYFY_CREDIT_PACK_NOT_FOUND"
    default_i18n_key = "oppyfy:errors.credit_pack_not_found"
    default_title = "AI Credit Pack Not Found"


@dataclass
class CreditPackDTO:
    """DTO para transporte y serialización de paquetes de créditos IA."""

    id: int
    pack_name: str
    credits_amount: Decimal
    price_clp: Decimal
    price_usd: Decimal
    bonus_credits: Decimal = Decimal("0.00")
    is_popular: bool = False
    is_active: bool = True
    sort_order: int = 0
    plan_tier_discounts: dict[str, Decimal] = field(default_factory=dict)

    @property
    def total_credits(self) -> Decimal:
        return (self.credits_amount + self.bonus_credits).quantize(_TWO_DECIMALS, ROUND_HALF_UP)


@dataclass(frozen=True)
class CreditPackPurchaseQuoteDTO:
    """Cotización de compra de un paquete con descuento aplicado por plan base SaaS."""

    pack_id: int
    pack_name: str
    base_plan_tier: str
    original_price_usd: Decimal
    original_price_clp: Decimal
    discount_pct: Decimal
    final_price_usd: Decimal
    final_price_clp: Decimal
    total_credits: Decimal


def _build_default_sample_packs() -> list[CreditPackDTO]:
    """Catálogo inicial representativo para Platform Admin."""
    return [
        CreditPackDTO(
            id=1,
            pack_name="Starter Boost (1.000 Créditos)",
            credits_amount=Decimal("1000.00"),
            price_clp=Decimal("9990.00"),
            price_usd=Decimal("11.00"),
            bonus_credits=Decimal("0.00"),
            is_popular=False,
            is_active=True,
            sort_order=1,
            plan_tier_discounts={"plan_basico": Decimal("0.00"), "plan_pro": Decimal("10.00"), "plan_enterprise": Decimal("20.00")},
        ),
        CreditPackDTO(
            id=2,
            pack_name="Growth Pack (5.000 Créditos)",
            credits_amount=Decimal("5000.00"),
            price_clp=Decimal("44990.00"),
            price_usd=Decimal("49.00"),
            bonus_credits=Decimal("250.00"),
            is_popular=True,
            is_active=True,
            sort_order=2,
            plan_tier_discounts={"plan_basico": Decimal("0.00"), "plan_pro": Decimal("10.00"), "plan_enterprise": Decimal("20.00")},
        ),
        CreditPackDTO(
            id=3,
            pack_name="Enterprise Scale (10.000 Créditos)",
            credits_amount=Decimal("10000.00"),
            price_clp=Decimal("79990.00"),
            price_usd=Decimal("88.00"),
            bonus_credits=Decimal("1000.00"),
            is_popular=False,
            is_active=True,
            sort_order=3,
            plan_tier_discounts={"plan_basico": Decimal("0.00"), "plan_pro": Decimal("15.00"), "plan_enterprise": Decimal("25.00")},
        ),
    ]


class AiCreditPacksService:
    """
    Servicio de gestión integral de paquetes de créditos IA de `OppyFy`.
    """

    def __init__(self, sample_packs: list[CreditPackDTO] | None = None) -> None:
        self._packs: dict[int, CreditPackDTO] = {
            p.id: p for p in (sample_packs or _build_default_sample_packs())
        }
        self._next_id: int = max(self._packs.keys(), default=0) + 1

    def list_packs(self, *, is_active_only: bool = False) -> list[CreditPackDTO]:
        """Lista todos los paquetes ordenados por `sort_order` ascendente."""
        packs = list(self._packs.values())
        if is_active_only:
            packs = [p for p in packs if p.is_active]
        return sorted(packs, key=lambda p: (p.sort_order, p.id))

    def get_pack_by_id(self, pack_id: int) -> CreditPackDTO:
        """Obtiene un paquete por su ID o lanza `AiCreditPackNotFoundError`."""
        if pack_id not in self._packs:
            raise AiCreditPackNotFoundError(
                f"AI Credit Pack with ID {pack_id} was not found.",
                context={"pack_id": pack_id},
            )
        return self._packs[pack_id]

    def create_pack(
        self,
        *,
        pack_name: str,
        credits_amount: Decimal,
        price_clp: Decimal,
        price_usd: Decimal,
        bonus_credits: Decimal = Decimal("0.00"),
        is_popular: bool = False,
        is_active: bool = True,
        sort_order: int = 0,
        plan_tier_discounts: Mapping[str, Decimal] | None = None,
    ) -> CreditPackDTO:
        """Crea un nuevo paquete de créditos IA validando montos positivos."""
        if credits_amount <= Decimal("0.00"):
            raise OppyTecError("Credits amount must be strictly greater than 0.")
        if price_clp < Decimal("0.00") or price_usd < Decimal("0.00"):
            raise OppyTecError("Prices cannot be negative.")

        pack = CreditPackDTO(
            id=self._next_id,
            pack_name=pack_name,
            credits_amount=credits_amount.quantize(_TWO_DECIMALS, ROUND_HALF_UP),
            price_clp=price_clp.quantize(_TWO_DECIMALS, ROUND_HALF_UP),
            price_usd=price_usd.quantize(_TWO_DECIMALS, ROUND_HALF_UP),
            bonus_credits=bonus_credits.quantize(_TWO_DECIMALS, ROUND_HALF_UP),
            is_popular=is_popular,
            is_active=is_active,
            sort_order=sort_order,
            plan_tier_discounts=dict(plan_tier_discounts or {}),
        )
        self._packs[pack.id] = pack
        self._next_id += 1
        return pack

    def update_pack(
        self,
        pack_id: int,
        *,
        pack_name: str | None = None,
        credits_amount: Decimal | None = None,
        price_clp: Decimal | None = None,
        price_usd: Decimal | None = None,
        bonus_credits: Decimal | None = None,
        is_popular: bool | None = None,
        is_active: bool | None = None,
        sort_order: int | None = None,
        plan_tier_discounts: Mapping[str, Decimal] | None = None,
    ) -> CreditPackDTO:
        """Actualiza campos de un paquete existente."""
        pack = self.get_pack_by_id(pack_id)

        if pack_name is not None:
            pack.pack_name = pack_name
        if credits_amount is not None:
            if credits_amount <= Decimal("0.00"):
                raise OppyTecError("Credits amount must be strictly greater than 0.")
            pack.credits_amount = credits_amount.quantize(_TWO_DECIMALS, ROUND_HALF_UP)
        if price_clp is not None:
            pack.price_clp = price_clp.quantize(_TWO_DECIMALS, ROUND_HALF_UP)
        if price_usd is not None:
            pack.price_usd = price_usd.quantize(_TWO_DECIMALS, ROUND_HALF_UP)
        if bonus_credits is not None:
            pack.bonus_credits = bonus_credits.quantize(_TWO_DECIMALS, ROUND_HALF_UP)
        if is_popular is not None:
            pack.is_popular = is_popular
        if is_active is not None:
            pack.is_active = is_active
        if sort_order is not None:
            pack.sort_order = sort_order
        if plan_tier_discounts is not None:
            pack.plan_tier_discounts = dict(plan_tier_discounts)

        return pack

    def delete_pack(self, pack_id: int) -> bool:
        """Elimina un paquete del catálogo."""
        if pack_id not in self._packs:
            raise AiCreditPackNotFoundError(
                f"AI Credit Pack with ID {pack_id} was not found.",
                context={"pack_id": pack_id},
            )
        del self._packs[pack_id]
        return True

    def calculate_quote(
        self,
        pack_id: int,
        base_plan_tier: str | None = None,
    ) -> CreditPackPurchaseQuoteDTO:
        """Calcula la cotización aplicando bonificaciones y descuentos del plan SaaS base."""
        pack = self.get_pack_by_id(pack_id)
        domain_entity = DomainAiCreditPack(
            pack_id=uuid.uuid4(),
            slug=f"pack_{pack.id}",
            name=pack.pack_name,
            credit_amount=pack.credits_amount,
            price_clp=pack.price_clp,
            price_usd=pack.price_usd,
            bonus_credits=pack.bonus_credits,
            is_active=pack.is_active,
            plan_tier_discounts=pack.plan_tier_discounts,
        )
        discount_pct, final_usd, final_clp = evaluate_pack_plan_match(
            domain_entity, base_plan_tier
        )
        return CreditPackPurchaseQuoteDTO(
            pack_id=pack.id,
            pack_name=pack.pack_name,
            base_plan_tier=base_plan_tier or "standard",
            original_price_usd=pack.price_usd,
            original_price_clp=pack.price_clp,
            discount_pct=discount_pct,
            final_price_usd=final_usd,
            final_price_clp=final_clp,
            total_credits=pack.total_credits,
        )
