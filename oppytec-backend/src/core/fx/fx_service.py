"""
oppytec-backend/src/core/fx/fx_service.py
Servicio Institucional Multi-Moneda (`CLP`, `USD`, `EUR`, `BRL`, `UF`):
1. Triangulación exacta 100% `Decimal` (`Decimal("0.00000001")` para tasas y `Decimal("0.01")` / `Decimal("1")` para montos).
2. Integración con `evaluate_fx_rate_drift` (Escudo Anti-Anomalías > 8%).
3. Soporte para Override Manual Auditado por el SuperUser (`apply_manual_fx_override`).
4. Conversión automática de precios de planes comerciales (`system_plans`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from src.core.fx.anomaly_guard import (
    DEFAULT_MAX_VARIATION_RATIO,
    FxAnomalyEvaluation,
    evaluate_fx_rate_drift,
)
from src.core.fx.providers import (
    RATE_PRECISION_QUANT,
    SUPPORTED_CURRENCIES,
    FxQuote,
    to_rate_decimal,
)

TWO_DECIMAL_QUANT: Decimal = Decimal("0.01")
INTEGER_CLP_QUANT: Decimal = Decimal("1")
ONE_DECIMAL: Decimal = Decimal("1")
PIVOT_CURRENCIES: tuple[str, ...] = ("CLP", "USD", "EUR")


@dataclass(frozen=True)
class FxAuditRecord:
    """Registro inmutable de auditoría cambiaria (`public.fx_audit_log`)."""

    currency_pair: str
    previous_rate: Decimal
    previous_source: str
    new_rate: Decimal
    variation_pct: Decimal
    action_taken: str
    actor_user_id: int | None
    reason: str
    created_at: datetime


@dataclass
class ActiveFxRateEntry:
    """Estado vigente de un par de monedas en el motor cambiario (`public.fx_current_rates`)."""

    base_currency: str
    quote_currency: str
    rate: Decimal
    source_provider: str
    is_manual_override: bool
    updated_at: datetime


class FXService:
    """
    Motor Cambiario Institucional de OppyTec v2.0 (100% `Decimal`, 0% `float`).
    """

    def __init__(self, seed_default_rates: bool = True) -> None:
        self._rates: dict[tuple[str, str], ActiveFxRateEntry] = {}
        self._history: list[FxQuote] = []
        self._audit_logs: list[FxAuditRecord] = []
        if seed_default_rates:
            self._seed_institutional_defaults()

    def _seed_institutional_defaults(self) -> None:
        """Inicializa tasas institucionales base de referencia (BCCh + BCE Frankfurter)."""
        now = datetime.now(tz=UTC)
        initial_quotes = [
            FxQuote("USD", "CLP", Decimal("950.00000000"), "BCCH_OFFICIAL", now),
            FxQuote("EUR", "CLP", Decimal("1035.50000000"), "BCCH_OFFICIAL", now),
            FxQuote("UF", "CLP", Decimal("37950.00000000"), "BCCH_OFFICIAL", now),
            FxQuote("EUR", "USD", Decimal("1.09000000"), "ECB_FRANKFURTER", now),
            FxQuote("EUR", "BRL", Decimal("6.10400000"), "ECB_FRANKFURTER", now),
            FxQuote("USD", "BRL", Decimal("5.60000000"), "ECB_FRANKFURTER", now),
        ]
        for q in initial_quotes:
            self._rates[(q.base_currency, q.quote_currency)] = ActiveFxRateEntry(
                base_currency=q.base_currency,
                quote_currency=q.quote_currency,
                rate=q.rate,
                source_provider=q.source_provider,
                is_manual_override=False,
                updated_at=now,
            )
            self._history.append(q)

    @property
    def audit_logs(self) -> list[FxAuditRecord]:
        """Devuelve la bitácora inmutable de auditoría cambiaria."""
        return list(self._audit_logs)

    @property
    def rate_history(self) -> list[FxQuote]:
        """Devuelve el historial cronológico de tasas aplicadas."""
        return list(self._history)

    def ingest_automatic_quote(
        self,
        quote: FxQuote,
        *,
        max_variation_ratio: Decimal = DEFAULT_MAX_VARIATION_RATIO,
        confirmed_by_secondary_source: bool = False,
        respect_manual_override_lock: bool = True,
    ) -> FxAnomalyEvaluation:
        """
        Procesa una cotización proveniente de BCCh o BCE aplicando:
        1. Respeto al candado de Override Manual del SuperUser si está activo.
        2. Evaluación del Escudo Anti-Anomalías (`> 8%`).
        """
        base = quote.base_currency.strip().upper()
        target = quote.quote_currency.strip().upper()
        pair_key = (base, target)
        pair_str = f"{base}/{target}"
        existing = self._rates.get(pair_key)

        if existing is not None and existing.is_manual_override and respect_manual_override_lock:
            return FxAnomalyEvaluation(
                currency_pair=pair_str,
                previous_rate=existing.rate,
                candidate_rate=to_rate_decimal(quote.rate),
                variation_ratio=Decimal("0.00000000"),
                variation_pct=Decimal("0.0000"),
                is_quarantined=True,
                effective_rate=existing.rate,
                action_taken="SKIPPED_MANUAL_OVERRIDE_LOCKED",
                alert_message="Rate locked by SuperUser manual override.",
            )

        prev_rate = existing.rate if existing is not None else None
        prev_source = existing.source_provider if existing is not None else "NONE"
        evaluation = evaluate_fx_rate_drift(
            currency_pair=pair_str,
            previous_rate=prev_rate,
            candidate_rate=quote.rate,
            max_variation_ratio=max_variation_ratio,
            confirmed_by_secondary_source=confirmed_by_secondary_source,
            is_manual_override=False,
        )

        if evaluation.is_quarantined:
            self._audit_logs.append(
                FxAuditRecord(
                    currency_pair=pair_str,
                    previous_rate=evaluation.previous_rate,
                    previous_source=prev_source,
                    new_rate=evaluation.candidate_rate,
                    variation_pct=evaluation.variation_pct,
                    action_taken=evaluation.action_taken,
                    actor_user_id=None,
                    reason=evaluation.alert_message or "Automatic FX drift circuit breaker triggered",
                    created_at=quote.effective_date,
                )
            )
            return evaluation

        self._rates[pair_key] = ActiveFxRateEntry(
            base_currency=base,
            quote_currency=target,
            rate=evaluation.effective_rate,
            source_provider=quote.source_provider,
            is_manual_override=False,
            updated_at=quote.effective_date,
        )
        self._history.append(
            FxQuote(
                base_currency=base,
                quote_currency=target,
                rate=evaluation.effective_rate,
                source_provider=quote.source_provider,
                effective_date=quote.effective_date,
            )
        )
        return evaluation

    def apply_manual_fx_override(
        self,
        base_currency: str,
        quote_currency: str,
        new_rate: Decimal,
        *,
        actor_user_id: int,
        reason: str,
        is_superuser: bool = True,
    ) -> FxAuditRecord:
        """
        Aplica un Override Manual Auditado por el SuperUser de OppyTec:
        - Valida rol `SuperUser` y motivo auditable (`>= 10` caracteres).
        - Registra en `fx_audit_log` la tasa previa, la fuente previa, la nueva tasa manual y el `actor_user_id`.
        """
        if not is_superuser:
            raise PermissionError("Solo el SuperUser de OppyTec puede aplicar un override manual FX.")

        cleaned_reason = reason.strip()
        if len(cleaned_reason) < 10:
            raise ValueError(
                "El motivo del override manual cambiario debe tener al menos 10 caracteres auditables."
            )

        base = base_currency.strip().upper()
        target = quote_currency.strip().upper()
        if base == target:
            raise ValueError("No se puede aplicar override sobre la misma moneda origen y destino.")

        validated_rate = to_rate_decimal(new_rate)
        pair_key = (base, target)
        pair_str = f"{base}/{target}"
        existing = self._rates.get(pair_key)
        prev_rate = existing.rate if existing is not None else validated_rate
        prev_source = existing.source_provider if existing is not None else "NONE"

        evaluation = evaluate_fx_rate_drift(
            currency_pair=pair_str,
            previous_rate=prev_rate,
            candidate_rate=validated_rate,
            is_manual_override=True,
        )

        now = datetime.now(tz=UTC)
        self._rates[pair_key] = ActiveFxRateEntry(
            base_currency=base,
            quote_currency=target,
            rate=validated_rate,
            source_provider="MANUAL_SUPERUSER_OVERRIDE",
            is_manual_override=True,
            updated_at=now,
        )
        self._history.append(
            FxQuote(
                base_currency=base,
                quote_currency=target,
                rate=validated_rate,
                source_provider="MANUAL_SUPERUSER_OVERRIDE",
                effective_date=now,
            )
        )

        audit_record = FxAuditRecord(
            currency_pair=pair_str,
            previous_rate=prev_rate,
            previous_source=prev_source,
            new_rate=validated_rate,
            variation_pct=evaluation.variation_pct,
            action_taken="MANUAL_SUPERUSER_OVERRIDE",
            actor_user_id=actor_user_id,
            reason=cleaned_reason,
            created_at=now,
        )
        self._audit_logs.append(audit_record)
        return audit_record

    def release_manual_fx_override(self, base_currency: str, quote_currency: str) -> bool:
        """Libera el candado manual de un par cambiario para retomar la sincronización automática."""
        pair_key = (base_currency.strip().upper(), quote_currency.strip().upper())
        entry = self._rates.get(pair_key)
        if entry is None:
            return False
        entry.is_manual_override = False
        return True

    def get_exchange_rate(self, base_currency: str, quote_currency: str) -> Decimal:
        """
        Obtiene la tasa de cambio `Decimal(18, 8)` entre `base_currency` y `quote_currency`
        usando resolución directa, inversa exacta (`1 / rate`) o triangulación por pivote (`CLP`, `USD`, `EUR`).
        """
        base = base_currency.strip().upper()
        target = quote_currency.strip().upper()

        if base not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Moneda origen no soportada: {base}")
        if target not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Moneda destino no soportada: {target}")

        if base == target:
            return ONE_DECIMAL.quantize(RATE_PRECISION_QUANT, rounding=ROUND_HALF_UP)

        direct = self._lookup_direct_or_inverse(base, target)
        if direct is not None:
            return direct

        for pivot in PIVOT_CURRENCIES:
            if pivot in (base, target):
                continue
            leg_1 = self._lookup_direct_or_inverse(base, pivot)
            leg_2 = self._lookup_direct_or_inverse(pivot, target)
            if leg_1 is not None and leg_2 is not None:
                return (leg_1 * leg_2).quantize(RATE_PRECISION_QUANT, rounding=ROUND_HALF_UP)

        raise LookupError(f"No existe ruta de triangulación FX disponible para {base}/{target}")

    def _lookup_direct_or_inverse(self, base: str, target: str) -> Decimal | None:
        """Busca tasa directa `(base, target)` o calcula su inversa `(1 / rate)` en `Decimal(18, 8)`."""
        direct_entry = self._rates.get((base, target))
        if direct_entry is not None:
            return direct_entry.rate

        inverse_entry = self._rates.get((target, base))
        if inverse_entry is not None:
            return (ONE_DECIMAL / inverse_entry.rate).quantize(
                RATE_PRECISION_QUANT,
                rounding=ROUND_HALF_UP,
            )
        return None

    def convert_amount(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        *,
        integer_clp: bool = False,
    ) -> Decimal:
        """
        Convierte un monto `Decimal` desde `from_currency` hacia `to_currency`.
        Aplica redondeo financiero `ROUND_HALF_UP` a `Decimal("0.01")` (o `Decimal("1")` si `integer_clp=True` y destino es `CLP`).
        """
        if not isinstance(amount, Decimal):
            raise TypeError("El monto monetario debe ser estrictamente decimal.Decimal (prohibido float).")

        target = to_currency.strip().upper()
        rate = self.get_exchange_rate(from_currency, target)
        raw_converted = amount * rate
        quant = INTEGER_CLP_QUANT if (integer_clp and target == "CLP") else TWO_DECIMAL_QUANT
        return raw_converted.quantize(quant, rounding=ROUND_HALF_UP)

    def convert_system_plan_prices(
        self,
        anchor_amount: Decimal,
        anchor_currency: str = "USD",
        *,
        integer_clp: bool = False,
    ) -> dict[str, Decimal]:
        """
        Calcula automáticamente la matriz de precios equivalentes (`price_clp`, `price_usd`, `price_eur`, `price_brl`)
        para un Plan Comercial (`public.system_plans`) a partir de su moneda ancla.
        """
        return {
            "price_clp": self.convert_amount(
                anchor_amount, anchor_currency, "CLP", integer_clp=integer_clp
            ),
            "price_usd": self.convert_amount(anchor_amount, anchor_currency, "USD"),
            "price_eur": self.convert_amount(anchor_amount, anchor_currency, "EUR"),
            "price_brl": self.convert_amount(anchor_amount, anchor_currency, "BRL"),
        }
