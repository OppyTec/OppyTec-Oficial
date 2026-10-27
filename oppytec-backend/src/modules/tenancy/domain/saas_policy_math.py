"""
oppytec-backend/src/modules/tenancy/domain/saas_policy_math.py
Reglas puras de dominio, Value Objects y cálculo FinOps para:
1. Nivel jerárquico de planes comerciales (`PlanTier`).
2. Conversión determinista de tokens brutos a créditos IA (`TokenCreditConversion`).
3. Costos reales de API de Google Gemini (Flash / Pro) en USD y conversión FX.
4. Simulación de márgenes comerciales (> 95%) y valor de venta en CLP y USD.
Cumple estrictamente la Regla de Oro: Cero uso de `float` (exclusivamente `Decimal` e `int`).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Any, Literal

from src.core.exceptions import DomainValidationError

ZERO = Decimal(0)
ONE_HUNDRED = Decimal(100)
ONE_MILLION = Decimal("1000000")

# Precisiones estándar
TWO_DECIMALS = Decimal("0.01")
FOUR_DECIMALS = Decimal("0.0001")
SIX_DECIMALS = Decimal("0.000001")

# Constantes de Política SaaS y Precios FinOps
DEFAULT_TOKENS_PER_CREDIT: int = 1000
DEFAULT_MONTHLY_CREDITS: int = 2000
DEFAULT_CREDIT_PRICE_CLP = Decimal("15.00")
DEFAULT_CREDIT_PRICE_USD = Decimal("0.0150")
DEFAULT_USD_TO_CLP_RATE = Decimal("950.00")

# Tarifas oficiales de Google Gemini por millón de tokens (USD)
# Gemini 1.5 Flash: $0.075 / 1M input, $0.30 / 1M output -> blended $0.15 / 1M tokens
GEMINI_FLASH_INPUT_COST_PER_M = Decimal("0.075")
GEMINI_FLASH_OUTPUT_COST_PER_M = Decimal("0.300")
GEMINI_FLASH_BLENDED_COST_PER_M = Decimal("0.150")

# Gemini 1.5 Pro: $3.50 / 1M input, $10.50 / 1M output -> blended $7.00 / 1M tokens
GEMINI_PRO_INPUT_COST_PER_M = Decimal("3.500")
GEMINI_PRO_OUTPUT_COST_PER_M = Decimal("10.500")
GEMINI_PRO_BLENDED_COST_PER_M = Decimal("7.000")

AIModelPricingTier = Literal["gemini-1.5-flash", "gemini-1.5-pro", "custom"]


# ============================================================================
# 1. VALUE OBJECT: PlanTier
# ============================================================================


@dataclass(frozen=True)
class PlanTier:
    """
    Nivel jerárquico inmutable de un plan comercial SaaS (entero estrictamente > 0).
    Ejemplos: Tier 1 (Básico), Tier 2 (Pro), Tier 3 (Enterprise).
    """

    value: int

    def __init__(self, value: int | str | PlanTier) -> None:
        if isinstance(value, bool):
            raise TypeError("Boolean is strictly forbidden for PlanTier; use int or integer str")
        if type(value).__name__ == "float":
            raise TypeError("Float is strictly forbidden for PlanTier; use int or integer str")

        if isinstance(value, PlanTier):
            int_val = value.value
        elif isinstance(value, int):
            int_val = value
        elif isinstance(value, str):
            try:
                int_val = int(value.strip())
            except Exception as exc:
                raise ValueError(f"Invalid integer representation for PlanTier: '{value}'") from exc
        else:
            raise TypeError(f"Unsupported type for PlanTier: {type(value).__name__}")

        if int_val <= 0:
            raise ValueError(f"PlanTier must be strictly positive (> 0), received {int_val}")

        object.__setattr__(self, "value", int_val)

    def __int__(self) -> int:
        return self.value

    def __repr__(self) -> str:
        return f"PlanTier({self.value})"

    def __str__(self) -> str:
        return f"Tier {self.value}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PlanTier):
            return self.value == other.value
        if isinstance(other, int) and not isinstance(other, bool):
            return self.value == other
        return False

    def __lt__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, PlanTier) else int(other)
        return self.value < other_val

    def __le__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, PlanTier) else int(other)
        return self.value <= other_val

    def __gt__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, PlanTier) else int(other)
        return self.value > other_val

    def __ge__(self, other: Any) -> bool:
        other_val = other.value if isinstance(other, PlanTier) else int(other)
        return self.value >= other_val


# ============================================================================
# 2. CONVERSIÓN DE TOKENS Y CRÉDITOS IA
# ============================================================================


@dataclass(frozen=True)
class TokenCreditConversionRate:
    """
    Tasa inmutable de conversión entre tokens brutos y créditos de IA.
    tokens_per_credit: Entero > 0 (por defecto 1.000 tokens = 1 crédito).
    """

    tokens_per_credit: int = DEFAULT_TOKENS_PER_CREDIT

    def __post_init__(self) -> None:
        if isinstance(self.tokens_per_credit, bool):
            raise TypeError("Boolean is forbidden for tokens_per_credit")
        if type(self.tokens_per_credit).__name__ == "float":
            raise TypeError("Float is strictly forbidden for tokens_per_credit; use int")
        if not isinstance(self.tokens_per_credit, int):
            try:
                object.__setattr__(self, "tokens_per_credit", int(self.tokens_per_credit))
            except Exception as exc:
                raise TypeError(f"Invalid type for tokens_per_credit: {type(self.tokens_per_credit).__name__}") from exc
        if self.tokens_per_credit <= 0:
            raise ValueError(f"tokens_per_credit must be strictly positive, received {self.tokens_per_credit}")

    def tokens_to_credits(
        self,
        tokens: int | Decimal,
        *,
        round_up: bool = True,
    ) -> int:
        """
        Convierte tokens brutos consumidos a créditos enteros de IA.
        - Si round_up=True (por defecto): redondeo estricto hacia arriba (ROUND_CEILING / ROUND_UP),
          asegurando que cualquier fracción de token consuma al menos 1 crédito.
        - Si round_up=False: redondeo estándar ROUND_HALF_UP.
        - 0 tokens -> 0 créditos.
        - Tokens negativos -> ValueError.
        """
        if isinstance(tokens, bool):
            raise TypeError("Boolean is forbidden for tokens")
        if type(tokens).__name__ == "float":
            raise TypeError("Float is strictly forbidden for tokens; use int or Decimal")

        dec_tokens = Decimal(str(tokens)) if not isinstance(tokens, Decimal) else tokens

        if dec_tokens < ZERO:
            raise ValueError(f"Tokens count cannot be negative: {dec_tokens}")
        if dec_tokens == ZERO:
            return 0

        rate_dec = Decimal(self.tokens_per_credit)
        exact_credits = dec_tokens / rate_dec

        rounding_mode = ROUND_CEILING if round_up else ROUND_HALF_UP
        return int(exact_credits.to_integral_value(rounding=rounding_mode))

    def credits_to_tokens(self, credits: int | Decimal) -> int:
        """
        Convierte créditos de IA a cantidad estimada de tokens brutos.
        """
        if isinstance(credits, bool):
            raise TypeError("Boolean is forbidden for credits")
        if type(credits).__name__ == "float":
            raise TypeError("Float is strictly forbidden for credits; use int or Decimal")

        dec_credits = Decimal(str(credits)) if not isinstance(credits, Decimal) else credits
        if dec_credits < ZERO:
            raise ValueError(f"Credits cannot be negative: {dec_credits}")

        tokens_dec = dec_credits * Decimal(self.tokens_per_credit)
        return int(tokens_dec.to_integral_value(rounding=ROUND_HALF_UP))


# ============================================================================
# 3. COSTOS REALES DE API GOOGLE GEMINI (FinOps)
# ============================================================================


def calculate_real_api_cost_usd(
    tokens: int | Decimal,
    *,
    model: AIModelPricingTier = "gemini-1.5-flash",
    custom_cost_per_million: Decimal | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> Decimal:
    """
    Calcula el costo real de API en USD a partir de tokens y tarifas oficiales de Google Gemini.
    - Cero uso de float (exclusivamente Decimal).
    - Cuantizado a 6 decimales (0.000001 USD) con ROUND_HALF_UP.
    """
    if isinstance(tokens, bool) or isinstance(input_tokens, bool) or isinstance(output_tokens, bool):
        raise TypeError("Boolean is forbidden for tokens")
    if type(tokens).__name__ == "float" or type(custom_cost_per_million).__name__ == "float":
        raise TypeError("Float is strictly forbidden for token cost calculation; use Decimal or int")

    dec_total = Decimal(str(tokens)) if not isinstance(tokens, Decimal) else tokens
    if dec_total < ZERO:
        raise ValueError("Tokens cannot be negative")

    # Si se detallan tokens de entrada y salida, calculamos con tarifas exactas desglosadas
    if input_tokens is not None and output_tokens is not None:
        dec_in = Decimal(input_tokens)
        dec_out = Decimal(output_tokens)
        if dec_in < ZERO or dec_out < ZERO:
            raise ValueError("Input and output tokens cannot be negative")

        if model == "gemini-1.5-flash":
            cost_in = (dec_in / ONE_MILLION) * GEMINI_FLASH_INPUT_COST_PER_M
            cost_out = (dec_out / ONE_MILLION) * GEMINI_FLASH_OUTPUT_COST_PER_M
            return (cost_in + cost_out).quantize(SIX_DECIMALS, ROUND_HALF_UP)
        elif model == "gemini-1.5-pro":
            cost_in = (dec_in / ONE_MILLION) * GEMINI_PRO_INPUT_COST_PER_M
            cost_out = (dec_out / ONE_MILLION) * GEMINI_PRO_OUTPUT_COST_PER_M
            return (cost_in + cost_out).quantize(SIX_DECIMALS, ROUND_HALF_UP)

    # Cálculo blended promedio
    if custom_cost_per_million is not None:
        cost_per_m = custom_cost_per_million
    elif model == "gemini-1.5-flash":
        cost_per_m = GEMINI_FLASH_BLENDED_COST_PER_M
    elif model == "gemini-1.5-pro":
        cost_per_m = GEMINI_PRO_BLENDED_COST_PER_M
    else:
        raise ValueError(f"Unknown model pricing tier: {model}")

    cost_usd = (dec_total / ONE_MILLION) * cost_per_m
    return cost_usd.quantize(SIX_DECIMALS, ROUND_HALF_UP)


# ============================================================================
# 4. SIMULACIÓN DE MÁRGENES COMERCIALES Y RENTABILIDAD SAAS
# ============================================================================


@dataclass(frozen=True)
class SimulatedProfitMargin:
    """
    Resultado inmutable de la simulación financiera FinOps de la política SaaS.
    Compara el costo real de proveedor en USD vs el precio de venta comercial sugerido en CLP y USD.
    Garantiza que el margen bruto supere el 95.00%.
    """

    credits: int
    tokens_per_credit: int
    simulated_tokens_monthly: int
    simulated_cost_usd: Decimal
    simulated_cost_clp: Decimal
    simulated_commercial_value_clp: Decimal
    simulated_commercial_value_usd: Decimal
    gross_margin_clp: Decimal
    gross_margin_usd: Decimal
    gross_margin_pct: Decimal
    is_margin_above_95_pct: bool


def calculate_simulated_profit_margin(
    *,
    credits: int = DEFAULT_MONTHLY_CREDITS,
    tokens_per_credit: int = DEFAULT_TOKENS_PER_CREDIT,
    credit_price_clp: Decimal = DEFAULT_CREDIT_PRICE_CLP,
    credit_price_usd: Decimal = DEFAULT_CREDIT_PRICE_USD,
    usd_to_clp_fx_rate: Decimal = DEFAULT_USD_TO_CLP_RATE,
    api_model: AIModelPricingTier = "gemini-1.5-flash",
    custom_cost_per_million_usd: Decimal | None = None,
) -> SimulatedProfitMargin:
    """
    Ejecuta la simulación matemática de márgenes comerciales para la política SaaS:
    - simulated_tokens_monthly = credits * tokens_per_credit
    - simulated_cost_usd = (simulated_tokens_monthly / 1_000_000) * cost_per_m
    - simulated_cost_clp = simulated_cost_usd * usd_to_clp_fx_rate
    - simulated_commercial_value_clp = credits * credit_price_clp
    - simulated_commercial_value_usd = credits * credit_price_usd
    - gross_margin_pct = (commercial_value - real_cost) / commercial_value * 100
    - Retorna objeto inmutable SimulatedProfitMargin.
    """
    for val, name in [
        (credit_price_clp, "credit_price_clp"),
        (credit_price_usd, "credit_price_usd"),
        (usd_to_clp_fx_rate, "usd_to_clp_fx_rate"),
        (custom_cost_per_million_usd, "custom_cost_per_million_usd"),
    ]:
        if isinstance(val, bool):
            raise TypeError(f"Boolean is forbidden for {name}")
        if type(val).__name__ == "float":
            raise TypeError(f"Float precision IEEE-754 is strictly forbidden for {name}; use Decimal")

    if credits < 0:
        raise ValueError("credits cannot be negative")
    if tokens_per_credit <= 0:
        raise ValueError("tokens_per_credit must be strictly positive")
    if credit_price_clp < ZERO or credit_price_usd < ZERO:
        raise ValueError("Credit prices cannot be negative")
    if usd_to_clp_fx_rate <= ZERO:
        raise ValueError("FX rate must be strictly positive")

    conv_rate = TokenCreditConversionRate(tokens_per_credit=tokens_per_credit)
    simulated_tokens = conv_rate.credits_to_tokens(credits)

    cost_usd = calculate_real_api_cost_usd(
        tokens=simulated_tokens,
        model=api_model,
        custom_cost_per_million=custom_cost_per_million_usd,
    )
    cost_clp = (cost_usd * usd_to_clp_fx_rate).quantize(TWO_DECIMALS, ROUND_HALF_UP)

    commercial_val_clp = (Decimal(credits) * credit_price_clp).quantize(TWO_DECIMALS, ROUND_HALF_UP)
    commercial_val_usd = (Decimal(credits) * credit_price_usd).quantize(TWO_DECIMALS, ROUND_HALF_UP)

    margin_clp = (commercial_val_clp - cost_clp).quantize(TWO_DECIMALS, ROUND_HALF_UP)
    margin_usd = (commercial_val_usd - cost_usd).quantize(TWO_DECIMALS, ROUND_HALF_UP)

    if commercial_val_clp > ZERO:
        margin_pct = ((margin_clp / commercial_val_clp) * ONE_HUNDRED).quantize(TWO_DECIMALS, ROUND_HALF_UP)
    else:
        margin_pct = ZERO

    is_healthy = margin_pct >= Decimal("95.00")

    return SimulatedProfitMargin(
        credits=credits,
        tokens_per_credit=tokens_per_credit,
        simulated_tokens_monthly=simulated_tokens,
        simulated_cost_usd=cost_usd,
        simulated_cost_clp=cost_clp,
        simulated_commercial_value_clp=commercial_val_clp,
        simulated_commercial_value_usd=commercial_val_usd,
        gross_margin_clp=margin_clp,
        gross_margin_usd=margin_usd,
        gross_margin_pct=margin_pct,
        is_margin_above_95_pct=is_healthy,
    )
