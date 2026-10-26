// oppytec-frontend/src/features/inventory/alerts/__tests__/AlertasViews.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import * as httpClient from "@/shared/api/httpClient";
import { toast } from "sonner";
import {
  StockCriticoCard,
  ExpiredLotCard,
  UpcomingExpiryCard,
  StockCriticoTable,
  VencimientosCard,
} from "../components";
import { AlertasPage } from "../AlertasPage";
import { format, formatDistanceToNow, parseISO, isPast } from "../dateUtils";
import { MOCK_ALERTS_SUMMARY } from "../mockData";
import type { CriticalStockAlert, ExpiredLotAlert, UpcomingExpiryAlert } from "../types";

// Mock de framer-motion para tests deterministas
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

// Mock de toast Sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock de react-router-dom useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<any>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

const mockCriticalItem: CriticalStockAlert = {
  producto_id: 101,
  bodega_id: 1,
  bodega_nombre: "Bodega Central",
  producto_nombre: "Pechuga de Pollo",
  stock_actual: 4,
  stock_minimo: 10,
  unidad_medida: "kg",
  ratio: {
    stock_actual: 4,
    stock_minimo: 10,
    raw_ratio: 40,
    clamped_ratio: 40,
    status: "critical",
  },
  is_depleted: false,
  bodega_color: "#ef4444",
  bodega_icono: "Store",
  costo_promedio: 4500,
};

const mockDepletedItem: CriticalStockAlert = {
  ...mockCriticalItem,
  producto_id: 102,
  producto_nombre: "Arroz Grano Largo",
  stock_actual: 0,
  is_depleted: true,
};

const mockExpiredItem: ExpiredLotAlert = {
  producto_id: 201,
  bodega_id: 1,
  bodega_nombre: "Bodega Cocina",
  producto_nombre: "Crema de Leche",
  lote_codigo: "LOTE-2024-X",
  fecha_vencimiento: "2024-01-15",
  cantidad_vencida: 12,
  dias_vencido: 10,
  costo_ppp: 1200,
  valor_total_riesgo: 14400,
  unidad_medida: "un",
  bodega_color: "#ef4444",
  bodega_icono: "Store",
};

const mockUpcomingItem: UpcomingExpiryAlert = {
  producto_id: 301,
  bodega_id: 2,
  bodega_nombre: "Bodega Bar",
  producto_nombre: "Jugo Natural de Naranja",
  lote_codigo: "LOTE-2026-Y",
  fecha_vencimiento: "2026-11-10",
  cantidad_en_riesgo: 25,
  dias_restantes: 16,
  costo_ppp: 1500,
  valor_total_riesgo: 37500,
  unidad_medida: "L",
  bodega_color: "#f59e0b",
  bodega_icono: "Beer",
};

