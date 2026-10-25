// oppytec-frontend/src/features/inventory/stock/components/StockRow.tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeftRight,
  ShoppingCart,
  ChevronDown,
  Calendar,
  Layers,
  MapPin,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import type { StockItem } from "../../types";

export interface StockRowProps {
  readonly item: StockItem;
  readonly isExpanded?: boolean;
  readonly onToggleExpand?: () => void;
  readonly onOpenSolicitar?: (item: StockItem) => void;
  readonly onOpenTransfer?: (item: StockItem) => void;
  readonly onOpenMerma?: (item: StockItem) => void;
}

export function StockRow({
  item,
  isExpanded = false,
  onToggleExpand,
  onOpenSolicitar,
  onOpenTransfer,
  onOpenMerma,
}: StockRowProps) {
  const { t } = useTranslation("inventory");
  const { convertAndFormat } = useCurrencyFormatter();
  const [internalExpanded, setInternalExpanded] = useState(false);
  const expanded = onToggleExpand ? isExpanded : internalExpanded;
  const toggle = onToggleExpand ?? (() => setInternalExpanded((prev) => !prev));

  const isCritico = item.semaforo === "CRITICO" || item.stock_actual <= 0;
  const isMinimo = item.semaforo === "MINIMO" && item.stock_actual > 0;

  const formatCurrency = (val: number) => {
    return convertAndFormat(val, "CLP");
  };

  const formatLocation = () => {
    const loc = item.ubicacion;
    if (!loc) return t("stock.row.general_location");
    const parts: string[] = [];
    if (loc.pasillo) parts.push(`${t("stock.row.aisle_prefix")}${loc.pasillo}`);
    if (loc.estante) parts.push(`${t("stock.row.shelf_prefix")}${loc.estante}`);
    if (loc.nivel) parts.push(`${t("stock.row.level_prefix")}${loc.nivel}`);
    return parts.length > 0 ? parts.join(" ") : t("stock.row.general_location");
  };

  // Semáforo cromático
  const getSemaforoBadge = () => {
    if (isCritico) {
      return (
        <span
          data-testid="badge-semaforo-critico"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-destructive/15 text-destructive border border-destructive/30 animate-pulse"
        >
          <AlertTriangle className="h-3 w-3" />
          <span>{item.stock_actual <= 0 ? t("stock.row.badge_exhausted") : t("stock.row.badge_critical")}</span>
        </span>
      );
    }
    if (isMinimo) {
      return (
        <span
          data-testid="badge-semaforo-minimo"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
        >
          <Clock className="h-3 w-3" />
          <span>{t("stock.row.badge_minimum")}</span>
        </span>
      );
    }
    return (
      <span
        data-testid="badge-semaforo-optimo"
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
      >
        <CheckCircle2 className="h-3 w-3" />
        <span>{t("stock.row.badge_optimal")}</span>
      </span>
    );
  };

  return (
    <div
      data-testid={`stock-row-${item.id}`}
      className={cn(
        "group transition-colors border-b border-border/50 hover:bg-muted/30",
        isCritico && "bg-destructive/5",
        isMinimo && "bg-amber-500/5"
      )}
    >
      <div className="grid grid-cols-12 gap-2 items-center px-4 py-3 text-xs">
        {/* COL 1: Semáforo y Estado (col-span-2) */}
        <div className="col-span-2 flex items-center gap-2">
          {getSemaforoBadge()}
        </div>

        {/* COL 2: SKU y Producto (col-span-3) */}
        <div className="col-span-3 flex items-center gap-2.5 min-w-0">
          <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
            <CategoryIcon name={item.categoria_icono || "Package"} className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-bold text-foreground text-sm truncate" title={item.nombre}>
              {item.nombre}
            </div>
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
              <span>{t("stock.row.sku_label", { sku: item.sku })}</span>
              <span>•</span>
              <span className="truncate">{item.categoria}</span>
            </div>
          </div>
        </div>

        {/* COL 3: Bodega y Ubicación (col-span-2) */}
        <div className="col-span-2 min-w-0">
          <div className="font-semibold text-foreground truncate">{item.bodega_nombre}</div>
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <MapPin className="h-3 w-3 shrink-0 text-muted-foreground/80" />
            <span className="truncate">{formatLocation()}</span>
          </div>
        </div>

        {/* COL 4: Stock Actual y Mínimo (col-span-2) */}
        <div className="col-span-2 text-center">
          <div className="flex items-baseline justify-center gap-1 font-mono">
            <span
              className={cn(
                "text-base font-black tabular-nums",
                isCritico ? "text-destructive" : isMinimo ? "text-amber-600 dark:text-amber-400" : "text-foreground"
              )}
            >
              {item.stock_actual}
            </span>
            <span className="text-[10px] font-bold text-muted-foreground">/ {item.stock_minimo}</span>
            <span className="text-[10px] text-muted-foreground font-sans uppercase">
              {item.unidad_medida}
            </span>
          </div>
          {item.lotes && item.lotes.length > 0 && (
            <button
              type="button"
              onClick={toggle}
              className="mt-1 inline-flex items-center gap-1 text-[10px] text-primary hover:underline cursor-pointer"
            >
              <Calendar className="h-3 w-3" />
              <span>{t("stock.row.lots_count", { count: item.lotes.length })}</span>
              <ChevronDown className={cn("h-3 w-3 transition-transform", expanded && "rotate-180")} />
            </button>
          )}
        </div>

        {/* COL 5: Costos (PPP y Total) (col-span-2) */}
        <div className="col-span-2 text-right font-mono">
          <div className="font-bold text-foreground text-xs tabular-nums">
            {formatCurrency(item.costo_total_valorizado)}
          </div>
          <div className="text-[10px] text-muted-foreground tabular-nums">
            {t("stock.row.ppp_label", { value: formatCurrency(item.costo_unitario_ppp) })}
          </div>
        </div>

        {/* COL 6: Acciones de Fila (col-span-1) */}
        <div className="col-span-1 flex items-center justify-end gap-1">
          {onOpenSolicitar && (
            <button
              type="button"
              title={t("stock.row.action_request")}
              onClick={() => onOpenSolicitar(item)}
              data-testid={`btn-solicitar-${item.id}`}
              className="h-8 w-8 rounded-lg border border-border bg-background hover:bg-blue-500/10 hover:text-blue-500 text-muted-foreground flex items-center justify-center transition-colors cursor-pointer"
            >
              <ShoppingCart className="h-3.5 w-3.5" />
            </button>
          )}

          {onOpenTransfer && (
            <button
              type="button"
              title={t("stock.row.action_transfer")}
              onClick={() => onOpenTransfer(item)}
              data-testid={`btn-transferir-${item.id}`}
              className="h-8 w-8 rounded-lg border border-border bg-background hover:bg-emerald-500/10 hover:text-emerald-500 text-muted-foreground flex items-center justify-center transition-colors cursor-pointer"
            >
              <ArrowLeftRight className="h-3.5 w-3.5" />
            </button>
          )}

          {onOpenMerma && (
            <button
              type="button"
              title={t("stock.row.action_merma")}
              onClick={() => onOpenMerma(item)}
              data-testid={`btn-merma-${item.id}`}
              className="h-8 w-8 rounded-lg border border-border bg-background hover:bg-destructive/10 hover:text-destructive text-muted-foreground flex items-center justify-center transition-colors cursor-pointer"
            >
              <AlertTriangle className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Detalle Desplegable de Lotes y FEFO */}
      <AnimatePresence>
        {expanded && item.lotes && item.lotes.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden bg-muted/20 border-t border-border/40 px-6 py-2.5"
          >
            <div className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-primary" />
              <span>{t("stock.row.lots_breakdown")}</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {item.lotes.map((lote, idx) => (
                <div
                  key={`${item.id}-lote-${idx}`}
                  className="rounded-xl border border-border/60 bg-card p-2 text-xs flex items-center justify-between"
                >
                  <div>
                    <div className="font-mono font-bold text-foreground">{lote.lote_codigo}</div>
                    <div className="text-[10px] text-muted-foreground">
                      {t("stock.row.expires_label", { date: lote.fecha_vencimiento || t("stock.row.no_expiry") })}
                    </div>
                  </div>
                  <div className="text-right font-mono font-bold text-foreground">
                    {lote.cantidad} {item.unidad_medida}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default StockRow;
