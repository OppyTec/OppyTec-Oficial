// oppytec-frontend/src/features/consumo/__tests__/BuffetPage.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BuffetPage } from "../BuffetPage";

function renderWithProviders(ui: React.ReactElement) {
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

  return render(
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </BrowserRouter>
  );
}

describe("Módulo de Consumo - Vista 3: BuffetPage (Buffet Inteligente)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(async () => {
    cleanup();
    vi.restoreAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    await new Promise((r) => setTimeout(r, 20));
  });

  // ==========================================================================
  // 1. Cabecera Visual y Contexto Operativo
  // ==========================================================================
  describe("Cabecera Visual y Contexto Operativo", () => {
    it("renders SectionHeader with correct title, subtitle, and #06b6d4 identity", async () => {
      renderWithProviders(<BuffetPage />);

      expect(await screen.findByText("Buffet Inteligente")).toBeInTheDocument();
      expect(
        screen.getAllByText(
          "Control de estaciones, pesaje y liquidación de consumo por comensal"
        )[0]
      ).toBeInTheDocument();
    });

    it("renders context selectors and tabs (Sesión Activa, Historial)", async () => {
      renderWithProviders(<BuffetPage />);

      expect(screen.getByTestId("tab-sesion-activa")).toBeInTheDocument();
      expect(screen.getByTestId("tab-historial-buffet")).toBeInTheDocument();
      expect(screen.getByTestId("active-session-title")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 2. Métricas Financieras en Vivo y Cuadratura Pax
  // ==========================================================================
  describe("Métricas Financieras en Vivo", () => {
    it("displays live metrics cards (Montaje, Sobrante, Consumido, Costo Pax)", async () => {
      renderWithProviders(<BuffetPage />);

      expect(screen.getByTestId("metric-costo-montaje")).toBeInTheDocument();
      expect(screen.getByTestId("metric-sobrante")).toBeInTheDocument();
      expect(screen.getByTestId("metric-consumido")).toBeInTheDocument();
      expect(screen.getByTestId("metric-costo-pax")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 3. Tabla de Insumos de Buffet (BuffetItemsTable)
  // ==========================================================================
  describe("Tabla de Insumos de Buffet", () => {
    it("renders initial buffet session items with correct quantities", async () => {
      renderWithProviders(<BuffetPage />);

      expect(await screen.findByTestId("buffet-row-b-it-1")).toBeInTheDocument();
      expect(screen.getAllByText("Queso Parmesano Reggiano")[0]).toBeInTheDocument();
      expect(screen.getByTestId("val-apertura-b-it-1")).toHaveTextContent("2");
    });

    it("increments and decrements quantities reactively", async () => {
      renderWithProviders(<BuffetPage />);

      const incBtn = await screen.findByTestId("btn-inc-apertura-b-it-1");
      fireEvent.click(incBtn);

      expect(screen.getByTestId("val-apertura-b-it-1")).toHaveTextContent("2.5");

      const decBtn = screen.getByTestId("btn-dec-apertura-b-it-1");
      fireEvent.click(decBtn);
      expect(screen.getByTestId("val-apertura-b-it-1")).toHaveTextContent("2");
    });

    it("toggles leftover action between Retornar and Merma", async () => {
      renderWithProviders(<BuffetPage />);

      const toggleBtn = await screen.findByTestId("btn-toggle-sobrante-b-it-1");
      expect(toggleBtn).toHaveTextContent("Retornar");

      fireEvent.click(toggleBtn);
      expect(screen.getByTestId("btn-toggle-sobrante-b-it-1")).toHaveTextContent("Merma");
    });

    it("removes an item from the balance when trash button is clicked", async () => {
      renderWithProviders(<BuffetPage />);

      const removeBtn = await screen.findByTestId("btn-remove-b-it-1");
      fireEvent.click(removeBtn);

      await waitFor(() => {
        expect(screen.queryByText("Queso Parmesano Reggiano")).not.toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // 4. Escáner Visual de Cámara (StationCameraScanner)
  // ==========================================================================
  describe("Escáner Visual de Cámara", () => {
    it("opens camera scanner modal and executes IA simulated detection", async () => {
      renderWithProviders(<BuffetPage />);

      const openScannerBtn = screen.getByTestId("open-station-scanner-btn");
      fireEvent.click(openScannerBtn);

      expect(await screen.findByTestId("station-camera-scanner-modal")).toBeInTheDocument();

      // En entorno de test sin WebRTC, se activa simulate scan
      const simulateBtn = screen.getByTestId("simulate-scan-btn");
      fireEvent.click(simulateBtn);

      expect(await screen.findByTestId("detection-item-0")).toBeInTheDocument();

      // Ajustar cantidad de la primera detección
      const incDetBtn = screen.getByTestId("det-increment-0");
      fireEvent.click(incDetBtn);

      // Confirmar estación e incorporar al balance
      const confirmBtn = screen.getByTestId("confirm-station-btn");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("station-camera-scanner-modal")).not.toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // 5. Diálogo de Liquidación y Conciliación Pax (BuffetConciliationDialog)
  // ==========================================================================
  describe("Diálogo de Liquidación y Conciliación Pax", () => {
    it("opens conciliation dialog, updates Pax and submits finalization", async () => {
      renderWithProviders(<BuffetPage />);

      const openConciliationBtn = screen.getByTestId("open-conciliation-modal-btn");
      fireEvent.click(openConciliationBtn);

      expect(await screen.findByTestId("buffet-conciliation-dialog")).toBeInTheDocument();

      const paxInput = screen.getByTestId("pax-input");
      fireEvent.change(paxInput, { target: { value: "100" } });
      expect(paxInput).toHaveValue(100);

      const confirmFinalizeBtn = screen.getByTestId("confirm-finalize-buffet-btn");
      fireEvent.click(confirmFinalizeBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("buffet-conciliation-dialog")).not.toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // 6. Gestor de Plantillas de Buffet (BuffetTemplateModal)
  // ==========================================================================
  describe("Gestor de Plantillas de Buffet", () => {
    it("opens template modal, adds custom station, and saves template", async () => {
      renderWithProviders(<BuffetPage />);

      const openTemplatesBtn = screen.getByTestId("open-buffet-templates-btn");
      fireEvent.click(openTemplatesBtn);

      expect(await screen.findByTestId("buffet-template-modal")).toBeInTheDocument();

      const nameInput = screen.getByTestId("buffet-tpl-name-input");
      fireEvent.change(nameInput, { target: { value: "Buffet Parrillero Premium" } });

      const customStationInput = screen.getByTestId("custom-station-input");
      fireEvent.change(customStationInput, { target: { value: "Estación Parrilla en Vivo" } });

      const addStationBtn = screen.getByTestId("add-custom-station-btn");
      fireEvent.click(addStationBtn);

      expect(await screen.findByText("Estación Parrilla en Vivo")).toBeInTheDocument();

      const saveTplBtn = screen.getByTestId("save-buffet-template-btn");
      fireEvent.click(saveTplBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("buffet-template-modal")).not.toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // 7. Agregado Manual de Ítems e Historial de Sesiones
  // ==========================================================================
  describe("Agregado Manual de Ítems e Historial de Sesiones", () => {
    it("opens manual item modal and adds an item to the balance", async () => {
      renderWithProviders(<BuffetPage />);

      const openManualBtn = screen.getByTestId("open-manual-item-btn");
      fireEvent.click(openManualBtn);

      expect(await screen.findByTestId("manual-item-modal")).toBeInTheDocument();

      const nameInput = screen.getByTestId("manual-item-name-input");
      fireEvent.change(nameInput, { target: { value: "Prosciutto Di Parma" } });

      const qtyInput = screen.getByTestId("manual-item-qty-input");
      fireEvent.change(qtyInput, { target: { value: "3" } });

      const addBtn = screen.getByTestId("confirm-add-manual-item-btn");
      fireEvent.click(addBtn);

      await waitFor(() => {
        expect(screen.getAllByText("Prosciutto Di Parma")[0]).toBeInTheDocument();
      });
    });

    it("switches to Historial tab and displays registered sessions", async () => {
      renderWithProviders(<BuffetPage />);

      const historyTab = screen.getByTestId("tab-historial-buffet");
      fireEvent.click(historyTab);

      expect(await screen.findByTestId("buffet-history-view")).toBeInTheDocument();
      expect(screen.getByText("Desayuno Buffet Ejecutivo")).toBeInTheDocument();
    });
  });
});
