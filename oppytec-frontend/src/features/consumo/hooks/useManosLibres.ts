// oppytec-frontend/src/features/consumo/hooks/useManosLibres.ts
import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { useRealtimeSync } from "@/shared/realtime/useRealtimeSync";
import type { WorkerStation, VoiceOrderLog } from "../types";
import { MOCK_VOICE_STATIONS, MOCK_VOICE_ORDERS } from "../mockData";

// ============================================================================
// UTILIDADES FONÉTICAS Y DE LIMPIEZA DE AUDIO ASR
// ============================================================================

/**
 * Elimina duplicaciones progresivas causadas por motores de voz móviles (Android Chrome ASR)
 * que concatenan hipótesis acumulativas.
 */
export function cleanProgressiveDuplicates(raw: string): string {
  if (!raw) return "";
  let text = raw.trim();

  let prefix = "";
  const oppyMatch = text.match(/^(oppy\s+)+(.*)/i);
  if (oppyMatch && oppyMatch[2]) {
    prefix = "Oppy ";
    text = oppyMatch[2].trim();
  }

  const words = text.split(/\s+/).filter(Boolean);
  if (words.length <= 2) {
    return (prefix + text).trim();
  }

  const firstWord = words[0]?.toLowerCase() ?? "";
  const restartIndices: number[] = [];
  for (let i = 0; i < words.length; i++) {
    const word = words[i];
    if (word && word.toLowerCase() === firstWord) {
      restartIndices.push(i);
    }
  }

  if (restartIndices.length > 1) {
    const lastStart = restartIndices[restartIndices.length - 1] ?? 0;
    const candidate = words.slice(lastStart).join(" ");
    let allPrefixes = true;

    for (let r = 0; r < restartIndices.length - 1; r++) {
      const start = restartIndices[r] ?? 0;
      const end = restartIndices[r + 1] ?? 0;
      const seg = words.slice(start, end).join(" ").toLowerCase();
      if (!candidate.toLowerCase().startsWith(seg)) {
        allPrefixes = false;
        break;
      }
    }

    if (allPrefixes) {
      return (prefix + candidate).trim();
    }
  }

  return (prefix + text).trim();
}

/**
 * Ensambla limpiamente la lista de resultados de Web Speech API (SpeechRecognitionResultList).
 */
export function assembleCleanTranscript(results: any): string {
  if (!results) return "";
  const chunks: string[] = [];

  for (let i = 0; i < results.length; i++) {
    const raw = (results[i]?.[0]?.transcript || "").trim();
    if (!raw) continue;

    if (chunks.length === 0) {
      chunks.push(raw);
      continue;
    }

    const lastIdx = chunks.length - 1;
    const prev = chunks[lastIdx];
    if (!prev) {
      chunks.push(raw);
      continue;
    }
    const prevLower = prev.toLowerCase();
    const currLower = raw.toLowerCase();

    if (currLower.startsWith(prevLower)) {
      chunks[lastIdx] = raw;
      continue;
    }

    if (prevLower.endsWith(currLower) || prevLower.includes(currLower)) {
      continue;
    }

    const prevWords = prev.split(/\s+/).filter(Boolean);
    const currWords = raw.split(/\s+/).filter(Boolean);
    let merged = false;

    for (
      let overlap = Math.min(prevWords.length, currWords.length);
      overlap > 0;
      overlap--
    ) {
      const prevSuffix = prevWords.slice(-overlap).join(" ").toLowerCase();
      const currPrefix = currWords.slice(0, overlap).join(" ").toLowerCase();
      if (prevSuffix === currPrefix) {
        const combined = prevWords.concat(currWords.slice(overlap)).join(" ");
        chunks[lastIdx] = combined;
        merged = true;
        break;
      }
    }

    if (!merged) {
      chunks.push(raw);
    }
  }

  return chunks.join(" ").trim();
}

/**
 * Normaliza términos fonéticos comunes de cocina y llamados a Oppy.
 */
