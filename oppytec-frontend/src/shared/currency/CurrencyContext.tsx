/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

export const SUPPORTED_CURRENCIES = [
  "CLP",
  "USD",
  "EUR",
  "BRL",
  "UF",
] as const;

export type SupportedCurrency = (typeof SUPPORTED_CURRENCIES)[number];

export type CentralBankSource = "BCCh" | "BCE Frankfurter" | "Manual Override";

export interface ExchangeRateDescriptor {
  readonly currency: SupportedCurrency;
  /** Rate expressed in CLP per 1 unit of `currency` (exact decimal string). */
  readonly rateToClp: string;
  readonly previousRateToClp?: string;
  readonly source: CentralBankSource;
  readonly updatedAtIso: string;
}

export const CURRENCY_STORAGE_KEY = "oppytec_currency";

/**
 * Maximum daily variation threshold (8%) before activating the FX anomaly circuit breaker (Rule 16).
 */
export const FX_ANOMALY_THRESHOLD_PCT = 8;

const SCALE_DIGITS = 8;
const SCALE_FACTOR = 100_000_000n; // 10^8 exact fixed-point scale

export const DEFAULT_CENTRAL_BANK_RATES: Readonly<
  Record<SupportedCurrency, ExchangeRateDescriptor>
> = {
  CLP: {
    currency: "CLP",
    rateToClp: "1.00000000",
    previousRateToClp: "1.00000000",
    source: "BCCh",
    updatedAtIso: "2026-01-15T08:30:00Z",
  },
  USD: {
    currency: "USD",
    rateToClp: "960.00000000",
    previousRateToClp: "955.00000000",
    source: "BCCh",
    updatedAtIso: "2026-01-15T08:30:00Z",
  },
  EUR: {
    currency: "EUR",
    rateToClp: "1040.00000000",
    previousRateToClp: "1035.00000000",
    source: "BCE Frankfurter",
    updatedAtIso: "2026-01-15T08:30:00Z",
  },
  BRL: {
    currency: "BRL",
    rateToClp: "192.00000000",
    previousRateToClp: "190.00000000",
    source: "BCE Frankfurter",
    updatedAtIso: "2026-01-15T08:30:00Z",
  },
  UF: {
    currency: "UF",
    rateToClp: "38400.00000000",
    previousRateToClp: "38380.00000000",
    source: "BCCh",
    updatedAtIso: "2026-01-15T08:30:00Z",
  },
};

export const CURRENCY_DECIMALS: Readonly<Record<SupportedCurrency, number>> = {
  CLP: 0,
  USD: 2,
  EUR: 2,
  BRL: 2,
  UF: 4,
};

/**
 * Parses a decimal string or number into an exact `BigInt` scaled by 10^8.
 */
export function parseScaledDecimal(value: string | number): bigint {
  const raw = String(value).trim();
  if (!raw || raw === "NaN") {
    throw new Error(`Invalid monetary decimal value: "${String(value)}"`);
  }
  const isNegative = raw.startsWith("-");
  const unsigned =
    raw.startsWith("-") || raw.startsWith("+") ? raw.slice(1) : raw;
  const parts = unsigned.split(".");
  if (parts.length > 2) {
    throw new Error(`Invalid monetary decimal format: "${raw}"`);
  }
  const intPartStr = parts[0] && parts[0].length > 0 ? parts[0] : "0";
  const fracPartRaw = parts[1] ?? "";
  const paddedFrac = fracPartRaw
    .padEnd(SCALE_DIGITS + 1, "0")
    .slice(0, SCALE_DIGITS + 1);
  const mainFrac = paddedFrac.slice(0, SCALE_DIGITS);
  const roundingDigit = Number(paddedFrac.slice(SCALE_DIGITS, SCALE_DIGITS + 1));

  let scaled =
    BigInt(intPartStr) * SCALE_FACTOR + BigInt(mainFrac || "0");
  if (roundingDigit >= 5) {
    scaled += 1n;
  }
  return isNegative ? -scaled : scaled;
}

/**
 * Formats a 10^8-scaled `BigInt` back to a fixed-point string with `decimals` digits (half-up rounding).
 */
export function formatScaledDecimal(scaled: bigint, decimals: number): string {
  const isNegative = scaled < 0n;
  const absVal = isNegative ? -scaled : scaled;
  const dropDigits = SCALE_DIGITS - decimals;

  let roundedUnits: bigint;
  if (dropDigits > 0) {
    const divisor = 10n ** BigInt(dropDigits);
    const half = divisor / 2n;
    roundedUnits = (absVal + half) / divisor;
  } else {
    roundedUnits = absVal * 10n ** BigInt(-dropDigits);
  }

  const signPrefix = isNegative && roundedUnits > 0n ? "-" : "";
  if (decimals <= 0) {
    return `${signPrefix}${roundedUnits.toString()}`;
  }

  const unitScale = 10n ** BigInt(decimals);
  const intPart = roundedUnits / unitScale;
  const fracPart = (roundedUnits % unitScale)
    .toString()
    .padStart(decimals, "0");
  return `${signPrefix}${intPart.toString()}.${fracPart}`;
}

