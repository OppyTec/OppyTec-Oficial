import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { RecetasTable, getMargenBadge } from "../components/recetas/RecetasTable";
import { RecetasToolbar } from "../components/recetas/RecetasToolbar";
import { RecetaMobileCard } from "../components/recetas/RecetaMobileCard";
import type { Receta, CategoriaReceta } from "../types";

const MOCK_CATEGORIAS: CategoriaReceta[] = [
  { id: "cat-rec-carnes", nombre: "Carnes a las Brasas", color: "#f59e0b" },
  { id: "cat-rec-mar", nombre: "Pescados y Mariscos", color: "#06b6d4" },
  { id: "cat-rec-postres", nombre: "Postres y Pastelería", color: "#ec4899" },
];

const MOCK_RECETAS: Receta[] = [
  {
    id: "rec-1",
    codigo: "REC-LOM-001",
    nombre: "Lomo Vetado a la Parrilla 350g",
    descripcion: "Corte selecto angus sellado al carbón",
    categoria_receta_id: "cat-rec-carnes",
    categoria_nombre: "Carnes a las Brasas",
    es_subreceta: false,
    es_dinamica: true,
    porciones: 1,
    porciones_rendimiento: 1,
    costo_total: 6200,
    costo_total_calculado: 6200,
    costo_porcion: 6200,
    costo_peor_caso: 7400,
    precio: 18900,
    precio_neto: 15882.35,
    precio_bruto: 18900,
    margen_pct: 60.96, // Semáforo: Amarillo (40 - 64.99%)
    ingredientes_fijos: [
      {
        id: "ing-1",
        receta_id: "rec-1",
        producto_id: "prod-1",
        nombre: "Lomo Vetado Angus",
        target_type: "producto",
        unidad: "kg",
        cantidad_receta: 0.35,
        porcentaje_merma: 5,
        costo_unitario: 14500,
        costo_total: 5328.95,
      },
    ],
    grupos_opciones: [
      { id: "rgo-1", receta_id: "rec-1", grupo_id: "grp-1", orden: 1, es_requerido: true },
      { id: "rgo-2", receta_id: "rec-1", grupo_id: "grp-2", orden: 2, es_requerido: false },
    ],
  },
  {
    id: "rec-2",
    codigo: "REC-SAL-002",
    nombre: "Salmón Grillado Finas Hierbas",
    descripcion: "Filete de salmón fresco",
    categoria_receta_id: "cat-rec-mar",
    categoria_nombre: "Pescados y Mariscos",
    es_subreceta: false,
    es_dinamica: false,
    porciones: 2,
    porciones_rendimiento: 2,
    costo_total: 8000,
    costo_total_calculado: 8000,
    costo_porcion: 4000,
    precio: 29900,
    precio_neto: 25126.05,
    precio_bruto: 29900,
    margen_pct: 73.25, // Semáforo: Verde (>= 65%)
    ingredientes_fijos: [
      {
        id: "ing-2",
        receta_id: "rec-2",
        producto_id: "prod-2",
        nombre: "Salmón Fresco",
        target_type: "producto",
        unidad: "kg",
        cantidad_receta: 0.5,
        porcentaje_merma: 2,
        costo_unitario: 16000,
        costo_total: 8000,
      },
    ],
  },
  {
    id: "rec-sub-1",
    codigo: "SUB-CHIMI-001",
    nombre: "Chimichurri Casero del Chef 1L",
    descripcion: "Sub-receta base de salsa",
    categoria_receta_id: "cat-rec-carnes",
    categoria_nombre: "Salsas & Subrecetas",
    es_subreceta: true,
    es_dinamica: false,
    porciones: 10,
    porciones_rendimiento: 10,
    costo_total: 4800,
    costo_total_calculado: 4800,
    costo_porcion: 480,
    precio: 0,
    precio_neto: 0,
    precio_bruto: 0,
    margen_pct: 0, // Semáforo: Rojo (< 40%)
    ingredientes_fijos: [
      {
        id: "ing-sub-1",
        receta_id: "rec-sub-1",
        producto_id: "prod-3",
        nombre: "Aceite de Oliva Extra Virgen",
        target_type: "producto",
        unidad: "litro",
        cantidad_receta: 1,
        porcentaje_merma: 0,
        costo_unitario: 4800,
        costo_total: 4800,
      },
    ],
  },
];

