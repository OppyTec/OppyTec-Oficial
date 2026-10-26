// oppytec-frontend/src/features/consumo/hooks/__tests__/useBuffet.test.ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as httpClient from "@/shared/api/httpClient";
import { useBuffet } from "../useBuffet";
import { MOCK_BUFFET_SESSIONS } from "../../mockData";

function createWrapper() {
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
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe("Módulo de Buffet Inteligente - useBuffet Hook & Conciliación Pax", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await new Promise((r) => setTimeout(r, 20));
  });

  // ==========================================================================
  // 1. Carga de Sesiones y Plantillas
  // ==========================================================================
  describe("Sesiones y Plantillas de Buffet", () => {
    it("loads sessions and defaults to the first active session", () => {
      const { result } = renderHook(() => useBuffet(), {
        wrapper: createWrapper(),
      });

      expect(result.current.sessions.length).toBeGreaterThan(0);
      expect(result.current.activeSession?.id).toBe(MOCK_BUFFET_SESSIONS[0]?.id);
      expect(result.current.templates.length).toBeGreaterThan(0);
    });

    it("allows selecting a specific session by id", () => {
      const { result } = renderHook(
        () => useBuffet({ initialSessionId: "buffet-ses-001" }),
        { wrapper: createWrapper() }
      );

      expect(result.current.activeSession?.id).toBe("buffet-ses-001");

      act(() => {
        result.current.setActiveSessionId("non-existent");
      });
      expect(result.current.activeSession).toBeNull();
    });
  });

  // ==========================================================================
  // 2. Conciliación Matemática y Costeo por Pax
  // ==========================================================================
  describe("Conciliación Matemática de Costos por Pax", () => {
    it("calculates cost per pax accurately: (montaje - sobrante) / pax", () => {
      const { result } = renderHook(() => useBuffet(), {
        wrapper: createWrapper(),
      });

      // Caso estándar: montaje 120.000, sobrante 30.000, 45 comensales -> (120000 - 30000) / 45 = 2000
      const costPax = result.current.calculateCostPerPax(120000, 30000, 45);
      expect(costPax).toBe(2000);

      // Si pax es 0 o negativo, devuelve 0 sin arrojar división por cero
      expect(result.current.calculateCostPerPax(10000, 2000, 0)).toBe(0);
      expect(result.current.calculateCostPerPax(10000, 2000, -5)).toBe(0);

      // Si sobrante excede montaje, no da costo negativo
      expect(result.current.calculateCostPerPax(5000, 10000, 10)).toBe(0);
    });

    it("evaluates sessionMetrics from the active buffet session", () => {
      const { result } = renderHook(() => useBuffet(), {
        wrapper: createWrapper(),
      });

      const metrics = result.current.sessionMetrics;
      expect(metrics.totalMontaje).toBe(120000);
      expect(metrics.totalSobrante).toBe(30000);
      expect(metrics.totalConsumido).toBe(90000);
      expect(metrics.costoNetoPax).toBe(2000);
    });
  });

  // ==========================================================================
  // 3. Mutaciones de Ciclo de Vida de Buffet
  // ==========================================================================
  describe("Mutaciones Transaccionales de Buffet", () => {
    it("calls startSession and updates activeSessionId", async () => {
      const apiSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockImplementation(async (path, options) => {
          if (
            path.includes("/buffet/sessions/start") &&
            options?.method === "POST"
          ) {
            return {
              data: {
                id: "buffet-ses-new",
                tipo_servicio: "ALMUERZO",
                estado: "abierto",
              } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          return {
            data: options?.fallbackData,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          } as any;
        });

      const { result } = renderHook(() => useBuffet(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.startSession({
          bodega_id: 1,
          tipo_servicio: "ALMUERZO",
          estaciones: [{ nombre: "Estación Ensaladas", orden: 1 }],
        });
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/buffet/sessions/start",
        expect.objectContaining({ method: "POST" })
      );
      expect(result.current.activeSessionId).toBe("buffet-ses-new");
    });

    it("calls updateItems on buffet session", async () => {
      const apiSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockImplementation(async (path, options) => {
          if (
            path.includes("/buffet/sessions/buffet-ses-001/items") &&
            options?.method === "PUT"
          ) {
            return {
              data: { id: "buffet-ses-001" } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          return {
            data: options?.fallbackData,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          } as any;
        });

      const { result } = renderHook(() => useBuffet(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.updateItems({
          sessionId: "buffet-ses-001",
          payload: {
            stations: [
              {
                station_id: 1,
                items: [
                  {
                    tipo_item: "producto",
                    item_id: "prod-queso-parm",
                    cantidad_montada: 3,
                    cantidad_sobrante: 0.5,
                  },
                ],
              },
            ],
          },
        });
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/buffet/sessions/buffet-ses-001/items",
        expect.objectContaining({ method: "PUT" })
      );
    });

    it("calls finalizeSession and triggers Kardex settlement", async () => {
      const apiSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockImplementation(async (path, options) => {
          if (
            path.includes("/buffet/sessions/buffet-ses-001/finalize") &&
            options?.method === "POST"
          ) {
            return {
              data: {
                id: "buffet-ses-001",
                estado: "CONCILIADO",
                costo_neto_pax: 2000,
              } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          return {
            data: options?.fallbackData,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          } as any;
        });

      const { result } = renderHook(() => useBuffet(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.finalizeSession({
          sessionId: "buffet-ses-001",
          payload: {
            pax: 50,
            leftover_reusable_value: 20000,
          },
        });
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/buffet/sessions/buffet-ses-001/finalize",
        expect.objectContaining({ method: "POST" })
      );
    });

    it("calls createTemplate successfully", async () => {
      const apiSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockImplementation(async (path, options) => {
          if (
            path.includes("/buffet/templates") &&
            options?.method === "POST"
          ) {
            return {
              data: { id: "tmpl-new", nombre: "Buffet Cena Gala" } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          return {
            data: options?.fallbackData,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          } as any;
        });

      const { result } = renderHook(() => useBuffet(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.createTemplate({
          nombre: "Buffet Cena Gala",
          estaciones_json: ["Parrilla", "Postres"],
        });
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/buffet/templates",
        expect.objectContaining({ method: "POST" })
      );
    });
  });
});
