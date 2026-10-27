import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import {
  MOCK_TOKEN_CONSUMPTION,
  type CreditQuotaAdjustmentResponse,
  type HoldingCreditsUpdatePayload,
  type HoldingGroup,
  type TenantCreditsUpdatePayload,
  type TokenConsumptionResponse,
  type TokenLogItem,
} from "../types";

export interface HoldingCreditsAdjustmentArgs {
  readonly holdingId: string;
  readonly monthly_credits?: number;
  readonly limit?: number;
  readonly distribution_mode?: "shared" | "per_tenant";
  readonly distributionMode?: "shared" | "per_tenant";
}

export interface TenantCreditsAdjustmentArgs {
  readonly tenantId: string;
  readonly monthly_credits?: number;
  readonly limit?: number;
}

export interface UseTokenConsumptionOptions {
  readonly initialPage?: number;
  readonly initialPageSize?: number;
  readonly initialSearch?: string;
  readonly initialHoldingId?: string | null;
  readonly initialTenantId?: string | null;
  readonly initialModelName?: string | null;
  readonly initialApiSuccess?: boolean | null;
  readonly initialStartDate?: string | null;
  readonly initialEndDate?: string | null;
  readonly initialViewMode?: "credits" | "tokens";
}

export interface UseTokenConsumptionReturn {
  readonly data: TokenConsumptionResponse;
  readonly holdings: readonly HoldingGroup[];
  readonly logs: readonly TokenLogItem[];
  readonly totalRecords: number;
  readonly totalTokensAll: number;
  readonly totalCostUsdAll: number;
  readonly totalCostClpAll: number;
  readonly totalCreditsUsedAll: number;
  readonly tokensPerCredit: number;
  readonly isLoading: boolean;
  readonly isError: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
  // Estado de vista dual
  readonly viewMode: "credits" | "tokens";
  readonly setViewMode: (mode: "credits" | "tokens") => void;
  // Filtros reactivos
  readonly page: number;
  readonly setPage: (page: number) => void;
  readonly pageSize: number;
  readonly setPageSize: (size: number) => void;
  readonly search: string;
  readonly setSearch: (s: string) => void;
  readonly holdingId: string | null;
  readonly setHoldingId: (id: string | null) => void;
  readonly tenantId: string | null;
  readonly setTenantId: (id: string | null) => void;
  readonly modelName: string | null;
  readonly setModelName: (m: string | null) => void;
  readonly apiSuccess: boolean | null;
  readonly setApiSuccess: (val: boolean | null) => void;
  readonly startDate: string | null;
  readonly setStartDate: (date: string | null) => void;
  readonly endDate: string | null;
  readonly setEndDate: (date: string | null) => void;
  // Mutaciones de Ajuste de Cupos
  readonly updateHoldingCredits: {
    (holdingId: string, limit: number, distributionMode?: string): Promise<CreditQuotaAdjustmentResponse>;
    (payload: HoldingCreditsAdjustmentArgs): Promise<CreditQuotaAdjustmentResponse>;
  };
  readonly updateTenantCredits: {
    (tenantId: string, limit: number): Promise<CreditQuotaAdjustmentResponse>;
    (payload: TenantCreditsAdjustmentArgs): Promise<CreditQuotaAdjustmentResponse>;
  };
  readonly isUpdatingQuota: boolean;
}

