// oppytec-frontend/src/features/gestion/hooks/__tests__/useCombos.test.ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as httpClient from "@/shared/api/httpClient";
import { useCombos, INITIAL_COMBOS_MOCK, INITIAL_CATEGORIAS_COMBOS_MOCK } from "../useCombos";
import type { Combo } from "../../types";

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

describe("Hook Reactivo useCombos (TanStack Query v5 + WebSockets Realtime)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await new Promise((r) => setTimeout(r, 20));
  });

  it("loads default gastronomy combos mock dataset with theoretical portions availability", async () => {
    const { result } = renderHook(() => useCombos(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.combos.length).toBeGreaterThan(0);
    });

    expect(result.current.combos[0]?.nombre).toBe("Menú Ejecutivo Parrillero");
    expect(result.current.combos[0]?.disponibilidad_stock_porciones).toBe(18);
    expect(result.current.categorias.length).toBe(INITIAL_CATEGORIAS_COMBOS_MOCK.length);
  });

  it("filters combos reactively by search query and category", async () => {
    const { result } = renderHook(() => useCombos(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.combos.length).toBeGreaterThan(0);
    });

    act(() => {
      result.current.setSearchFiltro("Austral");
    });
    expect(result.current.combosFiltrados.length).toBe(1);
    expect(result.current.combosFiltrados[0]?.nombre).toContain("Austral");

    act(() => {
      result.current.setSearchFiltro("");
      result.current.setCategoriaFiltro("cat-cmb-ejecutivos");
    });
    expect(result.current.combosFiltrados.every((c) => c.categoria_combo_id === "cat-cmb-ejecutivos")).toBe(true);
  });

  it("creates a new combo via POST /api/v1/combos", async () => {
    const newCombo: Combo = {
      id: "combo-test-10",
      codigo: "CMB-TEST-10",
      nombre: "Combo Degustación Mar y Tierra",
      categoria_combo_id: "cat-cmb-degustacion",
      es_dinamico: true,
      precio_venta_neto: 28000,
      precio_venta_bruto: 33320,
      costo_total_calculado: 12500,
      costo_base: 12500,
      margen_amount: 15500,
      margen_pct: 55.35,
      food_cost_pct: 44.65,
      disponibilidad_stock_porciones: 15,
      esta_disponible: true,
    };

    const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (_path, options) => {
      if (options?.method === "POST") {
        return {
          data: newCombo as any,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      return {
        data: INITIAL_COMBOS_MOCK as any,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });

    const { result } = renderHook(() => useCombos(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.combos.length).toBeGreaterThan(0);
    });

    await act(async () => {
      const res = await result.current.createCombo({
        nombre: "Combo Degustación Mar y Tierra",
        codigo: "CMB-TEST-10",
        precio_venta_neto: 28000,
        categoria_combo_id: "cat-cmb-degustacion",
      });
      expect(res.id).toBe("combo-test-10");
    });

    expect(spyApi).toHaveBeenCalledWith(
      "/api/v1/combos",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("updates an existing combo via PUT /api/v1/combos/{id}", async () => {
    const updatedCombo: Combo = {
      ...INITIAL_COMBOS_MOCK[0]!,
      nombre: "Menú Ejecutivo Parrillero VIP",
      precio_venta_bruto: 25900,
    };

    const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (_path, options) => {
      if (options?.method === "PUT") {
        return {
          data: updatedCombo as any,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      return {
        data: INITIAL_COMBOS_MOCK as any,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });

    const { result } = renderHook(() => useCombos(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.combos.length).toBeGreaterThan(0);
    });

    await act(async () => {
      const res = await result.current.updateCombo({
        id: "combo-1",
        data: { nombre: "Menú Ejecutivo Parrillero VIP", precio_venta_bruto: 25900 },
      });
      expect(res.nombre).toBe("Menú Ejecutivo Parrillero VIP");
    });

    expect(spyApi).toHaveBeenCalledWith(
      "/api/v1/combos/combo-1",
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("deletes a combo via DELETE /api/v1/combos/{id}", async () => {
    const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (_path, options) => {
      if (options?.method === "DELETE") {
        return {
          data: undefined as any,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      return {
        data: INITIAL_COMBOS_MOCK as any,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });

    const { result } = renderHook(() => useCombos(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.combos.length).toBeGreaterThan(0);
    });

    await act(async () => {
      const res = await result.current.deleteCombo("combo-1");
      expect(res).toBe("combo-1");
    });

    expect(spyApi).toHaveBeenCalledWith(
      "/api/v1/combos/combo-1",
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("handles 'recipes_combo_updated' window event for reactive cache invalidation", async () => {
    const { result } = renderHook(() => useCombos(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.combos.length).toBeGreaterThan(0);
    });

    act(() => {
      window.dispatchEvent(new CustomEvent("recipes_combo_updated"));
    });

    await waitFor(() => {
      expect(result.current.isLoadingCombos).toBe(false);
    });
  });
});
