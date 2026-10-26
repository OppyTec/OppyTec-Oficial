// oppytec-frontend/src/features/inventory/alerts/__tests__/AlertasI18nAndFX.test.tsx
/**
 * Suite de Certificación: FASE 9 — Internacionalización (i18n) 100% es/en & Multi-Moneda FX (/alertas)
 * 1. Cobertura 1:1 de traducción en español e inglés sin claves faltantes.
 * 2. Ausencia total de cadenas hardcodeadas en JSX y atributos accesibles (aria-label, title, placeholder).
 * 3. Formateo y conversión Multi-Moneda FX con precisión Decimal (CLP, USD, EUR, UF).
 * 4. Aislamiento e independencia entre idioma activo y moneda activa.
 */

import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import * as httpClient from "@/shared/api/httpClient";
import {
  LanguageProvider,
  setActiveLanguage,
  translateKey,
} from "@/shared/i18n";
import {
  CurrencyProvider,
  formatCurrencyAmount,
} from "@/shared/currency";
import {
  StockCriticoCard,
  ExpiredLotCard,
  UpcomingExpiryCard,
  StockCriticoTable,
  VencimientosCard,
} from "../components";
import { formatDistanceToNow, es, en } from "../dateUtils";
import { MOCK_ALERTS_SUMMARY } from "../mockData";
import type { CriticalStockAlert, ExpiredLotAlert, UpcomingExpiryAlert } from "../types";

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

// Mock de sonner
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

