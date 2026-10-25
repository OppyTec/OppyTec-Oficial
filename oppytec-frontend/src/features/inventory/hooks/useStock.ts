// oppytec-frontend/src/features/inventory/hooks/useStock.ts
import { useState, useMemo, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type {
  StockItem,
  StockMovement,
  StockFilter,
  StockViewMode,
  StockSemaforo,
  BulkTransferPayload,
  MovementPayload,
  AdjustmentPayload,
  MermaPayload,
} from "../types";
import {
  MOCK_STOCK_ITEMS,
  MOCK_KARDEX_MOVEMENTS,
  MOCK_BODEGAS,
} from "../mockData";

export interface UseStockOptions {
  initialBodegaId?: number | "all";
  initialAreaOperativaId?: number | "all";
  initialViewMode?: StockViewMode;
}

export function useStock(options?: UseStockOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const holdingId = context.holdingId || "holding-gastro-sur";
  const tenantId = context.tenantId || "tenant_rest_central";

  // Intento de suscripción al túnel WebSocket en tiempo real
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Si se monta fuera de RealtimeProvider (ej. tests unitarios), continúa sin fallar
  }

  const [viewMode, setViewMode] = useState<StockViewMode>(
    options?.initialViewMode ?? "agrupado"
  );

  const [filter, setFilter] = useState<StockFilter>({
    search: "",
    bodega_id: options?.initialBodegaId ?? "all",
    area_operativa_id: options?.initialAreaOperativaId ?? "all",
    semaforo: "ALL",
    categoria: "ALL",
    sortBy: "urgency",
  });

  // Query de existencias (Stock Snapshot)
  const effectiveBodegaParam =
    filter.bodega_id !== undefined && filter.bodega_id !== "all"
      ? filter.bodega_id
      : 1;

  const stockQueryKey = useMemo(
    () =>
      queryKeys.inventory.stock({
        holdingId,
        tenantId,
        warehouseId:
          filter.bodega_id && filter.bodega_id !== "all"
            ? String(filter.bodega_id)
            : "all",
      }),
    [holdingId, tenantId, filter.bodega_id]
  );

  const {
    data: stockData,
    isLoading: isStockLoading,
    isError: isStockError,
    refetch: refetchStock,
  } = useQuery<StockItem[]>({
    queryKey: stockQueryKey,
    queryFn: async () => {
      const endpoint = `/api/v1/inventory/stock/status?bodega_id=${effectiveBodegaParam}`;
      const res = await apiRequest<StockItem[]>(endpoint, {
        method: "GET",
        fallbackData: MOCK_STOCK_ITEMS,
      });

      // Si la API devuelve el DTO crudo de backend, aseguramos el contrato frontend
      if (Array.isArray(res.data) && res.data.length > 0) {
        return res.data.map((item, idx) => {
          const fallbackMatch =
            MOCK_STOCK_ITEMS.find(
              (m) =>
                m.producto_id === item.producto_id &&
                m.bodega_id === item.bodega_id
            ) ||
            MOCK_STOCK_ITEMS[idx % MOCK_STOCK_ITEMS.length];

          const semaforo: StockSemaforo =
            item.semaforo ||
            (item.stock_actual <= item.stock_minimo * 0.5
              ? "CRITICO"
              : item.stock_actual <= item.stock_minimo
              ? "MINIMO"
              : "OPTIMO");

          const fallbackUnitCost = fallbackMatch ? fallbackMatch.costo_unitario_ppp : 0;
          return {
            ...fallbackMatch,
            ...item,
            id: item.id ?? `stock-${item.producto_id}-${item.bodega_id}`,
            semaforo,
            costo_total_valorizado:
              item.costo_total_valorizado ??
              item.stock_actual * (item.costo_unitario_ppp || fallbackUnitCost),
          };
        });
      }

      return MOCK_STOCK_ITEMS;
    },
    staleTime: 60_000,
  });

  // Query de movimientos Kardex inmutables
  const kardexQueryKey = useMemo(
    () => ["oppytec", "inventory", "kardex", tenantId] as const,
    [tenantId]
  );

  const {
    data: kardexData,
    isLoading: isKardexLoading,
    refetch: refetchKardex,
  } = useQuery<StockMovement[]>({
    queryKey: kardexQueryKey,
    queryFn: async () => {
      const res = await apiRequest<StockMovement[]>(
        "/api/v1/inventory/kardex/movements",
        {
          method: "GET",
          fallbackData: MOCK_KARDEX_MOVEMENTS,
        }
      );
      return res.data;
    },
    staleTime: 60_000,
  });

  // Invalidación reactiva ante eventos WebSocket push (cero polling)
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const lastEvent = realtimeEvents[0];
    if (
      lastEvent?.eventType === "inventory.stock.updated" ||
      lastEvent?.eventType.startsWith("inventory.")
    ) {
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory"] });
    }
  }, [realtimeEvents, queryClient]);

  // Manejo de eventos custom window para sincronización local
  useEffect(() => {
    const handleLocalSync = () => {
      void queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory"] });
    };
    window.addEventListener("inventory_stock_updated", handleLocalSync);
    return () => {
      window.removeEventListener("inventory_stock_updated", handleLocalSync);
    };
  }, [queryClient]);

  const items = useMemo(() => stockData ?? MOCK_STOCK_ITEMS, [stockData]);
  const movements = useMemo(() => kardexData ?? MOCK_KARDEX_MOVEMENTS, [kardexData]);

  // Filtrado y ordenamiento de la tabla
  const filteredStockItems = useMemo(() => {
    let result = [...items];

    // Filtro por búsqueda textual
    if (filter.search.trim()) {
      const query = filter.search.toLowerCase().trim();
      result = result.filter(
        (i) =>
          i.nombre.toLowerCase().includes(query) ||
          i.sku.toLowerCase().includes(query) ||
          i.categoria.toLowerCase().includes(query) ||
          i.bodega_nombre.toLowerCase().includes(query)
      );
    }

    // Filtro por bodega
    if (filter.bodega_id !== undefined && filter.bodega_id !== "all") {
      result = result.filter((i) => i.bodega_id === Number(filter.bodega_id));
    }

    // Filtro por semáforo
    if (filter.semaforo && filter.semaforo !== "ALL") {
      result = result.filter((i) => i.semaforo === filter.semaforo);
    }

    // Filtro por categoría
    if (filter.categoria && filter.categoria !== "ALL") {
      result = result.filter((i) => i.categoria === filter.categoria);
    }

    // Ordenamiento
    result.sort((a, b) => {
      switch (filter.sortBy) {
        case "urgency": {
          const score = (s: StockSemaforo) =>
            s === "CRITICO" ? 3 : s === "MINIMO" ? 2 : 1;
          return score(b.semaforo) - score(a.semaforo);
        }
        case "az":
          return a.nombre.localeCompare(b.nombre);
        case "za":
          return b.nombre.localeCompare(a.nombre);
        case "stock_asc":
          return a.stock_actual - b.stock_actual;
        case "stock_desc":
          return b.stock_actual - a.stock_actual;
        default:
          return 0;
      }
    });

    return result;
  }, [items, filter]);

  // Agrupamiento por producto o categoría según viewMode
  const groupedStockItems = useMemo(() => {
    const groups = new Map<string, StockItem[]>();
    for (const item of filteredStockItems) {
      const key = item.categoria;
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key)!.push(item);
    }
    return Array.from(groups.entries()).map(([categoria, itemsInCat]) => ({
      categoria,
      color: itemsInCat[0]?.categoria_color ?? "#3B82F6",
      icono: itemsInCat[0]?.categoria_icono ?? "package",
      items: itemsInCat,
      totalValorizado: itemsInCat.reduce((acc, i) => acc + i.costo_total_valorizado, 0),
    }));
  }, [filteredStockItems]);

  // Métodos de mutación y operaciones operativas

  const transferStockBulk = useCallback(
    async (payload: BulkTransferPayload) => {
      try {
        const res = await apiRequest("/api/v1/inventory/stock/bulk-transfer", {
          method: "POST",
          body: {
            bodega_origen_id: payload.bodega_origen_id,
            bodega_destino_id: payload.bodega_destino_id,
            items: payload.items.map((i) => ({
              producto_id: i.producto_id,
              cantidad: i.cantidad,
            })),
            fecha_transferencia: payload.fecha_transferencia,
          },
        });
        toast.success("Transferencia de stock realizada exitosamente");
        void queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory"] });
        window.dispatchEvent(new CustomEvent("inventory_stock_updated"));
        return res.data;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Error desconocido";
        toast.error(`Error en la transferencia: ${message}`);
        throw err;
      }
    },
    [queryClient]
  );

  const registerMovement = useCallback(
    async (payload: MovementPayload | AdjustmentPayload) => {
      try {
        const isAdjustment = "reason" in payload;
        const movementType = payload.tipo_movimiento;
        const body = {
          producto_id: payload.producto_id,
          bodega_id: payload.bodega_id,
          movement_type: movementType,
          quantity: payload.cantidad,
          unit_cost: payload.unit_cost ?? 0,
          lote_codigo: payload.lote_codigo ?? null,
          fecha_vencimiento_lote: payload.fecha_vencimiento_lote ?? null,
          documento_referencia: isAdjustment
            ? `AJUSTE: ${payload.reason}`
            : (payload as MovementPayload).documento_referencia ?? null,
        };

        const res = await apiRequest<StockMovement>(
          "/api/v1/inventory/kardex/movements",
          {
            method: "POST",
            body,
          }
        );
        toast.success("Movimiento registrado en Kardex exitosamente");
        void queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory"] });
        window.dispatchEvent(new CustomEvent("inventory_stock_updated"));
        return res.data;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Error desconocido";
        toast.error(`Error al registrar movimiento: ${message}`);
        throw err;
      }
    },
    [queryClient]
  );

  const undoMovement = useCallback(
    async (movementId: number, reason: string = "Reversión de operación de usuario") => {
      try {
        const res = await apiRequest<StockMovement>("/api/v1/inventory/stock/undo", {
          method: "POST",
          body: { movement_id: movementId, reason },
        });
        toast.success(`Movimiento #${movementId} revertido en Kardex`);
        void queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory"] });
        window.dispatchEvent(new CustomEvent("inventory_stock_updated"));
        return res.data;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Error desconocido";
        toast.error(`No fue posible revertir: ${message}`);
        throw err;
      }
    },
    [queryClient]
  );

  const redoMovement = useCallback(
    async (movementId: number, reason: string = "Reaplicación de operación") => {
      try {
        const res = await apiRequest<StockMovement>("/api/v1/inventory/stock/redo", {
          method: "POST",
          body: { movement_id: movementId, reason },
        });
        toast.success(`Movimiento #${movementId} reaplicado en Kardex`);
        void queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory"] });
        window.dispatchEvent(new CustomEvent("inventory_stock_updated"));
        return res.data;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Error desconocido";
        toast.error(`No fue posible reaplicar: ${message}`);
        throw err;
      }
    },
    [queryClient]
  );

  const reportMerma = useCallback(
    async (payload: MermaPayload) => {
      try {
        const res = await apiRequest("/api/v1/inventory/mermas", {
          method: "POST",
          body: {
            producto_id: payload.producto_id,
            bodega_id: payload.bodega_id,
            quantity: payload.quantity,
            unit_cost: payload.unit_cost,
            reason: payload.reason,
          },
        });
        toast.success("Merma reportada satisfactoriamente");
        void queryClient.invalidateQueries({ queryKey: ["oppytec", "inventory"] });
        return res.data;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Error desconocido";
        toast.error(`Error al reportar merma: ${message}`);
        throw err;
      }
    },
    [queryClient]
  );

  return {
    stockItems: items,
    filteredStockItems,
    groupedStockItems,
    movements,
    bodegas: MOCK_BODEGAS,
    isLoading: isStockLoading || isKardexLoading,
    isStockLoading,
    isKardexLoading,
    isError: isStockError,
    viewMode,
    setViewMode,
    filter,
    setFilter,
    refetchStock,
    refetchKardex,
    transferStockBulk,
    registerMovement,
    undoMovement,
    redoMovement,
    reportMerma,
  };
}
