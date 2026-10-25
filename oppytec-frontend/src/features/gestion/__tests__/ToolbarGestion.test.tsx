import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  ToolbarGestion,
  CategoriaSeccion,
  TablePagination,
  DraftRecoveryBanner,
  DRAFT_STORAGE_KEY,
  GestionPage,
} from "../index";
import { PermissionsProvider, DEFAULT_RBAC_POLICY_STATE } from "@/shared/auth/usePermissions";
import * as httpClient from "@/shared/api/httpClient";

vi.mock("@/shared/api/httpClient", async () => {
  const actual = await vi.importActual<any>("@/shared/api/httpClient");
  return {
    ...actual,
    apiRequest: vi.fn().mockRejectedValue(new Error("Offline in test")),
  };
});

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<any>("framer-motion");
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
  };
});

const mockCategorias = [
  { id: "cat-carnes", nombre: "Carnes y Aves", color: "#DC2626", icono: "Utensils" },
  { id: "cat-lacteos", nombre: "Lácteos y Quesos", color: "#EAB308", icono: "Coffee" },
  { id: "cat-bebidas", nombre: "Vinos y Licores", color: "#7C3AED", icono: "Wine" },
];

function openDropdown(trigger: HTMLElement) {
  fireEvent.pointerDown(trigger, { button: 0, ctrlKey: false });
  fireEvent.click(trigger);
  fireEvent.keyDown(trigger, { key: "ArrowDown" });
}

