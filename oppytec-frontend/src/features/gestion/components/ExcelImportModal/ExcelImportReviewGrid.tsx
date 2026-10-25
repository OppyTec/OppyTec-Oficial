// oppytec-frontend/src/features/gestion/components/ExcelImportModal/ExcelImportReviewGrid.tsx
import React, { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Trash2,
  Search,
  DollarSign,
  Percent,
} from "lucide-react";
import { cn } from "@/shared/lib/utils";

export type RowStatus = "valid" | "warning" | "error";

export interface ParsedProductRow {
  readonly id: string;
  nombre: string;
  sku: string;
  codigo_barra: string;
  categoria: string;
  marca: string;
  unidad_base: string;
  tipo_envase: string;
  costo_neto: number;
  precio_venta_neto: number;
  stock_actual: number;
  stock_minimo: number;
  bodega: string;
  pasillo?: string;
  rack?: string;
}

export interface ExcelImportReviewGridProps {
  readonly rows: readonly ParsedProductRow[];
  readonly onUpdateRow: (id: string, field: keyof ParsedProductRow, value: any) => void;
  readonly onDeleteRow: (id: string) => void;
  readonly ivaPorcentaje?: number;
}

export function validateProductRow(row: ParsedProductRow): { status: RowStatus; message: string } {
  if (!row.nombre?.trim()) {
    return { status: "error", message: "El nombre es obligatorio" };
  }
  if (isNaN(row.costo_neto) || row.costo_neto < 0) {
    return { status: "error", message: "Costo unitario inválido o negativo" };
  }
  if (!row.categoria?.trim()) {
    return { status: "error", message: "La categoría es obligatoria" };
  }
  if (!row.sku?.trim()) {
    return { status: "warning", message: "Sin SKU (se autogenerará al guardar)" };
  }
  if (row.stock_actual === 0 || isNaN(row.stock_actual)) {
    return { status: "warning", message: "Stock inicial en cero" };
  }
  return { status: "valid", message: "Listo para importar" };
}

