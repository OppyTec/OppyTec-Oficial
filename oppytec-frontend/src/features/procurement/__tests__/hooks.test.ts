/**
 * oppytec-frontend/src/features/procurement/__tests__/hooks.test.ts
 * Pruebas unitarias completas con Vitest para hooks reactivos de Compras, Proveedores y Mermas (Fase 3).
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import {
  calculateDateRange,
  formatDateToIsoDay,
  useCompras,
  useMermaAnalytics,
  useProveedores,
} from "../hooks";
import {
  MOCK_COMPRAS,
  MOCK_MERMA_ANALYTICS,
  MOCK_MERMA_HISTORY,
  MOCK_PRODUCTOS_PROVEEDOR,
  MOCK_PROVEEDORES,
  MOCK_PROCUREMENT_DASHBOARD,
} from "../mockData";
import {
  COMPRA_DRAFT_STORAGE_KEY,
  type CompraDraft,
  type CreateOrderPayload,
  type CreateProveedorPayload,
  type ReceiveGoodsPayload,
  type RegisterIncidencePayload,
} from "../types";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// In-Memory localStorage mock para garantizar aislamiento de tests
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
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

describe("Feature Procurement - Reactive Hooks & Domain Contracts (Fase 3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. Contratos TypeScript y Mocks de Fallback
  // ==========================================================================
  describe("1. Contratos y Mocks de Dominio (types.ts & mockData.ts)", () => {
    it("valida estructura de proveedores y respeta la regla comercial 'Pollo King'", () => {
      expect(MOCK_PROVEEDORES.length).toBeGreaterThan(0);
      const prov = MOCK_PROVEEDORES[0]!;
      expect(prov.id).toBe(1);
      expect(prov.rut_tax_id).toBe("76.321.400-8");
      expect(prov.estado).toBe("ACTIVO");
      expect(prov.lead_time_dias).toBeGreaterThanOrEqual(0);

      // Catálogo contiene ítem 'Pollo King'
      const itemsProv1 = MOCK_PRODUCTOS_PROVEEDOR[1]!;
      expect(itemsProv1).toBeDefined();
      const polloKing = itemsProv1.find((p) => p.producto_nombre === "Pollo King");
      expect(polloKing).toBeDefined();
      expect(polloKing?.producto_nombre).toBe("Pollo King");
      expect(polloKing?.es_proveedor_principal).toBe(true);
    });

    it("valida estructura de compras, estados y desglose de items", () => {
      expect(MOCK_COMPRAS.length).toBeGreaterThanOrEqual(3);
      const oc1 = MOCK_COMPRAS[0]!;
      expect(oc1.numero_orden).toBe("OC-2026-0842");
      expect(oc1.estado).toBe("EN_CAMINO");
      expect(oc1.items.length).toBe(2);
      expect(oc1.items[0]!.producto_nombre).toBe("Pollo King");
      expect(oc1.moneda).toBe("CLP");
    });

    it("valida analítica de mermas con agregación por motivo y línea de tiempo", () => {
      expect(MOCK_MERMA_ANALYTICS.motivos_breakdown.length).toBeGreaterThan(0);
      expect(MOCK_MERMA_ANALYTICS.motivo_principal).toBe("Vencimiento");
      expect(MOCK_MERMA_ANALYTICS.timeline.length).toBeGreaterThan(0);
      expect(MOCK_MERMA_HISTORY.length).toBeGreaterThan(0);
      expect(MOCK_MERMA_HISTORY[0]!.motivo).toBe("Vencimiento");
    });
  });

  // ==========================================================================
  // 2. Hook useCompras
  // ==========================================================================
  describe("2. Hook useCompras", () => {
    it("carga órdenes de compra y dashboard con fallback seguro ante error de red", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Network Error"));

      const { result } = renderHook(() => useCompras(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoadingOrders).toBe(false);
      });

      expect(result.current.orders.length).toBe(MOCK_COMPRAS.length);
      expect(result.current.dashboard.proveedores_activos).toBe(
        MOCK_PROCUREMENT_DASHBOARD.proveedores_activos
      );
    });

    it("consume órdenes del backend cuando la API responde OK", async () => {
      const customOrder = {
        ...MOCK_COMPRAS[0],
        id: 99,
        numero_orden: "OC-2026-TEST",
      };

      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (path) => {
        if (path.includes("/api/v1/procurement/orders")) {
          return {
            data: [customOrder],
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          };
        }
        return {
          data: MOCK_PROCUREMENT_DASHBOARD,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      });

      const { result } = renderHook(() => useCompras(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.orders.length).toBe(1);
      });

      expect(result.current.orders[0]!.numero_orden).toBe("OC-2026-TEST");
    });

    it("filtra órdenes por texto de búsqueda (número de orden y nombre de proveedor)", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: MOCK_COMPRAS,
        traceId: "trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useCompras(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.orders.length).toBe(3);
      });

      // Filtrar por número de orden "0842"
      act(() => {
        result.current.setFilter("search", "0842");
      });

      expect(result.current.orders.length).toBe(1);
      expect(result.current.orders[0]!.numero_orden).toBe("OC-2026-0842");

      // Filtrar por nombre de proveedor "Valle Central"
      act(() => {
        result.current.setFilter("search", "Valle Central");
      });

      expect(result.current.orders.length).toBe(1);
      expect(result.current.orders[0]!.numero_orden).toBe("OC-2026-0841");

      // Limpiar filtros
      act(() => {
        result.current.resetFilters();
      });

      expect(result.current.orders.length).toBe(3);
    });

    it("persiste y recupera el borrador de orden en localStorage con auto-recuperación", () => {
      const { result } = renderHook(() => useCompras(), {
        wrapper: createWrapper(),
      });

      expect(result.current.hasDraft).toBe(false);
      expect(result.current.draftData).toBeNull();

      // Guardar un borrador
      const sampleDraft: Partial<CompraDraft> = {
        proveedor_id: 1,
        proveedor_nombre: "Distribuidora Austral Food SpA",
        bodega_destino_id: 1,
        moneda: "CLP",
        notas: "Pedido borrador para fin de semana",
        items: [
          {
            producto_id: 10,
            producto_nombre: "Pollo King",
            cantidad_solicitada: 100,
            costo_unitario_neto: 3850,
            subtotal_linea: 385000,
          },
        ],
      };

      act(() => {
        result.current.saveDraft(sampleDraft);
      });

      expect(result.current.hasDraft).toBe(true);
      expect(result.current.draftData?.proveedor_id).toBe(1);
      expect(result.current.draftData?.items[0]?.producto_nombre).toBe("Pollo King");
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        COMPRA_DRAFT_STORAGE_KEY,
        expect.any(String)
      );

      // Montar otro hook para verificar la auto-recuperación desde localStorage
      const { result: secondHook } = renderHook(() => useCompras(), {
        wrapper: createWrapper(),
      });

      expect(secondHook.current.hasDraft).toBe(true);
      expect(secondHook.current.draftData?.proveedor_nombre).toBe(
        "Distribuidora Austral Food SpA"
      );

      // Limpiar borrador
      act(() => {
        secondHook.current.clearDraft();
      });

      expect(secondHook.current.hasDraft).toBe(false);
      expect(secondHook.current.draftData).toBeNull();
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(COMPRA_DRAFT_STORAGE_KEY);
    });

    it("ejecuta createOrder exitosamente y limpia el borrador persistente", async () => {
      const createdOrder = {
        ...MOCK_COMPRAS[0],
        id: 777,
        numero_orden: "OC-2026-0999",
      };

      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (path, opts) => {
        if (opts?.method === "POST" && path.includes("/api/v1/procurement/orders")) {
          return {
            data: createdOrder,
            traceId: "trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          };
        }
        return {
          data: MOCK_COMPRAS,
          traceId: "trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      });

      const { result } = renderHook(() => useCompras(), {
        wrapper: createWrapper(),
      });

      // Crear borrador previo
      act(() => {
        result.current.saveDraft({ proveedor_id: 1, notas: "Temporal" });
      });
      expect(result.current.hasDraft).toBe(true);

      const payload: CreateOrderPayload = {
        proveedor_id: 1,
        bodega_destino_id: 1,
        items: [
          {
            producto_id: 10,
            cantidad_solicitada: 50,
            costo_unitario_neto: 3850,
          },
        ],
      };

      let resOrder;
      await act(async () => {
        resOrder = await result.current.createOrder(payload);
      });

      expect(resOrder).toEqual(createdOrder);
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("OC-2026-0999"));
      // Verifica que el borrador fue limpiado
      expect(result.current.hasDraft).toBe(false);
    });

    it("ejecuta receiveGoods, registerIncidence y cancelOrder correctamente", async () => {
      const orderReceived = {
        ...MOCK_COMPRAS[0],
        estado: "RECIBIDA_TOTAL" as const,
      };

      const incidenceCreated = {
        id: 10,
        compra_id: 1,
        compra_item_id: 1001,
        tipo_incidencia: "Dañado",
        cantidad_afectada: 5,
        monto_disputa: 19250,
        resolucion: "PENDIENTE",
        descripcion: "5 cajas de Pollo King aplastadas",
        foto_evidencia_url: null,
        created_at: new Date().toISOString(),
      };

      const orderCancelled = {
        ...MOCK_COMPRAS[0],
        estado: "CANCELADA" as const,
      };

      const apiSpy = vi.spyOn(httpClient, "apiRequest");

      const { result } = renderHook(() => useCompras(), {
        wrapper: createWrapper(),
      });

      // 1. Recepción
      apiSpy.mockResolvedValueOnce({
        data: orderReceived,
        traceId: "t1",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const receivePayload: ReceiveGoodsPayload = {
        order_id: 1,
        items: [{ producto_id: 10, cantidad_recibida: 200 }],
        notas: "Recepción completa",
      };

      await act(async () => {
        const res = await result.current.receiveGoods(receivePayload);
        expect(res.estado).toBe("RECIBIDA_TOTAL");
      });
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("recepcionada conforme"));

      // 2. Registro de Incidencia
      apiSpy.mockResolvedValueOnce({
        data: incidenceCreated,
        traceId: "t2",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const incPayload: RegisterIncidencePayload = {
        order_id: 1,
        compra_item_id: 1001,
        tipo_incidencia: "Dañado",
        cantidad_afectada: 5,
        descripcion: "5 cajas de Pollo King aplastadas",
      };

      await act(async () => {
        const resInc = await result.current.registerIncidence(incPayload);
        expect(resInc.tipo_incidencia).toBe("Dañado");
      });
      expect(toast.success).toHaveBeenCalledWith("Incidencia registrada con éxito.");

      // 3. Cancelación
      apiSpy.mockResolvedValueOnce({
        data: orderCancelled,
        traceId: "t3",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      await act(async () => {
        const resCancel = await result.current.cancelOrder({
          order_id: 1,
          motivo: "Proveedor sin stock",
        });
        expect(resCancel.estado).toBe("CANCELADA");
      });
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("cancelada"));
    });
  });

  // ==========================================================================
  // 3. Hook useProveedores
  // ==========================================================================
  describe("3. Hook useProveedores", () => {
    it("carga listado de proveedores y filtra por estado ACTIVO/INACTIVO", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: MOCK_PROVEEDORES,
        traceId: "trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useProveedores(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.proveedores.length).toBe(MOCK_PROVEEDORES.length);
      });

      // Filtrar sólo INACTIVO
      act(() => {
        result.current.setFilter("estado", "INACTIVO");
      });

      expect(result.current.proveedores.length).toBe(1);
      expect(result.current.proveedores[0]!.razon_social).toContain("Gourmet Pacific");

      // Filtrar sólo ACTIVO
      act(() => {
        result.current.setFilter("estado", "ACTIVO");
      });

      expect(result.current.proveedores.length).toBe(3);
    });

    it("soporta búsqueda predictiva con debounce de proveedores", async () => {
      vi.useFakeTimers();

      vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: MOCK_PROVEEDORES,
        traceId: "trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useProveedores(), {
        wrapper: createWrapper(),
      });

      // Cambiar búsqueda sin avanzar el tiempo
      act(() => {
        result.current.setFilter("search", "Lácteos");
      });

      expect(result.current.debouncedSearch).toBe("");

      // Avanzar timer 300ms
      act(() => {
        vi.advanceTimersByTime(300);
      });

      expect(result.current.debouncedSearch).toBe("Lácteos");
      expect(result.current.proveedores.length).toBe(1);
      expect(result.current.proveedores[0]!.razon_social).toContain("Lácteos del Sur");

      vi.useRealTimers();
    });

    it("carga catálogo de un proveedor cuando se especifica activeSupplierId", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (path) => {
        if (path.includes("/products")) {
          return {
            data: MOCK_PRODUCTOS_PROVEEDOR[1],
            traceId: "cat-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          };
        }
        return {
          data: MOCK_PROVEEDORES,
          traceId: "trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      });

      const { result } = renderHook(() => useProveedores(undefined, 1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.catalog.length).toBe(2);
      });

      expect(result.current.catalog[0]!.producto_nombre).toBe("Pollo King");
    });

    it("ejecuta createProveedor, updateProveedor, deleteProveedor y updateCatalog", async () => {
      const apiSpy = vi.spyOn(httpClient, "apiRequest");
      const { result } = renderHook(() => useProveedores(), {
        wrapper: createWrapper(),
      });

      // 1. Create
      const newProv = {
        ...MOCK_PROVEEDORES[0],
        id: 99,
        razon_social: "Nuevo Proveedor Gastronómico SpA",
      };
      apiSpy.mockResolvedValueOnce({
        data: newProv,
        traceId: "t-create",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const createPayload: CreateProveedorPayload = {
        rut_tax_id: "76.999.888-1",
        razon_social: "Nuevo Proveedor Gastronómico SpA",
        lead_time_dias: 2,
      };

      await act(async () => {
        const res = await result.current.createProveedor(createPayload);
        expect(res.id).toBe(99);
      });
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("Nuevo Proveedor"));

      // 2. Update
      const updatedProv = { ...newProv, lead_time_dias: 4 };
      apiSpy.mockResolvedValueOnce({
        data: updatedProv,
        traceId: "t-upd",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      await act(async () => {
        const res = await result.current.updateProveedor({
          id: 99,
          payload: { lead_time_dias: 4 },
        });
        expect(res.lead_time_dias).toBe(4);
      });
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("actualizado"));

      // 3. Delete
      apiSpy.mockResolvedValueOnce({
        data: { ok: true, message: "Proveedor 99 eliminado" },
        traceId: "t-del",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      await act(async () => {
        const resDel = await result.current.deleteProveedor(99);
        expect(resDel.ok).toBe(true);
      });
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("desactivado"));

      // 4. Update Catalog
      apiSpy.mockResolvedValueOnce({
        data: MOCK_PRODUCTOS_PROVEEDOR[1],
        traceId: "t-cat",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      await act(async () => {
        const resCat = await result.current.updateCatalog({
          supplier_id: 1,
          items: [
            {
              producto_id: 10,
              precio_pactado: "3950.00",
              es_proveedor_principal: true,
            },
          ],
        });
        expect(resCat.length).toBe(2);
      });
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("Catálogo de precios"));
    });
  });

  // ==========================================================================
  // 4. Hook useMermaAnalytics y Cálculo de Fechas
  // ==========================================================================
  describe("4. Hook useMermaAnalytics & Función calculateDateRange", () => {
    const fixedDate = new Date(2026, 9, 26); // 26 de Octubre de 2026

    it("calcula correctamente todos los presets de rango de fechas", () => {
      // Hoy
      const hoy = calculateDateRange("hoy", null, null, fixedDate);
      expect(hoy.date_from).toBe("2026-10-26");
      expect(hoy.date_to).toBe("2026-10-26");

      // 7 días
      const d7 = calculateDateRange("7d", null, null, fixedDate);
      expect(d7.date_from).toBe("2026-10-19");
      expect(d7.date_to).toBe("2026-10-26");

      // 30 días
      const d30 = calculateDateRange("30d", null, null, fixedDate);
      expect(d30.date_from).toBe("2026-09-26");
      expect(d30.date_to).toBe("2026-10-26");

      // Mes actual (1 de octubre a hoy)
      const mesActual = calculateDateRange("mes_actual", null, null, fixedDate);
      expect(mesActual.date_from).toBe("2026-10-01");
      expect(mesActual.date_to).toBe("2026-10-26");

      // Mes anterior (septiembre completo: 2026-09-01 a 2026-09-30)
      const mesAnterior = calculateDateRange("mes_anterior", null, null, fixedDate);
      expect(mesAnterior.date_from).toBe("2026-09-01");
      expect(mesAnterior.date_to).toBe("2026-09-30");

      // Personalizado
      const custom = calculateDateRange(
        "personalizado",
        "2026-08-01",
        "2026-08-15",
        fixedDate
      );
      expect(custom.date_from).toBe("2026-08-01");
      expect(custom.date_to).toBe("2026-08-15");
    });

    it("formatea correctamente una fecha a formato ISO Day YYYY-MM-DD", () => {
      const dt = new Date(2026, 0, 5); // 5 de enero de 2026
      expect(formatDateToIsoDay(dt)).toBe("2026-01-05");
    });

    it("carga analítica e historial de mermas con fallback resiliente ante error", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Network Error"));

      const { result } = renderHook(() => useMermaAnalytics(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoadingAnalytics).toBe(false);
      });

      expect(result.current.analytics.motivo_principal).toBe("Vencimiento");
      expect(result.current.historyItems.length).toBe(MOCK_MERMA_HISTORY.length);
      expect(result.current.historyItems[0]!.producto_nombre).toBe("Pollo King");
    });

    it("permite cambiar reactivamente entre presets y definir rangos personalizados", () => {
      const { result } = renderHook(() => useMermaAnalytics({ preset: "30d" }), {
        wrapper: createWrapper(),
      });

      expect(result.current.filters.preset).toBe("30d");

      // Cambiar a 'hoy'
      act(() => {
        result.current.setPreset("hoy");
      });
      expect(result.current.filters.preset).toBe("hoy");
      expect(result.current.filters.date_from).toBe(result.current.filters.date_to);

      // Definir rango personalizado
      act(() => {
        result.current.setCustomRange("2026-05-01", "2026-05-31");
      });
      expect(result.current.filters.preset).toBe("personalizado");
      expect(result.current.filters.date_from).toBe("2026-05-01");
      expect(result.current.filters.date_to).toBe("2026-05-31");

      // Resetear filtros
      act(() => {
        result.current.resetFilters();
      });
      expect(result.current.filters.preset).toBe("30d");
    });
  });
});
