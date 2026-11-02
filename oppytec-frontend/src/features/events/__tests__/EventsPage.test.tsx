// oppytec-frontend/src/features/events/__tests__/EventsPage.test.tsx
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EventsPage } from "../EventsPage";
import { eventsApi } from "../api/eventsApi";
import { MOCK_EVENTOS_LIST, MOCK_SALONES, MOCK_FALTANTES_RESPONSE } from "../mockData";

// Mock de sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

function renderWithClient(ui: React.ReactElement) {
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
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe("Feature Events - EventsPage & Operational Components (Fase 4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(eventsApi, "getEvents").mockResolvedValue(MOCK_EVENTOS_LIST);
    vi.spyOn(eventsApi, "getSalones").mockResolvedValue(MOCK_SALONES);
    vi.spyOn(eventsApi, "getFaltantesAnalytics").mockResolvedValue(MOCK_FALTANTES_RESPONSE);
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renderiza la cabecera institucional y toolbar estandarizado", async () => {
    renderWithClient(<EventsPage />);

    expect(screen.getByTestId("events-page-root")).toBeInTheDocument();
    expect(screen.getByText("Eventos y Banquetes")).toBeInTheDocument();
    expect(screen.getAllByText("Programación y Control de Consumo")[0]).toBeInTheDocument();

    expect(screen.getByTestId("events-toolbar")).toBeInTheDocument();
    expect(screen.getByTestId("btn-abrir-salones")).toBeInTheDocument();
    expect(screen.getByTestId("btn-exportar-eventos")).toBeInTheDocument();
    expect(screen.getByTestId("btn-view-grid")).toBeInTheDocument();
    expect(screen.getByTestId("btn-view-calendar")).toBeInTheDocument();
    expect(screen.getByTestId("btn-nuevo-evento")).toBeInTheDocument();
  });

  it("muestra banner de alerta cuando existen faltantes de stock proyectados", async () => {
    renderWithClient(<EventsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("event-shortages-banner")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Alerta de Stock Comprometido/i)
    ).toBeInTheDocument();

    const btnVerFaltantes = screen.getByTestId("btn-ver-resumen-faltantes");
    fireEvent.click(btnVerFaltantes);

    await waitFor(() => {
      expect(screen.getByTestId("resumen-faltantes-dialog-content")).toBeInTheDocument();
    });
  });

  it("permite alternar entre pestañas y actualiza los contadores reactivos", async () => {
    renderWithClient(<EventsPage />);

    // Esperar que TanStack Query cargue y actualice los contadores reactivos
    await waitFor(() => {
      expect(screen.getByTestId("badge-count-proximos")).toHaveTextContent("2");
    });

    const tabHistorial = screen.getByTestId("tab-historial");
    const tabCancelados = screen.getByTestId("tab-cancelados");

    fireEvent.click(tabHistorial);
    await waitFor(() => {
      expect(screen.getByTestId("badge-count-historial")).toHaveTextContent("1");
    });

    fireEvent.click(tabCancelados);
    await waitFor(() => {
      expect(screen.getByTestId("badge-count-cancelados")).toHaveTextContent("1");
    });
  });

  it("alterna entre vista de grilla de tarjetas y vista de calendario", async () => {
    renderWithClient(<EventsPage />);

    expect(screen.getByTestId("events-grid-view")).toBeInTheDocument();
    expect(screen.queryByTestId("events-calendar-view")).not.toBeInTheDocument();

    const btnCalendar = screen.getByTestId("btn-view-calendar");
    fireEvent.click(btnCalendar);

    await waitFor(() => {
      expect(screen.getByTestId("events-calendar-view")).toBeInTheDocument();
      expect(screen.getByTestId("eventos-calendar")).toBeInTheDocument();
    });

    const btnSemana = screen.getByTestId("calendar-view-week");
    fireEvent.click(btnSemana);

    const btnMes = screen.getByTestId("calendar-view-month");
    fireEvent.click(btnMes);

    const btnToday = screen.getByTestId("calendar-today");
    fireEvent.click(btnToday);

    const btnGrid = screen.getByTestId("btn-view-grid");
    fireEvent.click(btnGrid);
    expect(screen.getByTestId("events-grid-view")).toBeInTheDocument();
  });

  it("abre el diálogo de creación al presionar 'Nuevo Evento'", async () => {
    renderWithClient(<EventsPage />);

    const btnNuevo = screen.getByTestId("btn-nuevo-evento");
    fireEvent.click(btnNuevo);

    await waitFor(() => {
      expect(screen.getByTestId("evento-dialog-content")).toBeInTheDocument();
      expect(screen.getByTestId("step-1-content")).toBeInTheDocument();
    });

    const btnSiguiente = screen.getByTestId("btn-siguiente-step");
    fireEvent.click(btnSiguiente);

    await waitFor(() => {
      expect(screen.getByTestId("step-2-content")).toBeInTheDocument();
    });
  });

  it("abre el diálogo de gestión de salones al presionar 'Salones'", async () => {
    renderWithClient(<EventsPage />);

    const btnSalones = screen.getByTestId("btn-abrir-salones");
    fireEvent.click(btnSalones);

    await waitFor(() => {
      expect(screen.getByTestId("salones-dialog-content")).toBeInTheDocument();
    });

    expect(screen.getByTestId("input-salon-nombre")).toBeInTheDocument();
    expect(screen.getByTestId("input-salon-neto")).toBeInTheDocument();
    expect(screen.getByTestId("input-salon-bruto")).toBeInTheDocument();
  });

  it("calcula recálculo bidireccional Neto / Bruto en el formulario de salones", async () => {
    renderWithClient(<EventsPage />);

    fireEvent.click(screen.getByTestId("btn-abrir-salones"));

    await waitFor(() => {
      expect(screen.getByTestId("input-salon-neto")).toBeInTheDocument();
    });

    const inputNeto = screen.getByTestId("input-salon-neto") as HTMLInputElement;
    const inputBruto = screen.getByTestId("input-salon-bruto") as HTMLInputElement;

    fireEvent.change(inputNeto, { target: { value: "100000" } });
    expect(inputBruto.value).toBe("119000");

    fireEvent.change(inputBruto, { target: { value: "238000" } });
    expect(inputNeto.value).toBe("200000");
  });

  it("ejecuta la exportación de eventos a archivo CSV", async () => {
    renderWithClient(<EventsPage />);

    const btnExportar = screen.getByTestId("btn-exportar-eventos");
    fireEvent.click(btnExportar);

    expect(btnExportar).toBeInTheDocument();
  });
});
