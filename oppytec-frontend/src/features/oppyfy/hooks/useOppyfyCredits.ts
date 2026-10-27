/**
 * oppytec-frontend/src/features/oppyfy/hooks/useOppyfyCredits.ts
 * Hook reactivo para la billetera de créditos OppyFy, cupos de trabajadores
 * y catálogo/cotizador de paquetes Add-On (v2.0):
 * - Consulta de saldo sin caducidad (`GET /api/v1/oppyfy/wallets/me`)
 * - Ajuste de cupos y activación de trabajador (`PATCH /api/v1/oppyfy/wallets/{user_id}`)
 * - Catálogo de paquetes de créditos Add-On (`GET /api/v1/platform-admin/ai-packs`)
 * - Cotizador con descuento por plan SaaS base (`GET /api/v1/platform-admin/ai-packs/{pack_id}/quote`)
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import type {
  OppyfyWalletResponse,
  OppyfyWalletPatchRequest,
  AiCreditPackResponse,
  AiCreditPackQuoteResponse,
} from "../types";

export interface UseOppyfyCreditsOptions {
  readonly tenantId?: string;
  readonly isActiveOnlyPacks?: boolean;
}

export function useOppyfyCredits(options?: UseOppyfyCreditsOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = options?.tenantId ?? context.tenantId;

  // 1. Consulta de billetera del usuario autenticado
  const walletQuery = useQuery({
    queryKey: queryKeys.oppyfy.wallet(tenantId),
    queryFn: async (): Promise<OppyfyWalletResponse> => {
      const response = await apiRequest<OppyfyWalletResponse>(
        "/api/v1/oppyfy/wallets/me"
      );
      return response.data;
    },
    staleTime: 1000 * 30, // 30 segundos
  });

  // 2. Catálogo de paquetes Add-On independientes
  const aiPacksQuery = useQuery({
    queryKey: queryKeys.oppyfy.aiPacks(options?.isActiveOnlyPacks),
    queryFn: async (): Promise<AiCreditPackResponse[]> => {
      const queryParam = options?.isActiveOnlyPacks ? "?is_active_only=true" : "";
      const response = await apiRequest<AiCreditPackResponse[]>(
        `/api/v1/platform-admin/ai-packs${queryParam}`
      );
      return response.data;
    },
    staleTime: 1000 * 60 * 10, // 10 minutos
  });

  // 3. Mutación de asignación de cupos de trabajador
  const updateWorkerWalletMutation = useMutation({
    mutationFn: async ({
      userId,
      patch,
    }: {
      userId: number;
      patch: OppyfyWalletPatchRequest;
    }): Promise<OppyfyWalletResponse> => {
      const response = await apiRequest<OppyfyWalletResponse>(
        `/api/v1/oppyfy/wallets/${String(userId)}`,
        {
          method: "PATCH",
          body: patch,
        }
      );
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.oppyfy.wallet(tenantId),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.oppyfy.credits(tenantId),
      });
    },
  });

  // 4. Cotizador de paquetes con descuentos por plan base SaaS
  const quotePack = async (
    packId: number,
    basePlanTier?: string
  ): Promise<AiCreditPackQuoteResponse> => {
    const queryParam = basePlanTier
      ? `?base_plan_tier=${encodeURIComponent(basePlanTier)}`
      : "";
    const response = await apiRequest<AiCreditPackQuoteResponse>(
      `/api/v1/platform-admin/ai-packs/${String(packId)}/quote${queryParam}`
    );
    return response.data;
  };

  return {
    // Billetera
    wallet: walletQuery.data ?? null,
    remainingCredits: walletQuery.data ? Number(walletQuery.data.remaining_credits) : 0,
    allocatedCredits: walletQuery.data ? Number(walletQuery.data.assigned_credits_balance) : 0,
    consumedCredits: walletQuery.data ? Number(walletQuery.data.consumed_credits_total) : 0,
    isOppyfyEnabled: walletQuery.data?.is_oppyfy_enabled ?? false,
    isLoadingWallet: walletQuery.isLoading,
    walletError: walletQuery.error,
    refetchWallet: walletQuery.refetch,

    // Paquetes Add-On
    aiPacks: aiPacksQuery.data ?? [],
    isLoadingPacks: aiPacksQuery.isLoading,
    packsError: aiPacksQuery.error,
    refetchPacks: aiPacksQuery.refetch,

    // Gestión de cupos
    updateWorkerWallet: updateWorkerWalletMutation.mutateAsync,
    isUpdatingWallet: updateWorkerWalletMutation.isPending,
    updateWalletError: updateWorkerWalletMutation.error,

    // Cotización
    quotePack,
  };
}
