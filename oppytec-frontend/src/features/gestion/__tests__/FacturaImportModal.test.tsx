// oppytec-frontend/src/features/gestion/__tests__/FacturaImportModal.test.tsx
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  FacturaImportModal,
  FACTURA_DRAFT_KEY,
} from "../components/FacturaImportModal/FacturaImportModal";
import {
  FacturaSupplierBanner,
  type FacturaSupplierInfo,
} from "../components/FacturaImportModal/FacturaSupplierBanner";
import {
  UnidadMedidaCombobox,
} from "../components/FacturaImportModal/UnidadMedidaCombobox";
import {
  FacturaReviewGrid,
  type FacturaParsedLine,
} from "../components/FacturaImportModal/FacturaReviewGrid";
import type { Producto } from "../types";

// Mock API Client to avoid unhandled network errors
vi.mock("@/shared/api/httpClient", () => ({
  apiRequest: vi.fn().mockImplementation((url: string) => {
    if (url.includes("/inventory/import/parse-invoice")) {
      return Promise.resolve({
        data: {
          supplier: {
            rut: "76.890.123-4",
            razonSocial: "Distribuidora Gastronómica Los Andes SpA",
            giro: "Distribución Mayorista de Alimentos y Bebidas",
            folio: "54291",
            fechaEmision: "2026-10-24",
            montoNeto: 185000,
            montoIva: 35150,
            montoTotal: 220150,
          },
          lines: [
            {
              id: "fline-1",
              codigo: "CAR-LOM-001",
              descripcion: "Lomo Vetado Angus Premium",
              cantidad: 10,
              unidad: "kg",
              factor_conversion: 1,
              precio_unitario: 14500,
              total_linea: 145000,
              producto_asociado_id: "prod-1",
              bodega_id: "bod-central",
            },
            {
              id: "fline-2",
              codigo: "LAC-LEC-004",
              descripcion: "Leche Entera Colun 1L Tetra Brik",
              cantidad: 40,
              unidad: "un",
              factor_conversion: 1,
              precio_unitario: 1000,
              total_linea: 40000,
              producto_asociado_id: "prod-2",
              bodega_id: "bod-central",
            },
          ],
        },
      });
    }
    if (url.includes("/inventory/import/confirm-invoice")) {
      return Promise.resolve({
        data: {
          success: true,
          folio: "54291",
          lines_count: 2,
        },
      });
    }
    return Promise.resolve({ data: {} });
  }),
}));

const MOCK_SUPPLIER: FacturaSupplierInfo = {
  rut: "76.890.123-4",
  razonSocial: "Distribuidora Gastronómica Los Andes SpA",
  giro: "Distribución Mayorista de Alimentos y Bebidas",
  folio: "54291",
  fechaEmision: "2026-10-24",
  montoNeto: 185000,
  montoIva: 35150,
  montoTotal: 220150,
};

const MOCK_PRODUCTS: Producto[] = [
  {
    id: "prod-1",
    nombre: "Lomo Vetado Angus Premium",
    sku: "CAR-LOM-001",
    categoria_id: "cat-carnes",
    unidad: "kg",
    costo_unitario: 14500,
    bodegas_config: [{ bodega_id: "bod-central", stock_minimo: 10, stock_actual: 20 }],
  },
  {
    id: "prod-2",
    nombre: "Leche Entera Colun 1L Tetra Brik",
    sku: "LAC-LEC-004",
    categoria_id: "cat-lacteos",
    unidad: "un",
    costo_unitario: 1000,
    bodegas_config: [{ bodega_id: "bod-central", stock_minimo: 20, stock_actual: 100 }],
  },
];

const MOCK_LINES: FacturaParsedLine[] = [
  {
    id: "line-1",
    codigo: "CAR-LOM-001",
    descripcion: "Lomo Vetado Angus Premium Corte Americano",
    cantidad: 10,
    unidad: "kg",
    factor_conversion: 1,
    precio_unitario: 14500,
    total_linea: 145000,
    producto_asociado_id: "prod-1",
    bodega_id: "bod-central",
  },
  {
    id: "line-2",
    codigo: "NEW-VIN-999",
    descripcion: "Vino Reserva Especial Syrah",
    cantidad: 6,
    unidad: "bot",
    factor_conversion: 1,
    precio_unitario: 8900,
    total_linea: 53400,
    producto_asociado_id: "__new__",
    bodega_id: "bod-central",
  },
];

