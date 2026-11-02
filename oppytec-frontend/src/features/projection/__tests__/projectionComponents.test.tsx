// oppytec-frontend/src/features/projection/__tests__/projectionComponents.test.tsx
import "@testing-library/jest-dom";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  ProyeccionCategoryFilter,
  ProyeccionExecutiveBanner,
  ProyeccionHeader,
  ProyeccionPagination,
  ProyeccionToolbar,
  PROJECTION_THEME_COLOR,
} from "../components";
import { MOCK_PROJECTION_METRICS_SUMMARY } from "../mockData";

describe("Feature Projection - Phase 4 UI Components", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("1. ProyeccionHeader", () => {
    it("debe renderizar el título, subtítulo e icono canónico con color ADN #10b981", () => {
      render(<ProyeccionHeader />);

      expect(screen.getByTestId("proyeccion-header")).toBeInTheDocument();
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Proyección");
      const subtitles = screen.getAllByText("Simulación de Disponibilidad y Alertas");
      expect(subtitles.length).toBeGreaterThan(0);
      expect(subtitles[0]).toBeInTheDocument();
      expect(PROJECTION_THEME_COLOR).toBe("#10b981");
    });
  });

  describe("2. ProyeccionToolbar", () => {
    it("debe manejar búsqueda de texto y botón de limpieza", () => {
      const handleSearchChange = vi.fn();
      const { rerender } = render(
        <ProyeccionToolbar
          searchTerm=""
          onSearchChange={handleSearchChange}
          horizonDays={30}
          onHorizonChange={vi.fn()}
          sortBy="urgency_desc"
          onSortChange={vi.fn()}
          pageSize={30}
          onPageSizeChange={vi.fn()}
        />
      );

      const input = screen.getByTestId("projection-search-input");
      expect(input).toBeInTheDocument();

      fireEvent.change(input, { target: { value: "pollo" } });
      expect(handleSearchChange).toHaveBeenCalledWith("pollo");

      // Con texto, debe mostrar botón de limpieza
      rerender(
        <ProyeccionToolbar
          searchTerm="pollo"
          onSearchChange={handleSearchChange}
          horizonDays={30}
          onHorizonChange={vi.fn()}
          sortBy="urgency_desc"
          onSortChange={vi.fn()}
          pageSize={30}
          onPageSizeChange={vi.fn()}
        />
      );

      const clearBtn = screen.getByTestId("projection-search-clear");
      expect(clearBtn).toBeInTheDocument();
      fireEvent.click(clearBtn);
      expect(handleSearchChange).toHaveBeenCalledWith("");
    });

    it("debe permitir cambiar el horizonte de días y ordenamiento", () => {
      const handleHorizonChange = vi.fn();
      const handleSortChange = vi.fn();

      render(
        <ProyeccionToolbar
          searchTerm=""
          onSearchChange={vi.fn()}
          horizonDays={30}
          onHorizonChange={handleHorizonChange}
          sortBy="urgency_desc"
          onSortChange={handleSortChange}
          pageSize={30}
          onPageSizeChange={vi.fn()}
        />
      );

      const horizonSelect = screen.getByTestId("projection-horizon-select");
      fireEvent.change(horizonSelect, { target: { value: "60" } });
      expect(handleHorizonChange).toHaveBeenCalledWith(60);

      const sortSelect = screen.getByTestId("projection-sort-select");
      fireEvent.change(sortSelect, { target: { value: "projected_asc" } });
      expect(handleSortChange).toHaveBeenCalledWith("projected_asc");
    });

    it("debe gestionar el toggle de categorías con badge numérico", () => {
      const handleToggleCategories = vi.fn();

      render(
        <ProyeccionToolbar
          searchTerm=""
          onSearchChange={vi.fn()}
          horizonDays={30}
          onHorizonChange={vi.fn()}
          sortBy="urgency_desc"
          onSortChange={vi.fn()}
          isCategoriesOpen={false}
          onToggleCategories={handleToggleCategories}
          activeCategoriesCount={3}
          pageSize={30}
          onPageSizeChange={vi.fn()}
        />
      );

      const toggleBtn = screen.getByTestId("projection-toggle-categories");
      expect(toggleBtn).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();

      fireEvent.click(toggleBtn);
      expect(handleToggleCategories).toHaveBeenCalledTimes(1);
    });

    it("debe soportar recálculo con feedback y selector de tamaño de página", () => {
      const handleRecompute = vi.fn();
      const handlePageSizeChange = vi.fn();

      const { rerender } = render(
        <ProyeccionToolbar
          searchTerm=""
          onSearchChange={vi.fn()}
          horizonDays={30}
          onHorizonChange={vi.fn()}
          sortBy="urgency_desc"
          onSortChange={vi.fn()}
          onRecompute={handleRecompute}
          isRecomputing={false}
          pageSize={30}
          onPageSizeChange={handlePageSizeChange}
        />
      );

      const recomputeBtn = screen.getByTestId("projection-recompute-btn");
      expect(recomputeBtn).toBeInTheDocument();
      fireEvent.click(recomputeBtn);
      expect(handleRecompute).toHaveBeenCalledTimes(1);

      // Cambiar filas por página
      const pageSizeSelect = screen.getByTestId("projection-pagesize-select");
      fireEvent.change(pageSizeSelect, { target: { value: "50" } });
      expect(handlePageSizeChange).toHaveBeenCalledWith(50);

      // Estado recomputing
      rerender(
        <ProyeccionToolbar
          searchTerm=""
          onSearchChange={vi.fn()}
          horizonDays={30}
          onHorizonChange={vi.fn()}
          sortBy="urgency_desc"
          onSortChange={vi.fn()}
          onRecompute={handleRecompute}
          isRecomputing={true}
          pageSize={50}
          onPageSizeChange={handlePageSizeChange}
        />
      );

      expect(screen.getByText("Calculando...")).toBeInTheDocument();
      expect(recomputeBtn).toBeDisabled();
    });
  });

  describe("3. ProyeccionCategoryFilter", () => {
    const mockCategories = [
      { id: 1, name: "Carnes y Aves", count: 12 },
      { id: 2, name: "Lácteos y Huevos", count: 8 },
      { id: 3, name: "Bebidas y Licores", count: 15 },
    ];

    it("debe renderizar píldoras con 'Todas' activa por defecto", () => {
      const handleSelect = vi.fn();

      render(
        <ProyeccionCategoryFilter
          categories={mockCategories}
          selectedCategoryId="all"
          onSelectCategory={handleSelect}
        />
      );

      expect(screen.getByTestId("category-pill-all")).toBeInTheDocument();
      expect(screen.getByTestId("category-pill-1")).toHaveTextContent("Carnes y Aves");
      expect(screen.getByText("12")).toBeInTheDocument();

      fireEvent.click(screen.getByTestId("category-pill-1"));
      expect(handleSelect).toHaveBeenCalledWith(1);
    });

    it("debe deseleccionar a 'all' si se vuelve a clickear la categoría activa", () => {
      const handleSelect = vi.fn();

      render(
        <ProyeccionCategoryFilter
          categories={mockCategories}
          selectedCategoryId={1}
          onSelectCategory={handleSelect}
        />
      );

      fireEvent.click(screen.getByTestId("category-pill-1"));
      expect(handleSelect).toHaveBeenCalledWith("all");
    });
  });

  describe("4. ProyeccionExecutiveBanner", () => {
    it("debe mostrar los 5 KPIs del horizonte con formateo y alertas", () => {
      const handleFilterClick = vi.fn();

      render(
        <ProyeccionExecutiveBanner
          metrics={MOCK_PROJECTION_METRICS_SUMMARY}
          horizonDays={30}
          isLoading={false}
          selectedStatus="all"
          onStatusFilterClick={handleFilterClick}
        />
      );

      expect(screen.getByTestId("kpi-card-total")).toBeInTheDocument();
      expect(screen.getByText("6")).toBeInTheDocument(); // total items

      expect(screen.getByTestId("kpi-card-critical")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-card-warning")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-card-coverage")).toBeInTheDocument();
      expect(screen.getByText("14.8")).toBeInTheDocument(); // avg coverage

      expect(screen.getByTestId("kpi-card-risk-value")).toBeInTheDocument();
      // Formateo CLP de 312500 -> $312.500
      expect(screen.getByText("$312.500")).toBeInTheDocument();

      // Click en tarjeta de críticos
      fireEvent.click(screen.getByTestId("kpi-card-critical"));
      expect(handleFilterClick).toHaveBeenCalledWith("critical");
    });

    it("debe renderizar skeletons de carga cuando isLoading=true", () => {
      render(
        <ProyeccionExecutiveBanner
          metrics={null}
          horizonDays={30}
          isLoading={true}
        />
      );

      expect(screen.getByTestId("proyeccion-executive-banner-skeleton")).toBeInTheDocument();
    });
  });

  describe("5. ProyeccionPagination", () => {
    it("debe renderizar resumen y deshabilitar botones de navegación en límites", () => {
      const handlePageChange = vi.fn();
      const handlePageSizeChange = vi.fn();

      const { rerender } = render(
        <ProyeccionPagination
          currentPage={1}
          totalItems={90}
          pageSize={30}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
        />
      );

      // Resumen visual: Mostrando 1 - 30 de 90 productos
      expect(screen.getByTestId("pagination-summary")).toHaveTextContent("Mostrando 1 - 30");
      expect(screen.getByTestId("pagination-summary")).toHaveTextContent("90 productos");

      // Botones primera y anterior deben estar deshabilitados en página 1
      expect(screen.getByTestId("pagination-first-page")).toBeDisabled();
      expect(screen.getByTestId("pagination-prev-page")).toBeDisabled();

      // Siguiente y última habilitados
      const nextBtn = screen.getByTestId("pagination-next-page");
      const lastBtn = screen.getByTestId("pagination-last-page");
      expect(nextBtn).toBeEnabled();
      expect(lastBtn).toBeEnabled();

      fireEvent.click(nextBtn);
      expect(handlePageChange).toHaveBeenCalledWith(2);

      fireEvent.click(lastBtn);
      expect(handlePageChange).toHaveBeenCalledWith(3);

      // Rerender en página 3 (última página)
      rerender(
        <ProyeccionPagination
          currentPage={3}
          totalItems={90}
          pageSize={30}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
        />
      );

      expect(screen.getByTestId("pagination-next-page")).toBeDisabled();
      expect(screen.getByTestId("pagination-last-page")).toBeDisabled();
      expect(screen.getByTestId("pagination-first-page")).toBeEnabled();
      expect(screen.getByTestId("pagination-prev-page")).toBeEnabled();
    });

    it("debe permitir cambiar el tamaño de página y resetear a página 1", () => {
      const handlePageChange = vi.fn();
      const handlePageSizeChange = vi.fn();

      render(
        <ProyeccionPagination
          currentPage={2}
          totalItems={120}
          pageSize={30}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
        />
      );

      const sizeSelect = screen.getByTestId("pagination-page-size-select");
      fireEvent.change(sizeSelect, { target: { value: "50" } });

      expect(handlePageSizeChange).toHaveBeenCalledWith(50);
      expect(handlePageChange).toHaveBeenCalledWith(1);
    });

    it("debe soportar clic en botón de número de página específico", () => {
      const handlePageChange = vi.fn();

      render(
        <ProyeccionPagination
          currentPage={1}
          totalItems={60}
          pageSize={20}
          onPageChange={handlePageChange}
          onPageSizeChange={vi.fn()}
        />
      );

      const page2Btn = screen.getByTestId("pagination-page-2");
      expect(page2Btn).toBeInTheDocument();

      fireEvent.click(page2Btn);
      expect(handlePageChange).toHaveBeenCalledWith(2);
    });
  });
});