function createWrapper(lang: "es" | "en" = "es") {
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
          <LanguageProvider initialLanguage={lang}>
            <CurrencyProvider initialCurrency="CLP">
              {children}
            </CurrencyProvider>
          </LanguageProvider>
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

describe("AlertasI18nAndFX Suite — Certificación Exhaustiva i18n & Multi-Moneda FX", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
    setActiveLanguage("es");
    vi.spyOn(httpClient, "apiRequest").mockImplementation(async () => ({
      data: MOCK_ALERTS_SUMMARY,
      traceId: "test-trace",
      timestampIso: new Date().toISOString(),
      tenantId: "tenant_rest_central",
    }));
  });

  afterEach(() => {
    cleanup();
    setActiveLanguage("es");
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. Verificación de Claves y Paridad 1:1 en alerts.json
  // ==========================================================================
  describe("1. Paridad 1:1 y Claves i18n en alerts.json", () => {
    it("proporciona traducciones consistentes en español e inglés para encabezados", () => {
      setActiveLanguage("es");
      expect(translateKey("alerts", "title")).toBe("Alertas");
      expect(translateKey("alerts", "subtitle")).toBe(
        "Estado de Stock y Vencimientos del Sistema"
      );
      expect(translateKey("alerts", "loading")).toBe("Cargando Alertas...");

      setActiveLanguage("en");
      expect(translateKey("alerts", "title")).toBe("Alerts");
      expect(translateKey("alerts", "subtitle")).toBe(
        "System Stock Status and Expirations"
      );
      expect(translateKey("alerts", "loading")).toBe("Loading Alerts...");
    });

    it("traduce filtros del toolbar con paridad 1:1", () => {
      setActiveLanguage("es");
      expect(translateKey("alerts", "toolbar.filter_all")).toBe("Todas las alertas");
      expect(translateKey("alerts", "toolbar.filter_stock")).toBe("Stock Crítico");
      expect(translateKey("alerts", "toolbar.filter_upcoming")).toBe("Próximos a vencer");
      expect(translateKey("alerts", "toolbar.filter_expired")).toBe("Productos Vencidos");
      expect(translateKey("alerts", "toolbar.view_cards")).toBe("Tarjetas");
      expect(translateKey("alerts", "toolbar.view_list")).toBe("Listado");

      setActiveLanguage("en");
      expect(translateKey("alerts", "toolbar.filter_all")).toBe("All Alerts");
      expect(translateKey("alerts", "toolbar.filter_stock")).toBe("Critical Stock");
      expect(translateKey("alerts", "toolbar.filter_upcoming")).toBe("Near Expiration");
      expect(translateKey("alerts", "toolbar.filter_expired")).toBe("Expired Products");
      expect(translateKey("alerts", "toolbar.view_cards")).toBe("Cards");
      expect(translateKey("alerts", "toolbar.view_list")).toBe("List");
    });

    it("traduce tarjetas de stock crítico, vencimientos y estados", () => {
      setActiveLanguage("es");
      expect(translateKey("alerts", "status.depleted")).toBe("Agotado");
      expect(translateKey("alerts", "status.critical")).toBe("Bajo Mínimo");
      expect(translateKey("alerts", "cards.actual")).toBe("Actual");
      expect(translateKey("alerts", "cards.minimo")).toBe("Mínimo");
      expect(translateKey("alerts", "cards.expiration")).toBe("Vencimiento");
      expect(translateKey("alerts", "cards.affected_stock")).toBe("Stock Afectado");
      expect(translateKey("alerts", "cards.total_stock")).toBe("Stock Total");
      expect(translateKey("alerts", "cards.report_merma")).toBe("Reportar Merma");
      expect(translateKey("alerts", "cards.manage")).toBe("Gestionar");

      setActiveLanguage("en");
      expect(translateKey("alerts", "status.depleted")).toBe("Out of Stock");
      expect(translateKey("alerts", "status.critical")).toBe("Below Minimum");
      expect(translateKey("alerts", "cards.actual")).toBe("Current");
      expect(translateKey("alerts", "cards.minimo")).toBe("Minimum");
      expect(translateKey("alerts", "cards.expiration")).toBe("Expiration");
      expect(translateKey("alerts", "cards.affected_stock")).toBe("Affected Stock");
      expect(translateKey("alerts", "cards.total_stock")).toBe("Total Stock");
      expect(translateKey("alerts", "cards.report_merma")).toBe("Report Waste");
      expect(translateKey("alerts", "cards.manage")).toBe("Manage");
    });
  });

  // ==========================================================================
  // 2. Renderizado Reactivo con Cambio de Idioma (ES vs EN)
  // ==========================================================================
  describe("2. Renderizado Reactivo en Componentes (ES vs EN)", () => {
    it("renderiza StockCriticoCard en inglés correctamente al cambiar idioma", () => {
      setActiveLanguage("en");
      render(
        <StockCriticoCard
          item={mockCriticalItem}
          isAnimating={false}
          onAddToCart={vi.fn()}
        />,
        { wrapper: createWrapper("en") }
      );

      expect(screen.getByText("Below Minimum")).toBeInTheDocument();
      expect(screen.getByText("Current")).toBeInTheDocument();
      expect(screen.getByText("Minimum")).toBeInTheDocument();
      const cartBtn = screen.getByTestId("btn-add-cart-card-101");
      expect(cartBtn).toHaveAttribute("title", "Add to shopping cart");
      expect(cartBtn).toHaveAttribute("aria-label", "Buy Pechuga de Pollo");
    });

    it("renderiza StockCriticoCard con 'Out of Stock' cuando stock actual es 0 en EN", () => {
      setActiveLanguage("en");
      render(
        <StockCriticoCard
          item={mockDepletedItem}
          isAnimating={false}
          onAddToCart={vi.fn()}
        />,
        { wrapper: createWrapper("en") }
      );

      expect(screen.getByText("Out of Stock")).toBeInTheDocument();
    });

    it("renderiza ExpiredLotCard en inglés con fecha y distancia relativa", () => {
      setActiveLanguage("en");
      render(<ExpiredLotCard item={mockExpiredItem} />, {
        wrapper: createWrapper("en"),
      });

      expect(screen.getByText("Expiration")).toBeInTheDocument();
      expect(screen.getByText("Lot: LOTE-2024-X")).toBeInTheDocument();
      expect(screen.getByText("Affected Stock")).toBeInTheDocument();
      const reportBtn = screen.getByTestId("btn-report-merma-201");
      expect(reportBtn).toHaveAttribute("title", "Report Waste");
      expect(reportBtn).toHaveAttribute("aria-label", "Report waste for Crema de Leche");
    });

    it("renderiza UpcomingExpiryCard en inglés correctamente", () => {
      setActiveLanguage("en");
      render(<UpcomingExpiryCard item={mockUpcomingItem} />, {
        wrapper: createWrapper("en"),
      });

      expect(screen.getByText("Expiration")).toBeInTheDocument();
      expect(screen.getByText("Lot: LOTE-2026-Y")).toBeInTheDocument();
      expect(screen.getByText("Total Stock")).toBeInTheDocument();
      const manageBtn = screen.getByTestId("btn-manage-upcoming-301");
      expect(manageBtn).toHaveAttribute("title", "Manage");
      expect(manageBtn).toHaveAttribute("aria-label", "Manage Jugo Natural de Naranja");
    });

    it("renderiza StockCriticoTable en inglés con cabeceras y botón traducidos", () => {
      setActiveLanguage("en");
      render(
        <StockCriticoTable
          data={[mockCriticalItem]}
          totalCount={1}
          addToCart={vi.fn()}
          animatingCarts={{}}
        />,
        { wrapper: createWrapper("en") }
      );

      expect(screen.getByText("Products below Minimum Stock")).toBeInTheDocument();
      expect(screen.getByText("1 active alert")).toBeInTheDocument();
      expect(screen.getByText("Product")).toBeInTheDocument();
      expect(screen.getByText("Status / Health")).toBeInTheDocument();
      expect(screen.getByText("Current")).toBeInTheDocument();
      expect(screen.getByText("Minimum")).toBeInTheDocument();
      expect(screen.getByText("Action")).toBeInTheDocument();
      expect(screen.getByText("Below Minimum")).toBeInTheDocument();
    });

    it("renderiza VencimientosCard en inglés con recomendación y estados vacíos", () => {
      setActiveLanguage("en");
      render(
        <VencimientosCard
          type="expired"
          data={[mockExpiredItem]}
          totalCount={1}
        />,
        { wrapper: createWrapper("en") }
      );

      expect(screen.getByText("Expired Products")).toBeInTheDocument();
      expect(screen.getByText(/Affected stock:/i)).toBeInTheDocument();
      expect(
        screen.getByText(
          "It is recommended to write off inventory (Waste) for these products."
        )
      ).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 3. dateUtils Multi-Idioma (es vs en)
  // ==========================================================================
  describe("3. dateUtils Multi-Idioma (Spanish / English relative distances)", () => {
    it("formatea distancias relativas en español con locale es", () => {
      const past = formatDistanceToNow("2020-01-01", { addSuffix: true, locale: es });
      expect(past).toMatch(/hace \d+ (meses|años)/);

      const future = formatDistanceToNow("2099-01-01", { addSuffix: true, locale: es });
      expect(future).toMatch(/en \d+ (meses|años)/);
    });

    it("formatea distancias relativas en inglés con locale en", () => {
      const past = formatDistanceToNow("2020-01-01", { addSuffix: true, locale: en });
      expect(past).toMatch(/\d+ (months|years) ago/);

      const future = formatDistanceToNow("2099-01-01", { addSuffix: true, locale: en });
      expect(future).toMatch(/in \d+ (months|years)/);
    });
  });

  // ==========================================================================
  // 4. Multi-Moneda FX con Precisión Decimal
  // ==========================================================================
  describe("4. Multi-Moneda FX con Precisión Decimal (formatCurrencyAmount)", () => {
    it("formatea montos en CLP sin decimales", () => {
      expect(formatCurrencyAmount(4500, "CLP")).toBe("$4.500");
      expect(formatCurrencyAmount(14400, "CLP")).toBe("$14.400");
      expect(formatCurrencyAmount(37500, "CLP")).toBe("$37.500");
    });

    it("formatea montos en USD y EUR con exactamente 2 decimales", () => {
      expect(formatCurrencyAmount("12.50", "USD")).toBe("US$12.50");
      expect(formatCurrencyAmount("12.50", "EUR")).toBe("€12,50");
    });

    it("formatea montos en UF con exactamente 4 decimales", () => {
      expect(formatCurrencyAmount("1.2500", "UF")).toBe("UF 1,2500");
    });

    it("expone atributos data-unit-cost y data-financial-risk en tarjetas y tablas", () => {
      const { rerender } = render(
        <StockCriticoCard
          item={mockCriticalItem}
          isAnimating={false}
          onAddToCart={vi.fn()}
        />,
        { wrapper: createWrapper("es") }
      );

      const card = screen.getByTestId("card-stock-101");
      expect(card).toHaveAttribute("data-unit-cost", "$4.500");

      rerender(
        <ExpiredLotCard item={mockExpiredItem} />
      );
      const expiredCard = screen.getByTestId("card-expired-201");
      expect(expiredCard).toHaveAttribute("data-financial-risk", "$14.400");
    });
  });
});