describe("ToolbarGestion & Phase 2 Gestion Components Suite", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    (httpClient.apiRequest as any).mockRejectedValue(new Error("Offline in test"));
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. ToolbarGestion Component Tests
  // ==========================================================================
  describe("ToolbarGestion Component", () => {
    it("renders desktop and mobile toolbars with area and warehouse controls", () => {
      render(
        <PermissionsProvider>
          <ToolbarGestion
            showCategories={true}
            onToggleShowCategories={vi.fn()}
            onOpenTableConfig={vi.fn()}
            onOpenAdminCategorias={vi.fn()}
            onOpenCatalogos={vi.fn()}
            onOpenTransfer={vi.fn()}
            onNewProduct={vi.fn()}
          />
        </PermissionsProvider>
      );

      expect(screen.getByTestId("toolbar-gestion")).toBeTruthy();
      expect(screen.getByTestId("toolbar-table-dropdown-trigger")).toBeTruthy();
      expect(screen.getByTestId("toolbar-categories-dropdown-trigger")).toBeTruthy();
      expect(screen.getByTestId("toolbar-btn-catalogos")).toBeTruthy();
      expect(screen.getByTestId("toolbar-actions-dropdown-trigger")).toBeTruthy();
      expect(screen.getByTestId("toolbar-btn-new-product")).toBeTruthy();
    });

    it("triggers onOpenTableConfig when clicking 'Personalizar Vista de Tabla'", async () => {
      const onOpenTableConfig = vi.fn();
      render(
        <PermissionsProvider>
          <ToolbarGestion
            showCategories={true}
            onToggleShowCategories={vi.fn()}
            onOpenTableConfig={onOpenTableConfig}
            onOpenAdminCategorias={vi.fn()}
            onOpenCatalogos={vi.fn()}
            onOpenTransfer={vi.fn()}
            onNewProduct={vi.fn()}
          />
        </PermissionsProvider>
      );

      const tableBtn = screen.getByTestId("toolbar-table-dropdown-trigger");
      openDropdown(tableBtn);

      const configOption = await screen.findByTestId("btn-open-table-config");
      expect(configOption).toBeTruthy();
      fireEvent.click(configOption);

      expect(onOpenTableConfig).toHaveBeenCalledTimes(1);
    });

    it("triggers onOpenAdminCategorias from Categories dropdown", async () => {
      const onOpenAdminCategorias = vi.fn();

      render(
        <PermissionsProvider>
          <ToolbarGestion
            showCategories={true}
            onToggleShowCategories={vi.fn()}
            onOpenTableConfig={vi.fn()}
            onOpenAdminCategorias={onOpenAdminCategorias}
            onOpenCatalogos={vi.fn()}
            onOpenTransfer={vi.fn()}
            onNewProduct={vi.fn()}
          />
        </PermissionsProvider>
      );

      const catBtn = screen.getByTestId("toolbar-categories-dropdown-trigger");
      openDropdown(catBtn);

      const adminOption = await screen.findByTestId("btn-admin-categories");
      expect(adminOption).toBeTruthy();
      fireEvent.click(adminOption);
      expect(onOpenAdminCategorias).toHaveBeenCalledTimes(1);
    });

    it("triggers onToggleShowCategories from Categories dropdown", async () => {
      const onToggleShowCategories = vi.fn();

      render(
        <PermissionsProvider>
          <ToolbarGestion
            showCategories={true}
            onToggleShowCategories={onToggleShowCategories}
            onOpenTableConfig={vi.fn()}
            onOpenAdminCategorias={vi.fn()}
            onOpenCatalogos={vi.fn()}
            onOpenTransfer={vi.fn()}
            onNewProduct={vi.fn()}
          />
        </PermissionsProvider>
      );

      const catBtn = screen.getByTestId("toolbar-categories-dropdown-trigger");
      openDropdown(catBtn);

      const toggleOption = await screen.findByTestId("btn-toggle-show-categories");
      fireEvent.click(toggleOption);
      expect(onToggleShowCategories).toHaveBeenCalledTimes(1);
    });

    it("triggers onOpenCatalogos, onOpenTransfer and onNewProduct", async () => {
      const onOpenCatalogos = vi.fn();
      const onOpenTransfer = vi.fn();
      const onNewProduct = vi.fn();

      render(
        <PermissionsProvider>
          <ToolbarGestion
            showCategories={true}
            onToggleShowCategories={vi.fn()}
            onOpenTableConfig={vi.fn()}
            onOpenAdminCategorias={vi.fn()}
            onOpenCatalogos={onOpenCatalogos}
            onOpenTransfer={onOpenTransfer}
            onNewProduct={onNewProduct}
          />
        </PermissionsProvider>
      );

      // Catalogos
      const catalogosBtn = screen.getByTestId("toolbar-btn-catalogos");
      fireEvent.click(catalogosBtn);
      expect(onOpenCatalogos).toHaveBeenCalledTimes(1);

      // Actions -> Transfer
      const actionsBtn = screen.getByTestId("toolbar-actions-dropdown-trigger");
      openDropdown(actionsBtn);
      const transferOption = await screen.findByTestId("btn-action-transfer-stock");
      fireEvent.click(transferOption);
      expect(onOpenTransfer).toHaveBeenCalledTimes(1);

      // New Product primary button
      const newProductBtn = screen.getByTestId("toolbar-btn-new-product");
      fireEvent.click(newProductBtn);
      expect(onNewProduct).toHaveBeenCalledTimes(1);
    });

    it("hides primary button if user lacks catalog.products.create permission", () => {
      const policyWithoutPerm = {
        ...DEFAULT_RBAC_POLICY_STATE,
        isSuperUser: false,
        rolePermissions: [],
      };

      render(
        <PermissionsProvider initialPolicy={policyWithoutPerm}>
          <ToolbarGestion
            showCategories={true}
            onToggleShowCategories={vi.fn()}
            onOpenTableConfig={vi.fn()}
            onOpenAdminCategorias={vi.fn()}
            onOpenCatalogos={vi.fn()}
            onOpenTransfer={vi.fn()}
            onNewProduct={vi.fn()}
          />
        </PermissionsProvider>
      );

      expect(screen.queryByTestId("toolbar-btn-new-product")).toBeNull();
    });
  });

  // ==========================================================================
  // 2. DraftRecoveryBanner Component Tests
  // ==========================================================================
  describe("DraftRecoveryBanner Component", () => {
    it("renders nothing when no draft is stored in localStorage", () => {
      render(<DraftRecoveryBanner />);
      expect(screen.queryByTestId("draft-recovery-banner")).toBeNull();
    });

    it("detects draft in localStorage, renders details, and can discard", async () => {
      const mockDraft = {
        nombre: "Bife Angosto Angus",
        currentStep: 2,
      };
      window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(mockDraft));

      const onDismiss = vi.fn();
      render(<DraftRecoveryBanner onDismiss={onDismiss} />);

      expect(screen.getByTestId("draft-recovery-banner")).toBeTruthy();
      expect(screen.getByText("Bife Angosto Angus")).toBeTruthy();
      expect(screen.getByText("Paso 2 de 4")).toBeTruthy();

      const discardBtn = screen.getByTestId("btn-discard-draft");
      fireEvent.click(discardBtn);

      expect(window.localStorage.getItem(DRAFT_STORAGE_KEY)).toBeNull();
      expect(onDismiss).toHaveBeenCalledTimes(1);
    });

    it("calls onRecoverDraft with parsed draft payload when clicking recover", () => {
      const mockDraft = {
        nombre: "Vino Carménère Reserva",
        currentStep: 3,
        sku: "VIN-CAR-001",
      };
      window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(mockDraft));

      const onRecoverDraft = vi.fn();
      render(<DraftRecoveryBanner onRecoverDraft={onRecoverDraft} />);

      const recoverBtn = screen.getByTestId("btn-recover-draft");
      fireEvent.click(recoverBtn);

      expect(onRecoverDraft).toHaveBeenCalledWith(
        expect.objectContaining({
          nombre: "Vino Carménère Reserva",
          currentStep: 3,
          sku: "VIN-CAR-001",
        })
      );
    });

    it("handles corrupted JSON gracefully without breaking", () => {
      window.localStorage.setItem(DRAFT_STORAGE_KEY, "invalid-json{{");
      render(<DraftRecoveryBanner />);
      expect(screen.queryByTestId("draft-recovery-banner")).toBeNull();
    });
  });

  // ==========================================================================
  // 3. CategoriaSeccion Component Tests
  // ==========================================================================
  describe("CategoriaSeccion Component", () => {
    it("renders category badges and toggles selection on click", () => {
      const selectedIds = new Set(["cat-carnes"]);
      const onToggle = vi.fn();

      render(
        <CategoriaSeccion
          categorias={mockCategorias}
          selectedIds={selectedIds}
          onToggle={onToggle}
        />
      );

      expect(screen.getByTestId("categoria-seccion")).toBeTruthy();
      expect(screen.getByText("Carnes y Aves")).toBeTruthy();
      expect(screen.getByText("Lácteos y Quesos")).toBeTruthy();
      expect(screen.getByText("Vinos y Licores")).toBeTruthy();

      const carnesBadge = screen.getByTestId("category-badge-cat-carnes");
      expect(carnesBadge.getAttribute("aria-pressed")).toBe("true");

      const lacteosBadge = screen.getByTestId("category-badge-cat-lacteos");
      expect(lacteosBadge.getAttribute("aria-pressed")).toBe("false");

      fireEvent.click(lacteosBadge);
      expect(onToggle).toHaveBeenCalledWith("cat-lacteos");
    });

    it("returns null safely when categories list is empty", () => {
      const { container } = render(
        <CategoriaSeccion
          categorias={[]}
          selectedIds={new Set()}
          onToggle={vi.fn()}
        />
      );
      expect(container.firstChild).toBeNull();
    });

    it("deduplicates categories with duplicate names safely", () => {
      const duplicates = [
        ...mockCategorias,
        { id: "cat-carnes-dup", nombre: "Carnes y Aves", color: "#DC2626" },
      ];

      render(
        <CategoriaSeccion
          categorias={duplicates}
          selectedIds={new Set()}
          onToggle={vi.fn()}
        />
      );

      const items = screen.getAllByText("Carnes y Aves");
      expect(items.length).toBe(1);
    });
  });

  // ==========================================================================
  // 4. TablePagination Component Tests
  // ==========================================================================
  describe("TablePagination Component", () => {
    it("renders summary and calculates item range correctly", () => {
      const onPageChange = vi.fn();
      const onPageSizeChange = vi.fn();

      render(
        <TablePagination
          currentPage={2}
          totalItems={45}
          pageSize={10}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
          itemLabel="insumos"
        />
      );

      expect(screen.getByText("Mostrando 11 - 20")).toBeTruthy();
      expect(screen.getByText("45 insumos")).toBeTruthy();
    });

    it("handles page navigation: next, prev, first, last, and direct page click", () => {
      const onPageChange = vi.fn();

      render(
        <TablePagination
          currentPage={2}
          totalItems={50}
          pageSize={10}
          onPageChange={onPageChange}
          onPageSizeChange={vi.fn()}
        />
      );

      // Prev page
      fireEvent.click(screen.getByTestId("pagination-prev-page"));
      expect(onPageChange).toHaveBeenCalledWith(1);

      // Next page
      fireEvent.click(screen.getByTestId("pagination-next-page"));
      expect(onPageChange).toHaveBeenCalledWith(3);

      // First page
      fireEvent.click(screen.getByTestId("pagination-first-page"));
      expect(onPageChange).toHaveBeenCalledWith(1);

      // Last page
      fireEvent.click(screen.getByTestId("pagination-last-page"));
      expect(onPageChange).toHaveBeenCalledWith(5);

      // Direct page number
      fireEvent.click(screen.getByTestId("pagination-page-3"));
      expect(onPageChange).toHaveBeenCalledWith(3);
    });

    it("handles page size selection and resets to page 1", () => {
      const onPageChange = vi.fn();
      const onPageSizeChange = vi.fn();

      render(
        <TablePagination
          currentPage={3}
          totalItems={100}
          pageSize={10}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
        />
      );

      const select = screen.getByTestId("pagination-page-size-select");
      fireEvent.change(select, { target: { value: "30" } });

      expect(onPageSizeChange).toHaveBeenCalledWith(30);
      expect(onPageChange).toHaveBeenCalledWith(1);
    });

    it("disables first and prev buttons on page 1", () => {
      render(
        <TablePagination
          currentPage={1}
          totalItems={20}
          pageSize={10}
          onPageChange={vi.fn()}
          onPageSizeChange={vi.fn()}
        />
      );

      const firstBtn = screen.getByTestId("pagination-first-page") as HTMLButtonElement;
      const prevBtn = screen.getByTestId("pagination-prev-page") as HTMLButtonElement;
      expect(firstBtn.disabled).toBe(true);
      expect(prevBtn.disabled).toBe(true);
    });
  });

  // ==========================================================================
  // 5. GestionPage Integration Tests
  // ==========================================================================
  describe("GestionPage Integration", () => {
    it("renders GestionPage with SectionHeader, search bar, and mock products", async () => {
      render(
        <MemoryRouter>
          <PermissionsProvider>
            <GestionPage />
          </PermissionsProvider>
        </MemoryRouter>
      );

      expect(screen.getByTestId("gestion-page")).toBeTruthy();
      expect(screen.getByRole("heading", { level: 1 })).toBeTruthy();
      expect(screen.getByTestId("gestion-search-input")).toBeTruthy();

      // Check product row renders
      await waitFor(() => {
        expect(screen.getAllByText("Lomo Vetado Angus Premium").length).toBeGreaterThan(0);
      });
    });

    it("filters products using search query input", async () => {
      render(
        <MemoryRouter>
          <PermissionsProvider>
            <GestionPage />
          </PermissionsProvider>
        </MemoryRouter>
      );

      const searchInput = screen.getByTestId("gestion-search-input");
      fireEvent.change(searchInput, { target: { value: "Pollo" } });

      await waitFor(() => {
        expect(screen.getAllByText("Pechuga de Pollo Deshuesada").length).toBeGreaterThan(0);
        expect(screen.queryByText("Lomo Vetado Angus Premium")).toBeNull();
      });
    });

    it("opens and closes responsive dialogs properly", async () => {
      render(
        <MemoryRouter>
          <PermissionsProvider>
            <GestionPage />
          </PermissionsProvider>
        </MemoryRouter>
      );

      // Open new product dialog
      const newProductBtn = screen.getByTestId("toolbar-btn-new-product");
      fireEvent.click(newProductBtn);

      expect(screen.getByTestId("producto-wizard-dialog")).toBeTruthy();

      // Close dialog
      const closeBtn = screen.getByTestId("btn-wizard-cancel");
      fireEvent.click(closeBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("producto-wizard-dialog")).toBeNull();
      });
    });
  });
});
