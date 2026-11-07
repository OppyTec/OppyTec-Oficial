import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { isMockDataEnabled, MOCK_DATA_MODE_EVENT_NAME, useMockDataMode } from "@/shared/mock/mockModeStorage";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import {
  MOCK_JEV_CONSUMPTION,
  type JevConsumptionSummaryResponse,
  type JevHoldingGroup,
  type JevLogItem,
  type JevTenantGroup,
} from "../types";

export type JevViewMode = "holding" | "tenant" | "logs";

export interface UseJevConsumptionOptions {
  readonly initialPage?: number;
  readonly initialPageSize?: number;
  readonly initialSearch?: string;
  readonly initialCallerFeature?: string | null;
  readonly initialDecisionPrimitive?: string | null;
  readonly initialCalibratedAction?: string | null;
  readonly initialHoldingId?: string | null;
  readonly initialTenantId?: string | null;
  readonly initialViewMode?: JevViewMode;
}

export interface UseJevConsumptionReturn {
  readonly data: JevConsumptionSummaryResponse;
  readonly holdings: readonly JevHoldingGroup[];
  readonly tenants: readonly JevTenantGroup[];
  readonly logs: readonly JevLogItem[];
  readonly totalDecisionsAll: number;
  readonly totalCostUsdAll: number;
  readonly totalCostClpAll: number;
  readonly totalCreditsDeductedAll: number;
  readonly avgLatencyMsAll: number;
  readonly totalAutoAcceptedAll: number;
  readonly totalFlaggedWarningAll: number;
  readonly totalFallbackLlmAll: number;
  readonly estimatedSavingsUsdAll: number;
  readonly estimatedSavingsClpAll: number;
  readonly totalRecords: number;
  readonly isLoading: boolean;
  readonly isError: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
  // Estado de vista tri-modo
  readonly viewMode: JevViewMode;
  readonly setViewMode: (mode: JevViewMode) => void;
  // Filtros reactivos
  readonly page: number;
  readonly setPage: (page: number) => void;
  readonly pageSize: number;
  readonly setPageSize: (size: number) => void;
  readonly search: string;
  readonly setSearch: (s: string) => void;
  readonly callerFeature: string | null;
  readonly setCallerFeature: (f: string | null) => void;
  readonly decisionPrimitive: string | null;
  readonly setDecisionPrimitive: (p: string | null) => void;
  readonly calibratedAction: string | null;
  readonly setCalibratedAction: (a: string | null) => void;
  readonly holdingId: string | null;
  readonly setHoldingId: (id: string | null) => void;
  readonly tenantId: string | null;
  readonly setTenantId: (id: string | null) => void;
}

const CLEAN_JEV_CONSUMPTION: JevConsumptionSummaryResponse = {
  holdings: [],
  tenants: [],
  all_logs: [],
  total_decisions_all: 0,
  total_cost_usd_all: 0,
  total_cost_clp_all: 0,
  total_credits_deducted_all: 0,
  avg_latency_ms_all: 0,
  total_auto_accepted_all: 0,
  total_flagged_warning_all: 0,
  total_fallback_llm_all: 0,
  estimated_savings_usd_all: 0,
  estimated_savings_clp_all: 0,
  total_logs_count: 0,
  page: 1,
  page_size: 50,
};