export function useTokenConsumption(
  options: UseTokenConsumptionOptions = {}
): UseTokenConsumptionReturn {
  const queryClient = useQueryClient();

  const [page, setPage] = useState<number>(options.initialPage ?? 1);
  const [pageSize, setPageSize] = useState<number>(options.initialPageSize ?? 50);
  const [search, setSearch] = useState<string>(options.initialSearch ?? "");
  const [holdingId, setHoldingId] = useState<string | null>(
    options.initialHoldingId ?? null
  );
  const [tenantId, setTenantId] = useState<string | null>(
    options.initialTenantId ?? null
  );
  const [modelName, setModelName] = useState<string | null>(
    options.initialModelName ?? null
  );
  const [apiSuccess, setApiSuccess] = useState<boolean | null>(
    options.initialApiSuccess ?? null
  );
  const [startDate, setStartDate] = useState<string | null>(
    options.initialStartDate ?? null
  );
  const [endDate, setEndDate] = useState<string | null>(
    options.initialEndDate ?? null
  );
  const [viewMode, setViewMode] = useState<"credits" | "tokens">(
    options.initialViewMode ?? "credits"
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
      lastEvent?.eventType === "oppyfy.token_consumed" ||
      lastEvent?.eventType === "oppyfy.quota_adjusted" ||
      lastEvent?.eventType === "saas.policy_updated" ||
      lastEvent?.eventType?.startsWith("oppyfy.")
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.tokenConsumption(),
      });
    }
  }, [realtimeEvents, queryClient]);

  // Listener local de sincronización
  useEffect(() => {
    const handleSync = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.tokenConsumption(),
      });
    };
    window.addEventListener("token_consumption_changed", handleSync);
    return () => {
      window.removeEventListener("token_consumption_changed", handleSync);
    };
  }, [queryClient]);

  const queryFilters = useMemo(
    () => ({
      page,
      pageSize,
      search: search.trim() || undefined,
      holdingId: holdingId ?? undefined,
      tenantId: tenantId ?? undefined,
      modelName: modelName ?? undefined,
      apiSuccess: apiSuccess !== null ? apiSuccess : undefined,
      startDate: startDate ?? undefined,
      endDate: endDate ?? undefined,
    }),
    [page, pageSize, search, holdingId, tenantId, modelName, apiSuccess, startDate, endDate]
  );

  const queryKey = useMemo(
    () => queryKeys.platformAdmin.tokenConsumption(queryFilters),
    [queryFilters]
  );

  const {
    data = MOCK_TOKEN_CONSUMPTION,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<TokenConsumptionResponse>({
    queryKey,
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append("page", String(page));
      params.append("page_size", String(pageSize));
      if (search.trim()) params.append("search", search.trim());
      if (holdingId) params.append("holding_id", holdingId);
      if (tenantId) params.append("tenant_id", tenantId);
      if (modelName) params.append("model_name", modelName);
      if (apiSuccess !== null) params.append("api_success", String(apiSuccess));
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);

      const qs = params.toString();
      const endpoint = `/api/v1/platform-admin/token-consumption${qs ? `?${qs}` : ""}`;

      const res = await apiRequest<TokenConsumptionResponse>(endpoint, {
        method: "GET",
        fallbackData: MOCK_TOKEN_CONSUMPTION,
      });
      return res.data;
    },
    staleTime: 15_000,
  });

  // Mutación: Ajustar Cupo de Holding
  const updateHoldingMutation = useMutation({
    mutationFn: async ({
      holdingId: targetHoldingId,
      monthly_credits,
      distribution_mode,
    }: { holdingId: string } & HoldingCreditsUpdatePayload) => {
      const res = await apiRequest<CreditQuotaAdjustmentResponse>(
        `/api/v1/platform-admin/holdings/${targetHoldingId}/ai-credits`,
        {
          method: "PATCH",
          body: {
            monthly_credits,
            distribution_mode: distribution_mode ?? "shared",
          },
        }
      );
      const data = res.data;
      return {
        target_id: data.target_id,
        target_type: data.target_type ?? "holding",
        monthly_credit_limit: data.monthly_credit_limit ?? data.monthly_credits ?? monthly_credits,
        monthly_credits: data.monthly_credits ?? monthly_credits,
        credit_distribution_mode: data.credit_distribution_mode ?? distribution_mode ?? "shared",
        updated_at: data.updated_at ?? new Date().toISOString(),
        updated_by: data.updated_by ?? "SuperUser Platform Admin",
        message: data.message ?? "Cuota de créditos de Holding actualizada exitosamente",
      };
    },
    onSuccess: (resp) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.tokenConsumption(),
      });
      toast.success(
        resp.message || `Cupo de Holding actualizado a ${resp.monthly_credits ?? resp.monthly_credit_limit} créditos`
      );
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("token_consumption_changed"));
      }
    },
    onError: (err: any) => {
      const msg = err?.message || "Error al actualizar el cupo de créditos del holding";
      toast.error(msg);
    },
  });

  // Mutación: Ajustar Cupo de Tenant
  const updateTenantMutation = useMutation({
    mutationFn: async ({
      tenantId: targetTenantId,
      monthly_credits,
    }: { tenantId: string } & TenantCreditsUpdatePayload) => {
      const res = await apiRequest<CreditQuotaAdjustmentResponse>(
        `/api/v1/platform-admin/tenants/${targetTenantId}/ai-credits`,
        {
          method: "PATCH",
          body: { monthly_credits },
        }
      );
      const data = res.data;
      return {
        target_id: data.target_id,
        target_type: data.target_type ?? "tenant",
        monthly_credit_limit: data.monthly_credit_limit ?? data.monthly_credits ?? monthly_credits,
        monthly_credits: data.monthly_credits ?? monthly_credits,
        credit_distribution_mode: null,
        updated_at: data.updated_at ?? new Date().toISOString(),
        updated_by: data.updated_by ?? "SuperUser Platform Admin",
        message: data.message ?? "Cuota de créditos de Tenant actualizada exitosamente",
      };
    },
    onSuccess: (resp) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.tokenConsumption(),
      });
      toast.success(
        resp.message || `Cupo de Tenant actualizado a ${resp.monthly_credits ?? resp.monthly_credit_limit} créditos`
      );
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("token_consumption_changed"));
      }
    },
    onError: (err: any) => {
      const msg = err?.message || "Error al actualizar el cupo de créditos de la sucursal";
      toast.error(msg);
    },
  });

  const updateHoldingCredits = async (
    holdingIdOrPayload: string | HoldingCreditsAdjustmentArgs,
    limit?: number,
    distributionMode?: string
  ): Promise<CreditQuotaAdjustmentResponse> => {
    if (typeof holdingIdOrPayload === "string") {
      return updateHoldingMutation.mutateAsync({
        holdingId: holdingIdOrPayload,
        monthly_credits: limit ?? 0,
        distribution_mode: (distributionMode ?? "shared") as "shared" | "per_tenant",
      });
    }
    return updateHoldingMutation.mutateAsync({
      holdingId: holdingIdOrPayload.holdingId,
      monthly_credits: holdingIdOrPayload.monthly_credits ?? holdingIdOrPayload.limit ?? 0,
      distribution_mode: (holdingIdOrPayload.distribution_mode ?? holdingIdOrPayload.distributionMode ?? "shared") as "shared" | "per_tenant",
    });
  };

  const updateTenantCredits = async (
    tenantIdOrPayload: string | TenantCreditsAdjustmentArgs,
    limit?: number
  ): Promise<CreditQuotaAdjustmentResponse> => {
    if (typeof tenantIdOrPayload === "string") {
      return updateTenantMutation.mutateAsync({
        tenantId: tenantIdOrPayload,
        monthly_credits: limit ?? 0,
      });
    }
    return updateTenantMutation.mutateAsync({
      tenantId: tenantIdOrPayload.tenantId,
      monthly_credits: tenantIdOrPayload.monthly_credits ?? tenantIdOrPayload.limit ?? 0,
    });
  };

  return {
    data,
    holdings: data.holdings,
    logs: data.logs,
    totalRecords: data.total_records,
    totalTokensAll: data.total_tokens_all,
    totalCostUsdAll: data.total_cost_usd_all,
    totalCostClpAll: data.total_cost_clp_all,
    totalCreditsUsedAll: data.total_credits_used_all,
    tokensPerCredit: data.tokens_per_credit,
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
    holdingId,
    setHoldingId,
    tenantId,
    setTenantId,
    modelName,
    setModelName,
    apiSuccess,
    setApiSuccess,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    updateHoldingCredits,
    updateTenantCredits,
    isUpdatingQuota: updateHoldingMutation.isPending || updateTenantMutation.isPending,
  };
}
