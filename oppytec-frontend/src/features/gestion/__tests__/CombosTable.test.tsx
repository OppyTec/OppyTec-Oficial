import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { CombosTable } from "../components/combos/CombosTable";
import { CombosToolbar } from "../components/combos/CombosToolbar";
import { ComboMobileCard } from "../components/combos/ComboMobileCard";
import type { Combo, CategoriaCombo } from "../types";

const MOCK_CATEGORIAS_COMBOS: CategoriaCombo[] = [
  { id: "cat-cmb-ejecutivos", nombre: "Menús Ejecutivos", color: "#ec4899", icono: "Boxes", orden: 1 },
  { id: "cat-cmb-promos", nombre: "Promociones y Dúos", color: "#8b5cf6", icono: "Tags", orden: 2 },
];

const MOCK_COMBOS: Combo[] = [
  {
    id: "combo-1",
    codigo: "CMB-PARR-001",
    nombre: "Menú Ejecutivo Parrillero",
    descripcion: "Lomo vetado a la parrilla + bebestible a elección",
    categoria_combo_id: "cat-cmb-ejecutivos",
    categoria_nombre: "Menús Ejecutivos",
    es_dinamico: true,
    precio: 23900,
    precio_neto: 20084.03,
    precio_bruto: 23900,
    costo_base: 8900,
    costo_total_calculado: 8900,
    margen_pct: 55.69, // Amarillo (40-64%)
    disponibilidad_stock_porciones: 18,
    esta_disponible: true,
    items_fijos: [
      {
        id: "cf-1",
        combo_id: "combo-1",
        receta_id: "rec-1",
        nombre: "Lomo Vetado a la Parrilla 350g",
        target_type: "receta",
        cantidad: 1,
        costo_unitario: 6200,
        costo_total: 6200,
      },
    ],
    grupos_opciones: [
      { id: "cgo-1", combo_id: "combo-1", grupo_id: "grp-1", orden: 1, es_requerido: true },
    ],
  },
  {
    id: "combo-2",
    codigo: "CMB-DUO-002",
    nombre: "Dúo Marino Austral",
    descripcion: "2 porciones de Salmón grillado",
    categoria_combo_id: "cat-cmb-promos",
    categoria_nombre: "Promociones y Dúos",
    es_dinamico: false,
    precio: 34900,
    precio_neto: 29327.73,
    precio_bruto: 34900,
    costo_base: 14200,
    costo_total_calculado: 14200,
    margen_pct: 68.5, // Verde (>= 65%)
    disponibilidad_stock_porciones: 0,
    esta_disponible: false,
    items_fijos: [
      {
        id: "cf-2",
        combo_id: "combo-2",
        receta_id: "rec-2",
        nombre: "Salmón Grillado Finas Hierbas",
        target_type: "receta",
        cantidad: 2,
        costo_unitario: 7100,
        costo_total: 14200,
      },
    ],
  },
];

