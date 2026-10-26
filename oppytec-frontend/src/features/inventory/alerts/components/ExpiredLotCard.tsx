// oppytec-frontend/src/features/inventory/alerts/components/ExpiredLotCard.tsx
import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { BodegaBadge } from "@/shared/components/layout";
import { useCurrencyFormatter } from "@/shared/currency";
import { cn } from "@/shared/lib";
import { format, formatDistanceToNow, es, en } from "../dateUtils";
import type { ExpiredLotAlert, AlertProductItem } from "../types";

export interface ExpiredLotCardProps {
  readonly item: ExpiredLotAlert | AlertProductItem;
  readonly onReportMerma?: (item: ExpiredLotAlert | AlertProductItem) => void;
}

export function ExpiredLotCard({ item, onReportMerma }: ExpiredLotCardProps) {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation("alerts");
  const { convertAndFormat } = useCurrencyFormatter();

  const productId = "producto_id" in item ? item.producto_id : 0;
  const productName = "producto_nombre" in item ? item.producto_nombre : item.nombre;
  const loteCodigo = "lote_codigo" in item ? item.lote_codigo : null;
  const fechaVencimiento = item.fecha_vencimiento;
  const cantidadVencida = item.cantidad_vencida;
  const unidadMedida = "unidad_medida" in item ? item.unidad_medida : item.unidad;
  const bodegaNombre = item.bodega_nombre;
  const bodegaColor = item.bodega_color;
  const bodegaIcono = item.bodega_icono;
  const valorRiesgo =
    "valor_total_riesgo" in item && typeof item.valor_total_riesgo === "number"
      ? item.valor_total_riesgo
      : 0;

  const handleMermaClick = () => {
    if (onReportMerma) {
      onReportMerma(item);
    } else {
      navigate("/gestion?tab=mermas");
    }
  };

  const formattedDate = fechaVencimiento ? format(fechaVencimiento, "dd-MM-yyyy") : "—";
  const activeLocale = i18n.language === "en" ? en : es;
  const relativeDistance = fechaVencimiento
    ? formatDistanceToNow(fechaVencimiento, { addSuffix: true, locale: activeLocale })
    : "";

  return (
    <div
      data-testid={`card-expired-${productId}`}
      data-financial-risk={valorRiesgo > 0 ? convertAndFormat(valorRiesgo) : undefined}
      className="group relative rounded-3xl border border-red-500/20 bg-card/60 backdrop-blur-sm p-5 transition-all duration-300 hover:shadow-2xl hover:scale-[1.02] overflow-hidden flex flex-col justify-between h-48"
    >
      {/* Indicador inferior cromático rojo */}
      <div className="absolute bottom-0 inset-x-0 h-1 bg-red-600" />

      {/* Bloque Superior: Título y Vencimiento */}
      <div className="space-y-2">
        <div className="flex justify-between items-start gap-2">
          <h4
            className="font-black text-base tracking-tight group-hover:text-primary transition-colors line-clamp-2 h-12 leading-tight flex-1"
            title={productName}
          >
            {productName}
          </h4>
        </div>

        <div>
          <div className="flex justify-between items-center text-[8px] font-black uppercase opacity-50">
            <span>{t("cards.expiration")}</span>
            {loteCodigo && <span>{t("cards.lot_prefix", { code: loteCodigo })}</span>}
          </div>
          <div className="flex justify-between items-center mt-0.5">
            <span className="text-xs font-bold text-destructive">
              {formattedDate}
            </span>
            {relativeDistance && (
              <span className="text-[9px] italic text-muted-foreground">
                {relativeDistance}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Bloque Inferior: Stock Afectado, Bodega y Botón Merma */}
      <div className="flex justify-between items-center mt-4 w-full gap-2 bg-secondary/10 p-2 rounded-2xl border border-border/40">
        <div className="shrink-0">
          <p className="text-[7.5px] font-black uppercase opacity-60 tracking-wider">
            {t("cards.affected_stock")}
          </p>
          <p className="font-black text-[13px] text-destructive leading-none mt-0.5">
            {cantidadVencida}{" "}
            <span className="text-[9px] font-normal text-muted-foreground">
              {unidadMedida}
            </span>
          </p>
        </div>

        <div className="flex-1 flex justify-center px-1">
          <BodegaBadge
            nombre={bodegaNombre}
            color={bodegaColor}
            icono={bodegaIcono}
            className="text-[10px] py-1 px-2 shrink-0"
          />
        </div>

        <div className="text-right shrink-0">
          <button
            type="button"
            data-testid={`btn-report-merma-${productId}`}
            onClick={handleMermaClick}
            title={t("cards.report_merma")}
            aria-label={t("cards.report_merma_for", { name: productName })}
            className={cn(
              "h-8 w-8 rounded-xl shrink-0 [touch-action:manipulation] border-none inline-flex items-center justify-center transition-all select-none",
              "bg-red-500/10 text-destructive hover:bg-red-500/20 active:scale-95"
            )}
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default ExpiredLotCard;
