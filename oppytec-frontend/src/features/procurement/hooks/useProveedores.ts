/**
 * oppytec-frontend/src/features/procurement/hooks/useProveedores.ts
 * Hook reactivo TanStack Query v5 para Directorio de Proveedores y Catálogo Pactado.
 * Zero HTTP polling: suscripción WebSocket a `procurement.supplier.updated`.
 * Filtros predictivos con debounce y fallback resiliente.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import {
  MOCK_PRODUCTOS_PROVEEDOR,
  MOCK_PROVEEDORES,
} from "../mockData";
import type {
  CreateProveedorPayload,
  ProductoProveedor,
  Proveedor,
  ProveedorEstado,
  UpdateProveedorPayload,
  UpdateSupplierCatalogPayload,
} from "../types";

export interface ProveedoresFilterState {
  search: string;
  estado: ProveedorEstado | "TODOS" | null;
}

const EMPTY_CATALOG: ProductoProveedor[] = [];

export const INITIAL_PROVEEDORES_FILTERS: ProveedoresFilterState = {
  search: "",
  estado: "TODOS",
};

export function useProveedores(
  initialFilters?: Partial<ProveedoresFilterState>,
  activeSupplierId?: number | null
) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  // Filtros y debounce de búsqueda
  const [filters, setFiltersState] = useState<ProveedoresFilterState>({
    ...INITIAL_PROVEEDORES_FILTERS,
    ...(initialFilters ?? {}),
  });
  const [debouncedSearch, setDebouncedSearch] = useState<string>(filters.search);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(filters.search);
    }, 250);
    return () => clearTimeout(timer);
  }, [filters.search]);

  const setFilter = useCallback(
    <K extends keyof ProveedoresFilterState>(
      key: K,
      value: ProveedoresFilterState[K]
    ) => {
      setFiltersState((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const resetFilters = useCallback(() => {
    setFiltersState(INITIAL_PROVEEDORES_FILTERS);
  }, []);

  // ==========================================================================
  // QUERY DE PROVEEDORES
  // ==========================================================================
  const queryParams = useMemo(() => {
    const params: Record<string, string> = {};
    if (debouncedSearch && debouncedSearch.trim().length > 0) {
      params.search = debouncedSearch.trim();
    }
    if (filters.estado && filters.estado !== "TODOS") {
      params.status = filters.estado;
    }
    return params;
  }, [debouncedSearch, filters.estado]);

  const suppliersQueryKey = queryKeys.procurement.suppliers(tenantId, queryParams);

  const {
    data: rawSuppliers = MOCK_PROVEEDORES,
    isLoading: isLoadingSuppliers,
    isError: isErrorSuppliers,
    refetch: refetchSuppliers,
  } = useQuery({
    queryKey: suppliersQueryKey,
    queryFn: async () => {
      const qs = new URLSearchParams(queryParams).toString();
      const endpoint = qs
        ? `/api/v1/procurement/suppliers?${qs}`
        : "/api/v1/procurement/suppliers";
      const response = await apiRequest<Proveedor[]>(endpoint, {
        method: "GET",
        fallbackData: MOCK_PROVEEDORES,
      });
      return response.data;
    },
    staleTime: 1000 * 60 * 5,
  });

  // Filtrado resiliente en cliente adicional si el backend devuelve colección completa
  const filteredSuppliers = useMemo(() => {
    if (!rawSuppliers || !Array.isArray(rawSuppliers)) return [];
    let list = [...rawSuppliers];

    if (debouncedSearch && debouncedSearch.trim().length > 0) {
      const term = debouncedSearch.toLowerCase().trim();
      list = list.filter(
        (s) =>
          s.razon_social.toLowerCase().includes(term) ||
          (s.nombre_fantasia && s.nombre_fantasia.toLowerCase().includes(term)) ||
          s.rut_tax_id.toLowerCase().includes(term)
      );
    }

    if (filters.estado && filters.estado !== "TODOS") {
      list = list.filter((s) => s.estado === filters.estado);
    }

    return list;
  }, [rawSuppliers, debouncedSearch, filters.estado]);

  // ==========================================================================
  // QUERY DE CATÁLOGO DEL PROVEEDOR SELECCIONADO
  // ==========================================================================
  const selectedSupplierId = activeSupplierId ?? null;
  const catalogQueryKey = selectedSupplierId
    ? queryKeys.procurement.supplierCatalog(tenantId, selectedSupplierId)
    : (["oppytec", "procurement", "catalog", "none"] as const);

  const fallbackCatalog = useMemo(
    () =>
      selectedSupplierId
        ? MOCK_PRODUCTOS_PROVEEDOR[selectedSupplierId] ?? EMPTY_CATALOG
        : EMPTY_CATALOG,
    [selectedSupplierId]
  );

  const {
    data: catalog = fallbackCatalog,
    isLoading: isLoadingCatalog,
    isError: isErrorCatalog,
    refetch: refetchCatalog,
  } = useQuery({
    queryKey: catalogQueryKey,
    queryFn: async () => {
      if (!selectedSupplierId) return EMPTY_CATALOG;
      const response = await apiRequest<ProductoProveedor[]>(
        `/api/v1/procurement/suppliers/${selectedSupplierId}/products`,
        {
          method: "GET",
          fallbackData: fallbackCatalog,
        }
      );
      return response.data;
    },
    enabled: selectedSupplierId !== null,
    staleTime: 1000 * 60 * 5,
  });

  // ==========================================================================
  // SUSCRIPCIÓN WEBSOCKET (procurement.supplier.updated -> Cero Polling)
  // ==========================================================================
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Modo desacoplado
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const latestEvent = realtimeEvents[0];
    if (latestEvent?.eventType === "procurement.supplier.updated") {
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement"],
      });
    }
  }, [realtimeEvents, queryClient]);

  // ==========================================================================
  // MUTACIONES
  // ==========================================================================
  const createProveedorMutation = useMutation({
    mutationFn: async (payload: CreateProveedorPayload): Promise<Proveedor> => {
      const res = await apiRequest<Proveedor>("/api/v1/procurement/suppliers", {
        method: "POST",
        body: payload,
      });
      return res.data;
    },
    onSuccess: (created) => {
      toast.success(`Proveedor "${created.razon_social}" registrado con éxito.`);
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement", "suppliers"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement", "dashboard"],
      });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al crear el proveedor.";
      toast.error(msg);
    },
  });

  const updateProveedorMutation = useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number;
      payload: UpdateProveedorPayload;
    }): Promise<Proveedor> => {
      const res = await apiRequest<Proveedor>(`/api/v1/procurement/suppliers/${id}`, {
        method: "PUT",
        body: payload,
      });
      return res.data;
    },
    onSuccess: (updated) => {
      toast.success(`Proveedor "${updated.razon_social}" actualizado.`);
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement", "suppliers"],
      });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al actualizar proveedor.";
      toast.error(msg);
    },
  });

  const deleteProveedorMutation = useMutation({
    mutationFn: async (id: number): Promise<{ ok: boolean; message: string }> => {
      const res = await apiRequest<{ ok: boolean; message: string }>(
        `/api/v1/procurement/suppliers/${id}`,
        {
          method: "DELETE",
        }
      );
      return res.data;
    },
    onSuccess: (_, id) => {
      toast.success(`Proveedor #${id} desactivado correctamente.`);
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement", "suppliers"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "procurement", "dashboard"],
      });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al eliminar proveedor.";
      toast.error(msg);
    },
  });

  const updateCatalogMutation = useMutation({
    mutationFn: async ({
      supplier_id,
      items,
    }: UpdateSupplierCatalogPayload): Promise<ProductoProveedor[]> => {
      const res = await apiRequest<ProductoProveedor[]>(
        `/api/v1/procurement/suppliers/${supplier_id}/products`,
        {
          method: "POST",
          body: { items },
        }
      );
      return res.data;
    },
    onSuccess: (_, vars) => {
      toast.success(`Catálogo de precios actualizado (${vars.items.length} ítems).`);
      void queryClient.invalidateQueries({
        queryKey: queryKeys.procurement.supplierCatalog(tenantId, vars.supplier_id),
      });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al actualizar catálogo.";
      toast.error(msg);
    },
  });

  return {
    // Datos y estados
    proveedores: filteredSuppliers,
    rawSuppliers,
    catalog,
    isLoadingSuppliers,
    isLoadingCatalog,
    isErrorSuppliers,
    isErrorCatalog,
    refetchSuppliers,
    refetchCatalog,

    // Filtros
    filters,
    setFilter,
    resetFilters,
    debouncedSearch,

    // Mutaciones
    createProveedor: createProveedorMutation.mutateAsync,
    isCreatingProveedor: createProveedorMutation.isPending,
    updateProveedor: updateProveedorMutation.mutateAsync,
    isUpdatingProveedor: updateProveedorMutation.isPending,
    deleteProveedor: deleteProveedorMutation.mutateAsync,
    isDeletingProveedor: deleteProveedorMutation.isPending,
    updateCatalog: updateCatalogMutation.mutateAsync,
    isUpdatingCatalog: updateCatalogMutation.isPending,
  };
}
