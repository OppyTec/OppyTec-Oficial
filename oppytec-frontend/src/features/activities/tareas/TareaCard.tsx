import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Calendar,
  Check,
  CheckCircle2,
  Circle,
  Clock,
  Edit2,
  MoreVertical,
  ShoppingCart,
  Trash2,
  User,
  AlertOctagon,
  Play,
  RotateCcw,
} from "lucide-react";
import { cn } from "@/shared/lib";
import type { Tarea, TareaEstado, TareaUrgencia } from "../types";

export interface TareaCardProps {
  readonly tarea: Tarea;
  readonly isChecklistMode?: boolean;
  readonly onEdit?: (tarea: Tarea) => void;
  readonly onDelete?: (id: number) => void;
  readonly onStatusChange?: (id: number, estado: TareaEstado) => void;
  readonly onRequireIncomplete?: (tarea: Tarea) => void;
}

export function getUrgencyBorderColor(urgencia: TareaUrgencia): string {
  switch (urgencia) {
    case "alta":
      return "border-l-[6px] border-l-red-500 shadow-[0_0_12px_rgba(239,68,68,0.15)]";
    case "media":
      return "border-l-[6px] border-l-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.15)]";
    case "baja":
      return "border-l-[6px] border-l-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.15)]";
  }
}

export function getUrgencyBadge(urgencia: TareaUrgencia, t: (key: string, opts?: any) => string) {
  switch (urgencia) {
    case "alta":
      return {
        label: t("activities.tareas.urgency.alta", { defaultValue: "Alta" }),
        className: "bg-red-500/10 text-red-500 border-red-500/30",
      };
    case "media":
      return {
        label: t("activities.tareas.urgency.media", { defaultValue: "Media" }),
        className: "bg-amber-500/10 text-amber-500 border-amber-500/30",
      };
    case "baja":
      return {
        label: t("activities.tareas.urgency.baja", { defaultValue: "Baja" }),
        className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30",
      };
  }
}

