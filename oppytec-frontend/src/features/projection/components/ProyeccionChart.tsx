/**
 * oppytec-frontend/src/features/projection/components/ProyeccionChart.tsx
 * Gráfico Interactivo de Proyección de Demanda y Curvas FEFO utilizando Recharts.
 * Curva principal en índigo (#6366f1), línea de referencia para Stock Mínimo y Tooltip Enriquecido.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import type { FC } from "react";
import { useId } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { LineChart as ChartIcon, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import type { DayPoint } from "../types";
import { ProyeccionChartTooltip } from "./ProyeccionChartTooltip";

export interface ProyeccionChartProps {
  readonly data: readonly DayPoint[];
  readonly stockMinimo?: number;
  readonly unit?: string;
  readonly costoUnitario?: number;
  readonly height?: number | string;
  readonly className?: string;
  readonly isLoading?: boolean;
}

export const ProyeccionChart: FC<ProyeccionChartProps> = ({
  data,
  stockMinimo,
  unit = "un",
  costoUnitario = 0,
  height = 320,
  className,
  isLoading = false,
}) => {
  const { t } = useTranslation("projection");
  const gradientId = useId();

  if (isLoading) {
    return (
      <div
        data-testid="proyeccion-chart-loading"
        className={cn(
          "flex flex-col items-center justify-center rounded-2xl border border-border/60 bg-card/60 p-6 backdrop-blur-sm",
          className
        )}
        style={{ height }}
      >
        <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
        <p className="mt-3 text-xs font-semibold text-muted-foreground animate-pulse">
          {t("chart.loading", {
            defaultValue: "Cargando simulación de curva...",
          })}
        </p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div
        data-testid="proyeccion-chart-empty"
        className={cn(
          "flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/40 p-6 text-center",
          className
        )}
        style={{ height }}
      >
        <ChartIcon className="h-10 w-10 text-muted-foreground/40 mb-2" />
        <h4 className="text-sm font-bold text-foreground">
          {t("chart.empty_title", {
            defaultValue: "Sin datos de proyección",
          })}
        </h4>
        <p className="mt-1 text-xs text-muted-foreground max-w-sm">
          {t("chart.empty_description", {
            defaultValue:
              "No se encontraron registros de demanda o stock para generar la serie temporal.",
          })}
        </p>
      </div>
    );
  }

  // Calcular límites de eje Y para que la curva y la línea de stock mínimo no queden apretadas
  const maxQty = Math.max(...data.map((d) => d.qty), stockMinimo ?? 0);
  const yDomainMax = Math.max(10, Math.ceil(maxQty * 1.15));

  return (
    <div
      data-testid="proyeccion-chart-container"
      className={cn(
        "relative w-full rounded-2xl border border-border bg-card p-3 sm:p-4 shadow-sm",
        className
      )}
    >
      <div className="flex items-center justify-between pb-3 px-1 text-xs text-muted-foreground">
        <span className="font-semibold text-foreground flex items-center gap-1.5">
          <ChartIcon className="h-4 w-4 text-emerald-500" />
          {t("chart.title", {
            defaultValue: "Evolución Estimada de Stock",
          })}
        </span>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-4 rounded bg-[#6366f1]" />
            <span>{t("chart.legend_stock", { defaultValue: "Stock Proyectado" })}</span>
          </div>
          {stockMinimo !== undefined && stockMinimo > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="h-0.5 w-4 border-b border-dashed border-red-500" />
              <span className="text-red-500 font-medium">
                {t("chart.legend_min", { defaultValue: "Mínimo" })} ({stockMinimo} {unit})
              </span>
            </div>
          )}
        </div>
      </div>

      <div style={{ width: "100%", height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data as unknown as Record<string, unknown>[]}
            margin={{ top: 10, right: 15, left: -10, bottom: 0 }}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="currentColor"
              className="text-border/40"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              stroke="currentColor"
              className="text-[11px] text-muted-foreground"
              tickLine={false}
              axisLine={false}
              dy={6}
            />
            <YAxis
              domain={[0, yDomainMax]}
              stroke="currentColor"
              className="text-[11px] text-muted-foreground"
              tickLine={false}
              axisLine={false}
              dx={-4}
            />
            <Tooltip
              content={
                <ProyeccionChartTooltip unit={unit} costoUnitario={costoUnitario} />
              }
            />
            {stockMinimo !== undefined && stockMinimo > 0 && (
              <ReferenceLine
                y={stockMinimo}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{
                  value: `${t("chart.min_stock_label", {
                    defaultValue: "Mínimo",
                  })}: ${stockMinimo} ${unit}`,
                  fill: "#ef4444",
                  position: "insideTopRight",
                  fontSize: 10,
                  fontWeight: 600,
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey="qty"
              name={t("chart.stock_label", { defaultValue: "Stock" })}
              stroke="#6366f1"
              strokeWidth={3}
              dot={(dotProps) => {
                const pt = dotProps.payload as DayPoint;
                const hasExpiring = pt?.expiring && pt.expiring.length > 0;
                const hasEvents = pt?.events && pt.events.length > 0;

                if (hasExpiring) {
                  return (
                    <circle
                      key={`dot-exp-${dotProps.index}`}
                      cx={dotProps.cx}
                      cy={dotProps.cy}
                      r={5}
                      fill="#ef4444"
                      stroke="#ffffff"
                      strokeWidth={2}
                    />
                  );
                }

                if (hasEvents) {
                  return (
                    <circle
                      key={`dot-ev-${dotProps.index}`}
                      cx={dotProps.cx}
                      cy={dotProps.cy}
                      r={4.5}
                      fill="#3b82f6"
                      stroke="#ffffff"
                      strokeWidth={2}
                    />
                  );
                }

                return (
                  <circle
                    key={`dot-reg-${dotProps.index}`}
                    cx={dotProps.cx}
                    cy={dotProps.cy}
                    r={2.5}
                    fill="#6366f1"
                  />
                );
              }}
              activeDot={{
                r: 6,
                fill: "#6366f1",
                stroke: "#ffffff",
                strokeWidth: 2,
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
