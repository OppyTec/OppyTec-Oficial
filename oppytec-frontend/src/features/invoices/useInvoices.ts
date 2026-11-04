/**
 * oppytec-frontend/src/features/invoices/useInvoices.ts
 * Hook reactivo maestro con TanStack Query v5 para el Módulo de Facturas y Conciliación DTE.
 * Cero Polling: Invalida y sincroniza automáticamente mediante WebSockets (`useRealtimeSync`).
 * Incluye drafting en localStorage (`oppytec_invoice_review_draft_${id}`) y mutaciones optimistas.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getHttpRequestContext } from "@/shared/api/httpClient";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import { invoicesApi } from "./invoicesApi";
import type {
  ConfirmStockPayload,
  ExportFormat,
  Invoice,
  InvoiceFilters,
  InvoiceLineItem,
  InvoiceStats,
  InvoiceWebhook,
  PriceDriftItem,
} from "./types";

export const INVOICE_DRAFT_PREFIX = "oppytec_invoice_review_draft_";

export const INITIAL_INVOICE_FILTERS: InvoiceFilters = {
  search: "",
  status: "ALL",
  dte_type: "ALL",
  date_from: null,
  date_to: null,
  area_id: "all",
  page: 1,
  limit: 20,
};

export function useInvoices(initialFilters?: Partial<InvoiceFilters>) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  // Estado de filtros
  const [filters, setFiltersState] = useState<InvoiceFilters>({
    ...INITIAL_INVOICE_FILTERS,
    ...(initialFilters ?? {}),
  });

  // Búsqueda con debounce local
  const [searchInput, setSearchInput] = useState<string>(filters.search || "");

  useEffect(() => {
    const handler = setTimeout(() => {
      setFiltersState((prev) => {
        if (prev.search === searchInput) return prev;
        return { ...prev, search: searchInput, page: 1 };
      });
    }, 350);
    return () => clearTimeout(handler);
  }, [searchInput]);

  const setFilter = useCallback(
    <K extends keyof InvoiceFilters>(key: K, value: InvoiceFilters[K]) => {
      setFiltersState((prev) => ({
        ...prev,
        [key]: value,
        page: key === "page" ? (value as number) : 1,
      }));
    },
    []
  );

  const resetFilters = useCallback(() => {
    setSearchInput("");
    setFiltersState(INITIAL_INVOICE_FILTERS);
  }, []);

  // Claves de consulta
  const invoicesKey = useMemo(
    () => ["oppytec", "invoices", "list", tenantId, filters] as const,
    [tenantId, filters]
  );
  const statsKey = useMemo(
    () => ["oppytec", "invoices", "stats", tenantId] as const,
    [tenantId]
  );
  const driftKey = useMemo(
    () => ["oppytec", "invoices", "price_drift", tenantId] as const,
    [tenantId]
  );

  // Consulta de facturas
  const {
    data: invoicesData,
    isLoading: isLoadingInvoices,
    isFetching: isFetchingInvoices,
    error: invoicesError,
    refetch: refetchInvoices,
  } = useQuery({
    queryKey: invoicesKey,
    queryFn: () => invoicesApi.list(filters),
    staleTime: 30_000,
  });

  // Consulta de estadísticas FinOps
  const {
    data: stats,
    isLoading: isLoadingStats,
    refetch: refetchStats,
  } = useQuery<InvoiceStats>({
    queryKey: statsKey,
    queryFn: () => invoicesApi.getStats(),
    staleTime: 60_000,
  });

  // Consulta de radar de variación de precios
  const {
    data: priceDriftItems = [],
    isLoading: isLoadingPriceDrift,
  } = useQuery<PriceDriftItem[]>({
    queryKey: driftKey,
    queryFn: () => invoicesApi.getPriceDrift(),
    staleTime: 60_000,
  });

  // Suscripción WebSocket Zero-Polling
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Decoupled mode if outside provider
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const latestEvent = realtimeEvents[0];
    if (!latestEvent) return;

    if (
      latestEvent.eventType.startsWith("invoice.") ||
      latestEvent.eventType === "invoices.changed"
    ) {
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "invoices"] });
      if (latestEvent.eventType === "invoice.stock_confirmed") {
        void queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory"] });
      }
    }
  }, [realtimeEvents, queryClient]);

  // Mutación de Subida
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const uploadMutation = useMutation({
    mutationFn: (files: File[]) =>
      invoicesApi.upload(files, (pct) => setUploadProgress(pct)),
    onSuccess: (res) => {
      setUploadProgress(100);
      toast.success(`${res.uploaded} factura(s) cargada(s) correctamente.`);
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "invoices"] });
      setTimeout(() => setUploadProgress(0), 1000);
    },
    onError: (err: any) => {
      setUploadProgress(0);
      toast.error(err?.message || "Error al subir facturas.");
    },
  });

  // Mutación Re-procesar
  const reprocessMutation = useMutation({
    mutationFn: (id: string) => invoicesApi.process(id),
    onSuccess: () => {
      toast.success("Factura re-procesada con IA exitosamente.");
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "invoices"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al re-procesar factura.");
    },
  });

  // Mutación Eliminar Individual
  const deleteMutation = useMutation({
    mutationFn: (id: string) => invoicesApi.remove(id),
    onSuccess: () => {
      toast.success("Factura eliminada.");
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "invoices"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al eliminar factura.");
    },
  });

  // Mutación Acciones Masivas
  const bulkProcessMutation = useMutation({
    mutationFn: (ids: string[]) => invoicesApi.bulkProcess(ids),
    onSuccess: (res) => {
      toast.success(`${res.processed} facturas enviadas a procesar.`);
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "invoices"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error en procesamiento masivo.");
    },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) => invoicesApi.bulkDelete(ids),
    onSuccess: (res) => {
      toast.success(`${res.deleted} facturas eliminadas.`);
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "invoices"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error en eliminación masiva.");
    },
  });

  // Exportación
  const exportMutation = useMutation({
    mutationFn: ({ ids, format }: { ids: string[]; format: ExportFormat }) =>
      invoicesApi.exportInvoices(ids, format),
    onSuccess: (blob, variables) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const ext = variables.format === "excel" ? "xlsx" : "csv";
      a.download = `facturas_${variables.format}_${new Date().toISOString().split("T")[0]}.${ext}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`Archivo exportado exitosamente (${variables.format}).`);
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al exportar archivo.");
    },
  });

  return {
    // Listado y estado
    invoices: invoicesData?.items ?? [],
    totalInvoices: invoicesData?.total ?? 0,
    isLoadingInvoices,
    isFetchingInvoices,
    invoicesError,
    refetchInvoices,

    // Filtros
    filters,
    searchInput,
    setSearchInput,
    setFilter,
    resetFilters,

    // Estadísticas & FinOps
    stats,
    isLoadingStats,
    refetchStats,
    priceDriftItems,
    isLoadingPriceDrift,

    // Subida
    uploadProgress,
    uploadInvoices: uploadMutation.mutateAsync,
    isUploading: uploadMutation.isPending,

    // Operaciones
    reprocessInvoice: reprocessMutation.mutateAsync,
    isReprocessing: reprocessMutation.isPending,
    deleteInvoice: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,

    // Masivas & Exportación
    bulkProcess: bulkProcessMutation.mutateAsync,
    isBulkProcessing: bulkProcessMutation.isPending,
    bulkDelete: bulkDeleteMutation.mutateAsync,
    isBulkDeleting: bulkDeleteMutation.isPending,
    exportInvoices: exportMutation.mutateAsync,
    isExporting: exportMutation.isPending,
  };
}

/**
 * Hook para la vista de detalle e inspector dual de una factura (`/contabilidad/facturas/:id`).
 */
