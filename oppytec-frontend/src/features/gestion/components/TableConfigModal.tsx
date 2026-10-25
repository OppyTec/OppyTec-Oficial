import { useState, useMemo, useEffect } from "react";
import {
  SlidersHorizontal,
  Search,
  Trash2,
  Bookmark,
  Check,
  Package,
  DollarSign,
  Tag,
  Clock,
  ArrowUp,
  ArrowDown,
  RotateCcw,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib/utils";
import { toast } from "sonner";
import {
  type ColumnKey,
  type ColumnOption,
  type SortOption,
  type TablePreset,
  type ViewMode,
  SYSTEM_PRESETS,
  ALL_COLUMNS,
} from "../types";

export interface TableConfigModalProps<
  TSortKey extends string = "nombre" | "stock" | "precio" | "vigencia",
  TColKey extends string = ColumnKey
> {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sortConfig: { key: TSortKey; direction: "asc" | "desc" };
  onSortChange: (config: { key: TSortKey; direction: "asc" | "desc" }) => void;
  sortOptions: SortOption<TSortKey>[];
  columns?: readonly ColumnOption<TColKey>[];
  visibleColsOrder: TColKey[];
  onSaveConfig: (params: {
    orderedColumns: TColKey[];
    sortConfig: { key: TSortKey; direction: "asc" | "desc" };
    viewMode: ViewMode;
    presetId?: string;
  }) => void;
  viewMode?: ViewMode;
  onResetView?: () => void;
}

const SECTION_ICONS: Record<string, typeof Package> = {
  "📦 Stock y Logística": Package,
  "💰 Costos de Compra": DollarSign,
  "🏷️ Ventas y Valorización": Tag,
  "⏳ Rotación y Autonomía": Clock,
};

export function TableConfigModal<
  TSortKey extends string = "nombre" | "stock" | "precio" | "vigencia",
  TColKey extends string = ColumnKey
>({
  open,
  onOpenChange,
  sortConfig,
  sortOptions,
  columns = ALL_COLUMNS as unknown as readonly ColumnOption<TColKey>[],
  visibleColsOrder,
  onSaveConfig,
  viewMode = "simple",
  onResetView,
}: TableConfigModalProps<TSortKey, TColKey>) {
  // Estado local temporal
  const [tempOrderedCols, setTempOrderedCols] = useState<TColKey[]>(visibleColsOrder);
  const [tempSortConfig, setTempSortConfig] = useState(sortConfig);
  const [tempViewMode, setTempViewMode] = useState<ViewMode>(viewMode);
  const [searchColQuery, setSearchColQuery] = useState("");
  const [activeSection, setActiveSection] = useState<string>("all");

  // Presets
  const [presets, setPresets] = useState<TablePreset<TColKey, TSortKey>[]>(() => {
    try {
      const saved = typeof window !== "undefined" ? window.localStorage?.getItem("gestion_table_presets_v1") : null;
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return [...(SYSTEM_PRESETS as unknown as TablePreset<TColKey, TSortKey>[]), ...parsed];
        }
      }
    } catch {
      // ignore
    }
    return SYSTEM_PRESETS as unknown as TablePreset<TColKey, TSortKey>[];
  });
  const [selectedPresetId, setSelectedPresetId] = useState<string>("system-resumen");

  // Sub-modal para guardar nuevo preset
  const [showSavePresetModal, setShowSavePresetModal] = useState(false);
  const [newPresetName, setNewPresetName] = useState("");
  const [newPresetDesc, setNewPresetDesc] = useState("");

  // Sincronizar estado al abrir
  useEffect(() => {
    if (open) {
      setTempOrderedCols(visibleColsOrder);
      setTempSortConfig(sortConfig);
      setTempViewMode(viewMode);

      const matchingPreset = presets.find((p) => {
        const pCols = p.columns.filter((k) => columns.some((c) => c.key === k));
        if (pCols.length !== visibleColsOrder.length) return false;
        return pCols.every((c, i) => visibleColsOrder[i] === c);
      });
      if (matchingPreset) {
        setSelectedPresetId(matchingPreset.id);
      } else {
        setSelectedPresetId("system-resumen");
      }
    }
  }, [open, visibleColsOrder, sortConfig, viewMode, presets, columns]);

  const visibleColsSet = useMemo(() => new Set(tempOrderedCols), [tempOrderedCols]);

  // Secciones únicas disponibles
  const sections = useMemo(() => {
    const set = new Set<string>();
    columns.forEach((c) => {
      if (c.section) set.add(c.section);
    });
    return Array.from(set);
  }, [columns]);

  // Filtrado de columnas disponibles según buscador y sección activa
  const filteredColumns = useMemo(() => {
    return columns.filter((col) => {
      const matchesSearch =
        searchColQuery.trim() === "" ||
        col.label.toLowerCase().includes(searchColQuery.toLowerCase()) ||
        col.key.toLowerCase().includes(searchColQuery.toLowerCase()) ||
        (col.subsection && col.subsection.toLowerCase().includes(searchColQuery.toLowerCase()));

      const matchesSection = activeSection === "all" || col.section === activeSection;

      return matchesSearch && matchesSection;
    });
  }, [columns, searchColQuery, activeSection]);

  // Alternar selección de columna
  const toggleCol = (key: TColKey) => {
    setTempOrderedCols((prev) => {
      if (prev.includes(key)) {
        return prev.filter((k) => k !== key);
      } else {
        return [...prev, key];
      }
    });
  };

  // Reordenar columnas seleccionadas
  const moveColumn = (index: number, direction: "up" | "down") => {
    setTempOrderedCols((prev) => {
      const next = [...prev];
      const targetIndex = direction === "up" ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= next.length) return prev;
      const current = next[index];
      const target = next[targetIndex];
      if (current !== undefined && target !== undefined) {
        next[index] = target;
        next[targetIndex] = current;
      }
      return next;
    });
  };

  // Switch masivo de columnas Neto vs Bruto
  const handleMassSwitch = (target: "neto" | "bruto") => {
    setTempOrderedCols((prev) => {
      return prev.map((key) => {
        const colObj = columns.find((c) => c.key === key);
        if (colObj && colObj.counterpartKey) {
          if (target === "neto" && colObj.isBruto) {
            return colObj.counterpartKey;
          }
          if (target === "bruto" && colObj.isNeto) {
            return colObj.counterpartKey;
          }
        }
        return key;
      });
    });
    toast.success(`Cambiadas columnas a valores ${target === "neto" ? "Netos" : "Brutos"}`);
  };

  // Aplicar un preset
  const handleApplyPreset = (presetId: string) => {
    const preset = presets.find((p) => p.id === presetId);
    if (!preset) return;

    setSelectedPresetId(presetId);
    const validPresetCols = preset.columns.filter((k) =>
      columns.some((c) => c.key === k)
    );
    setTempOrderedCols(validPresetCols);

    if (preset.sortConfig) {
      setTempSortConfig(preset.sortConfig);
    }
    if (preset.viewMode) {
      setTempViewMode(preset.viewMode);
    }
    toast.success(`Plantilla "${preset.name}" aplicada`);
  };

  // Guardar preset personalizado
  const handleSaveCustomPreset = () => {
    if (!newPresetName.trim()) {
      toast.error("Ingresa un nombre para la plantilla");
      return;
    }
    const newId = `custom-preset-${Date.now()}`;
    const newPreset: TablePreset<TColKey, TSortKey> = {
      id: newId,
      name: newPresetName.trim(),
      description: newPresetDesc.trim() || undefined,
      columns: [...tempOrderedCols],
      sortConfig: tempSortConfig,
      viewMode: tempViewMode,
      isSystem: false,
    };

    const customPresets = presets.filter((p) => !p.isSystem);
    const updatedCustom = [...customPresets, newPreset];

    setPresets([...(SYSTEM_PRESETS as unknown as TablePreset<TColKey, TSortKey>[]), ...updatedCustom]);
    try {
      window.localStorage?.setItem("gestion_table_presets_v1", JSON.stringify(updatedCustom));
    } catch {
      // ignore
    }

    setSelectedPresetId(newId);
    setNewPresetName("");
    setNewPresetDesc("");
    setShowSavePresetModal(false);
    toast.success(`Plantilla "${newPreset.name}" guardada con éxito`);
  };

  // Eliminar preset personalizado
  const handleDeletePreset = (id: string) => {
    const preset = presets.find((p) => p.id === id);
    if (preset?.isSystem) {
      toast.error("No se pueden eliminar plantillas del sistema");
      return;
    }
    const updatedCustom = presets.filter((p) => !p.isSystem && p.id !== id);
    setPresets([...(SYSTEM_PRESETS as unknown as TablePreset<TColKey, TSortKey>[]), ...updatedCustom]);
    try {
      window.localStorage?.setItem("gestion_table_presets_v1", JSON.stringify(updatedCustom));
    } catch {
      // ignore
    }
    setSelectedPresetId("system-resumen");
    toast.success("Plantilla personalizada eliminada");
  };

  // Confirmar y guardar configuración
  const handleConfirmSave = () => {
    onSaveConfig({
      orderedColumns: tempOrderedCols,
      sortConfig: tempSortConfig,
      viewMode: tempViewMode,
      presetId: selectedPresetId,
    });
    onOpenChange(false);
    toast.success("Configuración de tabla aplicada exitosamente");
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={() => onOpenChange(false)}
      title="Personalizar Vista de Tabla"
      description="Selecciona, reordena y personaliza las columnas analíticas de productos e insumos."
      maxWidth="max-w-4xl"
    >
      <div className="space-y-4 py-1 text-foreground" data-testid="table-config-modal">
        {/* BARRA SUPERIOR: SELECCIÓN DE PRESET & CONTROLES */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-xl bg-secondary/30 border border-border">
          <div className="flex-1 min-w-0">
            <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              Plantilla de Columnas (Preset)
            </label>
            <div className="flex items-center gap-2">
              <select
                value={selectedPresetId}
                onChange={(e) => handleApplyPreset(e.target.value)}
                data-testid="preset-select"
                className="h-10 px-3 rounded-xl bg-card border border-input text-xs font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary flex-1 min-w-0"
              >
                <optgroup label="Plantillas Canónicas del Sistema">
                  {presets
                    .filter((p) => p.isSystem)
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                </optgroup>
                {presets.some((p) => !p.isSystem) && (
                  <optgroup label="Mis Plantillas Personalizadas">
                    {presets
                      .filter((p) => !p.isSystem)
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                  </optgroup>
                )}
              </select>

              <button
                type="button"
                onClick={() => setShowSavePresetModal(true)}
                data-testid="btn-save-as-preset"
                title="Guardar como nueva plantilla"
                className="touch-target inline-flex min-h-[40px] px-3 items-center gap-1.5 rounded-xl border border-border bg-card hover:bg-secondary text-xs font-bold text-foreground cursor-pointer select-none transition-colors"
              >
                <Bookmark className="h-3.5 w-3.5 text-primary" />
                <span className="hidden sm:inline">Guardar</span>
              </button>

              {presets.some((p) => p.id === selectedPresetId && !p.isSystem) && (
                <button
                  type="button"
                  onClick={() => handleDeletePreset(selectedPresetId)}
                  data-testid="btn-delete-preset"
                  title="Eliminar plantilla seleccionada"
                  className="touch-target inline-flex min-h-[40px] px-3 items-center gap-1.5 rounded-xl border border-destructive/30 bg-destructive/10 hover:bg-destructive/20 text-xs font-bold text-destructive cursor-pointer select-none transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* TOGGLE NETO / BRUTO MASIVO */}
          <div className="shrink-0">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              Valores Monetarios
            </span>
            <div className="inline-flex rounded-xl border border-border bg-card p-1">
              <button
                type="button"
                onClick={() => handleMassSwitch("neto")}
                data-testid="btn-mass-neto"
                className="px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-secondary cursor-pointer select-none transition-all"
              >
                Todo Neto
              </button>
              <button
                type="button"
                onClick={() => handleMassSwitch("bruto")}
                data-testid="btn-mass-bruto"
                className="px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-secondary cursor-pointer select-none transition-all"
              >
                Todo Bruto
              </button>
            </div>
          </div>
        </div>

        {/* MODAL SECUNDARIO: GUARDAR PRESET */}
        {showSavePresetModal && (
          <div className="p-3 rounded-xl border-2 border-primary/40 bg-card/90 space-y-3 animate-fade-in">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-black uppercase text-primary">
                Guardar como Nueva Plantilla
              </h4>
              <button
                type="button"
                onClick={() => setShowSavePresetModal(false)}
                className="text-xs text-muted-foreground hover:text-foreground cursor-pointer"
              >
                Cancelar
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <input
                type="text"
                placeholder="Nombre de la plantilla..."
                value={newPresetName}
                onChange={(e) => setNewPresetName(e.target.value)}
                data-testid="input-preset-name"
                className="h-10 px-3 rounded-xl bg-background border border-input text-xs font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <input
                type="text"
                placeholder="Descripción (opcional)..."
                value={newPresetDesc}
                onChange={(e) => setNewPresetDesc(e.target.value)}
                data-testid="input-preset-desc"
                className="h-10 px-3 rounded-xl bg-background border border-input text-xs font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleSaveCustomPreset}
                data-testid="btn-confirm-save-preset"
                className="touch-target inline-flex min-h-[40px] px-4 items-center gap-1.5 rounded-xl bg-primary text-primary-foreground text-xs font-bold cursor-pointer select-none"
              >
                <Check className="h-3.5 w-3.5" />
                Confirmar y Guardar Plantilla
              </button>
            </div>
          </div>
        )}

        {/* CONTROLES DE MODO DE VISTA Y ORDENAMIENTO */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-xl bg-secondary/15 border border-border/80">
          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              Modo de Visualización de Tabla
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setTempViewMode("simple")}
                data-testid="viewmode-simple"
                className={cn(
                  "h-10 rounded-xl border text-xs font-bold cursor-pointer select-none transition-all flex items-center justify-center gap-1.5",
                  tempViewMode === "simple"
                    ? "bg-primary text-primary-foreground border-primary shadow-sm"
                    : "bg-card text-foreground border-border hover:bg-secondary/50"
                )}
              >
                <SlidersHorizontal className="h-3.5 w-3.5" />
                Vista Simple (Plana)
              </button>
              <button
                type="button"
                onClick={() => setTempViewMode("agrupado")}
                data-testid="viewmode-agrupado"
                className={cn(
                  "h-10 rounded-xl border text-xs font-bold cursor-pointer select-none transition-all flex items-center justify-center gap-1.5",
                  tempViewMode === "agrupado"
                    ? "bg-primary text-primary-foreground border-primary shadow-sm"
                    : "bg-card text-foreground border-border hover:bg-secondary/50"
                )}
              >
                <Package className="h-3.5 w-3.5" />
                Vista Agrupada
              </button>
            </div>
          </div>

          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              Criterio de Ordenamiento Predeterminado
            </label>
            <div className="flex gap-2">
              <select
                value={tempSortConfig.key}
                onChange={(e) =>
                  setTempSortConfig((prev) => ({
                    ...prev,
                    key: e.target.value as TSortKey,
                  }))
                }
                data-testid="sort-option-select"
                className="h-10 px-3 rounded-xl bg-card border border-input text-xs font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary flex-1 min-w-0"
              >
                {sortOptions.map((opt) => (
                  <option key={`${opt.key}-${opt.direction}`} value={opt.key}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() =>
                  setTempSortConfig((prev) => ({
                    ...prev,
                    direction: prev.direction === "asc" ? "desc" : "asc",
                  }))
                }
                data-testid="btn-toggle-sort-direction"
                title="Cambiar dirección (Ascendente / Descendente)"
                className="touch-target inline-flex min-h-[40px] px-3 items-center justify-center rounded-xl border border-border bg-card hover:bg-secondary text-xs font-bold text-foreground cursor-pointer select-none"
              >
                {tempSortConfig.direction === "asc" ? "ASC ↑" : "DESC ↓"}
              </button>
            </div>
          </div>
        </div>

        {/* FILTRO DE SECCIONES Y BUSCADOR DE COLUMNAS */}
        <div className="space-y-2">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
            <div className="flex items-center gap-1 overflow-x-auto pb-1 max-w-full">
              <button
                type="button"
                onClick={() => setActiveSection("all")}
                data-testid="section-tab-all"
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap cursor-pointer select-none transition-colors",
                  activeSection === "all"
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary/40 text-muted-foreground hover:text-foreground"
                )}
              >
                Todas ({columns.length})
              </button>
              {sections.map((sec) => {
                const IconComponent = SECTION_ICONS[sec] || Package;
                return (
                  <button
                    key={sec}
                    type="button"
                    onClick={() => setActiveSection(sec)}
                    data-testid={`section-tab-${sec}`}
                    className={cn(
                      "px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap cursor-pointer select-none transition-colors flex items-center gap-1.5",
                      activeSection === sec
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary/40 text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <IconComponent className="h-3 w-3" />
                    <span>{sec.replace(/^[^\w\s]+\s*/, "")}</span>
                  </button>
                );
              })}
            </div>

            <div className="relative min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
              <input
                type="text"
                placeholder="Filtrar columnas..."
                value={searchColQuery}
                onChange={(e) => setSearchColQuery(e.target.value)}
                data-testid="input-filter-columns"
                className="w-full h-9 pl-8 pr-3 rounded-xl bg-card border border-input text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
        </div>

        {/* CONTENEDOR DE 2 COLUMNAS: COLUMNAS DISPONIBLES VS ORDEN VISIBLE */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* Panel Izquierdo: Selección de Columnas */}
          <div className="flex flex-col rounded-xl border border-border bg-card p-3 max-h-[300px]">
            <div className="flex items-center justify-between pb-2 border-b border-border mb-2">
              <span className="text-xs font-black uppercase text-foreground">
                Columnas Disponibles ({filteredColumns.length})
              </span>
              <span className="text-[10px] text-muted-foreground">
                Click para marcar/desmarcar
              </span>
            </div>
            <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
              {filteredColumns.map((col) => {
                const isSelected = visibleColsSet.has(col.key);
                return (
                  <button
                    key={col.key}
                    type="button"
                    onClick={() => toggleCol(col.key)}
                    data-testid={`col-toggle-${col.key}`}
                    className={cn(
                      "w-full flex items-center justify-between p-2 rounded-lg text-left text-xs transition-colors cursor-pointer select-none",
                      isSelected
                        ? "bg-primary/10 border border-primary/30 text-primary font-bold"
                        : "bg-secondary/20 hover:bg-secondary/40 text-foreground border border-transparent font-medium"
                    )}
                  >
                    <div className="flex flex-col min-w-0 pr-2">
                      <span className="truncate">{col.label}</span>
                      {col.subsection && (
                        <span className="text-[10px] text-muted-foreground">
                          {col.subsection}
                        </span>
                      )}
                    </div>
                    <div
                      className={cn(
                        "h-4 w-4 rounded flex items-center justify-center shrink-0 border",
                        isSelected
                          ? "bg-primary border-primary text-primary-foreground"
                          : "border-muted-foreground/40 bg-card"
                      )}
                    >
                      {isSelected && <Check className="h-3 w-3 stroke-[3]" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Panel Derecho: Reordenamiento de Columnas Visibles */}
          <div className="flex flex-col rounded-xl border border-border bg-card p-3 max-h-[300px]">
            <div className="flex items-center justify-between pb-2 border-b border-border mb-2">
              <span className="text-xs font-black uppercase text-foreground">
                Columnas Visibles ({tempOrderedCols.length})
              </span>
              <span className="text-[10px] text-muted-foreground">
                Orden de izquierda a derecha
              </span>
            </div>
            <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
              {tempOrderedCols.length === 0 ? (
                <div className="p-6 text-center text-xs text-muted-foreground">
                  No hay columnas seleccionadas. Marca columnas desde el panel izquierdo.
                </div>
              ) : (
                tempOrderedCols.map((key, idx) => {
                  const colObj = columns.find((c) => c.key === key);
                  return (
                    <div
                      key={key}
                      data-testid={`visible-col-item-${key}`}
                      className="flex items-center justify-between p-1.5 pl-2.5 rounded-lg bg-secondary/30 border border-border text-xs font-medium"
                    >
                      <span className="truncate text-foreground font-semibold">
                        {idx + 1}. {colObj?.label || key}
                      </span>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          type="button"
                          onClick={() => moveColumn(idx, "up")}
                          disabled={idx === 0}
                          title="Mover a la izquierda"
                          className="p-1 rounded text-muted-foreground hover:text-foreground disabled:opacity-30 cursor-pointer"
                        >
                          <ArrowUp className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => moveColumn(idx, "down")}
                          disabled={idx === tempOrderedCols.length - 1}
                          title="Mover a la derecha"
                          className="p-1 rounded text-muted-foreground hover:text-foreground disabled:opacity-30 cursor-pointer"
                        >
                          <ArrowDown className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => toggleCol(key)}
                          title="Quitar columna"
                          className="p-1 rounded text-muted-foreground hover:text-destructive cursor-pointer"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* PIE DEL MODAL CON BOTONES DE ACCIÓN */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 pt-3 border-t border-border">
          {onResetView ? (
            <button
              type="button"
              onClick={onResetView}
              data-testid="btn-reset-view"
              className="touch-target inline-flex min-h-[44px] px-3 items-center justify-center gap-1.5 rounded-xl border border-border bg-card hover:bg-secondary text-xs font-bold text-foreground cursor-pointer select-none"
            >
              <RotateCcw className="h-3.5 w-3.5 text-muted-foreground" />
              <span>Restablecer Todo</span>
            </button>
          ) : (
            <div />
          )}

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              data-testid="btn-cancel-table-config"
              className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center rounded-xl border border-border bg-secondary text-xs font-bold text-secondary-foreground hover:bg-secondary/80 cursor-pointer select-none flex-1 sm:flex-initial"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleConfirmSave}
              data-testid="btn-apply-table-config"
              className="touch-target inline-flex min-h-[44px] px-5 items-center justify-center gap-1.5 rounded-xl bg-primary text-xs font-bold text-primary-foreground hover:bg-primary/90 shadow-md cursor-pointer select-none flex-1 sm:flex-initial"
            >
              <Check className="h-4 w-4 stroke-[3]" />
              <span>Aplicar Configuración</span>
            </button>
          </div>
        </div>
      </div>
    </ResponsiveDialog>
  );
}
