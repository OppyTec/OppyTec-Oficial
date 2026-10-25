import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import {
  ProductTable,
  ProductMobileCard,
  CategoryTableWrapper,
  type Producto,
  type Categoria,
  ALL_COLUMNS,
  type ColumnKey,
  type BodegaInfo,
} from "../index";

// Mock dataset
const mockCategorias: Categoria[] = [
  { id: "cat-carnes", nombre: "Carnes y Aves", color: "#DC2626", icono: "beef" },
  { id: "cat-lacteos", nombre: "Lácteos y Quesos", color: "#EAB308", icono: "milk" },
];

const mockBodegas: BodegaInfo[] = [
  { id: "bod-central", nombre: "Bodega Principal", color: "#6366F1", icono: "Warehouse" },
  { id: "bod-frio", nombre: "Cámara Fría -18°C", color: "#0284C7", icono: "Snowflake" },
];

const mockBodegaMap: Record<string, BodegaInfo> = {
  "bod-central": { id: "bod-central", nombre: "Bodega Principal", color: "#6366F1", icono: "Warehouse" },
  "bod-frio": { id: "bod-frio", nombre: "Cámara Fría -18°C", color: "#0284C7", icono: "Snowflake" },
};

const mockProductInflated: Producto = {
  id: "prod-inflated",
  nombre: "Queso Parmesano Reggiano",
  categoria_id: "cat-lacteos",
  marca: "Colun",
  unidad: "kg",
  costo_unitario: 12000,
  costo_unitario_ultimo: 12000,
  costo_unitario_penultimo: 10000, // +20% variation -> 🔴 +20.0%
  costo_unitario_ppp: 11000,
  costo_unitario_promedio_10: 10500,
  precio_venta: 18000,
  iva_porcentaje: 19,
  stock_actual: 50,
  contenido_envase: 1,
  contenido_drenado: 0.8,
  unidades_vendidas_mes: 100,
  consumo_diario_promedio: 5,
  estado: "activo",
  bodegas_config: [
    {
      bodega_id: "bod-central",
      stock_minimo: 20,
      stock_actual: 35,
      coordenada_letra: "A",
      coordenada_numero: "1",
    },
    {
      bodega_id: "bod-frio",
      stock_minimo: 30,
      stock_actual: 15, // Low stock: 15 < 30
      coordenada_letra: "B",
      coordenada_numero: "2",
    },
  ],
  presentaciones_compra: [
    {
      nombre: "Caja x10 Queso",
      equivalencia: 10,
      cantidad: 10,
      ultimo_costo: 120000,
      penultimo_costo: 100000,
      costo_bruto: 142800,
    },
  ],
};

const mockProductDeflated: Producto = {
  id: "prod-deflated",
  nombre: "Filete de Vacuno Angus",
  categoria_id: "cat-carnes",
  marca: "Angus Pride",
  unidad: "kg",
  costo_unitario: 15000,
  costo_unitario_ultimo: 15000,
  costo_unitario_penultimo: 20000, // -25% variation -> 🟢 -25.0%
  costo_unitario_ppp: 16000,
  costo_unitario_promedio_10: 17000,
  precio_venta: 26000,
  iva_porcentaje: 19,
  stock_actual: 40,
  contenido_envase: 2,
  unidades_vendidas_mes: 80,
  consumo_diario_promedio: 4,
  estado: "activo",
  bodegas_config: [
    {
      bodega_id: "bod-central",
      stock_minimo: 10,
      stock_actual: 40,
      coordenada_letra: "C",
      coordenada_numero: "3",
    },
  ],
};

const allColumnKeys = ALL_COLUMNS.map((c) => c.key as ColumnKey);

