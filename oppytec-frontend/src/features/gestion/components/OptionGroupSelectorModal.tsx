import { useState, useEffect, useMemo } from "react";
import {
  X,
  Search,
  Plus,
  Trash2,
  Check,
  Library,
  Sparkles,
  Layers,
  Pencil,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/shared/lib";
import { useCurrencyFormatter } from "@/shared/currency";
import { useGruposOpciones, INITIAL_GRUPOS_OPCIONES_MOCK } from "../hooks/useGruposOpciones";
import { INITIAL_PRODUCTOS_MOCK } from "../useGestion";
import { INITIAL_RECETAS_MOCK } from "../hooks/useRecetas";
import type {
  GrupoOpciones,
  GrupoOpcionesItem,
  Producto,
  Receta,
} from "../types";

export interface OptionGroupSelectorModalProps {
  open: boolean;
  onClose: () => void;
  onSelectGroup: (grupo: GrupoOpciones) => void;
  initialTab?: "library" | "create";
  editingGroup?: GrupoOpciones | null;
  gruposBiblioteca?: GrupoOpciones[];
  productos?: Producto[];
  subrecetas?: Receta[];
}

export function OptionGroupSelectorModal({
  open,
  onClose,
  onSelectGroup,
  initialTab = "library",
  editingGroup = null,
  gruposBiblioteca,
  productos = INITIAL_PRODUCTOS_MOCK,
  subrecetas = INITIAL_RECETAS_MOCK,
}: OptionGroupSelectorModalProps) {
  const { t } = useTranslation("recipes");
  const { convertAndFormat } = useCurrencyFormatter();
  const {
    gruposOpciones: hookGrupos,
    createGrupoOpciones,
    updateGrupoOpciones,
  } = useGruposOpciones();

  const allGroups = useMemo(() => {
    if (gruposBiblioteca && gruposBiblioteca.length > 0) return gruposBiblioteca;
    return hookGrupos.length > 0 ? hookGrupos : INITIAL_GRUPOS_OPCIONES_MOCK;
  }, [gruposBiblioteca, hookGrupos]);

  const [activeTab, setActiveTab] = useState<"library" | "create">(initialTab);
  const [searchQuery, setSearchQuery] = useState("");

  // Form state for Create / Edit In-Situ
  const [editingId, setEditingId] = useState<string | number | null>(null);
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [seleccionMinima, setSeleccionMinima] = useState<number>(1);
  const [seleccionMaxima, setSeleccionMaxima] = useState<number>(1);
  const [permiteRepetir, setPermiteRepetir] = useState<boolean>(false);
  const [items, setItems] = useState<GrupoOpcionesItem[]>([]);

  // Quick selector state for adding polymorphic option items
  const [quickSourceType, setQuickSourceType] = useState<"producto" | "receta">("producto");
  const [quickSourceId, setQuickSourceId] = useState<string>("");

  useEffect(() => {
    if (!open) return;
    if (editingGroup) {
      setActiveTab("create");
      setEditingId(editingGroup.id);
      setNombre(editingGroup.nombre);
      setDescripcion(editingGroup.descripcion || "");
      setSeleccionMinima(editingGroup.seleccion_minima ?? editingGroup.min_selecciones ?? 1);
      setSeleccionMaxima(editingGroup.seleccion_maxima ?? editingGroup.max_selecciones ?? 1);
      setPermiteRepetir(Boolean(editingGroup.permite_repetir));
      setItems(
        (editingGroup.items || []).map((it, idx) => ({
          ...it,
          id: it.id ?? `opt-item-${idx}`,
          target_type: it.target_type ?? it.type ?? "producto",
          type: it.type ?? it.target_type ?? "producto",
          cantidad: it.cantidad ?? it.cantidad_porcion ?? 1,
          cantidad_porcion: it.cantidad_porcion ?? it.cantidad ?? 1,
          es_opcion_default: Boolean(it.es_opcion_default ?? it.es_default),
          es_default: Boolean(it.es_default ?? it.es_opcion_default),
          recargo_precio: it.recargo_precio ?? it.precio_adicional ?? 0,
          precio_adicional: it.precio_adicional ?? it.recargo_precio ?? 0,
          costo_referencial: it.costo_referencial ?? 0,
        }))
      );
    } else {
      setActiveTab(initialTab);
      setEditingId(null);
      setNombre("");
      setDescripcion("");
      setSeleccionMinima(1);
      setSeleccionMaxima(1);
      setPermiteRepetir(false);
      setItems([
        {
          id: `opt-init-1`,
          nombre: productos[0]?.nombre || t("modals.common.default_option_1"),
          producto_id: productos[0]?.id ?? "prod-1",
          target_type: "producto",
          type: "producto",
          cantidad: 1,
          cantidad_porcion: 1,
          es_opcion_default: true,
          es_default: true,
          recargo_precio: 0,
          precio_adicional: 0,
          costo_referencial: productos[0]?.costo_unitario_ppp ?? productos[0]?.costo_unitario ?? 500,
          orden: 1,
        },
      ]);
    }
  }, [open, editingGroup, initialTab, productos, t]);

  const filteredLibrary = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return allGroups;
    return allGroups.filter(
      (g) =>
        g.nombre.toLowerCase().includes(q) ||
        g.descripcion?.toLowerCase().includes(q) ||
        g.items?.some((i) => i.nombre?.toLowerCase().includes(q))
    );
  }, [allGroups, searchQuery]);

  if (!open) return null;

  const handleLoadGroupForEdit = (grupo: GrupoOpciones) => {
    setEditingId(grupo.id);
    setNombre(grupo.nombre);
    setDescripcion(grupo.descripcion || "");
    setSeleccionMinima(grupo.seleccion_minima ?? grupo.min_selecciones ?? 1);
    setSeleccionMaxima(grupo.seleccion_maxima ?? grupo.max_selecciones ?? 1);
    setPermiteRepetir(Boolean(grupo.permite_repetir));
    setItems(
      (grupo.items || []).map((it, idx) => ({
        ...it,
        id: it.id ?? `opt-edit-${idx}`,
        target_type: it.target_type ?? it.type ?? "producto",
        type: it.type ?? it.target_type ?? "producto",
        cantidad: it.cantidad ?? it.cantidad_porcion ?? 1,
        cantidad_porcion: it.cantidad_porcion ?? it.cantidad ?? 1,
        es_opcion_default: Boolean(it.es_opcion_default ?? it.es_default),
        es_default: Boolean(it.es_default ?? it.es_opcion_default),
        recargo_precio: it.recargo_precio ?? it.precio_adicional ?? 0,
        precio_adicional: it.precio_adicional ?? it.recargo_precio ?? 0,
        costo_referencial: it.costo_referencial ?? 0,
      }))
    );
    setActiveTab("create");
  };

  const handleAddOptionItem = () => {
    let itemNombre = "";
    let prodId: string | number | null = null;
    let recId: string | number | null = null;
    let costoRef = 0;

    if (quickSourceType === "producto") {
      const found =
        productos.find((p) => String(p.id) === String(quickSourceId)) || productos[0];
      if (found) {
        prodId = found.id;
        itemNombre = found.nombre;
        costoRef = found.costo_unitario_ppp ?? found.costo_unitario ?? 0;
      }
    } else {
      const found =
        subrecetas.find((r) => String(r.id) === String(quickSourceId)) || subrecetas[0];
      if (found) {
        recId = found.id;
        itemNombre = found.nombre;
        costoRef = found.costo_porcion ?? found.costo_total ?? 0;
      }
    }

    const newItem: GrupoOpcionesItem = {
      id: `opt-item-${Date.now()}-${items.length}`,
      producto_id: prodId,
      receta_id: recId,
      nombre: itemNombre,
      target_type: quickSourceType,
      type: quickSourceType,
      cantidad: 1,
      cantidad_porcion: 1,
      es_opcion_default: items.length === 0,
      es_default: items.length === 0,
      recargo_precio: 0,
      precio_adicional: 0,
      costo_referencial: costoRef,
      orden: items.length + 1,
    };

    setItems((prev) => [...prev, newItem]);
  };

  const handleUpdateItem = (index: number, patch: Partial<GrupoOpcionesItem>) => {
    setItems((prev) =>
      prev.map((it, idx) => {
        if (idx !== index) return it;
        const next = { ...it, ...patch };
        if ("cantidad" in patch) next.cantidad_porcion = patch.cantidad;
        if ("cantidad_porcion" in patch) next.cantidad = patch.cantidad_porcion;
        if ("es_opcion_default" in patch) next.es_default = patch.es_opcion_default;
        if ("es_default" in patch) next.es_opcion_default = patch.es_default;
        if ("recargo_precio" in patch) next.precio_adicional = patch.recargo_precio;
        if ("precio_adicional" in patch) next.recargo_precio = patch.precio_adicional;
        return next;
      })
    );
  };

  const handleRemoveItem = (index: number) => {
    setItems((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleSaveAndLink = async () => {
    if (!nombre.trim()) return;

    const minVal = Math.max(0, Number(seleccionMinima) || 0);
    const maxVal = Math.max(minVal || 1, Number(seleccionMaxima) || 1);

    const normalizedItems: GrupoOpcionesItem[] = items.map((it, idx) => ({
      ...it,
      id: it.id ?? `goi-${Date.now()}-${idx}`,
      cantidad: Number(it.cantidad ?? it.cantidad_porcion ?? 1),
      cantidad_porcion: Number(it.cantidad_porcion ?? it.cantidad ?? 1),
      es_opcion_default: Boolean(it.es_opcion_default ?? it.es_default),
      es_default: Boolean(it.es_default ?? it.es_opcion_default),
      recargo_precio: Number(it.recargo_precio ?? it.precio_adicional ?? 0),
      precio_adicional: Number(it.precio_adicional ?? it.recargo_precio ?? 0),
      costo_referencial: Number(it.costo_referencial ?? 0),
      orden: idx + 1,
    }));

    const localGroup: GrupoOpciones = {
      id: editingId ?? `grp-insitu-${Date.now()}`,
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      seleccion_minima: minVal,
      seleccion_maxima: maxVal,
      min_selecciones: minVal,
      max_selecciones: maxVal,
      permite_repetir: permiteRepetir,
      items: normalizedItems,
    };

    try {
      const payload = {
        nombre: localGroup.nombre,
        descripcion: localGroup.descripcion,
        seleccion_minima: localGroup.seleccion_minima,
        seleccion_maxima: localGroup.seleccion_maxima,
        permite_repetir: localGroup.permite_repetir,
        items: normalizedItems.map((i, idx) => ({
          producto_id: i.producto_id ?? null,
          receta_id: i.receta_id ?? null,
          nombre: i.nombre ?? "",
          cantidad: i.cantidad ?? 1,
          es_opcion_default: Boolean(i.es_opcion_default),
          recargo_precio: i.recargo_precio ?? 0,
          orden: idx + 1,
        })),
      };

      if (editingId) {
        const updated = await updateGrupoOpciones({ id: editingId, data: payload });
        onSelectGroup({ ...localGroup, ...updated, items: updated.items || normalizedItems });
      } else {
        const created = await createGrupoOpciones(payload);
        onSelectGroup({ ...localGroup, ...created, items: created.items || normalizedItems });
      }
    } catch {
      // Offline / fallback in situ creation without losing state
      onSelectGroup(localGroup);
    }

    onClose();
  };

  return (
    <div
      data-testid="option-group-selector-modal"
      role="dialog"
      aria-modal="true"
      aria-label={t("modals.option_group.modal_title")}
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-xs p-2 sm:p-4 overflow-y-auto"
    >
      <div className="relative w-full max-w-4xl rounded-2xl border border-border bg-card text-foreground shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4 bg-muted/30">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/15 text-purple-600 dark:text-purple-400">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-foreground">
                {t("modals.option_group.modal_title")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {t("modals.option_group.modal_subtitle")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="btn-close-option-group-modal"
            aria-label={t("modals.common.close")}
            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-border bg-muted/20 px-5 pt-2 gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("library")}
            data-testid="tab-option-group-library"
            className={cn(
              "inline-flex min-h-[44px] items-center gap-2 px-4 py-2 text-xs sm:text-sm font-bold border-b-2 transition-colors cursor-pointer",
              activeTab === "library"
                ? "border-purple-500 text-purple-600 dark:text-purple-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <Library className="h-4 w-4" />
            <span>{t("modals.option_group.tab_library")}</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("create")}
            data-testid="tab-option-group-create"
            className={cn(
              "inline-flex min-h-[44px] items-center gap-2 px-4 py-2 text-xs sm:text-sm font-bold border-b-2 transition-colors cursor-pointer",
              activeTab === "create"
                ? "border-purple-500 text-purple-600 dark:text-purple-400"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <Sparkles className="h-4 w-4" />
            <span>{t("modals.option_group.tab_create")}</span>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {activeTab === "library" ? (
            <div className="space-y-4" data-testid="option-group-library-panel">
              {/* Search bar */}
              <div className="relative flex items-center">
                <Search className="absolute left-3.5 h-4 w-4 text-muted-foreground pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t("modals.option_group.search_library_placeholder")}
                  data-testid="option-group-search-input"
                  className="w-full min-h-[44px] pl-10 pr-4 rounded-xl border border-input bg-background text-sm focus:outline-none focus:border-purple-500"
                />
              </div>

              {/* Groups list */}
              {filteredLibrary.length === 0 ? (
                <div
                  data-testid="option-group-library-empty"
                  className="p-8 text-center rounded-xl border border-dashed border-border text-xs text-muted-foreground"
                >
                  {t("modals.option_group.empty_library")}
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3">
                  {filteredLibrary.map((grupo) => {
                    const minSel = grupo.seleccion_minima ?? grupo.min_selecciones ?? 1;
                    const maxSel = grupo.seleccion_maxima ?? grupo.max_selecciones ?? 1;
                    return (
                      <div
                        key={grupo.id}
                        data-testid={`library-group-card-${grupo.id}`}
                        className="rounded-xl border border-border bg-background/60 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-purple-500/40 transition-colors"
                      >
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-sm text-foreground">
                              {grupo.nombre}
                            </span>
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-purple-500/15 text-purple-600 dark:text-purple-400 border border-purple-500/30">
                              {t("modals.option_group.cardinality_hint", {
                                min: minSel,
                                max: maxSel,
                              })}
                            </span>
                          </div>
                          {grupo.descripcion && (
                            <p className="text-xs text-muted-foreground">
                              {grupo.descripcion}
                            </p>
                          )}
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {(grupo.items || []).map((it, idx) => {
                              const isDef = it.es_opcion_default ?? it.es_default;
                              const recargo = it.recargo_precio ?? it.precio_adicional ?? 0;
                              return (
                                <span
                                  key={it.id ?? idx}
                                  className={cn(
                                    "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium border",
                                    isDef
                                      ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 font-bold"
                                      : "bg-muted text-muted-foreground border-border"
                                  )}
                                >
                                  <span>{it.nombre}</span>
                                  {recargo > 0 && (
                                    <span className="text-amber-600 dark:text-amber-400 font-bold">
                                      +{convertAndFormat(recargo)}
                                    </span>
                                  )}
                                </span>
                              );
                            })}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={() => handleLoadGroupForEdit(grupo)}
                            data-testid={`btn-edit-library-group-${grupo.id}`}
                            className="inline-flex min-h-[44px] items-center gap-1.5 px-3 py-2 rounded-xl border border-border bg-secondary text-xs font-bold text-foreground hover:bg-secondary/80 transition-colors cursor-pointer"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                            <span>{t("modals.option_group.edit_group_btn")}</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              onSelectGroup(grupo);
                              onClose();
                            }}
                            data-testid={`btn-select-group-${grupo.id}`}
                            className="inline-flex min-h-[44px] items-center gap-1.5 px-4 py-2 rounded-xl bg-purple-600 text-xs font-extrabold text-white hover:bg-purple-500 transition-colors cursor-pointer"
                          >
                            <Check className="h-4 w-4" />
                            <span>{t("modals.option_group.select_group_btn")}</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            /* Create / Edit In-Situ Panel */
            <div className="space-y-4" data-testid="option-group-create-panel">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.option_group.field_group_name")}
                  </label>
                  <input
                    type="text"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    placeholder={t("modals.option_group.field_group_name_placeholder")}
                    data-testid="input-group-name"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.option_group.field_group_desc")}
                  </label>
                  <input
                    type="text"
                    value={descripcion}
                    onChange={(e) => setDescripcion(e.target.value)}
                    placeholder={t("modals.option_group.field_group_desc_placeholder")}
                    data-testid="input-group-desc"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.option_group.field_min")}
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={seleccionMinima}
                    onChange={(e) => setSeleccionMinima(Number(e.target.value))}
                    data-testid="input-group-min"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    {t("modals.option_group.field_max")}
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={seleccionMaxima}
                    onChange={(e) => setSeleccionMaxima(Number(e.target.value))}
                    data-testid="input-group-max"
                    className="w-full min-h-[44px] px-3 rounded-xl border border-input bg-background text-sm"
                  />
                </div>
                <label className="flex items-center gap-2 min-h-[44px] px-3 rounded-xl border border-border bg-muted/20 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={permiteRepetir}
                    onChange={(e) => setPermiteRepetir(e.target.checked)}
                    data-testid="checkbox-group-allow-repeat"
                    className="h-4 w-4 rounded accent-purple-600"
                  />
                  <span className="text-xs font-semibold text-foreground">
                    {t("modals.option_group.field_allow_repeat")}
                  </span>
                </label>
              </div>

              {/* Polymorphic Options Builder */}
              <div className="space-y-3 pt-2 border-t border-border">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <h3 className="text-xs font-extrabold uppercase tracking-wider text-muted-foreground">
                    {t("modals.option_group.items_section_title")}
                  </h3>
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      value={quickSourceType}
                      onChange={(e) => {
                        setQuickSourceType(e.target.value as "producto" | "receta");
                        setQuickSourceId("");
                      }}
                      data-testid="select-quick-option-source-type"
                      className="min-h-[44px] px-2.5 rounded-xl border border-input bg-background text-xs font-semibold"
                    >
                      <option value="producto">
                        {t("modals.option_group.item_type_product")}
                      </option>
                      <option value="receta">
                        {t("modals.option_group.item_type_recipe")}
                      </option>
                    </select>

                    <select
                      value={quickSourceId}
                      onChange={(e) => setQuickSourceId(e.target.value)}
                      data-testid="select-quick-option-source-id"
                      className="min-h-[44px] px-2.5 rounded-xl border border-input bg-background text-xs"
                    >
                      {quickSourceType === "producto"
                        ? productos.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.nombre} ({convertAndFormat(p.costo_unitario_ppp ?? p.costo_unitario ?? 0)})
                            </option>
                          ))
                        : subrecetas.map((r) => (
                            <option key={r.id} value={r.id}>
                              {r.nombre} ({convertAndFormat(r.costo_porcion ?? r.costo_total ?? 0)})
                            </option>
                          ))}
                    </select>

                    <button
                      type="button"
                      onClick={handleAddOptionItem}
                      data-testid="btn-add-group-option-item"
                      className="inline-flex min-h-[44px] items-center gap-1.5 px-3 py-2 rounded-xl bg-purple-600/15 text-purple-600 dark:text-purple-400 border border-purple-500/30 text-xs font-extrabold hover:bg-purple-600/25 transition-colors cursor-pointer"
                    >
                      <Plus className="h-4 w-4" />
                      <span>{t("modals.option_group.add_item_btn")}</span>
                    </button>
                  </div>
                </div>

                {/* Options Rows */}
                <div className="space-y-2">
                  {items.map((item, idx) => (
                    <div
                      key={item.id ?? idx}
                      data-testid={`group-option-item-row-${idx}`}
                      className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center p-2.5 rounded-xl border border-border bg-background/70"
                    >
                      <div className="sm:col-span-4">
                        <input
                          type="text"
                          value={item.nombre || ""}
                          onChange={(e) => handleUpdateItem(idx, { nombre: e.target.value })}
                          placeholder={t("modals.option_group.item_name_placeholder")}
                          data-testid={`input-option-name-${idx}`}
                          className="w-full min-h-[40px] px-2.5 rounded-lg border border-input bg-background text-xs font-semibold"
                        />
                      </div>

                      <div className="sm:col-span-2">
                        <label className="block text-[10px] text-muted-foreground">
                          {t("modals.option_group.item_portion_label")}
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          min="0.01"
                          value={item.cantidad ?? item.cantidad_porcion ?? 1}
                          onChange={(e) =>
                            handleUpdateItem(idx, { cantidad: Number(e.target.value) })
                          }
                          data-testid={`input-option-portion-${idx}`}
                          className="w-full min-h-[38px] px-2 rounded-lg border border-input bg-background text-xs"
                        />
                      </div>

                      <div className="sm:col-span-2">
                        <label className="block text-[10px] text-muted-foreground">
                          {t("modals.option_group.item_surcharge_label")}
                        </label>
                        <input
                          type="number"
                          step="100"
                          min="0"
                          value={item.recargo_precio ?? item.precio_adicional ?? 0}
                          onChange={(e) =>
                            handleUpdateItem(idx, { recargo_precio: Number(e.target.value) })
                          }
                          data-testid={`input-option-surcharge-${idx}`}
                          className="w-full min-h-[38px] px-2 rounded-lg border border-input bg-background text-xs"
                        />
                      </div>

                      <div className="sm:col-span-2">
                        <label className="block text-[10px] text-muted-foreground">
                          {t("modals.option_group.item_cost_label")}
                        </label>
                        <input
                          type="number"
                          step="50"
                          min="0"
                          value={item.costo_referencial ?? 0}
                          onChange={(e) =>
                            handleUpdateItem(idx, { costo_referencial: Number(e.target.value) })
                          }
                          data-testid={`input-option-cost-${idx}`}
                          className="w-full min-h-[38px] px-2 rounded-lg border border-input bg-background text-xs"
                        />
                      </div>

                      <div className="sm:col-span-1 flex items-center justify-center">
                        <label className="flex items-center gap-1 cursor-pointer text-[11px] font-bold">
                          <input
                            type="checkbox"
                            checked={Boolean(item.es_opcion_default ?? item.es_default)}
                            onChange={(e) =>
                              handleUpdateItem(idx, { es_opcion_default: e.target.checked })
                            }
                            data-testid={`checkbox-option-default-${idx}`}
                            className="h-4 w-4 accent-emerald-600"
                          />
                          <span className="sr-only">
                            {t("modals.option_group.item_default_label")}
                          </span>
                        </label>
                      </div>

                      <div className="sm:col-span-1 flex justify-end">
                        <button
                          type="button"
                          onClick={() => handleRemoveItem(idx)}
                          data-testid={`btn-remove-option-item-${idx}`}
                          aria-label={t("modals.common.delete")}
                          className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg text-rose-500 hover:bg-rose-500/10 cursor-pointer"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-border px-5 py-3.5 bg-muted/30">
          <button
            type="button"
            onClick={onClose}
            data-testid="btn-cancel-option-group-modal"
            className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-border bg-secondary px-4 py-2 text-xs font-bold text-foreground hover:bg-secondary/80 transition-colors cursor-pointer"
          >
            {t("modals.common.cancel")}
          </button>
          {activeTab === "create" && (
            <button
              type="button"
              onClick={handleSaveAndLink}
              disabled={!nombre.trim()}
              data-testid="btn-save-and-link-group"
              className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-purple-600 px-5 py-2 text-xs font-extrabold text-white hover:bg-purple-500 disabled:opacity-50 transition-colors cursor-pointer"
            >
              <Check className="h-4 w-4" />
              <span>{t("modals.option_group.save_and_link_btn")}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default OptionGroupSelectorModal;
