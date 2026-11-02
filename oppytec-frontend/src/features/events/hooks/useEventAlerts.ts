// oppytec-frontend/src/features/events/hooks/useEventAlerts.ts
import { useMemo, useEffect, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import { eventsApi } from "../api/eventsApi";
import type {
  FaltanteItem,
  CommittedStockItem,
  EventAlertItem,
} from "../types";

export interface UseEventAlertsOptions {
  areaId?: number | string;
  bodegaId?: number | string;
}

/**
 * Hook reactivo de TanStack Query v5 para Analítica de Stock Comprometido y Alertas Operativas de Eventos.
 * Cumple FASE 7 con paridad 1:1, sincronización WebSocket zero-polling y clasificación por severidad:
 * - CRITICAL: Eventos agendados en < 48h con insumos en quiebre de stock.
 * - WARNING: Eventos agendados en los próximos 14 días con quiebre proyectado.
 */
export function useEventAlerts(options?: UseEventAlertsOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  // Suscripción reactiva sin sondeo (Zero-Polling)
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Modo aislado si se monta fuera de RealtimeProvider
  }

  // Invalidación ante notificaciones WebSockets emitidas por backend (Redis Pub/Sub)
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[realtimeEvents.length - 1];

    if (
      lastEvent?.eventType?.startsWith("inventory.") ||
      lastEvent?.eventType?.startsWith("events.") ||
      lastEvent?.eventType === "inventory.stock_changed" ||
      lastEvent?.eventType === "events.changed" ||
      lastEvent?.eventType === "events.events.changed"
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.events.faltantes(tenantId),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.events.committedStock(tenantId),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.events.alerts(tenantId),
      });
    }
  }, [realtimeEvents, queryClient, tenantId]);

  // 1. Consulta de Faltantes Consolidados (legacy y analítica agregada)
  const faltantesQuery = useQuery({
    queryKey: queryKeys.events.faltantes(
      tenantId,
      options?.areaId !== undefined ? String(options.areaId) : undefined
    ),
    queryFn: () => eventsApi.getFaltantesAnalytics(options?.areaId),
    staleTime: 1000 * 60 * 2, // 2 minutos
  });

  // 2. Consulta de Stock Comprometido (demanda futura reservada y saldo libre)
  const committedStockQuery = useQuery({
    queryKey: queryKeys.events.committedStock(
      tenantId,
      options?.bodegaId !== undefined ? String(options.bodegaId) : undefined
    ),
    queryFn: () => eventsApi.getCommittedStock(options?.bodegaId),
    staleTime: 1000 * 60 * 2,
  });

  // 3. Consulta de Alertas Operativas de Eventos clasificadas por severidad
  const alertsQuery = useQuery({
    queryKey: queryKeys.events.alerts(tenantId),
    queryFn: () => eventsApi.getEventAlerts(),
    staleTime: 1000 * 60 * 2,
  });

  // Procesamiento de datos de faltantes
  const faltantesData = faltantesQuery.data;
  const items: FaltanteItem[] = useMemo(() => faltantesData?.items ?? [], [faltantesData]);
  const totalFaltantes = faltantesData?.total_faltantes ?? items.length;
  const eventosAfectadosCount = faltantesData?.eventos_afectados_count ?? 0;
  const hasShortages = items.length > 0;

  // Procesamiento de Stock Comprometido
  const committedStockData = committedStockQuery.data;
  const committedStock: CommittedStockItem[] = useMemo(
    () => committedStockData?.items ?? [],
    [committedStockData]
  );
  const totalCommittedItems = committedStockData?.total_items ?? committedStock.length;

  // Procesamiento de Alertas Operativas por Severidad
  const eventAlerts: EventAlertItem[] = useMemo(
    () => alertsQuery.data ?? [],
    [alertsQuery.data]
  );

  const { criticalAlerts, warningAlerts } = useMemo(() => {
    const critical: EventAlertItem[] = [];
    const warning: EventAlertItem[] = [];

    eventAlerts.forEach((alert) => {
      const sev = (alert.severidad || "").toUpperCase();
      if (sev === "CRITICAL" || alert.horas_restantes < 48) {
        critical.push(alert);
      } else {
        warning.push(alert);
      }
    });

    return { criticalAlerts: critical, warningAlerts: warning };
  }, [eventAlerts]);

  const criticalAlertsCount = criticalAlerts.length;
  const warningAlertsCount = warningAlerts.length;
  const hasCriticalAlerts = criticalAlertsCount > 0;
  const hasWarningAlerts = warningAlertsCount > 0;

  // Clasificación de criticidad global
  const isCritical = useMemo(
    () =>
      hasCriticalAlerts ||
      items.some((item) => (item.deficit ?? item.faltante ?? 0) > 0),
    [hasCriticalAlerts, items]
  );

  // Helper: Obtener registro de stock comprometido para un producto y bodega
  const getCommittedStockByProduct = useCallback(
    (productId: number | string, bodegaId?: number | string): CommittedStockItem | undefined => {
      const pId = Number(productId);
      const bId = bodegaId !== undefined && bodegaId !== "all" ? Number(bodegaId) : undefined;

      return committedStock.find((it) => {
        if (it.producto_id !== pId) return false;
        if (bId !== undefined && it.bodega_id !== bId) return false;
        return true;
      });
    },
    [committedStock]
  );

  // Helper: Verificar si un producto tiene existencias comprometidas en eventos
  const isProductCommitted = useCallback(
    (productId: number | string): boolean => {
      const pId = Number(productId);
      return committedStock.some(
        (it) => it.producto_id === pId && (it.stock_comprometido ?? 0) > 0
      );
    },
    [committedStock]
  );

  // Helper: Saldo Disponible Real = max(0, stock_actual - stock_comprometido)
  const getAvailableRealStock = useCallback(
    (productId: number | string, bodegaId?: number | string): number => {
      const item = getCommittedStockByProduct(productId, bodegaId);
      if (!item) return 0;
      return item.stock_disponible_real ?? Math.max(0, item.stock_actual - item.stock_comprometido);
    },
    [getCommittedStockByProduct]
  );

  const isLoading =
    faltantesQuery.isLoading ||
    committedStockQuery.isLoading ||
    alertsQuery.isLoading;

  const isError =
    faltantesQuery.isError ||
    committedStockQuery.isError ||
    alertsQuery.isError;

  const error =
    faltantesQuery.error ||
    committedStockQuery.error ||
    alertsQuery.error;

  const refetch = useCallback(async () => {
    await Promise.all([
      faltantesQuery.refetch(),
      committedStockQuery.refetch(),
      alertsQuery.refetch(),
    ]);
  }, [faltantesQuery, committedStockQuery, alertsQuery]);

  return {
    // Faltantes (compatibilidad retroactiva)
    items,
    totalFaltantes,
    eventosAfectadosCount,
    hasShortages,
    isCritical,

    // Stock Comprometido (FASE 7)
    committedStock,
    totalCommittedItems,
    getCommittedStockByProduct,
    isProductCommitted,
    getAvailableRealStock,

    // Alertas Clasificadas por Severidad (FASE 7)
    eventAlerts,
    criticalAlerts,
    warningAlerts,
    criticalAlertsCount,
    warningAlertsCount,
    hasCriticalAlerts,
    hasWarningAlerts,

    // Estados de Carga
    isLoading,
    isError,
    error,
    refetch,
  };
}