export function useInvoiceDetail(id: string | undefined) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  const detailKey = useMemo(
    () => ["oppytec", "invoices", "detail", tenantId, id] as const,
    [tenantId, id]
  );

  const {
    data: invoice,
    isLoading,
    error,
    refetch,
  } = useQuery<Invoice>({
    queryKey: detailKey,
    queryFn: () => {
      if (!id) throw new Error("ID de factura no provisto");
      return invoicesApi.getById(id);
    },
    enabled: !!id,
    staleTime: 30_000,
  });

  // Estado editable local de ítems
  const [editableItems, setEditableItems] = useState<InvoiceLineItem[]>([]);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);

  // Inicialización o restauración desde borrador en localStorage
  useEffect(() => {
    if (!id || !invoice) return;
    const draftKey = `${INVOICE_DRAFT_PREFIX}${id}`;
    let loadedFromDraft = false;

    if (typeof window !== "undefined" && window.localStorage) {
      try {
        const saved = window.localStorage.getItem(draftKey);
        if (saved) {
          const parsed = JSON.parse(saved) as InvoiceLineItem[];
          if (Array.isArray(parsed) && parsed.length > 0) {
            setEditableItems(parsed);
            setHasUnsavedChanges(true);
            loadedFromDraft = true;
          }
        }
      } catch {
        // Fallback ignorando error de parsing
      }
    }

    if (!loadedFromDraft) {
      setEditableItems(invoice.items || []);
      setHasUnsavedChanges(false);
    }
  }, [id, invoice]);

  // Manejo de cambios en filas
  const updateItems = useCallback(
    (newItems: InvoiceLineItem[]) => {
      setEditableItems(newItems);
      setHasUnsavedChanges(true);
      if (id && typeof window !== "undefined" && window.localStorage) {
        try {
          window.localStorage.setItem(
            `${INVOICE_DRAFT_PREFIX}${id}`,
            JSON.stringify(newItems)
          );
        } catch {
          // LocalStorage quota fallback
        }
      }
    },
    [id]
  );

  const discardDraft = useCallback(() => {
    if (!id) return;
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.removeItem(`${INVOICE_DRAFT_PREFIX}${id}`);
    }
    if (invoice?.items) {
      setEditableItems(invoice.items);
    }
    setHasUnsavedChanges(false);
    toast.info("Cambios descartados.");
  }, [id, invoice]);

  // Guardar cambios en servidor
  const updateMutation = useMutation({
    mutationFn: (updatedInvoice: Partial<Invoice>) => {
      if (!id) throw new Error("ID no provisto");
      return invoicesApi.update(id, {
        ...updatedInvoice,
        items: editableItems,
      });
    },
    onSuccess: (saved) => {
      if (id && typeof window !== "undefined" && window.localStorage) {
        window.localStorage.removeItem(`${INVOICE_DRAFT_PREFIX}${id}`);
      }
      setHasUnsavedChanges(false);
      queryClient.setQueryData(detailKey, saved);
      toast.success("Factura guardada correctamente.");
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al guardar factura.");
    },
  });

  // Confirmar e Ingresar a Inventario (Auto-Stock)
  const confirmStockMutation = useMutation({
    mutationFn: (payload: ConfirmStockPayload) => {
      if (!id) throw new Error("ID no provisto");
      return invoicesApi.confirmStock(id, payload);
    },
    onSuccess: (res) => {
      if (id && typeof window !== "undefined" && window.localStorage) {
        window.localStorage.removeItem(`${INVOICE_DRAFT_PREFIX}${id}`);
      }
      setHasUnsavedChanges(false);
      toast.success(
        `¡Stock ingresado exitosamente! ${res.movements_created} movimientos registrados en Kardex.`
      );
      void queryClient.invalidateQueries({ queryKey: detailKey });
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "invoices"] });
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al confirmar ingreso a bodega.");
    },
  });

  return {
    invoice,
    isLoading,
    error,
    refetch,
    editableItems,
    setEditableItems: updateItems,
    hasUnsavedChanges,
    discardDraft,
    saveChanges: updateMutation.mutateAsync,
    isSaving: updateMutation.isPending,
    confirmStockIngest: confirmStockMutation.mutateAsync,
    isConfirmingStock: confirmStockMutation.isPending,
  };
}

