import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type { PlantillaRutina, Tarea, TareaEstado, TareaUrgencia } from "../types";
import { MOCK_PLANTILLAS, MOCK_TAREAS } from "../mockData";

export interface UseTareasFilters {
  area_id?: string;
  estado?: TareaEstado;
  asignado_a_user_id?: number;
  solo_mis_tareas?: boolean;
}

export function useTareas(filters?: UseTareasFilters) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  // Reactive subscription without polling
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Isolated tests or outside provider
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const last = realtimeEvents[realtimeEvents.length - 1];
    if (
      last?.eventType?.startsWith("actividades.tareas") ||
      last?.eventType?.startsWith("operations.tareas") ||
      last?.channel === "activities"
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    }
  }, [realtimeEvents, queryClient, tenantId]);

  // Query: Tareas
  const tareasQuery = useQuery({
    queryKey: queryKeys.activities.tareas(tenantId, filters as Record<string, unknown>),
    queryFn: async (): Promise<Tarea[]> => {
      const params = new URLSearchParams();
      if (filters?.area_id && filters.area_id !== "all") {
        params.append("area_id", filters.area_id);
      }
      if (filters?.estado) {
        params.append("estado", filters.estado);
      }
      if (filters?.asignado_a_user_id) {
        params.append("asignado_a_user_id", String(filters.asignado_a_user_id));
      }
      if (filters?.solo_mis_tareas) {
        params.append("solo_mis_tareas", "true");
      }
      const q = params.toString() ? `?${params.toString()}` : "";
      const res = await apiRequest<Tarea[]>(`/api/v1/actividades/tareas${q}`, {
        fallbackData: MOCK_TAREAS,
      });
      return res.data;
    },
    staleTime: 1000 * 60,
  });

  // Query: Plantillas de Rutinas
  const plantillasQuery = useQuery({
    queryKey: queryKeys.activities.plantillas(tenantId),
    queryFn: async (): Promise<PlantillaRutina[]> => {
      const res = await apiRequest<PlantillaRutina[]>("/api/v1/actividades/rutinas/plantillas", {
        fallbackData: MOCK_PLANTILLAS,
      });
      return res.data;
    },
    staleTime: 1000 * 60 * 5,
  });

  // Mutation: Crear Tarea
  const createTareaMutation = useMutation({
    mutationFn: async (payload: {
      titulo: string;
      descripcion?: string | null;
      asignado_a_user_id?: number | null;
      area_id?: string | null;
      estado?: TareaEstado;
      urgencia?: TareaUrgencia;
      fecha_limite?: string | null;
      compra_id?: string | null;
      foto_evidencia_url?: string | null;
    }) => {
      return apiRequest<Tarea>("/api/v1/actividades/tareas", {
        method: "POST",
        body: payload,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    },
  });

  // Mutation: Actualizar Tarea
  const updateTareaMutation = useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: {
      id: number;
      titulo?: string;
      descripcion?: string | null;
      asignado_a_user_id?: number | null;
      area_id?: string | null;
      estado?: TareaEstado;
      urgencia?: TareaUrgencia;
      fecha_limite?: string | null;
      nota_incompleta?: string | null;
      compra_id?: string | null;
    }) => {
      return apiRequest<Tarea>(`/api/v1/actividades/tareas/${id}`, {
        method: "PUT",
        body: payload,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    },
  });

  // Mutation: Cambiar Estado (con nota incompleta obligatoria si aplica)
  const updateEstadoMutation = useMutation({
    mutationFn: async ({
      id,
      estado,
      nota_incompleta,
      foto_evidencia_url,
      completada,
    }: {
      id: number;
      estado: TareaEstado;
      nota_incompleta?: string | null;
      foto_evidencia_url?: string | null;
      completada?: boolean;
    }) => {
      return apiRequest<Tarea>(`/api/v1/actividades/tareas/${id}/estado`, {
        method: "PATCH",
        body: {
          estado,
          nota_incompleta: nota_incompleta ?? null,
          foto_evidencia_url: foto_evidencia_url ?? null,
          completada: completada ?? (estado === "completada"),
        },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    },
  });

  // Mutation: Eliminar Tarea
  const deleteTareaMutation = useMutation({
    mutationFn: async (id: number) => {
      return apiRequest<void>(`/api/v1/actividades/tareas/${id}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    },
  });

  // Mutation: Aplicar Plantilla de Rutina
  const aplicarPlantillaMutation = useMutation({
    mutationFn: async ({
      plantillaId,
      asignado_a_user_id,
      area_id,
      fecha_limite,
    }: {
      plantillaId: number;
      asignado_a_user_id?: number | null;
      area_id?: string | null;
      fecha_limite?: string | null;
    }) => {
      return apiRequest<Tarea[]>(`/api/v1/actividades/rutinas/plantillas/${plantillaId}/aplicar`, {
        method: "POST",
        body: {
          asignado_a_user_id: asignado_a_user_id ?? null,
          area_id: area_id ?? null,
          fecha_limite: fecha_limite ?? null,
        },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    },
  });

  return {
    tareas: tareasQuery.data ?? MOCK_TAREAS,
    plantillas: plantillasQuery.data ?? MOCK_PLANTILLAS,
    isLoading: tareasQuery.isLoading,
    isError: tareasQuery.isError,
    createTarea: createTareaMutation.mutateAsync,
    updateTarea: updateTareaMutation.mutateAsync,
    updateEstado: updateEstadoMutation.mutateAsync,
    deleteTarea: deleteTareaMutation.mutateAsync,
    aplicarPlantilla: aplicarPlantillaMutation.mutateAsync,
    refetch: () => {
      void tareasQuery.refetch();
    },
  };
}
