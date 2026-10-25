// oppytec-frontend/src/features/inventory/hooks/useContarInventario.ts
import { useState, useEffect, useCallback, useMemo } from "react";
import { toast } from "sonner";
import { apiRequest } from "@/shared/api/httpClient";
import type {
  ConteoStep,
  ConteoItemDraft,
} from "../types";

export const BLIND_COUNT_DRAFT_KEY = "oppytec_blind_count_draft";

export interface BlindCountDraftState {
  sessionId: number | null;
  bodegaId: number;
  areaOperativaId: number | null;
  step: ConteoStep;
  items: ConteoItemDraft[];
  notas: string;
  savedAt: string;
}

export interface UseContarInventarioOptions {
  initialBodegaId?: number;
  initialAreaOperativaId?: number;
}

export function useContarInventario(options?: UseContarInventarioOptions) {
  // Inicialización resiliente desde localStorage (0 pérdida de datos ante caídas)
  const initialDraft = useMemo<BlindCountDraftState | null>(() => {
    try {
      const saved = localStorage.getItem(BLIND_COUNT_DRAFT_KEY);
      if (saved) {
        return JSON.parse(saved) as BlindCountDraftState;
      }
      // Fallback a llaves históricas OppyTec-Legacy
      const legacyItems = localStorage.getItem("conteo_items");
      const legacyStep = localStorage.getItem("conteo_step") as ConteoStep | null;
      const legacyBodega = localStorage.getItem("conteo_bodega_id");
      if (legacyItems) {
        return {
          sessionId: null,
          bodegaId: legacyBodega ? Number(legacyBodega) : options?.initialBodegaId ?? 1,
          areaOperativaId: options?.initialAreaOperativaId ?? null,
          step: legacyStep || "idle",
          items: JSON.parse(legacyItems) as ConteoItemDraft[],
          notas: "",
          savedAt: new Date().toISOString(),
        };
      }
    } catch {
      // Ignorar errores de parseo en JSON corrupto
    }
    return null;
  }, [options?.initialBodegaId, options?.initialAreaOperativaId]);

  const [step, setStep] = useState<ConteoStep>(initialDraft?.step ?? "idle");
  const [sessionId, setSessionId] = useState<number | null>(
    initialDraft?.sessionId ?? null
  );
  const [bodegaId, setBodegaId] = useState<number>(
    initialDraft?.bodegaId ?? options?.initialBodegaId ?? 1
  );
  const [areaOperativaId, setAreaOperativaId] = useState<number | null>(
    initialDraft?.areaOperativaId ?? options?.initialAreaOperativaId ?? null
  );
  const [items, setItems] = useState<ConteoItemDraft[]>(
    initialDraft?.items ?? []
  );
  const [notas, setNotas] = useState<string>(initialDraft?.notas ?? "");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [hasDraftState, setHasDraftState] = useState<boolean>(
    () => (initialDraft?.items?.length ?? 0) > 0
  );

  // Auto-guardado continuo e incremental en localStorage en cada actualización
  useEffect(() => {
    if ((step === "idle" && items.length === 0) || step === "finished") {
      return;
    }

    const draft: BlindCountDraftState = {
      sessionId,
      bodegaId,
      areaOperativaId,
      step,
      items,
      notas,
      savedAt: new Date().toISOString(),
    };

    try {
      localStorage.setItem(BLIND_COUNT_DRAFT_KEY, JSON.stringify(draft));
      // Guardado por sesión individual y llaves legacy
      if (sessionId) {
        localStorage.setItem(
          `oppytec_blind_count_${sessionId}`,
          JSON.stringify(draft)
        );
      }
      localStorage.setItem("conteo_step", step);
      localStorage.setItem("conteo_items", JSON.stringify(items));
      localStorage.setItem("conteo_bodega_id", String(bodegaId));
    } catch {
      // Manejo seguro en caso de quota de localStorage
    }
  }, [sessionId, bodegaId, areaOperativaId, step, items, notas]);

  // Apertura de una nueva sesión de conteo ciego
  const startSession = useCallback(
    async (targetBodegaId: number, targetAreaId?: number | null, sessionNotas?: string) => {
      setBodegaId(targetBodegaId);
      setAreaOperativaId(targetAreaId ?? null);
      setNotas(sessionNotas ?? "");
      setItems([]);

      try {
        // Intento de apertura de sesión en backend REST
        const res = await apiRequest<{ id: number }>("/api/v1/inventory/counts/start", {
          method: "POST",
          body: {
            bodega_id: targetBodegaId,
            area_operativa_id: targetAreaId ?? null,
            notas: sessionNotas ?? "Toma física de inventario",
          },
          fallbackData: { id: Date.now() },
        });

        const activeId = res.data.id || Date.now();
        setSessionId(activeId);
        setStep("counting");
        toast.info("Sesión de recuento físico iniciada");
        return activeId;
      } catch {
        // Modo offline: crea id local resiliente
        const localId = Date.now();
        setSessionId(localId);
        setStep("counting");
        toast.info("Sesión local offline iniciada (sin conexión)");
        return localId;
      }
    },
    []
  );

  // Registro rápido o incremento de conteo de un ítem
  const recordCount = useCallback(
    (input: {
      producto_id: number;
      producto_nombre?: string;
      unidad_medida?: string;
      stock_fisico_contado: number;
      lote_codigo?: string | null;
      fecha_vencimiento?: string | null;
      costo_unitario_ppp?: number;
    }) => {
      setStep((currentStep) => (currentStep === "idle" ? "counting" : currentStep));
      setItems((prev) => {
        // Búsqueda de coincidencia por producto y lote/vencimiento
        const existingIdx = prev.findIndex(
          (i) =>
            i.producto_id === input.producto_id &&
            (i.lote_codigo ?? "") === (input.lote_codigo ?? "") &&
            (i.fecha_vencimiento ?? "") === (input.fecha_vencimiento ?? "")
        );

        if (existingIdx >= 0 && prev[existingIdx]) {
          const current = prev[existingIdx]!;
          const updated = [...prev];
          updated[existingIdx] = {
            ...current,
            stock_fisico_contado: input.stock_fisico_contado,
            costo_unitario_ppp: input.costo_unitario_ppp ?? current.costo_unitario_ppp,
          };
          return updated;
        }

        const newItem: ConteoItemDraft = {
          localId: `cnt-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
          producto_id: input.producto_id,
          producto_nombre: input.producto_nombre ?? `Producto #${input.producto_id}`,
          unidad_medida: input.unidad_medida ?? "unidades",
          stock_fisico_contado: input.stock_fisico_contado,
          lote_codigo: input.lote_codigo ?? null,
          fecha_vencimiento: input.fecha_vencimiento ?? null,
          costo_unitario_ppp: input.costo_unitario_ppp ?? 0,
        };

        return [newItem, ...prev];
      });
    },
    []
  );

  const updateItemQuantity = useCallback(
    (localId: string, quantity: number) => {
      setItems((prev) =>
        prev.map((item) =>
          item.localId === localId
            ? { ...item, stock_fisico_contado: Math.max(0, quantity) }
            : item
        )
      );
    },
    []
  );

  const removeItem = useCallback((localId: string) => {
    setItems((prev) => prev.filter((item) => item.localId !== localId));
  }, []);

  const clearOfflineDraft = useCallback(() => {
    try {
      localStorage.removeItem(BLIND_COUNT_DRAFT_KEY);
      localStorage.removeItem("conteo_step");
      localStorage.removeItem("conteo_items");
      localStorage.removeItem("conteo_bodega_id");
      if (sessionId) {
        localStorage.removeItem(`oppytec_blind_count_${sessionId}`);
      }
    } catch {
      // Ignorar errores
    }
    setItems([]);
    setStep("idle");
    setSessionId(null);
    setNotas("");
    setHasDraftState(false);
  }, [sessionId]);

  const resumeDraft = useCallback(() => {
    if (initialDraft) {
      setStep(initialDraft.step);
      setSessionId(initialDraft.sessionId);
      setBodegaId(initialDraft.bodegaId);
      setAreaOperativaId(initialDraft.areaOperativaId);
      setItems(initialDraft.items);
      setNotas(initialDraft.notas);
      toast.success("Borrador de conteo offline recuperado");
    }
  }, [initialDraft]);

  const finalizeSession = useCallback(async () => {
    if (items.length === 0) {
      toast.warning("No hay ítems registrados en el recuento");
      return false;
    }

    setIsSubmitting(true);
    setStep("submitting");

    try {
      const activeId = sessionId || Date.now();
      const payloadItems = items.map((i) => ({
        producto_id: i.producto_id,
        stock_fisico_contado: Number(i.stock_fisico_contado),
        costo_unitario_ppp: Number(i.costo_unitario_ppp ?? 0),
        lote_codigo: i.lote_codigo ?? null,
        fecha_vencimiento: i.fecha_vencimiento ?? null,
      }));

      // Guardar ítems y finalizar en backend
      await apiRequest(`/api/v1/inventory/counts/${activeId}/items`, {
        method: "PUT",
        body: { items: payloadItems },
        fallbackData: { id: activeId },
      });

      await apiRequest(`/api/v1/inventory/counts/${activeId}/finalize`, {
        method: "POST",
        fallbackData: { id: activeId, estado: "PENDIENTE_APROBACION" },
      });

      toast.success(
        "Recuento enviado exitosamente para aprobación de administración"
      );
      clearOfflineDraft();
      setStep("finished");
      window.dispatchEvent(new CustomEvent("inventory_stock_updated"));
      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error de red";
      toast.warning(
        `Recuento guardado en borrador offline (${message}). Se sincronizará al reconectar.`
      );
      setStep("reviewing");
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, [items, sessionId, clearOfflineDraft]);

  const hasOfflineDraft = hasDraftState;

  return {
    step,
    setStep,
    sessionId,
    bodegaId,
    setBodegaId,
    areaOperativaId,
    setAreaOperativaId,
    items,
    setItems,
    notas,
    setNotas,
    isSubmitting,
    hasOfflineDraft,
    startSession,
    recordCount,
    updateItemQuantity,
    removeItem,
    clearOfflineDraft,
    resumeDraft,
    finalizeSession,
  };
}
