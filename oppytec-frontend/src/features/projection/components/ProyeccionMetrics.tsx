/**
 * oppytec-frontend/src/features/projection/components/ProyeccionMetrics.tsx
 * Panel Lateral de Métricas y Acciones Rápidas para el Detalle de Producto Proyectado.
 * Muestra valorización monetaria en inventario, fecha de quiebre, stock comparativo y botones de acción.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import type { FC } from "react";
import {
  AlertOctagon,
  AlertTriangle,
  ArrowRightLeft,
  Calendar,
  CheckCircle2,
  DollarSign,
  Flame,
  Layers,
  ShoppingCart,
  TrendingDown,
  Warehouse,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { formatCurrencyAmount } from "@/shared/currency";
import { cn, formatOperationalDate } from "@/shared/lib";
import type { ProjectionProductOverview, ProjectionUrgencyStatus } from "../types";

export interface ProyeccionMetricsProps {
  readonly product: ProjectionProductOverview;
  readonly onOpenTransfer?: (product: ProjectionProductOverview) => void;
  readonly onManagePurchase?: (product: ProjectionProductOverview) => void;
  readonly className?: string;
}

export const ProyeccionMetrics: FC<ProyeccionMetricsProps> = ({
  product,
  onOpenTransfer,
  onManagePurchase,
  className,
}) => {
  const { t } = useTranslation("projection");

  const {
    current_qty,
    projected_qty,
    stock_minimo = 0,
    costo_unitario = 0,
    depletion_date,
    worst_status,
    worst_status_label,
    worst_day,
    daily_consumption_rate = 0,
    unidad = "un",
    bodega_nombre,
  } = product;

  const currentInventoryValue = current_qty * costo_unitario;
  const formattedInventoryValue = formatCurrencyAmount(currentInventoryValue, "CLP");
  const formattedCostoUnitario = formatCurrencyAmount(costo_unitario, "CLP");

  const statusConfig: Record<
    ProjectionUrgencyStatus,
    {
      readonly border: string;
      readonly bg: string;
      readonly text: string;
      readonly icon: typeof AlertOctagon;
    }
  > = {
    critical: {
      border: "border-red-500/40",
      bg: "bg-red-500/10 text-red-700 dark:text-red-400",
      text: "text-red-600 dark:text-red-400",
      icon: AlertOctagon,
    },
    warning: {
      border: "border-amber-500/40",
      bg: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
      text: "text-amber-600 dark:text-amber-400",
      icon: AlertTriangle,
    },
    normal: {
      border: "border-emerald-500/40",
      bg: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
      text: "text-emerald-600 dark:text-emerald-400",
      icon: CheckCircle2,
    },
  };

  const currentStatus = statusConfig[worst_status] ?? statusConfig.normal;
  const StatusIcon = currentStatus.icon;

  const formattedDepletion = depletion_date
    ? formatOperationalDate(depletion_date)
    : t("metrics.no_depletion", {
        defaultValue: "Sin quiebre en horizonte",
      });

  return (
    <div
      data-testid="proyeccion-metrics-panel"
      className={cn(
        "flex flex-col gap-4 rounded-2xl border border-border bg-card p-4 sm:p-5 shadow-sm text-card-foreground",
        className
      )}
    >
      {/* Banner de Estado de Urgencia */}
      <div
        className={cn(
          "flex items-center justify-between rounded-xl border p-3",
          currentStatus.border,
          currentStatus.bg
        )}
      >
        <div className="flex items-center gap-2">
          <StatusIcon className="h-5 w-5 shrink-0" />
          <span className="text-xs sm:text-sm font-bold tracking-tight">
            {worst_status_label || worst_status.toUpperCase()}
          </span>
        </div>
        {worst_day !== undefined && worst_day !== null && worst_status !== "normal" && (
          <span className="rounded-md bg-background/60 px-2 py-0.5 text-[11px] font-extrabold backdrop-blur-sm">
            {t("metrics.day_counter", {
              defaultValue: "Día {{day}}",
              day: worst_day,
            })}
          </span>
        )}
      </div>

      {/* Grid de Indicadores Clave */}
      <div className="grid grid-cols-2 gap-3">
        {/* Valor Actual en Inventario */}
        <div className="col-span-2 rounded-xl border border-border/80 bg-muted/30 p-3">
          <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1.5">
            <DollarSign className="h-3.5 w-3.5 text-emerald-500" />
            {t("metrics.inventory_value", {
              defaultValue: "Valor Actual en Inventario",
            })}
          </span>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-lg font-black text-foreground">
              {formattedInventoryValue}
            </span>
            {costo_unitario > 0 && (
              <span className="text-[10px] text-muted-foreground font-medium">
                PPP: {formattedCostoUnitario}/{unidad}
              </span>
            )}
          </div>
        </div>

        {/* Stock Actual Físico */}
        <div className="rounded-xl border border-border/80 bg-muted/20 p-3">
          <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5 text-blue-500" />
            {t("metrics.current_stock", { defaultValue: "Stock Actual" })}
          </span>
          <div className="mt-1">
            <span className="text-base font-extrabold text-foreground">
              {current_qty} <span className="text-xs font-normal text-muted-foreground">{unidad}</span>
            </span>
          </div>
        </div>

        {/* Stock Proyectado */}
        <div className="rounded-xl border border-border/80 bg-muted/20 p-3">
          <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1.5">
            <TrendingDown className="h-3.5 w-3.5 text-indigo-500" />
            {t("metrics.projected_stock", {
              defaultValue: "Stock Proyectado",
            })}
          </span>
          <div className="mt-1">
            <span
              className={cn(
                "text-base font-extrabold",
                projected_qty <= 0
                  ? "text-red-600 dark:text-red-400"
                  : projected_qty <= stock_minimo
                    ? "text-amber-600 dark:text-amber-400"
                    : "text-foreground"
              )}
            >
              {projected_qty} <span className="text-xs font-normal text-muted-foreground">{unidad}</span>
            </span>
          </div>
        </div>

        {/* Fecha Estimada de Agotamiento */}
        <div className="col-span-2 rounded-xl border border-border/80 bg-muted/20 p-3">
          <span className="text-[11px] font-semibold text-muted-foreground flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-orange-500" />
            {t("metrics.depletion_date", {
              defaultValue: "Agotamiento Estimado",
            })}
          </span>
          <div className="mt-1 flex items-center justify-between">
            <span
              className={cn(
                "text-xs sm:text-sm font-bold",
                depletion_date ? "text-red-600 dark:text-red-400" : "text-foreground"
              )}
            >
              {formattedDepletion}
            </span>
            {bodega_nombre && (
              <span className="flex items-center gap-1 text-[10px] text-muted-foreground font-medium">
                <Warehouse className="h-3 w-3" />
                {bodega_nombre}
              </span>
            )}
          </div>
        </div>

        {/* Tasa Diaria de Consumo y Stock Mínimo */}
        <div className="rounded-xl border border-border/80 bg-muted/10 p-2.5">
          <span className="text-[10px] font-medium text-muted-foreground flex items-center gap-1">
            <Flame className="h-3 w-3 text-amber-500" />
            {t("metrics.daily_rate", { defaultValue: "Consumo diario" })}
          </span>
          <span className="mt-0.5 block text-xs font-bold text-foreground">
            {daily_consumption_rate} {unidad}/día
          </span>
        </div>

        <div className="rounded-xl border border-border/80 bg-muted/10 p-2.5">
          <span className="text-[10px] font-medium text-muted-foreground">
            {t("metrics.min_stock", { defaultValue: "Stock Mínimo" })}
          </span>
          <span className="mt-0.5 block text-xs font-bold text-foreground">
            {stock_minimo} {unidad}
          </span>
        </div>
      </div>

      {/* Acciones Rápidas Operativas */}
      <div className="mt-2 flex flex-col gap-2 pt-2 border-t border-border/60">
        <button
          type="button"
          onClick={() => onManagePurchase?.(product)}
          data-testid="btn-manage-purchase"
          className="flex items-center justify-center gap-2 w-full h-10 px-4 rounded-xl bg-primary text-primary-foreground text-xs sm:text-sm font-bold shadow-md hover:bg-primary/90 active:scale-[0.99] transition-all cursor-pointer"
        >
          <ShoppingCart className="h-4 w-4 shrink-0" />
          <span>
            {t("metrics.btn_purchase", {
              defaultValue: "Gestionar Pedido / Compra",
            })}
          </span>
        </button>

        <button
          type="button"
          onClick={() => onOpenTransfer?.(product)}
          data-testid="btn-open-transfer"
          className="flex items-center justify-center gap-2 w-full h-10 px-4 rounded-xl border border-input bg-background text-foreground text-xs sm:text-sm font-semibold shadow-sm hover:bg-accent hover:text-accent-foreground active:scale-[0.99] transition-all cursor-pointer"
        >
          <ArrowRightLeft className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
          <span>
            {t("metrics.btn_transfer", {
              defaultValue: "Trasladar desde otra Bodega",
            })}
          </span>
        </button>
      </div>
    </div>
  );
};
