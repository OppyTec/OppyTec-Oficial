import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect } from "react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import {
  MOCK_SAAS_POLICY,
  type SaaSAIPolicy,
  type SaaSAIPolicyUpdateRequest,
} from "../types";

export interface CommercialMarginResult {
  readonly costClp: number;
  readonly marginPct: number;
  readonly isProfitable: boolean;
}

/**
 * Calcula los tokens equivalentes mensuales a partir de una cuota de créditos y la tasa técnica de conversión.
 */
export function simulateTokensMonthly(credits: number, tokensPerCredit: number): number {
  if (credits <= 0 || tokensPerCredit <= 0) return 0;
  return credits * tokensPerCredit;
}

/**
 * Calcula el margen comercial bruto (%) comparando el costo real de API en USD contra el precio de venta en CLP.
 * Margen saludable objetivo en OppyTec SaaS: >= 90%.
 */
export function calculateCommercialMargin(
  costUsd: number,
  packPriceClp: number,
  fxRateClpPerUsd: number = 950
): CommercialMarginResult {
  const costClp = Math.round(costUsd * fxRateClpPerUsd);
  if (packPriceClp <= 0) {
    return {
      costClp,
      marginPct: 0,
      isProfitable: false,
    };
  }

  const rawMarginPct = ((packPriceClp - costClp) / packPriceClp) * 100;
  const marginPct = Math.round((rawMarginPct + Number.EPSILON) * 100) / 100;
  const isProfitable = marginPct >= 90;

  return {
    costClp,
    marginPct,
    isProfitable,
  };
}

export interface UseSaaSQuotaPolicyReturn {
  readonly policy: SaaSAIPolicy;
  readonly isLoading: boolean;
  readonly isError: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
  readonly updatePolicy: (payload: SaaSAIPolicyUpdateRequest) => Promise<SaaSAIPolicy>;
  readonly isUpdating: boolean;
  readonly simulateTokens: (credits: number) => number;
  readonly calculateMargin: (
    costUsd: number,
    packPriceClp: number,
    fxRate?: number
  ) => CommercialMarginResult;
}

export function useSaaSQuotaPolicy(): UseSaaSQuotaPolicyReturn {
  const queryClient = useQueryClient();

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
      lastEvent?.eventType === "saas.policy_updated" ||
      lastEvent?.eventType?.startsWith("saas.policy")
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.saasPolicy(),
      });
    }
  }, [realtimeEvents, queryClient]);

  // Listener de sincronización local
  useEffect(() => {
    const handleSync = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.saasPolicy(),
      });
    };
    window.addEventListener("saas_policy_changed", handleSync);
    return () => {
      window.removeEventListener("saas_policy_changed", handleSync);
    };
  }, [queryClient]);

  // Consulta de política activa
  const {
    data: policy = MOCK_SAAS_POLICY,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<SaaSAIPolicy>({
    queryKey: queryKeys.platformAdmin.saasPolicy(),
    queryFn: async () => {
      const res = await apiRequest<SaaSAIPolicy>(
        "/api/v1/platform-admin/ai-credits/policy",
        {
          method: "GET",
          fallbackData: MOCK_SAAS_POLICY,
        }
      );
      return res.data;
    },
    staleTime: 60_000,
  });

  // Mutación: Actualizar política
  const updateMutation = useMutation({
    mutationFn: async (payload: SaaSAIPolicyUpdateRequest) => {
      const res = await apiRequest<SaaSAIPolicy>(
        "/api/v1/platform-admin/ai-credits/policy",
        {
          method: "PUT",
          body: payload,
        }
      );
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.platformAdmin.saasPolicy() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.platformAdmin.tokenConsumption() });
      toast.success("Política de conversión y créditos SaaS actualizada exitosamente");
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("saas_policy_changed"));
      }
    },
    onError: (err: any) => {
      const msg = err?.message || "Error al actualizar la política de créditos SaaS";
      toast.error(msg);
    },
  });

  const simulateTokens = useCallback(
    (credits: number) => simulateTokensMonthly(credits, policy.tokens_per_credit),
    [policy.tokens_per_credit]
  );

  const calculateMargin = useCallback(
    (costUsd: number, packPriceClp: number, fxRate?: number) =>
      calculateCommercialMargin(costUsd, packPriceClp, fxRate ?? 950),
    []
  );

  return {
    policy,
    isLoading,
    isError,
    error,
    refetch,
    updatePolicy: async (payload: SaaSAIPolicyUpdateRequest) =>
      updateMutation.mutateAsync(payload),
    isUpdating: updateMutation.isPending,
    simulateTokens,
    calculateMargin,
  };
}
