import { useState, useMemo } from "react";
import {
  Boxes,
  Award,
  Package,
  Plus,
  Pencil,
  Trash2,
  Search,
  Check,
  X,
  AlertTriangle,
} from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { cn } from "@/shared/lib/utils";
import { toast } from "sonner";
import type { Marca, TipoEnvase, Producto } from "../types";

export interface FamiliaProductoItem {
  id: string;
  nombre: string;
  color?: string;
  icono?: string;
}

export interface CatalogosManagerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultTab?: "familias" | "marcas" | "envases";
  marcas: Marca[];
  tiposEnvase: TipoEnvase[];
  productos?: Producto[];
  onCreateBrand: (nombre: string, logo_url?: string | null) => Promise<void>;
  onUpdateBrand?: (id: string, nombre: string, logo_url?: string | null) => Promise<void>;
  onDeleteBrand?: (id: string) => Promise<void>;
  onCreateTipoEnvase: (nombre: string, icono?: string | null) => Promise<void>;
  onUpdateTipoEnvase?: (id: string, nombre: string, icono?: string | null) => Promise<void>;
  onDeleteTipoEnvase?: (id: string) => Promise<void>;
  onSuccess?: () => void;
}

const INITIAL_FAMILIAS: FamiliaProductoItem[] = [
  { id: "fam-carnes", nombre: "Carnes y Proteínas", color: "#EF4444" },
  { id: "fam-lacteos", nombre: "Lácteos y Derivados", color: "#3B82F6" },
  { id: "fam-bebidas", nombre: "Licores y Bebidas", color: "#8B5CF6" },
  { id: "fam-abarrotes", nombre: "Abarrotes y Secos", color: "#F59E0B" },
];

