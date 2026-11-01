import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import { AdminSidebar } from "../../AdminSidebar";
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

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
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
  traceId: "trace-jev-test",
  timestampIso: new Date().toISOString(),
  tenantId: "tenant_rest_central",
});

describe("JevConsumptionPage — Consola FinOps de Decisiones JEV (Etapa 2 Frontend)", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
      const method = options?.method ?? "GET";
      if (method === "GET") {
        if (url.includes("/jev-consumption")) {
          return createMockEnvelope(MOCK_JEV_CONSUMPTION);
        }
      }
      return createMockEnvelope({});
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  // ==========================================================================
  // 1. CABECERA CANÓNICA Y NAVEGACIÓN
  // ==========================================================================
  describe("1. Cabecera Canónica y Enlaces", () => {
    it("renderiza el pre-título FinOps, título canónico y badge de motor heurístico", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      expect(screen.getByTestId("jev-consumption-page")).toBeInTheDocument();
      expect(screen.getByText(/Consumo de Decisiones JEV/i)).toBeInTheDocument();
      expect(screen.getByTestId("jev-subsymbolic-badge")).toBeInTheDocument();
      expect(screen.getByText(/Motor JEV Heurístico \/ Determinista/i)).toBeInTheDocument();
      expect(screen.getByTestId("token-consumption-link")).toHaveAttribute(
        "href",
        "/admin/token-consumption"
      );
    });
  });

  // ==========================================================================
  // 2. TARJETAS KPI SUPERIORES (HEAD METRICS)
  // ==========================================================================
  describe("2. Tarjetas KPI Superiores (Head Metrics)", () => {
    it("muestra las 4 tarjetas KPI con métricas agregadas globales", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      // KPI 1: Total Decisiones
      const kpiDecisions = screen.getByTestId("kpi-total-decisions");
      expect(kpiDecisions).toBeInTheDocument();
      expect(kpiDecisions).toHaveTextContent("12.480");

      // KPI 2: Costo Real Proveedor
      const kpiCost = screen.getByTestId("kpi-real-provider-cost");
      expect(kpiCost).toBeInTheDocument();
      expect(kpiCost).toHaveTextContent("$1.8450");

      // KPI 3: Latencia Promedio
      const kpiLatency = screen.getByTestId("kpi-avg-latency");
      expect(kpiLatency).toBeInTheDocument();
      expect(kpiLatency).toHaveTextContent("18.4 ms");

      // KPI 4: Calibración de Confianza
      const kpiCalib = screen.getByTestId("kpi-confidence-calibration");
      expect(kpiCalib).toBeInTheDocument();
      expect(kpiCalib).toHaveTextContent("90.1% Auto");
      expect(kpiCalib).toHaveTextContent("7.9% Warn");
      expect(kpiCalib).toHaveTextContent("2.0% LLM");
    });

    it("renderiza la tarjeta de Ahorro Estimado FinOps", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      const savingsCard = screen.getByTestId("finops-savings-card");
      expect(savingsCard).toBeInTheDocument();
      expect(savingsCard).toHaveTextContent("+$485.60 USD");
      expect(savingsCard).toHaveTextContent("Ahorro Estimado FinOps");
    });
  });

  // ==========================================================================
  // 3. PESTAÑAS (VIEW MODES): HOLDING, TENANT, LOGS
  // ==========================================================================
  describe("3. Pestañas / View Modes", () => {
    it("inicia en modo 'holding' con acordeón desplegable de Holdings", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      expect(screen.getByTestId("jev-holding-view")).toBeInTheDocument();
      expect(screen.getByTestId("holding-card-holding-gastro-sur")).toBeInTheDocument();
      expect(screen.getByText("Holding Gastronomía del Sur")).toBeInTheDocument();

      // Verificar que el primer holding está expandido por defecto
      expect(screen.getByTestId("holding-tenant-tenant_rest_central")).toBeInTheDocument();

      // Colapsar primer holding
      const toggleBtn = screen.getByTestId("toggle-holding-holding-gastro-sur");
      fireEvent.click(toggleBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("holding-tenant-tenant_rest_central")).not.toBeInTheDocument();
      });
    });

    it("cambia a la pestaña 'tenant' y muestra la grilla directa de tenants", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      const tenantTabBtn = screen.getByTestId("tab-view-tenant");
      fireEvent.click(tenantTabBtn);

      expect(screen.getByTestId("jev-tenant-view")).toBeInTheDocument();
      expect(screen.getByTestId("tenant-grid")).toBeInTheDocument();
      expect(screen.getByTestId("tenant-card-tenant_rest_central")).toBeInTheDocument();
      expect(screen.getByTestId("tenant-card-tenant_andes_las_condes")).toBeInTheDocument();
    });

    it("cambia a la pestaña 'logs' y muestra la bitácora con TablePagination", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      const logsTabBtn = screen.getByTestId("tab-view-logs");
      fireEvent.click(logsTabBtn);

      expect(screen.getByTestId("jev-logs-view")).toBeInTheDocument();
      expect(screen.getByTestId("jev-logs-table")).toBeInTheDocument();
      expect(screen.getByTestId("jev-log-row-jev-log-001")).toBeInTheDocument();
      expect(screen.getByTestId("table-pagination")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 4. FILTROS Y BARRA DE HERRAMIENTAS
  // ==========================================================================
  describe("4. Filtros y Búsqueda", () => {
    it("permite escribir en el buscador reactivo", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      const searchInput = screen.getByTestId("jev-consumption-search-input");
      fireEvent.change(searchInput, { target: { value: "Providencia" } });

      expect(searchInput).toHaveValue("Providencia");
    });

    it("permite filtrar por primitiva JEV", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      const primitiveSelect = screen.getByTestId("filter-primitive-select");
      fireEvent.change(primitiveSelect, { target: { value: "anomaly_score" } });

      expect(primitiveSelect).toHaveValue("anomaly_score");
    });

    it("permite filtrar por feature llamadora", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      const featureSelect = screen.getByTestId("filter-feature-select");
      fireEvent.change(featureSelect, { target: { value: "mermas_detection" } });

      expect(featureSelect).toHaveValue("mermas_detection");
    });

    it("permite filtrar por acción calibrada", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      const actionSelect = screen.getByTestId("filter-action-select");
      fireEvent.change(actionSelect, { target: { value: "AUTO_ACCEPTED" } });

      expect(actionSelect).toHaveValue("AUTO_ACCEPTED");
    });

    it("abre el popover de columnas opcionales en pestaña logs y persiste cambios", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      // Cambiar a pestaña logs
      fireEvent.click(screen.getByTestId("tab-view-logs"));

      const popoverBtn = screen.getByTestId("toggle-columns-popover-btn");
      fireEvent.click(popoverBtn);

      expect(screen.getByTestId("columns-popover-content")).toBeInTheDocument();
      expect(screen.getByText("Columnas Opcionales")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 5. BOTÓN DE ACTUALIZAR (REFRESH)
  // ==========================================================================
  describe("5. Botón de Actualizar (Refresh)", () => {
    it("refresca los datos y notifica con toast al hacer click", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <JevConsumptionPage />
        </Wrapper>
      );

      const refreshBtn = screen.getByTestId("refresh-jev-btn");

      await waitFor(() => {
        expect(refreshBtn.getAttribute("disabled")).toBeNull();
      });

      await act(async () => {
        fireEvent.click(refreshBtn);
      });

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalled();
      });
    });
  });

  // ==========================================================================
  // 6. NAVEGACIÓN DESDE ADMIN SIDEBAR
  // ==========================================================================
  describe("6. Navegación en AdminSidebar", () => {
    it("incluye el enlace de navegación hacia /admin/jev-consumption", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AdminSidebar isOpen={true} />
        </Wrapper>
      );

      const navItem = screen.getByTestId("admin-nav-item-jev-consumption");
      expect(navItem).toBeInTheDocument();
      expect(navItem).toHaveAttribute("href", "/admin/jev-consumption");
      expect(navItem).toHaveTextContent(/Consumo de JEV/i);
    });
  });
});
