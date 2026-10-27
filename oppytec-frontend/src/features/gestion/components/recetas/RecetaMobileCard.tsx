import { useState } from "react";
import { ChevronDown, ChevronUp, Eye, Pencil, Copy, Trash2, Sparkles, ScrollText, CookingPot } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import { getMargenBadge } from "./RecetasTable";
import type { Receta } from "../../types";

export interface RecetaMobileCardProps {
  receta: Receta;
  onView?: (receta: Receta) => void;
  onEdit?: (receta: Receta) => void;
  onDuplicate?: (receta: Receta) => void;
  onDelete?: (receta: Receta) => void;
}

export function RecetaMobileCard({
  receta,
  onView,
  onEdit,
  onDuplicate,
  onDelete,
}: RecetaMobileCardProps) {
  const { t } = useTranslation("recipes");
  const { convertAndFormat } = useCurrencyFormatter();
  const [isExpanded, setIsExpanded] = useState(false);

  const numFijos = receta.ingredientes_fijos?.length ?? 0;
  const numGrupos = receta.grupos_opciones?.length ?? 0;
  const porciones = receta.porciones_rendimiento || receta.porciones || 1;
  const costoTotal = receta.costo_total_calculado ?? receta.costo_total ?? 0;
  const costoPorcion =
    receta.costo_porcion ?? (porciones > 0 ? costoTotal / porciones : costoTotal);
  const precioNeto = receta.precio_venta_neto ?? receta.precio_neto ?? 0;
  const precioBruto = receta.precio_venta_bruto ?? receta.precio_bruto ?? receta.precio ?? 0;
  const margenBadge = getMargenBadge(receta.margen_pct);

  return (
    <article
      data-testid={`receta-card-${receta.id}`}
      className="bg-card border border-border/80 rounded-2xl p-4 shadow-sm space-y-3 transition-all"
    >
      {/* Header: Title, Code, Badges */}
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1 min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            {receta.codigo && (
              <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border/60">
                {receta.codigo}
              </span>
            )}
            {receta.categoria_nombre && (
              <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground">
                {receta.categoria_nombre}
              </span>
            )}
          </div>
          <h4 className="font-extrabold text-foreground text-base leading-tight truncate">
            {receta.nombre}
          </h4>
        </div>

        {/* Dynamic / Static Badge */}
        <div className="shrink-0">
          {receta.es_subreceta ? (
            <span
              data-testid="card-badge-subreceta"
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-sky-500/15 text-sky-700 dark:text-sky-300 border border-sky-500/30"
            >
              <CookingPot className="h-3 w-3" />
              <span>{t("badges.subrecipe")}</span>
            </span>
          ) : receta.es_dinamica ? (
            <span
              data-testid="card-badge-dinamica"
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-purple-500/15 text-purple-700 dark:text-purple-300 border border-purple-500/30"
            >
              <Sparkles className="h-3 w-3" />
              <span>{t("badges.dynamic")}</span>
            </span>
          ) : (
            <span
              data-testid="card-badge-fija"
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-slate-500/15 text-slate-700 dark:text-slate-300 border border-slate-500/30"
            >
              <ScrollText className="h-3 w-3" />
              <span>{t("badges.static")}</span>
            </span>
          )}
        </div>
      </div>

      {/* Metrics Row: Rendimiento, Insumos, Margen */}
      <div className="grid grid-cols-3 gap-2 p-2.5 rounded-xl bg-muted/40 border border-border/50 text-center">
        <div>
          <span className="text-[10px] uppercase font-bold text-muted-foreground block">
            {t("mobile_card.yield_label")}
          </span>
          <span className="text-xs font-black text-foreground">
            {porciones === 1
              ? t("badges.portions_short", { count: porciones })
              : t("badges.portions_short_plural", { count: porciones })}
          </span>
        </div>
        <div>
          <span className="text-[10px] uppercase font-bold text-muted-foreground block">
            {t("mobile_card.structure_label")}
          </span>
          <span className="text-xs font-black text-foreground">
            {receta.es_dinamica
              ? t("badges.fixed_dynamic_short", { fixed: numFijos, dynamic: numGrupos })
              : t("badges.fixed_only_short", { fixed: numFijos })}
          </span>
        </div>
        <div>
          <span className="text-[10px] uppercase font-bold text-muted-foreground block">
            {t("mobile_card.margin_label")}
          </span>
          <span
            data-testid={`card-margen-badge-${receta.id}`}
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-black border",
              margenBadge.className
            )}
          >
            {margenBadge.label}
          </span>
        </div>
      </div>

      {/* Financials: Cost vs Selling Price */}
      <div className="flex items-center justify-between text-xs px-1">
        <div>
          <span className="text-[10px] text-muted-foreground font-bold uppercase block">
            {t("mobile_card.cost_ppp_label")}
          </span>
          <span className="font-extrabold text-foreground text-sm">
            {convertAndFormat(costoPorcion)}
          </span>
          <span className="text-[10px] text-muted-foreground block">
            {t("table.recipes.total_prefix")} {convertAndFormat(costoTotal)}
          </span>
        </div>
        <div className="text-right">
          <span className="text-[10px] text-muted-foreground font-bold uppercase block">
            {t("mobile_card.sale_price_label")}
          </span>
          <span className="font-extrabold text-foreground text-sm">
            {convertAndFormat(precioBruto)}
          </span>
          <span className="text-[10px] text-muted-foreground block">
            {t("table.recipes.net_prefix")} {convertAndFormat(precioNeto)}
          </span>
        </div>
      </div>

      {/* Interactive Expandable Section for Recipe Details */}
      <div>
        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          data-testid={`btn-toggle-expand-${receta.id}`}
          className="w-full min-h-[44px] flex items-center justify-between px-3 py-2 rounded-xl bg-secondary/40 hover:bg-secondary/70 text-xs font-bold text-foreground transition-colors cursor-pointer select-none"
        >
          <span>
            {isExpanded
              ? t("mobile_card.hide_breakdown")
              : t("mobile_card.show_recipe_breakdown")}
          </span>
          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        {isExpanded && (
          <div className="mt-2.5 p-3 rounded-xl bg-muted/30 border border-border/60 space-y-2 text-xs animate-fade-in">
            {/* Fixed Ingredients */}
            <div>
              <span className="text-[10px] font-black uppercase tracking-wider text-muted-foreground block mb-1">
                {t("mobile_card.fixed_ingredients_header", { count: numFijos })}
              </span>
              {numFijos > 0 ? (
                <ul className="space-y-1">
                  {receta.ingredientes_fijos?.map((ing) => (
                    <li
                      key={ing.id || ing.producto_id}
                      className="flex items-center justify-between text-xs py-0.5 border-b border-border/40 last:border-none"
                    >
                      <span className="font-medium text-foreground">{ing.nombre}</span>
                      <span className="text-muted-foreground font-mono">
                        {ing.cantidad_receta} {ing.unidad}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground italic text-[11px]">
                  {t("mobile_card.empty_fixed_ingredients")}
                </p>
              )}
            </div>

            {/* Dynamic Options */}
            {receta.es_dinamica && (
              <div className="pt-2 border-t border-border/60">
                <span className="text-[10px] font-black uppercase tracking-wider text-purple-600 dark:text-purple-400 block mb-1">
                  {t("mobile_card.option_groups_header", { count: numGrupos })}
                </span>
                <p className="text-[11px] text-muted-foreground">
                  {t("mobile_card.option_groups_count", { count: numGrupos })}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Touch Action Bar (min-h-[44px] touch targets) */}
      <div className="pt-2 border-t border-border/60 flex items-center justify-end gap-1.5">
        {onView && (
          <button
            type="button"
            data-testid={`card-btn-view-${receta.id}`}
            onClick={() => onView(receta)}
            aria-label={t("table.recipes.action_view_aria", { name: receta.nombre })}
            className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-foreground flex items-center justify-center transition-colors cursor-pointer"
          >
            <Eye className="h-4 w-4" />
          </button>
        )}
        {onEdit && (
          <button
            type="button"
            data-testid={`card-btn-edit-${receta.id}`}
            onClick={() => onEdit(receta)}
            aria-label={t("table.recipes.action_edit_aria", { name: receta.nombre })}
            className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-foreground flex items-center justify-center transition-colors cursor-pointer"
          >
            <Pencil className="h-4 w-4" />
          </button>
        )}
        {onDuplicate && (
          <button
            type="button"
            data-testid={`card-btn-duplicate-${receta.id}`}
            onClick={() => onDuplicate(receta)}
            aria-label={t("table.recipes.action_duplicate_aria", { name: receta.nombre })}
            className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-foreground flex items-center justify-center transition-colors cursor-pointer"
          >
            <Copy className="h-4 w-4" />
          </button>
        )}
        {onDelete && (
          <button
            type="button"
            data-testid={`card-btn-delete-${receta.id}`}
            onClick={() => onDelete(receta)}
            aria-label={t("table.recipes.action_delete_aria", { name: receta.nombre })}
            className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-center transition-colors cursor-pointer"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </article>
  );
}

export default RecetaMobileCard;
