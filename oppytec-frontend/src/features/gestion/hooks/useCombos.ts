import { useState, useMemo, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type {
  Combo,
  CategoriaCombo,
  ComboFilterParams,
  ComboCreateInput,
  ComboUpdateInput,
} from "../types";

export const INITIAL_COMBOS_MOCK: Combo[] = [
  {
    id: "combo-1",
    codigo: "CMB-PARR-001",
    nombre: "Menú Ejecutivo Parrillero",
    descripcion: "Lomo vetado a la parrilla + copa de vino reserva o bebida a elección",
    categoria_combo_id: "cat-cmb-ejecutivos",
    categoria_nombre: "Menús Ejecutivos",
    es_dinamico: true,
    precio: 23900,
    precio_venta_neto: 20084.03,
    precio_venta_bruto: 23900,
    precio_neto: 20084.03,
    precio_bruto: 23900,
    costo_total: 8900,
    costo_total_calculado: 8900,
    costo_base: 8900,
    margen_amount: 11184.03,
    margen_pct: 55.69,
    food_cost_pct: 44.31,
    iva_porcentaje: 19,
    iva_incluido: true,
    disponibilidad_stock_porciones: 18,
    esta_disponible: true,
    items_fijos: [
      {
        id: "cf-1",
        combo_id: "combo-1",
        receta_id: "rec-1",
        nombre: "Lomo Vetado a la Parrilla 350g",
        target_type: "receta",
        cantidad: 1,
        costo_unitario: 6200,
        costo_total: 6200,
      },
    ],
    grupos_opciones: [
      {
        id: "cgo-1",
        combo_id: "combo-1",
        grupo_id: "grp-bebestible",
        orden: 1,
        es_requerido: true,
      },
    ],
  },
  {
    id: "combo-2",
    codigo: "CMB-DUO-002",
    nombre: "Dúo Marino Austral",
    descripcion: "2 porciones de Salmón grillado finas hierbas para compartir",
    categoria_combo_id: "cat-cmb-promos",
    categoria_nombre: "Promociones y Dúos",
    es_dinamico: false,
    precio: 34900,
    precio_venta_neto: 29327.73,
    precio_venta_bruto: 34900,
    precio_neto: 29327.73,
    precio_bruto: 34900,
    costo_total: 14200,
    costo_total_calculado: 14200,
    costo_base: 14200,
    margen_amount: 15127.73,
    margen_pct: 51.58,
    food_cost_pct: 48.42,
    iva_porcentaje: 19,
    iva_incluido: true,
    disponibilidad_stock_porciones: 12,
    esta_disponible: true,
    items_fijos: [
      {
        id: "cf-2",
        combo_id: "combo-2",
        receta_id: "rec-2",
        nombre: "Salmón Grillado Finas Hierbas",
        target_type: "receta",
        cantidad: 2,
        costo_unitario: 7100,
        costo_total: 14200,
      },
    ],
  },
];

export const INITIAL_CATEGORIAS_COMBOS_MOCK: CategoriaCombo[] = [
  { id: "cat-cmb-ejecutivos", nombre: "Menús Ejecutivos", color: "#ec4899", icono: "Boxes", orden: 1 },
  { id: "cat-cmb-promos", nombre: "Promociones y Dúos", color: "#8b5cf6", icono: "Tags", orden: 2 },
  { id: "cat-cmb-degustacion", nombre: "Tablas & Degustación", color: "#f59e0b", icono: "Sparkles", orden: 3 },
];

export interface UseCombosOptions {
  initialFilter?: ComboFilterParams;
}

export function useCombos(options?: UseCombosOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  const [filter, setFilter] = useState<ComboFilterParams>({
    categoria_id: options?.initialFilter?.categoria_id ?? null,
    search: options?.initialFilter?.search ?? "",
    limit: options?.initialFilter?.limit ?? 50,
    offset: options?.initialFilter?.offset ?? 0,
  });

  // Suscripción al túnel WebSocket en tiempo real con Zero-Polling
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Si se monta fuera de RealtimeProvider, continúa con gracia
  }

  // 1. Query: Listado de Combos
  const combosQueryKey = useMemo(
    () => queryKeys.recipes.combos(tenantId, filter as unknown as Record<string, unknown>),
    [tenantId, filter]
  );

  const {
    data: rawCombos,
    isLoading: isLoadingCombos,
    isError: isCombosError,
    refetch: refetchCombos,
  } = useQuery<Combo[]>({
    queryKey: combosQueryKey,
    queryFn: async () => {
      const queryParams = new URLSearchParams();
      if (filter.categoria_id) queryParams.append("categoria_id", String(filter.categoria_id));
      if (filter.search?.trim()) queryParams.append("search", filter.search.trim());
      if (filter.limit) queryParams.append("limit", String(filter.limit));
      if (filter.offset) queryParams.append("offset", String(filter.offset));

      const path = `/api/v1/combos${queryParams.toString() ? `?${queryParams.toString()}` : ""}`;
      const response = await apiRequest<Combo[]>(path, {
        method: "GET",
        fallbackData: INITIAL_COMBOS_MOCK,
      });

      return response.data;
    },
    staleTime: 30_000,
  });

  // 2. Query: Categorías de Combos
  const comboCategoriesQueryKey = useMemo(
    () => queryKeys.recipes.comboCategories(tenantId),
    [tenantId]
  );

  const {
    data: rawCategorias,
    isLoading: isLoadingCategorias,
    refetch: refetchCategorias,
  } = useQuery<CategoriaCombo[]>({
    queryKey: comboCategoriesQueryKey,
    queryFn: async () => {
      const response = await apiRequest<CategoriaCombo[]>("/api/v1/combos/categories", {
        method: "GET",
        fallbackData: INITIAL_CATEGORIAS_COMBOS_MOCK,
      });
      return response.data;
    },
    staleTime: 60_000,
  });

  const categorias = useMemo(
    () => (Array.isArray(rawCategorias) ? rawCategorias : INITIAL_CATEGORIAS_COMBOS_MOCK),
    [rawCategorias]
  );

  // Invalidador quirúrgico de cache ante eventos WebSocket (recipes.combo.updated / recipes.recipe.updated)
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType === "recipes.combo.updated" ||
      lastEvent?.eventType === "recipes.recipe.updated" ||
      lastEvent?.eventType.startsWith("recipes.")
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.recipes.combos(tenantId),
      });
    }
  }, [realtimeEvents, queryClient, tenantId]);

  // Soporte para sincronización por CustomEvent de ventana
  useEffect(() => {
    const handleLocalSync = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.recipes.combos(tenantId),
      });
    };
    window.addEventListener("recipes_combo_updated", handleLocalSync);
    return () => {
      window.removeEventListener("recipes_combo_updated", handleLocalSync);
    };
  }, [queryClient, tenantId]);

  // Lista base
  const combos = useMemo(
    () => (Array.isArray(rawCombos) ? rawCombos : INITIAL_COMBOS_MOCK),
    [rawCombos]
  );

  // Filtrado reactivo en memoria
  const combosFiltrados = useMemo(() => {
    let result = [...combos];

    if (filter.categoria_id) {
      result = result.filter((c) => String(c.categoria_combo_id) === String(filter.categoria_id));
    }

    if (filter.search?.trim()) {
      const term = filter.search.toLowerCase().trim();
      result = result.filter(
        (c) =>
          c.nombre.toLowerCase().includes(term) ||
          c.codigo?.toLowerCase().includes(term) ||
          c.descripcion?.toLowerCase().includes(term)
      );
    }

    return result;
  }, [combos, filter]);

  // 3. Mutación: Crear Combo
  const createComboMutation = useMutation({
    mutationFn: async (payload: ComboCreateInput) => {
      const response = await apiRequest<Combo>("/api/v1/combos", {
        method: "POST",
        body: payload,
      });
      return response.data;
    },
    onSuccess: (newCombo) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recipes.combos(tenantId) });
      toast.success(`Combo "${newCombo.nombre}" creado con éxito.`);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al crear el combo";
      toast.error(`No se pudo crear el combo: ${msg}`);
    },
  });

  // 4. Mutación: Actualizar Combo
  const updateComboMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string | number; data: ComboUpdateInput }) => {
      const response = await apiRequest<Combo>(`/api/v1/combos/${id}`, {
        method: "PUT",
        body: data,
      });
      return response.data;
    },
    onSuccess: (updatedCombo) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recipes.combos(tenantId) });
      toast.success(`Combo "${updatedCombo.nombre}" actualizado.`);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al actualizar el combo";
      toast.error(`Error: ${msg}`);
    },
  });

  // 5. Mutación: Eliminar Combo (Soft-delete)
  const deleteComboMutation = useMutation({
    mutationFn: async (id: string | number) => {
      await apiRequest<void>(`/api/v1/combos/${id}`, {
        method: "DELETE",
      });
      return id;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recipes.combos(tenantId) });
      toast.success("Combo eliminado con éxito.");
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al eliminar el combo";
      toast.error(`Error: ${msg}`);
    },
  });

  const setCategoriaFiltro = useCallback((categoriaId: string | number | null) => {
    setFilter((prev) => ({ ...prev, categoria_id: categoriaId, offset: 0 }));
  }, []);

  const setSearchFiltro = useCallback((search: string) => {
    setFilter((prev) => ({ ...prev, search, offset: 0 }));
  }, []);

  return {
    combos,
    combosFiltrados,
    categorias,
    filter,
    setFilter,
    setCategoriaFiltro,
    setSearchFiltro,
    isLoading: isLoadingCombos || isLoadingCategorias,
    isLoadingCombos,
    isLoadingCategorias,
    isError: isCombosError,
    refetchCombos,
    refetchCategorias,
    // Mutaciones
    createCombo: createComboMutation.mutateAsync,
    updateCombo: updateComboMutation.mutateAsync,
    deleteCombo: deleteComboMutation.mutateAsync,
    isCreating: createComboMutation.isPending,
    isUpdating: updateComboMutation.isPending,
    isDeleting: deleteComboMutation.isPending,
  };
}
