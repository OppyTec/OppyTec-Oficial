// oppytec-frontend/src/features/gestion/hooks/__tests__/useRecetas.test.ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as httpClient from "@/shared/api/httpClient";
import { useRecetas, INITIAL_RECETAS_MOCK, INITIAL_CATEGORIAS_RECETAS_MOCK } from "../useRecetas";
import type { Receta, DynamicCostResult } from "../../types";

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

describe("Hook Reactivo useRecetas (TanStack Query v5 + WebSockets Realtime)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await new Promise((r) => setTimeout(r, 20));
  });

  it("loads default gastronomy mock dataset when API is offline / fallback", async () => {
    const { result } = renderHook(() => useRecetas(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.recetas.length).toBeGreaterThan(0);
    });

    expect(result.current.recetas[0]?.nombre).toBe("Lomo Vetado a la Parrilla 350g");
    expect(result.current.categorias.length).toBe(INITIAL_CATEGORIAS_RECETAS_MOCK.length);
  });

  it("filters recipes reactively by tipo: todas, estaticas, dinamicas, subrecetas", async () => {
    const { result } = renderHook(() => useRecetas(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.recetasFiltradas.length).toBe(INITIAL_RECETAS_MOCK.length);
    });

    // Solo Dinámicas
    act(() => {
      result.current.setTipoFiltro("dinamicas");
    });
    expect(result.current.recetasFiltradas.every((r) => r.es_dinamica)).toBe(true);

    // Solo Estáticas
    act(() => {
      result.current.setTipoFiltro("estaticas");
    });
    expect(result.current.recetasFiltradas.every((r) => !r.es_dinamica && !r.es_subreceta)).toBe(true);

    // Solo Sub-recetas
    act(() => {
      result.current.setTipoFiltro("subrecetas");
    });
    expect(result.current.recetasFiltradas.every((r) => r.es_subreceta)).toBe(true);
  });

  it("filters recipes by search query and category", async () => {
    const { result } = renderHook(() => useRecetas(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.recetas.length).toBeGreaterThan(0);
    });

    act(() => {
      result.current.setSearchFiltro("Salmón");
    });
    expect(result.current.recetasFiltradas.length).toBe(1);
    expect(result.current.recetasFiltradas[0]?.nombre).toContain("Salmón");

    act(() => {
      result.current.setSearchFiltro("");
      result.current.setCategoriaFiltro("cat-rec-mar");
    });
    expect(result.current.recetasFiltradas.every((r) => r.categoria_receta_id === "cat-rec-mar")).toBe(true);
  });

  it("creates a new recipe via POST /api/v1/recipes mutation", async () => {
    const createdRecipe: Receta = {
      id: "rec-new-99",
      codigo: "REC-TEST-99",
      nombre: "Pollo Crispy Marinado",
      es_subreceta: false,
      es_dinamica: false,
      porciones_rendimiento: 2,
      precio_venta_neto: 12000,
      precio_venta_bruto: 14280,
      costo_total_calculado: 4500,
      costo_porcion: 2250,
      costo_peor_caso: 4500,
      costo_mejor_caso: 4500,
      margen_neto: 7500,
      margen_bruto: 9780,
      margen_pct: 62.5,
      food_cost_pct: 37.5,
    };

    const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (_path, options) => {
      if (options?.method === "POST") {
        return {
          data: createdRecipe as any,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      return {
        data: INITIAL_RECETAS_MOCK as any,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });

    const { result } = renderHook(() => useRecetas(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.recetas.length).toBeGreaterThan(0);
    });

    await act(async () => {
      const res = await result.current.createReceta({
        codigo: "REC-TEST-99",
        nombre: "Pollo Crispy Marinado",
        precio_venta_neto: 12000,
        porciones_rendimiento: 2,
      });
      expect(res.id).toBe("rec-new-99");
    });

    expect(spyApi).toHaveBeenCalledWith(
      "/api/v1/recipes",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("updates an existing recipe via PUT /api/v1/recipes/{id}", async () => {
    const updatedRecipe: Receta = {
      ...INITIAL_RECETAS_MOCK[0]!,
      nombre: "Lomo Vetado Angus Premium 400g (Actualizado)",
    };

    const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (_path, options) => {
      if (options?.method === "PUT") {
        return {
          data: updatedRecipe as any,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      return {
        data: INITIAL_RECETAS_MOCK as any,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });

    const { result } = renderHook(() => useRecetas(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.recetas.length).toBeGreaterThan(0);
    });

    await act(async () => {
      const res = await result.current.updateReceta({
        id: "rec-1",
        data: { nombre: "Lomo Vetado Angus Premium 400g (Actualizado)" },
      });
      expect(res.nombre).toBe("Lomo Vetado Angus Premium 400g (Actualizado)");
    });

    expect(spyApi).toHaveBeenCalledWith(
      "/api/v1/recipes/rec-1",
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("deletes a recipe via DELETE /api/v1/recipes/{id}", async () => {
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
        data: INITIAL_RECETAS_MOCK as any,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });

    const { result } = renderHook(() => useRecetas(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.recetas.length).toBeGreaterThan(0);
    });

    await act(async () => {
      const deletedId = await result.current.deleteReceta("rec-1");
      expect(deletedId).toBe("rec-1");
    });

    expect(spyApi).toHaveBeenCalledWith(
      "/api/v1/recipes/rec-1",
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("simulates dynamic options cost via POST /api/v1/recipes/{id}/simulate-cost", async () => {
    const simulationResult: DynamicCostResult = {
      recipe_id: 1,
      recipe_nombre: "Lomo Vetado a la Parrilla 350g",
      base_fixed_cost: 5328.95,
      options_cost: 2500,
      total_cost: 7828.95,
      portion_cost: 7828.95,
      total_surcharge: 2500,
      effective_net_price: 18382.35,
      effective_gross_price: 21400,
      margin_amount: 10553.4,
      margin_pct: 57.41,
      food_cost_pct: 42.59,
      selected_options: [
        {
          item_id: 7,
          grupo_id: 2,
          grupo_nombre: "Guarnición",
          nombre: "Risotto de Hongos Silvestres",
          cantidad: 1,
          costo_unitario: 2500,
          costo_total: 2500,
          recargo_precio: 2500,
        },
      ],
    };

    const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (path, _options) => {
      if (path.includes("simulate-cost")) {
        return {
          data: simulationResult as any,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      return {
        data: INITIAL_RECETAS_MOCK as any,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });

    const { result } = renderHook(() => useRecetas(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.recetas.length).toBeGreaterThan(0);
    });

    await act(async () => {
      const res = await result.current.simulateCost({
        recipeId: "rec-1",
        selectedOptionItemIds: [7],
      });
      expect(res.total_cost).toBe(7828.95);
      expect(res.selected_options.length).toBe(1);
    });

    expect(spyApi).toHaveBeenCalledWith(
      "/api/v1/recipes/rec-1/simulate-cost",
      expect.objectContaining({
        method: "POST",
        body: { selected_option_item_ids: [7] },
      })
    );
  });

  it("handles window 'recipes_recipe_updated' event for zero-polling invalidation", async () => {
    const { result } = renderHook(() => useRecetas(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.recetas.length).toBeGreaterThan(0);
    });

    act(() => {
      window.dispatchEvent(new CustomEvent("recipes_recipe_updated"));
    });

    await waitFor(() => {
      expect(result.current.isLoadingRecetas).toBe(false);
    });
  });
});
