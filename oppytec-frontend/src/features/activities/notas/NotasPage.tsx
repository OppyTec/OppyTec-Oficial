import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  Flame,
  Layers,
  Package,
  Plus,
  Search,
  Users,
  User,
  ConciergeBell,
  MessageSquare,
  Sparkles,
  X,
} from "lucide-react";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { useNotas } from "../hooks/useNotas";
import { NotaCard } from "./NotaCard";
import { NotaDialog } from "./NotaDialog";
import { MinutaTraspasoDialog } from "./MinutaTraspasoDialog";
import { toast } from "sonner";
import { cn } from "@/shared/lib";
import type { NotaCategoria, NotaEquipo, NotaPersonal } from "../types";

export function NotasPage() {
  const { t } = useTranslation("operations");

  const [activeTab, setActiveTab] = useState<"equipo" | "personales">("equipo");
  const [selectedAreaId, setSelectedAreaId] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<NotaCategoria | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [minutaDialogOpen, setMinutaDialogOpen] = useState(false);
  const [editingNota, setEditingNota] = useState<NotaEquipo | NotaPersonal | null>(null);

  const {
    notasEquipo,
    notasPersonales,
    isLoading,
    createEquipo,
    updateEquipo,
    deleteEquipo,
    markAsRead,
    createPersonal,
    updatePersonal,
    deletePersonal,
  } = useNotas({
    area_id: selectedAreaId,
    categoria: selectedCategory,
  });

  // Filtrado local por búsqueda (@mención, #tag, texto)
  const filteredNotas = useMemo(() => {
    const list = activeTab === "equipo" ? notasEquipo : notasPersonales;
    return list.filter((n) => {
      // Filtro de área
      if (selectedAreaId !== "all" && n.area_id && n.area_id !== selectedAreaId) {
        return false;
      }
      // Filtro de categoría (solo equipo)
      if (activeTab === "equipo" && selectedCategory !== "all") {
        const eq = n as NotaEquipo;
        if (eq.categoria !== selectedCategory) return false;
      }
      // Filtro de búsqueda
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase().trim();
      const matchTitle = n.titulo.toLowerCase().includes(q);
      const matchBody = n.contenido.toLowerCase().includes(q);
      return matchTitle || matchBody;
    });
  }, [activeTab, notasEquipo, notasPersonales, selectedAreaId, selectedCategory, searchQuery]);

  const handleOpenCreate = () => {
    setEditingNota(null);
    setDialogOpen(true);
  };

  const handleOpenEdit = (nota: NotaEquipo | NotaPersonal) => {
    setEditingNota(nota);
    setDialogOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      if (activeTab === "equipo") {
        await deleteEquipo(id);
      } else {
        await deletePersonal(id);
      }
      toast.success(t("activities.common.success_deleted", { defaultValue: "Nota eliminada" }));
    } catch {
      toast.error(t("activities.notas.error_delete", { defaultValue: "Error al eliminar la nota" }));
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await markAsRead(id);
      toast.success(t("activities.notas.read_by_me", { defaultValue: "Nota leída" }));
    } catch {
      toast.error(t("activities.notas.error_mark_read", { defaultValue: "Error al registrar lectura" }));
    }
  };

  const handleSaveNota = async (data: {
    titulo: string;
    contenido: string;
    area_id?: string | null;
    categoria?: NotaCategoria | string;
    foto_url?: string | null;
    menciones_user_ids?: number[];
  }) => {
    try {
      if (activeTab === "equipo") {
        if (editingNota) {
          await updateEquipo({
            id: editingNota.id,
            ...data,
          });
          toast.success(t("activities.common.success_updated", { defaultValue: "Nota actualizada" }));
        } else {
          await createEquipo(data);
          toast.success(t("activities.common.success_created", { defaultValue: "Nota creada" }));
        }
      } else {
        if (editingNota) {
          await updatePersonal({
            id: editingNota.id,
            titulo: data.titulo,
            contenido: data.contenido,
            area_id: data.area_id,
          });
          toast.success(t("activities.common.success_updated", { defaultValue: "Nota actualizada" }));
        } else {
          await createPersonal({
            titulo: data.titulo,
            contenido: data.contenido,
            area_id: data.area_id,
          });
          toast.success(t("activities.common.success_created", { defaultValue: "Nota creada" }));
        }
      }
    } catch {
      toast.error(t("activities.notas.error_save", { defaultValue: "Error al guardar la nota" }));
    }
  };

  const categoriesConfig: Array<{ id: NotaCategoria | "all"; label: string; icon: any }> = [
    { id: "all", label: t("activities.notas.categories.all", { defaultValue: "Todas" }), icon: Layers },
    { id: "incidente", label: t("activities.notas.categories.incidente", { defaultValue: "Incidente" }), icon: AlertTriangle },
    { id: "stock", label: t("activities.notas.categories.stock", { defaultValue: "Stock" }), icon: Package },
    { id: "produccion", label: t("activities.notas.categories.produccion", { defaultValue: "Producción" }), icon: Flame },
    { id: "servicio", label: t("activities.notas.categories.servicio", { defaultValue: "Servicio" }), icon: ConciergeBell },
  ];

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6 max-w-7xl mx-auto w-full" data-testid="notas-page">
      {/* Encabezado con SectionHeader */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <SectionHeader
          icon={MessageSquare}
          color="#3B82F6"
          center={false}
          title={t("activities.notas.title", { defaultValue: "Notas de Turno" })}
          subtitle={t("activities.notas.subtitle", {
            defaultValue: "Muro de novedades, bitácora colaborativa y notas personales del equipo",
          })}
        />

        {/* Acciones de Encabezado: OppyFy Minuta + Nueva Nota */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setMinutaDialogOpen(true)}
            className="inline-flex items-center gap-2 rounded-2xl border border-indigo-500/30 bg-indigo-500/10 px-3.5 py-2 text-xs font-black uppercase tracking-wider text-indigo-400 hover:bg-indigo-500/20 active:scale-95 transition-all cursor-pointer select-none shadow-sm shadow-indigo-500/10"
            data-testid="oppyfy-minuta-btn"
          >
            <Sparkles className="h-4 w-4 text-indigo-400 animate-pulse" />
            <span>{t("activities.notas.oppyfy_minuta_btn", { defaultValue: "🤖 Resumen de Traspaso (OppyFy)" })}</span>
          </button>

          {/* Botón Desktop para crear nota */}
          <button
            type="button"
            onClick={handleOpenCreate}
            className="hidden md:inline-flex items-center gap-2 rounded-2xl bg-blue-600 px-4 py-2.5 text-xs font-black uppercase tracking-wider text-white shadow-lg shadow-blue-500/25 hover:bg-blue-700 active:scale-95 transition-all cursor-pointer select-none"
          >
            <Plus className="h-4 w-4" />
            <span>{t("activities.notas.new_note", { defaultValue: "Nueva Nota" })}</span>
          </button>
        </div>
      </div>

      {/* Toolbar unificada: Pestañas + AreaSelector + Buscador + Selector de categorías */}
      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-3 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Pestañas animadas: Equipo vs Personales */}
          <div className="inline-flex rounded-xl bg-secondary/80 p-1 border border-border">
            <button
              type="button"
              onClick={() => setActiveTab("equipo")}
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-bold uppercase tracking-wider transition-all cursor-pointer",
                activeTab === "equipo"
                  ? "bg-card text-blue-500 shadow-sm font-black"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Users className="h-3.5 w-3.5" />
              <span>{t("activities.notas.tab_team", { defaultValue: "Notas de Equipo" })}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("personales")}
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-bold uppercase tracking-wider transition-all cursor-pointer",
                activeTab === "personales"
                  ? "bg-card text-purple-500 shadow-sm font-black"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <User className="h-3.5 w-3.5" />
              <span>{t("activities.notas.tab_personal", { defaultValue: "Personales" })}</span>
            </button>
          </div>

          {/* AreaSelector Integrado */}
          <div className="flex items-center gap-2">
            <AreaSelector
              selectedAreaId={selectedAreaId}
              onSelectArea={(id) => setSelectedAreaId(id)}
            />
          </div>
        </div>

        {/* Buscador con luz perimetral azul (#3b82f6) */}
        <div className="relative w-full">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-muted-foreground">
            <Search className="h-4 w-4" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("activities.notas.search_placeholder", {
              defaultValue: "Buscar notas, menciones (@) o insumos (#)...",
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

        {/* Categorías operativas horizontales (solo en notas de equipo) */}
        {activeTab === "equipo" && (
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-0.5 custom-scrollbar">
            {categoriesConfig.map((cat) => {
              const CatIcon = cat.icon;
              const isSelected = selectedCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setSelectedCategory(cat.id)}
                  className={cn(
                    "inline-flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-1 text-xs font-bold uppercase tracking-wider transition-all cursor-pointer",
                    isSelected
                      ? "bg-blue-500/15 text-blue-500 border border-blue-500/30 font-black shadow-sm"
                      : "bg-secondary/60 text-muted-foreground hover:bg-secondary hover:text-foreground border border-transparent"
                  )}
                >
                  <CatIcon className="h-3 w-3" />
                  <span>{cat.label}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Muro / Feed de Tarjetas */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-48 rounded-2xl border border-border bg-card p-4 animate-pulse"
            />
          ))}
        </div>
      ) : filteredNotas.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border p-12 text-center bg-card/40">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-secondary text-muted-foreground mb-3">
            <Layers className="h-6 w-6" />
          </div>
          <h4 className="text-sm font-bold text-foreground">
            {activeTab === "equipo"
              ? t("activities.notas.empty_team", { defaultValue: "No hay notas de equipo para los filtros seleccionados." })
              : t("activities.notas.empty_personal", { defaultValue: "No tienes notas personales registradas." })}
          </h4>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredNotas.map((nota) => (
            <NotaCard
              key={nota.id}
              nota={nota}
              isPersonal={activeTab === "personales"}
              onEdit={handleOpenEdit}
              onDelete={handleDelete}
              onMarkRead={handleMarkRead}
              onMentionClick={(username) => setSearchQuery(`@${username}`)}
              onTagClick={(tag) => setSearchQuery(`#${tag}`)}
            />
          ))}
        </div>
      )}

      {/* FAB Flotante en Móvil (Mobile-First Rule 21) */}
      <button
        type="button"
        aria-label={t("activities.notas.new_note", { defaultValue: "Nueva Nota" })}
        onClick={handleOpenCreate}
        className="md:hidden fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-2xl shadow-blue-500/50 hover:bg-blue-700 active:scale-90 transition-transform cursor-pointer border border-blue-400/30"
      >
        <Plus className="h-6 w-6" />
      </button>

      {/* Diálogo de Crear / Editar Nota */}
      <NotaDialog
        open={dialogOpen}
        isPersonal={activeTab === "personales"}
        initialData={editingNota}
        onClose={() => setDialogOpen(false)}
        onSave={handleSaveNota}
      />

      {/* Diálogo de Minuta de Traspaso OppyFy */}
      <MinutaTraspasoDialog
        open={minutaDialogOpen}
        areaId={selectedAreaId}
        onClose={() => setMinutaDialogOpen(false)}
        onSaveAsNota={async (notaData) => {
          await createEquipo(notaData);
        }}
      />
    </div>
  );
}
