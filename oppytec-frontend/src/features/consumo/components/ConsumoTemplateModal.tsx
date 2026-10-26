// oppytec-frontend/src/features/consumo/components/ConsumoTemplateModal.tsx
import React, { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Bookmark,
  Globe,
  Star,
  Search,
  Check,
  X,
  Trash2,
  ArrowUp,
  ArrowDown,
  LayoutGrid,
  Sparkles,
} from "lucide-react";
import { cn } from "@/shared/lib/utils";
import type {
  ConsumoTemplate,
  ProductoConsumo,
  CategoriaConsumo,
} from "../types";

export interface ConsumoTemplateModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly initialTemplate?: ConsumoTemplate | null;
  readonly productos: ProductoConsumo[];
  readonly categorias: CategoriaConsumo[];
  readonly onSaveTemplate: (template: ConsumoTemplate) => Promise<void> | void;
  readonly onDeleteTemplate?: (templateId: string) => Promise<void> | void;
}

export function ConsumoTemplateModal({
  open,
  onOpenChange,
  initialTemplate,
  productos,
  categorias,
  onSaveTemplate,
  onDeleteTemplate,
}: ConsumoTemplateModalProps) {
  const { t } = useTranslation("operations");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [columnsCount, setColumnsCount] = useState(8);
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (initialTemplate) {
      setName(initialTemplate.name || "");
      setDescription(initialTemplate.description || "");
      setIsPublic(!!initialTemplate.isPublic);
      setColumnsCount(initialTemplate.columnsCount || 8);
      setSelectedProductIds(initialTemplate.productIds || []);
    } else {
      setName("");
      setDescription("");
      setIsPublic(false);
      setColumnsCount(8);
      setSelectedProductIds([]);
    }
    setSearchTerm("");
    setSelectedCategory("all");
  }, [initialTemplate, open]);

  const filteredProducts = useMemo(() => {
    return productos.filter((prod) => {
      const matchesSearch =
        searchTerm === "" ||
        prod.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (prod.sku && prod.sku.toLowerCase().includes(searchTerm.toLowerCase()));
      const matchesCat =
        selectedCategory === "all" || prod.categoria_id === selectedCategory;
      return matchesSearch && matchesCat;
    });
  }, [productos, searchTerm, selectedCategory]);

  if (!open) return null;

  const toggleProduct = (productId: string) => {
    setSelectedProductIds((prev) =>
      prev.includes(productId)
        ? prev.filter((id) => id !== productId)
        : [...prev, productId]
    );
  };

  const moveProductOrder = (index: number, direction: "up" | "down") => {
    const nextList = [...selectedProductIds];
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= nextList.length) return;

    const temp = nextList[index];
    const targetItem = nextList[targetIndex];
    if (temp === undefined || targetItem === undefined) return;
    nextList[index] = targetItem;
    nextList[targetIndex] = temp;
    setSelectedProductIds(nextList);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSaving(true);
    try {
      const templateToSave: ConsumoTemplate = {
        id: initialTemplate?.id || `tpl-${Date.now()}`,
        name: name.trim(),
        description: description.trim() || undefined,
        isPublic,
        columnsCount,
        productIds: selectedProductIds,
        customProductOrder: selectedProductIds,
        createdAt: initialTemplate?.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      await onSaveTemplate(templateToSave);
      onOpenChange(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!initialTemplate?.id || !onDeleteTemplate) return;
    setIsSaving(true);
    try {
      await onDeleteTemplate(initialTemplate.id);
      onOpenChange(false);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="consumo-template-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div className="w-full max-w-3xl rounded-3xl bg-card border border-border shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Cabecera */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-2xl bg-primary/15 text-primary border border-primary/30 flex items-center justify-center">
              <Bookmark className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-black uppercase tracking-wider text-foreground">
                {initialTemplate
                  ? t("consumption.modals.templates.edit_title", { defaultValue: "Editar Plantilla" })
                  : t("consumption.modals.templates.create_title", { defaultValue: "Nueva Plantilla de Consumo" })}
              </h3>
              <p className="text-xs text-muted-foreground">
                Personaliza un subconjunto de productos y columnas para turnos u operarios
              </p>
            </div>
          </div>

          <button
            type="button"
            data-testid="template-cancel-btn"
            onClick={() => onOpenChange(false)}
            className="p-1.5 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSave} className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar">
            {/* Parámetros Básicos */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Nombre de la Plantilla *
                </label>
                <input
                  type="text"
                  required
                  data-testid="template-name-input"
                  placeholder="Ej: Turno Mañana / Cuadrilla Cocina"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full h-10 px-3.5 rounded-xl border border-border bg-background text-sm font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Descripción (Opcional)
                </label>
                <input
                  type="text"
                  data-testid="template-desc-input"
                  placeholder="Ej: Insumos críticos para montaje matutino"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full h-10 px-3.5 rounded-xl border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>
            </div>

            {/* Ajuste de Columnas y Privacidad */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-2xl border border-border bg-muted/20">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <LayoutGrid className="h-4 w-4 text-primary" />
                  <span>Columnas de Catálogo ({columnsCount} cols)</span>
                </label>
                <select
                  data-testid="template-cols-select"
                  value={columnsCount}
                  onChange={(e) => setColumnsCount(Number(e.target.value))}
                  className="w-full h-10 px-3 rounded-xl border border-border bg-background text-xs font-bold text-foreground cursor-pointer"
                >
                  {[5, 6, 7, 8, 9, 10].map((num) => (
                    <option key={num} value={num}>
                      {num} Columnas {num === 8 ? "(Recomendado)" : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <span>Visibilidad de Plantilla</span>
                </label>
                <div className="flex items-center gap-2 pt-1">
                  <button
                    type="button"
                    data-testid="template-public-toggle"
                    onClick={() => setIsPublic(!isPublic)}
                    className={cn(
                      "flex items-center gap-2 h-10 px-4 rounded-xl border text-xs font-bold transition-all cursor-pointer",
                      isPublic
                        ? "bg-blue-600/15 text-blue-600 border-blue-600/30 font-black"
                        : "bg-amber-500/15 text-amber-600 border-amber-500/30 font-black"
                    )}
                  >
                    {isPublic ? (
                      <>
                        <Globe className="h-4 w-4" />
                        <span>Pública para toda el área</span>
                      </>
                    ) : (
                      <>
                        <Star className="h-4 w-4" />
                        <span>Privada (Solo tú)</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Selector de Productos */}
            <div className="space-y-3">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div>
                  <h4 className="text-xs font-black uppercase tracking-wider text-foreground">
                    Productos Incluidos ({selectedProductIds.length})
                  </h4>
                  <p className="text-[11px] text-muted-foreground">
                    Selecciona los productos que aparecerán en esta vista
                  </p>
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <div className="relative flex-1 sm:w-48">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <input
                      type="text"
                      data-testid="template-product-search"
                      placeholder="Buscar producto..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full h-8 pl-8 pr-2 rounded-lg border border-border bg-background text-xs text-foreground focus:outline-none"
                    />
                  </div>

                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="h-8 px-2 rounded-lg border border-border bg-background text-xs font-bold text-muted-foreground cursor-pointer"
                  >
                    <option value="all">Todas</option>
                    {categorias.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nombre}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Grid de Productos con Checkboxes */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-48 overflow-y-auto p-2 border border-border rounded-2xl bg-muted/20 custom-scrollbar">
                {filteredProducts.map((p) => {
                  const isChecked = selectedProductIds.includes(p.id);
                  return (
                    <button
                      type="button"
                      key={p.id}
                      data-testid={`template-product-checkbox-${p.id}`}
                      onClick={() => toggleProduct(p.id)}
                      className={cn(
                        "flex items-center gap-2.5 p-2 rounded-xl border text-left transition-all cursor-pointer select-none",
                        isChecked
                          ? "bg-primary/10 border-primary text-foreground shadow-sm"
                          : "bg-card border-border hover:border-border/80 text-muted-foreground"
                      )}
                    >
                      <div
                        className={cn(
                          "h-5 w-5 rounded-lg border flex items-center justify-center shrink-0 transition-colors",
                          isChecked
                            ? "bg-primary border-primary text-primary-foreground"
                            : "border-border bg-background"
                        )}
                      >
                        {isChecked && <Check className="h-3 w-3 stroke-[3]" />}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-bold truncate text-foreground">
                          {p.nombre}
                        </p>
                        {p.sku && (
                          <p className="text-[10px] text-muted-foreground">
                            SKU: {p.sku}
                          </p>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Ordenamiento de Productos Seleccionados */}
              {selectedProductIds.length > 0 && (
                <div className="space-y-2 pt-2">
                  <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Orden de Visualización (Arrastra o reordena)
                  </p>
                  <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto p-2 border border-border rounded-xl bg-muted/10">
                    {selectedProductIds.map((pId, idx) => {
                      const prod = productos.find((p) => p.id === pId);
                      return (
                        <div
                          key={pId}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-border bg-card text-xs font-bold shadow-sm"
                        >
                          <span className="truncate max-w-[120px]">
                            {prod?.nombre || pId}
                          </span>
                          <div className="flex items-center gap-0.5 text-muted-foreground">
                            <button
                              type="button"
                              disabled={idx === 0}
                              onClick={() => moveProductOrder(idx, "up")}
                              className="hover:text-foreground disabled:opacity-30 cursor-pointer"
                              title="Subir"
                            >
                              <ArrowUp className="h-3 w-3" />
                            </button>
                            <button
                              type="button"
                              disabled={idx === selectedProductIds.length - 1}
                              onClick={() => moveProductOrder(idx, "down")}
                              className="hover:text-foreground disabled:opacity-30 cursor-pointer"
                              title="Bajar"
                            >
                              <ArrowDown className="h-3 w-3" />
                            </button>
                            <button
                              type="button"
                              onClick={() => toggleProduct(pId)}
                              className="hover:text-destructive text-muted-foreground ml-1 cursor-pointer"
                              title="Quitar"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer de Acciones */}
          <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between shrink-0">
            <div>
              {initialTemplate && onDeleteTemplate && (
                <button
                  type="button"
                  data-testid="template-delete-btn"
                  onClick={handleDelete}
                  disabled={isSaving}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold text-destructive hover:bg-destructive/10 transition-colors cursor-pointer"
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Eliminar</span>
                </button>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                className="px-4 py-2 rounded-xl border border-border text-xs font-bold hover:bg-muted transition-colors cursor-pointer text-muted-foreground hover:text-foreground"
              >
                Cancelar
              </button>

              <button
                type="submit"
                data-testid="template-save-btn"
                disabled={isSaving || !name.trim()}
                className="px-5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-black uppercase tracking-wider hover:opacity-90 disabled:opacity-50 transition-all cursor-pointer shadow-md"
              >
                {isSaving ? "Guardando..." : "Guardar Plantilla"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ConsumoTemplateModal;
