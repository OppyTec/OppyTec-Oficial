/**
 * oppytec-frontend/src/features/procurement/hooks/useMermaAnalytics.ts
 * Hook reactivo TanStack Query v5 para Analítica Financiera e Historial de Mermas.
 * Presets de rango de fechas ("hoy", "7d", "30d", "mes_actual", "mes_anterior", "personalizado").
 * Zero HTTP polling: suscripción WebSocket a `inventory.waste.registered`.
 * Fallback resiliente con datos de mock y precisión Decimal.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import {
  MOCK_MERMA_ANALYTICS,
  MOCK_MERMA_HISTORY,
} from "../mockData";
import type {
  DateRangePreset,
  MermaAnalyticsData,
  MermaHistoryItem,
} from "../types";

export interface MermaFilterState {
  preset: DateRangePreset;
  date_from: string | null;
  date_to: string | null;
  bodega_id?: number | null;
  motivo?: string | null;
  estado?: string | null;
}

export function formatDateToIsoDay(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function calculateDateRange(
  preset: DateRangePreset,
  customFrom?: string | null,
  customTo?: string | null,
  nowDate: Date = new Date()
): { date_from: string | null; date_to: string | null } {
  const today = new Date(nowDate.getFullYear(), nowDate.getMonth(), nowDate.getDate());
  const todayStr = formatDateToIsoDay(today);

  switch (preset) {
    case "hoy":
      return { date_from: todayStr, date_to: todayStr };

    case "7d": {
      const past7 = new Date(today);
      past7.setDate(past7.getDate() - 7);
      return { date_from: formatDateToIsoDay(past7), date_to: todayStr };
    }

    case "30d": {
      const past30 = new Date(today);
      past30.setDate(past30.getDate() - 30);
      return { date_from: formatDateToIsoDay(past30), date_to: todayStr };
    }

    case "mes_actual": {
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
      return { date_from: formatDateToIsoDay(firstDay), date_to: todayStr };
    }

    case "mes_anterior": {
      const firstDayPrev = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const lastDayPrev = new Date(today.getFullYear(), today.getMonth(), 0);
      return {
        date_from: formatDateToIsoDay(firstDayPrev),
        date_to: formatDateToIsoDay(lastDayPrev),
      };
    }

    case "personalizado":
    default:
      return {
        date_from: customFrom ?? null,
        date_to: customTo ?? null,
      };
  }
}

export const INITIAL_MERMA_FILTERS: MermaFilterState = {
  preset: "30d",
  date_from: null,
  date_to: null,
  bodega_id: null,
  motivo: null,
  estado: null,
};

export function useMermaAnalytics(initialFilters?: Partial<MermaFilterState>) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  const [filters, setFiltersState] = useState<MermaFilterState>(() => {
    const preset = initialFilters?.preset ?? INITIAL_MERMA_FILTERS.preset;
    const computed = calculateDateRange(
      preset,
      initialFilters?.date_from,
      initialFilters?.date_to
    );
    return {
      ...INITIAL_MERMA_FILTERS,
      ...(initialFilters ?? {}),
      preset,
      date_from: computed.date_from,
      date_to: computed.date_to,
    };
  });

  const setPreset = useCallback((preset: DateRangePreset) => {
    setFiltersState((prev) => {
      const computed = calculateDateRange(preset, prev.date_from, prev.date_to);
      return {
        ...prev,
        preset,
        date_from: computed.date_from,
        date_to: computed.date_to,
      };
    });
  }, []);

  const setCustomRange = useCallback((dateFrom: string, dateTo: string) => {
    setFiltersState((prev) => ({
      ...prev,
      preset: "personalizado",
      date_from: dateFrom,
      date_to: dateTo,
    }));
  }, []);

  const setFilter = useCallback(
    <K extends keyof MermaFilterState>(key: K, value: MermaFilterState[K]) => {
      setFiltersState((prev) => {
        const next = { ...prev, [key]: value };
        if (key === "preset" && typeof value === "string") {
          const computed = calculateDateRange(
            value as DateRangePreset,
            prev.date_from,
            prev.date_to
          );
          next.date_from = computed.date_from;
          next.date_to = computed.date_to;
        }
        return next;
      });
    },
    []
  );

  const resetFilters = useCallback(() => {
    const computed = calculateDateRange("30d");
    setFiltersState({
      ...INITIAL_MERMA_FILTERS,
      date_from: computed.date_from,
      date_to: computed.date_to,
    });
  }, []);

  // ==========================================================================
  // PARÁMETROS DE QUERY
  // ==========================================================================
  const queryParams = useMemo(() => {
    const params: Record<string, string> = {};
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;
    if (filters.bodega_id) params.bodega_id = String(filters.bodega_id);
    if (filters.motivo) params.motivo = filters.motivo;
    if (filters.estado) params.estado = filters.estado;
    return params;
  }, [filters]);

  const analyticsQueryKey = queryKeys.inventory.mermasAnalytics(tenantId, queryParams);
  const historyQueryKey = queryKeys.inventory.mermasHistory(tenantId, queryParams);

  // ==========================================================================
  // QUERIES REACTIVAS (Analytics y History)
  // ==========================================================================
  const {
    data: analytics = MOCK_MERMA_ANALYTICS,
    isLoading: isLoadingAnalytics,
    isError: isErrorAnalytics,
    refetch: refetchAnalytics,
  } = useQuery({
    queryKey: analyticsQueryKey,
    queryFn: async () => {
      const qs = new URLSearchParams(queryParams).toString();
      const endpoint = qs
        ? `/api/v1/inventory/mermas/analytics?${qs}`
        : "/api/v1/inventory/mermas/analytics";
      const response = await apiRequest<MermaAnalyticsData>(endpoint, {
        method: "GET",
        fallbackData: MOCK_MERMA_ANALYTICS,
      });
      return response.data;
    },
    staleTime: 1000 * 60 * 5,
  });

  const {
    data: historyResponse,
    isLoading: isLoadingHistory,
    isError: isErrorHistory,
    refetch: refetchHistory,
  } = useQuery({
    queryKey: historyQueryKey,
    queryFn: async () => {
      const qs = new URLSearchParams(queryParams).toString();
      const endpoint = qs
        ? `/api/v1/inventory/mermas/history?${qs}`
        : "/api/v1/inventory/mermas/history";
      const response = await apiRequest<{ items: MermaHistoryItem[]; total: number }>(
        endpoint,
        {
          method: "GET",
          fallbackData: { items: MOCK_MERMA_HISTORY, total: MOCK_MERMA_HISTORY.length },
        }
      );
      return response.data;
    },
    staleTime: 1000 * 60 * 5,
  });

  const historyItems: MermaHistoryItem[] = historyResponse?.items ?? MOCK_MERMA_HISTORY;
  const historyTotal: number = historyResponse?.total ?? historyItems.length;

  // ==========================================================================
  // SUSCRIPCIÓN WEBSOCKET (inventory.waste.registered -> Cero Polling)
  // ==========================================================================
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Desacoplado
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const latestEvent = realtimeEvents[0];
    if (
      latestEvent?.eventType === "inventory.waste.registered" ||
      latestEvent?.eventType === "inventory.merma.threshold_alert" ||
      latestEvent?.eventType.startsWith("inventory.mermas")
    ) {
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "inventory", "mermas"],
      });
    }
  }, [realtimeEvents, queryClient]);

  return {
    // Datos y estados
    analytics,
    historyItems,
    historyTotal,
    isLoadingAnalytics,
    isLoadingHistory,
    isErrorAnalytics,
    isErrorHistory,
    refetchAnalytics,
    refetchHistory,

    // Filtros de fecha y presets
    filters,
    setPreset,
    setCustomRange,
    setFilter,
    resetFilters,
  };
}
