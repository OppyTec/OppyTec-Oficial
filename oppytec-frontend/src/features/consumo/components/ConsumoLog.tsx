// oppytec-frontend/src/features/consumo/components/ConsumoLog.tsx
import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  History,
  Calendar,
  X,
  Search,
  Download,
  Edit2,
  Trash2,
  CookingPot,
  Package,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/shared/lib/utils";
import { useCurrencyFormatter } from "@/shared/currency";
import type { ConsumptionRecord } from "../types";

export interface ConsumoLogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly records: ConsumptionRecord[];
  readonly onRefresh?: () => void;
  readonly onEdit?: (record: ConsumptionRecord) => void;
  readonly onDelete?: (record: ConsumptionRecord) => void;
  readonly logDate: Date;
  readonly setLogDate: (date: Date) => void;
  readonly logEndDate?: Date;
  readonly setLogEndDate?: (date: Date) => void;
  readonly isRangeMode?: boolean;
  readonly setIsRangeMode?: (val: boolean) => void;
}

export function ConsumoLog({
  open,
  onOpenChange,
  records,
  onRefresh: _onRefresh,
  onEdit,
  onDelete,
  logDate,
  setLogDate,
  logEndDate,
  setLogEndDate,
  isRangeMode = false,
  setIsRangeMode,
}: ConsumoLogProps) {
  const { t } = useTranslation("operations");
  const { format } = useCurrencyFormatter();
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedRecipes, setExpandedRecipes] = useState<Record<string, boolean>>({});

  const dateToStr = (d: Date): string => d.toISOString().split("T")[0] || "";

  const filteredRecords = useMemo(() => {
    const selectedDateStr = dateToStr(logDate);
    const selectedEndDateStr = logEndDate ? dateToStr(logEndDate) : selectedDateStr;

    return records.filter((r) => {
      const recDate = r.created_at ? r.created_at.split("T")[0] || "" : "";
      const matchesDate = isRangeMode
        ? recDate >= selectedDateStr && recDate <= selectedEndDateStr
        : recDate === selectedDateStr;

      if (!matchesDate && records.length > 0) {
        return true;
      }

      if (searchTerm.trim() === "") return true;
      const lower = searchTerm.toLowerCase();
      const prodName = (r.nombre_producto || "").toLowerCase();
      const recName = (r.nombre_receta || "").toLowerCase();
      const folio = (r.codigo_folio || "").toLowerCase();
      const user = (r.usuario_nombre || r.user_display_name || "").toLowerCase();

      return (
        prodName.includes(lower) ||
        recName.includes(lower) ||
        folio.includes(lower) ||
        user.includes(lower)
      );
    });
  }, [records, logDate, logEndDate, isRangeMode, searchTerm]);

  // Agrupamiento por receta_consumo_id si aplica
  const { groupedList, recipeChildren } = useMemo(() => {
    const groups: Record<string, ConsumptionRecord[]> = {};
    const standalone: ConsumptionRecord[] = [];

    filteredRecords.forEach((r) => {
      const gId = r.receta_consumo_id;
      if (gId) {
        if (!groups[gId]) {
          groups[gId] = [];
        }
        groups[gId]?.push(r);
      } else {
        standalone.push(r);
      }
    });

    const parents: ConsumptionRecord[] = [];
    const seen = new Set<string>();

    filteredRecords.forEach((r) => {
      const gId = r.receta_consumo_id;
      if (gId) {
        if (!seen.has(gId)) {
          seen.add(gId);
          parents.push(r);
        }
      }
    });

    return {
      groupedList: [...parents, ...standalone],
      recipeChildren: groups,
    };
  }, [filteredRecords]);

  if (!open) return null;

  const toggleRecipeExpand = (recipeGroupId: string) => {
    setExpandedRecipes((prev) => ({
      ...prev,
      [recipeGroupId]: !prev[recipeGroupId],
    }));
  };

  const exportCsv = () => {
    const headers = [
      "ID",
      "Folio",
      "Fecha",
      "Tipo",
      "Item",
      "Cantidad",
      "Unidad",
      "Costo Total",
      "Usuario",
      "Motivo",
    ];
    const rows = filteredRecords.map((r) => [
      r.id,
      r.codigo_folio || "",
      r.created_at || "",
      r.tipo_movimiento || r.tipo_origen || "CONSUMO",
      r.nombre_producto || r.nombre_receta || "",
      r.cantidad || 0,
      r.unidad_medida || "und",
      r.costo_total || 0,
      r.usuario_nombre || r.user_display_name || "",
      r.motivo_merma || r.notas || "",
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `historial_consumo_${dateToStr(logDate)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="consumo-log-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div className="w-full max-w-4xl rounded-3xl bg-card border border-border shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Cabecera */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-2xl bg-[#06b6d4]/15 text-[#06b6d4] border border-[#06b6d4]/30 flex items-center justify-center shadow-sm">
              <History className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-black uppercase tracking-wider text-foreground">
                {t("consumption.modals.log.title", { defaultValue: "Historial de Consumo y Kardex" })}
              </h3>
              <p className="text-xs text-muted-foreground">
                Trazabilidad inmutable de salidas, consumos de personal y mermas
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              data-testid="log-export-btn"
              onClick={exportCsv}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border bg-background hover:bg-muted text-xs font-bold text-foreground transition-colors cursor-pointer"
              title="Exportar CSV"
            >
              <Download className="h-4 w-4 text-primary" />
              <span className="hidden sm:inline">Exportar</span>
            </button>

            <button
              type="button"
              data-testid="log-close-btn"
              onClick={() => onOpenChange(false)}
              className="p-1.5 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Barra de Filtros (Fecha y Búsqueda) */}
        <div className="p-3 border-b border-border bg-muted/10 flex flex-wrap items-center justify-between gap-3 shrink-0">
          {/* Controles de Fecha */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 bg-background border border-border rounded-xl px-2.5 py-1">
              <Calendar className="h-4 w-4 text-muted-foreground shrink-0" />
              <input
                type="date"
                data-testid="log-date-input"
                value={dateToStr(logDate)}
                onChange={(e) => {
                  if (e.target.value) setLogDate(new Date(e.target.value));
                }}
                className="text-xs font-bold bg-transparent border-none text-foreground focus:outline-none"
              />
            </div>

            {isRangeMode && setLogEndDate && logEndDate && (
              <div className="flex items-center gap-1.5 bg-background border border-border rounded-xl px-2.5 py-1">
                <span className="text-xs text-muted-foreground">hasta</span>
                <input
                  type="date"
                  data-testid="log-end-date-input"
                  value={dateToStr(logEndDate)}
                  onChange={(e) => {
                    if (e.target.value) setLogEndDate(new Date(e.target.value));
                  }}
                  className="text-xs font-bold bg-transparent border-none text-foreground focus:outline-none"
                />
              </div>
            )}

            {setIsRangeMode && (
              <button
                type="button"
                data-testid="log-range-toggle"
                onClick={() => setIsRangeMode(!isRangeMode)}
                className={cn(
                  "px-2.5 py-1 rounded-xl text-xs font-bold border transition-colors cursor-pointer",
                  isRangeMode
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background border-border text-muted-foreground hover:text-foreground"
                )}
              >
                Rango
              </button>
            )}
          </div>

          {/* Buscador Rápido */}
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              data-testid="log-search-input"
              placeholder="Buscar por ítem, folio u operario..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-8 pl-8 pr-3 rounded-xl border border-border bg-background text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {/* Tabla / Lista de Registros */}
        <div
          data-testid="log-records-list"
          className="flex-1 overflow-y-auto p-4 space-y-2.5 custom-scrollbar"
        >
          {groupedList.length === 0 ? (
            <div className="text-center py-16 space-y-2 text-muted-foreground">
              <History className="h-10 w-10 mx-auto opacity-40" />
              <p className="text-xs font-bold uppercase tracking-wider">
                No hay movimientos de consumo registrados para esta fecha
              </p>
            </div>
          ) : (
            groupedList.map((record) => {
              const rGroupId = record.receta_consumo_id;
              const hasIngredients =
                Boolean(rGroupId) &&
                Boolean(recipeChildren[rGroupId || ""] && (recipeChildren[rGroupId || ""]?.length ?? 0) > 0);
              const isExpanded =
                Boolean(rGroupId) &&
                Boolean(expandedRecipes[rGroupId || ""]);

              const itemName =
                record.nombre_receta ||
                record.nombre_producto ||
                `Registro #${record.id}`;

              return (
                <div
                  key={record.id}
                  data-testid={`log-record-item-${record.id}`}
                  className="rounded-2xl border border-border bg-card p-3.5 shadow-sm space-y-2 hover:border-border/80 transition-all"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    {/* Izquierda: Icono + Detalle */}
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          "h-9 w-9 rounded-xl flex items-center justify-center shrink-0 border",
                          record.nombre_receta
                            ? "bg-purple-600/15 text-purple-600 border-purple-600/30"
                            : "bg-yellow-500/15 text-yellow-500 border-yellow-500/30"
                        )}
                      >
                        {record.nombre_receta ? (
                          <CookingPot className="h-4 w-4" />
                        ) : (
                          <Package className="h-4 w-4" />
                        )}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-black uppercase text-foreground">
                            {itemName}
                          </p>
                          {record.codigo_folio && (
                            <span className="text-[10px] font-bold text-muted-foreground bg-muted px-2 py-0.5 rounded-md">
                              {record.codigo_folio}
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-muted-foreground mt-0.5">
                          <span>
                            {new Date(record.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                          <span>· Cant: {record.cantidad} {record.unidad_medida || "und"}</span>
                          {record.costo_total ? (
                            <span>· {format(record.costo_total)}</span>
                          ) : null}
                          {(record.usuario_nombre || record.user_display_name) && (
                            <span>· Por: {record.usuario_nombre || record.user_display_name}</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Derecha: Botones de Acción */}
                    <div className="flex items-center gap-1.5 self-end sm:self-center">
                      {hasIngredients && rGroupId && (
                        <button
                          type="button"
                          onClick={() => toggleRecipeExpand(rGroupId)}
                          className="flex items-center gap-1 text-[10px] font-bold text-purple-600 hover:bg-purple-500/10 px-2 py-1 rounded-lg transition-colors cursor-pointer"
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-3 w-3" />
                          ) : (
                            <ChevronRight className="h-3 w-3" />
                          )}
                          <span>Insumos</span>
                        </button>
                      )}

                      {onEdit && (
                        <button
                          type="button"
                          data-testid={`log-edit-btn-${record.id}`}
                          onClick={() => onEdit(record)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                          title="Editar consumo"
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                        </button>
                      )}

                      {onDelete && (
                        <button
                          type="button"
                          data-testid={`log-delete-btn-${record.id}`}
                          onClick={() => onDelete(record)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors cursor-pointer"
                          title="Anular en Kardex"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Desglose de Insumos para Receta */}
                  {isExpanded && rGroupId && (
                    <div className="mt-2 pl-12 pr-2 py-2 border-t border-border/50 bg-muted/20 rounded-xl space-y-1">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Insumos deducidos del inventario:
                      </p>
                      {recipeChildren[rGroupId]?.map((child) => (
                        <div
                          key={child.id}
                          className="flex items-center justify-between text-xs text-muted-foreground py-0.5"
                        >
                          <span>{child.nombre_producto || child.producto_id}</span>
                          <span className="font-bold">
                            {child.cantidad} {child.unidad_medida || "und"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-muted/20 flex justify-between items-center shrink-0">
          <span className="text-xs font-bold text-muted-foreground">
            {filteredRecords.length} movimientos encontrados
          </span>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-bold uppercase tracking-wider hover:opacity-90 transition-opacity cursor-pointer"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConsumoLog;
