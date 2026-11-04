import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertCircle, AlertTriangle } from "lucide-react";
import { ResponsiveDialog } from "@/shared/components/ui/ResponsiveDialog";
import { useIsMobile } from "@/shared/hooks/useIsMobile";
import type { Tarea } from "../types";

export interface IncompleteTaskDialogProps {
  readonly open: boolean;
  readonly tarea: Tarea | null;
  readonly onClose: () => void;
  readonly onConfirm: (tareaId: number, justificacion: string) => Promise<void>;
}

export function IncompleteTaskDialog({
  open,
  tarea,
  onClose,
  onConfirm,
}: IncompleteTaskDialogProps) {
  const { t } = useTranslation("operations");
  const isMobile = useIsMobile();
  const [justificacion, setJustificacion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!tarea) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!justificacion.trim() || justificacion.trim().length < 5) return;

    setIsSubmitting(true);
    try {
      await onConfirm(tarea.id, justificacion.trim());
      setJustificacion("");
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
      maxWidth="max-w-md"
      title={t("activities.tareas.incomplete_dialog.title", {
        defaultValue: "Justificar Tarea Incompleta",
      })}
      description={t("activities.tareas.incomplete_dialog.description", {
        defaultValue: "Regla Operativa Obligatoria: Es mandatorio registrar el motivo por el cual esta tarea no pudo ser finalizada.",
      })}
    >
      <form onSubmit={handleSubmit} className="space-y-4 py-2">
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 flex items-start gap-2.5 text-xs text-red-600 dark:text-red-400">
          <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold">{tarea.titulo}</p>
            <p className="opacity-90">
              {t("activities.tareas.incomplete_dialog.audit_notice", {
                defaultValue: "Esta justificación quedará registrada de forma inmutable en el registro de auditoría del turno.",
              })}
            </p>
          </div>
        </div>

        <div>
          <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1">
            {t("activities.tareas.incomplete_dialog.reason_label", {
              defaultValue: "Motivo / Justificación Inviolable",
            })} *
          </label>
          <textarea
            required
            rows={4}
            value={justificacion}
            onChange={(e) => setJustificacion(e.target.value)}
            placeholder={t("activities.tareas.incomplete_dialog.reason_placeholder", {
              defaultValue: "Explica la causa: falta de stock, avería mecánica, etc...",
            })}
            className="w-full rounded-xl border border-border bg-background p-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-red-500/50 shadow-sm resize-none"
          />
          {justificacion.trim().length > 0 && justificacion.trim().length < 5 && (
            <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
              <AlertCircle className="h-3 w-3" />
              <span>
                {t("activities.tareas.incomplete_dialog.min_length_hint", {
                  defaultValue: "Mínimo 5 caracteres de justificación detallada",
                })}
              </span>
            </p>
          )}
        </div>

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
            disabled={isSubmitting || justificacion.trim().length < 5}
            className="rounded-xl bg-red-600 px-5 py-2 text-xs font-bold uppercase tracking-wider text-white shadow-md shadow-red-500/20 hover:bg-red-700 disabled:opacity-50 transition-all cursor-pointer"
          >
            {isSubmitting
              ? t("activities.tareas.incomplete_dialog.submitting", { defaultValue: "Registrando..." })
              : t("activities.tareas.incomplete_dialog.submit_button", {
                  defaultValue: "Confirmar como Incompleta",
                })}
          </button>
        </div>
      </form>
    </ResponsiveDialog>
  );
}