/**
 * Hook para la gestión de Webhooks salientes de facturación (`PipelineTab`).
 */
export function useInvoiceWebhooks() {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  const webhooksKey = useMemo(
    () => ["oppytec", "invoices", "webhooks", tenantId] as const,
    [tenantId]
  );

  const {
    data: webhooks = [],
    isLoading,
    refetch,
  } = useQuery<InvoiceWebhook[]>({
    queryKey: webhooksKey,
    queryFn: () => invoicesApi.listWebhooks(),
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: (webhook: Partial<InvoiceWebhook>) => invoicesApi.createWebhook(webhook),
    onSuccess: () => {
      toast.success("Webhook registrado exitosamente.");
      void queryClient.invalidateQueries({ queryKey: webhooksKey });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al crear webhook.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => invoicesApi.deleteWebhook(id),
    onSuccess: () => {
      toast.success("Webhook eliminado.");
      void queryClient.invalidateQueries({ queryKey: webhooksKey });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error al eliminar webhook.");
    },
  });

  const pingMutation = useMutation({
    mutationFn: (id: string) => invoicesApi.pingWebhook(id),
    onSuccess: (res) => {
      toast.success(
        `Ping exitoso (HTTP ${res.status_code}) en ${res.response_time_ms} ms.`
      );
    },
    onError: (err: any) => {
      toast.error(err?.message || "Error en la prueba de conexión del webhook.");
    },
  });

  return {
    webhooks,
    isLoading,
    refetch,
    createWebhook: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    deleteWebhook: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    pingWebhook: pingMutation.mutateAsync,
    isPinging: pingMutation.isPending,
  };
}
