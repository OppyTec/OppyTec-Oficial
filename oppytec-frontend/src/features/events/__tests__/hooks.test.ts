// oppytec-frontend/src/features/events/__tests__/hooks.test.ts
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { eventsApi } from "../api/eventsApi";
import {
  useEvents,
  useSalones,
  useEventAlerts,
  getEventEstimatedCost,
  getInsumosDesglosados,
} from "../hooks";
import {
  MOCK_EVENTOS,
  MOCK_SALONES,
  MOCK_FALTANTES_RESPONSE,
} from "../mockData";
import type { Evento, SalonCreatePayload } from "../types";

// Mock de sonner para verificar notificaciones toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

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
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

describe("Feature Events - Core Reactive Hooks & Analytics (Fase 3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // =========================================================================
  // 1. Helpers Analíticos de Eventos
  // =========================================================================
  describe("Helpers Analíticos: getEventEstimatedCost y getInsumosDesglosados", () => {
    it("calcula correctamente el costo estimado sumando items, recetas y combos", () => {
      const evento = MOCK_EVENTOS[0]!; // Boda Romina & Ignacio
      // items: (48 * 4500) + (15 * 1800) = 216000 + 27000 = 243000
      // recetas: 100 * 6500 = 650000
      // combos: 100 * 2800 = 280000
      // Total esperado: 243000 + 650000 + 280000 = 1173000
      const totalCost = getEventEstimatedCost(evento);
      expect(totalCost).toBe(1173000);
    });

    it("retorna 0 si el evento no tiene suministros o es nulo", () => {
      expect(getEventEstimatedCost(null as unknown as Evento)).toBe(0);
      expect(getEventEstimatedCost(MOCK_EVENTOS[3]!)).toBe(0); // evento cancelado sin items
    });

    it("desglosa las cantidades de suministros directos, recetas y combos", () => {
      const evento = MOCK_EVENTOS[0]!;
      const desglose = getInsumosDesglosados(evento);
      expect(desglose.directosCount).toBe(2);
      expect(desglose.recetasCount).toBe(1);
      expect(desglose.combosCount).toBe(1);
      expect(desglose.totalInsumos).toBe(4);
    });
  });

  // =========================================================================
  // 2. Hook useEvents
  // =========================================================================
  describe("useEvents", () => {
    it("carga eventos y clasifica correctamente por pestañas y contadores reactivos", async () => {
      const { result } = renderHook(() => useEvents(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.allEvents.length).toBeGreaterThan(0);
      expect(result.current.counts.total).toBe(result.current.allEvents.length);
      expect(result.current.counts.proximos).toBeGreaterThanOrEqual(1);
      expect(result.current.counts.historial).toBeGreaterThanOrEqual(1);
      expect(result.current.counts.cancelados).toBeGreaterThanOrEqual(1);

      // Pestaña inicial 'proximos'
      expect(result.current.activeTab).toBe("proximos");
      result.current.events.forEach((evt) => {
        expect(evt.ejecutado).toBe(false);
        expect(evt.cancelado).toBe(false);
      });

      // Cambio a pestaña 'historial'
      act(() => {
        result.current.setActiveTab("historial");
      });
      expect(result.current.activeTab).toBe("historial");
      result.current.events.forEach((evt) => {
        expect(evt.ejecutado || evt.estado === "finalizado" || evt.estado === "EJECUTADO").toBe(true);
      });

      // Cambio a pestaña 'cancelados'
      act(() => {
        result.current.setActiveTab("cancelados");
      });
      expect(result.current.activeTab).toBe("cancelados");
      result.current.events.forEach((evt) => {
        expect(evt.cancelado || evt.estado === "cancelado" || evt.estado === "CANCELADO").toBe(true);
      });
    });

    it("ejecuta createEvent con toast de éxito", async () => {
      const spy = vi.spyOn(eventsApi, "createEvent");
      const { result } = renderHook(() => useEvents(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.createEvent({
          nombre: "Cena Gala Fin de Año",
          fecha: "2026-12-31",
          cantidad_personas: 80,
          color: "#ec4899",
        });
      });

      expect(spy).toHaveBeenCalledTimes(1);
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("Cena Gala Fin de Año")
      );
    });

    it("ejecuta updateEvent con toast de éxito", async () => {
      const spy = vi.spyOn(eventsApi, "updateEvent");
      const { result } = renderHook(() => useEvents(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.updateEvent({
          id: MOCK_EVENTOS[0]!.id,
          data: { titular: "Romina y Esposo Actualizado" },
        });
      });

      expect(spy).toHaveBeenCalledTimes(1);
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("actualizado")
      );
    });

    it("ejecuta executeEvent consumiendo inventario en Kardex", async () => {
      const spy = vi.spyOn(eventsApi, "executeEvent");
      const { result } = renderHook(() => useEvents(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.executeEvent(MOCK_EVENTOS[0]!.id);
      });

      expect(spy).toHaveBeenCalledTimes(1);
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("ejecutado con éxito")
      );
    });

    it("ejecuta cancelEvent y reactivateEvent correctamente", async () => {
      const cancelSpy = vi.spyOn(eventsApi, "cancelEvent");
      const reactivateSpy = vi.spyOn(eventsApi, "reactivateEvent");

      const { result } = renderHook(() => useEvents(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      // Cancelar
      await act(async () => {
        await result.current.cancelEvent({
          id: MOCK_EVENTOS[0]!.id,
          motivo: "Fuerza mayor climática",
        });
      });
      expect(cancelSpy).toHaveBeenCalledWith(MOCK_EVENTOS[0]!.id, "Fuerza mayor climática");
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("cancelado"));

      // Reactivar
      await act(async () => {
        await result.current.reactivateEvent(MOCK_EVENTOS[0]!.id);
      });
      expect(reactivateSpy).toHaveBeenCalledWith(MOCK_EVENTOS[0]!.id);
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("reactivado"));
    });

    it("ejecuta deleteEvent con toast de éxito", async () => {
      const deleteSpy = vi.spyOn(eventsApi, "deleteEvent");
      const { result } = renderHook(() => useEvents(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.deleteEvent(MOCK_EVENTOS[0]!.id);
      });

      expect(deleteSpy).toHaveBeenCalledWith(MOCK_EVENTOS[0]!.id);
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("eliminado del calendario")
      );
    });

    it("maneja errores de mutación mostrando toast.error", async () => {
      vi.spyOn(eventsApi, "createEvent").mockRejectedValueOnce(
        new Error("Error de validación anti-overbooking: Salón ya reservado")
      );

      const { result } = renderHook(() => useEvents(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        try {
          await result.current.createEvent({
            nombre: "Evento Colisionante",
            fecha: "2026-11-15",
          });
        } catch {
          // Captura esperada
        }
      });

      expect(toast.error).toHaveBeenCalledWith(
        "Error de validación anti-overbooking: Salón ya reservado"
      );
    });
  });

  // =========================================================================
  // 3. Hook useSalones
  // =========================================================================
  describe("useSalones", () => {
    it("carga salones y permite buscar por id", async () => {
      const { result } = renderHook(() => useSalones(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.salones.length).toBe(MOCK_SALONES.length);
      const found = result.current.getSalonById(MOCK_SALONES[0]!.id);
      expect(found?.nombre).toBe(MOCK_SALONES[0]!.nombre);

      const notFound = result.current.getSalonById("sal-no-existe");
      expect(notFound).toBeUndefined();
    });

    it("crea, actualiza y elimina salones con toasts de éxito", async () => {
      const createSpy = vi.spyOn(eventsApi, "createSalon");
      const updateSpy = vi.spyOn(eventsApi, "updateSalon");
      const deleteSpy = vi.spyOn(eventsApi, "deleteSalon");

      const { result } = renderHook(() => useSalones(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      // Crear
      const newPayload: SalonCreatePayload = {
        nombre: "Nuevo Pabellón de Eventos",
        capacidad_personas: 200,
        precio_neto: 250000,
      };
      await act(async () => {
        await result.current.createSalon(newPayload);
      });
      expect(createSpy).toHaveBeenCalledWith(newPayload);
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("creado exitosamente"));

      // Actualizar
      await act(async () => {
        await result.current.updateSalon({
          id: MOCK_SALONES[0]!.id,
          data: { precio_neto: 180000 },
        });
      });
      expect(updateSpy).toHaveBeenCalledTimes(1);
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("actualizado"));

      // Eliminar
      await act(async () => {
        await result.current.deleteSalon(MOCK_SALONES[0]!.id);
      });
      expect(deleteSpy).toHaveBeenCalledWith(MOCK_SALONES[0]!.id);
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("Salón eliminado"));
    });
  });

  // =========================================================================
  // 4. Hook useEventAlerts (FASE 7)
  // =========================================================================
  describe("useEventAlerts", () => {
    it("carga analítica de faltantes e identifica stock comprometido y alertas críticas", async () => {
      const { result } = renderHook(() => useEventAlerts(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.hasShortages).toBe(true);
      expect(result.current.isCritical).toBe(true);
      expect(result.current.totalFaltantes).toBe(MOCK_FALTANTES_RESPONSE.total_faltantes);
      expect(result.current.eventosAfectadosCount).toBe(
        MOCK_FALTANTES_RESPONSE.eventos_afectados_count
      );
      expect(result.current.items.length).toBeGreaterThan(0);
    });

    it("maneja respuesta sin faltantes marcando hasShortages como falso", async () => {
      vi.spyOn(eventsApi, "getFaltantesAnalytics").mockResolvedValueOnce({
        total_faltantes: 0,
        items: [],
        eventos_afectados_count: 0,
        generado_at: new Date().toISOString(),
      });
      vi.spyOn(eventsApi, "getEventAlerts").mockResolvedValueOnce([]);

      const { result } = renderHook(() => useEventAlerts(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.hasShortages).toBe(false);
      expect(result.current.hasCriticalAlerts).toBe(false);
      expect(result.current.hasWarningAlerts).toBe(false);
      expect(result.current.criticalAlertsCount).toBe(0);
      expect(result.current.warningAlertsCount).toBe(0);
      expect(result.current.totalFaltantes).toBe(0);
    });

    it("carga resumen de stock comprometido y expone helpers analíticos", async () => {
      const { result } = renderHook(() => useEventAlerts(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Validar lista de stock comprometido
      expect(result.current.committedStock.length).toBeGreaterThan(0);
      expect(result.current.totalCommittedItems).toBe(result.current.committedStock.length);

      // Helper: getCommittedStockByProduct
      const item1 = result.current.getCommittedStockByProduct(1, 1);
      expect(item1).toBeDefined();
      expect(item1?.producto_id).toBe(1);
      expect(item1?.stock_comprometido).toBe(48);
      expect(item1?.stock_actual).toBe(32);
      // Definición matemática FASE 7: max(0, 32 - 48) = 0
      expect(item1?.stock_disponible_real).toBe(0);

      // Helper: isProductCommitted
      expect(result.current.isProductCommitted(1)).toBe(true);
      expect(result.current.isProductCommitted(9999)).toBe(false);

      // Helper: getAvailableRealStock
      const realStockProd2 = result.current.getAvailableRealStock(2, 1);
      expect(realStockProd2).toBe(20); // 50 actual - 30 comprometido = 20 libre
      expect(result.current.getAvailableRealStock(9999)).toBe(0);
    });

    it("clasifica alertas operativas por severidad (CRITICAL <48h vs WARNING <=14d)", async () => {
      const { result } = renderHook(() => useEventAlerts(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.eventAlerts.length).toBeGreaterThanOrEqual(2);
      expect(result.current.criticalAlertsCount).toBe(1);
      expect(result.current.warningAlertsCount).toBe(1);
      expect(result.current.hasCriticalAlerts).toBe(true);
      expect(result.current.hasWarningAlerts).toBe(true);

      // Validar alerta crítica (< 48h)
      const critical = result.current.criticalAlerts[0]!;
      expect(critical.severidad).toBe("CRITICAL");
      expect(critical.horas_restantes).toBeLessThan(48);
      expect(critical.evento_nombre).toContain("Boda Romina & Ignacio");
      expect(critical.total_insumos_deficit).toBe(2);

      // Validar alerta de advertencia (<= 14d)
      const warning = result.current.warningAlerts[0]!;
      expect(warning.severidad).toBe("WARNING");
      expect(warning.horas_restantes).toBeGreaterThanOrEqual(48);
      expect(warning.dias_restantes).toBe(5);
      expect(warning.evento_nombre).toContain("TechCorp");
    });

    it("permite refetch combinado de faltantes, stock comprometido y alertas", async () => {
      const faltantesSpy = vi.spyOn(eventsApi, "getFaltantesAnalytics");
      const committedSpy = vi.spyOn(eventsApi, "getCommittedStock");
      const alertsSpy = vi.spyOn(eventsApi, "getEventAlerts");

      const { result } = renderHook(() => useEventAlerts(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.refetch();
      });

      expect(faltantesSpy).toHaveBeenCalled();
      expect(committedSpy).toHaveBeenCalled();
      expect(alertsSpy).toHaveBeenCalled();
    });
  });
});
