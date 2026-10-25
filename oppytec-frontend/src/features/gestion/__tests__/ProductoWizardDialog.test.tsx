// oppytec-frontend/src/features/gestion/__tests__/ProductoWizardDialog.test.tsx
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  ProductoWizardDialog,
  generateFullProductName,
  calculateFinancialKPIs,
} from "../components/ProductoWizardDialog";
import { DRAFT_STORAGE_KEY } from "../components/DraftRecoveryBanner";
import type { Categoria, Marca, TipoEnvase, Producto } from "../types";

const MOCK_CATEGORIAS: Categoria[] = [
  { id: "cat-carnes", nombre: "Carnes y Aves", color: "#DC2626", icono: "beef" },
  { id: "cat-bebidas", nombre: "Vinos y Licores", color: "#7C3AED", icono: "wine" },
];

const MOCK_MARCAS: Marca[] = [
  { id: "marca-angus", nombre: "Angus Pride", logo_url: null },
  { id: "marca-concha", nombre: "Concha y Toro", logo_url: null },
];

const MOCK_TIPOS_ENVASE: TipoEnvase[] = [
  { id: "env-botella", nombre: "Botella", icono: "bottle" },
  { id: "env-lata", nombre: "Lata", icono: "can" },
  { id: "env-granel", nombre: "A Granel", icono: "scale" },
];

