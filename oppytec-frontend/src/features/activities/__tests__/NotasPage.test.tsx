import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NotasPage } from "../notas/NotasPage";
import { NotaCard } from "../notas/NotaCard";
import { MOCK_NOTAS_EQUIPO } from "../mockData";

// Mock de sonner
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

describe("Submódulo 1: Notas de Turno y Muro Operativo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renderiza correctamente NotasPage con título y toolbar unificada", async () => {
    renderWithClient(<NotasPage />);

    expect(screen.getByTestId("notas-page")).toBeInTheDocument();
    expect(screen.getByText("Notas de Turno")).toBeInTheDocument();
    expect(screen.getByTestId("area-selector")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Buscar notas/i)).toBeInTheDocument();
  });

  it("permite alternar entre pestañas 'Notas de Equipo' y 'Personales'", async () => {
    renderWithClient(<NotasPage />);

    const teamTab = screen.getByText("Notas de Equipo");
    const personalTab = screen.getByText("Personales");
    expect(teamTab).toBeInTheDocument();
    expect(personalTab).toBeInTheDocument();

    // Cambiar a Personales
    fireEvent.click(personalTab);
    await waitFor(() => {
      expect(screen.getByText("Revisar costos de mermas de fin de mes")).toBeInTheDocument();
    });

    // Volver a Notas de Equipo
    fireEvent.click(teamTab);
    await waitFor(() => {
      expect(screen.getByText("Cambio de proveedor para Lomo Liso y Salmón")).toBeInTheDocument();
    });
  });

  it("renderiza NotaCard con avatar, cargo gastronómico y formato interactivo de @menciones y #insumos", () => {
    const mockNota = MOCK_NOTAS_EQUIPO[0]!;
    const onTagClick = vi.fn();
    const onMentionClick = vi.fn();

    renderWithClient(
      <NotaCard
        nota={mockNota}
        onTagClick={onTagClick}
        onMentionClick={onMentionClick}
      />
    );

    expect(screen.getByText("Juan Campillay")).toBeInTheDocument();
    expect(screen.getByText("Chef")).toBeInTheDocument();
    expect(screen.getByText("@mrodriguez")).toBeInTheDocument();
    expect(screen.getByText("#lomo-vetado")).toBeInTheDocument();

    // Click en la mención interactiva
    fireEvent.click(screen.getByText("@mrodriguez"));
    expect(onMentionClick).toHaveBeenCalledWith("mrodriguez");

    // Click en el tag de insumo interactivo
    fireEvent.click(screen.getByText("#lomo-vetado"));
    expect(onTagClick).toHaveBeenCalledWith("lomo-vetado");
  });

  it("permite confirmar la lectura con 'Marcar como leído'", async () => {
    const baseNota = MOCK_NOTAS_EQUIPO[1]!;
    const mockNota = { ...baseNota, leido_por_mi: false };
    const onMarkRead = vi.fn();

    renderWithClient(
      <NotaCard
        nota={mockNota}
        onMarkRead={onMarkRead}
      />
    );

    const markReadBtn = screen.getByText("Marcar como leído");
    expect(markReadBtn).toBeInTheDocument();
    fireEvent.click(markReadBtn);
    expect(onMarkRead).toHaveBeenCalledWith(mockNota.id);
  });

  it("abre el diálogo para redactar una nueva nota", async () => {
    renderWithClient(<NotasPage />);

    const newNoteBtn = screen.getAllByText("Nueva Nota")[0]!;
    fireEvent.click(newNoteBtn);

    await waitFor(() => {
      expect(screen.getByTestId("responsive-dialog")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Ej: Novedades del turno matutino/i)).toBeInTheDocument();
    });
  });

  it("abre el diálogo de Minuta de Traspaso OppyFy y presenta los 4 puntos clave", async () => {
    // Mock navigator.clipboard
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });

    renderWithClient(<NotasPage />);

    // Buscar y pulsar botón OppyFy
    const oppyfyBtn = screen.getByTestId("oppyfy-minuta-btn");
    expect(oppyfyBtn).toBeInTheDocument();
    fireEvent.click(oppyfyBtn);

    // Diálogo abierto
    await waitFor(() => {
      expect(screen.getByText("🤖 Resumen de Traspaso (OppyFy AI)")).toBeInTheDocument();
      expect(screen.getByText("1. Incidentes y Novedades Críticas")).toBeInTheDocument();
      expect(screen.getByText("2. Producción y Stock")).toBeInTheDocument();
      expect(screen.getByText("3. Tareas Pendientes y Relevo")).toBeInTheDocument();
      expect(screen.getByText("4. Dotación y Asistencia")).toBeInTheDocument();
    });

    // Probar acción Copiar Minuta
    const copyBtn = screen.getByText("Copiar Minuta");
    expect(copyBtn).toBeInTheDocument();
    fireEvent.click(copyBtn);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalled();
    });
  });
});