export function normalizeKitchenVoiceTranscript(raw: string): string {
  if (!raw) return "";
  let text = cleanProgressiveDuplicates(raw);

  // 1. Fonética para "Oppy merma" / "Oppy consumo"
  text = text.replace(/\b(oprimer|oprime)\s+m[aá]s\b/gi, "Oppy merma");
  text = text.replace(/\b(oprimer|oprime)\s+merma\b/gi, "Oppy merma");
  text = text.replace(/\bpapi\s+(merma|mermar)\b/gi, "Oppy merma");
  text = text.replace(/\b(oprimer|oprime)\b(?=\s+\d)/gi, "Oppy merma");

  // 2. Prefijos de llamado comunes seguidos de Oppy
  text = text.replace(
    /\b(oye|hey|ok|okey|hola|atento|escucha)\s+(oppy|oppi|opi|opy|obby|obbi|obi|o\s*pi|oki)\b/gi,
    "Oppy"
  );

  // 3. Fonética extendida para el nombre de Oppy
  text = text.replace(
    /\b(oppi|opi|opy|obby|obbi|obi|o\s+pi|o\s+py|o\s+ti|papi|hoppy|hopi|hobby|hockey|copy|copi|uppy|upi|okey|oki)\b/gi,
    "Oppy"
  );

  // Apio/apoyo como primera palabra
  text = text.replace(/^apio\b/gi, "Oppy");
  text = text.replace(/\bapio\s+(merma|consumo|ingreso|gasto)\b/gi, "Oppy $1");
  text = text.replace(/\bapoyo\s+(merma|consumo|ingreso|gasto)\b/gi, "Oppy $1");

  // 4. Normalizar unidades de cocina
  text = text.replace(/\bkilogramos?\b/gi, "kg");
  text = text.replace(/\bkilos?\b/gi, "kg");
  text = text.replace(/\bgramos?\b/gi, "g");
  text = text.replace(/\blitros?\b/gi, "L");
  text = text.replace(/\bmililitros?\b/gi, "ml");

  return text.trim();
}

// ============================================================================
// CONTRATOS Y HOOK
// ============================================================================

export interface UseManosLibresOptions {
  areaOperativaId?: number | null;
  autoRestart?: boolean;
  onVoiceOrderDetected?: (order: VoiceOrderLog) => void;
}

export interface RegisterVoiceOrderPayload {
  station_id: number;
  texto_transcrito: string;
  accion_detectada: "CONSUMO" | "MERMA" | "consumo" | "merma";
  confianza_ia?: number;
  items_interpretados: Array<{
    item_id?: string | null;
    nombre: string;
    cantidad: number;
    unidad: string;
    motivo_merma?: string | null;
  }>;
}

