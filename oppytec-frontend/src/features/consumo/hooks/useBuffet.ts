// oppytec-frontend/src/features/consumo/hooks/useBuffet.ts
import { useState, useMemo, useCallback, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type {
  BuffetSession,
  BuffetTemplate,
} from "../types";
import { MOCK_BUFFET_SESSIONS, MOCK_BUFFET_TEMPLATES } from "../mockData";

export interface BuffetSessionStartPayload {
  bodega_id: number | string;
  tipo_servicio: string;
  area_operativa_id?: number | string | null;
  template_id?: string | null;
  estaciones: Array<{
    nombre: string;
    orden: number;
    items?: Array<{
      tipo_item: "producto" | "receta";
      item_id: string;
      cantidad_montada: number;
    }>;
  }>;
}

export interface BuffetItemsUpdatePayload {
  stations: Array<{
    station_id: number | string;
    items: Array<{
      tipo_item: "producto" | "receta";
      item_id: string;
      cantidad_montada?: number;
      cantidad_sobrante?: number;
      cantidad_merma?: number;
    }>;
  }>;
}

export interface BuffetFinalizePayload {
  pax: number;
  leftover_reusable_value?: number;
}

export interface BuffetTemplateCreatePayload {
  nombre: string;
  descripcion?: string | null;
  comensales_estimados?: number;
  estaciones_json: any;
  is_system?: boolean;
  is_public?: boolean;
}

export interface UseBuffetOptions {
  bodegaId?: number | string | null;
  estado?: string | null;
  initialSessionId?: string | null;
}

export function useBuffet(options?: UseBuffetOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";
  const holdingId = context.holdingId || "holding-gastro-sur";

  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    options?.initialSessionId ?? null
  );

  // Suscripción WebSocket zero-polling para buffet
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Offline / unit test
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const latest = realtimeEvents[0];
    if (latest && latest.eventType === "buffet.session_changed") {
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "operations", "buffet"],
      });
      toast.info("Actualización en vivo de sesión de buffet");
    }
  }, [realtimeEvents, queryClient]);

  // ==========================================================================
  // CONSULTAS TANSTACK QUERY V5
  // ==========================================================================

  // 1. Sesiones de buffet
  const sessionsQueryKey = useMemo(
    () =>
      queryKeys.operations.buffetSessions(
        tenantId,
        options?.bodegaId,
        options?.estado
      ),
    [tenantId, options?.bodegaId, options?.estado]
  );

  const {
    data: sessions = MOCK_BUFFET_SESSIONS,
    isLoading: isLoadingSessions,
    refetch: refetchSessions,
  } = useQuery<BuffetSession[]>({
    queryKey: sessionsQueryKey,
    queryFn: async () => {
      let url = "/api/v1/operations/buffet/sessions";
      const params = new URLSearchParams();
      if (options?.bodegaId) params.append("bodega_id", String(options.bodegaId));
      if (options?.estado) params.append("estado", options.estado);
      const queryStr = params.toString();
      if (queryStr) url += `?${queryStr}`;

      const res = await apiRequest<BuffetSession[]>(url, {
        fallbackData: MOCK_BUFFET_SESSIONS,
      });
      return res.data;
    },
  });

  // 2. Detalle de sesión seleccionada
  const activeSession = useMemo(() => {
    if (!Array.isArray(sessions)) return null;
    if (activeSessionId) {
      return sessions.find((s) => String(s.id) === String(activeSessionId)) || null;
    }
    return sessions[0] || null;
  }, [sessions, activeSessionId]);

  // 3. Plantillas de buffet
  const {
    data: templates = MOCK_BUFFET_TEMPLATES,
    isLoading: isLoadingTemplates,
  } = useQuery<BuffetTemplate[]>({
    queryKey: queryKeys.operations.buffetTemplates(tenantId),
    queryFn: async () => {
      const res = await apiRequest<BuffetTemplate[]>(
        "/api/v1/operations/buffet/templates",
        {
          fallbackData: MOCK_BUFFET_TEMPLATES,
        }
      );
      return res.data;
    },
  });

  // ==========================================================================
  // FUNCIONES MATEMÁTICAS PURAS DE CUADRATURA Y COSTEO PAX
  // ==========================================================================

  /**
   * Conciliación matemática de costo por comensal:
   * costo_pax = (costo_montaje - sobrante_reutilizable) / pax
   */
  const calculateCostPerPax = useCallback(
    (
      costoMontaje: number,
      valorSobranteReutilizable: number,
      pax: number
    ): number => {
      if (pax <= 0 || isNaN(pax)) return 0;
      const netCost = Math.max(0, costoMontaje - valorSobranteReutilizable);
      return +(netCost / pax).toFixed(2);
    },
    []
  );

  /**
   * Resumen y totales acumulados de la sesión activa
   */
  const sessionMetrics = useMemo(() => {
    if (!activeSession) {
      return {
        totalMontaje: 0,
        totalSobrante: 0,
        totalConsumido: 0,
        costoNetoPax: 0,
      };
    }

    const totalMontaje = activeSession.costo_total_montaje ?? 0;
    const totalSobrante = activeSession.valor_sobrante_reutilizable ?? 0;
    const pax = activeSession.pax_comensales ?? 0;
    const costoNetoPax = calculateCostPerPax(totalMontaje, totalSobrante, pax);

    return {
      totalMontaje,
      totalSobrante,
      totalConsumido: Math.max(0, totalMontaje - totalSobrante),
      costoNetoPax,
    };
  }, [activeSession, calculateCostPerPax]);

  // ==========================================================================
  // MUTACIONES TRANSACCIONALES
  // ==========================================================================

  // 1. Iniciar nueva sesión
  const startSessionMutation = useMutation({
    mutationFn: async (payload: BuffetSessionStartPayload) => {
      const res = await apiRequest<BuffetSession>(
        "/api/v1/operations/buffet/sessions/start",
        {
          method: "POST",
          body: payload,
          fallbackData: {
            id: `buffet-${Date.now()}`,
            nombre: `Servicio ${payload.tipo_servicio}`,
            tipo_servicio: payload.tipo_servicio,
            bodega_id: String(payload.bodega_id),
            usuario_creador_id: 1,
            estado: "abierto",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            estaciones: payload.estaciones.map((e, idx) => ({
              id: `st-${idx}`,
              nombre_estacion: e.nombre,
              orden: e.orden,
            })),
            items: [],
          },
        }
      );
      return res.data;
    },
    onSuccess: (newSession) => {
      toast.success("Sesión de buffet iniciada");
      setActiveSessionId(String(newSession.id));
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "operations", "buffet"],
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al iniciar sesión de buffet");
    },
  });

  // 2. Actualizar conteos por estación
  const updateItemsMutation = useMutation({
    mutationFn: async ({
      sessionId: _sessionId,
      payload: _payload,
    }: {
      sessionId: number | string;
      payload: BuffetItemsUpdatePayload;
    }) => {
      const res = await apiRequest<BuffetSession>(
        `/api/v1/operations/buffet/sessions/${_sessionId}/items`,
        {
          method: "PUT",
          body: _payload,
          fallbackData: MOCK_BUFFET_SESSIONS[0]!,
        }
      );
      return res.data;
    },
    onSuccess: () => {
      toast.success("Conteos de estación actualizados");
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "operations", "buffet"],
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al actualizar conteos");
    },
  });

  // 3. Liquidar y conciliar sesión
  const finalizeSessionMutation = useMutation({
    mutationFn: async ({
      sessionId: _sessionId,
      payload,
    }: {
      sessionId: number | string;
      payload: BuffetFinalizePayload;
    }) => {
      const res = await apiRequest<BuffetSession>(
        `/api/v1/operations/buffet/sessions/${_sessionId}/finalize`,
        {
          method: "POST",
          body: payload,
          fallbackData: {
            ...MOCK_BUFFET_SESSIONS[0]!,
            estado: "CONCILIADO",
            pax_comensales: payload.pax,
            valor_sobrante_reutilizable: payload.leftover_reusable_value,
          },
        }
      );
      return res.data;
    },
    onSuccess: () => {
      toast.success("Sesión de buffet liquidada exitosamente");
      void queryClient.invalidateQueries({
        queryKey: queryKeys.inventory.stock({ holdingId, tenantId }),
      });
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "operations", "buffet"],
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al liquidar sesión de buffet");
    },
  });

  // 4. Crear plantilla de buffet
  const createTemplateMutation = useMutation({
    mutationFn: async (payload: BuffetTemplateCreatePayload) => {
      const res = await apiRequest<BuffetTemplate>(
        "/api/v1/operations/buffet/templates",
        {
          method: "POST",
          body: payload,
          fallbackData: {
            id: `tpl-${Date.now()}`,
            nombre: payload.nombre,
            descripcion: payload.descripcion,
            comensales_estimados: payload.comensales_estimados,
            estaciones: payload.estaciones_json,
            isPublic: payload.is_public ?? false,
          },
        }
      );
      return res.data;
    },
    onSuccess: () => {
      toast.success("Plantilla de buffet guardada");
      void queryClient.invalidateQueries({
        queryKey: queryKeys.operations.buffetTemplates(tenantId),
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al crear plantilla");
    },
  });

  return {
    sessions,
    isLoadingSessions,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    templates,
    isLoadingTemplates,
    sessionMetrics,
    calculateCostPerPax,
    refetchSessions,
    startSession: startSessionMutation.mutateAsync,
    updateItems: updateItemsMutation.mutateAsync,
    finalizeSession: finalizeSessionMutation.mutateAsync,
    createTemplate: createTemplateMutation.mutateAsync,
    isFinalizing: finalizeSessionMutation.isPending,
  };
}
