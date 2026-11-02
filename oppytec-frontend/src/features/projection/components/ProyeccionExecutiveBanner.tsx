/**
 * oppytec-frontend/src/features/projection/components/ProyeccionExecutiveBanner.tsx
 * Banner Ejecutivo de KPIs y Métricas de Proyección para el horizonte seleccionado.
 * Muestra Total Monitoreados, Quiebre Crítico (#ef4444), Advertencia (#f59e0b), Cobertura Promedio y Valor en Riesgo (FX/CLP).
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import type { FC } from "react";
import {
  AlertOctagon,
  AlertTriangle,
  Boxes,
  CalendarDays,
  Coins,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { formatCurrencyAmount } from "@/shared/currency";
import { cn } from "@/shared/lib";
import type { ProjectionMetricsSummary, ProjectionUrgencyStatus } from "../types";

export interface ProyeccionExecutiveBannerProps {
  readonly metrics?: ProjectionMetricsSummary | null;
  readonly horizonDays?: number;
  readonly isLoading?: boolean;
  readonly selectedStatus?: "all" | ProjectionUrgencyStatus;
  readonly onStatusFilterClick?: (status: "all" | ProjectionUrgencyStatus) => void;
  readonly className?: string;
}

export const ProyeccionExecutiveBanner: FC<ProyeccionExecutiveBannerProps> = ({
  metrics,
  horizonDays = 30,
  isLoading = false,
  selectedStatus = "all",
  onStatusFilterClick,
  className,
}) => {
  const { t } = useTranslation("projection");

  const totalItems = metrics?.total_items ?? 0;
  const criticalCount = metrics?.in_critical_count ?? 0;
  const warningCount = metrics?.in_warning_count ?? 0;
  const avgCoverageDays = metrics?.avg_coverage_days ?? 0;
  const valueAtRisk = metrics?.total_value_at_risk ?? 0;

  const formattedRisk = formatCurrencyAmount(valueAtRisk, "CLP");

  if (isLoading) {
    return (
      <div
        data-testid="proyeccion-executive-banner-skeleton"
        className={cn(
          "grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 w-full",
          className
        )}
      >
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={`kpi-skeleton-${i}`}
            className="h-24 rounded-2xl border border-border/60 bg-card/60 p-4 animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <div
      data-testid="proyeccion-executive-banner"
      className={cn(
        "grid grid-cols-2 gap-2.5 sm:gap-3 sm:grid-cols-3 lg:grid-cols-5 w-full",
        className
      )}
    >
      {/* 1. Total Monitoreados */}
      <div
        onClick={() => onStatusFilterClick?.("all")}
        data-testid="kpi-card-total"
        className={cn(
          "group relative flex flex-col justify-between rounded-2xl border p-3.5 sm:p-4 bg-card shadow-sm transition-all duration-200 select-none",
          onStatusFilterClick && "cursor-pointer hover:border-foreground/30",
          selectedStatus === "all"
            ? "border-primary/50 ring-1 ring-primary/40 bg-primary/5"
            : "border-border/60"
        )}
      >
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-[11px] font-bold uppercase tracking-wider">
            {t("kpi.total_items", { defaultValue: "Monitoreados" })}
          </span>
          <Boxes className="h-4 w-4 text-primary" aria-hidden="true" />
        </div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-2xl sm:text-3xl font-black tracking-tight text-foreground">
            {totalItems}
          </span>
          <span className="text-[11px] font-medium text-muted-foreground">
            {t("kpi.items_unit", { defaultValue: "insumos" })}
          </span>
        </div>
        <span className="text-[10px] text-muted-foreground mt-1">
          {t("kpi.horizon_window", {
            days: horizonDays,
            defaultValue: `Ventana ${horizonDays}d`,
          })}
        </span>
      </div>

      {/* 2. Quiebre Crítico (#ef4444) */}
      <div
        onClick={() => onStatusFilterClick?.("critical")}
        data-testid="kpi-card-critical"
        className={cn(
          "group relative flex flex-col justify-between rounded-2xl border p-3.5 sm:p-4 bg-card shadow-sm transition-all duration-200 select-none",
          onStatusFilterClick && "cursor-pointer hover:border-red-500/50",
          selectedStatus === "critical"
            ? "border-red-500 ring-1 ring-red-500/40 bg-red-500/10"
            : "border-border/60"
        )}
      >
        <div className="flex items-center justify-between text-red-500">
          <span className="text-[11px] font-bold uppercase tracking-wider">
            {t("kpi.critical_shortage", { defaultValue: "Quiebre Crítico" })}
          </span>
          <AlertOctagon className="h-4 w-4 text-red-500" aria-hidden="true" />
        </div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-2xl sm:text-3xl font-black tracking-tight text-red-600 dark:text-red-400">
            {criticalCount}
          </span>
          <span className="text-[11px] font-medium text-red-600/80 dark:text-red-400/80">
            {t("kpi.critical_unit", { defaultValue: "a quiebre" })}
          </span>
        </div>
        <span className="text-[10px] text-red-600/70 dark:text-red-400/70 mt-1 font-semibold">
          {criticalCount > 0
            ? t("kpi.requires_transfer", { defaultValue: "Requiere reposición" })
            : t("kpi.no_critical", { defaultValue: "Sin quiebres previstos" })}
        </span>
      </div>

      {/* 3. En Advertencia / Stock Bajo (#f59e0b) */}
      <div
        onClick={() => onStatusFilterClick?.("warning")}
        data-testid="kpi-card-warning"
        className={cn(
          "group relative flex flex-col justify-between rounded-2xl border p-3.5 sm:p-4 bg-card shadow-sm transition-all duration-200 select-none",
          onStatusFilterClick && "cursor-pointer hover:border-amber-500/50",
          selectedStatus === "warning"
            ? "border-amber-500 ring-1 ring-amber-500/40 bg-amber-500/10"
            : "border-border/60"
        )}
      >
        <div className="flex items-center justify-between text-amber-500">
          <span className="text-[11px] font-bold uppercase tracking-wider">
            {t("kpi.warning_stock", { defaultValue: "Stock Bajo" })}
          </span>
          <AlertTriangle className="h-4 w-4 text-amber-500" aria-hidden="true" />
        </div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-2xl sm:text-3xl font-black tracking-tight text-amber-600 dark:text-amber-400">
            {warningCount}
          </span>
          <span className="text-[11px] font-medium text-amber-600/80 dark:text-amber-400/80">
            {t("kpi.warning_unit", { defaultValue: "en alerta" })}
          </span>
        </div>
        <span className="text-[10px] text-amber-600/70 dark:text-amber-400/70 mt-1 font-semibold">
          {t("kpi.under_safety", { defaultValue: "Bajo stock mínimo o caducando" })}
        </span>
      </div>

      {/* 4. Días Promedio de Cobertura */}
      <div
        data-testid="kpi-card-coverage"
        className="relative flex flex-col justify-between rounded-2xl border border-border/60 p-3.5 sm:p-4 bg-card shadow-sm transition-all duration-200 select-none"
      >
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-[11px] font-bold uppercase tracking-wider">
            {t("kpi.avg_coverage", { defaultValue: "Autonomía Prom." })}
          </span>
          <CalendarDays className="h-4 w-4 text-emerald-500" aria-hidden="true" />
        </div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-2xl sm:text-3xl font-black tracking-tight text-foreground">
            {avgCoverageDays.toFixed(1)}
          </span>
          <span className="text-[11px] font-medium text-muted-foreground">
            {t("kpi.days_unit", { defaultValue: "días" })}
          </span>
        </div>
        <span className="text-[10px] text-muted-foreground mt-1">
          {t("kpi.weighted_autonomy", { defaultValue: "Cobertura ponderada de bodega" })}
        </span>
      </div>

      {/* 5. Valor Financiero en Riesgo */}
      <div
        data-testid="kpi-card-risk-value"
        className="col-span-2 sm:col-span-1 lg:col-span-1 relative flex flex-col justify-between rounded-2xl border border-border/60 p-3.5 sm:p-4 bg-card shadow-sm transition-all duration-200 select-none"
      >
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-[11px] font-bold uppercase tracking-wider">
            {t("kpi.value_at_risk", { defaultValue: "Valor en Riesgo" })}
          </span>
          <Coins className="h-4 w-4 text-emerald-500" aria-hidden="true" />
        </div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-xl sm:text-2xl font-black tracking-tight text-foreground">
            {formattedRisk}
          </span>
        </div>
        <span className="text-[10px] text-muted-foreground mt-1">
          {t("kpi.risk_breakdown", {
            defaultValue: "Lotes en riesgo y quiebre",
          })}
        </span>
      </div>
    </div>
  );
};

export default ProyeccionExecutiveBanner;
