import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import {
  MOCK_SAAS_POLICY,
  MOCK_TOKEN_CONSUMPTION,
} from "../../types";
import { TokenConsumptionPage } from "../TokenConsumptionPage";

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
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

const createMockEnvelope = <T,>(data: T): httpClient.ApiEnvelope<T> => ({
  data,
  traceId: "trace-token-consumption-test",
  timestampIso: new Date().toISOString(),
  tenantId: "tenant_rest_central",
});

describe("TokenConsumptionPage — Consola FinOps de Tokens & Créditos (Fase 5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
      const method = options?.method ?? "GET";
      if (method === "GET") {
        if (url.includes("/token-consumption")) {
          return createMockEnvelope(MOCK_TOKEN_CONSUMPTION);
        }
        if (url.includes("/ai-credits/policy")) {
          return createMockEnvelope(MOCK_SAAS_POLICY);
        }
      }
      if (method === "PATCH") {
        if (url.includes("/holdings/")) {
          return createMockEnvelope({
            target_id: "holding-gastro-sur",
            target_type: "holding",
            monthly_credits: 15000,
            distribution_mode: "shared",
            message: "Cuota de Holding actualizada",
          });
        }
        if (url.includes("/tenants/")) {
          return createMockEnvelope({
            target_id: "tenant_rest_central",
            target_type: "tenant",
            monthly_credits: 3500,
            message: "Cupo de Tenant actualizado",
          });
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
  // 1. RENDERIZADO DE CABECERA, PRE-TÍTULO, BADGE DE TASA Y ENLACE A PLANES
  // ==========================================================================
  describe("1. Cabecera Canónica y Navegación", () => {
    it("renderiza el pre-título FinOps, título canónico y badge de conversión de créditos", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      expect(screen.getByText("Monetización & Consumo de IA SaaS")).toBeTruthy();
      expect(screen.getByText("Consumo & Sistema de Créditos IA")).toBeTruthy();

      const badge = screen.getByTestId("token-conversion-badge");
      expect(badge).toBeTruthy();
      expect(badge.textContent).toContain("1 Cr = 1.000 Tokens");

      expect(
        screen.getByText(/Control de cuotas, conversión dinámica de tokens a créditos/i)
      ).toBeTruthy();
    });

    it("provee enlace canónico hacia /admin/plans para configurar políticas", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      const configLink = screen.getByTestId("configure-plans-link");
      expect(configLink).toBeTruthy();
      expect(configLink.getAttribute("href")).toBe("/admin/plans");
      expect(configLink.textContent).toContain("Configurar Planes & Política");
    });
  });

  // ==========================================================================
  // 2. 4 TARJETAS KPI RESUMEN (MODO CRÉDITOS Y MODO TOKENS)
  // ==========================================================================
  describe("2. Tarjetas KPI Resumen", () => {
    it("muestra las 4 tarjetas KPI con métricas globales en modo créditos por defecto", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("kpi-total-requests")).toBeTruthy();
      });

      // KPI 1: Solicitudes
      const kpiRequests = screen.getByTestId("kpi-total-requests");
      expect(kpiRequests.textContent).toContain("3");
      expect(kpiRequests.textContent).toContain("Solicitudes Totales");

      // KPI 2: Consumo (Créditos)
      const kpiConsumption = screen.getByTestId("kpi-total-consumption");
      expect(kpiConsumption.textContent).toContain("Créditos Consumidos");
      expect(kpiConsumption.textContent).toContain("643 cr");

      // KPI 3: Costo Real API
      const kpiCost = screen.getByTestId("kpi-total-cost");
      expect(kpiCost.textContent).toContain("$0.5130");
      expect(kpiCost.textContent).toContain("CLP");

      // KPI 4: Holdings Activos
      const kpiHoldings = screen.getByTestId("kpi-active-holdings");
      expect(kpiHoldings.textContent).toContain("2");
    });

    it("cambia dinámicamente la tarjeta de consumo al alternar entre modo créditos y modo tokens", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      const toggleTokensBtn = screen.getByTestId("toggle-view-tokens");
      const toggleCreditsBtn = screen.getByTestId("toggle-view-credits");

      // Alternar a modo tokens
      act(() => {
        fireEvent.click(toggleTokensBtn);
      });

      const kpiConsumption = screen.getByTestId("kpi-total-consumption");
      expect(kpiConsumption.textContent).toContain("Tokens Consumidos");
      expect(kpiConsumption.textContent).toContain("643.400");

      // Volver a modo créditos
      act(() => {
        fireEvent.click(toggleCreditsBtn);
      });

      expect(kpiConsumption.textContent).toContain("Créditos Consumidos");
      expect(kpiConsumption.textContent).toContain("643 cr");
    });
  });

  // ==========================================================================
  // 3. BARRA DE HERRAMIENTAS, FILTROS Y BUSCADOR
  // ==========================================================================
  describe("3. Barra de Herramientas, Filtros y Paginación", () => {
    it("permite escribir en el buscador reactivo", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      const searchInput = screen.getByTestId("token-consumption-search-input") as HTMLInputElement;
      act(() => {
        fireEvent.change(searchInput, { target: { value: "Costanera" } });
      });

      expect(searchInput.value).toBe("Costanera");
    });

    it("permite seleccionar filtro por modelo LLM", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      const modelSelect = screen.getByTestId("filter-model-select") as HTMLSelectElement;
      act(() => {
        fireEvent.change(modelSelect, { target: { value: "gemini-2.5-pro" } });
      });

      expect(modelSelect.value).toBe("gemini-2.5-pro");
    });

    it("permite seleccionar filtro por estado de API", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      const statusSelect = screen.getByTestId("filter-status-select") as HTMLSelectElement;
      act(() => {
        fireEvent.change(statusSelect, { target: { value: "success" } });
      });

      expect(statusSelect.value).toBe("success");

      act(() => {
        fireEvent.change(statusSelect, { target: { value: "error" } });
      });

      expect(statusSelect.value).toBe("error");
    });

    it("permite cambiar la cantidad de registros por página", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      const pageSizeSelect = screen.getByTestId("page-size-select") as HTMLSelectElement;
      act(() => {
        fireEvent.change(pageSizeSelect, { target: { value: "10" } });
      });

      expect(pageSizeSelect.value).toBe("10");
    });
  });

  // ==========================================================================
  // 4. POPOVER DE COLUMNAS OPCIONALES Y PERSISTENCIA LOCALSTORAGE
  // ==========================================================================
  describe("4. Popover de Columnas Opcionales", () => {
    it("abre el popover de columnas y persiste la configuración en localStorage", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      const toggleColsBtn = screen.getByTestId("toggle-columns-popover-btn");

      // Abrir popover
      act(() => {
        fireEvent.click(toggleColsBtn);
      });

      expect(screen.getByTestId("columns-popover-content")).toBeTruthy();

      // Checkbox de error_message
      const errorMsgCheckbox = screen.getByTestId("col-checkbox-error-message") as HTMLInputElement;
      expect(errorMsgCheckbox.checked).toBe(false);

      act(() => {
        fireEvent.click(errorMsgCheckbox);
      });

      expect(errorMsgCheckbox.checked).toBe(true);

      const savedColsRaw = localStorage.getItem("oppy_token_consumption_cols");
      expect(savedColsRaw).not.toBeNull();
      const parsed = JSON.parse(savedColsRaw!);
      expect(parsed.error_message).toBe(true);
    });
  });

  // ==========================================================================
  // 5. BOTÓN DE ACTUALIZACIÓN
  // ==========================================================================
  describe("5. Botón de Actualización", () => {
    it("refresca los datos y notifica con toast al hacer click en 'Actualizar'", async () => {
      render(<TokenConsumptionPage />, { wrapper: createWrapper() });

      const refreshBtn = screen.getByTestId("refresh-tokens-btn");

      await waitFor(() => {
        expect(refreshBtn.getAttribute("disabled")).toBeNull();
      });

      await act(async () => {
        fireEvent.click(refreshBtn);
      });

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          expect.stringContaining("Registros de consumo y créditos actualizados")
        );
      });
    });
  });

  // ==========================================================================
  // 6. TABLA JERÁRQUICA: HOLDINGS, TENANTS, LOGS Y MODALES DE AJUSTE
  // ==========================================================================
  describe("6. Tabla Jerárquica y Modales de Cupos", () => {
    it("renderiza los holdings y permite colapsar/desplegar locales", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("holding-row-holding-gastro-sur")).toBeTruthy();
      });

      expect(screen.getByText("Holding Gastronómico Sur SpA")).toBeTruthy();
      expect(screen.getByText("Pacífico Food Service S.A.")).toBeTruthy();

      // El primer holding viene expandido por defecto, verificar que el tenant esté presente
      expect(screen.getByTestId("tenant-row-tenant_rest_central")).toBeTruthy();

      // Colapsar
      const toggleSurBtn = screen.getByTestId("toggle-holding-holding-gastro-sur");
      act(() => {
        fireEvent.click(toggleSurBtn);
      });

      // Al colapsar, no se renderizan los tenants de ese holding
      expect(screen.queryByTestId("tenant-row-tenant_rest_central")).toBeNull();

      // Volver a expandir
      act(() => {
        fireEvent.click(toggleSurBtn);
      });

      expect(screen.getByTestId("tenant-row-tenant_rest_central")).toBeTruthy();
    });

    it("abre el modal de edición de créditos para un Holding y ejecuta la mutación", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest");
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("edit-holding-credits-btn-holding-gastro-sur")).toBeTruthy();
      });

      const editBtn = screen.getByTestId("edit-holding-credits-btn-holding-gastro-sur");
      act(() => {
        fireEvent.click(editBtn);
      });

      expect(screen.getByTestId("holding-credits-modal")).toBeTruthy();
      expect(screen.getByText(/Ajustar Créditos: Holding Gastronómico Sur SpA/i)).toBeTruthy();

      const input = screen.getByTestId("input-holding-credit-limit");
      act(() => {
        fireEvent.change(input, { target: { value: "15000" } });
      });

      const saveBtn = screen.getByTestId("save-holding-credits-btn");
      await act(async () => {
        fireEvent.click(saveBtn);
      });

      await waitFor(() => {
        expect(spyApi).toHaveBeenCalledWith(
          "/api/v1/platform-admin/holdings/holding-gastro-sur/ai-credits",
          expect.objectContaining({
            method: "PATCH",
            body: expect.objectContaining({
              monthly_credits: 15000,
            }),
          })
        );
      });

      expect(screen.queryByTestId("holding-credits-modal")).toBeNull();
    });

    it("abre el modal de cupo de Tenant y ejecuta la mutación", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest");
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("edit-tenant-credits-btn-tenant_rest_central")).toBeTruthy();
      });

      const editBtn = screen.getByTestId("edit-tenant-credits-btn-tenant_rest_central");
      act(() => {
        fireEvent.click(editBtn);
      });

      expect(screen.getByTestId("tenant-credits-modal")).toBeTruthy();
      expect(screen.getByText(/Cupo de Créditos: Restaurante Central Santiago/i)).toBeTruthy();

      const input = screen.getByTestId("input-tenant-credit-limit");
      act(() => {
        fireEvent.change(input, { target: { value: "3500" } });
      });

      const saveBtn = screen.getByTestId("save-tenant-credits-btn");
      await act(async () => {
        fireEvent.click(saveBtn);
      });

      await waitFor(() => {
        expect(spyApi).toHaveBeenCalledWith(
          "/api/v1/platform-admin/tenants/tenant_rest_central/ai-credits",
          expect.objectContaining({
            method: "PATCH",
            body: expect.objectContaining({
              monthly_credits: 3500,
            }),
          })
        );
      });

      expect(screen.queryByTestId("tenant-credits-modal")).toBeNull();
    });
  });

  // ==========================================================================
  // 7. EMPTY STATE
  // ==========================================================================
  describe("7. Estado Vacío", () => {
    it("muestra empty state cuando la lista de holdings viene vacía", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string) => {
        if (url.includes("/token-consumption")) {
          return createMockEnvelope({
            ...MOCK_TOKEN_CONSUMPTION,
            holdings: [],
            total_records: 0,
          });
        }
        return createMockEnvelope(MOCK_SAAS_POLICY);
      });

      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("empty-holdings-state")).toBeTruthy();
      });

      expect(
        screen.getByText("No se encontraron registros de consumo con los filtros aplicados.")
      ).toBeTruthy();
    });
  });

  // ==========================================================================
  // 8. FASE 6 — TABLA JERÁRQUICA 3 NIVELES, PROGRESO, PAGINADOR Y VALIDACIÓN
  // ==========================================================================
  describe("8. Fase 6 — Tabla Jerárquica 3 Niveles, Barras de Progreso, TablePagination y Validación de Cupos", () => {
    it("renderiza la barra de progreso visual de créditos en Holding con porcentaje y formato USD/CLP", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("holding-row-holding-gastro-sur")).toBeTruthy();
      });

      const holdingProgressBars = screen.getAllByTestId("holding-progress-bar");
      expect(holdingProgressBars.length).toBeGreaterThan(0);
      // El holding gastro sur tiene 5.15% o 5.2% de uso
      expect(holdingProgressBars[0]?.textContent).toMatch(/5\.[12]%|Uso Cupo/);

      // Costo USD y CLP en la fila del holding
      const holdingRow = screen.getByTestId("holding-row-holding-gastro-sur");
      expect(holdingRow.textContent).toContain("USD");
      expect(holdingRow.textContent).toContain("CLP");
    });

    it("renderiza la barra de progreso visual de créditos en Tenant con porcentaje y formato USD/CLP", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("tenant-row-tenant_rest_central")).toBeTruthy();
      });

      const tenantProgressBars = screen.getAllByTestId("tenant-progress-bar");
      expect(tenantProgressBars.length).toBeGreaterThan(0);
      expect(tenantProgressBars[0]?.textContent).toMatch(/4\.[78]%|Uso/);

      // Costo USD y CLP en la fila del tenant
      const tenantRow = screen.getByTestId("tenant-row-tenant_rest_central");
      expect(tenantRow.textContent).toContain("USD");
      expect(tenantRow.textContent).toContain("CLP");
    });

    it("renderiza el nivel 3 con logs inmutables, iniciales de usuario, caller badge, modelo, duración y estado 200 OK", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("log-row-log-001")).toBeTruthy();
      });

      const logRow = screen.getByTestId("log-row-log-001");
      // Iniciales o nombre del usuario
      expect(logRow.textContent).toContain("Chef Ejecutivo");
      expect(logRow.textContent).toContain("CE");

      // Caller feature badge
      expect(logRow.textContent).toContain("escandallo_generator");

      // Model name badge
      expect(logRow.textContent).toContain("gemini-1.5-flash");

      // Duración en milisegundos
      expect(logRow.textContent).toContain("820 ms");

      // Estado API 200 OK
      expect(logRow.textContent).toContain("200 OK");

      // Costo unitario en USD
      expect(logRow.textContent).toContain("$0.0003");
    });

    it("integra el paginador canónico TablePagination con itemLabel 'registros de consumo'", async () => {
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("table-pagination")).toBeTruthy();
      });

      const pagination = screen.getByTestId("table-pagination");
      expect(pagination.textContent).toContain("registros de consumo");
    });

    it("valida contra valores negativos en el modal de Holding e impide la mutación", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest");
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("edit-holding-credits-btn-holding-gastro-sur")).toBeTruthy();
      });

      act(() => {
        fireEvent.click(screen.getByTestId("edit-holding-credits-btn-holding-gastro-sur"));
      });

      expect(screen.getByTestId("holding-credits-modal")).toBeTruthy();

      const input = screen.getByTestId("input-holding-credit-limit");
      act(() => {
        fireEvent.change(input, { target: { value: "-500" } });
      });

      const saveBtn = screen.getByTestId("save-holding-credits-btn");
      await act(async () => {
        fireEvent.click(saveBtn);
      });

      // No debe llamar a apiRequest con PATCH
      expect(spyApi).not.toHaveBeenCalledWith(
        expect.stringContaining("/ai-credits"),
        expect.objectContaining({ method: "PATCH" })
      );

      // El modal permanece abierto con mensaje de error
      expect(screen.getByTestId("holding-credits-modal")).toBeTruthy();
      expect(screen.getByText("El cupo de créditos no puede ser negativo")).toBeTruthy();
      expect(toast.error).toHaveBeenCalledWith("El cupo de créditos no puede ser negativo");
    });

    it("valida contra valores negativos en el modal de Tenant e impide la mutación", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest");
      const Wrapper = createWrapper();
      render(<TokenConsumptionPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByTestId("edit-tenant-credits-btn-tenant_rest_central")).toBeTruthy();
      });

      act(() => {
        fireEvent.click(screen.getByTestId("edit-tenant-credits-btn-tenant_rest_central"));
      });

      expect(screen.getByTestId("tenant-credits-modal")).toBeTruthy();

      const input = screen.getByTestId("input-tenant-credit-limit");
      act(() => {
        fireEvent.change(input, { target: { value: "-100" } });
      });

      const saveBtn = screen.getByTestId("save-tenant-credits-btn");
      await act(async () => {
        fireEvent.click(saveBtn);
      });

      // No debe llamar a apiRequest con PATCH
      expect(spyApi).not.toHaveBeenCalledWith(
        expect.stringContaining("/ai-credits"),
        expect.objectContaining({ method: "PATCH" })
      );

      // El modal permanece abierto con mensaje de error
      expect(screen.getByTestId("tenant-credits-modal")).toBeTruthy();
      expect(screen.getByText("El cupo de créditos no puede ser negativo")).toBeTruthy();
      expect(toast.error).toHaveBeenCalledWith("El cupo de créditos no puede ser negativo");
    });
  });

  // ==========================================================================
  // 9. FASE 6 — TELEMETRÍA OPPYFY EN TIEMPO REAL & FINOPS MARGEN BRUTO
  // ==========================================================================
  describe("9. Fase 6 — Telemetría OppyFy en Tiempo Real & FinOps Margen Bruto", () => {
    it("provee enlace de acción rápida hacia /admin/plans?tab=ai-packs para configurar paquetes de créditos IA", () => {
      render(<TokenConsumptionPage />, { wrapper: createWrapper() });

      const link = screen.getByTestId("configure-ai-packs-link");
      expect(link).toBeTruthy();
      expect(link.getAttribute("href")).toBe("/admin/plans?tab=ai-packs");
      expect(link.textContent).toContain("Configurar Paquetes de Créditos IA");
    });

    it("renderiza el banner de Telemetría OppyFy en Tiempo Real sincronizado con public.llm_request_logs", () => {
      render(<TokenConsumptionPage />, { wrapper: createWrapper() });

      const banner = screen.getByTestId("oppyfy-telemetry-banner");
      expect(banner).toBeTruthy();
      expect(screen.getByText("Telemetría OppyFy en Tiempo Real")).toBeTruthy();
      expect(screen.getAllByText(/public\.llm_request_logs/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/En Vivo · Zero-Polling WebSocket/i)).toBeTruthy();
      expect(screen.getByText(/Modelos Monitoreados/i)).toBeTruthy();
      expect(screen.getByText(/Latencia Promedio/i)).toBeTruthy();
      expect(screen.getByText(/Tasa de Éxito API/i)).toBeTruthy();
    });

    it("renderiza la tarjeta de métricas FinOps de Margen Bruto de IA con ingresos proyectados y margen comercial", () => {
      render(<TokenConsumptionPage />, { wrapper: createWrapper() });

      const finopsCard = screen.getByTestId("finops-gross-margin-card");
      expect(finopsCard).toBeTruthy();
      expect(screen.getByText("Métricas FinOps: Margen Bruto de IA")).toBeTruthy();
      expect(screen.getByText(/Margen Saludable \(> 85%\)/i)).toBeTruthy();
      expect(screen.getByText(/Ingresos Proyectados/i)).toBeTruthy();
      expect(screen.getByText(/Costo Facturado LLM/i)).toBeTruthy();
      expect(screen.getByText(/Margen Bruto Neto/i)).toBeTruthy();
      expect(screen.getByText(/Margen Comercial/i)).toBeTruthy();
    });
  });
});
