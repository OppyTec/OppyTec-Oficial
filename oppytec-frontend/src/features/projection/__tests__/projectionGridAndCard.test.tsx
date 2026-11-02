/**
 * oppytec-frontend/src/features/projection/__tests__/projectionGridAndCard.test.tsx
 * Pruebas Unitarias y de Integración UI para ProyeccionProductCard y ProyeccionProductGrid.
 * Cobertura completa: estados de urgencia (critical, warning, normal), ADN Visual (#ef4444, #f59e0b, #10b981),
 * interacción táctil y por teclado, skeletons de carga, estado vacío con reseteo y agrupación por categorías.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import "@testing-library/jest-dom";
import type { ReactNode, HTMLAttributes } from "react";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  ProyeccionProductCard,
  ProyeccionProductCardSkeleton,
  ProyeccionProductGrid,
} from "../components";
import { MOCK_PROJECTION_PRODUCTS } from "../mockData";
import type { ProjectionProductOverview } from "../types";

// Mock de framer-motion para tests rápidos y deterministas
vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("framer-motion");
  return {
    ...actual,
    AnimatePresence: ({ children }: { readonly children: ReactNode }) => <>{children}</>,
    motion: {
      div: ({
        children,
        className,
        onClick,
        layout: _layout,
        ...props
      }: HTMLAttributes<HTMLDivElement> & {
        readonly children?: ReactNode;
        readonly layout?: unknown;
      }) => (
        <div className={className} onClick={onClick} {...props}>
          {children}
        </div>
      ),
    },
  };
});

describe("Feature Projection - Phase 5 Product Card and Adaptive Grid", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("1. ProyeccionProductCard", () => {
    const criticalProduct = MOCK_PROJECTION_PRODUCTS[0] as ProjectionProductOverview;
    const warningProduct = MOCK_PROJECTION_PRODUCTS[1] as ProjectionProductOverview;
    const normalProduct = MOCK_PROJECTION_PRODUCTS[3] as ProjectionProductOverview;

    it("debe renderizar correctamente un producto en estado CRÍTICO (#ef4444)", () => {
      render(<ProyeccionProductCard product={criticalProduct} />);

      const card = screen.getByTestId(`projection-product-card-${criticalProduct.producto_id}`);
      expect(card).toBeInTheDocument();
      expect(card).toHaveAttribute("data-status", "critical");

      // Verificación de ADN Visual (borde y barra inferior roja)
      expect(card.className).toContain("border-red-500/30");
      const bottomBar = screen.getByTestId("card-urgency-bottom-bar");
      expect(bottomBar).toHaveClass("bg-[#ef4444]");

      // Textos y etiquetas principales
      expect(screen.getByTestId("card-product-name")).toHaveTextContent(criticalProduct.nombre);
      expect(screen.getByTestId("card-bodega-badge")).toHaveTextContent("Cocina Central");
      expect(screen.getByTestId("card-sku-badge")).toHaveTextContent("CAR-POL-001");
      expect(screen.getByTestId("card-unit-badge")).toHaveTextContent("kg");
      expect(screen.getByTestId("card-category-name")).toHaveTextContent("Carnes y Aves");

      // Píldora de urgencia con día del quiebre
      const urgencyPill = screen.getByTestId("card-urgency-pill");
      expect(urgencyPill).toHaveTextContent("Sin stock (día 11)");
      expect(urgencyPill.className).toContain("text-red-600");

      // Comparativa numérica táctil
      expect(screen.getByTestId("card-current-qty")).toHaveTextContent("45.5");
      const projectedQty = screen.getByTestId("card-projected-qty");
      expect(projectedQty).toHaveTextContent("0");
      expect(projectedQty.className).toContain("text-red-600");

      // Fecha de agotamiento y tasa de consumo diario
      expect(screen.getByTestId("card-depletion-date")).toHaveTextContent("12-11-2026");
      expect(screen.getByTestId("card-daily-rate")).toHaveTextContent("3.8");
    });

    it("debe renderizar correctamente un producto en estado ADVERTENCIA (#f59e0b)", () => {
      render(<ProyeccionProductCard product={warningProduct} />);

      const card = screen.getByTestId(`projection-product-card-${warningProduct.producto_id}`);
      expect(card).toBeInTheDocument();
      expect(card).toHaveAttribute("data-status", "warning");

      // ADN Visual: bordes y barra ámbar
      expect(card.className).toContain("border-amber-500/30");
      const bottomBar = screen.getByTestId("card-urgency-bottom-bar");
      expect(bottomBar).toHaveClass("bg-[#f59e0b]");

      // Píldora de urgencia con día advertencia
      const urgencyPill = screen.getByTestId("card-urgency-pill");
      expect(urgencyPill).toHaveTextContent("Bajo stock (día 23)");
      expect(urgencyPill.className).toContain("text-amber-600");

      // Valores numéricos
      expect(screen.getByTestId("card-current-qty")).toHaveTextContent("28");
      expect(screen.getByTestId("card-projected-qty")).toHaveTextContent("4.2");
      expect(screen.getByTestId("card-daily-rate")).toHaveTextContent("0.9");
    });

    it("debe renderizar correctamente un producto en estado NORMAL (#10b981)", () => {
      render(<ProyeccionProductCard product={normalProduct} />);

      const card = screen.getByTestId(`projection-product-card-${normalProduct.producto_id}`);
      expect(card).toBeInTheDocument();
      expect(card).toHaveAttribute("data-status", "normal");

      // ADN Visual: bordes y barra esmeralda (#10b981)
      expect(card.className).toContain("border-emerald-500/30");
      const bottomBar = screen.getByTestId("card-urgency-bottom-bar");
      expect(bottomBar).toHaveClass("bg-[#10b981]");

      // Píldora de estado óptimo
      const urgencyPill = screen.getByTestId("card-urgency-pill");
      expect(urgencyPill).toHaveTextContent("Stock saludable y estable");
      expect(urgencyPill.className).toContain("text-emerald-600");

      // Agotamiento "Sin quiebre"
      expect(screen.getByTestId("card-depletion-date")).toHaveTextContent("Sin quiebre");
    });

    it("debe disparar onClick al hacer clic o tap sobre la tarjeta", () => {
      const handleClick = vi.fn();
      render(<ProyeccionProductCard product={criticalProduct} onClick={handleClick} />);

      const card = screen.getByTestId(`projection-product-card-${criticalProduct.producto_id}`);
      fireEvent.click(card);

      expect(handleClick).toHaveBeenCalledTimes(1);
      expect(handleClick).toHaveBeenCalledWith(criticalProduct);
    });

    it("debe responder a interacción accesible por teclado con Enter y Espacio", () => {
      const handleClick = vi.fn();
      render(<ProyeccionProductCard product={normalProduct} onClick={handleClick} />);

      const card = screen.getByTestId(`projection-product-card-${normalProduct.producto_id}`);

      fireEvent.keyDown(card, { key: "Enter" });
      expect(handleClick).toHaveBeenCalledTimes(1);
      expect(handleClick).toHaveBeenCalledWith(normalProduct);

      fireEvent.keyDown(card, { key: " " });
      expect(handleClick).toHaveBeenCalledTimes(2);

      // Otra tecla no debe disparar click
      fireEvent.keyDown(card, { key: "Tab" });
      expect(handleClick).toHaveBeenCalledTimes(2);
    });

    it("debe renderizar el Skeleton de tarjeta con animación pulse", () => {
      render(<ProyeccionProductCardSkeleton />);

      const skeleton = screen.getByTestId("proyeccion-product-card-skeleton");
      expect(skeleton).toBeInTheDocument();
      expect(skeleton.className).toContain("animate-pulse");
      expect(skeleton.className).toContain("rounded-3xl");
    });
  });

  describe("2. ProyeccionProductGrid", () => {
    it("debe mostrar el estado de carga con skeletons cuando isLoading es true", () => {
      render(
        <ProyeccionProductGrid
          products={[]}
          isLoading={true}
          skeletonCount={4}
        />
      );

      const loadingContainer = screen.getByTestId("proyeccion-product-grid-loading");
      expect(loadingContainer).toBeInTheDocument();
      expect(loadingContainer.className).toContain("grid-cols-1");
      expect(loadingContainer.className).toContain("md:grid-cols-2");
      expect(loadingContainer.className).toContain("lg:grid-cols-3");
      expect(loadingContainer.className).toContain("xl:grid-cols-4");

      const skeletons = screen.getAllByTestId("proyeccion-product-card-skeleton");
      expect(skeletons).toHaveLength(4);
    });

    it("debe mostrar el estado vacío con botón de reseteo si no hay productos", () => {
      const handleReset = vi.fn();
      render(
        <ProyeccionProductGrid
          products={[]}
          isLoading={false}
          onResetFilters={handleReset}
        />
      );

      const emptyContainer = screen.getByTestId("proyeccion-product-grid-empty");
      expect(emptyContainer).toBeInTheDocument();
      expect(screen.getByText("No se encontraron productos")).toBeInTheDocument();

      const resetBtn = screen.getByTestId("btn-reset-projection-filters");
      expect(resetBtn).toBeInTheDocument();

      fireEvent.click(resetBtn);
      expect(handleReset).toHaveBeenCalledTimes(1);
    });

    it("debe renderizar el grid plano de productos con sus tarjetas correspondientes", () => {
      const handleProductClick = vi.fn();
      const testProducts = MOCK_PROJECTION_PRODUCTS.slice(0, 4);

      render(
        <ProyeccionProductGrid
          products={testProducts}
          isLoading={false}
          onProductClick={handleProductClick}
        />
      );

      const grid = screen.getByTestId("proyeccion-product-grid");
      expect(grid).toBeInTheDocument();
      expect(grid.className).toContain("grid-cols-1");
      expect(grid.className).toContain("md:grid-cols-2");
      expect(grid.className).toContain("lg:grid-cols-3");
      expect(grid.className).toContain("xl:grid-cols-4");

      for (const prod of testProducts) {
        expect(
          screen.getByTestId(`projection-product-card-${prod.producto_id}`)
        ).toBeInTheDocument();
      }

      // Clic en la primera tarjeta
      const firstProduct = testProducts[0]!;
      fireEvent.click(screen.getByTestId(`projection-product-card-${firstProduct.producto_id}`));
      expect(handleProductClick).toHaveBeenCalledWith(firstProduct);
    });

    it("debe renderizar los productos agrupados por categoría cuando groupByCategory es true", () => {
      const handleProductClick = vi.fn();
      const testProducts = MOCK_PROJECTION_PRODUCTS.slice(0, 5);

      render(
        <ProyeccionProductGrid
          products={testProducts}
          isLoading={false}
          groupByCategory={true}
          onProductClick={handleProductClick}
        />
      );

      const groupedContainer = screen.getByTestId("proyeccion-product-grid-grouped");
      expect(groupedContainer).toBeInTheDocument();

      // En los primeros 5 productos de mockData tenemos "Carnes y Aves", "Lácteos y Huevos", "Pescados y Mariscos", "Frutas y Verduras"
      expect(screen.getByTestId("category-group-Carnes y Aves")).toBeInTheDocument();
      expect(screen.getByTestId("category-group-Lácteos y Huevos")).toBeInTheDocument();

      // Todas las tarjetas deben existir dentro de sus secciones
      for (const prod of testProducts) {
        expect(
          screen.getByTestId(`projection-product-card-${prod.producto_id}`)
        ).toBeInTheDocument();
      }
    });
  });
});
