// oppytec-frontend/src/features/inventory/stock/components/StockRowMobile.tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeftRight,
  ShoppingCart,
  Calendar,
  MapPin,
  ChevronDown,
  Warehouse,
} from "lucide-react";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import type { StockItem } from "../../types";

export interface StockRowMobileProps {
  readonly item: StockItem;
  readonly onOpenSolicitar?: (item: StockItem) => void;
  readonly onOpenTransfer?: (item: StockItem) => void;
  readonly onOpenMerma?: (item: StockItem) => void;
}

export function StockRowMobile({
  item,
  onOpenSolicitar,
  onOpenTransfer,
  onOpenMerma,
}: StockRowMobileProps) {
  const { t } = useTranslation("inventory");
  const { convertAndFormat } = useCurrencyFormatter();
  const [expanded, setExpanded] = useState(false);

  const isCritico = item.semaforo === "CRITICO" || item.stock_actual <= 0;
  const isMinimo = item.semaforo === "MINIMO" && item.stock_actual > 0;

  const formatCurrency = (val: number) => {
    return convertAndFormat(val, "CLP");
  };

  const formatLocation = () => {
    const loc = item.ubicacion;
    if (!loc) return t("stock.row.general_location", "General");
    const parts: string[] = [];
    if (loc.pasillo) parts.push(`${t("stock.row.aisle_prefix", "P:")}${loc.pasillo}`);
    if (loc.estante) parts.push(`${t("stock.row.shelf_prefix", "E:")}${loc.estante}`);
    if (loc.nivel) parts.push(`${t("stock.row.level_prefix", "N:")}${loc.nivel}`);
    return parts.length > 0 ? parts.join(" ") : t("stock.row.general_location", "General");
  };

  return (
    <div
      data-testid={`stock-row-mobile-${item.id}`}
      className={cn(
        "rounded-2xl border bg-card shadow-sm overflow-hidden transition-all relative",
        isCritico
          ? "border-destructive/40 shadow-destructive/5"
          : isMinimo
          ? "border-amber-500/40 shadow-amber-500/5"
          : "border-border"
      )}
    >
      {/* Borde Cromático Superior / Lateral */}
      <div
        className={cn(
          "h-1.5 w-full",
          isCritico ? "bg-destructive" : isMinimo ? "bg-amber-500" : "bg-emerald-500"
        )}
      />

      <div className="p-3.5 space-y-3">
        {/* Cabecera del Item Móvil */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="h-9 w-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
              <CategoryIcon name={item.categoria_icono || "Package"} className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <h4 className="font-bold text-foreground text-sm leading-tight truncate" title={item.nombre}>
                {item.nombre}
              </h4>
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono mt-0.5">
                <span>{t("stock.row.sku_label", { sku: item.sku, defaultValue: `SKU: ${item.sku}` })}</span>
                <span>•</span>
                <span className="truncate">{item.categoria}</span>
              </div>
            </div>
          </div>

          {/* Badge de Semáforo */}
          <div className="shrink-0">
            {isCritico ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-destructive/15 text-destructive border border-destructive/30">
                <AlertTriangle className="h-3 w-3" />
                <span>{item.stock_actual <= 0 ? t("stock.row.badge_exhausted", "Agotado") : t("stock.row.badge_critical", "Crítico")}</span>
              </span>
            ) : isMinimo ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30">
                <span>{t("stock.row.badge_minimum_mobile", "Bajo Mín")}</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                <span>{t("stock.row.badge_optimal", "Óptimo")}</span>
              </span>
            )}
          </div>
        </div>

        {/* Rejilla de Métricas Móviles */}
        <div className="grid grid-cols-2 gap-2 bg-muted/30 p-2.5 rounded-xl border border-border/50 text-xs">
          {/* Existencia */}
          <div>
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">
              {t("stock.row.stock_minimum_label", "Stock / Mínimo")}
            </span>
            <div className="flex items-baseline gap-1 font-mono mt-0.5">
              <span
                className={cn(
                  "text-base font-black tabular-nums",
                  isCritico ? "text-destructive" : isMinimo ? "text-amber-600 dark:text-amber-400" : "text-foreground"
                )}
              >
                {item.stock_actual}
              </span>
              <span className="text-[11px] font-bold text-muted-foreground">/ {item.stock_minimo}</span>
              <span className="text-[10px] text-muted-foreground uppercase font-sans">
                {item.unidad_medida}
              </span>
            </div>
          </div>

          {/* Valorización */}
          <div className="text-right">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">
              {t("stock.row.value_ppp_label", "Valorizado (PPP)")}
            </span>
            <div className="font-mono font-bold text-foreground text-sm mt-0.5 tabular-nums">
              {formatCurrency(item.costo_total_valorizado)}
            </div>
            <div className="text-[10px] text-muted-foreground font-mono tabular-nums">
              {formatCurrency(item.costo_unitario_ppp)}
            </div>
          </div>
        </div>

        {/* Bodega y Ubicación */}
        <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
          <div className="flex items-center gap-1.5 truncate">
            <Warehouse className="h-3.5 w-3.5 text-primary shrink-0" />
            <span className="font-semibold text-foreground truncate">{item.bodega_nombre}</span>
          </div>
          <div className="flex items-center gap-1 shrink-0 font-mono text-[11px]">
            <MapPin className="h-3 w-3 text-muted-foreground/70" />
            <span>{formatLocation()}</span>
          </div>
        </div>

        {/* Lotes y Acordeón Táctil */}
        {item.lotes && item.lotes.length > 0 && (
          <div>
            <button
              type="button"
              aria-label={t("stock.row.lots_breakdown", "Desglose de Lotes y FEFO")}
              onClick={() => setExpanded((prev) => !prev)}
              className="w-full flex items-center justify-between py-1.5 px-2 text-[11px] font-semibold text-primary hover:bg-primary/5 rounded-lg transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" />
                <span>{t("stock.row.lots_registered", { count: item.lotes.length, defaultValue: `${item.lotes.length} lote(s) registrados` })}</span>
              </div>
              <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")} />
            </button>

            <AnimatePresence>
              {expanded && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-1.5 pt-2"
                >
                  {item.lotes.map((lote, idx) => (
                    <div
                      key={`${item.id}-lote-mobile-${idx}`}
                      className="p-2 rounded-lg bg-background border border-border text-[11px] flex items-center justify-between font-mono"
                    >
                      <div>
                        <span className="font-bold text-foreground">{lote.lote_codigo}</span>
                        <div className="text-[10px] text-muted-foreground font-sans">
                          {t("stock.row.expires_label", { date: lote.fecha_vencimiento || t("stock.row.no_expiry", "Sin fecha"), defaultValue: `Vence: ${lote.fecha_vencimiento || "Sin fecha"}` })}
                        </div>
                      </div>
                      <span className="font-bold text-foreground">
                        {lote.cantidad} {item.unidad_medida}
                      </span>
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Barra de Acciones Móviles con Touch Targets >= 44px */}
        <div className="grid grid-cols-3 gap-2 pt-1 border-t border-border/50">
          <button
            type="button"
            data-testid={`btn-mobile-solicitar-${item.id}`}
            aria-label={t("stock.row.mobile_ask", "Pedir")}
            onClick={() => onOpenSolicitar?.(item)}
            className="min-h-[44px] px-2 gap-1 rounded-xl border border-border bg-background hover:bg-blue-500/10 hover:text-blue-500 text-foreground text-xs font-bold inline-flex items-center justify-center transition-colors cursor-pointer select-none active:scale-95"
          >
            <ShoppingCart className="h-4 w-4 text-blue-500 shrink-0" />
            <span>{t("stock.row.mobile_ask", "Pedir")}</span>
          </button>

          <button
            type="button"
            data-testid={`btn-mobile-transferir-${item.id}`}
            aria-label={t("stock.row.mobile_move", "Mover")}
            onClick={() => onOpenTransfer?.(item)}
            className="min-h-[44px] px-2 gap-1 rounded-xl border border-border bg-background hover:bg-emerald-500/10 hover:text-emerald-500 text-foreground text-xs font-bold inline-flex items-center justify-center transition-colors cursor-pointer select-none active:scale-95"
          >
            <ArrowLeftRight className="h-4 w-4 text-emerald-500 shrink-0" />
            <span>{t("stock.row.mobile_move", "Mover")}</span>
          </button>

          <button
            type="button"
            data-testid={`btn-mobile-merma-${item.id}`}
            aria-label={t("stock.row.mobile_merma", "Merma")}
            onClick={() => onOpenMerma?.(item)}
            className="min-h-[44px] px-2 gap-1 rounded-xl bg-destructive/15 hover:bg-destructive/25 text-destructive border border-destructive/30 text-xs font-bold inline-flex items-center justify-center transition-colors cursor-pointer select-none active:scale-95"
          >
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{t("stock.row.mobile_merma", "Merma")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default StockRowMobile;

