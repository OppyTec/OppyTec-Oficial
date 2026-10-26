// oppytec-frontend/src/features/consumo/hooks/__tests__/useManosLibres.test.ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as httpClient from "@/shared/api/httpClient";
import {
  useManosLibres,
  cleanProgressiveDuplicates,
  assembleCleanTranscript,
  normalizeKitchenVoiceTranscript,
} from "../useManosLibres";
import { MOCK_VOICE_STATIONS } from "../../mockData";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe("Módulo de Manos Libres - useManosLibres Hook & Audio Phonetics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await new Promise((r) => setTimeout(r, 20));
  });

  // ==========================================================================
  // 1. Limpieza Fonética y Desduplicación de Audio
  // ==========================================================================
  describe("Limpieza Fonética y Desduplicación de Audio", () => {
    it("cleanProgressiveDuplicates removes repetitive accumulated prefixes", () => {
      const raw = "merma merma 7 merma 7 kg de carne";
      const cleaned = cleanProgressiveDuplicates(raw);
      expect(cleaned).toBe("merma 7 kg de carne");
    });

    it("assembleCleanTranscript handles progressive results from Web Speech API", () => {
      const mockResults = [
        [{ transcript: "merma" }],
        [{ transcript: "merma 2" }],
        [{ transcript: "merma 2 kilos de queso" }],
      ];
      const assembled = assembleCleanTranscript(mockResults);
      expect(assembled).toBe("merma 2 kilos de queso");
    });

    it("normalizeKitchenVoiceTranscript corrects phonetic errors like 'oprime más' -> 'Oppy merma'", () => {
      expect(normalizeKitchenVoiceTranscript("oprime más 5 kilos de harina")).toBe(
        "Oppy merma 5 kg de harina"
      );
      expect(normalizeKitchenVoiceTranscript("oye oppy consumo 2 litros de leche")).toBe(
        "Oppy consumo 2 L de leche"
      );
      expect(normalizeKitchenVoiceTranscript("apio merma 3 kilos de tomate")).toBe(
        "Oppy merma 3 kg de tomate"
      );
    });
  });

  // ==========================================================================
  // 2. Estaciones de Voz y Selección
  // ==========================================================================
  describe("Estaciones de Voz y Estado de Escucha", () => {
    it("loads voice stations and selects active station", () => {
      const { result } = renderHook(() => useManosLibres(), {
        wrapper: createWrapper(),
      });

      expect(result.current.stations.length).toBeGreaterThan(0);
      expect(result.current.activeStation?.id).toBe(MOCK_VOICE_STATIONS[0]?.id);

      act(() => {
        result.current.setSelectedStationId(2);
      });

      expect(result.current.activeStation?.id).toBe(2);
    });

    it("toggles listening state safely", () => {
      const { result } = renderHook(() => useManosLibres(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isListening).toBe(false);

      act(() => {
        result.current.stopListening();
      });

      expect(result.current.isListening).toBe(false);
    });
  });

  // ==========================================================================
  // 3. Mutaciones de Órdenes Verbales
  // ==========================================================================
  describe("Mutaciones de Órdenes Verbales", () => {
    it("calls registerVoiceOrder and updates pending orders", async () => {
      const apiSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockImplementation(async (path, options) => {
          if (
            path.includes("/operations/voice/orders") &&
            options?.method === "POST"
          ) {
            return {
              data: {
                id: 101,
                station_id: 1,
                texto_transcrito: "Oppy consumo 2 kg de salmon",
                accion_detectada: "CONSUMO",
                confianza_ia: 0.98,
                items_interpretados_json: [
                  { nombre: "Salmón", cantidad: 2, unidad: "kg" },
                ],
                estado: "PENDIENTE",
              } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          return {
            data: options?.fallbackData,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          } as any;
        });

      const { result } = renderHook(() => useManosLibres(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.registerVoiceOrder({
          station_id: 1,
          texto_transcrito: "Oppy consumo 2 kg de salmon",
          accion_detectada: "CONSUMO",
          items_interpretados: [{ nombre: "Salmón", cantidad: 2, unidad: "kg" }],
        });
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/voice/orders",
        expect.objectContaining({ method: "POST" })
      );
      expect(result.current.pendingOrders[0]?.solicitud_id).toBe("101");
    });

    it("calls confirmVoiceOrder and rejectVoiceOrder", async () => {
      const apiSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockImplementation(async (path, options) => {
          if (path.includes("/confirm") && options?.method === "POST") {
            return {
              data: { id: 101, estado: "CONFIRMADO" } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          if (path.includes("/reject") && options?.method === "POST") {
            return {
              data: { id: 102, estado: "RECHAZADO" } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          return {
            data: options?.fallbackData,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          } as any;
        });

      const { result } = renderHook(() => useManosLibres(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.confirmVoiceOrder({
          id: 101,
          bodegaId: 1,
        });
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/voice/orders/101/confirm",
        expect.objectContaining({ method: "POST" })
      );

      await act(async () => {
        await result.current.rejectVoiceOrder(102);
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/voice/orders/102/reject",
        expect.objectContaining({ method: "POST" })
      );
    });

    it("triggers speech synthesis feedback safely", () => {
      const mockSpeak = vi.fn();
      const mockCancel = vi.fn();

      // Mock window.speechSynthesis
      (window as any).speechSynthesis = {
        speak: mockSpeak,
        cancel: mockCancel,
      };
      (window as any).SpeechSynthesisUtterance = vi.fn().mockImplementation((text) => ({
        text,
        lang: "es-CL",
      }));

      const { result } = renderHook(() => useManosLibres(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.speakFeedback("Orden confirmada");
      });

      expect(mockCancel).toHaveBeenCalled();
      expect(mockSpeak).toHaveBeenCalled();
    });
  });
});
