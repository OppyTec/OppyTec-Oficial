/**
 * oppytec-frontend/src/features/procurement/__tests__/GestionarMermaView.test.tsx
 * Suite de Pruebas Unitarias e Integración para Gestión Analítica de Mermas (Fase 6).
 * Cubre:
 * - SectionHeader (#ef4444), KpiDashboard con formateo FX y motivo principal.
 * - MermaDateRangePicker (presets hoy/7d/30d/mes_actual/mes_anterior y rango personalizado).
 * - MermaStats (evolución temporal determinista y desglose por motivos/categorías).
 * - MermaHistory (filtrado por texto y motivo, regla "Pollo King", vista Tabla/Tarjetas).
 * - Apertura y operación del modal "+ Registrar Merma" (MermaDialog).
 * - Montaje integrado en GestionPage con ?tab=mermas y navegación por GestionTabNav.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { CurrencyProvider } from "@/shared/currency";
import { GestionPage } from "@/features/gestion/GestionPage";
import { GestionarMermaView } from "../mermas/GestionarMermaView";
import {
  MOCK_MERMA_ANALYTICS,
  MOCK_MERMA_HISTORY,
} from "../mockData";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string): string | null => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = String(value);
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((idx: number) => Object.keys(store)[idx] ?? null),
  };
})();

Object.defineProperty(globalThis, "localStorage", {
  value: mockLocalStorage,
  writable: true,
});

function createWrapper(initialRoute = "/gestion?tab=mermas") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={[initialRoute]}>
        <QueryClientProvider client={queryClient}>
          <PermissionsProvider>
            <CurrencyProvider>{children}</CurrencyProvider>
          </PermissionsProvider>
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

describe("Feature Procurement - Fase 6: Gestión Analítica de Mermas Suite", () => {
  beforeEach(() => {
    mockLocalStorage.clear();
    vi.clearAllMocks();

    vi.spyOn(httpClient, "apiRequest").mockImplementation(
      async <T,>(url: string, options?: { fallbackData?: T }): Promise<httpClient.ApiEnvelope<T>> => {
        let returnData: unknown = options?.fallbackData;

        if (url.includes("/api/v1/inventory/mermas/analytics")) {
          returnData = MOCK_MERMA_ANALYTICS;
        } else if (url.includes("/api/v1/inventory/mermas/history")) {
          returnData = {
            items: MOCK_MERMA_HISTORY,
            total: MOCK_MERMA_HISTORY.length,
          };
        }

        return {
          data: (returnData ?? options?.fallbackData) as T,
          traceId: "test-merma-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
    );
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. RENDERIZADO DE SECTIONHEADER Y KPIDASHBOARD
  // ==========================================================================
  describe("1. Renderizado de SectionHeader (#ef4444) y KpiDashboard con Formateo FX", () => {
    it("renderiza SectionHeader con título, subtítulo y los 4 KPIs financieros y operativos", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GestionarMermaView />
        </Wrapper>
      );

      expect(screen.getByTestId("mermas-section-header")).toBeDefined();
      expect(screen.getByText("Gestión y Control de Mermas")).toBeDefined();
      expect(
        screen.getAllByText(
          "Monitoreo analítico de pérdidas operativas, caducidades y motivos"
        )[0]
      ).toBeDefined();

      // KPIs
      await screen.findByTestId("merma-kpi-dashboard");
      expect(screen.getByTestId("kpi-perdida-neta-ppp")).toBeDefined();
      expect(screen.getByTestId("kpi-unidades-descartadas")).toBeDefined();
      expect(screen.getByTestId("kpi-ratio-merma")).toBeDefined();
      expect(screen.getByTestId("kpi-motivo-principal")).toBeDefined();

      // Valores de KPIs
      expect(screen.getByTestId("kpi-ratio-value").textContent).toContain("1.42%");
      expect(screen.getByTestId("kpi-motivo-principal-name").textContent).toBe("Vencimiento");
      expect(screen.getByTestId("kpi-motivo-principal-pct").textContent).toContain("53.1%");
    });
  });

  // ==========================================================================
  // 2. MERMADATERANGEPICKER (PRESETS Y RANGO PERSONALIZADO)
  // ==========================================================================
  describe("2. Selector Reactivo de Rango de Fechas (MermaDateRangePicker)", () => {
    it("permite alternar entre los presets rápidos (hoy, 7d, 30d, mes_actual, mes_anterior)", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GestionarMermaView />
        </Wrapper>
      );

      expect(screen.getByTestId("merma-date-range-picker")).toBeDefined();

      // Por defecto inicia en 30d
      const btn30d = screen.getByTestId("preset-btn-30d");
      expect(btn30d.getAttribute("aria-pressed")).toBe("true");

      // Cambiar a Hoy
      const btnHoy = screen.getByTestId("preset-btn-hoy");
      fireEvent.click(btnHoy);

      await waitFor(() => {
        expect(btnHoy.getAttribute("aria-pressed")).toBe("true");
        expect(btn30d.getAttribute("aria-pressed")).toBe("false");
      });

      // Cambiar a Últimos 7 días
      const btn7d = screen.getByTestId("preset-btn-7d");
      fireEvent.click(btn7d);

      await waitFor(() => {
        expect(btn7d.getAttribute("aria-pressed")).toBe("true");
      });

      // Cambiar a Este Mes
      const btnMesActual = screen.getByTestId("preset-btn-mes_actual");
      fireEvent.click(btnMesActual);

      await waitFor(() => {
        expect(btnMesActual.getAttribute("aria-pressed")).toBe("true");
      });

      // Cambiar a Mes Anterior
      const btnMesAnterior = screen.getByTestId("preset-btn-mes_anterior");
      fireEvent.click(btnMesAnterior);

      await waitFor(() => {
        expect(btnMesAnterior.getAttribute("aria-pressed")).toBe("true");
      });
    });

    it("despliega controles de rango personalizado y actualiza las fechas reactivamente", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GestionarMermaView />
        </Wrapper>
      );

      const btnCustom = screen.getByTestId("preset-btn-personalizado");
      fireEvent.click(btnCustom);

      await waitFor(() => {
        expect(screen.getByTestId("custom-date-range-controls")).toBeDefined();
      });

      const inputFrom = screen.getByTestId("input-date-from") as HTMLInputElement;
      const inputTo = screen.getByTestId("input-date-to") as HTMLInputElement;

      fireEvent.change(inputFrom, { target: { value: "2026-10-05" } });
      fireEvent.change(inputTo, { target: { value: "2026-10-20" } });
      fireEvent.click(screen.getByTestId("btn-apply-custom-range"));

      await waitFor(() => {
        expect(screen.getByTestId("merma-active-date-range-label").textContent).toContain(
          "2026-10-05 → 2026-10-20"
        );
      });
    });
  });

  // ==========================================================================
  // 3. MERMASTATS (EVOLUCIÓN TEMPORAL Y DISTRIBUCIÓN POR MOTIVO/CATEGORÍA)
  // ==========================================================================
  describe("3. Visualización Analítica (MermaStats)", () => {
    it("renderiza la serie de evolución temporal y el desglose por motivos y categorías", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GestionarMermaView />
        </Wrapper>
      );

      expect(screen.getByTestId("merma-stats-timeline")).toBeDefined();
      expect(screen.getByTestId("merma-timeline-bars")).toBeDefined();
      expect(screen.getByTestId("timeline-point-2026-10-23")).toBeDefined();

      // Desglose por motivos
      expect(screen.getByTestId("merma-stats-motivos")).toBeDefined();
      expect(screen.getByTestId("motivo-breakdown-item-Vencimiento")).toBeDefined();
      expect(screen.getByTestId("motivo-breakdown-item-Rotura / Daño Físico")).toBeDefined();

      // Cambiar a desglose por Categoría
      fireEvent.click(screen.getByTestId("btn-breakdown-categoria"));

      await waitFor(() => {
        expect(screen.getByTestId("motivo-breakdown-item-Proteínas y Carnes")).toBeDefined();
        expect(screen.getByTestId("motivo-breakdown-item-Lácteos y Derivados")).toBeDefined();
      });

      // Volver a desglose por Motivo
      fireEvent.click(screen.getByTestId("btn-breakdown-motivo"));

      await waitFor(() => {
        expect(screen.getByTestId("motivo-breakdown-item-Vencimiento")).toBeDefined();
      });
    });
  });

  // ==========================================================================
  // 4. MERMAHISTORY (FILTRADO, REGLA POLLO KING Y VISTA DUAL)
  // ==========================================================================
  describe("4. Historial Detallado de Mermas (MermaHistory) y Regla 'Pollo King'", () => {
    it("muestra los registros históricos respetando 'Pollo King' y permite filtrar por texto y motivo", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GestionarMermaView />
        </Wrapper>
      );

      await screen.findByTestId("merma-history-table");

      // Regla "Pollo King": nombre comercial intacto
      expect(screen.getByTestId("merma-row-producto-501").textContent).toBe("Pollo King");
      expect(screen.getByTestId("merma-row-producto-502").textContent).toBe(
        "Salmón Atlántico Fresco"
      );
      expect(screen.getByTestId("merma-row-producto-503").textContent).toBe("Tomate Larga Vida");

      // Filtrar por texto "Pollo King"
      const searchInput = screen.getByTestId("input-search-merma-history");
      fireEvent.change(searchInput, { target: { value: "Pollo King" } });

      await waitFor(() => {
        expect(screen.getByTestId("merma-history-row-501")).toBeDefined();
        expect(screen.queryByTestId("merma-history-row-502")).toBeNull();
        expect(screen.queryByTestId("merma-history-row-503")).toBeNull();
      });

      // Limpiar búsqueda
      fireEvent.click(screen.getByTestId("btn-clear-merma-search"));

      await waitFor(() => {
        expect(screen.getByTestId("merma-history-row-502")).toBeDefined();
      });

      // Filtrar por motivo "Cadena de Frío"
      const motivoSelect = screen.getByTestId("select-filter-motivo");
      fireEvent.change(motivoSelect, { target: { value: "Cadena de Frío" } });

      await waitFor(() => {
        expect(screen.getByTestId("merma-history-row-502")).toBeDefined();
        expect(screen.queryByTestId("merma-history-row-501")).toBeNull();
      });

      // Conmutar a vista de tarjetas Mobile-First
      fireEvent.click(screen.getByTestId("merma-history-view-cards"));

      await waitFor(() => {
        expect(screen.getByTestId("merma-history-cards")).toBeDefined();
        expect(screen.getByTestId("merma-history-card-502")).toBeDefined();
      });
    });
  });

  // ==========================================================================
  // 5. MODAL + REGISTRAR MERMA (MERMADIALOG)
  // ==========================================================================
  describe("5. Apertura y Registro en MermaDialog (+ Registrar Merma)", () => {
    it("abre el modal MermaDialog al hacer clic en '+ Registrar Merma' y permite confirmar una merma", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <GestionarMermaView />
        </Wrapper>
      );

      const btnRegistrar = screen.getByTestId("btn-registrar-merma");
      fireEvent.click(btnRegistrar);

      await waitFor(() => {
        expect(screen.getByTestId("dialog-merma-container")).toBeDefined();
        expect(screen.getByTestId("merma-product-select")).toBeDefined();
        expect(screen.getByTestId("merma-quantity-input")).toBeDefined();
      });

      // Cambiar cantidad y confirmar
      fireEvent.change(screen.getByTestId("merma-quantity-input"), {
        target: { value: "2" },
      });

      const confirmBtn = screen.getByTestId("btn-confirm-merma");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("dialog-merma-container")).toBeNull();
      });
    });
  });

  // ==========================================================================
  // 6. MONTAJE INTEGRADO EN GESTIONPAGE (?tab=mermas)
  // ==========================================================================
  describe("6. Montaje en GestionPage (/gestion?tab=mermas)", () => {
    it("monta GestionarMermaView cuando la ruta es /gestion?tab=mermas y permite navegar desde GestionTabNav", async () => {
      const Wrapper = createWrapper("/gestion?tab=mermas");
      render(
        <Wrapper>
          <GestionPage />
        </Wrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId("gestionar-merma-view")).toBeDefined();
        expect(screen.getByText("Gestión y Control de Mermas")).toBeDefined();
        expect(screen.getByTestId("gestion-tab-mermas")).toBeDefined();
      });
    });
  });
});
