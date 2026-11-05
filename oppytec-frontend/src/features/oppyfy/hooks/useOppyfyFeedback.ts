/**
 * oppytec-frontend/src/features/oppyfy/hooks/useOppyfyFeedback.ts
 * Hook reactivo para el registro de feedback humano (RLHF) y reporte de alucinaciones:
 * - Mutación con TanStack Query v5 a `POST /api/v1/oppy_ai/chat/feedback`
 * - Resiliencia offline/fallback y persistencia local de votos (👍 / 👎)
 * - Toasts accesibles con Sonner y soporte i18n
 */

import { useState, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import { translateKey } from "@/shared/i18n";
import type {
  ChatFeedbackPayload,
  FeedbackResponse,
  FeedbackType,
  FailureCategory,
} from "../types";

export const FEEDBACK_STORAGE_PREFIX = "oppyfy_feedback_v2_";

export interface FeedbackRecord {
  readonly feedbackType: FeedbackType;
  readonly failureCategory?: FailureCategory | null;
  readonly userCorrection?: string | null;
  readonly submittedAt: string;
}

function safeGetStorage<T>(key: string, fallback: T): T {
  if (typeof window === "undefined" || !window.localStorage) {
    return fallback;
  }
  try {
    const item = window.localStorage.getItem(key);
    return item ? (JSON.parse(item) as T) : fallback;
  } catch {
    return fallback;
  }
}

function safeSetStorage<T>(key: string, value: T): void {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage quota errors
  }
}

export function getPersistedFeedback(messageId: string): FeedbackRecord | null {
  return safeGetStorage<FeedbackRecord | null>(
    `${FEEDBACK_STORAGE_PREFIX}${messageId}`,
    null
  );
}

export function persistFeedback(messageId: string, record: FeedbackRecord): void {
  safeSetStorage(`${FEEDBACK_STORAGE_PREFIX}${messageId}`, record);
}

export interface UseOppyfyFeedbackOptions {
  readonly onFeedbackSubmitted?: (
    payload: ChatFeedbackPayload,
    response: FeedbackResponse
  ) => void;
}

export function useOppyfyFeedback(options?: UseOppyfyFeedbackOptions) {
  const queryClient = useQueryClient();
  const [activeFeedbackMap, setActiveFeedbackMap] = useState<
    Record<string, FeedbackRecord>
  >({});

  const mutation = useMutation<FeedbackResponse, Error, ChatFeedbackPayload>({
    mutationFn: async (payload: ChatFeedbackPayload): Promise<FeedbackResponse> => {
      const fallbackResponse: FeedbackResponse = {
        id: payload.message_id,
        status: "success",
        message: "Feedback registrado exitosamente",
        feedback_type: payload.feedback_type,
        failure_category: payload.failure_category ?? null,
        trace_id: payload.trace_id,
        created_at: new Date().toISOString(),
      };

      const res = await apiRequest<FeedbackResponse>(
        "/api/v1/oppy_ai/chat/feedback",
        {
          method: "POST",
          body: {
            message_id: payload.message_id,
            trace_id: payload.trace_id ?? "00000000000000000000000000000000",
            feedback_type: payload.feedback_type,
            failure_category: payload.failure_category ?? null,
            user_correction: payload.user_correction ?? null,
            rating: payload.rating ?? (payload.feedback_type === "positive" ? 5 : 1),
          },
          fallbackData: fallbackResponse,
        }
      );

      return res.data;
    },
    onSuccess: (data, variables) => {
      const record: FeedbackRecord = {
        feedbackType: variables.feedback_type,
        failureCategory: variables.failure_category,
        userCorrection: variables.user_correction,
        submittedAt: new Date().toISOString(),
      };

      persistFeedback(variables.message_id, record);
      setActiveFeedbackMap((prev) => ({
        ...prev,
        [variables.message_id]: record,
      }));

      // Invalida consultas de feedback o chat si existen
      void queryClient.invalidateQueries({ queryKey: ["oppyfy", "feedback"] });

      toast.success(
        translateKey("oppyfy", "feedback.submit_success")
      );

      options?.onFeedbackSubmitted?.(variables, data);
    },
    onError: (err) => {
      toast.error(
        translateKey("oppyfy", "feedback.submit_error") || err.message
      );
    },
  });

  const getFeedbackForMessage = useCallback(
    (messageId: string): FeedbackRecord | null => {
      if (activeFeedbackMap[messageId]) {
        return activeFeedbackMap[messageId];
      }
      return getPersistedFeedback(messageId);
    },
    [activeFeedbackMap]
  );

  const submitFeedback = useCallback(
    async (payload: ChatFeedbackPayload): Promise<FeedbackResponse> => {
      return mutation.mutateAsync(payload);
    },
    [mutation]
  );

  return {
    submitFeedback,
    getFeedbackForMessage,
    isSubmitting: mutation.isPending,
    error: mutation.error,
    reset: mutation.reset,
  };
}
