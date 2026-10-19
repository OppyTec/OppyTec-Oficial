import { translateKey } from "@/shared/i18n";
import {
  SUPPORTED_CURRENCIES,
  type SupportedCurrency,
  useCurrency,
} from "./CurrencyContext";
import { CURRENCY_SYMBOLS } from "./useCurrencyFormatter";

export interface CurrencySelectorProps {
  readonly onCurrencyChange?: (currency: SupportedCurrency) => void;
  readonly className?: string;
}

/**
 * Navbar currency selector (`CLP`, `USD`, `EUR`, `BRL`, `UF`) operating independently
 * of `<LanguageFlagSelector />` (Rule 15 & Rule 16).
 */
export function CurrencySelector({
  onCurrencyChange,
  className = "",
}: CurrencySelectorProps) {
  const { currency, setCurrency, activeRate } = useCurrency();

  const handleSelect = (next: SupportedCurrency): void => {
    setCurrency(next);
    onCurrencyChange?.(next);
  };

  return (
    <div
      role="group"
      aria-label={translateKey("common", "currency.label")}
      data-testid="currency-selector"
      data-active-currency={currency}
      data-rate-source={activeRate.source}
      className={`inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-card/80 p-1 ${className}`.trim()}
    >
      {SUPPORTED_CURRENCIES.map((code) => {
        const isSelected = currency === code;
        return (
          <button
            key={code}
            type="button"
            data-testid={`currency-option-${code}`}
            aria-pressed={isSelected}
            onClick={() => handleSelect(code)}
            className={`touch-target inline-flex min-h-[44px] min-w-[44px] items-center gap-1 rounded-md px-2.5 py-1.5 font-mono text-xs font-semibold transition-all ${
              isSelected
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/60 text-secondary-foreground hover:bg-secondary"
            }`}
          >
            <span className="opacity-75">{CURRENCY_SYMBOLS[code]}</span>
            <span>{code}</span>
          </button>
        );
      })}
    </div>
  );
}
