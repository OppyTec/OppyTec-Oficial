import { useState, useMemo } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  Check,
  Building2,
  Layers,
  AlertTriangle,
  Search,
  Palette,
  X,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { CategoryIcon } from "@/shared/components/ui/CategoryIcon";
import { cn } from "@/shared/lib/utils";
import { toast } from "sonner";
import type { Categoria, Producto } from "../types";

export interface AreaOperativa {
  id: string;
  nombre: string;
  icono?: string;
  color?: string;
}

export interface AdministradorCategoriasDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  categorias: Categoria[];
  areas?: AreaOperativa[];
  productos?: Producto[];
  onCreateCategory: (nombre: string, meta?: Partial<Categoria>) => Promise<void>;
  onUpdateCategory: (id: string, nombre: string, meta?: Partial<Categoria>) => Promise<void>;
  onDeleteCategory: (id: string) => Promise<void>;
  onAssignCategoryArea?: (categoriaId: string, areaIds: string[]) => Promise<void>;
}

export const PRESET_COLORS = [
  "#EF4444", // Rojo
  "#F97316", // Naranja
  "#F59E0B", // Ámbar
  "#10B981", // Esmeralda
  "#06B6D4", // Cian
  "#3B82F6", // Azul
  "#6366F1", // Índigo
  "#8B5CF6", // Púrpura
  "#EC4899", // Rosa
  "#64748B", // Pizarra
];

export const AVAILABLE_ICONS = [
  "Tag",
  "Utensils",
  "ChefHat",
  "Coffee",
  "Wine",
  "Beer",
  "GlassWater",
  "IceCream",
  "Cake",
  "Pizza",
  "Package",
  "Box",
  "Boxes",
  "ShoppingBag",
  "Warehouse",
  "Store",
  "Sparkles",
  "Briefcase",
  "Layers",
  "BadgeCheck",
];

const DEFAULT_AREAS: AreaOperativa[] = [
  { id: "area-cocina", nombre: "Cocina Caliente", icono: "ChefHat", color: "#EF4444" },
  { id: "area-bar", nombre: "Bar & Cava", icono: "Wine", color: "#8B5CF6" },
  { id: "area-bodega", nombre: "Bodega Central", icono: "Warehouse", color: "#3B82F6" },
  { id: "area-salon", nombre: "Salón & Comedor", icono: "Utensils", color: "#10B981" },
];

