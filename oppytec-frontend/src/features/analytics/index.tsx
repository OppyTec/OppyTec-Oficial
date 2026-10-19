import { useState } from "react";
import { MoneyBadge } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";

const ANALYTICS_PANELS = [
  "HomeDashboard",
  "Proyeccion",
  "Informes",
  "ReporteFoodCost",
  "ReporteRotacion",
  "ReporteMerma7x24",
  "ReporteParetoABC",
  "ReporteKasavanaSmith",
] as const;

export type AnalyticsPanelId = (typeof ANALYTICS_PANELS)[number];

export function AnalyticsFeatureView() {
  const [activePanel, setActivePanel] =
    useState<AnalyticsPanelId>("HomeDashboard");

  return (
    <section
      data-testid="feature-analytics"
      className="glass-card space-y-4 rounded-xl p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {translateKey("analytics", "title")}
          </h2>
          <p className="text-xs text-muted-foreground">
            {translateKey("analytics", "kpis.period_comparison", {
              period: "2026-10",
            })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-lg bg-primary/15 px-2.5 py-1 font-mono text-xs font-bold text-primary">
            {translateKey("analytics", "kpis.real_vs_theoretical", {
              gapPct: "1.4",
            })}
          </span>
          <span className="rounded-lg bg-secondary px-2.5 py-1 font-mono text-xs text-foreground">
            {translateKey("analytics", "kpis.inventory_turnover", { days: 6 })}
          </span>
        </div>
      </div>

      {/* Selector de HomeDashboard, Proyeccion, Informes y los 5 Reportes */}
      <div className="flex flex-wrap gap-1.5">
        {ANALYTICS_PANELS.map((panel) => (
          <button
            key={panel}
            type="button"
            data-testid={`analytics-panel-btn-${panel}`}
            onClick={() => setActivePanel(panel)}
            className={`touch-target inline-flex min-h-[44px] items-center rounded-lg px-3 py-1.5 text-xs font-semibold ${
              activePanel === panel
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground"
            }`}
          >
            {panel}
          </button>
        ))}
      </div>

      <div
        data-testid={`analytics-active-panel-${activePanel}`}
        className="grid grid-cols-1 gap-3 md:grid-cols-2"
      >
        <div className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3">
          <h3 className="text-xs font-bold uppercase text-muted-foreground">
            Matriz Kasavana & Smith (Ingeniería de Menú)
          </h3>
          <ul className="space-y-1 text-xs">
            <li className="rounded bg-card p-2">
              {translateKey("analytics", "matrix.star")} — Pollo King Grill
            </li>
            <li className="rounded bg-card p-2">
              {translateKey("analytics", "matrix.plowhorse")} — Menú Ejecutivo
            </li>
            <li className="rounded bg-card p-2">
              {translateKey("analytics", "matrix.puzzle")} — Salmón Trufado
            </li>
            <li className="rounded bg-card p-2">
              {translateKey("analytics", "matrix.dog")} — Ensalada Estacional
            </li>
          </ul>
        </div>

        <div className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3">
          <h3 className="text-xs font-bold uppercase text-muted-foreground">
            {`Panel Financiero Multi-Moneda: ${activePanel}`}
          </h3>
          <div className="flex items-center justify-between rounded-lg bg-card p-2.5 text-xs">
            <span>Ventas Netas Acumuladas</span>
            <MoneyBadge amount="48500000" baseCurrency="CLP" />
          </div>
          <div className="flex items-center justify-between rounded-lg bg-card p-2.5 text-xs">
            <span>Costo Real de Ventas (Kardex)</span>
            <MoneyBadge amount="14850000" baseCurrency="CLP" />
          </div>
        </div>
      </div>
    </section>
  );
}
