/**
 * oppytec-frontend/src/features/oppyfy/components/FeedbackReportModal.tsx
 * Modal interactivo y accesible (@radix-ui/react-dialog) para reporte de alucinaciones
 * y feedback humano negativo (RLHF):
 * - Selector con 5 categorías de fallo estandarizadas
 * - Textarea opcional para corrección con terminología del negocio
 * - Touch targets >= 44px y diseño Mobile-First compatible con los 3 temas del ADN Visual
 */

import React, { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  X,
  Send,
  Calculator,
  Hourglass,
  FileEdit,
  HelpCircle,
  ShieldAlert,
} from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type { FailureCategory } from "../types";

export interface FeedbackReportModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly onSubmit: (data: {
    failure_category: FailureCategory;
    user_correction?: string;
  }) => Promise<void> | void;
  readonly isSubmitting?: boolean;
  readonly messageId: string;
}

interface CategoryOption {
  readonly key: FailureCategory;
  readonly labelKey: string;
  readonly fallbackLabel: string;
  readonly icon: React.ComponentType<{ className?: string }>;
  readonly testId: string;
}

const FAILURE_OPTIONS: readonly CategoryOption[] = [
  {
    key: "hallucination",
    labelKey: "feedback.categories.hallucination",
    fallbackLabel: "🚨 Alucinación / Datos inventados",
    icon: ShieldAlert,
    testId: "category-hallucination",
  },
  {
    key: "math_error",
    labelKey: "feedback.categories.math_error",
    fallbackLabel: "📉 Error en cálculos o costos",
    icon: Calculator,
    testId: "category-math_error",
  },
  {
    key: "incomplete",
    labelKey: "feedback.categories.incomplete",
    fallbackLabel: "⏳ Respuesta incompleta",
    icon: Hourglass,
    testId: "category-incomplete",
  },
  {
    key: "bad_formatting",
    labelKey: "feedback.categories.bad_formatting",
    fallbackLabel: "📝 Mala redacción o formato",
    icon: FileEdit,
    testId: "category-bad_formatting",
  },
  {
    key: "other",
    labelKey: "feedback.categories.other",
    fallbackLabel: "❓ Otro motivo",
    icon: HelpCircle,
    testId: "category-other",
  },
];

export const FeedbackReportModal: React.FC<FeedbackReportModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting = false,
  messageId,
}) => {
  const [selectedCategory, setSelectedCategory] =
    useState<FailureCategory>("hallucination");
  const [userCorrection, setUserCorrection] = useState<string>("");

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (isSubmitting) return;

    await onSubmit({
      failure_category: selectedCategory,
      user_correction: userCorrection.trim() || undefined,
    });
    setUserCorrection("");
    onClose();
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay
          data-testid="feedback-modal-overlay"
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm transition-opacity"
        />
        <Dialog.Content
          data-testid="feedback-report-modal"
          aria-describedby="feedback-modal-description"
          className="fixed left-[50%] top-[50%] z-50 w-full max-w-lg translate-x-[-50%] translate-y-[-50%] rounded-xl border border-border bg-card p-5 sm:p-6 shadow-2xl transition-all focus:outline-none"
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-3 border-b border-border pb-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-destructive/15 text-destructive">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <Dialog.Title className="text-base font-bold text-foreground">
                  {translateKey("oppyfy", "feedback.modal_title") ||
                    "Retroalimentación de Respuesta OppyFy"}
                </Dialog.Title>
                <Dialog.Description
                  id="feedback-modal-description"
                  className="text-xs text-muted-foreground leading-relaxed mt-0.5"
                >
                  {translateKey("oppyfy", "feedback.modal_subtitle") ||
                    "Ayúdanos a mejorar el modelo reportando fallos o discrepancias con los datos de tu negocio gastronómico."}
                </Dialog.Description>
              </div>
            </div>

            <Dialog.Close asChild>
              <button
                type="button"
                data-testid="feedback-close-btn"
                aria-label={translateKey("oppyfy", "feedback.cancel") || "Cerrar"}
                onClick={onClose}
                className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-muted-foreground transition hover:bg-secondary hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </Dialog.Close>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <input type="hidden" name="messageId" value={messageId} />

            {/* Selector de Categoría */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-foreground">
                {translateKey("oppyfy", "feedback.category_label") ||
                  "Motivo del fallo:"}
              </label>
              <div
                role="radiogroup"
                aria-label="Motivo del fallo"
                className="grid grid-cols-1 gap-2 sm:grid-cols-2"
              >
                {FAILURE_OPTIONS.map((opt) => {
                  const isSelected = selectedCategory === opt.key;
                  const Icon = opt.icon;
                  const label =
                    translateKey("oppyfy", opt.labelKey) || opt.fallbackLabel;

                  return (
                    <button
                      key={opt.key}
                      type="button"
                      role="radio"
                      aria-checked={isSelected}
                      data-testid={opt.testId}
                      onClick={() => setSelectedCategory(opt.key)}
                      className={`touch-target flex min-h-[44px] items-center gap-2.5 rounded-lg border p-2.5 text-left text-xs font-medium transition ${
                        isSelected
                          ? "border-destructive bg-destructive/10 text-destructive shadow-sm ring-1 ring-destructive/40"
                          : "border-border bg-secondary/30 text-foreground hover:border-border/80 hover:bg-secondary/60"
                      }`}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="truncate">{label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Textarea Opcional de Corrección */}
            <div className="space-y-1.5">
              <label
                htmlFor="feedback-user-correction"
                className="block text-xs font-semibold text-foreground"
              >
                {translateKey("oppyfy", "feedback.user_correction_label") ||
                  "¿Cuál era la respuesta correcta esperada según tu negocio?"}
              </label>
              <textarea
                id="feedback-user-correction"
                data-testid="feedback-user-correction-input"
                rows={3}
                value={userCorrection}
                onChange={(e) => setUserCorrection(e.target.value)}
                placeholder={
                  translateKey("oppyfy", "feedback.user_correction_placeholder") ||
                  "Ejemplo: Para Pollo King el costo teórico de la pechuga es $3.500 y no $4.200..."
                }
                className="w-full rounded-lg border border-border bg-background p-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary min-h-[80px]"
              />
            </div>

            {/* Acciones */}
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-3 pt-2">
              <button
                type="button"
                data-testid="feedback-cancel-btn"
                onClick={onClose}
                disabled={isSubmitting}
                className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border border-border bg-secondary/50 px-4 py-2 text-xs font-semibold text-foreground transition hover:bg-secondary disabled:opacity-50"
              >
                {translateKey("oppyfy", "feedback.cancel") || "Cancelar"}
              </button>
              <button
                type="submit"
                data-testid="feedback-submit-btn"
                disabled={isSubmitting}
                className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-2 rounded-lg bg-destructive px-4 py-2 text-xs font-bold text-destructive-foreground shadow-sm transition hover:opacity-90 disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                <span>
                  {isSubmitting
                    ? translateKey("oppyfy", "feedback.submitting") || "Enviando..."
                    : translateKey("oppyfy", "feedback.submit") ||
                      "Enviar Retroalimentación"}
                </span>
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
