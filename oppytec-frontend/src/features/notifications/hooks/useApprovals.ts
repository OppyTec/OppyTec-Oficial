import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import {
  type CategoryType,
  type MainViewType,
  MOCK_SOLICITUDES,
  type Solicitud,
  type SolicitudesListResponse,
  type SolicitudTipo,
} from "../types";

export interface UseApprovalsOptions {
  readonly mainView?: MainViewType;
  readonly activeCategory?: CategoryType | "all";
  readonly selectedAreaId?: string | number | null;
  readonly selectedBodegaId?: string | number | null;
  readonly searchTerm?: string;
  readonly page?: number;
  readonly pageSize?: number;
}

export interface UseApprovalsReturn {
  readonly solicitudes: readonly Solicitud[];
  readonly total: number;
  readonly page: number;
  readonly pageSize: number;
  readonly isLoading: boolean;
  readonly isError: boolean;
  readonly error: unknown;
  readonly refetch: () => Promise<unknown>;
  // Edición Inline Pre-Aprobación
  readonly editedDetailsMap: Readonly<Record<string, Record<string, any>>>;
  readonly editedTipoMap: Readonly<Record<string, SolicitudTipo>>;
  readonly setEditedDetail: (id: string, field: string, value: any) => void;
  readonly setEditedDetails: (
    id: string,
    details: Record<string, any>
  ) => void;
  readonly setEditedTipo: (id: string, tipo: SolicitudTipo) => void;
  readonly getEditedDetails: (
    id: string,
    original?: Record<string, any>
  ) => Record<string, any>;
  readonly getEditedTipo: (
    id: string,
    original?: SolicitudTipo
  ) => SolicitudTipo | undefined;
  readonly resetEdited: (id: string) => void;
  // Mutaciones de Resolución
  readonly approveRequest: (
    id: string,
    customDetails?: Record<string, any>
  ) => Promise<Solicitud>;
  readonly rejectRequest: (id: string, reason: string) => Promise<Solicitud>;
  readonly isApproving: boolean;
  readonly isRejecting: boolean;
}

/**
 * Filtra el mock data local para evitar pantallas en blanco ante caídas del backend (Regla OppyTec v2.0).
 */
function filterMockData(
  list: readonly Solicitud[],
  options: UseApprovalsOptions
): { items: readonly Solicitud[]; total: number } {
  let filtered = [...list];

  // Filtro por Vista Principal (Bandeja vs Historial)
  if (options.mainView === "bandeja" || !options.mainView) {
    filtered = filtered.filter((s) => s.estado === "pendiente");
  } else if (options.mainView === "historial") {
    filtered = filtered.filter((s) => s.estado !== "pendiente");
  }

  // Filtro por Categoría
  if (options.activeCategory && options.activeCategory !== "all") {
    filtered = filtered.filter((s) => s.categoria === options.activeCategory);
  }

  // Filtro por Área
  if (
    options.selectedAreaId !== undefined &&
    options.selectedAreaId !== null &&
    options.selectedAreaId !== "all"
  ) {
    const areaIdNum = Number(options.selectedAreaId);
    filtered = filtered.filter((s) => s.area_operativa_id === areaIdNum);
  }

  // Filtro por Bodega
  if (
    options.selectedBodegaId !== undefined &&
    options.selectedBodegaId !== null &&
    options.selectedBodegaId !== "all"
  ) {
    const bodegaIdNum = Number(options.selectedBodegaId);
    filtered = filtered.filter((s) => s.bodega_id === bodegaIdNum);
  }

  // Búsqueda por texto libre
  if (options.searchTerm && options.searchTerm.trim() !== "") {
    const q = options.searchTerm.toLowerCase();
    filtered = filtered.filter((s) => {
      const matchTipo = s.tipo.toLowerCase().includes(q);
      const matchUser =
        s.usuario?.first_name?.toLowerCase().includes(q) ||
        s.usuario?.last_name?.toLowerCase().includes(q) ||
        s.usuario?.username?.toLowerCase().includes(q);
      const matchDetalles = JSON.stringify(s.detalles).toLowerCase().includes(q);
      return matchTipo || matchUser || matchDetalles;
    });
  }

  const page = options.page ?? 1;
  const pageSize = options.pageSize ?? 20;
  const total = filtered.length;
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  return { items: paginated, total };
}

