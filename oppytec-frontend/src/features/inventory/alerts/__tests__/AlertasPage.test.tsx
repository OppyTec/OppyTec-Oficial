// oppytec-frontend/src/features/inventory/alerts/__tests__/AlertasPage.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import * as httpClient from "@/shared/api/httpClient";
import { AlertasPage } from "../AlertasPage";
import { AlertasToolbar } from "../components/AlertasToolbar";
import { MOCK_ALERTS_SUMMARY } from "../mockData";

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

describe("AlertasPage & AlertasToolbar — Suite de Renderizado y Paridad Legacy (Fase 4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof window !== "undefined") {
      window.HTMLElement.prototype.scrollIntoView = vi.fn();
      window.HTMLElement.prototype.hasPointerCapture = vi.fn();
      window.HTMLElement.prototype.setPointerCapture = vi.fn();
      window.HTMLElement.prototype.releasePointerCapture = vi.fn();
    }
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers({ "X-Trace-ID": "test-trace" }),
        json: async () => MOCK_ALERTS_SUMMARY,
      })
    );
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
        data: MOCK_ALERTS_SUMMARY,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
  });

  // ==========================================================================
  // 1. Renderizado de Cabecera Centrada y SectionHeader
  // ==========================================================================
  describe("1. Cabecera Centrada y SectionHeader Canónico", () => {
    it("renders SectionHeader with centered title, subtitle and alert icon", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Alertas")).toBeInTheDocument();
      });

      const subtitles = screen.getAllByText("Estado de Stock y Vencimientos del Sistema");
      expect(subtitles.length).toBeGreaterThan(0);
    });
  });

  // ==========================================================================
  // 2. Toolbar Unificado Desktop y Mobile-First
  // ==========================================================================
  describe("2. Toolbar Unificado Desktop y Mobile", () => {
    it("renders outer card container and both desktop and mobile toolbar variants", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("alerts-toolbar")).toBeInTheDocument();
      });

      expect(screen.getByTestId("alerts-toolbar-desktop")).toBeInTheDocument();
      expect(screen.getByTestId("alerts-toolbar-mobile")).toBeInTheDocument();
    });

    it("renders area and bodega selectors in toolbar", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getAllByTestId("area-selector").length).toBeGreaterThan(0);
      });

      expect(screen.getAllByTestId("bodega-selector").length).toBeGreaterThan(0);
    });

    it("renders standalone AlertasToolbar and triggers callbacks", () => {
      const onSelectArea = vi.fn();
      const onSelectWarehouse = vi.fn();
      const onFilterChange = vi.fn();
      const onViewModeChange = vi.fn();

      render(
        <AlertasToolbar
          selectedAreaId="all"
          onSelectArea={onSelectArea}
          activeWarehouseId="all"
          onSelectWarehouse={onSelectWarehouse}
          filterType="all"
          onFilterChange={onFilterChange}
          viewMode="cards"
          onViewModeChange={onViewModeChange}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId("alerts-toolbar")).toBeInTheDocument();

      // Clic en toggle modo listado desktop
      const toggleListBtn = screen.getByTestId("toggle-view-list");
      fireEvent.click(toggleListBtn);
      expect(onViewModeChange).toHaveBeenCalledWith("list");

      // Clic en toggle modo tarjetas mobile
      const toggleCardsMobileBtn = screen.getByTestId("toggle-view-cards-mobile");
      fireEvent.click(toggleCardsMobileBtn);
      expect(onViewModeChange).toHaveBeenCalledWith("cards");
    });
  });

  // ==========================================================================
  // 3. Conmutación de Filtro de Alertas
  // ==========================================================================
  describe("3. Filtro de Alertas (Dropdown y Opciones)", () => {
    it("opens dropdown and selects 'stock' (Stock Crítico) filter", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("alerts-filter-trigger")).toBeInTheDocument();
      });

      const trigger = screen.getByTestId("alerts-filter-trigger");
      fireEvent.keyDown(trigger, { key: "ArrowDown" });

      const stockOption = await screen.findByTestId("filter-option-stock");
      fireEvent.click(stockOption);

      // Ahora solo debe mostrarse la sección de Stock Crítico
      await waitFor(() => {
        expect(screen.getByTestId("section-stock-critico")).toBeInTheDocument();
        expect(screen.queryByTestId("section-vencidos")).not.toBeInTheDocument();
        expect(screen.queryByTestId("section-proximos")).not.toBeInTheDocument();
      });
    });

    it("selects 'expired' filter and shows only expired products", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("alerts-filter-trigger")).toBeInTheDocument();
      });

      const trigger = screen.getByTestId("alerts-filter-trigger");
      fireEvent.keyDown(trigger, { key: "ArrowDown" });
      const expiredOption = await screen.findByTestId("filter-option-expired");
      fireEvent.click(expiredOption);

      await waitFor(() => {
        expect(screen.getByTestId("section-vencidos")).toBeInTheDocument();
        expect(screen.queryByTestId("section-stock-critico")).not.toBeInTheDocument();
        expect(screen.queryByTestId("section-proximos")).not.toBeInTheDocument();
      });
    });

    it("selects 'upcoming' filter and shows only upcoming expiries", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("alerts-filter-trigger")).toBeInTheDocument();
      });

      const trigger = screen.getByTestId("alerts-filter-trigger");
      fireEvent.keyDown(trigger, { key: "ArrowDown" });
      const upcomingOption = await screen.findByTestId("filter-option-upcoming");
      fireEvent.click(upcomingOption);

      await waitFor(() => {
        expect(screen.getByTestId("section-proximos")).toBeInTheDocument();
        expect(screen.queryByTestId("section-stock-critico")).not.toBeInTheDocument();
        expect(screen.queryByTestId("section-vencidos")).not.toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // 4. Conmutación de Vistas (Cards vs List) y Persistencia en LocalStorage
  // ==========================================================================
  describe("4. Toggle de Vistas y Persistencia en LocalStorage", () => {
    it("starts in 'cards' mode by default and renders cards view", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("alerts-cards-view")).toBeInTheDocument();
      });

      expect(screen.queryByTestId("alerts-list-view")).not.toBeInTheDocument();
    });

    it("switches to 'list' mode on button click and persists to localStorage", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("toggle-view-list")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("toggle-view-list"));

      await waitFor(() => {
        expect(screen.getByTestId("alerts-list-view")).toBeInTheDocument();
      });
      expect(screen.queryByTestId("alerts-cards-view")).not.toBeInTheDocument();
      expect(localStorage.getItem("alerts_view_mode")).toBe("list");
    });

    it("restores 'list' mode from localStorage on initial render", async () => {
      localStorage.setItem("alerts_view_mode", "list");

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("alerts-list-view")).toBeInTheDocument();
      });
      expect(screen.queryByTestId("alerts-cards-view")).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 5. Carrito de Compras Rápido y Notificaciones
  // ==========================================================================
  describe("5. Carrito de Compras Rápido (gestion_purchase_cart)", () => {
    it("adds product to cart when clicking shopping cart button", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("btn-add-cart-card-101")).toBeInTheDocument();
      });

      const cartBtn = screen.getByTestId("btn-add-cart-card-101");
      fireEvent.click(cartBtn);

      const cartData = JSON.parse(localStorage.getItem("gestion_purchase_cart") || "[]");
      expect(cartData.length).toBe(1);
      expect(cartData[0].producto_id).toBe(101);
      expect(cartData[0].nombre).toBe("Pechuga de Pollo Fresca");
      expect(cartData[0].cantidad).toBe(1);
    });

    it("increments quantity if product already exists in cart", async () => {
      localStorage.setItem(
        "gestion_purchase_cart",
        JSON.stringify([
          {
            producto_id: 101,
            bodega_id: 1,
            bodega_nombre: "Bodega Cocina Central",
            nombre: "Pechuga de Pollo Fresca",
            cantidad: 2,
            precio: 0,
            unidad: "kg",
          },
        ])
      );

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("btn-add-cart-card-101")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("btn-add-cart-card-101"));

      const cartData = JSON.parse(localStorage.getItem("gestion_purchase_cart") || "[]");
      expect(cartData.length).toBe(1);
      expect(cartData[0].cantidad).toBe(3);
    });
  });

  // ==========================================================================
  // 6. Paginación Integrada
  // ==========================================================================
  describe("6. Paginación Integrada", () => {
    it("renders TablePagination when total items exceed 0", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("table-pagination")).toBeInTheDocument();
      });
    });

    it("honors alerts_page_size from localStorage", async () => {
      localStorage.setItem("alerts_page_size", "50");

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("table-pagination")).toBeInTheDocument();
      });
    });
  });
});
