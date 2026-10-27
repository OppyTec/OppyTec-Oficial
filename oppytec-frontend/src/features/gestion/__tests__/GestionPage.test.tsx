// oppytec-frontend/src/features/gestion/__tests__/GestionPage.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, useSearchParams } from "react-router-dom";
import { GestionPage } from "../GestionPage";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { applyDocumentTheme } from "@/shared/hooks/useTheme";
import type { OppyTecTheme } from "@/shared/components/ui/designTokens";
import * as httpClient from "@/shared/api/httpClient";

// Mock API Client to guarantee zero blank screens and offline fallback predictability
vi.mock("@/shared/api/httpClient", async () => {
  const actual = await vi.importActual<any>("@/shared/api/httpClient");
  return {
    ...actual,
    apiRequest: vi.fn().mockRejectedValue(new Error("Offline in test harness")),
  };
});

// Mock framer-motion AnimatePresence to avoid jsdom timing or exit layout delays
vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<any>("framer-motion");
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
  };
});

function openDropdown(trigger: HTMLElement) {
  fireEvent.pointerDown(trigger, { button: 0, ctrlKey: false });
  fireEvent.click(trigger);
  fireEvent.keyDown(trigger, { key: "ArrowDown" });
}

function renderGestionPage(route = "/gestion?tab=productos") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <PermissionsProvider>
          <GestionPage />
        </PermissionsProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Fase 8: GestionPage Integration & E2E Suite", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    (httpClient.apiRequest as any).mockRejectedValue(new Error("Offline in test harness"));
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. Full Mounting under MemoryRouter (?tab=productos) & Structural Anatomy
  // ==========================================================================
  describe("1. Montaje Completo bajo MemoryRouter y Renderizado Estructural", () => {
    it("renders GestionPage container when mounted with query param ?tab=productos", async () => {
      renderGestionPage("/gestion?tab=productos");

      const container = screen.getByTestId("gestion-page");
      expect(container).toBeDefined();
      expect(container.className).toContain("max-w-7xl");
      expect(container.className).toContain("space-y-6");

      const header = container.querySelector("header");
      expect(header).toBeDefined();
      expect(header?.className).toContain("justify-center");

      await screen.findByTestId("product-table-root");
      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/Gestión/i);
      });
      expect(screen.getAllByText("Catálogo de productos e insumos")[0]).toBeDefined();
    });

    it("renders unified toolbar, search bar, and category carousel", async () => {
      renderGestionPage();

      // Header and Section
      expect(screen.getByTestId("toolbar-gestion")).toBeDefined();
      expect(screen.getByTestId("gestion-search-input")).toBeDefined();

      // Wait for async catalog loading
      await screen.findByTestId("categoria-seccion");

      // Categories should be present in carousel
      expect(screen.getByTestId("category-badge-cat-carnes")).toBeDefined();
      expect(screen.getByTestId("category-badge-cat-pescados")).toBeDefined();
      expect(screen.getByTestId("category-badge-cat-lacteos")).toBeDefined();
    });

    it("renders multidimensional product table with initial catalog items", async () => {
      renderGestionPage();

      // Wait for async catalog loading
      const tableRoot = await screen.findByTestId("product-table-root");
      expect(tableRoot).toBeDefined();

      // Initial products from offline dataset should be visible
      expect(screen.getByText("Lomo Vetado Angus Premium")).toBeDefined();
      expect(screen.getByText("Salmón Atlántico Fresco")).toBeDefined();
      expect(screen.getByText("Leche Entera Colun 1L")).toBeDefined();
    });
  });

  // ==========================================================================
  // 2. Interactive Filtering (Search & Category Carousel)
  // ==========================================================================
  describe("2. Interacción de Filtrado (Búsqueda por Texto y Carrusel de Categorías)", () => {
    it("filters products reactively by search input query with debounce", async () => {
      renderGestionPage();

      await screen.findByTestId("product-table-root");

      const searchInput = screen.getByTestId("gestion-search-input");
      fireEvent.change(searchInput, { target: { value: "Salmón" } });

      await waitFor(
        () => {
          expect(screen.getByText("Salmón Atlántico Fresco")).toBeDefined();
          expect(screen.queryByText("Lomo Vetado Angus Premium")).toBeNull();
          expect(screen.queryByText("Leche Entera Colun 1L")).toBeNull();
        },
        { timeout: 1500 }
      );

      // Clear search button should appear and reset query
      const clearBtn = screen.getByTestId("gestion-clear-search");
      expect(clearBtn).toBeDefined();
      fireEvent.click(clearBtn);

      await waitFor(() => {
        expect(screen.getByText("Lomo Vetado Angus Premium")).toBeDefined();
        expect(screen.getByText("Salmón Atlántico Fresco")).toBeDefined();
      });
    });

    it("filters products when toggling a category badge in the carousel", async () => {
      renderGestionPage();

      await screen.findByTestId("product-table-root");

      const carnesBadge = await screen.findByTestId("category-badge-cat-carnes");
      fireEvent.click(carnesBadge);

      await waitFor(() => {
        expect(screen.getByText("Lomo Vetado Angus Premium")).toBeDefined();
        expect(screen.queryByText("Salmón Atlántico Fresco")).toBeNull();
        expect(screen.queryByText("Leche Entera Colun 1L")).toBeNull();
      });

      // Toggle off category badge
      fireEvent.click(carnesBadge);

      await waitFor(() => {
        expect(screen.getByText("Lomo Vetado Angus Premium")).toBeDefined();
        expect(screen.getByText("Salmón Atlántico Fresco")).toBeDefined();
        expect(screen.getByText("Leche Entera Colun 1L")).toBeDefined();
      });
    });

    it("shows empty state when no products match search query and allows resetting", async () => {
      renderGestionPage();

      await screen.findByTestId("product-table-root");

      const searchInput = screen.getByTestId("gestion-search-input");
      fireEvent.change(searchInput, { target: { value: "Trompeta Inexistente 9999" } });

      await waitFor(() => {
        expect(screen.getByTestId("gestion-empty-state")).toBeDefined();
        expect(screen.getByText("No se encontraron productos")).toBeDefined();
        expect(screen.getByText("Limpiar filtros")).toBeDefined();
      });

      // Click clear filters button
      fireEvent.click(screen.getByText("Limpiar filtros"));

      await waitFor(() => {
        expect(screen.queryByTestId("gestion-empty-state")).toBeNull();
        expect(screen.getByText("Lomo Vetado Angus Premium")).toBeDefined();
      });
    });
  });

  // ==========================================================================
  // 3. Modales de Ingesta Inteligente (Excel IA y Factura IA)
  // ==========================================================================
  describe("3. Apertura e Interacción con Modales Excel IA y Factura IA", () => {
    it("opens ExcelImportModal via Toolbar Actions dropdown and allows closing it", async () => {
      renderGestionPage();

      await screen.findByTestId("product-table-root");

      // Open Actions dropdown
      const actionsDropdownTrigger = screen.getByTestId("toolbar-actions-dropdown-trigger");
      openDropdown(actionsDropdownTrigger);

      // Click Importar Excel (IA) option
      const excelItem = await screen.findByTestId("btn-action-import-excel");
      expect(excelItem).toBeDefined();
      fireEvent.click(excelItem);

      // Verify ExcelImportModal is mounted
      await waitFor(() => {
        expect(screen.getByTestId("excel-import-modal")).toBeDefined();
      });

      // Close modal
      const cancelBtn = screen.getByTestId("btn-cancel-excel-import");
      fireEvent.click(cancelBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("excel-import-modal")).toBeNull();
      });
    });

    it("opens FacturaImportModal via Toolbar Actions dropdown and allows closing it", async () => {
      renderGestionPage();

      await screen.findByTestId("product-table-root");

      // Open Actions dropdown
      const actionsDropdownTrigger = screen.getByTestId("toolbar-actions-dropdown-trigger");
      openDropdown(actionsDropdownTrigger);

      // Click Cargar Factura (IA) option
      const facturaItem = await screen.findByTestId("btn-action-import-factura");
      expect(facturaItem).toBeDefined();
      fireEvent.click(facturaItem);

      // Verify FacturaImportModal is mounted
      await waitFor(() => {
        expect(screen.getByTestId("factura-import-modal")).toBeDefined();
      });

      // Close modal
      const cancelBtn = screen.getByTestId("btn-cancel-factura-import");
      fireEvent.click(cancelBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("factura-import-modal")).toBeNull();
      });
    });

    it("transitions from ProductoWizardDialog tabs directly to Excel IA and Factura IA modals", async () => {
      renderGestionPage();

      await screen.findByTestId("product-table-root");

      // Open new product wizard
      const newProductBtn = screen.getByTestId("toolbar-btn-new-product");
      fireEvent.click(newProductBtn);

      await waitFor(() => {
        expect(screen.getByTestId("producto-wizard-dialog")).toBeDefined();
      });

      // Click Excel channel tab in wizard header
      const channelExcelBtn = screen.getByTestId("channel-excel");
      fireEvent.click(channelExcelBtn);

      // Wizard should close and Excel modal should open
      await waitFor(() => {
        expect(screen.queryByTestId("producto-wizard-dialog")).toBeNull();
        expect(screen.getByTestId("excel-import-modal")).toBeDefined();
      });

      // Close Excel modal
      fireEvent.click(screen.getByTestId("btn-cancel-excel-import"));
      await waitFor(() => {
        expect(screen.queryByTestId("excel-import-modal")).toBeNull();
      });

      // Re-open wizard and test Invoice channel tab
      fireEvent.click(screen.getByTestId("toolbar-btn-new-product"));
      await waitFor(() => {
        expect(screen.getByTestId("producto-wizard-dialog")).toBeDefined();
      });

      const channelInvoiceBtn = screen.getByTestId("channel-invoice");
      fireEvent.click(channelInvoiceBtn);

      // Wizard should close and Factura modal should open
      await waitFor(() => {
        expect(screen.queryByTestId("producto-wizard-dialog")).toBeNull();
        expect(screen.getByTestId("factura-import-modal")).toBeDefined();
      });

      // Close Factura modal
      fireEvent.click(screen.getByTestId("btn-cancel-factura-import"));
      await waitFor(() => {
        expect(screen.queryByTestId("factura-import-modal")).toBeNull();
      });
    });
  });

  // ==========================================================================
  // 4. Resilience and Error-Free Rendering across 3 Themes
  // ==========================================================================
  describe("4. Resiliencia y Renderizado en los 3 Temas (light, dark, ocean-blue)", () => {
    const OFFICIAL_THEMES: OppyTecTheme[] = ["light", "dark", "ocean-blue"];

    OFFICIAL_THEMES.forEach((theme) => {
      it(`renders GestionPage cleanly under "${theme}" theme without blank screens or errors`, async () => {
        applyDocumentTheme(theme);

        // Verify HTML document reflects active theme token
        expect(document.documentElement.getAttribute("data-theme")).toBe(theme);
        expect(document.documentElement.classList.contains(theme)).toBe(true);

        renderGestionPage();

        expect(screen.getByTestId("gestion-page")).toBeDefined();
        expect(screen.getByTestId("toolbar-gestion")).toBeDefined();
        await screen.findByTestId("product-table-root");
        expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/Gestión/i);
      });
    });
  });

  // ==========================================================================
  // 5. Navegación Integrada de Tabs y Eliminación de Grupos-Opciones
  // ==========================================================================
  describe("5. Navegación Integrada de Tabs y Eliminación de Grupos-Opciones", () => {
    it("renders the 3 main navigation tabs and ensures grupos-opciones is NOT present", async () => {
      renderGestionPage("/gestion?tab=productos");

      expect(screen.getByTestId("gestion-tab-productos")).toBeDefined();
      expect(screen.getByTestId("gestion-tab-recetas")).toBeDefined();
      expect(screen.getByTestId("gestion-tab-combos")).toBeDefined();

      // Ensure orphan tab is completely absent
      expect(screen.queryByTestId("gestion-tab-grupos-opciones")).toBeNull();
      expect(screen.queryByRole("tab", { name: /grupos.*opciones/i })).toBeNull();
    });

    it("mounts directly under /gestion?tab=recetas and displays Recetas view and header", async () => {
      renderGestionPage("/gestion?tab=recetas");

      expect(screen.getByTestId("recetas-view-root")).toBeDefined();
      expect(screen.getByTestId("recetas-toolbar")).toBeDefined();
      await screen.findByTestId("recetas-table-root");

      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/Recetas/i);
      });

      // Products table should not be in the DOM
      expect(screen.queryByTestId("product-table-root")).toBeNull();
    });

    it("mounts directly under /gestion?tab=combos and displays Combos view and header", async () => {
      renderGestionPage("/gestion?tab=combos");

      expect(screen.getByTestId("combos-view-root")).toBeDefined();
      expect(screen.getByTestId("combos-toolbar")).toBeDefined();
      await screen.findByTestId("combos-table-root");

      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/Combos/i);
      });

      // Products table should not be in the DOM
      expect(screen.queryByTestId("product-table-root")).toBeNull();
    });

    it("switches reactively between tabs on user click", async () => {
      renderGestionPage("/gestion?tab=productos");

      // Initially on products tab
      await screen.findByTestId("product-table-root");

      // Click Recetas tab
      const recetasTab = screen.getByTestId("gestion-tab-recetas");
      fireEvent.click(recetasTab);

      await screen.findByTestId("recetas-view-root");
      await screen.findByTestId("recetas-table-root");
      expect(screen.queryByTestId("product-table-root")).toBeNull();

      // Click Combos tab
      const combosTab = screen.getByTestId("gestion-tab-combos");
      fireEvent.click(combosTab);

      await screen.findByTestId("combos-view-root");
      await screen.findByTestId("combos-table-root");
      expect(screen.queryByTestId("recetas-view-root")).toBeNull();

      // Click back to Productos tab
      const productosTab = screen.getByTestId("gestion-tab-productos");
      fireEvent.click(productosTab);

      await screen.findByTestId("product-table-root");
      expect(screen.queryByTestId("combos-view-root")).toBeNull();
    });

    it("falls back to productos when loaded with orphan query /gestion?tab=grupos-opciones", async () => {
      renderGestionPage("/gestion?tab=grupos-opciones");

      await screen.findByTestId("product-table-root");
      expect(screen.getByTestId("gestion-tab-productos")).toBeDefined();
      expect(screen.queryByTestId("gestion-tab-grupos-opciones")).toBeNull();
    });

    it("does not trigger React Error #310 when transitioning between ?tab=pedidos and other tabs", async () => {
      function TestRouteController() {
        const [, setSearchParams] = useSearchParams();
        return (
          <div data-testid="route-controller">
            <button data-testid="nav-pedidos" onClick={() => setSearchParams({ tab: "pedidos" })}>Pedidos</button>
            <button data-testid="nav-recetas" onClick={() => setSearchParams({ tab: "recetas" })}>Recetas</button>
            <button data-testid="nav-combos" onClick={() => setSearchParams({ tab: "combos" })}>Combos</button>
            <button data-testid="nav-productos" onClick={() => setSearchParams({ tab: "productos" })}>Productos</button>
          </div>
        );
      }

      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: 0 } },
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={["/gestion?tab=pedidos"]}>
            <PermissionsProvider>
              <TestRouteController />
              <GestionPage />
            </PermissionsProvider>
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Initially on pedidos
      expect(screen.getByTestId("gestion-page-pedidos")).toBeDefined();
      expect(screen.getByText("Gestión de Pedidos y Abastecimiento")).toBeDefined();

      // Transition to recetas (would fail with React Error #310 if early return existed)
      fireEvent.click(screen.getByTestId("nav-recetas"));
      expect(await screen.findByTestId("recetas-view-root")).toBeDefined();
      expect(screen.queryByTestId("gestion-page-pedidos")).toBeNull();

      // Transition to combos
      fireEvent.click(screen.getByTestId("nav-combos"));
      expect(await screen.findByTestId("combos-view-root")).toBeDefined();

      // Transition back to pedidos
      fireEvent.click(screen.getByTestId("nav-pedidos"));
      expect(await screen.findByTestId("gestion-page-pedidos")).toBeDefined();

      // Transition to productos
      fireEvent.click(screen.getByTestId("nav-productos"));
      expect(await screen.findByTestId("product-table-root")).toBeDefined();
    });
  });
});
