// oppytec-frontend/src/features/consumo/hooks/useConsumo.ts
import { useState, useEffect, useMemo, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type {
  CategoriaConsumo,
  ProductoConsumo,
  RecetaConsumo,
  ComboConsumo,
  CartItem,
  ConsumoTemplate,
  ConsumptionRecord,
  LotInfo,
  OptionSelection,
} from "../types";
import {
  DEFAULT_CONSUMO_COLS,
  MIN_CONSUMO_COLS,
  MAX_CONSUMO_COLS,
} from "../types";
import {
  MOCK_CATEGORIAS_CONSUMO,
  MOCK_PRODUCTOS_CONSUMO,
  MOCK_RECETAS_CONSUMO,
  MOCK_COMBOS_CONSUMO,
  MOCK_TEMPLATES_CONSUMO,
  MOCK_CONSUMPTION_RECORDS,
} from "../mockData";

export interface ContingencyCheckResult {
  isContingency: boolean;
  reason?: "expired_lots" | "out_of_stock";
  expiredLots?: LotInfo[];
  totalStock?: number;
  nonExpiredStock?: number;
  productName?: string;
}

export interface UseConsumoOptions {
  bodegaId?: string;
  areaId?: string | null;
  initialColsCount?: number;
}

export interface ConsumptionRegisterPayload {
  bodega_id: number | string;
  items: Array<{
    tipo_item: "producto" | "receta" | "combo";
    item_id: string;
    cantidad: number;
    unidad_medida?: string;
    costo_unitario_ppp?: number;
    lote_codigo?: string | null;
    fecha_vencimiento_lote?: string | null;
    opciones_seleccionadas?: OptionSelection[] | null;
  }>;
  tipo_origen?: string;
  area_operativa_id?: number | string | null;
  folio_ticket?: string | null;
  notas?: string | null;
  allow_expired?: boolean;
}

export interface MermaExpiredStockPayload {
  producto_id: string;
  bodega_id: number | string;
  quantity: number;
  lote_codigo?: string | null;
  fecha_vencimiento?: string | null;
  motivo?: string;
  unit_cost?: number;
  descripcion?: string;
}

export function useConsumo(
  optionsOrBodegaId: UseConsumoOptions | string = "all",
  areaIdParam: string | null = null
) {
  const options: UseConsumoOptions =
    typeof optionsOrBodegaId === "string"
      ? { bodegaId: optionsOrBodegaId, areaId: areaIdParam }
      : optionsOrBodegaId;

  const bodegaId = options.bodegaId ?? "all";
  const areaId = options.areaId ?? null;

  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const holdingId = context.holdingId || "holding-gastro-sur";
  const tenantId = context.tenantId || "tenant_rest_central";

  // Suscripción al túnel WebSocket zero-polling
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Modo offline o ejecución en pruebas unitarias sin provider
  }

  // Reactividad quirúrgica ante eventos push WebSocket
  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const latestEvent = realtimeEvents[0];
    if (
      latestEvent?.eventType === "consumption.recorded" ||
      latestEvent?.eventType === "inventory.stock.updated"
    ) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.inventory.stock({ holdingId, tenantId }),
      });
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "operations", "consumption"],
      });
    }
  }, [realtimeEvents, queryClient, holdingId, tenantId]);

  // ==========================================================================
  // ESTADO PERSISTENTE DEL CARRITO EN LOCALSTORAGE Y MULTIVENTANA
  // ==========================================================================
  const [cart, setCart] = useState<CartItem[]>(() => {
    if (typeof window === "undefined" || !window.localStorage) return [];
    const saved = localStorage.getItem("consumo_cart");
    if (!saved) return [];
    try {
      const items = JSON.parse(saved);
      if (!Array.isArray(items)) return [];
      const merged: CartItem[] = [];
      items.forEach((i: any) => {
        if (!i || typeof i !== "object") return;
        const optionsStr = JSON.stringify(i.optionSelections || []);
        const existing = merged.find(
          (m) =>
            String(m.id) === String(i.id) &&
            m.type === i.type &&
            (m.bodega_id || "") === (i.bodega_id || "") &&
            JSON.stringify(m.optionSelections || []) === optionsStr
        );
        if (existing) {
          existing.quantity = +(
            existing.quantity + (Number(i.quantity) || 1)
          ).toFixed(3);
        } else {
          merged.push({
            ...i,
            quantity: Number(i.quantity) || 1,
            cartItemId:
              i.cartItemId ||
              `${i.id}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
          });
        }
      });
      return merged;
    } catch {
      return [];
    }
  });

  // Guardar en localStorage y emitir evento custom `cart-updated`
  const persistCart = useCallback((newCart: CartItem[]) => {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        localStorage.setItem("consumo_cart", JSON.stringify(newCart));
        window.dispatchEvent(new Event("cart-updated"));
      }
    } catch {
      // Ignorar quota errors
    }
  }, []);

  // Escuchar sincronización multiventana (evento 'storage' nativo y custom 'cart-updated')
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleSync = () => {
      try {
        const raw = localStorage.getItem("consumo_cart");
        if (raw) {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed)) {
            setCart(parsed);
          }
        } else {
          setCart([]);
        }
      } catch {
        // Fallo seguro
      }
    };

    window.addEventListener("storage", handleSync);
    window.addEventListener("cart-updated", handleSync);
    return () => {
      window.removeEventListener("storage", handleSync);
      window.removeEventListener("cart-updated", handleSync);
    };
  }, []);

  // ==========================================================================
  // CONFIGURACIÓN DE COLUMNAS DE GRILLA (5 a 10)
  // ==========================================================================
  const [colsCount, setColsCountState] = useState<number>(() => {
    if (typeof window === "undefined" || !window.localStorage) {
      return DEFAULT_CONSUMO_COLS;
    }
    const saved = localStorage.getItem("consumo_cols_count");
    if (!saved) return DEFAULT_CONSUMO_COLS;
    const num = Number(saved);
    return isNaN(num) || num < MIN_CONSUMO_COLS || num > MAX_CONSUMO_COLS
      ? DEFAULT_CONSUMO_COLS
      : num;
  });

  const setColsCount = useCallback((val: number) => {
    const clamped = Math.max(MIN_CONSUMO_COLS, Math.min(MAX_CONSUMO_COLS, val));
    setColsCountState(clamped);
    if (typeof window !== "undefined" && window.localStorage) {
      localStorage.setItem("consumo_cols_count", String(clamped));
    }
  }, []);

  const [showOutOfStock, setShowOutOfStockState] = useState<boolean>(() => {
    if (typeof window === "undefined" || !window.localStorage) return false;
    return localStorage.getItem("consumo_show_out_of_stock") === "true";
  });

  const setShowOutOfStock = useCallback((val: boolean) => {
    setShowOutOfStockState(val);
    if (typeof window !== "undefined" && window.localStorage) {
      localStorage.setItem("consumo_show_out_of_stock", String(val));
    }
  }, []);

  // Rango de fechas para historial de consumo
  const [logDate, setLogDate] = useState<Date>(new Date());
  const [logEndDate, setLogEndDate] = useState<Date>(new Date());
  const [isRangeMode, setIsRangeMode] = useState<boolean>(false);

  const getLocalDateString = useCallback((d: Date): string => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }, []);

  // ==========================================================================
  // CONSULTAS TANSTACK QUERY V5 CON FALLBACK RESILIENTE
  // ==========================================================================

  // 1. Categorías de catálogo
  const { data: categorias = MOCK_CATEGORIAS_CONSUMO } = useQuery<
    CategoriaConsumo[]
  >({
    queryKey: queryKeys.catalog.categories(tenantId),
    queryFn: async () => {
      const res = await apiRequest<CategoriaConsumo[]>(
        "/api/v1/catalog/categories",
        {
          fallbackData: MOCK_CATEGORIAS_CONSUMO,
        }
      );
      return res.data;
    },
  });

  // 2. Productos
  const {
    data: rawProductos = MOCK_PRODUCTOS_CONSUMO,
    isLoading: isLoadingProductos,
  } = useQuery<ProductoConsumo[]>({
    queryKey: queryKeys.catalog.products(tenantId),
    queryFn: async () => {
      const res = await apiRequest<ProductoConsumo[]>("/api/v1/catalog/products", {
        fallbackData: MOCK_PRODUCTOS_CONSUMO,
      });
      return res.data;
    },
  });

  // 3. Stock Snapshot por bodega
  const effectiveBodegaParam =
    bodegaId !== "all" && bodegaId !== "none" ? bodegaId : "all";

  const stockQueryKey = useMemo(
    () =>
      queryKeys.inventory.stock({
        holdingId,
        tenantId,
        warehouseId: effectiveBodegaParam,
      }),
    [holdingId, tenantId, effectiveBodegaParam]
  );

  const { data: stockStatusData, isLoading: isLoadingStock } = useQuery<
    any[]
  >({
    queryKey: stockQueryKey,
    queryFn: async () => {
      const endpoint =
        effectiveBodegaParam === "all"
          ? "/api/v1/inventory/stock/status"
          : `/api/v1/inventory/stock/status?bodega_id=${effectiveBodegaParam}`;
      const res = await apiRequest<any[]>(endpoint, {
        fallbackData: [],
      });
      return res.data;
    },
  });

  // 4. Recetas (Escandallos)
  const { data: allRecetas = MOCK_RECETAS_CONSUMO, isLoading: isLoadingRecetas } =
    useQuery<RecetaConsumo[]>({
      queryKey: queryKeys.recipes.escandallos(tenantId),
      queryFn: async () => {
        const res = await apiRequest<RecetaConsumo[]>(
          "/api/v1/recipes/escandallos",
          {
            fallbackData: MOCK_RECETAS_CONSUMO,
          }
        );
        return res.data;
      },
    });

  // 5. Combos
  const { data: allCombos = MOCK_COMBOS_CONSUMO, isLoading: isLoadingCombos } =
    useQuery<ComboConsumo[]>({
      queryKey: queryKeys.recipes.combos(tenantId),
      queryFn: async () => {
        const url = areaId
          ? `/api/v1/recipes/combos?area_id=${encodeURIComponent(areaId)}`
          : "/api/v1/recipes/combos";
        const res = await apiRequest<ComboConsumo[]>(url, {
          fallbackData: MOCK_COMBOS_CONSUMO,
        });
        return res.data;
      },
    });

  // 6. Historial de consumo
  const historyDateStart = getLocalDateString(logDate);
  const historyDateEnd = getLocalDateString(isRangeMode ? logEndDate : logDate);

  const historyQueryKey = useMemo(
    () =>
      queryKeys.operations.consumption.history(tenantId, {
        bodegaId,
        areaId,
        start_date: historyDateStart,
        end_date: historyDateEnd,
      }),
    [tenantId, bodegaId, areaId, historyDateStart, historyDateEnd]
  );

  const {
    data: consumptionHistoryData,
    isLoading: isLoadingHistory,
    refetch: refetchHistory,
  } = useQuery<{ items: ConsumptionRecord[]; total: number }>({
    queryKey: historyQueryKey,
    queryFn: async () => {
      let url = `/api/v1/operations/consumption/history?start_date=${historyDateStart}&end_date=${historyDateEnd}`;
      if (bodegaId !== "all" && bodegaId !== "none") {
        url += `&bodega_id=${encodeURIComponent(bodegaId)}`;
      }
      if (areaId) {
        url += `&area_operativa_id=${encodeURIComponent(areaId)}`;
      }
      const res = await apiRequest<{ items: ConsumptionRecord[]; total: number }>(
        url,
        {
          fallbackData: { items: MOCK_CONSUMPTION_RECORDS, total: 1 },
        }
      );
      return res.data;
    },
  });

  const consumptionLog = useMemo(
    () => consumptionHistoryData?.items ?? MOCK_CONSUMPTION_RECORDS,
    [consumptionHistoryData]
  );

  // 7. Plantillas de Consumo
  const { data: templates = MOCK_TEMPLATES_CONSUMO } = useQuery<
    ConsumoTemplate[]
  >({
    queryKey: queryKeys.operations.consumption.templates(tenantId),
    queryFn: async () => {
      const res = await apiRequest<ConsumoTemplate[]>(
        "/api/v1/operations/consumption/templates",
        {
          fallbackData: MOCK_TEMPLATES_CONSUMO,
        }
      );
      return res.data;
    },
  });

  // ==========================================================================
  // MAPAS DE STOCK Y LOTES EN MEMORIA PARA CÁLCULOS MATEMÁTICOS DE ALTA VELOCIDAD
  // ==========================================================================
  const { stockByProduct, stockByBodega, lotsByProduct } = useMemo(() => {
    const stockMap: Record<string, number> = {};
    const stockBodegaMap: Record<string, Record<string, number>> = {};
    const lotsMap: Record<string, LotInfo[]> = {};

    // 1. Población inicial con los lotes definidos en productos
    rawProductos.forEach((prod) => {
      stockMap[prod.id] = prod.stock_disponible ?? 0;
      stockBodegaMap[prod.id] = {};
      lotsMap[prod.id] = prod.lotes ? [...prod.lotes] : [];
    });

    // 2. Si vino información detallada de stock por bodega desde API, cruzarla
    if (Array.isArray(stockStatusData) && stockStatusData.length > 0) {
      stockStatusData.forEach((s: any) => {
        const pId = String(s.producto_id ?? s.id ?? "");
        const bId = String(s.bodega_id ?? "1");
        const realStock =
          typeof s.stock_total_real === "number"
            ? Math.max(0, s.stock_total_real)
            : typeof s.stock_actual === "number"
            ? Math.max(0, s.stock_actual)
            : 0;

        if (stockMap[pId] === undefined) {
          stockMap[pId] = 0;
          stockBodegaMap[pId] = {};
          lotsMap[pId] = [];
        }

        const currentBodegaMap = stockBodegaMap[pId];
        if (currentBodegaMap && currentBodegaMap[bId] === undefined) {
          currentBodegaMap[bId] = realStock;
        }

        const currentLots = lotsMap[pId];
        if (currentLots && s.fecha_vencimiento && s.stock_actual > 0) {
          currentLots.push({
            lote_codigo: s.lote_codigo ?? null,
            fecha_vencimiento: s.fecha_vencimiento,
            cantidad: s.stock_actual,
          });
        }
      });
    }

    return {
      stockByProduct: stockMap,
      stockByBodega: stockBodegaMap,
      lotsByProduct: lotsMap,
    };
  }, [rawProductos, stockStatusData]);

  // ==========================================================================
  // FUNCIONES MATEMÁTICAS PURAS Y VERIFICADORES
  // ==========================================================================

  const getStock = useCallback(
    (productoId: string, specificBodegaId?: string): number => {
      if (specificBodegaId) {
        return stockByBodega[productoId]?.[specificBodegaId] ?? 0;
      }
      return stockByProduct[productoId] ?? 0;
    },
    [stockByBodega, stockByProduct]
  );

  const getNonExpiredStock = useCallback(
    (productoId: string, specificBodegaId?: string): number => {
      const todayStr = getLocalDateString(new Date());
      const total = getStock(productoId, specificBodegaId);

      const lots = lotsByProduct[productoId] || [];
      const expiredLots = lots.filter((l) => {
        if (!l.fecha_vencimiento) return false;
        return l.fecha_vencimiento < todayStr;
      });

      const expiredSum = expiredLots.reduce((acc, curr) => acc + curr.cantidad, 0);
      return Math.max(0, total - expiredSum);
    },
    [getStock, getLocalDateString, lotsByProduct]
  );

  const getAlertStatus = useCallback(
    (productoId: string): "normal" | "warning" | "critical" => {
      const stock = getStock(productoId);
      const prod = rawProductos.find((p) => p.id === productoId);
      const min = prod?.stock_minimo ?? 0;
      const threshold = prod?.dias_alerta_vencimiento ?? 15;

      if (stock <= 0) return "critical";

      const lots = lotsByProduct[productoId] ?? [];
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      let hasExpired = false;
      let isSoon = false;

      lots.forEach((l) => {
        if (!l.fecha_vencimiento) return;
        const target = new Date(l.fecha_vencimiento + "T00:00:00");
        const diffDays = Math.ceil(
          (target.getTime() - today.getTime()) / (1000 * 3600 * 24)
        );
        if (diffDays < 0) hasExpired = true;
        else if (diffDays <= threshold) isSoon = true;
      });

      if (hasExpired) return "critical";
      if (isSoon || stock <= min) return "warning";
      return "normal";
    },
    [getStock, rawProductos, lotsByProduct]
  );

  const getRecipeAvailability = useCallback(
    (recetaId: string): number => {
      const receta = allRecetas.find((r) => r.id === recetaId);
      if (!receta || !receta.ingredientes?.length) return 0;
      const porciones = Number(receta.porciones) || 1.0;

      let minAvailability = Infinity;
      receta.ingredientes.forEach((ing) => {
        if (!ing.producto_id) return;
        const stock = getStock(ing.producto_id);
        const reqPorPorcion = (ing.cantidad || 0) / porciones;
        const possible =
          reqPorPorcion > 0 ? Math.floor(stock / reqPorPorcion) : Infinity;
        if (possible < minAvailability) minAvailability = possible;
      });

      return minAvailability === Infinity ? 0 : minAvailability;
    },
    [allRecetas, getStock]
  );

  // Verificación de contingencia antes de agregar al carrito
  const checkContingency = useCallback(
    (item: ProductoConsumo, requestedQuantity: number = 1): ContingencyCheckResult => {
      const total = getStock(item.id);
      const nonExpired = getNonExpiredStock(item.id);
      const lots = lotsByProduct[item.id] || [];
      const todayStr = getLocalDateString(new Date());
      const expiredLots = lots.filter(
        (l) => Boolean(l.fecha_vencimiento) && l.fecha_vencimiento < todayStr
      );

      // Si no hay stock absoluto
      if (total <= 0) {
        return {
          isContingency: true,
          reason: "out_of_stock",
          totalStock: 0,
          nonExpiredStock: 0,
          expiredLots: [],
          productName: item.nombre,
        };
      }

      // Si hay lotes vencidos y la cantidad solicitada excede el stock no vencido
      if (expiredLots.length > 0 && nonExpired < requestedQuantity) {
        return {
          isContingency: true,
          reason: "expired_lots",
          expiredLots,
          totalStock: total,
          nonExpiredStock: nonExpired,
          productName: item.nombre,
        };
      }

      return {
        isContingency: false,
        totalStock: total,
        nonExpiredStock: nonExpired,
        expiredLots,
        productName: item.nombre,
      };
    },
    [getStock, getNonExpiredStock, lotsByProduct, getLocalDateString]
  );

  // ==========================================================================
  // FILTRADO Y AGRUPACIÓN
  // ==========================================================================

  const filteredProducts = useMemo(() => {
    return rawProductos.filter((p) => {
      if (showOutOfStock) return true;
      return getNonExpiredStock(p.id) > 0;
    });
  }, [rawProductos, showOutOfStock, getNonExpiredStock]);

  const filteredCategorias = useMemo(() => {
    if (!areaId) return categorias;
    return categorias.filter(
      (cat) =>
        !cat.area_operativa_ids ||
        cat.area_operativa_ids.length === 0 ||
        cat.area_operativa_ids.includes(areaId)
    );
  }, [categorias, areaId]);

  const groupedProducts = useMemo(() => {
    const validCatIds = new Set(filteredCategorias.map((c) => c.id));
    const areaProducts = filteredProducts.filter(
      (p) =>
        !p.categoria_id ||
        validCatIds.has(p.categoria_id) ||
        !categorias.some((c) => c.id === p.categoria_id)
    );

    const grouped = filteredCategorias
      .map((c) => ({
        ...c,
        productos: areaProducts.filter((p) => p.categoria_id === c.id),
      }))
      .filter((c) => c.productos.length > 0);

    const prodsWithoutCategory = areaProducts.filter(
      (p) => !p.categoria_id || !categorias.some((c) => c.id === p.categoria_id)
    );
    if (prodsWithoutCategory.length > 0) {
      grouped.push({
        id: "sin_categoria",
        nombre: "Sin Categoría",
        productos: prodsWithoutCategory,
      });
    }
    return grouped;
  }, [categorias, filteredCategorias, filteredProducts]);

  const recetasDisponibles = useMemo(() => {
    const base = areaId
      ? allRecetas.filter((r) => r.areas_operativas_ids?.includes(areaId))
      : allRecetas;
    return base.filter((r) => getRecipeAvailability(r.id) > 0);
  }, [allRecetas, areaId, getRecipeAvailability]);

  // ==========================================================================
  // OPERACIONES DEL CARRITO
  // ==========================================================================

  const addToCart = useCallback(
    (
      item: ProductoConsumo | RecetaConsumo | ComboConsumo,
      type: "producto" | "receta" | "combo",
      targetBodegaId: string,
      optionSelections?: OptionSelection[]
    ) => {
      setCart((prev) => {
        const optionsStr = JSON.stringify(optionSelections || []);
        const existing = prev.find(
          (i) =>
            String(i.id) === String(item.id) &&
            i.type === type &&
            (i.bodega_id || "") === (targetBodegaId || "") &&
            JSON.stringify(i.optionSelections || []) === optionsStr
        );

        let nextCart: CartItem[];
        if (existing) {
          nextCart = prev.map((i) =>
            i.cartItemId === existing.cartItemId
              ? { ...i, quantity: +(i.quantity + 1).toFixed(3) }
              : i
          );
        } else {
          const unit =
            type === "producto"
              ? (item as ProductoConsumo).unidad || "unidad"
              : type === "receta"
              ? "porc."
              : "comb.";
          const price =
            type === "producto"
              ? (item as ProductoConsumo).precio_venta ||
                (item as ProductoConsumo).costo_unitario ||
                0
              : (item as RecetaConsumo | ComboConsumo).precio || 0;

          nextCart = [
            ...prev,
            {
              cartItemId: `${item.id}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
              id: item.id,
              type,
              quantity: 1,
              name: item.nombre,
              bodega_id: targetBodegaId,
              unit,
              price,
              optionSelections: optionSelections || [],
            },
          ];
        }

        persistCart(nextCart);
        return nextCart;
      });
      toast.success(`${item.nombre} agregado al carrito`);
    },
    [persistCart]
  );

  const removeFromCart = useCallback(
    (cartItemId: string) => {
      setCart((prev) => {
        const nextCart = prev.filter((i) => i.cartItemId !== cartItemId);
        persistCart(nextCart);
        return nextCart;
      });
    },
    [persistCart]
  );

  const updateQuantity = useCallback(
    (cartItemId: string, qty: number) => {
      if (qty <= 0 || isNaN(qty)) return;
      setCart((prev) => {
        const nextCart = prev.map((i) =>
          i.cartItemId === cartItemId ? { ...i, quantity: qty } : i
        );
        persistCart(nextCart);
        return nextCart;
      });
    },
    [persistCart]
  );

  const updateCartItemLot = useCallback(
    (cartItemId: string, lot: string | null) => {
      setCart((prev) => {
        const nextCart = prev.map((i) =>
          i.cartItemId === cartItemId ? { ...i, selectedLot: lot } : i
        );
        persistCart(nextCart);
        return nextCart;
      });
    },
    [persistCart]
  );

  const updateIngredientLotOverride = useCallback(
    (
      cartItemId: string,
      producto_id: string,
      fecha_vencimiento: string | null,
      lote_codigo?: string | null
    ) => {
      setCart((prev) => {
        const nextCart = prev.map((item) => {
          if (item.cartItemId !== cartItemId || item.type !== "receta") return item;
          const existing = item.ingredientLotOverrides || [];
          const filtered = existing.filter((ov) => ov.producto_id !== producto_id);
          return {
            ...item,
            ingredientLotOverrides: [
              ...filtered,
              { producto_id, fecha_vencimiento, lote_codigo },
            ],
          };
        });
        persistCart(nextCart);
        return nextCart;
      });
    },
    [persistCart]
  );

  const clearCart = useCallback(() => {
    setCart([]);
    persistCart([]);
  }, [persistCart]);

  // ==========================================================================
  // MUTACIONES CON INVALIDACIÓN QUIRÚRGICA
  // ==========================================================================

  // 1. Registrar consumo transaccional
  const registerMutation = useMutation({
    mutationFn: async (payload: ConsumptionRegisterPayload) => {
      const res = await apiRequest<ConsumptionRecord>(
        "/api/v1/operations/consumption",
        {
          method: "POST",
          body: payload,
        }
      );
      return res.data;
    },
    onSuccess: () => {
      toast.success("Consumo registrado exitosamente");
      clearCart();
      void queryClient.invalidateQueries({
        queryKey: queryKeys.inventory.stock({ holdingId, tenantId }),
      });
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "operations", "consumption"],
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al registrar consumo");
    },
  });

  // 2. Mermar lote vencido
  const mermaExpiredMutation = useMutation({
    mutationFn: async (payload: MermaExpiredStockPayload) => {
      const res = await apiRequest("/api/v1/operations/consumption/merma-expired", {
        method: "POST",
        body: payload,
      });
      return res.data;
    },
    onSuccess: () => {
      toast.success("Merma de stock vencido procesada");
      void queryClient.invalidateQueries({
        queryKey: queryKeys.inventory.stock({ holdingId, tenantId }),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.inventory.mermas(tenantId),
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al procesar merma");
    },
  });

  // 3. Modificar notas de consumo
  const updateMutation = useMutation({
    mutationFn: async ({ id, notas }: { id: number | string; notas: string }) => {
      const res = await apiRequest<ConsumptionRecord>(
        `/api/v1/operations/consumption/${id}`,
        {
          method: "PUT",
          body: { notas },
        }
      );
      return res.data;
    },
    onSuccess: () => {
      toast.success("Registro de consumo actualizado");
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "operations", "consumption"],
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al actualizar consumo");
    },
  });

  // 4. Anular / Revertir consumo en Kardex
  const deleteMutation = useMutation({
    mutationFn: async ({
      id,
      reason,
    }: {
      id: number | string;
      reason?: string;
    }) => {
      const url = reason
        ? `/api/v1/operations/consumption/${id}?reason=${encodeURIComponent(reason)}`
        : `/api/v1/operations/consumption/${id}`;
      const res = await apiRequest<ConsumptionRecord>(url, {
        method: "DELETE",
      });
      return res.data;
    },
    onSuccess: () => {
      toast.success("Consumo revertido en Kardex");
      void queryClient.invalidateQueries({
        queryKey: queryKeys.inventory.stock({ holdingId, tenantId }),
      });
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "operations", "consumption"],
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al anular consumo");
    },
  });

  // 5. Guardar / Actualizar Plantilla de Consumo
  const saveTemplateMutation = useMutation({
    mutationFn: async (template: ConsumoTemplate) => {
      const res = await apiRequest<ConsumoTemplate>(
        `/api/v1/operations/consumption/templates`,
        {
          method: "POST",
          body: template,
          fallbackData: template,
        }
      );
      return res.data;
    },
    onSuccess: () => {
      toast.success("Plantilla guardada correctamente");
      void queryClient.invalidateQueries({
        queryKey: queryKeys.operations.consumption.templates(tenantId),
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al guardar plantilla");
    },
  });

  // 6. Eliminar Plantilla de Consumo
  const deleteTemplateMutation = useMutation({
    mutationFn: async (templateId: string) => {
      const res = await apiRequest(
        `/api/v1/operations/consumption/templates/${templateId}`,
        {
          method: "DELETE",
        }
      );
      return res.data;
    },
    onSuccess: () => {
      toast.success("Plantilla eliminada");
      void queryClient.invalidateQueries({
        queryKey: queryKeys.operations.consumption.templates(tenantId),
      });
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al eliminar plantilla");
    },
  });

  return {
    // Catálogos
    productos: rawProductos,
    filteredProducts,
    categorias: filteredCategorias,
    recetas: recetasDisponibles,
    allRecetas,
    combos: allCombos,
    templates,
    groupedProducts,
    consumptionLog,
    lotsByProduct,
    stockByBodega,
    // Estados de carga
    loading:
      isLoadingProductos ||
      isLoadingStock ||
      isLoadingRecetas ||
      isLoadingCombos ||
      isLoadingHistory,
    isSaving: registerMutation.isPending,
    // Estado del carrito
    cart,
    setCart,
    addToCart,
    removeFromCart,
    updateQuantity,
    updateCartItemLot,
    updateIngredientLotOverride,
    clearCart,
    // Columnas y filtros
    colsCount,
    setColsCount,
    showOutOfStock,
    setShowOutOfStock,
    logDate,
    setLogDate,
    logEndDate,
    setLogEndDate,
    isRangeMode,
    setIsRangeMode,
    // Cálculos matemáticos y contingencias
    getStock,
    getNonExpiredStock,
    getAlertStatus,
    getRecipeAvailability,
    checkContingency,
    // Mutaciones
    registerConsumption: registerMutation.mutateAsync,
    mermaExpiredStock: mermaExpiredMutation.mutateAsync,
    updateConsumption: updateMutation.mutateAsync,
    deleteConsumption: deleteMutation.mutateAsync,
    saveTemplate: saveTemplateMutation.mutateAsync,
    deleteTemplate: deleteTemplateMutation.mutateAsync,
    refetchHistory,
  };
}
