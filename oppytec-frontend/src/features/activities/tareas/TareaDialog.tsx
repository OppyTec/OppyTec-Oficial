import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { OFFICIAL_AREAS } from "@/shared/components/layout/AreaSelector";
import { useCollaborators } from "../hooks/useCollaborators";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import type { Tarea, TareaEstado, TareaUrgencia } from "../types";

export interface TareaDialogProps {
  readonly open: boolean;
  readonly initialData?: Tarea | null;
  readonly onClose: () => void;
  readonly onSave: (data: {
    titulo: string;
    descripcion?: string | null;
    asignado_a_user_id?: number | null;
    area_id?: string | null;
    estado?: TareaEstado;
    urgencia?: TareaUrgencia;
    fecha_limite?: string | null;
    compra_id?: string | null;
  }) => Promise<void>;
}

export function TareaDialog({
  open,
  initialData,
  onClose,
  onSave,
}: TareaDialogProps) {
  const { t } = useTranslation("operations");
  const isMobile = useIsMobile();
  const { collaborators } = useCollaborators();

  const [titulo, setTitulo] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [asignadoA, setAsignadoA] = useState<string>("none");
  const [areaId, setAreaId] = useState<string>("all");
  const [urgencia, setUrgencia] = useState<TareaUrgencia>("media");
  const [fechaLimite, setFechaLimite] = useState("");
  const [compraId, setCompraId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (initialData) {
      setTitulo(initialData.titulo);
      setDescripcion(initialData.descripcion ?? "");
      setAsignadoA(initialData.asignado_a_user_id ? String(initialData.asignado_a_user_id) : "none");
      setAreaId(initialData.area_id ?? "all");
      setUrgencia(initialData.urgencia);
      setFechaLimite(initialData.fecha_limite ? initialData.fecha_limite.slice(0, 16) : "");
      setCompraId(initialData.compra_id ?? "");
    } else {
      setTitulo("");
      setDescripcion("");
      setAsignadoA("none");
      setAreaId("all");
      setUrgencia("media");
      setFechaLimite("");
      setCompraId("");
    }
  }, [initialData, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!titulo.trim()) return;

    setIsSubmitting(true);
    try {
      await onSave({
        titulo: titulo.trim(),
        descripcion: descripcion.trim() || null,
        asignado_a_user_id: asignadoA === "none" ? null : Number(asignadoA),
        area_id: areaId === "all" ? null : areaId,
        urgencia,
        fecha_limite: fechaLimite ? new Date(fechaLimite).toISOString() : null,
        compra_id: compraId.trim() || null,
      });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onClose={onClose}
      isMobile={isMobile}
      maxWidth="max-w-lg"
      title={
        initialData
          ? t("activities.tareas.edit_task", { defaultValue: "Editar Tarea" })
          : t("activities.tareas.new_task", { defaultValue: "Nueva Tarea" })
      }
      description={t("activities.tareas.subtitle", {
        defaultValue: "Gestión de tareas, checklists y rutinas de turno",
      })}
    >
      <form onSubmit={handleSubmit} className="space-y-4 py-2">
        {/* Título */}
        <div>
          <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
            {t("activities.tareas.form.title_label", { defaultValue: "Título de la Tarea" })} *
          </label>
          <input
            type="text"
            required
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            placeholder={t("activities.tareas.form.title_placeholder", {
              defaultValue: "Ej: Sanitización de línea de frío",
            })}
            className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
          />
        </div>

        {/* Descripción */}
        <div>
          <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
            {t("activities.tareas.form.desc_label", { defaultValue: "Descripción / Instrucciones" })}
          </label>
          <textarea
            rows={2}
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            placeholder={t("activities.tareas.form.desc_placeholder", {
              defaultValue: "Detalles adicionales para el colaborador...",
            })}
            className="w-full rounded-xl border border-border bg-background p-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm resize-none"
          />
        </div>

        {/* Fila: Responsable y Urgencia */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
              {t("activities.tareas.form.assigned_to", { defaultValue: "Responsable" })}
            </label>
            <select
              value={asignadoA}
              onChange={(e) => setAsignadoA(e.target.value)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
            >
              <option value="none">
                {t("activities.tareas.form.unassigned", { defaultValue: "Sin asignar" })}
              </option>
              {collaborators.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.role})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
              {t("activities.tareas.form.urgency_label", { defaultValue: "Nivel de Urgencia" })}
            </label>
            <select
              value={urgencia}
              onChange={(e) => setUrgencia(e.target.value as TareaUrgencia)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
            >
              <option value="baja">{t("activities.tareas.urgency.baja", { defaultValue: "Baja" })}</option>
              <option value="media">{t("activities.tareas.urgency.media", { defaultValue: "Media" })}</option>
              <option value="alta">{t("activities.tareas.urgency.alta", { defaultValue: "Alta" })}</option>
            </select>
          </div>
        </div>

        {/* Fila: Área y Fecha Límite */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
              {t("activities.tareas.form.area_label", { defaultValue: "Área" })}
            </label>
            <select
              value={areaId}
              onChange={(e) => setAreaId(e.target.value)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
            >
              {OFFICIAL_AREAS.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nombre}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
              {t("activities.tareas.form.due_date", { defaultValue: "Fecha y Hora Límite" })}
            </label>
            <input
              type="datetime-local"
              value={fechaLimite}
              onChange={(e) => setFechaLimite(e.target.value)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
            />
          </div>
        </div>

        {/* Orden de compra opcional */}
        <div>
          <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
            {t("activities.tareas.form.purchase_order", {
              defaultValue: "Orden de Compra Asociada (Opcional)",
            })}
          </label>
          <input
            type="text"
            value={compraId}
            onChange={(e) => setCompraId(e.target.value)}
            placeholder="Ej: OC-2026-881"
            className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
          />
        </div>

        {/* Botones */}
        <div className="flex items-center justify-end gap-2 border-t border-border pt-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-border px-4 py-2 text-xs font-bold uppercase tracking-wider text-muted-foreground hover:bg-secondary transition-colors"
          >
            {t("activities.common.cancel", { defaultValue: "Cancelar" })}
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !titulo.trim()}
            className="rounded-xl bg-blue-600 px-5 py-2 text-xs font-bold uppercase tracking-wider text-white shadow-md shadow-blue-500/20 hover:bg-blue-700 disabled:opacity-50 transition-all cursor-pointer"
          >
            {isSubmitting
              ? t("activities.common.saving", { defaultValue: "Guardando..." })
              : t("activities.common.save", { defaultValue: "Guardar" })}
          </button>
        </div>
      </form>
    </ResponsiveDialog>
  );
}
