import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { isMockDataEnabled, MOCK_DATA_MODE_EVENT_NAME } from "@/shared/mock/mockModeStorage";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type { NotaCategoria, NotaEquipo, NotaPersonal } from "../types";
import { MOCK_NOTAS_EQUIPO, MOCK_NOTAS_PERSONALES } from "../mockData";

export interface UseNotasFilters {
  area_id?: string;
  categoria?: NotaCategoria | "all" | string;
  searchTerm?: string;
}

export function useNotas(filters?: UseNotasFilters) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  // Reactive subscription without polling (Realtime WebSocket tunnel)
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Unmounted or in isolated test runner
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const last = realtimeEvents[realtimeEvents.length - 1];
    if (
      last?.eventType?.startsWith("actividades.notas") ||
      last?.eventType?.startsWith("operations.notas") ||
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

  // Query: Notas de Equipo
  const equipoQuery = useQuery({
    queryKey: queryKeys.activities.notasEquipo(tenantId, {
      area: filters?.area_id,
      cat: filters?.categoria,
    }),
    queryFn: async (): Promise<NotaEquipo[]> => {
      const params = new URLSearchParams();
      if (filters?.area_id && filters.area_id !== "all") {
        params.append("area_id", filters.area_id);
      }
      if (filters?.categoria && filters.categoria !== "all") {
        params.append("categoria", filters.categoria);
      }
      const q = params.toString() ? `?${params.toString()}` : "";
      const res = await apiRequest<NotaEquipo[]>(`/api/v1/actividades/notas/equipo${q}`, {
        fallbackData: isMockDataEnabled() ? MOCK_NOTAS_EQUIPO : [],
      });
      return res.data;
    },
    staleTime: 1000 * 60,
  });

  // Query: Notas Personales
  const personalesQuery = useQuery({
    queryKey: queryKeys.activities.notasPersonales(tenantId, {
      area: filters?.area_id,
    }),
    queryFn: async (): Promise<NotaPersonal[]> => {
      const params = new URLSearchParams();
      if (filters?.area_id && filters.area_id !== "all") {
        params.append("area_id", filters.area_id);
      }
      const q = params.toString() ? `?${params.toString()}` : "";
      const res = await apiRequest<NotaPersonal[]>(`/api/v1/actividades/notas/personales${q}`, {
        fallbackData: isMockDataEnabled() ? MOCK_NOTAS_PERSONALES : [],
      });
      return res.data;
    },
    staleTime: 1000 * 60,
  });

  // Mutation: Crear Nota de Equipo
  const createEquipoMutation = useMutation({
    mutationFn: async (payload: {
      titulo: string;
      contenido: string;
      area_id?: string | null;
      categoria?: string;
      insumo_id?: string | null;
      receta_id?: number | null;
      foto_url?: string | null;
      menciones_user_ids?: number[];
    }) => {
      return apiRequest<NotaEquipo>("/api/v1/actividades/notas/equipo", {
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

  // Mutation: Actualizar Nota de Equipo
  const updateEquipoMutation = useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: {
      id: number;
      titulo?: string;
      contenido?: string;
      area_id?: string | null;
      categoria?: string;
      insumo_id?: string | null;
      foto_url?: string | null;
    }) => {
      return apiRequest<NotaEquipo>(`/api/v1/actividades/notas/equipo/${id}`, {
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

  // Mutation: Eliminar Nota de Equipo
  const deleteEquipoMutation = useMutation({
    mutationFn: async (id: number) => {
      return apiRequest<void>(`/api/v1/actividades/notas/equipo/${id}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    },
  });

  // Mutation: Marcar como Leído
  const markReadMutation = useMutation({
    mutationFn: async (notaId: number) => {
      return apiRequest<{ id: number; nota_id: number; user_id: number }>(
        `/api/v1/actividades/notas/equipo/${notaId}/read`,
        { method: "POST" }
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    },
  });

  // Mutation: Crear Nota Personal
  const createPersonalMutation = useMutation({
    mutationFn: async (payload: {
      titulo: string;
      contenido: string;
      area_id?: string | null;
      fecha?: string | null;
    }) => {
      return apiRequest<NotaPersonal>("/api/v1/actividades/notas/personales", {
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

  // Mutation: Actualizar Nota Personal
  const updatePersonalMutation = useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: {
      id: number;
      titulo?: string;
      contenido?: string;
      area_id?: string | null;
      fecha?: string | null;
    }) => {
      return apiRequest<NotaPersonal>(`/api/v1/actividades/notas/personales/${id}`, {
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

  // Mutation: Eliminar Nota Personal
  const deletePersonalMutation = useMutation({
    mutationFn: async (id: number) => {
      return apiRequest<void>(`/api/v1/actividades/notas/personales/${id}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.all(tenantId),
      });
    },
  });

  return {
    notasEquipo: equipoQuery.data ?? (isMockDataEnabled() ? MOCK_NOTAS_EQUIPO : []),
    notasPersonales: personalesQuery.data ?? (isMockDataEnabled() ? MOCK_NOTAS_PERSONALES : []),
    isLoading: equipoQuery.isLoading || personalesQuery.isLoading,
    isError: equipoQuery.isError || personalesQuery.isError,
    createEquipo: createEquipoMutation.mutateAsync,
    updateEquipo: updateEquipoMutation.mutateAsync,
    deleteEquipo: deleteEquipoMutation.mutateAsync,
    markAsRead: markReadMutation.mutateAsync,
    createPersonal: createPersonalMutation.mutateAsync,
    updatePersonal: updatePersonalMutation.mutateAsync,
    deletePersonal: deletePersonalMutation.mutateAsync,
    refetch: () => {
      void equipoQuery.refetch();
      void personalesQuery.refetch();
    },
  };
}
