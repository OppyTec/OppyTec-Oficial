import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { TableConfigModal } from "../components/TableConfigModal";
import { AdministradorCategoriasDialog } from "../components/AdministradorCategoriasDialog";
import { CatalogosManagerDialog } from "../components/CatalogosManagerDialog";
import { TransferDialog } from "../components/TransferDialog";
import { GestionPage } from "../GestionPage";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import * as httpClient from "@/shared/api/httpClient";
import {
  ALL_COLUMNS,
  DEFAULT_COLUMNS,
  PRODUCT_SORT_OPTIONS,
  type Producto,
  type Categoria,
  type Marca,
  type TipoEnvase,
} from "../types";

vi.mock("@/shared/api/httpClient", async () => {
  const actual = await vi.importActual<any>("@/shared/api/httpClient");
  return {
    ...actual,
    apiRequest: vi.fn().mockRejectedValue(new Error("Offline in test")),
  };
});

// Mock matchMedia and fetch
beforeEach(() => {
  (httpClient.apiRequest as any).mockRejectedValue(new Error("Offline in test"));
  global.fetch = vi.fn().mockRejectedValue(new Error("Offline in test"));
  window.matchMedia =
    window.matchMedia ||
    function () {
      return {
        matches: false,
        addListener: () => {},
        removeListener: () => {},
      };
    };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function openDropdown(trigger: HTMLElement) {
  fireEvent.pointerDown(trigger, { button: 0, ctrlKey: false });
  fireEvent.click(trigger);
  fireEvent.keyDown(trigger, { key: "ArrowDown" });
}

const MOCK_CATEGORIAS: Categoria[] = [
  { id: "cat-1", nombre: "Carnes", color: "#EF4444", icono: "ChefHat", tipo_categoria: "insumo", area_operativa_ids: ["area-cocina"] },
  { id: "cat-2", nombre: "Bebidas", color: "#8B5CF6", icono: "Wine", tipo_categoria: "producto", area_operativa_ids: ["area-bar"] },
];

const MOCK_MARCAS: Marca[] = [
  { id: "marca-1", nombre: "Colun" },
  { id: "marca-2", nombre: "Coca Cola" },
];

const MOCK_ENVASE: TipoEnvase[] = [
  { id: "env-1", nombre: "Botella 750ml", icono: "Package" },
  { id: "env-2", nombre: "Bolsa 1Kg", icono: "Box" },
];

const MOCK_PRODUCTOS: Producto[] = [
  {
    id: "p1",
    nombre: "Lomo Vetado 1Kg",
    categoria_id: "cat-1",
    marca_id: "marca-1",
    tipo_envase_id: "env-2",
    unidad: "Kg",
    costo_unitario: 12000,
    precio_venta: 18000,
    stock_actual: 25,
    bodegas_config: [
      { bodega_id: "bod-central", bodega_nombre: "Bodega Principal", stock_actual: 20, stock_minimo: 5 },
      { bodega_id: "bod-cocina", bodega_nombre: "Cocina Caliente", stock_actual: 5, stock_minimo: 2 },
    ],
  },
  {
    id: "p2",
    nombre: "Vino Tinto Reserva 750ml",
    categoria_id: "cat-2",
    marca_id: "marca-2",
    tipo_envase_id: "env-1",
    unidad: "botella",
    costo_unitario: 5000,
    precio_venta: 12000,
    stock_actual: 40,
    bodegas_config: [
      { bodega_id: "bod-central", bodega_nombre: "Bodega Principal", stock_actual: 30, stock_minimo: 10 },
      { bodega_id: "bod-bar", bodega_nombre: "Bar & Cava", stock_actual: 10, stock_minimo: 4 },
    ],
  },
];

describe("Modales de Soporte de Gestión (Fase 4)", () => {
  describe("1. TableConfigModal", () => {
    it("renders modal with sections, presets, and columns", () => {
      const onSaveConfig = vi.fn();
      const onOpenChange = vi.fn();

      render(
        <TableConfigModal
          open={true}
          onOpenChange={onOpenChange}
          sortConfig={{ key: "nombre", direction: "asc" }}
          onSortChange={vi.fn()}
          sortOptions={PRODUCT_SORT_OPTIONS}
          columns={ALL_COLUMNS}
          visibleColsOrder={DEFAULT_COLUMNS}
          onSaveConfig={onSaveConfig}
        />
      );

      expect(screen.getByTestId("table-config-modal")).toBeDefined();
      expect(screen.getByTestId("preset-select")).toBeDefined();
      expect(screen.getByTestId("viewmode-simple")).toBeDefined();
      expect(screen.getByTestId("viewmode-agrupado")).toBeDefined();
      expect(screen.getByTestId("btn-mass-neto")).toBeDefined();
      expect(screen.getByTestId("btn-mass-bruto")).toBeDefined();
    });

    it("allows toggling columns and applying configuration", () => {
      const onSaveConfig = vi.fn();
      const onOpenChange = vi.fn();

      render(
        <TableConfigModal
          open={true}
          onOpenChange={onOpenChange}
          sortConfig={{ key: "nombre", direction: "asc" }}
          onSortChange={vi.fn()}
          sortOptions={PRODUCT_SORT_OPTIONS}
          columns={ALL_COLUMNS}
          visibleColsOrder={DEFAULT_COLUMNS}
          onSaveConfig={onSaveConfig}
        />
      );

      // Click on a column toggle
      const colToggle = screen.getByTestId("col-toggle-bodega");
      fireEvent.click(colToggle);

      // Switch view mode to simple
      const btnSimple = screen.getByTestId("viewmode-simple");
      fireEvent.click(btnSimple);

      // Click save button
      const btnApply = screen.getByTestId("btn-apply-table-config");
      fireEvent.click(btnApply);

      expect(onSaveConfig).toHaveBeenCalled();
      const params = onSaveConfig.mock.calls[0]?.[0];
      expect(params?.viewMode).toBe("simple");
      expect(params?.orderedColumns).toContain("bodega");
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });

    it("supports mass switching between neto and bruto columns", () => {
      const onSaveConfig = vi.fn();

      render(
        <TableConfigModal
          open={true}
          onOpenChange={vi.fn()}
          sortConfig={{ key: "nombre", direction: "asc" }}
          onSortChange={vi.fn()}
          sortOptions={PRODUCT_SORT_OPTIONS}
          columns={ALL_COLUMNS}
          visibleColsOrder={["ultimo_costo_unidad_neto", "precio_venta_bruto"]}
          onSaveConfig={onSaveConfig}
        />
      );

      // Mass bruto
      fireEvent.click(screen.getByTestId("btn-mass-bruto"));

      // Apply
      fireEvent.click(screen.getByTestId("btn-apply-table-config"));
      const params = onSaveConfig.mock.calls[0]?.[0];
      expect(params?.orderedColumns).toContain("ultimo_costo_unidad_bruto");
    });
  });

  describe("2. AdministradorCategoriasDialog", () => {
    it("renders categories tab and switches to operational areas tab", () => {
      render(
        <AdministradorCategoriasDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          productos={MOCK_PRODUCTOS}
          onCreateCategory={vi.fn()}
          onUpdateCategory={vi.fn()}
          onDeleteCategory={vi.fn()}
        />
      );

      expect(screen.getByTestId("admin-categorias-dialog")).toBeDefined();
      expect(screen.getByText("Carnes")).toBeDefined();
      expect(screen.getByText("Bebidas")).toBeDefined();

      // Switch to Areas tab
      fireEvent.click(screen.getByTestId("tab-areas"));
      expect(screen.getByText("Áreas Operativas (4)")).toBeDefined();
    });

    it("opens category creation modal and submits new category", async () => {
      const onCreateCategory = vi.fn().mockResolvedValue(undefined);

      render(
        <AdministradorCategoriasDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          productos={MOCK_PRODUCTOS}
          onCreateCategory={onCreateCategory}
          onUpdateCategory={vi.fn()}
          onDeleteCategory={vi.fn()}
        />
      );

      fireEvent.click(screen.getByTestId("btn-nueva-categoria"));
      expect(screen.getByTestId("modal-form-categoria")).toBeDefined();

      const inputName = screen.getByTestId("input-cat-name");
      fireEvent.change(inputName, { target: { value: "Postres y Pastelería" } });

      fireEvent.click(screen.getByTestId("btn-save-category"));

      await waitFor(() => {
        expect(onCreateCategory).toHaveBeenCalledWith("Postres y Pastelería", expect.any(Object));
      });
    });

    it("shows warning when deleting category with linked products", () => {
      render(
        <AdministradorCategoriasDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          productos={MOCK_PRODUCTOS}
          onCreateCategory={vi.fn()}
          onUpdateCategory={vi.fn()}
          onDeleteCategory={vi.fn()}
        />
      );

      // Click delete on Carnes (has linked product p1)
      fireEvent.click(screen.getByTestId("btn-delete-cat-cat-1"));
      expect(screen.getByTestId("confirm-delete-category-dialog")).toBeDefined();
      expect(screen.getByText(/Advertencia: Hay/i)).toBeDefined();
    });
  });

  describe("3. CatalogosManagerDialog", () => {
    it("renders 3 tabs (familias, marcas, envases) and switches between them", () => {
      render(
        <CatalogosManagerDialog
          open={true}
          onOpenChange={vi.fn()}
          marcas={MOCK_MARCAS}
          tiposEnvase={MOCK_ENVASE}
          productos={MOCK_PRODUCTOS}
          onCreateBrand={vi.fn()}
          onCreateTipoEnvase={vi.fn()}
        />
      );

      expect(screen.getByTestId("catalogos-manager-dialog")).toBeDefined();
      expect(screen.getByTestId("tab-familias")).toBeDefined();
      expect(screen.getByTestId("tab-marcas")).toBeDefined();
      expect(screen.getByTestId("tab-envases")).toBeDefined();

      // Switch to marcas
      fireEvent.click(screen.getByTestId("tab-marcas"));
      expect(screen.getByText("Colun")).toBeDefined();
      expect(screen.getByText("Coca Cola")).toBeDefined();

      // Switch to envases
      fireEvent.click(screen.getByTestId("tab-envases"));
      expect(screen.getByText("Botella 750ml")).toBeDefined();
    });

    it("opens create modal and invokes onCreateBrand", async () => {
      const onCreateBrand = vi.fn().mockResolvedValue(undefined);

      render(
        <CatalogosManagerDialog
          open={true}
          onOpenChange={vi.fn()}
          defaultTab="marcas"
          marcas={MOCK_MARCAS}
          tiposEnvase={MOCK_ENVASE}
          productos={MOCK_PRODUCTOS}
          onCreateBrand={onCreateBrand}
          onCreateTipoEnvase={vi.fn()}
        />
      );

      fireEvent.click(screen.getByTestId("btn-nuevo-catalogo-item"));
      expect(screen.getByTestId("modal-form-catalog-item")).toBeDefined();

      fireEvent.change(screen.getByTestId("input-catalog-item-name"), {
        target: { value: "Nestle" },
      });
      fireEvent.click(screen.getByTestId("btn-save-catalog-item"));

      await waitFor(() => {
        expect(onCreateBrand).toHaveBeenCalledWith("Nestle", null);
      });
    });
  });

  describe("4. TransferDialog", () => {
    it("renders origin and destination warehouse selects and transfers item", async () => {
      const onSuccess = vi.fn();
      const onOpenChange = vi.fn();

      render(
        <TransferDialog
          open={true}
          onOpenChange={onOpenChange}
          productos={MOCK_PRODUCTOS}
          categorias={MOCK_CATEGORIAS}
          onSuccess={onSuccess}
        />
      );

      expect(screen.getByTestId("transfer-dialog")).toBeDefined();
      expect(screen.getByTestId("select-bodega-origen")).toBeDefined();
      expect(screen.getByTestId("select-bodega-destino")).toBeDefined();

      // Select origin and destination
      fireEvent.change(screen.getByTestId("select-bodega-origen"), {
        target: { value: "bod-central" },
      });
      fireEvent.change(screen.getByTestId("select-bodega-destino"), {
        target: { value: "bod-cocina" },
      });

      // Select product
      fireEvent.change(screen.getByTestId("select-product-0"), {
        target: { value: "p1" },
      });

      // Set quantity
      fireEvent.change(screen.getByTestId("input-transfer-qty-0"), {
        target: { value: "5" },
      });

      // Click confirm transfer
      fireEvent.click(screen.getByTestId("btn-confirm-transfer"));

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
        expect(onOpenChange).toHaveBeenCalledWith(false);
      });
    });

    it("prevents selecting same warehouse for origin and destination", () => {
      render(
        <TransferDialog
          open={true}
          onOpenChange={vi.fn()}
          productos={MOCK_PRODUCTOS}
          categorias={MOCK_CATEGORIAS}
        />
      );

      fireEvent.change(screen.getByTestId("select-bodega-origen"), {
        target: { value: "bod-central" },
      });
      fireEvent.change(screen.getByTestId("select-bodega-destino"), {
        target: { value: "bod-central" },
      });

      expect(
        screen.getByText(/La bodega de origen y la bodega de destino deben ser diferentes/i)
      ).toBeDefined();
      expect((screen.getByTestId("btn-confirm-transfer") as HTMLButtonElement).disabled).toBe(true);
    });
  });

  describe("5. GestionPage Integration with Modals", () => {
    it("renders GestionPage and can open TableConfigModal from toolbar", async () => {
      render(
        <PermissionsProvider>
          <GestionPage />
        </PermissionsProvider>
      );

      expect(screen.getByTestId("gestion-page")).toBeDefined();

      // TableConfigModal should be closed initially
      expect(screen.queryByTestId("table-config-modal")).toBeNull();

      // Open TableConfig from Toolbar
      const btnTable = screen.getByTestId("toolbar-table-dropdown-trigger");
      openDropdown(btnTable);

      const btnConfig = await screen.findByTestId("btn-open-table-config");
      fireEvent.click(btnConfig);

      // Now TableConfigModal should be open
      expect(screen.getByTestId("table-config-modal")).toBeDefined();
    });

    it("can open AdministradorCategoriasDialog from toolbar", async () => {
      render(
        <PermissionsProvider>
          <GestionPage />
        </PermissionsProvider>
      );

      const btnCategorias = screen.getByTestId("toolbar-categories-dropdown-trigger");
      openDropdown(btnCategorias);

      const btnAdminCat = await screen.findByTestId("btn-admin-categories");
      fireEvent.click(btnAdminCat);

      expect(screen.getByTestId("admin-categorias-dialog")).toBeDefined();
    });

    it("can open CatalogosManagerDialog from toolbar", () => {
      render(
        <PermissionsProvider>
          <GestionPage />
        </PermissionsProvider>
      );

      const btnCatalogos = screen.getByTestId("toolbar-btn-catalogos");
      fireEvent.click(btnCatalogos);

      expect(screen.getByTestId("catalogos-manager-dialog")).toBeDefined();
    });

    it("can open TransferDialog from toolbar", async () => {
      render(
        <PermissionsProvider>
          <GestionPage />
        </PermissionsProvider>
      );

      const btnAcciones = screen.getByTestId("toolbar-actions-dropdown-trigger");
      openDropdown(btnAcciones);

      const btnTransfer = await screen.findByTestId("btn-action-transfer-stock");
      fireEvent.click(btnTransfer);

      expect(screen.getByTestId("transfer-dialog")).toBeDefined();
    });

    it("can open ProductoWizardDialog from toolbar", () => {
      render(
        <PermissionsProvider>
          <GestionPage />
        </PermissionsProvider>
      );

      const btnNewProduct = screen.getByTestId("toolbar-btn-new-product");
      fireEvent.click(btnNewProduct);

      expect(screen.getByTestId("producto-wizard-dialog")).toBeDefined();
    });
  });
});
