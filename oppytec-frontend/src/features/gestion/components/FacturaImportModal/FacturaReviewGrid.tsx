// oppytec-frontend/src/features/gestion/components/FacturaImportModal/FacturaReviewGrid.tsx
import React, { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Trash2, Search, Link2, Sparkles, Check } from "lucide-react";
import { cn } from "@/shared/lib/utils";
import { UnidadMedidaCombobox } from "./UnidadMedidaCombobox";
import type { Producto } from "../../types";

export interface FacturaParsedLine {
  readonly id: string;
  codigo: string;
  descripcion: string;
  cantidad: number;
  unidad: string;
  factor_conversion: number;
  precio_unitario: number;
  total_linea: number;
  producto_asociado_id: string; // id de producto o '__new__'
  bodega_id: string;
}

export interface FacturaReviewGridProps {
  readonly lines: readonly FacturaParsedLine[];
  readonly productos: readonly Producto[];
  readonly onUpdateLine: (id: string, field: keyof FacturaParsedLine, value: any) => void;
  readonly onDeleteLine: (id: string) => void;
  readonly className?: string;
}

export const FacturaReviewGrid: React.FC<FacturaReviewGridProps> = ({
  lines,
  productos,
  onUpdateLine,
  onDeleteLine,
  className,
}) => {
  const { t } = useTranslation(["factura_import"]);
  const [search, setSearch] = useState("");

  // Filter lines
  const filteredLines = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return lines;
    return lines.filter(
      (l) =>
        l.descripcion.toLowerCase().includes(q) ||
        l.codigo.toLowerCase().includes(q)
    );
  }, [lines, search]);

  // Total calculated
  const totalFacturaCalculado = useMemo(() => {
    return lines.reduce((acc, l) => acc + l.cantidad * l.precio_unitario, 0);
  }, [lines]);

  const newProductsCount = useMemo(() => {
    return lines.filter((l) => l.producto_asociado_id === "__new__" || !l.producto_asociado_id).length;
  }, [lines]);

  const matchedProductsCount = lines.length - newProductsCount;

  return (
    <div className={cn("space-y-3", className)} data-testid="factura-review-grid">
      {/* Search and Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 p-3 rounded-xl bg-secondary/30 border border-border">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder={t("review_grid.search_placeholder", "Buscar ítems en factura...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid="input-factura-search"
            className="w-full h-10 pl-9 pr-3 rounded-xl bg-background border border-input text-xs font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center gap-3 text-xs font-bold">
          <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
            <Check className="h-3.5 w-3.5" />
            {t("review_grid.matched_count", { count: matchedProductsCount, defaultValue: `${matchedProductsCount} Asociados al Catálogo` })}
          </span>
          <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-primary/10 text-primary border border-primary/30">
            <Sparkles className="h-3.5 w-3.5" />
            {t("review_grid.new_count", { count: newProductsCount, defaultValue: `${newProductsCount} Nuevos a Crear` })}
          </span>
        </div>
      </div>

      {/* Grid Table */}
      <div className="rounded-xl border border-border bg-card overflow-x-auto max-h-[380px] custom-scrollbar shadow-xs">
        <table className="w-full text-xs text-left border-collapse min-w-[950px]">
          <thead className="bg-secondary/50 text-muted-foreground font-black uppercase text-[10px] sticky top-0 z-10 border-b border-border">
            <tr>
              <th className="p-3 w-28">{t("review_grid.columns.code", "Código / SKU")}</th>
              <th className="p-3">{t("review_grid.columns.description", "Descripción Facturada")}</th>
              <th className="p-3 w-24 text-right">{t("review_grid.columns.quantity", "Cantidad")}</th>
              <th className="p-3 w-36">{t("review_grid.columns.unit", "Unidad")}</th>
              <th className="p-3 w-28 text-right">{t("review_grid.columns.price", "Precio Neto Unit.")}</th>
              <th className="p-3 w-28 text-right">{t("review_grid.columns.total", "Total Línea")}</th>
              <th className="p-3 w-64">{t("review_grid.columns.association", "Asociar a Producto Catálogo")}</th>
              <th className="p-3 w-12 text-center">{t("review_grid.columns.actions", "Acciones")}</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-border">
            {filteredLines.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-muted-foreground text-xs font-bold">
                  {t("review_grid.empty_state", "No se encontraron líneas en el documento.")}
                </td>
              </tr>
            ) : (
              filteredLines.map((line) => {
                const totalLineaCalc = Math.round(line.cantidad * line.precio_unitario);
                const isMatched = line.producto_asociado_id && line.producto_asociado_id !== "__new__";

                return (
                  <tr
                    key={line.id}
                    data-testid={`factura-line-row-${line.id}`}
                    className="hover:bg-secondary/15 transition-colors"
                  >
                    {/* Código */}
                    <td className="p-2">
                      <input
                        type="text"
                        value={line.codigo}
                        onChange={(e) => onUpdateLine(line.id, "codigo", e.target.value)}
                        data-testid={`input-line-code-${line.id}`}
                        className="w-full h-9 px-2 rounded-lg bg-background border border-input text-xs font-mono font-bold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </td>

                    {/* Descripción */}
                    <td className="p-2">
                      <input
                        type="text"
                        value={line.descripcion}
                        onChange={(e) => onUpdateLine(line.id, "descripcion", e.target.value)}
                        data-testid={`input-line-desc-${line.id}`}
                        className="w-full h-9 px-2.5 rounded-lg bg-background border border-input text-xs font-bold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </td>

                    {/* Cantidad */}
                    <td className="p-2 text-right">
                      <input
                        type="number"
                        min="0"
                        step="any"
                        value={line.cantidad}
                        onChange={(e) =>
                          onUpdateLine(line.id, "cantidad", Number(e.target.value) || 0)
                        }
                        data-testid={`input-line-qty-${line.id}`}
                        className="w-full h-9 px-2 rounded-lg bg-background border border-input text-xs font-mono font-bold text-right text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </td>

                    {/* Unidad y factor */}
                    <td className="p-2">
                      <UnidadMedidaCombobox
                        value={line.unidad}
                        factor={line.factor_conversion}
                        onChange={(unit, factor) => {
                          onUpdateLine(line.id, "unidad", unit);
                          onUpdateLine(line.id, "factor_conversion", factor);
                        }}
                      />
                    </td>

                    {/* Precio Unitario */}
                    <td className="p-2 text-right">
                      <input
                        type="number"
                        min="0"
                        value={line.precio_unitario}
                        onChange={(e) =>
                          onUpdateLine(line.id, "precio_unitario", Number(e.target.value) || 0)
                        }
                        data-testid={`input-line-price-${line.id}`}
                        className="w-full h-9 px-2 rounded-lg bg-background border border-input text-xs font-mono font-bold text-right text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </td>

                    {/* Total Línea */}
                    <td className="p-2 text-right font-mono font-black text-foreground">
                      ${totalLineaCalc.toLocaleString("es-CL")}
                    </td>

                    {/* Asociar a Producto Catálogo */}
                    <td className="p-2">
                      <div className="flex items-center gap-1.5">
                        <Link2
                          className={cn(
                            "h-4 w-4 shrink-0",
                            isMatched ? "text-emerald-600 dark:text-emerald-400" : "text-primary"
                          )}
                        />
                        <select
                          value={line.producto_asociado_id || "__new__"}
                          onChange={(e) =>
                            onUpdateLine(line.id, "producto_asociado_id", e.target.value)
                          }
                          data-testid={`select-product-match-${line.id}`}
                          className={cn(
                            "w-full h-9 px-2 rounded-lg border text-xs font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer truncate",
                            isMatched
                              ? "bg-emerald-500/10 border-emerald-500/30 font-bold"
                              : "bg-background border-input"
                          )}
                        >
                          <option value="__new__">{t("review_grid.new_product_option", "✨ + Crear como Nuevo Producto")}</option>
                          <optgroup label={t("review_grid.existing_products_group", "Productos Existentes en Catálogo")}>
                            {productos.map((prod) => (
                              <option key={prod.id} value={prod.id}>
                                {prod.nombre} (SKU: {prod.sku || "N/A"})
                              </option>
                            ))}
                          </optgroup>
                        </select>
                      </div>
                    </td>

                    {/* Eliminar Fila */}
                    <td className="p-2 text-center">
                      <button
                        type="button"
                        onClick={() => onDeleteLine(line.id)}
                        data-testid={`btn-delete-line-${line.id}`}
                        title={t("review_grid.delete_line_tooltip", "Quitar línea")}
                        className="touch-target inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Footer Total bar */}
      <div className="flex items-center justify-between p-3 rounded-xl bg-card border border-border text-xs">
        <span className="font-bold text-muted-foreground">
          {t("review_grid.total_calculated", { count: lines.length, defaultValue: `Total Líneas Calculado (${lines.length} ítems):` })}
        </span>
        <strong className="text-base font-black text-foreground font-mono">
          ${totalFacturaCalculado.toLocaleString("es-CL")} CLP
        </strong>
      </div>
    </div>
  );
};
