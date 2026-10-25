// oppytec-frontend/src/features/inventory/stock/components/StockTable.tsx
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Package2, ArrowDown, ArrowUp } from "lucide-react";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { StockRow } from "./StockRow";
import { StockGroupRow, type StockGroup } from "./StockGroupRow";
import { StockRowMobile } from "./StockRowMobile";
import { StockGroupRowMobile } from "./StockGroupRowMobile";
import type { StockItem, StockSortOption, StockViewMode } from "../../types";

export interface StockTableProps {
  readonly items: readonly StockItem[];
  readonly showCategories?: boolean;
  readonly viewMode?: StockViewMode;
  readonly sortOption?: StockSortOption;
  readonly onSortChange?: (option: StockSortOption) => void;
  readonly onOpenSolicitar?: (item: StockItem) => void;
  readonly onOpenTransfer?: (item: StockItem) => void;
  readonly onOpenMerma?: (item: StockItem) => void;
}

export function StockTable({
  items,
  showCategories = true,
  viewMode = "agrupado",
  sortOption = "urgency",
  onSortChange,
  onOpenSolicitar,
  onOpenTransfer,
  onOpenMerma,
}: StockTableProps) {
  const { t } = useTranslation("inventory");
  // Agrupación por categoría
  const categoryGroups = useMemo(() => {
    const map = new Map<
      string,
      {
        nombre: string;
        color?: string;
        icono?: string;
        items: StockItem[];
      }
    >();

    for (const item of items) {
      const catKey = item.categoria || t("stock.table.uncategorized");
      if (!map.has(catKey)) {
        map.set(catKey, {
          nombre: catKey,
          color: item.categoria_color,
          icono: item.categoria_icono,
          items: [],
        });
      }
      map.get(catKey)!.items.push(item);
    }

    return Array.from(map.values());
  }, [items]);

  // Agrupación por Producto (multi-bodega)
  const productGroups = useMemo((): StockGroup[] => {
    const map = new Map<number, StockGroup>();

    for (const item of items) {
      const existing = map.get(item.producto_id);
      if (!existing) {
        map.set(item.producto_id, {
          productoId: item.producto_id,
          nombre: item.nombre,
          sku: item.sku,
          categoria: item.categoria,
          categoriaColor: item.categoria_color,
          categoriaIcono: item.categoria_icono,
          totalStock: item.stock_actual,
          totalMinimo: item.stock_minimo,
          unidadMedida: item.unidad_medida,
          totalValorizado: item.costo_total_valorizado,
          items: [item],
        });
      } else {
        existing.totalStock += item.stock_actual;
        existing.totalMinimo += item.stock_minimo;
        existing.totalValorizado += item.costo_total_valorizado;
        existing.items.push(item);
      }
    }

    return Array.from(map.values());
  }, [items]);

  const renderEmpty = () => (
    <div
      data-testid="stock-table-empty"
      className="flex flex-col items-center justify-center py-20 bg-muted/10 rounded-2xl border-2 border-dashed border-border"
    >
      <Package2 className="h-12 w-12 text-muted-foreground/30 mb-3" />
      <p className="text-muted-foreground font-black uppercase tracking-widest text-xs">
        {t("stock.table.empty_title")}
      </p>
      <span className="text-muted-foreground/60 text-xs mt-1">
        {t("stock.table.empty_description")}
      </span>
    </div>
  );

  const renderTableHeader = () => (
    <div className="sticky top-0 z-20 bg-card rounded-t-2xl border-b border-border shadow-xs select-none backdrop-blur-md">
      <div className="grid grid-cols-12 gap-2 items-center px-4 py-3 bg-muted/40 text-[10px] font-black uppercase tracking-wider text-muted-foreground">
        <div
          className="col-span-2 cursor-pointer hover:text-foreground flex items-center gap-1"
          onClick={() => onSortChange?.(sortOption === "urgency" ? "stock_asc" : "urgency")}
        >
          <span>{t("stock.table.col_status")}</span>
          {sortOption === "urgency" && <ArrowDown className="h-3 w-3 text-primary inline" />}
        </div>

        <div
          className="col-span-3 cursor-pointer hover:text-foreground flex items-center gap-1"
          onClick={() => onSortChange?.(sortOption === "az" ? "za" : "az")}
        >
          <span>{t("stock.table.col_product")}</span>
          {sortOption === "az" && <ArrowUp className="h-3 w-3 text-primary inline" />}
          {sortOption === "za" && <ArrowDown className="h-3 w-3 text-primary inline" />}
        </div>

        <div className="col-span-2">{t("stock.table.col_warehouse")}</div>

        <div
          className="col-span-2 text-center cursor-pointer hover:text-foreground flex items-center justify-center gap-1"
          onClick={() => onSortChange?.(sortOption === "stock_desc" ? "stock_asc" : "stock_desc")}
        >
          <span>{t("stock.table.col_stock")}</span>
          {sortOption === "stock_desc" && <ArrowDown className="h-3 w-3 text-primary inline" />}
          {sortOption === "stock_asc" && <ArrowUp className="h-3 w-3 text-primary inline" />}
        </div>

        <div className="col-span-2 text-right">{t("stock.table.col_value")}</div>

        <div className="col-span-1 text-right">{t("stock.table.col_actions")}</div>
      </div>
    </div>
  );

  if (items.length === 0) {
    return renderEmpty();
  }

  // Renderizado de lista de items (escritorio y móvil)
  const renderItemList = (itemList: readonly StockItem[]) => {
    return (
      <>
        {/* Vista Escritorio */}
        <div className="hidden md:block rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
          {renderTableHeader()}
          <div className="divide-y divide-border/50">
            {itemList.map((item) => (
              <StockRow
                key={item.id}
                item={item}
                onOpenSolicitar={onOpenSolicitar}
                onOpenTransfer={onOpenTransfer}
                onOpenMerma={onOpenMerma}
              />
            ))}
          </div>
        </div>

        {/* Vista Móvil (< 768px) */}
        <div className="md:hidden grid grid-cols-1 sm:grid-cols-2 gap-3">
          {itemList.map((item) => (
            <StockRowMobile
              key={item.id}
              item={item}
              onOpenSolicitar={onOpenSolicitar}
              onOpenTransfer={onOpenTransfer}
              onOpenMerma={onOpenMerma}
            />
          ))}
        </div>
      </>
    );
  };

  // Renderizado por Grupos de Producto (cuando viewMode === 'agrupado' y no agrupamos por categoría)
  const renderProductGroups = () => {
    return (
      <>
        {/* Vista Escritorio */}
        <div className="hidden md:block rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
          {renderTableHeader()}
          <div className="divide-y divide-border/50">
            {productGroups.map((g) => {
              const first = g.items[0];
              if (!first) return null;

              if (g.items.length === 1) {
                return (
                  <StockRow
                    key={first.id}
                    item={first}
                    onOpenSolicitar={onOpenSolicitar}
                    onOpenTransfer={onOpenTransfer}
                    onOpenMerma={onOpenMerma}
                  />
                );
              }
              return (
                <StockGroupRow
                  key={g.productoId}
                  group={g}
                  onOpenSolicitar={onOpenSolicitar}
                  onOpenTransfer={onOpenTransfer}
                  onOpenMerma={onOpenMerma}
                />
              );
            })}
          </div>
        </div>

        {/* Vista Móvil */}
        <div className="md:hidden grid grid-cols-1 sm:grid-cols-2 gap-3">
          {productGroups.map((g) => {
            const first = g.items[0];
            if (!first) return null;

            if (g.items.length === 1) {
              return (
                <StockRowMobile
                  key={first.id}
                  item={first}
                  onOpenSolicitar={onOpenSolicitar}
                  onOpenTransfer={onOpenTransfer}
                  onOpenMerma={onOpenMerma}
                />
              );
            }
            return (
              <StockGroupRowMobile
                key={g.productoId}
                group={g}
                onOpenSolicitar={onOpenSolicitar}
                onOpenTransfer={onOpenTransfer}
                onOpenMerma={onOpenMerma}
              />
            );
          })}
        </div>
      </>
    );
  };

  // Si showCategories es true, mostramos dividido por categorías
  if (showCategories) {
    return (
      <div className="space-y-8" data-testid="stock-table-categorized">
        {categoryGroups.map((catGroup) => (
          <div key={catGroup.nombre} className="space-y-3">
            {/* Encabezado de Categoría */}
            <div className="flex items-center gap-3 px-1">
              <div
                className="inline-flex items-center gap-2 text-[11px] font-black uppercase tracking-wider bg-primary/10 px-3.5 py-1.5 rounded-full border border-primary/20"
                style={{
                  color: catGroup.color || "var(--primary)",
                  borderColor: catGroup.color ? `${catGroup.color}40` : undefined,
                }}
              >
                <CategoryIcon name={catGroup.icono || "Package"} className="h-3.5 w-3.5" />
                <span>{catGroup.nombre}</span>
                <span className="opacity-60 font-mono text-[10px]">
                  ({catGroup.items.length})
                </span>
              </div>
              <div className="h-px flex-1 bg-gradient-to-r from-primary/30 via-primary/10 to-transparent" />
            </div>

            {/* Listado de items de esta categoría */}
            {renderItemList(catGroup.items)}
          </div>
        ))}
      </div>
    );
  }

  // Vista plana o agrupada por producto
  return (
    <div className="space-y-4" data-testid="stock-table-flat">
      {viewMode === "agrupado" ? renderProductGroups() : renderItemList(items)}
    </div>
  );
}

export default StockTable;
