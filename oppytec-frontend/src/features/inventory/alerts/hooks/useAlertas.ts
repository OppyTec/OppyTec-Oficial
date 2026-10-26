// oppytec-frontend/src/features/inventory/alerts/hooks/useAlertas.ts
import { useState, useMemo, useEffect, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type {
  AlertsSummary,
  AlertFilterType,
  AlertProductItem,
  CriticalStockAlert,
  ExpiredLotAlert,
  UpcomingExpiryAlert,
} from "../types";
import {
  MOCK_ALERTS_SUMMARY,
  mapSummaryToProductItems,
} from "../mockData";

export interface UseAlertasOptions {
  readonly bodegaIds?: readonly number[] | number | string | "all";
  readonly areaOperativaId?: number | string | "all";
  readonly filterType?: AlertFilterType;
  readonly upcomingDays?: number;
  readonly initialFilterType?: AlertFilterType;
}

export interface UseAlertasReturn {
  readonly data: readonly AlertProductItem[];
  readonly summary: AlertsSummary;
  readonly stockCritico: readonly CriticalStockAlert[];
  readonly vencidos: readonly ExpiredLotAlert[];
  readonly vencimientosProximos: readonly UpcomingExpiryAlert[];
  readonly loading: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
  readonly refresh: () => Promise<unknown>;
  readonly filterType: AlertFilterType;
  readonly setFilterType: (next: AlertFilterType) => void;
}

/**
 * Filter mock summary locally for fallback and offline resilience.
 */
function filterMockSummary(
  source: AlertsSummary,
  bodegaIds: readonly number[],
  _areaId: number | undefined,
  filterType: AlertFilterType
): AlertsSummary {
  let critical = [...source.critical_stock];
  let expired = [...source.expired_lots];
  let upcoming = [...source.upcoming_expiries];

  if (bodegaIds.length > 0) {
    critical = critical.filter((item) => bodegaIds.includes(item.bodega_id));
    expired = expired.filter((item) => bodegaIds.includes(item.bodega_id));
    upcoming = upcoming.filter((item) => bodegaIds.includes(item.bodega_id));
  }

  if (filterType === "stock") {
    expired = [];
    upcoming = [];
  } else if (filterType === "expired") {
    critical = [];
    upcoming = [];
  } else if (filterType === "upcoming") {
    critical = [];
    expired = [];
  }

  const totalRisk =
    expired.reduce((sum, item) => sum + item.valor_total_riesgo, 0) +
    upcoming.reduce((sum, item) => sum + item.valor_total_riesgo, 0);

  return {
    total_count: critical.length + expired.length + upcoming.length,
    critical_count: critical.length,
    expired_count: expired.length,
    upcoming_count: upcoming.length,
    has_critical: critical.length > 0 || expired.length > 0,
    total_financial_risk: totalRisk,
    critical_stock: critical,
    expired_lots: expired,
    upcoming_expiries: upcoming,
  };
}

export function useAlertas(options?: UseAlertasOptions): UseAlertasReturn {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const holdingId = context.holdingId || "holding-gastro-sur";
  const tenantId = context.tenantId || "tenant_rest_central";

  // Filter type state (defaults to options or "all")
  const [internalFilterType, setInternalFilterType] = useState<AlertFilterType>(
    options?.initialFilterType ?? options?.filterType ?? "all"
  );

  const effectiveFilterType = options?.filterType ?? internalFilterType;
  const upcomingDays = options?.upcomingDays ?? 30;

  // Normalize bodega IDs filter
  const effectiveBodegaIds = useMemo<readonly number[]>(() => {
    const raw = options?.bodegaIds;
    if (!raw || raw === "all") return [];
    if (Array.isArray(raw)) {
      return raw
        .filter((id) => typeof id === "number" || (!isNaN(Number(id)) && id !== "all"))
        .map(Number);
    }
    const parsed = Number(raw);
    return isNaN(parsed) ? [] : [parsed];
  }, [options?.bodegaIds]);

  // Normalize area operativa ID filter
  const effectiveAreaId = useMemo<number | undefined>(() => {
    const raw = options?.areaOperativaId;
    if (!raw || raw === "all") return undefined;
    const parsed = Number(raw);
    return isNaN(parsed) ? undefined : parsed;
  }, [options?.areaOperativaId]);

  // Attempt real-time subscription via WebSocket push events (Zero Polling)
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Graceful fallback if mounted outside RealtimeProvider (e.g., unit tests)
  }

  // Construct deterministic query key
  const queryKey = useMemo(
    () =>
      queryKeys.inventory.alerts({
        holdingId,
        tenantId,
        bodegaIds:
          effectiveBodegaIds.length > 0
            ? effectiveBodegaIds.slice().sort().join(",")
            : "all",
        areaOperativaId:
          effectiveAreaId !== undefined ? String(effectiveAreaId) : "all",
        filterType: effectiveFilterType,
        upcomingDays,
      }),
    [
      holdingId,
      tenantId,
      effectiveBodegaIds,
      effectiveAreaId,
      effectiveFilterType,
      upcomingDays,
    ]
  );

  // Local fallback dataset matching the current filters
  const fallbackSummary = useMemo(
    () =>
      filterMockSummary(
        MOCK_ALERTS_SUMMARY,
        effectiveBodegaIds,
        effectiveAreaId,
        effectiveFilterType
      ),
    [effectiveBodegaIds, effectiveAreaId, effectiveFilterType]
  );

  // TanStack Query v5 consuming GET /api/v1/inventory/alerts
  const {
    data: rawData,
    isLoading,
    error,
    refetch,
  } = useQuery<AlertsSummary>({
    queryKey,
    queryFn: async () => {
      const params = new URLSearchParams();
      if (effectiveBodegaIds.length > 0) {
        effectiveBodegaIds.forEach((id) =>
          params.append("bodega_id", String(id))
        );
      }
      if (effectiveAreaId !== undefined) {
        params.append("area_operativa_id", String(effectiveAreaId));
      }
      if (effectiveFilterType && effectiveFilterType !== "all") {
        params.append("tipo", effectiveFilterType);
      }
      if (upcomingDays !== 30) {
        params.append("upcoming_days", String(upcomingDays));
      }

      const queryString = params.toString();
      const endpoint = `/api/v1/inventory/alerts${queryString ? `?${queryString}` : ""}`;

      const res = await apiRequest<AlertsSummary>(endpoint, {
        method: "GET",
        fallbackData: fallbackSummary,
      });

      return res.data;
    },
    staleTime: 60_000,
  });

  // Zero-polling real-time invalidation upon push WebSocket events
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType === "inventory.alerts.changed" ||
      lastEvent?.eventType === "inventory.stock.updated" ||
      lastEvent?.eventType.startsWith("inventory.")
    ) {
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "inventory", "alerts"],
      });
    }
  }, [realtimeEvents, queryClient]);

  // Listen to window-level custom events for local cross-view synchronization
  useEffect(() => {
    const handleLocalSync = () => {
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "inventory", "alerts"],
      });
    };
    window.addEventListener("inventory_alerts_changed", handleLocalSync);
    return () => {
      window.removeEventListener("inventory_alerts_changed", handleLocalSync);
    };
  }, [queryClient]);

  // Consolidated summary
  const summary: AlertsSummary = useMemo(() => {
    return rawData ?? fallbackSummary;
  }, [rawData, fallbackSummary]);

  // Synchronize badge in localStorage and dispatch `notif-updated`
  useEffect(() => {
    if (summary) {
      try {
        if (typeof window !== "undefined" && window.localStorage) {
          window.localStorage.setItem("notif_total_count", String(summary.total_count));
          window.localStorage.setItem("notif_has_critical", String(summary.has_critical));
          window.dispatchEvent(new Event("notif-updated"));
        }
      } catch {
        // Safe catch for constrained test environments
      }
    }
  }, [summary]);

  // Mapped product items for legacy ProductoAnalitico paridad
  const data: readonly AlertProductItem[] = useMemo(() => {
    return mapSummaryToProductItems(summary);
  }, [summary]);

  const stockCritico = summary.critical_stock;
  const vencidos = summary.expired_lots;
  const vencimientosProximos = summary.upcoming_expiries;

  const handleRefresh = useCallback(async () => {
    return refetch();
  }, [refetch]);

  return {
    data,
    summary,
    stockCritico,
    vencidos,
    vencimientosProximos,
    loading: isLoading,
    error,
    refetch,
    refresh: handleRefresh,
    filterType: effectiveFilterType,
    setFilterType: setInternalFilterType,
  };
}
