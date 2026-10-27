import { Eye, Pencil, Copy, Trash2, Sparkles, ScrollText, CookingPot } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import type { Receta } from "../../types";

export interface RecetasTableProps {
  recetas: Receta[];
  onView?: (receta: Receta) => void;
  onEdit?: (receta: Receta) => void;
  onDuplicate?: (receta: Receta) => void;
  onDelete?: (receta: Receta) => void;
}

export function getMargenBadge(margenPct: number | undefined | null) {
  if (margenPct === undefined || margenPct === null || isNaN(margenPct)) {
    return {
      label: "—",
      className: "bg-muted text-muted-foreground border-border",
      level: "neutral" as const,
    };
  }
  const formatted = `${margenPct.toFixed(1)}%`;
  if (margenPct >= 65) {
    return {
      label: formatted,
      className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
      level: "success" as const,
    };
  }
  if (margenPct >= 40) {
    return {
      label: formatted,
      className: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
      level: "warning" as const,
    };
  }
  return {
    label: formatted,
    className: "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30",
    level: "danger" as const,
  };
}

export function RecetasTable({
  recetas,
  onView,
  onEdit,
  onDuplicate,
  onDelete,
}: RecetasTableProps) {
  const { t } = useTranslation("recipes");
  const { convertAndFormat } = useCurrencyFormatter();

  return (
    <div
      data-testid="recetas-table-root"
      className="w-full overflow-hidden rounded-2xl border border-border bg-card shadow-sm"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-border/80 bg-muted/40 text-[11px] font-black uppercase tracking-wider text-muted-foreground">
              <th scope="col" className="py-3 px-4">
                {t("table.recipes.col_recipe")}
              </th>
              <th scope="col" className="py-3 px-3 text-center">
                {t("table.recipes.col_type")}
              </th>
              <th scope="col" className="py-3 px-3 text-center">
                {t("table.recipes.col_yield")}
              </th>
              <th scope="col" className="py-3 px-3">
                {t("table.recipes.col_inputs")}
              </th>
              <th scope="col" className="py-3 px-3 text-right">
                {t("table.recipes.col_cost_ppp")}
              </th>
              <th scope="col" className="py-3 px-3 text-right">
                {t("table.recipes.col_sale_price")}
              </th>
              <th scope="col" className="py-3 px-3 text-center">
                {t("table.recipes.col_margin")}
              </th>
              <th scope="col" className="py-3 px-4 text-right">
                {t("table.recipes.col_actions")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {recetas.map((receta) => {
              const numFijos = receta.ingredientes_fijos?.length ?? 0;
              const numGrupos = receta.grupos_opciones?.length ?? 0;
              const porciones = receta.porciones_rendimiento || receta.porciones || 1;
              const costoTotal = receta.costo_total_calculado ?? receta.costo_total ?? 0;
              const costoPorcion =
                receta.costo_porcion ?? (porciones > 0 ? costoTotal / porciones : costoTotal);
              const precioNeto = receta.precio_venta_neto ?? receta.precio_neto ?? 0;
              const precioBruto =
                receta.precio_venta_bruto ?? receta.precio_bruto ?? receta.precio ?? 0;
              const margenBadge = getMargenBadge(receta.margen_pct);

              return (
                <tr
                  key={receta.id}
                  data-testid={`receta-row-${receta.id}`}
                  className="hover:bg-muted/30 transition-colors group"
                >
                  {/* 1. Receta & Código */}
                  <td className="py-3.5 px-4">
                    <div className="flex flex-col gap-1 min-w-[180px]">
                      <div className="flex items-center gap-2">
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
                      <span className="font-bold text-foreground text-sm group-hover:text-primary transition-colors">
                        {receta.nombre}
                      </span>
                      {receta.descripcion && (
                        <p className="text-[11px] text-muted-foreground line-clamp-1 max-w-xs">
                          {receta.descripcion}
                        </p>
                      )}
                    </div>
                  </td>

                  {/* 2. Badge Tipo */}
                  <td className="py-3.5 px-3 text-center whitespace-nowrap">
                    {receta.es_subreceta ? (
                      <span
                        data-testid="badge-subreceta"
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-sky-500/15 text-sky-700 dark:text-sky-300 border border-sky-500/30"
                      >
                        <CookingPot className="h-3 w-3" />
                        <span>{t("badges.subrecipe")}</span>
                      </span>
                    ) : receta.es_dinamica ? (
                      <span
                        data-testid="badge-dinamica"
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-purple-500/15 text-purple-700 dark:text-purple-300 border border-purple-500/30"
                      >
                        <Sparkles className="h-3 w-3" />
                        <span>{t("badges.dynamic")}</span>
                      </span>
                    ) : (
                      <span
                        data-testid="badge-fija"
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-slate-500/15 text-slate-700 dark:text-slate-300 border border-slate-500/30"
                      >
                        <ScrollText className="h-3 w-3" />
                        <span>{t("badges.static")}</span>
                      </span>
                    )}
                  </td>

                  {/* 3. Rendimiento en Porciones */}
                  <td className="py-3.5 px-3 text-center whitespace-nowrap">
                    <span className="font-semibold text-foreground">
                      {porciones === 1
                        ? t("badges.portions_count", { count: porciones })
                        : t("badges.portions_count_plural", { count: porciones })}
                    </span>
                  </td>

                  {/* 4. Estructura de Insumos */}
                  <td className="py-3.5 px-3 whitespace-nowrap">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-muted text-foreground border border-border/60">
                        {t("badges.fixed_count", { count: numFijos })}
                      </span>
                      {receta.es_dinamica && (
                        <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                          {t("badges.dynamic_count", { count: numGrupos })}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* 5. Costo Escandallo (PPP) */}
                  <td className="py-3.5 px-3 text-right whitespace-nowrap">
                    <div className="flex flex-col items-end">
                      <span className="font-extrabold text-foreground">
                        {convertAndFormat(costoPorcion)} {t("table.recipes.per_portion_suffix")}
                      </span>
                      <span className="text-[10px] text-muted-foreground font-medium">
                        {t("table.recipes.total_prefix")} {convertAndFormat(costoTotal)}
                      </span>
                      {receta.es_dinamica && receta.costo_peor_caso && receta.costo_peor_caso > costoTotal && (
                        <span className="text-[10px] text-amber-600 dark:text-amber-400 font-bold">
                          {t("table.recipes.max_prefix")} {convertAndFormat(receta.costo_peor_caso)}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* 6. Precio de Venta */}
                  <td className="py-3.5 px-3 text-right whitespace-nowrap">
                    <div className="flex flex-col items-end">
                      <span className="font-extrabold text-foreground">
                        {convertAndFormat(precioBruto)}
                      </span>
                      <span className="text-[10px] text-muted-foreground font-medium">
                        {t("table.recipes.net_prefix")} {convertAndFormat(precioNeto)}
                      </span>
                    </div>
                  </td>

                  {/* 7. Semáforo de Margen % */}
                  <td className="py-3.5 px-3 text-center whitespace-nowrap">
                    <span
                      data-testid={`margen-badge-${receta.id}`}
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
                          data-testid={`btn-view-receta-${receta.id}`}
                          onClick={() => onView(receta)}
                          aria-label={t("table.recipes.action_view_aria", { name: receta.nombre })}
                          title={t("table.recipes.action_view_title")}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors cursor-pointer min-h-[36px] min-w-[36px] flex items-center justify-center"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      )}
                      {onEdit && (
                        <button
                          type="button"
                          data-testid={`btn-edit-receta-${receta.id}`}
                          onClick={() => onEdit(receta)}
                          aria-label={t("table.recipes.action_edit_aria", { name: receta.nombre })}
                          title={t("table.recipes.action_edit_title")}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors cursor-pointer min-h-[36px] min-w-[36px] flex items-center justify-center"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                      )}
                      {onDuplicate && (
                        <button
                          type="button"
                          data-testid={`btn-duplicate-receta-${receta.id}`}
                          onClick={() => onDuplicate(receta)}
                          aria-label={t("table.recipes.action_duplicate_aria", { name: receta.nombre })}
                          title={t("table.recipes.action_duplicate_title")}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors cursor-pointer min-h-[36px] min-w-[36px] flex items-center justify-center"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                      )}
                      {onDelete && (
                        <button
                          type="button"
                          data-testid={`btn-delete-receta-${receta.id}`}
                          onClick={() => onDelete(receta)}
                          aria-label={t("table.recipes.action_delete_aria", { name: receta.nombre })}
                          title={t("table.recipes.action_delete_title")}
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

export default RecetasTable;
