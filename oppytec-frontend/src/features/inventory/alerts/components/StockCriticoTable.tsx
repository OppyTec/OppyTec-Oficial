// oppytec-frontend/src/features/inventory/alerts/components/StockCriticoTable.tsx
import React from "react";
import { AlertCircle, ShoppingCart } from "lucide-react";
import { useTranslation } from "react-i18next";
import { BodegaBadge } from "@/shared/components/layout";
import { useCurrencyFormatter } from "@/shared/currency";
import { cn } from "@/shared/lib";
import type { CriticalStockAlert, AlertProductItem } from "../types";

export interface StockCriticoTableProps {
  readonly data: readonly (CriticalStockAlert | AlertProductItem)[];
  readonly totalCount?: number;
  readonly addToCart: (p: CriticalStockAlert | AlertProductItem, e?: React.MouseEvent) => void;
  readonly animatingCarts: Record<string, boolean>;
}

export function StockCriticoTable({
  data,
  totalCount,
  addToCart,
  animatingCarts,
}: StockCriticoTableProps) {
  const { t } = useTranslation("alerts");
  const { convertAndFormat } = useCurrencyFormatter();

  // Función para calcular el color de la barra de progreso
  const getProgressColor = (current: number, min: number) => {
    if (current <= 0) return "bg-destructive";
    if (current <= min * 0.5) return "bg-orange-500";
    return "bg-amber-500";
  };

  const countDisplay = totalCount !== undefined ? totalCount : data.length;

  return (
    <div
      data-testid="stock-critico-table"
      className="bg-card border border-border rounded-2xl shadow-sm overflow-hidden"
    >
      {/* Cabecera estilizada */}
      <div className="p-4 border-b border-border bg-muted/30 flex justify-between items-center">
        <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-destructive" />
          <span>{t("table.title")}</span>
        </h3>
        <span
          data-testid="stock-table-alert-badge"
          className="text-xs font-black uppercase tracking-wider px-3 py-1 rounded-full bg-destructive/10 text-destructive border border-destructive/20"
        >
          {countDisplay === 1
            ? t("table.active_alert_one", { count: countDisplay })
            : t("table.active_alert_other", { count: countDisplay })}
        </span>
      </div>

      {/* Contenedor con scroll horizontal */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-border bg-muted/20 text-[10px] font-black uppercase tracking-wider text-muted-foreground select-none">
              <th className="py-3 px-4">{t("table.col_product")}</th>
              <th className="py-3 px-4 w-48">{t("table.col_health")}</th>
              <th className="py-3 px-4 text-right">{t("table.col_actual")}</th>
              <th className="py-3 px-4 text-right">{t("table.col_min")}</th>
              <th className="py-3 px-4 w-12 text-center">{t("table.col_action")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  data-testid="empty-stock-critico-table"
                  className="text-center py-8 text-muted-foreground italic text-xs"
                >
                  {t("table.empty")}
                </td>
              </tr>
            ) : (
              data.map((prod) => {
                const productId = "producto_id" in prod ? prod.producto_id : 0;
                const productName =
                  "producto_nombre" in prod ? prod.producto_nombre : prod.nombre;
                const stockActual =
                  "stock_actual" in prod ? prod.stock_actual : prod.cantidad;
                const stockMinimo = prod.stock_minimo;
                const unidad =
                  "unidad_medida" in prod ? prod.unidad_medida : prod.unidad;
                const bodegaNombre = prod.bodega_nombre;
                const bodegaColor = prod.bodega_color;
                const bodegaIcono = prod.bodega_icono;
                const costoPromedio =
                  "costo_promedio" in prod && typeof prod.costo_promedio === "number"
                    ? prod.costo_promedio
                    : "costo_unitario" in prod && typeof prod.costo_unitario === "number"
                    ? prod.costo_unitario
                    : 0;

                const itemId =
                  "id" in prod && prod.id
                    ? String(prod.id)
                    : `${productId}::${prod.bodega_id}`;
                const isAnimating = !!(
                  animatingCarts[itemId] ||
                  animatingCarts[`${productId}::${prod.bodega_id}`] ||
                  animatingCarts[String(productId)]
                );

                const ratio =
                  stockMinimo > 0 ? (stockActual / stockMinimo) * 100 : 0;
                const cappedRatio = Math.min(Math.max(ratio, 5), 100);

                return (
                  <tr
                    key={itemId}
                    data-testid={`stock-table-row-${productId}`}
                    data-unit-cost={costoPromedio > 0 ? convertAndFormat(costoPromedio) : undefined}
                    className="hover:bg-muted/30 transition-colors"
                  >
                    {/* Columna: Producto + BodegaBadge */}
                    <td className="py-3 px-4">
                      <div className="font-semibold text-foreground text-xs">
                        {productName}
                      </div>
                      <div className="mt-1">
                        <BodegaBadge
                          nombre={bodegaNombre}
                          color={bodegaColor}
                          icono={bodegaIcono}
                          className="scale-75 origin-left"
                        />
                      </div>
                    </td>

                    {/* Columna: Estado / Salud con Barra Cromática */}
                    <td className="py-3 px-4 w-48">
                      <div className="space-y-1">
                        <div className="flex justify-between text-[10px] font-bold uppercase">
                          <span
                            className={cn(
                              stockActual <= 0
                                ? "text-destructive"
                                : "text-orange-600"
                            )}
                          >
                            {stockActual <= 0 ? t("status.depleted") : t("status.critical")}
                          </span>
                          <span className="text-muted-foreground">
                            {Math.round(ratio)}%
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                          <div
                            className={cn(
                              "h-full transition-all duration-500",
                              getProgressColor(stockActual, stockMinimo)
                            )}
                            style={{ width: `${cappedRatio}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* Columna: Actual */}
                    <td className="py-3 px-4 text-right font-black text-xs text-foreground whitespace-nowrap">
                      {stockActual}{" "}
                      <span className="text-[10px] font-normal text-muted-foreground">
                        {unidad}
                      </span>
                    </td>

                    {/* Columna: Mínimo */}
                    <td className="py-3 px-4 text-right text-muted-foreground font-medium text-xs whitespace-nowrap">
                      {stockMinimo} {unidad}
                    </td>

                    {/* Columna: Botón Carrito de Compra Morado */}
                    <td className="py-3 px-4 text-center">
                      <button
                        type="button"
                        data-testid={`btn-add-cart-table-${productId}`}
                        onClick={(e) => addToCart(prod, e)}
                        className={cn(
                          "h-8 w-8 rounded-xl shrink-0 [touch-action:manipulation] border-none inline-flex items-center justify-center transition-all select-none",
                          isAnimating
                            ? "bg-purple-600 hover:bg-purple-600 text-white scale-110 shadow-md shadow-purple-500/40"
                            : "bg-purple-500/10 hover:bg-purple-500/20 text-purple-600 active:scale-95"
                        )}
                        title={t("cards.add_to_cart")}
                        aria-label={t("cards.buy_product", { name: productName })}
                      >
                        <ShoppingCart
                          className={cn(
                            "h-4 w-4",
                            isAnimating
                              ? "scale-110 transition-none"
                              : "transition-transform duration-1000 ease-out"
                          )}
                        />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default StockCriticoTable;
