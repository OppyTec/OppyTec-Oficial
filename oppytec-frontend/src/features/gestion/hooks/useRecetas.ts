import { useState, useMemo, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type {
  Receta,
  CategoriaReceta,
  RecipeFilterParams,
  RecipeCreateInput,
  RecipeUpdateInput,
  DynamicCostResult,
  TipoRecetaFiltro,
  AllergenInfo,
  KitchenSheetResponse,
} from "../types";

export const INITIAL_RECETAS_MOCK: Receta[] = [
  {
    id: "rec-1",
    codigo: "REC-LOM-001",
    nombre: "Lomo Vetado a la Parrilla 350g",
    descripcion: "Corte selecto angus sellado al carbón con chimichurri casero",
    categoria_receta_id: "cat-rec-carnes",
    categoria_nombre: "Carnes a las Brasas",
    es_subreceta: false,
    es_dinamica: true,
    porciones: 1,
    porciones_rendimiento: 1,
    costo_total: 6200,
    costo_total_calculado: 6200,
    costo_porcion: 6200,
    costo_peor_caso: 7400,
    costo_mejor_caso: 6200,
    precio: 18900,
    precio_venta_neto: 15882.35,
    precio_venta_bruto: 18900,
    precio_neto: 15882.35,
    precio_bruto: 18900,
    iva_porcentaje: 19,
    iva_incluido: true,
    margen_neto: 9682.35,
    margen_bruto: 12700,
    margen_pct: 60.96,
    food_cost_pct: 39.04,
    alergenos: [],
    ingredientes_fijos: [
      {
        id: "ing-1",
        receta_id: "rec-1",
        producto_id: "prod-1",
        nombre: "Lomo Vetado Angus",
        target_type: "producto",
        unidad: "kg",
        cantidad_receta: 0.35,
        porcentaje_merma: 5,
        costo_unitario: 14500,
        costo_total: 5328.95,
      },
    ],
    grupos_opciones: [
      {
        id: "rgo-1",
        receta_id: "rec-1",
        grupo_id: "grp-termino",
        orden: 1,
        es_requerido: true,
      },
      {
        id: "rgo-2",
        receta_id: "rec-1",
        grupo_id: "grp-guarnicion",
        orden: 2,
        es_requerido: false,
      },
    ],
  },
  {
    id: "rec-2",
    codigo: "REC-SAL-002",
    nombre: "Salmón Grillado Finas Hierbas",
    descripcion: "Filete de salmón fresco acompañado de mantequilla de finas hierbas",
    categoria_receta_id: "cat-rec-mar",
    categoria_nombre: "Pescados y Mariscos",
    es_subreceta: false,
    es_dinamica: false,
    porciones: 1,
    porciones_rendimiento: 1,
    costo_total: 7100,
    costo_total_calculado: 7100,
    costo_porcion: 7100,
    costo_peor_caso: 7100,
    costo_mejor_caso: 7100,
    precio: 19500,
    precio_venta_neto: 16386.55,
    precio_venta_bruto: 19500,
    precio_neto: 16386.55,
    precio_bruto: 19500,
    iva_porcentaje: 19,
    iva_incluido: true,
    margen_neto: 9286.55,
    margen_bruto: 12400,
    margen_pct: 56.67,
    food_cost_pct: 43.33,
    alergenos: [
      {
        code: "FISH",
        nombre: "Pescado",
        nombre_en: "Fish",
        icono: "Fish",
        descripcion: "Pescado y productos a base de pescado.",
      },
      {
        code: "MILK",
        nombre: "Lácteos",
        nombre_en: "Milk",
        icono: "Milk",
        descripcion: "Leche y sus derivados (mantequilla con lactosa).",
      },
    ],
    ingredientes_fijos: [
      {
        id: "ing-2",
        receta_id: "rec-2",
        producto_id: "prod-3",
        nombre: "Salmón Fresco",
        target_type: "producto",
        unidad: "kg",
        cantidad_receta: 0.25,
        porcentaje_merma: 3,
        costo_unitario: 18000,
        costo_total: 4639.18,
      },
    ],
  },
  {
    id: "rec-sub-1",
    codigo: "SUB-CHIMI-001",
    nombre: "Chimichurri Casero del Chef 1L",
    descripcion: "Sub-receta base de salsa criolla de hierbas para marinar carnes",
    categoria_receta_id: "cat-rec-bases",
    categoria_nombre: "Salsas & Subrecetas",
    es_subreceta: true,
    es_dinamica: false,
    porciones: 10,
    porciones_rendimiento: 10,
    costo_total: 4800,
    costo_total_calculado: 4800,
    costo_porcion: 480,
    costo_peor_caso: 4800,
    costo_mejor_caso: 4800,
    precio: 0,
    precio_venta_neto: 0,
    precio_venta_bruto: 0,
    iva_porcentaje: 19,
    iva_incluido: true,
    margen_neto: 0,
    margen_bruto: 0,
    margen_pct: 0,
    food_cost_pct: 100,
    ingredientes_fijos: [
      {
        id: "ing-sub-1",
        receta_id: "rec-sub-1",
        producto_id: "prod-6",
        nombre: "Aceite de Oliva Extra Virgen",
        target_type: "producto",
        unidad: "litro",
        cantidad_receta: 0.7,
        porcentaje_merma: 0,
        costo_unitario: 5000,
        costo_total: 3500,
      },
    ],
  },
];

export const INITIAL_CATEGORIAS_RECETAS_MOCK: CategoriaReceta[] = [
  { id: "cat-rec-carnes", nombre: "Carnes a las Brasas", color: "#f59e0b", icono: "Flame", orden: 1 },
  { id: "cat-rec-mar", nombre: "Pescados y Mariscos", color: "#06b6d4", icono: "Fish", orden: 2 },
  { id: "cat-rec-pastas", nombre: "Pastas y Masas", color: "#eab308", icono: "Utensils", orden: 3 },
  { id: "cat-rec-bases", nombre: "Salsas & Subrecetas", color: "#8b5cf6", icono: "CookingPot", orden: 4 },
];

export interface UseRecetasOptions {
  initialFilter?: RecipeFilterParams;
  autoSyncWebSocket?: boolean;
}

export function useRecetas(options?: UseRecetasOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  const [filter, setFilter] = useState<RecipeFilterParams>({
    tipo: options?.initialFilter?.tipo ?? "todas",
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
    // Si se monta fuera de RealtimeProvider (ej. tests o stories), continúa con gracia
  }

  // 1. Query: Listado de Recetas
  const recipesQueryKey = useMemo(
    () => queryKeys.recipes.list(tenantId, filter as unknown as Record<string, unknown>),
    [tenantId, filter]
  );

  const {
    data: rawRecetas,
    isLoading: isLoadingRecetas,
    isError: isRecetasError,
    refetch: refetchRecetas,
  } = useQuery<Receta[]>({
    queryKey: recipesQueryKey,
    queryFn: async () => {
      const queryParams = new URLSearchParams();
      if (filter.tipo && filter.tipo !== "todas") queryParams.append("tipo", filter.tipo);
      if (filter.categoria_id) queryParams.append("categoria_id", String(filter.categoria_id));
      if (filter.search?.trim()) queryParams.append("search", filter.search.trim());
      if (filter.limit) queryParams.append("limit", String(filter.limit));
      if (filter.offset) queryParams.append("offset", String(filter.offset));

      const path = `/api/v1/recipes${queryParams.toString() ? `?${queryParams.toString()}` : ""}`;
      const response = await apiRequest<Receta[]>(path, {
        method: "GET",
        fallbackData: INITIAL_RECETAS_MOCK,
      });

      return response.data;
    },
    staleTime: 30_000,
  });

  // 2. Query: Categorías de Recetas
  const categoriesQueryKey = useMemo(() => queryKeys.recipes.categories(tenantId), [tenantId]);

  const {
    data: rawCategorias,
    isLoading: isLoadingCategorias,
    refetch: refetchCategorias,
  } = useQuery<CategoriaReceta[]>({
    queryKey: categoriesQueryKey,
    queryFn: async () => {
      const response = await apiRequest<CategoriaReceta[]>("/api/v1/recipes/categories", {
        method: "GET",
        fallbackData: INITIAL_CATEGORIAS_RECETAS_MOCK,
      });
      return response.data;
    },
    staleTime: 60_000,
  });

  const categorias = useMemo(
    () => (Array.isArray(rawCategorias) ? rawCategorias : INITIAL_CATEGORIAS_RECETAS_MOCK),
    [rawCategorias]
  );

  // Invalidador quirúrgico de cache ante eventos WebSocket (recipes.recipe.updated / recipes.cost.recalculated)
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType === "recipes.recipe.updated" ||
      lastEvent?.eventType === "recipes.cost.recalculated" ||
      lastEvent?.eventType.startsWith("recipes.")
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.recipes.all(tenantId),
      });
    }
  }, [realtimeEvents, queryClient, tenantId]);

  // Soporte para sincronización por CustomEvent de ventana
  useEffect(() => {
    const handleLocalSync = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.recipes.all(tenantId),
      });
    };
    window.addEventListener("recipes_recipe_updated", handleLocalSync);
    return () => {
      window.removeEventListener("recipes_recipe_updated", handleLocalSync);
    };
  }, [queryClient, tenantId]);

  // Lista base
  const recetas = useMemo(
    () => (Array.isArray(rawRecetas) ? rawRecetas : INITIAL_RECETAS_MOCK),
    [rawRecetas]
  );

  // Filtrado reactivo en memoria (garantiza predictibilidad de UI)
  const recetasFiltradas = useMemo(() => {
    let result = [...recetas];

    // Filtro por tipo
    if (filter.tipo === "estaticas") {
      result = result.filter((r) => !r.es_dinamica && !r.es_subreceta);
    } else if (filter.tipo === "dinamicas") {
      result = result.filter((r) => r.es_dinamica);
    } else if (filter.tipo === "subrecetas") {
      result = result.filter((r) => r.es_subreceta);
    }

    // Filtro por categoría
    if (filter.categoria_id) {
      result = result.filter((r) => String(r.categoria_receta_id) === String(filter.categoria_id));
    }

    // Filtro textual
    if (filter.search?.trim()) {
      const term = filter.search.toLowerCase().trim();
      result = result.filter(
        (r) =>
          r.nombre.toLowerCase().includes(term) ||
          r.codigo?.toLowerCase().includes(term) ||
          r.descripcion?.toLowerCase().includes(term)
      );
    }

    return result;
  }, [recetas, filter]);

  // 3. Mutación: Crear Receta
  const createRecetaMutation = useMutation({
    mutationFn: async (payload: RecipeCreateInput) => {
      const response = await apiRequest<Receta>("/api/v1/recipes", {
        method: "POST",
        body: payload,
      });
      return response.data;
    },
    onSuccess: (newRecipe) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recipes.all(tenantId) });
      toast.success(`Receta "${newRecipe.nombre}" creada con éxito.`);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error desconocido al crear la receta";
      toast.error(`No se pudo crear la receta: ${msg}`);
    },
  });

  // 4. Mutación: Actualizar Receta
  const updateRecetaMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string | number; data: RecipeUpdateInput }) => {
      const response = await apiRequest<Receta>(`/api/v1/recipes/${id}`, {
        method: "PUT",
        body: data,
      });
      return response.data;
    },
    onSuccess: (updatedRecipe) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recipes.all(tenantId) });
      toast.success(`Receta "${updatedRecipe.nombre}" actualizada.`);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al actualizar la receta";
      toast.error(`Error: ${msg}`);
    },
  });

  // 5. Mutación: Eliminar Receta (Soft-delete)
  const deleteRecetaMutation = useMutation({
    mutationFn: async (id: string | number) => {
      await apiRequest<void>(`/api/v1/recipes/${id}`, {
        method: "DELETE",
      });
      return id;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recipes.all(tenantId) });
      toast.success(`Receta eliminada.`);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al eliminar la receta";
      toast.error(`Error: ${msg}`);
    },
  });

  // 6. Mutación: Simulación de Costos Dinámicos en Vivo
  const simulateCostMutation = useMutation({
    mutationFn: async ({
      recipeId,
      selectedOptionItemIds,
    }: {
      recipeId: string | number;
      selectedOptionItemIds: (string | number)[];
    }) => {
      const response = await apiRequest<DynamicCostResult>(`/api/v1/recipes/${recipeId}/simulate-cost`, {
        method: "POST",
        body: { selected_option_item_ids: selectedOptionItemIds.map(Number) },
      });
      return response.data;
    },
  });

  // 7. Métodos de Ficha Técnica de Cocina y Trazabilidad de Alérgenos (Fase 6)
  const getKitchenSheet = useCallback(
    async (recipeId: string | number, servings?: number): Promise<KitchenSheetResponse> => {
      const query = servings && servings > 0 ? `?servings=${servings}` : "";
      const response = await apiRequest<KitchenSheetResponse>(
        `/api/v1/recipes/${recipeId}/kitchen-sheet${query}`,
        { method: "GET" }
      );
      return response.data;
    },
    []
  );

  const getAllergens = useCallback(
    async (recipeId: string | number): Promise<AllergenInfo[]> => {
      const response = await apiRequest<AllergenInfo[]>(
        `/api/v1/recipes/${recipeId}/allergens`,
        { method: "GET" }
      );
      return response.data;
    },
    []
  );

  // Acciones auxiliares de filtrado
  const setTipoFiltro = useCallback((tipo: TipoRecetaFiltro) => {
    setFilter((prev) => ({ ...prev, tipo, offset: 0 }));
  }, []);

  const setCategoriaFiltro = useCallback((categoriaId: string | number | null) => {
    setFilter((prev) => ({ ...prev, categoria_id: categoriaId, offset: 0 }));
  }, []);

  const setSearchFiltro = useCallback((search: string) => {
    setFilter((prev) => ({ ...prev, search, offset: 0 }));
  }, []);

  return {
    recetas,
    recetasFiltradas,
    categorias,
    filter,
    setFilter,
    setTipoFiltro,
    setCategoriaFiltro,
    setSearchFiltro,
    isLoading: isLoadingRecetas || isLoadingCategorias,
    isLoadingRecetas,
    isLoadingCategorias,
    isError: isRecetasError,
    refetchRecetas,
    refetchCategorias,
    // Mutaciones y Consultas Especializadas
    createReceta: createRecetaMutation.mutateAsync,
    updateReceta: updateRecetaMutation.mutateAsync,
    deleteReceta: deleteRecetaMutation.mutateAsync,
    simulateCost: simulateCostMutation.mutateAsync,
    getKitchenSheet,
    getAllergens,
    isCreating: createRecetaMutation.isPending,
    isUpdating: updateRecetaMutation.isPending,
    isDeleting: deleteRecetaMutation.isPending,
    isSimulatingCost: simulateCostMutation.isPending,
  };
}

