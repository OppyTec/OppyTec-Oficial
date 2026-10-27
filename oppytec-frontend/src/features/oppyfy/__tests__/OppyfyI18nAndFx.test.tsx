/**
 * oppytec-frontend/src/features/oppyfy/__tests__/OppyfyI18nAndFx.test.tsx
 *
 * Test suite para la Fase 7.1 y 7.2 de PLAN_MAESTRO_OPPYFY_AI.md:
 * "Internacionalización 100% es/en, Regla Inmutable Pollo King y Multi-Moneda FX"
 *
 * Cobertura:
 * 1. Paridad 1:1 estricta y simetría de interpolación ({{var}}) entre locales es/en para oppyfy.json y platform_admin.json.
 * 2. Cumplimiento estricto de la regla inmutable "Pollo King" (jamás traducido a "Chicken King" ni alterado).
 * 3. Precisión Multi-Moneda FX (CLP 0 decimales, USD 2 decimales, UF 4 decimales, fixed-point 10^8, sin floats contables).
 * 4. Renderizado fiel de componentes con formateo seguro (BuyCreditPackModal, OppyfyWorkerWalletsManager, MoneyBadge).
 */

import { render, screen, cleanup, fireEvent, renderHook } from "@testing-library/react";
import "@testing-library/jest-dom";
import { createElement, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  CURRENCY_DECIMALS,
  CURRENCY_SYMBOLS,
  CurrencyProvider,
  FX_ANOMALY_THRESHOLD_PCT,
  MoneyBadge,
  SUPPORTED_CURRENCIES,
  convertAmountExact,
  detectFxAnomaly,
  formatCurrencyAmount,
  formatMoney,
  formatScaledDecimal,
  parseScaledDecimal,
  useCurrencyFormatter,
} from "@/shared/currency";
import {
  I18N_NAMESPACES,
  I18N_RESOURCES,
  IMMUTABLE_PROPER_NOUNS,
  type TranslatableDynamicRecord,
  resolveDynamicFieldI18n,
  setActiveLanguage,
  translateKey,
} from "@/shared/i18n";

import { BuyCreditPackModal } from "../components/governance/BuyCreditPackModal";
import { OppyfyWorkerWalletsManager } from "../components/governance/OppyfyWorkerWalletsManager";
import type {
  AiCreditPackQuoteResponse,
  AiCreditPackResponse,
  OppyfyTenantCreditBagSummary,
  OppyfyWorkerWalletItem,
} from "../types";

// ============================================================================
// HELPERS DE INSPECCIÓN RECURSIVA DE CLAVES E INTERPOLACIONES
// ============================================================================
function extractLeafEntries(
  obj: unknown,
  prefix = ""
): Array<{ key: string; value: string }> {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) {
    return prefix ? [{ key: prefix, value: String(obj ?? "") }] : [];
  }
  return Object.entries(obj).flatMap(([k, v]) =>
    extractLeafEntries(v, prefix ? `${prefix}.${k}` : k)
  );
}

function extractInterpolationPlaceholders(text: string): string[] {
  const matches = text.match(/\{\{\s*[\w.]+\s*\}\}/g) ?? [];
  return matches.map((m) => m.replace(/\s+/g, "")).sort();
}

// ============================================================================
// MOCK DATA PARA PRUEBAS DE COMPONENTES
// ============================================================================
const MOCK_PACKS: readonly AiCreditPackResponse[] = [
  {
    id: 1,
    pack_name: "Pack Inicial Starter",
    credits_amount: 1000,
    price_clp: "15000.00",
    price_usd: "15.00",
    bonus_credits: 0,
    total_credits: 1000,
    is_popular: false,
    is_active: true,
    sort_order: 1,
    plan_tier_discounts: {},
  },
  {
    id: 2,
    pack_name: "Pack Enterprise Pollo King",
    credits_amount: 25000,
    price_clp: "299000.00",
    price_usd: "310.00",
    bonus_credits: 2500,
    total_credits: 27500,
    is_popular: true,
    is_active: true,
    sort_order: 2,
    plan_tier_discounts: {},
  },
];

