import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Clock,
  Copy,
  Plus,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { useHorarios } from "../hooks/useHorarios";
import { useCollaborators } from "../hooks/useCollaborators";
import { TurnoDialog } from "./TurnoDialog";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import { useSwipeNavigation } from "@/shared/hooks/useSwipeNavigation";
import { toast } from "sonner";
import { cn } from "@/shared/lib";
import type { TurnoHorario } from "../types";

// Helper para calcular lunes de la semana actual
export function getMonday(d: Date): Date {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(date.setDate(diff));
}

export function formatDateYMD(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function HorariosPage() {
  const { t } = useTranslation("operations");
  const isMobile = useIsMobile();
  const { collaborators } = useCollaborators();

  const [currentMonday, setCurrentMonday] = useState<Date>(() => getMonday(new Date()));
  const [selectedAreaId, setSelectedAreaId] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"semana" | "3dias">(() =>
    isMobile ? "3dias" : "semana"
  );
  const [mobileDayOffset, setMobileDayOffset] = useState<number>(0);

  // Modales
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTurno, setEditingTurno] = useState<TurnoHorario | null>(null);
  const [selectedDateForNew, setSelectedDateForNew] = useState<string | undefined>(undefined);

  // Soporte para gestos táctiles Swipe en móvil (useSwipeNavigation)
  const { onTouchStartX, onTouchEndX } = useSwipeNavigation(40);

  const {
    turnos,
    createTurno,
    updateTurno,
    deleteTurno,
    clonarSemana,
    validarAlertas,
    isCloning,
  } = useHorarios({
    area_id: selectedAreaId,
  });

  // Cálculo de los 7 días de la semana activa
  const weekDays = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(currentMonday);
      d.setDate(currentMonday.getDate() + i);
      const dayNames = [
        t("activities.horarios.days.mon", { defaultValue: "Lunes" }),
        t("activities.horarios.days.tue", { defaultValue: "Martes" }),
        t("activities.horarios.days.wed", { defaultValue: "Miércoles" }),
        t("activities.horarios.days.thu", { defaultValue: "Jueves" }),
        t("activities.horarios.days.fri", { defaultValue: "Viernes" }),
        t("activities.horarios.days.sat", { defaultValue: "Sábado" }),
        t("activities.horarios.days.sun", { defaultValue: "Domingo" }),
      ];
      return {
        dateStr: formatDateYMD(d),
        dayName: dayNames[i] ?? "",
        dayNumber: d.getDate(),
        monthName: d.toLocaleDateString(undefined, { month: "short" }),
        isToday: formatDateYMD(d) === formatDateYMD(new Date()),
      };
    });
  }, [currentMonday, t]);

  // Días visibles en modo móvil (3 días con ventana deslizante)
  const visibleDays = useMemo(() => {
    if (viewMode === "semana") return weekDays;
    return weekDays.slice(mobileDayOffset, mobileDayOffset + 3);
  }, [viewMode, weekDays, mobileDayOffset]);

  // Auditoría Legal Guard del Turno en la semana: cálculo de horas y descansos
  const legalAuditMap = useMemo(() => {
    const map = new Map<number, { totalHours: number; restWarning: boolean; hoursWarning: boolean }>();

    collaborators.forEach((c) => {
      const userTurnos = turnos.filter((trn) => trn.user_id === c.id);
      let totalH = 0;
      let restWarn = false;

      // Ordenar por fecha y hora
      const sorted = [...userTurnos].sort((a, b) => {
        const da = `${a.fecha_inicio ?? ""} ${a.hora_inicio ?? ""}`;
        const db = `${b.fecha_inicio ?? ""} ${b.hora_inicio ?? ""}`;
        return da.localeCompare(db);
      });

      for (let i = 0; i < sorted.length; i++) {
        const cur = sorted[i];
        if (!cur) continue;
        if (cur.hora_inicio && cur.hora_fin) {
          const parts1 = cur.hora_inicio.split(":");
          const parts2 = cur.hora_fin.split(":");
          const h1 = Number(parts1[0] ?? 0);
          const m1 = Number(parts1[1] ?? 0);
          const h2 = Number(parts2[0] ?? 0);
          const m2 = Number(parts2[1] ?? 0);
          let diff = (h2 + m2 / 60) - (h1 + m1 / 60);
          if (diff < 0) diff += 24;
          totalH += diff;
        }

        if (i > 0) {
          const prev = sorted[i - 1];
          if (prev?.fecha_inicio && cur.fecha_inicio && prev.hora_fin && cur.hora_inicio) {
            const dtPrev = new Date(`${prev.fecha_inicio}T${prev.hora_fin}`);
            const dtCur = new Date(`${cur.fecha_inicio}T${cur.hora_inicio}`);
            const diffHours = (dtCur.getTime() - dtPrev.getTime()) / (1000 * 3600);
            if (diffHours > 0 && diffHours < 12) {
              restWarn = true;
            }
          }
        }
      }

      map.set(c.id, {
        totalHours: Math.round(totalH * 10) / 10,
        restWarning: restWarn,
        hoursWarning: totalH > 40,
      });
    });

    return map;
  }, [collaborators, turnos]);

  // Navegación de semanas
  const handlePrevWeek = () => {
    const prev = new Date(currentMonday);
    prev.setDate(prev.getDate() - 7);
    setCurrentMonday(prev);
    setMobileDayOffset(0);
  };

  const handleNextWeek = () => {
    const next = new Date(currentMonday);
    next.setDate(next.getDate() + 7);
    setCurrentMonday(next);
    setMobileDayOffset(0);
  };

  const handleToday = () => {
    setCurrentMonday(getMonday(new Date()));
    setMobileDayOffset(0);
  };

  // Manejo de swipes en móvil
  const handleTouchEnd = (e: React.TouchEvent) => {
    const touch = e.changedTouches[0];
    if (!touch) return;
    const dir = onTouchEndX(touch.clientX);
    if (viewMode === "3dias") {
      if (dir === "left") {
        setMobileDayOffset((prev) => Math.min(prev + 1, 4));
      } else if (dir === "right") {
        setMobileDayOffset((prev) => Math.max(prev - 1, 0));
      }
    }
  };

  // Clonar Semana Anterior
  const handleClonarSemana = async () => {
    const prevMon = new Date(currentMonday);
    prevMon.setDate(prevMon.getDate() - 7);
    const fechaLunesOrigen = formatDateYMD(prevMon);
    const fechaLunesDestino = formatDateYMD(currentMonday);

    try {
      await clonarSemana({
        fecha_lunes_origen: fechaLunesOrigen,
        fecha_lunes_destino: fechaLunesDestino,
        area_id: selectedAreaId === "all" ? null : selectedAreaId,
      });
      toast.success(t("activities.horarios.clone_success", { defaultValue: "Semana anterior clonada exitosamente" }));
    } catch {
      toast.error(t("activities.horarios.error_clone", { defaultValue: "Error al clonar los turnos de la semana" }));
    }
  };

  const handleOpenCreateForDate = (dateStr?: string) => {
    setEditingTurno(null);
    setSelectedDateForNew(dateStr);
    setDialogOpen(true);
  };

  const handleOpenEdit = (turno: TurnoHorario) => {
    setEditingTurno(turno);
    setSelectedDateForNew(turno.fecha_inicio ?? undefined);
    setDialogOpen(true);
  };

  const handleDeleteTurno = async (id: number) => {
    try {
      await deleteTurno(id);
      toast.success(t("activities.common.success_deleted", { defaultValue: "Turno eliminado" }));
    } catch {
      toast.error(t("activities.horarios.error_delete", { defaultValue: "Error al eliminar turno" }));
    }
  };

  const handleSaveTurno = async (data: any) => {
    try {
      if (editingTurno) {
        await updateTurno({ id: editingTurno.id, ...data });
        toast.success(t("activities.common.success_updated", { defaultValue: "Turno actualizado" }));
      } else {
        await createTurno(data);
        toast.success(t("activities.common.success_created", { defaultValue: "Turno asignado" }));
      }
    } catch {
      toast.error(t("activities.horarios.error_save", { defaultValue: "Error al guardar turno" }));
    }
  };

  return (
    <div
      className="flex flex-col gap-6 p-4 md:p-6 max-w-7xl mx-auto w-full select-none"
      data-testid="horarios-page"
      onTouchStart={(e) => {
        const touch = e.touches[0];
        if (touch) onTouchStartX(touch.clientX);
      }}
      onTouchEnd={handleTouchEnd}
    >
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <SectionHeader
          icon={Calendar}
          color="#8B5CF6"
          center={false}
          title={t("activities.horarios.title", { defaultValue: "Cuadrante de Horarios y Turnos" })}
          subtitle={t("activities.horarios.subtitle", {
            defaultValue: "Planificación semanal de turnos, matriz de jornadas y cumplimiento de la Ley 40 Horas",
          })}
        />

        <div className="flex items-center gap-2 flex-wrap">
          {/* Botón Clonar Semana Anterior */}
          <button
            type="button"
            disabled={isCloning}
            onClick={handleClonarSemana}
            className="inline-flex items-center gap-2 rounded-2xl border border-border bg-card px-3.5 py-2 text-xs font-bold uppercase tracking-wider text-foreground hover:bg-secondary transition-all cursor-pointer shadow-sm active:scale-95 disabled:opacity-50"
          >
            <Copy className="h-4 w-4 text-primary" />
            <span className="hidden sm:inline">
              {t("activities.horarios.clone_previous_week", { defaultValue: "Clonar Semana Anterior" })}
            </span>
          </button>

          {/* Botón Asignar Turno */}
          <button
            type="button"
            onClick={() => handleOpenCreateForDate()}
            className="hidden md:inline-flex items-center gap-2 rounded-2xl bg-blue-600 px-4 py-2.5 text-xs font-black uppercase tracking-wider text-white shadow-lg shadow-blue-500/25 hover:bg-blue-700 active:scale-95 transition-all cursor-pointer"
          >
            <Plus className="h-4 w-4" />
            <span>{t("activities.horarios.new_shift", { defaultValue: "Asignar Turno" })}</span>
          </button>
        </div>
      </div>

      {/* Toolbar: Paginador Semanal + AreaSelector + Switch 3 días */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card p-3 shadow-sm">
        {/* Navegación de semana */}
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-xl bg-secondary/80 p-0.5 border border-border">
            <button
              type="button"
              aria-label={t("activities.horarios.prev_week", { defaultValue: "Semana Anterior" })}
              onClick={handlePrevWeek}
              className="p-1.5 rounded-lg text-foreground hover:bg-card transition-colors cursor-pointer"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={handleToday}
              className="px-2.5 py-1 text-xs font-bold text-foreground hover:bg-card rounded-lg transition-colors cursor-pointer"
            >
              {t("activities.horarios.today", { defaultValue: "Hoy" })}
            </button>
            <button
              type="button"
              aria-label={t("activities.horarios.next_week", { defaultValue: "Semana Siguiente" })}
              onClick={handleNextWeek}
              className="p-1.5 rounded-lg text-foreground hover:bg-card transition-colors cursor-pointer"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <span className="text-xs font-bold text-foreground flex items-center gap-1.5 ml-1">
            <Calendar className="h-4 w-4 text-primary" />
            <span>
              {weekDays[0]?.dayNumber ?? 1} {weekDays[0]?.monthName ?? ""} — {weekDays[6]?.dayNumber ?? 7} {weekDays[6]?.monthName ?? ""}
            </span>
          </span>
        </div>

        {/* Controles de vista & Área */}
        <div className="flex items-center gap-2">
          {/* Toggle Vista 3 días / Semana */}
          <div className="inline-flex rounded-xl bg-secondary/80 p-1 border border-border">
            <button
              type="button"
              onClick={() => setViewMode("semana")}
              className={cn(
                "rounded-lg px-2.5 py-1 text-xs font-bold uppercase tracking-wider transition-all cursor-pointer",
                viewMode === "semana" ? "bg-card text-blue-500 shadow-sm font-black" : "text-muted-foreground"
              )}
            >
              {t("activities.horarios.view_week", { defaultValue: "Semana" })}
            </button>
            <button
              type="button"
              onClick={() => setViewMode("3dias")}
              className={cn(
                "rounded-lg px-2.5 py-1 text-xs font-bold uppercase tracking-wider transition-all cursor-pointer",
                viewMode === "3dias" ? "bg-card text-emerald-500 shadow-sm font-black" : "text-muted-foreground"
              )}
            >
              {t("activities.horarios.view_3days", { defaultValue: "3 Días" })}
            </button>
          </div>

          <AreaSelector
            selectedAreaId={selectedAreaId}
            onSelectArea={(id) => setSelectedAreaId(id)}
          />
        </div>
      </div>

      {/* Matriz Cuadrante de Turnos */}
      <div className="overflow-x-auto rounded-2xl border border-border bg-card shadow-sm custom-scrollbar">
        <div className="min-w-[800px]">
          {/* Fila de Encabezados de Días */}
          <div
            className="grid border-b border-border bg-muted/30"
            style={{
              gridTemplateColumns: `240px repeat(${visibleDays.length}, minmax(130px, 1fr))`,
            }}
          >
            {/* Esquina superior izquierda: Colaborador / Legal Guard */}
            <div className="p-3 border-r border-border text-xs font-black uppercase tracking-wider text-muted-foreground flex items-center justify-between">
              <span>{t("activities.horarios.form.collaborator", { defaultValue: "Colaborador" })}</span>
              <span className="text-[10px] text-primary flex items-center gap-1">
                <ShieldAlert className="h-3.5 w-3.5" />
                <span>{t("activities.horarios.legal_guard_title", { defaultValue: "Legal Guard" })}</span>
              </span>
            </div>

            {/* Columnas de los Días */}
            {visibleDays.map((day) => (
              <div
                key={day.dateStr}
                className={cn(
                  "p-2.5 border-r border-border last:border-r-0 text-center flex flex-col items-center justify-center transition-colors",
                  day.isToday ? "bg-blue-500/10" : ""
                )}
              >
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  {day.dayName}
                </span>
                <span
                  className={cn(
                    "text-sm font-black mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full",
                    day.isToday ? "bg-blue-600 text-white" : "text-foreground"
                  )}
                >
                  {day.dayNumber}
                </span>
              </div>
            ))}
          </div>

          {/* Filas por cada Colaborador Gastronómico */}
          {collaborators.map((collab) => {
            const audit = legalAuditMap.get(collab.id) ?? { totalHours: 0, restWarning: false, hoursWarning: false };

            return (
              <div
                key={collab.id}
                className="grid border-b border-border last:border-b-0 hover:bg-secondary/20 transition-colors items-stretch"
                style={{
                  gridTemplateColumns: `240px repeat(${visibleDays.length}, minmax(130px, 1fr))`,
                }}
              >
                {/* Columna Colaborador con Alertas Legal Guard */}
                <div className="p-3 border-r border-border flex items-center justify-between gap-2 bg-card">
                  <div className="flex items-center gap-2.5 min-w-0">
                    {collab.avatar ? (
                      <img
                        src={collab.avatar}
                        alt={collab.name}
                        className="h-9 w-9 rounded-full object-cover border border-border shrink-0"
                      />
                    ) : (
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-xs shrink-0">
                        {collab.name[0]}
                      </div>
                    )}
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-foreground truncate">{collab.name}</p>
                      <p className="text-[10px] text-muted-foreground truncate">{collab.role}</p>
                    </div>
                  </div>

                  {/* Resumen Legal Guard: Horas semanales y advertencias */}
                  <div className="text-right shrink-0">
                    <span
                      className={cn(
                        "text-xs font-black",
                        audit.hoursWarning ? "text-red-500" : "text-foreground"
                      )}
                    >
                      {audit.totalHours}h
                    </span>
                    {(audit.hoursWarning || audit.restWarning) && (
                      <div className="flex items-center justify-end gap-1 mt-0.5">
                        {audit.hoursWarning && (
                          <span
                            title={t("activities.horarios.legal_hours_warning", {
                              defaultValue: "Excede las 40 horas semanales",
                            })}
                            className="text-red-500"
                          >
                            <AlertTriangle className="h-3 w-3" />
                          </span>
                        )}
                        {audit.restWarning && (
                          <span
                            title={t("activities.horarios.legal_rest_warning", {
                              defaultValue: "Descanso menor a 12 horas",
                            })}
                            className="text-amber-500"
                          >
                            <Clock className="h-3 w-3" />
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Celdas de los Días para este Colaborador */}
                {visibleDays.map((day) => {
                  const dayTurnos = turnos.filter(
                    (trn) => trn.user_id === collab.id && trn.fecha_inicio === day.dateStr
                  );

                  return (
                    <div
                      key={day.dateStr}
                      className="p-1.5 border-r border-border last:border-r-0 min-h-[72px] flex flex-col gap-1 relative group/cell"
                    >
                      {dayTurnos.map((trn) => (
                        <div
                          key={trn.id}
                          onClick={() => handleOpenEdit(trn)}
                          style={{
                            borderLeftColor: trn.color ?? "#3B82F6",
                            borderLeftWidth: "4px",
                          }}
                          className="rounded-lg border border-border bg-card p-1.5 text-xs shadow-sm cursor-pointer hover:shadow-md transition-all group/item"
                        >
                          <div className="flex items-center justify-between gap-1">
                            <span className="font-bold text-[11px] text-foreground">
                              {trn.hora_inicio?.slice(0, 5)} - {trn.hora_fin?.slice(0, 5)}
                            </span>
                            <button
                              type="button"
                              aria-label={t("activities.horarios.delete_shift", { defaultValue: "Eliminar turno" })}
                              onClick={(e) => {
                                e.stopPropagation();
                                void handleDeleteTurno(trn.id);
                              }}
                              className="opacity-0 group-hover/item:opacity-100 p-0.5 text-muted-foreground hover:text-red-500 transition-opacity"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                          {trn.nota && (
                            <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                              {trn.nota}
                            </p>
                          )}
                        </div>
                      ))}

                      {/* Botón rápido '+' al pasar el cursor sobre la celda */}
                      <button
                        type="button"
                        onClick={() => handleOpenCreateForDate(day.dateStr)}
                        className="opacity-0 group-hover/cell:opacity-100 mt-auto flex items-center justify-center rounded-lg border border-dashed border-border py-1 text-[10px] font-bold text-muted-foreground hover:bg-secondary hover:text-foreground transition-all"
                      >
                        <Plus className="h-3 w-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      {/* FAB Flotante en Móvil */}
      <button
        type="button"
        aria-label={t("activities.horarios.new_shift", { defaultValue: "Asignar Turno" })}
        onClick={() => handleOpenCreateForDate()}
        className="md:hidden fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-2xl shadow-blue-500/50 hover:bg-blue-700 active:scale-90 transition-transform cursor-pointer border border-blue-400/30"
      >
        <Plus className="h-6 w-6" />
      </button>

      {/* Diálogo Crear / Editar Turno con Legal Guard en Vivo */}
      <TurnoDialog
        open={dialogOpen}
        initialData={editingTurno}
        defaultDate={selectedDateForNew}
        onClose={() => setDialogOpen(false)}
        onSave={handleSaveTurno}
        onValidateLegalGuard={validarAlertas}
      />
    </div>
  );
}
