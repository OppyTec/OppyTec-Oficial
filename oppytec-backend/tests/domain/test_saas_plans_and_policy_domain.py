"""
oppytec-backend/tests/domain/test_saas_plans_and_policy_domain.py
Pruebas unitarias de dominio DDD para:
1. Value Object `PlanTier` (invariantes, comparaciones, tipos).
2. Conversión determinista de tokens y créditos IA (`TokenCreditConversionRate`).
3. Costos reales de API de Google Gemini en USD (`calculate_real_api_cost_usd`).
4. Simulación de rentabilidad, valor comercial y márgenes (> 95%) (`SimulatedProfitMargin`).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.tenancy.domain.saas_policy_math import (
    DEFAULT_CREDIT_PRICE_CLP,
    DEFAULT_CREDIT_PRICE_USD,
    DEFAULT_MONTHLY_CREDITS,
    DEFAULT_TOKENS_PER_CREDIT,
    DEFAULT_USD_TO_CLP_RATE,
    GEMINI_FLASH_BLENDED_COST_PER_M,
    GEMINI_FLASH_INPUT_COST_PER_M,
    GEMINI_FLASH_OUTPUT_COST_PER_M,
    GEMINI_PRO_BLENDED_COST_PER_M,
    GEMINI_PRO_INPUT_COST_PER_M,
    GEMINI_PRO_OUTPUT_COST_PER_M,
    PlanTier,
    SimulatedProfitMargin,
    TokenCreditConversionRate,
    calculate_real_api_cost_usd,
    calculate_simulated_profit_margin,
)

pytestmark = pytest.mark.unit


# ============================================================================
# 1. VALUE OBJECT: PlanTier
# ============================================================================


class TestPlanTier:
    """Validación exhaustiva de invariantes de PlanTier."""

    def test_creation_valid_int_str_tier(self) -> None:
        t1 = PlanTier(1)
        t2 = PlanTier("2")
        t3 = PlanTier("  3  ")
        t4 = PlanTier(t1)

        assert t1.value == 1
        assert t2.value == 2
        assert t3.value == 3
        assert t4.value == 1
        assert int(t1) == 1
        assert str(t1) == "Tier 1"
        assert repr(t1) == "PlanTier(1)"

    def test_tier_must_be_strictly_positive(self) -> None:
        with pytest.raises(ValueError, match="PlanTier must be strictly positive"):
            PlanTier(0)
        with pytest.raises(ValueError, match="PlanTier must be strictly positive"):
            PlanTier(-1)
        with pytest.raises(ValueError, match="PlanTier must be strictly positive"):
            PlanTier("-5")

    def test_boolean_strictly_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Boolean is strictly forbidden"):
            PlanTier(True)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Boolean is strictly forbidden"):
            PlanTier(False)  # type: ignore[arg-type]

    def test_float_strictly_forbidden(self) -> None:
        with pytest.raises(TypeError, match="Float is strictly forbidden"):
            PlanTier(1.0)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Float is strictly forbidden"):
            PlanTier(2.5)  # type: ignore[arg-type]

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid integer representation"):
            PlanTier("basic")
        with pytest.raises(ValueError, match="Invalid integer representation"):
            PlanTier("1.5")

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError, match="Unsupported type"):
            PlanTier([])  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Unsupported type"):
            PlanTier({})  # type: ignore[arg-type]

    def test_comparisons(self) -> None:
        t1 = PlanTier(1)
        t2 = PlanTier(2)
        t3 = PlanTier(1)

        assert t1 < t2
        assert t1 <= t2
        assert t1 <= t3
        assert t2 > t1
        assert t2 >= t1
        assert t1 == t3
        assert t1 == 1
        assert t2 == 2
        assert not (t1 == t2)
        assert not (t1 == "1")
        assert not (t1 == object())


# ============================================================================
# 2. TOKEN & CREDIT CONVERSION
# ============================================================================


class TestTokenCreditConversion:
    """Pruebas del conversor bidireccional determinista entre tokens y créditos IA."""

    def test_default_rate_instantiation(self) -> None:
        rate = TokenCreditConversionRate()
        assert rate.tokens_per_credit == 1000

    def test_custom_rate_valid(self) -> None:
        rate = TokenCreditConversionRate(tokens_per_credit=500)
        assert rate.tokens_per_credit == 500

    def test_rate_invariants(self) -> None:
        rate_str = TokenCreditConversionRate(tokens_per_credit="1000")  # type: ignore[arg-type]
        assert rate_str.tokens_per_credit == 1000

        with pytest.raises(TypeError, match="Invalid type for tokens_per_credit"):
            TokenCreditConversionRate(tokens_per_credit=[])  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="must be strictly positive"):
            TokenCreditConversionRate(tokens_per_credit=0)
        with pytest.raises(ValueError, match="must be strictly positive"):
            TokenCreditConversionRate(tokens_per_credit=-500)
        with pytest.raises(TypeError, match="Boolean is forbidden"):
            TokenCreditConversionRate(tokens_per_credit=True)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Float is strictly forbidden"):
            TokenCreditConversionRate(tokens_per_credit=1000.0)  # type: ignore[arg-type]

    def test_tokens_to_credits_with_round_up(self) -> None:
        rate = TokenCreditConversionRate(tokens_per_credit=1000)

        # 0 tokens -> 0 créditos
        assert rate.tokens_to_credits(0) == 0
        assert rate.tokens_to_credits(Decimal("0")) == 0

        # Fracciones mínimas consumen al menos 1 crédito (regla anti-abuso)
        assert rate.tokens_to_credits(1) == 1
        assert rate.tokens_to_credits(999) == 1
        assert rate.tokens_to_credits(1000) == 1

        # 1001 tokens salta a 2 créditos
        assert rate.tokens_to_credits(1001) == 2
        assert rate.tokens_to_credits(1999) == 2
        assert rate.tokens_to_credits(2000) == 2

        # Cifras mayores
        assert rate.tokens_to_credits(250000) == 250
        assert rate.tokens_to_credits(250001) == 251

    def test_tokens_to_credits_with_round_half_up(self) -> None:
        rate = TokenCreditConversionRate(tokens_per_credit=1000)

        # Con round_up=False, redondea al entero más cercano
        assert rate.tokens_to_credits(499, round_up=False) == 0
        assert rate.tokens_to_credits(500, round_up=False) == 1
        assert rate.tokens_to_credits(1499, round_up=False) == 1
        assert rate.tokens_to_credits(1500, round_up=False) == 2

    def test_tokens_to_credits_negative_raises(self) -> None:
        rate = TokenCreditConversionRate()
        with pytest.raises(ValueError, match="cannot be negative"):
            rate.tokens_to_credits(-10)

    def test_tokens_to_credits_forbidden_types(self) -> None:
        rate = TokenCreditConversionRate()
        with pytest.raises(TypeError, match="Boolean is forbidden"):
            rate.tokens_to_credits(True)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Float is strictly forbidden"):
            rate.tokens_to_credits(1000.5)  # type: ignore[arg-type]

    def test_credits_to_tokens_conversion(self) -> None:
        rate = TokenCreditConversionRate(tokens_per_credit=1000)

        assert rate.credits_to_tokens(0) == 0
        assert rate.credits_to_tokens(1) == 1000
        assert rate.credits_to_tokens(2000) == 2000000
        assert rate.credits_to_tokens(Decimal("15.5")) == 15500

    def test_credits_to_tokens_invariants(self) -> None:
        rate = TokenCreditConversionRate()
        with pytest.raises(ValueError, match="cannot be negative"):
            rate.credits_to_tokens(-5)
        with pytest.raises(TypeError, match="Boolean is forbidden"):
            rate.credits_to_tokens(False)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Float is strictly forbidden"):
            rate.credits_to_tokens(10.5)  # type: ignore[arg-type]


# ============================================================================
# 3. REAL API COSTS (Google Gemini Pricing)
# ============================================================================


class TestRealApiCosts:
    """Pruebas del cálculo de costos reales de API en USD."""

    def test_gemini_flash_blended_cost(self) -> None:
        # 1M tokens con Gemini Flash blended ($0.150 / 1M) -> $0.150000 USD
        cost_1m = calculate_real_api_cost_usd(1000000, model="gemini-1.5-flash")
        assert cost_1m == Decimal("0.150000")

        # 2M tokens -> $0.300000 USD
        cost_2m = calculate_real_api_cost_usd(2000000, model="gemini-1.5-flash")
        assert cost_2m == Decimal("0.300000")

    def test_gemini_flash_split_input_output(self) -> None:
        # Input: $0.075 / 1M, Output: $0.300 / 1M
        # 1M input + 1M output = $0.375000 USD
        cost = calculate_real_api_cost_usd(
            tokens=2000000,
            model="gemini-1.5-flash",
            input_tokens=1000000,
            output_tokens=1000000,
        )
        assert cost == Decimal("0.375000")

    def test_gemini_pro_blended_and_split(self) -> None:
        # Blended: $7.00 / 1M
        cost_pro = calculate_real_api_cost_usd(1000000, model="gemini-1.5-pro")
        assert cost_pro == Decimal("7.000000")

        # Split: 1M input ($3.50) + 1M output ($10.50) = $14.000000
        cost_split = calculate_real_api_cost_usd(
            tokens=2000000,
            model="gemini-1.5-pro",
            input_tokens=1000000,
            output_tokens=1000000,
        )
        assert cost_split == Decimal("14.000000")

    def test_custom_cost_per_million(self) -> None:
        cost = calculate_real_api_cost_usd(
            tokens=500000,
            model="custom",
            custom_cost_per_million=Decimal("2.000"),
        )
        assert cost == Decimal("1.000000")

    def test_api_cost_invariants(self) -> None:
        with pytest.raises(ValueError, match="Tokens cannot be negative"):
            calculate_real_api_cost_usd(-100)
        with pytest.raises(TypeError, match="Boolean is forbidden"):
            calculate_real_api_cost_usd(True)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Float is strictly forbidden"):
            calculate_real_api_cost_usd(1000.5)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="Input and output tokens cannot be negative"):
            calculate_real_api_cost_usd(100, input_tokens=-1, output_tokens=101)
        with pytest.raises(ValueError, match="Unknown model pricing tier"):
            calculate_real_api_cost_usd(100, model="unknown_tier")  # type: ignore[arg-type]


# ============================================================================
# 4. SIMULATED PROFIT MARGIN & FINOPS SAAS
# ============================================================================


class TestSimulatedProfitMargin:
    """Pruebas de la simulación financiera SaaS y margen comercial (> 95%)."""

    def test_standard_saas_policy_margin(self) -> None:
        # 2,000 créditos base * 1,000 tokens = 2,000,000 tokens
        # Costo API Gemini Flash: 2M * 0.15 / 1M = 0.300000 USD
        # Costo CLP @ 950: 0.30 * 950 = 285.00 CLP
        # Valor Comercial CLP @ 15.00: 2,000 * 15 = 30,000.00 CLP
        # Margen CLP: 30,000 - 285 = 29,715.00 CLP
        # Margen %: (29,715 / 30,000) * 100 = 99.05%
        sim = calculate_simulated_profit_margin(
            credits=2000,
            tokens_per_credit=1000,
            credit_price_clp=Decimal("15.00"),
            credit_price_usd=Decimal("0.0150"),
            usd_to_clp_fx_rate=Decimal("950.00"),
        )

        assert sim.credits == 2000
        assert sim.tokens_per_credit == 1000
        assert sim.simulated_tokens_monthly == 2000000
        assert sim.simulated_cost_usd == Decimal("0.300000")
        assert sim.simulated_cost_clp == Decimal("285.00")
        assert sim.simulated_commercial_value_clp == Decimal("30000.00")
        assert sim.simulated_commercial_value_usd == Decimal("30.00")
        assert sim.gross_margin_clp == Decimal("29715.00")
        assert sim.gross_margin_usd == Decimal("29.70")
        assert sim.gross_margin_pct == Decimal("99.05")
        assert sim.is_margin_above_95_pct is True

    def test_zero_credits_edge_case(self) -> None:
        sim = calculate_simulated_profit_margin(credits=0)
        assert sim.simulated_tokens_monthly == 0
        assert sim.simulated_commercial_value_clp == Decimal("0.00")
        assert sim.gross_margin_pct == Decimal("0")
        assert sim.is_margin_above_95_pct is False

    def test_low_margin_scenario(self) -> None:
        # Precios irrisorios que bajan el margen por debajo del 95%
        sim = calculate_simulated_profit_margin(
            credits=1000,
            tokens_per_credit=1000,
            credit_price_clp=Decimal("0.20"),  # 1000 * 0.20 = 200 CLP
            usd_to_clp_fx_rate=Decimal("1000.00"),
            # Costo 1M tokens @ 0.15 = 0.15 USD * 1000 = 150 CLP
            # Margen = (200 - 150) / 200 = 25%
        )
        assert sim.is_margin_above_95_pct is False
        assert sim.gross_margin_pct == Decimal("25.00")

    def test_margin_calculation_invariants(self) -> None:
        with pytest.raises(ValueError, match="credits cannot be negative"):
            calculate_simulated_profit_margin(credits=-1)
        with pytest.raises(ValueError, match="tokens_per_credit must be strictly positive"):
            calculate_simulated_profit_margin(tokens_per_credit=0)
        with pytest.raises(ValueError, match="Credit prices cannot be negative"):
            calculate_simulated_profit_margin(credit_price_clp=Decimal("-1.00"))
        with pytest.raises(ValueError, match="FX rate must be strictly positive"):
            calculate_simulated_profit_margin(usd_to_clp_fx_rate=Decimal("0.00"))

    def test_float_strictly_forbidden_in_simulated_margin(self) -> None:
        with pytest.raises(TypeError, match="Boolean is forbidden"):
            calculate_simulated_profit_margin(credit_price_clp=True)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            calculate_simulated_profit_margin(credit_price_clp=15.0)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Float precision IEEE-754 is strictly forbidden"):
            calculate_simulated_profit_margin(usd_to_clp_fx_rate=950.5)  # type: ignore[arg-type]
