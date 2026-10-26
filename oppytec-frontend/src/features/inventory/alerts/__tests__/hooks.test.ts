// oppytec-frontend/src/features/inventory/alerts/__tests__/hooks.test.ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as httpClient from "@/shared/api/httpClient";
import { useAlertas } from "../hooks/useAlertas";
import { useAlertBadge } from "../hooks/useAlertBadge";
import {
  MOCK_ALERTS_SUMMARY,
  MOCK_ALERTS_BADGE,
  MOCK_ALERTS_EMPTY,
  mapSummaryToProductItems,
} from "../mockData";
import type { AlertsSummary, AlertBadge } from "../types";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe("Módulo de Alertas - Hooks Reactivos (Fase 3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
  });

  afterEach(() => {
    vi.restoreAllMocks();
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
  });

  // ==========================================================================
  // 1. Modelos de Dominio y Conversión Semántica (ProductoAnalitico)
  // ==========================================================================
  describe("Modelos y Transformación a ProductoAnalitico", () => {
    it("converts mock summary into legacy-compatible AlertProductItem array", () => {
      const items = mapSummaryToProductItems(MOCK_ALERTS_SUMMARY);
      expect(items.length).toBe(MOCK_ALERTS_SUMMARY.total_count);

      // Verify Critical Stock mapping
      const criticalItem = items.find((i) => i.alert_type === "critical");
      expect(criticalItem).toBeDefined();
      expect(criticalItem?.id).toBe("101::1");
      expect(criticalItem?.nombre).toBe("Pechuga de Pollo Fresca");
      expect(criticalItem?.ratio?.status).toBe("critical");
      expect(criticalItem?.ratio?.clamped_ratio).toBe(18);

      // Verify Expired Lot mapping
      const expiredItem = items.find((i) => i.alert_type === "expired");
      expect(expiredItem).toBeDefined();
      expect(expiredItem?.lote_codigo).toBe("LOT-2026-CR01");
      expect(expiredItem?.dias_vencido).toBe(7);
      expect(expiredItem?.valor_total_riesgo).toBe(27200);

      // Verify Upcoming Expiry mapping
      const upcomingItem = items.find((i) => i.alert_type === "upcoming");
      expect(upcomingItem).toBeDefined();
      expect(upcomingItem?.lote_codigo).toBe("LOT-SALM-04");
      expect(upcomingItem?.dias_restantes).toBe(3);
      expect(upcomingItem?.valor_total_riesgo).toBe(187500);
    });

    it("handles empty alerts summary without crashing", () => {
      const items = mapSummaryToProductItems(MOCK_ALERTS_EMPTY);
      expect(items).toEqual([]);
    });
  });

  // ==========================================================================
  // 2. useAlertas: Consulta Inicial, Filtros y Transformación
  // ==========================================================================
  describe("useAlertas Hook - Consultas y Filtros", () => {
    it("loads fallback mock summary data when API returns fallback", async () => {
      const { result } = renderHook(() => useAlertas(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.summary.total_count).toBe(7);
      expect(result.current.summary.critical_count).toBe(3);
      expect(result.current.summary.expired_count).toBe(2);
      expect(result.current.summary.upcoming_count).toBe(2);
      expect(result.current.summary.has_critical).toBe(true);

      expect(result.current.stockCritico.length).toBe(3);
      expect(result.current.vencidos.length).toBe(2);
      expect(result.current.vencimientosProximos.length).toBe(2);
      expect(result.current.data.length).toBe(7);
    });

    it("filters alerts by single bodegaId correctly", async () => {
      const { result } = renderHook(
        () => useAlertas({ bodegaIds: 2 }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Bodega 2 has: 1 critical (Aceite Oliva), 1 expired (Crema de Leche), 1 upcoming (Salmón) = 3
      expect(result.current.summary.total_count).toBe(3);
      expect(result.current.summary.critical_count).toBe(1);
      expect(result.current.summary.expired_count).toBe(1);
      expect(result.current.summary.upcoming_count).toBe(1);
      expect(result.current.stockCritico[0]?.bodega_id).toBe(2);
      expect(result.current.vencidos[0]?.bodega_id).toBe(2);
      expect(result.current.vencimientosProximos[0]?.bodega_id).toBe(2);
    });

    it("filters alerts by array of bodegaIds", async () => {
      const { result } = renderHook(
        () => useAlertas({ bodegaIds: [1] }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Bodega 1 has: 2 critical (Pollo, Harina), 1 expired (Yogurt), 1 upcoming (Queso Mozzarella) = 4
      expect(result.current.summary.total_count).toBe(4);
      expect(result.current.summary.critical_count).toBe(2);
      expect(result.current.summary.expired_count).toBe(1);
      expect(result.current.summary.upcoming_count).toBe(1);
    });

    it("filters alerts by filterType 'stock'", async () => {
      const { result } = renderHook(
        () => useAlertas({ filterType: "stock" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.summary.critical_count).toBe(3);
      expect(result.current.summary.expired_count).toBe(0);
      expect(result.current.summary.upcoming_count).toBe(0);
      expect(result.current.summary.total_count).toBe(3);
    });

    it("filters alerts by filterType 'expired'", async () => {
      const { result } = renderHook(
        () => useAlertas({ filterType: "expired" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.summary.critical_count).toBe(0);
      expect(result.current.summary.expired_count).toBe(2);
      expect(result.current.summary.upcoming_count).toBe(0);
      expect(result.current.summary.total_count).toBe(2);
    });

    it("filters alerts by filterType 'upcoming'", async () => {
      const { result } = renderHook(
        () => useAlertas({ filterType: "upcoming" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.summary.critical_count).toBe(0);
      expect(result.current.summary.expired_count).toBe(0);
      expect(result.current.summary.upcoming_count).toBe(2);
      expect(result.current.summary.total_count).toBe(2);
    });

    it("updates filterType interactively via setFilterType", async () => {
      const { result } = renderHook(
        () => useAlertas({ initialFilterType: "all" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.filterType).toBe("all");
      expect(result.current.summary.total_count).toBe(7);

      act(() => {
        result.current.setFilterType("stock");
      });

      await waitFor(() => {
        expect(result.current.filterType).toBe("stock");
        expect(result.current.summary.total_count).toBe(3);
      });
    });

    it("consumes custom API response when apiRequest succeeds", async () => {
      const customSummary: AlertsSummary = {
        total_count: 1,
        critical_count: 1,
        expired_count: 0,
        upcoming_count: 0,
        has_critical: true,
        total_financial_risk: 0,
        critical_stock: [
          {
            producto_id: 999,
            bodega_id: 1,
            bodega_nombre: "Bodega Test",
            producto_nombre: "Carne Premium",
            stock_actual: 1.0,
            stock_minimo: 10.0,
            unidad_medida: "kg",
            ratio: {
              stock_actual: 1.0,
              stock_minimo: 10.0,
              raw_ratio: 10.0,
              clamped_ratio: 10.0,
              status: "critical",
            },
            is_depleted: false,
            bodega_color: "#ef4444",
            bodega_icono: "warehouse",
            costo_promedio: 12000,
          },
        ],
        expired_lots: [],
        upcoming_expiries: [],
      };

      vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: customSummary,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant-test",
      });

      const { result } = renderHook(() => useAlertas(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.summary.total_count).toBe(1);
        expect(result.current.data[0]?.nombre).toBe("Carne Premium");
      });
    });
  });

  // ==========================================================================
  // 3. Sincronización en Background y Eventos de Ventana
  // ==========================================================================
  describe("useAlertas Hook - Sincronización en Background & Eventos", () => {
    it("synchronizes notif_total_count and notif_has_critical in localStorage and emits 'notif-updated'", async () => {
      const dispatchSpy = vi.spyOn(window, "dispatchEvent");

      renderHook(() => useAlertas(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(localStorage.getItem("notif_total_count")).toBe("7");
        expect(localStorage.getItem("notif_has_critical")).toBe("true");
      });

      const notifEvents = dispatchSpy.mock.calls.filter(
        (call) => (call[0] as Event).type === "notif-updated"
      );
      expect(notifEvents.length).toBeGreaterThanOrEqual(1);
    });

    it("invalidates queries reactively when 'inventory_alerts_changed' is dispatched", async () => {
      const apiSpy = vi.spyOn(httpClient, "apiRequest");

      const { result } = renderHook(() => useAlertas(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const initialCalls = apiSpy.mock.calls.length;

      act(() => {
        window.dispatchEvent(new Event("inventory_alerts_changed"));
      });

      await waitFor(() => {
        expect(apiSpy.mock.calls.length).toBeGreaterThan(initialCalls);
      });
    });

    it("triggers refetch and refresh without error", async () => {
      const { result } = renderHook(() => useAlertas(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await act(async () => {
        await result.current.refetch();
      });

      await act(async () => {
        await result.current.refresh();
      });

      expect(result.current.summary.total_count).toBe(7);
    });
  });

  // ==========================================================================
  // 4. useAlertBadge: Hook Ultraliviano para Sidebar
  // ==========================================================================
  describe("useAlertBadge Hook", () => {
    it("returns correct badge summary counts from fallback data", async () => {
      const { result } = renderHook(() => useAlertBadge(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.totalCount).toBe(MOCK_ALERTS_BADGE.total_count);
      expect(result.current.hasCritical).toBe(MOCK_ALERTS_BADGE.has_critical);
      expect(result.current.criticalCount).toBe(MOCK_ALERTS_BADGE.critical_stock_count);
      expect(result.current.expiredCount).toBe(MOCK_ALERTS_BADGE.expired_count);
      expect(result.current.upcomingCount).toBe(MOCK_ALERTS_BADGE.upcoming_count);
    });

    it("synchronizes localStorage when badge data is received", async () => {
      renderHook(() => useAlertBadge(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(localStorage.getItem("notif_total_count")).toBe("7");
        expect(localStorage.getItem("notif_has_critical")).toBe("true");
      });
    });

    it("updates local state instantly when 'notif-updated' event is dispatched", async () => {
      const { result } = renderHook(() => useAlertBadge(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      act(() => {
        localStorage.setItem("notif_total_count", "12");
        localStorage.setItem("notif_has_critical", "true");
        window.dispatchEvent(new Event("notif-updated"));
      });

      await waitFor(() => {
        expect(result.current.totalCount).toBe(12);
        expect(result.current.hasCritical).toBe(true);
      });
    });

    it("updates local state instantly when 'storage' event is dispatched across tabs", async () => {
      const { result } = renderHook(() => useAlertBadge(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      act(() => {
        localStorage.setItem("notif_total_count", "4");
        localStorage.setItem("notif_has_critical", "false");
        window.dispatchEvent(new Event("storage"));
      });

      await waitFor(() => {
        expect(result.current.totalCount).toBe(4);
        expect(result.current.hasCritical).toBe(false);
      });
    });

    it("consumes custom badge API response correctly", async () => {
      const customBadge: AlertBadge = {
        total_count: 5,
        has_critical: false,
        critical_stock_count: 0,
        expired_count: 0,
        upcoming_count: 5,
      };

      vi.spyOn(httpClient, "apiRequest").mockResolvedValue({
        data: customBadge,
        traceId: "badge-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant-test",
      });

      const { result } = renderHook(() => useAlertBadge(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.totalCount).toBe(5);
        expect(result.current.hasCritical).toBe(false);
        expect(result.current.upcomingCount).toBe(5);
      });
    });

    it("supports refresh and refetch for badge", async () => {
      const { result } = renderHook(() => useAlertBadge(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await act(async () => {
        await result.current.refetch();
      });

      await act(async () => {
        await result.current.refresh();
      });

      expect(result.current.totalCount).toBe(7);
    });
  });
});
