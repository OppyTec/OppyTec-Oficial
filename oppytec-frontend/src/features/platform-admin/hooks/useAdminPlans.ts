import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import {
  MOCK_SYSTEM_PLANS,
  SYSTEM_MODULE_CATALOG,
  type SystemModuleCatalogItem,
  type SystemPlan,
  type SystemPlanCreateRequest,
  type SystemPlanUpdateRequest,
} from "../types";

export interface UseAdminPlansReturn {
  readonly plans: readonly SystemPlan[];
  readonly isLoading: boolean;
  readonly isError: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
  readonly createPlan: (plan: SystemPlanCreateRequest) => Promise<SystemPlan>;
  readonly updatePlan: (slug: string, plan: SystemPlanUpdateRequest) => Promise<SystemPlan>;
  readonly deletePlan: (slug: string) => Promise<SystemPlan>;
  readonly isCreating: boolean;
  readonly isUpdating: boolean;
  readonly isDeleting: boolean;
  readonly moduleCatalog: readonly SystemModuleCatalogItem[];
}

export function useAdminPlans(): UseAdminPlansReturn {
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
      lastEvent?.eventType === "saas.plan_changed" ||
      lastEvent?.eventType?.startsWith("saas.plan")
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.plans(),
      });
    }
  }, [realtimeEvents, queryClient]);

  // Listener para sincronización local multiventana
  useEffect(() => {
    const handleSync = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.platformAdmin.plans(),
      });
    };
    window.addEventListener("admin_plans_changed", handleSync);
    return () => {
      window.removeEventListener("admin_plans_changed", handleSync);
    };
  }, [queryClient]);

  // Query de planes
  const {
    data: plans = MOCK_SYSTEM_PLANS,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<readonly SystemPlan[]>({
    queryKey: queryKeys.platformAdmin.plans(),
    queryFn: async () => {
      const res = await apiRequest<readonly SystemPlan[]>("/api/v1/platform-admin/plans", {
        method: "GET",
        fallbackData: MOCK_SYSTEM_PLANS,
      });
      return res.data;
    },
    staleTime: 30_000,
  });

  // Mutación: Crear Plan
  const createMutation = useMutation({
    mutationFn: async (payload: SystemPlanCreateRequest) => {
      const res = await apiRequest<SystemPlan>("/api/v1/platform-admin/plans", {
        method: "POST",
        body: payload,
      });
      return res.data;
    },
    onSuccess: (newPlan) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.platformAdmin.plans() });
      toast.success(`Plan '${newPlan.name}' creado exitosamente`);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("admin_plans_changed"));
      }
    },
    onError: (err: any) => {
      const msg = err?.message || "Error al crear el plan comercial";
      toast.error(msg);
    },
  });

  // Mutación: Actualizar Plan
  const updateMutation = useMutation({
    mutationFn: async ({ slug, plan }: { slug: string; plan: SystemPlanUpdateRequest }) => {
      const res = await apiRequest<SystemPlan>(`/api/v1/platform-admin/plans/${slug}`, {
        method: "PUT",
        body: plan,
      });
      return res.data;
    },
    onSuccess: (updated) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.platformAdmin.plans() });
      toast.success(`Plan '${updated.name}' actualizado exitosamente`);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("admin_plans_changed"));
      }
    },
    onError: (err: any) => {
      const msg = err?.message || "Error al actualizar el plan comercial";
      toast.error(msg);
    },
  });

  // Mutación: Eliminar Plan
  const deleteMutation = useMutation({
    mutationFn: async (slug: string) => {
      const res = await apiRequest<SystemPlan>(`/api/v1/platform-admin/plans/${slug}`, {
        method: "DELETE",
      });
      return res.data;
    },
    onSuccess: (deleted) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.platformAdmin.plans() });
      toast.success(`Plan '${deleted.name}' eliminado exitosamente`);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("admin_plans_changed"));
      }
    },
    onError: (err: any) => {
      const msg =
        err?.message?.includes("409")
          ? "No se puede eliminar el plan porque tiene clientes activos suscritos"
          : err?.message || "Error al eliminar el plan comercial";
      toast.error(msg);
    },
  });

  return {
    plans,
    isLoading,
    isError,
    error,
    refetch,
    createPlan: async (plan: SystemPlanCreateRequest) => createMutation.mutateAsync(plan),
    updatePlan: async (slug: string, plan: SystemPlanUpdateRequest) =>
      updateMutation.mutateAsync({ slug, plan }),
    deletePlan: async (slug: string) => deleteMutation.mutateAsync(slug),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    moduleCatalog: SYSTEM_MODULE_CATALOG,
  };
}

export { SYSTEM_MODULE_CATALOG };
