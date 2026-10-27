/**
 * oppytec-frontend/src/features/oppyfy/components/OppyfyHeader.tsx
 * Encabezado de la interfaz de OppyFy:
 * - Selector de hilos recientes
 * - Badge de créditos disponibles sin vencimiento
 * - Medidor semafórico de contexto (verde/ámbar/rojo)
 */

import React from "react";
import { MessageSquarePlus, Coins } from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type { ContextHealthState } from "../types";
import type { ThreadMetadata } from "../hooks/useOppyfyChat";
import { ContextHealthMeter } from "./ContextHealthMeter";

export interface OppyfyHeaderProps {
  readonly threads: readonly ThreadMetadata[];
  readonly currentThreadId: string;
  readonly remainingCredits: number;
  readonly contextHealth: ContextHealthState;
  readonly onSwitchThread: (threadId: string) => void;
  readonly onNewThread: () => void;
  readonly onOpenRolloverModal: () => void;
}

export const OppyfyHeader: React.FC<OppyfyHeaderProps> = ({
  threads,
  currentThreadId,
  remainingCredits,
  contextHealth,
  onSwitchThread,
  onNewThread,
  onOpenRolloverModal,
}) => {
  return (
    <header className="flex flex-col gap-3 border-b border-border pb-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground md:text-2xl">
            {translateKey("oppyfy", "title")}
          </h1>
          <p className="text-xs text-muted-foreground">
            {translateKey("oppyfy", "subtitle")}
          </p>
        </div>

        {/* Billetera de créditos sin vencimiento */}
        <div className="flex items-center gap-2">
          <div
            data-testid="oppyfy-credit-wallet"
            className="flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/10 px-3 py-1.5 font-mono text-xs font-semibold text-primary"
          >
            <Coins className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>
              {translateKey("oppyfy", "chat.credits_remaining", {
                credits: remainingCredits,
              })}
            </span>
            <span className="text-[11px] text-muted-foreground">
              {translateKey("oppyfy", "header.credits_unlimited")}
            </span>
          </div>
        </div>
      </div>

      {/* Barra de control: selector de hilos + Medidor de salud de contexto */}
      <div className="grid grid-cols-1 items-center gap-3 md:grid-cols-12">
        <div className="flex flex-wrap items-center gap-2 md:col-span-6">
          <div className="relative min-w-[200px] flex-1">
            <select
              aria-label={translateKey("oppyfy", "header.thread_aria")}
              data-testid="oppyfy-thread-select"
              value={currentThreadId}
              onChange={(e) => onSwitchThread(e.target.value)}
              className="touch-target min-h-[44px] w-full rounded-md border border-border bg-card px-3 py-2 text-xs font-medium text-foreground shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {threads.map((t) => (
                <option key={t.threadId} value={t.threadId}>
                  {t.title}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            data-testid="oppyfy-new-thread-btn"
            onClick={onNewThread}
            className="touch-target inline-flex min-h-[44px] items-center gap-1.5 rounded-md border border-border bg-secondary px-3 py-2 text-xs font-medium text-secondary-foreground shadow-sm transition hover:bg-secondary/80 focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <MessageSquarePlus className="h-4 w-4" />
            <span>{translateKey("oppyfy", "header.new_thread")}</span>
          </button>
        </div>

        {/* Medidor Semafórico */}
        <div className="md:col-span-6">
          <ContextHealthMeter
            contextHealth={contextHealth}
            onOpenRolloverModal={onOpenRolloverModal}
          />
        </div>
      </div>
    </header>
  );
};
