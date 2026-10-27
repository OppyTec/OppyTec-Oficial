/**
 * oppytec-frontend/src/features/procurement/mermas/MermaStats.tsx
 * Gráficos y Distribución Analítica de Mermas (Fase 6.4).
 * - Evolución temporal diaria/semanal con barras/SVG determinista (cero ResizeObserver).
 * - Distribución porcentual por tipología/motivo y por categoría con barras de progreso y badges cromáticos.
 */

import { useState, useMemo } from "react";
import { BarChart3, PieChart, Layers, Flame } from "lucide-react";
import { useCurrencyFormatter } from "@/shared/currency";
import type { MermaAnalyticsData } from "../types";

export interface MermaStatsProps {
  readonly analytics: MermaAnalyticsData;
  readonly onFilterByMotivo?: (motivo: string) => void;
}

const MOTIVO_COLOR_PALETTE: ReadonlyArray<{
  readonly bar: string;
  readonly badge: string;
  readonly hex: string;
}> = [
  {
    bar: "bg-rose-500",
    badge: "border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400",
    hex: "#ef4444",
  },
  {
    bar: "bg-amber-500",
    badge: "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
    hex: "#f59e0b",
  },
  {
    bar: "bg-blue-500",
    badge: "border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400",
    hex: "#3b82f6",
  },
  {
    bar: "bg-purple-500",
    badge: "border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400",
    hex: "#a855f7",
  },
  {
    bar: "bg-emerald-500",
    badge: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    hex: "#10b981",
  },
];

