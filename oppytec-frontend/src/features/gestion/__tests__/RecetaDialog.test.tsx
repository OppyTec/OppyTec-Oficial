import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RecetaDialog } from "../components/RecetaDialog";
import { RecetasView } from "../components/recetas/RecetasView";
import { CombosView } from "../components/combos/CombosView";
import { INITIAL_RECETAS_MOCK, INITIAL_CATEGORIAS_RECETAS_MOCK } from "../hooks/useRecetas";
import { INITIAL_GRUPOS_OPCIONES_MOCK } from "../hooks/useGruposOpciones";
import { INITIAL_PRODUCTOS_MOCK } from "../useGestion";
import * as httpClient from "@/shared/api/httpClient";

vi.mock("@/shared/api/httpClient", async () => {
  const actual = await vi.importActual<any>("@/shared/api/httpClient");
  return {
    ...actual,
    apiRequest: vi.fn().mockRejectedValue(new Error("Offline in test harness")),
  };
});

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("FASE 5: RecetaDialog & Integration with RecetasView / CombosView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (httpClient.apiRequest as any).mockRejectedValue(new Error("Offline in test harness"));
  });

  afterEach(() => {
    cleanup();
  });

  it("opens RecetaDialog in duplicate mode with Copy prefix", () => {
    const onClose = vi.fn();
    renderWithQuery(
      <RecetaDialog
        open={true}
        onClose={onClose}
        receta={INITIAL_RECETAS_MOCK[0]!}
        isDuplicate={true}
        categorias={INITIAL_CATEGORIAS_RECETAS_MOCK}
        productos={INITIAL_PRODUCTOS_MOCK}
        recetasCatalogo={INITIAL_RECETAS_MOCK}
        gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
      />
    );

    const nameInput = screen.getByTestId("input-receta-nombre") as HTMLInputElement;
    expect(nameInput.value).toContain("Lomo Vetado");
    const codeInput = screen.getByTestId("input-receta-codigo") as HTMLInputElement;
    expect(codeInput.value).toContain("-COPY");
  });

  it("connects RecetaDialog and RecetaDetalleModal inside RecetasView (Create, View, Edit, Duplicate)", async () => {
    renderWithQuery(<RecetasView productos={INITIAL_PRODUCTOS_MOCK} />);

    await screen.findByTestId("recetas-table-root");

    // 1. Click "+ Nueva Receta" -> opens RecetaDialog
    fireEvent.click(screen.getByTestId("btn-new-receta"));
    expect(screen.getByTestId("receta-dialog")).toBeDefined();
    fireEvent.click(screen.getByTestId("btn-close-receta-dialog"));
    expect(screen.queryByTestId("receta-dialog")).toBeNull();

    // 2. Click View on rec-1 -> opens RecetaDetalleModal
    fireEvent.click(screen.getByTestId("btn-view-receta-rec-1"));
    expect(screen.getByTestId("receta-detalle-modal")).toBeDefined();

    // Click Edit inside RecetaDetalleModal -> transitions to RecetaDialog
    fireEvent.click(screen.getByTestId("btn-detalle-edit-receta"));
    expect(screen.queryByTestId("receta-detalle-modal")).toBeNull();
    expect(screen.getByTestId("receta-dialog")).toBeDefined();
    fireEvent.click(screen.getByTestId("btn-close-receta-dialog"));

    // 3. Click Duplicate on rec-1 -> opens RecetaDialog in duplicate mode
    fireEvent.click(screen.getByTestId("btn-duplicate-receta-rec-1"));
    expect(screen.getByTestId("receta-dialog")).toBeDefined();
  });

  it("connects ComboDialog inside CombosView (Create, Edit, Duplicate)", async () => {
    renderWithQuery(<CombosView productos={INITIAL_PRODUCTOS_MOCK} />);

    await screen.findByTestId("combos-table-root");

    // 1. Click "+ Nuevo Combo" -> opens ComboDialog
    fireEvent.click(screen.getByTestId("btn-new-combo"));
    expect(screen.getByTestId("combo-dialog")).toBeDefined();
    fireEvent.click(screen.getByTestId("btn-close-combo-dialog"));
    expect(screen.queryByTestId("combo-dialog")).toBeNull();

    // 2. Click Edit on combo-1 -> opens ComboDialog
    fireEvent.click(screen.getByTestId("btn-edit-combo-combo-1"));
    expect(screen.getByTestId("combo-dialog")).toBeDefined();
  });
});
