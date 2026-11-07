/**
 * oppytec-frontend/src/features/platform-admin/sandbox/__tests__/SandboxI18nAndFx.test.tsx
 *
 * Test suite de Certificación Formal i18n & Multi-Moneda FX para:
 * Agente 07 (07-i18n-and-fx-currency-specialist)
 * Consola "Lab & QA Sandbox" de Platform Admin en OppyTec v2.0.
 *
 * Cobertura de Certificación:
 * 1. Paridad 1:1 Estricta de Claves (100%) entre `es/platform_admin.json` y `en/platform_admin.json`.
 * 2. Conmutación dinámica de idioma en tiempo real (es <-> en) para SandboxLayout y vistas sandbox.
 * 3. Formateo y precisión `Decimal` sin coma flotante (usando `formatMoney` de `shared/lib`) en FefoDatesSandboxView y MockDataSandboxView.
 * 4. Protección estricta de nombres propios gastronómicos ("Pollo King", "OppyTec", "JEV") según Regla 15.
 */

import "@testing-library/jest-dom";
import { cleanup, render, screen } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { formatMoney } from "@/shared/lib";
import {
  I18N_RESOURCES,
  IMMUTABLE_PROPER_NOUNS,
  resolveDynamicFieldI18n,
  setActiveLanguage,
  translateKey,
} from "@/shared/i18n";

import { SandboxLayout } from "../SandboxLayout";
import { MockDataSandboxView } from "../MockDataSandboxView";
import { PlaywrightRunnerSandboxView } from "../PlaywrightRunnerSandboxView";
import { FefoDatesSandboxView } from "../FefoDatesSandboxView";

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, layout: _l, layoutId: _li, initial: _i, animate: _a, exit: _e, transition: _t, ...props }: any) => (
      <div {...props}>{children}</div>
    ),
    button: ({ children, layout: _l, layoutId: _li, initial: _i, animate: _a, exit: _e, transition: _t, whileHover: _wh, whileTap: _wt, ...props }: any) => (
      <button {...props}>{children}</button>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

function extractLeafKeys(obj: unknown, prefix = ""): string[] {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) {
    return prefix ? [prefix] : [];
  }
  return Object.entries(obj).flatMap(([k, v]) =>
    extractLeafKeys(v, prefix ? `${prefix}.${k}` : k)
  );
}

function renderInTestHarness(
  ui: React.ReactElement,
  {
    initialRoute = "/admin/sandbox/mock-data",
    permissions = [
      "platform_admin.sandbox.access",
      "platform_admin.sandbox.manage",
    ],
  } = {}
) {
  const rbacState = {
    roleName: "SuperAdmin",
    isSuperUser: true,
    planModules: ["platform_admin"],
    rolePermissions: permissions as any,
    temporaryGrants: [],
    deniedPermissions: [],
  };

  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <PermissionsProvider initialPolicy={rbacState}>
        {ui}
      </PermissionsProvider>
    </MemoryRouter>
  );
}

