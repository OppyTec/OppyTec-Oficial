import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Loader2,
  ShieldAlert,
  X,
  XCircle,
} from "lucide-react";
import { cn } from "@/shared/lib/utils";
import type { Solicitud } from "../types";

export interface RechazoModalProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly solicitud: Solicitud | null;
  readonly onConfirmReject: (id: string, reason: string) => Promise<void> | void;
  readonly isRejecting?: boolean;
}

export function RechazoModal({
  open,
  onClose,
  solicitud,
  onConfirmReject,
  isRejecting = false,
}: RechazoModalProps) {
  const [reason, setReason] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (open) {
      setReason("");
      setErrorMessage("");
    }
  }, [open]);

  if (!open || !solicitud) return null;

  const handleConfirm = async () => {
    const trimmed = reason.trim();
    if (!trimmed || trimmed.length < 5) {
      setErrorMessage("La justificación de rechazo debe contener al menos 5 caracteres.");
      return;
    }

    try {
      await onConfirmReject(solicitud.id, trimmed);
      onClose();
    } catch {
      // Error manejado por el handler superior
    }
  };

  const detalles = solicitud.detalles || {};
  const insumoNombre =
    detalles.producto_nombre ||
    detalles.buffet_nombre ||
    (detalles.acta_conteo_id ? `Acta #${detalles.acta_conteo_id}` : null) ||
    detalles.proveedor_nombre ||
    solicitud.tipo;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Rechazar Solicitud Operativa"
      data-testid="rechazo-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-3 sm:p-4 overflow-y-auto"
    >
      <div className="glass-card w-full max-w-lg rounded-3xl border border-destructive/30 bg-background/95 p-5 sm:p-6 shadow-2xl flex flex-col space-y-4 my-auto animate-in fade-in zoom-in-95">
        {/* Cabecera de Alerta */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-2xl bg-destructive/15 border border-destructive/30 flex items-center justify-center text-destructive shrink-0">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-black text-foreground">
                Rechazar Solicitud Operativa
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Esta acción es irreversible y notificará al emisor inmediatamente.
              </p>
            </div>
          </div>
          <button
            type="button"
            data-testid="rechazo-modal-close"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground p-1 rounded-lg"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Resumen del Elemento a Rechazar */}
        <div className="p-3 rounded-2xl bg-muted/40 border border-border/60 text-xs space-y-1">
          <div className="flex items-center justify-between">
            <span className="font-bold text-muted-foreground uppercase text-[10px]">
              Elemento involucrado
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-muted text-foreground">
              ID: {solicitud.id}
            </span>
          </div>
          <p className="font-black text-sm text-foreground">{insumoNombre}</p>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span>Tipo: <strong className="text-foreground uppercase font-mono">{solicitud.tipo}</strong></span>
            {solicitud.usuario && (
              <span>• Solicitante: <strong>{solicitud.usuario.username}</strong></span>
            )}
          </div>
        </div>

        {/* Formulario con Validación */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-foreground flex items-center justify-between">
            <span>Motivo o Justificación Obligatoria *</span>
            <span
              className={cn(
                "text-[10px] font-mono",
                reason.trim().length >= 5
                  ? "text-emerald-500 font-bold"
                  : "text-muted-foreground"
              )}
            >
              {reason.trim().length} / 5 mín
            </span>
          </label>
          <textarea
            data-testid="rechazo-modal-textarea"
            rows={3}
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              if (errorMessage) setErrorMessage("");
            }}
            placeholder="Especifica claramente la causa del rechazo (ej: 'Las cantidades no corresponden al turno de noche')..."
            className={cn(
              "w-full p-3 rounded-2xl bg-background border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2",
              errorMessage
                ? "border-destructive focus:ring-destructive"
                : "border-border/80 focus:ring-destructive/50"
            )}
          />
          {errorMessage && (
            <p
              data-testid="rechazo-modal-error"
              className="text-xs font-bold text-destructive flex items-center gap-1 mt-1"
            >
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>{errorMessage}</span>
            </p>
          )}
        </div>

        {/* Acciones del Modal */}
        <div className="pt-2 flex items-center justify-end gap-2 border-t border-border/50">
          <button
            type="button"
            data-testid="rechazo-modal-cancel"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-input text-xs font-bold text-muted-foreground hover:bg-muted cursor-pointer"
          >
            Cancelar
          </button>
          <button
            type="button"
            data-testid="rechazo-modal-confirm"
            onClick={handleConfirm}
            disabled={isRejecting}
            className="px-4 py-2 rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground text-xs font-black uppercase tracking-wider inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            {isRejecting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <XCircle className="w-3.5 h-3.5" />
            )}
            <span>{isRejecting ? "Rechazando..." : "Confirmar Rechazo"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default RechazoModal;
