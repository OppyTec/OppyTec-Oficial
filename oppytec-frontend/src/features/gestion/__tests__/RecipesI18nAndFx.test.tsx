import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import recipesEs from "@/shared/i18n/locales/es/recipes.json";
import recipesEn from "@/shared/i18n/locales/en/recipes.json";
import { setActiveLanguage } from "@/shared/i18n";
import {
  CurrencyProvider,
  MoneyBadge,
  convertAmountExact,
  formatCurrencyAmount,
} from "@/shared/currency";
import { formatMoney } from "@/shared/lib";
import { GestionTabNav } from "../components/GestionTabNav";
import { RecetasToolbar } from "../components/recetas/RecetasToolbar";
import { RecetasTable } from "../components/recetas/RecetasTable";
import { RecetaMobileCard } from "../components/recetas/RecetaMobileCard";
import { CombosToolbar } from "../components/combos/CombosToolbar";
import { CombosTable } from "../components/combos/CombosTable";
import { ComboMobileCard } from "../components/combos/ComboMobileCard";
import {
  RecetaDialog,
  calculateIngredientTotalCost,
} from "../components/RecetaDialog";
import { ComboDialog } from "../components/ComboDialog";
import { OptionGroupSelectorModal } from "../components/OptionGroupSelectorModal";
import { RecetaDetalleModal } from "../components/RecetaDetalleModal";
import { AllergenBadge } from "../components/AllergenBadge";
import {
  INITIAL_RECETAS_MOCK,
  INITIAL_CATEGORIAS_RECETAS_MOCK,
} from "../hooks/useRecetas";
import {
  INITIAL_COMBOS_MOCK,
  INITIAL_CATEGORIAS_COMBOS_MOCK,
} from "../hooks/useCombos";
import { INITIAL_GRUPOS_OPCIONES_MOCK } from "../hooks/useGruposOpciones";
import { INITIAL_PRODUCTOS_MOCK } from "../useGestion";

vi.mock("@/shared/api/httpClient", async () => {
  const actual = await vi.importActual<any>("@/shared/api/httpClient");
  return {
    ...actual,
    apiRequest: vi.fn().mockRejectedValue(new Error("Offline in test harness")),
  };
});

function extractLeafPaths(
  obj: Record<string, unknown>,
  prefix = ""
): Array<{ path: string; value: unknown }> {
  const entries: Array<{ path: string; value: unknown }> = [];
  for (const key of Object.keys(obj)) {
    const fullPath = prefix ? `${prefix}.${key}` : key;
    const val = obj[key];
    if (val !== null && typeof val === "object" && !Array.isArray(val)) {
      entries.push(...extractLeafPaths(val as Record<string, unknown>, fullPath));
    } else {
      entries.push({ path: fullPath, value: val });
    }
  }
  return entries;
}

function extractInterpolationPlaceholders(str: string): string[] {
  const matches = str.match(/\{\{[^}]+\}\}/g);
  return matches ? [...matches].sort() : [];
}

function renderWithProviders(
  ui: React.ReactElement,
  currency: "CLP" | "USD" | "EUR" | "UF" = "CLP"
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <CurrencyProvider initialCurrency={currency}>{ui}</CurrencyProvider>
    </QueryClientProvider>
  );
}