export function CatalogosManagerDialog({
  open,
  onOpenChange,
  defaultTab = "familias",
  marcas,
  tiposEnvase,
  productos = [],
  onCreateBrand,
  onUpdateBrand,
  onDeleteBrand,
  onCreateTipoEnvase,
  onUpdateTipoEnvase,
  onDeleteTipoEnvase,
  onSuccess,
}: CatalogosManagerDialogProps) {
  const [activeTab, setActiveTab] = useState<"familias" | "marcas" | "envases">(defaultTab);
  const [search, setSearch] = useState("");

  // Familias locales con soporte offline
  const [familias, setFamilias] = useState<FamiliaProductoItem[]>(() => {
    try {
      const saved = typeof window !== "undefined" ? window.localStorage.getItem("oppytec_familias_v1") : null;
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {
      // ignore
    }
    return INITIAL_FAMILIAS;
  });

  // Modal Crear/Editar Ítem
  const [showItemModal, setShowItemModal] = useState(false);
  const [editingItem, setEditingItem] = useState<{
    id?: string;
    nombre: string;
    extra?: string; // logo_url o icono o color
  } | null>(null);

  // Modal Confirmar Eliminación
  const [deleteConfirmTarget, setDeleteConfirmTarget] = useState<{
    type: "familias" | "marcas" | "envases";
    id: string;
    nombre: string;
    productCount: number;
  } | null>(null);

  // Recuento de productos por marca
  const countByBrand = useMemo(() => {
    const counts: Record<string, number> = {};
    productos.forEach((p) => {
      const key = p.marca_id || p.marca;
      if (key) {
        counts[key] = (counts[key] || 0) + 1;
      }
    });
    return counts;
  }, [productos]);

  // Recuento de productos por tipo envase
  const countByEnvase = useMemo(() => {
    const counts: Record<string, number> = {};
    productos.forEach((p) => {
      const key = p.tipo_envase_id;
      if (key) {
        counts[key] = (counts[key] || 0) + 1;
      }
    });
    return counts;
  }, [productos]);

  // Filtrado de elementos por pestaña y búsqueda
  const filteredFamilias = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return familias;
    return familias.filter((f) => f.nombre.toLowerCase().includes(q));
  }, [familias, search]);

  const filteredMarcas = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return marcas;
    return marcas.filter((m) => m.nombre.toLowerCase().includes(q));
  }, [marcas, search]);

  const filteredEnvases = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return tiposEnvase;
    return tiposEnvase.filter((e) => e.nombre.toLowerCase().includes(q));
  }, [tiposEnvase, search]);

  // Iniciar creación
  const handleOpenCreate = () => {
    setEditingItem({ nombre: "", extra: "" });
    setShowItemModal(true);
  };

  // Iniciar edición
  const handleOpenEdit = (id: string, nombre: string, extra?: string) => {
    setEditingItem({ id, nombre, extra: extra || "" });
    setShowItemModal(true);
  };

  // Guardar ítem según pestaña activa
  const handleSaveItem = async () => {
    if (!editingItem?.nombre.trim()) {
      toast.error("El nombre es requerido");
      return;
    }

    const name = editingItem.nombre.trim();
    const extra = editingItem.extra?.trim() || null;

    try {
      if (activeTab === "familias") {
        if (editingItem.id) {
          setFamilias((prev) => {
            const next = prev.map((f) =>
              f.id === editingItem.id ? { ...f, nombre: name } : f
            );
            window.localStorage?.setItem("oppytec_familias_v1", JSON.stringify(next));
            return next;
          });
          toast.success("Familia actualizada");
        } else {
          const newFam: FamiliaProductoItem = {
            id: `fam-${Date.now()}`,
            nombre: name,
            color: "#6366F1",
          };
          setFamilias((prev) => {
            const next = [...prev, newFam];
            window.localStorage?.setItem("oppytec_familias_v1", JSON.stringify(next));
            return next;
          });
          toast.success("Familia creada");
        }
      } else if (activeTab === "marcas") {
        if (editingItem.id && onUpdateBrand) {
          await onUpdateBrand(editingItem.id, name, extra);
        } else {
          await onCreateBrand(name, extra);
        }
      } else if (activeTab === "envases") {
        if (editingItem.id && onUpdateTipoEnvase) {
          await onUpdateTipoEnvase(editingItem.id, name, extra);
        } else {
          await onCreateTipoEnvase(name, extra);
        }
      }

      setShowItemModal(false);
      setEditingItem(null);
      onSuccess?.();
    } catch {
      // Handled
    }
  };

  // Confirmar eliminación
  const handleConfirmDelete = async () => {
    if (!deleteConfirmTarget) return;

    try {
      if (deleteConfirmTarget.type === "familias") {
        setFamilias((prev) => {
          const next = prev.filter((f) => f.id !== deleteConfirmTarget.id);
          window.localStorage?.setItem("oppytec_familias_v1", JSON.stringify(next));
          return next;
        });
        toast.success("Familia eliminada");
      } else if (deleteConfirmTarget.type === "marcas") {
        if (onDeleteBrand) {
          await onDeleteBrand(deleteConfirmTarget.id);
        } else {
          toast.success("Marca eliminada");
        }
      } else if (deleteConfirmTarget.type === "envases") {
        if (onDeleteTipoEnvase) {
          await onDeleteTipoEnvase(deleteConfirmTarget.id);
        } else {
          toast.success("Tipo de envase eliminado");
        }
      }

      setDeleteConfirmTarget(null);
      onSuccess?.();
    } catch {
      // Handled
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={() => onOpenChange(false)}
      title="Gestión de Catálogos Maestros"
      description="Administra familias de productos, marcas comerciales y formatos de envases."
      maxWidth="max-w-4xl"
    >
      <div className="space-y-4 py-1 text-foreground" data-testid="catalogos-manager-dialog">
        {/* NAVEGACIÓN POR PESTAÑAS */}
        <div className="flex items-center gap-2 border-b border-border pb-2 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab("familias")}
            data-testid="tab-familias"
            className={cn(
              "touch-target inline-flex min-h-[44px] px-4 items-center gap-2 rounded-xl text-xs font-bold transition-all cursor-pointer select-none whitespace-nowrap",
              activeTab === "familias"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/40 text-muted-foreground hover:text-foreground"
            )}
          >
            <Boxes className="h-4 w-4" />
            <span>Familias ({familias.length})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("marcas")}
            data-testid="tab-marcas"
            className={cn(
              "touch-target inline-flex min-h-[44px] px-4 items-center gap-2 rounded-xl text-xs font-bold transition-all cursor-pointer select-none whitespace-nowrap",
              activeTab === "marcas"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/40 text-muted-foreground hover:text-foreground"
            )}
          >
            <Award className="h-4 w-4" />
            <span>Marcas ({marcas.length})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("envases")}
            data-testid="tab-envases"
            className={cn(
              "touch-target inline-flex min-h-[44px] px-4 items-center gap-2 rounded-xl text-xs font-bold transition-all cursor-pointer select-none whitespace-nowrap",
              activeTab === "envases"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-secondary/40 text-muted-foreground hover:text-foreground"
            )}
          >
            <Package className="h-4 w-4" />
            <span>Formatos y Envases ({tiposEnvase.length})</span>
          </button>
        </div>

        {/* BARRA DE ACCIÓN Y BÚSQUEDA */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              placeholder={`Buscar en ${activeTab}...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              data-testid="input-catalog-search"
              className="w-full h-10 min-h-[40px] pl-9 pr-3 rounded-xl bg-card border border-input text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <button
            type="button"
            onClick={handleOpenCreate}
            data-testid="btn-nuevo-catalogo-item"
            className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center gap-1.5 rounded-xl bg-primary text-xs font-bold text-primary-foreground hover:bg-primary/90 shadow-sm cursor-pointer select-none"
          >
            <Plus className="h-4 w-4" />
            <span>
              + Nuevo{" "}
              {activeTab === "familias"
                ? "Familia"
                : activeTab === "marcas"
                ? "Marca"
                : "Envase"}
            </span>
          </button>
        </div>

        {/* LISTA DINÁMICA SEGÚN PESTAÑA */}
        <div className="rounded-xl border border-border bg-card divide-y divide-border max-h-[360px] overflow-y-auto custom-scrollbar">
          {activeTab === "familias" && (
            <>
              {filteredFamilias.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No hay familias registradas. Presiona "+ Nuevo Familia" para agregar una.
                </div>
              ) : (
                filteredFamilias.map((fam) => (
                  <div
                    key={fam.id}
                    data-testid={`familia-item-${fam.id}`}
                    className="flex items-center justify-between p-3 hover:bg-secondary/20 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0 text-white"
                        style={{ backgroundColor: fam.color || "#6366F1" }}
                      >
                        <Boxes className="h-4 w-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-foreground">{fam.nombre}</h4>
                        <span className="text-[10px] text-muted-foreground">Familia de catálogo</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleOpenEdit(fam.id, fam.nombre, fam.color)}
                        data-testid={`btn-edit-fam-${fam.id}`}
                        className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:text-foreground hover:bg-secondary cursor-pointer"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          setDeleteConfirmTarget({
                            type: "familias",
                            id: fam.id,
                            nombre: fam.nombre,
                            productCount: 0,
                          })
                        }
                        data-testid={`btn-delete-fam-${fam.id}`}
                        className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </>
          )}

          {activeTab === "marcas" && (
            <>
              {filteredMarcas.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No hay marcas registradas. Presiona "+ Nuevo Marca" para agregar una.
                </div>
              ) : (
                filteredMarcas.map((m) => {
                  const pCount = countByBrand[m.id] || countByBrand[m.nombre] || 0;
                  return (
                    <div
                      key={m.id}
                      data-testid={`marca-item-${m.id}`}
                      className="flex items-center justify-between p-3 hover:bg-secondary/20 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                          <Award className="h-4 w-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-foreground">{m.nombre}</h4>
                          <span className="text-[10px] text-muted-foreground">
                            {pCount} {pCount === 1 ? "producto vinculado" : "productos vinculados"}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleOpenEdit(m.id, m.nombre, m.logo_url || "")}
                          data-testid={`btn-edit-marca-${m.id}`}
                          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:text-foreground hover:bg-secondary cursor-pointer"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            setDeleteConfirmTarget({
                              type: "marcas",
                              id: m.id,
                              nombre: m.nombre,
                              productCount: pCount,
                            })
                          }
                          data-testid={`btn-delete-marca-${m.id}`}
                          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </>
          )}

          {activeTab === "envases" && (
            <>
              {filteredEnvases.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No hay envases registrados. Presiona "+ Nuevo Envase" para agregar uno.
                </div>
              ) : (
                filteredEnvases.map((env) => {
                  const pCount = countByEnvase[env.id] || countByEnvase[env.nombre] || 0;
                  return (
                    <div
                      key={env.id}
                      data-testid={`envase-item-${env.id}`}
                      className="flex items-center justify-between p-3 hover:bg-secondary/20 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                          <Package className="h-4 w-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-foreground">{env.nombre}</h4>
                          <span className="text-[10px] text-muted-foreground">
                            {pCount} {pCount === 1 ? "producto vinculado" : "productos vinculados"}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleOpenEdit(env.id, env.nombre, env.icono || "")}
                          data-testid={`btn-edit-env-${env.id}`}
                          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:text-foreground hover:bg-secondary cursor-pointer"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            setDeleteConfirmTarget({
                              type: "envases",
                              id: env.id,
                              nombre: env.nombre,
                              productCount: pCount,
                            })
                          }
                          data-testid={`btn-delete-env-${env.id}`}
                          className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </>
          )}
        </div>

        {/* SUB-MODAL CREAR / EDITAR ÍTEM */}
        {showItemModal && editingItem && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 backdrop-blur-xs">
            <div
              className="glass-card w-full max-w-md rounded-2xl border border-border p-5 shadow-2xl bg-card space-y-4"
              data-testid="modal-form-catalog-item"
            >
              <div className="flex items-center justify-between border-b border-border pb-2">
                <h4 className="text-xs font-black uppercase text-foreground">
                  {editingItem.id ? "Editar" : "Nuevo"}{" "}
                  {activeTab === "familias"
                    ? "Familia"
                    : activeTab === "marcas"
                    ? "Marca"
                    : "Envase"}
                </h4>
                <button
                  type="button"
                  onClick={() => setShowItemModal(false)}
                  className="p-1 rounded text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
                  Nombre *
                </label>
                <input
                  type="text"
                  placeholder={`Ej. ${
                    activeTab === "familias"
                      ? "Abarrotes"
                      : activeTab === "marcas"
                      ? "Coca Cola"
                      : "Botella Vidrio 750ml"
                  }`}
                  value={editingItem.nombre}
                  onChange={(e) =>
                    setEditingItem((prev) => (prev ? { ...prev, nombre: e.target.value } : null))
                  }
                  data-testid="input-catalog-item-name"
                  className="w-full h-11 px-3 rounded-xl bg-background border border-input text-xs font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowItemModal(false)}
                  className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center rounded-xl bg-secondary text-xs font-bold text-secondary-foreground hover:bg-secondary/80 cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleSaveItem}
                  data-testid="btn-save-catalog-item"
                  className="touch-target inline-flex min-h-[44px] px-5 items-center justify-center gap-1.5 rounded-xl bg-primary text-xs font-bold text-primary-foreground hover:bg-primary/90 shadow-md cursor-pointer"
                >
                  <Check className="h-4 w-4 stroke-[3]" />
                  <span>Guardar</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* DIÁLOGO DE CONFIRMACIÓN DE ELIMINACIÓN */}
        {deleteConfirmTarget && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 backdrop-blur-xs">
            <div
              className="glass-card w-full max-w-md rounded-2xl border border-destructive/40 p-5 shadow-2xl bg-card space-y-3"
              data-testid="confirm-delete-catalog-dialog"
            >
              <div className="flex items-center gap-2 text-destructive font-black">
                <AlertTriangle className="h-5 w-5" />
                <h4 className="text-sm uppercase">Confirmar Eliminación</h4>
              </div>
              <p className="text-xs text-foreground font-medium">
                ¿Deseas eliminar "{deleteConfirmTarget.nombre}"?
              </p>
              {deleteConfirmTarget.productCount > 0 && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 text-xs">
                  ⚠️ Atención: Hay {deleteConfirmTarget.productCount} producto(s) vinculado(s) a este registro.
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setDeleteConfirmTarget(null)}
                  className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center rounded-xl bg-secondary text-xs font-bold text-secondary-foreground hover:bg-secondary/80 cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleConfirmDelete}
                  data-testid="btn-confirm-delete-catalog"
                  className="touch-target inline-flex min-h-[44px] px-4 items-center justify-center gap-1.5 rounded-xl bg-destructive text-xs font-bold text-destructive-foreground hover:bg-destructive/90 shadow-sm cursor-pointer"
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Eliminar</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* PIE DEL DIÁLOGO PRINCIPAL */}
        <div className="flex justify-end gap-2 pt-3 border-t border-border">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            data-testid="btn-close-catalogos"
            className="touch-target inline-flex min-h-[44px] px-5 items-center justify-center rounded-xl bg-primary text-xs font-bold text-primary-foreground hover:bg-primary/90 shadow-sm cursor-pointer select-none"
          >
            Listo / Cerrar
          </button>
        </div>
      </div>
    </ResponsiveDialog>
  );
}
