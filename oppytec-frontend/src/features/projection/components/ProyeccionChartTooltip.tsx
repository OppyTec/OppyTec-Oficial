/**
 * oppytec-frontend/src/features/projection/components/ProyeccionChartTooltip.tsx
 * Tooltip Enriquecido para gráficos interactivos de Recharts en el Módulo de Proyección.
 * Muestra fecha, saldo proyectado, valorización monetaria y desglose de mermas FEFO y eventos agendados.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import type { FC } from "react";
import { AlertTriangle, Calendar, DollarSign, Layers } from "lucide-react";
import { useTranslation } from "react-i18next";
import { formatCurrencyAmount } from "@/shared/currency";
import { cn } from "@/shared/lib";
import type { DayPoint } from "../types";

export interface ChartPayloadItem {
  readonly payload?: DayPoint;
  readonly value?: number;
  readonly name?: string;
  readonly color?: string;
  readonly dataKey?: string;
}

export interface ProyeccionChartTooltipProps {
  readonly active?: boolean;
  readonly payload?: readonly ChartPayloadItem[];
  readonly label?: string;
  readonly unit?: string;
  readonly costoUnitario?: number;
}

export const ProyeccionChartTooltip: FC<ProyeccionChartTooltipProps> = ({
  active,
  payload,
  label,
  unit = "un",
  costoUnitario = 0,
}) => {
  const { t } = useTranslation("projection");

  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const point = payload[0]?.payload;
  if (!point) {
    return null;
  }

  const totalValue = point.qty * costoUnitario;
  const formattedValue = formatCurrencyAmount(totalValue, "CLP");

  const statusBadgeBg =
    point.status === "critical"
      ? "bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30"
      : point.status === "warning"
        ? "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30"
        : "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30";

  return (
    <div
      data-testid="proyeccion-chart-tooltip"
      className="min-w-[220px] max-w-[320px] rounded-2xl border border-border bg-popover/95 p-3.5 shadow-2xl backdrop-blur-md text-popover-foreground transition-all duration-150 animate-in fade-in-50 zoom-in-95"
    >
      {/* Header: Fecha y Badge de Estado */}
      <div className="flex items-center justify-between gap-2 border-b border-border/60 pb-2">
        <span className="text-xs font-bold text-foreground">
          {point.label || label || point.date}
        </span>
        <span
          className={cn(
            "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase",
            statusBadgeBg
          )}
        >
          {point.statusLabel || point.status}
        </span>
      </div>

      {/* Métricas Principales del Día */}
      <div className="mt-2.5 space-y-1.5 text-xs">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-muted-foreground font-medium">
            <Layers className="h-3.5 w-3.5 text-indigo-500" />
            {t("chart.stock_projected", {
              defaultValue: "Stock proyectado:",
            })}
          </span>
          <span className="font-extrabold text-foreground">
            {point.qty} {unit}
          </span>
        </div>

        {costoUnitario > 0 && (
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-muted-foreground font-medium">
              <DollarSign className="h-3.5 w-3.5 text-emerald-500" />
              {t("chart.estimated_value", {
                defaultValue: "Valor estimado:",
              })}
            </span>
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">
              {formattedValue}
            </span>
          </div>
        )}
      </div>

      {/* Desglose de Lotes por Vencer (FEFO) */}
      {point.expiring && point.expiring.length > 0 && (
        <div
          data-testid="tooltip-expiring-section"
          className="mt-3 rounded-xl border border-red-500/20 bg-red-500/5 p-2 text-[11px]"
        >
          <div className="flex items-center gap-1.5 font-bold text-red-600 dark:text-red-400">
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>
              {t("chart.expiring_title", {
                defaultValue: "Lotes que caducan hoy:",
              })}
            </span>
          </div>
          <ul className="mt-1 space-y-0.5 divide-y divide-red-500/10">
            {point.expiring.map((lot, idx) => (
              <li
                key={lot.lote_id ?? `${lot.fecha_vencimiento}-${idx}`}
                className="flex items-center justify-between pt-0.5 text-foreground/80 font-medium"
              >
                <span>
                  {lot.numero_lote
                    ? `Lote ${lot.numero_lote}`
                    : t("chart.lot", { defaultValue: "Lote" })}
                </span>
                <span className="font-bold text-red-600 dark:text-red-400">
                  -{lot.cantidad} {unit}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Desglose de Eventos Agendados */}
      {point.events && point.events.length > 0 && (
        <div
          data-testid="tooltip-events-section"
          className="mt-2.5 rounded-xl border border-blue-500/20 bg-blue-500/5 p-2 text-[11px]"
        >
          <div className="flex items-center gap-1.5 font-bold text-blue-600 dark:text-blue-400">
            <Calendar className="h-3.5 w-3.5" />
            <span>
              {t("chart.events_title", {
                defaultValue: "Consumo de eventos agendados:",
              })}
            </span>
          </div>
          <ul className="mt-1 space-y-0.5 divide-y divide-blue-500/10">
            {point.events.map((ev, idx) => (
              <li
                key={ev.id ?? `${ev.name}-${idx}`}
                className="flex items-center justify-between pt-0.5 text-foreground/80 font-medium"
              >
                <span className="truncate max-w-[150px]" title={ev.name}>
                  {ev.name}
                </span>
                <span className="font-bold text-blue-600 dark:text-blue-400">
                  -{ev.qty} {unit}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
