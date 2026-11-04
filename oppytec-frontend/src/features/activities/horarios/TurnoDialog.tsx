import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, ShieldAlert } from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { OFFICIAL_AREAS } from "@/shared/components/layout/AreaSelector";
import { useCollaborators } from "../hooks/useCollaborators";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import type { TurnoHorario, ValidacionLaboral } from "../types";

export interface TurnoDialogProps {
  readonly open: boolean;
  readonly initialData?: TurnoHorario | null;
  readonly defaultDate?: string;
  readonly onClose: () => void;
  readonly onSave: (data: {
    user_id: number;
    area_id?: string | null;
    fecha_inicio: string;
    fecha_fin: string;
    hora_inicio: string;
    hora_fin: string;
    nota?: string | null;
    color?: string | null;
  }) => Promise<void>;
  readonly onValidateLegalGuard?: (data: {
    user_id: number;
    fecha_inicio: string;
    fecha_fin: string;
    hora_inicio: string;
    hora_fin: string;
    turno_id_excluir?: number | null;
  }) => Promise<ValidacionLaboral>;
}

export const PRESET_SHIFT_COLORS = [
  "#3B82F6", // Azul
  "#10B981", // Esmeralda
  "#F59E0B", // Ámbar
  "#EC4899", // Rosa
  "#8B5CF6", // Púrpura
  "#06B6D4", // Cian
  "#F97316", // Naranja
];

export function TurnoDialog({
  open,
  initialData,
  defaultDate,
  onClose,
  onSave,
  onValidateLegalGuard,
}: TurnoDialogProps) {
  const { t } = useTranslation("operations");
  const isMobile = useIsMobile();
  const { collaborators } = useCollaborators();

  const [userId, setUserId] = useState<number>(1);
  const [areaId, setAreaId] = useState<string>("all");
  const [fecha, setFecha] = useState<string>(
    defaultDate ?? new Date().toISOString().slice(0, 10)
  );
  const [horaInicio, setHoraInicio] = useState<string>("09:00");
  const [horaFin, setHoraFin] = useState<string>("17:00");
  const [nota, setNota] = useState<string>("");
  const [color, setColor] = useState<string>("#3B82F6");

  const [legalAlerts, setLegalAlerts] = useState<ValidacionLaboral | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (initialData) {
      setUserId(initialData.user_id);
      setAreaId(initialData.area_id ?? "all");
      setFecha(initialData.fecha_inicio ?? defaultDate ?? new Date().toISOString().slice(0, 10));
      setHoraInicio(initialData.hora_inicio?.slice(0, 5) ?? "09:00");
      setHoraFin(initialData.hora_fin?.slice(0, 5) ?? "17:00");
      setNota(initialData.nota ?? "");
      setColor(initialData.color ?? "#3B82F6");
    } else {
      setUserId(collaborators[0]?.id ?? 1);
      setAreaId("all");
      setFecha(defaultDate ?? new Date().toISOString().slice(0, 10));
      setHoraInicio("09:00");
      setHoraFin("17:00");
      setNota("");
      setColor("#3B82F6");
    }
    setLegalAlerts(null);
  }, [initialData, defaultDate, open, collaborators]);

  // Validación reactiva de Legal Guard al cambiar horas o colaborador
  useEffect(() => {
    if (!open || !onValidateLegalGuard) return;
    const timeout = setTimeout(async () => {
      try {
        const val = await onValidateLegalGuard({
          user_id: userId,
          fecha_inicio: fecha,
          fecha_fin: fecha,
          hora_inicio: `${horaInicio}:00`,
          hora_fin: `${horaFin}:00`,
          turno_id_excluir: initialData?.id,
        });
        setLegalAlerts(val);
      } catch {
        // En caso de mock o error silencioso
      }
    }, 400);

    return () => clearTimeout(timeout);
  }, [userId, fecha, horaInicio, horaFin, initialData, open, onValidateLegalGuard]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSave({
        user_id: userId,
        area_id: areaId === "all" ? null : areaId,
        fecha_inicio: fecha,
        fecha_fin: fecha,
        hora_inicio: horaInicio.length === 5 ? `${horaInicio}:00` : horaInicio,
        hora_fin: horaFin.length === 5 ? `${horaFin}:00` : horaFin,
        nota: nota.trim() || null,
        color,
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
          ? t("activities.horarios.edit_shift", { defaultValue: "Editar Turno" })
          : t("activities.horarios.new_shift", { defaultValue: "Asignar Turno" })
      }
      description={t("activities.horarios.subtitle", {
        defaultValue: "Planificación semanal de turnos y cumplimiento de la Ley 40 Horas",
      })}
    >
      <form onSubmit={handleSubmit} className="space-y-4 py-2">
        {/* Banner Legal Guard si se detectan anomalías laborales */}
        {legalAlerts?.tiene_alertas && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 space-y-1.5 text-xs text-amber-600 dark:text-amber-400">
            <div className="flex items-center gap-1.5 font-bold">
              <ShieldAlert className="h-4 w-4" />
              <span>{t("activities.horarios.legal_guard_title", { defaultValue: "Legal Guard Laboral" })}</span>
            </div>
            {legalAlerts.alertas.map((a, idx) => (
              <p key={idx} className="flex items-start gap-1">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                <span>{a.mensaje}</span>
              </p>
            ))}
          </div>
        )}

        {/* Colaborador */}
        <div>
          <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
            {t("activities.horarios.form.collaborator", { defaultValue: "Colaborador" })} *
          </label>
          <select
            value={userId}
            onChange={(e) => setUserId(Number(e.target.value))}
            className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
          >
            {collaborators.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} — {c.role}
              </option>
            ))}
          </select>
        </div>

        {/* Área Operativa */}
        <div>
          <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
            {t("activities.horarios.form.area", { defaultValue: "Área Asignada" })}
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

        {/* Fila: Fecha y Horas */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
              {t("activities.horarios.form.date_start", { defaultValue: "Fecha" })} *
            </label>
            <input
              type="date"
              required
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
              {t("activities.horarios.form.time_start", { defaultValue: "Hora Entrada" })} *
            </label>
            <input
              type="time"
              required
              value={horaInicio}
              onChange={(e) => setHoraInicio(e.target.value)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
              {t("activities.horarios.form.time_end", { defaultValue: "Hora Salida" })} *
            </label>
            <input
              type="time"
              required
              value={horaFin}
              onChange={(e) => setHoraFin(e.target.value)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
            />
          </div>
        </div>

        {/* Color de Turno */}
        <div>
          <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1.5">
            {t("activities.horarios.form.color", { defaultValue: "Color de Turno" })}
          </label>
          <div className="flex items-center gap-2 flex-wrap">
            {PRESET_SHIFT_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                style={{ backgroundColor: c }}
                className={`h-7 w-7 rounded-full border-2 transition-transform ${
                  color === c ? "scale-125 border-foreground shadow-md" : "border-transparent"
                }`}
              />
            ))}
          </div>
        </div>

        {/* Observaciones */}
        <div>
          <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
            {t("activities.horarios.form.notes", { defaultValue: "Observaciones / Turno" })}
          </label>
          <input
            type="text"
            value={nota}
            onChange={(e) => setNota(e.target.value)}
            placeholder={t("activities.horarios.form.notes_placeholder", { defaultValue: "Ej: Turno de apertura o refuerzo de cena" })}
            className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
          />
        </div>

        {/* Botones de acción */}
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
            disabled={isSubmitting}
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
