/**
 * oppytec-frontend/src/features/projection/hooks/useProyeccionData.ts
 * Hook reactivo de alto rendimiento para el Grid de Proyecciones de OppyTec v2.0.
 * Conexión con TanStack Query v5, paginación server-side fluida (keepPreviousData),
 * mutación de recálculo con feedback Sonner y soporte WebSocket zero-polling.
 */
import { useEffect, useMemo } from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { MOCK_DATA_MODE_EVENT_NAME } from "@/shared/mock/mockModeStorage";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import { projectionApi } from "../api/projectionApi";
import type {
  PaginatedProjectionResponse,
  ProjectionFilters,
  ProjectionMetricsSummary,
  ProjectionProductOverview,
  RecomputeResponsePayload,
} from "../types";

export interface UseProyeccionDataOptions {
  readonly filters: ProjectionFilters;
  readonly enableRealtime?: boolean;
}

export function calculateProjectionMetrics(
  items: readonly ProjectionProductOverview[],
  totalItemsServer: number
): ProjectionMetricsSummary {
  if (!items || items.length === 0) {
    return {
      total_items: totalItemsServer,
      in_warning_count: 0,
      in_critical_count: 0,
      normal_count: 0,
      avg_coverage_days: 0,
      total_value_at_risk: 0,
    };
  }

  let warningCount = 0;
  let criticalCount = 0;
  let normalCount = 0;
  let coverageSum = 0;
  let validCoverageCount = 0;
  let valueAtRisk = 0;

  for (const item of items) {
    if (item.worst_status === "critical") {
      criticalCount++;
      const cost = item.costo_unitario ?? 0;
      valueAtRisk += (item.current_qty ?? 0) * cost;
    } else if (item.worst_status === "warning") {
      warningCount++;
    } else {
      normalCount++;
    }

    if (item.worst_day !== null && item.worst_day !== undefined) {
      coverageSum += item.worst_day;
      validCoverageCount++;
    } else if (item.daily_consumption_rate && item.daily_consumption_rate > 0) {
      const days = item.current_qty / item.daily_consumption_rate;
      coverageSum += Math.min(days, item.horizon_days);
      validCoverageCount++;
    } else {
      coverageSum += item.horizon_days;
      validCoverageCount++;
    }
  }

  const avgCoverage = validCoverageCount > 0 ? Number((coverageSum / validCoverageCount).toFixed(1)) : 0;

  return {
    total_items: totalItemsServer,
    in_warning_count: warningCount,
    in_critical_count: criticalCount,
    normal_count: normalCount,
    avg_coverage_days: avgCoverage,
    total_value_at_risk: Math.round(valueAtRisk),
  };
}

export function useProyeccionData(options: UseProyeccionDataOptions) {
  const { filters, enableRealtime = true } = options;
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  // Suscripción WebSocket Push Zero-Polling
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    if (enableRealtime) {
      const rt = useRealtimeSync();
      realtimeEvents = rt.authorizedEvents;
    }
  } catch {
    // Si se monta fuera de RealtimeProvider en pruebas unitarias
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[realtimeEvents.length - 1];

    if (
      lastEvent?.eventType?.startsWith("projection.") ||
      lastEvent?.channel === "projection" ||
      lastEvent?.eventType === "projection.snapshots_recomputed"
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.projection.all(tenantId),
      });

      if (lastEvent?.eventType === "projection.critical_alert") {
        toast.warning(
          typeof lastEvent.payload === "string"
            ? lastEvent.payload
            : "Alerta crítica de agotamiento detectada en proyección."
        );
      }
    }
  }, [realtimeEvents, queryClient, tenantId]);

  useEffect(() => {
    const handleMockModeChange = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.projection.all(tenantId),
      });
    };
    window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
    return () => window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
  }, [queryClient, tenantId]);

  // Consulta paginada server-side con keepPreviousData
  const snapshotsQuery = useQuery<PaginatedProjectionResponse, Error>({
    queryKey: queryKeys.projection.snapshots(tenantId, filters as unknown as Record<string, unknown>),
    queryFn: () => projectionApi.getPaginatedSnapshots(filters),
    placeholderData: keepPreviousData,
    staleTime: 1000 * 60 * 2, // 2 minutos
  });

  // Mutación para forzar recálculo inmediato con feedback de toast
  const recomputeMutation = useMutation<RecomputeResponsePayload, Error, number | undefined>({
    mutationFn: (horizon?: number) =>
      projectionApi.recomputeSnapshots(horizon ?? filters.horizonDays),
    onMutate: () => {
      toast.info("Recalculando proyección del restaurante...", {
        duration: 3000,
      });
    },
    onSuccess: (result) => {
      toast.success(
        `Recálculo completado: ${result.processed} productos procesados (${result.duration_ms ?? 0} ms)`
      );
      void queryClient.invalidateQueries({
        queryKey: queryKeys.projection.all(tenantId),
      });
    },
    onError: (err) => {
      toast.error(`Error al recalcular proyección: ${err.message}`);
    },
  });

  const items = useMemo(() => {
    return snapshotsQuery.data?.items ?? [];
  }, [snapshotsQuery.data?.items]);

  const metrics = useMemo(() => {
    return calculateProjectionMetrics(items, snapshotsQuery.data?.total_items ?? items.length);
  }, [items, snapshotsQuery.data?.total_items]);

  const pagination = useMemo(() => {
    const data = snapshotsQuery.data;
    return {
      page: data?.page ?? filters.page,
      pageSize: data?.page_size ?? filters.pageSize,
      totalItems: data?.total_items ?? items.length,
      totalPages: data?.total_pages ?? Math.max(1, Math.ceil((data?.total_items ?? items.length) / filters.pageSize)),
      hasNext: data?.has_next ?? false,
      hasPrev: data?.has_prev ?? false,
    };
  }, [snapshotsQuery.data, filters.page, filters.pageSize, items.length]);

  return {
    data: snapshotsQuery.data,
    items,
    metrics,
    pagination,
    isLoading: snapshotsQuery.isLoading,
    isFetching: snapshotsQuery.isFetching,
    isPlaceholderData: snapshotsQuery.isPlaceholderData,
    isError: snapshotsQuery.isError,
    error: snapshotsQuery.error,
    refetch: snapshotsQuery.refetch,
    recompute: recomputeMutation.mutateAsync,
    isRecomputing: recomputeMutation.isPending,
  };
}
