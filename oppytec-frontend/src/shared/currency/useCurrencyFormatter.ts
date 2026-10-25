import { useCallback, useContext } from "react";
import {
  CURRENCY_DECIMALS,
  CurrencyContext,
  DEFAULT_CENTRAL_BANK_RATES,
  convertAmountExact,
  formatScaledDecimal,
  parseScaledDecimal,
  type SupportedCurrency,
} from "./CurrencyContext";

export const CURRENCY_SYMBOLS: Readonly<Record<SupportedCurrency, string>> = {
  CLP: "$",
  USD: "US$",
  EUR: "€",
  BRL: "R$",
  UF: "UF",
};

function addThousandsSeparators(
  intDigits: string,
  separator: string
): string {
  const isNeg = intDigits.startsWith("-");
  const clean = isNeg ? intDigits.slice(1) : intDigits;
  const grouped = clean.replace(/\B(?=(\d{3})+(?!\d))/g, separator);
  return isNeg ? `-${grouped}` : grouped;
}

/**
 * Formats an exact monetary amount respecting canonical currency precision:
 * - `CLP`: 0 decimals (`$12.500`)
 * - `USD` / `EUR` / `BRL`: 2 decimals (`US$12.50`, `€12,50`, `R$12,50`)
 * - `UF`: 4 decimals (`UF 1,2500`)
 */
export function formatCurrencyAmount(
  amount: string | number,
  currency: SupportedCurrency = "CLP"
): string {
  const decimals = CURRENCY_DECIMALS[currency];
  const scaled = parseScaledDecimal(amount);
  const exactStr = formatScaledDecimal(scaled, decimals);
  const symbol = CURRENCY_SYMBOLS[currency];

  const [rawInt = "0", rawFrac = ""] = exactStr.split(".");
  if (currency === "CLP") {
    return `${symbol}${addThousandsSeparators(rawInt, ".")}`;
  }
  if (currency === "UF") {
    return `${symbol} ${addThousandsSeparators(rawInt, ".")},${rawFrac}`;
  }
  if (currency === "USD") {
    return `${symbol}${addThousandsSeparators(rawInt, ",")}.${rawFrac}`;
  }
  return `${symbol}${addThousandsSeparators(rawInt, ".")},${rawFrac}`;
}

export interface UseCurrencyFormatterReturn {
  readonly currency: SupportedCurrency;
  readonly format: (
    amount: string | number,
    overrideCurrency?: SupportedCurrency
  ) => string;
  readonly convertAndFormat: (
    amount: string | number,
    fromCurrency?: SupportedCurrency,
    toCurrency?: SupportedCurrency
  ) => string;
}

export function useCurrencyFormatter(): UseCurrencyFormatterReturn {
  const context = useContext(CurrencyContext);
  const currency = context?.currency ?? "CLP";
  const rates = context?.rates ?? DEFAULT_CENTRAL_BANK_RATES;

  const format = useCallback(
    (
      amount: string | number,
      overrideCurrency: SupportedCurrency = currency
    ): string => formatCurrencyAmount(amount, overrideCurrency),
    [currency]
  );

  const convertAndFormat = useCallback(
    (
      amount: string | number,
      fromCurrency: SupportedCurrency = "CLP",
      toCurrency: SupportedCurrency = currency
    ): string => {
      const converted = convertAmountExact(
        amount,
        fromCurrency,
        toCurrency,
        rates
      );
      return formatCurrencyAmount(converted, toCurrency);
    },
    [currency, rates]
  );

  return {
    currency,
    format,
    convertAndFormat,
  };
}