export function useKitchenSheet(
  recipeId: string | number | undefined,
  servings?: number,
  options?: { enabled?: boolean }
) {
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "default-tenant";

  return useQuery({
    queryKey: recipeId
      ? queryKeys.recipes.kitchenSheet(tenantId, recipeId, servings)
      : (["oppytec", "recipes", "kitchenSheet", "disabled"] as const),
    queryFn: async () => {
      if (!recipeId) throw new Error("Recipe ID is required");
      const query = servings && servings > 0 ? `?servings=${servings}` : "";
      const res = await apiRequest<KitchenSheetResponse>(
        `/api/v1/recipes/${recipeId}/kitchen-sheet${query}`,
        { method: "GET" }
      );
      return res.data;
    },
    enabled: Boolean(recipeId) && (options?.enabled ?? true),
    staleTime: 1000 * 60 * 2,
  });
}

export function useRecipeAllergens(
  recipeId: string | number | undefined,
  options?: { enabled?: boolean }
) {
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "default-tenant";

  return useQuery({
    queryKey: recipeId
      ? queryKeys.recipes.allergens(tenantId, recipeId)
      : (["oppytec", "recipes", "allergens", "disabled"] as const),
    queryFn: async () => {
      if (!recipeId) throw new Error("Recipe ID is required");
      const res = await apiRequest<AllergenInfo[]>(
        `/api/v1/recipes/${recipeId}/allergens`,
        { method: "GET" }
      );
      return res.data;
    },
    enabled: Boolean(recipeId) && (options?.enabled ?? true),
    staleTime: 1000 * 60 * 5,
  });
}
