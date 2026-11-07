import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { isMockDataEnabled, MOCK_DATA_MODE_EVENT_NAME } from "@/shared/mock/mockModeStorage";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type { TurnoHorario, ValidacionLaboral } from "../types";
import { MOCK_TURNOS } from "../mockData";

export interface UseHorariosFilters {
  user_id?: number;
  area_id?: string;
  fecha_inicio?: string;
  fecha_fin?: string;
}

export function useHorarios(filters?: UseHorariosFilters) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  // Reactive subscription without polling
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Isolated tests
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const last = realtimeEvents[realtimeEvents.length - 1];
    if (
      last?.eventType?.startsWith("actividades.horarios") ||
      last?.eventType?.startsWith("operations.horarios") ||
      last?.channel === "activities"
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    }
  }, [realtimeEvents, queryClient, tenantId]);

  useEffect(() => {
    const handleMockModeChange = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    };
    window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
    return () => window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
  }, [queryClient, tenantId]);

  // Query: Turnos Horarios
  const turnosQuery = useQuery({
    queryKey: queryKeys.activities.horarios(tenantId, filters as Record<string, unknown>),
    queryFn: async (): Promise<TurnoHorario[]> => {
      const params = new URLSearchParams();
      if (filters?.user_id) params.append("user_id", String(filters.user_id));
      if (filters?.area_id && filters.area_id !== "all") params.append("area_id", filters.area_id);
      if (filters?.fecha_inicio) params.append("fecha_inicio", filters.fecha_inicio);
      if (filters?.fecha_fin) params.append("fecha_fin", filters.fecha_fin);

      const q = params.toString() ? `?${params.toString()}` : "";
      const res = await apiRequest<TurnoHorario[]>(`/api/v1/actividades/horarios${q}`, {
        fallbackData: isMockDataEnabled() ? MOCK_TURNOS : [],
      });
      return res.data;
    },
    staleTime: 1000 * 60,
  });

  // Mutation: Crear Turno
  const createTurnoMutation = useMutation({
    mutationFn: async (payload: {
      user_id: number;
      area_id?: string | null;
      fecha_inicio?: string | null;
      fecha_fin?: string | null;
      hora_inicio?: string | null;
      hora_fin?: string | null;
      nota?: string | null;
      color?: string | null;
    }) => {
      return apiRequest<TurnoHorario>("/api/v1/actividades/horarios", {
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

  // Mutation: Actualizar Turno
  const updateTurnoMutation = useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: {
      id: number;
      user_id?: number;
      area_id?: string | null;
      fecha_inicio?: string | null;
      fecha_fin?: string | null;
      hora_inicio?: string | null;
      hora_fin?: string | null;
      nota?: string | null;
      color?: string | null;
    }) => {
      return apiRequest<TurnoHorario>(`/api/v1/actividades/horarios/${id}`, {
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

  // Mutation: Eliminar Turno
  const deleteTurnoMutation = useMutation({
    mutationFn: async (id: number) => {
      return apiRequest<void>(`/api/v1/actividades/horarios/${id}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    },
  });

  // Mutation: Clonar Semana Anterior
  const clonarSemanaMutation = useMutation({
    mutationFn: async ({
      fecha_lunes_origen,
      fecha_lunes_destino,
      area_id,
    }: {
      fecha_lunes_origen: string;
      fecha_lunes_destino: string;
      area_id?: string | null;
    }) => {
      return apiRequest<TurnoHorario[]>("/api/v1/actividades/horarios/clonar-semana", {
        method: "POST",
        body: {
          fecha_lunes_origen,
          fecha_lunes_destino,
          area_id: area_id ?? null,
        },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    },
  });

  // Helper Mutation: Validar Alertas Laborales (Legal Guard: Ley 40 Horas / 12h descanso)
  const validarAlertasMutation = useMutation({
    mutationFn: async (payload: {
      user_id: number;
      fecha_inicio?: string | null;
      fecha_fin?: string | null;
      hora_inicio?: string | null;
      hora_fin?: string | null;
      turno_id_excluir?: number | null;
    }): Promise<ValidacionLaboral> => {
      const res = await apiRequest<ValidacionLaboral>("/api/v1/actividades/horarios/validar-alertas", {
        method: "POST",
        body: payload,
      });
      return res.data;
    },
  });

  return {
    turnos: turnosQuery.data ?? (isMockDataEnabled() ? MOCK_TURNOS : []),
    isLoading: turnosQuery.isLoading,
    isError: turnosQuery.isError,
    createTurno: createTurnoMutation.mutateAsync,
    updateTurno: updateTurnoMutation.mutateAsync,
    deleteTurno: deleteTurnoMutation.mutateAsync,
    clonarSemana: clonarSemanaMutation.mutateAsync,
    validarAlertas: validarAlertasMutation.mutateAsync,
    isCloning: clonarSemanaMutation.isPending,
    refetch: () => {
      void turnosQuery.refetch();
    },
  };
}