export const ExcelImportReviewGrid: React.FC<ExcelImportReviewGridProps> = ({
  rows,
  onUpdateRow,
  onDeleteRow,
  ivaPorcentaje = 19,
}) => {
  const { t } = useTranslation(["excel_import", "gestion"]);
  const [filterStatus, setFilterStatus] = useState<"all" | "valid" | "warning" | "error">("all");
  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState<"neto" | "bruto">("neto");

  const ivaMultiplier = 1 + ivaPorcentaje / 100;

  // Compute validations
  const rowValidations = useMemo(() => {
    const map = new Map<string, { status: RowStatus; message: string }>();
    rows.forEach((r) => map.set(r.id, validateProductRow(r)));
    return map;
  }, [rows]);

  // Counts
  const counts = useMemo(() => {
    let valid = 0;
    let warning = 0;
    let error = 0;
    rowValidations.forEach((v) => {
      if (v.status === "valid") valid++;
      else if (v.status === "warning") warning++;
      else if (v.status === "error") error++;
    });
    return { all: rows.length, valid, warning, error };
  }, [rows.length, rowValidations]);

  // Filtered rows
  const filteredRows = useMemo(() => {
    const q = search.toLowerCase().trim();
    return rows.filter((r) => {
      const v = rowValidations.get(r.id)?.status || "valid";
      if (filterStatus !== "all" && v !== filterStatus) return false;
      if (!q) return true;
      return (
        r.nombre.toLowerCase().includes(q) ||
        r.sku.toLowerCase().includes(q) ||
        r.categoria.toLowerCase().includes(q) ||
        r.marca.toLowerCase().includes(q)
      );
    });
  }, [rows, filterStatus, search, rowValidations]);

  return (
    <div className="space-y-3" data-testid="excel-import-review-grid">
      {/* Controls & Filter Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 p-3 rounded-xl bg-secondary/30 border border-border">
        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder={t("review_grid.search_placeholder", "Buscar en la grilla...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid="input-grid-search"
            className="w-full h-10 pl-9 pr-3 rounded-xl bg-background border border-input text-xs font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Status Filter Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <button
            type="button"
            onClick={() => setFilterStatus("all")}
            data-testid="filter-chip-all"
            className={cn(
              "touch-target inline-flex min-h-[40px] px-3 items-center gap-1 rounded-xl text-xs font-bold transition-all cursor-pointer select-none",
              filterStatus === "all"
                ? "bg-primary text-primary-foreground shadow-xs"
                : "bg-card border border-border text-muted-foreground hover:text-foreground"
            )}
          >
            <span>{t("review_grid.filter_all", "Todos")}</span>
            <span className="opacity-75">({counts.all})</span>
          </button>

          <button
            type="button"
            onClick={() => setFilterStatus("valid")}
            data-testid="filter-chip-valid"
            className={cn(
              "touch-target inline-flex min-h-[40px] px-3 items-center gap-1 rounded-xl text-xs font-bold transition-all cursor-pointer select-none",
              filterStatus === "valid"
                ? "bg-emerald-600 text-white shadow-xs"
                : "bg-card border border-border text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10"
            )}
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>{t("review_grid.filter_valid", "Válidos")}</span>
            <span>({counts.valid})</span>
          </button>

          <button
            type="button"
            onClick={() => setFilterStatus("warning")}
            data-testid="filter-chip-warning"
            className={cn(
              "touch-target inline-flex min-h-[40px] px-3 items-center gap-1 rounded-xl text-xs font-bold transition-all cursor-pointer select-none",
              filterStatus === "warning"
                ? "bg-amber-600 text-white shadow-xs"
                : "bg-card border border-border text-amber-600 dark:text-amber-400 hover:bg-amber-500/10"
            )}
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>{t("review_grid.filter_warning", "Alertas")}</span>
            <span>({counts.warning})</span>
          </button>

          {counts.error > 0 && (
            <button
              type="button"
              onClick={() => setFilterStatus("error")}
              data-testid="filter-chip-error"
              className={cn(
                "touch-target inline-flex min-h-[40px] px-3 items-center gap-1 rounded-xl text-xs font-bold transition-all cursor-pointer select-none",
                filterStatus === "error"
                  ? "bg-destructive text-destructive-foreground shadow-xs"
                  : "bg-card border border-border text-destructive hover:bg-destructive/10"
              )}
            >
              <XCircle className="h-3.5 w-3.5" />
              <span>{t("review_grid.filter_error", "Errores")}</span>
              <span>({counts.error})</span>
            </button>
          )}
        </div>

        {/* Switcher Neto / Bruto */}
        <div className="inline-flex p-1 rounded-xl bg-card border border-border shadow-xs shrink-0">
          <button
            type="button"
            onClick={() => setViewMode("neto")}
            data-testid="btn-grid-view-neto"
            className={cn(
              "touch-target inline-flex min-h-[38px] px-3 items-center gap-1.5 rounded-lg text-xs font-bold cursor-pointer select-none",
              viewMode === "neto"
                ? "bg-primary text-primary-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <DollarSign className="h-3.5 w-3.5" />
            <span>{t("review_grid.view_neto", "Neto")}</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode("bruto")}
            data-testid="btn-grid-view-bruto"
            className={cn(
              "touch-target inline-flex min-h-[38px] px-3 items-center gap-1.5 rounded-lg text-xs font-bold cursor-pointer select-none",
              viewMode === "bruto"
                ? "bg-primary text-primary-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Percent className="h-3.5 w-3.5" />
            <span>{t("review_grid.view_bruto", "Bruto (c/IVA)")}</span>
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="rounded-xl border border-border bg-card overflow-x-auto max-h-[420px] custom-scrollbar shadow-xs">
        <table className="w-full text-xs text-left border-collapse min-w-[900px]">
          <thead className="bg-secondary/50 text-muted-foreground font-black uppercase text-[10px] sticky top-0 z-10 border-b border-border">
            <tr>
              <th className="p-3 w-12 text-center">{t("review_grid.columns.status", "Estado")}</th>
              <th className="p-3">{t("review_grid.columns.nombre", "Nombre Comercial *")}</th>
              <th className="p-3 w-28">{t("review_grid.columns.sku", "SKU")}</th>
              <th className="p-3">{t("review_grid.columns.categoria", "Categoría *")}</th>
              <th className="p-3">{t("review_grid.columns.marca", "Marca")}</th>
              <th className="p-3 w-28 text-right">
                {viewMode === "neto"
                  ? t("review_grid.columns.costo_neto", "Costo Neto *")
                  : t("review_grid.columns.costo_bruto", "Costo Bruto *")}
              </th>
              <th className="p-3 w-28 text-right">
                {viewMode === "neto"
                  ? t("review_grid.columns.precio_neto", "Precio Neto")
                  : t("review_grid.columns.precio_bruto", "Precio Bruto")}
              </th>
              <th className="p-3 w-20 text-right">{t("review_grid.columns.stock", "Stock")}</th>
              <th className="p-3 w-12 text-center">{t("review_grid.columns.actions", "Acciones")}</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-border">
            {filteredRows.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-8 text-center text-muted-foreground text-xs font-bold">
                  {t("review_grid.empty_state", "No hay filas que coincidan con los filtros seleccionados.")}
                </td>
              </tr>
            ) : (
              filteredRows.map((row) => {
                const validation = rowValidations.get(row.id) || {
                  status: "valid",
                  message: "Válido",
                };

                const displayCosto =
                  viewMode === "neto"
                    ? row.costo_neto
                    : Math.round(row.costo_neto * ivaMultiplier);

                const displayPrecio =
                  viewMode === "neto"
                    ? row.precio_venta_neto
                    : Math.round(row.precio_venta_neto * ivaMultiplier);

                return (
                  <tr
                    key={row.id}
                    data-testid={`grid-row-${row.id}`}
                    className={cn(
                      "hover:bg-secondary/15 transition-colors",
                      validation.status === "error" && "bg-destructive/5",
                      validation.status === "warning" && "bg-amber-500/5"
                    )}
                  >
                    {/* Status Badge */}
                    <td className="p-2 text-center">
                      <span
                        title={validation.message}
                        data-testid={`row-status-${row.id}-${validation.status}`}
                        className="inline-flex items-center justify-center cursor-help"
                      >
                        {validation.status === "valid" && (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                        )}
                        {validation.status === "warning" && (
                          <AlertTriangle className="h-4 w-4 text-amber-500" />
                        )}
                        {validation.status === "error" && (
                          <XCircle className="h-4 w-4 text-destructive" />
                        )}
                      </span>
                    </td>

                    {/* Nombre */}
                    <td className="p-2">
                      <input
                        type="text"
                        value={row.nombre}
                        onChange={(e) => onUpdateRow(row.id, "nombre", e.target.value)}
                        data-testid={`input-grid-nombre-${row.id}`}
                        className={cn(
                          "w-full h-9 px-2.5 rounded-lg bg-background border text-xs font-bold text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
                          !row.nombre?.trim() ? "border-destructive bg-destructive/10" : "border-input"
                        )}
                      />
                    </td>

                    {/* SKU */}
                    <td className="p-2">
                      <input
                        type="text"
                        value={row.sku}
                        placeholder="AUTO"
                        onChange={(e) => onUpdateRow(row.id, "sku", e.target.value)}
                        data-testid={`input-grid-sku-${row.id}`}
                        className="w-full h-9 px-2.5 rounded-lg bg-background border border-input text-xs font-mono font-bold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </td>

                    {/* Categoría */}
                    <td className="p-2">
                      <input
                        type="text"
                        value={row.categoria}
                        onChange={(e) => onUpdateRow(row.id, "categoria", e.target.value)}
                        data-testid={`input-grid-categoria-${row.id}`}
                        className={cn(
                          "w-full h-9 px-2.5 rounded-lg bg-background border text-xs font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
                          !row.categoria?.trim() ? "border-destructive bg-destructive/10" : "border-input"
                        )}
                      />
                    </td>

                    {/* Marca */}
                    <td className="p-2">
                      <input
                        type="text"
                        value={row.marca}
                        placeholder="Genérica"
                        onChange={(e) => onUpdateRow(row.id, "marca", e.target.value)}
                        data-testid={`input-grid-marca-${row.id}`}
                        className="w-full h-9 px-2.5 rounded-lg bg-background border border-input text-xs font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </td>

                    {/* Costo */}
                    <td className="p-2 text-right">
                      <input
                        type="number"
                        min="0"
                        value={displayCosto || ""}
                        onChange={(e) => {
                          const val = Number(e.target.value) || 0;
                          const netoVal = viewMode === "neto" ? val : Math.round(val / ivaMultiplier);
                          onUpdateRow(row.id, "costo_neto", netoVal);
                        }}
                        data-testid={`input-grid-costo-${row.id}`}
                        className={cn(
                          "w-full h-9 px-2.5 rounded-lg bg-background border text-xs font-mono font-bold text-right text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
                          row.costo_neto < 0 ? "border-destructive bg-destructive/10" : "border-input"
                        )}
                      />
                    </td>

                    {/* Precio Venta */}
                    <td className="p-2 text-right">
                      <input
                        type="number"
                        min="0"
                        value={displayPrecio || ""}
                        onChange={(e) => {
                          const val = Number(e.target.value) || 0;
                          const netoVal = viewMode === "neto" ? val : Math.round(val / ivaMultiplier);
                          onUpdateRow(row.id, "precio_venta_neto", netoVal);
                        }}
                        data-testid={`input-grid-precio-${row.id}`}
                        className="w-full h-9 px-2.5 rounded-lg bg-background border border-input text-xs font-mono font-bold text-right text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </td>

                    {/* Stock Inicial */}
                    <td className="p-2 text-right">
                      <input
                        type="number"
                        min="0"
                        value={row.stock_actual ?? 0}
                        onChange={(e) =>
                          onUpdateRow(row.id, "stock_actual", Number(e.target.value) || 0)
                        }
                        data-testid={`input-grid-stock-${row.id}`}
                        className="w-full h-9 px-2 rounded-lg bg-background border border-input text-xs font-mono font-bold text-right text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </td>

                    {/* Eliminar Fila */}
                    <td className="p-2 text-center">
                      <button
                        type="button"
                        onClick={() => onDeleteRow(row.id)}
                        data-testid={`btn-delete-row-${row.id}`}
                        title={t("review_grid.delete_row_tooltip", "Quitar fila")}
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
    </div>
  );
};
