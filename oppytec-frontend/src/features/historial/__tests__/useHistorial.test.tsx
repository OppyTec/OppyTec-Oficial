// oppytec-frontend/src/features/historial/__tests__/useHistorial.test.tsx
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as httpClient from "@/shared/api/httpClient";
import { useHistorial } from "../useHistorial";
import type {
  RegistroMovimiento,
  PaginatedKardexHistoryResponse,
} from "../types";
import {
  MOCK_HISTORIAL_PRODUCTS,
  MOCK_HISTORIAL_REGISTROS,
} from "../mockData";

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

describe("Módulo Historial y Auditoría Kardex - Hook useHistorial", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
    window.history.pushState({}, "", "/historial");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    sessionStorage.clear();
    localStorage.clear();
    window.history.pushState({}, "", "/historial");
  });

  // ==========================================================================
  // 1. Carga Inicial, Resiliencia y Fallback Seguro (Cero Pantallas en Blanco)
  // ==========================================================================
  describe("Carga Inicial y Resiliencia Offline", () => {
    it("carga datos fallback seguros sin romper la UI cuando la API falla", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Network Error"));

      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.registros.length).toBeGreaterThan(0);
      expect(result.current.filtered.length).toBeGreaterThan(0);
      expect(result.current.productos.length).toBe(MOCK_HISTORIAL_PRODUCTS.length);
      expect(result.current.pagination.page).toBe(1);
      expect(result.current.pagination.limit).toBe(50);
      expect(result.current.pagination.total).toBe(MOCK_HISTORIAL_REGISTROS.length);
    });

    it("consume exitosamente el endpoint paginado /api/v1/inventory/history/paginated", async () => {
      const mockApiItems: RegistroMovimiento[] = [
        {
          id: 999,
          producto_id: 1,
          cantidad: 10,
          tipo_movimiento: "entrada",
          motivo_merma: null,
          usuario_id: 5,
          created_at: "2026-10-25T10:00:00Z",
          bodega_id: 1,
          descripcion_merma: null,
          fecha_recuento: "2026-10-25",
          user_display_name: "Auditor Senior",
          nombre_producto: "Lomo Vetado Angus Premium",
          nombre_bodega: "Cámara de Frío Principal",
          unidad_medida: "kg",
          costo_unitario_ppp: 14200,
          costo_total_movimiento: 142000,
          saldo_resultante: 45,
          delta_before: 35,
          delta_after: 45,
        },
      ];

      const mockResponse: PaginatedKardexHistoryResponse = {
        total: 1,
        skip: 0,
        limit: 50,
        page: 1,
        total_pages: 1,
        items: mockApiItems,
      };

      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (path) => {
        if (path.includes("/api/v1/inventory/history/paginated")) {
          return {
            data: mockResponse,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          };
        }
        if (path.includes("/api/v1/catalog/products")) {
          return {
            data: MOCK_HISTORIAL_PRODUCTS,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          };
        }
        return {
          data: {} as unknown,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        } as never;
      });

      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.registros.length).toBe(1);
      expect(result.current.registros[0]?.user_display_name).toBe("Auditor Senior");
      expect(result.current.pagination.total).toBe(1);
    });
  });

  // ==========================================================================
  // 2. Soporte para Deep Linking por URL (?search= y ?producto_id=)
  // ==========================================================================
  describe("Deep Linking por URL", () => {
    it("resuelve ?search=<nombre_producto> seteando filtroProducto al id correspondiente", async () => {
      window.history.pushState({}, "", "/historial?search=Salm%C3%B3n");

      vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: MOCK_HISTORIAL_PRODUCTS,
        traceId: "trace-id",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant-id",
      });

      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        // En MOCK_HISTORIAL_PRODUCTS el Salmón tiene id: 2
        expect(result.current.filtros.filtroProducto).toBe("2");
      });
    });

    it("resuelve ?producto_id=<id> seteando directamente filtroProducto", async () => {
      window.history.pushState({}, "", "/historial?producto_id=4");

      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.filtros.filtroProducto).toBe("4");
      });
    });
  });

  // ==========================================================================
  // 3. Cálculo de Deltas Before / After (computeBeforeAfter)
  // ==========================================================================
  describe("computeBeforeAfter", () => {
    it("utiliza delta_before y delta_after retornados por el backend prioritariamente", () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      const record: RegistroMovimiento = {
        id: 1,
        producto_id: 1,
        cantidad: 15,
        tipo_movimiento: "conteo",
        motivo_merma: null,
        usuario_id: 1,
        created_at: "2026-10-25T14:30:00Z",
        bodega_id: 1,
        descripcion_merma: null,
        fecha_recuento: "2026-10-25",
        delta_before: 20,
        delta_after: 35,
      };

      const delta = result.current.computeBeforeAfter(record);
      expect(delta).toEqual({ before: 20, after: 35 });
    });

    it("calcula delta fallback seguro para conteos cuando delta_before es null", () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      const record: RegistroMovimiento = {
        id: 2,
        producto_id: 1,
        cantidad: 10,
        tipo_movimiento: "conteo",
        motivo_merma: null,
        usuario_id: 1,
        created_at: "2026-10-25T14:30:00Z",
        bodega_id: 1,
        descripcion_merma: null,
        fecha_recuento: "2026-10-25",
        saldo_resultante: 40,
        delta_before: null,
        delta_after: null,
      };

      const delta = result.current.computeBeforeAfter(record);
      expect(delta).toEqual({ before: 30, after: 40 });
    });

    it("calcula delta fallback seguro para ajustes cuando delta_before es null", () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      const record: RegistroMovimiento = {
        id: 3,
        producto_id: 1,
        cantidad: -5,
        tipo_movimiento: "ajuste",
        motivo_merma: null,
        usuario_id: 1,
        created_at: "2026-10-25T14:30:00Z",
        bodega_id: 1,
        descripcion_merma: null,
        fecha_recuento: "2026-10-25",
        saldo_resultante: 35,
        delta_before: null,
        delta_after: null,
      };

      const delta = result.current.computeBeforeAfter(record);
      expect(delta).toEqual({ before: 40, after: 35 });
    });

    it("retorna null para movimientos que no son conteo ni ajuste sin deltas explícitos", () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      const record: RegistroMovimiento = {
        id: 4,
        producto_id: 1,
        cantidad: 10,
        tipo_movimiento: "compra",
        motivo_merma: null,
        usuario_id: 1,
        created_at: "2026-10-25T14:30:00Z",
        bodega_id: 1,
        descripcion_merma: null,
        fecha_recuento: "2026-10-25",
        saldo_resultante: 50,
      };

      const delta = result.current.computeBeforeAfter(record);
      expect(delta).toBeNull();
    });
  });

  // ==========================================================================
  // 4. Manejo de Filtros y Paginación Server-Side
  // ==========================================================================
  describe("Filtros y Paginación", () => {
    it("filtra por producto y restablece la página a 1", async () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      act(() => {
        result.current.pagination.setPage(3);
      });
      expect(result.current.pagination.page).toBe(3);

      act(() => {
        result.current.filtros.setFiltroProducto("1");
      });

      expect(result.current.filtros.filtroProducto).toBe("1");
      expect(result.current.pagination.page).toBe(1);
    });

    it("filtra por tipo de movimiento", async () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      act(() => {
        result.current.filtros.setFiltroTipo("merma");
      });

      expect(result.current.filtros.filtroTipo).toBe("merma");
      const everyMerma = result.current.filtered.every(
        (r) => r.tipo_movimiento.toLowerCase() === "merma"
      );
      expect(everyMerma).toBe(true);
    });

    it("filtra por usuario persistiendo en sessionStorage", async () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.filtros.setFiltroUsuario("Ana");
      });

      expect(result.current.filtros.filtroUsuario).toBe("Ana");
      expect(sessionStorage.getItem("search_historial_usuario")).toBe("Ana");
    });

    it("filtra por rango de fechas", async () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      act(() => {
        result.current.filtros.setFechaDesde(new Date("2026-10-25T00:00:00"));
        result.current.filtros.setFechaHasta(new Date("2026-10-25T23:59:59"));
      });

      expect(result.current.filtros.fechaDesde).toBeDefined();
      expect(result.current.filtros.fechaHasta).toBeDefined();
      expect(result.current.filtered.length).toBeGreaterThan(0);
      expect(
        result.current.filtered.every((r) => r.fecha_recuento === "2026-10-25")
      ).toBe(true);
    });

    it("clearFilters restablece todos los criterios de filtro y la página", async () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.filtros.setFiltroProducto("1");
        result.current.filtros.setFiltroTipo("conteo");
        result.current.filtros.setFiltroUsuario("Carlos");
        result.current.filtros.setFechaDesde(new Date());
        result.current.pagination.setPage(2);
      });

      act(() => {
        result.current.filtros.clearFilters();
      });

      expect(result.current.filtros.filtroProducto).toBe("all");
      expect(result.current.filtros.filtroTipo).toBe("all");
      expect(result.current.filtros.filtroUsuario).toBe("");
      expect(result.current.filtros.fechaDesde).toBeUndefined();
      expect(result.current.filtros.fechaHasta).toBeUndefined();
      expect(result.current.pagination.page).toBe(1);
    });
  });

  // ==========================================================================
  // 5. Utilidades y Helpers
  // ==========================================================================
  describe("Utilidades prodName, prodUnit y tipoLabel", () => {
    it("prodName y prodUnit resuelven nombres y unidades correctamente", async () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.productos.length).toBeGreaterThan(0);
      });

      expect(result.current.prodName(1)).toBe("Lomo Vetado Angus Premium");
      expect(result.current.prodUnit(1)).toBe("kg");
      expect(result.current.prodName(999)).toBe("—");
      expect(result.current.prodUnit(999)).toBe("");
    });

    it("tipoLabel formatea canónicamente los tipos de movimiento", () => {
      const { result } = renderHook(() => useHistorial(), {
        wrapper: createWrapper(),
      });

      expect(result.current.tipoLabel("conteo")).toBe("Conteo");
      expect(result.current.tipoLabel("consumo")).toBe("Consumo");
      expect(result.current.tipoLabel("merma")).toBe("Merma");
      expect(result.current.tipoLabel("ajuste")).toBe("Ajuste");
      expect(result.current.tipoLabel("transferencia")).toBe("Transferencia");
      expect(result.current.tipoLabel("compra")).toBe("Compra");
      expect(result.current.tipoLabel("entrada")).toBe("Entrada");
      expect(result.current.tipoLabel("salida")).toBe("Salida");
      expect(result.current.tipoLabel("reversion")).toBe("Reversión");
      expect(result.current.tipoLabel("redo")).toBe("Rehacer");
      expect(result.current.tipoLabel("ajuste_auditoria")).toBe("Ajuste Auditoría");
    });
  });

  // ==========================================================================
  // 6. Sincronización Reactiva WebSocket (Zero HTTP Polling)
  // ==========================================================================
  describe("Sincronización Reactiva WebSocket", () => {
    it("invalida la query de historial ante evento local inventory_stock_updated", async () => {
      const queryClient = new QueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      renderHook(() => useHistorial(), { wrapper });

      act(() => {
        window.dispatchEvent(new CustomEvent("inventory_stock_updated"));
      });

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["inventory", "history"],
      });
    });
  });
});
