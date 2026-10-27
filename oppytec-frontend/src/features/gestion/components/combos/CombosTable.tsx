import { Eye, Pencil, Copy, Trash2, Sparkles, ScrollText, CheckCircle2, AlertCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import { getMargenBadge } from "../recetas/RecetasTable";
import type { Combo } from "../../types";

export interface CombosTableProps {
  combos: Combo[];
  onView?: (combo: Combo) => void;
  onEdit?: (combo: Combo) => void;
  onDuplicate?: (combo: Combo) => void;
  onDelete?: (combo: Combo) => void;
}

export function CombosTable({
  combos,
  onView,
  onEdit,
  onDuplicate,
  onDelete,
}: CombosTableProps) {
  const { t } = useTranslation("recipes");
  const { convertAndFormat } = useCurrencyFormatter();

  return (
    <div
      data-testid="combos-table-root"
      className="w-full overflow-hidden rounded-2xl border border-border bg-card shadow-sm"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-border/80 bg-muted/40 text-[11px] font-black uppercase tracking-wider text-muted-foreground">
              <th scope="col" className="py-3 px-4">
                {t("table.combos.col_combo")}
              </th>
              <th scope="col" className="py-3 px-3 text-center">
                {t("table.combos.col_type")}
              </th>
              <th scope="col" className="py-3 px-3 text-center">
                {t("table.combos.col_stock")}
              </th>
              <th scope="col" className="py-3 px-3">
                {t("table.combos.col_components")}
              </th>
              <th scope="col" className="py-3 px-3 text-right">
                {t("table.combos.col_base_cost")}
              </th>
              <th scope="col" className="py-3 px-3 text-right">
                {t("table.combos.col_sale_price")}
              </th>
              <th scope="col" className="py-3 px-3 text-center">
                {t("table.combos.col_margin")}
              </th>
              <th scope="col" className="py-3 px-4 text-right">
                {t("table.combos.col_actions")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {combos.map((combo) => {
              const numFijos = combo.items_fijos?.length ?? 0;
              const numGrupos = combo.grupos_opciones?.length ?? 0;
              const costoBase = combo.costo_base ?? combo.costo_total_calculado ?? combo.costo_total ?? 0;
              const precioNeto = combo.precio_venta_neto ?? combo.precio_neto ?? 0;
              const precioBruto = combo.precio_venta_bruto ?? combo.precio_bruto ?? combo.precio ?? 0;
              const stock = combo.disponibilidad_stock_porciones;
              const hasStock = stock !== undefined && stock !== null ? stock > 0 : combo.esta_disponible !== false;
              const margenBadge = getMargenBadge(combo.margen_pct);

              return (
                <tr
                  key={combo.id}
                  data-testid={`combo-row-${combo.id}`}
                  className="hover:bg-muted/30 transition-colors group"
                >
                  {/* 1. Combo & Código */}
                  <td className="py-3.5 px-4">
                    <div className="flex flex-col gap-1 min-w-[180px]">
                      <div className="flex items-center gap-2">
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
                      <span className="font-bold text-foreground text-sm group-hover:text-pink-600 transition-colors">
                        {combo.nombre}
                      </span>
                      {combo.descripcion && (
                        <p className="text-[11px] text-muted-foreground line-clamp-1 max-w-xs">
                          {combo.descripcion}
                        </p>
                      )}
                    </div>
                  </td>

                  {/* 2. Badge Tipo */}
                  <td className="py-3.5 px-3 text-center whitespace-nowrap">
                    {combo.es_dinamico ? (
                      <span
                        data-testid="badge-combo-dinamico"
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-purple-500/15 text-purple-700 dark:text-purple-300 border border-purple-500/30"
                      >
                        <Sparkles className="h-3 w-3" />
                        <span>{t("badges.dynamic_combo")}</span>
                      </span>
                    ) : (
                      <span
                        data-testid="badge-combo-fijo"
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-slate-500/15 text-slate-700 dark:text-slate-300 border border-slate-500/30"
                      >
                        <ScrollText className="h-3 w-3" />
                        <span>{t("badges.static_combo")}</span>
                      </span>
                    )}
                  </td>

                  {/* 3. Disponibilidad de Stock */}
                  <td className="py-3.5 px-3 text-center whitespace-nowrap">
                    <span
                      data-testid={`stock-badge-${combo.id}`}
                      className={cn(
                        "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-black border",
                        hasStock
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                          : "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30"
                      )}
                    >
                      {hasStock ? (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          <span>
                            {stock !== undefined && stock !== null
                              ? t("badges.available_count", { count: stock })
                              : t("badges.available")}
                          </span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="h-3.5 w-3.5" />
                          <span>{t("badges.out_of_stock")}</span>
                        </>
                      )}
                    </span>
                  </td>

                  {/* 4. Componentes */}
                  <td className="py-3.5 px-3 whitespace-nowrap">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-muted text-foreground border border-border/60">
                        {t("badges.fixed_count", { count: numFijos })}
                      </span>
                      {combo.es_dinamico && (
                        <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                          {t("badges.configurable_count", { count: numGrupos })}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* 5. Costo Base */}
                  <td className="py-3.5 px-3 text-right whitespace-nowrap">
                    <span className="font-extrabold text-foreground">
                      {convertAndFormat(costoBase)}
                    </span>
                  </td>

                  {/* 6. Precio de Venta */}
                  <td className="py-3.5 px-3 text-right whitespace-nowrap">
                    <div className="flex flex-col items-end">
                      <span className="font-extrabold text-foreground">
                        {convertAndFormat(precioBruto)}
                      </span>
                      <span className="text-[10px] text-muted-foreground font-medium">
                        {t("table.combos.net_prefix")} {convertAndFormat(precioNeto)}
                      </span>
                    </div>
                  </td>

                  {/* 7. Margen % */}
                  <td className="py-3.5 px-3 text-center whitespace-nowrap">
                    <span
                      data-testid={`margen-badge-${combo.id}`}
                      className={cn(
                        "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-black border",
                        margenBadge.className
                      )}
                    >
                      {margenBadge.label}
                    </span>
                  </td>

                  {/* 8. Acciones Rápidas */}
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <div className="inline-flex items-center justify-end gap-1">
                      {onView && (
                        <button
                          type="button"
                          data-testid={`btn-view-combo-${combo.id}`}
                          onClick={() => onView(combo)}
                          aria-label={t("table.combos.action_view_aria", { name: combo.nombre })}
                          title={t("table.combos.action_view_title")}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors cursor-pointer min-h-[36px] min-w-[36px] flex items-center justify-center"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      )}
                      {onEdit && (
                        <button
                          type="button"
                          data-testid={`btn-edit-combo-${combo.id}`}
                          onClick={() => onEdit(combo)}
                          aria-label={t("table.combos.action_edit_aria", { name: combo.nombre })}
                          title={t("table.combos.action_edit_title")}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors cursor-pointer min-h-[36px] min-w-[36px] flex items-center justify-center"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                      )}
                      {onDuplicate && (
                        <button
                          type="button"
                          data-testid={`btn-duplicate-combo-${combo.id}`}
                          onClick={() => onDuplicate(combo)}
                          aria-label={t("table.combos.action_duplicate_aria", { name: combo.nombre })}
                          title={t("table.combos.action_duplicate_title")}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors cursor-pointer min-h-[36px] min-w-[36px] flex items-center justify-center"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                      )}
                      {onDelete && (
                        <button
                          type="button"
                          data-testid={`btn-delete-combo-${combo.id}`}
                          onClick={() => onDelete(combo)}
                          aria-label={t("table.combos.action_delete_aria", { name: combo.nombre })}
                          title={t("table.combos.action_delete_title")}
                          className="p-1.5 rounded-lg text-rose-500 hover:text-rose-700 hover:bg-rose-500/10 transition-colors cursor-pointer min-h-[36px] min-w-[36px] flex items-center justify-center"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default CombosTable;
