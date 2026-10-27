import { useState } from "react";
import { ChevronDown, ChevronUp, Eye, Pencil, Copy, Trash2, Sparkles, ScrollText, CheckCircle2, AlertCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import { getMargenBadge } from "../recetas/RecetasTable";
import type { Combo } from "../../types";

export interface ComboMobileCardProps {
  combo: Combo;
  onView?: (combo: Combo) => void;
  onEdit?: (combo: Combo) => void;
  onDuplicate?: (combo: Combo) => void;
  onDelete?: (combo: Combo) => void;
}

export function ComboMobileCard({
  combo,
  onView,
  onEdit,
  onDuplicate,
  onDelete,
}: ComboMobileCardProps) {
  const { t } = useTranslation("recipes");
  const { convertAndFormat } = useCurrencyFormatter();
  const [isExpanded, setIsExpanded] = useState(false);

  const numFijos = combo.items_fijos?.length ?? 0;
  const numGrupos = combo.grupos_opciones?.length ?? 0;
  const costoBase = combo.costo_base ?? combo.costo_total_calculado ?? combo.costo_total ?? 0;
  const precioNeto = combo.precio_venta_neto ?? combo.precio_neto ?? 0;
  const precioBruto = combo.precio_venta_bruto ?? combo.precio_bruto ?? combo.precio ?? 0;
  const stock = combo.disponibilidad_stock_porciones;
  const hasStock = stock !== undefined && stock !== null ? stock > 0 : combo.esta_disponible !== false;
  const margenBadge = getMargenBadge(combo.margen_pct);

  return (
    <article
      data-testid={`combo-card-${combo.id}`}
      className="bg-card border border-border/80 rounded-2xl p-4 shadow-sm space-y-3 transition-all"
    >
      {/* Header: Title, Code, Badges */}
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1 min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            {combo.codigo && (
              <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border/60">
                {combo.codigo}
              </span>
            )}
            {combo.categoria_nombre && (
              <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-pink-500/10 text-pink-600 dark:text-pink-400">
                {combo.categoria_nombre}
              </span>
            )}
          </div>
          <h4 className="font-extrabold text-foreground text-base leading-tight truncate">
            {combo.nombre}
          </h4>
        </div>

        {/* Dynamic / Static Badge */}
        <div className="shrink-0">
          {combo.es_dinamico ? (
            <span
              data-testid="card-badge-combo-dinamico"
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-purple-500/15 text-purple-700 dark:text-purple-300 border border-purple-500/30"
            >
              <Sparkles className="h-3 w-3" />
              <span>{t("badges.dynamic_combo")}</span>
            </span>
          ) : (
            <span
              data-testid="card-badge-combo-fijo"
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-slate-500/15 text-slate-700 dark:text-slate-300 border border-slate-500/30"
            >
              <ScrollText className="h-3 w-3" />
              <span>{t("badges.static_combo")}</span>
            </span>
          )}
        </div>
      </div>

      {/* Metrics Row: Stock, Componentes, Margen */}
      <div className="grid grid-cols-3 gap-2 p-2.5 rounded-xl bg-muted/40 border border-border/50 text-center">
        <div>
          <span className="text-[10px] uppercase font-bold text-muted-foreground block">
            {t("mobile_card.stock_label")}
          </span>
          <span
            data-testid={`card-stock-badge-${combo.id}`}
            className={cn(
              "inline-flex items-center gap-0.5 text-xs font-black",
              hasStock ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
            )}
          >
            {hasStock ? (
              <>
                <CheckCircle2 className="h-3 w-3" />
                <span>
                  {stock !== undefined && stock !== null
                    ? t("badges.available_count_short", { count: stock })
                    : t("badges.available_short")}
                </span>
              </>
            ) : (
              <>
                <AlertCircle className="h-3 w-3" />
                <span>{t("badges.out_of_stock")}</span>
              </>
            )}
          </span>
        </div>
        <div>
          <span className="text-[10px] uppercase font-bold text-muted-foreground block">
            {t("mobile_card.components_label")}
          </span>
          <span className="text-xs font-black text-foreground">
            {combo.es_dinamico
              ? t("badges.fixed_dynamic_short", { fixed: numFijos, dynamic: numGrupos })
              : t("badges.fixed_only_short", { fixed: numFijos })}
          </span>
        </div>
        <div>
          <span className="text-[10px] uppercase font-bold text-muted-foreground block">
            {t("mobile_card.margin_label")}
          </span>
          <span
            data-testid={`card-margen-badge-${combo.id}`}
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
            {t("mobile_card.base_cost_label")}
          </span>
          <span className="font-extrabold text-foreground text-sm">
            {convertAndFormat(costoBase)}
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
            {t("table.combos.net_prefix")} {convertAndFormat(precioNeto)}
          </span>
        </div>
      </div>

      {/* Interactive Expandable Section for Combo Details */}
      <div>
        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          data-testid={`btn-toggle-expand-combo-${combo.id}`}
          className="w-full min-h-[44px] flex items-center justify-between px-3 py-2 rounded-xl bg-secondary/40 hover:bg-secondary/70 text-xs font-bold text-foreground transition-colors cursor-pointer select-none"
        >
          <span>
            {isExpanded
              ? t("mobile_card.hide_breakdown")
              : t("mobile_card.show_combo_breakdown")}
          </span>
          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        {isExpanded && (
          <div className="mt-2.5 p-3 rounded-xl bg-muted/30 border border-border/60 space-y-2 text-xs animate-fade-in">
            {/* Fixed Items */}
            <div>
              <span className="text-[10px] font-black uppercase tracking-wider text-muted-foreground block mb-1">
                {t("mobile_card.fixed_items_header", { count: numFijos })}
              </span>
              {numFijos > 0 ? (
                <ul className="space-y-1">
                  {combo.items_fijos?.map((it) => (
                    <li
                      key={it.id || it.producto_id || it.receta_id}
                      className="flex items-center justify-between text-xs py-0.5 border-b border-border/40 last:border-none"
                    >
                      <span className="font-medium text-foreground">{it.nombre}</span>
                      <span className="text-muted-foreground font-mono">x{it.cantidad}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground italic text-[11px]">
                  {t("mobile_card.empty_fixed_items")}
                </p>
              )}
            </div>

            {/* Dynamic Options */}
            {combo.es_dinamico && (
              <div className="pt-2 border-t border-border/60">
                <span className="text-[10px] font-black uppercase tracking-wider text-purple-600 dark:text-purple-400 block mb-1">
                  {t("mobile_card.configurable_groups_header", { count: numGrupos })}
                </span>
                <p className="text-[11px] text-muted-foreground">
                  {t("mobile_card.configurable_groups_count", { count: numGrupos })}
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
            data-testid={`card-btn-view-combo-${combo.id}`}
            onClick={() => onView(combo)}
            aria-label={t("mobile_card.action_view_combo_aria", { name: combo.nombre })}
            className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-foreground flex items-center justify-center transition-colors cursor-pointer"
          >
            <Eye className="h-4 w-4" />
          </button>
        )}
        {onEdit && (
          <button
            type="button"
            data-testid={`card-btn-edit-combo-${combo.id}`}
            onClick={() => onEdit(combo)}
            aria-label={t("table.combos.action_edit_aria", { name: combo.nombre })}
            className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-foreground flex items-center justify-center transition-colors cursor-pointer"
          >
            <Pencil className="h-4 w-4" />
          </button>
        )}
        {onDuplicate && (
          <button
            type="button"
            data-testid={`card-btn-duplicate-combo-${combo.id}`}
            onClick={() => onDuplicate(combo)}
            aria-label={t("table.combos.action_duplicate_aria", { name: combo.nombre })}
            className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-foreground flex items-center justify-center transition-colors cursor-pointer"
          >
            <Copy className="h-4 w-4" />
          </button>
        )}
        {onDelete && (
          <button
            type="button"
            data-testid={`card-btn-delete-combo-${combo.id}`}
            onClick={() => onDelete(combo)}
            aria-label={t("table.combos.action_delete_aria", { name: combo.nombre })}
            className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-center transition-colors cursor-pointer"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </article>
  );
}

export default ComboMobileCard;
