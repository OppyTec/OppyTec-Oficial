// oppytec-frontend/src/features/gestion/hooks/__tests__/useGruposOpciones.test.ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as httpClient from "@/shared/api/httpClient";
import { useGruposOpciones, INITIAL_GRUPOS_OPCIONES_MOCK } from "../useGruposOpciones";
import type { GrupoOpciones } from "../../types";

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

describe("Hook Reactivo useGruposOpciones (Biblioteca & Creación In-Situ)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await new Promise((r) => setTimeout(r, 20));
  });

  it("loads options library with polymorphic items (products and subrecipes)", async () => {
    const { result } = renderHook(() => useGruposOpciones(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.gruposOpciones.length).toBe(INITIAL_GRUPOS_OPCIONES_MOCK.length);
    });

    const terminoGroup = result.current.getGrupoById("grp-termino");
    expect(terminoGroup).toBeDefined();
    expect(terminoGroup?.items.length).toBe(4);
    expect(terminoGroup?.items.some((i) => i.es_opcion_default)).toBe(true);
  });

  it("filters option groups by name or item name for in-situ autocomplete modal", async () => {
    const { result } = renderHook(() => useGruposOpciones(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.gruposOpciones.length).toBe(INITIAL_GRUPOS_OPCIONES_MOCK.length);
    });

    // Búsqueda por nombre de grupo
    act(() => {
      result.current.setSearch("Guarnición");
    });
    expect(result.current.gruposFiltrados.length).toBe(1);
    expect(result.current.gruposFiltrados[0]?.id).toBe("grp-guarnicion");

    // Búsqueda por ítem constituyente (Risotto)
    act(() => {
      result.current.setSearch("Risotto");
    });
    expect(result.current.gruposFiltrados.length).toBe(1);
    expect(result.current.gruposFiltrados[0]?.id).toBe("grp-guarnicion");
  });

  it("creates a new option group in-situ via POST /api/v1/recipes/option-groups", async () => {
    const newGroup: GrupoOpciones = {
      id: "grp-salsas-extra",
      nombre: "Salsas Adicionales",
      descripcion: "Selección opcional de salsas gourmet",
      seleccion_minima: 0,
      seleccion_maxima: 3,
      min_selecciones: 0,
      max_selecciones: 3,
      permite_repetir: true,
      items: [
        {
          id: "goi-s1",
          nombre: "Salsa BBQ Ahumada",
          target_type: "producto",
          cantidad: 1,
          recargo_precio: 800,
          orden: 1,
        },
      ],
    };

    const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (_path, options) => {
      if (options?.method === "POST") {
        return {
          data: newGroup as any,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      return {
        data: INITIAL_GRUPOS_OPCIONES_MOCK as any,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });

    const { result } = renderHook(() => useGruposOpciones(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.gruposOpciones.length).toBeGreaterThan(0);
    });

    await act(async () => {
      const res = await result.current.createGrupoOpciones({
        nombre: "Salsas Adicionales",
        seleccion_minima: 0,
        seleccion_maxima: 3,
        permite_repetir: true,
      });
      expect(res.id).toBe("grp-salsas-extra");
    });

    expect(spyApi).toHaveBeenCalledWith(
      "/api/v1/recipes/option-groups",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("updates an option group via PUT /api/v1/recipes/option-groups/{id}", async () => {
    const updatedGroup: GrupoOpciones = {
      ...INITIAL_GRUPOS_OPCIONES_MOCK[0]!,
      nombre: "Punto de Cocción de Carnes Rojas",
    };

    const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (_path, options) => {
      if (options?.method === "PUT") {
        return {
          data: updatedGroup as any,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      return {
        data: INITIAL_GRUPOS_OPCIONES_MOCK as any,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });

    const { result } = renderHook(() => useGruposOpciones(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.gruposOpciones.length).toBeGreaterThan(0);
    });

    await act(async () => {
      const res = await result.current.updateGrupoOpciones({
        id: "grp-termino",
        data: { nombre: "Punto de Cocción de Carnes Rojas" },
      });
      expect(res.nombre).toBe("Punto de Cocción de Carnes Rojas");
    });

    expect(spyApi).toHaveBeenCalledWith(
      "/api/v1/recipes/option-groups/grp-termino",
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("deletes an option group via DELETE /api/v1/recipes/option-groups/{id}", async () => {
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
        data: INITIAL_GRUPOS_OPCIONES_MOCK as any,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });

    const { result } = renderHook(() => useGruposOpciones(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.gruposOpciones.length).toBeGreaterThan(0);
    });

    await act(async () => {
      const res = await result.current.deleteGrupoOpciones("grp-termino");
      expect(res).toBe("grp-termino");
    });

    expect(spyApi).toHaveBeenCalledWith(
      "/api/v1/recipes/option-groups/grp-termino",
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("invalidates cache on 'recipes_options_updated' window event", async () => {
    const { result } = renderHook(() => useGruposOpciones(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.gruposOpciones.length).toBeGreaterThan(0);
    });

    act(() => {
      window.dispatchEvent(new CustomEvent("recipes_options_updated"));
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });
});
