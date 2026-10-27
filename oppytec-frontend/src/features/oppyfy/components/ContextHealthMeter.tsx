/**
 * oppytec-frontend/src/features/oppyfy/components/ContextHealthMeter.tsx
 * Medidor semafórico visual de salud de contexto RAG:
 * - 🟢 Verde (0% - 65%): Óptimo.
 * - 🟡 Ámbar (66% - 85%): Advertencia preventiva recomendando nuevo hilo.
 * - 🔴 Rojo (>85%): Límite crítico alcanzado; muestra badge de bloqueo
 *   anti-alucinación y botón destacado "Continuar en Hilo Fresco con Resumen Inteligente".
 */

import React from "react";
import { AlertTriangle, CheckCircle2, ShieldAlert, Sparkles } from "lucide-react";
import { translateKey } from "@/shared/i18n";
import type { ContextHealthState } from "../types";

export interface ContextHealthMeterProps {
  readonly contextHealth: ContextHealthState;
  readonly onOpenRolloverModal?: () => void;
  readonly compact?: boolean;
  readonly className?: string;
}

export const ContextHealthMeter: React.FC<ContextHealthMeterProps> = ({
  contextHealth,
  onOpenRolloverModal,
  compact = false,
  className = "",
}) => {
  const { pct, status, isAntiHallucinationBlocked } = contextHealth;

  const statusConfig = {
    green: {
      colorClass: "bg-emerald-500 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
      barBg: "bg-emerald-500",
      label: translateKey("oppyfy", "context_meter.optimal"),
      icon: CheckCircle2,
    },
    amber: {
      colorClass: "bg-amber-500 text-amber-600 dark:text-amber-400 border-amber-500/30",
      barBg: "bg-amber-500",
      label: translateKey("oppyfy", "context_meter.warning"),
      icon: AlertTriangle,
    },
    red: {
      colorClass: "bg-destructive text-destructive border-destructive/40",
      barBg: "bg-destructive",
      label: translateKey("oppyfy", "context_meter.critical"),
      icon: ShieldAlert,
    },
  }[status];

  const StatusIcon = statusConfig.icon;

  return (
    <div
      data-testid="oppyfy-context-meter"
      className={`flex flex-col gap-1.5 rounded-lg border border-border bg-card/60 p-2 text-xs transition-colors ${className}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 font-medium text-foreground">
          <StatusIcon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>{translateKey("oppyfy", "context_meter.label")}:</span>
          <span
            data-testid="context-traffic-status"
            className="font-mono font-bold"
          >
            {`${pct}% (${statusConfig.label})`}
          </span>
        </div>

        {isAntiHallucinationBlocked && (
          <span
            data-testid="anti-hallucination-badge"
            className="inline-flex items-center gap-1 rounded-md border border-destructive/40 bg-destructive/15 px-2 py-0.5 text-[11px] font-bold text-destructive"
          >
            <ShieldAlert className="h-3 w-3" />
            {translateKey("oppyfy", "context_meter.anti_hallucination_badge")}
          </span>
        )}
      </div>

      {/* Barra de progreso visual semafórica */}
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${translateKey("oppyfy", "context_meter.label")} ${pct}%`}
        className="relative h-2 w-full overflow-hidden rounded-full bg-secondary"
      >
        <div
          data-testid="context-meter-bar"
          className={`h-full transition-all duration-300 ${statusConfig.barBg}`}
          style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
        />
      </div>

      {/* Botón destacado cuando se alcanza el límite crítico (>85%) */}
      {status === "red" && onOpenRolloverModal && !compact && (
        <button
          type="button"
          data-testid="rollover-prompt-btn"
          onClick={onOpenRolloverModal}
          className="touch-target mt-1 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-md bg-destructive px-3 py-2 text-xs font-bold text-destructive-foreground shadow-sm transition hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-destructive focus:ring-offset-2"
        >
          <Sparkles className="h-4 w-4" />
          <span>
            {translateKey("oppyfy", "context_meter.continue_fresh_thread")}
          </span>
        </button>
      )}
    </div>
  );
};
