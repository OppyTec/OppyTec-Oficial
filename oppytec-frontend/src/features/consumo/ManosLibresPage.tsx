// oppytec-frontend/src/features/consumo/ManosLibresPage.tsx
/**
 * Vista 2: Consumo Manos Libres (/consumo/manos-libres)
 * OppyTec v2.0 - PLAN_MAESTRO_CONSUMO.md Fase 6
 * - SectionHeader centrado (#f97316, Mic).
 * - Selección de Área Operativa y Bodega.
 * - Estaciones de trabajo y selección de operarios.
 * - Control interactivo de reconocimiento por voz (Web Speech API / Azure ASR).
 * - Consola de transcripción en vivo e input manual de contingencia.
 * - Feed en tiempo real de órdenes de voz con confirmación y descarte.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Send,
  CheckCircle2,
  XCircle,
  Clock,
  Flame,
  UtensilsCrossed,
  ChefHat,
  Radio,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/shared/components/ui/SectionHeader";
import { AreaSelector } from "@/shared/components/layout/AreaSelector";
import { BodegaSelector } from "@/shared/components/layout/BodegaSelector";
import { cn } from "@/shared/lib/utils";
import { useManosLibres } from "./hooks/useManosLibres";
import type { WorkerStation, VoiceOrderLog } from "./types";

export function ManosLibresPage() {
  const { t } = useTranslation("operations");
  const [areaId, setAreaId] = useState<string | null>(null);
  const [bodegaId, setBodegaId] = useState<string>("all");
  const [ttsEnabled, setTtsEnabled] = useState<boolean>(true);
  const [manualInput, setManualInput] = useState<string>("");

  const {
    stations,
    selectedStationId,
    setSelectedStationId,
    activeStation,
    isListening,
    transcript,
    interimTranscript,
    pendingOrders,
    startListening,
    stopListening,
    speakFeedback,
    registerVoiceOrder,
    confirmVoiceOrder,
    rejectVoiceOrder,
  } = useManosLibres();

  const handleToggleListening = () => {
    if (isListening) {
      stopListening();
      if (ttsEnabled) {
        speakFeedback(
          t("consumption.manos_libres.listening.feedback_paused", {
            defaultValue: "Escucha pausada",
          })
        );
      }
    } else {
      startListening();
      if (ttsEnabled) {
        speakFeedback(
          t("consumption.manos_libres.listening.feedback_active", {
            station: activeStation?.name || "activa",
            defaultValue: `Estación ${activeStation?.name || "activa"}, escuchando`,
          })
        );
      }
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualInput.trim()) return;

    const commandText = manualInput.trim();
    setManualInput("");

    try {
      await registerVoiceOrder({
        station_id: activeStation?.id ?? 1,
        texto_transcrito: commandText,
        accion_detectada: commandText.toLowerCase().includes("merma")
          ? "MERMA"
          : "CONSUMO",
        confianza_ia: 0.98,
        items_interpretados: [
          {
            nombre: commandText.replace(/oppy/i, "").trim() || "Insumo de cocina",
            cantidad: 1,
            unidad: "unidad",
          },
        ],
      });
      toast.success(
        t("consumption.manos_libres.console.success_manual", {
          defaultValue: "Comanda de voz ingresada manualmente",
        })
      );
      if (ttsEnabled) {
        speakFeedback(
          t("consumption.manos_libres.tts.feedback_manual_order", {
            defaultValue: "Comanda manual ingresada",
          })
        );
      }
    } catch {
      toast.error(
        t("consumption.manos_libres.console.error_manual", {
          defaultValue: "Error al registrar comando manual",
        })
      );
    }
  };

  const handleConfirmOrder = async (orderId: string) => {
    try {
      await confirmVoiceOrder({
        id: orderId,
        bodegaId: bodegaId === "all" ? 1 : Number(bodegaId) || 1,
      });
      toast.success("Comanda confirmada y registrada en Kardex");
      if (ttsEnabled) speakFeedback("Consumo registrado en Kardex");
    } catch {
      toast.error("Error al confirmar comanda");
    }
  };

  const handleRejectOrder = async (orderId: string) => {
    try {
      await rejectVoiceOrder(orderId);
      toast.info("Comanda descartada");
      if (ttsEnabled) speakFeedback("Comanda descartada");
    } catch {
      toast.error("Error al descartar comanda");
    }
  };

  return (
    <div
      className="relative min-h-screen px-2 md:px-6 py-4 space-y-6 pb-24"
      data-testid="manos-libres-page"
    >
      {/* ─── 1. CABECERA CANÓNICA CENTRADA (#f97316) ─── */}
      <SectionHeader
        title={t("consumption.manos_libres.title", { defaultValue: "Consumo Manos Libres" })}
        subtitle={t("consumption.manos_libres.subtitle", {
          defaultValue: "Registro operativo por voz para cocina, barra y preparación",
        })}
        icon={Mic}
        color="#f97316"
        center={true}
      />

      {/* ─── 2. TOOLBAR DE CONTEXTO Y AJUSTES ─── */}
      <div
        className="bg-card backdrop-blur-md p-4 rounded-3xl border border-border shadow-xl"
        data-testid="manos-libres-toolbar"
      >
        <div className="bg-muted/40 p-3 rounded-2xl border border-border flex flex-col lg:flex-row items-center justify-between gap-4 w-full">
          {/* Selectores de Área y Bodega */}
          <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3 w-full lg:w-auto shrink-0">
            <AreaSelector
              className="w-auto shrink-0"
              buttonClassName="h-10 rounded-xl bg-background border-border shadow-sm text-xs font-bold min-w-[150px]"
              selectedAreaId={areaId || "all"}
              onSelectArea={(id: string) => setAreaId(id === "all" ? null : id)}
            />
            <BodegaSelector
              className="w-auto min-w-[170px] shrink-0 h-10 rounded-xl bg-background border-border shadow-sm text-xs font-bold"
              activeWarehouseId={bodegaId}
              onSelectWarehouse={setBodegaId}
              allowAll={true}
            />
          </div>

          {/* Toggle de Síntesis TTS y Estado de Red */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-background border border-border text-xs font-bold text-muted-foreground">
              <Radio className="h-4 w-4 text-emerald-500 animate-pulse shrink-0" />
              <span className="hidden sm:inline">Reconocimiento ASR Activo</span>
            </div>

            <button
              type="button"
              data-testid="voice-tts-toggle"
              onClick={() => setTtsEnabled(!ttsEnabled)}
              className={cn(
                "flex items-center gap-2 h-10 px-3.5 rounded-xl border text-xs font-bold transition-all cursor-pointer",
                ttsEnabled
                  ? "bg-[#f97316]/15 text-[#f97316] border-[#f97316]/30 font-black shadow-sm"
                  : "bg-background text-muted-foreground border-border hover:text-foreground"
              )}
              title="Activar/Desactivar confirmación por voz (TTS)"
            >
              {ttsEnabled ? (
                <>
                  <Volume2 className="h-4 w-4" />
                  <span className="hidden sm:inline">Voz TTS Activada</span>
                </>
              ) : (
                <>
                  <VolumeX className="h-4 w-4" />
                  <span className="hidden sm:inline">Voz Silenciada</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ─── 3. ESTACIONES DE TRABAJO Y OPERARIOS ─── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <ChefHat className="h-5 w-5 text-[#f97316]" />
            <h3 className="text-sm font-black uppercase tracking-wider text-foreground">
              Estaciones de Cocina y Operarios
            </h3>
          </div>
          <span className="text-xs text-muted-foreground font-bold">
            Selecciona la estación activa para asociar comandas
          </span>
        </div>

        <div
          data-testid="stations-grid"
          className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3"
        >
          {stations.map((st: WorkerStation) => {
            const isSelected = selectedStationId === st.id;
            return (
              <button
                type="button"
                key={st.id}
                data-testid={`station-card-${st.id}`}
                onClick={() => setSelectedStationId(st.id)}
                className={cn(
                  "p-3.5 rounded-2xl border text-left transition-all cursor-pointer flex items-center gap-3 relative select-none",
                  isSelected
                    ? "bg-[#f97316]/10 border-[#f97316] shadow-md scale-102 font-black"
                    : "bg-card border-border hover:border-border/80 text-muted-foreground"
                )}
              >
                <div
                  className={cn(
                    "h-11 w-11 rounded-xl flex items-center justify-center shrink-0 border",
                    isSelected
                      ? "bg-[#f97316] text-white border-[#f97316] shadow-md shadow-[#f97316]/30"
                      : "bg-muted text-foreground border-border"
                  )}
                >
                  <ChefHat className="h-5 w-5" />
                </div>

                <div className="min-w-0 flex-1">
                  <p className="text-xs font-black uppercase text-foreground truncate">
                    {st.name}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate">
                    {st.role}
                  </p>
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-muted text-muted-foreground border border-border/60">
                      Clave: &ldquo;{st.voice_command}&rdquo;
                    </span>
                  </div>
                </div>

                {isSelected && (
                  <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-[#f97316] animate-ping" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* ─── 4. CONTROL CENTRAL DE ESCUCHA Y CONSOLA EN VIVO ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Panel Izquierdo: Botón Central de Escucha (lg:col-span-5) */}
        <div className="lg:col-span-5 bg-card p-6 rounded-3xl border border-border shadow-xl flex flex-col items-center justify-center text-center space-y-6 min-h-[360px]">
          <div className="space-y-1">
            <span className="text-xs font-black uppercase tracking-wider text-[#f97316]">
              {activeStation ? activeStation.name : "Estación Principal"}
            </span>
            <h4 className="text-xl font-black text-foreground tracking-tight">
              Control de Audio en Cocina
            </h4>
            <p className="text-xs text-muted-foreground max-w-xs">
              Presiona el botón o di &ldquo;Oppy&rdquo; seguido de tu orden de consumo o merma
            </p>
          </div>

          {/* Gran Botón de Micrófono Interactivo */}
          <div className="relative flex items-center justify-center">
            {isListening && (
              <div className="absolute h-36 w-36 rounded-full bg-emerald-500/20 animate-ping" />
            )}

            <button
              type="button"
              data-testid="voice-mic-btn"
              onClick={handleToggleListening}
              className={cn(
                "relative z-10 h-28 w-28 rounded-full flex flex-col items-center justify-center gap-1 text-white shadow-2xl transition-all cursor-pointer active:scale-95 border-4",
                isListening
                  ? "bg-emerald-500 border-emerald-400 shadow-emerald-500/40 animate-pulse"
                  : "bg-[#f97316] border-[#f97316]/50 shadow-[#f97316]/30 hover:bg-[#ea580c] hover:scale-105"
              )}
              title={isListening ? "Detener escucha" : "Iniciar escucha"}
            >
              {isListening ? (
                <>
                  <Mic className="h-9 w-9" />
                  <span className="text-[10px] font-black uppercase tracking-wider">
                    {t("consumption.manos_libres.listening.listening_badge", { defaultValue: "Escuchando" })}
                  </span>
                </>
              ) : (
                <>
                  <MicOff className="h-9 w-9" />
                  <span className="text-[10px] font-black uppercase tracking-wider">
                    {t("consumption.manos_libres.listening.activate_mic", { defaultValue: "Iniciar" })}
                  </span>
                </>
              )}
            </button>
          </div>

          {/* Feedback de Estado */}
          <div className="space-y-1 text-center">
            <p className="text-xs font-black uppercase tracking-wider text-foreground">
              {isListening
                ? "🎙️ Micrófono Abierto: Di tu comanda"
                : "Micrófono en Pausa"}
            </p>
            <p className="text-[11px] text-muted-foreground">
              Comandos de ejemplo: &ldquo;Oppy consumo 2 kilos de salmón&rdquo; · &ldquo;Oppy merma 1 paquete de queso&rdquo;
            </p>
          </div>
        </div>

        {/* Panel Derecho: Consola de Transcripción e Input de Contingencia (lg:col-span-7) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Consola Terminal Glassmorphic */}
          <div
            data-testid="voice-transcript-console"
            className="p-5 rounded-3xl bg-black/85 border border-border shadow-xl text-white space-y-3 font-mono min-h-[220px] flex flex-col justify-between"
          >
            <div className="flex items-center justify-between border-b border-white/10 pb-2">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <Sparkles className="h-4 w-4" />
                <span>TRANSCRIPCIÓN EN TIEMPO REAL (ASR)</span>
              </div>
              <span className="text-[10px] text-white/50">
                {isListening ? "EN VIVO" : "STANDBY"}
              </span>
            </div>

            <div className="flex-1 space-y-2 py-2">
              {interimTranscript && (
                <p
                  data-testid="voice-interim-transcript"
                  className="text-xs text-yellow-400 animate-pulse italic"
                >
                  &gt; {interimTranscript} ...
                </p>
              )}

              {transcript ? (
                <p
                  data-testid="voice-final-transcript"
                  className="text-sm font-bold text-emerald-300 leading-relaxed"
                >
                  &gt; &ldquo;{transcript}&rdquo;
                </p>
              ) : (
                !interimTranscript && (
                  <p className="text-xs text-white/40 italic">
                    Esperando audio... Las órdenes habladas aparecerán aquí transcritas al instante.
                  </p>
                )
              )}
            </div>

            <div className="border-t border-white/10 pt-2 flex items-center justify-between text-[10px] text-white/50">
              <span>Palabra clave: &ldquo;Oppy&rdquo;</span>
              <span>Motor Web Speech API</span>
            </div>
          </div>

          {/* Formulario Manual de Contingencia */}
          <form
            onSubmit={handleManualSubmit}
            className="p-3.5 rounded-2xl border border-border bg-card shadow-sm flex items-center gap-2"
          >
            <input
              type="text"
              data-testid="voice-manual-input"
              value={manualInput}
              onChange={(e) => setManualInput(e.target.value)}
              placeholder={t("consumption.manos_libres.console.placeholder", {
                defaultValue: "Contingencia: escribe comanda manual (ej: Oppy consumo 2 kilos de salmon)...",
              })}
              className="flex-1 h-10 px-3.5 rounded-xl border border-border bg-background text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-[#f97316]/40"
            />
            <button
              type="submit"
              data-testid="voice-manual-send-btn"
              disabled={!manualInput.trim()}
              className="h-10 px-4 rounded-xl bg-[#f97316] text-white text-xs font-bold uppercase tracking-wider hover:bg-[#ea580c] disabled:opacity-40 transition-all cursor-pointer flex items-center gap-1.5 shadow-md active:scale-95"
            >
              <Send className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">
                {t("consumption.manos_libres.console.send_button", { defaultValue: "Enviar" })}
              </span>
            </button>
          </form>
        </div>
      </div>

      {/* ─── 5. FEED EN TIEMPO REAL DE COMANDAS RECIBIDAS ─── */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-primary" />
            <h3 className="text-sm font-black uppercase tracking-wider text-foreground">
              Comandas por Voz en Espera ({pendingOrders.length})
            </h3>
          </div>
          <span className="text-xs text-muted-foreground font-bold">
            Verifica y confirma las salidas deducidas automáticamente
          </span>
        </div>

        <div
          data-testid="voice-pending-orders-feed"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {pendingOrders.length === 0 ? (
            <div className="col-span-full py-16 text-center space-y-2 border border-dashed border-border rounded-3xl bg-card/40 text-muted-foreground">
              <UtensilsCrossed className="h-10 w-10 mx-auto opacity-40" />
              <p className="text-xs font-bold uppercase tracking-wider">
                {t("consumption.manos_libres.orders.empty", { defaultValue: "Sin órdenes verbales pendientes" })}
              </p>
              <p className="text-[11px] max-w-sm mx-auto">
                Las órdenes dictadas por los cocineros se listarán aquí en tiempo real para su aprobación inmediata.
              </p>
            </div>
          ) : (
            pendingOrders.map((ord: VoiceOrderLog) => {
              const isMerma = ord.action_type === "merma";
              const timeDisplay = ord.timestamp
                ? new Date(ord.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "Ahora";

              return (
                <div
                  key={ord.solicitud_id}
                  data-testid={`voice-order-card-${ord.solicitud_id}`}
                  className={cn(
                    "p-4 rounded-3xl border bg-card shadow-md space-y-3 transition-all",
                    isMerma ? "border-destructive/40" : "border-emerald-500/40"
                  )}
                >
                  {/* Cabecera de la Comanda */}
                  <div className="flex items-center justify-between border-b border-border/50 pb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "px-2.5 py-0.5 rounded-full text-[10px] font-black tracking-wider uppercase border",
                          isMerma
                            ? "bg-destructive/15 text-destructive border-destructive/30"
                            : "bg-emerald-500/15 text-emerald-600 border-emerald-500/30"
                        )}
                      >
                        {isMerma ? "MERMA" : "CONSUMO"}
                      </span>
                      <span className="text-xs font-bold text-foreground">
                        {ord.worker?.name || "Operario"}
                      </span>
                    </div>

                    <span className="text-[10px] font-bold text-muted-foreground">
                      {timeDisplay}
                    </span>
                  </div>

                  {/* Detalle del Ítem */}
                  <div className="space-y-1">
                    <p className="text-sm font-black text-foreground">
                      {ord.item?.name || "Ítem de consumo"}
                    </p>
                    <p className="text-xs font-bold text-muted-foreground">
                      Cantidad:{" "}
                      <span className="text-foreground font-black">
                        {ord.item?.quantity} {ord.item?.unit || "und"}
                      </span>
                    </p>
                    {isMerma && ord.motivo_merma && (
                      <p className="text-[11px] text-destructive font-medium flex items-center gap-1">
                        <Flame className="h-3 w-3 shrink-0" />
                        <span>Motivo: {ord.motivo_merma}</span>
                      </p>
                    )}
                  </div>

                  {/* Botones de Confirmar o Descartar */}
                  <div className="pt-2 flex items-center justify-end gap-2 border-t border-border/40">
                    <button
                      type="button"
                      data-testid={`voice-order-reject-btn-${ord.solicitud_id}`}
                      onClick={() => handleRejectOrder(ord.solicitud_id)}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-xl border border-destructive/30 bg-destructive/10 text-destructive text-xs font-bold hover:bg-destructive/20 transition-all cursor-pointer"
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      <span>{t("consumption.manos_libres.orders.reject", { defaultValue: "Descartar" })}</span>
                    </button>

                    <button
                      type="button"
                      data-testid={`voice-order-confirm-btn-${ord.solicitud_id}`}
                      onClick={() => handleConfirmOrder(ord.solicitud_id)}
                      className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-black uppercase tracking-wider transition-all shadow-md active:scale-95 cursor-pointer"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>{t("consumption.manos_libres.orders.confirm", { defaultValue: "Confirmar" })}</span>
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

export default ManosLibresPage;
