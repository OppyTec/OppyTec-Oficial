/**
 * oppytec-frontend/src/features/oppyfy/components/OppyfyChatPane.tsx
 * Panel de conversación de OppyFy (v2.0):
 * - Historial de mensajes con avatares y estados
 * - Badges de dominio consultado y herramientas ejecutadas
 * - Citaciones colapsables a fuentes oficiales
 * - Banner de advertencia anti-alucinación
 * - Sugerencias de preguntas rápidas (FEFO, Banquete, Varianza Food Cost)
 * - Protección declarativa RBAC con `<Can perform="oppyfy.workspace.query">`
 */

import React, { useState } from "react";
import {
  Send,
  Sparkles,
  User,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  FileText,
  Wrench,
  Layers,
  Flame,
} from "lucide-react";
import { Can } from "@/shared/auth/Can";
import { translateKey } from "@/shared/i18n";
import type { ChatMessage, ContextHealthState } from "../types";

export interface OppyfyChatPaneProps {
  readonly messages: readonly ChatMessage[];
  readonly draftPrompt: string;
  readonly onChangeDraftPrompt: (text: string) => void;
  readonly onSendMessage: (promptText: string) => Promise<unknown> | void;
  readonly isSending: boolean;
  readonly contextHealth: ContextHealthState;
  readonly onOpenRolloverModal?: () => void;
  readonly onSelectArtifact?: (message: ChatMessage) => void;
}

