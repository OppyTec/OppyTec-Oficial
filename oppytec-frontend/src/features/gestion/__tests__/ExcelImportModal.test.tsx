// oppytec-frontend/src/features/gestion/__tests__/ExcelImportModal.test.tsx
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  ExcelImportModal,
  EXCEL_DRAFT_KEY,
} from "../components/ExcelImportModal/ExcelImportModal";
import {
  ExcelColumnMatcher,
  detectColumnMatch,
  autoMapExcelHeaders,
  TARGET_CATALOG_FIELDS,
} from "../components/ExcelImportModal/ExcelColumnMatcher";
import { ExcelEntityMatcherBanner } from "../components/ExcelImportModal/ExcelEntityMatcherBanner";
import {
  ExcelImportReviewGrid,
  validateProductRow,
  type ParsedProductRow,
} from "../components/ExcelImportModal/ExcelImportReviewGrid";
import {
  downloadExcelTemplate,
  sanitizeSpreadsheetFormula,
  EXCEL_TEMPLATE_COLUMNS,
  SAMPLE_TEMPLATE_ROWS,
} from "../components/ExcelImportModal/ExcelTemplateDownloader";

import type { Categoria, Marca } from "../types";

const MOCK_CATEGORIAS: Categoria[] = [
  { id: "cat-carnes", nombre: "Carnes y Aves", color: "#DC2626", icono: "beef" },
  { id: "cat-bebidas", nombre: "Vinos y Licores", color: "#7C3AED", icono: "wine" },
];

const MOCK_MARCAS: Marca[] = [
  { id: "marca-angus", nombre: "Angus Pride" },
  { id: "marca-concha", nombre: "Concha y Toro" },
];

const MOCK_ROWS: ParsedProductRow[] = [
  {
    id: "r1",
    nombre: "Lomo Vetado Angus",
    sku: "CAR-LOM-001",
    codigo_barra: "7801234567890",
    categoria: "Carnes y Aves",
    marca: "Angus Pride",
    unidad_base: "kg",
    tipo_envase: "Bolsa al Vacío",
    costo_neto: 14500,
    precio_venta_neto: 22900,
    stock_actual: 25,
    stock_minimo: 10,
    bodega: "Bodega Central",
  },
  {
    id: "r2",
    nombre: "Vino Cabernet Sauvignon",
    sku: "",
    codigo_barra: "",
    categoria: "Vinos y Licores",
    marca: "Concha y Toro",
    unidad_base: "botella",
    tipo_envase: "Botella",
    costo_neto: 5200,
    precio_venta_neto: 14900,
    stock_actual: 0, // warning stock 0 & no sku
    stock_minimo: 5,
    bodega: "Bodega Central",
  },
  {
    id: "r3",
    nombre: "", // error: empty name
    sku: "ERR-001",
    codigo_barra: "",
    categoria: "Carnes y Aves",
    marca: "Angus Pride",
    unidad_base: "kg",
    tipo_envase: "Bolsa",
    costo_neto: -100, // error: negative cost
    precio_venta_neto: 0,
    stock_actual: 5,
    stock_minimo: 2,
    bodega: "Bodega Central",
  },
];

