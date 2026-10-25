// oppytec-frontend/src/features/inventory/stock/components/StockGroupRowMobile.tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Warehouse } from "lucide-react";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { StockRowMobile } from "./StockRowMobile";
import type { StockGroup } from "./StockGroupRow";
import type { StockItem } from "../../types";

export interface StockGroupRowMobileProps {
  readonly group: StockGroup;
  readonly onOpenSolicitar?: (item: StockItem) => void;
  readonly onOpenTransfer?: (item: StockItem) => void;
  readonly onOpenMerma?: (item: StockItem) => void;
}

export function StockGroupRowMobile({
  group,
  onOpenSolicitar,
  onOpenTransfer,
  onOpenMerma,
}: StockGroupRowMobileProps) {
  const { t } = useTranslation("inventory");
  const { convertAndFormat } = useCurrencyFormatter();
  const [expanded, setExpanded] = useState(false);

  const hasCritico = group.items.some((i) => i.semaforo === "CRITICO" || i.stock_actual <= 0);
  const hasMinimo = !hasCritico && group.items.some((i) => i.semaforo === "MINIMO");

  const formatCurrency = (val: number) => {
    return convertAndFormat(val, "CLP");
  };

  return (
    <div
      data-testid={`stock-group-mobile-${group.productoId}`}
      className={cn(
        "rounded-2xl border bg-card shadow-sm overflow-hidden transition-all",
        hasCritico
          ? "border-destructive/30"
          : hasMinimo
          ? "border-amber-500/30"
          : "border-border"
      )}
    >
      {/* Botón Cabecera Táctil del Grupo con Altura >= 44px */}
      <button
        type="button"
        aria-label={t("stock.toolbar.view_grouped", "Cambiar a vista agrupada")}
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full text-left p-3.5 flex items-center justify-between gap-3 hover:bg-muted/30 transition-colors cursor-pointer select-none"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="h-9 w-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
            <CategoryIcon name={group.categoriaIcono || "Package"} className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h4 className="font-bold text-foreground text-sm truncate" title={group.nombre}>
              {group.nombre}
            </h4>
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
              <span>{t("stock.row.sku_label", { sku: group.sku, defaultValue: `SKU: ${group.sku}` })}</span>
              <span>•</span>
              <span className="truncate">{group.categoria}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="text-right">
            <div className="font-mono font-bold text-xs text-foreground">
              {group.totalStock} {group.unidadMedida}
            </div>
            <div className="text-[10px] text-muted-foreground font-mono">
              {formatCurrency(group.totalValorizado)}
            </div>
          </div>
          <div className="h-7 w-7 rounded-lg bg-muted flex items-center justify-center text-muted-foreground">
            <ChevronDown className={cn("h-4 w-4 transition-transform duration-200", expanded && "rotate-180")} />
          </div>
        </div>
      </button>

      {/* Sub-tarjetas Desplegables de cada Bodega */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="p-3 bg-muted/20 border-t border-border/50 space-y-2.5"
          >
            <div className="flex items-center gap-1.5 text-xs font-bold text-muted-foreground uppercase tracking-wider px-1">
              <Warehouse className="h-3.5 w-3.5 text-primary" />
              <span>{t("stock.row.warehouse_breakdown", { count: group.items.length, defaultValue: `Desglose por Bodega (${group.items.length})` })}</span>
            </div>
            {group.items.map((subItem) => (
              <StockRowMobile
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

export default StockGroupRowMobile;
