import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RecetaDialog, calculateIngredientTotalCost } from "../components/RecetaDialog";
import { ComboDialog } from "../components/ComboDialog";
import { OptionGroupSelectorModal } from "../components/OptionGroupSelectorModal";
import { RecetaDetalleModal } from "../components/RecetaDetalleModal";
import { INITIAL_RECETAS_MOCK, INITIAL_CATEGORIAS_RECETAS_MOCK } from "../hooks/useRecetas";
import { INITIAL_COMBOS_MOCK, INITIAL_CATEGORIAS_COMBOS_MOCK } from "../hooks/useCombos";
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

describe("FASE 5: Modales Operativos Especializados (RecetaDialog, ComboDialog, OptionGroupSelectorModal, RecetaDetalleModal)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (httpClient.apiRequest as any).mockRejectedValue(new Error("Offline in test harness"));
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. RecetaDialog.tsx (Modal Maestro de Recetas en 3 Pestañas + Escandallo Vivo)
  // ==========================================================================
  describe("1. RecetaDialog — 3 Pestañas, Escandallo Fijo, Opciones Dinámicas y Costeo en Vivo", () => {
    it("calculates ingredient total cost with merma factor accurately", () => {
      // Sin merma: 2 * 5000 = 10000
      expect(calculateIngredientTotalCost(2, 0, 5000)).toBe(10000);
      // Con 20% merma: 1 / (1 - 0.2) * 8000 = 1.25 * 8000 = 10000
      expect(calculateIngredientTotalCost(1, 20, 8000)).toBe(10000);
    });

    it("renders the 3 internal tabs and switches between General, Fixed Ingredients, and Dynamic Components", () => {
      const onClose = vi.fn();
      renderWithQuery(
        <RecetaDialog
          open={true}
          onClose={onClose}
          categorias={INITIAL_CATEGORIAS_RECETAS_MOCK}
          productos={INITIAL_PRODUCTOS_MOCK}
          recetasCatalogo={INITIAL_RECETAS_MOCK}
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
        />
      );

      expect(screen.getByTestId("receta-dialog")).toBeDefined();
      expect(screen.getByTestId("receta-tab-general")).toBeDefined();
      expect(screen.getByTestId("receta-tab-ingredients")).toBeDefined();
      expect(screen.getByTestId("receta-tab-dynamic")).toBeDefined();
      expect(screen.getByTestId("receta-live-costing-panel")).toBeDefined();

      // Default tab is general
      expect(screen.getByTestId("receta-panel-general")).toBeDefined();

      // Switch to Tab 2: Ingredients
      fireEvent.click(screen.getByTestId("receta-tab-ingredients"));
      expect(screen.getByTestId("receta-panel-ingredients")).toBeDefined();

      // Switch to Tab 3: Dynamic Options
      fireEvent.click(screen.getByTestId("receta-tab-dynamic"));
      expect(screen.getByTestId("receta-panel-dynamic")).toBeDefined();
    });

    it("adds fixed ingredients, prevents self-reference, and recalculates Live Costing (Base & Worst-Case)", async () => {
      const onSave = vi.fn();
      const onClose = vi.fn();
      const existingReceta = INITIAL_RECETAS_MOCK[0]!; // Lomo Vetado (rec-1)

      renderWithQuery(
        <RecetaDialog
          open={true}
          onClose={onClose}
          receta={existingReceta}
          categorias={INITIAL_CATEGORIAS_RECETAS_MOCK}
          productos={INITIAL_PRODUCTOS_MOCK}
          recetasCatalogo={INITIAL_RECETAS_MOCK}
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
          onSave={onSave}
        />
      );

      // Go to Tab 2: Fixed Ingredients
      fireEvent.click(screen.getByTestId("receta-tab-ingredients"));

      // Verify self-reference is blocked: rec-1 should not be in the candidate select options
      const candidateSelect = screen.getByTestId("select-candidate-ingrediente") as HTMLSelectElement;
      const optionValues = Array.from(candidateSelect.options).map((o) => o.value);
      expect(optionValues).not.toContain(`subreceta:${existingReceta.id}`);
      // But sub-recipe rec-sub-1 IS available
      expect(optionValues).toContain("subreceta:rec-sub-1");

      // Add a new ingredient
      fireEvent.click(screen.getByTestId("btn-add-ingrediente-fijo"));
      expect(screen.getByTestId("ingrediente-fijo-row-1")).toBeDefined();

      // Update quantity and merma on row 1
      fireEvent.change(screen.getByTestId("input-ingrediente-cantidad-1"), {
        target: { value: "0.5" },
      });
      fireEvent.change(screen.getByTestId("input-ingrediente-merma-1"), {
        target: { value: "10" },
      });

      // Go to Tab 3: Dynamic Components and check linked groups from rec-1
      fireEvent.click(screen.getByTestId("receta-tab-dynamic"));
      expect(screen.getByTestId("receta-dynamic-group-0")).toBeDefined();
      expect(screen.getByTestId("receta-dynamic-group-1")).toBeDefined();

      // Live costing panel shows Fixed Cost, Default Options Cost, Total Base Cost, and Worst-Case Cost
      const fixedCostText = screen.getByTestId("live-cost-fixed").textContent || "";
      const worstCaseText = screen.getByTestId("live-cost-worst-case").textContent || "";
      expect(fixedCostText.length).toBeGreaterThan(0);
      expect(worstCaseText.length).toBeGreaterThan(0);

      // Save recipe
      fireEvent.click(screen.getByTestId("btn-save-receta"));
      await waitFor(() => {
        expect(onSave).toHaveBeenCalledTimes(1);
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  // ==========================================================================
  // 2. ComboDialog.tsx (Modal Maestro de Combos: Fijos + Dinámicos + Ahorro)
  // ==========================================================================
  describe("2. ComboDialog — Componentes Fijos, Grupos Dinámicos y Resumen Financiero con Ahorro", () => {
    it("renders ComboDialog, adds fixed components and links dynamic option groups, calculating savings", async () => {
      const onSave = vi.fn();
      const onClose = vi.fn();

      renderWithQuery(
        <ComboDialog
          open={true}
          onClose={onClose}
          combo={INITIAL_COMBOS_MOCK[0]!}
          categorias={INITIAL_CATEGORIAS_COMBOS_MOCK}
          productos={INITIAL_PRODUCTOS_MOCK}
          recetas={INITIAL_RECETAS_MOCK}
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
          onSave={onSave}
        />
      );

      expect(screen.getByTestId("combo-dialog")).toBeDefined();
      expect(screen.getByTestId("combo-block-fixed")).toBeDefined();
      expect(screen.getByTestId("combo-block-dynamic")).toBeDefined();
      expect(screen.getByTestId("combo-live-summary")).toBeDefined();

      // Add a fixed item to the combo
      fireEvent.click(screen.getByTestId("btn-add-combo-fixed-item"));
      expect(screen.getByTestId("combo-fixed-item-row-1")).toBeDefined();

      // Open OptionGroupSelectorModal from ComboDialog and link another group
      fireEvent.click(screen.getByTestId("btn-combo-open-option-group-selector"));
      expect(screen.getByTestId("option-group-selector-modal")).toBeDefined();

      fireEvent.click(screen.getByTestId("btn-select-group-grp-guarnicion"));
      expect(screen.queryByTestId("option-group-selector-modal")).toBeNull();
      expect(screen.getByTestId("combo-dynamic-group-1")).toBeDefined();

      // Financial summary displays base cost, combo price, and client savings
      expect(screen.getByTestId("combo-summary-base-cost")).toBeDefined();
      expect(screen.getByTestId("combo-summary-client-savings")).toBeDefined();
      expect(screen.getByTestId("combo-summary-margin-badge")).toBeDefined();

      // Save combo
      fireEvent.click(screen.getByTestId("btn-save-combo"));
      await waitFor(() => {
        expect(onSave).toHaveBeenCalledTimes(1);
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  // ==========================================================================
  // 3. OptionGroupSelectorModal.tsx (Biblioteca y Creación In-Situ)
  // ==========================================================================
  describe("3. OptionGroupSelectorModal — Selección desde Biblioteca y Creación In-Situ", () => {
    it("filters option groups in library and selects an existing group", () => {
      const onSelectGroup = vi.fn();
      const onClose = vi.fn();

      renderWithQuery(
        <OptionGroupSelectorModal
          open={true}
          onClose={onClose}
          onSelectGroup={onSelectGroup}
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
          productos={INITIAL_PRODUCTOS_MOCK}
          subrecetas={INITIAL_RECETAS_MOCK}
        />
      );

      expect(screen.getByTestId("option-group-selector-modal")).toBeDefined();
      expect(screen.getByTestId("option-group-library-panel")).toBeDefined();

      // Search for "Guarnición"
      fireEvent.change(screen.getByTestId("option-group-search-input"), {
        target: { value: "Guarnición" },
      });

      expect(screen.getByTestId("library-group-card-grp-guarnicion")).toBeDefined();
      expect(screen.queryByTestId("library-group-card-grp-termino")).toBeNull();

      // Click select
      fireEvent.click(screen.getByTestId("btn-select-group-grp-guarnicion"));
      expect(onSelectGroup).toHaveBeenCalledWith(
        expect.objectContaining({ id: "grp-guarnicion" })
      );
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("creates a new polymorphic option group in-situ and links it immediately", async () => {
      const onSelectGroup = vi.fn();
      const onClose = vi.fn();

      renderWithQuery(
        <OptionGroupSelectorModal
          open={true}
          onClose={onClose}
          onSelectGroup={onSelectGroup}
          initialTab="create"
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
          productos={INITIAL_PRODUCTOS_MOCK}
          subrecetas={INITIAL_RECETAS_MOCK}
        />
      );

      expect(screen.getByTestId("option-group-create-panel")).toBeDefined();

      // Fill group metadata
      fireEvent.change(screen.getByTestId("input-group-name"), {
        target: { value: "Elección de Salsa Especial" },
      });
      fireEvent.change(screen.getByTestId("input-group-min"), {
        target: { value: "1" },
      });
      fireEvent.change(screen.getByTestId("input-group-max"), {
        target: { value: "2" },
      });

      // Add another polymorphic option item
      fireEvent.click(screen.getByTestId("btn-add-group-option-item"));
      expect(screen.getByTestId("group-option-item-row-1")).toBeDefined();

      // Save and link
      fireEvent.click(screen.getByTestId("btn-save-and-link-group"));
      await waitFor(() => {
        expect(onSelectGroup).toHaveBeenCalledWith(
          expect.objectContaining({
            nombre: "Elección de Salsa Especial",
            seleccion_minima: 1,
            seleccion_maxima: 2,
          })
        );
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  // ==========================================================================
  // 4. RecetaDetalleModal.tsx (Ficha Técnica Gastronómica y Escalador de Porciones)
  // ==========================================================================
  describe("4. RecetaDetalleModal — Escalador Interactivo de Porciones en Vivo", () => {
    it("renders technical sheet and dynamically scales net/gross quantities and costs for 10 and 50 portions", () => {
      const onClose = vi.fn();
      const onEdit = vi.fn();
      const sampleReceta = {
        ...INITIAL_RECETAS_MOCK[0]!,
        preparacion: "1. Sellar a fuego vivo.\n2. Reposar 3 minutos.",
        video_url: "https://example.com/video-lomo.mp4",
        documento_url: "https://example.com/ficha-lomo.pdf",
      };

      render(
        <RecetaDetalleModal
          open={true}
          onClose={onClose}
          receta={sampleReceta}
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
          onEdit={onEdit}
        />
      );

      expect(screen.getByTestId("receta-detalle-modal")).toBeDefined();
      expect(screen.getByTestId("receta-portion-scaler")).toBeDefined();

      // Base yield is 1 portion: Lomo Vetado net qty = 0.35 kg
      expect(screen.getByTestId("scaled-net-qty-0").textContent).toContain("0.35 kg");
      expect(screen.getByTestId("scaler-factor-badge").textContent).toContain("1x");

      // Click preset 10 portions -> net qty = 3.5 kg
      fireEvent.click(screen.getByTestId("btn-preset-porciones-10"));
      expect(screen.getByTestId("scaler-factor-badge").textContent).toContain("10x");
      expect(screen.getByTestId("scaled-net-qty-0").textContent).toContain("3.5 kg");

      // Click preset 50 portions -> net qty = 17.5 kg
      fireEvent.click(screen.getByTestId("btn-preset-porciones-50"));
      expect(screen.getByTestId("scaler-factor-badge").textContent).toContain("50x");
      expect(screen.getByTestId("scaled-net-qty-0").textContent).toContain("17.5 kg");

      // Verify preparation text and multimedia links
      expect(screen.getByTestId("detalle-preparacion-section").textContent).toContain(
        "Sellar a fuego vivo"
      );
      expect(screen.getByTestId("link-detalle-video")).toBeDefined();
      expect(screen.getByTestId("link-detalle-documento")).toBeDefined();

      // Verify Print button and Kitchen Print Header
      const printBtn = screen.getByTestId("btn-print-receta-detalle");
      expect(printBtn).toBeDefined();
      const printSpy = vi.fn();
      window.print = printSpy;
      fireEvent.click(printBtn);
      expect(printSpy).toHaveBeenCalled();
      expect(screen.getByTestId("kitchen-print-header")).toBeDefined();
    });
  });
});
