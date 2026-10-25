// oppytec-frontend/src/features/inventory/__tests__/ContarInventarioPage.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup, within } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import * as httpClient from "@/shared/api/httpClient";
import { ContarInventarioPage } from "../conteo/ContarInventarioPage";
import { BLIND_COUNT_DRAFT_KEY } from "../hooks/useContarInventario";

// Mock de framer-motion para tests rápidos y deterministas
vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<any>("framer-motion");
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
    motion: {
      div: ({ children, className, onClick, ...props }: any) => (
        <div className={className} onClick={onClick} {...props}>
          {children}
        </div>
      ),
    },
  };
});

function createWrapper(initialEntries = ["/contar-inventario"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={initialEntries}>
        <QueryClientProvider client={queryClient}>
          <PermissionsProvider>
            <Routes>
              <Route path="/contar-inventario" element={children} />
              <Route path="/recuentos" element={<div data-testid="page-recuentos">Historial</div>} />
              <Route path="/" element={<div data-testid="page-home">Home</div>} />
            </Routes>
          </PermissionsProvider>
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

describe("ContarInventarioPage — Recuento Físico Ciego (Fase 6)", () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    vi.clearAllMocks();

    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url, options) => {
      const baseEnvelope = {
        status: 200,
        statusText: "OK",
        headers: {},
        traceId: "trace-mock-conteo",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant-mock-conteo",
      };

      if (url.includes("/api/v1/inventory/counts/start")) {
        return { ...baseEnvelope, data: { id: 7001 } };
      }
      if (url.includes("/finalize")) {
        return { ...baseEnvelope, data: { id: 7001, estado: "PENDIENTE_APROBACION" } };
      }
      if (url.includes("/items")) {
        return { ...baseEnvelope, data: { id: 7001 } };
      }
      if (options?.fallbackData) {
        return { ...baseEnvelope, data: options.fallbackData };
      }
      return { ...baseEnvelope, data: {} };
    });
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  // --------------------------------------------------------------------------
  // 1. Estado Idle: Bienvenida, Selectores y Reanudar Borrador
  // --------------------------------------------------------------------------
  describe("1. Estado Idle (Inicio de Sesión)", () => {
    it("renderiza correctamente la pantalla de bienvenida con SectionHeader centrado", () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });

      expect(screen.getByTestId("contar-inventario-container")).toBeInTheDocument();
      expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
      expect(screen.getAllByText("Recuento de Inventario")[0]).toBeInTheDocument();
      expect(screen.getByTestId("conteo-step-idle")).toBeInTheDocument();
      expect(screen.getByText("Iniciar nuevo recuento")).toBeInTheDocument();
      expect(screen.getByTestId("conteo-start-btn")).toBeInTheDocument();
    });

    it("permite cambiar la bodega seleccionada y refleja el nombre en el botón de inicio", () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });

      const selectBodega = screen.getByTestId("conteo-bodega-select") as HTMLSelectElement;
      expect(selectBodega.value).toBe("1");

      fireEvent.change(selectBodega, { target: { value: "3" } });
      expect(selectBodega.value).toBe("3");

      const startBtn = screen.getByTestId("conteo-start-btn");
      expect(startBtn).toHaveTextContent("Bodega Seca Central");
    });

    it("muestra banner de borrador offline si existe en localStorage y permite descartarlo", () => {
      const mockDraft = {
        sessionId: 99,
        bodegaId: 2,
        areaOperativaId: null,
        step: "idle",
        items: [
          {
            localId: "c-1",
            producto_id: 1,
            producto_nombre: "Lomo Vetado Angus Premium",
            unidad_medida: "kg",
            stock_fisico_contado: 12,
            lote_codigo: "LOT-1",
            fecha_vencimiento: null,
            costo_unitario_ppp: 14200,
          },
        ],
        notas: "Borrador de prueba",
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem(BLIND_COUNT_DRAFT_KEY, JSON.stringify(mockDraft));

      render(<ContarInventarioPage />, { wrapper: createWrapper() });

      expect(screen.getByTestId("conteo-offline-draft-banner")).toBeInTheDocument();
      expect(screen.getByTestId("conteo-resume-draft-btn")).toBeInTheDocument();

      // Descartar borrador
      window.confirm = vi.fn().mockReturnValue(true);
      fireEvent.click(screen.getByTestId("conteo-discard-draft-btn"));
      expect(screen.queryByTestId("conteo-offline-draft-banner")).not.toBeInTheDocument();
    });

    it("restaura directamente en pantalla counting si el borrador guardado estaba activo", () => {
      const mockDraft = {
        sessionId: 99,
        bodegaId: 2,
        areaOperativaId: null,
        step: "counting",
        items: [
          {
            localId: "c-1",
            producto_id: 1,
            producto_nombre: "Lomo Vetado Angus Premium",
            unidad_medida: "kg",
            stock_fisico_contado: 12,
            lote_codigo: "LOT-1",
            fecha_vencimiento: null,
            costo_unitario_ppp: 14200,
          },
        ],
        notas: "Conteo en vivo",
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem(BLIND_COUNT_DRAFT_KEY, JSON.stringify(mockDraft));

      render(<ContarInventarioPage />, { wrapper: createWrapper() });

      expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      expect(screen.getByTestId("conteo-row-1")).toBeInTheDocument();
      expect(within(screen.getByTestId("conteo-row-1")).getByText("Lomo Vetado Angus Premium")).toBeInTheDocument();
    });
  });

  // --------------------------------------------------------------------------
  // 2. Transición a Counting y Toma Física de Inventario
  // --------------------------------------------------------------------------
  describe("2. Estado Counting (Toma Física Activa)", () => {
    it("inicia la sesión al presionar Comenzar y muestra la pantalla de conteo", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });

      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      // Indicador offline activo
      expect(screen.getByTestId("conteo-offline-indicator")).toBeInTheDocument();
      expect(screen.getByTestId("conteo-search-input")).toBeInTheDocument();
      expect(screen.getByTestId("inventario-table-wrapper")).toBeInTheDocument();
    });

    it("permite buscar un insumo por texto y añadirlo a la grilla", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId("conteo-search-input");
      fireEvent.change(searchInput, { target: { value: "Salmón" } });

      await waitFor(() => {
        expect(screen.getByTestId("conteo-search-results")).toBeInTheDocument();
      });

      const salmonItem = screen.getByTestId("conteo-search-item-2");
      fireEvent.mouseDown(salmonItem);

      // Ahora debe aparecer en la tabla de recuento
      expect(screen.getByTestId("conteo-row-2")).toBeInTheDocument();
      expect(within(screen.getByTestId("conteo-row-2")).getByText("Salmón Atlántico Fresco")).toBeInTheDocument();
    });

    it("soporta escaneo rápido de código de barra / SKU con tecla Enter", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId("conteo-search-input");
      // Escaneo de SKU "CAR-LOM-001" (Lomo Vetado)
      fireEvent.change(searchInput, { target: { value: "CAR-LOM-001" } });
      fireEvent.keyDown(searchInput, { key: "Enter", code: "Enter" });

      expect(screen.getByTestId("conteo-row-1")).toBeInTheDocument();
      expect(within(screen.getByTestId("conteo-row-1")).getByText("Lomo Vetado Angus Premium")).toBeInTheDocument();
    });

    it("permite modificar la cantidad contada y usar los atajos rápidos (+1, +5, +10)", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      // Agregar Lomo Vetado
      const searchInput = screen.getByTestId("conteo-search-input");
      fireEvent.change(searchInput, { target: { value: "CAR-LOM-001" } });
      fireEvent.keyDown(searchInput, { key: "Enter" });

      const qtyInput = screen.getByTestId("conteo-qty-1") as HTMLInputElement;
      expect(qtyInput.value).toBe("0");

      // Modificación directa
      fireEvent.change(qtyInput, { target: { value: "15" } });
      expect(qtyInput.value).toBe("15");

      // Botón rápido +5
      const btnPlus5 = screen.getAllByTitle("Sumar 5 unidades")[0]!;
      fireEvent.click(btnPlus5);
      expect(qtyInput.value).toBe("20");

      // Botón rápido +10
      const btnPlus10 = screen.getAllByTitle("Sumar 10 unidades")[0]!;
      fireEvent.click(btnPlus10);
      expect(qtyInput.value).toBe("30");

      // Botón rápido +1
      const btnPlus1 = screen.getAllByTitle("Sumar 1 unidad")[0]!;
      fireEvent.click(btnPlus1);
      expect(qtyInput.value).toBe("31");
    });

    it("permite eliminar una fila contada de la lista", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId("conteo-search-input");
      fireEvent.change(searchInput, { target: { value: "CAR-LOM-001" } });
      fireEvent.keyDown(searchInput, { key: "Enter" });

      expect(screen.getByTestId("conteo-row-1")).toBeInTheDocument();

      const deleteBtn = screen.getByTestId("conteo-delete-1");
      fireEvent.click(deleteBtn);

      expect(screen.queryByTestId("conteo-row-1")).not.toBeInTheDocument();
    });

    it("permite cancelar el conteo activo y volver a idle", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      window.confirm = vi.fn().mockReturnValue(true);
      fireEvent.click(screen.getByTestId("conteo-cancel-btn"));

      expect(screen.getByTestId("conteo-step-idle")).toBeInTheDocument();
    });
  });

  // --------------------------------------------------------------------------
  // 3. Revisión, Finalización y Éxito 1:1 Legacy
  // --------------------------------------------------------------------------
  describe("3. Revisión y Finalización (Reviewing -> Finished)", () => {
    it("navega al paso de revisión al pulsar Finalizar Conteo", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      // Añadir un producto
      const searchInput = screen.getByTestId("conteo-search-input");
      fireEvent.change(searchInput, { target: { value: "CAR-LOM-001" } });
      fireEvent.keyDown(searchInput, { key: "Enter" });

      const reviewBtn = screen.getByTestId("conteo-review-btn");
      fireEvent.click(reviewBtn);

      expect(screen.getByTestId("conteo-step-reviewing")).toBeInTheDocument();
      expect(screen.getByText("Revisión del Recuento Físico")).toBeInTheDocument();
      expect(screen.getByTestId("conteo-notas-input")).toBeInTheDocument();
    });

    it("permite regresar desde revisión a seguir modificando el conteo", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId("conteo-search-input");
      fireEvent.change(searchInput, { target: { value: "CAR-LOM-001" } });
      fireEvent.keyDown(searchInput, { key: "Enter" });

      fireEvent.click(screen.getByTestId("conteo-review-btn"));
      expect(screen.getByTestId("conteo-step-reviewing")).toBeInTheDocument();

      fireEvent.click(screen.getByTestId("conteo-back-to-counting-btn"));
      expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
    });

    it("confirma y finaliza el recuento enviando la sesión y mostrando la pantalla de éxito", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      // Añadir insumo y escribir notas
      const searchInput = screen.getByTestId("conteo-search-input");
      fireEvent.change(searchInput, { target: { value: "CAR-LOM-001" } });
      fireEvent.keyDown(searchInput, { key: "Enter" });

      fireEvent.click(screen.getByTestId("conteo-review-btn"));

      const notasInput = screen.getByTestId("conteo-notas-input");
      fireEvent.change(notasInput, { target: { value: "Conteo físico fin de turno sin incidentes" } });

      const confirmBtn = screen.getByTestId("conteo-confirm-finalize-btn");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-finished")).toBeInTheDocument();
      });

      expect(screen.getByText("¡Recuento Enviado!")).toBeInTheDocument();
      expect(screen.getByText("pendiente")).toBeInTheDocument();
      expect(screen.getByTestId("conteo-start-another-btn")).toBeInTheDocument();
      expect(screen.getByTestId("conteo-go-recuentos-btn")).toBeInTheDocument();
      expect(screen.getByTestId("conteo-go-home-btn")).toBeInTheDocument();
    });

    it("permite iniciar otro conteo desde la pantalla final de éxito", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId("conteo-search-input");
      fireEvent.change(searchInput, { target: { value: "CAR-LOM-001" } });
      fireEvent.keyDown(searchInput, { key: "Enter" });

      fireEvent.click(screen.getByTestId("conteo-review-btn"));
      fireEvent.click(screen.getByTestId("conteo-confirm-finalize-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-finished")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("conteo-start-another-btn"));
      expect(screen.getByTestId("conteo-step-idle")).toBeInTheDocument();
    });

    it("navega al historial de recuentos al hacer clic en Ver Historial", async () => {
      render(<ContarInventarioPage />, { wrapper: createWrapper() });
      fireEvent.click(screen.getByTestId("conteo-start-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-counting")).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId("conteo-search-input");
      fireEvent.change(searchInput, { target: { value: "CAR-LOM-001" } });
      fireEvent.keyDown(searchInput, { key: "Enter" });

      fireEvent.click(screen.getByTestId("conteo-review-btn"));
      fireEvent.click(screen.getByTestId("conteo-confirm-finalize-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("conteo-step-finished")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("conteo-go-recuentos-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("page-recuentos")).toBeInTheDocument();
      });
    });
  });
});
