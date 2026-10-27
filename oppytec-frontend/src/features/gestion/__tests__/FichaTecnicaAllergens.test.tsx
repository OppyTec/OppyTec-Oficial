import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AllergenBadge } from "../components/AllergenBadge";
import { RecetaDetalleModal } from "../components/RecetaDetalleModal";
import { useRecetas, INITIAL_RECETAS_MOCK } from "../hooks/useRecetas";
import { INITIAL_GRUPOS_OPCIONES_MOCK } from "../hooks/useGruposOpciones";
import * as httpClient from "@/shared/api/httpClient";
import type { AllergenInfo, Receta } from "../types";

vi.mock("@/shared/api/httpClient", async () => {
  const actual = await vi.importActual<any>("@/shared/api/httpClient");
  return {
    ...actual,
    apiRequest: vi.fn(),
    getHttpRequestContext: () => ({ tenantId: "tenant-mock-123" }),
  };
});

function createQueryWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("FASE 6: Ficha Técnica Imprimible/Exportable para Cocina y Trazabilidad de Alérgenos", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. AllergenBadge Component Unit Tests
  // ==========================================================================
  describe("1. Componente AllergenBadge", () => {
    it("renders allergen badge with icon, translated label, and tooltip for GLUTEN", () => {
      const allergen: AllergenInfo = {
        code: "GLUTEN",
        nombre: "Gluten",
        nombre_en: "Gluten",
        icono: "Wheat",
        descripcion: "Cereales que contienen gluten: trigo, avena, cebada",
      };

      render(<AllergenBadge allergen={allergen} size="md" />);

      const badge = screen.getByTestId("allergen-badge-gluten");
      expect(badge).toBeDefined();
      expect(badge.textContent).toContain("Gluten");
      expect(badge.getAttribute("title")).toBe("Cereales que contienen gluten: trigo, avena, cebada");
    });

    it("renders allergen from string code and supports showLabel=false", () => {
      render(<AllergenBadge allergen="CRUSTACEANS" showLabel={false} size="sm" />);

      const badge = screen.getByTestId("allergen-badge-crustaceans");
      expect(badge).toBeDefined();
      expect(badge.textContent).toBe(""); // label hidden
      expect(badge.getAttribute("title")).toBe("Crustáceos");
    });

    it("renders multiple allergens with distinct styling (FISH, MILK, EGGS, NUTS)", () => {
      const sampleCodes = ["FISH", "MILK", "EGGS", "NUTS"] as const;
      const { unmount } = render(
        <div>
          {sampleCodes.map((code) => (
            <AllergenBadge key={code} allergen={code} />
          ))}
        </div>
      );

      expect(screen.getByTestId("allergen-badge-fish")).toBeDefined();
      expect(screen.getByTestId("allergen-badge-milk")).toBeDefined();
      expect(screen.getByTestId("allergen-badge-eggs")).toBeDefined();
      expect(screen.getByTestId("allergen-badge-nuts")).toBeDefined();
      unmount();
    });
  });

  // ==========================================================================
  // 2. RecetaDetalleModal: Trazabilidad de Alérgenos y Advertencias
  // ==========================================================================
  describe("2. RecetaDetalleModal — Trazabilidad de Alérgenos Normados", () => {
    it("displays declared allergens section with count badge and warning banner when allergens exist", () => {
      const recetaConAlergenos: Receta = {
        id: "rec-salmon",
        codigo: "REC-SAL-001",
        nombre: "Salmón a la Mantequilla Negra",
        porciones_rendimiento: 1,
        costo_total_calculado: 8500,
        alergenos: [
          {
            code: "FISH",
            nombre: "Pescado",
            nombre_en: "Fish",
            icono: "Fish",
            descripcion: "Pescado fresco y derivados",
          },
          {
            code: "MILK",
            nombre: "Lácteos",
            nombre_en: "Milk",
            icono: "Milk",
            descripcion: "Mantequilla con lactosa",
          },
        ],
        ingredientes_fijos: [
          {
            id: "ing-1",
            nombre: "Filete de Salmón",
            target_type: "producto",
            unidad: "kg",
            cantidad_receta: 0.25,
            porcentaje_merma: 5,
            costo_unitario: 16000,
            costo_total: 4210.53,
          },
        ],
      };

      render(
        <RecetaDetalleModal
          open={true}
          onClose={vi.fn()}
          receta={recetaConAlergenos}
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
        />
      );

      // Section exists
      expect(screen.getByTestId("detalle-alergenos-section")).toBeDefined();
      // Count badge
      expect(screen.getByTestId("badge-allergens-count").textContent).toContain("2 detectados");
      // Badges
      expect(screen.getByTestId("allergen-badge-fish")).toBeDefined();
      expect(screen.getByTestId("allergen-badge-milk")).toBeDefined();
      // Cross-contamination warning
      expect(screen.getByTestId("detalle-alergenos-section").textContent).toContain(
        "ADVERTENCIA: Contiene alérgenos normados"
      );
    });

    it("displays '0 alérgenos' badge and empty text when recipe has no allergens declared", () => {
      const recetaLimpia: Receta = {
        id: "rec-limpia",
        codigo: "REC-ENS-001",
        nombre: "Ensalada Verde de la Huerta",
        porciones_rendimiento: 1,
        costo_total_calculado: 1200,
        alergenos: [],
        ingredientes_fijos: [
          {
            id: "ing-lechuga",
            nombre: "Lechuga Costina",
            target_type: "producto",
            unidad: "kg",
            cantidad_receta: 0.15,
            porcentaje_merma: 10,
            costo_unitario: 1500,
            costo_total: 250,
          },
        ],
      };

      render(
        <RecetaDetalleModal
          open={true}
          onClose={vi.fn()}
          receta={recetaLimpia}
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
        />
      );

      expect(screen.getByTestId("badge-allergens-none").textContent).toContain("0 alérgenos");
      expect(screen.getByTestId("detalle-allergens-empty").textContent).toContain(
        "Sin alérgenos declarados en la formulación"
      );
    });
  });

  // ==========================================================================
  // 3. Ficha Técnica Imprimible para Cocina & Ticket Térmico
  // ==========================================================================
  describe("3. Ficha Técnica Imprimible para Cocina (window.print & Escalamiento Bruto)", () => {
    it("renders printable kitchen header with order info, recipe code, name, and scaled portions", () => {
      const receta = {
        ...INITIAL_RECETAS_MOCK[0]!,
        preparacion: "1. Encender el fuego a 220°C.\n2. Marinar y sellar 4 minutos por lado.",
      };

      render(
        <RecetaDetalleModal
          open={true}
          onClose={vi.fn()}
          receta={receta}
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
        />
      );

      const kitchenHeader = screen.getByTestId("kitchen-print-header");
      expect(kitchenHeader).toBeDefined();
      expect(kitchenHeader.textContent).toContain("FICHA DE PRODUCCIÓN DE COCINA");
      expect(kitchenHeader.textContent).toContain("OPPYTEC RESTOBAR & GASTRONOMY");
      expect(kitchenHeader.textContent).toContain(receta.nombre);
      expect(kitchenHeader.textContent).toContain(receta.codigo);
    });

    it("triggers window.print() when clicking header and footer print buttons", () => {
      const printSpy = vi.fn();
      window.print = printSpy;

      render(
        <RecetaDetalleModal
          open={true}
          onClose={vi.fn()}
          receta={INITIAL_RECETAS_MOCK[0]!}
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
        />
      );

      const headerPrintBtn = screen.getByTestId("btn-print-receta-detalle");
      const footerPrintBtn = screen.getByTestId("btn-print-receta-footer");

      fireEvent.click(headerPrintBtn);
      expect(printSpy).toHaveBeenCalledTimes(1);

      fireEvent.click(footerPrintBtn);
      expect(printSpy).toHaveBeenCalledTimes(2);
    });

    it("calculates accurate gross quantity with merma factor when scaling to 25 portions", () => {
      // 0.35 kg con 5% merma: gross multiplier = 1 / (1 - 0.05) = 1.0526...
      // a 25 porciones: net = 0.35 * 25 = 8.75 kg, gross = 8.75 / 0.95 = 9.211 kg
      render(
        <RecetaDetalleModal
          open={true}
          onClose={vi.fn()}
          receta={INITIAL_RECETAS_MOCK[0]!}
          gruposBiblioteca={INITIAL_GRUPOS_OPCIONES_MOCK}
        />
      );

      fireEvent.click(screen.getByTestId("btn-preset-porciones-25"));

      expect(screen.getByTestId("scaler-factor-badge").textContent).toContain("25x");
      expect(screen.getByTestId("scaled-net-qty-0").textContent).toContain("8.75 kg");
      expect(screen.getByTestId("scaled-gross-qty-0").textContent).toContain("9.211 kg");
    });
  });

  // ==========================================================================
  // 4. Hook useRecetas: Consumo de Endpoints Phase 6
  // ==========================================================================
  describe("4. useRecetas — getKitchenSheet & getAllergens", () => {
    it("calls GET /api/v1/recipes/{id}/kitchen-sheet?servings=N with correct parameters", async () => {
      const mockSheetResponse = {
        recipe_id: 10,
        codigo: "REC-TEST-10",
        nombre: "Test Ficha",
        porciones_base: 1,
        porciones_solicitadas: 50,
        factor_escalamiento: 50,
        ingredientes_fijos: [],
        grupos_opciones: [],
        alergenos_consolidados: [],
      };

      (httpClient.apiRequest as any).mockResolvedValue({
        data: mockSheetResponse,
        status: 200,
      });

      const { result } = renderHook(() => useRecetas(), {
        wrapper: createQueryWrapper(),
      });

      const sheet = await result.current.getKitchenSheet(10, 50);

      expect(httpClient.apiRequest).toHaveBeenCalledWith(
        "/api/v1/recipes/10/kitchen-sheet?servings=50",
        { method: "GET" }
      );
      expect(sheet.porciones_solicitadas).toBe(50);
    });

    it("calls GET /api/v1/recipes/{id}/allergens and returns consolidated allergen list", async () => {
      const mockAllergens: AllergenInfo[] = [
        { code: "GLUTEN", nombre: "Gluten" },
        { code: "EGGS", nombre: "Huevos" },
      ];

      (httpClient.apiRequest as any).mockResolvedValue({
        data: mockAllergens,
        status: 200,
      });

      const { result } = renderHook(() => useRecetas(), {
        wrapper: createQueryWrapper(),
      });

      const allergens = await result.current.getAllergens(10);

      expect(httpClient.apiRequest).toHaveBeenCalledWith(
        "/api/v1/recipes/10/allergens",
        { method: "GET" }
      );
      expect(allergens).toHaveLength(2);
      expect(allergens[0]?.code).toBe("GLUTEN");
    });
  });
});
