// oppytec-frontend/src/features/inventory/stock/components/StockGroupRow.tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Warehouse, ShoppingCart } from "lucide-react";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { StockRow } from "./StockRow";
import type { StockItem } from "../../types";

export interface StockGroup {
  readonly productoId: number;
  readonly nombre: string;
  readonly sku: string;
  readonly categoria: string;
  readonly categoriaColor?: string;
  readonly categoriaIcono?: string;
  totalStock: number;
  totalMinimo: number;
  readonly unidadMedida: string;
  totalValorizado: number;
  readonly items: StockItem[];
}

export interface StockGroupRowProps {
  readonly group: StockGroup;
  readonly isExpanded?: boolean;
  readonly onToggleExpand?: () => void;
  readonly onOpenSolicitar?: (item: StockItem) => void;
  readonly onOpenTransfer?: (item: StockItem) => void;
  readonly onOpenMerma?: (item: StockItem) => void;
}

export function StockGroupRow({
  group,
  isExpanded = false,
  onToggleExpand,
  onOpenSolicitar,
  onOpenTransfer,
  onOpenMerma,
}: StockGroupRowProps) {
  const { t } = useTranslation("inventory");
  const { convertAndFormat } = useCurrencyFormatter();
  const [internalExpanded, setInternalExpanded] = useState(false);
  const expanded = onToggleExpand ? isExpanded : internalExpanded;
  const toggle = onToggleExpand ?? (() => setInternalExpanded((prev) => !prev));

  const hasCritico = group.items.some((i) => i.semaforo === "CRITICO" || i.stock_actual <= 0);
  const hasMinimo = !hasCritico && group.items.some((i) => i.semaforo === "MINIMO");

  const formatCurrency = (val: number) => {
    return convertAndFormat(val, "CLP");
  };

  const firstItem = group.items[0];

  return (
    <div
      data-testid={`stock-group-row-${group.productoId}`}
      className="border-b border-border/70 bg-card/60 transition-colors"
    >
      {/* Cabecera del Grupo Consolidado */}
      <div
        onClick={toggle}
        className={cn(
          "grid grid-cols-12 gap-2 items-center px-4 py-3.5 text-xs cursor-pointer select-none transition-colors hover:bg-muted/40",
          expanded && "bg-muted/30"
        )}
      >
        {/* COL 1: Estado Consolidado y Botón Desplegable (col-span-2) */}
        <div className="col-span-2 flex items-center gap-2">
          <button
            type="button"
            aria-label={t("stock.toolbar.view_grouped", "Cambiar a vista agrupada")}
            className="h-7 w-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 transition-transform"
          >
            <ChevronDown className={cn("h-4 w-4 transition-transform duration-200", expanded && "rotate-180")} />
          </button>
          {hasCritico ? (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-destructive/15 text-destructive border border-destructive/30">
              {t("stock.group.alert_stock", "Alerta Stock")}
            </span>
          ) : hasMinimo ? (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30">
              {t("stock.group.under_minimum", "Bajo Mínimo")}
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
              {t("stock.group.consolidated", "Consolidado")}
            </span>
          )}
        </div>

        {/* COL 2: Info de Producto (col-span-3) */}
        <div className="col-span-3 flex items-center gap-2.5 min-w-0">
          <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
            <CategoryIcon name={group.categoriaIcono || "Package"} className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-black text-foreground text-sm truncate" title={group.nombre}>
              {group.nombre}
            </div>
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
              <span>{t("stock.row.sku_label", { sku: group.sku, defaultValue: `SKU: ${group.sku}` })}</span>
              <span>•</span>
              <span className="truncate">{group.categoria}</span>
            </div>
          </div>
        </div>

        {/* COL 3: Bodegas Involucradas (col-span-2) */}
        <div className="col-span-2 flex items-center gap-1.5 text-muted-foreground font-semibold">
          <Warehouse className="h-4 w-4 text-primary shrink-0" />
          <span>
            {group.items.length === 1
              ? t("stock.group.warehouse_count_one", "1 bodega")
              : t("stock.group.warehouse_count_other", { count: group.items.length, defaultValue: `${group.items.length} bodegas` })}
          </span>
        </div>

        {/* COL 4: Stock Total Consolidado (col-span-2) */}
        <div className="col-span-2 text-center font-mono">
          <div className="flex items-baseline justify-center gap-1">
            <span
              className={cn(
                "text-base font-black tabular-nums",
                hasCritico ? "text-destructive" : hasMinimo ? "text-amber-600 dark:text-amber-400" : "text-foreground"
              )}
            >
              {group.totalStock}
            </span>
            <span className="text-[10px] font-bold text-muted-foreground">/ {group.totalMinimo}</span>
            <span className="text-[10px] text-muted-foreground font-sans uppercase">
              {group.unidadMedida}
            </span>
          </div>
        </div>

        {/* COL 5: Valor Total Consolidado (col-span-2) */}
        <div className="col-span-2 text-right font-mono">
          <div className="font-bold text-foreground text-xs tabular-nums">
            {formatCurrency(group.totalValorizado)}
          </div>
          <div className="text-[10px] text-muted-foreground">{t("stock.group.total_value", "Valor Total")}</div>
        </div>

        {/* COL 6: Acciones Rápidas (col-span-1) */}
        <div className="col-span-1 flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
          {onOpenSolicitar && firstItem && (
            <button
              type="button"
              title={t("stock.row.action_request", "Solicitar mercadería")}
              aria-label={t("stock.row.action_request", "Solicitar mercadería")}
              onClick={() => onOpenSolicitar(firstItem)}
              className="h-8 w-8 rounded-lg border border-border bg-background hover:bg-blue-500/10 hover:text-blue-500 text-muted-foreground flex items-center justify-center transition-colors cursor-pointer"
            >
              <ShoppingCart className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Sub-filas por Bodega con animación framer-motion */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            className="overflow-hidden bg-muted/15 border-t border-border/40 pl-6 divide-y divide-border/30"
          >
            {group.items.map((subItem) => (
              <StockRow
                key={subItem.id}
                item={subItem}
                onOpenSolicitar={onOpenSolicitar}
                onOpenTransfer={onOpenTransfer}
                onOpenMerma={onOpenMerma}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default StockGroupRow;