export function AdministradorCategoriasDialog({
  open,
  onOpenChange,
  categorias,
  areas = DEFAULT_AREAS,
  productos = [],
  onCreateCategory,
  onUpdateCategory,
  onDeleteCategory,
  onAssignCategoryArea,
}: AdministradorCategoriasDialogProps) {
  // Tabs: "catalogo" | "areas"
  const [activeTab, setActiveTab] = useState<"catalogo" | "areas">("catalogo");
  const [searchCat, setSearchCat] = useState("");

  // Sub-modal: Crear / Editar Categoría
  const [isEditing, setIsEditing] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Categoria | null>(null);
  const [formNombre, setFormNombre] = useState("");
  const [formColor, setFormColor] = useState(PRESET_COLORS[0]);
  const [formIcono, setFormIcono] = useState("Tag");
  const [formTipo, setFormTipo] = useState<"insumo" | "producto_terminado" | "activo_fijo" | "servicio">("insumo");

  // Sub-modal: Confirmación de Eliminación con productos vinculados
  const [deleteCandidate, setDeleteCandidate] = useState<Categoria | null>(null);

  // Mapeo interactivo local de categorías por área
  const [localAreaMappings, setLocalAreaMappings] = useState<Record<string, Set<string>>>(() => {
    const map: Record<string, Set<string>> = {};
    areas.forEach((a) => {
      map[a.id] = new Set<string>();
    });
    categorias.forEach((cat) => {
      (cat.area_operativa_ids || []).forEach((areaId) => {
        if (!map[areaId]) map[areaId] = new Set<string>();
        map[areaId].add(cat.id);
      });
    });
    return map;
  });

  // Conteo de productos vinculados por categoría
  const productCountByCat = useMemo(() => {
    const counts: Record<string, number> = {};
    productos.forEach((p) => {
      if (p.categoria_id) {
        counts[p.categoria_id] = (counts[p.categoria_id] || 0) + 1;
      }
    });
    return counts;
  }, [productos]);

  // Categorías filtradas por buscador
  const filteredCategorias = useMemo(() => {
    if (!searchCat.trim()) return categorias;
    const q = searchCat.toLowerCase().trim();
    return categorias.filter(
      (c) =>
        c.nombre.toLowerCase().includes(q) ||
        (c.tipo_categoria && c.tipo_categoria.toLowerCase().includes(q))
    );
  }, [categorias, searchCat]);

  // Iniciar creación de categoría
  const handleOpenCreate = () => {
    setEditingCategory(null);
    setFormNombre("");
    setFormColor(PRESET_COLORS[Math.floor(Math.random() * PRESET_COLORS.length)]);
    setFormIcono("Tag");
    setFormTipo("insumo");
    setIsEditing(true);
  };

  // Iniciar edición de categoría
  const handleOpenEdit = (cat: Categoria) => {
    setEditingCategory(cat);
    setFormNombre(cat.nombre);
    setFormColor(cat.color || PRESET_COLORS[0]);
    setFormIcono(cat.icono || "Tag");
    setFormTipo((cat.tipo_categoria as any) || "insumo");
    setIsEditing(true);
  };

  // Guardar categoría (crear o actualizar)
  const handleSaveCategory = async () => {
    if (!formNombre.trim()) {
      toast.error("El nombre de la categoría es obligatorio");
      return;
    }

    try {
      if (editingCategory) {
        await onUpdateCategory(editingCategory.id, formNombre.trim(), {
          color: formColor,
          icono: formIcono,
          tipo_categoria: formTipo,
        });
      } else {
        await onCreateCategory(formNombre.trim(), {
          color: formColor,
          icono: formIcono,
          tipo_categoria: formTipo,
        });
      }
      setIsEditing(false);
      setEditingCategory(null);
    } catch {
      // Error handled by parent or toast
    }
  };

  // Confirmar eliminación
  const handleConfirmDelete = async () => {
    if (!deleteCandidate) return;
    try {
      await onDeleteCategory(deleteCandidate.id);
      setDeleteCandidate(null);
    } catch {
      // handled
    }
  };

  // Toggle asignación de categoría a un área
  const handleToggleAreaMapping = (areaId: string, categoriaId: string) => {
    setLocalAreaMappings((prev) => {
      const next = { ...prev };
      const currentSet = new Set(next[areaId] || []);
      if (currentSet.has(categoriaId)) {
        currentSet.delete(categoriaId);
      } else {
        currentSet.add(categoriaId);
      }
      next[areaId] = currentSet;

      // Llamar callback opcional si existe
      if (onAssignCategoryArea) {
        const areaIdsForCat = Object.entries(next)
          .filter(([_, set]) => set.has(categoriaId))
          .map(([aId]) => aId);
        onAssignCategoryArea(categoriaId, areaIdsForCat).catch(() => {});
      }

      return next;
    });
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={() => onOpenChange(false)}
      title="Administrador de Categorías y Áreas"
      description="Configura el catálogo de categorías, sus íconos y colores, y su distribución por áreas operativas."
      maxWidth="max-w-4xl"
    >
      <div className="space-y-4 py-1 text-foreground" data-testid="admin-categorias-dialog">
        {/* NAVEGACIÓN POR PESTAÑAS */}
        <div className="flex items-center gap-2 border-b border-border pb-2">
          <button
            type="button"
            onClick={() => setActiveTab("catalogo")}
            data-testid="tab-catalogo"
            className={cn(
              "touch-target inline-flex min-h-[44px] px-4 items-center gap-2 rounded-xl text-xs font-bold transition-all cursor-pointer select-none",
              activeTab === "catalogo"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/40 text-muted-foreground hover:text-foreground"
            )}
          >
            <Layers className="h-4 w-4" />
            <span>Catálogo de Categorías ({categorias.length})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("areas")}
            data-testid="tab-areas"
            className={cn(
              "touch-target inline-flex min-h-[44px] px-4 items-center gap-2 rounded-xl text-xs font-bold transition-all cursor-pointer select-none",
              activeTab === "areas"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/40 text-muted-foreground hover:text-foreground"
            )}
          >
            <Building2 className="h-4 w-4" />
            <span>Áreas Operativas ({areas.length})</span>
          </button>
        </div>

        {/* PESTAÑA 1: CATÁLOGO DE CATEGORÍAS */}
        {activeTab === "catalogo" && (
          <div className="space-y-3">
            {/* BARRA SUPERIOR DE ACCIÓN Y BÚSQUEDA */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                <input
                  type="text"
                  placeholder="Buscar categoría por nombre o tipo..."
                  value={searchCat}
                  onChange={(e) => setSearchCat(e.target.value)}
                  data-testid="input-search-categoria"
                  className="w-full h-10 min-h-[40px] pl-9 pr-3 rounded-xl bg-card border border-input text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <button
                type="button"
                onClick={handleOpenCreate}
                data-testid="btn-nueva-categoria"
                className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center gap-1.5 rounded-xl bg-primary text-xs font-bold text-primary-foreground hover:bg-primary/90 shadow-sm cursor-pointer select-none"
              >
                <Plus className="h-4 w-4" />
                <span>+ Nueva Categoría</span>
              </button>
            </div>

            {/* LISTA DE CATEGORÍAS */}
            <div className="rounded-xl border border-border bg-card divide-y divide-border max-h-[360px] overflow-y-auto custom-scrollbar">
              {filteredCategorias.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No se encontraron categorías. Presiona "+ Nueva Categoría" para crear la primera.
                </div>
              ) : (
                filteredCategorias.map((cat) => {
                  const pCount = productCountByCat[cat.id] || 0;
                  return (
                    <div
                      key={cat.id}
                      data-testid={`categoria-item-${cat.id}`}
                      className="flex items-center justify-between p-3 hover:bg-secondary/20 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className="h-9 w-9 rounded-xl flex items-center justify-center shrink-0 shadow-xs border border-white/10"
                          style={{ backgroundColor: cat.color || "#6366F1" }}
                        >
                          <CategoryIcon
                            name={cat.icono || "Tag"}
                            className="h-4 w-4 text-white"
                          />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-foreground truncate">
                              {cat.nombre}
                            </span>
                            <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground">
                              {cat.tipo_categoria || "Insumo"}
                            </span>
                          </div>
                          <p className="text-[11px] text-muted-foreground">
                            {pCount} {pCount === 1 ? "producto vinculado" : "productos vinculados"}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleOpenEdit(cat)}
                          data-testid={`btn-edit-cat-${cat.id}`}
                          title="Editar categoría"
                          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:text-foreground hover:bg-secondary cursor-pointer"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleteCandidate(cat)}
                          data-testid={`btn-delete-cat-${cat.id}`}
                          title="Eliminar categoría"
                          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* PESTAÑA 2: ÁREAS OPERATIVAS (MATRIZ INTERACTIVA) */}
        {activeTab === "areas" && (
          <div className="space-y-3">
            <div className="p-3 rounded-xl bg-secondary/20 border border-border text-xs text-muted-foreground">
              Define la visibilidad operativa de cada categoría activando las casillas de las áreas correspondientes.
            </div>

            <div className="rounded-xl border border-border bg-card overflow-x-auto max-h-[380px] custom-scrollbar">
              <table className="w-full text-xs text-left border-collapse">
                <thead className="bg-secondary/40 text-muted-foreground font-black uppercase text-[10px] sticky top-0 z-10 border-b border-border">
                  <tr>
                    <th className="p-3">Categoría</th>
                    {areas.map((area) => (
                      <th key={area.id} className="p-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <span
                            className="h-2 w-2 rounded-full"
                            style={{ backgroundColor: area.color || "#3B82F6" }}
                          />
                          <span>{area.nombre}</span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {categorias.map((cat) => (
                    <tr key={cat.id} className="hover:bg-secondary/15 transition-colors">
                      <td className="p-3 font-semibold text-foreground flex items-center gap-2">
                        <span
                          className="h-3 w-3 rounded-full shrink-0"
                          style={{ backgroundColor: cat.color || "#6366F1" }}
                        />
                        <span className="truncate">{cat.nombre}</span>
                      </td>
                      {areas.map((area) => {
                        const isAssigned = Boolean(localAreaMappings[area.id]?.has(cat.id));
                        return (
                          <td key={area.id} className="p-3 text-center">
                            <label className="inline-flex items-center justify-center cursor-pointer min-h-[44px] min-w-[44px]">
                              <input
                                type="checkbox"
                                checked={isAssigned}
                                onChange={() => handleToggleAreaMapping(area.id, cat.id)}
                                data-testid={`matrix-check-${area.id}-${cat.id}`}
                                className="h-4 w-4 rounded text-primary focus:ring-primary cursor-pointer"
                              />
                            </label>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* SUB-MODAL / FORMULARIO: CREAR O EDITAR CATEGORÍA */}
        {isEditing && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 backdrop-blur-xs">
            <div
              className="glass-card w-full max-w-lg rounded-2xl border border-border p-5 shadow-2xl bg-card space-y-4 max-h-[90vh] overflow-y-auto"
              data-testid="modal-form-categoria"
            >
              <div className="flex items-center justify-between border-b border-border pb-2">
                <div className="flex items-center gap-2">
                  <Palette className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-black uppercase text-foreground">
                    {editingCategory ? "Editar Categoría" : "Nueva Categoría"}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="p-1 rounded-lg text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Vista previa en vivo */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-secondary/30 border border-border">
                <div
                  className="h-11 w-11 rounded-xl flex items-center justify-center shrink-0 shadow-md text-white border border-white/20"
                  style={{ backgroundColor: formColor }}
                >
                  <CategoryIcon name={formIcono} className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-foreground">
                    {formNombre || "Nombre de Categoría"}
                  </h4>
                  <span className="text-[10px] uppercase font-black px-2 py-0.5 rounded bg-secondary text-secondary-foreground">
                    {formTipo}
                  </span>
                </div>
              </div>

              {/* Campo Nombre */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
                  Nombre de Categoría *
                </label>
                <input
                  type="text"
                  placeholder="Ej. Carnes y Vacunos"
                  value={formNombre}
                  onChange={(e) => setFormNombre(e.target.value)}
                  data-testid="input-cat-name"
                  className="w-full h-11 px-3 rounded-xl bg-background border border-input text-xs font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
              </div>

              {/* Campo Tipo de Categoría */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
                  Tipo de Categoría
                </label>
                <select
                  value={formTipo}
                  onChange={(e) => setFormTipo(e.target.value as any)}
                  data-testid="select-cat-tipo"
                  className="w-full h-11 px-3 rounded-xl bg-background border border-input text-xs font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="insumo">Insumo</option>
                  <option value="producto_terminado">Producto Terminado</option>
                  <option value="activo_fijo">Activo Fijo</option>
                  <option value="servicio">Servicio</option>
                </select>
              </div>

              {/* Selector de Color */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                  Color Distintivo
                </label>
                <div className="grid grid-cols-5 gap-2">
                  {PRESET_COLORS.map((col) => (
                    <button
                      key={col}
                      type="button"
                      onClick={() => setFormColor(col)}
                      data-testid={`color-swatch-${col}`}
                      className={cn(
                        "h-9 rounded-xl flex items-center justify-center transition-all cursor-pointer border-2",
                        formColor === col ? "border-primary scale-105 shadow-md" : "border-transparent hover:scale-102"
                      )}
                      style={{ backgroundColor: col }}
                    >
                      {formColor === col && <Check className="h-4 w-4 text-white stroke-[3]" />}
                    </button>
                  ))}
                </div>
              </div>

              {/* Selector de Ícono */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                  Ícono Representativo
                </label>
                <div className="grid grid-cols-5 sm:grid-cols-6 gap-2 max-h-36 overflow-y-auto p-1 custom-scrollbar">
                  {AVAILABLE_ICONS.map((iconName) => (
                    <button
                      key={iconName}
                      type="button"
                      onClick={() => setFormIcono(iconName)}
                      data-testid={`icon-btn-${iconName}`}
                      className={cn(
                        "h-10 rounded-xl border flex items-center justify-center transition-all cursor-pointer",
                        formIcono === iconName
                          ? "bg-primary text-primary-foreground border-primary shadow-xs"
                          : "bg-secondary/20 hover:bg-secondary/50 text-foreground border-border"
                      )}
                    >
                      <CategoryIcon name={iconName} className="h-4 w-4" />
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center rounded-xl bg-secondary text-xs font-bold text-secondary-foreground hover:bg-secondary/80 cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleSaveCategory}
                  data-testid="btn-save-category"
                  className="touch-target inline-flex min-h-[44px] px-5 items-center justify-center gap-1.5 rounded-xl bg-primary text-xs font-bold text-primary-foreground hover:bg-primary/90 shadow-md cursor-pointer"
                >
                  <Check className="h-4 w-4 stroke-[3]" />
                  <span>Guardar Categoría</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* DIÁLOGO DE ADVERTENCIA PARA ELIMINACIÓN CON PRODUCTOS VINCULADOS */}
        {deleteCandidate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 backdrop-blur-xs">
            <div
              className="glass-card w-full max-w-md rounded-2xl border border-destructive/40 p-5 shadow-2xl bg-card space-y-3"
              data-testid="confirm-delete-category-dialog"
            >
              <div className="flex items-center gap-2 text-destructive font-black">
                <AlertTriangle className="h-5 w-5" />
                <h4 className="text-sm uppercase">Confirmar Eliminación</h4>
              </div>
              <p className="text-xs text-foreground font-medium">
                ¿Estás seguro de que deseas eliminar la categoría{" "}
                <span className="font-bold text-destructive">"{deleteCandidate.nombre}"</span>?
              </p>
              {(productCountByCat[deleteCandidate.id] || 0) > 0 && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 text-xs">
                  ⚠️ Advertencia: Hay{" "}
                  <strong>{productCountByCat[deleteCandidate.id]}</strong> producto(s)
                  vinculado(s) a esta categoría. Al eliminarla, quedarán sin categoría asignada.
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setDeleteCandidate(null)}
                  className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center rounded-xl bg-secondary text-xs font-bold text-secondary-foreground hover:bg-secondary/80 cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleConfirmDelete}
                  data-testid="btn-confirm-delete-cat"
                  className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center gap-1.5 rounded-xl bg-destructive text-xs font-bold text-destructive-foreground hover:bg-destructive/90 shadow-sm cursor-pointer"
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Sí, Eliminar</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* PIE DEL MODAL PRINCIPAL */}
        <div className="flex justify-end gap-2 pt-3 border-t border-border">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            data-testid="btn-close-admin-categorias"
            className="touch-target inline-flex min-h-[44px] px-5 items-center justify-center rounded-xl bg-primary text-xs font-bold text-primary-foreground hover:bg-primary/90 shadow-sm cursor-pointer select-none"
          >
            Listo / Cerrar
          </button>
        </div>
      </div>
    </ResponsiveDialog>
  );
}
