import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
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

const CURRENCY_FULL_NAMES: Readonly<Record<SupportedCurrency, string>> = {
  CLP: "Peso Chileno",
  USD: "Dólar USD",
  EUR: "Euro",
  BRL: "Real Brasileño",
  UF: "Unidad Fomento",
};

/**
 * Navbar currency selector (`CLP`, `USD`, `EUR`, `BRL`, `UF`) rendered as a compact,
 * styled dropdown menu operating independently of `<LanguageFlagSelector />` (Rule 15 & Rule 16).
 */
export function CurrencySelector({
  onCurrencyChange,
  className = "",
}: CurrencySelectorProps) {
  const { currency, setCurrency, activeRate } = useCurrency();
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside or Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const handleSelect = (next: SupportedCurrency): void => {
    setCurrency(next);
    onCurrencyChange?.(next);
    setIsOpen(false);
  };

  return (
    <div
      ref={dropdownRef}
      role="group"
      aria-label={translateKey("common", "currency.label")}
      data-testid="currency-selector"
      data-active-currency={currency}
      data-rate-source={activeRate.source}
      className={`relative inline-flex items-center ${className}`.trim()}
    >
      {/* Trigger Button showing active currency + symbol + chevron */}
      <button
        type="button"
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label={translateKey("common", "currency.label")}
        onClick={() => setIsOpen((prev) => !prev)}
        className="touch-target inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-border bg-card/90 px-3 py-1.5 font-mono text-xs font-semibold text-foreground shadow-sm transition-all hover:bg-secondary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <span className="text-muted-foreground">{CURRENCY_SYMBOLS[currency]}</span>
        <span>{currency}</span>
        <ChevronDown
          className={`h-3.5 w-3.5 text-muted-foreground transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown menu popover */}
      <div
        role="menu"
        aria-orientation="vertical"
        className={`absolute right-0 top-full mt-1.5 w-44 rounded-lg border border-border bg-popover p-1 shadow-lg z-50 ${
          isOpen ? "block animate-in fade-in-50 zoom-in-95" : "hidden"
        }`}
      >
        {SUPPORTED_CURRENCIES.map((code) => {
          const isSelected = currency === code;
          return (
            <button
              key={code}
              type="button"
              role="menuitem"
              data-testid={`currency-option-${code}`}
              aria-pressed={isSelected}
              onClick={() => handleSelect(code)}
              className={`touch-target flex w-full items-center justify-between rounded-md px-2.5 py-1.5 font-mono text-xs font-semibold transition-all ${
                isSelected
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-foreground hover:bg-secondary"
              }`}
            >
              <div className="flex items-center gap-1.5">
                <span className="w-5 text-left opacity-75">{CURRENCY_SYMBOLS[code]}</span>
                <span>{code}</span>
                <span className="text-[10px] font-sans font-normal text-muted-foreground truncate max-w-[70px]">
                  {CURRENCY_FULL_NAMES[code]}
                </span>
              </div>
              {isSelected && <Check className="h-3.5 w-3.5 shrink-0" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
