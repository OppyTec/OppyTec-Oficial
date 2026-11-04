import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TareasPage } from "../tareas/TareasPage";
import { TareaCard } from "../tareas/TareaCard";
import { IncompleteTaskDialog } from "../tareas/IncompleteTaskDialog";
import { MOCK_TAREAS } from "../mockData";

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

describe("Submódulo 2: Tareas Operativas y Checklists de Turno", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renderiza el Tablero Kanban con las 4 columnas operativas", async () => {
    renderWithClient(<TareasPage />);

    expect(screen.getByTestId("tareas-page")).toBeInTheDocument();
    expect(screen.getByText("Tareas Operativas")).toBeInTheDocument();

    const kanbanBtn = screen.getByText("Tablero Kanban");
    fireEvent.click(kanbanBtn);

    await waitFor(() => {
      expect(screen.getByText("Pendiente")).toBeInTheDocument();
      expect(screen.getByText("En Progreso")).toBeInTheDocument();
      expect(screen.getByText("Completada")).toBeInTheDocument();
      expect(screen.getByText("Incompleta")).toBeInTheDocument();
    });
  });

  it("permite alternar al Modo Checklist para smartphones de operarios", async () => {
    renderWithClient(<TareasPage />);

    const checklistBtn = screen.getByText("Modo Checklist");
    fireEvent.click(checklistBtn);

    await waitFor(() => {
      const checklistItems = screen.getAllByTestId("tarea-checklist-item");
      expect(checklistItems.length).toBeGreaterThan(0);
    });
  });

  it("renderiza el semáforo de urgencia de 6px en TareaCard", () => {
    const altaTarea = MOCK_TAREAS[0]!; // urgencia alta
    renderWithClient(<TareaCard tarea={altaTarea} />);

    const card = screen.getByTestId("tarea-card");
    expect(card.className).toContain("border-l-[6px]");
    expect(card.className).toContain("border-l-red-500");
    expect(screen.getByText("Alta")).toBeInTheDocument();
    expect(screen.getByText("Pedro Torres")).toBeInTheDocument();
  });

  it("IncompleteTaskDialog exige justificación mínima antes de confirmar", async () => {
    const tarea = MOCK_TAREAS[0]!;
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    renderWithClient(
      <IncompleteTaskDialog
        open={true}
        tarea={tarea}
        onClose={onClose}
        onConfirm={onConfirm}
      />
    );

    expect(screen.getByText("Justificar Tarea Incompleta")).toBeInTheDocument();

    const submitBtn = screen.getByText("Confirmar como Incompleta");
    expect(submitBtn).toBeDisabled();

    const textarea = screen.getByPlaceholderText(/Explica la causa/i);
    fireEvent.change(textarea, { target: { value: "Falta de stock crítico" } });

    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith(tarea.id, "Falta de stock crítico");
    });
  });

  it("abre el diálogo para crear una nueva tarea", async () => {
    renderWithClient(<TareasPage />);

    const newTaskBtn = screen.getAllByText("Nueva Tarea")[0]!;
    fireEvent.click(newTaskBtn);

    await waitFor(() => {
      expect(screen.getByTestId("responsive-dialog")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Ej: Sanitización de línea de frío/i)).toBeInTheDocument();
    });
  });
});
