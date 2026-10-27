/**
 * oppytec-frontend/src/features/procurement/mermas/KpiDashboard.tsx
 * Dashboard de Tarjetas de KPIs Financieros y Operativos de Merma (Fase 6.3).
 * - Pérdida Neta Total valorizada a PPP (con formateo FX Decimal).
 * - Unidades Totales Descartadas.
 * - Ratio de Pérdida respecto a Inventario / Ventas (%).
 * - Motivo Principal de Merma con proporción porcentual.
 */

import { useMemo } from "react";
import {
  AlertTriangle,
  DollarSign,
  PackageX,
  Percent,
  ShieldAlert,
  TrendingDown,
} from "lucide-react";
import { useCurrencyFormatter } from "@/shared/currency";
import type { MermaAnalyticsData } from "../types";

export interface KpiDashboardProps {
  readonly analytics: MermaAnalyticsData;
  readonly isLoading?: boolean;
  readonly onSelectMotivo?: (motivo: string) => void;
}

export function KpiDashboard({
  analytics,
  isLoading = false,
  onSelectMotivo,
}: KpiDashboardProps) {
  const { format } = useCurrencyFormatter();

  const mainMotivoDetails = useMemo(() => {
    const breakdown = analytics.motivos_breakdown ?? analytics.por_motivo ?? [];
    const mainName = analytics.motivo_principal || breakdown[0]?.motivo || "Vencimiento";
    const match =
      breakdown.find((m) => m.motivo.toLowerCase() === mainName.toLowerCase()) ??
      breakdown[0];

    const pct = match ? Number(match.porcentaje || 0).toFixed(1) : "0.0";
    const cost = match ? match.total_costo : 0;

    return {
      motivo: mainName,
      porcentaje: pct,
      costo: cost,
    };
  }, [analytics]);

  const ratioNum = Number(analytics.ratio_merma_ventas || 0);
  const isHighRatio = ratioNum >= 2.0;

  if (isLoading) {
    return (
      <div
        data-testid="merma-kpi-dashboard-skeleton"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        {[1, 2, 3, 4].map((idx) => (
          <div
            key={idx}
            className="glass-card h-28 animate-pulse rounded-2xl border border-border bg-card p-4"
          />
        ))}
      </div>
    );
  }

  return (
    <div
      data-testid="merma-kpi-dashboard"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
    >
      {/* 1. Pérdida Neta Total valorizada a PPP */}
      <div
        data-testid="kpi-perdida-neta-ppp"
        className="glass-card relative overflow-hidden rounded-2xl border border-rose-500/30 bg-card p-4 shadow-sm transition-all hover:border-rose-500/50 hover:shadow-md flex flex-col justify-between min-h-[118px]"
      >
        <div className="flex items-start justify-between gap-2">
          <span className="text-[11px] font-black uppercase tracking-wider text-muted-foreground">
            Pérdida Neta Total (PPP)
          </span>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-rose-500/15 text-rose-500">
            <DollarSign className="h-4 w-4" />
          </div>
        </div>
        <div className="my-1">
          <span
            data-testid="kpi-perdida-neta-value"
            className="text-xl font-black tracking-tight text-rose-600 dark:text-rose-400 font-mono block truncate"
          >
            {format(analytics.total_perdida_ppp || 0)}
          </span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1 font-semibold text-rose-500">
            <TrendingDown className="h-3.5 w-3.5" />
            Valorizado a Costo Promedio
          </span>
          {analytics.mermas_pendientes_aprobacion ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-600 dark:text-amber-400">
              <ShieldAlert className="h-3 w-3" />
              {analytics.mermas_pendientes_aprobacion} pend.
            </span>
          ) : null}
        </div>
      </div>

      {/* 2. Unidades Totales Descartadas */}
      <div
        data-testid="kpi-unidades-descartadas"
        className="glass-card relative overflow-hidden rounded-2xl border border-border bg-card p-4 shadow-sm transition-all hover:border-primary/40 hover:shadow-md flex flex-col justify-between min-h-[118px]"
      >
        <div className="flex items-start justify-between gap-2">
          <span className="text-[11px] font-black uppercase tracking-wider text-muted-foreground">
            Unidades Descartadas
          </span>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-500">
            <PackageX className="h-4 w-4" />
          </div>
        </div>
        <div className="my-1">
          <span
            data-testid="kpi-unidades-value"
            className="text-xl font-black tracking-tight text-foreground font-mono block truncate"
          >
            {Number(analytics.unidades_mermadas || 0).toLocaleString("es-CL", {
              maximumFractionDigits: 2,
            })}{" "}
            <span className="text-xs font-semibold text-muted-foreground">unid.</span>
          </span>
        </div>
        <div className="text-[11px] text-muted-foreground font-medium">
          En{" "}
          <strong className="text-foreground">
            {analytics.items_mermados_count ?? analytics.motivos_breakdown?.length ?? 0}
          </strong>{" "}
          registros auditados
        </div>
      </div>

      {/* 3. Ratio de Pérdida respecto a Inventario / Ventas (%) */}
      <div
        data-testid="kpi-ratio-merma"
        className="glass-card relative overflow-hidden rounded-2xl border border-border bg-card p-4 shadow-sm transition-all hover:border-primary/40 hover:shadow-md flex flex-col justify-between min-h-[118px]"
      >
        <div className="flex items-start justify-between gap-2">
          <span className="text-[11px] font-black uppercase tracking-wider text-muted-foreground">
            Ratio Merma / Ventas
          </span>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-blue-500/15 text-blue-500">
            <Percent className="h-4 w-4" />
          </div>
        </div>
        <div className="my-1 flex items-baseline gap-2">
          <span
            data-testid="kpi-ratio-value"
            className="text-xl font-black tracking-tight text-foreground font-mono"
          >
            {ratioNum.toFixed(2)}%
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
              isHighRatio
                ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30"
                : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
            }`}
          >
            {isHighRatio ? "Alerta Crítica" : "Bajo Umbral"}
          </span>
        </div>
        <div className="text-[11px] text-muted-foreground font-medium">
          Impacto sobre costo de inventario y ventas
        </div>
      </div>

      {/* 4. Motivo Principal de Merma */}
      <button
        type="button"
        data-testid="kpi-motivo-principal"
        onClick={() => onSelectMotivo?.(mainMotivoDetails.motivo)}
        className="glass-card relative overflow-hidden rounded-2xl border border-border bg-card p-4 shadow-sm transition-all hover:border-amber-500/50 hover:shadow-md flex flex-col justify-between min-h-[118px] text-left cursor-pointer"
      >
        <div className="flex items-start justify-between gap-2 w-full">
          <span className="text-[11px] font-black uppercase tracking-wider text-muted-foreground">
            Motivo Principal de Merma
          </span>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-purple-500/15 text-purple-500">
            <AlertTriangle className="h-4 w-4" />
          </div>
        </div>
        <div className="my-1 w-full">
          <span
            data-testid="kpi-motivo-principal-name"
            className="text-base font-black tracking-tight text-foreground block truncate"
          >
            {mainMotivoDetails.motivo}
          </span>
        </div>
        <div className="flex items-center justify-between w-full text-[11px]">
          <span
            data-testid="kpi-motivo-principal-pct"
            className="font-bold text-amber-600 dark:text-amber-400"
          >
            {mainMotivoDetails.porcentaje}% del total
          </span>
          <span className="font-mono font-semibold text-muted-foreground">
            {format(mainMotivoDetails.costo)}
          </span>
        </div>
      </button>
    </div>
  );
}

export default KpiDashboard;