export function TareaCard({
  tarea,
  isChecklistMode = false,
  onEdit,
  onDelete,
  onStatusChange,
  onRequireIncomplete,
}: TareaCardProps) {
  const { t } = useTranslation("operations");
  const [menuOpen, setMenuOpen] = useState(false);

  const urgencyBadge = getUrgencyBadge(tarea.urgencia, t);
  const urgencyBorder = getUrgencyBorderColor(tarea.urgencia);

  const handleToggleCompleted = () => {
    if (tarea.estado === "completada") {
      onStatusChange?.(tarea.id, "pendiente");
    } else {
      onStatusChange?.(tarea.id, "completada");
    }
  };

  const handleSelectStatus = (newStatus: TareaEstado) => {
    setMenuOpen(false);
    if (newStatus === "incompleta") {
      onRequireIncomplete?.(tarea);
    } else {
      onStatusChange?.(tarea.id, newStatus);
    }
  };

  const formatDeadline = (isoString: string | null) => {
    if (!isoString) return null;
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Modo Checklist Compacto (Optimizado para Smartphones de operarios)
  if (isChecklistMode) {
    return (
      <div
        data-testid="tarea-checklist-item"
        className={cn(
          "flex items-center justify-between rounded-xl border border-border bg-card p-3 shadow-sm transition-all hover:border-primary/40",
          urgencyBorder,
          tarea.estado === "completada" ? "opacity-60 bg-muted/30" : ""
        )}
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <button
            type="button"
            onClick={handleToggleCompleted}
            aria-label={t("activities.tareas.toggle_status", { defaultValue: "Toggle Estado Tarea" })}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border bg-background hover:bg-secondary transition-colors cursor-pointer"
          >
            {tarea.estado === "completada" ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            ) : tarea.estado === "incompleta" ? (
              <AlertOctagon className="h-5 w-5 text-red-500" />
            ) : (
              <Circle className="h-5 w-5 text-muted-foreground" />
            )}
          </button>

          <div className="min-w-0 flex-1">
            <p
              className={cn(
                "text-sm font-semibold text-foreground truncate",
                tarea.estado === "completada" && "line-through text-muted-foreground"
              )}
            >
              {tarea.titulo}
            </p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5 flex-wrap">
              {tarea.asignado_a_name && (
                <span className="flex items-center gap-1 font-medium">
                  <User className="h-3 w-3" />
                  <span>{tarea.asignado_a_name}</span>
                </span>
              )}
              {tarea.fecha_limite && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  <span>{formatDeadline(tarea.fecha_limite)}</span>
                </span>
              )}
              {tarea.compra_id && (
                <span className="inline-flex items-center gap-1 rounded bg-blue-500/10 px-1.5 py-0.2 text-[10px] font-bold text-blue-500">
                  <ShoppingCart className="h-2.5 w-2.5" />
                  <span>{tarea.compra_id}</span>
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Acciones */}
        <div className="flex items-center gap-1 shrink-0 ml-2">
          {tarea.estado !== "incompleta" && (
            <button
              type="button"
              onClick={() => onRequireIncomplete?.(tarea)}
              title={t("activities.tareas.incomplete_dialog.title", { defaultValue: "Marcar Incompleta" })}
              className="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
            >
              <AlertOctagon className="h-4 w-4" />
            </button>
          )}
          {onEdit && (
            <button
              type="button"
              onClick={() => onEdit(tarea)}
              className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-lg transition-colors"
            >
              <Edit2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // Modo Tarjeta Kanban Estándar
  return (
    <article
      data-testid="tarea-card"
      className={cn(
        "group relative flex flex-col rounded-2xl border border-border bg-card p-4 shadow-sm transition-all duration-200 hover:shadow-md hover:border-primary/40",
        urgencyBorder,
        tarea.estado === "completada" ? "opacity-75" : ""
      )}
    >
      {/* Header: Badges & Menú */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-wider border",
              urgencyBadge.className
            )}
          >
            {urgencyBadge.label}
          </span>

          {tarea.compra_id && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2 py-0.5 text-[10px] font-bold text-blue-500 border border-blue-500/20">
              <ShoppingCart className="h-2.5 w-2.5" />
              <span>{t("activities.tareas.purchase_badge", { id: tarea.compra_id, defaultValue: tarea.compra_id })}</span>
            </span>
          )}

          {tarea.area_id && (
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              {tarea.area_id.replace("-", " ")}
            </span>
          )}
        </div>

        {/* Acciones */}
        <div className="relative">
          <button
            type="button"
            aria-label={t("activities.common.actions", { defaultValue: "Acciones de tarea" })}
            onClick={() => setMenuOpen((prev) => !prev)}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          >
            <MoreVertical className="h-3.5 w-3.5" />
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 z-40 w-44 rounded-xl border border-border bg-popover p-1 shadow-xl">
                <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
                  {t("activities.tareas.change_status", { defaultValue: "Cambiar Estado" })}
                </div>
                <button
                  type="button"
                  onClick={() => handleSelectStatus("pendiente")}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-foreground hover:bg-secondary"
                >
                  <RotateCcw className="h-3 w-3 text-zinc-400" />
                  <span>{t("activities.tareas.columns.pendiente", { defaultValue: "Pendiente" })}</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectStatus("progreso")}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-foreground hover:bg-secondary"
                >
                  <Play className="h-3 w-3 text-blue-500" />
                  <span>{t("activities.tareas.columns.progreso", { defaultValue: "En Progreso" })}</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectStatus("completada")}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-foreground hover:bg-secondary"
                >
                  <Check className="h-3 w-3 text-emerald-500" />
                  <span>{t("activities.tareas.columns.completada", { defaultValue: "Completada" })}</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectStatus("incompleta")}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-red-500 hover:bg-red-500/10"
                >
                  <AlertOctagon className="h-3 w-3" />
                  <span>{t("activities.tareas.columns.incompleta", { defaultValue: "Incompleta" })}</span>
                </button>

                <div className="my-1 border-t border-border" />

                {onEdit && (
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onEdit(tarea);
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-foreground hover:bg-secondary"
                  >
                    <Edit2 className="h-3 w-3" />
                    <span>{t("activities.common.edit", { defaultValue: "Editar" })}</span>
                  </button>
                )}

                {onDelete && (
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onDelete(tarea.id);
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-red-500 hover:bg-red-500/10"
                  >
                    <Trash2 className="h-3 w-3" />
                    <span>{t("activities.common.delete", { defaultValue: "Eliminar" })}</span>
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Título */}
      <h4
        className={cn(
          "mt-2 text-sm font-bold text-foreground tracking-tight leading-snug",
          tarea.estado === "completada" && "line-through text-muted-foreground"
        )}
      >
        {tarea.titulo}
      </h4>

      {/* Descripción si existe */}
      {tarea.descripcion && (
        <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
          {tarea.descripcion}
        </p>
      )}

      {/* Justificación obligatoria en caso de estar incompleta */}
      {tarea.estado === "incompleta" && tarea.nota_incompleta && (
        <div className="mt-2.5 rounded-xl border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-600 dark:text-red-400">
          <p className="font-bold text-[10px] uppercase tracking-wider mb-0.5">
            {t("activities.tareas.incomplete_reason_label", { defaultValue: "Motivo Incompleta:" })}
          </p>
          <p className="italic">"{tarea.nota_incompleta}"</p>
        </div>
      )}

      {/* Footer: Responsable & Fecha Límite */}
      <div className="mt-4 flex items-center justify-between border-t border-border pt-2.5 text-xs">
        <div className="flex items-center gap-2 min-w-0">
          {tarea.asignado_a_avatar ? (
            <img
              src={tarea.asignado_a_avatar}
              alt={tarea.asignado_a_name ?? t("activities.common.user", { defaultValue: "Usuario" })}
              className="h-6 w-6 rounded-full object-cover border border-border"
            />
          ) : (
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-secondary text-[10px] font-bold text-foreground">
              {tarea.asignado_a_name ? tarea.asignado_a_name[0] : <User className="h-3 w-3" />}
            </div>
          )}
          <span className="truncate text-xs font-medium text-foreground max-w-[100px]">
            {tarea.asignado_a_name ?? t("activities.tareas.form.unassigned", { defaultValue: "Sin asignar" })}
          </span>
        </div>

        {tarea.fecha_limite && (
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground font-medium shrink-0">
            <Calendar className="h-3 w-3" />
            <span>{formatDeadline(tarea.fecha_limite)}</span>
          </div>
        )}
      </div>
    </article>
  );
}
