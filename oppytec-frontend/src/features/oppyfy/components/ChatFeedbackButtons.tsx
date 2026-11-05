/**
 * oppytec-frontend/src/features/oppyfy/components/ChatFeedbackButtons.tsx
 * Barra interactiva de retroalimentación humana (RLHF) debajo de respuestas de OppyFy:
 * - Botones accesibles 👍 (útil) y 👎 (reporte de fallo / alucinación)
 * - Touch targets >= 44px para cumplimiento estricto Mobile-First
 * - Micro-animaciones fluidas con framer-motion y resplandor activo cuando ya fue votado
 * - Envío inmediato en 👍 y apertura de diálogo asistido en 👎
 */

import React, { useState } from "react";
import { motion } from "framer-motion";
import { ThumbsUp, ThumbsDown, CheckCircle2 } from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type { FeedbackType, FailureCategory } from "../types";
import { useOppyfyFeedback } from "../hooks/useOppyfyFeedback";
import { FeedbackReportModal } from "./FeedbackReportModal";

export interface ChatFeedbackButtonsProps {
  readonly messageId: string;
  readonly traceId?: string;
  readonly initialFeedback?: FeedbackType | null;
  readonly onFeedbackSubmitted?: (
    type: FeedbackType,
    category?: FailureCategory
  ) => void;
  readonly className?: string;
}

export const ChatFeedbackButtons: React.FC<ChatFeedbackButtonsProps> = ({
  messageId,
  traceId,
  initialFeedback,
  onFeedbackSubmitted,
  className = "",
}) => {
  const { submitFeedback, getFeedbackForMessage, isSubmitting } =
    useOppyfyFeedback();

  const [isModalOpen, setIsModalOpen] = useState(false);

  const existingRecord = getFeedbackForMessage(messageId);
  const activeFeedback: FeedbackType | null =
    existingRecord?.feedbackType ?? initialFeedback ?? null;

  const handleThumbsUp = async (): Promise<void> => {
    if (activeFeedback === "positive" || isSubmitting) return;

    try {
      await submitFeedback({
        message_id: messageId,
        trace_id: traceId,
        feedback_type: "positive",
        rating: 5,
      });
      onFeedbackSubmitted?.("positive");
    } catch {
      // Error handled by hook's toast
    }
  };

  const handleThumbsDownClick = (): void => {
    if (isSubmitting) return;
    setIsModalOpen(true);
  };

  const handleModalSubmit = async (data: {
    failure_category: FailureCategory;
    user_correction?: string;
  }): Promise<void> => {
    try {
      await submitFeedback({
        message_id: messageId,
        trace_id: traceId,
        feedback_type: "negative",
        failure_category: data.failure_category,
        user_correction: data.user_correction,
        rating: 1,
      });
      onFeedbackSubmitted?.("negative", data.failure_category);
    } catch {
      // Error handled by hook's toast
    }
  };

  const isPositive = activeFeedback === "positive";
  const isNegative = activeFeedback === "negative";

  return (
    <div
      data-testid={`chat-feedback-buttons-${messageId}`}
      className={`flex items-center gap-2 pt-1 text-xs ${className}`}
    >
      {/* Botón Pulgar Arriba (👍) */}
      <motion.button
        type="button"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        data-testid={`thumbs-up-btn-${messageId}`}
        aria-label={
          translateKey("oppyfy", "feedback.thumbs_up") || "Respuesta útil"
        }
        aria-pressed={isPositive}
        disabled={isSubmitting || isPositive}
        onClick={handleThumbsUp}
        className={`touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border transition-all ${
          isPositive
            ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-600 shadow-[0_0_12px_rgba(16,185,129,0.3)] ring-1 ring-emerald-500/40 dark:text-emerald-400"
            : "border-border bg-card/70 text-muted-foreground hover:border-emerald-500/40 hover:bg-emerald-500/10 hover:text-emerald-600 dark:hover:text-emerald-400"
        } disabled:cursor-default`}
      >
        <ThumbsUp className={`h-4 w-4 ${isPositive ? "fill-current" : ""}`} />
      </motion.button>

      {/* Botón Pulgar Abajo (👎) */}
      <motion.button
        type="button"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        data-testid={`thumbs-down-btn-${messageId}`}
        aria-label={
          translateKey("oppyfy", "feedback.thumbs_down") || "Reportar problema"
        }
        aria-pressed={isNegative}
        disabled={isSubmitting}
        onClick={handleThumbsDownClick}
        className={`touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border transition-all ${
          isNegative
            ? "border-destructive/50 bg-destructive/15 text-destructive shadow-[0_0_12px_rgba(239,68,68,0.3)] ring-1 ring-destructive/40"
            : "border-border bg-card/70 text-muted-foreground hover:border-destructive/40 hover:bg-destructive/10 hover:text-destructive"
        }`}
      >
        <ThumbsDown className={`h-4 w-4 ${isNegative ? "fill-current" : ""}`} />
      </motion.button>

      {/* Indicador de estado si ya se envió feedback */}
      {isPositive && (
        <span
          data-testid="feedback-positive-indicator"
          className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400"
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          <span>
            {translateKey("oppyfy", "feedback.already_voted_positive") ||
              "Respuesta útil"}
          </span>
        </span>
      )}

      {isNegative && (
        <span
          data-testid="feedback-negative-indicator"
          className="inline-flex items-center gap-1 text-[11px] font-medium text-destructive"
        >
          <span>
            {translateKey("oppyfy", "feedback.already_voted_negative") ||
              "Problema reportado"}
          </span>
        </span>
      )}

      {/* Modal de Reporte de Fallo */}
      <FeedbackReportModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleModalSubmit}
        isSubmitting={isSubmitting}
        messageId={messageId}
      />
    </div>
  );
};