describe("Phase 3 ProductTable & Adaptive Mobile Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. Analytical Columns Rendering (30+ Columns)
  // ==========================================================================
  describe("ProductTable Analytical Columns", () => {
    it("renders all 30+ analytical columns headers and formatted values", () => {
      render(
        <PermissionsProvider>
          <ProductTable
            productos={[mockProductInflated]}
            categorias={mockCategorias}
            bodegas={mockBodegas}
            bodegaMap={mockBodegaMap}
            activeCols={allColumnKeys}
            viewMode="simple"
          />
        </PermissionsProvider>
      );

      // Verify product identification
      expect(screen.getByText("Queso Parmesano Reggiano")).toBeTruthy();

      // 📦 Stock y Logística
      expect(screen.getByText("Principal")).toBeTruthy();
      expect(screen.getByText("A1")).toBeTruthy(); // Ubicacion
      expect(screen.getByText("B2")).toBeTruthy();
      expect(screen.getByText("💧 28 kg")).toBeTruthy(); // Drained liquid indicator

      // 💰 Costos de Compra & Variación Inflacionaria (+20.0%)
      const inflationBadge = screen.getByTestId("inflation-badge-prod-inflated");
      expect(inflationBadge.textContent).toContain("🔴 +20.0%");

      // 🏷️ Ventas y Márgenes
      expect(screen.getByText("Valor Inventario Neto")).toBeTruthy();
      expect(screen.getByText("Días de Cobertura")).toBeTruthy();
      expect(screen.getByText("Índice de Rotación (Mensual)")).toBeTruthy();
    });

    it("renders negative deflationary variation correctly with 🟢 badge", () => {
      render(
        <PermissionsProvider>
          <ProductTable
            productos={[mockProductDeflated]}
            categorias={mockCategorias}
            bodegas={mockBodegas}
            bodegaMap={mockBodegaMap}
            activeCols={["variacion_costo", "ultimo_costo_unidad_neto", "penultimo_costo_unidad_neto"]}
            viewMode="simple"
          />
        </PermissionsProvider>
      );

      const inflationBadge = screen.getByTestId("inflation-badge-prod-deflated");
      expect(inflationBadge.textContent).toContain("🟢 -25.0%");
    });

    it("renders safe fallbacks for missing or null data without blank screens", () => {
      const minimalProduct: Producto = {
        id: "prod-empty",
        nombre: "Insumo Genérico Sin Costos",
        categoria_id: "cat-carnes",
        unidad: "un",
        costo_unitario: 0,
        bodegas_config: [],
      };

      render(
        <PermissionsProvider>
          <ProductTable
            productos={[minimalProduct]}
            categorias={mockCategorias}
            bodegas={mockBodegas}
            bodegaMap={mockBodegaMap}
            activeCols={allColumnKeys}
            viewMode="simple"
          />
        </PermissionsProvider>
      );

      expect(screen.getByText("Insumo Genérico Sin Costos")).toBeTruthy();
      expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    });
  });

  // ==========================================================================
  // 2. Grouping Mode: Grouped by Categories vs Simple Flat List
  // ==========================================================================
  describe("ProductTable Grouping Modes", () => {
    it("renders collapsible category sections with product counts in grouped mode", () => {
      const onToggleCollapse = vi.fn();

      render(
        <PermissionsProvider>
          <ProductTable
            productos={[mockProductInflated, mockProductDeflated]}
            categorias={mockCategorias}
            bodegas={mockBodegas}
            bodegaMap={mockBodegaMap}
            viewMode="grouped"
            onToggleCategoryCollapse={onToggleCollapse}
          />
        </PermissionsProvider>
      );

      // Check category headers
      expect(screen.getByTestId("category-header-cat-carnes")).toBeTruthy();
      expect(screen.getByTestId("category-header-cat-lacteos")).toBeTruthy();

      // Check product count badges
      expect(screen.getByTestId("category-count-cat-carnes").textContent).toContain("1 producto");
      expect(screen.getByTestId("category-count-cat-lacteos").textContent).toContain("1 producto");

      // Click to toggle collapse
      fireEvent.click(screen.getByTestId("category-header-cat-carnes"));
      expect(onToggleCollapse).toHaveBeenCalledWith("cat-carnes");
    });

    it("renders a single flat list when viewMode is 'simple'", () => {
      render(
        <PermissionsProvider>
          <ProductTable
            productos={[mockProductInflated, mockProductDeflated]}
            categorias={mockCategorias}
            bodegas={mockBodegas}
            bodegaMap={mockBodegaMap}
            viewMode="simple"
          />
        </PermissionsProvider>
      );

      expect(screen.getByTestId("product-table-simple")).toBeTruthy();
      expect(screen.queryByTestId("category-header-cat-carnes")).toBeNull();
      expect(screen.getByText("Queso Parmesano Reggiano")).toBeTruthy();
      expect(screen.getByText("Filete de Vacuno Angus")).toBeTruthy();
    });
  });

  // ==========================================================================
  // 3. Actions & RBAC Guards (<Can>)
  // ==========================================================================
  describe("ProductTable Actions & Permissions", () => {
    it("triggers onEdit callback when clicking edit button", () => {
      const onEdit = vi.fn();

      render(
        <PermissionsProvider>
          <ProductTable
            productos={[mockProductInflated]}
            categorias={mockCategorias}
            bodegas={mockBodegas}
            bodegaMap={mockBodegaMap}
            viewMode="simple"
            onEdit={onEdit}
          />
        </PermissionsProvider>
      );

      const editBtn = screen.getByTestId("edit-product-btn-prod-inflated");
      fireEvent.click(editBtn);

      expect(onEdit).toHaveBeenCalledWith(mockProductInflated);
    });

    it("opens delete confirmation modal and calls onDelete when confirmed", () => {
      const onDelete = vi.fn();

      render(
        <PermissionsProvider>
          <ProductTable
            productos={[mockProductInflated]}
            categorias={mockCategorias}
            bodegas={mockBodegas}
            bodegaMap={mockBodegaMap}
            viewMode="simple"
            onDelete={onDelete}
          />
        </PermissionsProvider>
      );

      // Click delete button on row
      const deleteBtn = screen.getByTestId("delete-product-btn-prod-inflated");
      fireEvent.click(deleteBtn);

      // Confirm dialog should open
      expect(screen.getByText("Confirmar Eliminación")).toBeTruthy();
      expect(screen.getByTestId("confirm-delete-btn")).toBeTruthy();

      // Click confirm delete
      fireEvent.click(screen.getByTestId("confirm-delete-btn"));
      expect(onDelete).toHaveBeenCalledWith(mockProductInflated);
    });
  });

  // ==========================================================================
  // 4. ProductMobileCard Component Tests
  // ==========================================================================
  describe("ProductMobileCard Component", () => {
    it("renders collapsed mobile card with touch targets >= 44px and expands accordion on click", () => {
      const onToggleExpand = vi.fn();
      const onEdit = vi.fn();
      const onDelete = vi.fn();

      const { rerender } = render(
        <PermissionsProvider>
          <ProductMobileCard
            product={mockProductInflated}
            bodegas={mockBodegas}
            bodegaMap={mockBodegaMap}
            isExpanded={false}
            onToggleExpand={onToggleExpand}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        </PermissionsProvider>
      );

      // Check header info
      expect(screen.getByText("Queso Parmesano Reggiano")).toBeTruthy();
      const headerBtn = screen.getByTestId("product-mobile-header-prod-inflated");
      expect(headerBtn).toBeTruthy();

      // Click header
      fireEvent.click(headerBtn);
      expect(onToggleExpand).toHaveBeenCalledTimes(1);

      // Rerender as expanded
      rerender(
        <PermissionsProvider>
          <ProductMobileCard
            product={mockProductInflated}
            bodegas={mockBodegas}
            bodegaMap={mockBodegaMap}
            isExpanded={true}
            onToggleExpand={onToggleExpand}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        </PermissionsProvider>
      );

      // Expanded content is now visible
      expect(screen.getByTestId("product-mobile-content-prod-inflated")).toBeTruthy();
      expect(screen.getByText("Desglose por Bodega")).toBeTruthy();
      expect(screen.getByText("Costos, Precios y Rentabilidad")).toBeTruthy();

      // Check bodega breakdown
      expect(screen.getByTestId("mobile-bodega-row-bod-central")).toBeTruthy();
      expect(screen.getByTestId("mobile-bodega-row-bod-frio")).toBeTruthy();

      // Check mobile action buttons
      const mobileEditBtn = screen.getByTestId("mobile-edit-btn-prod-inflated");
      const mobileDeleteBtn = screen.getByTestId("mobile-delete-btn-prod-inflated");
      expect(mobileEditBtn).toBeTruthy();
      expect(mobileDeleteBtn).toBeTruthy();

      fireEvent.click(mobileEditBtn);
      expect(onEdit).toHaveBeenCalledWith(mockProductInflated);

      fireEvent.click(mobileDeleteBtn);
      expect(onDelete).toHaveBeenCalledWith(mockProductInflated);
    });
  });

  // ==========================================================================
  // 5. CategoryTableWrapper Scroll Sync & Wheel Pan Tests
  // ==========================================================================
  describe("CategoryTableWrapper Component", () => {
    it("registers container ref and calls onHorizontalScroll", () => {
      const registerContainer = vi.fn();
      const onHorizontalScroll = vi.fn();

      render(
        <CategoryTableWrapper
          catId="cat-test"
          activeCols={[{ key: "costo", label: "Costo" }]}
          minTableWidth={500}
          columnWidths={{ costo: "w-[120px]" }}
          getColWidthPx={() => 120}
          registerContainer={registerContainer}
          onHorizontalScroll={onHorizontalScroll}
        >
          <tr>
            <td>Test Row</td>
          </tr>
        </CategoryTableWrapper>
      );

      expect(registerContainer).toHaveBeenCalledWith("cat-test", expect.anything());

      const bodyContainer = screen.getByTestId("category-table-body-cat-test");
      fireEvent.scroll(bodyContainer, { target: { scrollLeft: 100 } });

      expect(onHorizontalScroll).toHaveBeenCalledWith(100, "cat-test");
    });
  });
});