export function MermaStats({ analytics, onFilterByMotivo }: MermaStatsProps) {
  const { format } = useCurrencyFormatter();
  const [breakdownMode, setBreakdownMode] = useState<"motivo" | "categoria">("motivo");

  const timeline = useMemo(() => analytics.timeline ?? [], [analytics.timeline]);

  const maxTimelineCost = useMemo(() => {
    if (timeline.length === 0) return 1;
    const costs = timeline.map((p) => Number(p.costo || 0));
    return Math.max(...costs, 1);
  }, [timeline]);

  const motivosList = useMemo(() => {
    const raw = analytics.motivos_breakdown ?? analytics.por_motivo ?? [];
    return raw.map((item, idx) => ({
      id: item.motivo,
      label: item.motivo,
      costo: Number(item.total_costo || 0),
      cantidad: Number(item.cantidad || 0),
      porcentaje: Number(item.porcentaje || 0),
      palette: MOTIVO_COLOR_PALETTE[idx % MOTIVO_COLOR_PALETTE.length]!,
    }));
  }, [analytics.motivos_breakdown, analytics.por_motivo]);

  const categoriasList = useMemo(() => {
    const raw = analytics.por_categoria ?? [];
    const totalCost = raw.reduce((acc, c) => acc + Number(c.total_costo || 0), 0) || 1;
    return raw.map((cat, idx) => {
      const costo = Number(cat.total_costo || 0);
      const pct = (costo / totalCost) * 100;
      return {
        id: String(cat.categoria_id),
        label: cat.categoria_nombre,
        costo,
        cantidad: Number(cat.cantidad || 0),
        porcentaje: pct,
        palette: MOTIVO_COLOR_PALETTE[idx % MOTIVO_COLOR_PALETTE.length]!,
      };
    });
  }, [analytics.por_categoria]);

  const activeBreakdown = breakdownMode === "motivo" ? motivosList : categoriasList;

  return (
    <div
      data-testid="merma-stats-root"
      className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-stretch"
    >
      {/* COLUMNA 1: EVOLUCIÓN TEMPORAL DE DESPERDICIO (7 cols) */}
      <div
        data-testid="merma-stats-timeline"
        className="glass-card rounded-2xl border border-border bg-card p-5 shadow-sm flex flex-col justify-between lg:col-span-7"
      >
        <div>
          <div className="flex items-center justify-between gap-2 pb-4 border-b border-border/60">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-rose-500/10 text-rose-500">
                <BarChart3 className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-xs font-black uppercase tracking-wider text-foreground">
                  Evolución Temporal de Mermas
                </h3>
                <p className="text-[11px] text-muted-foreground">
                  Curva diaria de pérdidas valorizadas a Costo Promedio Ponderado (PPP)
                </p>
              </div>
            </div>
            <span className="rounded-full bg-muted px-2.5 py-1 text-[10px] font-bold text-muted-foreground">
              {timeline.length} días con registros
            </span>
          </div>

          {timeline.length === 0 ? (
            <div
              data-testid="merma-timeline-empty"
              className="flex min-h-[220px] flex-col items-center justify-center text-center text-xs text-muted-foreground"
            >
              No se registran eventos de merma en la serie temporal seleccionada.
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              {/* Gráfico de Barras Verticales Deterministas */}
              <div
                data-testid="merma-timeline-bars"
                className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5 pt-2 items-end min-h-[160px]"
              >
                {timeline.map((point) => {
                  const costVal = Number(point.costo || 0);
                  const heightPct = Math.max(12, Math.round((costVal / maxTimelineCost) * 100));
                  const isPeak = costVal === maxTimelineCost && costVal > 0;
                  const shortDate = point.fecha.length >= 10 ? point.fecha.slice(5) : point.fecha;

                  return (
                    <div
                      key={point.fecha}
                      data-testid={`timeline-point-${point.fecha}`}
                      className="flex flex-col items-center justify-end h-full gap-1.5 rounded-xl border border-border/50 bg-muted/20 p-2.5 transition-all hover:border-rose-500/40 hover:bg-muted/40"
                    >
                      <span className="text-[10px] font-mono font-bold text-foreground truncate max-w-full">
                        {format(costVal)}
                      </span>
                      <div className="w-full h-24 flex items-end justify-center bg-muted/50 rounded-lg p-1 overflow-hidden">
                        <div
                          className={`w-full rounded-md transition-all duration-300 ${
                            isPeak ? "bg-rose-600 shadow-sm shadow-rose-500/40" : "bg-rose-500/75"
                          }`}
                          style={{ height: `${heightPct}%` }}
                        />
                      </div>
                      <div className="text-center">
                        <div className="text-[11px] font-mono font-bold text-foreground">
                          {shortDate}
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                          {Number(point.cantidad || 0).toFixed(1)} u.
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="mt-4 pt-3 border-t border-border/50 flex items-center justify-between text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <Flame className="h-3.5 w-3.5 text-rose-500" />
            Pico máximo diario:{" "}
            <strong className="font-mono text-foreground">{format(maxTimelineCost)}</strong>
          </span>
          <span>Cero Polling · Sincronización en tiempo real</span>
        </div>
      </div>

      {/* COLUMNA 2: DISTRIBUCIÓN POR MOTIVO / CATEGORÍA (5 cols) */}
      <div
        data-testid="merma-stats-motivos"
        className="glass-card rounded-2xl border border-border bg-card p-5 shadow-sm flex flex-col justify-between lg:col-span-5"
      >
        <div>
          <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-border/60">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 text-amber-500">
                <PieChart className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-xs font-black uppercase tracking-wider text-foreground">
                  Distribución por Tipología
                </h3>
                <p className="text-[11px] text-muted-foreground">
                  Desglose porcentual por causa operativa o familia
                </p>
              </div>
            </div>

            {/* Conmutador Por Motivo / Por Categoría */}
            <div className="inline-flex rounded-xl border border-border bg-muted/40 p-0.5 text-xs">
              <button
                type="button"
                data-testid="btn-breakdown-motivo"
                onClick={() => setBreakdownMode("motivo")}
                className={`min-h-[36px] rounded-lg px-2.5 py-1 text-[11px] font-bold transition-all cursor-pointer ${
                  breakdownMode === "motivo"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Por Motivo
              </button>
              <button
                type="button"
                data-testid="btn-breakdown-categoria"
                onClick={() => setBreakdownMode("categoria")}
                className={`min-h-[36px] rounded-lg px-2.5 py-1 text-[11px] font-bold transition-all cursor-pointer ${
                  breakdownMode === "categoria"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Por Categoría
              </button>
            </div>
          </div>

          {activeBreakdown.length === 0 ? (
            <div className="flex min-h-[200px] items-center justify-center text-xs text-muted-foreground">
              Sin desglose disponible para el período seleccionado.
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              {activeBreakdown.map((item) => {
                const clampedPct = Math.min(100, Math.max(0, item.porcentaje));
                return (
                  <div
                    key={item.id}
                    data-testid={`motivo-breakdown-item-${item.label}`}
                    onClick={() => {
                      if (breakdownMode === "motivo" && onFilterByMotivo) {
                        onFilterByMotivo(item.label);
                      }
                    }}
                    className={`rounded-xl border border-border/60 bg-background/60 p-3 transition-all hover:border-primary/40 ${
                      breakdownMode === "motivo" && onFilterByMotivo ? "cursor-pointer" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 text-xs mb-1.5">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold ${item.palette.badge}`}
                        >
                          {item.label}
                        </span>
                        <span className="text-[11px] text-muted-foreground font-mono">
                          ({item.cantidad.toFixed(1)} u.)
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <span className="font-mono font-bold text-foreground">
                          {format(item.costo)}
                        </span>
                        <span className="font-mono text-[11px] font-black text-rose-600 dark:text-rose-400">
                          {clampedPct.toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    {/* Barra de progreso cromática */}
                    <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${item.palette.bar}`}
                        style={{ width: `${clampedPct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="mt-4 pt-3 border-t border-border/50 flex items-center justify-between text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5 text-primary" />
            Total auditado:{" "}
            <strong className="font-mono text-foreground">
              {format(analytics.total_perdida_ppp || 0)}
            </strong>
          </span>
          <span>Haz clic en un motivo para filtrar historial</span>
        </div>
      </div>
    </div>
  );
}

export default MermaStats;
