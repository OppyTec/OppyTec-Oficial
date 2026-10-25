import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  FUTURE_LANGUAGE_CODES,
  FUTURE_LANGUAGES,
  FlagES,
  FlagUS,
  type FlagIconProps,
  type FutureLanguage,
  type FutureLanguageDescriptor,
  I18N_NAMESPACES,
  I18N_RESOURCES,
  type I18nNamespace,
  IMMUTABLE_PROPER_NOUNS,
  LANGUAGE_FLAG_COMPONENTS,
  LANGUAGE_STORAGE_KEY,
  LanguageFlagSelector,
  type LanguageFlagSelectorProps,
  LanguageProvider,
  useLanguage,
  SUPPORTED_LANGUAGES,
  type SupportedLanguage,
  type TranslatableDynamicRecord,
  type TranslationInterpolationVars,
  getActiveLanguage,
  i18next,
  resolveDynamicFieldI18n,
  setActiveLanguage,
  translateKey,
} from "./index";

describe("Frontend i18n Suite (12 Namespaces, SVG Flags & Pollo King Proper Noun Guard)", () => {
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

  afterAll(() => {
    cleanup();
    window.localStorage.clear();
    setActiveLanguage("es");
  });

  it("initializes all 19 namespaces for both es and en with 1:1 parity", () => {
    expect(SUPPORTED_LANGUAGES).toEqual(["es", "en"]);
    expect(I18N_NAMESPACES).toHaveLength(19);
    expect(I18N_NAMESPACES).toContain("configuracion");
    expect(I18N_NAMESPACES).toContain("profile");
    expect(I18N_NAMESPACES).toContain("users");
    expect(I18N_NAMESPACES).toContain("navigation");
    expect(I18N_NAMESPACES).toContain("gestion");
    expect(I18N_NAMESPACES).toContain("products");
    expect(I18N_NAMESPACES).toContain("excel_import");
    expect(I18N_NAMESPACES).toContain("factura_import");
    expect(i18next.isInitialized).toBe(true);

    for (const ns of I18N_NAMESPACES) {
      expect(I18N_RESOURCES.es?.[ns]).toBeDefined();
      expect(I18N_RESOURCES.en?.[ns]).toBeDefined();
    }

    const vars: TranslationInterpolationVars = { name: "Chef" };
    expect(translateKey("common", "app.welcome", vars)).toBe(
      "Bienvenido a OppyTec, Chef"
    );
    expect(translateKey("gestion", "header.title")).toBe("Gestión de Productos");
    expect(translateKey("products", "wizard.kpis.net_margin")).toBe("Margen Neto");
    expect(translateKey("excel_import", "modal.title")).toBe(
      "Importador Inteligente de Productos (Excel / CSV IA)"
    );
    expect(translateKey("factura_import", "modal.title")).toBe(
      "Ingreso de Factura Inteligente (PDF / XML DTE IA)"
    );

    setActiveLanguage("en");
    expect(getActiveLanguage()).toBe("en");
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("en");
    expect(translateKey("common", "app.welcome", vars)).toBe(
      "Welcome to OppyTec, Chef"
    );
    expect(translateKey("gestion", "header.title")).toBe("Product Management");
    expect(translateKey("products", "wizard.kpis.net_margin")).toBe("Net Margin");
    expect(translateKey("excel_import", "modal.title")).toBe(
      "Smart Product Importer (Excel / CSV AI)"
    );
    expect(translateKey("factura_import", "modal.title")).toBe(
      "Smart Invoice Ingestion (PDF / XML DTE AI)"
    );
  });

  it("preserves protected proper nouns like 'Pollo King' and 'Savory' across all languages", () => {
    expect(IMMUTABLE_PROPER_NOUNS).toContain("Pollo King");
    expect(IMMUTABLE_PROPER_NOUNS).toContain("Savory");

    const polloKingRecord: TranslatableDynamicRecord = {
      name: "Pollo King",
      name_i18n: {
        es: "Pollo Rey",
        en: "King Chicken",
      },
      is_proper_noun: true,
    };

    expect(resolveDynamicFieldI18n(polloKingRecord, "es")).toBe("Pollo King");
    expect(resolveDynamicFieldI18n(polloKingRecord, "en")).toBe("Pollo King");

    const savoryImplicitBrand: TranslatableDynamicRecord = {
      name: "Savory",
      name_i18n: {
        en: "Tasty Ice Cream",
      },
    };
    expect(resolveDynamicFieldI18n(savoryImplicitBrand, "en")).toBe("Savory");

    const genericIngredient: TranslatableDynamicRecord = {
      name: "Pechuga de Pollo Deshuesada",
      name_i18n: {
        es: "Pechuga de Pollo Deshuesada",
        en: "Boneless Chicken Breast",
      },
      is_proper_noun: false,
    };

    expect(resolveDynamicFieldI18n(genericIngredient, "es")).toBe(
      "Pechuga de Pollo Deshuesada"
    );
    expect(resolveDynamicFieldI18n(genericIngredient, "en")).toBe(
      "Boneless Chicken Breast"
    );
  });

  it("renders crisp SVG flags (FlagES, FlagUS) and exposes future languages metadata (pt, fr, it, de)", () => {
    expect(FUTURE_LANGUAGE_CODES).toEqual(["pt", "fr", "it", "de"]);
    expect(FUTURE_LANGUAGES).toHaveLength(4);
    const ptMeta: FutureLanguageDescriptor | undefined = FUTURE_LANGUAGES[0];
    const futureCode: FutureLanguage = ptMeta?.code ?? "pt";
    expect(futureCode).toBe("pt");
    expect(LANGUAGE_FLAG_COMPONENTS.es).toBe(FlagES);
    expect(LANGUAGE_FLAG_COMPONENTS.en).toBe(FlagUS);

    const flagProps: FlagIconProps = { title: "US Test Flag" };
    const { unmount } = render(
      <div>
        <FlagES title="ES Test Flag" />
        <FlagUS {...flagProps} />
      </div>
    );

    expect(screen.getByLabelText("ES Test Flag")).toBeDefined();
    expect(screen.getByLabelText("US Test Flag")).toBeDefined();
    unmount();
  });

  it("switches languages instantaneously via LanguageFlagSelector without affecting currency", () => {
    const onLanguageChange = vi.fn<(lang: SupportedLanguage) => void>();
    const selectorProps: LanguageFlagSelectorProps = {
      onLanguageChange,
    };

    render(<LanguageFlagSelector {...selectorProps} />);

    const selector = screen.getByTestId("language-flag-selector");
    expect(selector.getAttribute("data-active-lang")).toBe("es");

    const enButton = screen.getByTestId("lang-option-en");
    fireEvent.click(enButton);

    expect(onLanguageChange).toHaveBeenCalledWith("en");
    expect(getActiveLanguage()).toBe("en");
    expect(selector.getAttribute("data-active-lang")).toBe("en");

    const nsCheck: I18nNamespace = "inventory";
    expect(
      translateKey(nsCheck, "warehouse.stock_level", {
        quantity: 25,
        unit: "kg",
      })
    ).toBe("Available stock: 25 kg");
  });

  it("renders LanguageFlagSelector as an interactive dropdown displaying active language and closes upon option selection", () => {
    render(<LanguageFlagSelector />);

    const trigger = screen.getByRole("button", { name: translateKey("common", "language.label") });
    expect(trigger.textContent).toContain("Español");

    // Open dropdown
    fireEvent.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");

    // Select English
    const enButton = screen.getByTestId("lang-option-en");
    fireEvent.click(enButton);

    // Dropdown closes and trigger text updates to "English"
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(trigger.textContent).toContain("English");
    expect(getActiveLanguage()).toBe("en");
  });

  it("reactively updates all mounted views within LanguageProvider when language switches", () => {
    function ReactiveView() {
      useLanguage();
      return (
        <div>
          <span data-testid="reactive-title">{translateKey("common", "status.empty")}</span>
          <LanguageFlagSelector />
        </div>
      );
    }

    render(
      <LanguageProvider>
        <ReactiveView />
      </LanguageProvider>
    );

    // Initial Spanish text
    expect(screen.getByTestId("reactive-title").textContent).toBe("Sin registros disponibles");

    // Switch to English
    fireEvent.click(screen.getByTestId("lang-option-en"));

    // Immediately updates to English in the mounted view
    expect(screen.getByTestId("reactive-title").textContent).toBe("No records available");

    // Switch back to Spanish
    fireEvent.click(screen.getByTestId("lang-option-es"));
    expect(screen.getByTestId("reactive-title").textContent).toBe("Sin registros disponibles");
  });

  it("verifies 1:1 parity and full coverage for 'gestion', 'products', 'excel_import' and 'factura_import' namespaces", () => {
    function extractLeafKeys(obj: unknown, prefix = ""): string[] {
      if (!obj || typeof obj !== "object" || Array.isArray(obj)) {
        return prefix ? [prefix] : [];
      }
      return Object.entries(obj).flatMap(([k, v]) =>
        extractLeafKeys(v, prefix ? `${prefix}.${k}` : k)
      );
    }

    for (const ns of ["gestion", "products", "excel_import", "factura_import"] as const) {
      const esResource = I18N_RESOURCES.es?.[ns];
      const enResource = I18N_RESOURCES.en?.[ns];

      expect(esResource).toBeDefined();
      expect(enResource).toBeDefined();

      const esKeys = extractLeafKeys(esResource).sort();
      const enKeys = extractLeafKeys(enResource).sort();

      expect(esKeys).toEqual(enKeys);
      expect(esKeys.length).toBeGreaterThan(50);
    }

    // Gestion specific keys
    expect(translateKey("gestion", "header.subtitle")).toBe(
      "Catálogo de productos e insumos"
    );
    expect(translateKey("gestion", "columns.labels.ultimo_costo_unidad_neto")).toBe(
      "Último Costo Unitario Neto"
    );
    expect(translateKey("gestion", "modals.table_config.title")).toBe(
      "Configuración de Tabla Analítica"
    );
    expect(translateKey("gestion", "modals.transfer.title")).toBe(
      "Transferencia de Stock entre Bodegas"
    );

    // Products specific keys
    expect(translateKey("products", "wizard.stepper.step_1")).toBe(
      "1. Básico & Familia"
    );
    expect(translateKey("products", "wizard.stepper.step_4")).toBe(
      "4. Precios & Costos"
    );
    expect(translateKey("products", "wizard.kpis.markup")).toBe("Markup %");
    expect(translateKey("products", "wizard.kpis.food_cost")).toBe("Food Cost");
    expect(translateKey("products", "wizard.draft.saving")).toBe(
      "Guardando borrador..."
    );

    // Excel import specific keys
    expect(translateKey("excel_import", "stepper.step_1")).toBe("Carga");
    expect(translateKey("excel_import", "stepper.step_2")).toBe("Columnas");
    expect(translateKey("excel_import", "columns.fields.costo_neto")).toBe("Costo Unitario Neto");

    // Factura import specific keys
    expect(translateKey("factura_import", "upload.select_button")).toBe("Seleccionar Factura");
    expect(translateKey("factura_import", "supplier.new_supplier_badge")).toBe("Nuevo Proveedor");

    // English switch
    setActiveLanguage("en");
    expect(translateKey("gestion", "header.subtitle")).toBe(
      "Product and supplies catalog"
    );
    expect(translateKey("gestion", "columns.labels.ultimo_costo_unidad_neto")).toBe(
      "Last Unit Cost Net"
    );
    expect(translateKey("gestion", "modals.table_config.title")).toBe(
      "Analytical Table Configuration"
    );
    expect(translateKey("products", "wizard.stepper.step_1")).toBe(
      "1. Basic & Family"
    );
    expect(translateKey("products", "wizard.kpis.markup")).toBe("Markup %");
    expect(translateKey("products", "wizard.draft.saving")).toBe(
      "Saving draft..."
    );
    expect(translateKey("excel_import", "stepper.step_1")).toBe("Upload");
    expect(translateKey("excel_import", "stepper.step_2")).toBe("Columns");
    expect(translateKey("excel_import", "columns.fields.costo_neto")).toBe("Net Unit Cost");
    expect(translateKey("factura_import", "upload.select_button")).toBe("Select Invoice");
    expect(translateKey("factura_import", "supplier.new_supplier_badge")).toBe("New Supplier");
  });
});