describe("Fase 6: ExcelImportModal Suite (Excel / CSV IA)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
  });

  // ==========================================================================
  // 1. Template Downloader
  // ==========================================================================
  describe("1. ExcelTemplateDownloader Utility", () => {
    it("defines 16 canonical ERP template columns with examples", () => {
      expect(EXCEL_TEMPLATE_COLUMNS.length).toBe(16);
      const keys = EXCEL_TEMPLATE_COLUMNS.map((c) => c.key);
      expect(keys).toContain("nombre");
      expect(keys).toContain("sku");
      expect(keys).toContain("categoria");
      expect(keys).toContain("costo_unitario_neto");
      expect(keys).toContain("precio_venta_neto");
      expect(SAMPLE_TEMPLATE_ROWS.length).toBeGreaterThanOrEqual(3);
    });

    it("triggers CSV download creating blob link and clicking", () => {
      const createElementSpy = vi.spyOn(document, "createElement");
      const appendSpy = vi.spyOn(document.body, "appendChild");
      const removeSpy = vi.spyOn(document.body, "removeChild");

      // Mock URL.createObjectURL and revokeObjectURL
      const mockUrl = "blob:http://localhost/mock-template";
      window.URL.createObjectURL = vi.fn().mockReturnValue(mockUrl);
      window.URL.revokeObjectURL = vi.fn();

      downloadExcelTemplate("csv", "test_template");

      expect(createElementSpy).toHaveBeenCalledWith("a");
      expect(appendSpy).toHaveBeenCalled();
      expect(removeSpy).toHaveBeenCalled();
      expect(window.URL.revokeObjectURL).toHaveBeenCalledWith(mockUrl);
    });
  });

  // ==========================================================================
  // 2. Column Matcher
  // ==========================================================================
  describe("2. ExcelColumnMatcher Component & Heuristics", () => {
    it("detects exact and suggested matches accurately", () => {
      const nombreDef = TARGET_CATALOG_FIELDS.find((f) => f.key === "nombre")!;
      expect(detectColumnMatch("Nombre Comercial", nombreDef)).toBe("exact");
      expect(detectColumnMatch("Articulo", nombreDef)).toBe("exact");
      expect(detectColumnMatch("Nombre_Prod", nombreDef)).toBe("suggested");
      expect(detectColumnMatch("ColumnaInexistente", nombreDef)).toBe("none");

      const costoDef = TARGET_CATALOG_FIELDS.find((f) => f.key === "costo_neto")!;
      expect(detectColumnMatch("Costo Unitario", costoDef)).toBe("exact");
      expect(detectColumnMatch("Precio Compra", costoDef)).toBe("exact");
    });

    it("autoMaps headers automatically", () => {
      const headers = ["Nombre Comercial", "SKU", "Categoría", "Costo", "Existencias", "Extra"];
      const mappings = autoMapExcelHeaders(headers);

      expect(mappings.nombre).toBe("Nombre Comercial");
      expect(mappings.sku).toBe("SKU");
      expect(mappings.categoria).toBe("Categoría");
      expect(mappings.costo_neto).toBe("Costo");
      expect(mappings.stock_actual).toBe("Existencias");
      expect(mappings.extra).toBeUndefined();
    });

    it("renders column matcher with required status and handles selection", () => {
      const onMappingChange = vi.fn();
      const headers = ["Nombre", "SKU", "Categoria", "Costo"];

      render(
        <ExcelColumnMatcher
          excelHeaders={headers}
          mappings={{ nombre: "Nombre", categoria: "Categoria" }}
          onMappingChange={onMappingChange}
          previewRows={[{ Nombre: "Lomo", SKU: "LOM-1", Categoria: "Carnes", Costo: "10000" }]}
        />
      );

      expect(screen.getByTestId("excel-column-matcher")).toBeDefined();
      expect(screen.getByTestId("matcher-required-status")).toBeDefined();

      // Change mapping for costo_neto
      const selectCosto = screen.getByTestId("select-mapping-costo_neto");
      fireEvent.change(selectCosto, { target: { value: "Costo" } });

      expect(onMappingChange).toHaveBeenCalledWith("costo_neto", "Costo");
    });
  });

  // ==========================================================================
  // 3. Entity Matcher Banner
  // ==========================================================================
  describe("3. ExcelEntityMatcherBanner Component", () => {
    it("shows success badge when all categories and brands already exist", () => {
      render(
        <ExcelEntityMatcherBanner
          detectedCategories={["Carnes y Aves"]}
          detectedBrands={["Angus Pride"]}
          existingCategories={MOCK_CATEGORIAS}
          existingBrands={MOCK_MARCAS}
          categoryMappings={{}}
          brandMappings={{}}
          onCategoryMappingChange={vi.fn()}
          onBrandMappingChange={vi.fn()}
          onAutoCreateAll={vi.fn()}
        />
      );

      expect(screen.getByTestId("excel-entity-all-matched")).toBeDefined();
      expect(screen.getByText(/Todas las categorías/i)).toBeDefined();
    });

    it("alerts when new categories and brands are detected and triggers auto-create", () => {
      const onAutoCreateAll = vi.fn();
      const onCatChange = vi.fn();

      render(
        <ExcelEntityMatcherBanner
          detectedCategories={["Carnes y Aves", "Postres y Dulces"]}
          detectedBrands={["Angus Pride", "Nestlé"]}
          existingCategories={MOCK_CATEGORIAS}
          existingBrands={MOCK_MARCAS}
          categoryMappings={{}}
          brandMappings={{}}
          onCategoryMappingChange={onCatChange}
          onBrandMappingChange={vi.fn()}
          onAutoCreateAll={onAutoCreateAll}
        />
      );

      expect(screen.getByTestId("excel-entity-matcher-banner")).toBeDefined();
      expect(screen.getByTestId("entity-row-cat-Postres y Dulces")).toBeDefined();
      expect(screen.getByTestId("entity-row-brand-Nestlé")).toBeDefined();

      // Click auto create all
      fireEvent.click(screen.getByTestId("btn-auto-create-entities"));
      expect(onAutoCreateAll).toHaveBeenCalledTimes(1);

      // Select mapping for new category
      const selectCat = screen.getByTestId("select-cat-mapping-Postres y Dulces");
      fireEvent.change(selectCat, { target: { value: "cat-carnes" } });
      expect(onCatChange).toHaveBeenCalledWith("Postres y Dulces", "cat-carnes");
    });
  });

  // ==========================================================================
  // 4. Review Grid
  // ==========================================================================
  describe("4. ExcelImportReviewGrid Component", () => {
    it("validates rows properly (valid, warning, error)", () => {
      expect(validateProductRow(MOCK_ROWS[0]!).status).toBe("valid");
      expect(validateProductRow(MOCK_ROWS[1]!).status).toBe("warning");
      expect(validateProductRow(MOCK_ROWS[2]!).status).toBe("error");
    });

    it("renders grid, supports inline edits and toggles Neto/Bruto view mode", () => {
      const onUpdateRow = vi.fn();
      const onDeleteRow = vi.fn();

      render(
        <ExcelImportReviewGrid
          rows={MOCK_ROWS}
          onUpdateRow={onUpdateRow}
          onDeleteRow={onDeleteRow}
          ivaPorcentaje={19}
        />
      );

      expect(screen.getByTestId("excel-import-review-grid")).toBeDefined();
      expect(screen.getByTestId("grid-row-r1")).toBeDefined();

      // Edit name
      const inputNombre = screen.getByTestId("input-grid-nombre-r1");
      fireEvent.change(inputNombre, { target: { value: "Lomo Vetado Premium" } });
      expect(onUpdateRow).toHaveBeenCalledWith("r1", "nombre", "Lomo Vetado Premium");

      // Toggle to Bruto view
      const btnBruto = screen.getByTestId("btn-grid-view-bruto");
      fireEvent.click(btnBruto);

      // Switch back to Neto view
      const btnNeto = screen.getByTestId("btn-grid-view-neto");
      fireEvent.click(btnNeto);

      // Delete row r3
      const btnDelete = screen.getByTestId("btn-delete-row-r3");
      fireEvent.click(btnDelete);
      expect(onDeleteRow).toHaveBeenCalledWith("r3");
    });

    it("filters rows by status chips and search input", () => {
      render(
        <ExcelImportReviewGrid
          rows={MOCK_ROWS}
          onUpdateRow={vi.fn()}
          onDeleteRow={vi.fn()}
        />
      );

      // Filter by Error
      fireEvent.click(screen.getByTestId("filter-chip-error"));
      expect(screen.queryByTestId("grid-row-r1")).toBeNull();
      expect(screen.getByTestId("grid-row-r3")).toBeDefined();

      // Search input
      const inputSearch = screen.getByTestId("input-grid-search");
      fireEvent.change(inputSearch, { target: { value: "Vino" } });
      // When searching "Vino" with filter error, 0 results
      expect(screen.getByText(/No hay filas que coincidan/i)).toBeDefined();

      // Clear filter to all
      fireEvent.click(screen.getByTestId("filter-chip-all"));
      expect(screen.getByTestId("grid-row-r2")).toBeDefined();
    });
  });

  // ==========================================================================
  // 5. ExcelImportModal Pipeline & Drafting
  // ==========================================================================
  describe("5. ExcelImportModal 5-Step Pipeline & Drafting", () => {
    it("renders step 1 upload dropzone and can download template", () => {
      const onOpenChange = vi.fn();

      render(
        <ExcelImportModal
          open={true}
          onOpenChange={onOpenChange}
          categorias={MOCK_CATEGORIAS}
          marcas={MOCK_MARCAS}
          initialStep={1}
        />
      );

      expect(screen.getByTestId("excel-import-modal")).toBeDefined();
      expect(screen.getByTestId("excel-dropzone")).toBeDefined();
      expect(screen.getByTestId("btn-download-template")).toBeDefined();
    });

    it("navigates through steps and confirms import on step 5", async () => {
      const onImportComplete = vi.fn();
      const onOpenChange = vi.fn();

      render(
        <ExcelImportModal
          open={true}
          onOpenChange={onOpenChange}
          categorias={MOCK_CATEGORIAS}
          marcas={MOCK_MARCAS}
          onImportComplete={onImportComplete}
          initialStep={5}
        />
      );

      expect(screen.getByTestId("step-5-confirm")).toBeDefined();
      expect(screen.getByTestId("select-import-target-bodega")).toBeDefined();

      // Go back to step 4
      fireEvent.click(screen.getByTestId("btn-prev-excel-step"));
      expect(screen.getByTestId("step-4-review")).toBeDefined();

      // Go forward to step 5
      fireEvent.click(screen.getByTestId("btn-next-excel-step"));
      expect(screen.getByTestId("step-5-confirm")).toBeDefined();
    });

    it("saves draft to localStorage and supports restore/discard", async () => {
      const mockDraft = {
        fileName: "test_draft.csv",
        step: 4,
        headers: ["Nombre", "Categoria", "Costo"],
        mappings: { nombre: "Nombre", categoria: "Categoria", costo_neto: "Costo" },
        rows: MOCK_ROWS,
        timestamp: new Date().toISOString(),
      };

      window.localStorage.setItem(EXCEL_DRAFT_KEY, JSON.stringify(mockDraft));

      render(
        <ExcelImportModal
          open={true}
          onOpenChange={vi.fn()}
          categorias={MOCK_CATEGORIAS}
          marcas={MOCK_MARCAS}
          initialStep={1}
        />
      );

      expect(screen.getByTestId("btn-restore-excel-draft")).toBeDefined();

      // Restore draft
      fireEvent.click(screen.getByTestId("btn-restore-excel-draft"));
      expect(screen.getByTestId("step-4-review")).toBeDefined();
    });
  });

  // ==========================================================================
  // 6. Security: Anti-Formula Injection (CWE-1236)
  // ==========================================================================
  describe("6. Spreadsheet Formula Sanitization (CWE-1236)", () => {
    it("neutralizes dangerous formula triggers by prepending single quote", () => {
      expect(sanitizeSpreadsheetFormula("=SUM(A1:A10)")).toBe("'=SUM(A1:A10)");
      expect(sanitizeSpreadsheetFormula("@SUM(1,2)")).toBe("'@SUM(1,2)");
      expect(sanitizeSpreadsheetFormula("+12345")).toBe("'+12345");
      expect(sanitizeSpreadsheetFormula("-100")).toBe("'-100");
      expect(sanitizeSpreadsheetFormula("\tcmd")).toBe("'\tcmd");
      expect(sanitizeSpreadsheetFormula("\rcmd")).toBe("'\rcmd");
      expect(sanitizeSpreadsheetFormula("   =EVIL()")).toBe("'   =EVIL()");
    });

    it("leaves safe text unchanged", () => {
      expect(sanitizeSpreadsheetFormula("Lomo Vetado Angus")).toBe("Lomo Vetado Angus");
      expect(sanitizeSpreadsheetFormula("CAR-LOM-001")).toBe("CAR-LOM-001");
      expect(sanitizeSpreadsheetFormula(14500)).toBe("14500");
      expect(sanitizeSpreadsheetFormula("")).toBe("");
      expect(sanitizeSpreadsheetFormula(null as unknown as string)).toBe("");
    });
  });
});
