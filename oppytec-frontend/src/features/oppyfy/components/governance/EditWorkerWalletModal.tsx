/**
 * oppytec-frontend/src/features/oppyfy/components/governance/EditWorkerWalletModal.tsx
 * Modal para ajustar el cupo de créditos asignados y habilitar/deshabilitar OppyFy
 * para un trabajador del Tenant.
 */

import { useState } from "react";
import { X, WalletCards, Check } from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type { OppyfyWorkerWalletItem, OppyfyWalletPatchRequest } from "../../types";

export interface EditWorkerWalletModalProps {
  readonly isOpen: boolean;
  readonly worker: OppyfyWorkerWalletItem | null;
  readonly onClose: () => void;
  readonly onSave: (userId: number, patch: OppyfyWalletPatchRequest) => Promise<void>;
  readonly isSaving?: boolean;
}

export function EditWorkerWalletModal({
  isOpen,
  worker,
  onClose,
  onSave,
  isSaving = false,
}: EditWorkerWalletModalProps) {
  const [ceiling, setCeiling] = useState<string>(
    worker ? String(worker.assigned_credit_ceiling) : "50.00"
  );
  const [isEnabled, setIsEnabled] = useState<boolean>(worker?.is_oppyfy_enabled ?? true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen || !worker) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const parsedCeiling = parseFloat(ceiling.trim());
    if (isNaN(parsedCeiling) || parsedCeiling < 0) {
      setErrorMsg(translateKey("oppyfy", "governance.edit_wallet_modal.error_invalid_ceiling"));
      return;
    }

    try {
      await onSave(worker.user_id, {
        assigned_credit_ceiling: String(parsedCeiling),
        is_oppyfy_enabled: isEnabled,
      });
      onClose();
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : translateKey("oppyfy", "governance.edit_wallet_modal.error_save")
      );
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-worker-wallet-title"
      data-testid="modal-edit-worker-wallet"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in"
    >
      <div className="glass-card relative flex w-full max-w-md flex-col overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-2xl">
        {/* Cabecera */}
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary">
              <WalletCards className="h-5 w-5" />
            </div>
            <div>
              <h2
                id="edit-worker-wallet-title"
                className="text-base font-bold text-card-foreground"
              >
                {translateKey("oppyfy", "governance.edit_wallet_modal.title")}
              </h2>
            </div>
          </div>
          <button
            type="button"
            data-testid="btn-close-edit-wallet"
            onClick={onClose}
            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label={translateKey("oppyfy", "governance.edit_wallet_modal.close_aria")}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {errorMsg && (
          <div
            role="alert"
            data-testid="edit-wallet-error"
            className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive"
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          {/* Trabajador info */}
          <div className="rounded-xl border border-border bg-secondary/15 p-3">
            <span className="text-[11px] font-semibold uppercase text-muted-foreground">
              {translateKey("oppyfy", "governance.edit_wallet_modal.worker_label")}
            </span>
            <div className="mt-0.5 text-sm font-bold text-card-foreground">
              {worker.full_name}
            </div>
            <div className="text-xs text-muted-foreground font-mono">
              {worker.role_name} • {worker.email}
            </div>
          </div>

          {/* Cupo Asignado */}
          <div>
            <label
              htmlFor="worker-ceiling-input"
              className="mb-1 block text-xs font-semibold text-card-foreground"
            >
              {translateKey("oppyfy", "governance.edit_wallet_modal.ceiling_label")}
            </label>
            <input
              id="worker-ceiling-input"
              type="number"
              step="0.01"
              min="0"
              data-testid="input-worker-ceiling"
              value={ceiling}
              onChange={(e) => setCeiling(e.target.value)}
              className="touch-target min-h-[44px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              required
            />
            <p className="mt-1 text-[11px] text-muted-foreground">
              {translateKey("oppyfy", "governance.edit_wallet_modal.current_consumption", {
                consumed: worker.consumed_credits_total,
              })}
            </p>
          </div>

          {/* Interruptor Habilitación */}
          <div className="rounded-xl border border-border bg-card p-3">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-xs font-semibold text-card-foreground">
                {translateKey("oppyfy", "governance.edit_wallet_modal.enable_label")}
              </span>
              <input
                type="checkbox"
                data-testid="check-worker-enable-oppyfy"
                checked={isEnabled}
                onChange={(e) => setIsEnabled(e.target.checked)}
                className="h-5 w-5 rounded border-border text-primary focus:ring-primary"
              />
            </label>
          </div>

          {/* Botones de acción */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <button
              type="button"
              data-testid="btn-cancel-edit-wallet"
              onClick={onClose}
              disabled={isSaving}
              className="touch-target inline-flex min-h-[44px] items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-xs font-semibold text-card-foreground transition-colors hover:bg-muted"
            >
              {translateKey("oppyfy", "governance.edit_wallet_modal.cancel")}
            </button>
            <button
              type="submit"
              data-testid="btn-submit-edit-wallet"
              disabled={isSaving}
              className="touch-target inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:opacity-90 disabled:opacity-50"
            >
              <Check className="h-4 w-4" />
              <span>
                {isSaving
                  ? translateKey("oppyfy", "governance.edit_wallet_modal.saving")
                  : translateKey("oppyfy", "governance.edit_wallet_modal.submit")}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
