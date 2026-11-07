// oppytec-frontend/src/features/events/hooks/useEvents.ts
import { useState, useMemo, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { MOCK_DATA_MODE_EVENT_NAME } from "@/shared/mock/mockModeStorage";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import { eventsApi } from "../api/eventsApi";
import type {
  Evento,
  EventoListItem,
  EventoCreatePayload,
  EventoUpdatePayload,
  EventFilterParams,
  EventoTabType,
  EventExecutionResult,
} from "../types";

/**
 * Helper analítico para calcular el costo estimado consolidado de un evento.
 */
export function getEventEstimatedCost(evento?: Evento | EventoListItem | null): number {
  if (!evento) return 0;

  // Si es un Evento completo con items, recetas y combos detallados
  if ("items" in evento && Array.isArray(evento.items)) {
    const itemsCost = evento.items.reduce((acc, item) => {
      const unit = item.costo_unitario_estimado ?? 0;
      const total = item.costo_total_estimado ?? unit * item.cantidad;
      return acc + total;
    }, 0);

    const recetasCost = (evento.recetas ?? []).reduce((acc, receta) => {
      const unit = receta.costo_unitario_estimado ?? 0;
      const total = receta.costo_estimado ?? unit * receta.porciones;
      return acc + total;
    }, 0);

    const combosCost = (evento.combos ?? []).reduce((acc, combo) => {
      const unit = combo.costo_unitario_estimado ?? 0;
      const total = combo.costo_estimado ?? unit * combo.cantidad;
      return acc + total;
    }, 0);

    return itemsCost + recetasCost + combosCost;
  }

  // Si es EventoListItem con conteos
  return 0;
}

/**
 * Helper para desglosar el resumen de suministros de un evento.
 */
export function getInsumosDesglosados(evento: Evento) {
  const directosCount = evento.items?.length ?? 0;
  const recetasCount = evento.recetas?.length ?? 0;
  const combosCount = evento.combos?.length ?? 0;
  const totalInsumos = directosCount + recetasCount + combosCount;

  return {
    directosCount,
    recetasCount,
    combosCount,
    totalInsumos,
  };
}

export interface UseEventsOptions {
  initialTab?: EventoTabType;
  initialFilters?: EventFilterParams;
}

export function useEvents(options?: UseEventsOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  // Suscripción reactiva sin sondeo (WebSocket push)
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Si se monta fuera de RealtimeProvider (ej. tests unitarios aislados)
  }

  const [activeTab, setActiveTab] = useState<EventoTabType>(options?.initialTab ?? "proximos");
  const [filters, setFilters] = useState<EventFilterParams>(options?.initialFilters ?? {});

  // Invalidación automática de caché al recibir notificación WebSocket del backend
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[realtimeEvents.length - 1];

    if (
      lastEvent?.eventType?.startsWith("events.") ||
      lastEvent?.channel === "events" ||
      lastEvent?.eventType === "events.changed"
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.events.all(tenantId),
      });
    }
  }, [realtimeEvents, queryClient, tenantId]);

  useEffect(() => {
    const handleMockModeChange = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.events.all(tenantId),
      });
    };
    window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
    return () => window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
  }, [queryClient, tenantId]);

  // Consulta principal de eventos
  const eventsQuery = useQuery({
    queryKey: queryKeys.events.list(tenantId, filters as Record<string, unknown>),
    queryFn: () => eventsApi.getEvents(filters),
    staleTime: 1000 * 60 * 2, // 2 minutos
  });

  const rawEvents = useMemo(() => eventsQuery.data ?? [], [eventsQuery.data]);

  // Clasificación por pestañas de estado
  const proximosEvents = useMemo(() => {
    return rawEvents.filter(
      (e) =>
        !e.ejecutado &&
        !e.cancelado &&
        e.estado?.toLowerCase() !== "cancelado" &&
        e.estado?.toLowerCase() !== "ejecutado" &&
        e.estado?.toLowerCase() !== "finalizado"
    );
  }, [rawEvents]);

  const historialEvents = useMemo(() => {
    return rawEvents.filter(
      (e) =>
        e.ejecutado ||
        e.estado?.toLowerCase() === "ejecutado" ||
        e.estado?.toLowerCase() === "finalizado"
    );
  }, [rawEvents]);

  const canceladosEvents = useMemo(() => {
    return rawEvents.filter(
      (e) =>
        e.cancelado ||
        e.estado?.toLowerCase() === "cancelado"
    );
  }, [rawEvents]);

  // Eventos mostrados según la pestaña activa
  const filteredEvents = useMemo(() => {
    switch (activeTab) {
      case "proximos":
        return proximosEvents;
      case "historial":
        return historialEvents;
      case "cancelados":
        return canceladosEvents;
      default:
        return proximosEvents;
    }
  }, [activeTab, proximosEvents, historialEvents, canceladosEvents]);

  // Contadores reactivos para badges de pestaña
  const counts = useMemo(
    () => ({
      proximos: proximosEvents.length,
      historial: historialEvents.length,
      cancelados: canceladosEvents.length,
      total: rawEvents.length,
    }),
    [proximosEvents.length, historialEvents.length, canceladosEvents.length, rawEvents.length]
  );

  // Invalidador genérico de eventos y faltantes
  const invalidateEventsCache = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.events.all(tenantId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.events.faltantes(tenantId) }),
    ]);
  }, [queryClient, tenantId]);

  // Mutación: Crear Evento
  const createEventMutation = useMutation({
    mutationFn: (data: EventoCreatePayload) => eventsApi.createEvent(data),
    onSuccess: (newEvent) => {
      toast.success(`Evento "${newEvent.nombre}" agendado con éxito`);
      void invalidateEventsCache();
    },
    onError: (err: Error) => {
      toast.error(err.message || "Error al agendar el evento");
    },
  });

  // Mutación: Actualizar Evento
  const updateEventMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: EventoUpdatePayload }) =>
      eventsApi.updateEvent(id, data),
    onSuccess: (updated) => {
      toast.success(`Evento "${updated.nombre}" actualizado correctamente`);
      void invalidateEventsCache();
    },
    onError: (err: Error) => {
      toast.error(err.message || "Error al actualizar el evento");
    },
  });

  // Mutación: Eliminar Evento
  const deleteEventMutation = useMutation({
    mutationFn: (id: string) => eventsApi.deleteEvent(id),
    onSuccess: () => {
      toast.success("Evento eliminado del calendario");
      void invalidateEventsCache();
    },
    onError: (err: Error) => {
      toast.error(err.message || "No se pudo eliminar el evento");
    },
  });

  // Mutación: Ejecutar Evento en Kardex
  const executeEventMutation = useMutation({
    mutationFn: (id: string) => eventsApi.executeEvent(id),
    onSuccess: (result: EventExecutionResult) => {
      toast.success(
        `Evento ejecutado con éxito. Se generaron ${result.total_movimientos_kardex} movimientos de Kardex.`
      );
      void invalidateEventsCache();
    },
    onError: (err: Error) => {
      toast.error(err.message || "Error al ejecutar el consumo del evento en Kardex");
    },
  });

  // Mutación: Cancelar Evento
  const cancelEventMutation = useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo?: string }) =>
      eventsApi.cancelEvent(id, motivo),
    onSuccess: (canceled) => {
      toast.success(`Evento "${canceled.nombre}" marcado como cancelado`);
      void invalidateEventsCache();
    },
    onError: (err: Error) => {
      toast.error(err.message || "No se pudo cancelar el evento");
    },
  });

  // Mutación: Reactivar Evento
  const reactivateEventMutation = useMutation({
    mutationFn: (id: string) => eventsApi.reactivateEvent(id),
    onSuccess: (reactivated) => {
      toast.success(`Evento "${reactivated.nombre}" reactivado en el calendario`);
      void invalidateEventsCache();
    },
    onError: (err: Error) => {
      toast.error(err.message || "No se pudo reactivar el evento");
    },
  });

  return {
    events: filteredEvents,
    allEvents: rawEvents,
    counts,
    activeTab,
    setActiveTab,
    filters,
    setFilters,
    isLoading: eventsQuery.isLoading,
    isError: eventsQuery.isError,
    error: eventsQuery.error,
    refetch: eventsQuery.refetch,
    createEvent: createEventMutation.mutateAsync,
    updateEvent: updateEventMutation.mutateAsync,
    deleteEvent: deleteEventMutation.mutateAsync,
    executeEvent: executeEventMutation.mutateAsync,
    cancelEvent: cancelEventMutation.mutateAsync,
    reactivateEvent: reactivateEventMutation.mutateAsync,
    isCreating: createEventMutation.isPending,
    isUpdating: updateEventMutation.isPending,
    isDeleting: deleteEventMutation.isPending,
    isExecuting: executeEventMutation.isPending,
    isCanceling: cancelEventMutation.isPending,
    isReactivating: reactivateEventMutation.isPending,
  };
}
