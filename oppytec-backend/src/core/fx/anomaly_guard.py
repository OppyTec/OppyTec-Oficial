"""
oppytec-backend/src/core/fx/anomaly_guard.py
Escudo Anti-Anomalías Cambiarias (*FX Drift Circuit Breaker*):
Si una nueva tasa de cambio varía más de `Decimal("0.08")` (`> 8.0%`) respecto a la última tasa válida
sin confirmación de una segunda fuente oficial ni `is_manual_override=True`, rechaza la actualización
automática, conserva la tasa previa y emite alerta crítica `FX_ANOMALY_QUARANTINED`.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from src.core.fx.providers import RATE_PRECISION_QUANT, to_rate_decimal

DEFAULT_MAX_VARIATION_RATIO: Decimal = Decimal("0.08")
PCT_PRECISION_QUANT: Decimal = Decimal("0.0001")
HUNDRED_DECIMAL: Decimal = Decimal("100")


@dataclass(frozen=True)
class FxAnomalyEvaluation:
    """Resultado determinista de la evaluación del Circuit Breaker Cambiario (`Decimal`)."""

    currency_pair: str
    previous_rate: Decimal
    candidate_rate: Decimal
    variation_ratio: Decimal
    variation_pct: Decimal
    is_quarantined: bool
    effective_rate: Decimal
    action_taken: str
    alert_message: str | None = None


def calculate_rate_variation_ratio(previous_rate: Decimal, candidate_rate: Decimal) -> Decimal:
    """
    Calcula la razón de variación relativa `|candidate - previous| / previous` en `Decimal(18, 8)`.
    """
    prev_dec = to_rate_decimal(previous_rate)
    cand_dec = to_rate_decimal(candidate_rate)
    diff = abs(cand_dec - prev_dec)
    return (diff / prev_dec).quantize(RATE_PRECISION_QUANT, rounding=ROUND_HALF_UP)


def evaluate_fx_rate_drift(
    currency_pair: str,
    previous_rate: Decimal | None,
    candidate_rate: Decimal,
    *,
    max_variation_ratio: Decimal = DEFAULT_MAX_VARIATION_RATIO,
    confirmed_by_secondary_source: bool = False,
    is_manual_override: bool = False,
) -> FxAnomalyEvaluation:
    """
    Evalúa si una nueva tasa cambiaria supera el umbral de seguridad (`±8.0%` por defecto):
    - Si `previous_rate` es `None`, acepta la tasa inicial (`INITIAL_SEED`).
    - Si `variation_ratio > max_variation_ratio` y NO está confirmada por fuente secundaria
      ni es un `is_manual_override`, rechaza el cambio (`is_quarantined=True`),
      conserva `previous_rate` y genera alerta crítica `FX_ANOMALY_QUARANTINED`.
    """
    cand_dec = to_rate_decimal(candidate_rate)
    pair_norm = currency_pair.strip().upper()

    if previous_rate is None:
        return FxAnomalyEvaluation(
            currency_pair=pair_norm,
            previous_rate=cand_dec,
            candidate_rate=cand_dec,
            variation_ratio=Decimal("0.00000000"),
            variation_pct=Decimal("0.0000"),
            is_quarantined=False,
            effective_rate=cand_dec,
            action_taken="INITIAL_SEED",
            alert_message=None,
        )

    prev_dec = to_rate_decimal(previous_rate)
    variation_ratio = calculate_rate_variation_ratio(prev_dec, cand_dec)
    variation_pct = (variation_ratio * HUNDRED_DECIMAL).quantize(
        PCT_PRECISION_QUANT,
        rounding=ROUND_HALF_UP,
    )

    if is_manual_override:
        return FxAnomalyEvaluation(
            currency_pair=pair_norm,
            previous_rate=prev_dec,
            candidate_rate=cand_dec,
            variation_ratio=variation_ratio,
            variation_pct=variation_pct,
            is_quarantined=False,
            effective_rate=cand_dec,
            action_taken="MANUAL_SUPERUSER_OVERRIDE",
            alert_message=None,
        )

    if variation_ratio > max_variation_ratio and not confirmed_by_secondary_source:
        alert = (
            f"CRITICAL FX_ANOMALY_QUARANTINED [{pair_norm}]: variation {variation_pct}% exceeds "
            f"threshold {(max_variation_ratio * HUNDRED_DECIMAL).quantize(PCT_PRECISION_QUANT)}%. "
            f"Candidate rate {cand_dec} rejected; preserving previous valid rate {prev_dec}."
        )
        return FxAnomalyEvaluation(
            currency_pair=pair_norm,
            previous_rate=prev_dec,
            candidate_rate=cand_dec,
            variation_ratio=variation_ratio,
            variation_pct=variation_pct,
            is_quarantined=True,
            effective_rate=prev_dec,
            action_taken="FX_ANOMALY_QUARANTINED",
            alert_message=alert,
        )

    action = (
        "AUTO_UPDATED_SECONDARY_CONFIRMED"
        if variation_ratio > max_variation_ratio and confirmed_by_secondary_source
        else "AUTO_UPDATED"
    )
    return FxAnomalyEvaluation(
        currency_pair=pair_norm,
        previous_rate=prev_dec,
        candidate_rate=cand_dec,
        variation_ratio=variation_ratio,
        variation_pct=variation_pct,
        is_quarantined=False,
        effective_rate=cand_dec,
        action_taken=action,
        alert_message=None,
    )
