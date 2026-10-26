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

  it("initializes all 22 namespaces for both es and en with 1:1 parity", () => {
    expect(SUPPORTED_LANGUAGES).toEqual(["es", "en"]);
    expect(I18N_NAMESPACES).toHaveLength(22);
    expect(I18N_NAMESPACES).toContain("configuracion");
    expect(I18N_NAMESPACES).toContain("profile");
    expect(I18N_NAMESPACES).toContain("users");
    expect(I18N_NAMESPACES).toContain("navigation");
    expect(I18N_NAMESPACES).toContain("gestion");
    expect(I18N_NAMESPACES).toContain("products");
    expect(I18N_NAMESPACES).toContain("excel_import");
    expect(I18N_NAMESPACES).toContain("factura_import");
    expect(I18N_NAMESPACES).toContain("alerts");
    expect(I18N_NAMESPACES).toContain("history");
    expect(I18N_NAMESPACES).toContain("notifications");
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
    expect(translateKey("alerts", "title")).toBe("Alertas");
    expect(translateKey("alerts", "subtitle")).toBe(
      "Estado de Stock y Vencimientos del Sistema"
    );
    expect(translateKey("history", "header.title")).toBe("Historial");
    expect(translateKey("history", "header.subtitle")).toBe(
      "Auditoría y Trazabilidad de Inventario"
    );
    expect(translateKey("notifications", "header.title")).toBe(
      "Centro de Notificaciones y Aprobaciones"
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
    expect(translateKey("alerts", "title")).toBe("Alerts");
    expect(translateKey("alerts", "subtitle")).toBe(
      "System Stock Status and Expirations"
    );
    expect(translateKey("history", "header.title")).toBe("History");
    expect(translateKey("history", "header.subtitle")).toBe(
      "Inventory Audit and Traceability"
    );
    expect(translateKey("notifications", "header.title")).toBe(
      "Notifications & Approvals Center"
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

    // Alerts specific keys
    expect(translateKey("alerts", "toolbar.filter_stock")).toBe("Stock Crítico");
    expect(translateKey("alerts", "status.depleted")).toBe("Agotado");
    expect(translateKey("alerts", "table.col_health")).toBe("Estado / Salud");

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

    // Alerts specific keys (en)
    expect(translateKey("alerts", "toolbar.filter_stock")).toBe("Critical Stock");
    expect(translateKey("alerts", "status.depleted")).toBe("Out of Stock");
    expect(translateKey("alerts", "table.col_health")).toBe("Status / Health");
  });

  it("verifies 1:1 parity and full canonical coverage for 'operations' namespace (Consumo, Manos Libres, Buffet & Modals)", () => {
    function extractLeafKeys(obj: unknown, prefix = ""): string[] {
      if (!obj || typeof obj !== "object" || Array.isArray(obj)) {
        return prefix ? [prefix] : [];
      }
      return Object.entries(obj).flatMap(([k, v]) =>
        extractLeafKeys(v, prefix ? `${prefix}.${k}` : k)
      );
    }

    const esOperations = I18N_RESOURCES.es?.operations;
    const enOperations = I18N_RESOURCES.en?.operations;

    expect(esOperations).toBeDefined();
    expect(enOperations).toBeDefined();

    const esKeys = extractLeafKeys(esOperations).sort();
    const enKeys = extractLeafKeys(enOperations).sort();

    // 1:1 parity check across all nested keys
    expect(esKeys).toEqual(enKeys);
    expect(esKeys.length).toBeGreaterThan(70);

    // 1. Registro de Consumo & Paginación (es)
    setActiveLanguage("es");
    expect(translateKey("operations", "consumption.registro.title")).toBe("Registro de Consumo");
    expect(translateKey("operations", "consumption.registro.subtitle")).toBe(
      "Registra salidas de productos, consumo de personal y mermas en tiempo real"
    );
    expect(translateKey("operations", "consumption.registro.modes.productos")).toBe("Productos");
    expect(translateKey("operations", "consumption.registro.modes.recetas")).toBe("Recetas");
    expect(translateKey("operations", "consumption.registro.modes.combos")).toBe("Combos");
    expect(translateKey("operations", "consumption.registro.toolbar.categories")).toBe("Categorías");
    expect(translateKey("operations", "consumption.registro.toolbar.merma")).toBe("Merma");
    expect(translateKey("operations", "consumption.registro.toolbar.templates")).toBe("Plantillas");
    expect(translateKey("operations", "consumption.registro.toolbar.history")).toBe("Historial");
    expect(
      translateKey("operations", "consumption.pagination.showing", { from: 1, to: 24 })
    ).toBe("Mostrando 1 - 24");
    expect(translateKey("operations", "consumption.pagination.of")).toBe("de");
    expect(
      translateKey("operations", "consumption.pagination.per_page", { count: 24 })
    ).toBe("24 por página");

    // 2. Manos Libres (es)
    expect(translateKey("operations", "consumption.manos_libres.title")).toBe("Consumo Manos Libres");
    expect(translateKey("operations", "consumption.manos_libres.subtitle")).toBe(
      "Registro operativo por voz para cocina, barra y preparación"
    );
    expect(translateKey("operations", "consumption.manos_libres.listening.listening_badge")).toBe("Escuchando...");
    expect(translateKey("operations", "consumption.manos_libres.listening.muted_badge")).toBe("Silenciado");
    expect(translateKey("operations", "consumption.manos_libres.tts.label")).toBe("Síntesis de Voz (TTS)");
    expect(translateKey("operations", "consumption.manos_libres.console.title")).toBe(
      "Consola de Transcripción & Entrada Manual"
    );
    expect(translateKey("operations", "consumption.manos_libres.orders.title")).toBe("Feed de Órdenes Verbales");
    expect(translateKey("operations", "consumption.manos_libres.orders.confirm")).toBe("Confirmar");
    expect(translateKey("operations", "consumption.manos_libres.orders.reject")).toBe("Descartar");

    // 3. Buffet Inteligente (es)
    expect(translateKey("operations", "consumption.buffet.title")).toBe("Buffet Inteligente");
    expect(translateKey("operations", "consumption.buffet.stages.apertura")).toBe("Apertura");
    expect(translateKey("operations", "consumption.buffet.stages.reposicion")).toBe("Reposición");
    expect(translateKey("operations", "consumption.buffet.stages.cierre")).toBe("Cierre");
    expect(translateKey("operations", "consumption.buffet.scanner.title")).toBe("Escáner de Bandejas Gastronorm");
    expect(translateKey("operations", "consumption.buffet.metrics.costo_pax")).toBe("Costo Neto por Pax");
    expect(translateKey("operations", "consumption.buffet.conciliation.finalize_btn")).toBe(
      "Finalizar y Liquidar Buffet"
    );

    // 4. Modales (es)
    expect(translateKey("operations", "consumption.modals.cart.title")).toBe("Carrito de Consumo");
    expect(translateKey("operations", "consumption.modals.cart.submit_btn")).toBe("Registrar Consumo");
    expect(translateKey("operations", "consumption.modals.templates.title")).toBe(
      "Plantillas de Catálogo de Consumo"
    );
    expect(translateKey("operations", "consumption.modals.contingency.title")).toBe(
      "Alerta de Contingencia de Stock"
    );
    expect(translateKey("operations", "consumption.modals.locate_stock.title")).toBe(
      "Localizador de Stock entre Bodegas"
    );
    expect(translateKey("operations", "consumption.modals.log.title")).toBe(
      "Historial de Consumo y Mermas"
    );
    expect(translateKey("operations", "consumption.modals.edit.title")).toBe(
      "Editar Registro de Consumo"
    );

    // 5. English switch (en)
    setActiveLanguage("en");
    expect(getActiveLanguage()).toBe("en");

    // Registro de Consumo & Paginación (en)
    expect(translateKey("operations", "consumption.registro.title")).toBe("Consumption Register");
    expect(translateKey("operations", "consumption.registro.subtitle")).toBe(
      "Log product outputs, staff meals and waste in real time"
    );
    expect(translateKey("operations", "consumption.registro.modes.productos")).toBe("Products");
    expect(translateKey("operations", "consumption.registro.modes.recetas")).toBe("Recipes");
    expect(translateKey("operations", "consumption.registro.modes.combos")).toBe("Combos");
    expect(translateKey("operations", "consumption.registro.toolbar.categories")).toBe("Categories");
    expect(translateKey("operations", "consumption.registro.toolbar.merma")).toBe("Waste");
    expect(translateKey("operations", "consumption.registro.toolbar.templates")).toBe("Templates");
    expect(translateKey("operations", "consumption.registro.toolbar.history")).toBe("History");
    expect(
      translateKey("operations", "consumption.pagination.showing", { from: 1, to: 24 })
    ).toBe("Showing 1 - 24");
    expect(translateKey("operations", "consumption.pagination.of")).toBe("of");
    expect(
      translateKey("operations", "consumption.pagination.per_page", { count: 24 })
    ).toBe("24 per page");

    // Manos Libres (en)
    expect(translateKey("operations", "consumption.manos_libres.title")).toBe("Hands-Free Consumption");
    expect(translateKey("operations", "consumption.manos_libres.subtitle")).toBe(
      "Voice operational logging for kitchen, bar and prep"
    );
    expect(translateKey("operations", "consumption.manos_libres.listening.listening_badge")).toBe("Listening...");
    expect(translateKey("operations", "consumption.manos_libres.listening.muted_badge")).toBe("Muted");
    expect(translateKey("operations", "consumption.manos_libres.tts.label")).toBe("Text-to-Speech (TTS)");
    expect(translateKey("operations", "consumption.manos_libres.console.title")).toBe(
      "Transcription Console & Manual Input"
    );
    expect(translateKey("operations", "consumption.manos_libres.orders.title")).toBe("Voice Orders Feed");
    expect(translateKey("operations", "consumption.manos_libres.orders.confirm")).toBe("Confirm");
    expect(translateKey("operations", "consumption.manos_libres.orders.reject")).toBe("Discard");

    // Buffet Inteligente (en)
    expect(translateKey("operations", "consumption.buffet.title")).toBe("Smart Buffet");
    expect(translateKey("operations", "consumption.buffet.stages.apertura")).toBe("Opening");
    expect(translateKey("operations", "consumption.buffet.stages.reposicion")).toBe("Replenishment");
    expect(translateKey("operations", "consumption.buffet.stages.cierre")).toBe("Closing");
    expect(translateKey("operations", "consumption.buffet.scanner.title")).toBe("Gastronorm Tray Scanner");
    expect(translateKey("operations", "consumption.buffet.metrics.costo_pax")).toBe("Net Cost per Pax");
    expect(translateKey("operations", "consumption.buffet.conciliation.finalize_btn")).toBe(
      "Finalize and Settle Buffet"
    );

    // Modales (en)
    expect(translateKey("operations", "consumption.modals.cart.title")).toBe("Consumption Cart");
    expect(translateKey("operations", "consumption.modals.cart.submit_btn")).toBe("Register Consumption");
    expect(translateKey("operations", "consumption.modals.templates.title")).toBe(
      "Consumption Catalog Templates"
    );
    expect(translateKey("operations", "consumption.modals.contingency.title")).toBe(
      "Stock Contingency Alert"
    );
    expect(translateKey("operations", "consumption.modals.locate_stock.title")).toBe(
      "Inter-Warehouse Stock Locator"
    );
    expect(translateKey("operations", "consumption.modals.log.title")).toBe(
      "Consumption & Waste History"
    );
    expect(translateKey("operations", "consumption.modals.edit.title")).toBe(
      "Edit Consumption Record"
    );
  });

  it("verifies 1:1 parity and full canonical coverage for 'notifications' namespace", () => {
    setActiveLanguage("es");

    // Header & Views (es)
    expect(translateKey("notifications", "header.title")).toBe(
      "Centro de Notificaciones y Aprobaciones"
    );
    expect(translateKey("notifications", "header.subtitle")).toBe(
      "Gobernanza operativa, control jerárquico de mermas, conteos y auditorías"
    );
    expect(translateKey("notifications", "views.bandeja")).toBe("Bandeja");
    expect(translateKey("notifications", "views.historial")).toBe("Historial");
    expect(translateKey("notifications", "views.configuracion")).toBe("Configuración");

    // Categories (es)
    expect(translateKey("notifications", "categories.all")).toBe("Todas");
    expect(translateKey("notifications", "categories.operaciones")).toBe("Operaciones");
    expect(translateKey("notifications", "categories.inventario")).toBe("Inventario");
    expect(translateKey("notifications", "categories.compras")).toBe("Compras");
    expect(translateKey("notifications", "categories.equipo")).toBe("Equipo");

    // Types & States (es)
    expect(translateKey("notifications", "types.merma")).toBe("Merma");
    expect(translateKey("notifications", "types.consumo_buffet")).toBe("Buffet");
    expect(translateKey("notifications", "types.conteo")).toBe("Conteo Físico");
    expect(translateKey("notifications", "states.pendiente")).toBe("Pendiente");
    expect(translateKey("notifications", "states.aprobado")).toBe("Aprobado");
    expect(translateKey("notifications", "states.rechazado")).toBe("Rechazado");

    // Modals (es)
    expect(translateKey("notifications", "modals.reject.title")).toBe(
      "Rechazar Solicitud Operativa"
    );
    expect(translateKey("notifications", "modals.reject.confirm")).toBe(
      "Confirmar Rechazo"
    );
    expect(translateKey("notifications", "modals.conteo.exact_stock")).toBe("Exacto");
    expect(translateKey("notifications", "modals.buffet.tabs.balance")).toBe(
      "Balance Consolidado"
    );
    expect(translateKey("notifications", "modals.buffet.tabs.split_view")).toBe(
      "Auditoría Split-View"
    );

    // Governance (es)
    expect(translateKey("notifications", "governance.title")).toBe(
      "Matriz de Notificaciones y Gobernanza"
    );
    expect(translateKey("notifications", "governance.tabs.my_notifications")).toBe(
      "Mis Notificaciones"
    );
    expect(translateKey("notifications", "governance.tabs.role_governance")).toBe(
      "Gobernanza de Cargos"
    );

    // Switch to English and verify parity
    setActiveLanguage("en");

    // Header & Views (en)
    expect(translateKey("notifications", "header.title")).toBe(
      "Notifications & Approvals Center"
    );
    expect(translateKey("notifications", "header.subtitle")).toBe(
      "Operational governance, hierarchical waste control, physical counts & audits"
    );
    expect(translateKey("notifications", "views.bandeja")).toBe("Inbox");
    expect(translateKey("notifications", "views.historial")).toBe("History");
    expect(translateKey("notifications", "views.configuracion")).toBe("Configuration");

    // Categories (en)
    expect(translateKey("notifications", "categories.all")).toBe("All");
    expect(translateKey("notifications", "categories.operaciones")).toBe("Operations");
    expect(translateKey("notifications", "categories.inventario")).toBe("Inventory");
    expect(translateKey("notifications", "categories.compras")).toBe("Purchasing");
    expect(translateKey("notifications", "categories.equipo")).toBe("Team");

    // Types & States (en)
    expect(translateKey("notifications", "types.merma")).toBe("Waste");
    expect(translateKey("notifications", "types.consumo_buffet")).toBe("Buffet");
    expect(translateKey("notifications", "types.conteo")).toBe("Physical Count");
    expect(translateKey("notifications", "states.pendiente")).toBe("Pending");
    expect(translateKey("notifications", "states.aprobado")).toBe("Approved");
    expect(translateKey("notifications", "states.rechazado")).toBe("Rejected");

    // Modals (en)
    expect(translateKey("notifications", "modals.reject.title")).toBe(
      "Reject Operational Request"
    );
    expect(translateKey("notifications", "modals.reject.confirm")).toBe(
      "Confirm Rejection"
    );
    expect(translateKey("notifications", "modals.conteo.exact_stock")).toBe("Exact");
    expect(translateKey("notifications", "modals.buffet.tabs.balance")).toBe(
      "Consolidated Balance"
    );
    expect(translateKey("notifications", "modals.buffet.tabs.split_view")).toBe(
      "Split-View Audit"
    );

    // Governance (en)
    expect(translateKey("notifications", "governance.title")).toBe(
      "Notification & Governance Matrix"
    );
    expect(translateKey("notifications", "governance.tabs.my_notifications")).toBe(
      "My Notifications"
    );
    expect(translateKey("notifications", "governance.tabs.role_governance")).toBe(
      "Role Governance"
    );

    // Symmetrical key depth check
    const esKeys = Object.keys(I18N_RESOURCES.es?.notifications || {}).sort();
    const enKeys = Object.keys(I18N_RESOURCES.en?.notifications || {}).sort();
    expect(esKeys).toEqual(enKeys);
    expect(esKeys.length).toBeGreaterThanOrEqual(10);
  });

  it("verifies 1:1 parity and full coverage for 'history' namespace", () => {
    function extractLeafKeys(obj: unknown, prefix = ""): string[] {
      if (!obj || typeof obj !== "object" || Array.isArray(obj)) {
        return prefix ? [prefix] : [];
      }
      return Object.entries(obj).flatMap(([k, v]) =>
        extractLeafKeys(v, prefix ? `${prefix}.${k}` : k)
      );
    }

    const esHistory = I18N_RESOURCES.es?.history;
    const enHistory = I18N_RESOURCES.en?.history;

    expect(esHistory).toBeDefined();
    expect(enHistory).toBeDefined();

    const esKeys = extractLeafKeys(esHistory).sort();
    const enKeys = extractLeafKeys(enHistory).sort();

    expect(esKeys).toEqual(enKeys);
    expect(esKeys.length).toBeGreaterThan(40);

    setActiveLanguage("es");
    expect(translateKey("history", "header.title")).toBe("Historial");
    expect(translateKey("history", "toolbar.badge_immutable")).toBe("Auditoría Inmutable");
    expect(translateKey("history", "filters.all_products")).toBe("Todos los productos");
    expect(translateKey("history", "table.headers.datetime")).toBe("Fecha y hora");

    setActiveLanguage("en");
    expect(translateKey("history", "header.title")).toBe("History");
    expect(translateKey("history", "toolbar.badge_immutable")).toBe("Immutable Audit");
    expect(translateKey("history", "filters.all_products")).toBe("All products");
    expect(translateKey("history", "table.headers.datetime")).toBe("Date and time");
  });
});
