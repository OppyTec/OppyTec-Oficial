// oppytec-frontend/src/features/consumo/components/ConsumoCatalog.tsx
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Package,
  CookingPot,
  Boxes,
  X,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { TablePagination } from "@/shared/components/ui/TablePagination";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { cn, getImageUrl } from "@/shared/lib";
import { formatCurrencyAmount, useCurrencyFormatter, type SupportedCurrency } from "@/shared/currency";
import type {
  ProductoConsumo,
  RecetaConsumo,
  ComboConsumo,
  CategoriaConsumo,
} from "../types";
import { PAGE_SIZE_OPTIONS } from "../types";

export function formatMoney(amount?: number | null, currency: SupportedCurrency = "CLP"): string {
  if (amount === undefined || amount === null || isNaN(amount)) return formatCurrencyAmount(0, currency);
  return formatCurrencyAmount(amount, currency);
}

const springTransition = {
  type: "spring" as const,
  stiffness: 350,
  damping: 25,
  mass: 1.2,
};

export interface ConsumoCatalogProps {
  readonly loading?: boolean;
  readonly busqueda: string;
  readonly onBusquedaChange: (v: string) => void;
  readonly productos: ProductoConsumo[];
  readonly recetas: RecetaConsumo[];
  readonly combos: ComboConsumo[];
  readonly categorias: CategoriaConsumo[];
  readonly onAdd: (
    item: ProductoConsumo | RecetaConsumo | ComboConsumo,
    type: "producto" | "receta" | "combo"
  ) => void;
  readonly getStock: (productoId: string) => number;
  readonly getAlertStatus: (productoId: string) => "normal" | "warning" | "critical";
  readonly getRecipeAvailability: (recetaId: string) => number;
  readonly viewMode: "productos" | "recetas" | "combos";
  readonly showCategories: boolean;
  readonly colsCount?: number;
}

