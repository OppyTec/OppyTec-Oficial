import { useState } from "react";
import { Can } from "@/shared/auth/Can";
import { useBarcodeScanner } from "@/shared/hooks/useBarcodeScanner";
import { translateKey } from "@/shared/i18n";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";

const OPERATIONS_VIEWS = [
  "Consumo",
  "Eventos",
  "Buffet",
  "Actividades",
  "Alertas",
  "Notificaciones",
  "Historial",
] as const;

export type OperationsViewTab = (typeof OPERATIONS_VIEWS)[number];

export function OperationsFeatureView() {
  const [activeView, setActiveView] = useState<OperationsViewTab>("Consumo");
  const [voiceHandsFree, setVoiceHandsFree] = useState<boolean>(false);
  const { lastScannedCode, simulateScan } = useBarcodeScanner();
  const { authorizedEvents } = useRealtimeSync();

  return (
    <section
      data-testid="feature-operations"
      className="glass-card space-y-4 rounded-xl p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            {translateKey("operations", "title")}
          </h2>
          <p className="text-xs text-muted-foreground">
            {translateKey("operations", "production.batch_code", {
              batchId: "PROD-20261019-A",
            })}
            {" · "}
            {translateKey("operations", "production.station", {
              stationName: "Cocina Caliente & Grill",
            })}
          </p>
        </div>

        <Can perform="operations.pos.consume">
          <button
            type="button"
            data-testid="operations-voice-handsfree-btn"
            aria-pressed={voiceHandsFree}
            onClick={() => setVoiceHandsFree((prev) => !prev)}
            className={`touch-target inline-flex min-h-[44px] items-center rounded-lg px-3 py-1.5 text-xs font-bold ${
              voiceHandsFree
                ? "animate-perimeter-glow bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground"
            }`}
          >
            {voiceHandsFree
              ? "Voz Manos Libres: ACTIVO"
              : "Activar Voz Manos Libres"}
          </button>
        </Can>
      </div>

      {/* 7 Sub-Vistas Operativas */}
      <div className="flex flex-wrap gap-1.5">
        {OPERATIONS_VIEWS.map((view) => (
          <button
            key={view}
            type="button"
            data-testid={`operations-tab-${view}`}
            onClick={() => setActiveView(view)}
            className={`touch-target inline-flex min-h-[44px] items-center rounded-lg px-3 py-1.5 text-xs font-semibold ${
              activeView === view
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground"
            }`}
          >
            {view}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div
          data-testid={`operations-panel-${activeView}`}
          className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <h3 className="text-xs font-bold uppercase text-muted-foreground">
            {`Vista Operativa: ${activeView} (Notas, Tareas & Turnos)`}
          </h3>
          <p className="text-xs text-foreground">
            {translateKey("operations", "counts.variance_summary", {
              delta: "-0.25",
              unit: "kg",
            })}
          </p>
          <div className="flex items-center justify-between border-t border-border pt-2 text-xs">
            <span className="font-mono">{`Barcode: ${lastScannedCode}`}</span>
            <button
              type="button"
              data-testid="operations-scan-barcode-btn"
              onClick={() => simulateScan("7809988776655")}
              className="touch-target inline-flex min-h-[44px] items-center rounded-md bg-secondary px-2.5 py-1 text-xs font-semibold text-secondary-foreground"
            >
              Simular Lector QR/EAN
            </button>
          </div>
        </div>

        {/* Stream WebSocket Tiempo Real (Cero Polling HTTP) */}
        <div
          data-testid="operations-realtime-feed"
          className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3"
        >
          <h3 className="text-xs font-bold uppercase text-muted-foreground">
            Alertas & Notificaciones Push (WS /api/v1/ws/realtime)
          </h3>
          <ul className="space-y-1.5 text-xs">
            {authorizedEvents.map((evt) => (
              <li
                key={evt.eventId}
                className="flex items-center justify-between rounded-md border border-border bg-card px-2.5 py-1.5 font-mono text-[11px]"
              >
                <span className="font-semibold text-primary">
                  {evt.eventType}
                </span>
                <span className="text-muted-foreground">#{evt.eventId}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
