// oppytec-frontend/src/features/inventory/alerts/components/StockCriticoCard.tsx
import React from "react";
import { ShoppingCart } from "lucide-react";
import { useTranslation } from "react-i18next";
import { BodegaBadge } from "@/shared/components/layout";
import { useCurrencyFormatter } from "@/shared/currency";
import { cn } from "@/shared/lib";
import type { CriticalStockAlert, AlertProductItem } from "../types";

export interface StockCriticoCardProps {
  readonly item: CriticalStockAlert | AlertProductItem;
  readonly isAnimating?: boolean;
  readonly onAddToCart: (item: CriticalStockAlert | AlertProductItem, e?: React.MouseEvent) => void;
}

export function StockCriticoCard({
  item,
  isAnimating = false,
  onAddToCart,
}: StockCriticoCardProps) {
  const { t } = useTranslation("alerts");
  const { convertAndFormat } = useCurrencyFormatter();

  const productId = "producto_id" in item ? item.producto_id : 0;
  const productName = "producto_nombre" in item ? item.producto_nombre : item.nombre;
  const stockActual = "stock_actual" in item ? item.stock_actual : item.cantidad;
  const stockMinimo = item.stock_minimo;
  const unidadMedida = "unidad_medida" in item ? item.unidad_medida : item.unidad;
  const bodegaNombre = item.bodega_nombre;
  const bodegaColor = item.bodega_color;
  const bodegaIcono = item.bodega_icono;
  const costoPromedio =
    "costo_promedio" in item && typeof item.costo_promedio === "number"
      ? item.costo_promedio
      : "costo_unitario" in item && typeof item.costo_unitario === "number"
      ? item.costo_unitario
      : 0;

  const ratio = stockMinimo > 0 ? (stockActual / stockMinimo) * 100 : 0;
  const cappedRatio = Math.min(Math.max(ratio, 5), 100);

  // Determinar color de barra según salud de existencias
  const getProgressColor = () => {
    if (stockActual <= 0) return "bg-destructive";
    if (stockActual <= stockMinimo * 0.5) return "bg-orange-500";
    return "bg-amber-500";
  };

  return (
    <div
      data-testid={`card-stock-${productId}`}
      data-unit-cost={costoPromedio > 0 ? convertAndFormat(costoPromedio) : undefined}
      className="group relative rounded-3xl border border-border bg-card/60 backdrop-blur-sm p-5 transition-all duration-300 hover:shadow-2xl hover:scale-[1.02] overflow-hidden flex flex-col justify-between h-48"
    >
      {/* Indicador inferior cromático fijo */}
      <div className="absolute bottom-0 inset-x-0 h-1 bg-destructive" />

      {/* Bloque Superior: Título y Barra de Salud */}
      <div className="space-y-2">
        <div className="flex justify-between items-start gap-2">
          <h4
            className="font-black text-base tracking-tight group-hover:text-primary transition-colors line-clamp-2 h-12 leading-tight flex-1"
            title={productName}
          >
            {productName}
          </h4>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[9px] font-bold uppercase">
            <span className={cn(stockActual <= 0 ? "text-destructive" : "text-orange-500")}>
              {stockActual <= 0 ? t("status.depleted") : t("status.critical")}
            </span>
            <span>{Math.round(ratio)}%</span>
          </div>
          <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
            <div
              className={cn("h-full transition-all duration-500", getProgressColor())}
              style={{ width: `${cappedRatio}%` }}
            />
          </div>
        </div>
      </div>

      {/* Bloque Inferior: Bodega, Stock Actual, Stock Mínimo y Carrito Morado */}
      <div className="flex justify-between items-center mt-4 w-full gap-2 bg-secondary/10 p-2 rounded-2xl border border-border/40">
        {/* Bodega */}
        <div className="shrink-0">
          <BodegaBadge
            nombre={bodegaNombre}
            color={bodegaColor}
            icono={bodegaIcono}
            className="text-[10px] py-1 px-2 shrink-0"
          />
        </div>

        {/* Stock Actual */}
        <div className="text-center shrink-0">
          <p className="text-[7.5px] font-black uppercase opacity-60 tracking-wider">
            {t("cards.actual")}
          </p>
          <p className="font-black text-[13px] text-foreground leading-none mt-0.5">
            {stockActual}{" "}
            <span className="text-[9px] font-normal text-muted-foreground">
              {unidadMedida}
            </span>
          </p>
        </div>

        {/* Stock Mínimo */}
        <div className="text-center shrink-0">
          <p className="text-[7.5px] font-black uppercase opacity-60 tracking-wider">
            {t("cards.minimo")}
          </p>
          <p className="font-black text-[13px] text-muted-foreground leading-none mt-0.5">
            {stockMinimo}{" "}
            <span className="text-[9px] font-normal text-muted-foreground">
              {unidadMedida}
            </span>
          </p>
        </div>

        {/* Botón Carrito de Compras Morado */}
        <button
          type="button"
          data-testid={`btn-add-cart-card-${productId}`}
          onClick={(e) => onAddToCart(item, e)}
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
              isAnimating ? "scale-110 transition-none" : "transition-transform duration-1000 ease-out"
            )}
          />
        </button>
      </div>
    </div>
  );
}

export default StockCriticoCard;
