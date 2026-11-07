/**
 * oppytec-frontend/src/features/procurement/hooks/useCompras.ts
 * Hook reactivo TanStack Query v5 para Órdenes de Compra y Recepción de Mercadería.
 * Zero HTTP polling: suscripción WebSocket a `procurement.order.updated`.
 * Persistencia en localStorage (`oppytec_compra_draft`) con auto-recuperación y fallback resiliente.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import { isMockDataEnabled, MOCK_DATA_MODE_EVENT_NAME, useMockDataMode } from "@/shared/mock/mockModeStorage";
import {
  MOCK_COMPRAS,
  MOCK_PROCUREMENT_DASHBOARD,
} from "../mockData";
import {
  COMPRA_DRAFT_STORAGE_KEY,
  type CancelOrderPayload,
  type CompraDraft,
  type CompraEstado,
  type CompraIncidencia,
  type CompraOrder,
  type CreateOrderPayload,
  type ProcurementDashboardData,
  type ReceiveGoodsPayload,
  type RegisterIncidencePayload,
} from "../types";

export const CLEAN_PROCUREMENT_DASHBOARD: ProcurementDashboardData = {
  monto_total_mes: "0.00",
  total_mes_monto: "0.00",
  ordenes_pendientes: 0,
  ordenes_pendientes_recepcion: 0,
  proveedores_activos: 0,
  proveedor_principal: null,
  tiempo_promedio_entrega_dias: 0,
  variacion_mes_anterior_pct: "0.0",
  ordenes_recientes: [],
  gastos_por_proveedor: [],
};

export interface ComprasFilterState {
  status?: CompraEstado | "TODOS" | null;
  supplier_id?: number | null;
  search?: string;
  date_from?: string | null;
  date_to?: string | null;
}

export const INITIAL_COMPRAS_FILTERS: ComprasFilterState = {
  status: "TODOS",
  supplier_id: null,
  search: "",
  date_from: null,
  date_to: null,
};

export function useCompras(initialFilters?: Partial<ComprasFilterState>) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";
  const { isDemo } = useMockDataMode();

  useEffect(() => {
    const handleModeChange = () => {
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement"],
      });
    };
    window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, handleModeChange);
    return () => {
      window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, handleModeChange);
    };
  }, [queryClient]);

  // Estado de filtros
  const [filters, setFiltersState] = useState<ComprasFilterState>({
    ...INITIAL_COMPRAS_FILTERS,
    ...(initialFilters ?? {}),
  });

  const setFilter = useCallback(
    <K extends keyof ComprasFilterState>(key: K, value: ComprasFilterState[K]) => {
      setFiltersState((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const setFilters = useCallback((next: Partial<ComprasFilterState>) => {
    setFiltersState((prev) => ({ ...prev, ...next }));
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState(INITIAL_COMPRAS_FILTERS);
  }, []);

  // ==========================================================================
  // BORRADOR LOCALSTORAGE (Auto-recuperación y persistencia)
  // ==========================================================================
  const [draftData, setDraftData] = useState<CompraDraft | null>(() => {
    if (typeof window === "undefined" || !window.localStorage) {
      return null;
    }
    try {
      const raw = window.localStorage.getItem(COMPRA_DRAFT_STORAGE_KEY);
      if (raw) {
        return JSON.parse(raw) as CompraDraft;
      }
    } catch {
      // Ignorar fallo de parseo
    }
    return null;
  });

  const saveDraft = useCallback((partial: Partial<CompraDraft>) => {
    setDraftData((prev) => {
      const updated: CompraDraft = {
        proveedor_id: partial.proveedor_id ?? prev?.proveedor_id ?? null,
        proveedor_nombre: partial.proveedor_nombre ?? prev?.proveedor_nombre,
        bodega_destino_id: partial.bodega_destino_id ?? prev?.bodega_destino_id ?? 1,
        bodega_nombre: partial.bodega_nombre ?? prev?.bodega_nombre,
        fecha_entrega_comprometida:
          partial.fecha_entrega_comprometida ?? prev?.fecha_entrega_comprometida ?? null,
        moneda: partial.moneda ?? prev?.moneda ?? "CLP",
        notas: partial.notas ?? prev?.notas ?? "",
        items: partial.items ?? prev?.items ?? [],
        updated_at: new Date().toISOString(),
      };
      if (typeof window !== "undefined" && window.localStorage) {
        try {
          window.localStorage.setItem(COMPRA_DRAFT_STORAGE_KEY, JSON.stringify(updated));
        } catch {
          // localStorage no disponible o quota excedida
        }
      }
      return updated;
    });
  }, []);

  const clearDraft = useCallback(() => {
    setDraftData(null);
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        window.localStorage.removeItem(COMPRA_DRAFT_STORAGE_KEY);
      } catch {
        // Ignorar
      }
    }
  }, []);

  const hasDraft = useMemo(() => {
    return Boolean(
      draftData && (draftData.items?.length > 0 || draftData.proveedor_id !== null)
    );
  }, [draftData]);

  // ==========================================================================
  // QUERIES REACTIVAS (Órdenes de Compra y Dashboard)
  // ==========================================================================
  const queryParams = useMemo(() => {
    const params: Record<string, string> = {};
    if (filters.status && filters.status !== "TODOS") {
      params.status = filters.status;
    }
    if (filters.supplier_id) {
      params.supplier_id = String(filters.supplier_id);
    }
    if (filters.date_from) {
      params.date_from = filters.date_from;
    }
    if (filters.date_to) {
      params.date_to = filters.date_to;
    }
    return params;
  }, [filters.status, filters.supplier_id, filters.date_from, filters.date_to]);

  const ordersQueryKey = queryKeys.procurement.purchaseOrders(tenantId, queryParams);
  const dashboardQueryKey = queryKeys.procurement.dashboard(tenantId);

  const {
    data: fetchedOrders,
    isLoading: isLoadingOrders,
    isError: isErrorOrders,
    refetch: refetchOrders,
  } = useQuery({
    queryKey: ordersQueryKey,
    queryFn: async () => {
      const searchParams = new URLSearchParams(queryParams).toString();
      const endpoint = searchParams
        ? `/api/v1/procurement/orders?${searchParams}`
        : "/api/v1/procurement/orders";
      const response = await apiRequest<CompraOrder[]>(endpoint, {
        method: "GET",
        fallbackData: isMockDataEnabled() ? MOCK_COMPRAS : [],
      });
      return response.data;
    },
    staleTime: 1000 * 60 * 5,
  });
  const rawOrders = fetchedOrders ?? (isDemo ? MOCK_COMPRAS : []);

  const {
    data: fetchedDashboard,
    isLoading: isLoadingDashboard,
    isError: isErrorDashboard,
    refetch: refetchDashboard,
  } = useQuery({
    queryKey: dashboardQueryKey,
    queryFn: async () => {
      const response = await apiRequest<ProcurementDashboardData>(
        "/api/v1/procurement/dashboard",
        {
          method: "GET",
          fallbackData: isMockDataEnabled()
            ? MOCK_PROCUREMENT_DASHBOARD
            : CLEAN_PROCUREMENT_DASHBOARD,
        }
      );
      return response.data;
    },
    staleTime: 1000 * 60 * 5,
  });
  const dashboard = useMemo(() => {
    if (!isDemo && fetchedDashboard === MOCK_PROCUREMENT_DASHBOARD) {
      return CLEAN_PROCUREMENT_DASHBOARD;
    }
    return fetchedDashboard ?? (isDemo ? MOCK_PROCUREMENT_DASHBOARD : CLEAN_PROCUREMENT_DASHBOARD);
  }, [fetchedDashboard, isDemo]);

  // Filtrado de órdenes en cliente (búsqueda por número orden o nombre de proveedor)
  const filteredOrders = useMemo(() => {
    if (!rawOrders || !Array.isArray(rawOrders)) return [];
    let list = [...rawOrders];

    if (filters.search && filters.search.trim().length > 0) {
      const term = filters.search.toLowerCase().trim();
      list = list.filter(
        (o) =>
          o.numero_orden.toLowerCase().includes(term) ||
          (o.po_number && o.po_number.toLowerCase().includes(term)) ||
          o.proveedor_nombre.toLowerCase().includes(term) ||
          (o.supplier_name && o.supplier_name.toLowerCase().includes(term))
      );
    }

    if (filters.status && filters.status !== "TODOS") {
      list = list.filter((o) => o.estado === filters.status);
    }

    if (filters.supplier_id) {
      list = list.filter(
        (o) => o.proveedor_id === filters.supplier_id || o.supplier_id === filters.supplier_id
      );
    }

    return list;
  }, [rawOrders, filters.search, filters.status, filters.supplier_id]);

  // ==========================================================================
  // SUSCRIPCIÓN WEBSOCKET (procurement.order.updated -> Cero polling)
  // ==========================================================================
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Si no está dentro de RealtimeProvider, opera en modo desacoplado
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const latestEvent = realtimeEvents[0];
    if (latestEvent?.eventType === "procurement.order.updated") {
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement"],
      });
    }
  }, [realtimeEvents, queryClient]);

  // ==========================================================================
  // MUTACIONES CON INVALIDACIÓN RESILIENTE
  // ==========================================================================
  const createOrderMutation = useMutation({
    mutationFn: async (payload: CreateOrderPayload): Promise<CompraOrder> => {
      const res = await apiRequest<CompraOrder>("/api/v1/procurement/orders", {
        method: "POST",
        body: payload,
      });
      return res.data;
    },
    onSuccess: (created) => {
      clearDraft();
      toast.success(
        `Orden ${created.numero_orden || created.po_number || "creada"} guardada exitosamente.`
      );
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement"],
      });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al crear la orden de compra.";
      toast.error(msg);
    },
  });

  const receiveGoodsMutation = useMutation({
    mutationFn: async (payload: ReceiveGoodsPayload): Promise<CompraOrder> => {
      const res = await apiRequest<CompraOrder>(
        `/api/v1/procurement/orders/${payload.order_id}/receive`,
        {
          method: "POST",
          body: {
            items: payload.items,
            notas: payload.notas,
          },
        }
      );
      return res.data;
    },
    onSuccess: (updated) => {
      toast.success(`Mercadería recepcionada conforme para la orden ${updated.numero_orden}.`);
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "inventory"],
      });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al registrar la recepción.";
      toast.error(msg);
    },
  });

  const registerIncidenceMutation = useMutation({
    mutationFn: async (payload: RegisterIncidencePayload): Promise<CompraIncidencia> => {
      const res = await apiRequest<CompraIncidencia>(
        `/api/v1/procurement/orders/${payload.order_id}/incidences`,
        {
          method: "POST",
          body: {
            compra_item_id: payload.compra_item_id,
            tipo_incidencia: payload.tipo_incidencia,
            cantidad_afectada: payload.cantidad_afectada,
            monto_disputa: payload.monto_disputa,
            resolucion: payload.resolucion ?? "PENDIENTE",
            descripcion: payload.descripcion,
            foto_evidencia_url: payload.foto_evidencia_url,
          },
        }
      );
      return res.data;
    },
    onSuccess: () => {
      toast.success("Incidencia registrada con éxito.");
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement"],
      });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al registrar incidencia.";
      toast.error(msg);
    },
  });

  const cancelOrderMutation = useMutation({
    mutationFn: async (payload: CancelOrderPayload): Promise<CompraOrder> => {
      const res = await apiRequest<CompraOrder>(
        `/api/v1/procurement/orders/${payload.order_id}/cancel`,
        {
          method: "POST",
          body: { motivo: payload.motivo },
        }
      );
      return res.data;
    },
    onSuccess: (cancelled) => {
      toast.success(`Orden ${cancelled.numero_orden} cancelada correctamente.`);
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement"],
      });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al cancelar la orden.";
      toast.error(msg);
    },
  });

  return {
    // Datos y estados de carga
    orders: filteredOrders,
    rawOrders,
    dashboard,
    isLoadingOrders,
    isLoadingDashboard,
    isErrorOrders,
    isErrorDashboard,
    refetchOrders,
    refetchDashboard,

    // Filtros
    filters,
    setFilter,
    setFilters,
    resetFilters,

    // Borrador local
    draftData,
    hasDraft,
    saveDraft,
    clearDraft,

    // Mutaciones
    createOrder: createOrderMutation.mutateAsync,
    isCreatingOrder: createOrderMutation.isPending,
    receiveGoods: receiveGoodsMutation.mutateAsync,
    isReceivingGoods: receiveGoodsMutation.isPending,
    registerIncidence: registerIncidenceMutation.mutateAsync,
    isRegisteringIncidence: registerIncidenceMutation.isPending,
    cancelOrder: cancelOrderMutation.mutateAsync,
    isCancellingOrder: cancelOrderMutation.isPending,
  };
}