describe("Fase 5: ProductoWizardDialog Suite", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
  });

  describe("1. Pure Formula Helpers", () => {
    it("generates full product name with brand and packaging", () => {
      const full = generateFullProductName({
        nombre: "Lomo Vetado",
        marcaNombre: "Angus Pride",
        envaseNombre: "Bolsa al Vacío",
        contenidoEnvase: 2.5,
        unidadEnvase: "kg",
      });
      expect(full).toBe("Lomo Vetado - Angus Pride (Bolsa al Vacío 2.5 kg)");
    });

    it("generates full product name for bulk/granel products", () => {
      const full = generateFullProductName({
        nombre: "Papas Nativas",
        marcaNombre: "La Finca",
        envaseNombre: "A Granel",
      });
      expect(full).toBe("Papas Nativas - La Finca (A Granel)");
    });

    it("returns empty string when product name is empty or whitespace", () => {
      expect(generateFullProductName({ nombre: "" })).toBe("");
      expect(generateFullProductName({ nombre: "   " })).toBe("");
    });

    it("calculates financial KPIs accurately (margins, markup, food cost)", () => {
      // Costo Neto: 10,000, Precio Venta Neto: 25,000
      // Margen Neto = (25000 - 10000) / 25000 = 60%
      // Markup = (25000 - 10000) / 10000 = 150%
      // Food Cost = 10000 / 25000 = 40%
      const kpis = calculateFinancialKPIs({
        costoNeto: 10000,
        costoBruto: 11900,
        precioVentaNeto: 25000,
        precioVentaBruto: 29750,
      });

      expect(kpis.margenNeto).toBe(60);
      expect(kpis.markup).toBe(150);
      expect(kpis.foodCost).toBe(40);
    });

    it("handles edge cases in financial calculations (zero prices/costs)", () => {
      const kpis = calculateFinancialKPIs({
        costoNeto: 0,
        costoBruto: 0,
        precioVentaNeto: 0,
        precioVentaBruto: 0,
      });

      expect(kpis.margenNeto).toBe(0);
      expect(kpis.margenBruto).toBe(0);
      expect(kpis.markup).toBe(0);
      expect(kpis.foodCost).toBe(0);
    });
  });

  describe("2. Multichannel Structure & Stepper Navigation", () => {
    it("renders modal with initial step 1 and dynamic title for new product", () => {
      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          marcas={MOCK_MARCAS}
          tiposEnvase={MOCK_TIPOS_ENVASE}
          onSave={vi.fn()}
        />
      );

      expect(screen.getByTestId("producto-wizard-dialog")).toBeDefined();
      expect(screen.getByText("Nuevo Producto")).toBeDefined();
      expect(screen.getByTestId("channel-manual")).toBeDefined();
      expect(screen.getByTestId("channel-excel")).toBeDefined();
      expect(screen.getByTestId("channel-invoice")).toBeDefined();
      expect(screen.getByTestId("step-1-content")).toBeDefined();
    });

    it("navigates forward and backward through all 4 wizard steps", () => {
      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          marcas={MOCK_MARCAS}
          tiposEnvase={MOCK_TIPOS_ENVASE}
          onSave={vi.fn()}
        />
      );

      // Must have name before going to step 2
      const inputName = screen.getByTestId("input-product-name");
      fireEvent.change(inputName, { target: { value: "Salmón Atlántico" } });

      // Click Next to step 2
      fireEvent.click(screen.getByTestId("btn-wizard-next"));
      expect(screen.getByTestId("step-2-content")).toBeDefined();

      // Click Next to step 3
      fireEvent.click(screen.getByTestId("btn-wizard-next"));
      expect(screen.getByTestId("step-3-content")).toBeDefined();

      // Click Next to step 4
      fireEvent.click(screen.getByTestId("btn-wizard-next"));
      expect(screen.getByTestId("step-4-content")).toBeDefined();

      // On step 4, the primary button is "Guardar Producto"
      expect(screen.getByTestId("btn-wizard-submit")).toBeDefined();

      // Click Previous back to step 3
      fireEvent.click(screen.getByTestId("btn-wizard-prev"));
      expect(screen.getByTestId("step-3-content")).toBeDefined();

      // Click Stepper directly to jump to step 1
      fireEvent.click(screen.getByTestId("stepper-step-1"));
      expect(screen.getByTestId("step-1-content")).toBeDefined();
    });

    it("switches to Excel and Invoice channels and invokes callbacks", () => {
      const onOpenExcel = vi.fn();
      const onOpenFactura = vi.fn();

      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          marcas={MOCK_MARCAS}
          tiposEnvase={MOCK_TIPOS_ENVASE}
          onOpenExcelImport={onOpenExcel}
          onOpenFacturaImport={onOpenFactura}
          onSave={vi.fn()}
        />
      );

      fireEvent.click(screen.getByTestId("channel-excel"));
      expect(onOpenExcel).toHaveBeenCalled();

      fireEvent.click(screen.getByTestId("channel-invoice"));
      expect(onOpenFactura).toHaveBeenCalled();
    });
  });

  describe("3. Auto-generated Full Name Banner in Real Time", () => {
    it("updates full name banner as user types name and selects brand", () => {
      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          marcas={MOCK_MARCAS}
          tiposEnvase={MOCK_TIPOS_ENVASE}
          onSave={vi.fn()}
        />
      );

      // Initially no banner
      expect(screen.queryByTestId("banner-nombre-autogenerado")).toBeNull();

      // Type name
      const inputName = screen.getByTestId("input-product-name");
      fireEvent.change(inputName, { target: { value: "Chardonnay Reserva" } });

      expect(screen.getByTestId("banner-nombre-autogenerado")).toBeDefined();
      expect(screen.getByTestId("text-nombre-completo-generado").textContent).toContain("Chardonnay Reserva");

      // Select brand
      const selectMarca = screen.getByTestId("select-marca");
      fireEvent.change(selectMarca, { target: { value: "marca-concha" } });

      expect(screen.getByTestId("text-nombre-completo-generado").textContent).toContain(
        "Chardonnay Reserva - Concha y Toro"
      );
    });

    it("supports adding a brand on-the-fly and selects it", async () => {
      const onCreateBrand = vi.fn().mockResolvedValue({
        id: "marca-nueva",
        nombre: "Bodega Los Andes",
        logo_url: null,
      });

      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          marcas={MOCK_MARCAS}
          tiposEnvase={MOCK_TIPOS_ENVASE}
          onCreateBrand={onCreateBrand}
          onSave={vi.fn()}
        />
      );

      fireEvent.click(screen.getByTestId("btn-toggle-new-marca"));
      const inputNewMarca = screen.getByTestId("input-new-marca");
      fireEvent.change(inputNewMarca, { target: { value: "Bodega Los Andes" } });

      fireEvent.click(screen.getByTestId("btn-save-new-marca"));

      await waitFor(() => {
        expect(onCreateBrand).toHaveBeenCalledWith("Bodega Los Andes");
      });
    });
  });

  describe("4. Step 2 & 3: Packaging, Packs and Warehouse Stocks", () => {
    it("allows adding and removing purchase presentations", () => {
      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          initialStep={2}
          onSave={vi.fn()}
        />
      );

      expect(screen.getByTestId("step-2-content")).toBeDefined();

      // Add presentation
      fireEvent.click(screen.getByTestId("btn-add-presentacion"));
      expect(screen.getByTestId("item-presentacion-0")).toBeDefined();

      const inputPresName = screen.getByTestId("input-pres-nombre-0");
      fireEvent.change(inputPresName, { target: { value: "Caja x12" } });
      expect((inputPresName as HTMLInputElement).value).toBe("Caja x12");

      // Remove presentation
      fireEvent.click(screen.getByTestId("btn-remove-pres-0"));
      expect(screen.queryByTestId("item-presentacion-0")).toBeNull();
    });

    it("allows configuring warehouse stock and aisle/rack coordinates in Step 3", () => {
      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          initialStep={3}
          onSave={vi.fn()}
        />
      );

      expect(screen.getByTestId("step-3-content")).toBeDefined();

      const checkCentral = screen.getByTestId("check-bodega-bod-central");
      if (!(checkCentral as HTMLInputElement).checked) {
        fireEvent.click(checkCentral);
      }

      const inputStock = screen.getByTestId("input-stock-actual-bod-central");
      fireEvent.change(inputStock, { target: { value: "50" } });
      expect((inputStock as HTMLInputElement).value).toBe("50");

      const inputLetra = screen.getByTestId("input-coord-letra-bod-central");
      fireEvent.change(inputLetra, { target: { value: "c" } });
      expect((inputLetra as HTMLInputElement).value).toBe("C");
    });
  });

  describe("5. Step 4: Prices, Costs, and Live Drafting", () => {
    it("synchronizes net and gross prices with configurable IVA and updates KPIs", () => {
      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          initialStep={4}
          onSave={vi.fn()}
        />
      );

      expect(screen.getByTestId("step-4-content")).toBeDefined();

      // Enter Costo Neto: 10,000
      const inputCostoNeto = screen.getByTestId("input-costo-neto");
      fireEvent.change(inputCostoNeto, { target: { value: "10000" } });

      // Costo Bruto auto-calculates with 19% IVA -> 11900
      const inputCostoBruto = screen.getByTestId("input-costo-bruto") as HTMLInputElement;
      expect(inputCostoBruto.value).toBe("11900");

      // Enter Precio Venta Neto: 20,000
      const inputPvNeto = screen.getByTestId("input-precio-venta-neto");
      fireEvent.change(inputPvNeto, { target: { value: "20000" } });

      // Precio Venta Bruto auto-calculates -> 23800
      const inputPvBruto = screen.getByTestId("input-precio-venta-bruto") as HTMLInputElement;
      expect(inputPvBruto.value).toBe("23800");

      // Check reactive KPIs
      // Margen Neto = (20000 - 10000) / 20000 = 50%
      // Markup = (20000 - 10000) / 10000 = 100%
      // Food Cost = 10000 / 20000 = 50%
      expect(screen.getByTestId("kpi-margen-neto").textContent).toBe("50%");
      expect(screen.getByTestId("kpi-markup").textContent).toBe("100%");
      expect(screen.getByTestId("kpi-food-cost").textContent).toBe("50%");
    });

    it("saves draft continuously to localStorage and allows discarding", async () => {
      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          onSave={vi.fn()}
        />
      );

      const inputName = screen.getByTestId("input-product-name");
      fireEvent.change(inputName, { target: { value: "Borrador Test" } });

      await waitFor(() => {
        const raw = window.localStorage.getItem(DRAFT_STORAGE_KEY);
        expect(raw).toBeTruthy();
        expect(JSON.parse(raw!).nombre).toBe("Borrador Test");
      });

      // Discard draft
      fireEvent.click(screen.getByTestId("btn-discard-draft"));
      expect((inputName as HTMLInputElement).value).toBe("");
      expect(window.localStorage.getItem(DRAFT_STORAGE_KEY)).toBeNull();
    });

    it("submits the full product payload on Step 4 and clears draft", async () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      const onOpenChange = vi.fn();

      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={onOpenChange}
          categorias={MOCK_CATEGORIAS}
          onSave={onSave}
        />
      );

      // Step 1: fill name
      fireEvent.change(screen.getByTestId("input-product-name"), {
        target: { value: "Filete de Res Angus" },
      });
      fireEvent.change(screen.getByTestId("input-sku"), {
        target: { value: "FIL-ANG-01" },
      });

      // Advance to step 4
      fireEvent.click(screen.getByTestId("stepper-step-4"));
      expect(screen.getByTestId("step-4-content")).toBeDefined();

      // Enter costs
      fireEvent.change(screen.getByTestId("input-costo-neto"), {
        target: { value: "15000" },
      });
      fireEvent.change(screen.getByTestId("input-precio-venta-neto"), {
        target: { value: "30000" },
      });

      // Submit
      fireEvent.click(screen.getByTestId("btn-wizard-submit"));

      await waitFor(() => {
        expect(onSave).toHaveBeenCalled();
        const payload = onSave.mock.calls[0]?.[0];
        expect(payload?.nombre).toBe("Filete de Res Angus");
        expect(payload?.sku).toBe("FIL-ANG-01");
        expect(payload?.costo_unitario).toBe(15000);
        expect(payload?.precio_venta).toBe(35700); // 30000 * 1.19
        expect(onOpenChange).toHaveBeenCalledWith(false);
      });
    });

    it("loads editingProduct data correctly when editing mode is active", () => {
      const existingProduct: Producto = {
        id: "prod-edit-1",
        nombre: "Pisco Sour Peruano",
        categoria_id: "cat-bebidas",
        unidad: "L",
        costo_unitario: 5000,
        precio_venta: 12000,
        sku: "BAR-PIS-001",
        bodegas_config: [],
      };

      render(
        <ProductoWizardDialog
          open={true}
          onOpenChange={vi.fn()}
          editingProduct={existingProduct}
          categorias={MOCK_CATEGORIAS}
          onSave={vi.fn()}
        />
      );

      expect(screen.getByText("Editar Producto")).toBeDefined();
      const inputName = screen.getByTestId("input-product-name") as HTMLInputElement;
      expect(inputName.value).toBe("Pisco Sour Peruano");
      const inputSku = screen.getByTestId("input-sku") as HTMLInputElement;
      expect(inputSku.value).toBe("BAR-PIS-001");
    });
  });
});
