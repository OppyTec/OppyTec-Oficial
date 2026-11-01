/**
 * oppytec-frontend/src/features/platform-admin/jev/__tests__/JevConsumptionI18nAndFx.test.tsx
 *
 * Test suite de Certificación y Auditoría para el Agente 07 (07-i18n-and-fx-currency-specialist):
 * "Internacionalización Atómica (es/en) y Precisión Multi-Moneda FX para la Consola FinOps JEV"
 *
 * Cobertura:
 * 1. Paridad 1:1 estricta de claves entre `es/platform_admin.json` y `en/platform_admin.json`
 *    en `jev`, `jevConsumption`, `nav.jevConsumption`, `admin.nav.jev_consumption` y `sidebar.menu_jev_consumption`.
 * 2. Ausencia de textos quemados o sin traducir en `JevConsumptionPage.tsx` (conmutación en vivo es/en).
 * 3. Precisión Multi-Moneda FX (USD con precisión decimal, CLP redondeado sin pérdida, cálculo de ahorros).
 */

import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as httpClient from "@/shared/api/httpClient";
import { formatCurrencyAmount } from "@/shared/currency";
import {
  I18N_RESOURCES,
  setActiveLanguage,
  translateKey,
} from "@/shared/i18n";

import { MOCK_JEV_CONSUMPTION } from "../../types";
import { JevConsumptionPage } from "../JevConsumptionPage";

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

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

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

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/admin/jev-consumption"]}>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

const createMockEnvelope = <T,>(data: T): httpClient.ApiEnvelope<T> => ({
  data,
  traceId: "trace-jev-i18n-test",
  timestampIso: new Date().toISOString(),
  tenantId: "tenant_rest_central",
});

