import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import {
  MOCK_AI_CREDIT_PACKS,
  type AiCreditPackCreatePayload,
  type AiCreditPackItem,
} from "../types";

export interface UseAiCreditPacksOptions {
  readonly isActiveOnly?: boolean;
}

export interface UseAiCreditPacksReturn {
  readonly packs: readonly AiCreditPackItem[];
  readonly isLoading: boolean;
  readonly isError: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
  readonly createPack: (payload: AiCreditPackCreatePayload) => Promise<AiCreditPackItem>;
  readonly isCreating: boolean;
}

export function useAiCreditPacks(options?: UseAiCreditPacksOptions): UseAiCreditPacksReturn {
  const queryClient = useQueryClient();
  const isActiveOnly = options?.isActiveOnly ?? false;

  // Realtime Sync vía WebSocket Push (Zero-Polling)
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
      lastEvent?.eventType === "saas.ai_pack_changed" ||
      lastEvent?.eventType?.startsWith("saas.ai_pack")
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.aiPacks(),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.oppyfy.aiPacks(),
      });
    }
  }, [realtimeEvents, queryClient]);

  // Listener para sincronización local
  useEffect(() => {
    const handleSync = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.aiPacks(),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.oppyfy.aiPacks(),
      });
    };
    window.addEventListener("admin_ai_packs_changed", handleSync);
    return () => {
      window.removeEventListener("admin_ai_packs_changed", handleSync);
    };
  }, [queryClient]);

  // Query de paquetes de créditos IA
  const {
    data: packs = MOCK_AI_CREDIT_PACKS,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<readonly AiCreditPackItem[]>({
    queryKey: queryKeys.platformAdmin.aiPacks(isActiveOnly),
    queryFn: async () => {
      const url = isActiveOnly
        ? "/api/v1/platform-admin/ai-packs?is_active_only=true"
        : "/api/v1/platform-admin/ai-packs";
      const res = await apiRequest<readonly AiCreditPackItem[]>(url, {
        method: "GET",
        fallbackData: MOCK_AI_CREDIT_PACKS,
      });
      return res.data;
    },
    staleTime: 30_000,
  });

  // Mutación: Crear Paquete de Créditos IA
  const createMutation = useMutation({
    mutationFn: async (payload: AiCreditPackCreatePayload) => {
      const res = await apiRequest<AiCreditPackItem>("/api/v1/platform-admin/ai-packs", {
        method: "POST",
        body: payload,
      });
      return res.data;
    },
    onSuccess: (newPack) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.platformAdmin.aiPacks() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.oppyfy.aiPacks() });
      toast.success(`Paquete '${newPack.pack_name}' creado exitosamente`);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("admin_ai_packs_changed"));
      }
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al crear el paquete de créditos IA");
    },
  });

  return {
    packs,
    isLoading,
    isError,
    error,
    refetch,
    createPack: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
  };
}