export function useManosLibres(options?: UseManosLibresOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = context.tenantId || "tenant_rest_central";

  const [isListening, setIsListening] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>("");
  const [interimTranscript, setInterimTranscript] = useState<string>("");
  const [selectedStationId, setSelectedStationId] = useState<number | null>(null);
  const [pendingOrders, setPendingOrders] = useState<VoiceOrderLog[]>(MOCK_VOICE_ORDERS);

  const recognitionRef = useRef<any>(null);

  // Suscripción WebSocket para alertas de voz
  let realtimeEvents: ReturnType<typeof useRealtimeSync>["authorizedEvents"] = [];
  try {
    const rt = useRealtimeSync();
    realtimeEvents = rt.authorizedEvents;
  } catch {
    // Offline / unit test
  }

  useEffect(() => {
    if (!realtimeEvents || realtimeEvents.length === 0) return;
    const latest = realtimeEvents[0];
    if (latest && latest.eventType === "voice.order_pending") {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.operations.voice.stations(tenantId),
      });
      toast.info("Nueva orden verbal registrada en cocina");
    }
  }, [realtimeEvents, queryClient, tenantId]);

  // Cargar estaciones de voz
  const { data: stations = MOCK_VOICE_STATIONS, isLoading: isLoadingStations } =
    useQuery<WorkerStation[]>({
      queryKey: queryKeys.operations.voice.stations(
        tenantId,
        options?.areaOperativaId
      ),
      queryFn: async () => {
        const url = options?.areaOperativaId
          ? `/api/v1/operations/voice/stations?area_operativa_id=${options.areaOperativaId}`
          : "/api/v1/operations/voice/stations";
        const res = await apiRequest<WorkerStation[]>(url, {
          fallbackData: MOCK_VOICE_STATIONS,
        });
        return res.data;
      },
    });

  // Mutación: Registrar orden de voz
  const registerOrderMutation = useMutation({
    mutationFn: async (payload: RegisterVoiceOrderPayload) => {
      const res = await apiRequest<any>("/api/v1/operations/voice/orders", {
        method: "POST",
        body: payload,
      });
      return res.data;
    },
    onSuccess: (data) => {
      const newLog: VoiceOrderLog = {
        solicitud_id: String(data.id || Date.now()),
        timestamp: new Date(),
        worker: {
          id: data.station_id || 1,
          name: "Operario de Cocina",
        },
        action_type:
          String(data.accion_detectada).toLowerCase() === "merma"
            ? "merma"
            : "consumo",
        item: {
          name: data.items_interpretados_json?.[0]?.nombre || "Insumo",
          quantity: data.items_interpretados_json?.[0]?.cantidad || 1,
          unit: data.items_interpretados_json?.[0]?.unidad || "unidad",
        },
        spoken_feedback: `Registrado ${data.texto_transcrito}`,
        transcript: data.texto_transcrito,
        confidence: data.confianza_ia ?? 0.95,
        status: data.estado || "PENDIENTE",
      };

      setPendingOrders((prev) => [newLog, ...prev]);
      speakFeedback(
        `Oppy registró ${newLog.item.quantity} ${newLog.item.unit} de ${newLog.item.name}`
      );
      toast.success("Comando de voz procesado");
      options?.onVoiceOrderDetected?.(newLog);
    },
    onError: (err: any) => {
      toast.error(err.message || "Error al procesar orden de voz");
    },
  });

  // Mutación: Confirmar orden de voz
  const confirmOrderMutation = useMutation({
    mutationFn: async ({
      id,
      bodegaId,
    }: {
      id: number | string;
      bodegaId: number | string;
    }) => {
      const res = await apiRequest(
        `/api/v1/operations/voice/orders/${id}/confirm`,
        {
          method: "POST",
          body: { bodega_id: Number(bodegaId) },
        }
      );
      return res.data;
    },
    onSuccess: (_, vars) => {
      toast.success("Orden verbal confirmada y descontada en Kardex");
      setPendingOrders((prev) =>
        prev.map((o) =>
          o.solicitud_id === String(vars.id) ? { ...o, status: "CONFIRMADO" } : o
        )
      );
      void queryClient.invalidateQueries({
        queryKey: ["oppytec", "operations", "consumption"],
      });
    },
  });

  // Mutación: Rechazar orden de voz
  const rejectOrderMutation = useMutation({
    mutationFn: async (id: number | string) => {
      const res = await apiRequest(
        `/api/v1/operations/voice/orders/${id}/reject`,
        {
          method: "POST",
        }
      );
      return res.data;
    },
    onSuccess: (_, id) => {
      toast.info("Orden verbal descartada");
      setPendingOrders((prev) =>
        prev.map((o) =>
          o.solicitud_id === String(id) ? { ...o, status: "RECHAZADO" } : o
        )
      );
    },
  });

  // ==========================================================================
  // SÍNTESIS DE VOZ AUDITIVA (TTS)
  // ==========================================================================
  const speakFeedback = useCallback((text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "es-CL";
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    } catch {
      // Ignorar fallo de audio en navegadores restrictivos
    }
  }, []);

  // ==========================================================================
  // MOTOR WEB SPEECH API (ASR)
  // ==========================================================================
  const startListening = useCallback(() => {
    if (typeof window === "undefined") return;

    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      toast.error("El navegador no soporta reconocimiento por voz");
      return;
    }

    try {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }

      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "es-CL";

      rec.onstart = () => {
        setIsListening(true);
      };

      rec.onresult = (event: any) => {
        let interim = "";
        let final = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const res = event.results[i];
          if (res.isFinal) {
            final += res[0].transcript;
          } else {
            interim += res[0].transcript;
          }
        }

        const cleanInterim = normalizeKitchenVoiceTranscript(interim);
        setInterimTranscript(cleanInterim);

        if (final) {
          const cleanFinal = normalizeKitchenVoiceTranscript(final);
          setTranscript(cleanFinal);
          setInterimTranscript("");

          // Interpretar y registrar automáticamente si incluye comando operativo
          if (cleanFinal.toLowerCase().includes("oppy")) {
            const isMerma = cleanFinal.toLowerCase().includes("merma");
            registerOrderMutation.mutate({
              station_id: selectedStationId || stations[0]?.id || 1,
              texto_transcrito: cleanFinal,
              accion_detectada: isMerma ? "MERMA" : "CONSUMO",
              items_interpretados: [
                {
                  nombre:
                    cleanFinal
                      .replace(/oppy\s+(consumo|merma)\s*/gi, "")
                      .trim() || "Insumo Detectado",
                  cantidad: 1,
                  unidad: "unidad",
                },
              ],
            });
          }
        }
      };

      rec.onerror = (e: any) => {
        if (e.error !== "no-speech") {
          console.warn("SpeechRecognition error:", e.error);
        }
      };

      rec.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = rec;
      rec.start();
    } catch (err) {
      console.error("Error al iniciar SpeechRecognition:", err);
      setIsListening(false);
    }
  }, [selectedStationId, stations, registerOrderMutation]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    setIsListening(false);
    setInterimTranscript("");
  }, []);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {}
      }
    };
  }, []);

  const activeStation = useMemo(
    () =>
      Array.isArray(stations)
        ? stations.find((s) => s.id === selectedStationId) || stations[0] || null
        : null,
    [stations, selectedStationId]
  );

  return {
    stations,
    isLoadingStations,
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
    registerVoiceOrder: registerOrderMutation.mutateAsync,
    confirmVoiceOrder: confirmOrderMutation.mutateAsync,
    rejectVoiceOrder: rejectOrderMutation.mutateAsync,
  };
}
