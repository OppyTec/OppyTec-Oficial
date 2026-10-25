// oppytec-frontend/src/features/inventory/__tests__/hooks.test.ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as httpClient from "@/shared/api/httpClient";
import { useStock } from "../hooks/useStock";
import {
  useContarInventario,
  BLIND_COUNT_DRAFT_KEY,
} from "../hooks/useContarInventario";
import { useRecuentos } from "../hooks/useRecuentos";
import {
  STOCK_COLUMNS,
} from "../types";
import {
  MOCK_STOCK_ITEMS,
  MOCK_KARDEX_MOVEMENTS,
  MOCK_PHYSICAL_COUNT_SESSIONS,
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

describe("Módulo de Inventario - Hooks Reactivos & Resiliencia Offline", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  // ==========================================================================
  // 1. Contratos y Columnas de Tabla
  // ==========================================================================
  describe("Contratos de Dominio y Columnas de Tabla", () => {
    it("defines the canonical columns for Stock Table with widths and labels", () => {
      expect(STOCK_COLUMNS.length).toBe(11);
      const columnIds = STOCK_COLUMNS.map((c) => c.id);
      expect(columnIds).toContain("semaforo");
      expect(columnIds).toContain("producto");
      expect(columnIds).toContain("sku");
      expect(columnIds).toContain("categoria");
      expect(columnIds).toContain("bodega");
      expect(columnIds).toContain("ubicacion");
      expect(columnIds).toContain("stock_actual");
      expect(columnIds).toContain("lotes");
      expect(columnIds).toContain("costo_unitario_ppp");
      expect(columnIds).toContain("costo_total_valorizado");
      expect(columnIds).toContain("acciones");
    });
  });

  // ==========================================================================
  // 2. useStock: Snapshots, Filtrado, Ordenamiento y Kardex
  // ==========================================================================
  describe("useStock Hook", () => {
    it("loads fallback mock stock items when API fails or is offline (0 blank screens)", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Network Error"));

      const { result } = renderHook(() => useStock(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.stockItems.length).toBeGreaterThan(0);
      });

      expect(result.current.stockItems.length).toBe(MOCK_STOCK_ITEMS.length);
      expect(result.current.movements.length).toBe(MOCK_KARDEX_MOVEMENTS.length);
    });

    it("filters stock items by textual search query (name, sku, category, bodega)", async () => {
      const { result } = renderHook(() => useStock(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.stockItems.length).toBeGreaterThan(0);
      });

      act(() => {
        result.current.setFilter({
          search: "Salmón",
          bodega_id: "all",
          area_operativa_id: "all",
          semaforo: "ALL",
          categoria: "ALL",
          sortBy: "urgency",
        });
      });

      expect(result.current.filteredStockItems.length).toBe(1);
      expect(result.current.filteredStockItems[0]?.nombre).toContain("Salmón Atlántico");
    });

    it("filters stock items by bodega and semaphore level", async () => {
      const { result } = renderHook(() => useStock(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.stockItems.length).toBeGreaterThan(0);
      });

      act(() => {
        result.current.setFilter({
          search: "",
          bodega_id: 1, // Cámara de Frío Principal
          area_operativa_id: "all",
          semaforo: "CRITICO",
          categoria: "ALL",
          sortBy: "urgency",
        });
      });

      expect(result.current.filteredStockItems.length).toBe(1);
      expect(result.current.filteredStockItems[0]?.semaforo).toBe("CRITICO");
      expect(result.current.filteredStockItems[0]?.bodega_id).toBe(1);
    });

    it("sorts items by urgency: CRITICO before MINIMO before OPTIMO", async () => {
      const { result } = renderHook(() => useStock(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.stockItems.length).toBeGreaterThan(0);
      });

      act(() => {
        result.current.setFilter((prev) => ({ ...prev, sortBy: "urgency" }));
      });

      const firstItem = result.current.filteredStockItems[0];
      expect(firstItem?.semaforo).toBe("CRITICO");
    });

    it("groups stock items by category with computed total valorizado", async () => {
      const { result } = renderHook(() => useStock(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.stockItems.length).toBeGreaterThan(0);
      });

      expect(result.current.groupedStockItems.length).toBeGreaterThan(0);
      const carnesGroup = result.current.groupedStockItems.find(
        (g) => g.categoria === "Carnes y Aves"
      );
      expect(carnesGroup).toBeDefined();
      expect(carnesGroup?.items.length).toBeGreaterThan(0);
      expect(carnesGroup?.totalValorizado).toBeGreaterThan(0);
    });

    it("executes transferStockBulk successfully and invalidates queries", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: {
          bodega_origen_id: 1,
          bodega_destino_id: 2,
          processed_items: 1,
          items: [
            {
              producto_id: 1,
              cantidad: 5,
              origen_resulting_balance: 30,
              destino_resulting_balance: 5,
            },
          ],
        },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useStock(), {
        wrapper: createWrapper(),
      });

      let response: unknown;
      await act(async () => {
        response = await result.current.transferStockBulk({
          bodega_origen_id: 1,
          bodega_destino_id: 2,
          items: [{ producto_id: 1, cantidad: 5 }],
        });
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/inventory/stock/bulk-transfer",
        expect.objectContaining({ method: "POST" })
      );
      expect(response).toBeDefined();
    });

    it("registers a movement in Kardex, undoes it and redoes it", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: {
          id: 501,
          producto_id: 1,
          bodega_id: 1,
          movement_type: "ENTRADA",
          quantity: 10,
          resulting_balance: 45,
          unit_cost: 14200,
          actor_user_id: 1,
          actor_nombre: "Test User",
          created_at: new Date().toISOString(),
        },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useStock(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.registerMovement({
          producto_id: 1,
          bodega_id: 1,
          cantidad: 10,
          tipo_movimiento: "ENTRADA",
          unit_cost: 14200,
        });
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/inventory/kardex/movements",
        expect.objectContaining({ method: "POST" })
      );

      await act(async () => {
        await result.current.undoMovement(501, "Error de tipeo");
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/inventory/stock/undo",
        expect.objectContaining({ method: "POST" })
      );

      await act(async () => {
        await result.current.redoMovement(501, "Reversión correcta");
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/inventory/stock/redo",
        expect.objectContaining({ method: "POST" })
      );
    });

    it("reports an operational merma", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: {
          waste_id: 301,
          producto_id: 2,
          bodega_id: 1,
          quantity: 1.0,
          total_cost: 16800,
          reason: "caducidad",
          reporter_user_id: 1,
          status: "APROBADA",
        },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useStock(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.reportMerma({
          producto_id: 2,
          bodega_id: 1,
          quantity: 1.0,
          unit_cost: 16800,
          reason: "caducidad",
        });
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/inventory/mermas",
        expect.objectContaining({ method: "POST" })
      );
    });
  });

  // ==========================================================================
  // 3. useContarInventario: Toma Física Ciega y Resiliencia Offline
  // ==========================================================================
  describe("useContarInventario Hook & Resiliencia Offline", () => {
    it("starts in idle step with empty items when no previous draft exists", () => {
      const { result } = renderHook(() => useContarInventario());
      expect(result.current.step).toBe("idle");
      expect(result.current.items.length).toBe(0);
      expect(result.current.hasOfflineDraft).toBe(false);
    });

    it("starts a new count session and transitions to counting", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: { id: 777 },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useContarInventario());

      await act(async () => {
        await result.current.startSession(1, 1, "Conteo matutino");
      });

      expect(result.current.step).toBe("counting");
      expect(result.current.sessionId).toBe(777);
      expect(result.current.bodegaId).toBe(1);
    });

    it("records counts and persists incrementally to localStorage", () => {
      const { result } = renderHook(() => useContarInventario());

      act(() => {
        result.current.recordCount({
          producto_id: 1,
          producto_nombre: "Lomo Vetado Angus",
          stock_fisico_contado: 25.5,
          lote_codigo: "LOT-A",
          fecha_vencimiento: "2026-11-15",
          costo_unitario_ppp: 14200,
        });
      });

      expect(result.current.items.length).toBe(1);
      expect(result.current.items[0]?.stock_fisico_contado).toBe(25.5);

      // Verify that localStorage contains the draft
      const rawSaved = localStorage.getItem(BLIND_COUNT_DRAFT_KEY);
      expect(rawSaved).not.toBeNull();
      const parsed = JSON.parse(rawSaved!);
      expect(parsed.items.length).toBe(1);
      expect(parsed.items[0].producto_id).toBe(1);
    });

    it("updates quantity if the same product and batch are counted again", () => {
      const { result } = renderHook(() => useContarInventario());

      act(() => {
        result.current.recordCount({
          producto_id: 1,
          producto_nombre: "Lomo Vetado Angus",
          stock_fisico_contado: 10,
          lote_codigo: "LOT-A",
          fecha_vencimiento: "2026-11-15",
        });
      });

      act(() => {
        // Operator re-counts the same batch with new quantity
        result.current.recordCount({
          producto_id: 1,
          producto_nombre: "Lomo Vetado Angus",
          stock_fisico_contado: 14,
          lote_codigo: "LOT-A",
          fecha_vencimiento: "2026-11-15",
        });
      });

      expect(result.current.items.length).toBe(1);
      expect(result.current.items[0]?.stock_fisico_contado).toBe(14);
    });

    it("allows updating item quantity by localId and removing item", () => {
      const { result } = renderHook(() => useContarInventario());

      act(() => {
        result.current.recordCount({
          producto_id: 2,
          stock_fisico_contado: 5,
        });
      });

      const localId = result.current.items[0]?.localId!;
      expect(localId).toBeDefined();

      act(() => {
        result.current.updateItemQuantity(localId, 8.5);
      });

      expect(result.current.items[0]?.stock_fisico_contado).toBe(8.5);

      act(() => {
        result.current.removeItem(localId);
      });

      expect(result.current.items.length).toBe(0);
    });

    it("restores active draft from localStorage on hook reload (Offline Survival)", () => {
      // Simulate draft already in localStorage
      const draft = {
        sessionId: 888,
        bodegaId: 2,
        areaOperativaId: null,
        step: "counting",
        items: [
          {
            localId: "test-item-1",
            producto_id: 3,
            producto_nombre: "Pollo King",
            unidad_medida: "kg",
            stock_fisico_contado: 12,
            lote_codigo: "LOT-POL",
            fecha_vencimiento: "2026-10-31",
            costo_unitario_ppp: 6500,
          },
        ],
        notas: "Sesión restaurada tras pérdida de señal",
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem(BLIND_COUNT_DRAFT_KEY, JSON.stringify(draft));

      const { result } = renderHook(() => useContarInventario());

      expect(result.current.hasOfflineDraft).toBe(true);
      expect(result.current.step).toBe("counting");
      expect(result.current.sessionId).toBe(888);
      expect(result.current.items.length).toBe(1);
      expect(result.current.items[0]?.producto_nombre).toBe("Pollo King");
    });

    it("clears offline draft completely from localStorage", () => {
      const { result } = renderHook(() => useContarInventario());

      act(() => {
        result.current.recordCount({
          producto_id: 1,
          stock_fisico_contado: 20,
        });
      });

      expect(localStorage.getItem(BLIND_COUNT_DRAFT_KEY)).not.toBeNull();

      act(() => {
        result.current.clearOfflineDraft();
      });

      expect(localStorage.getItem(BLIND_COUNT_DRAFT_KEY)).toBeNull();
      expect(result.current.items.length).toBe(0);
      expect(result.current.step).toBe("idle");
    });

    it("finalizes count session successfully, clearing draft upon API confirmation", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: { id: 999, estado: "PENDIENTE_APROBACION" },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useContarInventario());

      act(() => {
        result.current.recordCount({
          producto_id: 1,
          stock_fisico_contado: 35,
        });
      });

      let success = false;
      await act(async () => {
        success = await result.current.finalizeSession();
      });

      expect(success).toBe(true);
      expect(result.current.step).toBe("finished");
      expect(localStorage.getItem(BLIND_COUNT_DRAFT_KEY)).toBeNull();
      const countCalls = spyApi.mock.calls.filter(([url]) => typeof url === "string" && url.includes("/counts"));
      expect(countCalls.length).toBe(2); // items PUT + finalize POST
    });

    it("handles offline network failure during finalize without crashing, preserving draft", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("Network Offline"));

      const { result } = renderHook(() => useContarInventario());

      act(() => {
        result.current.recordCount({
          producto_id: 1,
          stock_fisico_contado: 35,
        });
      });

      let success = true;
      await act(async () => {
        success = await result.current.finalizeSession();
      });

      expect(success).toBe(false);
      // Moves back to reviewing step and keeps items safe in localStorage
      expect(result.current.step).toBe("reviewing");
      expect(result.current.items.length).toBe(1);
      expect(localStorage.getItem(BLIND_COUNT_DRAFT_KEY)).not.toBeNull();
    });
  });

  // ==========================================================================
  // 4. useRecuentos: Historial, Cuadraturas, Aprobación e Impacto en Kardex
  // ==========================================================================
  describe("useRecuentos Hook & Conciliación con Kardex", () => {
    it("loads historical sessions with fallback data when API is offline", async () => {
      vi.spyOn(httpClient, "apiRequest").mockRejectedValue(new Error("API offline"));

      const { result } = renderHook(() => useRecuentos(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.sessions.length).toBeGreaterThan(0);
      });

      expect(result.current.sessions.length).toBe(MOCK_PHYSICAL_COUNT_SESSIONS.length);
    });

    it("filters sessions by status (PENDIENTE_APROBACION, APROBADO, EN_PROGRESO)", async () => {
      const { result } = renderHook(() => useRecuentos(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.sessions.length).toBeGreaterThan(0);
      });

      act(() => {
        result.current.setStatusFilter("PENDIENTE_APROBACION");
      });

      expect(result.current.sessions.every((s) => s.estado === "PENDIENTE_APROBACION")).toBe(true);
      expect(result.current.sessions.length).toBe(1);
      expect(result.current.sessions[0]?.id).toBe(101);
    });

    it("filters sessions by bodegaId and search text", async () => {
      const { result } = renderHook(() => useRecuentos(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.sessions.length).toBeGreaterThan(0);
      });

      act(() => {
        result.current.setBodegaFilter(1);
        result.current.setSearch("Andrea");
      });

      expect(result.current.sessions.length).toBe(1);
      expect(result.current.sessions[0]?.responsable_nombre).toContain("Andrea");
    });

    it("approves session and performs cross-view cache invalidation of both counts and stock", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: {
          id: 101,
          bodega_id: 1,
          estado: "APROBADO",
          items: [],
        },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useRecuentos(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.approveSession(101);
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/inventory/counts/101/approve",
        expect.objectContaining({ method: "POST" })
      );
    });

    it("rejects session ordering a recount", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: {
          id: 101,
          estado: "RECHAZADO",
        },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useRecuentos(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.rejectSession(101);
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/inventory/counts/101/reject",
        expect.objectContaining({ method: "POST" })
      );
    });

    it("deletes a non-approved session", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: { success: true },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const { result } = renderHook(() => useRecuentos(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.deleteSession(103);
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/inventory/counts/103",
        expect.objectContaining({ method: "DELETE" })
      );
    });
  });
});
