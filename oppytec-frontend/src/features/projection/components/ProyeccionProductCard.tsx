/**
 * oppytec-frontend/src/features/projection/components/ProyeccionProductCard.tsx
 * Tarjeta de Producto Táctil para el Módulo de Proyección de OppyTec v2.0.
 * ADN Visual Legacy:
 *   - Bordes redondeados rounded-3xl con backdrop-blur y sombreado táctil.
 *   - Barra de estado inferior y borde coloreado según urgencia (#ef4444 critical, #f59e0b warning, #10b981 normal).
 *   - Semáforo FEFO táctil con comparativa numérica: Hoy vs Proyectado vs Agotamiento vs Tasa de consumo.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import type { FC, KeyboardEvent } from "react";
import {
  AlertOctagon,
  AlertTriangle,
  Boxes,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Flame,
  TrendingDown,
  Warehouse,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn, formatOperationalDate } from "@/shared/lib";
import type { ProjectionProductOverview, ProjectionUrgencyStatus } from "../types";

export interface ProyeccionProductCardProps {
  readonly product: ProjectionProductOverview;
  readonly onClick?: (product: ProjectionProductOverview) => void;
  readonly className?: string;
}

export const ProyeccionProductCard: FC<ProyeccionProductCardProps> = ({
  product,
  onClick,
  className,
}) => {
  const { t, i18n } = useTranslation("projection");

  const {
    producto_id,
    nombre,
    sku,
    unidad = "un",
    categoria_nombre,
    bodega_nombre,
    current_qty,
    projected_qty,
    depletion_date,
    worst_status,
    worst_status_label,
    worst_day,
    daily_consumption_rate = 0,
  } = product;

  // Status Styling Configuration
  const statusStyles: Record<
    ProjectionUrgencyStatus,
    {
      readonly border: string;
      readonly bar: string;
      readonly pill: string;
      readonly icon: FC<{ className?: string }>;
    }
  > = {
    critical: {
      border: "border-red-500/30 hover:border-red-500/60 shadow-red-500/5",
      bar: "bg-[#ef4444]",
      pill: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/25",
      icon: AlertOctagon,
    },
    warning: {
      border: "border-amber-500/30 hover:border-amber-500/60 shadow-amber-500/5",
      bar: "bg-[#f59e0b]",
      pill: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/25",
      icon: AlertTriangle,
    },
    normal: {
      border: "border-emerald-500/30 hover:border-emerald-500/60 shadow-emerald-500/5",
      bar: "bg-[#10b981]",
      pill: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/25",
      icon: CheckCircle2,
    },
  };

  const currentStatusConfig = statusStyles[worst_status] ?? statusStyles.normal;
  const StatusIcon = currentStatusConfig.icon;

  // Formatted depletion display
  const formattedDepletion = depletion_date
    ? formatOperationalDate(
        depletion_date,
        i18n.language === "en" ? "en" : "es"
      )
    : worst_day != null && worst_status !== "normal"
    ? t("card.day_prefix", {
        day: worst_day,
        defaultValue: `Día ${worst_day}`,
      })
    : t("card.no_depletion", { defaultValue: "Sin quiebre" });

  // Status badge label
  const urgencyBadgeText = (() => {
    if (worst_status === "critical") {
      if (worst_day != null) {
        return t("card.critical_day", {
          day: worst_day,
          defaultValue: `Sin stock (día ${worst_day})`,
        });
      }
      return worst_status_label || t("card.critical_label", { defaultValue: "Sin stock" });
    }
    if (worst_status === "warning") {
      if (worst_day != null) {
        return t("card.warning_day", {
          day: worst_day,
          defaultValue: `Bajo stock (día ${worst_day})`,
        });
      }
      return worst_status_label || t("card.warning_label", { defaultValue: "Bajo stock" });
    }
    return worst_status_label || t("card.normal_label", { defaultValue: "Stock óptimo" });
  })();

  const handleClick = () => {
    onClick?.(product);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick?.(product);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      data-testid={`projection-product-card-${producto_id}`}
      data-status={worst_status}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      aria-label={t("card.aria_open_detail", {
        name: nombre,
        defaultValue: `Ver proyección detallada de ${nombre}`,
      })}
      className={cn(
        "group relative flex flex-col justify-between rounded-3xl border bg-card/70 backdrop-blur-sm p-4 transition-all duration-200 select-none overflow-hidden",
        "hover:shadow-2xl hover:scale-[1.02] cursor-pointer touch-manipulation",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500",
        currentStatusConfig.border,
        className
      )}
    >
      {/* 1. Header superior con badges de Bodega, SKU y Urgencia */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 flex-wrap min-w-0">
            {bodega_nombre && (
              <span
                data-testid="card-bodega-badge"
                className="inline-flex items-center gap-1 rounded-md bg-secondary/80 px-2 py-0.5 text-[10px] font-semibold text-secondary-foreground uppercase tracking-wider"
              >
                <Warehouse className="h-2.5 w-2.5 opacity-70" aria-hidden="true" />
                <span className="truncate max-w-[110px]">{bodega_nombre}</span>
              </span>
            )}
            {sku && (
              <span
                data-testid="card-sku-badge"
                className="text-[11px] font-mono text-muted-foreground truncate max-w-[90px]"
              >
                {sku}
              </span>
            )}
          </div>

          <div
            data-testid="card-urgency-pill"
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold border shrink-0 transition-colors",
              currentStatusConfig.pill
            )}
          >
            <StatusIcon className="h-3 w-3 shrink-0" aria-hidden="true" />
            <span className="whitespace-nowrap">{urgencyBadgeText}</span>
          </div>
        </div>

        {/* 2. Título de producto y Categoría */}
        <div>
          <div className="flex items-start justify-between gap-1.5">
            <h3
              data-testid="card-product-name"
              title={nombre}
              className="font-black text-lg tracking-tight text-foreground line-clamp-2 leading-tight group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors"
            >
              {nombre}
            </h3>
            <span
              data-testid="card-unit-badge"
              className="inline-block px-1.5 py-0.5 rounded bg-muted/80 text-[10px] font-bold uppercase text-muted-foreground tracking-wider shrink-0 mt-0.5"
            >
              {unidad}
            </span>
          </div>
          {categoria_nombre && (
            <p
              data-testid="card-category-name"
              className="text-[11px] font-medium text-muted-foreground mt-0.5 truncate"
            >
              {categoria_nombre}
            </p>
          )}
        </div>
      </div>

      {/* 3. Comparativa Numérica Táctil (2x2 Metrics) */}
      <div className="mt-3.5 pt-3 border-t border-border/50">
        <div className="grid grid-cols-2 gap-2 text-xs">
          {/* Existencias Físicas Hoy */}
          <div className="rounded-xl bg-secondary/40 p-2 border border-border/30">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[10px] font-semibold uppercase tracking-wider">
                {t("card.current_stock", { defaultValue: "Hoy" })}
              </span>
              <Boxes className="h-3 w-3 opacity-60" aria-hidden="true" />
            </div>
            <p
              data-testid="card-current-qty"
              className="mt-1 text-sm sm:text-base font-black text-foreground tracking-tight"
            >
              {current_qty}{" "}
              <span className="text-[10px] font-normal text-muted-foreground">{unidad}</span>
            </p>
          </div>

          {/* Estimación Proyectada al Fin del Horizonte */}
          <div
            className={cn(
              "rounded-xl p-2 border transition-colors",
              projected_qty <= 0
                ? "bg-red-500/10 border-red-500/20 text-red-600 dark:text-red-400"
                : "bg-secondary/40 border-border/30 text-foreground"
            )}
          >
            <div className="flex items-center justify-between opacity-80">
              <span className="text-[10px] font-semibold uppercase tracking-wider">
                {t("card.projected_stock", { defaultValue: "Proyectado" })}
              </span>
              <TrendingDown className="h-3 w-3 opacity-70" aria-hidden="true" />
            </div>
            <p
              data-testid="card-projected-qty"
              className={cn(
                "mt-1 text-sm sm:text-base font-black tracking-tight",
                projected_qty <= 0 && "text-red-600 dark:text-red-400 font-extrabold"
              )}
            >
              {projected_qty}{" "}
              <span className="text-[10px] font-normal opacity-70">{unidad}</span>
            </p>
          </div>

          {/* Fecha / Días de Quiebre de Stock */}
          <div className="rounded-xl bg-secondary/20 p-2 border border-border/20">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[10px] font-semibold uppercase tracking-wider">
                {t("card.depletion", { defaultValue: "Agotamiento" })}
              </span>
              <Calendar className="h-3 w-3 opacity-60" aria-hidden="true" />
            </div>
            <p
              data-testid="card-depletion-date"
              className="mt-1 text-xs font-bold text-foreground truncate"
              title={formattedDepletion}
            >
              {formattedDepletion}
            </p>
          </div>

          {/* Tasa Promedio de Consumo Diario */}
          <div className="rounded-xl bg-secondary/20 p-2 border border-border/20">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[10px] font-semibold uppercase tracking-wider">
                {t("card.daily_rate", { defaultValue: "Consumo diario" })}
              </span>
              <Flame className="h-3 w-3 opacity-60 text-amber-500" aria-hidden="true" />
            </div>
            <p
              data-testid="card-daily-rate"
              className="mt-1 text-xs font-bold text-foreground"
            >
              {daily_consumption_rate}{" "}
              <span className="text-[10px] font-normal text-muted-foreground">
                {unidad}/{t("card.day_unit", { defaultValue: "d" })}
              </span>
            </p>
          </div>
        </div>

        {/* Micro-callout táctil inferior */}
        <div className="mt-2.5 flex items-center justify-between text-[11px] text-muted-foreground group-hover:text-foreground transition-colors px-0.5">
          <span className="text-[10px] font-medium text-muted-foreground/80">
            {t("card.touch_hint", { defaultValue: "Toca para ver curva FEFO" })}
          </span>
          <ChevronRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
        </div>
      </div>

      {/* 4. Barra de Color de Estado Inferior Inviolable (h-1) */}
      <div
        data-testid="card-urgency-bottom-bar"
        className={cn("absolute bottom-0 inset-x-0 h-1", currentStatusConfig.bar)}
        aria-hidden="true"
      />
    </div>
  );
};

export const ProyeccionProductCardSkeleton: FC<{ readonly className?: string }> = ({
  className,
}) => {
  return (
    <div
      data-testid="proyeccion-product-card-skeleton"
      className={cn(
        "relative flex flex-col justify-between rounded-3xl border border-border/50 bg-card/60 backdrop-blur-sm p-4 animate-pulse overflow-hidden h-[240px]",
        className
      )}
    >
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="h-5 w-24 rounded-md bg-muted/80" />
          <div className="h-5 w-28 rounded-full bg-muted/80" />
        </div>
        <div className="space-y-1.5">
          <div className="h-5 w-3/4 rounded bg-muted/80" />
          <div className="h-3.5 w-1/3 rounded bg-muted/60" />
        </div>
      </div>

      <div className="mt-3.5 pt-3 border-t border-border/30">
        <div className="grid grid-cols-2 gap-2">
          <div className="h-14 rounded-xl bg-muted/60" />
          <div className="h-14 rounded-xl bg-muted/60" />
          <div className="h-11 rounded-xl bg-muted/40" />
          <div className="h-11 rounded-xl bg-muted/40" />
        </div>
      </div>

      <div className="absolute bottom-0 inset-x-0 h-1 bg-muted/50" />
    </div>
  );
};
