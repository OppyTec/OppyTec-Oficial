/**
 * oppytec-frontend/src/features/oppyfy/components/OppyfyRolloverModal.tsx
 * Modal interactivo para traspasar a un hilo fresco al 5.00% de contexto:
 * - Evita Context Rot y activa la garantía Anti-Hallucination
 * - Permite editar la síntesis o resumen estructurado previo al rollover
 * - Restablece el medidor semafórico a Verde
 */

import React, { useState, useEffect } from "react";
import { Sparkles, X, ShieldCheck, ArrowRight } from "lucide-react";
import { translateKey } from "@/shared/i18n";

export interface OppyfyRolloverModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly onConfirm: (summaryNotes?: string) => Promise<void> | void;
  readonly initialSummary?: string;
  readonly isProcessing?: boolean;
}

export const OppyfyRolloverModal: React.FC<OppyfyRolloverModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  initialSummary = "",
  isProcessing = false,
}) => {
  const [summaryText, setSummaryText] = useState<string>(
    initialSummary || translateKey("oppyfy", "rollover_modal.default_summary")
  );

  useEffect(() => {
    if (initialSummary) {
      setSummaryText(initialSummary);
    } else {
      setSummaryText(translateKey("oppyfy", "rollover_modal.default_summary"));
    }
  }, [initialSummary, isOpen]);

  if (!isOpen) return null;

  const handleConfirm = async (): Promise<void> => {
    await onConfirm(summaryText);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="rollover-modal-title"
      data-testid="oppyfy-rollover-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
    >
      <div className="relative w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-2xl transition-all">
        {/* Cabecera del modal */}
        <div className="flex items-start justify-between gap-3 border-b border-border pb-3">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-primary/10 p-2 text-primary">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2
                id="rollover-modal-title"
                className="text-base font-bold text-foreground"
              >
                {translateKey("oppyfy", "rollover_modal.title")}
              </h2>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-500">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Contexto inicial garantizado al 5.00%</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            data-testid="rollover-close-btn"
            aria-label={translateKey("oppyfy", "rollover_modal.cancel")}
            onClick={onClose}
            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Cuerpo informativo */}
        <div className="my-4 space-y-3 text-xs">
          <p className="text-muted-foreground leading-relaxed">
            {translateKey("oppyfy", "rollover_modal.description")}
          </p>

          <div>
            <label
              htmlFor="rollover-summary"
              className="mb-1.5 block font-semibold text-foreground"
            >
              {translateKey("oppyfy", "rollover_modal.summary_label")}
            </label>
            <textarea
              id="rollover-summary"
              data-testid="rollover-summary-input"
              rows={4}
              value={summaryText}
              onChange={(e) => setSummaryText(e.target.value)}
              placeholder={translateKey(
                "oppyfy",
                "rollover_modal.summary_placeholder"
              )}
              className="w-full rounded-md border border-border bg-secondary/30 p-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {/* Acciones */}
        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-border pt-4">
          <button
            type="button"
            data-testid="rollover-cancel-btn"
            onClick={onClose}
            disabled={isProcessing}
            className="touch-target inline-flex min-h-[44px] items-center rounded-md border border-border bg-card px-4 py-2 text-xs font-semibold text-foreground hover:bg-secondary disabled:opacity-50"
          >
            {translateKey("oppyfy", "rollover_modal.cancel")}
          </button>

          <button
            type="button"
            data-testid="rollover-confirm-btn"
            onClick={handleConfirm}
            disabled={isProcessing}
            className="touch-target inline-flex min-h-[44px] items-center gap-2 rounded-md bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow transition hover:opacity-95 disabled:opacity-50"
          >
            {isProcessing ? (
              <span>{translateKey("oppyfy", "rollover_modal.processing")}</span>
            ) : (
              <>
                <span>{translateKey("oppyfy", "rollover_modal.confirm")}</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
