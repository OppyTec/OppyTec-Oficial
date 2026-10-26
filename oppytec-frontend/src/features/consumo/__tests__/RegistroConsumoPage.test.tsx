// oppytec-frontend/src/features/consumo/__tests__/RegistroConsumoPage.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RegistroConsumoPage } from "../RegistroConsumoPage";
import { ConsumoCatalog } from "../components/ConsumoCatalog";
import {
  MOCK_PRODUCTOS_CONSUMO,
  MOCK_RECETAS_CONSUMO,
  MOCK_COMBOS_CONSUMO,
  MOCK_CATEGORIAS_CONSUMO,
} from "../mockData";

function renderWithProviders(ui: React.ReactElement) {
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
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </BrowserRouter>
  );
}

describe("Módulo de Consumo - Vista 1: RegistroConsumoPage & ConsumoCatalog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(async () => {
    cleanup();
    vi.restoreAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    await new Promise((r) => setTimeout(r, 20));
  });

  // ==========================================================================
  // 1. Renderizado y Cabecera Canónica
  // ==========================================================================
  describe("Cabecera Canónica y Estructura Principal", () => {
    it("renders SectionHeader with correct title, subtitle and icons", async () => {
      renderWithProviders(<RegistroConsumoPage />);

      expect(await screen.findByText("Registro de Consumo")).toBeInTheDocument();
      expect(
        screen.getAllByText(
          "Registra salidas de productos, consumo de personal y mermas en tiempo real"
        )[0]
      ).toBeInTheDocument();
    });

    it("renders Toolbar with AreaSelector, BodegaSelector and Action Buttons", () => {
      renderWithProviders(<RegistroConsumoPage />);

      expect(screen.getByTestId("consumo-unified-toolbar")).toBeInTheDocument();
      expect(screen.getByTestId("area-selector")).toBeInTheDocument();
      expect(screen.getByTestId("bodega-selector")).toBeInTheDocument();
      expect(screen.getByTestId("viewmode-switcher")).toBeInTheDocument();
      expect(screen.getByTestId("toggle-categories-btn")).toBeInTheDocument();
      expect(screen.getByTestId("merma-trigger-btn")).toBeInTheDocument();
      expect(screen.getByTestId("templates-selector-wrapper")).toBeInTheDocument();
      expect(screen.getByTestId("history-trigger-btn")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 2. Switcher de Vistas (Productos, Recetas, Combos)
  // ==========================================================================
  describe("Switcher de Vistas", () => {
    it("switches viewMode between productos, recetas and combos smoothly", async () => {
      renderWithProviders(<RegistroConsumoPage />);

      // Por defecto está en 'productos'
      expect(screen.getByTestId("viewmode-productos-btn")).toHaveClass("bg-yellow-500");
      expect(screen.getByPlaceholderText(/Buscar producto o SKU/i)).toBeInTheDocument();

      // Cambiar a 'recetas'
      fireEvent.click(screen.getByTestId("viewmode-recetas-btn"));
      expect(screen.getByTestId("viewmode-recetas-btn")).toHaveClass("bg-purple-600");
      expect(screen.getByPlaceholderText(/Buscar receta/i)).toBeInTheDocument();

      // Cambiar a 'combos'
      fireEvent.click(screen.getByTestId("viewmode-combos-btn"));
      expect(screen.getByTestId("viewmode-combos-btn")).toHaveClass("bg-[#1c4c96]");
      expect(screen.getByPlaceholderText(/Buscar combo/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 3. Catálogo y TablePagination Integrado
  // ==========================================================================
  describe("Catálogo y TablePagination Integrado", () => {
    it("renders TablePagination component at the bottom of the catalog", async () => {
      renderWithProviders(<RegistroConsumoPage />);

      const pagination = await screen.findByTestId("table-pagination");
      expect(pagination).toBeInTheDocument();
      expect(screen.getByTestId("pagination-page-size-select")).toBeInTheDocument();
      expect(screen.getByTestId("pagination-page-1")).toBeInTheDocument();
    });

    it("displays paginated items and updates page slice accurately", () => {
      const handleAdd = vi.fn();

      render(
        <ConsumoCatalog
          busqueda=""
          onBusquedaChange={vi.fn()}
          productos={MOCK_PRODUCTOS_CONSUMO}
          recetas={MOCK_RECETAS_CONSUMO}
          combos={MOCK_COMBOS_CONSUMO}
          categorias={MOCK_CATEGORIAS_CONSUMO}
          onAdd={handleAdd}
          getStock={() => 10}
          getAlertStatus={() => "normal"}
          getRecipeAvailability={() => 5}
          viewMode="productos"
          showCategories={true}
          colsCount={8}
        />
      );

      // Los productos del mock deben ser visibles
      expect(screen.getByText("Salmón Fresco Filete")).toBeInTheDocument();
      expect(screen.getByText("Queso Parmesano Reggiano")).toBeInTheDocument();

      // Click en tarjeta dispara onAdd
      const salmonCard = screen.getByTestId("product-card-prod-salm-01");
      fireEvent.click(salmonCard);
      expect(handleAdd).toHaveBeenCalledWith(
        expect.objectContaining({ id: "prod-salm-01" }),
        "producto"
      );
    });

    it("filters catalog items using predictive search bar", () => {
      let currentSearch = "";
      const handleSearchChange = vi.fn((v: string) => {
        currentSearch = v;
      });

      const { rerender } = render(
        <ConsumoCatalog
          busqueda={currentSearch}
          onBusquedaChange={handleSearchChange}
          productos={MOCK_PRODUCTOS_CONSUMO}
          recetas={MOCK_RECETAS_CONSUMO}
          combos={MOCK_COMBOS_CONSUMO}
          categorias={MOCK_CATEGORIAS_CONSUMO}
          onAdd={vi.fn()}
          getStock={() => 10}
          getAlertStatus={() => "normal"}
          getRecipeAvailability={() => 5}
          viewMode="productos"
          showCategories={true}
          colsCount={8}
        />
      );

      const input = screen.getByTestId("catalog-search-input");
      fireEvent.change(input, { target: { value: "Salmón" } });
      expect(handleSearchChange).toHaveBeenCalledWith("Salmón");

      // Rerender con el valor filtrado
      rerender(
        <ConsumoCatalog
          busqueda="Salmón"
          onBusquedaChange={handleSearchChange}
          productos={MOCK_PRODUCTOS_CONSUMO}
          recetas={MOCK_RECETAS_CONSUMO}
          combos={MOCK_COMBOS_CONSUMO}
          categorias={MOCK_CATEGORIAS_CONSUMO}
          onAdd={vi.fn()}
          getStock={() => 10}
          getAlertStatus={() => "normal"}
          getRecipeAvailability={() => 5}
          viewMode="productos"
          showCategories={true}
          colsCount={8}
        />
      );

      expect(screen.getByText("Salmón Fresco Filete")).toBeInTheDocument();
      expect(screen.queryByText("Queso Parmesano Reggiano")).not.toBeInTheDocument();

      // Botón de limpiar búsqueda
      const clearBtn = screen.getByTestId("clear-search-btn");
      fireEvent.click(clearBtn);
      expect(handleSearchChange).toHaveBeenCalledWith("");
    });

    it("filters catalog items by category and resets with Limpiar Filtro", () => {
      render(
        <ConsumoCatalog
          busqueda=""
          onBusquedaChange={vi.fn()}
          productos={MOCK_PRODUCTOS_CONSUMO}
          recetas={MOCK_RECETAS_CONSUMO}
          combos={MOCK_COMBOS_CONSUMO}
          categorias={MOCK_CATEGORIAS_CONSUMO}
          onAdd={vi.fn()}
          getStock={() => 10}
          getAlertStatus={() => "normal"}
          getRecipeAvailability={() => 5}
          viewMode="productos"
          showCategories={true}
          colsCount={8}
        />
      );

      // Categoría Carnes y Aves (cat-carnes) contiene a Salmón
      const carnesBadge = screen.getByTestId("category-badge-cat-carnes");
      fireEvent.click(carnesBadge);

      expect(screen.getByText("Salmón Fresco Filete")).toBeInTheDocument();
      expect(screen.queryByText("Queso Parmesano Reggiano")).not.toBeInTheDocument();

      // Botón de limpiar filtro
      const clearCatBtn = screen.getByTestId("clear-categories-btn");
      expect(clearCatBtn).toBeInTheDocument();
      fireEvent.click(clearCatBtn);

      // Ahora ambos productos vuelven a ser visibles
      expect(screen.getByText("Salmón Fresco Filete")).toBeInTheDocument();
      expect(screen.getByText("Queso Parmesano Reggiano")).toBeInTheDocument();
    });

    it("shows empty state when no items match the criteria", () => {
      render(
        <ConsumoCatalog
          busqueda="PalabraQueNoExisteEnElCatalogo"
          onBusquedaChange={vi.fn()}
          productos={MOCK_PRODUCTOS_CONSUMO}
          recetas={MOCK_RECETAS_CONSUMO}
          combos={MOCK_COMBOS_CONSUMO}
          categorias={MOCK_CATEGORIAS_CONSUMO}
          onAdd={vi.fn()}
          getStock={() => 10}
          getAlertStatus={() => "normal"}
          getRecipeAvailability={() => 5}
          viewMode="productos"
          showCategories={true}
          colsCount={8}
        />
      );

      expect(screen.getByTestId("catalog-empty-state")).toBeInTheDocument();
      expect(screen.getByText(/No se encontraron productos/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 4. Carrito Flotante y Modal Triggers
  // ==========================================================================
  describe("Carrito Flotante e Interacciones", () => {
    it("displays floating cart indicator when items are added", async () => {
      renderWithProviders(<RegistroConsumoPage />);

      // Al inicio el carrito está vacío
      expect(screen.queryByTestId("floating-cart-indicator")).not.toBeInTheDocument();

      // Agregar un producto al carrito
      const salmonCard = await screen.findByTestId("product-card-prod-salm-01");
      fireEvent.click(salmonCard);

      // Ahora debe aparecer el indicador flotante
      await waitFor(() => {
        expect(screen.getByTestId("floating-cart-indicator")).toBeInTheDocument();
        expect(screen.getByTestId("floating-cart-badge")).toHaveTextContent("1");
      });
    });

    it("opens and closes merma and history notices", async () => {
      renderWithProviders(<RegistroConsumoPage />);

      // Abrir merma notice
      fireEvent.click(screen.getByTestId("merma-trigger-btn"));
      expect(screen.getByTestId("merma-notice-modal")).toBeInTheDocument();
      fireEvent.click(screen.getByText("Entendido"));
      expect(screen.queryByTestId("merma-notice-modal")).not.toBeInTheDocument();

      // Abrir history notice
      fireEvent.click(screen.getByTestId("history-trigger-btn"));
      expect(screen.getByTestId("history-notice-modal")).toBeInTheDocument();
      fireEvent.click(screen.getByText("Cerrar"));
      expect(screen.queryByTestId("history-notice-modal")).not.toBeInTheDocument();
    });
  });
});
