"""
oppytec-backend/src/core/fx/providers.py
Adaptadores y Parsers Oficiales de Bancos Centrales con precisión `Decimal(18, 8)` (CERO `float`):
1. Banco Central de Chile (`BCCh` / `mindicador.cl`): `USD -> CLP`, `EUR -> CLP`, `UF -> CLP`.
2. Banco Central Europeo (`BCE Frankfurter` / `api.frankfurter.dev`): `EUR -> USD`, `EUR -> BRL`, `USD -> BRL`.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal

RATE_PRECISION_QUANT: Decimal = Decimal("0.00000001")
SupportedCurrency = Literal["CLP", "USD", "EUR", "BRL", "UF"]
SUPPORTED_CURRENCIES: tuple[SupportedCurrency, ...] = ("CLP", "USD", "EUR", "BRL", "UF")

BCCH_SERIES_MAP: dict[str, SupportedCurrency] = {
    "dolar": "USD",
    "euro": "EUR",
    "uf": "UF",
}


def to_rate_decimal(raw_value: Decimal | int | str) -> Decimal:
    """
    Convierte un valor numérico/string de API a `Decimal(18, 8)` sin pasar jamás por coma flotante.
    Valida que la tasa sea estrictamente mayor que cero.
    """
    try:
        dec_val = raw_value if isinstance(raw_value, Decimal) else Decimal(str(raw_value).strip().replace(",", "."))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Valor de tasa FX inválido: {raw_value!r}") from exc

    quantized = dec_val.quantize(RATE_PRECISION_QUANT, rounding=ROUND_HALF_UP)
    if quantized <= Decimal("0"):
        raise ValueError(f"La tasa FX debe ser mayor que Decimal('0'), recibido: {quantized}")
    return quantized


@dataclass(frozen=True)
class FxQuote:
    """Cotización cambiaria normalizada con precisión `Decimal(18, 8)`."""

    base_currency: str
    quote_currency: str
    rate: Decimal
    source_provider: str
    effective_date: datetime

    @property
    def currency_pair(self) -> str:
        """Identificador canónico del par cambiario (`BASE/QUOTE`)."""
        return f"{self.base_currency.upper()}/{self.quote_currency.upper()}"


def parse_bcch_mindicador_payload(
    payload: Mapping[str, object],
    effective_date: datetime | None = None,
) -> list[FxQuote]:
    """
    Parsea la respuesta JSON del Banco Central de Chile (`mindicador.cl/api`)
    extrayendo `dolar` (`USD/CLP`), `euro` (`EUR/CLP`) y `UF` (`UF/CLP`) en `Decimal(18, 8)`.
    """
    resolved_date = effective_date or datetime.now(tz=UTC)
    quotes: list[FxQuote] = []

    for series_key, base_curr in BCCH_SERIES_MAP.items():
        node = payload.get(series_key)
        if not isinstance(node, Mapping):
            continue
        raw_val = node.get("valor")
        if raw_val is None and isinstance(node.get("serie"), list):
            serie_list = node.get("serie")
            if isinstance(serie_list, list) and serie_list and isinstance(serie_list[0], Mapping):
                raw_val = serie_list[0].get("valor")
        if raw_val is None:
            continue
        rate = to_rate_decimal(str(raw_val))
        quotes.append(
            FxQuote(
                base_currency=base_curr,
                quote_currency="CLP",
                rate=rate,
                source_provider="BCCH_OFFICIAL",
                effective_date=resolved_date,
            )
        )
    return quotes


def parse_ecb_frankfurter_payload(
    payload: Mapping[str, object],
    effective_date: datetime | None = None,
) -> list[FxQuote]:
    """
    Parsea la respuesta JSON del Banco Central Europeo (`api.frankfurter.dev/v1/latest`)
    extrayendo tasas respecto a `base` (`EUR` o `USD`) hacia `USD`, `EUR`, `BRL`, etc. en `Decimal(18, 8)`.
    """
    resolved_date = effective_date or datetime.now(tz=UTC)
    base_raw = str(payload.get("base", "EUR")).strip().upper()
    rates_node = payload.get("rates")
    if not isinstance(rates_node, Mapping):
        return []

    quotes: list[FxQuote] = []
    for quote_curr_raw, raw_rate in sorted(rates_node.items()):
        quote_curr = str(quote_curr_raw).strip().upper()
        if not quote_curr or raw_rate is None or quote_curr == base_raw:
            continue
        rate = to_rate_decimal(str(raw_rate))
        quotes.append(
            FxQuote(
                base_currency=base_raw,
                quote_currency=quote_curr,
                rate=rate,
                source_provider="ECB_FRANKFURTER",
                effective_date=resolved_date,
            )
        )
    return quotes
