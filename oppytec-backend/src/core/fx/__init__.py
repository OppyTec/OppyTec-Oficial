"""
oppytec-backend/src/core/fx/__init__.py
Exportaciones públicas del Motor Cambiario Institucional Multi-Moneda (`100% Decimal`, `0% float`).
"""
from __future__ import annotations

from src.core.fx.anomaly_guard import (
    DEFAULT_MAX_VARIATION_RATIO,
    FxAnomalyEvaluation,
    calculate_rate_variation_ratio,
    evaluate_fx_rate_drift,
)
from src.core.fx.fx_service import (
    INTEGER_CLP_QUANT,
    TWO_DECIMAL_QUANT,
    ActiveFxRateEntry,
    FxAuditRecord,
    FXService,
)
from src.core.fx.providers import (
    RATE_PRECISION_QUANT,
    SUPPORTED_CURRENCIES,
    FxQuote,
    SupportedCurrency,
    parse_bcch_mindicador_payload,
    parse_ecb_frankfurter_payload,
    to_rate_decimal,
)

__all__ = [
    "DEFAULT_MAX_VARIATION_RATIO",
    "INTEGER_CLP_QUANT",
    "RATE_PRECISION_QUANT",
    "SUPPORTED_CURRENCIES",
    "TWO_DECIMAL_QUANT",
    "ActiveFxRateEntry",
    "FXService",
    "FxAnomalyEvaluation",
    "FxAuditRecord",
    "FxQuote",
    "SupportedCurrency",
    "calculate_rate_variation_ratio",
    "evaluate_fx_rate_drift",
    "parse_bcch_mindicador_payload",
    "parse_ecb_frankfurter_payload",
    "to_rate_decimal",
]
