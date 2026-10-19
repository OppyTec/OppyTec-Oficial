import { translateKey } from "@/shared/i18n";
import {
  DEFAULT_CENTRAL_BANK_RATES,
  FX_ANOMALY_THRESHOLD_PCT,
  type SupportedCurrency,
  useCurrency,
} from "./CurrencyContext";
import { formatCurrencyAmount } from "./useCurrencyFormatter";

export interface MoneyBadgeProps {
  readonly amount: string | number;
  readonly baseCurrency?: SupportedCurrency;
  readonly displayCurrency?: SupportedCurrency;
  readonly showSource?: boolean;
  readonly className?: string;
}

/**
 * Visible badge displaying a formatted monetary amount alongside currency code,
 * official Central Bank source (`BCCh` / `BCE Frankfurter`), and anomaly warning if triggered.
 */
export function MoneyBadge({
  amount,
  baseCurrency = "CLP",
  displayCurrency,
  showSource = true,
  className = "",
}: MoneyBadgeProps) {
  const { currency, rates, convert, hasAnomaly } = useCurrency();
  const targetCurrency = displayCurrency ?? currency;
  const convertedAmount =
    baseCurrency === targetCurrency
      ? String(amount)
      : convert(amount, baseCurrency, targetCurrency);
  const formatted = formatCurrencyAmount(convertedAmount, targetCurrency);
  const rateDescriptor =
    rates[targetCurrency] ?? DEFAULT_CENTRAL_BANK_RATES[targetCurrency];

  return (
    <span
      data-testid="money-badge"
      data-currency={targetCurrency}
      data-rate-source={rateDescriptor.source}
      data-fx-anomaly={String(hasAnomaly)}
      className={`inline-flex items-center gap-1.5 rounded-md border border-border bg-secondary/50 px-2.5 py-1 font-mono text-xs font-semibold text-foreground ${className}`.trim()}
    >
      <span data-testid="money-badge-amount">{formatted}</span>
      <span className="rounded bg-primary/15 px-1.5 py-0.5 text-[10px] font-bold text-primary">
        {targetCurrency}
      </span>
      {showSource && (
        <span
          data-testid="money-badge-source"
          className="text-[10px] font-normal text-muted-foreground"
        >
          {translateKey("common", "currency.source_label", {
            source: rateDescriptor.source,
          })}
        </span>
      )}
      {hasAnomaly && (
        <span
          role="status"
          data-testid="money-badge-anomaly"
          title={translateKey("common", "currency.anomaly_warning", {
            threshold: FX_ANOMALY_THRESHOLD_PCT,
          })}
          className="rounded bg-destructive/20 px-1.5 py-0.5 text-[10px] font-bold text-destructive"
        >
          {`> ${FX_ANOMALY_THRESHOLD_PCT}% FX`}
        </span>
      )}
    </span>
  );
}
