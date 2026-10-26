// oppytec-frontend/src/features/inventory/alerts/AlertasPage.tsx
import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { TablePagination } from "@/shared/components/ui/TablePagination";
import { cn } from "@/shared/lib";
import { useAlertas } from "./hooks/useAlertas";
import {
  AlertasToolbar,
  StockCriticoCard,
  ExpiredLotCard,
  UpcomingExpiryCard,
  StockCriticoTable,
  VencimientosCard,
} from "./components";
import type {
  AlertFilterType,
  AlertViewMode,
  AlertProductItem,
  CriticalStockAlert,
  CartPurchaseItem,
} from "./types";

export function AlertasPage() {
  const navigate = useNavigate();
  const { t } = useTranslation("alerts");

  // Selectores de área y bodega
  const [selectedAreaId, setSelectedAreaId] = useState<string>("all");
  const [activeWarehouseId, setActiveWarehouseId] = useState<string>("all");

  // Filtro de alertas
  const [filterType, setFilterType] = useState<AlertFilterType>("all");

  // Hook reactivo de alertas (con Zero-Polling y WebSocket realtime)
  const {
    stockCritico,
    vencidos,
    vencimientosProximos,
    loading,
  } = useAlertas({
    bodegaIds: activeWarehouseId === "all" ? undefined : activeWarehouseId,
    areaOperativaId: selectedAreaId === "all" ? undefined : selectedAreaId,
    filterType,
  });

  // Modo de vista ('cards' | 'list') con persistencia en localStorage
  const [viewMode, setViewMode] = useState<AlertViewMode>(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      const saved = window.localStorage.getItem("alerts_view_mode");
      if (saved === "list" || saved === "cards") {
        return saved;
      }
    }
    return "cards";
  });

  const handleSetViewMode = useCallback((mode: AlertViewMode) => {
    setViewMode(mode);
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem("alerts_view_mode", mode);
      }
    } catch {
      // Ignorar fallos en contextos de prueba restringidos
    }
  }, []);

  // Tamaño de página con persistencia en localStorage
  const [pageSize, setPageSize] = useState<number>(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      const saved = window.localStorage.getItem("alerts_page_size");
      if (saved) {
        const parsed = parseInt(saved, 10);
        if (!isNaN(parsed) && parsed > 0) return parsed;
      }
    }
    return 10;
  });

  const [currentPage, setCurrentPage] = useState<number>(1);

  const handlePageSizeChange = useCallback((newSize: number) => {
    setPageSize(newSize);
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem("alerts_page_size", String(newSize));
      }
    } catch {
      // Ignorar fallos en contextos de prueba restringidos
    }
    setCurrentPage(1);
  }, []);

  // Reiniciar a página 1 ante cambio de filtro o modo de vista
  useEffect(() => {
    setCurrentPage(1);
  }, [filterType, viewMode, activeWarehouseId, selectedAreaId]);

  // Sincronizar badge de notificaciones globales en localStorage
  useEffect(() => {
    if (loading) return;
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        const total = stockCritico.length + vencidos.length + vencimientosProximos.length;
        const critical = stockCritico.length > 0 || vencidos.length > 0;
        window.localStorage.setItem("notif_total_count", String(total));
        window.localStorage.setItem("notif_has_critical", String(critical));
        window.dispatchEvent(new Event("notif-updated"));
      }
    } catch {
      // Safe catch
    }
  }, [stockCritico.length, vencidos.length, vencimientosProximos.length, loading]);

  // Ítems paginados
  const paginatedStockCritico = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return stockCritico.slice(start, start + pageSize);
  }, [stockCritico, currentPage, pageSize]);

  const paginatedVencidos = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return vencidos.slice(start, start + pageSize);
  }, [vencidos, currentPage, pageSize]);

  const paginatedVencimientosProximos = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return vencimientosProximos.slice(start, start + pageSize);
  }, [vencimientosProximos, currentPage, pageSize]);

  // Total de elementos para el control de paginación
  const totalItems = useMemo(() => {
    if (filterType === "stock") return stockCritico.length;
    if (filterType === "expired") return vencidos.length;
    if (filterType === "upcoming") return vencimientosProximos.length;
    return Math.max(stockCritico.length, vencidos.length, vencimientosProximos.length);
  }, [filterType, stockCritico.length, vencidos.length, vencimientosProximos.length]);

  // Carrito de compra rápida (gestión de reposición persistente)
  const [animatingCarts, setAnimatingCarts] = useState<Record<string, boolean>>({});
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach(clearTimeout);
    };
  }, []);

  const addToCart = useCallback(
    (item: CriticalStockAlert | AlertProductItem, e?: React.MouseEvent) => {
      if (e) e.stopPropagation();

      const numProductId = typeof item.producto_id === "number" ? item.producto_id : 0;
      if (!numProductId) return;

      const numBodegaId = typeof item.bodega_id === "number" ? item.bodega_id : 1;

      const targetBodegaName =
        "bodega_nombre" in item && item.bodega_nombre
          ? item.bodega_nombre
          : "Bodega Principal";

      const productName =
        "producto_nombre" in item && item.producto_nombre
          ? item.producto_nombre
          : "nombre" in item && item.nombre
          ? item.nombre
          : "Producto";

      const unitName =
        "unidad_medida" in item && item.unidad_medida
          ? item.unidad_medida
          : "unidad" in item && item.unidad
          ? item.unidad
          : "un";

      const price =
        "costo_promedio" in item && typeof item.costo_promedio === "number"
          ? item.costo_promedio
          : "costo_unitario" in item && typeof item.costo_unitario === "number"
          ? item.costo_unitario
          : "costo_ppp" in item && typeof (item as any).costo_ppp === "number"
          ? (item as any).costo_ppp
          : 0;

      const rawId = "id" in item && item.id ? String(item.id) : undefined;
      const compositeId = `${numProductId}::${numBodegaId}`;
      const prodIdStr = String(numProductId);

      // Micro-animación morada durante 400ms
      setAnimatingCarts((prev) => {
        const next: Record<string, boolean> = {
          ...prev,
          [compositeId]: true,
          [prodIdStr]: true,
        };
        if (rawId) next[rawId] = true;
        return next;
      });

      const timer = setTimeout(() => {
        setAnimatingCarts((prev) => {
          const next: Record<string, boolean> = {
            ...prev,
            [compositeId]: false,
            [prodIdStr]: false,
          };
          if (rawId) next[rawId] = false;
          return next;
        });
      }, 400);
      timeoutsRef.current.push(timer);

      let nextCart: CartPurchaseItem[] = [];
      try {
        const saved = window.localStorage.getItem("gestion_purchase_cart");
        const currentCart: CartPurchaseItem[] = saved ? JSON.parse(saved) : [];
        const existingIndex = currentCart.findIndex(
          (it) => it.producto_id === numProductId && it.bodega_id === numBodegaId
        );

        if (existingIndex >= 0) {
          nextCart = currentCart.map((it, idx) =>
            idx === existingIndex ? { ...it, cantidad: it.cantidad + 1 } : it
          );
        } else {
          nextCart = [
            ...currentCart,
            {
              producto_id: numProductId,
              bodega_id: numBodegaId,
              bodega_nombre: targetBodegaName,
              nombre: productName,
              cantidad: 1,
              precio: price,
              unidad: unitName,
            },
          ];
        }
      } catch {
        nextCart = [
          {
            producto_id: numProductId,
            bodega_id: numBodegaId,
            bodega_nombre: targetBodegaName,
            nombre: productName,
            cantidad: 1,
            precio: price,
            unidad: unitName,
          },
        ];
      }

      try {
        if (typeof window !== "undefined" && window.localStorage) {
          window.localStorage.setItem("gestion_purchase_cart", JSON.stringify(nextCart));
          window.dispatchEvent(new Event("cart-updated"));
        }
      } catch {
        // Safe catch
      }

      toast.success(
        targetBodegaName
          ? t("toast.cart_added_with_warehouse", {
              product: productName,
              warehouse: targetBodegaName,
            })
          : t("toast.cart_added", { product: productName })
      );
    },
    [t]
  );

  return (
    <div className="relative min-h-screen" data-testid="alertas-page">
      <div className="relative space-y-6 pb-12">
        {/* Cabecera Canónica Centrada OppyTec */}
        <SectionHeader
          title={t("title")}
          subtitle={t("subtitle")}
          icon={AlertTriangle}
          color="#ef4444"
          center
        />

        {/* Toolbar Unificado de Control */}
        <AlertasToolbar
          selectedAreaId={selectedAreaId}
          onSelectArea={setSelectedAreaId}
          activeWarehouseId={activeWarehouseId}
          onSelectWarehouse={setActiveWarehouseId}
          filterType={filterType}
          onFilterChange={setFilterType}
          viewMode={viewMode}
          onViewModeChange={handleSetViewMode}
        />

        {/* Estado de Carga Elegante */}
        {loading ? (
          <div
            className="flex h-[40vh] items-center justify-center"
            data-testid="alerts-loading"
          >
            <div className="flex flex-col items-center gap-2">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                {t("loading")}
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* ===================================================================
                MODO LISTADO ('list') — Paridad 1:1 con Legacy StockCriticoTable & VencimientosCard
                =================================================================== */}
            {viewMode === "list" ? (
              <div className="space-y-8 px-2" data-testid="alerts-list-view">
                {/* Stock Crítico Tabular */}
                {(filterType === "all" || filterType === "stock") && (
                  <div data-testid="section-stock-critico">
                    <StockCriticoTable
                      data={paginatedStockCritico}
                      totalCount={stockCritico.length}
                      addToCart={addToCart}
                      animatingCarts={animatingCarts}
                    />
                  </div>
                )}

                {/* Paneles de Vencimientos */}
                {(filterType === "all" || filterType === "upcoming" || filterType === "expired") && (
                  <div
                    className={cn(
                      filterType === "all" ? "grid md:grid-cols-2 gap-6" : "space-y-6"
                    )}
                  >
                    {(filterType === "all" || filterType === "upcoming") && (
                      <div data-testid="section-proximos">
                        <VencimientosCard
                          type="upcoming"
                          data={paginatedVencimientosProximos}
                          totalCount={vencimientosProximos.length}
                          onReportMerma={() => navigate("/gestion?tab=mermas")}
                        />
                      </div>
                    )}
                    {(filterType === "all" || filterType === "expired") && (
                      <div data-testid="section-vencidos">
                        <VencimientosCard
                          type="expired"
                          data={paginatedVencidos}
                          totalCount={vencidos.length}
                          onReportMerma={() => navigate("/gestion?tab=mermas")}
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              /* ===================================================================
                 MODO TARJETAS ('cards') — Grid Responsivo 1..4 Columnas
                 =================================================================== */
              <div className="space-y-8 px-2" data-testid="alerts-cards-view">
                {/* SECCIÓN 1: STOCK CRÍTICO */}
                {(filterType === "all" || filterType === "stock") && (
                  <div className="space-y-4" data-testid="section-stock-critico">
                    <div className="flex items-center gap-4 px-1">
                      <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.4em] bg-red-500/10 text-red-500 px-4 py-1.5 rounded-full border border-red-500/20">
                        <span>{t("sections.critical_stock")}</span>
                        <span className="opacity-50 font-normal tracking-normal">
                          ({stockCritico.length})
                        </span>
                      </div>
                      <div className="h-[1px] flex-1 bg-gradient-to-r from-red-500/30 via-red-500/5 to-transparent" />
                    </div>

                    {stockCritico.length === 0 ? (
                      <p
                        className="text-sm text-muted-foreground italic py-4 px-2"
                        data-testid="empty-stock-critico"
                      >
                        {t("empty.stock_critico")}
                      </p>
                    ) : paginatedStockCritico.length === 0 ? (
                      <p className="text-sm text-muted-foreground italic py-4 px-2">
                        {t("empty.page")}
                      </p>
                    ) : (
                      <div
                        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
                        data-testid="grid-stock-critico"
                      >
                        {paginatedStockCritico.map((p) => {
                          const pId = `${p.producto_id}::${p.bodega_id}`;
                          const rawId = "id" in p && p.id ? String(p.id) : undefined;
                          const isAnimating = !!(
                            animatingCarts[pId] ||
                            (rawId && animatingCarts[rawId]) ||
                            animatingCarts[String(p.producto_id)]
                          );
                          return (
                            <StockCriticoCard
                              key={pId}
                              item={p}
                              isAnimating={isAnimating}
                              onAddToCart={addToCart}
                            />
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* SECCIÓN 2: PRODUCTOS VENCIDOS */}
                {(filterType === "all" || filterType === "expired") && (
                  <div className="space-y-4" data-testid="section-vencidos">
                    <div className="flex items-center gap-4 px-1">
                      <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.4em] bg-red-600/10 text-red-600 px-4 py-1.5 rounded-full border border-red-600/20">
                        <span>{t("sections.expired_products")}</span>
                        <span className="opacity-50 font-normal tracking-normal">
                          ({vencidos.length})
                        </span>
                      </div>
                      <div className="h-[1px] flex-1 bg-gradient-to-r from-red-600/30 via-red-600/5 to-transparent" />
                    </div>

                    {vencidos.length === 0 ? (
                      <p
                        className="text-sm text-muted-foreground italic py-4 px-2"
                        data-testid="empty-vencidos"
                      >
                        {t("empty.expired")}
                      </p>
                    ) : paginatedVencidos.length === 0 ? (
                      <p className="text-sm text-muted-foreground italic py-4 px-2">
                        {t("empty.page")}
                      </p>
                    ) : (
                      <div
                        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
                        data-testid="grid-vencidos"
                      >
                        {paginatedVencidos.map((v) => (
                          <ExpiredLotCard
                            key={`expired-${v.producto_id}-${v.lote_codigo}-${v.bodega_id}`}
                            item={v}
                            onReportMerma={() => navigate("/gestion?tab=mermas")}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* SECCIÓN 3: PRÓXIMOS A VENCER */}
                {(filterType === "all" || filterType === "upcoming") && (
                  <div className="space-y-4" data-testid="section-proximos">
                    <div className="flex items-center gap-4 px-1">
                      <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.4em] bg-amber-500/10 text-amber-500 px-4 py-1.5 rounded-full border border-amber-500/20">
                        <span>{t("sections.upcoming_expiry")}</span>
                        <span className="opacity-50 font-normal tracking-normal">
                          ({vencimientosProximos.length})
                        </span>
                      </div>
                      <div className="h-[1px] flex-1 bg-gradient-to-r from-amber-500/30 via-amber-500/5 to-transparent" />
                    </div>

                    {vencimientosProximos.length === 0 ? (
                      <p
                        className="text-sm text-muted-foreground italic py-4 px-2"
                        data-testid="empty-proximos"
                      >
                        {t("empty.upcoming")}
                      </p>
                    ) : paginatedVencimientosProximos.length === 0 ? (
                      <p className="text-sm text-muted-foreground italic py-4 px-2">
                        {t("empty.page")}
                      </p>
                    ) : (
                      <div
                        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
                        data-testid="grid-proximos"
                      >
                        {paginatedVencimientosProximos.map((u) => (
                          <UpcomingExpiryCard
                            key={`upcoming-${u.producto_id}-${u.lote_codigo}-${u.bodega_id}`}
                            item={u}
                            onManage={() => navigate("/gestion?tab=mermas")}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Paginación */}
            {totalItems > 0 && (
              <div className="px-2 pt-2">
                <TablePagination
                  currentPage={currentPage}
                  totalItems={totalItems}
                  pageSize={pageSize}
                  pageSizeOptions={[10, 30, 50, 100]}
                  onPageChange={setCurrentPage}
                  onPageSizeChange={handlePageSizeChange}
                  itemLabel={t("pagination.item_label")}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default AlertasPage;
