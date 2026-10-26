// oppytec-frontend/src/features/consumo/__tests__/ManosLibresPage.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ManosLibresPage } from "../ManosLibresPage";

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

describe("Módulo de Consumo - Vista 2: ManosLibresPage", () => {
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
  // 1. Cabecera Canónica y Contexto Operativo
  // ==========================================================================
  describe("Cabecera Canónica y Contexto Operativo", () => {
    it("renders SectionHeader with correct title, subtitle, and mic icon", async () => {
      renderWithProviders(<ManosLibresPage />);

      expect(await screen.findByText("Consumo Manos Libres")).toBeInTheDocument();
      expect(
        screen.getAllByText(
          "Registro operativo por voz para cocina, barra y preparación"
        )[0]
      ).toBeInTheDocument();
    });

    it("renders context selectors (AreaSelector, BodegaSelector) and TTS toggle", () => {
      renderWithProviders(<ManosLibresPage />);

      expect(screen.getByTestId("manos-libres-toolbar")).toBeInTheDocument();
      expect(screen.getByTestId("area-selector")).toBeInTheDocument();
      expect(screen.getByTestId("bodega-selector")).toBeInTheDocument();
      expect(screen.getByTestId("voice-tts-toggle")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 2. Estaciones de Trabajo y Selección de Operario
  // ==========================================================================
  describe("Estaciones de Trabajo y Selección de Operario", () => {
    it("renders worker stations grid and allows changing active worker", async () => {
      renderWithProviders(<ManosLibresPage />);

      expect(screen.getByTestId("stations-grid")).toBeInTheDocument();

      const stationCard1 = await screen.findByTestId("station-card-1");
      const stationCard2 = await screen.findByTestId("station-card-2");

      expect(stationCard1).toBeInTheDocument();
      expect(stationCard2).toBeInTheDocument();

      // Cambiar de estación activa a la 2
      fireEvent.click(stationCard2);
      expect(stationCard2).toHaveClass("bg-[#f97316]/10");
    });
  });

  // ==========================================================================
  // 3. Control de Escucha e Input Manual de Contingencia
  // ==========================================================================
  describe("Control de Escucha e Input Manual de Contingencia", () => {
    it("toggles listening state and TTS audio settings", () => {
      renderWithProviders(<ManosLibresPage />);

      const micBtn = screen.getByTestId("voice-mic-btn");
      expect(micBtn).toBeInTheDocument();

      // Click para iniciar/detener escucha
      fireEvent.click(micBtn);

      const ttsToggle = screen.getByTestId("voice-tts-toggle");
      fireEvent.click(ttsToggle);
      expect(screen.getByText("Voz Silenciada")).toBeInTheDocument();

      fireEvent.click(ttsToggle);
      expect(screen.getByText("Voz TTS Activada")).toBeInTheDocument();
    });

    it("allows manual input submission as fallback when mic is unavailable", async () => {
      renderWithProviders(<ManosLibresPage />);

      const manualInput = screen.getByTestId("voice-manual-input");
      const sendBtn = screen.getByTestId("voice-manual-send-btn");

      expect(manualInput).toBeInTheDocument();
      expect(sendBtn).toBeDisabled();

      fireEvent.change(manualInput, {
        target: { value: "Oppy consumo 2 kilos de salmon filete" },
      });
      expect(sendBtn).not.toBeDisabled();

      fireEvent.click(sendBtn);

      await waitFor(() => {
        expect(manualInput).toHaveValue("");
      });
    });
  });

  // ==========================================================================
  // 4. Feed de Comandas Pendientes y Acciones
  // ==========================================================================
  describe("Feed de Comandas Pendientes", () => {
    it("renders pending orders feed with confirm and reject actions", async () => {
      renderWithProviders(<ManosLibresPage />);

      expect(screen.getByTestId("voice-pending-orders-feed")).toBeInTheDocument();

      // Comanda mock inicial
      const orderCard = await screen.findByTestId("voice-order-card-voice-ord-001");
      expect(orderCard).toBeInTheDocument();
      expect(screen.getByText("Salmón Fresco Filete")).toBeInTheDocument();
      expect(screen.getByText("CONSUMO")).toBeInTheDocument();

      // Botón confirmar
      const confirmBtn = screen.getByTestId("voice-order-confirm-btn-voice-ord-001");
      expect(confirmBtn).toBeInTheDocument();
      fireEvent.click(confirmBtn);

      // Botón descartar
      const rejectBtn = screen.getByTestId("voice-order-reject-btn-voice-ord-001");
      expect(rejectBtn).toBeInTheDocument();
      fireEvent.click(rejectBtn);
    });
  });
});
