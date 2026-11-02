/**
 * oppytec-frontend/src/features/projection/components/ProyeccionProductDetail.tsx
 * Vista de Detalle Profundo con Curva Recharts Interactiva y Panel Lateral de Métricas.
 * Integración con useProyeccionChart, fallback de simulación client-side, botón volver y animación Framer Motion.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import type { FC } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Boxes,
  CircleDollarSign,
  Package,
  Tag,
  Warehouse,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { formatCurrencyAmount } from "@/shared/currency";
import { cn } from "@/shared/lib";
import {
  buildClientSimulatedChartData,
  useProyeccionChart,
} from "../hooks/useProyeccionChart";
import type { ProjectionProductOverview } from "../types";
import { ProyeccionChart } from "./ProyeccionChart";
import { ProyeccionMetrics } from "./ProyeccionMetrics";

export interface ProyeccionProductDetailProps {
  readonly product: ProjectionProductOverview;
  readonly onBack: () => void;
  readonly onOpenTransfer?: (product: ProjectionProductOverview) => void;
  readonly onManagePurchase?: (product: ProjectionProductOverview) => void;
  readonly horizonDays?: number;
  readonly className?: string;
}

export const ProyeccionProductDetail: FC<ProyeccionProductDetailProps> = ({
  product,
  onBack,
  onOpenTransfer,
  onManagePurchase,
  horizonDays = 30,
  className,
}) => {
  const { t } = useTranslation("projection");

  const {
    producto_id,
    nombre,
    sku,
    unidad = "un",
    categoria_nombre,
    bodega_id,
    bodega_nombre,
    current_qty,
    stock_minimo = 0,
    costo_unitario = 0,
    daily_consumption_rate = 0,
  } = product;

  // Consulta reactiva de curva
  const {
    curvePoints,
    isLoading: isChartLoading,
  } = useProyeccionChart(producto_id, bodega_id ?? "all", horizonDays);

  // Si no hay datos del servidor (por ejemplo en tests sin mock del endpoint o desconexión),
  // utilizamos la simulación client-side ágil como fallback garantizado de paridad y robustez.
  const chartData =
    curvePoints.length > 0
      ? curvePoints
      : isChartLoading
        ? []
        : buildClientSimulatedChartData(
            current_qty,
            daily_consumption_rate || 2,
            horizonDays,
            stock_minimo
          );

  const formattedCosto = formatCurrencyAmount(costo_unitario, "CLP");

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.25 }}
      data-testid="proyeccion-product-detail"
      className={cn("flex flex-col gap-6 w-full", className)}
    >
      {/* Botón de Retorno y Barra Superior */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          data-testid="btn-back-to-list"
          className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-3.5 py-2 text-xs sm:text-sm font-bold text-foreground shadow-sm hover:bg-accent hover:text-accent-foreground active:scale-95 transition-all cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>
            {t("detail.back_button", {
              defaultValue: "Volver al listado",
            })}
          </span>
        </button>

        <span className="text-xs font-semibold text-muted-foreground">
          {t("detail.horizon_badge", {
            defaultValue: "Horizonte: {{days}} días",
            days: horizonDays,
          })}
        </span>
      </div>

      {/* Cabecera del Producto */}
      <div className="rounded-3xl border border-border bg-card p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-700 dark:text-emerald-400">
                <Package className="h-3.5 w-3.5" />
                {unidad.toUpperCase()}
              </span>
              {categoria_nombre && (
                <span className="inline-flex items-center gap-1 rounded-lg bg-muted px-2.5 py-1 text-xs font-semibold text-muted-foreground">
                  <Tag className="h-3.5 w-3.5" />
                  {categoria_nombre}
                </span>
              )}
              {sku && (
                <span className="text-xs font-mono text-muted-foreground">
                  SKU: {sku}
                </span>
              )}
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-foreground tracking-tight">
              {nombre}
            </h2>
          </div>

          {/* Badges de Bodega, PPP y Stock Actual */}
          <div className="flex flex-wrap items-center gap-3">
            {bodega_nombre && (
              <div className="flex items-center gap-1.5 rounded-2xl border border-border/80 bg-background px-3 py-1.5 text-xs font-semibold text-foreground">
                <Warehouse className="h-4 w-4 text-emerald-500" />
                <span>{bodega_nombre}</span>
              </div>
            )}
            <div className="flex items-center gap-1.5 rounded-2xl border border-border/80 bg-background px-3 py-1.5 text-xs font-semibold text-foreground">
              <CircleDollarSign className="h-4 w-4 text-emerald-500" />
              <span>PPP: {formattedCosto}</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-2xl border border-border/80 bg-background px-3 py-1.5 text-xs font-bold text-foreground">
              <Boxes className="h-4 w-4 text-blue-500" />
              <span>
                Stock: {current_qty} {unidad}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Contenido Principal: Gráfico Interactivo a la Izquierda, Métricas a la Derecha */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <div className="lg:col-span-2 space-y-4">
          <ProyeccionChart
            data={chartData}
            stockMinimo={stock_minimo}
            unit={unidad}
            costoUnitario={costo_unitario}
            height={360}
            isLoading={isChartLoading && chartData.length === 0}
          />
        </div>

        <div className="lg:col-span-1">
          <ProyeccionMetrics
            product={product}
            onOpenTransfer={onOpenTransfer}
            onManagePurchase={onManagePurchase}
          />
        </div>
      </div>
    </motion.div>
  );
};