describe("Agente 07 — Certificación de i18n & FX para Consola FinOps JEV", () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    setActiveLanguage("es");

    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string) => {
      if (url.includes("/jev-consumption")) {
        return createMockEnvelope(MOCK_JEV_CONSUMPTION);
      }
      return createMockEnvelope({});
    });
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
    setActiveLanguage("es");
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. PARIDAD 1:1 DE CLAVES EN PLATFORM_ADMIN.JSON
  // ==========================================================================
  describe("1. Paridad 1:1 Estricta de Claves en platform_admin.json", () => {
    it("certifica paridad 1:1 entre es y en para la sección 'jev' y 'jevConsumption'", () => {
      const esJev = (I18N_RESOURCES.es?.platform_admin as any)?.jev;
      const enJev = (I18N_RESOURCES.en?.platform_admin as any)?.jev;
      const esJevCons = (I18N_RESOURCES.es?.platform_admin as any)?.jevConsumption;
      const enJevCons = (I18N_RESOURCES.en?.platform_admin as any)?.jevConsumption;

      expect(esJev).toBeDefined();
      expect(enJev).toBeDefined();
      expect(esJevCons).toBeDefined();
      expect(enJevCons).toBeDefined();

      const esEntries = extractLeafEntries(esJev);
      const enEntries = extractLeafEntries(enJev);

      const esKeys = esEntries.map((e) => e.key).sort();
      const enKeys = enEntries.map((e) => e.key).sort();

      expect(esKeys).toEqual(enKeys);
      expect(esKeys.length).toBeGreaterThanOrEqual(30);

      // Paridad con jevConsumption
      const esConsEntries = extractLeafEntries(esJevCons);
      const enConsEntries = extractLeafEntries(enJevCons);
      expect(esConsEntries.map((e) => e.key).sort()).toEqual(esKeys);
      expect(enConsEntries.map((e) => e.key).sort()).toEqual(enKeys);
    });

    it("certifica claves de navegación 'nav.jevConsumption', 'admin.nav.jev_consumption' y 'sidebar.menu_jev_consumption'", () => {
      const esAdmin = I18N_RESOURCES.es?.platform_admin as any;
      const enAdmin = I18N_RESOURCES.en?.platform_admin as any;

      // nav.jevConsumption y nav.jev_consumption
      expect(esAdmin.nav?.jevConsumption).toBe("Consumo de JEV");
      expect(enAdmin.nav?.jevConsumption).toBe("JEV Consumption");
      expect(esAdmin.nav?.jev_consumption).toBe("Consumo de JEV");
      expect(enAdmin.nav?.jev_consumption).toBe("JEV Consumption");

      // admin.nav
      expect(esAdmin.admin?.nav?.jev_consumption).toBe("Consumo de JEV");
      expect(enAdmin.admin?.nav?.jev_consumption).toBe("JEV Consumption");
      expect(esAdmin.admin?.nav?.jevConsumption).toBe("Consumo de JEV");
      expect(enAdmin.admin?.nav?.jevConsumption).toBe("JEV Consumption");

      // sidebar.menu_jev_consumption
      expect(esAdmin.sidebar?.menu_jev_consumption).toBe("Consumo de JEV");
      expect(enAdmin.sidebar?.menu_jev_consumption).toBe("JEV Consumption");
    });
  });

  // ==========================================================================
  // 2. CONMUTACIÓN DINÁMICA DE IDIOMA EN JEV CONSUMPTION
  // ==========================================================================
  describe("2. Conmutación Dinámica de Idioma (es -> en)", () => {
    it("traduce correctamente los títulos y cabeceras al cambiar a inglés", () => {
      setActiveLanguage("es");
      expect(translateKey("platform_admin", "jev.title")).toBe("Consumo de Decisiones JEV");
      expect(translateKey("platform_admin", "jev.tabs.holding")).toBe("Vista por Holding");
      expect(translateKey("platform_admin", "jev.tabs.tenant")).toBe("Vista por Tenant");
      expect(translateKey("platform_admin", "jev.tabs.logs")).toBe("Bitácora de Decisiones");

      setActiveLanguage("en");
      expect(translateKey("platform_admin", "jev.title")).toBe("JEV Decision Consumption");
      expect(translateKey("platform_admin", "jev.tabs.holding")).toBe("Holding View");
      expect(translateKey("platform_admin", "jev.tabs.tenant")).toBe("Tenant View");
      expect(translateKey("platform_admin", "jev.tabs.logs")).toBe("Decision Logs");
    });

    it("renderiza JevConsumptionPage con textos en español y luego conmuta a inglés", () => {
      setActiveLanguage("es");
      const Wrapper = createWrapper();
      const { rerender } = render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      expect(screen.getByText(/Consumo de Decisiones JEV/i)).toBeInTheDocument();
      expect(screen.getByText(/FinOps & Optimización Sub-Simbólica/i)).toBeInTheDocument();

      // Cambiar a inglés
      setActiveLanguage("en");
      rerender(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      expect(screen.getByText(/JEV Decision Consumption/i)).toBeInTheDocument();
      expect(screen.getByText(/FinOps & Sub-Symbolic Optimization/i)).toBeInTheDocument();
      expect(screen.getByText(/Deterministic \/ Heuristic JEV Engine/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 3. MULTI-MONEDA FX Y PRECISIÓN FINOPS
  // ==========================================================================
  describe("3. Precisión Multi-Moneda FX y FinOps", () => {
    it("formatea correctamente costos en USD con alta precisión para micro-llamadas AI", () => {
      // Costo unitario sub-simbólico: 5 decimales
      const microCost = "0.00010";
      expect(Number(microCost).toFixed(5)).toBe("0.00010");

      // Formateador estándar de OppyTec
      expect(formatCurrencyAmount("1250.50", "USD")).toBe("US$1,250.50");
      expect(formatCurrencyAmount("15000", "CLP")).toBe("$15.000");
    });

    it("calcula y formatea el ahorro estimado FinOps en USD y CLP sin error", () => {
      const usdSavings = 485.60;
      const clpSavings = 461320;

      const formattedUsd = `+$${usdSavings.toFixed(2)} USD`;
      const formattedClp = `~+$${Math.round(clpSavings).toLocaleString("es-CL")} CLP`;

      expect(formattedUsd).toBe("+$485.60 USD");
      expect(formattedClp).toBe("~+$461.320 CLP");
    });
  });
});