describe("Agente 07 — Certificación Formal de i18n & FX para 'Lab & QA Sandbox'", () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    setActiveLanguage("es");
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
    setActiveLanguage("es");
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. PARIDAD 1:1 ESTRICTA DE CLAVES ENTRE ES Y EN
  // ==========================================================================
  describe("1. Paridad 1:1 Estricta de Claves en platform_admin.json", () => {
    it("certifica paridad 1:1 exhaustiva entre español e inglés en la sección 'sandbox'", () => {
      const esSandbox = (I18N_RESOURCES.es?.platform_admin as any)?.sandbox;
      const enSandbox = (I18N_RESOURCES.en?.platform_admin as any)?.sandbox;

      expect(esSandbox).toBeDefined();
      expect(enSandbox).toBeDefined();

      const esKeys = extractLeafKeys(esSandbox).sort();
      const enKeys = extractLeafKeys(enSandbox).sort();

      expect(esKeys).toEqual(enKeys);
      expect(esKeys.length).toBeGreaterThanOrEqual(40);

      // Verificación de subsecciones críticas
      expect(esSandbox.mock_data).toBeDefined();
      expect(enSandbox.mock_data).toBeDefined();
      expect(esSandbox.playwright).toBeDefined();
      expect(enSandbox.playwright).toBeDefined();
      expect(esSandbox.fefo).toBeDefined();
      expect(enSandbox.fefo).toBeDefined();
    });

    it("resuelve claves directamente con translateKey en ambos idiomas", () => {
      setActiveLanguage("es");
      expect(translateKey("platform_admin", "sandbox.title")).toBe("Lab & QA Sandbox");
      expect(translateKey("platform_admin", "sandbox.tabs.fefo_dates")).toBe("Simulador FEFO");

      setActiveLanguage("en");
      expect(translateKey("platform_admin", "sandbox.title")).toBe("Lab & QA Sandbox");
      expect(translateKey("platform_admin", "sandbox.tabs.fefo_dates")).toBe("FEFO Simulator");
    });

    it("certifica que todas las claves del sidebar relativas a sandbox tienen paridad y no están vacías", () => {
      const esSidebar = (I18N_RESOURCES.es?.platform_admin as any)?.sidebar;
      const enSidebar = (I18N_RESOURCES.en?.platform_admin as any)?.sidebar;

      const expectedSidebarKeys = [
        "section_sandbox",
        "menu_mock_data",
        "menu_playwright_runner",
        "menu_fefo_dates",
      ];

      for (const key of expectedSidebarKeys) {
        expect(esSidebar[key]).toBeTruthy();
        expect(enSidebar[key]).toBeTruthy();
        expect(typeof esSidebar[key]).toBe("string");
        expect(typeof enSidebar[key]).toBe("string");
      }

      expect(esSidebar.section_sandbox).toBe("Lab & QA Sandbox");
      expect(enSidebar.section_sandbox).toBe("Lab & QA Sandbox");
      expect(esSidebar.menu_mock_data).toBe("Mock Data & Presets");
      expect(enSidebar.menu_mock_data).toBe("Mock Data & Presets");
      expect(esSidebar.menu_playwright_runner).toBe("Playwright Runner");
      expect(enSidebar.menu_playwright_runner).toBe("Playwright Runner");
      expect(esSidebar.menu_fefo_dates).toBe("Simulador FEFO");
      expect(enSidebar.menu_fefo_dates).toBe("FEFO Simulator");
    });
  });

  // ==========================================================================
  // 2. CONMUTACIÓN DINÁMICA DE IDIOMA EN VISTAS SANDBOX
  // ==========================================================================
  describe("2. Conmutación Dinámica de Idioma (es <-> en)", () => {
    it("conmuta dinámicamente SandboxLayout entre español e inglés", () => {
      setActiveLanguage("es");
      const { rerender } = renderInTestHarness(
        <SandboxLayout activeTab="mock-data">
          <div>Contenido</div>
        </SandboxLayout>
      );

      expect(screen.getByText("Consola integral de pruebas de calidad, inyección sintética de datos y simulación temporal FEFO.")).toBeInTheDocument();
      expect(screen.getByText("Las mutaciones solo aplican al esquema del tenant seleccionado o modo dry-run. Esquema central protegido.")).toBeInTheDocument();

      // Cambiar a inglés
      setActiveLanguage("en");
      rerender(
        <MemoryRouter initialEntries={["/admin/sandbox/mock-data"]}>
          <SandboxLayout activeTab="mock-data">
            <div>Contenido</div>
          </SandboxLayout>
        </MemoryRouter>
      );

      expect(screen.getByText("Comprehensive console for quality testing, synthetic data seeding, and FEFO time-warp simulation.")).toBeInTheDocument();
      expect(screen.getByText("Mutations only apply to the selected tenant schema or dry-run mode. Central schema protected.")).toBeInTheDocument();
    });

    it("conmuta dinámicamente MockDataSandboxView entre español e inglés", () => {
      setActiveLanguage("es");
      const { rerender } = renderInTestHarness(<MockDataSandboxView />);

      expect(screen.getByText("Modo de Inyección de Datos")).toBeInTheDocument();
      expect(screen.getByText("Modo Demo Sintético")).toBeInTheDocument();
      expect(screen.getByText("BD Real Limpia (Esquema Tenant)")).toBeInTheDocument();
      expect(screen.getByText("Presets de Sembrado Rápido")).toBeInTheDocument();

      setActiveLanguage("en");
      rerender(
        <MemoryRouter initialEntries={["/admin/sandbox/mock-data"]}>
          <MockDataSandboxView />
        </MemoryRouter>
      );

      expect(screen.getByText("Data Injection Mode")).toBeInTheDocument();
      expect(screen.getByText("Synthetic Demo Mode")).toBeInTheDocument();
      expect(screen.getByText("Clean Real DB (Tenant Schema)")).toBeInTheDocument();
      expect(screen.getByText("Quick Seeding Presets")).toBeInTheDocument();
    });

    it("conmuta dinámicamente FefoDatesSandboxView entre español e inglés", () => {
      setActiveLanguage("es");
      const { rerender } = renderInTestHarness(<FefoDatesSandboxView />);

      expect(screen.getByText("Fecha Real del Servidor")).toBeInTheDocument();
      expect(screen.getByText("Fecha Simulada Time-Warp")).toBeInTheDocument();
      expect(screen.getByText("Selector de Escenarios y Parámetros Time-Warp")).toBeInTheDocument();
      expect(screen.getByText("Pérdida en Riesgo")).toBeInTheDocument();

      setActiveLanguage("en");
      rerender(
        <MemoryRouter initialEntries={["/admin/sandbox/fefo-dates"]}>
          <FefoDatesSandboxView />
        </MemoryRouter>
      );

      expect(screen.getByText("Real Server Date")).toBeInTheDocument();
      expect(screen.getByText("Simulated Time-Warp Date")).toBeInTheDocument();
      expect(screen.getByText("Scenario Selector and Time-Warp Parameters")).toBeInTheDocument();
      expect(screen.getByText("Loss at Risk")).toBeInTheDocument();
    });

    it("conmuta dinámicamente PlaywrightRunnerSandboxView entre español e inglés", () => {
      setActiveLanguage("es");
      const { rerender } = renderInTestHarness(<PlaywrightRunnerSandboxView />);

      expect(screen.getByText("Configuración del Ejecutor E2E")).toBeInTheDocument();
      expect(screen.getByText("Catálogo de Suites E2E")).toBeInTheDocument();
      expect(screen.getByText("Ejecutar Suite E2E")).toBeInTheDocument();

      setActiveLanguage("en");
      rerender(
        <MemoryRouter initialEntries={["/admin/sandbox/playwright-runner"]}>
          <PermissionsProvider
            initialPolicy={{
              roleName: "SuperAdmin",
              isSuperUser: true,
              planModules: ["platform_admin"],
              rolePermissions: [
                "platform_admin.sandbox.access",
                "platform_admin.sandbox.manage",
              ] as any,
              temporaryGrants: [],
              deniedPermissions: [],
            }}
          >
            <PlaywrightRunnerSandboxView />
          </PermissionsProvider>
        </MemoryRouter>
      );

      expect(screen.getByText("E2E Runner Configuration")).toBeInTheDocument();
      expect(screen.getByText("E2E Suites Catalog")).toBeInTheDocument();
      expect(screen.getByText("Run E2E Suite")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 3. PRECISIÓN DECIMAL Y FORMATEO FX SIN COMA FLOTANTE
  // ==========================================================================
  describe("3. Precisión Decimal y Formateo FX sin Coma Flotante", () => {
    it("formatea con precisión Decimal los importes de riesgo en FefoDatesSandboxView", () => {
      renderInTestHarness(<FefoDatesSandboxView />);

      // Total riesgo simulado default: 481850 CLP -> "$481.850"
      const kpiRisk = screen.getByTestId("kpi-fefo-risk-amount");
      expect(kpiRisk.textContent).toBe(formatMoney(481850, "CLP"));
      expect(kpiRisk.textContent).toBe("$481.850");

      // Primer lote de la tabla: 268250 CLP -> "$268.250"
      expect(screen.getByText(formatMoney(268250, "CLP"))).toBeInTheDocument();
    });

    it("formatea con precisión Decimal el volumen transaccional en MockDataSandboxView", () => {
      renderInTestHarness(<MockDataSandboxView />);

      // Preset inicial 'preset-full-restaurant': 2450000 CLP -> "$2.450.000"
      const kpiVol = screen.getByTestId("kpi-record-financial-volume");
      expect(kpiVol.textContent).toBe(formatMoney(2450000, "CLP"));
      expect(kpiVol.textContent).toBe("$2.450.000");
    });

    it("certifica que formatMoney maneja importes en CLP, USD y EUR sin imprecisión IEEE-754", () => {
      // Cálculo con centavos propensos a pérdida por coma flotante en IEEE-754 (0.1 + 0.2)
      const preciseAmount = "1250.75";
      expect(formatMoney(preciseAmount, "USD", "USD")).toBe("US$1,250.75");
      expect(formatMoney("950000", "CLP", "CLP")).toBe("$950.000");
      expect(formatMoney("1850.50", "EUR", "EUR")).toBe("€1.850,50");
    });
  });

  // ==========================================================================
  // 4. PROTECCIÓN ESTRICTA DE NOMBRES PROPIOS (INVARIANTE 'POLLO KING')
  // ==========================================================================
  describe("4. Protección Estricta de Nombres Propios ('Pollo King' Invariant)", () => {
    it("certifica que 'Pollo King' se encuentra en la lista canónica IMMUTABLE_PROPER_NOUNS", () => {
      expect(IMMUTABLE_PROPER_NOUNS).toContain("Pollo King");
      expect(IMMUTABLE_PROPER_NOUNS).toContain("OppyTec");
      expect(IMMUTABLE_PROPER_NOUNS).toContain("JEV");
    });

    it("resuelve nombres propios sin traducirlos al conmutar idiomas con resolveDynamicFieldI18n", () => {
      const properNounRecord = {
        id: "holding-01",
        name: "Pollo King",
        name_i18n: {
          es: "Pollo King",
          en: "Chicken King", // Intento espurio de traducción en JSONB
        },
      };

      // Debe retornar siempre "Pollo King" independientemente del idioma activo
      setActiveLanguage("es");
      expect(resolveDynamicFieldI18n(properNounRecord, "es")).toBe("Pollo King");

      setActiveLanguage("en");
      expect(resolveDynamicFieldI18n(properNounRecord, "en")).toBe("Pollo King");
    });
  });

  // ==========================================================================
  // 5. SUB-PLAN 2: CERTIFICACIÓN SWITCH MAESTRO, PRESETS GASTRONÓMICOS & FACTORY RESET
  // ==========================================================================
  describe("5. Sub-Plan 2: Switch Maestro, Presets Gastronómicos & Factory Reset", () => {
    it("certifica paridad 1:1 exhaustiva de títulos, subtítulos, descripciones y badges de los 4 presets canónicos", () => {
      const presetKeys = [
        "fast_food_title",
        "fast_food_subtitle",
        "fast_food_desc",
        "fast_food_badge",
        "steakhouse_title",
        "steakhouse_subtitle",
        "steakhouse_desc",
        "steakhouse_badge",
        "buffet_title",
        "buffet_subtitle",
        "buffet_desc",
        "buffet_badge",
        "clean_slate_title",
        "clean_slate_subtitle",
        "clean_slate_desc",
        "clean_slate_badge",
      ];

      const esPresets = (I18N_RESOURCES.es?.platform_admin as any)?.sandbox?.mock_data?.presets;
      const enPresets = (I18N_RESOURCES.en?.platform_admin as any)?.sandbox?.mock_data?.presets;

      expect(esPresets).toBeDefined();
      expect(enPresets).toBeDefined();

      for (const k of presetKeys) {
        expect(esPresets[k]).toBeDefined();
        expect(enPresets[k]).toBeDefined();
        expect(typeof esPresets[k]).toBe("string");
        expect(typeof enPresets[k]).toBe("string");
        expect(esPresets[k].length).toBeGreaterThan(0);
        expect(enPresets[k].length).toBeGreaterThan(0);
      }

      // Verificación de textos específicos en español
      expect(esPresets.fast_food_title).toBe("Fast Food & Pollo King");
      expect(esPresets.fast_food_badge).toBe("ALTA ROTACIÓN");
      expect(esPresets.steakhouse_title).toBe("Carnes Angus & Cava");
      expect(esPresets.steakhouse_badge).toBe("ALTA GAMA");
      expect(esPresets.buffet_title).toBe("Hotel & Desayuno Buffet");
      expect(esPresets.buffet_badge).toBe("HOSPITALITY");
      expect(esPresets.clean_slate_title).toBe("Clean Slate (Base Virgen)");
      expect(esPresets.clean_slate_badge).toBe("EMPTY STATE");

      // Verificación de textos específicos en inglés
      expect(enPresets.fast_food_title).toBe("Fast Food & Pollo King");
      expect(enPresets.fast_food_badge).toBe("HIGH ROTATION");
      expect(enPresets.steakhouse_title).toBe("Angus Steaks & Wine Cellar");
      expect(enPresets.steakhouse_badge).toBe("PREMIUM");
      expect(enPresets.buffet_title).toBe("Hotel & Breakfast Buffet");
      expect(enPresets.buffet_badge).toBe("HOSPITALITY");
      expect(enPresets.clean_slate_title).toBe("Clean Slate (Virgin DB)");
      expect(enPresets.clean_slate_badge).toBe("EMPTY STATE");
    });

    it("certifica la invariante inmutable del nombre propio 'Pollo King' (cero traducción espuria)", () => {
      setActiveLanguage("es");
      const esTitle = translateKey("platform_admin", "sandbox.mock_data.presets.fast_food_title");
      expect(esTitle).toContain("Pollo King");
      expect(esTitle).not.toContain("Chicken King");

      setActiveLanguage("en");
      const enTitle = translateKey("platform_admin", "sandbox.mock_data.presets.fast_food_title");
      expect(enTitle).toContain("Pollo King");
      expect(enTitle).not.toContain("Chicken King");
    });

    it("certifica paridad 1:1 del modal Factory Reset, Master Switch y métricas KPI", () => {
      const factoryResetKeys = [
        "factory_reset_btn",
        "factory_reset_title",
        "factory_reset_desc",
        "factory_reset_confirm",
        "factory_reset_btn_confirm",
        "factory_reset_btn_cancel",
        "factory_reset_success",
        "factory_reset_error",
        "master_switch_title_demo",
        "master_switch_title_clean",
        "master_switch_badge_demo",
        "master_switch_badge_clean",
        "kpi_skus",
        "kpi_warehouses",
        "kpi_fefo_batches",
        "kpi_recipes",
        "kpi_critical",
        "kpi_stock_value",
      ];

      const esMockData = (I18N_RESOURCES.es?.platform_admin as any)?.sandbox?.mock_data;
      const enMockData = (I18N_RESOURCES.en?.platform_admin as any)?.sandbox?.mock_data;

      for (const k of factoryResetKeys) {
        expect(esMockData[k]).toBeDefined();
        expect(enMockData[k]).toBeDefined();
        expect(typeof esMockData[k]).toBe("string");
        expect(typeof enMockData[k]).toBe("string");
      }

      // Paridad de placeholders en confirmación modal
      expect(esMockData.factory_reset_confirm).toContain("{{schema}}");
      expect(enMockData.factory_reset_confirm).toContain("{{schema}}");
    });

    it("certifica que los 4 importes canónicos en CLP ($3.85M, $8.94M, $4.12M, $0) se procesan con formatMoney (Decimal)", () => {
      // 1. Fast Food & Pollo King: 3.850.000 CLP
      expect(formatMoney(3850000, "CLP")).toBe("$3.850.000");

      // 2. Carnes Angus & Cava: 8.940.000 CLP
      expect(formatMoney(8940000, "CLP")).toBe("$8.940.000");

      // 3. Hotel & Desayuno Buffet: 4.120.000 CLP
      expect(formatMoney(4120000, "CLP")).toBe("$4.120.000");

      // 4. Clean Slate: 0 CLP
      expect(formatMoney(0, "CLP")).toBe("$0");

      // Verificación de conversiones FX exactas a USD (tasa default BCCh 960 CLP/USD)
      // 3850000 / 960 = 4010.41666667 USD
      const usdFastFood = formatMoney(3850000, "USD", "CLP");
      expect(usdFastFood).toMatch(/^US\$4,010/);

      // 8940000 / 960 = 9312.50 USD
      const usdAngus = formatMoney(8940000, "USD", "CLP");
      expect(usdAngus).toBe("US$9,312.50");

      // Clean Slate en USD siempre $0.00
      expect(formatMoney(0, "USD", "CLP")).toBe("US$0.00");
    });

    it("conmuta MockDataSandboxView dinámicamente reflejando presets y switch en es y en", () => {
      setActiveLanguage("es");
      const { rerender } = renderInTestHarness(<MockDataSandboxView />);

      expect(screen.getByText("Fast Food & Pollo King")).toBeInTheDocument();
      expect(screen.getByText("Carnes Angus & Cava")).toBeInTheDocument();
      expect(screen.getByText("Hotel & Desayuno Buffet")).toBeInTheDocument();
      expect(screen.getByText("Clean Slate (Base Virgen)")).toBeInTheDocument();
      expect(screen.getByText("ALTA ROTACIÓN")).toBeInTheDocument();
      expect(screen.getByText("ALTA GAMA")).toBeInTheDocument();

      // Conmutar a inglés
      setActiveLanguage("en");
      rerender(
        <MemoryRouter initialEntries={["/admin/sandbox/mock-data"]}>
          <MockDataSandboxView />
        </MemoryRouter>
      );

      // Nombres propios protegidos: "Pollo King" intacto en inglés
      expect(screen.getByText("Fast Food & Pollo King")).toBeInTheDocument();
      expect(screen.getByText("Angus Steaks & Wine Cellar")).toBeInTheDocument();
      expect(screen.getByText("Hotel & Breakfast Buffet")).toBeInTheDocument();
      expect(screen.getByText("Clean Slate (Virgin DB)")).toBeInTheDocument();
      expect(screen.getByText("HIGH ROTATION")).toBeInTheDocument();
      expect(screen.getByText("PREMIUM")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 6. SUB-PLAN 3: CERTIFICACIÓN I18N DE PLAYWRIGHT RUNNER & DOMINIOS CANÓNICOS
  // ==========================================================================
  describe("6. Sub-Plan 3: Consola Dinámica Playwright Runner & Dominios Canónicos", () => {
    it("certifica paridad 1:1 exhaustiva de métricas, controles, terminal y los 7 dominios canónicos", () => {
      const esPw = (I18N_RESOURCES.es?.platform_admin as any)?.sandbox?.playwright;
      const enPw = (I18N_RESOURCES.en?.platform_admin as any)?.sandbox?.playwright;

      expect(esPw).toBeDefined();
      expect(enPw).toBeDefined();

      // 1. Métricas de Catálogo
      const metricKeys = [
        "total_tests",
        "coverage_percentage",
        "status_ready",
        "status_in_progress",
        "status_planned",
        "run_all_ready",
      ];
      for (const k of metricKeys) {
        expect(esPw[k]).toBeDefined();
        expect(enPw[k]).toBeDefined();
        expect(typeof esPw[k]).toBe("string");
        expect(typeof enPw[k]).toBe("string");
      }

      // 2. Modos y Controles
      const controlKeys = [
        "mode_title",
        "mode_subtitle",
        "mode_live_demo",
        "mode_ci_headless",
        "browser",
        "workers",
        "retries",
        "target_schema",
      ];
      for (const k of controlKeys) {
        expect(esPw[k]).toBeDefined();
        expect(enPw[k]).toBeDefined();
        expect(typeof esPw[k]).toBe("string");
        expect(typeof enPw[k]).toBe("string");
      }

      // 3. Consola y Terminal
      const terminalKeys = [
        "terminal_title",
        "clear_logs",
        "cancel_run",
        "status_disconnected",
        "status_connecting",
        "status_running",
        "status_completed",
        "status_error",
        "screenshot_link",
      ];
      for (const k of terminalKeys) {
        expect(esPw[k]).toBeDefined();
        expect(enPw[k]).toBeDefined();
        expect(typeof esPw[k]).toBe("string");
        expect(typeof enPw[k]).toBe("string");
      }

      // 4. Los 7 Dominios Canónicos (títulos y descripciones)
      const canonicalDomains = [
        "tenancy",
        "auth_rbac",
        "inventory",
        "recipes",
        "procurement",
        "finops",
        "pos",
      ];
      expect(esPw.domains).toBeDefined();
      expect(enPw.domains).toBeDefined();

      for (const d of canonicalDomains) {
        expect(esPw.domains[d]).toBeDefined();
        expect(enPw.domains[d]).toBeDefined();
        expect(esPw.domains[`${d}_desc`]).toBeDefined();
        expect(enPw.domains[`${d}_desc`]).toBeDefined();
      }

      // Verificación de extracción exhaustiva de claves hoja en sandbox.playwright
      const esPwLeafKeys = extractLeafKeys(esPw).sort();
      const enPwLeafKeys = extractLeafKeys(enPw).sort();
      expect(esPwLeafKeys).toEqual(enPwLeafKeys);
    });

    it("conmuta dinámicamente PlaywrightRunnerSandboxView reflejando métricas, modos y controles en es y en", () => {
      setActiveLanguage("es");
      const { rerender } = renderInTestHarness(<PlaywrightRunnerSandboxView />);

      // Español: Textos de métricas y controles
      expect(screen.getByText("Ejecutar Todos los Tests Ready")).toBeInTheDocument();
      expect(screen.getAllByText("Total de Tests").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Cobertura E2E")).toBeInTheDocument();
      expect(screen.getByText("Modo de Ejecución & Navegador")).toBeInTheDocument();
      expect(screen.getByText("Motor de Navegador")).toBeInTheDocument();
      expect(screen.getByText("playwright-output.log")).toBeInTheDocument();

      // Conmutar a inglés
      setActiveLanguage("en");
      rerender(
        <MemoryRouter initialEntries={["/admin/sandbox/playwright-runner"]}>
          <PermissionsProvider
            initialPolicy={{
              roleName: "SuperAdmin",
              isSuperUser: true,
              planModules: ["platform_admin"],
              rolePermissions: [
                "platform_admin.sandbox.access",
                "platform_admin.sandbox.manage",
              ] as any,
              temporaryGrants: [],
              deniedPermissions: [],
            }}
          >
            <PlaywrightRunnerSandboxView />
          </PermissionsProvider>
        </MemoryRouter>
      );

      // Inglés: Textos conmutados sin hardcoding
      expect(screen.getByText("Run All Ready Tests")).toBeInTheDocument();
      expect(screen.getAllByText("Total Tests").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("E2E Coverage")).toBeInTheDocument();
      expect(screen.getByText("Execution Mode & Browser")).toBeInTheDocument();
      expect(screen.getByText("Browser Engine")).toBeInTheDocument();
      expect(screen.getByText("playwright-output.log")).toBeInTheDocument();
    });

    it("resuelve las descripciones de los 7 dominios canónicos mediante translateKey", () => {
      setActiveLanguage("es");
      expect(
        translateKey("platform_admin", "sandbox.playwright.domains.tenancy_desc")
      ).toContain("Aislamiento estricto multi-tenant");
      expect(
        translateKey("platform_admin", "sandbox.playwright.domains.inventory_desc")
      ).toContain("Gestión FEFO, lotes perecibles");
      expect(
        translateKey("platform_admin", "sandbox.playwright.domains.finops_desc")
      ).toContain("Gestión de créditos IA OppyFy");

      setActiveLanguage("en");
      expect(
        translateKey("platform_admin", "sandbox.playwright.domains.tenancy_desc")
      ).toContain("Strict multi-tenant isolation");
      expect(
        translateKey("platform_admin", "sandbox.playwright.domains.inventory_desc")
      ).toContain("FEFO management, perishable batches");
      expect(
        translateKey("platform_admin", "sandbox.playwright.domains.finops_desc")
      ).toContain("OppyFy AI credit management");
    });
  });

  // ==========================================================================
  // 7. SUB-PLAN 4: CERTIFICACIÓN I18N & MULTI-MONEDA FX PARA SIMULADOR FEFO
  // ==========================================================================
  describe("7. Sub-Plan 4: Simulador FEFO, Time-Travel Engine & Certificación i18n/FX", () => {
    it("certifica paridad 1:1 exhaustiva de claves de cabecera, bodega, switch, botón quirúrgico y modal en sandbox.fefo", () => {
      const esFefo = (I18N_RESOURCES.es?.platform_admin as any)?.sandbox?.fefo;
      const enFefo = (I18N_RESOURCES.en?.platform_admin as any)?.sandbox?.fefo;

      expect(esFefo).toBeDefined();
      expect(enFefo).toBeDefined();

      const esLeafKeys = extractLeafKeys(esFefo).sort();
      const enLeafKeys = extractLeafKeys(enFefo).sort();

      expect(esLeafKeys).toEqual(enLeafKeys);
      expect(esLeafKeys.length).toBeGreaterThanOrEqual(60);

      // Verificación de claves críticas del Sub-Plan 4
      const requiredKeys = [
        "header_title",
        "subplan_badge",
        "today_prefix",
        "tenant_prefix",
        "warehouse_label",
        "warehouse_central",
        "warehouse_bar",
        "warehouse_cold",
        "dry_run_label",
        "btn_sync_today",
        "btn_sync_today_loading",
        "sync_today_tooltip",
        "sync_today_success",
        "sync_today_error",
        "scenarios_title",
        "scenarios_subtitle",
        "scenario_active_badge",
        "scenario_distribution_label",
        "scenario_activated_feedback",
        "quick_offsets_label",
        "slider_time_shift_label",
        "slider_offset_today",
        "slider_offset_future",
        "slider_offset_past",
        "slider_range_info",
        "kpi_optimal_batches",
        "kpi_warning_batches",
        "kpi_critical_batches",
        "kpi_expired_batches",
        "kpi_risk_amount",
        "filter_all",
        "filter_optimal",
        "filter_warning",
        "filter_critical",
        "filter_expired",
        "modal_shift_title",
        "modal_shift_subtitle",
        "modal_tenant_label",
        "modal_offset_label",
        "modal_simulated_date_label",
        "modal_batches_affected_label",
        "modal_batches_affected_val",
        "modal_risk_amount_label",
        "modal_warning_text",
        "modal_confirm_checkbox",
        "modal_btn_cancel",
        "modal_btn_confirm",
        "btn_apply_shift",
        "btn_apply_shift_loading",
      ];

      for (const k of requiredKeys) {
        expect(esFefo[k]).toBeDefined();
        expect(enFefo[k]).toBeDefined();
        expect(typeof esFefo[k]).toBe("string");
        expect(typeof enFefo[k]).toBe("string");
        expect(esFefo[k].length).toBeGreaterThan(0);
        expect(enFefo[k].length).toBeGreaterThan(0);
      }
    });

    it("certifica paridad 1:1 de los 3 escenarios calibrados (HEALTHY, WARNING, CRITICAL) y semáforos", () => {
      const esFefo = (I18N_RESOURCES.es?.platform_admin as any)?.sandbox?.fefo;
      const enFefo = (I18N_RESOURCES.en?.platform_admin as any)?.sandbox?.fefo;

      const scenarios = ["scenario_healthy", "scenario_warning", "scenario_critical"];
      const scenarioFields = ["title", "subtitle", "description", "distribution_summary"];

      for (const s of scenarios) {
        expect(esFefo[s]).toBeDefined();
        expect(enFefo[s]).toBeDefined();
        for (const f of scenarioFields) {
          expect(esFefo[s][f]).toBeTruthy();
          expect(enFefo[s][f]).toBeTruthy();
          expect(typeof esFefo[s][f]).toBe("string");
          expect(typeof enFefo[s][f]).toBe("string");
        }
      }

      // Paridad de estados de semáforo
      const statuses = ["optimal", "warning", "critical", "expired"];
      for (const st of statuses) {
        expect(esFefo.status[st]).toBeTruthy();
        expect(enFefo.status[st]).toBeTruthy();
      }

      // Paridad de columnas de la tabla FEFO
      const tableColumns = [
        "col_batch_sku",
        "col_product",
        "col_warehouse",
        "col_original_expiry",
        "col_simulated_expiry",
        "col_days_left",
        "col_fefo_status",
        "col_stock",
        "col_est_loss",
      ];
      for (const col of tableColumns) {
        expect(esFefo.table[col]).toBeTruthy();
        expect(enFefo.table[col]).toBeTruthy();
      }
    });

    it("conmuta dinámicamente FefoDatesSandboxView sin hardcoding de strings en UI", () => {
      setActiveLanguage("es");
      const { rerender } = renderInTestHarness(<FefoDatesSandboxView />);

      // Textos en español
      expect(screen.getByText("Simulador FEFO & Time-Travel Engine")).toBeInTheDocument();
      expect(screen.getByText("Escenarios Calibrados de Demostración")).toBeInTheDocument();
      expect(screen.getByText("Operación Saludable")).toBeInTheDocument();
      expect(screen.getByText("Alerta Fin de Semana")).toBeInTheDocument();
      expect(screen.getByText("Auditoría / Rotura de Frío")).toBeInTheDocument();
      expect(screen.getByText("⚡ Sincronizar Fechas a Hoy")).toBeInTheDocument();
      expect(screen.getByText("Desplazamiento Temporal:")).toBeInTheDocument();
      expect(screen.getByText("Accesos Rápidos:")).toBeInTheDocument();
      expect(screen.getByText("Bodega Cocina Central")).toBeInTheDocument();
      expect(screen.getByText("Modo Dry-Run")).toBeInTheDocument();

      // Cambiar a inglés
      setActiveLanguage("en");
      rerender(
        <MemoryRouter initialEntries={["/admin/sandbox/fefo-dates"]}>
          <PermissionsProvider
            initialPolicy={{
              roleName: "SuperAdmin",
              isSuperUser: true,
              planModules: ["platform_admin"],
              rolePermissions: [
                "platform_admin.sandbox.access",
                "platform_admin.sandbox.manage",
              ] as any,
              temporaryGrants: [],
              deniedPermissions: [],
            }}
          >
            <FefoDatesSandboxView />
          </PermissionsProvider>
        </MemoryRouter>
      );

      // Textos en inglés conmutados limpiamente
      expect(screen.getByText("FEFO Simulator & Time-Travel Engine")).toBeInTheDocument();
      expect(screen.getByText("Calibrated Demo Scenarios")).toBeInTheDocument();
      expect(screen.getByText("Healthy Operation")).toBeInTheDocument();
      expect(screen.getByText("Weekend Alert")).toBeInTheDocument();
      expect(screen.getByText("Audit / Cold Chain Failure")).toBeInTheDocument();
      expect(screen.getByText("⚡ Sync Dates to Today")).toBeInTheDocument();
      expect(screen.getByText("Time Shift:")).toBeInTheDocument();
      expect(screen.getByText("Quick Offsets:")).toBeInTheDocument();
      expect(screen.getByText("Central Kitchen Warehouse")).toBeInTheDocument();
      expect(screen.getByText("Dry-Run Mode")).toBeInTheDocument();
    });

    it("certifica cuantificación de merma y precisión Decimal en conversiones FX (CLP -> USD / EUR)", () => {
      // 1. Caso Lote Vencido (100% merma)
      // Cantidad 18.5 Kg * $14.500 CLP = $268.250 CLP
      const expiredLoss = 18.5 * 14500 * 1.0;
      expect(formatMoney(expiredLoss, "CLP")).toBe("$268.250");

      // 2. Caso Lote Crítico (75% merma)
      // Cantidad 24 Kg * $8.900 CLP * 0.75 = $160.200 CLP
      const criticalLoss = 24 * 8900 * 0.75;
      expect(formatMoney(criticalLoss, "CLP")).toBe("$160.200");

      // 3. Caso Lote Advertencia u Óptimo (0% merma)
      expect(formatMoney(0, "CLP")).toBe("$0");

      // 4. Conversión FX exacta a USD (960 CLP/USD tasa fija BCCh)
      // 268.250 / 960 = 279.42708333 USD -> US$279.43
      const fxUsd = formatMoney(expiredLoss, "USD", "CLP");
      expect(fxUsd).toBe("US$279.43");

      // 5. Conversión FX exacta a EUR (1040 CLP/EUR tasa fija BCE)
      // 268.250 / 1040 = 257.9326923 USD -> €257,93
      const fxEur = formatMoney(expiredLoss, "EUR", "CLP");
      expect(fxEur).toBe("€257,93");
    });

    it("certifica que los placeholders de plantillas ({{date}}, {{days}}, {{tenant}}, {{count}}) guardan paridad estricta", () => {
      const esFefo = (I18N_RESOURCES.es?.platform_admin as any)?.sandbox?.fefo;
      const enFefo = (I18N_RESOURCES.en?.platform_admin as any)?.sandbox?.fefo;

      // sync_today_success: {{date}}
      expect(esFefo.sync_today_success).toContain("{{date}}");
      expect(enFefo.sync_today_success).toContain("{{date}}");

      // shift_success: {{days}}, {{tenant}}
      expect(esFefo.shift_success).toContain("{{days}}");
      expect(enFefo.shift_success).toContain("{{days}}");
      expect(esFefo.shift_success).toContain("{{tenant}}");
      expect(enFefo.shift_success).toContain("{{tenant}}");

      // modal_warning_text: {{tenant}}
      expect(esFefo.modal_warning_text).toContain("{{tenant}}");
      expect(enFefo.modal_warning_text).toContain("{{tenant}}");

      // modal_batches_affected_val: {{count}}
      expect(esFefo.modal_batches_affected_val).toContain("{{count}}");
      expect(enFefo.modal_batches_affected_val).toContain("{{count}}");

      // filter_all: {{count}}
      expect(esFefo.filter_all).toContain("{{count}}");
      expect(enFefo.filter_all).toContain("{{count}}");
    });
  });

  // ==========================================================================
  // 8. ADR-022: CERTIFICACIÓN BÓVEDA DE RESPALDO JSON, CLEAN SLATE ($0) & 11 NAMESPACES CORE
  // ==========================================================================
  describe("8. ADR-022: Bóveda de Respaldo JSON (mock_data_backup.json), Clean Slate ($0) y Paridad 11 Namespaces", () => {
    it("certifica paridad 1:1 exacta en los 11 namespaces núcleo de i18n (es/en)", () => {
      const core11Namespaces = [
        "common",
        "auth",
        "navigation",
        "catalog",
        "inventory",
        "recipes",
        "operations",
        "analytics",
        "oppyfy",
        "platform_admin",
        "holding_hub",
      ] as const;

      for (const ns of core11Namespaces) {
        const esObj = (I18N_RESOURCES.es as any)?.[ns];
        const enObj = (I18N_RESOURCES.en as any)?.[ns];
        expect(esObj).toBeDefined();
        expect(enObj).toBeDefined();

        const esLeafs = extractLeafKeys(esObj).sort();
        const enLeafs = extractLeafKeys(enObj).sort();
        expect(esLeafs).toEqual(enLeafs);
        expect(esLeafs.length).toBeGreaterThan(0);
      }
    });

    it("certifica paridad 1:1 y conmutación dinámica de la Bóveda de Respaldo JSON (mock_data_backup.json) y Clean Slate", () => {
      const backupVaultKeys = [
        "backup_vault_title",
        "backup_vault_desc",
        "btn_download_backup",
        "btn_purge_clean_slate",
        "btn_restore_backup",
        "purge_clean_slate_success",
        "restore_backup_success",
      ];

      const esMock = (I18N_RESOURCES.es?.platform_admin as any)?.sandbox?.mock_data;
      const enMock = (I18N_RESOURCES.en?.platform_admin as any)?.sandbox?.mock_data;

      for (const k of backupVaultKeys) {
        expect(esMock[k]).toBeTruthy();
        expect(enMock[k]).toBeTruthy();
        expect(typeof esMock[k]).toBe("string");
        expect(typeof enMock[k]).toBe("string");
      }

      setActiveLanguage("es");
      const { rerender } = renderInTestHarness(<MockDataSandboxView />);

      expect(screen.getByText("Respaldo Maestro JSON (mock_data_backup.json)")).toBeInTheDocument();
      expect(screen.getByText("Descargar Respaldo JSON")).toBeInTheDocument();
      expect(screen.getByText("Limpiar Todo (Clean Slate 100%)")).toBeInTheDocument();
      expect(screen.getByText("Restaurar Mock Data desde Respaldo")).toBeInTheDocument();
      expect(screen.getByText("FinOps IA & Aislamiento de Créditos")).toBeInTheDocument();

      setActiveLanguage("en");
      rerender(
        <MemoryRouter initialEntries={["/admin/sandbox/mock-data"]}>
          <PermissionsProvider
            initialPolicy={{
              roleName: "SuperAdmin",
              isSuperUser: true,
              planModules: ["platform_admin"],
              rolePermissions: [
                "platform_admin.sandbox.access",
                "platform_admin.sandbox.manage",
              ] as any,
              temporaryGrants: [],
              deniedPermissions: [],
            }}
          >
            <MockDataSandboxView />
          </PermissionsProvider>
        </MemoryRouter>
      );

      expect(screen.getByText("Master JSON Backup (mock_data_backup.json)")).toBeInTheDocument();
      expect(screen.getByText("Download JSON Backup")).toBeInTheDocument();
      expect(screen.getByText("Purge All (100% Clean Slate)")).toBeInTheDocument();
      expect(screen.getByText("Restore Mock Data from Backup")).toBeInTheDocument();
      expect(screen.getByText("FinOps AI & Credit Isolation")).toBeInTheDocument();
    });

    it("certifica formateo monetario Decimal en modo Clean Slate ($0) sin regresiones", () => {
      expect(formatMoney(0, "CLP", "CLP")).toBe("$0");
      expect(formatMoney("0", "CLP", "CLP")).toBe("$0");
      expect(formatMoney(0, "USD", "CLP")).toBe("US$0.00");
      expect(formatMoney(0, "EUR", "CLP")).toBe("€0,00");
    });
  });
});