export function ConsumoCatalog({
  loading = false,
  busqueda,
  onBusquedaChange,
  productos,
  recetas,
  combos,
  categorias,
  onAdd,
  getStock,
  getAlertStatus,
  getRecipeAvailability,
  viewMode,
  showCategories,
  colsCount = 8,
}: ConsumoCatalogProps) {
  const { t } = useTranslation("operations");
  const { format } = useCurrencyFormatter();
  const catalogTopRef = useRef<HTMLDivElement>(null);

  // Filtro de categorías activas (Set de IDs)
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<Set<string>>(
    () => new Set()
  );

  const toggleCategory = useCallback((catId: string) => {
    setSelectedCategoryIds((prev) => {
      const next = new Set(prev);
      if (next.has(catId)) {
        next.delete(catId);
      } else {
        next.add(catId);
      }
      return next;
    });
  }, []);

  const clearCategories = useCallback(() => {
    setSelectedCategoryIds(new Set());
  }, []);

  // ==========================================================================
  // ESTADO DE PAGINACIÓN CANÓNICO CON TablePagination
  // ==========================================================================
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(PAGE_SIZE_OPTIONS[0] ?? 24);

  // Reset a página 1 al cambiar de vista, búsqueda o categoría
  useEffect(() => {
    setCurrentPage(1);
  }, [viewMode, busqueda, selectedCategoryIds]);

  // Manejar cambio de página con scroll suave hacia el inicio del catálogo
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
    if (catalogTopRef.current) {
      catalogTopRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  const handlePageSizeChange = useCallback((newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(1);
  }, []);

  // ==========================================================================
  // FILTRADO DETERMINISTA DE ÍTEMS
  // ==========================================================================
  const filteredList = useMemo(() => {
    const searchNormalized = busqueda.trim().toLowerCase();

    if (viewMode === "productos") {
      return productos.filter((p) => {
        if (
          selectedCategoryIds.size > 0 &&
          (!p.categoria_id || !selectedCategoryIds.has(p.categoria_id))
        ) {
          return false;
        }
        if (searchNormalized) {
          const matchName = p.nombre.toLowerCase().includes(searchNormalized);
          const matchSku = p.sku ? p.sku.toLowerCase().includes(searchNormalized) : false;
          return matchName || matchSku;
        }
        return true;
      });
    }

    if (viewMode === "recetas") {
      return recetas.filter((r) => {
        if (
          selectedCategoryIds.size > 0 &&
          (!r.categoria_receta_id || !selectedCategoryIds.has(r.categoria_receta_id))
        ) {
          return false;
        }
        if (searchNormalized) {
          return r.nombre.toLowerCase().includes(searchNormalized);
        }
        return true;
      });
    }

    // viewMode === "combos"
    return combos.filter((c) => {
      if (
        selectedCategoryIds.size > 0 &&
        (!c.categoria_combo_id || !selectedCategoryIds.has(c.categoria_combo_id))
      ) {
        return false;
      }
      if (searchNormalized) {
        return c.nombre.toLowerCase().includes(searchNormalized);
      }
      return true;
    });
  }, [viewMode, productos, recetas, combos, selectedCategoryIds, busqueda]);

  // Ítems de la página actual
  const paginatedItems = useMemo(() => {
    const from = (currentPage - 1) * pageSize;
    const to = from + pageSize;
    return filteredList.slice(from, to);
  }, [filteredList, currentPage, pageSize]);

  // Mapeo dinámico de columnas de grilla según colsCount (5 a 10)
  const gridColsMap: Record<number, string> = {
    5: "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-5",
    6: "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6",
    7: "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-7",
    8: "grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-7 xl:grid-cols-8",
    9: "grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-9",
    10: "grid-cols-3 sm:grid-cols-5 md:grid-cols-7 lg:grid-cols-9 xl:grid-cols-10",
  };
  const responsiveGridClass =
    gridColsMap[colsCount] ||
    "grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-7 xl:grid-cols-8";

  return (
    <div className="flex flex-col w-full" ref={catalogTopRef} data-testid="consumo-catalog">
      {/* ─── 1. CARRUSEL HORIZONTAL DE CATEGORÍAS ─── */}
      <AnimatePresence>
        {showCategories && categorias.length > 0 && (
          <motion.div
            key="consumo-categories-container"
            initial={{ opacity: 0, height: 0, marginBottom: 0 }}
            animate={{ opacity: 1, height: "auto", marginBottom: 16 }}
            exit={{ opacity: 0, height: 0, marginBottom: 0 }}
            transition={springTransition}
            className="overflow-hidden w-full"
            data-testid="categories-container"
          >
            <div className="w-full overflow-x-auto pb-2 custom-scrollbar text-center">
              <div className="flex justify-center flex-wrap items-center gap-2 py-2 px-2 min-w-max md:min-w-0 mx-auto">
                {categorias.map((cat) => {
                  const isSelected = selectedCategoryIds.has(cat.id);
                  return (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => toggleCategory(cat.id)}
                      data-testid={`category-badge-${cat.id}`}
                      style={{
                        backgroundColor: isSelected
                          ? cat.color || "#eab308"
                          : cat.color
                          ? `${cat.color}15`
                          : undefined,
                        color: isSelected ? "#ffffff" : cat.color || undefined,
                        borderColor: cat.color ? `${cat.color}40` : undefined,
                        boxShadow:
                          isSelected && cat.color
                            ? `0 0 12px ${cat.color}40`
                            : undefined,
                      }}
                      className={cn(
                        "flex items-center justify-center gap-1.5 px-3.5 py-1.5 h-9 border cursor-pointer select-none transition-all duration-200 whitespace-nowrap rounded-xl text-xs font-bold uppercase tracking-wider",
                        isSelected
                          ? "scale-105 font-black border-transparent shadow-md"
                          : "bg-secondary/40 border-border text-foreground hover:scale-105 hover:bg-secondary/70"
                      )}
                    >
                      <CategoryIcon name={cat.icono} className="h-4 w-4 shrink-0" />
                      <span>{cat.nombre}</span>
                    </button>
                  );
                })}

                {selectedCategoryIds.size > 0 && (
                  <button
                    type="button"
                    onClick={clearCategories}
                    data-testid="clear-categories-btn"
                    className="px-3.5 py-1.5 rounded-xl text-xs font-black uppercase tracking-widest text-destructive bg-destructive/10 hover:bg-destructive/20 border border-destructive/20 transition-all cursor-pointer h-9 ml-1"
                  >
                    {t("consumption.registro.search.clear_filters", { defaultValue: "Limpiar Filtro" })}
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── 2. BUSCADOR PREDICTIVO EN TIEMPO REAL ─── */}
      <div className="relative group w-full mb-4" data-testid="catalog-search-wrapper">
        <div className="absolute left-3.5 top-1/2 -translate-y-1/2 p-1 rounded-lg bg-[#f97316]/10 transition-colors group-focus-within:bg-[#f97316]/20">
          <Search className="h-4 w-4 text-[#f97316]" />
        </div>
        <input
          type="text"
          data-testid="catalog-search-input"
          placeholder={
            viewMode === "productos"
              ? t("consumption.registro.search.placeholder_products", { defaultValue: "Buscar producto o SKU..." })
              : viewMode === "recetas"
              ? t("consumption.registro.search.placeholder_recipes", { defaultValue: "Buscar receta..." })
              : t("consumption.registro.search.placeholder_combos", { defaultValue: "Buscar combo..." })
          }
          className="pl-11 pr-10 h-11 bg-card border border-[#f97316]/30 shadow-[0_0_12px_rgba(249,115,22,0.10)] focus-within:shadow-[0_0_16px_rgba(249,115,22,0.22)] focus-within:border-[#f97316]/60 rounded-xl text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-[#f97316]/20 w-full text-foreground placeholder:text-muted-foreground"
          value={busqueda}
          onChange={(e) => onBusquedaChange(e.target.value)}
        />
        {busqueda && (
          <button
            type="button"
            data-testid="clear-search-btn"
            onClick={() => onBusquedaChange("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
            title={t("consumption.registro.search.clear", { defaultValue: "Limpiar búsqueda" })}
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* ─── 3. ESTADO DE CARGA / GRILLA CUADRADA ─── */}
      {loading ? (
        <div
          className="flex h-[35vh] items-center justify-center w-full"
          data-testid="catalog-loading"
        >
          <div className="flex flex-col items-center gap-3">
            <div className="h-9 w-9 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-[11px] font-black uppercase tracking-widest text-muted-foreground">
              {t("consumption.registro.states.loading", { defaultValue: "Cargando Catálogo de Consumo..." })}
            </p>
          </div>
        </div>
      ) : paginatedItems.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center py-16 text-center border border-dashed border-border rounded-2xl bg-card/40 my-4"
          data-testid="catalog-empty-state"
        >
          <div className="h-14 w-14 rounded-2xl bg-muted flex items-center justify-center mb-3">
            <Search className="h-7 w-7 text-muted-foreground" />
          </div>
          <p className="text-sm font-black uppercase tracking-widest text-foreground">
            {t("consumption.registro.states.empty_title", {
              mode: t(`consumption.registro.modes.${viewMode}`, { defaultValue: viewMode }),
              defaultValue: `No se encontraron ${viewMode}`,
            })}
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm">
            {busqueda || selectedCategoryIds.size > 0
              ? t("consumption.registro.states.empty_subtitle", {
                  defaultValue: "Prueba cambiando el término de búsqueda o limpiando las categorías seleccionadas.",
                })
              : t("consumption.registro.states.empty_no_items", {
                  mode: t(`consumption.registro.modes.${viewMode}`, { defaultValue: viewMode }),
                  defaultValue: `No hay ${viewMode} disponibles en las bodegas asignadas.`,
                })}
          </p>
        </div>
      ) : (
        <>
          <div
            className={cn("grid gap-3 pt-1 pb-4", responsiveGridClass)}
            data-testid="catalog-cards-grid"
          >
            {/* TARJETAS DE PRODUCTOS */}
            {viewMode === "productos" &&
              (paginatedItems as ProductoConsumo[]).map((p) => {
                const stock = getStock(p.id);
                const status = getAlertStatus(p.id);

                return (
                  <button
                    type="button"
                    key={p.id}
                    data-testid={`product-card-${p.id}`}
                    onClick={() => onAdd(p, "producto")}
                    className={cn(
                      "group relative aspect-square flex flex-col items-center justify-center p-2 rounded-2xl border bg-card transition-all cursor-pointer active:scale-95 shadow-sm hover:shadow-md select-none",
                      status === "critical" &&
                        "border-destructive bg-destructive/5 hover:border-destructive animate-pulse",
                      status === "warning" &&
                        "border-orange-500 bg-orange-500/5 hover:border-orange-600",
                      status === "normal" && "border-border hover:border-primary/50"
                    )}
                  >
                    {/* Imagen / Ícono astronómico */}
                    {p.imagen_url ? (
                      <img
                        src={getImageUrl(p.imagen_url)}
                        alt={p.nombre}
                        className="w-[45%] h-[45%] max-w-[100px] max-h-[100px] rounded-xl object-cover mb-2 group-hover:scale-105 transition-transform"
                      />
                    ) : (
                      <Package
                        className={cn(
                          "w-[42%] h-[42%] max-w-[80px] max-h-[80px] mb-2 transition-colors",
                          status === "critical"
                            ? "text-destructive/70"
                            : status === "warning"
                            ? "text-orange-500/70"
                            : "text-muted-foreground/60"
                        )}
                      />
                    )}

                    {/* Nombre a dos líneas */}
                    <p className="text-[10px] md:text-[11px] font-black uppercase text-center leading-tight line-clamp-2 px-1 text-foreground">
                      {p.nombre}
                    </p>

                    {/* Precio unitario */}
                    {p.precio_venta !== undefined && (
                      <p className="text-[9px] font-bold text-muted-foreground mt-0.5">
                        {format(p.precio_venta)}
                      </p>
                    )}

                    {/* Badge de stock con semáforo */}
                    <div
                      data-testid={`stock-badge-${p.id}`}
                      className={cn(
                        "absolute -top-1.5 -right-1.5 px-2 py-0.5 rounded-full text-[9px] font-black shadow-md border",
                        status === "critical"
                          ? "bg-destructive text-white border-destructive"
                          : status === "warning"
                          ? "bg-orange-500 text-white border-orange-600"
                          : "bg-secondary text-secondary-foreground border-border"
                      )}
                    >
                      {stock} {p.unidad || "u"}
                    </div>
                  </button>
                );
              })}

            {/* TARJETAS DE RECETAS */}
            {viewMode === "recetas" &&
              (paginatedItems as RecetaConsumo[]).map((r) => {
                const availability = getRecipeAvailability(r.id);

                return (
                  <button
                    type="button"
                    key={r.id}
                    data-testid={`recipe-card-${r.id}`}
                    onClick={() => onAdd(r, "receta")}
                    className="group relative aspect-square flex flex-col items-center justify-center p-2 rounded-2xl border border-border bg-card transition-all cursor-pointer active:scale-95 shadow-sm hover:shadow-md hover:border-purple-500/60 select-none"
                  >
                    {r.imagen_url ? (
                      <img
                        src={getImageUrl(r.imagen_url)}
                        alt={r.nombre}
                        className="w-[45%] h-[45%] max-w-[100px] max-h-[100px] rounded-xl object-cover mb-2 group-hover:scale-105 transition-transform"
                      />
                    ) : (
                      <CookingPot className="w-[42%] h-[42%] max-w-[80px] max-h-[80px] mb-2 text-purple-500/70" />
                    )}

                    <p className="text-[10px] md:text-[11px] font-black uppercase text-center leading-tight line-clamp-2 px-1 text-foreground">
                      {r.nombre}
                    </p>

                    <div className="flex items-center gap-1 mt-0.5">
                      <p className="text-[9px] font-bold text-muted-foreground">
                        {format(r.precio)}
                      </p>
                      {r.porciones && r.porciones > 1 && (
                        <span
                          className="text-[8px] bg-purple-500/10 text-purple-600 dark:text-purple-400 font-bold px-1 rounded border border-purple-500/20"
                          title={t("consumption.registro.badges.yield_tooltip", {
                            count: r.porciones,
                            defaultValue: `Rendimiento: ${r.porciones} porciones`,
                          })}
                        >
                          {r.porciones}p
                        </span>
                      )}
                    </div>

                    {/* Badge de disponibilidad */}
                    <div
                      data-testid={`recipe-badge-${r.id}`}
                      className={cn(
                        "absolute -top-1.5 -right-1.5 px-2 py-0.5 rounded-full text-[9px] font-black shadow-md border",
                        availability > 0
                          ? "bg-purple-600 text-white border-purple-700 shadow-purple-600/20"
                          : "bg-destructive text-white border-destructive"
                      )}
                    >
                      {availability}{" "}
                      {t("consumption.registro.badges.portions", {
                        count: availability,
                        defaultValue: "porc.",
                      })}
                    </div>
                  </button>
                );
              })}

            {/* TARJETAS DE COMBOS */}
            {viewMode === "combos" &&
              (paginatedItems as ComboConsumo[]).map((c) => {
                const availability = c.disponibilidad ?? 0;

                return (
                  <button
                    type="button"
                    key={c.id}
                    data-testid={`combo-card-${c.id}`}
                    onClick={() => onAdd(c, "combo")}
                    className="group relative aspect-square flex flex-col items-center justify-center p-2 rounded-2xl border border-border bg-card transition-all cursor-pointer active:scale-95 shadow-sm hover:shadow-md hover:border-[#1c4c96]/70 select-none"
                  >
                    {c.imagen_url ? (
                      <img
                        src={getImageUrl(c.imagen_url)}
                        alt={c.nombre}
                        className="w-[45%] h-[45%] max-w-[100px] max-h-[100px] rounded-xl object-cover mb-2 group-hover:scale-105 transition-transform"
                      />
                    ) : (
                      <Boxes className="w-[42%] h-[42%] max-w-[80px] max-h-[80px] mb-2 text-[#1c4c96]" />
                    )}

                    <p className="text-[10px] md:text-[11px] font-black uppercase text-center leading-tight line-clamp-2 px-1 text-foreground">
                      {c.nombre}
                    </p>

                    <p className="text-[9px] font-bold text-muted-foreground mt-0.5">
                      {format(c.precio)}
                    </p>

                    {/* Badge de disponibilidad */}
                    <div
                      data-testid={`combo-badge-${c.id}`}
                      className={cn(
                        "absolute -top-1.5 -right-1.5 px-2 py-0.5 rounded-full text-[9px] font-black shadow-md border",
                        availability > 0
                          ? "bg-[#1c4c96] text-white border-[#153b75] shadow-[#1c4c96]/30"
                          : "bg-destructive text-white border-destructive"
                      )}
                    >
                      {availability}{" "}
                      {t("consumption.registro.badges.combos_count", {
                        count: availability,
                        defaultValue: "comb.",
                      })}
                    </div>
                  </button>
                );
              })}
          </div>

          {/* ─── 4. PAGINADOR OFICIAL CON TablePagination ─── */}
          <TablePagination
            currentPage={currentPage}
            totalItems={filteredList.length}
            pageSize={pageSize}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
            itemLabel={viewMode}
          />
        </>
      )}
    </div>
  );
}

export default ConsumoCatalog;