export const OppyfyChatPane: React.FC<OppyfyChatPaneProps> = ({
  messages,
  draftPrompt,
  onChangeDraftPrompt,
  onSendMessage,
  isSending,
  contextHealth,
  onOpenRolloverModal,
  onSelectArtifact,
}) => {
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});

  const toggleCitations = (messageId: string): void => {
    setExpandedCitations((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    if (draftPrompt.trim() && !isSending) {
      void onSendMessage(draftPrompt);
    }
  };

  const handleSelectQuickPrompt = (prompt: string): void => {
    onChangeDraftPrompt(prompt);
  };

  const isBlocked =
    contextHealth.isAntiHallucinationBlocked || contextHealth.pct > 85;

  return (
    <div
      data-testid="oppyfy-chat-pane"
      className="flex h-full flex-col justify-between rounded-xl border border-border bg-card/60 p-3 md:p-4 shadow-sm"
    >
      {/* Banner de bloqueo preventivo Anti-Hallucination Guard */}
      {isBlocked && (
        <div
          data-testid="anti-hallucination-warning-banner"
          role="alert"
          className="mb-3 flex items-start justify-between gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive"
        >
          <div className="flex items-start gap-2">
            <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">
                {translateKey("oppyfy", "context_meter.anti_hallucination_badge")}
              </p>
              <p className="mt-0.5 text-muted-foreground text-[11px] leading-relaxed">
                {translateKey("oppyfy", "chat.blocked_banner")}
              </p>
            </div>
          </div>

          {onOpenRolloverModal && (
            <button
              type="button"
              data-testid="banner-rollover-btn"
              onClick={onOpenRolloverModal}
              className="touch-target inline-flex min-h-[44px] shrink-0 items-center rounded-md bg-destructive px-3 py-1.5 text-xs font-bold text-destructive-foreground shadow-sm hover:opacity-95"
            >
              Nuevo Hilo
            </button>
          )}
        </div>
      )}

      {/* Historial de mensajes */}
      <div
        data-testid="oppyfy-messages-container"
        className="flex-1 space-y-4 overflow-y-auto pr-1"
      >
        {messages.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center rounded-lg border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
            <Sparkles className="mb-2 h-6 w-6 text-primary/60" />
            <p>{translateKey("oppyfy", "chat.empty_history")}</p>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const isUser = msg.role === "user";
            const citationsOpen = !!expandedCitations[msg.id];
            const hasCitations = msg.citations && msg.citations.length > 0;

            return (
              <div
                key={msg.id}
                data-testid={`chat-message-${msg.id}`}
                className={`flex gap-3 text-xs ${
                  isUser ? "flex-row-reverse" : "flex-row"
                }`}
              >
                {/* Avatar */}
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                    isUser
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-foreground border border-border"
                  }`}
                  aria-label={
                    isUser
                      ? translateKey("oppyfy", "chat.user_avatar")
                      : translateKey("oppyfy", "chat.assistant_avatar")
                  }
                >
                  {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4 text-primary" />}
                </div>

                {/* Burbuja del mensaje */}
                <div
                  className={`max-w-[85%] space-y-2 rounded-xl p-3 shadow-sm ${
                    isUser
                      ? "bg-primary text-primary-foreground"
                      : msg.isBlocked
                      ? "border border-destructive/40 bg-destructive/10 text-destructive"
                      : "border border-border bg-secondary/30 text-foreground"
                  }`}
                >
                  {/* Metadata de la respuesta del asistente */}
                  {!isUser && (
                    <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                      {msg.subdomainSlug && (
                        <span
                          data-testid={`domain-badge-${idx}`}
                          className="inline-flex items-center gap-1 rounded bg-secondary px-1.5 py-0.5 font-mono text-muted-foreground"
                        >
                          <Layers className="h-2.5 w-2.5" />
                          {msg.subdomainSlug}
                        </span>
                      )}
                      {msg.toolExecuted && (
                        <span
                          data-testid={`tool-badge-${idx}`}
                          className="inline-flex items-center gap-1 rounded bg-primary/15 px-1.5 py-0.5 font-mono font-semibold text-primary"
                        >
                          <Wrench className="h-2.5 w-2.5" />
                          {msg.toolExecuted}
                        </span>
                      )}
                      {msg.canvasPayload && onSelectArtifact && (
                        <button
                          type="button"
                          onClick={() => onSelectArtifact(msg)}
                          className="inline-flex items-center gap-1 rounded bg-accent px-1.5 py-0.5 font-semibold text-accent-foreground underline hover:opacity-80"
                        >
                          Ver en Canvas
                        </button>
                      )}
                    </div>
                  )}

                  {/* Contenido formateado */}
                  <div className="whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </div>

                  {/* Citaciones colapsables */}
                  {hasCitations && (
                    <div className="mt-2 border-t border-border/50 pt-1.5">
                      <button
                        type="button"
                        data-testid={`toggle-citations-btn-${msg.id}`}
                        onClick={() => toggleCitations(msg.id)}
                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline"
                      >
                        <FileText className="h-3 w-3" />
                        <span>
                          {citationsOpen
                            ? translateKey("oppyfy", "chat.citations_toggle_hide")
                            : translateKey(
                                "oppyfy",
                                "chat.citations_toggle_show",
                                { count: msg.citations?.length ?? 0 }
                              )}
                        </span>
                        {citationsOpen ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronDown className="h-3 w-3" />
                        )}
                      </button>

                      {citationsOpen && (
                        <ul
                          data-testid={`citation-list-${msg.id}`}
                          className="mt-1.5 space-y-1 rounded-md border border-border bg-card/60 p-2 text-[11px] text-muted-foreground font-mono"
                        >
                          {msg.citations?.map((cit, cIdx) => (
                            <li
                              key={`${msg.id}-cit-${cIdx}`}
                              data-testid={`citation-item-${cIdx}`}
                              className="flex items-start gap-1"
                            >
                              <span className="text-primary font-bold">[{cIdx + 1}]</span>
                              <span>{cit}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Sugerencias de preguntas rápidas */}
      <div className="mt-3 space-y-1.5 border-t border-border pt-2.5">
        <div className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
          <Flame className="h-3.5 w-3.5 text-amber-500" />
          <span>{translateKey("oppyfy", "chat.quick_suggestions_title")}</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            data-testid="quick-suggestion-fefo"
            onClick={() =>
              handleSelectQuickPrompt(
                translateKey("oppyfy", "chat.suggestion_fefo")
              )
            }
            className="touch-target inline-flex min-h-[36px] items-center rounded-full border border-border bg-secondary/50 px-3 py-1 text-[11px] font-medium text-foreground transition hover:border-primary hover:bg-primary/10"
          >
            {translateKey("oppyfy", "chat.suggestion_fefo_label")}
          </button>
          <button
            type="button"
            data-testid="quick-suggestion-banquet"
            onClick={() =>
              handleSelectQuickPrompt(
                translateKey("oppyfy", "chat.suggestion_banquet")
              )
            }
            className="touch-target inline-flex min-h-[36px] items-center rounded-full border border-border bg-secondary/50 px-3 py-1 text-[11px] font-medium text-foreground transition hover:border-primary hover:bg-primary/10"
          >
            {translateKey("oppyfy", "chat.suggestion_banquet_label")}
          </button>
          <button
            type="button"
            data-testid="quick-suggestion-food-cost"
            onClick={() =>
              handleSelectQuickPrompt(
                translateKey("oppyfy", "chat.suggestion_food_cost")
              )
            }
            className="touch-target inline-flex min-h-[36px] items-center rounded-full border border-border bg-secondary/50 px-3 py-1 text-[11px] font-medium text-foreground transition hover:border-primary hover:bg-primary/10"
          >
            {translateKey("oppyfy", "chat.suggestion_food_cost_label")}
          </button>
        </div>
      </div>

      {/* Input de consulta con protección RBAC */}
      <form onSubmit={handleSubmit} className="mt-2.5 flex items-center gap-2">
        <input
          type="text"
          aria-label="Prompt OppyFy"
          data-testid="oppyfy-prompt-input"
          value={draftPrompt}
          onChange={(e) => onChangeDraftPrompt(e.target.value)}
          placeholder={translateKey("oppyfy", "chat.placeholder", {
            brandName: "OppyFy",
          })}
          disabled={isSending || isBlocked}
          className="touch-target min-h-[44px] flex-1 rounded-md border border-border bg-card px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
        />

        <Can perform="oppyfy.workspace.query">
          <button
            type="submit"
            data-testid="oppyfy-send-btn"
            disabled={!draftPrompt.trim() || isSending || isBlocked}
            className="touch-target inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-md bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">
              {isSending
                ? translateKey("oppyfy", "chat.sending")
                : translateKey("oppyfy", "chat.send_btn")}
            </span>
          </button>
        </Can>
      </form>
    </div>
  );
};
