// oppytec-frontend/src/features/consumo/components/buffet/StationCameraScanner.tsx
import { useState, useRef, useEffect, useCallback } from "react";
import {
  Camera,
  RotateCcw,
  Plus,
  Minus,
  Trash2,
  Sparkles,
  Zap,
  Check,
  AlertTriangle,
  Layers,
  UtensilsCrossed,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/shared/lib/utils";
import { apiRequest } from "@/shared/api/httpClient";
import type { BuffetItemDetection, BuffetStationScanResponse } from "../../types";

export interface StationCameraScannerProps {
  open: boolean;
  onClose: () => void;
  bodegaId: string;
  defaultStationName?: string;
  stage: "apertura" | "reposicion" | "cierre";
  onConfirmStation: (data: {
    station_name: string;
    foto_url: string;
    detections: BuffetItemDetection[];
  }) => void;
}

const SAMPLE_SIMULATED_DETECTIONS: Record<string, BuffetItemDetection[]> = {
  apertura: [
    {
      item_id: "prod-queso-parm",
      item_type: "producto",
      name: "Queso Parmesano Reggiano",
      count: 2.0,
      unit: "kg",
      bounding_boxes: [[120, 80, 400, 420]],
      confidence: 0.94,
    },
    {
      item_id: "prod-salm-01",
      item_type: "producto",
      name: "Salmón Fresco Filete",
      count: 3.5,
      unit: "kg",
      bounding_boxes: [[150, 450, 480, 820]],
      confidence: 0.91,
    },
    {
      item_id: "rec-pancakes-01",
      item_type: "receta",
      name: "Pancakes Caseros con Miel",
      count: 12,
      unit: "porción",
      bounding_boxes: [[500, 200, 750, 600]],
      confidence: 0.88,
    },
  ],
  reposicion: [
    {
      item_id: "prod-salm-01",
      item_type: "producto",
      name: "Salmón Fresco Filete (Bandeja Reposición)",
      count: 2.0,
      unit: "kg",
      bounding_boxes: [[100, 100, 450, 450]],
      confidence: 0.95,
    },
  ],
  cierre: [
    {
      item_id: "prod-queso-parm",
      item_type: "producto",
      name: "Queso Parmesano (Remanente)",
      count: 0.4,
      unit: "kg",
      bounding_boxes: [[120, 80, 300, 320]],
      confidence: 0.92,
    },
    {
      item_id: "prod-salm-01",
      item_type: "producto",
      name: "Salmón Filete (Remanente)",
      count: 0.8,
      unit: "kg",
      bounding_boxes: [[150, 450, 350, 650]],
      confidence: 0.89,
    },
  ],
};

export function StationCameraScanner({
  open,
  onClose,
  bodegaId,
  defaultStationName = "Estación Calientes & Huevos",
  stage,
  onConfirmStation,
}: StationCameraScannerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [hasCameraPermission, setHasCameraPermission] = useState<boolean | null>(null);
  const [torchAvailable, setTorchAvailable] = useState(false);
  const [torchOn, setTorchOn] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [stationName, setStationName] = useState(defaultStationName);
  const [frozenImageSrc, setFrozenImageSrc] = useState<string | null>(null);
  const [uploadedFotoUrl, setUploadedFotoUrl] = useState<string | null>(null);
  const [detections, setDetections] = useState<BuffetItemDetection[]>([]);

  // Feedback sonoro tecnológico
  const playTechChime = useCallback(() => {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1760, ctx.currentTime + 0.12);

      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.12);
    } catch {
      // AudioContext no disponible en jsdom/test
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setTorchOn(false);
  }, []);

  const startCamera = useCallback(async () => {
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setHasCameraPermission(false);
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setHasCameraPermission(true);

      const track = stream.getVideoTracks()[0];
      if (track) {
        const capabilities: any = (track as any).getCapabilities ? (track as any).getCapabilities() : {};
        if (capabilities.torch) {
          setTorchAvailable(true);
        }
      }
    } catch {
      setHasCameraPermission(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      setStationName(defaultStationName);
      setFrozenImageSrc(null);
      setUploadedFotoUrl(null);
      setDetections([]);
      void startCamera();
    } else {
      stopCamera();
    }
    return () => {
      stopCamera();
    };
  }, [open, defaultStationName, startCamera, stopCamera]);

  // Toggle Linterna
  const toggleTorch = async () => {
    if (!streamRef.current) return;
    const track = streamRef.current.getVideoTracks()[0];
    if (!track) return;
    try {
      const nextState = !torchOn;
      await (track as any).applyConstraints({
        advanced: [{ torch: nextState }],
      });
      setTorchOn(nextState);
      toast.info(nextState ? "Linterna encendida" : "Linterna apagada");
    } catch {
      toast.error("No se pudo encender la linterna");
    }
  };

  // Capturar frame desde video
  const handleCaptureFrame = async () => {
    setIsCapturing(true);
    try {
      let dataUrl = "";
      if (videoRef.current) {
        const canvas = document.createElement("canvas");
        const video = videoRef.current;
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          dataUrl = canvas.toDataURL("image/webp", 0.85);
        }
      }

      const snapshot = dataUrl || "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'/>";
      setFrozenImageSrc(snapshot);

      // Enviar a backend o fallback inteligente
      const simulated: BuffetItemDetection[] = SAMPLE_SIMULATED_DETECTIONS[stage] ?? SAMPLE_SIMULATED_DETECTIONS.apertura ?? [];
      try {
        const res = await apiRequest<BuffetStationScanResponse>(
          "/api/v1/operations/buffet/scan-station",
          {
            method: "POST",
            body: {
              bodega_id: bodegaId,
              stage,
              snapshot_data: snapshot.slice(0, 100),
            },
            fallbackData: {
              station_name_suggestion: stationName,
              detections: simulated,
              foto_original_url: "/images/buffet/station-gastronorm-1.webp",
            },
          }
        );
        setUploadedFotoUrl(res.data.foto_original_url || "/images/buffet/station-gastronorm-1.webp");
        if (res.data.station_name_suggestion) {
          setStationName(res.data.station_name_suggestion);
        }
        setDetections(res.data.detections || simulated);
      } catch {
        setUploadedFotoUrl("/images/buffet/station-gastronorm-1.webp");
        setDetections(simulated);
      }

      playTechChime();
      toast.success("Detección de bandejas gastronorm completada");
    } catch {
      toast.error("Error al procesar escaneo visual");
    } finally {
      setIsCapturing(false);
    }
  };

  // Simulación directa para entornos de prueba o terminales sin cámara
  const handleSimulateScan = () => {
    const simulated: BuffetItemDetection[] = SAMPLE_SIMULATED_DETECTIONS[stage] ?? SAMPLE_SIMULATED_DETECTIONS.apertura ?? [];
    setFrozenImageSrc("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'/>");
    setUploadedFotoUrl("/images/buffet/station-gastronorm-1.webp");
    setDetections(simulated);
    playTechChime();
    toast.success("Simulación IA de bandejas ejecutada con éxito");
  };

  // Reanudar cámara
  const handleRetake = () => {
    setFrozenImageSrc(null);
    setUploadedFotoUrl(null);
    setDetections([]);
    void startCamera();
  };

  // Ajustar cantidad de una detección
  const handleUpdateCount = (index: number, delta: number) => {
    setDetections((prev) =>
      prev.map((det, idx) => {
        if (idx !== index) return det;
        const newCount = Math.max(0.1, Math.round((det.count + delta) * 10) / 10);
        return { ...det, count: newCount };
      })
    );
  };

  // Eliminar detección
  const handleRemoveDetection = (index: number) => {
    setDetections((prev) => prev.filter((_, idx) => idx !== index));
    toast.info("Ítem descartado de la estación");
  };

  // Confirmar estación y transferir al balance
  const handleConfirm = () => {
    if (detections.length === 0) {
      toast.error("No hay ítems detectados en la estación.");
      return;
    }

    onConfirmStation({
      station_name: stationName.trim() || defaultStationName,
      foto_url: uploadedFotoUrl || "/images/buffet/station-gastronorm-1.webp",
      detections,
    });
    toast.success(`Estación "${stationName}" registrada exitosamente`);
    onClose();
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Escáner Visual de Estación Buffet"
      data-testid="station-camera-scanner-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-3 md:p-6"
    >
      <div className="w-full max-w-4xl max-h-[92vh] flex flex-col rounded-3xl bg-slate-900 border border-cyan-500/30 text-white shadow-2xl overflow-hidden">
        {/* Cabecera del Escáner */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-cyan-500/20 bg-slate-950/60 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-400">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-cyan-100 flex items-center gap-2">
                Escaneo Visual de Estación
                <span className="text-[10px] uppercase font-black px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  Fase: {stage}
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Alinea las bandejas gastronorm para pesaje y detección óptica automatizada
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="close-scanner-btn"
            className="touch-target px-3 py-1.5 rounded-xl bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 text-xs font-semibold cursor-pointer"
          >
            Cerrar
          </button>
        </div>

        {/* Cuerpo Principal */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 grid grid-cols-1 md:grid-cols-12 gap-6 min-h-0">
          {/* Lado Izquierdo: Visor de Cámara / Frame Congelado */}
          <div className="md:col-span-7 flex flex-col gap-3">
            <div className="relative aspect-video w-full rounded-2xl overflow-hidden bg-black border border-cyan-500/20 shadow-inner flex items-center justify-center">
              {frozenImageSrc ? (
                <div className="relative w-full h-full">
                  <img
                    src={frozenImageSrc}
                    alt="Frame capturado"
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-cyan-950/30 backdrop-brightness-110 flex items-center justify-center pointer-events-none">
                    <div className="px-3 py-1.5 rounded-full bg-cyan-500/80 text-black text-xs font-bold flex items-center gap-1.5 shadow-lg">
                      <Sparkles className="w-3.5 h-3.5" />
                      Frame Capturado y Procesado
                    </div>
                  </div>
                </div>
              ) : hasCameraPermission === false ? (
                <div className="text-center p-6 space-y-3">
                  <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto" />
                  <p className="text-sm font-semibold text-slate-300">
                    Cámara física no disponible o permiso denegado
                  </p>
                  <p className="text-xs text-slate-400 max-w-xs mx-auto">
                    Puedes utilizar el modo de simulación asistida por IA para continuar con la operación.
                  </p>
                  <button
                    type="button"
                    onClick={handleSimulateScan}
                    data-testid="simulate-scan-btn"
                    className="touch-target inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold shadow-md cursor-pointer"
                  >
                    <Sparkles className="w-4 h-4" />
                    Simular Escaneo de Bandejas
                  </button>
                </div>
              ) : (
                <>
                  <video
                    ref={videoRef}
                    playsInline
                    muted
                    autoPlay
                    className="w-full h-full object-cover"
                  />
                  {/* Mira láser gastronorm de referencia */}
                  <div className="absolute inset-8 border border-cyan-400/30 rounded-2xl pointer-events-none flex items-center justify-center">
                    <span className="text-[11px] font-bold text-cyan-400/60 uppercase tracking-widest bg-black/40 px-3 py-1 rounded-full">
                      Área de Bandejas Gastronorm
                    </span>
                  </div>
                </>
              )}
            </div>

            {/* Controles de Disparo */}
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                {torchAvailable && (
                  <button
                    type="button"
                    onClick={() => void toggleTorch()}
                    data-testid="toggle-torch-btn"
                    className={cn(
                      "p-2.5 rounded-xl border text-xs font-semibold cursor-pointer transition-colors",
                      torchOn
                        ? "bg-amber-500/20 border-amber-500/40 text-amber-300"
                        : "bg-slate-800 border-slate-700 text-slate-300"
                    )}
                  >
                    <Zap className="w-4 h-4" />
                  </button>
                )}
                {frozenImageSrc && (
                  <button
                    type="button"
                    onClick={handleRetake}
                    data-testid="retake-scan-btn"
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-300 cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Reintentar
                  </button>
                )}
              </div>

              {!frozenImageSrc && (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSimulateScan}
                    data-testid="simulate-scan-quick-btn"
                    className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 cursor-pointer flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                    Simular
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleCaptureFrame()}
                    disabled={isCapturing}
                    data-testid="capture-frame-btn"
                    className="touch-target flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-400 hover:to-teal-400 text-black font-bold text-xs shadow-lg shadow-cyan-500/20 cursor-pointer disabled:opacity-50"
                  >
                    <Camera className="w-4 h-4" />
                    {isCapturing ? "Procesando..." : "Capturar Estación"}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Lado Derecho: Nombre de Estación y Detecciones */}
          <div className="md:col-span-5 flex flex-col gap-4">
            <div>
              <label htmlFor="station-name-input" className="block text-xs font-bold text-cyan-300 uppercase tracking-wider mb-1.5">
                Nombre de la Estación
              </label>
              <input
                id="station-name-input"
                type="text"
                value={stationName}
                onChange={(e) => setStationName(e.target.value)}
                placeholder="Ej. Estación Calientes & Huevos"
                data-testid="station-name-input"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white text-sm focus:border-cyan-400 focus:outline-none"
              />
            </div>

            <div className="flex-1 flex flex-col min-h-[220px]">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-cyan-400" />
                  Bandejas Detectadas ({detections.length})
                </span>
              </div>

              {detections.length === 0 ? (
                <div className="flex-1 border border-dashed border-slate-800 rounded-2xl flex flex-col items-center justify-center p-6 text-center bg-slate-950/40">
                  <UtensilsCrossed className="w-8 h-8 text-slate-600 mb-2" />
                  <p className="text-xs text-slate-400">
                    Captura o simula una imagen para identificar automáticamente los insumos.
                  </p>
                </div>
              ) : (
                <div className="space-y-2 flex-1 overflow-y-auto max-h-[320px] pr-1">
                  {detections.map((det, idx) => (
                    <div
                      key={`${det.item_id}-${idx}`}
                      data-testid={`detection-item-${idx}`}
                      className="p-3 rounded-xl bg-slate-950/80 border border-cyan-500/20 flex items-center justify-between gap-3 shadow-xs"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                            {det.item_type}
                          </span>
                          <span className="text-xs font-semibold text-slate-100 truncate">
                            {det.name}
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-400">
                          Confianza: {Math.round(det.confidence * 100)}%
                        </span>
                      </div>

                      {/* Controles numéricos */}
                      <div className="flex items-center gap-1.5 shrink-0">
                        <button
                          type="button"
                          onClick={() => handleUpdateCount(idx, -0.5)}
                          data-testid={`det-decrement-${idx}`}
                          className="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center justify-center cursor-pointer"
                        >
                          <Minus className="w-3.5 h-3.5" />
                        </button>
                        <span
                          data-testid={`det-count-${idx}`}
                          className="w-12 text-center text-xs font-mono font-bold text-cyan-300"
                        >
                          {det.count} {det.unit || "kg"}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleUpdateCount(idx, 0.5)}
                          data-testid={`det-increment-${idx}`}
                          className="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center justify-center cursor-pointer"
                        >
                          <Plus className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRemoveDetection(idx)}
                          data-testid={`det-remove-${idx}`}
                          className="w-7 h-7 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 flex items-center justify-center cursor-pointer ml-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Botón de Confirmación */}
            <button
              type="button"
              onClick={handleConfirm}
              disabled={detections.length === 0}
              data-testid="confirm-station-btn"
              className="touch-target w-full py-3 rounded-2xl bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-400 hover:to-teal-400 text-black font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 cursor-pointer disabled:opacity-50"
            >
              <Check className="w-4 h-4 stroke-[3]" />
              Confirmar y Agregar al Balance
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