describe("AlertasViews Suite — FASE 5: Renderizado Paritario 1:1 de Vistas (Tarjetas vs Listado)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
    vi.spyOn(httpClient, "apiRequest").mockImplementation(async () => ({
      data: MOCK_ALERTS_SUMMARY,
      traceId: "test-trace",
      timestampIso: new Date().toISOString(),
      tenantId: "tenant_rest_central",
    }));
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. Pruebas Unitarias de Utilidades de Fecha (dateUtils)
  // ==========================================================================
  describe("1. Date Utilities (dateUtils.ts)", () => {
    it("parses ISO YYYY-MM-DD correctly without time shift", () => {
      const d = parseISO("2026-10-25");
      expect(d.getFullYear()).toBe(2026);
      expect(d.getMonth()).toBe(9); // 0-indexed: October is 9
      expect(d.getDate()).toBe(25);
    });

    it("formats dates to dd-MM-yyyy pattern", () => {
      expect(format("2026-10-25", "dd-MM-yyyy")).toBe("25-10-2026");
      expect(format(null)).toBe("—");
      expect(format("invalid-date")).toBe("—");
    });

    it("evaluates past dates with isPast", () => {
      expect(isPast("2020-01-01")).toBe(true);
      expect(isPast("2099-01-01")).toBe(false);
    });

    it("calculates relative distance in Spanish", () => {
      const pastStr = formatDistanceToNow("2020-01-01", { addSuffix: true });
      expect(pastStr).toMatch(/hace \d+ (meses|años)/);

      const futureStr = formatDistanceToNow("2099-01-01", { addSuffix: true });
      expect(futureStr).toMatch(/en \d+ (meses|años)/);
    });
  });

  // ==========================================================================
  // 2. Componente StockCriticoCard
  // ==========================================================================
  describe("2. StockCriticoCard", () => {
    it("renders product name, bodega badge, and actual/min stock", () => {
      const onAddToCart = vi.fn();
      render(
        <StockCriticoCard
          item={mockCriticalItem}
          isAnimating={false}
          onAddToCart={onAddToCart}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("Pechuga de Pollo")).toBeInTheDocument();
      expect(screen.getByText("Central")).toBeInTheDocument(); // BodegaBadge strips "Bodega "
      expect(screen.getByText("4")).toBeInTheDocument();
      expect(screen.getByText("10")).toBeInTheDocument();
      expect(screen.getByText("Bajo Mínimo")).toBeInTheDocument();
      expect(screen.getByText("40%")).toBeInTheDocument();
    });

    it("renders 'Agotado' and destructive styling when stock is <= 0", () => {
      const onAddToCart = vi.fn();
      render(
        <StockCriticoCard
          item={mockDepletedItem}
          isAnimating={false}
          onAddToCart={onAddToCart}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("Arroz Grano Largo")).toBeInTheDocument();
      expect(screen.getByText("Agotado")).toBeInTheDocument();
      expect(screen.getByText("0%")).toBeInTheDocument();
    });

    it("calls onAddToCart when clicking shopping cart button", () => {
      const onAddToCart = vi.fn();
      render(
        <StockCriticoCard
          item={mockCriticalItem}
          isAnimating={false}
          onAddToCart={onAddToCart}
        />,
        { wrapper: createWrapper() }
      );

      const cartBtn = screen.getByTestId("btn-add-cart-card-101");
      fireEvent.click(cartBtn);
      expect(onAddToCart).toHaveBeenCalledTimes(1);
    });

    it("applies animation classes when isAnimating is true", () => {
      const onAddToCart = vi.fn();
      const { rerender } = render(
        <StockCriticoCard
          item={mockCriticalItem}
          isAnimating={false}
          onAddToCart={onAddToCart}
        />,
        { wrapper: createWrapper() }
      );

      let cartBtn = screen.getByTestId("btn-add-cart-card-101");
      expect(cartBtn.className).toContain("text-purple-600");

      rerender(
        <StockCriticoCard
          item={mockCriticalItem}
          isAnimating={true}
          onAddToCart={onAddToCart}
        />
      );

      cartBtn = screen.getByTestId("btn-add-cart-card-101");
      expect(cartBtn.className).toContain("bg-purple-600");
      expect(cartBtn.className).toContain("scale-110");
    });
  });

  // ==========================================================================
  // 3. Componente ExpiredLotCard
  // ==========================================================================
  describe("3. ExpiredLotCard", () => {
    it("renders expired lot details with formatted date and relative distance", () => {
      render(<ExpiredLotCard item={mockExpiredItem} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText("Crema de Leche")).toBeInTheDocument();
      expect(screen.getByText("Lote: LOTE-2024-X")).toBeInTheDocument();
      expect(screen.getByText("15-01-2024")).toBeInTheDocument();
      expect(screen.getByText("12")).toBeInTheDocument();
      expect(screen.getByText("Stock Afectado")).toBeInTheDocument();
    });

    it("navigates to /gestion?tab=mermas when clicking report merma button", () => {
      render(<ExpiredLotCard item={mockExpiredItem} />, {
        wrapper: createWrapper(),
      });

      const mermaBtn = screen.getByTestId("btn-report-merma-201");
      fireEvent.click(mermaBtn);
      expect(mockNavigate).toHaveBeenCalledWith("/gestion?tab=mermas");
    });

    it("calls custom onReportMerma callback if provided", () => {
      const onReportMerma = vi.fn();
      render(
        <ExpiredLotCard item={mockExpiredItem} onReportMerma={onReportMerma} />,
        { wrapper: createWrapper() }
      );

      const mermaBtn = screen.getByTestId("btn-report-merma-201");
      fireEvent.click(mermaBtn);
      expect(onReportMerma).toHaveBeenCalledWith(mockExpiredItem);
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  // ==========================================================================
  // 4. Componente UpcomingExpiryCard
  // ==========================================================================
  describe("4. UpcomingExpiryCard", () => {
    it("renders upcoming expiry item details and risk stock", () => {
      render(<UpcomingExpiryCard item={mockUpcomingItem} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText("Jugo Natural de Naranja")).toBeInTheDocument();
      expect(screen.getByText("Lote: LOTE-2026-Y")).toBeInTheDocument();
      expect(screen.getByText("10-11-2026")).toBeInTheDocument();
      expect(screen.getByText("25")).toBeInTheDocument();
      expect(screen.getByText("Stock Total")).toBeInTheDocument();
    });

    it("navigates to /gestion?tab=mermas on manage button click", () => {
      render(<UpcomingExpiryCard item={mockUpcomingItem} />, {
        wrapper: createWrapper(),
      });

      const manageBtn = screen.getByTestId("btn-manage-upcoming-301");
      fireEvent.click(manageBtn);
      expect(mockNavigate).toHaveBeenCalledWith("/gestion?tab=mermas");
    });
  });

  // ==========================================================================
  // 5. Componente StockCriticoTable
  // ==========================================================================
  describe("5. StockCriticoTable", () => {
    it("renders tabular headers and rows with progress bars", () => {
      const addToCart = vi.fn();
      render(
        <StockCriticoTable
          data={[mockCriticalItem, mockDepletedItem]}
          totalCount={2}
          addToCart={addToCart}
          animatingCarts={{}}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("Productos bajo Stock Mínimo")).toBeInTheDocument();
      expect(screen.getByText("2 alertas activas")).toBeInTheDocument();
      expect(screen.getByText("Pechuga de Pollo")).toBeInTheDocument();
      expect(screen.getByText("Arroz Grano Largo")).toBeInTheDocument();

      const addBtn = screen.getByTestId("btn-add-cart-table-101");
      fireEvent.click(addBtn);
      expect(addToCart).toHaveBeenCalledWith(mockCriticalItem, expect.anything());
    });

    it("renders empty state message when data array is empty", () => {
      render(
        <StockCriticoTable
          data={[]}
          totalCount={0}
          addToCart={vi.fn()}
          animatingCarts={{}}
        />,
        { wrapper: createWrapper() }
      );

      expect(
        screen.getByText("Todo bajo control. No hay productos en stock crítico.")
      ).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 6. Componente VencimientosCard
  // ==========================================================================
  describe("6. VencimientosCard", () => {
    it("renders expired card with banner de recomendación de merma", () => {
      render(
        <VencimientosCard
          type="expired"
          data={[mockExpiredItem]}
          totalCount={1}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("Productos Vencidos")).toBeInTheDocument();
      expect(screen.getByTestId("vencimientos-count-badge-expired")).toHaveTextContent("1");
      expect(screen.getByText("Crema de Leche")).toBeInTheDocument();
      expect(screen.getByTestId("banner-recomendacion-merma")).toBeInTheDocument();
    });

    it("renders upcoming card without merma recommendation banner", () => {
      render(
        <VencimientosCard
          type="upcoming"
          data={[mockUpcomingItem]}
          totalCount={1}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("Próximos a Vencer")).toBeInTheDocument();
      expect(screen.getByTestId("vencimientos-count-badge-upcoming")).toHaveTextContent("1");
      expect(screen.getByText("Jugo Natural de Naranja")).toBeInTheDocument();
      expect(screen.queryByTestId("banner-recomendacion-merma")).not.toBeInTheDocument();
    });

    it("renders empty state when data is empty", () => {
      render(
        <VencimientosCard type="expired" data={[]} totalCount={0} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("No hay registros para mostrar")).toBeInTheDocument();
    });

    it("handles action click triggering navigation to /gestion?tab=mermas", () => {
      render(
        <VencimientosCard
          type="expired"
          data={[mockExpiredItem]}
          totalCount={1}
        />,
        { wrapper: createWrapper() }
      );

      const actionBtn = screen.getByTestId("btn-action-vencimiento-expired-201");
      fireEvent.click(actionBtn);
      expect(mockNavigate).toHaveBeenCalledWith("/gestion?tab=mermas");
    });
  });

  // ==========================================================================
  // 7. Integración Completa en AlertasPage (Fase 5)
  // ==========================================================================
  describe("7. Integración Completa en AlertasPage", () => {
    it("switches smoothly between cards mode and list mode", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      // Modo Tarjetas por defecto
      await waitFor(() => {
        expect(screen.getByTestId("alerts-cards-view")).toBeInTheDocument();
        expect(screen.getByTestId("grid-stock-critico")).toBeInTheDocument();
      });

      // Conmutar a modo listado
      const toggleListBtn = screen.getByTestId("toggle-view-list");
      fireEvent.click(toggleListBtn);

      await waitFor(() => {
        expect(screen.getByTestId("alerts-list-view")).toBeInTheDocument();
        expect(screen.getByTestId("stock-critico-table")).toBeInTheDocument();
        expect(screen.getByTestId("vencimientos-card-upcoming")).toBeInTheDocument();
        expect(screen.getByTestId("vencimientos-card-expired")).toBeInTheDocument();
      });
    });

    it("adds item to cart in list mode, triggers toast and dispatches cart-updated event", async () => {
      localStorage.setItem("alerts_view_mode", "list");

      const cartListener = vi.fn();
      window.addEventListener("cart-updated", cartListener);

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("stock-critico-table")).toBeInTheDocument();
      });

      // Click en botón de carrito de la tabla (producto 101)
      const tableCartBtn = screen.getByTestId("btn-add-cart-table-101");
      fireEvent.click(tableCartBtn);

      expect(cartListener).toHaveBeenCalled();
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("agregado al carrito de compras")
      );

      const cart = JSON.parse(localStorage.getItem("gestion_purchase_cart") || "[]");
      expect(cart.length).toBe(1);
      expect(cart[0].producto_id).toBe(101);

      window.removeEventListener("cart-updated", cartListener);
    });

    it("filters reactively by 'stock' in list mode", async () => {
      localStorage.setItem("alerts_view_mode", "list");
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("alerts-filter-trigger")).toBeInTheDocument();
      });

      const trigger = screen.getByTestId("alerts-filter-trigger");
      fireEvent.keyDown(trigger, { key: "ArrowDown" });
      const stockOption = await screen.findByTestId("filter-option-stock");
      fireEvent.click(stockOption);

      await waitFor(() => {
        expect(screen.getByTestId("stock-critico-table")).toBeInTheDocument();
        expect(screen.queryByTestId("vencimientos-card-upcoming")).not.toBeInTheDocument();
        expect(screen.queryByTestId("vencimientos-card-expired")).not.toBeInTheDocument();
      });
    });

    it("filters reactively by 'expired' in list mode", async () => {
      localStorage.setItem("alerts_view_mode", "list");
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("alerts-filter-trigger")).toBeInTheDocument();
      });

      const trigger = screen.getByTestId("alerts-filter-trigger");
      fireEvent.keyDown(trigger, { key: "ArrowDown" });
      const expiredOption = await screen.findByTestId("filter-option-expired");
      fireEvent.click(expiredOption);

      await waitFor(() => {
        expect(screen.getByTestId("vencimientos-card-expired")).toBeInTheDocument();
        expect(screen.queryByTestId("stock-critico-table")).not.toBeInTheDocument();
        expect(screen.queryByTestId("vencimientos-card-upcoming")).not.toBeInTheDocument();
      });
    });

    it("filters reactively by 'upcoming' in list mode", async () => {
      localStorage.setItem("alerts_view_mode", "list");
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("alerts-filter-trigger")).toBeInTheDocument();
      });

      const trigger = screen.getByTestId("alerts-filter-trigger");
      fireEvent.keyDown(trigger, { key: "ArrowDown" });
      const upcomingOption = await screen.findByTestId("filter-option-upcoming");
      fireEvent.click(upcomingOption);

      await waitFor(() => {
        expect(screen.getByTestId("vencimientos-card-upcoming")).toBeInTheDocument();
        expect(screen.queryByTestId("stock-critico-table")).not.toBeInTheDocument();
        expect(screen.queryByTestId("vencimientos-card-expired")).not.toBeInTheDocument();
      });
    });
  });
});
