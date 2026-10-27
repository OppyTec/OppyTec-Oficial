import { useState, useMemo, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type {
  GrupoOpciones,
  OptionGroupCreateInput,
  OptionGroupUpdateInput,
} from "../types";

export const INITIAL_GRUPOS_OPCIONES_MOCK: GrupoOpciones[] = [
  {
    id: "grp-termino",
    nombre: "Término de Cocción de la Carne",
    descripcion: "Punto de cocción preferido por el comensal para cortes a la parrilla",
    seleccion_minima: 1,
    seleccion_maxima: 1,
    min_selecciones: 1,
    max_selecciones: 1,
    permite_repetir: false,
    items: [
      {
        id: "goi-1",
        grupo_id: "grp-termino",
        nombre: "Casi Crudo / Bleu",
        target_type: "producto",
        type: "producto",
        cantidad: 1,
        es_opcion_default: false,
        recargo_precio: 0,
        precio_adicional: 0,
        orden: 1,
        costo_referencial: 0,
      },
      {
        id: "goi-2",
        grupo_id: "grp-termino",
        nombre: "A Punto / Término Medio (Recomendado)",
        target_type: "producto",
        type: "producto",
        cantidad: 1,
        es_opcion_default: true,
        recargo_precio: 0,
        precio_adicional: 0,
        orden: 2,
        costo_referencial: 0,
      },
      {
        id: "goi-3",
        grupo_id: "grp-termino",
        nombre: "Tres Cuartos (3/4)",
        target_type: "producto",
        type: "producto",
        cantidad: 1,
        es_opcion_default: false,
        recargo_precio: 0,
        precio_adicional: 0,
        orden: 3,
        costo_referencial: 0,
      },
      {
        id: "goi-4",
        grupo_id: "grp-termino",
        nombre: "Bien Cocido",
        target_type: "producto",
        type: "producto",
        cantidad: 1,
        es_opcion_default: false,
        recargo_precio: 0,
        precio_adicional: 0,
        orden: 4,
        costo_referencial: 0,
      },
    ],
  },
  {
    id: "grp-guarnicion",
    nombre: "Guarnición de Acompañamiento",
    descripcion: "Acompañamiento para platos principales",
    seleccion_minima: 0,
    seleccion_maxima: 2,
    min_selecciones: 0,
    max_selecciones: 2,
    permite_repetir: false,
    items: [
      {
        id: "goi-5",
        grupo_id: "grp-guarnicion",
        producto_id: "prod-papa-rustica",
        nombre: "Papas Rústicas al Romero",
        target_type: "producto",
        type: "producto",
        cantidad: 0.2,
        es_opcion_default: true,
        recargo_precio: 0,
        precio_adicional: 0,
        orden: 1,
        costo_referencial: 650,
      },
      {
        id: "goi-6",
        grupo_id: "grp-guarnicion",
        producto_id: "prod-ensalada-mixta",
        nombre: "Ensalada Verde de Temporada",
        target_type: "producto",
        type: "producto",
        cantidad: 0.15,
        es_opcion_default: false,
        recargo_precio: 500,
        precio_adicional: 500,
        orden: 2,
        costo_referencial: 850,
      },
      {
        id: "goi-7",
        grupo_id: "grp-guarnicion",
        receta_id: "rec-risotto-hongos",
        nombre: "Risotto de Hongos Silvestres (Premium)",
        target_type: "receta",
        type: "receta",
        cantidad: 0.18,
        es_opcion_default: false,
        recargo_precio: 2500,
        precio_adicional: 2500,
        orden: 3,
        costo_referencial: 1800,
      },
    ],
  },
  {
    id: "grp-bebestible",
    nombre: "Bebestible de Combo",
    descripcion: "Selección de bebida o vino para combos y menús",
    seleccion_minima: 1,
    seleccion_maxima: 1,
    min_selecciones: 1,
    max_selecciones: 1,
    permite_repetir: false,
    items: [
      {
        id: "goi-8",
        grupo_id: "grp-bebestible",
        producto_id: "prod-8",
        nombre: "Vino Cabernet Sauvignon Reserva 750ml",
        target_type: "producto",
        type: "producto",
        cantidad: 1,
        es_opcion_default: true,
        recargo_precio: 0,
        precio_adicional: 0,
        orden: 1,
        costo_referencial: 5200,
      },
      {
        id: "goi-9",
        grupo_id: "grp-bebestible",
        producto_id: "prod-9",
        nombre: "Cerveza Artesanal IPA 330ml",
        target_type: "producto",
        type: "producto",
        cantidad: 1,
        es_opcion_default: false,
        recargo_precio: 0,
        precio_adicional: 0,
        orden: 2,
        costo_referencial: 1200,
      },
    ],
  },
];

export interface UseGruposOpcionesOptions {
  searchQuery?: string;
}

export function useGruposOpciones(options?: UseGruposOpcionesOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  const [search, setSearch] = useState<string>(options?.searchQuery ?? "");

  // Suscripción al túnel WebSocket en tiempo real con Zero-Polling
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Si se monta fuera de RealtimeProvider, continúa con gracia
  }

  // 1. Query: Biblioteca de Grupos de Opciones
  const optionGroupsQueryKey = useMemo(
    () => queryKeys.recipes.optionGroups(tenantId),
    [tenantId]
  );

  const {
    data: rawGrupos,
    isLoading,
    isError,
    refetch,
  } = useQuery<GrupoOpciones[]>({
    queryKey: optionGroupsQueryKey,
    queryFn: async () => {
      const response = await apiRequest<GrupoOpciones[]>("/api/v1/recipes/option-groups", {
        method: "GET",
        fallbackData: INITIAL_GRUPOS_OPCIONES_MOCK,
      });
      return response.data;
    },
    staleTime: 60_000,
  });

  // Invalidador reactivo ante eventos WebSocket
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType === "recipes.options.updated" ||
      lastEvent?.eventType === "recipes.recipe.updated" ||
      lastEvent?.eventType.startsWith("recipes.")
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.recipes.optionGroups(tenantId),
      });
    }
  }, [realtimeEvents, queryClient, tenantId]);

  // Soporte para sincronización por CustomEvent de ventana
  useEffect(() => {
    const handleLocalSync = () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.recipes.optionGroups(tenantId),
      });
    };
    window.addEventListener("recipes_options_updated", handleLocalSync);
    return () => {
      window.removeEventListener("recipes_options_updated", handleLocalSync);
    };
  }, [queryClient, tenantId]);

  const gruposOpciones = useMemo(
    () => (Array.isArray(rawGrupos) ? rawGrupos : INITIAL_GRUPOS_OPCIONES_MOCK),
    [rawGrupos]
  );

  // Filtrado reactivo en memoria para autocompletado y buscadores
  const gruposFiltrados = useMemo(() => {
    if (!search.trim()) return gruposOpciones;
    const term = search.toLowerCase().trim();
    return gruposOpciones.filter(
      (g) =>
        g.nombre.toLowerCase().includes(term) ||
        g.descripcion?.toLowerCase().includes(term) ||
        g.items.some((i) => i.nombre?.toLowerCase().includes(term))
    );
  }, [gruposOpciones, search]);

  // 2. Mutación: Crear Grupo de Opciones (Biblioteca o In-situ)
  const createGrupoMutation = useMutation({
    mutationFn: async (payload: OptionGroupCreateInput) => {
      const response = await apiRequest<GrupoOpciones>("/api/v1/recipes/option-groups", {
        method: "POST",
        body: payload,
      });
      return response.data;
    },
    onSuccess: (newGroup) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recipes.optionGroups(tenantId) });
      toast.success(`Grupo de opciones "${newGroup.nombre}" creado.`);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al crear grupo de opciones";
      toast.error(`Error: ${msg}`);
    },
  });

  // 3. Mutación: Actualizar Grupo de Opciones
  const updateGrupoMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string | number; data: OptionGroupUpdateInput }) => {
      const response = await apiRequest<GrupoOpciones>(`/api/v1/recipes/option-groups/${id}`, {
        method: "PUT",
        body: data,
      });
      return response.data;
    },
    onSuccess: (updatedGroup) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recipes.optionGroups(tenantId) });
      toast.success(`Grupo "${updatedGroup.nombre}" actualizado.`);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al actualizar grupo";
      toast.error(`Error: ${msg}`);
    },
  });

  // 4. Mutación: Eliminar Grupo de Opciones
  const deleteGrupoMutation = useMutation({
    mutationFn: async (id: string | number) => {
      await apiRequest<void>(`/api/v1/recipes/option-groups/${id}`, {
        method: "DELETE",
      });
      return id;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recipes.optionGroups(tenantId) });
      toast.success("Grupo de opciones eliminado.");
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Error al eliminar grupo de opciones";
      toast.error(`Error: ${msg}`);
    },
  });

  const getGrupoById = useCallback(
    (id: string | number) => {
      return gruposOpciones.find((g) => String(g.id) === String(id));
    },
    [gruposOpciones]
  );

  return {
    gruposOpciones,
    gruposFiltrados,
    search,
    setSearch,
    getGrupoById,
    isLoading,
    isError,
    refetch,
    // Mutaciones
    createGrupoOpciones: createGrupoMutation.mutateAsync,
    updateGrupoOpciones: updateGrupoMutation.mutateAsync,
    deleteGrupoOpciones: deleteGrupoMutation.mutateAsync,
    isCreating: createGrupoMutation.isPending,
    isUpdating: updateGrupoMutation.isPending,
    isDeleting: deleteGrupoMutation.isPending,
  };
}
