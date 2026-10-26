// oppytec-frontend/src/features/inventory/alerts/__tests__/AlertasFlujosYPaginacion.test.tsx
/**
 * Suite de Certificación: FASE 6 — Flujos Operativos y Paginación (/alertas)
 * 6.1 Flujo del Carrito de Compras de Reabastecimiento (`addToCart`, `gestion_purchase_cart`)
 * 6.2 Flujo de Baja / Mermas Operativas (`/gestion?tab=mermas`)
 * 6.3 Control de Paginación Integrado (`TablePagination`, `alerts_page_size`)
 */

import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import * as httpClient from "@/shared/api/httpClient";
import { toast } from "sonner";
import { AlertasPage } from "../AlertasPage";
import { MOCK_ALERTS_SUMMARY } from "../mockData";
import type {
  AlertsSummary,
  CriticalStockAlert,
  ExpiredLotAlert,
  UpcomingExpiryAlert,
  CartPurchaseItem,
} from "../types";

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

// Mock de Sonner Toast
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

// Generador de dataset extendido para pruebas de paginación
function createExtendedAlertsSummary(
  criticalCount: number = 15,
  expiredCount: number = 12,
  upcomingCount: number = 7
): AlertsSummary {
  const critical_stock: CriticalStockAlert[] = Array.from({ length: criticalCount }, (_, i) => ({
    producto_id: 1000 + i + 1,
    bodega_id: 1,
    bodega_nombre: "Bodega Cocina Central",
    producto_nombre: `Insumo Crítico #${i + 1}`,
    stock_actual: i < 5 ? 0 : i + 1,
    stock_minimo: 20,
    unidad_medida: "kg",
    ratio: {
      stock_actual: i < 5 ? 0 : i + 1,
      stock_minimo: 20,
      raw_ratio: i < 5 ? 0 : ((i + 1) / 20) * 100,
      clamped_ratio: i < 5 ? 5 : ((i + 1) / 20) * 100,
      status: i < 5 ? "depleted" : "critical",
    },
    is_depleted: i < 5,
    bodega_color: "#3B82F6",
    bodega_icono: "warehouse",
    costo_promedio: 2500 + i * 100,
  }));

  const expired_lots: ExpiredLotAlert[] = Array.from({ length: expiredCount }, (_, i) => ({
    producto_id: 2000 + i + 1,
    bodega_id: 2,
    bodega_nombre: "Cámara Fría -18°C",
    producto_nombre: `Lote Caducado #${i + 1}`,
    lote_codigo: `LOT-EXP-${100 + i}`,
    fecha_vencimiento: "2026-10-15",
    cantidad_vencida: 5 + i,
    dias_vencido: 10,
    costo_ppp: 1800,
    valor_total_riesgo: (5 + i) * 1800,
    unidad_medida: "lt",
    bodega_color: "#10B981",
    bodega_icono: "snowflake",
  }));

  const upcoming_expiries: UpcomingExpiryAlert[] = Array.from({ length: upcomingCount }, (_, i) => ({
    producto_id: 3000 + i + 1,
    bodega_id: 2,
    bodega_nombre: "Cámara Fría -18°C",
    producto_nombre: `Lote Próximo #${i + 1}`,
    lote_codigo: `LOT-UPC-${200 + i}`,
    fecha_vencimiento: "2026-11-05",
    cantidad_en_riesgo: 8 + i,
    dias_restantes: 11,
    costo_ppp: 3200,
    valor_total_riesgo: (8 + i) * 3200,
    unidad_medida: "kg",
    bodega_color: "#10B981",
    bodega_icono: "snowflake",
  }));

  return {
    total_count: criticalCount + expiredCount + upcomingCount,
    critical_count: criticalCount,
    expired_count: expiredCount,
    upcoming_count: upcomingCount,
    has_critical: criticalCount > 0 || expiredCount > 0,
    total_financial_risk: 500000,
    critical_stock,
    expired_lots,
    upcoming_expiries,
  };
}

