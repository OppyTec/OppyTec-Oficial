import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import {
  getActiveLanguage,
  LanguageFlagSelector,
  setActiveLanguage,
} from "@/shared/i18n";
import {
  CURRENCY_DECIMALS,
  CURRENCY_STORAGE_KEY,
  CURRENCY_SYMBOLS,
  type CentralBankSource,
  type CurrencyContextValue,
  CurrencyProvider,
  type CurrencyProviderProps,
  CurrencySelector,
  type CurrencySelectorProps,
  DEFAULT_CENTRAL_BANK_RATES,
  type ExchangeRateDescriptor,
  FX_ANOMALY_THRESHOLD_PCT,
  MoneyBadge,
  type MoneyBadgeProps,
  SUPPORTED_CURRENCIES,
  type SupportedCurrency,
  type UseCurrencyFormatterReturn,
  convertAmountExact,
  detectFxAnomaly,
  formatCurrencyAmount,
  formatScaledDecimal,
  parseScaledDecimal,
  useCurrency,
  useCurrencyFormatter,
} from "./index";

function CurrencyHookConsumer() {
  const ctx: CurrencyContextValue = useCurrency();
  const fmt: UseCurrencyFormatterReturn = useCurrencyFormatter();
  return (
    <div>
      <span data-testid="ctx-currency">{ctx.currency}</span>
      <span data-testid="ctx-formatted">{fmt.format("12500")}</span>
      <span data-testid="ctx-converted">
        {fmt.convertAndFormat("9600", "CLP", ctx.currency)}
      </span>
    </div>
  );
}

describe("Frontend Multi-Currency FX Suite (CLP, USD, EUR, BRL, UF & Central Bank Governance)", () => {
  beforeEach(() => {
    cleanup();
    window.localStorage.clear();
    setActiveLanguage("es");
  });

  afterEach(() => {
    cleanup();
  });

  it("formats CLP (0 decimals), USD/EUR/BRL (2 decimals), and UF (4 decimals) using exact fixed-point math", () => {
    expect(SUPPORTED_CURRENCIES).toEqual(["CLP", "USD", "EUR", "BRL", "UF"]);
    expect(CURRENCY_DECIMALS.CLP).toBe(0);
    expect(CURRENCY_DECIMALS.USD).toBe(2);
    expect(CURRENCY_DECIMALS.EUR).toBe(2);
    expect(CURRENCY_DECIMALS.BRL).toBe(2);
    expect(CURRENCY_DECIMALS.UF).toBe(4);
    expect(CURRENCY_SYMBOLS.UF).toBe("UF");

    const scaled = parseScaledDecimal("12500.55");
    expect(formatScaledDecimal(scaled, 0)).toBe("12501");

    expect(formatCurrencyAmount("12500", "CLP")).toBe("$12.500");
    expect(formatCurrencyAmount("1250.5", "USD")).toBe("US$1,250.50");
    expect(formatCurrencyAmount("1250.5", "EUR")).toBe("€1.250,50");
    expect(formatCurrencyAmount("1250.5", "BRL")).toBe("R$1.250,50");
    expect(formatCurrencyAmount("1.25", "UF")).toBe("UF 1,2500");
  });

  it("converts exact decimal amounts via BCCh / BCE Frankfurter rates and flags >8% anomalies", () => {
    expect(FX_ANOMALY_THRESHOLD_PCT).toBe(8);
    expect(convertAmountExact("9600", "CLP", "USD")).toBe("10.00");
    expect(convertAmountExact("10", "USD", "CLP")).toBe("9600");
    expect(convertAmountExact("38400", "CLP", "UF")).toBe("1.0000");
    expect(convertAmountExact("1040", "CLP", "EUR")).toBe("1.00");
    expect(convertAmountExact("1920", "CLP", "BRL")).toBe("10.00");

    expect(detectFxAnomaly("960.00000000", "955.00000000")).toBe(false);
    expect(detectFxAnomaly("1100.00000000", "955.00000000")).toBe(true);
  });

  it("renders CurrencySelector and MoneyBadge independently of LanguageFlagSelector", () => {
    const onCurrencyChange = vi.fn<(c: SupportedCurrency) => void>();
    const selectorProps: CurrencySelectorProps = { onCurrencyChange };
    const badgeProps: MoneyBadgeProps = {
      amount: "38400",
      baseCurrency: "CLP",
    };

    const customSource: CentralBankSource = "BCCh";
    const anomalousUsd: ExchangeRateDescriptor = {
      currency: "USD",
      rateToClp: "1150.00000000",
      previousRateToClp: "950.00000000",
      source: customSource,
      updatedAtIso: "2026-01-15T08:30:00Z",
    };

    const providerProps: CurrencyProviderProps = {
      initialCurrency: "CLP",
      rates: {
        ...DEFAULT_CENTRAL_BANK_RATES,
        USD: anomalousUsd,
      },
      children: null,
    };

    render(
      <CurrencyProvider
        initialCurrency={providerProps.initialCurrency}
        rates={providerProps.rates}
      >
        <LanguageFlagSelector />
        <CurrencySelector {...selectorProps} />
        <MoneyBadge {...badgeProps} />
        <CurrencyHookConsumer />
      </CurrencyProvider>
    );

    expect(screen.getByTestId("money-badge-amount").textContent).toBe("$38.400");
    expect(screen.getByTestId("ctx-formatted").textContent).toBe("$12.500");

    // Switch currency to UF -> language remains 'es'
    fireEvent.click(screen.getByTestId("currency-option-UF"));
    expect(onCurrencyChange).toHaveBeenCalledWith("UF");
    expect(window.localStorage.getItem(CURRENCY_STORAGE_KEY)).toBe("UF");
    expect(getActiveLanguage()).toBe("es");
    expect(screen.getByTestId("money-badge-amount").textContent).toBe(
      "UF 1,0000"
    );

    // Switch language to 'en' -> currency remains 'UF'
    fireEvent.click(screen.getByTestId("lang-option-en"));
    expect(getActiveLanguage()).toBe("en");
    expect(
      screen.getByTestId("currency-selector").getAttribute("data-active-currency")
    ).toBe("UF");

    // Switch currency to USD with >8% anomaly -> anomaly badge is rendered
    fireEvent.click(screen.getByTestId("currency-option-USD"));
    expect(
      screen.getByTestId("money-badge").getAttribute("data-fx-anomaly")
    ).toBe("true");
    expect(screen.getByTestId("money-badge-anomaly")).toBeDefined();
  });

  it("renders CurrencySelector as an interactive dropdown showing active currency code + symbol and closes upon selection", () => {
    const onCurrencyChange = vi.fn<(c: SupportedCurrency) => void>();
    render(
      <CurrencyProvider initialCurrency="CLP">
        <CurrencySelector onCurrencyChange={onCurrencyChange} />
      </CurrencyProvider>
    );

    const trigger = screen.getByRole("button", { name: /Moneda/i });
    expect(trigger.textContent).toContain("CLP");
    expect(trigger.getAttribute("aria-expanded")).toBe("false");

    // Open dropdown
    fireEvent.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");

    // Select EUR
    const eurOption = screen.getByTestId("currency-option-EUR");
    fireEvent.click(eurOption);

    // Dropdown closes and trigger text updates to "EUR"
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(trigger.textContent).toContain("EUR");
    expect(onCurrencyChange).toHaveBeenCalledWith("EUR");
  });
});