describe("Fase 6: FacturaImportModal Suite (Facturas PDF / XML DTE IA)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. FacturaSupplierBanner
  // ==========================================================================
  describe("1. FacturaSupplierBanner Component", () => {
    it("renders supplier info, folio, emission date, and financial amounts", () => {
      render(<FacturaSupplierBanner supplier={MOCK_SUPPLIER} isNewSupplier={false} />);

      expect(screen.getByTestId("factura-supplier-banner")).toBeDefined();
      expect(screen.getByText("Distribuidora Gastronómica Los Andes SpA")).toBeDefined();
      expect(screen.getByText("RUT: 76.890.123-4")).toBeDefined();
      expect(screen.getByText("Factura N° 54291")).toBeDefined();
      expect(screen.getByText("2026-10-24")).toBeDefined();
      expect(screen.getByText("$185.000")).toBeDefined();
      expect(screen.getByText("$220.150")).toBeDefined();
      expect(screen.getByText("Registrado")).toBeDefined();
    });

    it("renders quick register action when supplier is not registered", () => {
      const onRegister = vi.fn();
      render(
        <FacturaSupplierBanner
          supplier={MOCK_SUPPLIER}
          isNewSupplier={true}
          onRegisterSupplier={onRegister}
        />
      );

      expect(screen.getByText("Nuevo Proveedor")).toBeDefined();
      const btnRegister = screen.getByTestId("btn-register-supplier");
      expect(btnRegister).toBeDefined();

      fireEvent.click(btnRegister);
      expect(onRegister).toHaveBeenCalledWith(MOCK_SUPPLIER);
    });
  });

  // ==========================================================================
  // 2. UnidadMedidaCombobox
  // ==========================================================================
  describe("2. UnidadMedidaCombobox Component", () => {
    it("renders initial unit and lists common measurement units", () => {
      const onChange = vi.fn();
      render(<UnidadMedidaCombobox value="kg" factor={1} onChange={onChange} />);

      const trigger = screen.getByTestId("unidad-combobox-trigger");
      expect(trigger).toBeDefined();
      expect(screen.getByText("kg")).toBeDefined();

      // Open dropdown
      fireEvent.click(trigger);
      expect(screen.getByTestId("unidad-combobox-dropdown")).toBeDefined();

      // Verify some units exist in dropdown
      expect(screen.getByTestId("unit-opt-kg")).toBeDefined();
      expect(screen.getByTestId("unit-opt-caja")).toBeDefined();
      expect(screen.getByTestId("unit-opt-pack")).toBeDefined();
    });

    it("triggers onChange with symbol and default factor when selecting a unit", () => {
      const onChange = vi.fn();
      render(<UnidadMedidaCombobox value="un" factor={1} onChange={onChange} />);

      fireEvent.click(screen.getByTestId("unidad-combobox-trigger"));

      // Click 'caja' option (default factor 12)
      fireEvent.click(screen.getByTestId("unit-opt-caja"));
      expect(onChange).toHaveBeenCalledWith("caja", 12);
    });

    it("respects disabled state", () => {
      const onChange = vi.fn();
      render(<UnidadMedidaCombobox value="L" disabled={true} onChange={onChange} />);

      const trigger = screen.getByTestId("unidad-combobox-trigger");
      expect(trigger.getAttribute("disabled")).not.toBeNull();
      fireEvent.click(trigger);
      expect(screen.queryByTestId("unidad-combobox-dropdown")).toBeNull();
    });
  });

  // ==========================================================================
  // 3. FacturaReviewGrid
  // ==========================================================================
  describe("3. FacturaReviewGrid Component", () => {
    it("renders invoice lines with computed totals, matched and new badges", () => {
      render(
        <FacturaReviewGrid
          lines={MOCK_LINES}
          productos={MOCK_PRODUCTS}
          onUpdateLine={vi.fn()}
          onDeleteLine={vi.fn()}
        />
      );

      expect(screen.getByTestId("factura-review-grid")).toBeDefined();
      expect(screen.getByTestId("factura-line-row-line-1")).toBeDefined();
      expect(screen.getByTestId("factura-line-row-line-2")).toBeDefined();

      // Check badge counts: 1 matched, 1 new
      expect(screen.getByText("1 Asociados al Catálogo")).toBeDefined();
      expect(screen.getByText("1 Nuevos a Crear")).toBeDefined();

      // Check computed total: 10 * 14500 + 6 * 8900 = 145000 + 53400 = 198400
      expect(screen.getByText("$198.400 CLP")).toBeDefined();
    });

    it("supports search filter on invoice lines", () => {
      render(
        <FacturaReviewGrid
          lines={MOCK_LINES}
          productos={MOCK_PRODUCTS}
          onUpdateLine={vi.fn()}
          onDeleteLine={vi.fn()}
        />
      );

      const searchInput = screen.getByTestId("input-factura-search");
      fireEvent.change(searchInput, { target: { value: "Syrah" } });

      expect(screen.queryByTestId("factura-line-row-line-1")).toBeNull();
      expect(screen.getByTestId("factura-line-row-line-2")).toBeDefined();
    });

    it("handles field updates and row deletions", () => {
      const onUpdateLine = vi.fn();
      const onDeleteLine = vi.fn();

      render(
        <FacturaReviewGrid
          lines={MOCK_LINES}
          productos={MOCK_PRODUCTS}
          onUpdateLine={onUpdateLine}
          onDeleteLine={onDeleteLine}
        />
      );

      // Edit description
      const descInput = screen.getByTestId("input-line-desc-line-1");
      fireEvent.change(descInput, { target: { value: "Lomo Vetado Premium Modificado" } });
      expect(onUpdateLine).toHaveBeenCalledWith(
        "line-1",
        "descripcion",
        "Lomo Vetado Premium Modificado"
      );

      // Edit quantity
      const qtyInput = screen.getByTestId("input-line-qty-line-1");
      fireEvent.change(qtyInput, { target: { value: "15" } });
      expect(onUpdateLine).toHaveBeenCalledWith("line-1", "cantidad", 15);

      // Change product match
      const selectMatch = screen.getByTestId("select-product-match-line-1");
      fireEvent.change(selectMatch, { target: { value: "__new__" } });
      expect(onUpdateLine).toHaveBeenCalledWith("line-1", "producto_asociado_id", "__new__");

      // Delete line
      const btnDelete = screen.getByTestId("btn-delete-line-line-1");
      fireEvent.click(btnDelete);
      expect(onDeleteLine).toHaveBeenCalledWith("line-1");
    });
  });

  // ==========================================================================
  // 4. FacturaImportModal Lifecycle & Workflow
  // ==========================================================================
  describe("4. FacturaImportModal Workflow", () => {
    it("renders stage 1 upload dropzone", () => {
      render(
        <FacturaImportModal
          open={true}
          onOpenChange={vi.fn()}
          productos={MOCK_PRODUCTS}
        />
      );

      expect(screen.getByTestId("factura-import-modal")).toBeDefined();
      expect(screen.getByTestId("factura-stage-upload")).toBeDefined();
      expect(screen.getByTestId("factura-dropzone")).toBeDefined();
    });

    it("processes uploaded invoice document and transitions to review stage", async () => {
      render(
        <FacturaImportModal
          open={true}
          onOpenChange={vi.fn()}
          productos={MOCK_PRODUCTS}
        />
      );

      const file = new File(["%PDF-1.4 mock content"], "factura_proveedor.pdf", {
        type: "application/pdf",
      });

      const fileInput = screen.getByTestId("input-factura-file");
      fireEvent.change(fileInput, { target: { files: [file] } });

      // Wait for transition to review stage
      await waitFor(() => {
        expect(screen.getByTestId("factura-stage-review")).toBeDefined();
      });

      expect(screen.getByTestId("factura-supplier-banner")).toBeDefined();
      expect(screen.getByTestId("factura-review-grid")).toBeDefined();
      expect(screen.getByTestId("select-factura-bodega")).toBeDefined();
      expect(screen.getByTestId("btn-confirm-factura-import")).toBeDefined();
    });

    it("can navigate back to upload stage via reupload button", async () => {
      render(
        <FacturaImportModal
          open={true}
          onOpenChange={vi.fn()}
          productos={MOCK_PRODUCTS}
        />
      );

      const file = new File(["mock xml dte"], "dte_sii.xml", {
        type: "application/xml",
      });
      fireEvent.change(screen.getByTestId("input-factura-file"), { target: { files: [file] } });

      await waitFor(() => {
        expect(screen.getByTestId("factura-stage-review")).toBeDefined();
      });

      // Click reupload
      const btnReupload = screen.getByTestId("btn-reupload-factura");
      fireEvent.click(btnReupload);

      expect(screen.getByTestId("factura-stage-upload")).toBeDefined();
    });

    it("confirms invoice, updates stock, invokes callback, and closes dialog", async () => {
      const onInvoiceConfirmed = vi.fn();
      const onOpenChange = vi.fn();

      render(
        <FacturaImportModal
          open={true}
          onOpenChange={onOpenChange}
          productos={MOCK_PRODUCTS}
          onInvoiceConfirmed={onInvoiceConfirmed}
        />
      );

      const file = new File(["mock invoice"], "factura.pdf", { type: "application/pdf" });
      fireEvent.change(screen.getByTestId("input-factura-file"), { target: { files: [file] } });

      await waitFor(() => {
        expect(screen.getByTestId("btn-confirm-factura-import")).toBeDefined();
      });

      fireEvent.click(screen.getByTestId("btn-confirm-factura-import"));

      await waitFor(() => {
        expect(onInvoiceConfirmed).toHaveBeenCalled();
        expect(onOpenChange).toHaveBeenCalledWith(false);
      });
    });
  });

  // ==========================================================================
  // 5. FacturaImportModal LocalStorage Draft Persistence
  // ==========================================================================
  describe("5. FacturaImportModal LocalStorage Draft Persistence", () => {
    it("renders restore draft alert if draft exists in localStorage", () => {
      const mockDraft = {
        fileName: "factura_guardada.pdf",
        supplier: MOCK_SUPPLIER,
        lines: MOCK_LINES,
        bodegaId: "bod-central",
        timestamp: new Date().toISOString(),
      };
      window.localStorage.setItem(FACTURA_DRAFT_KEY, JSON.stringify(mockDraft));

      render(
        <FacturaImportModal
          open={true}
          onOpenChange={vi.fn()}
          productos={MOCK_PRODUCTS}
        />
      );

      expect(screen.getByTestId("btn-restore-factura-draft")).toBeDefined();
      expect(screen.getByTestId("btn-discard-factura-draft")).toBeDefined();
    });

    it("restores draft into review stage when clicking restore", () => {
      const mockDraft = {
        fileName: "factura_guardada.pdf",
        supplier: MOCK_SUPPLIER,
        lines: MOCK_LINES,
        bodegaId: "bod-cocina",
        timestamp: new Date().toISOString(),
      };
      window.localStorage.setItem(FACTURA_DRAFT_KEY, JSON.stringify(mockDraft));

      render(
        <FacturaImportModal
          open={true}
          onOpenChange={vi.fn()}
          productos={MOCK_PRODUCTS}
        />
      );

      fireEvent.click(screen.getByTestId("btn-restore-factura-draft"));

      expect(screen.getByTestId("factura-stage-review")).toBeDefined();
      expect(screen.getByText("Distribuidora Gastronómica Los Andes SpA")).toBeDefined();
    });

    it("discards draft and removes it from localStorage", () => {
      const mockDraft = {
        fileName: "factura_guardada.pdf",
        supplier: MOCK_SUPPLIER,
        lines: MOCK_LINES,
        bodegaId: "bod-cocina",
        timestamp: new Date().toISOString(),
      };
      window.localStorage.setItem(FACTURA_DRAFT_KEY, JSON.stringify(mockDraft));

      render(
        <FacturaImportModal
          open={true}
          onOpenChange={vi.fn()}
          productos={MOCK_PRODUCTS}
        />
      );

      fireEvent.click(screen.getByTestId("btn-discard-factura-draft"));

      expect(window.localStorage.getItem(FACTURA_DRAFT_KEY)).toBeNull();
      expect(screen.queryByTestId("btn-restore-factura-draft")).toBeNull();
    });
  });
});
