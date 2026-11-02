// oppytec-frontend/src/features/projection/__tests__/projectionHooks.test.ts
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { projectionApi } from "../api/projectionApi";
import {
  calculateProjectionMetrics,
  useProyeccionData,
  buildClientSimulatedChartData,
  useProyeccionChart,
  useProyeccionState,
} from "../hooks";
import {
  MOCK_PROJECTION_PRODUCTS,
} from "../mockData";
import type { ProjectionFilters } from "../types";

// Mock de sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

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

describe("Feature Projection - Phase 3 Frontend Core & Reactive Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.clear();
    }
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // =========================================================================
  // 1. projectionApi Client Tests
  // =========================================================================
  describe("projectionApi Client", () => {
    it("getPaginatedSnapshots retorna lista paginada normalizando strings a números", async () => {
      const filters: ProjectionFilters = {
        page: 1,
        pageSize: 30,
        horizonDays: 30,
        search: "Pollo",
        bodegaId: 1,
        status: "critical",
        sortBy: "urgency_desc",
      };

      const result = await projectionApi.getPaginatedSnapshots(filters);
      expect(result).toBeDefined();
      expect(Array.isArray(result.items)).toBe(true);
      expect(result.page).toBe(1);
      expect(result.page_size).toBe(30);

      if (result.items.length > 0) {
        const item = result.items[0]!;
        expect(typeof item.current_qty).toBe("number");
        expect(typeof item.projected_qty).toBe("number");
        expect(typeof item.worst_status).toBe("string");
      }
    });

    it("getProductCurve retorna detalle y serie temporal con puntos de simulación", async () => {
      const curve = await projectionApi.getProductCurve(101, 1, 30);
      expect(curve).toBeDefined();
      expect(curve.producto_id).toBe(101);
      expect(Array.isArray(curve.curve)).toBe(true);
      expect(curve.curve.length).toBeGreaterThan(0);

      const pt = curve.curve[0]!;
      expect(typeof pt.qty).toBe("number");
      expect(typeof pt.status).toBe("string");
      expect(pt.date).toBeDefined();
    });

    it("getProjectionAlerts retorna alertas y sugerencias de traspaso", async () => {
      const alerts = await projectionApi.getProjectionAlerts(1, 30);
      expect(Array.isArray(alerts)).toBe(true);
      expect(alerts.length).toBeGreaterThan(0);

      const al = alerts[0]!;
      expect(al.producto_id).toBeDefined();
      expect(al.status).toBe("critical");
      expect(Array.isArray(al.transfer_suggestions)).toBe(true);
    });

    it("recomputeSnapshots dispara recálculo con feedback y métricas de procesamiento", async () => {
      const result = await projectionApi.recomputeSnapshots(30);
      expect(result.status).toBe("completed");
      expect(result.processed).toBeGreaterThan(0);
      expect(typeof result.duration_ms).toBe("number");
    });
  });

  // =========================================================================
  // 2. Metrics Calculation Helper
  // =========================================================================
  describe("calculateProjectionMetrics Helper", () => {
    it("calcula correctamente contadores por estado y valor en riesgo", () => {
      const summary = calculateProjectionMetrics(MOCK_PROJECTION_PRODUCTS, MOCK_PROJECTION_PRODUCTS.length);
      expect(summary.total_items).toBe(6);
      expect(summary.in_critical_count).toBe(2);
      expect(summary.in_warning_count).toBe(2);
      expect(summary.normal_count).toBe(2);
      expect(summary.avg_coverage_days).toBeGreaterThan(0);
      expect(summary.total_value_at_risk).toBeGreaterThan(0);
    });

    it("retorna ceros ante lista vacía", () => {
      const emptySummary = calculateProjectionMetrics([], 0);
      expect(emptySummary.total_items).toBe(0);
      expect(emptySummary.in_critical_count).toBe(0);
      expect(emptySummary.in_warning_count).toBe(0);
      expect(emptySummary.normal_count).toBe(0);
      expect(emptySummary.avg_coverage_days).toBe(0);
      expect(emptySummary.total_value_at_risk).toBe(0);
    });
  });

  // =========================================================================
  // 3. useProyeccionData Hook
  // =========================================================================
  describe("useProyeccionData Hook", () => {
    it("obtiene datos paginados y calcula métricas reactivas", async () => {
      const filters: ProjectionFilters = {
        page: 1,
        pageSize: 30,
        horizonDays: 30,
      };

      const { result } = renderHook(
        () => useProyeccionData({ filters, enableRealtime: false }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.items.length).toBeGreaterThan(0);
      expect(result.current.metrics.total_items).toBeGreaterThan(0);
      expect(result.current.pagination.page).toBe(1);
      expect(result.current.pagination.pageSize).toBe(30);
    });

    it("ejecuta recompute mutation mostrando feedback toast de sonner", async () => {
      const filters: ProjectionFilters = {
        page: 1,
        pageSize: 30,
        horizonDays: 30,
      };

      const { result } = renderHook(
        () => useProyeccionData({ filters, enableRealtime: false }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.recompute(30);
      });

      expect(toast.info).toHaveBeenCalledWith(
        "Recalculando proyección del restaurante...",
        expect.any(Object)
      );
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("Recálculo completado")
      );
    });
  });

  // =========================================================================
  // 4. useProyeccionChart Hook & Client Simulation
  // =========================================================================
  describe("useProyeccionChart & buildClientSimulatedChartData", () => {
    it("simula client-side deduciendo consumo, eventos y caducidad de lotes", () => {
      const points = buildClientSimulatedChartData(
        50,
        2,
        30,
        10,
        [{ name: "Catering", qty: 10, date: new Date().toISOString().slice(0, 10) }],
        []
      );

      expect(points.length).toBe(31); // día 0 a día 30
      expect(points[0]!.qty).toBe(40); // 50 - 10 del evento en día 0
      expect(points[points.length - 1]!.qty).toBe(0); // agota a 0
    });

    it("useProyeccionChart carga datos y calcula dominios para Recharts", async () => {
      const { result } = renderHook(
        () => useProyeccionChart(101, 1, 30),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.curvePoints.length).toBeGreaterThan(0);
      expect(result.current.metrics.yAxisDomain[1]).toBeGreaterThan(0);
      expect(result.current.metrics.criticalPoint).toBeDefined();
    });
  });

  // =========================================================================
  // 5. useProyeccionState Hook
  // =========================================================================
  describe("useProyeccionState Hook", () => {
    it("inicializa con defaults y persiste cambios en localStorage", async () => {
      const { result } = renderHook(() => useProyeccionState());

      expect(result.current.pageSize).toBe(30);
      expect(result.current.horizonDays).toBe(30);
      expect(result.current.page).toBe(1);
      expect(result.current.bodegaId).toBe("all");
      expect(result.current.status).toBe("all");

      // Cambiar pageSize
      act(() => {
        result.current.setPageSize(50);
      });
      expect(result.current.pageSize).toBe(50);
      expect(window.localStorage.getItem("projection_page_size")).toBe("50");

      // Cambiar horizonDays
      act(() => {
        result.current.setHorizonDays(60);
      });
      expect(result.current.horizonDays).toBe(60);
      expect(window.localStorage.getItem("projection_horizon_days")).toBe("60");
    });

    it("resetea página a 1 cuando cambian filtros de búsqueda o selección", () => {
      const { result } = renderHook(() => useProyeccionState());

      act(() => {
        result.current.setPage(4);
      });
      expect(result.current.page).toBe(4);

      act(() => {
        result.current.setBodegaId(2);
      });
      expect(result.current.page).toBe(1);

      act(() => {
        result.current.setPage(3);
      });
      expect(result.current.page).toBe(3);

      act(() => {
        result.current.setStatus("critical");
      });
      expect(result.current.page).toBe(1);
    });

    it("resetFilters limpia todos los filtros aplicados", () => {
      const { result } = renderHook(() => useProyeccionState());

      act(() => {
        result.current.setSearch("Carne");
        result.current.setBodegaId(1);
        result.current.setStatus("warning");
        result.current.setSortBy("name_asc");
        result.current.setPage(3);
      });

      expect(result.current.activeFiltersCount).toBeGreaterThan(0);

      act(() => {
        result.current.resetFilters();
      });

      expect(result.current.searchTerm).toBe("");
      expect(result.current.bodegaId).toBe("all");
      expect(result.current.categoryId).toBe("all");
      expect(result.current.status).toBe("all");
      expect(result.current.sortBy).toBe("urgency_desc");
      expect(result.current.page).toBe(1);
      expect(result.current.activeFiltersCount).toBe(0);
    });
  });
});
