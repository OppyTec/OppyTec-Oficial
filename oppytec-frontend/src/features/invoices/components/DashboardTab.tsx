/**
 * oppytec-frontend/src/features/invoices/components/DashboardTab.tsx
 * Pestaña Dashboard del Módulo de Facturas: KPIs contables, control FinOps de tokens Gemini
 * y radar analítico de variación de precios de insumos (Price Drift).
 */

import { useTranslation } from "react-i18next";
import {
  Clock,
  CheckCircle2,
  Cpu,
  DollarSign,
  TrendingUp,
  ArrowUpRight,
} from "lucide-react";
import { formatMoney, formatUnitCost, cn } from "@/shared/lib";
import type { InvoiceStats, PriceDriftItem } from "../types";

export interface DashboardTabProps {
  stats?: InvoiceStats;
  priceDriftItems?: PriceDriftItem[];
  isLoading: boolean;
  onNavigateToReview?: () => void;
}

export function DashboardTab({
  stats,
  priceDriftItems = [],
  isLoading,
  onNavigateToReview,
}: DashboardTabProps) {
  const { t } = useTranslation(["invoices"]);
  if (isLoading || !stats) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 rounded-2xl bg-muted/60" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-64 rounded-2xl bg-muted/60" />
          <div className="h-64 rounded-2xl bg-muted/60" />
        </div>
      </div>
    );
  }

  const conversionRate =
    stats.total_invoices > 0
      ? Math.round((stats.confirmed_stock / stats.total_invoices) * 100)
      : 0;

  const costPerInvoiceUsd =
    stats.total_invoices > 0
      ? (stats.total_cost_usd / stats.total_invoices).toFixed(4)
      : "0.0030";

  return (
    <div data-testid="dashboard-tab" className="space-y-6">
      {/* Tarjetas KPI Superiores */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Facturas Pendientes */}
        <div
          onClick={onNavigateToReview}
          className="glass-card rounded-2xl border border-border p-5 shadow-sm hover:border-primary/50 transition-all cursor-pointer relative overflow-hidden group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("invoices:dashboard.kpi_pending", "Por Revisar")}
            </span>
            <div className="h-9 w-9 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center">
              <Clock className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-extrabold text-foreground font-mono">
              {stats.pending_review}
            </span>
            <span className="text-xs text-muted-foreground">
              {t("invoices:dashboard.kpi_pending_of_total", {
                total: stats.total_invoices,
                defaultValue: `de ${stats.total_invoices} total`,
              })}
            </span>
          </div>
          {stats.pending_review > 0 && (
            <div className="mt-2 flex items-center gap-1.5 text-[11px] font-semibold text-amber-500">
              <span className="h-2 w-2 rounded-full bg-amber-500 animate-ping" />
              {t("invoices:dashboard.kpi_pending_badge", "Requieren revisión de stock")}
            </div>
          )}
        </div>

        {/* KPI 2: Total Neto Facturado */}
        <div className="glass-card rounded-2xl border border-border p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("invoices:dashboard.kpi_net", "Neto Compras")}
            </span>
            <div className="h-9 w-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <DollarSign className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-foreground font-mono">
              {formatMoney(stats.total_net_clp)}
            </span>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            {t("invoices:dashboard.kpi_net_sub", "Período en curso")}
          </p>
        </div>

        {/* KPI 3: Total IVA Crédito Fiscal */}
        <div className="glass-card rounded-2xl border border-border p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("invoices:dashboard.kpi_tax", "IVA Crédito (19%)")}
            </span>
            <div className="h-9 w-9 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-foreground font-mono text-blue-600 dark:text-blue-400">
              {formatMoney(stats.total_tax_clp)}
            </span>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            {t("invoices:dashboard.kpi_tax_sub", "Crédito fiscal acumulado")}
          </p>
        </div>

        {/* KPI 4: Ingestadas a Inventario */}
        <div className="glass-card rounded-2xl border border-border p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("invoices:dashboard.kpi_ingested", "Ingreso a Bodega")}
            </span>
            <div className="h-9 w-9 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 font-mono">
              {stats.confirmed_stock}
            </span>
            <span className="text-xs text-muted-foreground font-semibold">({conversionRate}%)</span>
          </div>
          <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-500"
              style={{ width: `${conversionRate}%` }}
            />
          </div>
        </div>
      </div>

      {/* Fila Inferior: FinOps IA & Radar Price Drift */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Panel FinOps de IA (Tokens Gemini & Costo USD) */}
        <div className="glass-card rounded-2xl border border-border p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-primary" />
              <h3 className="text-sm font-bold text-foreground">
                {t("invoices:dashboard.finops_title", "Control FinOps de Tokens IA")}
              </h3>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
              {t("invoices:dashboard.finops_badge", "Gemini 1.5 Multimodal")}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-muted/40 border border-border">
              <span className="text-[11px] text-muted-foreground block">
                {t("invoices:dashboard.tokens_consumed", "Tokens Consumidos")}
              </span>
              <span className="text-xl font-bold font-mono text-foreground mt-1 block">
                {stats.total_tokens_used.toLocaleString("es-CL")}
              </span>
              <span className="text-[10px] text-muted-foreground block mt-1">
                {t("invoices:dashboard.tokens_sub", "Prompt + Candidate")}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <span className="text-[11px] text-emerald-600 dark:text-emerald-400 block font-medium">
                {t("invoices:dashboard.ai_cost", "Gasto Acumulado IA")}
              </span>
              <span className="text-xl font-extrabold font-mono text-emerald-600 dark:text-emerald-400 mt-1 block">
                ${stats.total_cost_usd.toFixed(4)} USD
              </span>
              <span className="text-[10px] text-muted-foreground block mt-1">
                {t("invoices:dashboard.ai_cost_avg", {
                  cost: costPerInvoiceUsd,
                  defaultValue: `Promedio ~$${costPerInvoiceUsd} USD / doc`,
                })}
              </span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-background border border-border/70 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">
              {t("invoices:dashboard.ocr_accuracy", "Promedio de Precisión OCR Global:")}
            </span>
            <span className="font-bold text-foreground font-mono text-sm">
              {Math.round(stats.avg_confidence_score * 100)}%
            </span>
          </div>
        </div>

        {/* Radar de Variación de Precios (Price Drift Widget) */}
        <div className="glass-card rounded-2xl border border-border p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-amber-500" />
              <h3 className="text-sm font-bold text-foreground">
                {t("invoices:dashboard.price_drift_title", "Radar de Variación de Precios (Price Drift)")}
              </h3>
            </div>
            <span className="text-xs text-muted-foreground">
              {t("invoices:dashboard.price_drift_sub", "Top Insumos con Alzas")}
            </span>
          </div>

          {priceDriftItems.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              {t("invoices:dashboard.no_drift", "No se han detectado variaciones significativas de precios en el período.")}
            </div>
          ) : (
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {priceDriftItems.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-2.5 rounded-xl bg-muted/40 border border-border text-xs hover:bg-muted/70 transition-colors"
                >
                  <div className="truncate pr-2">
                    <span className="font-bold text-foreground block truncate">
                      {item.producto_nombre}
                    </span>
                    <span className="text-[10px] text-muted-foreground block truncate">
                      {item.proveedor_nombre} • {item.fecha}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 text-right">
                    <div className="text-[11px] font-mono">
                      <span className="text-muted-foreground line-through block text-[10px]">
                        {formatUnitCost(item.costo_anterior)}
                      </span>
                      <span className="font-bold text-foreground">
                        {formatUnitCost(item.costo_nuevo)}
                      </span>
                    </div>

                    <span
                      className={cn(
                        "inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[11px] font-bold font-mono",
                        item.variacion_pct >= 15
                          ? "bg-rose-500/15 text-rose-500 border border-rose-500/25"
                          : "bg-amber-500/15 text-amber-500 border border-amber-500/25"
                      )}
                    >
                      <ArrowUpRight className="h-3 w-3" />+{item.variacion_pct}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
