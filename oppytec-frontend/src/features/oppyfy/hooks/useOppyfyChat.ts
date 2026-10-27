/**
 * oppytec-frontend/src/features/oppyfy/hooks/useOppyfyChat.ts
 * Hook reactivo para el espacio conversacional de OppyFy (v2.0):
 * - Envío a `POST /api/v1/oppyfy/chat`
 * - Control semafórico (<65% verde, 66-85% ámbar, >85% rojo)
 * - Bloqueo anti-alucinación automático cuando el contexto supera el 85%
 * - Rollover a hilo fresco al 5.00% vía `POST /api/v1/oppyfy/threads/{id}/rollover`
 * - Persistencia local segura de borradores e historial de hilos
 */

import { useState, useCallback, useMemo } from "react";
import { apiRequest } from "@/shared/api/httpClient";
import type {
  ChatMessage,
  CanvasArtifact,
  ContextHealthState,
  OppyfyChatRequest,
  OppyfyChatResponse,
  OppyfyThreadRolloverRequest,
  OppyfyThreadRolloverResponse,
} from "../types";
import {
  calculateContextHealth,
  FRESH_THREAD_CONTEXT_PCT,
} from "../types";

export interface ThreadMetadata {
  readonly threadId: string;
  readonly title: string;
  readonly updatedAt: string;
  readonly lastContextPct: number;
}

export interface UseOppyfyChatOptions {
  readonly initialThreadId?: string;
  readonly initialRemainingCredits?: number;
  readonly initialContextPct?: number;
  readonly defaultSubdomainSlug?: string;
}

const STORAGE_PREFIX = "oppyfy_v2";

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
    // Ignore storage quota errors in test/restricted environments
  }
}

function generateUuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `thread-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useOppyfyChat(options?: UseOppyfyChatOptions) {
  const initialThreadId = useMemo(
    () => options?.initialThreadId ?? generateUuid(),
    [options?.initialThreadId]
  );

  const [currentThreadId, setCurrentThreadId] = useState<string>(initialThreadId);
  const [remainingCredits, setRemainingCredits] = useState<number>(
    options?.initialRemainingCredits ?? 100
  );
  const [contextHealth, setContextHealth] = useState<ContextHealthState>(() =>
    calculateContextHealth(options?.initialContextPct ?? 0)
  );
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    safeGetStorage<ChatMessage[]>(
      `${STORAGE_PREFIX}_messages_${initialThreadId}`,
      []
    )
  );
  const [threads, setThreads] = useState<ThreadMetadata[]>(() =>
    safeGetStorage<ThreadMetadata[]>(`${STORAGE_PREFIX}_threads`, [
      {
        threadId: initialThreadId,
        title: "Nuevo Hilo OppyFy",
        updatedAt: new Date().toISOString(),
        lastContextPct: options?.initialContextPct ?? 0,
      },
    ])
  );
  const [draftPrompt, setDraftPromptState] = useState<string>(() =>
    safeGetStorage<string>(`${STORAGE_PREFIX}_draft_${initialThreadId}`, "")
  );
  const [activeCanvasArtifact, setActiveCanvasArtifact] = useState<CanvasArtifact | null>(null);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Sync draft prompt to storage when user types
  const setDraftPrompt = useCallback(
    (text: string) => {
      setDraftPromptState(text);
      safeSetStorage(`${STORAGE_PREFIX}_draft_${currentThreadId}`, text);
    },
    [currentThreadId]
  );

  // Switch active thread
  const switchThread = useCallback((threadId: string) => {
    setCurrentThreadId(threadId);
    const storedMessages = safeGetStorage<ChatMessage[]>(
      `${STORAGE_PREFIX}_messages_${threadId}`,
      []
    );
    setMessages(storedMessages);
    const storedDraft = safeGetStorage<string>(
      `${STORAGE_PREFIX}_draft_${threadId}`,
      ""
    );
    setDraftPromptState(storedDraft);
    setError(null);

    // Calculate context from last message or fallback
    const lastMsgWithPct = [...storedMessages]
      .reverse()
      .find((m) => m.contextUsagePct !== undefined);
    const pct = lastMsgWithPct?.contextUsagePct ?? 0;
    setContextHealth(calculateContextHealth(pct));
  }, []);

  // Send message to OppyFy backend
  const sendMessage = useCallback(
    async (
      promptText: string,
      sendOptions?: {
        targetSubdomainSlug?: string;
        canViewCosts?: boolean;
        estimatedCost?: number;
      }
    ): Promise<ChatMessage | null> => {
      const cleanPrompt = promptText.trim();
      if (!cleanPrompt) return null;

      // Anti-Hallucination Guard: Context > 85% is strictly blocked
      if (contextHealth.isAntiHallucinationBlocked || contextHealth.pct > 85) {
        const blockErrorMsg =
          "Bloqueo anti-alucinación activo (>85% de contexto). Debe continuar en un hilo fresco mediante rollover para prevenir respuestas distorsionadas.";
        setError(blockErrorMsg);

        const blockedMessage: ChatMessage = {
          id: generateUuid(),
          role: "assistant",
          content: blockErrorMsg,
          contextUsagePct: contextHealth.pct,
          timestamp: new Date().toISOString(),
          isBlocked: true,
          status: "blocked",
          threadId: currentThreadId,
        };

        const updatedMessages = [...messages, blockedMessage];
        setMessages(updatedMessages);
        safeSetStorage(
          `${STORAGE_PREFIX}_messages_${currentThreadId}`,
          updatedMessages
        );
        return blockedMessage;
      }

      setError(null);
      setIsSending(true);

      const userMessage: ChatMessage = {
        id: generateUuid(),
        role: "user",
        content: cleanPrompt,
        timestamp: new Date().toISOString(),
        threadId: currentThreadId,
        status: "success",
      };

      const messagesWithUser = [...messages, userMessage];
      setMessages(messagesWithUser);
      setDraftPromptState("");
      safeSetStorage(`${STORAGE_PREFIX}_draft_${currentThreadId}`, "");
      safeSetStorage(
        `${STORAGE_PREFIX}_messages_${currentThreadId}`,
        messagesWithUser
      );

      try {
        const payload: OppyfyChatRequest = {
          prompt_text: cleanPrompt,
          target_subdomain_slug:
            sendOptions?.targetSubdomainSlug ??
            options?.defaultSubdomainSlug ??
            "recipes_kitchen",
          can_view_costs: sendOptions?.canViewCosts ?? false,
          prior_thread_tokens: Math.round(contextHealth.pct * 100),
          remaining_credits: remainingCredits,
          estimated_credit_cost: sendOptions?.estimatedCost ?? 1.0,
          thread_id: currentThreadId,
        };

        const response = await apiRequest<OppyfyChatResponse>(
          "/api/v1/oppyfy/chat",
          {
            method: "POST",
            body: payload,
          }
        );

        const chatRes = response.data;
        const newContextPct = Number(chatRes.context_usage_percent);
        const updatedContextHealth = calculateContextHealth(newContextPct);
        setContextHealth(updatedContextHealth);

        const newRemaining = Number(chatRes.remaining_credits);
        setRemainingCredits(newRemaining);

        // Convert tool payload to canvas artifact if present
        let canvasArtifact: CanvasArtifact | null = null;
        if (chatRes.tool_payload && typeof chatRes.tool_payload === "object") {
          const payloadObj = chatRes.tool_payload;
          const artifactType =
            payloadObj.tipo_grafico || payloadObj.chart_type
              ? "chart"
              : payloadObj.items || payloadObj.columns || Array.isArray(payloadObj.data)
                ? "table"
                : "action_card";

          canvasArtifact = {
            type: artifactType,
            title:
              (payloadObj.title as string) ??
              (payloadObj.titulo as string) ??
              `Artefacto: ${chatRes.tool_executed ?? "OppyFy"}`,
            data: payloadObj.data ?? payloadObj.items ?? payloadObj,
            summary: chatRes.answer_text,
            columns: (payloadObj.columns as string[]) ?? undefined,
          };
          setActiveCanvasArtifact(canvasArtifact);
        }

        const citations = Array.isArray(chatRes.tool_payload?.citations)
          ? (chatRes.tool_payload.citations as string[])
          : [];

        const assistantMessage: ChatMessage = {
          id: generateUuid(),
          role: "assistant",
          content: chatRes.answer_text,
          citations,
          canvasPayload: canvasArtifact,
          contextUsagePct: newContextPct,
          creditsSpent: Number(chatRes.credits_deducted),
          timestamp: new Date().toISOString(),
          isBlocked: !chatRes.allowed,
          status: chatRes.allowed ? "success" : "blocked",
          threadId: currentThreadId,
          subdomainSlug: chatRes.subdomain_slug,
          toolExecuted: chatRes.tool_executed,
        };

        const finalizedMessages = [...messagesWithUser, assistantMessage];
        setMessages(finalizedMessages);
        safeSetStorage(
          `${STORAGE_PREFIX}_messages_${currentThreadId}`,
          finalizedMessages
        );

        // Update threads metadata
        setThreads((prevThreads) => {
          const title =
            messages.length === 0
              ? cleanPrompt.slice(0, 40)
              : prevThreads.find((t) => t.threadId === currentThreadId)?.title ??
                "Conversación OppyFy";

          const nextThreads = prevThreads.map((t) =>
            t.threadId === currentThreadId
              ? {
                  ...t,
                  title,
                  updatedAt: new Date().toISOString(),
                  lastContextPct: newContextPct,
                }
              : t
          );
          safeSetStorage(`${STORAGE_PREFIX}_threads`, nextThreads);
          return nextThreads;
        });

        return assistantMessage;
      } catch (err) {
        const errorMsg =
          err instanceof Error
            ? err.message
            : "Error inesperado al consultar a OppyFy";
        setError(errorMsg);

        const errorMessage: ChatMessage = {
          id: generateUuid(),
          role: "assistant",
          content: `No fue posible completar la consulta: ${errorMsg}`,
          timestamp: new Date().toISOString(),
          status: "error",
          threadId: currentThreadId,
        };

        const updatedMessages = [...messagesWithUser, errorMessage];
        setMessages(updatedMessages);
        safeSetStorage(
          `${STORAGE_PREFIX}_messages_${currentThreadId}`,
          updatedMessages
        );
        return errorMessage;
      } finally {
        setIsSending(false);
      }
    },
    [
      messages,
      currentThreadId,
      contextHealth,
      remainingCredits,
      options?.defaultSubdomainSlug,
    ]
  );

  // Assisted thread rollover: Resets context to 5.00% with structured synthesis
  const rolloverToFreshThread = useCallback(
    async (summaryNotes?: string): Promise<string> => {
      setIsSending(true);
      setError(null);
      try {
        const payload: OppyfyThreadRolloverRequest = {
          summary_notes: summaryNotes ?? "Traspaso de hilo con resumen sintético estructurado",
          prior_thread_tokens: Math.round(contextHealth.pct * 100),
        };

        const response = await apiRequest<OppyfyThreadRolloverResponse>(
          `/api/v1/oppyfy/threads/${currentThreadId}/rollover`,
          {
            method: "POST",
            body: payload,
          }
        );

        const rolloverRes = response.data;
        const newThreadId = rolloverRes.new_thread_id;
        const freshPct = Number(rolloverRes.fresh_context_usage_percent);

        // Reset context health to fresh 5%
        const freshHealth = calculateContextHealth(freshPct || FRESH_THREAD_CONTEXT_PCT);
        setContextHealth(freshHealth);
        setCurrentThreadId(newThreadId);
        setActiveCanvasArtifact(null);
        setDraftPromptState("");

        const handoverMessage: ChatMessage = {
          id: generateUuid(),
          role: "assistant",
          content: `${rolloverRes.message}\n\n**Resumen del Hilo Anterior:**\n${rolloverRes.summary_artifact}`,
          contextUsagePct: freshPct,
          creditsSpent: 0,
          timestamp: new Date().toISOString(),
          threadId: newThreadId,
          status: "success",
        };

        const initialNewMessages = [handoverMessage];
        setMessages(initialNewMessages);
        safeSetStorage(
          `${STORAGE_PREFIX}_messages_${newThreadId}`,
          initialNewMessages
        );

        // Register new thread in history
        setThreads((prev) => {
          const newThreadMeta: ThreadMetadata = {
            threadId: newThreadId,
            title: `Continuación: ${rolloverRes.summary_artifact.slice(0, 30)}...`,
            updatedAt: new Date().toISOString(),
            lastContextPct: freshPct,
          };
          const next = [newThreadMeta, ...prev];
          safeSetStorage(`${STORAGE_PREFIX}_threads`, next);
          return next;
        });

        return newThreadId;
      } catch (err) {
        const errorMsg =
          err instanceof Error
            ? err.message
            : "Error al realizar el rollover del hilo";
        setError(errorMsg);
        throw err;
      } finally {
        setIsSending(false);
      }
    },
    [currentThreadId, contextHealth.pct]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setContextHealth(calculateContextHealth(0));
    safeSetStorage(`${STORAGE_PREFIX}_messages_${currentThreadId}`, []);
  }, [currentThreadId]);

  return {
    messages,
    currentThreadId,
    remainingCredits,
    contextHealth,
    draftPrompt,
    setDraftPrompt,
    activeCanvasArtifact,
    setActiveCanvasArtifact,
    isSending,
    error,
    threads,
    switchThread,
    sendMessage,
    rolloverToFreshThread,
    clearMessages,
  };
}