describe("FASE 7 (7.1 & 7.2): Paridad i18n 100% (es/en recipes.json) y Multi-Moneda FX con Decimal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    act(() => {
      setActiveLanguage("es");
    });
  });

  afterEach(() => {
    act(() => {
      setActiveLanguage("es");
    });
    cleanup();
  });

  // ==========================================================================
  // 1. Paridad 1:1 de Claves e Interpolaciones en es/recipes.json vs en/recipes.json
  // ==========================================================================
  describe("1. Paridad Exacta 1:1 en shared/i18n/locales/{es,en}/recipes.json", () => {
    it("guarantees 100% key parity between es/recipes.json and en/recipes.json with non-empty values", () => {
      const esLeaves = extractLeafPaths(recipesEs as Record<string, unknown>);
      const enLeaves = extractLeafPaths(recipesEn as Record<string, unknown>);

      const esKeys = esLeaves.map((e) => e.path).sort();
      const enKeys = enLeaves.map((e) => e.path).sort();

      expect(esKeys.length).toBeGreaterThan(150);
      expect(esKeys).toEqual(enKeys);

      for (const leaf of esLeaves) {
        expect(typeof leaf.value).toBe("string");
        expect((leaf.value as string).trim().length).toBeGreaterThan(0);
      }

      for (const leaf of enLeaves) {
        expect(typeof leaf.value).toBe("string");
        expect((leaf.value as string).trim().length).toBeGreaterThan(0);
      }
    });

    it("preserves identical {{...}} interpolation placeholders across es and en", () => {
      const esMap = new Map(
        extractLeafPaths(recipesEs as Record<string, unknown>).map((e) => [
          e.path,
          String(e.value),
        ])
      );
      const enMap = new Map(
        extractLeafPaths(recipesEn as Record<string, unknown>).map((e) => [
          e.path,
          String(e.value),
        ])
      );

      for (const [key, esText] of esMap.entries()) {
        const enText = enMap.get(key) ?? "";
        const esVars = extractInterpolationPlaceholders(esText);
        const enVars = extractInterpolationPlaceholders(enText);
        expect(enVars).toEqual(esVars);
      }
    });
  });

  // ==========================================================================
  // 2. Cambio Dinámico de Idioma (es <-> en) en Vistas, Tablas y Modales
  // ==========================================================================
  describe("2. Cambio Dinámico de Idioma (es <-> en) sin Strings Hardcodeadas", () => {
    it("switches GestionTabNav, RecetasToolbar, RecetasTable, and RecetaMobileCard dynamically between es and en", () => {
      renderWithProviders(
        <div>
          <GestionTabNav activeTab="recetas" onSelectTab={vi.fn()} />
          <RecetasToolbar
            searchQuery="lomo"
            onSearchChange={vi.fn()}
            selectedCategoriaId={null}
            onSelectCategoria={vi.fn()}
            categorias={INITIAL_CATEGORIAS_RECETAS_MOCK}
            tipoFiltro="todas"
            onSelectTipo={vi.fn()}
            onNewReceta={vi.fn()}
            onManageCategorias={vi.fn()}
          />
          <RecetasTable
            recetas={INITIAL_RECETAS_MOCK}
            onView={vi.fn()}
            onEdit={vi.fn()}
            onDuplicate={vi.fn()}
            onDelete={vi.fn()}
          />
          <RecetaMobileCard receta={INITIAL_RECETAS_MOCK[0]!} onView={vi.fn()} />
        </div>
      );

      // Spanish assertions
      expect(screen.getByTestId("gestion-tab-recetas").textContent).toBe(
        "Recetas & Escandallos"
      );
      expect(screen.getByTestId("btn-new-receta").textContent).toContain(
        "+ Nueva Receta"
      );
      expect(screen.getByText("Receta & Ficha Técnica")).toBeDefined();
      expect(screen.getByText("Estructura de Insumos")).toBeDefined();
      expect(screen.getByTestId("badge-dinamica").textContent).toBe("Dinámica");

      // Switch to English dynamically
      act(() => {
        setActiveLanguage("en");
      });

      expect(screen.getByTestId("gestion-tab-recetas").textContent).toBe(
        "Recipes & Costing"
      );
      expect(screen.getByTestId("btn-new-receta").textContent).toContain(
        "+ New Recipe"
      );
      expect(screen.getByText("Recipe & Technical Sheet")).toBeDefined();
      expect(screen.getByText("Inputs Structure")).toBeDefined();
      expect(screen.getByTestId("badge-dinamica").textContent).toBe("Dynamic");
      expect(
        screen.getByTestId("btn-toggle-expand-rec-1").textContent
      ).toContain("View inputs breakdown");

      // Expand mobile card in English
      fireEvent.click(screen.getByTestId("btn-toggle-expand-rec-1"));
      expect(
        screen.getByTestId("btn-toggle-expand-rec-1").textContent
      ).toContain("Hide breakdown");
    });

    it("switches CombosToolbar, CombosTable, and ComboMobileCard dynamically between es and en", () => {
      renderWithProviders(
        <div>
          <CombosToolbar
            searchQuery=""
            onSearchChange={vi.fn()}
            selectedCategoriaId={null}
            onSelectCategoria={vi.fn()}
            categorias={INITIAL_CATEGORIAS_COMBOS_MOCK}
            onNewCombo={vi.fn()}
            onManageCategorias={vi.fn()}
          />
          <CombosTable combos={INITIAL_COMBOS_MOCK} onEdit={vi.fn()} />
          <ComboMobileCard combo={INITIAL_COMBOS_MOCK[0]!} onEdit={vi.fn()} />
        </div>
      );

      // Spanish assertions
      expect(screen.getByTestId("btn-new-combo").textContent).toContain(
        "+ Nuevo Combo"
      );
      expect(screen.getByText("Disponibilidad Stock")).toBeDefined();
      expect(screen.getByTestId("badge-combo-dinamico").textContent).toBe(
        "Dinámico"
      );

      // Switch to English
      act(() => {
        setActiveLanguage("en");
      });

      expect(screen.getByTestId("btn-new-combo").textContent).toContain(
        "+ New Combo"
      );
      expect(screen.getByText("Stock Availability")).toBeDefined();
      expect(screen.getByTestId("badge-combo-dinamico").textContent).toBe(
        "Dynamic"
      );
      expect(
        screen.getByTestId("btn-toggle-expand-combo-combo-1").textContent
      ).toContain("View combo components");
    });

    it("switches RecetaDialog, ComboDialog, OptionGroupSelectorModal, RecetaDetalleModal, and AllergenBadge between es and en", () => {
      act(() => {
        setActiveLanguage("en");
      });

      renderWithProviders(
        <div>
          <AllergenBadge allergen="CRUSTACEANS" />
          <RecetaDialog
            open={true}
            onClose={vi.fn()}
            receta={INITIAL_RECETAS_MOCK[0]!}
            categorias={INITIAL_CATEGORIAS_RECETAS_MOCK}
            productos={INITIAL_PRODUCTOS_MOCK}
            recetasCatalogo={INITIAL_RECETAS_MOCK}
            gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
          />
          <ComboDialog
            open={true}
            onClose={vi.fn()}
            combo={INITIAL_COMBOS_MOCK[0]!}
            categorias={INITIAL_CATEGORIAS_COMBOS_MOCK}
            productos={INITIAL_PRODUCTOS_MOCK}
            recetas={INITIAL_RECETAS_MOCK}
            gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
          />
          <OptionGroupSelectorModal
            open={true}
            onClose={vi.fn()}
            onSelectGroup={vi.fn()}
            gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
          />
          <RecetaDetalleModal
            open={true}
            onClose={vi.fn()}
            receta={{
              ...INITIAL_RECETAS_MOCK[0]!,
              alergenos: [{ code: "MILK", nombre: "Lácteos" }],
            }}
            gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
          />
        </div>
      );

      expect(screen.getByTestId("allergen-badge-crustaceans").textContent).toBe(
        "Crustaceans"
      );
      expect(screen.getByText("Edit Recipe & Costing")).toBeDefined();
      expect(screen.getByText("Live Costing")).toBeDefined();
      expect(screen.getByText("Edit Promotional Combo")).toBeDefined();
      expect(screen.getByText("Option Groups Assistant")).toBeDefined();
      expect(screen.getByText("Interactive Production Scaler")).toBeDefined();
      expect(screen.getByTestId("badge-allergens-count").textContent).toBe(
        "1 detected"
      );
    });
  });

  // ==========================================================================
  // 3. Multi-Moneda FX con Precisión Decimal (CLP, USD, EUR) y 0 Floats
  // ==========================================================================
  describe("3. Multi-Moneda FX Determinista con Precisión Decimal (CLP, USD, EUR)", () => {
    it("eliminates floating-point precision drift in calculateIngredientTotalCost and convertAmountExact", () => {
      // Classic IEEE-754 float trap: 0.1 * 0.2 = 0.020000000000000004 in JS floats
      expect(calculateIngredientTotalCost(0.1, 0, 200)).toBe(20);
      // 0.35 kg with 20% merma at $9.600/kg: 0.35 / 0.8 * 9600 = 4200.00 exact
      expect(calculateIngredientTotalCost(0.35, 20, 9600)).toBe(4200);

      // Exact conversion CLP -> USD (rate 960 CLP/USD) & CLP -> EUR (rate 1040 CLP/EUR)
      expect(convertAmountExact("9600", "CLP", "USD")).toBe("10.00");
      expect(convertAmountExact("10400", "CLP", "EUR")).toBe("10.00");

      // formatMoney helper with multi-currency support
      expect(formatMoney(9600, "CLP")).toBe("$9.600");
      expect(formatMoney(9600, "USD", "CLP")).toBe("US$10.00");
      expect(formatMoney(10400, "EUR", "CLP")).toBe("€10,00");
      expect(formatCurrencyAmount("1.2500", "UF")).toBe("UF 1,2500");
    });

    it("formats recipe escandallo costs, option surcharges, and combo prices in USD and EUR without float drift", () => {
      const sampleReceta = {
        ...INITIAL_RECETAS_MOCK[0]!,
        costo_total: 9600,
        costo_total_calculado: 9600,
        costo_porcion: 9600,
        precio_venta_bruto: 19200,
        precio_venta_neto: 14400,
      };

      const { unmount } = renderWithProviders(
        <div>
          <MoneyBadge amount={9600} baseCurrency="CLP" />
          <RecetasTable recetas={[sampleReceta]} />
          <ComboDialog
            open={true}
            onClose={vi.fn()}
            combo={{
              ...INITIAL_COMBOS_MOCK[0]!,
              precio_venta_bruto: 19200,
              precio_venta_neto: 14400,
              items_fijos: [
                {
                  id: "cf-fx-1",
                  receta_id: "rec-1",
                  nombre: "Lomo Vetado",
                  target_type: "receta",
                  cantidad: 1,
                  costo_unitario: 9600,
                  costo_total: 9600,
                },
              ],
              grupos_opciones: [],
            }}
          />
        </div>,
        "USD"
      );

      // In USD (rate = 960 CLP/USD): 9600 CLP -> US$10.00, 19200 CLP -> US$20.00
      expect(screen.getByTestId("money-badge-amount").textContent).toBe(
        "US$10.00"
      );
      expect(screen.getByTestId("receta-row-rec-1").textContent).toContain(
        "US$10.00"
      );
      expect(screen.getByTestId("receta-row-rec-1").textContent).toContain(
        "US$20.00"
      );
      expect(
        screen.getByTestId("combo-summary-base-cost").textContent
      ).toBe("US$10.00");
      expect(
        screen.getByTestId("combo-summary-combo-price").textContent
      ).toBe("US$20.00");

      unmount();

      // Render in EUR (rate = 1040 CLP/EUR): 10400 CLP -> €10,00
      const eurReceta = {
        ...sampleReceta,
        costo_total: 10400,
        costo_total_calculado: 10400,
        costo_porcion: 10400,
        precio_venta_bruto: 20800,
        precio_venta_neto: 15600,
      };

      renderWithProviders(
        <div>
          <MoneyBadge amount={10400} baseCurrency="CLP" />
          <RecetasTable recetas={[eurReceta]} />
        </div>,
        "EUR"
      );

      expect(screen.getByTestId("money-badge-amount").textContent).toBe(
        "€10,00"
      );
      expect(screen.getByTestId("receta-row-rec-1").textContent).toContain(
        "€10,00"
      );
      expect(screen.getByTestId("receta-row-rec-1").textContent).toContain(
        "€20,00"
      );
    });
  });
});
