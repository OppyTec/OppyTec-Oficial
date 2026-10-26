// oppytec-frontend/src/features/inventory/alerts/hooks/useAlertBadge.ts
import { useState, useMemo, useEffect, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type { AlertBadge } from "../types";
import { MOCK_ALERTS_BADGE } from "../mockData";

export interface UseAlertBadgeOptions {
  readonly bodegaIds?: readonly number[] | number | string | "all";
  readonly areaOperativaId?: number | string | "all";
}

export interface UseAlertBadgeReturn {
  readonly totalCount: number;
  readonly hasCritical: boolean;
  readonly criticalCount: number;
  readonly expiredCount: number;
  readonly upcomingCount: number;
  readonly loading: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
  readonly refresh: () => Promise<unknown>;
}

export function useAlertBadge(options?: UseAlertBadgeOptions): UseAlertBadgeReturn {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const holdingId = context.holdingId || "holding-gastro-sur";
  const tenantId = context.tenantId || "tenant_rest_central";

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

  // Realtime subscription via WebSocket push events (Zero Polling)
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Graceful fallback if outside RealtimeProvider (e.g. unit tests)
  }

  // Construct query key
  const queryKey = useMemo(
    () =>
      queryKeys.inventory.alertsBadge({
        holdingId,
        tenantId,
        bodegaIds:
          effectiveBodegaIds.length > 0
            ? effectiveBodegaIds.slice().sort().join(",")
            : "all",
        areaOperativaId:
          effectiveAreaId !== undefined ? String(effectiveAreaId) : "all",
      }),
    [holdingId, tenantId, effectiveBodegaIds, effectiveAreaId]
  );

  // TanStack Query v5 consuming GET /api/v1/inventory/alerts/badge
  const {
    data: badgeData,
    isLoading,
    error,
    refetch,
  } = useQuery<AlertBadge>({
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

      const queryString = params.toString();
      const endpoint = `/api/v1/inventory/alerts/badge${queryString ? `?${queryString}` : ""}`;

      const res = await apiRequest<AlertBadge>(endpoint, {
        method: "GET",
        fallbackData: MOCK_ALERTS_BADGE,
      });

      return res.data;
    },
    staleTime: 60_000,
  });

  // Local storage state fallback for zero latency and cross-tab/Sidebar synchronization
  const [localCounts, setLocalCounts] = useState<{
    totalCount: number;
    hasCritical: boolean;
  }>(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      const total = Number(window.localStorage.getItem("notif_total_count") || "0");
      const critical = window.localStorage.getItem("notif_has_critical") === "true";
      return { totalCount: isNaN(total) ? 0 : total, hasCritical: critical };
    }
    return { totalCount: 0, hasCritical: false };
  });

  // Keep localStorage updated when badgeData arrives
  useEffect(() => {
    if (badgeData && typeof window !== "undefined" && window.localStorage) {
      try {
        window.localStorage.setItem("notif_total_count", String(badgeData.total_count));
        window.localStorage.setItem("notif_has_critical", String(badgeData.has_critical));
        setLocalCounts({
          totalCount: badgeData.total_count,
          hasCritical: badgeData.has_critical,
        });
      } catch {
        // safe
      }
    }
  }, [badgeData]);

  // Synchronize on window "notif-updated" or "storage" events and update Query Cache
  useEffect(() => {
    const handleNotifUpdated = () => {
      if (typeof window !== "undefined" && window.localStorage) {
        const total = Number(window.localStorage.getItem("notif_total_count") || "0");
        const critical = window.localStorage.getItem("notif_has_critical") === "true";
        const validTotal = isNaN(total) ? 0 : total;

        setLocalCounts({ totalCount: validTotal, hasCritical: critical });

        // Update TanStack Query cache deterministically
        queryClient.setQueryData<AlertBadge>(queryKey, (prev) => {
          if (!prev) {
            return {
              total_count: validTotal,
              has_critical: critical,
              critical_stock_count: critical ? validTotal : 0,
              expired_count: 0,
              upcoming_count: critical ? 0 : validTotal,
            };
          }
          return {
            ...prev,
            total_count: validTotal,
            has_critical: critical,
          };
        });
      }
    };

    window.addEventListener("notif-updated", handleNotifUpdated);
    window.addEventListener("storage", handleNotifUpdated);
    return () => {
      window.removeEventListener("notif-updated", handleNotifUpdated);
      window.removeEventListener("storage", handleNotifUpdated);
    };
  }, [queryClient, queryKey]);

  // WebSocket push event invalidation (Zero Polling)
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType === "inventory.alerts.changed" ||
      lastEvent?.eventType === "inventory.stock.updated" ||
      lastEvent?.eventType.startsWith("inventory.")
    ) {
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "inventory", "alerts", "badge"],
      });
    }
  }, [realtimeEvents, queryClient]);

  const totalCount = badgeData?.total_count ?? localCounts.totalCount;
  const hasCritical = badgeData?.has_critical ?? localCounts.hasCritical;
  const criticalCount = badgeData?.critical_stock_count ?? 0;
  const expiredCount = badgeData?.expired_count ?? 0;
  const upcomingCount = badgeData?.upcoming_count ?? 0;

  const handleRefresh = useCallback(async () => {
    return refetch();
  }, [refetch]);

  return {
    totalCount,
    hasCritical,
    criticalCount,
    expiredCount,
    upcomingCount,
    loading: isLoading,
    error,
    refetch,
    refresh: handleRefresh,
  };
}