export function useJevConsumption(
  options: UseJevConsumptionOptions = {}
): UseJevConsumptionReturn {
  const queryClient = useQueryClient();
  const { isDemo } = useMockDataMode();
  const defaultJevData = isDemo ? MOCK_JEV_CONSUMPTION : CLEAN_JEV_CONSUMPTION;

  const [page, setPage] = useState<number>(options.initialPage ?? 1);
  const [pageSize, setPageSize] = useState<number>(options.initialPageSize ?? 50);
  const [search, setSearch] = useState<string>(options.initialSearch ?? "");
  const [callerFeature, setCallerFeature] = useState<string | null>(
    options.initialCallerFeature ?? null
  );
  const [decisionPrimitive, setDecisionPrimitive] = useState<string | null>(
    options.initialDecisionPrimitive ?? null
  );
  const [calibratedAction, setCalibratedAction] = useState<string | null>(
    options.initialCalibratedAction ?? null
  );
  const [holdingId, setHoldingId] = useState<string | null>(
    options.initialHoldingId ?? null
  );
  const [tenantId, setTenantId] = useState<string | null>(
    options.initialTenantId ?? null
  );
  const [viewMode, setViewMode] = useState<JevViewMode>(
    options.initialViewMode ?? "holding"
  );

  // Suscripción Realtime Zero-Polling vía WebSocket
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Modo desacoplado o unit tests
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType === "oppyfy.jev_decision" ||
      lastEvent?.eventType === "oppyfy.token_consumed" ||
      lastEvent?.eventType?.startsWith("jev.")
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.jevConsumption(),
      });
    }
  }, [realtimeEvents, queryClient]);

  // Listener de sincronización local
  useEffect(() => {
    const handleSync = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.jevConsumption(),
      });
    };
    window.addEventListener("jev_consumption_changed", handleSync);
    window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, handleSync);
    return () => {
      window.removeEventListener("jev_consumption_changed", handleSync);
      window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, handleSync);
    };
  }, [queryClient]);

  const queryFilters = useMemo(
    () => ({
      page,
      pageSize,
      search: search.trim() || undefined,
      callerFeature: callerFeature ?? undefined,
      decisionPrimitive: decisionPrimitive ?? undefined,
      calibratedAction: calibratedAction ?? undefined,
      holdingId: holdingId ?? undefined,
      tenantId: tenantId ?? undefined,
    }),
    [page, pageSize, search, callerFeature, decisionPrimitive, calibratedAction, holdingId, tenantId]
  );

  const queryKey = useMemo(
    () => [...queryKeys.platformAdmin.jevConsumption(queryFilters), isDemo ? "demo" : "clean"],
    [queryFilters, isDemo]
  );

  const {
    data = defaultJevData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<JevConsumptionSummaryResponse>({
    queryKey,
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append("page", String(page));
      params.append("page_size", String(pageSize));
      if (search.trim()) params.append("search", search.trim());
      if (callerFeature) params.append("caller_feature", callerFeature);
      if (decisionPrimitive) params.append("decision_primitive", decisionPrimitive);
      if (calibratedAction) params.append("calibrated_action", calibratedAction);
      if (holdingId) params.append("holding_id", holdingId);
      if (tenantId) params.append("tenant_id", tenantId);

      const qs = params.toString();
      const endpoint = `/api/v1/platform-admin/jev-consumption${qs ? `?${qs}` : ""}`;
      const fallback = isMockDataEnabled() ? MOCK_JEV_CONSUMPTION : CLEAN_JEV_CONSUMPTION;

      const res = await apiRequest<JevConsumptionSummaryResponse>(endpoint, {
        method: "GET",
        fallbackData: fallback,
        forceFallback: true,
      });
      return res.data;
    },
    staleTime: 15_000,
  });

  return {
    data,
    holdings: data.holdings ?? [],
    tenants: data.tenants ?? [],
    logs: data.all_logs ?? [],
    totalDecisionsAll: data.total_decisions_all ?? 0,
    totalCostUsdAll: data.total_cost_usd_all ?? 0,
    totalCostClpAll: data.total_cost_clp_all ?? 0,
    totalCreditsDeductedAll: data.total_credits_deducted_all ?? 0,
    avgLatencyMsAll: data.avg_latency_ms_all ?? 0,
    totalAutoAcceptedAll: data.total_auto_accepted_all ?? 0,
    totalFlaggedWarningAll: data.total_flagged_warning_all ?? 0,
    totalFallbackLlmAll: data.total_fallback_llm_all ?? 0,
    estimatedSavingsUsdAll: data.estimated_savings_usd_all ?? 0,
    estimatedSavingsClpAll: data.estimated_savings_clp_all ?? 0,
    totalRecords: data.total_logs_count ?? data.total_decisions_all ?? 0,
    isLoading,
    isError,
    error,
    refetch,
    viewMode,
    setViewMode,
    page,
    setPage,
    pageSize,
    setPageSize,
    search,
    setSearch,
    callerFeature,
    setCallerFeature,
    decisionPrimitive,
    setDecisionPrimitive,
    calibratedAction,
    setCalibratedAction,
    holdingId,
    setHoldingId,
    tenantId,
    setTenantId,
  };
}
