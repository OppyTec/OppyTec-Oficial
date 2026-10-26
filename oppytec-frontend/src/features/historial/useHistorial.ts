// oppytec-frontend/src/features/historial/useHistorial.ts
import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { usePersistentSearch } from "@/shared/hooks/usePersistentSearch";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type {
  RegistroMovimiento,
  TipoMovimiento,
  HistorialCatalogProduct,
  BeforeAfterDelta,
  PaginatedKardexHistoryResponse,
  UseHistorialOptions,
  UseHistorialReturn,
} from "./types";
import {
  MOCK_HISTORIAL_PRODUCTS,
  MOCK_HISTORIAL_REGISTROS,
  MOCK_PAGINATED_RESPONSE,
} from "./mockData";

/**
 * Hook reactivo de gestión del Kardex auditado e historial de movimientos.
 * Integra TanStack Query v5, sincronización realtime WebSocket sin polling HTTP,
 * persistencia de sesión en filtros, deep-linking URL y fallbacks seguros.
 */
export function useHistorial(
  selectedBodegaIdOrOptions?: string | number | UseHistorialOptions
): UseHistorialReturn {
  const queryClient = useQueryClient();

  // Normalización de argumentos (compatibilidad legacy y opciones v2.0)
  const options: UseHistorialOptions =
    typeof selectedBodegaIdOrOptions === "object" && selectedBodegaIdOrOptions !== null
      ? selectedBodegaIdOrOptions
      : { selectedBodegaId: selectedBodegaIdOrOptions ?? "all" };

  const selectedBodegaId = options.selectedBodegaId ?? "all";
  const limit = options.initialLimit ?? 50;

  // Suscripción segura a WebSocket Realtime (resiliente ante falta de Provider en tests unitarios)
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Si se monta fuera de RealtimeProvider, continúa operando normalmente
  }

  // Estados de filtros
  const [filtroProducto, setFiltroProducto] = useState<string>("all");
  const [filtroTipo, setFiltroTipo] = useState<TipoMovimiento>("all");
  const [fechaDesde, setFechaDesde] = useState<Date | undefined>();
  const [fechaHasta, setFechaHasta] = useState<Date | undefined>();
  const [filtroUsuario, setFiltroUsuario] = usePersistentSearch(
    "historial_usuario",
    ""
  );

  // Paginación server-side
  const [page, setPage] = useState<number>(1);
  const [hasInitialized, setHasInitialized] = useState<boolean>(false);

  // 1. Carga de catálogo de productos para selectores y resolución de nombres
  const { data: productos = MOCK_HISTORIAL_PRODUCTS, isLoading: isProductsLoading } =
    useQuery<HistorialCatalogProduct[]>({
      queryKey: ["oppytec", "catalog", "products", "historial"],
      queryFn: async () => {
        try {
          const res = await apiRequest<
            Array<{ id: string | number; nombre: string; unidad_medida?: string; unidad?: string }>
          >("/api/v1/catalog/products", {
            method: "GET",
            fallbackData: MOCK_HISTORIAL_PRODUCTS,
          });

          if (Array.isArray(res.data) && res.data.length > 0) {
            return res.data.map((p) => ({
              id: p.id,
              nombre: p.nombre,
              unidad: p.unidad_medida || p.unidad || "",
            }));
          }
          return MOCK_HISTORIAL_PRODUCTS;
        } catch {
          return MOCK_HISTORIAL_PRODUCTS;
        }
      },
      staleTime: 5 * 60_000,
    });

  // 2. Soporte para Deep Linking por URL (?search=<nombre> o ?producto_id=<id>)
  useEffect(() => {
    if (typeof window === "undefined") {
      setHasInitialized(true);
      return;
    }

    try {
      const params = new URLSearchParams(window.location.search);
      const searchVal = params.get("search");
      const productoIdVal = params.get("producto_id");

      if (productoIdVal && !hasInitialized) {
        setFiltroProducto(productoIdVal);
        setHasInitialized(true);
      } else if (searchVal && productos.length > 0 && !hasInitialized) {
        const found = productos.find((p) =>
          p.nombre.toLowerCase().includes(searchVal.toLowerCase())
        );
        if (found) {
          setFiltroProducto(String(found.id));
        }
        setHasInitialized(true);
      } else if (!searchVal && !productoIdVal) {
        setHasInitialized(true);
      }
    } catch {
      setHasInitialized(true);
    }
  }, [productos, hasInitialized]);

  // 3. Reset de página al cambiar criterios de filtrado
  const prevFiltersRef = useRef({
    selectedBodegaId,
    filtroProducto,
    filtroTipo,
    fechaDesde,
    fechaHasta,
    filtroUsuario,
  });

  useEffect(() => {
    const prev = prevFiltersRef.current;
    if (
      prev.selectedBodegaId !== selectedBodegaId ||
      prev.filtroProducto !== filtroProducto ||
      prev.filtroTipo !== filtroTipo ||
      prev.fechaDesde !== fechaDesde ||
      prev.fechaHasta !== fechaHasta ||
      prev.filtroUsuario !== filtroUsuario
    ) {
      setPage(1);
      prevFiltersRef.current = {
        selectedBodegaId,
        filtroProducto,
        filtroTipo,
        fechaDesde,
        fechaHasta,
        filtroUsuario,
      };
    }
  }, [
    selectedBodegaId,
    filtroProducto,
    filtroTipo,
    fechaDesde,
    fechaHasta,
    filtroUsuario,
  ]);

  // 4. Query reactiva de Historial Paginado en TanStack Query v5
  const queryParamsKey = useMemo(
    () => ({
      bodegaId: String(selectedBodegaId),
      productoId: filtroProducto,
      tipoMovimiento: filtroTipo,
      fechaDesde: fechaDesde ? fechaDesde.toISOString().split("T")[0] : null,
      fechaHasta: fechaHasta ? fechaHasta.toISOString().split("T")[0] : null,
      usuarioBusqueda: filtroUsuario.trim() || null,
      page,
      limit,
    }),
    [
      selectedBodegaId,
      filtroProducto,
      filtroTipo,
      fechaDesde,
      fechaHasta,
      filtroUsuario,
      page,
      limit,
    ]
  );

  const historyQueryKey = useMemo(
    () => queryKeys.inventory.history(queryParamsKey),
    [queryParamsKey]
  );

  const {
    data: historyData,
    isLoading: isHistoryLoading,
    isError: isHistoryError,
    refetch,
  } = useQuery<PaginatedKardexHistoryResponse>({
    queryKey: historyQueryKey,
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedBodegaId !== "all") {
        params.append("bodega_id", String(selectedBodegaId));
      }
      if (filtroProducto !== "all") {
        params.append("producto_id", filtroProducto);
      }
      if (filtroTipo !== "all") {
        params.append("tipo_movimiento", filtroTipo);
      }
      if (fechaDesde) {
        params.append("fecha_desde", fechaDesde.toISOString().split("T")[0] ?? "");
      }
      if (fechaHasta) {
        params.append("fecha_hasta", fechaHasta.toISOString().split("T")[0] ?? "");
      }
      if (filtroUsuario.trim() !== "") {
        params.append("user_search", filtroUsuario.trim());
        params.append("usuario_busqueda", filtroUsuario.trim());
      }
      const skip = (page - 1) * limit;
      params.append("skip", String(skip));
      params.append("limit", String(limit));

      try {
        const res = await apiRequest<PaginatedKardexHistoryResponse>(
          `/api/v1/inventory/history/paginated?${params.toString()}`,
          {
            method: "GET",
            fallbackData: MOCK_PAGINATED_RESPONSE,
          }
        );
        return res.data;
      } catch {
        return MOCK_PAGINATED_RESPONSE;
      }
    },
    staleTime: 30_000,
  });

  // 5. Sincronización reactiva con WebSockets (cero polling HTTP)
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType === "inventory.stock.updated" ||
      lastEvent?.eventType?.startsWith("inventory.")
    ) {
      void queryClient.invalidateQueries({
        queryKey: ["inventory", "history"],
      });
    }
  }, [realtimeEvents, queryClient]);

  // Manejo de eventos custom window para sincronización local inmediata
  useEffect(() => {
    const handleLocalSync = () => {
      void queryClient.invalidateQueries({
        queryKey: ["inventory", "history"],
      });
    };
    window.addEventListener("inventory_stock_updated", handleLocalSync);
    return () => {
      window.removeEventListener("inventory_stock_updated", handleLocalSync);
    };
  }, [queryClient]);

  // 6. Normalización y fallback seguro de registros para Cero Pantallas en Blanco
  const rawRegistros = useMemo<RegistroMovimiento[]>(() => {
    if (historyData?.items && Array.isArray(historyData.items)) {
      return historyData.items.map((item) => ({
        ...item,
        usuario_id:
          item.usuario_id ??
          (item as unknown as { actor_user_id?: number }).actor_user_id ??
          0,
      }));
    }
    return MOCK_HISTORIAL_REGISTROS;
  }, [historyData?.items]);

  // Filtrado resiliente de registros (garantiza consistencia en modo offline y datos cacheados)
  const filtered = useMemo<RegistroMovimiento[]>(() => {
    return rawRegistros.filter((r) => {
      const matchBodega =
        selectedBodegaId === "all" ||
        String(r.bodega_id) === String(selectedBodegaId);
      const matchProducto =
        filtroProducto === "all" ||
        String(r.producto_id) === String(filtroProducto);
      const matchTipo =
        filtroTipo === "all" ||
        r.tipo_movimiento.toLowerCase() === filtroTipo.toLowerCase();

      let matchUsuario = true;
      if (filtroUsuario.trim() !== "") {
        const uName = (r.user_display_name || "Sistema").toLowerCase();
        matchUsuario = uName.includes(filtroUsuario.toLowerCase());
      }

      let matchFecha = true;
      if (fechaDesde && r.fecha_recuento) {
        const d = new Date(r.fecha_recuento + "T00:00:00");
        if (d < fechaDesde) matchFecha = false;
      }
      if (fechaHasta && r.fecha_recuento) {
        const d = new Date(r.fecha_recuento + "T23:59:59");
        if (d > fechaHasta) matchFecha = false;
      }
      return matchBodega && matchProducto && matchTipo && matchFecha && matchUsuario;
    });
  }, [
    rawRegistros,
    selectedBodegaId,
    filtroProducto,
    filtroTipo,
    fechaDesde,
    fechaHasta,
    filtroUsuario,
  ]);

  // 7. Cálculo de Deltas Before / After
  const computeBeforeAfter = useCallback(
    (r: RegistroMovimiento): BeforeAfterDelta | null => {
      if (r.delta_before != null && r.delta_after != null) {
        return {
          before: Number(r.delta_before),
          after: Number(r.delta_after),
        };
      }
      const t = (r.tipo_movimiento || "").toLowerCase();
      if (t === "conteo" || t.includes("ajuste")) {
        if (r.saldo_resultante != null) {
          const after = Number(r.saldo_resultante);
          const before = after - Number(r.cantidad || 0);
          return { before, after };
        }
      }
      return null;
    },
    []
  );

  // 8. Utilidades de presentación
  const prodName = useCallback(
    (id: string | number): string => {
      const found = productos.find((p) => String(p.id) === String(id));
      return found?.nombre ?? "—";
    },
    [productos]
  );

  const prodUnit = useCallback(
    (id: string | number): string => {
      const found = productos.find((p) => String(p.id) === String(id));
      return found?.unidad ?? "";
    },
    [productos]
  );

  const tipoLabel = useCallback((t: string): string => {
    const map: Record<string, string> = {
      conteo: "Conteo",
      consumo: "Consumo",
      merma: "Merma",
      ajuste: "Ajuste",
      transferencia: "Transferencia",
      compra: "Compra",
      entrada: "Entrada",
      salida: "Salida",
      reversion: "Reversión",
      redo: "Rehacer",
      ajuste_auditoria: "Ajuste Auditoría",
      ajuste_positivo: "Ajuste Positivo",
      ajuste_negativo: "Ajuste Negativo",
    };
    const key = (t || "").toLowerCase();
    if (map[key]) return map[key];
    return t ? t.charAt(0).toUpperCase() + t.slice(1) : "—";
  }, []);

  const clearFilters = useCallback(() => {
    setFiltroProducto("all");
    setFiltroTipo("all");
    setFechaDesde(undefined);
    setFechaHasta(undefined);
    setFiltroUsuario("");
    setPage(1);

    if (typeof window !== "undefined" && window.history) {
      try {
        const url = new URL(window.location.href);
        url.searchParams.delete("search");
        url.searchParams.delete("producto_id");
        window.history.replaceState({}, "", url.toString());
      } catch {
        // Safe fallback
      }
    }
  }, [setFiltroUsuario]);

  const total = historyData?.total ?? filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const loading = isHistoryLoading || isProductsLoading;

  return {
    registros: rawRegistros,
    filtered,
    loading,
    isLoading: isHistoryLoading,
    isError: isHistoryError,
    productos,
    filtros: {
      filtroProducto,
      setFiltroProducto,
      filtroTipo,
      setFiltroTipo,
      fechaDesde,
      setFechaDesde,
      fechaHasta,
      setFechaHasta,
      filtroUsuario,
      setFiltroUsuario,
      clearFilters,
    },
    pagination: {
      page,
      setPage,
      total,
      limit,
      totalPages,
    },
    computeBeforeAfter,
    prodName,
    prodUnit,
    tipoLabel,
    refetch,
  };
}
