// oppytec-frontend/src/features/events/hooks/useSalones.ts
import { useState, useMemo, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { MOCK_DATA_MODE_EVENT_NAME } from "@/shared/mock/mockModeStorage";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import { eventsApi } from "../api/eventsApi";
import type { Salon, SalonCreatePayload, SalonUpdatePayload } from "../types";

export interface UseSalonesOptions {
  areaId?: number | string;
}

export function useSalones(options?: UseSalonesOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  const [selectedAreaId, setSelectedAreaId] = useState<number | string | undefined>(
    options?.areaId
  );

  // Suscripción reactiva sin sondeo
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Si se monta fuera de RealtimeProvider
  }

  // Invalidación automática al recibir eventos de salones
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[realtimeEvents.length - 1];

    if (
      lastEvent?.eventType?.startsWith("events.salones") ||
      lastEvent?.eventType === "salones.changed"
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.events.salones(tenantId),
      });
    }
  }, [realtimeEvents, queryClient, tenantId]);

  useEffect(() => {
    const handleMockModeChange = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.events.salones(tenantId),
      });
    };
    window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
    return () => window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
  }, [queryClient, tenantId]);

  const salonesQuery = useQuery({
    queryKey: queryKeys.events.salones(
      tenantId,
      selectedAreaId !== undefined ? String(selectedAreaId) : undefined
    ),
    queryFn: () => eventsApi.getSalones(selectedAreaId),
    staleTime: 1000 * 60 * 5, // 5 minutos
  });

  const salones = useMemo(() => salonesQuery.data ?? [], [salonesQuery.data]);

  const invalidateSalonesCache = useCallback(async () => {
    await queryClient.invalidateQueries({
      queryKey: queryKeys.events.salones(tenantId),
    });
  }, [queryClient, tenantId]);

  // Mutación: Crear Salón
  const createSalonMutation = useMutation({
    mutationFn: (data: SalonCreatePayload) => eventsApi.createSalon(data),
    onSuccess: (newSalon) => {
      toast.success(`Salón "${newSalon.nombre}" creado exitosamente`);
      void invalidateSalonesCache();
    },
    onError: (err: Error) => {
      toast.error(err.message || "Error al registrar el salón");
    },
  });

  // Mutación: Actualizar Salón
  const updateSalonMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: SalonUpdatePayload }) =>
      eventsApi.updateSalon(id, data),
    onSuccess: (updated) => {
      toast.success(`Salón "${updated.nombre}" actualizado`);
      void invalidateSalonesCache();
    },
    onError: (err: Error) => {
      toast.error(err.message || "Error al actualizar el salón");
    },
  });

  // Mutación: Eliminar Salón
  const deleteSalonMutation = useMutation({
    mutationFn: (id: string) => eventsApi.deleteSalon(id),
    onSuccess: () => {
      toast.success("Salón eliminado");
      void invalidateSalonesCache();
    },
    onError: (err: Error) => {
      toast.error(err.message || "No se pudo eliminar el salón");
    },
  });

  const getSalonById = useCallback(
    (id: string): Salon | undefined => {
      return salones.find((s) => s.id === id);
    },
    [salones]
  );

  return {
    salones,
    selectedAreaId,
    setSelectedAreaId,
    getSalonById,
    isLoading: salonesQuery.isLoading,
    isError: salonesQuery.isError,
    error: salonesQuery.error,
    refetch: salonesQuery.refetch,
    createSalon: createSalonMutation.mutateAsync,
    updateSalon: updateSalonMutation.mutateAsync,
    deleteSalon: deleteSalonMutation.mutateAsync,
    isCreating: createSalonMutation.isPending,
    isUpdating: updateSalonMutation.isPending,
    isDeleting: deleteSalonMutation.isPending,
  };
}
