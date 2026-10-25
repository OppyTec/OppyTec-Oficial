// oppytec-frontend/src/features/inventory/__tests__/StockRegistroPage.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import * as httpClient from "@/shared/api/httpClient";
import {
  StockRegistroPage,
  StockActions,
  StockTable,
  StockRow,
  StockGroupRow,
  StockRowMobile,
  StockGroupRowMobile,
} from "../index";
import { MOCK_STOCK_ITEMS } from "../mockData";

// Mock de framer-motion para tests estables
vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<any>("framer-motion");
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
    motion: {
      div: ({ children, className, onClick, ...props }: any) => (
        <div className={className} onClick={onClick} {...props}>
          {children}
        </div>
      ),
    },
  };
});

function createWrapper() {
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

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <PermissionsProvider>{children}</PermissionsProvider>
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

describe("StockRegistroPage & Componentes Visuales de Stock (Fase 4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (_url, options) => {
      if (options?.fallbackData) {
        return {
          data: options.fallbackData,
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      return {
        data: MOCK_STOCK_ITEMS,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. StockActions Toolbar Tests
  // ==========================================================================
  describe("StockActions Toolbar Component", () => {
    it("renders desktop and mobile toolbars with selectors, sort, and action buttons", () => {
      const onToggleCategories = vi.fn();
      const onSortChange = vi.fn();
      const onOpenSolicitar = vi.fn();
      const onOpenMerma = vi.fn();
      const onOpenAdjustment = vi.fn();
      const onOpenReceive = vi.fn();

      render(
        <StockActions
          selectedAreaId="all"
          activeWarehouseId="bod-cocina-central"
          showCategories={true}
          onToggleCategories={onToggleCategories}
          sortOption="urgency"
          onSortChange={onSortChange}
          onOpenSolicitar={onOpenSolicitar}
          onOpenMerma={onOpenMerma}
          onOpenAdjustment={onOpenAdjustment}
          onOpenReceive={onOpenReceive}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId("stock-actions-toolbar")).toBeInTheDocument();
      expect(screen.getByTestId("stock-sort-trigger")).toBeInTheDocument();
      expect(screen.getByTestId("stock-toggle-categories")).toBeInTheDocument();
      expect(screen.getByTestId("stock-action-receive")).toBeInTheDocument();
      expect(screen.getByTestId("stock-action-solicitar")).toBeInTheDocument();
      expect(screen.getByTestId("stock-action-adjustment")).toBeInTheDocument();
      expect(screen.getByTestId("stock-action-merma")).toBeInTheDocument();

      // Trigger action
      fireEvent.click(screen.getByTestId("stock-action-merma"));
      expect(onOpenMerma).toHaveBeenCalledTimes(1);

      fireEvent.click(screen.getByTestId("stock-toggle-categories"));
      expect(onToggleCategories).toHaveBeenCalledTimes(1);
    });
  });

  // ==========================================================================
  // 2. StockRow y StockGroupRow Tests (Desktop)
  // ==========================================================================
  describe("StockRow & StockGroupRow (Desktop)", () => {
    it("renders StockRow with chromatic semaforo and product details", () => {
      const item = MOCK_STOCK_ITEMS[0]!; // Lomo Vetado (OPTIMO)
      const onOpenSolicitar = vi.fn();
      const onOpenTransfer = vi.fn();
      const onOpenMerma = vi.fn();

      render(
        <StockRow
          item={item}
          onOpenSolicitar={onOpenSolicitar}
          onOpenTransfer={onOpenTransfer}
          onOpenMerma={onOpenMerma}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId(`stock-row-${item.id}`)).toBeInTheDocument();
      expect(screen.getByText(item.nombre)).toBeInTheDocument();
      expect(screen.getByText(new RegExp(`SKU: ${item.sku}`))).toBeInTheDocument();
      expect(screen.getByTestId("badge-semaforo-optimo")).toBeInTheDocument();

      // Click on actions
      fireEvent.click(screen.getByTestId(`btn-solicitar-${item.id}`));
      expect(onOpenSolicitar).toHaveBeenCalledWith(item);

      fireEvent.click(screen.getByTestId(`btn-transferir-${item.id}`));
      expect(onOpenTransfer).toHaveBeenCalledWith(item);

      fireEvent.click(screen.getByTestId(`btn-merma-${item.id}`));
      expect(onOpenMerma).toHaveBeenCalledWith(item);
    });

    it("renders StockGroupRow for consolidated multi-warehouse products", () => {
      const items = MOCK_STOCK_ITEMS.slice(0, 2);
      const group = {
        productoId: 101,
        nombre: "Lomo Vetado Angus Premium",
        sku: "CAR-VAC-001",
        categoria: "Carnes Vacuno",
        totalStock: 12.5,
        totalMinimo: 15,
        unidadMedida: "kg",
        totalValorizado: 206250,
        items,
      };

      render(<StockGroupRow group={group} />, { wrapper: createWrapper() });

      expect(screen.getByTestId(`stock-group-row-${group.productoId}`)).toBeInTheDocument();
      expect(screen.getByText("Lomo Vetado Angus Premium")).toBeInTheDocument();
      expect(screen.getByText("2 bodegas")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 3. StockRowMobile & StockGroupRowMobile Tests
  // ==========================================================================
  describe("StockRowMobile & StockGroupRowMobile (Mobile-First)", () => {
    it("renders mobile card with touch targets and formatted metrics", () => {
      const item = MOCK_STOCK_ITEMS[2]!; // Pechuga de Pollo King (MINIMO)
      const onOpenSolicitar = vi.fn();

      render(
        <StockRowMobile item={item} onOpenSolicitar={onOpenSolicitar} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId(`stock-row-mobile-${item.id}`)).toBeInTheDocument();
      expect(screen.getByText(item.nombre)).toBeInTheDocument();
      expect(screen.getByText("Bajo Mín")).toBeInTheDocument();

      const btnPedir = screen.getByTestId(`btn-mobile-solicitar-${item.id}`);
      expect(btnPedir.className).toContain("min-h-[44px]");
      fireEvent.click(btnPedir);
      expect(onOpenSolicitar).toHaveBeenCalledWith(item);
    });

    it("renders mobile group card with accordion functionality", () => {
      const group = {
        productoId: 102,
        nombre: "Filete de Salmón Fresco",
        sku: "PES-SAL-002",
        categoria: "Pescados y Mariscos",
        totalStock: 6.0,
        totalMinimo: 8,
        unidadMedida: "kg",
        totalValorizado: 99000,
        items: [MOCK_STOCK_ITEMS[1]!],
      };

      render(<StockGroupRowMobile group={group} />, { wrapper: createWrapper() });

      expect(screen.getByTestId(`stock-group-mobile-${group.productoId}`)).toBeInTheDocument();
      expect(screen.getByText("Filete de Salmón Fresco")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 4. StockTable Component Tests
  // ==========================================================================
  describe("StockTable Component", () => {
    it("renders categorized view with group headers and empty state gracefully", () => {
      const { rerender } = render(
        <StockTable items={MOCK_STOCK_ITEMS} showCategories={true} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId("stock-table-categorized")).toBeInTheDocument();

      // Empty state
      rerender(<StockTable items={[]} showCategories={true} />);
      expect(screen.getByTestId("stock-table-empty")).toBeInTheDocument();
      expect(screen.getByText("Sin registros en el inventario actual")).toBeInTheDocument();
    });

    it("renders flat view when showCategories is false", () => {
      render(
        <StockTable items={MOCK_STOCK_ITEMS} showCategories={false} viewMode="plano" />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId("stock-table-flat")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 5. StockRegistroPage Full Integration Tests
  // ==========================================================================
  describe("StockRegistroPage Full Integration", () => {
    it("renders complete page with SectionHeader, search bar, and TablePagination", async () => {
      render(<StockRegistroPage />, { wrapper: createWrapper() });

      // Contenedor principal
      expect(screen.getByTestId("stock-registro-container")).toBeInTheDocument();

      // SectionHeader animado
      expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
      expect(screen.getAllByText("Terminal de Control e Inventario")[0]).toBeInTheDocument();

      // Toolbar de acciones
      expect(screen.getByTestId("stock-actions-toolbar")).toBeInTheDocument();

      // Buscador
      expect(screen.getByTestId("stock-search-input")).toBeInTheDocument();

      // Esperar a que el spinner desaparezca y cargue la tabla
      await waitFor(() => {
        expect(screen.queryByTestId("stock-loading-spinner")).not.toBeInTheDocument();
      });

      // Tabla y Paginación
      await waitFor(() => {
        expect(screen.getByTestId("table-pagination")).toBeInTheDocument();
      });
    });

    it("filters stock items interactively with the search input", async () => {
      render(<StockRegistroPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.queryByTestId("stock-loading-spinner")).not.toBeInTheDocument();
      });

      const searchInput = screen.getByTestId("stock-search-input") as HTMLInputElement;

      // Buscar "Lomo"
      fireEvent.change(searchInput, { target: { value: "Lomo" } });
      expect(searchInput.value).toBe("Lomo");

      await waitFor(() => {
        expect(screen.getAllByText(/Lomo Vetado Angus Premium/i)[0]).toBeInTheDocument();
      });

      // Limpiar búsqueda con el botón X
      const clearBtn = screen.getByTestId("stock-search-clear");
      fireEvent.click(clearBtn);
      expect(searchInput.value).toBe("");
    });

    it("filters items when clicking category badges", async () => {
      render(<StockRegistroPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.queryByTestId("stock-loading-spinner")).not.toBeInTheDocument();
      });

      const catBadge = await screen.findByTestId("category-badge-Carnes y Aves");
      expect(catBadge).toBeInTheDocument();

      fireEvent.click(catBadge);
      await waitFor(() => {
        expect(screen.getAllByText(/Lomo Vetado Angus Premium/i)[0]).toBeInTheDocument();
      });

      // Regresar a 'Todas las Categorías'
      const allBadge = screen.getByTestId("category-badge-all");
      fireEvent.click(allBadge);
    });

    it("opens and handles action dialogs (Merma, Transfer, Adjustment)", async () => {
      render(<StockRegistroPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.queryByTestId("stock-loading-spinner")).not.toBeInTheDocument();
      });

      // Abrir modal Merma desde toolbar
      const mermaBtn = screen.getByTestId("stock-action-merma");
      fireEvent.click(mermaBtn);

      await waitFor(() => {
        expect(screen.getByTestId("dialog-merma-content")).toBeInTheDocument();
      });

      const confirmMermaBtn = screen.getByTestId("btn-confirm-merma");
      fireEvent.click(confirmMermaBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("dialog-merma-content")).not.toBeInTheDocument();
      });

      // Abrir modal Ajuste desde toolbar
      const adjustmentBtn = screen.getByTestId("stock-action-adjustment");
      fireEvent.click(adjustmentBtn);

      await waitFor(() => {
        expect(screen.getByTestId("dialog-adjustment-content")).toBeInTheDocument();
      });

      const confirmAdjustmentBtn = screen.getByTestId("btn-confirm-adjustment");
      fireEvent.click(confirmAdjustmentBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("dialog-adjustment-content")).not.toBeInTheDocument();
      });
    });

    it("toggles categories visibility", async () => {
      render(<StockRegistroPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.queryByTestId("stock-loading-spinner")).not.toBeInTheDocument();
      });

      const allBadge = await screen.findByTestId("category-badge-all");
      expect(allBadge).toBeInTheDocument();

      const toggleCategoriesBtn = screen.getByTestId("stock-toggle-categories");

      // Click to hide categories
      fireEvent.click(toggleCategoriesBtn);
      expect(screen.queryByTestId("category-badge-all")).not.toBeInTheDocument();

      // Click to show categories again
      fireEvent.click(toggleCategoriesBtn);
      expect(screen.getByTestId("category-badge-all")).toBeInTheDocument();
    });
  });
});
