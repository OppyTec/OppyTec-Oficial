/**
 * oppytec-frontend/src/features/procurement/components/ComprasDashboard.tsx
 * Panel de Analítica y KPIs Ejecutivos para Abastecimiento y Compras.
 * Formateo monetario FX con precisión Decimal y adaptación visual Mobile-First.
 */

import { BarChart3, Clock, DollarSign, Package, TrendingDown, TrendingUp, Truck, RefreshCw } from "lucide-react";
import { useCurrencyFormatter } from "@/shared/currency";
import type { ProcurementDashboardData } from "../types";

export interface ComprasDashboardProps {
  readonly dashboard: ProcurementDashboardData;
  readonly isLoading?: boolean;
  readonly onRefresh?: () => void;
}

export function ComprasDashboard({
  dashboard,
  isLoading = false,
  onRefresh,
}: ComprasDashboardProps) {
  const { format } = useCurrencyFormatter();

  const totalGasto = dashboard.total_mes_monto ?? dashboard.monto_total_mes ?? 0;
  const ordenesPendientes =
    dashboard.ordenes_pendientes_recepcion ?? dashboard.ordenes_pendientes ?? 0;
  const tiempoPromedio = dashboard.tiempo_promedio_entrega_dias ?? 0;
  const proveedorPrincipal = dashboard.proveedor_principal || "Sin asignar";
  const variacionPct = Number(dashboard.variacion_mes_anterior_pct ?? 0);
  const esVariacionPositiva = variacionPct >= 0;

  const topProveedores = dashboard.gastos_por_proveedor ?? [];

  return (
    <div data-testid="compras-dashboard" className="space-y-6">
      {/* Header con botón refrescar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground md:text-xl">
            Panel de Control de Abastecimiento
          </h2>
          <p className="text-xs text-muted-foreground md:text-sm">
            Monitoreo en tiempo real de gastos, recepciones y cumplimiento de proveedores
          </p>
        </div>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={isLoading}
            data-testid="compras-dashboard-refresh-btn"
            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center gap-2 rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-semibold text-foreground shadow-sm transition-all hover:bg-muted active:scale-95 disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Actualizar</span>
          </button>
        )}
      </div>

      {/* Grid de 4 KPIs Superiores */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* KPI 1: Gasto Total */}
        <div
          data-testid="kpi-gasto-total"
          className="glass-card flex flex-col justify-between rounded-2xl border border-border p-4 shadow-sm transition-all hover:border-primary/40"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Gasto Total Período
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <DollarSign className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-black text-foreground">
              {format(totalGasto)}
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
              {esVariacionPositiva ? (
                <span className="flex items-center font-semibold text-emerald-600 dark:text-emerald-400">
                  <TrendingUp className="mr-0.5 h-3.5 w-3.5" />
                  +{variacionPct}%
                </span>
              ) : (
                <span className="flex items-center font-semibold text-rose-600 dark:text-rose-400">
                  <TrendingDown className="mr-0.5 h-3.5 w-3.5" />
                  {variacionPct}%
                </span>
              )}
              <span>vs mes anterior</span>
            </div>
          </div>
        </div>

        {/* KPI 2: Órdenes Pendientes */}
        <div
          data-testid="kpi-ordenes-pendientes"
          className="glass-card flex flex-col justify-between rounded-2xl border border-border p-4 shadow-sm transition-all hover:border-amber-500/40"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Órdenes Pendientes
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-500">
              <Package className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-black text-foreground">
              {ordenesPendientes}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              En espera de recepción física en andén
            </p>
          </div>
        </div>

        {/* KPI 3: Tiempo Promedio de Entrega */}
        <div
          data-testid="kpi-tiempo-entrega"
          className="glass-card flex flex-col justify-between rounded-2xl border border-border p-4 shadow-sm transition-all hover:border-blue-500/40"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Lead Time Promedio
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-500">
              <Clock className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-black text-foreground">
              {tiempoPromedio} <span className="text-sm font-normal text-muted-foreground">días</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Tiempo medio desde emisión a entrega
            </p>
          </div>
        </div>

        {/* KPI 4: Proveedor Principal */}
        <div
          data-testid="kpi-proveedor-principal"
          className="glass-card flex flex-col justify-between rounded-2xl border border-border p-4 shadow-sm transition-all hover:border-indigo-500/40"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Proveedor Principal
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-500">
              <Truck className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="truncate text-base font-bold text-foreground md:text-lg" title={proveedorPrincipal}>
              {proveedorPrincipal}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Mayor volumen de compras en el período
            </p>
          </div>
        </div>
      </div>

      {/* Distribución por Top Proveedores y Análisis */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Distribución de Compras por Proveedor */}
        <div
          data-testid="compras-distribution-card"
          className="glass-card rounded-2xl border border-border p-4 shadow-sm md:p-6"
        >
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              <h3 className="text-sm font-bold text-foreground md:text-base">
                Distribución de Gasto por Proveedor
              </h3>
            </div>
            <span className="text-xs font-medium text-muted-foreground">Top Participación</span>
          </div>

          <div className="space-y-4">
            {topProveedores.length === 0 ? (
              <p className="py-6 text-center text-xs text-muted-foreground">
                No hay datos de distribución disponibles para este ciclo.
              </p>
            ) : (
              topProveedores.map((item, index) => {
                const totalItem = item.total_costo ?? item.total ?? 0;
                const pct = Number(item.porcentaje ?? 0);
                const nombre = item.razon_social || `Proveedor #${item.proveedor_id || index + 1}`;

                return (
                  <div key={item.proveedor_id || index} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-medium">
                      <span className="truncate pr-2 text-foreground font-semibold" title={nombre}>
                        {nombre}
                      </span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-muted-foreground">{pct}%</span>
                        <span className="font-bold text-foreground">{format(totalItem)}</span>
                      </div>
                    </div>
                    <div className="h-2.5 w-full overflow-hidden rounded-full bg-secondary/50">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-primary to-primary/80 transition-all duration-500"
                        style={{ width: `${Math.min(100, Math.max(2, pct))}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Resumen Operativo y Recomendaciones */}
        <div className="glass-card flex flex-col justify-between rounded-2xl border border-border p-4 shadow-sm md:p-6">
          <div>
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Truck className="h-5 w-5 text-emerald-500" />
                <h3 className="text-sm font-bold text-foreground md:text-base">
                  Resumen de Abastecimiento & Scorecard
                </h3>
              </div>
              <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                Operación Normal
              </span>
            </div>

            <div className="space-y-3 text-xs md:text-sm text-muted-foreground">
              <p>
                El ritmo de abastecimiento actual mantiene una tasa de entrega promedio de{" "}
                <strong className="text-foreground">{tiempoPromedio} días</strong>.
              </p>
              <div className="rounded-xl border border-border bg-secondary/20 p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground">Proveedores activos:</span>
                  <span className="font-bold text-foreground">{dashboard.proveedores_activos ?? 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground">Órdenes pendientes de recepción:</span>
                  <span className="font-bold text-amber-600 dark:text-amber-400">{ordenesPendientes}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground">Volumen de gasto principal:</span>
                  <span className="font-semibold text-foreground truncate max-w-[200px]" title={proveedorPrincipal}>
                    {proveedorPrincipal}
                  </span>
                </div>
              </div>
              <p className="text-xs">
                💡 Recuerde registrar lotes y fechas de vencimiento al recepcionar insumos perecibles para asegurar la trazabilidad FIFO y control de mermas.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