/**
 * Detects whether a proposed rate change exceeds the 8% daily variation anomaly circuit breaker.
 */
export function detectFxAnomaly(
  currentRate: string | number,
  previousRate?: string | number
): boolean {
  if (previousRate === undefined) {
    return false;
  }
  const currScaled = parseScaledDecimal(currentRate);
  const prevScaled = parseScaledDecimal(previousRate);
  if (prevScaled <= 0n || currScaled <= 0n) {
    return true;
  }
  const diff =
    currScaled >= prevScaled
      ? currScaled - prevScaled
      : prevScaled - currScaled;
  // diff / prev > 0.08  <=>  diff * 100 > prev * 8
  return diff * 100n > prevScaled * BigInt(FX_ANOMALY_THRESHOLD_PCT);
}

/**
 * Exact fixed-point currency conversion triangulated via CLP using 10^8 scaled BigInt arithmetic.
 * Returns the exact decimal string rounded to the target currency's canonical decimal places
 * (or 8 decimals when `preserveFullPrecision` is true).
 */
export function convertAmountExact(
  amount: string | number,
  fromCurrency: SupportedCurrency,
  toCurrency: SupportedCurrency,
  rates: Readonly<
    Record<SupportedCurrency, ExchangeRateDescriptor>
  > = DEFAULT_CENTRAL_BANK_RATES,
  preserveFullPrecision = false
): string {
  const targetDecimals = preserveFullPrecision
    ? SCALE_DIGITS
    : CURRENCY_DECIMALS[toCurrency];
  const amountScaled = parseScaledDecimal(amount);

  if (fromCurrency === toCurrency) {
    return formatScaledDecimal(amountScaled, targetDecimals);
  }

  const fromRateScaled = parseScaledDecimal(rates[fromCurrency].rateToClp);
  const toRateScaled = parseScaledDecimal(rates[toCurrency].rateToClp);
  if (toRateScaled <= 0n) {
    throw new Error(`Invalid target exchange rate for ${toCurrency}`);
  }

  // Triangulate in CLP with half-up rounding
  const numerator = amountScaled * fromRateScaled;
  const halfDivisor = toRateScaled / 2n;
  const convertedScaled =
    numerator >= 0n
      ? (numerator + halfDivisor) / toRateScaled
      : (numerator - halfDivisor) / toRateScaled;

  return formatScaledDecimal(convertedScaled, targetDecimals);
}

export interface CurrencyContextValue {
  readonly currency: SupportedCurrency;
  readonly setCurrency: (next: SupportedCurrency) => void;
  readonly rates: Readonly<Record<SupportedCurrency, ExchangeRateDescriptor>>;
  readonly activeRate: ExchangeRateDescriptor;
  readonly hasAnomaly: boolean;
  readonly convert: (
    amount: string | number,
    fromCurrency?: SupportedCurrency,
    toCurrency?: SupportedCurrency
  ) => string;
}

const CurrencyContext = createContext<CurrencyContextValue | undefined>(
  undefined
);

function readPersistedCurrency(
  fallback: SupportedCurrency = "CLP"
): SupportedCurrency {
  if (typeof window === "undefined" || !window.localStorage) {
    return fallback;
  }
  const stored = window.localStorage.getItem(CURRENCY_STORAGE_KEY);
  if (
    stored === "CLP" ||
    stored === "USD" ||
    stored === "EUR" ||
    stored === "BRL" ||
    stored === "UF"
  ) {
    return stored;
  }
  return fallback;
}

export interface CurrencyProviderProps {
  readonly children: ReactNode;
  readonly initialCurrency?: SupportedCurrency;
  readonly rates?: Readonly<Record<SupportedCurrency, ExchangeRateDescriptor>>;
}

export function CurrencyProvider({
  children,
  initialCurrency,
  rates = DEFAULT_CENTRAL_BANK_RATES,
}: CurrencyProviderProps) {
  const [currency, setCurrencyState] = useState<SupportedCurrency>(() =>
    initialCurrency ?? readPersistedCurrency("CLP")
  );

  const setCurrency = useCallback((next: SupportedCurrency): void => {
    setCurrencyState(next);
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(CURRENCY_STORAGE_KEY, next);
    }
  }, []);

  const activeRate = rates[currency];

  const hasAnomaly = useMemo(
    () => detectFxAnomaly(activeRate.rateToClp, activeRate.previousRateToClp),
    [activeRate]
  );

  const convert = useCallback(
    (
      amount: string | number,
      fromCurrency: SupportedCurrency = "CLP",
      toCurrency: SupportedCurrency = currency
    ): string => convertAmountExact(amount, fromCurrency, toCurrency, rates),
    [currency, rates]
  );

  const contextValue = useMemo<CurrencyContextValue>(
    () => ({
      currency,
      setCurrency,
      rates,
      activeRate,
      hasAnomaly,
      convert,
    }),
    [currency, setCurrency, rates, activeRate, hasAnomaly, convert]
  );

  return (
    <CurrencyContext.Provider value={contextValue}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency(): CurrencyContextValue {
  const context = useContext(CurrencyContext);
  if (!context) {
    throw new Error("useCurrency must be used within a <CurrencyProvider />");
  }
  return context;
}