describe("FASE 4: CombosTable & Combos Components Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // 1. Multidimensional CombosTable Rendering
  describe("1. Renderizado de Tabla CombosTable", () => {
    it("renders table root, column headers, and combo rows", () => {
      render(<CombosTable combos={MOCK_COMBOS} />);

      expect(screen.getByTestId("combos-table-root")).toBeDefined();
      expect(screen.getByText("Combo & Código")).toBeDefined();
      expect(screen.getByText("Disponibilidad Stock")).toBeDefined();
      expect(screen.getByText("Componentes")).toBeDefined();
      expect(screen.getByText("Costo Base")).toBeDefined();

      expect(screen.getByTestId("combo-row-combo-1")).toBeDefined();
      expect(screen.getByTestId("combo-row-combo-2")).toBeDefined();
    });

    it("displays dynamic badge ⚡ for dynamic combo and fixed badge 📜 for static combo", () => {
      render(<CombosTable combos={MOCK_COMBOS} />);

      expect(screen.getByTestId("badge-combo-dinamico")).toBeDefined();
      expect(screen.getByTestId("badge-combo-dinamico").textContent).toContain("Dinámico");

      expect(screen.getByTestId("badge-combo-fijo")).toBeDefined();
      expect(screen.getByTestId("badge-combo-fijo").textContent).toContain("Fijo");
    });

    it("displays stock availability badges with quantities or out of stock", () => {
      render(<CombosTable combos={MOCK_COMBOS} />);

      // Combo 1 has 18 available
      const stockBadge1 = screen.getByTestId("stock-badge-combo-1");
      expect(stockBadge1.textContent).toContain("18 disponibles");
      expect(stockBadge1.className).toContain("emerald");

      // Combo 2 is out of stock (0)
      const stockBadge2 = screen.getByTestId("stock-badge-combo-2");
      expect(stockBadge2.textContent).toContain("Sin Stock");
      expect(stockBadge2.className).toContain("rose");
    });

    it("renders components structure count correctly", () => {
      render(<CombosTable combos={MOCK_COMBOS} />);

      // Combo 1: 1 fijo + 1 configurable
      expect(screen.getAllByText("1 fijos").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("1 configurables")).toBeDefined();
    });

    it("triggers callbacks when clicking view, edit, duplicate, and delete actions", () => {
      const onView = vi.fn();
      const onEdit = vi.fn();
      const onDuplicate = vi.fn();
      const onDelete = vi.fn();

      render(
        <CombosTable
          combos={MOCK_COMBOS}
          onView={onView}
          onEdit={onEdit}
          onDuplicate={onDuplicate}
          onDelete={onDelete}
        />
      );

      fireEvent.click(screen.getByTestId("btn-view-combo-combo-1"));
      expect(onView).toHaveBeenCalledWith(MOCK_COMBOS[0]);

      fireEvent.click(screen.getByTestId("btn-edit-combo-combo-1"));
      expect(onEdit).toHaveBeenCalledWith(MOCK_COMBOS[0]);

      fireEvent.click(screen.getByTestId("btn-duplicate-combo-combo-1"));
      expect(onDuplicate).toHaveBeenCalledWith(MOCK_COMBOS[0]);

      fireEvent.click(screen.getByTestId("btn-delete-combo-combo-1"));
      expect(onDelete).toHaveBeenCalledWith(MOCK_COMBOS[0]);
    });
  });

  // 2. CombosToolbar Component Tests
  describe("2. Barra de Herramientas CombosToolbar", () => {
    it("renders search bar, category dropdown, and primary/secondary buttons", () => {
      const onSearchChange = vi.fn();
      const onSelectCategoria = vi.fn();
      const onNewCombo = vi.fn();
      const onManageCategorias = vi.fn();

      render(
        <CombosToolbar
          searchQuery=""
          onSearchChange={onSearchChange}
          selectedCategoriaId={null}
          onSelectCategoria={onSelectCategoria}
          categorias={MOCK_CATEGORIAS_COMBOS}
          onNewCombo={onNewCombo}
          onManageCategorias={onManageCategorias}
        />
      );

      expect(screen.getByTestId("combos-toolbar")).toBeDefined();
      expect(screen.getByTestId("combos-search-input")).toBeDefined();
      expect(screen.getByTestId("combos-categoria-select")).toBeDefined();
      expect(screen.getByTestId("btn-new-combo")).toBeDefined();
      expect(screen.getByTestId("btn-combo-categories")).toBeDefined();
    });

    it("triggers callbacks for search clear, category change, and new combo click", () => {
      const onSearchChange = vi.fn();
      const onSelectCategoria = vi.fn();
      const onNewCombo = vi.fn();

      render(
        <CombosToolbar
          searchQuery="parrillero"
          onSearchChange={onSearchChange}
          selectedCategoriaId="cat-cmb-ejecutivos"
          onSelectCategoria={onSelectCategoria}
          categorias={MOCK_CATEGORIAS_COMBOS}
          onNewCombo={onNewCombo}
        />
      );

      // Clear search
      const clearBtn = screen.getByTestId("combos-clear-search");
      fireEvent.click(clearBtn);
      expect(onSearchChange).toHaveBeenCalledWith("");

      // Category select
      const select = screen.getByTestId("combos-categoria-select");
      fireEvent.change(select, { target: { value: "cat-cmb-promos" } });
      expect(onSelectCategoria).toHaveBeenCalledWith("cat-cmb-promos");

      // New combo button
      fireEvent.click(screen.getByTestId("btn-new-combo"));
      expect(onNewCombo).toHaveBeenCalled();
    });
  });

  // 3. Mobile Card Component Tests
  describe("3. Tarjeta Mobile-First ComboMobileCard", () => {
    it("renders mobile card with touch targets >= 44px and expands components list", () => {
      const onView = vi.fn();
      const onEdit = vi.fn();

      render(
        <ComboMobileCard
          combo={MOCK_COMBOS[0]!}
          onView={onView}
          onEdit={onEdit}
        />
      );

      expect(screen.getByTestId("combo-card-combo-1")).toBeDefined();
      expect(screen.getByTestId("card-badge-combo-dinamico")).toBeDefined();
      expect(screen.getByTestId("card-stock-badge-combo-1")).toBeDefined();

      // Accordion toggle button
      const toggleBtn = screen.getByTestId("btn-toggle-expand-combo-combo-1");
      expect(toggleBtn.className).toContain("min-h-[44px]");
      expect(screen.queryByText("Ítems Fijos (1):")).toBeNull();

      // Expand accordion
      fireEvent.click(toggleBtn);
      expect(screen.getByText("Ítems Fijos (1):")).toBeDefined();
      expect(screen.getByText("Lomo Vetado a la Parrilla 350g")).toBeDefined();
      expect(screen.getByText("Grupos Configurables (1):")).toBeDefined();

      // Action buttons
      const editBtn = screen.getByTestId("card-btn-edit-combo-combo-1");
      expect(editBtn.className).toContain("min-h-[44px]");
      fireEvent.click(editBtn);
      expect(onEdit).toHaveBeenCalledWith(MOCK_COMBOS[0]);
    });
  });
});
