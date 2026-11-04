import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertOctagon,
  CheckCircle2,
  Clock,
  Columns,
  ListTodo,
  Play,
  Plus,
  Search,
  Sparkles,
  UserCheck,
  X,
} from "lucide-react";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { useTareas } from "../hooks/useTareas";
import { TareaCard } from "./TareaCard";
import { TareaDialog } from "./TareaDialog";
import { IncompleteTaskDialog } from "./IncompleteTaskDialog";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import { toast } from "sonner";
import { cn } from "@/shared/lib";
import type { PlantillaRutina, Tarea, TareaEstado } from "../types";

export function TareasPage() {
  const { t } = useTranslation("operations");
  const isMobile = useIsMobile();

  // Vista activa: Kanban (desktop por defecto) o Checklist (móvil por defecto)
  const [viewMode, setViewMode] = useState<"kanban" | "checklist">(() =>
    isMobile ? "checklist" : "kanban"
  );
  const [selectedAreaId, setSelectedAreaId] = useState<string>("all");
  const [soloMisTareas, setSoloMisTareas] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Modales
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTarea, setEditingTarea] = useState<Tarea | null>(null);

  // Modal obligatorio de tarea incompleta
  const [incompleteModalTarea, setIncompleteModalTarea] = useState<Tarea | null>(null);

  // Selector de plantillas de rutina
  const [plantillaMenuOpen, setPlantillaMenuOpen] = useState(false);

  const {
    tareas,
    plantillas,
    isLoading,
    createTarea,
    updateTarea,
    updateEstado,
    deleteTarea,
    aplicarPlantilla,
  } = useTareas({
    area_id: selectedAreaId,
    solo_mis_tareas: soloMisTareas,
  });

  // Filtrado reactivo en memoria
  const filteredTareas = useMemo(() => {
    return tareas.filter((item) => {
      if (selectedAreaId !== "all" && item.area_id && item.area_id !== selectedAreaId) {
        return false;
      }
      if (soloMisTareas && item.asignado_a_user_id !== 1) {
        // ID 1 es el usuario logueado en la demo/sesión
        return false;
      }
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase().trim();
      const matchTitle = item.titulo.toLowerCase().includes(q);
      const matchAssignee = item.asignado_a_name?.toLowerCase().includes(q);
      const matchCompra = item.compra_id?.toLowerCase().includes(q);
      return matchTitle || matchAssignee || matchCompra;
    });
  }, [tareas, selectedAreaId, soloMisTareas, searchQuery]);

  // Agrupamiento por columnas Kanban
  const kanbanColumns: Array<{
    id: TareaEstado;
    label: string;
    icon: any;
    colorClass: string;
    items: Tarea[];
  }> = [
    {
      id: "pendiente",
      label: t("activities.tareas.columns.pendiente", { defaultValue: "Pendiente" }),
      icon: Clock,
      colorClass: "text-zinc-400 border-zinc-500/20 bg-zinc-500/5",
      items: filteredTareas.filter((t) => t.estado === "pendiente"),
    },
    {
      id: "progreso",
      label: t("activities.tareas.columns.progreso", { defaultValue: "En Progreso" }),
      icon: Play,
      colorClass: "text-blue-500 border-blue-500/30 bg-blue-500/5",
      items: filteredTareas.filter((t) => t.estado === "progreso"),
    },
    {
      id: "completada",
      label: t("activities.tareas.columns.completada", { defaultValue: "Completada" }),
      icon: CheckCircle2,
      colorClass: "text-emerald-500 border-emerald-500/30 bg-emerald-500/5",
      items: filteredTareas.filter((t) => t.estado === "completada"),
    },
    {
      id: "incompleta",
      label: t("activities.tareas.columns.incompleta", { defaultValue: "Incompleta" }),
      icon: AlertOctagon,
      colorClass: "text-red-500 border-red-500/30 bg-red-500/5",
      items: filteredTareas.filter((t) => t.estado === "incompleta"),
    },
  ];

  const handleOpenCreate = () => {
    setEditingTarea(null);
    setDialogOpen(true);
  };

  const handleOpenEdit = (tarea: Tarea) => {
    setEditingTarea(tarea);
    setDialogOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteTarea(id);
      toast.success(t("activities.common.success_deleted", { defaultValue: "Tarea eliminada" }));
    } catch {
      toast.error(t("activities.tareas.error_delete", { defaultValue: "Error al eliminar la tarea" }));
    }
  };

  const handleStatusChange = async (id: number, estado: TareaEstado) => {
    try {
      await updateEstado({ id, estado });
      toast.success(t("activities.common.success_updated", { defaultValue: "Estado actualizado" }));
    } catch {
      toast.error(t("activities.tareas.error_update_status", { defaultValue: "Error al actualizar estado" }));
    }
  };

  const handleConfirmIncomplete = async (tareaId: number, justificacion: string) => {
    try {
      await updateEstado({
        id: tareaId,
        estado: "incompleta",
        nota_incompleta: justificacion,
      });
      toast.warning(t("activities.tareas.warning_incomplete_marked", { defaultValue: "Tarea marcada como incompleta con registro de auditoría" }));
    } catch {
      toast.error(t("activities.tareas.error_incomplete_mark", { defaultValue: "Error al marcar tarea como incompleta" }));
    }
  };

  const handleSaveTarea = async (data: any) => {
    try {
      if (editingTarea) {
        await updateTarea({ id: editingTarea.id, ...data });
        toast.success(t("activities.common.success_updated", { defaultValue: "Tarea actualizada" }));
      } else {
        await createTarea(data);
        toast.success(t("activities.common.success_created", { defaultValue: "Tarea creada" }));
      }
    } catch {
      toast.error(t("activities.tareas.error_save", { defaultValue: "Error al guardar la tarea" }));
    }
  };

  const handleAplicarRutina = async (plantilla: PlantillaRutina) => {
    setPlantillaMenuOpen(false);
    try {
      await aplicarPlantilla({
        plantillaId: plantilla.id,
        area_id: selectedAreaId === "all" ? plantilla.area_id : selectedAreaId,
      });
      toast.success(t("activities.tareas.template_applied_success", { name: plantilla.nombre, defaultValue: `Rutina "${plantilla.nombre}" aplicada con éxito` }));
    } catch {
      toast.error(t("activities.tareas.error_apply_template", { defaultValue: "Error al aplicar rutina de plantilla" }));
    }
  };

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6 max-w-7xl mx-auto w-full" data-testid="tareas-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <SectionHeader
          icon={ListTodo}
          color="#10B981"
          center={false}
          title={t("activities.tareas.title", { defaultValue: "Tareas Operativas" })}
          subtitle={t("activities.tareas.subtitle", {
            defaultValue: "Gestión de tareas, checklists de apertura/cierre y rutinas de turno",
          })}
        />

        <div className="flex items-center gap-2">
          {/* Botón Aplicar Rutina */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setPlantillaMenuOpen((prev) => !prev)}
              className="inline-flex items-center gap-2 rounded-2xl border border-border bg-card px-3.5 py-2 text-xs font-bold uppercase tracking-wider text-foreground hover:bg-secondary transition-all cursor-pointer shadow-sm"
            >
              <Sparkles className="h-4 w-4 text-amber-500" />
              <span className="hidden sm:inline">
                {t("activities.tareas.apply_template", { defaultValue: "Aplicar Rutina" })}
              </span>
            </button>

            {plantillaMenuOpen && (
              <>
                <div className="fixed inset-0 z-30" onClick={() => setPlantillaMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-1.5 z-40 w-64 rounded-2xl border border-border bg-popover p-2 shadow-2xl">
                  <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border mb-1">
                    {t("activities.tareas.routine_templates", { defaultValue: "Plantillas de Rutina" })}
                  </div>
                  {plantillas.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => handleAplicarRutina(p)}
                      className="flex w-full flex-col items-start rounded-xl p-2 text-left hover:bg-secondary transition-colors"
                    >
                      <span className="text-xs font-bold text-foreground">{p.nombre}</span>
                      <span className="text-[11px] text-muted-foreground">
                        {p.tipo_rutina} • {t("activities.tareas.steps_count", { count: p.items_json.length, defaultValue: `${p.items_json.length} pasos` })}
                      </span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Botón Desktop Nueva Tarea */}
          <button
            type="button"
            onClick={handleOpenCreate}
            className="hidden md:inline-flex items-center gap-2 rounded-2xl bg-blue-600 px-4 py-2.5 text-xs font-black uppercase tracking-wider text-white shadow-lg shadow-blue-500/25 hover:bg-blue-700 active:scale-95 transition-all cursor-pointer select-none"
          >
            <Plus className="h-4 w-4" />
            <span>{t("activities.tareas.new_task", { defaultValue: "Nueva Tarea" })}</span>
          </button>
        </div>
      </div>

      {/* Toolbar: Toggle Vista + AreaSelector + Buscador + Switch Solo Mis Tareas */}
      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-3 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Switch de Modo de Vista: Kanban vs Checklist */}
          <div className="inline-flex rounded-xl bg-secondary/80 p-1 border border-border">
            <button
              type="button"
              onClick={() => setViewMode("kanban")}
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider transition-all cursor-pointer",
                viewMode === "kanban"
                  ? "bg-card text-blue-500 shadow-sm font-black"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Columns className="h-3.5 w-3.5" />
              <span>{t("activities.tareas.view_kanban", { defaultValue: "Tablero Kanban" })}</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("checklist")}
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider transition-all cursor-pointer",
                viewMode === "checklist"
                  ? "bg-card text-emerald-500 shadow-sm font-black"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <ListTodo className="h-3.5 w-3.5" />
              <span>{t("activities.tareas.view_checklist", { defaultValue: "Modo Checklist" })}</span>
            </button>
          </div>

          {/* Filtros: AreaSelector y Solo Mis Tareas */}
          <div className="flex items-center gap-2 flex-wrap">
            <AreaSelector
              selectedAreaId={selectedAreaId}
              onSelectArea={(id) => setSelectedAreaId(id)}
            />

            <button
              type="button"
              onClick={() => setSoloMisTareas((prev) => !prev)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-2xl border px-3 h-8 text-[11px] font-bold uppercase tracking-wider transition-all cursor-pointer select-none",
                soloMisTareas
                  ? "bg-primary/15 text-primary border-primary/40 font-black shadow-sm"
                  : "bg-card text-muted-foreground hover:bg-secondary border-border"
              )}
            >
              <UserCheck className="h-3.5 w-3.5" />
              <span>{t("activities.tareas.my_tasks_only", { defaultValue: "Solo mis tareas" })}</span>
            </button>
          </div>
        </div>

        {/* Buscador reactivo */}
        <div className="relative w-full">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-muted-foreground">
            <Search className="h-4 w-4" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("activities.tareas.search_placeholder", {
              defaultValue: "Buscar tareas por título o responsable...",
            })}
            className="w-full rounded-xl border border-border bg-background pl-9 pr-9 py-2 text-xs md:text-sm text-foreground transition-all duration-200 placeholder:text-muted-foreground focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:shadow-[0_0_15px_rgba(59,130,246,0.3)]"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute inset-y-0 right-0 flex items-center pr-3 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Contenido: Tablero Kanban vs Vista Checklist */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-80 rounded-2xl border border-border bg-card animate-pulse" />
          ))}
        </div>
      ) : viewMode === "kanban" ? (
        /* VISTA TABLERO KANBAN DE 4 COLUMNAS */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-start">
          {kanbanColumns.map((col) => {
            const ColIcon = col.icon;
            return (
              <div
                key={col.id}
                className={cn(
                  "flex flex-col rounded-2xl border bg-card/60 p-3 shadow-sm min-h-[300px]",
                  col.colorClass
                )}
              >
                {/* Header de la columna */}
                <div className="flex items-center justify-between border-b border-border/60 pb-2.5 mb-3">
                  <div className="flex items-center gap-2">
                    <ColIcon className="h-4 w-4" />
                    <h3 className="text-xs font-black uppercase tracking-wider text-foreground">
                      {col.label}
                    </h3>
                  </div>
                  <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-secondary px-1.5 text-[10px] font-black text-foreground">
                    {col.items.length}
                  </span>
                </div>

                {/* Listado de Tarjetas */}
                <div className="flex flex-col gap-3">
                  {col.items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 p-6 text-center text-xs text-muted-foreground">
                      <p>{t("activities.tareas.empty_column", { defaultValue: "Sin tareas" })}</p>
                    </div>
                  ) : (
                    col.items.map((tarea) => (
                      <TareaCard
                        key={tarea.id}
                        tarea={tarea}
                        onEdit={handleOpenEdit}
                        onDelete={handleDelete}
                        onStatusChange={handleStatusChange}
                        onRequireIncomplete={(t) => setIncompleteModalTarea(t)}
                      />
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* VISTA RÁPIDA CHECKLIST PARA OPERARIOS */
        <div className="flex flex-col gap-2.5">
          {filteredTareas.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border p-12 text-center bg-card/40">
              <p className="text-sm font-bold text-foreground">
                {t("activities.common.empty", { defaultValue: "No hay tareas registradas con estos filtros" })}
              </p>
            </div>
          ) : (
            filteredTareas.map((tarea) => (
              <TareaCard
                key={tarea.id}
                tarea={tarea}
                isChecklistMode={true}
                onEdit={handleOpenEdit}
                onDelete={handleDelete}
                onStatusChange={handleStatusChange}
                onRequireIncomplete={(t) => setIncompleteModalTarea(t)}
              />
            ))
          )}
        </div>
      )}

      {/* FAB Flotante en Móvil */}
      <button
        type="button"
        aria-label={t("activities.tareas.new_task", { defaultValue: "Nueva Tarea" })}
        onClick={handleOpenCreate}
        className="md:hidden fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-2xl shadow-blue-500/50 hover:bg-blue-700 active:scale-90 transition-transform cursor-pointer border border-blue-400/30"
      >
        <Plus className="h-6 w-6" />
      </button>

      {/* Diálogo Crear/Editar Tarea */}
      <TareaDialog
        open={dialogOpen}
        initialData={editingTarea}
        onClose={() => setDialogOpen(false)}
        onSave={handleSaveTarea}
      />

      {/* Diálogo Inviolable de Tarea Incompleta */}
      <IncompleteTaskDialog
        open={!!incompleteModalTarea}
        tarea={incompleteModalTarea}
        onClose={() => setIncompleteModalTarea(null)}
        onConfirm={handleConfirmIncomplete}
      />
    </div>
  );
}
