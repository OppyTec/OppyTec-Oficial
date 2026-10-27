import { renderHook } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  CURRENCY_DECIMALS,
  CurrencyProvider,
  SUPPORTED_CURRENCIES,
  type SupportedCurrency,
  convertAmountExact,
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
  getActiveLanguage,
  resolveDynamicFieldI18n,
  setActiveLanguage,
  translateKey,
} from "@/shared/i18n";
import {
  MOCK_COMPRAS,
  MOCK_MERMA_ANALYTICS,
  MOCK_MERMA_HISTORY,
  MOCK_PROCUREMENT_DASHBOARD,
  MOCK_PRODUCTOS_PROVEEDOR,
  MOCK_PROVEEDORES,
} from "../mockData";

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

describe("Phase 7 — Procurement i18n (es/en 1:1 Symmetry, Pollo King Rule) & Multi-Currency FX Precision", () => {
  beforeEach(() => {
    window.localStorage.clear();
    setActiveLanguage("es");
  });

  afterEach(() => {
    window.localStorage.clear();
    setActiveLanguage("es");
  });

  it("enforces 100% recursive 1:1 key symmetry and {{var}} placeholder parity in procurement.json, gestion.json, inventory.json and recipes.json", () => {
    expect(I18N_NAMESPACES).toContain("procurement");

    const esProcurement = I18N_RESOURCES.es?.procurement as Record<string, unknown>;
    const enProcurement = I18N_RESOURCES.en?.procurement as Record<string, unknown>;

    expect(esProcurement).toBeDefined();
    expect(enProcurement).toBeDefined();

    // Verify all required sections from Sub-modules 1, 2, and 3 exist in both locales
    const requiredSections = [
      // Sub-module 1: Purchase Orders & Receiving
      "orders",
      "dashboard",
      "reception",
      "incidences",
      "catalog",
      "draft",
      // Sub-module 2: Suppliers 360°
      "suppliers",
      "supplierDialog",
      "supplierCatalog",
      "supplierDashboard",
      // Sub-module 3: Waste Analytics (Mermas)
      "wasteAnalytics",
      "kpiDashboard",
      "mermaStats",
      "mermaHistory",
      "dateRangePicker",
    ] as const;

    for (const section of requiredSections) {
      expect(esProcurement[section]).toBeDefined();
      expect(enProcurement[section]).toBeDefined();
    }

    // Verify 0 orphan keys and identical {{var}} interpolation placeholders across procurement, gestion, inventory, recipes
    for (const ns of ["procurement", "gestion", "inventory", "recipes"] as const) {
      const esEntries = extractLeafEntries(I18N_RESOURCES.es?.[ns]);
      const enEntries = extractLeafEntries(I18N_RESOURCES.en?.[ns]);

      const esKeys = esEntries.map((e) => e.key).sort();
      const enKeys = enEntries.map((e) => e.key).sort();

      expect(esKeys).toEqual(enKeys);

      const enMap = new Map(enEntries.map((e) => [e.key, e.value]));
      for (const { key, value: esVal } of esEntries) {
        const enVal = enMap.get(key) ?? "";
        expect(esVal.trim().length).toBeGreaterThan(0);
        expect(enVal.trim().length).toBeGreaterThan(0);
        expect(extractInterpolationPlaceholders(esVal)).toEqual(
          extractInterpolationPlaceholders(enVal)
        );
      }
    }

    // Verify gestion, inventory and recipes tabs for 'pedidos' and 'mermas'
    setActiveLanguage("es");
    expect(translateKey("gestion", "tabs.pedidos")).toBe("Pedidos & Compras");
    expect(translateKey("gestion", "tabs.mermas")).toBe("Control de Mermas");
    expect(translateKey("inventory", "gestion_tabs.pedidos")).toBe("Pedidos & Compras");
    expect(translateKey("inventory", "gestion_tabs.mermas")).toBe("Control de Mermas");
    expect(translateKey("recipes", "tabs.pedidos")).toBe("Pedidos & Compras");
    expect(translateKey("recipes", "tabs.mermas")).toBe("Control de Mermas");

    setActiveLanguage("en");
    expect(translateKey("gestion", "tabs.pedidos")).toBe("Orders & Purchasing");
    expect(translateKey("gestion", "tabs.mermas")).toBe("Waste Control");
    expect(translateKey("inventory", "gestion_tabs.pedidos")).toBe("Orders & Purchasing");
    expect(translateKey("inventory", "gestion_tabs.mermas")).toBe("Waste Control");
    expect(translateKey("recipes", "tabs.pedidos")).toBe("Orders & Purchasing");
    expect(translateKey("recipes", "tabs.mermas")).toBe("Waste Control");
  });

  it("switches languages (es <-> en) seamlessly across all 3 procurement sub-modules", () => {
    // Spanish assertions
    setActiveLanguage("es");
    expect(getActiveLanguage()).toBe("es");

    // Sub-module 1
    expect(translateKey("procurement", "orders.title")).toBe(
      "Gestión de Pedidos y Abastecimiento"
    );
    expect(translateKey("procurement", "dashboard.kpi_total_spent")).toBe(
      "Inversión Acumulada"
    );
    expect(
      translateKey("procurement", "reception.order_reference", {
        orderNumber: "OC-2026-001",
        supplierName: "Distribuidora Austral Food SpA",
      })
    ).toBe("Orden OC-2026-001 • Distribuidora Austral Food SpA");
    expect(translateKey("procurement", "incidences.types.CADENA_FRIO")).toBe(
      "Ruptura de Cadena de Frío"
    );
    expect(translateKey("procurement", "catalog.col_agreed_price")).toBe(
      "Precio Pactado Neto"
    );
    expect(translateKey("procurement", "draft.submit_btn")).toBe(
      "Emitir Orden de Compra"
    );

    // Sub-module 2
    expect(translateKey("procurement", "suppliers.title")).toBe(
      "Directorio de Proveedores"
    );
    expect(translateKey("procurement", "supplierDialog.create_title")).toBe(
      "Registrar Nuevo Proveedor"
    );
    expect(
      translateKey("procurement", "supplierCatalog.title", {
        supplierName: "Pollo King",
      })
    ).toBe("Catálogo de Productos Pactados — Pollo King");
    expect(
      translateKey("procurement", "supplierDashboard.title", {
        supplierName: "Distribuidora Austral Food SpA",
      })
    ).toBe(
      "Dashboard Ejecutivo de Proveedor — Distribuidora Austral Food SpA"
    );

    // Sub-module 3
    expect(translateKey("procurement", "wasteAnalytics.title")).toBe(
      "Gestión y Control de Mermas"
    );
    expect(translateKey("procurement", "kpiDashboard.total_loss_ppp")).toBe(
      "Pérdida Económica Total (PPP)"
    );
    expect(translateKey("procurement", "mermaStats.by_reason_title")).toBe(
      "Distribución de Mermas por Motivo Tipificado"
    );
    expect(translateKey("procurement", "mermaHistory.col_total_ppp")).toBe(
      "Impacto Total PPP"
    );
    expect(translateKey("procurement", "dateRangePicker.presets.30d")).toBe(
      "Últimos 30 días"
    );

    // Switch to English
    setActiveLanguage("en");
    expect(getActiveLanguage()).toBe("en");

    // Sub-module 1 (en)
    expect(translateKey("procurement", "orders.title")).toBe(
      "Purchase Orders & Procurement Management"
    );
    expect(translateKey("procurement", "dashboard.kpi_total_spent")).toBe(
      "Cumulative Spend"
    );
    expect(
      translateKey("procurement", "reception.order_reference", {
        orderNumber: "OC-2026-001",
        supplierName: "Distribuidora Austral Food SpA",
      })
    ).toBe("Order OC-2026-001 • Distribuidora Austral Food SpA");
    expect(translateKey("procurement", "incidences.types.CADENA_FRIO")).toBe(
      "Cold Chain Breach"
    );
    expect(translateKey("procurement", "catalog.col_agreed_price")).toBe(
      "Agreed Net Price"
    );
    expect(translateKey("procurement", "draft.submit_btn")).toBe(
      "Issue Purchase Order"
    );

    // Sub-module 2 (en)
    expect(translateKey("procurement", "suppliers.title")).toBe(
      "Suppliers Directory"
    );
    expect(translateKey("procurement", "supplierDialog.create_title")).toBe(
      "Register New Supplier"
    );
    expect(
      translateKey("procurement", "supplierCatalog.title", {
        supplierName: "Pollo King",
      })
    ).toBe("Agreed Product Catalog — Pollo King");
    expect(
      translateKey("procurement", "supplierDashboard.title", {
        supplierName: "Distribuidora Austral Food SpA",
      })
    ).toBe("Supplier Executive Dashboard — Distribuidora Austral Food SpA");

    // Sub-module 3 (en)
    expect(translateKey("procurement", "wasteAnalytics.title")).toBe(
      "Waste Management & Analytics"
    );
    expect(translateKey("procurement", "kpiDashboard.total_loss_ppp")).toBe(
      "Total Economic Loss (WAC)"
    );
    expect(translateKey("procurement", "mermaStats.by_reason_title")).toBe(
      "Waste Distribution by Classified Reason"
    );
    expect(translateKey("procurement", "mermaHistory.col_total_ppp")).toBe(
      "Total WAC Impact"
    );
    expect(translateKey("procurement", "dateRangePicker.presets.30d")).toBe(
      "Last 30 days"
    );
  });

  it("strictly enforces the 'Pollo King' rule: commercial supplier proper nouns are never translated in es or en", () => {
    expect(IMMUTABLE_PROPER_NOUNS).toContain("Pollo King");
    expect(IMMUTABLE_PROPER_NOUNS).toContain("Distribuidora Austral Food SpA");

    const protectedSuppliers: TranslatableDynamicRecord[] = [
      {
        name: "Pollo King",
        name_i18n: {
          es: "Rey del Pollo",
          en: "Chicken King Corp",
        },
        is_proper_noun: true,
      },
      {
        name: "Pollo King",
        name_i18n: {
          en: "King Chicken",
        },
        // Even if is_proper_noun is omitted, IMMUTABLE_PROPER_NOUNS protects it
      },
      {
        name: "Distribuidora Austral Food SpA",
        name_i18n: {
          es: "Distribuidora de Alimentos del Sur",
          en: "Southern Food Distributor LLC",
        },
        is_proper_noun: true,
      },
      {
        name: "Distribuidora Austral Food SpA",
        name_i18n: {
          en: "Austral Food Distributors Inc.",
        },
      },
    ];

    for (const record of protectedSuppliers) {
      expect(resolveDynamicFieldI18n(record, "es")).toBe(record.name);
      expect(resolveDynamicFieldI18n(record, "en")).toBe(record.name);
    }

    // Verify mock dataset supplier names remain untouched across locale switches
    const australSupplier = MOCK_PROVEEDORES.find((p) =>
      p.razon_social.includes("Distribuidora Austral Food SpA")
    );
    expect(australSupplier).toBeDefined();
    expect(
      resolveDynamicFieldI18n(
        {
          name: australSupplier!.razon_social,
          name_i18n: { en: "Translated Supplier Name" },
          is_proper_noun: true,
        },
        "en"
      )
    ).toBe("Distribuidora Austral Food SpA");
  });

  it("formats and converts all procurement, supplier and waste PPP amounts with exact Decimal fixed-point precision across CLP, USD, EUR, BRL and UF", () => {
    expect(SUPPORTED_CURRENCIES).toEqual(["CLP", "USD", "EUR", "BRL", "UF"]);
    expect(CURRENCY_DECIMALS).toEqual({
      CLP: 0,
      USD: 2,
      EUR: 2,
      BRL: 2,
      UF: 4,
    });

    // Sub-module 1: Purchase Order financial amounts (exact Decimal strings, 0 accounting floats)
    const firstOrder = MOCK_COMPRAS[0]!;
    expect(firstOrder).toBeDefined();
    expect(typeof firstOrder.monto_neto).toBe("string");
    expect(typeof firstOrder.monto_impuestos).toBe("string");
    expect(typeof firstOrder.monto_total).toBe("string");
    expect(firstOrder.monto_neto).toBe("1218487.39");
    expect(firstOrder.monto_impuestos).toBe("231512.61");
    expect(firstOrder.monto_total).toBe("1450000.00");

    // Verify exact Decimal addition: monto_neto + monto_impuestos === monto_total
    const netScaled = parseScaledDecimal(firstOrder.monto_neto);
    const taxScaled = parseScaledDecimal(firstOrder.monto_impuestos);
    expect(formatScaledDecimal(netScaled + taxScaled, 2)).toBe(
      firstOrder.monto_total
    );

    // Format with formatMoney / formatCurrencyAmount across all 5 currencies
    expect(formatMoney(firstOrder.monto_total, "CLP")).toBe(
      formatCurrencyAmount(firstOrder.monto_total, "CLP")
    );
    expect(formatMoney(firstOrder.monto_total, "CLP")).toBe("$1.450.000");
    expect(formatMoney("960000", "USD")).toBe("US$960,000.00");
    expect(formatMoney("1250.50", "EUR")).toBe("€1.250,50");
    expect(formatMoney("1250.50", "BRL")).toBe("R$1.250,50");
    expect(formatMoney("25.125", "UF")).toBe("UF 25,1250");
    expect(formatMoney(MOCK_PROCUREMENT_DASHBOARD.monto_total_mes, "CLP")).toBe(
      "$18.450.000"
    );

    // Sub-module 2: Agreed Supplier Catalog prices (Pollo King @ "3850.00")
    const firstCatalogItem = MOCK_PRODUCTOS_PROVEEDOR[1]?.[0];
    expect(firstCatalogItem).toBeDefined();
    expect(firstCatalogItem?.producto_nombre).toBe("Pollo King");
    expect(firstCatalogItem?.precio_pactado).toBe("3850.00");
    const catalogUsd = convertAmountExact(
      firstCatalogItem?.precio_pactado ?? "0",
      "CLP",
      "USD"
    );
    expect(catalogUsd).toMatch(/^\d+\.\d{2}$/);

    // Sub-module 3: Waste Analytics PPP amounts
    const firstMerma = MOCK_MERMA_HISTORY[0]!;
    expect(firstMerma).toBeDefined();
    expect(firstMerma.producto_nombre).toBe("Pollo King");
    expect(firstMerma.costo_total).toBe("46200.00");
    expect(MOCK_MERMA_ANALYTICS.total_perdida_ppp).toBe("348500.00");

    const mermaTotalClp = formatMoney(
      MOCK_MERMA_ANALYTICS.total_perdida_ppp,
      "CLP"
    );
    expect(mermaTotalClp).toBe("$348.500");

    const mermaTotalUf = convertAmountExact(
      MOCK_MERMA_ANALYTICS.total_perdida_ppp,
      "CLP",
      "UF"
    );
    expect(mermaTotalUf).toMatch(/^\d+\.\d{4}$/);

    // Verify fixed-point math avoids classic IEEE-754 float bug (0.1 + 0.2 === 0.30)
    const scaledSum = parseScaledDecimal("0.1") + parseScaledDecimal("0.2");
    expect(formatScaledDecimal(scaledSum, 2)).toBe("0.30");

    // Verify useCurrencyFormatter hook inside CurrencyProvider for each currency
    const expectedFormats: Record<SupportedCurrency, string> = {
      CLP: "$38.400",
      USD: "US$40.00",
      EUR: "€36,92",
      BRL: "R$200,00",
      UF: "UF 1,0000",
    };

    for (const currency of SUPPORTED_CURRENCIES) {
      const wrapper = ({ children }: { children: ReactNode }) =>
        createElement(
          CurrencyProvider,
          { initialCurrency: currency, children },
          children
        );
      const { result } = renderHook(() => useCurrencyFormatter(), { wrapper });
      expect(result.current.currency).toBe(currency);
      expect(result.current.convertAndFormat("38400", "CLP", currency)).toBe(
        expectedFormats[currency]
      );
    }
  });
});