export function useApprovals(
  options: UseApprovalsOptions = {}
): UseApprovalsReturn {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "default";

  const {
    mainView = "bandeja",
    activeCategory = "all",
    selectedAreaId = "all",
    selectedBodegaId = "all",
    searchTerm = "",
    page = 1,
    pageSize = 20,
  } = options;

  // Estado local para edición inline temporal antes de aprobar
  const [editedDetailsMap, setEditedDetailsMap] = useState<
    Record<string, Record<string, any>>
  >({});
  const [editedTipoMap, setEditedTipoMap] = useState<
    Record<string, SolicitudTipo>
  >({});

  const setEditedDetail = useCallback(
    (id: string, field: string, value: any) => {
      setEditedDetailsMap((prev) => ({
        ...prev,
        [id]: {
          ...(prev[id] ?? {}),
          [field]: value,
        },
      }));
    },
    []
  );

  const setEditedDetails = useCallback(
    (id: string, details: Record<string, any>) => {
      setEditedDetailsMap((prev) => ({
        ...prev,
        [id]: details,
      }));
    },
    []
  );

  const setEditedTipo = useCallback((id: string, tipo: SolicitudTipo) => {
    setEditedTipoMap((prev) => ({
      ...prev,
      [id]: tipo,
    }));
  }, []);

  const getEditedDetails = useCallback(
    (id: string, original?: Record<string, any>) => {
      return editedDetailsMap[id] ?? original ?? {};
    },
    [editedDetailsMap]
  );

  const getEditedTipo = useCallback(
    (id: string, original?: SolicitudTipo) => {
      return editedTipoMap[id] ?? original;
    },
    [editedTipoMap]
  );

  const resetEdited = useCallback((id: string) => {
    setEditedDetailsMap((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setEditedTipoMap((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }, []);

  // Suscripción a eventos Realtime vía WebSocket (Zero Polling)
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] =
    [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Modo desacoplado o unit test sin RealtimeProvider
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType === "notification.created" ||
      lastEvent?.eventType === "notification.resolved" ||
      lastEvent?.eventType === "operations.notification.created" ||
      lastEvent?.eventType === "operations.notification.resolved" ||
      lastEvent?.eventType.startsWith("notification.")
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.approvals.all(),
      });
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "approvals", "pendingCount"],
      });
    }
  }, [realtimeEvents, queryClient]);

  // Listener para sincronización local entre pestañas/vistas
  useEffect(() => {
    const handleSync = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.approvals.all(),
      });
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "approvals", "pendingCount"],
      });
    };
    window.addEventListener("approvals_changed", handleSync);
    return () => {
      window.removeEventListener("approvals_changed", handleSync);
    };
  }, [queryClient]);

  const fallbackData = useMemo(
    () =>
      filterMockData(MOCK_SOLICITUDES, {
        mainView,
        activeCategory,
        selectedAreaId,
        selectedBodegaId,
        searchTerm,
        page,
        pageSize,
      }),
    [
      mainView,
      activeCategory,
      selectedAreaId,
      selectedBodegaId,
      searchTerm,
      page,
      pageSize,
    ]
  );

  // Determinación de estado para el query del backend
  const estadoFilter =
    mainView === "bandeja"
      ? "pendiente"
      : mainView === "historial"
        ? "all"
        : undefined;

  const areaIdParam =
    selectedAreaId !== "all" && selectedAreaId !== null && selectedAreaId !== undefined
      ? String(selectedAreaId)
      : undefined;

  const bodegaIdParam =
    selectedBodegaId !== "all" &&
    selectedBodegaId !== null &&
    selectedBodegaId !== undefined
      ? Number(selectedBodegaId)
      : undefined;

  const queryKey = useMemo(
    () =>
      queryKeys.approvals.list({
        tenantId,
        estado: estadoFilter ?? "all",
        categoria: activeCategory !== "all" ? activeCategory : "all",
        areaId: areaIdParam ?? "all",
        bodegaId: bodegaIdParam,
        search: searchTerm,
        page,
      }),
    [
      tenantId,
      estadoFilter,
      activeCategory,
      areaIdParam,
      bodegaIdParam,
      searchTerm,
      page,
    ]
  );

  // Query principal TanStack Query v5
  const {
    data: queryResult,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<SolicitudesListResponse>({
    queryKey,
    queryFn: async () => {
      const params = new URLSearchParams();
      if (estadoFilter && estadoFilter !== "all") {
        params.append("estado", estadoFilter);
      }
      if (activeCategory && activeCategory !== "all") {
        params.append("categoria", activeCategory);
      }
      if (areaIdParam) {
        params.append("area_id", areaIdParam);
      }
      if (bodegaIdParam !== undefined && !isNaN(bodegaIdParam)) {
        params.append("bodega_id", String(bodegaIdParam));
      }
      if (searchTerm && searchTerm.trim() !== "") {
        params.append("q", searchTerm.trim());
      }
      params.append("page", String(page));
      params.append("page_size", String(pageSize));

      const qs = params.toString();
      const endpoint = `/api/v1/operations/solicitudes${qs ? `?${qs}` : ""}`;

      const res = await apiRequest<SolicitudesListResponse>(endpoint, {
        method: "GET",
        fallbackData: {
          items: fallbackData.items,
          total: fallbackData.total,
          page,
          page_size: pageSize,
        },
      });

      return res.data;
    },
    staleTime: 30_000,
  });

  const solicitudes = queryResult?.items ?? fallbackData.items;
  const total = queryResult?.total ?? fallbackData.total;

  // Mutación para Aprobar Solicitud
  const approveMutation = useMutation({
    mutationFn: async ({
      id,
      customDetails,
    }: {
      id: string;
      customDetails?: Record<string, any>;
    }) => {
      const detailsToSubmit =
        customDetails ?? editedDetailsMap[id] ?? undefined;
      const endpoint = `/api/v1/operations/solicitudes/${id}/aprobar`;

      const res = await apiRequest<Solicitud>(endpoint, {
        method: "POST",
        body: detailsToSubmit ? { edited_details: detailsToSubmit } : {},
      });

      return res.data;
    },
    onSuccess: (_, variables) => {
      resetEdited(variables.id);
      toast.success("Solicitud aprobada correctamente");
      void queryClient.invalidateQueries({
        queryKey: queryKeys.approvals.all(),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.approvals.pendingCount(),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.operations.alerts(tenantId),
      });
      window.dispatchEvent(new Event("approvals_changed"));
    },
    onError: (err: any) => {
      const msg =
        err?.message ||
        "No se pudo aprobar la solicitud. Intente nuevamente.";
      toast.error(msg);
    },
  });

  // Mutación para Rechazar Solicitud
  const rejectMutation = useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason: string }) => {
      if (!reason || reason.trim().length < 5) {
        throw new Error("El motivo de rechazo debe tener al menos 5 caracteres");
      }
      const endpoint = `/api/v1/operations/solicitudes/${id}/rechazar`;

      const res = await apiRequest<Solicitud>(endpoint, {
        method: "POST",
        body: { motivo_rechazo: reason.trim() },
      });

      return res.data;
    },
    onSuccess: (_, variables) => {
      resetEdited(variables.id);
      toast.success("Solicitud rechazada correctamente");
      void queryClient.invalidateQueries({
        queryKey: queryKeys.approvals.all(),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.approvals.pendingCount(),
      });
      window.dispatchEvent(new Event("approvals_changed"));
    },
    onError: (err: any) => {
      const msg =
        err?.message ||
        "No se pudo rechazar la solicitud. Verifique el motivo e intente nuevamente.";
      toast.error(msg);
    },
  });

  const approveRequest = useCallback(
    async (id: string, customDetails?: Record<string, any>): Promise<Solicitud> => {
      return approveMutation.mutateAsync({ id, customDetails });
    },
    [approveMutation]
  );

  const rejectRequest = useCallback(
    async (id: string, reason: string): Promise<Solicitud> => {
      return rejectMutation.mutateAsync({ id, reason });
    },
    [rejectMutation]
  );

  return {
    solicitudes,
    total,
    page,
    pageSize,
    isLoading,
    isError,
    error,
    refetch,
    editedDetailsMap,
    editedTipoMap,
    setEditedDetail,
    setEditedDetails,
    setEditedTipo,
    getEditedDetails,
    getEditedTipo,
    resetEdited,
    approveRequest,
    rejectRequest,
    isApproving: approveMutation.isPending,
    isRejecting: rejectMutation.isPending,
  };
}
