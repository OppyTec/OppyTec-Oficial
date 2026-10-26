// oppytec-frontend/src/features/inventory/alerts/components/VencimientosCard.tsx
import { Clock, AlertTriangle, CalendarDays, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { BodegaBadge } from "@/shared/components/layout";
import { useCurrencyFormatter } from "@/shared/currency";
import { cn } from "@/shared/lib";
import { format, formatDistanceToNow, es, en } from "../dateUtils";
import type { ExpiredLotAlert, UpcomingExpiryAlert, AlertProductItem } from "../types";

export interface VencimientosCardProps {
  readonly type: "upcoming" | "expired";
  readonly data: readonly (ExpiredLotAlert | UpcomingExpiryAlert | AlertProductItem)[];
  readonly totalCount?: number;
  readonly onReportMerma?: (item: ExpiredLotAlert | UpcomingExpiryAlert | AlertProductItem) => void;
}

export function VencimientosCard({
  type,
  data,
  totalCount,
  onReportMerma,
}: VencimientosCardProps) {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation("alerts");
  const { convertAndFormat } = useCurrencyFormatter();
  const isExpired = type === "expired";
  const countDisplay = totalCount !== undefined ? totalCount : data.length;

  const handleActionClick = (item: ExpiredLotAlert | UpcomingExpiryAlert | AlertProductItem) => {
    if (onReportMerma) {
      onReportMerma(item);
    } else {
      navigate("/gestion?tab=mermas");
    }
  };

  const activeLocale = i18n.language === "en" ? en : es;

  return (
    <div
      data-testid={`vencimientos-card-${type}`}
      className={cn(
        "rounded-2xl border p-5 bg-card shadow-sm flex flex-col h-full transition-all duration-300",
        isExpired
          ? "border-red-500/20 bg-card/70"
          : "border-amber-500/20 bg-card/70"
      )}
    >
      {/* Cabecera del Panel */}
      <header className="mb-4 flex items-center justify-between">
        <h2 className="text-xs font-black uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          {isExpired ? (
            <AlertTriangle className="h-4 w-4 text-destructive" />
          ) : (
            <Clock className="h-4 w-4 text-amber-500" />
          )}
          <span className="text-foreground">
            {isExpired ? t("sections.expired_products") : t("sections.upcoming_expiry")}
          </span>
        </h2>
        <span
          data-testid={`vencimientos-count-badge-${type}`}
          className={cn(
            "text-xs px-2.5 py-0.5 rounded-full font-black uppercase tracking-wider border",
            isExpired
              ? "bg-red-500/10 text-red-600 border-red-500/20"
              : "bg-amber-500/10 text-amber-600 border-amber-500/20"
          )}
        >
          {countDisplay}
        </span>
      </header>

      {/* Lista vertical con scroll interno */}
      <div className="flex-1 space-y-2.5 overflow-y-auto max-h-[300px] pr-2 scrollbar-thin">
        {data.length === 0 ? (
          <div
            data-testid={`empty-vencimientos-${type}`}
            className="flex flex-col items-center justify-center h-32 text-center opacity-60"
          >
            <CalendarDays className="h-8 w-8 mb-2 text-muted-foreground" />
            <p className="text-xs text-muted-foreground font-medium">
              {t("empty.no_records")}
            </p>
          </div>
        ) : (
          data.map((p) => {
            const productId = "producto_id" in p ? p.producto_id : 0;
            const productName = "producto_nombre" in p ? p.producto_nombre : p.nombre;
            const loteCodigo = "lote_codigo" in p ? p.lote_codigo : null;
            const fechaVencimiento = p.fecha_vencimiento;
            const cantidad =
              "cantidad_vencida" in p && p.cantidad_vencida > 0
                ? p.cantidad_vencida
                : "cantidad_en_riesgo" in p
                ? p.cantidad_en_riesgo
                : "cantidad" in p
                ? p.cantidad
                : 0;
            const unidad = "unidad_medida" in p ? p.unidad_medida : p.unidad;
            const bodegaNombre = p.bodega_nombre;
            const bodegaColor = p.bodega_color;
            const bodegaIcono = p.bodega_icono;
            const valorRiesgo =
              "valor_total_riesgo" in p && typeof p.valor_total_riesgo === "number"
                ? p.valor_total_riesgo
                : 0;

            const formattedDate = fechaVencimiento
              ? format(fechaVencimiento, "dd-MM-yyyy")
              : "—";
            const relativeDistance = fechaVencimiento
              ? formatDistanceToNow(fechaVencimiento, { addSuffix: true, locale: activeLocale })
              : "";

            const key = `${productId}-${bodegaNombre}-${loteCodigo || "lot"}`;

            return (
              <div
                key={key}
                data-testid={`vencimiento-item-${type}-${productId}`}
                data-financial-risk={valorRiesgo > 0 ? convertAndFormat(valorRiesgo) : undefined}
                className="flex flex-col p-3 bg-secondary/30 rounded-xl hover:bg-secondary/50 transition-colors border border-border/40"
              >
                <div className="flex justify-between items-start mb-1 gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span
                      className="text-xs font-bold truncate max-w-[160px] sm:max-w-[200px] text-foreground"
                      title={productName}
                    >
                      {productName}
                    </span>
                    {loteCodigo && (
                      <span className="text-[10px] text-muted-foreground font-mono">
                        ({loteCodigo})
                      </span>
                    )}
                  </div>
                  <span
                    className={cn(
                      "text-[11px] font-black shrink-0",
                      isExpired ? "text-destructive" : "text-amber-600"
                    )}
                  >
                    {formattedDate}
                  </span>
                </div>

                <div className="flex justify-between items-center text-[10px] mt-1">
                  <BodegaBadge
                    nombre={bodegaNombre}
                    color={bodegaColor}
                    icono={bodegaIcono}
                    className="scale-75 origin-left"
                  />
                  {relativeDistance && (
                    <span className="italic text-muted-foreground">
                      {relativeDistance}
                    </span>
                  )}
                </div>

                {/* Badge de cantidad afectada y botón de acción */}
                <div className="mt-2.5 flex items-center justify-between">
                  <div className="text-[10px] bg-background/60 self-start px-2 py-0.5 rounded-lg border border-border/60">
                    {isExpired ? t("cards.affected_stock_label") : t("cards.risk_stock_label")}{" "}
                    <span className="font-black text-foreground">
                      {cantidad} {unidad}
                    </span>
                  </div>

                  <button
                    type="button"
                    data-testid={`btn-action-vencimiento-${type}-${productId}`}
                    onClick={() => handleActionClick(p)}
                    title={isExpired ? t("cards.report_merma") : t("cards.manage")}
                    aria-label={
                      isExpired
                        ? t("cards.report_merma_for", { name: productName })
                        : t("cards.manage_for", { name: productName })
                    }
                    className={cn(
                      "h-6 w-6 rounded-lg inline-flex items-center justify-center transition-all",
                      isExpired
                        ? "hover:bg-red-500/10 hover:text-destructive text-muted-foreground"
                        : "hover:bg-amber-500/10 hover:text-amber-600 text-muted-foreground"
                    )}
                  >
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Banner de recomendación operativa en vencidos */}
      {isExpired && data.length > 0 && (
        <div
          data-testid="banner-recomendacion-merma"
          className="mt-4 text-[10px] text-destructive font-medium bg-red-500/10 border border-red-500/20 p-2.5 rounded-xl flex items-center gap-2"
        >
          <span>⚠️</span>
          <span>{t("cards.merma_recommendation")}</span>
        </div>
      )}
    </div>
  );
}

export default VencimientosCard;