const MOCK_BAG: OppyfyTenantCreditBagSummary = {
  total_purchased_credits: 50000,
  total_allocated_credits: 15000,
  total_consumed_credits: 8250,
  remaining_pool_credits: 35000,
};

const MOCK_WORKERS: readonly OppyfyWorkerWalletItem[] = [
  {
    user_id: 1,
    full_name: "Juan Chef",
    role_name: "Chef Ejecutivo",
    email: "chef@polloking.cl",
    assigned_credit_ceiling: 500,
    consumed_credits_total: 120,
    remaining_credits: 380,
    is_oppyfy_enabled: true,
  },
  {
    user_id: 2,
    full_name: "Pedro Cocinero",
    role_name: "Cocinero",
    email: "pedro@polloking.cl",
    assigned_credit_ceiling: 100,
    consumed_credits_total: 80,
    remaining_credits: 20,
    is_oppyfy_enabled: false,
  },
];

// ============================================================================
// TEST SUITE PRINCIPAL
// ============================================================================
describe("Fase 7 — OppyFy & Platform Admin i18n Symmetry, Pollo King Guard & FX Precision", () => {
  beforeEach(() => {
    cleanup();
    window.localStorage.clear();
    setActiveLanguage("es");
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    setActiveLanguage("es");
  });

  // ==========================================================================
  // 1. PARIDAD 1:1 Y SIMETRÍA ES/EN
  // ==========================================================================
  describe("1. Paridad 1:1 Estricta y Simetría de Claves e Interpolación (es/en)", () => {
    it("valida paridad 1:1 estricta de claves y {{placeholders}} en oppyfy.json", () => {
      expect(I18N_NAMESPACES).toContain("oppyfy");

      const esEntries = extractLeafEntries(I18N_RESOURCES.es?.oppyfy);
      const enEntries = extractLeafEntries(I18N_RESOURCES.en?.oppyfy);

      expect(esEntries.length).toBeGreaterThan(0);
      expect(enEntries.length).toBeGreaterThan(0);

      const esKeys = esEntries.map((e) => e.key).sort();
      const enKeys = enEntries.map((e) => e.key).sort();

      expect(esKeys).toEqual(enKeys);

      const enMap = new Map(enEntries.map((e) => [e.key, e.value]));
      for (const { key, value: esVal } of esEntries) {
        const enVal = enMap.get(key) ?? "";
        expect(esVal.trim().length, `Clave vacía en es: ${key}`).toBeGreaterThan(0);
        expect(enVal.trim().length, `Clave vacía en en: ${key}`).toBeGreaterThan(0);

        const esPlaceholders = extractInterpolationPlaceholders(esVal);
        const enPlaceholders = extractInterpolationPlaceholders(enVal);
        expect(
          esPlaceholders,
          `Placeholders mismatch en clave ${key}`
        ).toEqual(enPlaceholders);
      }
    });

    it("valida paridad 1:1 estricta de claves y {{placeholders}} en platform_admin.json", () => {
      expect(I18N_NAMESPACES).toContain("platform_admin");

      const esEntries = extractLeafEntries(I18N_RESOURCES.es?.platform_admin);
      const enEntries = extractLeafEntries(I18N_RESOURCES.en?.platform_admin);

      expect(esEntries.length).toBeGreaterThan(0);
      expect(enEntries.length).toBeGreaterThan(0);

      const esKeys = esEntries.map((e) => e.key).sort();
      const enKeys = enEntries.map((e) => e.key).sort();

      expect(esKeys).toEqual(enKeys);

      const enMap = new Map(enEntries.map((e) => [e.key, e.value]));
      for (const { key, value: esVal } of esEntries) {
        const enVal = enMap.get(key) ?? "";
        expect(esVal.trim().length, `Clave vacía en es: ${key}`).toBeGreaterThan(0);
        expect(enVal.trim().length, `Clave vacía en en: ${key}`).toBeGreaterThan(0);

        const esPlaceholders = extractInterpolationPlaceholders(esVal);
        const enPlaceholders = extractInterpolationPlaceholders(enVal);
        expect(
          esPlaceholders,
          `Placeholders mismatch en clave ${key}`
        ).toEqual(enPlaceholders);
      }
    });

    it("conmuta dinámicamente entre es y en para términos de OppyFy y Gobernanza", () => {
      setActiveLanguage("es");
      expect(translateKey("oppyfy", "governance.wallets.pool_title")).toBe(
        "Bolsa Global de Créditos del Tenant"
      );
      expect(translateKey("oppyfy", "governance.buy_pack_modal.popular_badge")).toBe(
        "Más Elegido"
      );
      expect(translateKey("oppyfy", "governance.wallets.status_enabled")).toBe(
        "Habilitado"
      );
      expect(translateKey("oppyfy", "governance.wallets.status_disabled")).toBe(
        "Inhabilitado"
      );

      setActiveLanguage("en");
      expect(translateKey("oppyfy", "governance.wallets.pool_title")).toBe(
        "Tenant Global Credit Pool"
      );
      expect(translateKey("oppyfy", "governance.buy_pack_modal.popular_badge")).toBe(
        "Most Popular"
      );
      expect(translateKey("oppyfy", "governance.wallets.status_enabled")).toBe(
        "Enabled"
      );
      expect(translateKey("oppyfy", "governance.wallets.status_disabled")).toBe(
        "Disabled"
      );
    });
  });

  // ==========================================================================
  // 2. REGLA INMUTABLE "POLLO KING"
  // ==========================================================================
  describe("2. Regla Inmutable Pollo King (Nombres Comerciales Jamás Traducidos)", () => {
    it("incluye 'Pollo King' en la lista inmutable IMMUTABLE_PROPER_NOUNS", () => {
      expect(IMMUTABLE_PROPER_NOUNS).toContain("Pollo King");
    });

    it("resuelve 'Pollo King' idéntico en 'es' y 'en' a través de resolveDynamicFieldI18n", () => {
      const recordsToTest: TranslatableDynamicRecord[] = [
        {
          name: "Pollo King",
          name_i18n: {
            es: "Pollo Rey",
            en: "Chicken King",
          },
          is_proper_noun: true,
        },
        {
          name: "Pollo King",
          name_i18n: {
            en: "King of Chickens Inc",
          },
        },
        {
          name: "  Pollo King  ",
          name_i18n: {
            en: "Chicken King Corp",
          },
        },
      ];

      for (const rec of recordsToTest) {
        expect(resolveDynamicFieldI18n(rec, "es")).toBe(rec.name);
        expect(resolveDynamicFieldI18n(rec, "en")).toBe(rec.name);
      }
    });

    it("verifica que los mensajes de sugerencia y resumen en oppyfy.json preservan 'Pollo King' sin traducir", () => {
      setActiveLanguage("es");
      const esFefo = translateKey("oppyfy", "chat.suggestion_fefo");
      const esSummary = translateKey("oppyfy", "rollover_modal.default_summary");

      expect(esFefo).toContain("Pollo King");
      expect(esSummary).toContain("Pollo King");

      setActiveLanguage("en");
      const enFefo = translateKey("oppyfy", "chat.suggestion_fefo");
      const enSummary = translateKey("oppyfy", "rollover_modal.default_summary");

      expect(enFefo).toContain("Pollo King");
      expect(enSummary).toContain("Pollo King");
      expect(enFefo).not.toContain("Chicken King");
      expect(enSummary).not.toContain("Chicken King");
    });

    it("comprueba que el paquete 'Pack Enterprise Pollo King' mantiene el nombre intacto", () => {
      const enterprisePack = MOCK_PACKS[1]!;
      expect(enterprisePack.pack_name).toBe("Pack Enterprise Pollo King");
      expect(enterprisePack.pack_name).not.toContain("Chicken");
    });
  });

  // ==========================================================================
  // 3. PRECISIÓN MULTI-MONEDA FX (CLP, USD, UF) Y CERO FLOATS
  // ==========================================================================
  describe("3. Multi-Moneda FX y Precisión Exacta Decimal / Fixed-Point 10^8", () => {
    it("valida la configuración canónica de decimales para CLP (0), USD (2) y UF (4)", () => {
      expect(SUPPORTED_CURRENCIES).toEqual(["CLP", "USD", "EUR", "BRL", "UF"]);
      expect(CURRENCY_DECIMALS.CLP).toBe(0);
      expect(CURRENCY_DECIMALS.USD).toBe(2);
      expect(CURRENCY_DECIMALS.UF).toBe(4);
      expect(CURRENCY_SYMBOLS.CLP).toBe("$");
      expect(CURRENCY_SYMBOLS.USD).toBe("US$");
    });

    it("formatea montos contables sin derivas de coma flotante IEEE-754", () => {
      // 0.1 + 0.2 en floats clásicos da 0.30000000000000004
      const p1 = parseScaledDecimal("0.1");
      const p2 = parseScaledDecimal("0.2");
      expect(formatScaledDecimal(p1 + p2, 2)).toBe("0.30");

      // Monto CLP con 0 decimales y separador de miles
      expect(formatCurrencyAmount("299000.00", "CLP")).toBe("$299.000");
      expect(formatMoney("15000", "CLP")).toBe("$15.000");

      // Monto USD con 2 decimales y separador de comas
      expect(formatCurrencyAmount("310.00", "USD")).toBe("US$310.00");
      expect(formatMoney("1250.75", "USD")).toBe("US$1,250.75");

      // Monto UF con 4 decimales
      expect(formatCurrencyAmount("8.5521", "UF")).toBe("UF 8,5521");
    });

    it("triangula conversiones de divisa exactas vía tipos de cambio de Banco Central", () => {
      // 9600 CLP a USD con tasa 960 CLP/USD = 10.00 USD
      const usdAmount = convertAmountExact("9600", "CLP", "USD");
      expect(usdAmount).toBe("10.00");

      // 10 USD a CLP = 9600 CLP
      const clpAmount = convertAmountExact("10", "USD", "CLP");
      expect(clpAmount).toBe("9600");

      // 38400 CLP a UF con tasa 38400 = 1.0000 UF
      const ufAmount = convertAmountExact("38400", "CLP", "UF");
      expect(ufAmount).toBe("1.0000");
    });

    it("dispara advertencia de anomalía FX cuando la variación diaria supera el 8%", () => {
      expect(FX_ANOMALY_THRESHOLD_PCT).toBe(8);
      // Variación menor al 8% (960 vs 955)
      expect(detectFxAnomaly("960.00000000", "955.00000000")).toBe(false);
      // Variación superior al 8% (1050 vs 955 -> +9.9%)
      expect(detectFxAnomaly("1050.00000000", "955.00000000")).toBe(true);
    });

    it("opera correctamente a través de useCurrencyFormatter hook", () => {
      const wrapper = ({ children }: { children: ReactNode }) =>
        createElement(CurrencyProvider, { initialCurrency: "CLP", children }, children);

      const { result } = renderHook(() => useCurrencyFormatter(), { wrapper });

      expect(result.current.currency).toBe("CLP");
      expect(result.current.format("15000")).toBe("$15.000");
      expect(result.current.format("15.00", "USD")).toBe("US$15.00");
      expect(result.current.convertAndFormat("96000", "CLP", "USD")).toBe("US$100.00");
    });
  });

  // ==========================================================================
  // 4. PRUEBAS DE COMPONENTES CON FORMATEO SEGURO Y PRESERVACIÓN
  // ==========================================================================
  describe("4. Renderizado Seguro de Componentes (BuyCreditPackModal, Wallets, MoneyBadge)", () => {
    it("renderiza el modal BuyCreditPackModal con precios formateados en CLP y USD sin alteración de Pollo King", () => {
      const mockQuote: AiCreditPackQuoteResponse = {
        pack_id: 2,
        pack_name: "Pack Enterprise Pollo King",
        base_plan_tier: "enterprise",
        discount_pct: 15,
        original_price_clp: "299000.00",
        original_price_usd: "310.00",
        final_price_clp: "254150.00",
        final_price_usd: "263.50",
        total_credits: 27500,
      };

      const handleQuote = vi.fn().mockResolvedValue(mockQuote);
      const handleClose = vi.fn();

      render(
        <CurrencyProvider initialCurrency="CLP">
          <BuyCreditPackModal
            isOpen={true}
            packs={MOCK_PACKS}
            onClose={handleClose}
            onQuotePack={handleQuote}
          />
        </CurrencyProvider>
      );

      // Verificar que el Pack 2 muestra el nombre inmutable "Pack Enterprise Pollo King"
      expect(screen.getByText("Pack Enterprise Pollo King")).toBeInTheDocument();

      // Verificar precios formateados en las tarjetas
      expect(screen.getByTestId("credit-pack-price-clp-1")).toHaveTextContent("$15.000 CLP");
      expect(screen.getByTestId("credit-pack-price-usd-1")).toHaveTextContent("US$15.00");

      expect(screen.getByTestId("credit-pack-price-clp-2")).toHaveTextContent("$299.000 CLP");
      expect(screen.getByTestId("credit-pack-price-usd-2")).toHaveTextContent("US$310.00");

      // Seleccionar el pack 2 para cotizar
      fireEvent.click(screen.getByTestId("credit-pack-card-2"));
      expect(handleQuote).toHaveBeenCalledWith(2, "pro");
    });

    it("renderiza OppyfyWorkerWalletsManager y conmuta el estado de trabajador con traducciones simétricas", () => {
      const handleUpdate = vi.fn().mockResolvedValue(undefined);
      const handleQuote = vi.fn().mockResolvedValue({} as AiCreditPackQuoteResponse);

      const { rerender } = render(
        <CurrencyProvider initialCurrency="CLP">
          <OppyfyWorkerWalletsManager
            workers={MOCK_WORKERS}
            tenantCreditBag={MOCK_BAG}
            aiPacks={MOCK_PACKS}
            onUpdateWorkerWallet={handleUpdate}
            onQuotePack={handleQuote}
          />
        </CurrencyProvider>
      );

      // En español por defecto
      expect(screen.getByTestId("toggle-worker-oppyfy-1")).toHaveTextContent("Habilitado");
      expect(screen.getByTestId("toggle-worker-oppyfy-2")).toHaveTextContent("Inhabilitado");

      // Cambiar a inglés y re-renderizar
      setActiveLanguage("en");
      rerender(
        <CurrencyProvider initialCurrency="CLP">
          <OppyfyWorkerWalletsManager
            workers={MOCK_WORKERS}
            tenantCreditBag={MOCK_BAG}
            aiPacks={MOCK_PACKS}
            onUpdateWorkerWallet={handleUpdate}
            onQuotePack={handleQuote}
          />
        </CurrencyProvider>
      );

      expect(screen.getByTestId("toggle-worker-oppyfy-1")).toHaveTextContent("Enabled");
      expect(screen.getByTestId("toggle-worker-oppyfy-2")).toHaveTextContent("Disabled");
    });

    it("renderiza MoneyBadge con origen de banco central y manejo de anomalía de tipo de cambio", () => {
      const { rerender } = render(
        <CurrencyProvider initialCurrency="CLP">
          <MoneyBadge amount="96000" baseCurrency="CLP" displayCurrency="USD" />
        </CurrencyProvider>
      );

      const badge = screen.getByTestId("money-badge");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute("data-currency", "USD");
      expect(screen.getByTestId("money-badge-amount")).toHaveTextContent("US$100.00");
      expect(screen.getByTestId("money-badge-source")).toHaveTextContent("BCCh");

      // CLP directo
      rerender(
        <CurrencyProvider initialCurrency="CLP">
          <MoneyBadge amount="150000" baseCurrency="CLP" displayCurrency="CLP" />
        </CurrencyProvider>
      );
      expect(screen.getByTestId("money-badge-amount")).toHaveTextContent("$150.000");
    });
  });
});