describe("FASE 4: RecetasTable & Recetas Components Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // 1. Helper function getMargenBadge unit tests
  describe("1. Semáforo de Margen Visual (getMargenBadge)", () => {
    it("returns green/success badge for margin >= 65%", () => {
      const badge = getMargenBadge(75);
      expect(badge.level).toBe("success");
      expect(badge.label).toBe("75.0%");
      expect(badge.className).toContain("emerald");
    });

    it("returns amber/warning badge for margin between 40% and 64.99%", () => {
      const badge = getMargenBadge(55.5);
      expect(badge.level).toBe("warning");
      expect(badge.label).toBe("55.5%");
      expect(badge.className).toContain("amber");
    });

    it("returns rose/danger badge for margin < 40%", () => {
      const badge = getMargenBadge(25);
      expect(badge.level).toBe("danger");
      expect(badge.label).toBe("25.0%");
      expect(badge.className).toContain("rose");
    });

    it("returns neutral fallback when margin is undefined or null", () => {
      expect(getMargenBadge(undefined).level).toBe("neutral");
      expect(getMargenBadge(null).level).toBe("neutral");
    });
  });

  // 2. Multidimensional Table Rendering
  describe("2. Renderizado de Tabla Multidimensional RecetasTable", () => {
    it("renders table root, column headers, and all recipe rows", () => {
      render(<RecetasTable recetas={MOCK_RECETAS} />);

      expect(screen.getByTestId("recetas-table-root")).toBeDefined();
      expect(screen.getByText("Receta & Ficha Técnica")).toBeDefined();
      expect(screen.getByText("Estructura de Insumos")).toBeDefined();
      expect(screen.getByText("Costo Escandallo (PPP)")).toBeDefined();
      expect(screen.getByText("Margen %")).toBeDefined();

      expect(screen.getByTestId("receta-row-rec-1")).toBeDefined();
      expect(screen.getByTestId("receta-row-rec-2")).toBeDefined();
      expect(screen.getByTestId("receta-row-rec-sub-1")).toBeDefined();
    });

    it("renders dynamic badge ⚡ for dynamic recipe and static badge 📜 for fixed recipe", () => {
      render(<RecetasTable recetas={MOCK_RECETAS} />);

      // Receta 1: Dinamica
      const badgeDinamica = screen.getByTestId("badge-dinamica");
      expect(badgeDinamica.textContent).toContain("Dinámica");

      // Receta 2: Fija
      const badgeFija = screen.getByTestId("badge-fija");
      expect(badgeFija.textContent).toContain("Fija");

      // Receta 3: Sub-receta
      const badgeSubreceta = screen.getByTestId("badge-subreceta");
      expect(badgeSubreceta.textContent).toContain("Sub-receta");
    });

    it("displays portions yield, fixed ingredients count, and dynamic groups count", () => {
      render(<RecetasTable recetas={MOCK_RECETAS} />);

      // Portions
      expect(screen.getByText("1 porción")).toBeDefined();
      expect(screen.getByText("2 porciones")).toBeDefined();
      expect(screen.getByText("10 porciones")).toBeDefined();

      // Insumos structure
      expect(screen.getAllByText("1 fijos").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("2 dinámicos")).toBeDefined();
    });

    it("renders semaphores correctly for each recipe margin", () => {
      render(<RecetasTable recetas={MOCK_RECETAS} />);

      const badgeRec1 = screen.getByTestId("margen-badge-rec-1");
      expect(badgeRec1.textContent).toBe("61.0%");
      expect(badgeRec1.className).toContain("amber");

      const badgeRec2 = screen.getByTestId("margen-badge-rec-2");
      expect(badgeRec2.textContent).toBe("73.3%");
      expect(badgeRec2.className).toContain("emerald");

      const badgeRec3 = screen.getByTestId("margen-badge-rec-sub-1");
      expect(badgeRec3.textContent).toBe("0.0%");
      expect(badgeRec3.className).toContain("rose");
    });

    it("triggers action callbacks when clicking view, edit, duplicate, and delete buttons", () => {
      const onView = vi.fn();
      const onEdit = vi.fn();
      const onDuplicate = vi.fn();
      const onDelete = vi.fn();

      render(
        <RecetasTable
          recetas={MOCK_RECETAS}
          onView={onView}
          onEdit={onEdit}
          onDuplicate={onDuplicate}
          onDelete={onDelete}
        />
      );

      fireEvent.click(screen.getByTestId("btn-view-receta-rec-1"));
      expect(onView).toHaveBeenCalledWith(MOCK_RECETAS[0]);

      fireEvent.click(screen.getByTestId("btn-edit-receta-rec-1"));
      expect(onEdit).toHaveBeenCalledWith(MOCK_RECETAS[0]);

      fireEvent.click(screen.getByTestId("btn-duplicate-receta-rec-1"));
      expect(onDuplicate).toHaveBeenCalledWith(MOCK_RECETAS[0]);

      fireEvent.click(screen.getByTestId("btn-delete-receta-rec-1"));
      expect(onDelete).toHaveBeenCalledWith(MOCK_RECETAS[0]);
    });
  });

  // 3. RecetasToolbar Component Tests
  describe("3. Barra de Herramientas RecetasToolbar", () => {
    it("renders search input, category selector, type filter pills, and action buttons", () => {
      const onSearchChange = vi.fn();
      const onSelectCategoria = vi.fn();
      const onSelectTipo = vi.fn();
      const onNewReceta = vi.fn();
      const onManageCategorias = vi.fn();

      render(
        <RecetasToolbar
          searchQuery=""
          onSearchChange={onSearchChange}
          selectedCategoriaId={null}
          onSelectCategoria={onSelectCategoria}
          categorias={MOCK_CATEGORIAS}
          tipoFiltro="todas"
          onSelectTipo={onSelectTipo}
          onNewReceta={onNewReceta}
          onManageCategorias={onManageCategorias}
        />
      );

      expect(screen.getByTestId("recetas-toolbar")).toBeDefined();
      expect(screen.getByTestId("recetas-search-input")).toBeDefined();
      expect(screen.getByTestId("recetas-categoria-select")).toBeDefined();
      expect(screen.getByTestId("btn-new-receta")).toBeDefined();
      expect(screen.getByTestId("btn-receta-categories")).toBeDefined();

      // Check segmented type pills
      expect(screen.getByTestId("recetas-tipo-todas")).toBeDefined();
      expect(screen.getByTestId("recetas-tipo-dinamicas")).toBeDefined();
      expect(screen.getByTestId("recetas-tipo-estaticas")).toBeDefined();
      expect(screen.getByTestId("recetas-tipo-subrecetas")).toBeDefined();
    });

    it("triggers callbacks on search input, category selection, and type switching", () => {
      const onSearchChange = vi.fn();
      const onSelectCategoria = vi.fn();
      const onSelectTipo = vi.fn();
      const onNewReceta = vi.fn();

      render(
        <RecetasToolbar
          searchQuery="lomo"
          onSearchChange={onSearchChange}
          selectedCategoriaId="cat-rec-carnes"
          onSelectCategoria={onSelectCategoria}
          categorias={MOCK_CATEGORIAS}
          tipoFiltro="todas"
          onSelectTipo={onSelectTipo}
          onNewReceta={onNewReceta}
        />
      );

      // Clear search button appears when query is present
      const clearBtn = screen.getByTestId("recetas-clear-search");
      fireEvent.click(clearBtn);
      expect(onSearchChange).toHaveBeenCalledWith("");

      // Select category
      const select = screen.getByTestId("recetas-categoria-select");
      fireEvent.change(select, { target: { value: "cat-rec-mar" } });
      expect(onSelectCategoria).toHaveBeenCalledWith("cat-rec-mar");

      // Switch type to dinamicas
      fireEvent.click(screen.getByTestId("recetas-tipo-dinamicas"));
      expect(onSelectTipo).toHaveBeenCalledWith("dinamicas");

      // Click + Nueva Receta
      fireEvent.click(screen.getByTestId("btn-new-receta"));
      expect(onNewReceta).toHaveBeenCalled();
    });
  });

  // 4. Mobile Card Component Tests
  describe("4. Tarjeta Mobile-First RecetaMobileCard", () => {
    it("renders mobile card with touch targets >= 44px and expands details on click", () => {
      const onView = vi.fn();
      const onEdit = vi.fn();

      render(
        <RecetaMobileCard
          receta={MOCK_RECETAS[0]!}
          onView={onView}
          onEdit={onEdit}
        />
      );

      expect(screen.getByTestId("receta-card-rec-1")).toBeDefined();
      expect(screen.getByTestId("card-badge-dinamica")).toBeDefined();
      expect(screen.getByTestId("card-margen-badge-rec-1")).toBeDefined();

      // Accordion toggle button
      const toggleBtn = screen.getByTestId("btn-toggle-expand-rec-1");
      expect(toggleBtn.className).toContain("min-h-[44px]");
      expect(screen.queryByText("Ingredientes Fijos (1):")).toBeNull();

      // Expand accordion
      fireEvent.click(toggleBtn);
      expect(screen.getByText("Ingredientes Fijos (1):")).toBeDefined();
      expect(screen.getByText("Lomo Vetado Angus")).toBeDefined();
      expect(screen.getByText("Grupos de Opciones (2):")).toBeDefined();

      // Action buttons
      const viewBtn = screen.getByTestId("card-btn-view-rec-1");
      expect(viewBtn.className).toContain("min-h-[44px]");
      fireEvent.click(viewBtn);
      expect(onView).toHaveBeenCalledWith(MOCK_RECETAS[0]);
    });
  });
});