describe("AlertasFlujosYPaginacion Suite — FASE 6: Flujos Operativos y Paginación", () => {
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
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
  });

  // ==========================================================================
  // 6.1 Flujo del Carrito de Compras de Reabastecimiento (addToCart)
  // ==========================================================================
  describe("6.1 Flujo del Carrito de Compras de Reabastecimiento", () => {
    it("agrega un nuevo producto al carrito en localStorage con cantidad 1, precio = costo_promedio, emite evento y toast", async () => {
      const cartListener = vi.fn();
      window.addEventListener("cart-updated", cartListener);

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("btn-add-cart-card-101")).toBeInTheDocument();
      });

      const addBtn = screen.getByTestId("btn-add-cart-card-101");
      fireEvent.click(addBtn);

      // Verificar persistencia en localStorage
      const savedRaw = localStorage.getItem("gestion_purchase_cart");
      expect(savedRaw).toBeTruthy();
      const cart: CartPurchaseItem[] = JSON.parse(savedRaw!);
      expect(cart).toHaveLength(1);
      expect(cart[0]).toEqual({
        producto_id: 101,
        bodega_id: 1,
        bodega_nombre: "Bodega Cocina Central",
        nombre: "Pechuga de Pollo Fresca",
        cantidad: 1,
        precio: 4800, // Tomado de costo_promedio
        unidad: "kg",
      });

      // Verificar evento window cart-updated
      expect(cartListener).toHaveBeenCalledTimes(1);

      // Verificar notificación toast Sonner de éxito
      expect(toast.success).toHaveBeenCalledWith(
        "Pechuga de Pollo Fresca (Bodega Cocina Central) agregado al carrito de compras"
      );

      window.removeEventListener("cart-updated", cartListener);
    });

    it("incrementa la cantidad en +1 cuando el producto ya existe para la misma bodega", async () => {
      const initialCart: CartPurchaseItem[] = [
        {
          producto_id: 101,
          bodega_id: 1,
          bodega_nombre: "Bodega Cocina Central",
          nombre: "Pechuga de Pollo Fresca",
          cantidad: 2,
          precio: 4800,
          unidad: "kg",
        },
      ];
      localStorage.setItem("gestion_purchase_cart", JSON.stringify(initialCart));

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("btn-add-cart-card-101")).toBeInTheDocument();
      });

      const addBtn = screen.getByTestId("btn-add-cart-card-101");
      fireEvent.click(addBtn);

      const cart: CartPurchaseItem[] = JSON.parse(
        localStorage.getItem("gestion_purchase_cart")!
      );
      expect(cart).toHaveLength(1);
      expect(cart[0]!.cantidad).toBe(3);
      expect(cart[0]!.producto_id).toBe(101);
      expect(cart[0]!.bodega_id).toBe(1);
    });

    it("crea un nuevo ítem en el carrito si es el mismo producto pero en distinta bodega", async () => {
      const initialCart: CartPurchaseItem[] = [
        {
          producto_id: 101,
          bodega_id: 99, // Otra bodega
          bodega_nombre: "Bodega Secundaria",
          nombre: "Pechuga de Pollo Fresca",
          cantidad: 1,
          precio: 4800,
          unidad: "kg",
        },
      ];
      localStorage.setItem("gestion_purchase_cart", JSON.stringify(initialCart));

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("btn-add-cart-card-101")).toBeInTheDocument();
      });

      const addBtn = screen.getByTestId("btn-add-cart-card-101");
      fireEvent.click(addBtn);

      const cart: CartPurchaseItem[] = JSON.parse(
        localStorage.getItem("gestion_purchase_cart")!
      );
      expect(cart).toHaveLength(2);
      expect(cart[0]!.bodega_id).toBe(99);
      expect(cart[1]!.bodega_id).toBe(1);
      expect(cart[1]!.cantidad).toBe(1);
    });

    it("se recupera de forma segura ante JSON corrupto en localStorage", async () => {
      localStorage.setItem("gestion_purchase_cart", "{json-invalido");

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("btn-add-cart-card-101")).toBeInTheDocument();
      });

      const addBtn = screen.getByTestId("btn-add-cart-card-101");
      expect(() => fireEvent.click(addBtn)).not.toThrow();

      const cart: CartPurchaseItem[] = JSON.parse(
        localStorage.getItem("gestion_purchase_cart")!
      );
      expect(cart).toHaveLength(1);
      expect(cart[0]!.producto_id).toBe(101);
      expect(cart[0]!.cantidad).toBe(1);
    });

    it("activa la micro-animación morada en el botón durante 400ms al clickear", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("btn-add-cart-card-101")).toBeInTheDocument();
      });

      const addBtn = screen.getByTestId("btn-add-cart-card-101");
      // Antes del click no tiene clase de animación activa
      expect(addBtn.className).toContain("text-purple-600");
      expect(addBtn.className).not.toContain("bg-purple-600");

      fireEvent.click(addBtn);

      // Inmediatamente después del click tiene las clases activas
      expect(addBtn.className).toContain("bg-purple-600");
      expect(addBtn.className).toContain("scale-110");
      expect(addBtn.className).toContain("text-white");
    });

    it("funciona idénticamente en modo listado desde la tabla StockCriticoTable", async () => {
      localStorage.setItem("alerts_view_mode", "list");

      const cartListener = vi.fn();
      window.addEventListener("cart-updated", cartListener);

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("btn-add-cart-table-101")).toBeInTheDocument();
      });

      const tableBtn = screen.getByTestId("btn-add-cart-table-101");
      fireEvent.click(tableBtn);

      const cart: CartPurchaseItem[] = JSON.parse(
        localStorage.getItem("gestion_purchase_cart")!
      );
      expect(cart).toHaveLength(1);
      expect(cart[0]!.producto_id).toBe(101);
      expect(cartListener).toHaveBeenCalled();
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("agregado al carrito de compras")
      );

      window.removeEventListener("cart-updated", cartListener);
    });
  });

  // ==========================================================================
  // 6.2 Flujo de Baja / Mermas Operativas
  // ==========================================================================
  describe("6.2 Flujo de Baja / Mermas Operativas", () => {
    it("navega fluidamente hacia /gestion?tab=mermas desde tarjeta de lote vencido (ExpiredLotCard)", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("btn-report-merma-201")).toBeInTheDocument();
      });

      const mermaBtn = screen.getByTestId("btn-report-merma-201");
      fireEvent.click(mermaBtn);

      expect(mockNavigate).toHaveBeenCalledWith("/gestion?tab=mermas");
    });

    it("navega fluidamente hacia /gestion?tab=mermas desde tarjeta de lote próximo a vencer (UpcomingExpiryCard)", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("btn-manage-upcoming-301")).toBeInTheDocument();
      });

      const manageBtn = screen.getByTestId("btn-manage-upcoming-301");
      fireEvent.click(manageBtn);

      expect(mockNavigate).toHaveBeenCalledWith("/gestion?tab=mermas");
    });

    it("navega hacia /gestion?tab=mermas desde las tarjetas de vencimiento en modo listado", async () => {
      localStorage.setItem("alerts_view_mode", "list");

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(
          screen.getByTestId("btn-action-vencimiento-expired-201")
        ).toBeInTheDocument();
      });

      // Botón en tarjeta de vencidos
      const expiredActionBtn = screen.getByTestId(
        "btn-action-vencimiento-expired-201"
      );
      fireEvent.click(expiredActionBtn);
      expect(mockNavigate).toHaveBeenCalledWith("/gestion?tab=mermas");

      // Botón en tarjeta de próximos a vencer
      const upcomingActionBtn = screen.getByTestId(
        "btn-action-vencimiento-upcoming-301"
      );
      fireEvent.click(upcomingActionBtn);
      expect(mockNavigate).toHaveBeenCalledWith("/gestion?tab=mermas");
    });
  });

  // ==========================================================================
  // 6.3 Control de Paginación (TablePagination)
  // ==========================================================================
  describe("6.3 Control de Paginación Integrado", () => {
    beforeEach(() => {
      const extendedData = createExtendedAlertsSummary(15, 12, 7);
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async () => ({
        data: extendedData,
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      }));
    });

    it("calcula reactivamente totalItems según el filtro activo", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      // Filtro 'all': totalItems = Math.max(15, 12, 7) = 15
      await waitFor(() => {
        expect(screen.getByTestId("table-pagination")).toBeInTheDocument();
      });
      expect(screen.getByText(/15 alertas/i)).toBeInTheDocument();

      // Cambiar a filtro 'stock'
      const trigger = screen.getByTestId("alerts-filter-trigger");
      fireEvent.keyDown(trigger, { key: "ArrowDown" });
      const stockOption = await screen.findByTestId("filter-option-stock");
      fireEvent.click(stockOption);

      await waitFor(() => {
        expect(screen.getByText(/15 alertas/i)).toBeInTheDocument();
      });

      // Cambiar a filtro 'expired' -> totalItems = 12
      fireEvent.keyDown(trigger, { key: "ArrowDown" });
      const expiredOption = await screen.findByTestId("filter-option-expired");
      fireEvent.click(expiredOption);

      await waitFor(() => {
        expect(screen.getByText(/12 alertas/i)).toBeInTheDocument();
      });

      // Cambiar a filtro 'upcoming' -> totalItems = 7
      fireEvent.keyDown(trigger, { key: "ArrowDown" });
      const upcomingOption = await screen.findByTestId("filter-option-upcoming");
      fireEvent.click(upcomingOption);

      await waitFor(() => {
        expect(screen.getByText(/7 alertas/i)).toBeInTheDocument();
      });
    });

    it("calcula y pagina correctamente paginatedStockCritico, paginatedVencidos y paginatedVencimientosProximos", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("table-pagination")).toBeInTheDocument();
      });

      // Página 1 (tamaño 10 por defecto):
      // Stock crítico: 10 items (Insumo Crítico #1 a #10)
      expect(screen.getByText("Insumo Crítico #1")).toBeInTheDocument();
      expect(screen.getByText("Insumo Crítico #10")).toBeInTheDocument();
      expect(screen.queryByText("Insumo Crítico #11")).not.toBeInTheDocument();

      // Vencidos: 10 items (Lote Caducado #1 a #10)
      expect(screen.getByText("Lote Caducado #1")).toBeInTheDocument();
      expect(screen.getByText("Lote Caducado #10")).toBeInTheDocument();
      expect(screen.queryByText("Lote Caducado #11")).not.toBeInTheDocument();

      // Próximos: 7 items (todos visibles)
      expect(screen.getByText("Lote Próximo #1")).toBeInTheDocument();
      expect(screen.getByText("Lote Próximo #7")).toBeInTheDocument();

      // Avanzar a la página 2
      const nextBtn = screen.getByTestId("pagination-next-page");
      fireEvent.click(nextBtn);

      await waitFor(() => {
        // En página 2:
        // Stock crítico: items 11 a 15
        expect(screen.getByText("Insumo Crítico #11")).toBeInTheDocument();
        expect(screen.getByText("Insumo Crítico #15")).toBeInTheDocument();
        expect(screen.queryByText("Insumo Crítico #1")).not.toBeInTheDocument();

        // Vencidos: items 11 y 12
        expect(screen.getByText("Lote Caducado #11")).toBeInTheDocument();
        expect(screen.getByText("Lote Caducado #12")).toBeInTheDocument();
        expect(screen.queryByText("Lote Caducado #1")).not.toBeInTheDocument();

        // Próximos: no hay ítems en página 2 (sólo eran 7)
        expect(screen.queryByText("Lote Próximo #1")).not.toBeInTheDocument();
      });
    });

    it("resetea currentPage a 1 al alternar filtros de alertas", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("pagination-next-page")).toBeInTheDocument();
      });

      // Ir a página 2
      fireEvent.click(screen.getByTestId("pagination-next-page"));
      await waitFor(() => {
        expect(screen.getByText("Insumo Crítico #11")).toBeInTheDocument();
      });

      // Cambiar filtro a 'stock'
      const trigger = screen.getByTestId("alerts-filter-trigger");
      fireEvent.keyDown(trigger, { key: "ArrowDown" });
      const stockOption = await screen.findByTestId("filter-option-stock");
      fireEvent.click(stockOption);

      // Debe resetearse a la página 1
      await waitFor(() => {
        expect(screen.getByText("Insumo Crítico #1")).toBeInTheDocument();
        expect(screen.queryByText("Insumo Crítico #11")).not.toBeInTheDocument();
      });
    });

    it("resetea currentPage a 1 al alternar viewMode de tarjetas a listado", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("pagination-next-page")).toBeInTheDocument();
      });

      // Ir a página 2
      fireEvent.click(screen.getByTestId("pagination-next-page"));
      await waitFor(() => {
        expect(screen.getByText("Insumo Crítico #11")).toBeInTheDocument();
      });

      // Cambiar a modo listado
      const toggleListBtn = screen.getByTestId("toggle-view-list");
      fireEvent.click(toggleListBtn);

      await waitFor(() => {
        expect(screen.getByTestId("alerts-list-view")).toBeInTheDocument();
        // En listado debe estar en página 1
        expect(screen.getByText("Insumo Crítico #1")).toBeInTheDocument();
        expect(screen.queryByText("Insumo Crítico #11")).not.toBeInTheDocument();
      });
    });

    it("cambia el tamaño de página (10 -> 30), persiste en localStorage y resetea a página 1", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("pagination-page-size-select")).toBeInTheDocument();
      });

      // Primero ir a página 2
      fireEvent.click(screen.getByTestId("pagination-next-page"));
      await waitFor(() => {
        expect(screen.getByText("Insumo Crítico #11")).toBeInTheDocument();
      });

      // Cambiar tamaño de página a 30
      const select = screen.getByTestId("pagination-page-size-select");
      fireEvent.change(select, { target: { value: "30" } });

      // Debe persistir en localStorage
      expect(localStorage.getItem("alerts_page_size")).toBe("30");

      // Debe resetear a página 1 y mostrar todos los 15 items a la vez
      await waitFor(() => {
        expect(screen.getByText("Insumo Crítico #1")).toBeInTheDocument();
        expect(screen.getByText("Insumo Crítico #15")).toBeInTheDocument();
      });
    });

    it("restaura alerts_page_size previamente guardado en localStorage", async () => {
      localStorage.setItem("alerts_page_size", "50");

      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        const select = screen.getByTestId("pagination-page-size-select") as HTMLSelectElement;
        expect(select.value).toBe("50");
      });
    });

    it("navega correctamente usando botones Primera página, Anterior, Siguiente y Última", async () => {
      render(<AlertasPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("table-pagination")).toBeInTheDocument();
      });

      // En página 1: botón anterior y primero están deshabilitados
      expect(screen.getByTestId("pagination-prev-page")).toBeDisabled();
      expect(screen.getByTestId("pagination-first-page")).toBeDisabled();

      // Click siguiente -> pasa a página 2
      fireEvent.click(screen.getByTestId("pagination-next-page"));
      await waitFor(() => {
        expect(screen.getByText("Insumo Crítico #11")).toBeInTheDocument();
      });

      // En página 2 (última): siguiente y última están deshabilitados
      expect(screen.getByTestId("pagination-next-page")).toBeDisabled();
      expect(screen.getByTestId("pagination-last-page")).toBeDisabled();

      // Click primera página -> vuelve a página 1
      fireEvent.click(screen.getByTestId("pagination-first-page"));
      await waitFor(() => {
        expect(screen.getByText("Insumo Crítico #1")).toBeInTheDocument();
      });

      // Click última página -> pasa a página 2
      fireEvent.click(screen.getByTestId("pagination-last-page"));
      await waitFor(() => {
        expect(screen.getByText("Insumo Crítico #11")).toBeInTheDocument();
      });

      // Click anterior -> vuelve a página 1
      fireEvent.click(screen.getByTestId("pagination-prev-page"));
      await waitFor(() => {
        expect(screen.getByText("Insumo Crítico #1")).toBeInTheDocument();
      });
    });
  });
});
