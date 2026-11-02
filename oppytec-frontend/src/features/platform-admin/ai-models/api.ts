import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import {
  type AiModelCreatePayload,
  type AiModelItem,
  type AiModelUpdatePayload,
  MOCK_AI_MODELS,
} from "./types";

export interface UseAiModelsFilters {
  readonly tier?: string;
  readonly search?: string;
  readonly status?: "all" | "active" | "inactive";
}

export interface UseAiModelsReturn {
  readonly models: readonly AiModelItem[];
  readonly rawModels: readonly AiModelItem[];
  readonly isLoading: boolean;
  readonly isError: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
  readonly createModel: (payload: AiModelCreatePayload) => Promise<AiModelItem>;
  readonly updateModel: (slug: string, payload: AiModelUpdatePayload) => Promise<AiModelItem>;
  readonly deleteModel: (slug: string) => Promise<AiModelItem>;
  readonly isCreating: boolean;
  readonly isUpdating: boolean;
  readonly isDeleting: boolean;
}

export async function fetchAiModels(): Promise<readonly AiModelItem[]> {
  const res = await apiRequest<readonly AiModelItem[]>("/api/v1/platform-admin/ai-models", {
    method: "GET",
    fallbackData: MOCK_AI_MODELS,
  });
  return Array.isArray(res.data) ? res.data : MOCK_AI_MODELS;
}

export async function postAiModel(payload: AiModelCreatePayload): Promise<AiModelItem> {
  const res = await apiRequest<AiModelItem>("/api/v1/platform-admin/ai-models", {
    method: "POST",
    body: payload,
  });
  return res.data;
}

export async function putAiModel(slug: string, payload: AiModelUpdatePayload): Promise<AiModelItem> {
  const res = await apiRequest<AiModelItem>(`/api/v1/platform-admin/ai-models/${encodeURIComponent(slug)}`, {
    method: "PUT",
    body: payload,
  });
  return res.data;
}

export async function deleteAiModelApi(slug: string): Promise<AiModelItem> {
  const res = await apiRequest<AiModelItem>(`/api/v1/platform-admin/ai-models/${encodeURIComponent(slug)}`, {
    method: "DELETE",
  });
  return res.data;
}

export function useAiModels(filters?: UseAiModelsFilters): UseAiModelsReturn {
  const queryClient = useQueryClient();

  // Suscripción Realtime Push WebSocket
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Entorno decoupled o testing
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType?.startsWith("ai_model.") ||
      lastEvent?.eventType === "saas.ai_models_changed"
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.aiModels(),
      });
    }
  }, [realtimeEvents, queryClient]);

  // Listener de eventos locales multiventana
  useEffect(() => {
    const handleSync = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.aiModels(),
      });
    };
    window.addEventListener("admin_ai_models_changed", handleSync);
    return () => {
      window.removeEventListener("admin_ai_models_changed", handleSync);
    };
  }, [queryClient]);

  // Query principal
  const {
    data: allModels = MOCK_AI_MODELS,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<readonly AiModelItem[]>({
    queryKey: queryKeys.platformAdmin.aiModels(),
    queryFn: fetchAiModels,
    staleTime: 30_000,
  });

  // Mutación: Crear Modelo
  const createMutation = useMutation({
    mutationFn: postAiModel,
    onSuccess: (newModel) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.platformAdmin.aiModels() });
      toast.success(`Modelo '${newModel.display_name || newModel.model_slug}' registrado exitosamente`);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("admin_ai_models_changed"));
      }
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al registrar el modelo");
    },
  });

  // Mutación: Actualizar Modelo
  const updateMutation = useMutation({
    mutationFn: ({ slug, payload }: { slug: string; payload: AiModelUpdatePayload }) =>
      putAiModel(slug, payload),
    onSuccess: (updated) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.platformAdmin.aiModels() });
      toast.success(`Modelo '${updated.display_name || updated.model_slug}' actualizado exitosamente`);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("admin_ai_models_changed"));
      }
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al actualizar el modelo");
    },
  });

  // Mutación: Eliminar / Soft-Delete
  const deleteMutation = useMutation({
    mutationFn: (slug: string) => deleteAiModelApi(slug),
    onSuccess: (deleted) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.platformAdmin.aiModels() });
      toast.success(`Modelo '${deleted?.display_name || deleted?.model_slug || "seleccionado"}' desactivado lógicamente`);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("admin_ai_models_changed"));
      }
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al eliminar el modelo");
    },
  });

  // Filtrado reactivo en memoria
  const filteredModels = allModels.filter((model) => {
    // Si ya está borrado lógicamente, se excluye de la lista activa
    if (model.is_deleted) return false;

    // Filtro por Tier
    if (filters?.tier && filters.tier !== "ALL" && model.engine_tier !== filters.tier) {
      return false;
    }

    // Filtro por Estado
    if (filters?.status === "active" && !model.is_enabled) {
      return false;
    }
    if (filters?.status === "inactive" && model.is_enabled) {
      return false;
    }

    // Filtro por búsqueda
    if (filters?.search && filters.search.trim().length > 0) {
      const q = filters.search.toLowerCase().trim();
      const matchSlug = model.model_slug.toLowerCase().includes(q);
      const matchName = model.display_name.toLowerCase().includes(q);
      const matchProvider = model.provider.toLowerCase().includes(q);
      if (!matchSlug && !matchName && !matchProvider) {
        return false;
      }
    }

    return true;
  });

  return {
    models: filteredModels,
    rawModels: allModels,
    isLoading,
    isError,
    error,
    refetch,
    createModel: createMutation.mutateAsync,
    updateModel: (slug, payload) => updateMutation.mutateAsync({ slug, payload }),
    deleteModel: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
