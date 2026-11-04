import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HorariosPage } from "../horarios/HorariosPage";
import { TurnoDialog } from "../horarios/TurnoDialog";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
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

describe("Submódulo 3: Horarios, Turnos Semanales y Legal Guard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renderiza correctamente HorariosPage y la matriz semanal con colaboradores", async () => {
    renderWithClient(<HorariosPage />);

    expect(screen.getByTestId("horarios-page")).toBeInTheDocument();
    expect(screen.getByText("Cuadrante de Horarios y Turnos")).toBeInTheDocument();
    expect(screen.getByText("Clonar Semana Anterior")).toBeInTheDocument();
    expect(screen.getByText("Juan Campillay")).toBeInTheDocument();
    expect(screen.getByText("María Rodríguez")).toBeInTheDocument();
  });

  it("permite alternar entre vistas semanal y 3 días para smartphones", async () => {
    renderWithClient(<HorariosPage />);

    const weekBtn = screen.getByText("Semana Completa");
    expect(weekBtn).toBeInTheDocument();
    fireEvent.click(weekBtn);

    const threeDaysBtn = screen.getByText("3 Días (Móvil)");
    expect(threeDaysBtn).toBeInTheDocument();
    fireEvent.click(threeDaysBtn);

    await waitFor(() => {
      expect(screen.getByTestId("horarios-page")).toBeInTheDocument();
    });
  });

  it("TurnoDialog muestra alertas de Legal Guard si se detectan advertencias", async () => {
    const onValidate = vi.fn().mockResolvedValue({
      tiene_alertas: true,
      total_horas_semanales: "48.0",
      alertas: [
        {
          tipo: "EXCESO_40_HORAS",
          mensaje: "Jornada excede las 40 horas legales semanales",
          severidad: "advertencia",
          detalle: {},
        },
      ],
    });

    renderWithClient(
      <TurnoDialog
        open={true}
        onClose={vi.fn()}
        onSave={vi.fn()}
        onValidateLegalGuard={onValidate}
      />
    );

    expect(screen.getByText("Asignar Turno")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Legal Guard Laboral")).toBeInTheDocument();
      expect(screen.getByText("Jornada excede las 40 horas legales semanales")).toBeInTheDocument();
    });
  });
});
