/**
 * oppytec-frontend/src/features/projection/__tests__/projectionChartAndDetail.test.tsx
 * Pruebas Unitarias y de Integración UI para la FASE 6 de Proyección:
 *   - ProyeccionChartTooltip: desglose de lotes caducados (FEFO), eventos agendados y valorización monetaria.
 *   - ProyeccionChart: estados de carga, vacío y curva interactiva con Recharts y ReferenceLine.
 *   - ProyeccionMetrics: valor en inventario, fecha de agotamiento, acciones rápidas de compra y traspaso.
 *   - ProyeccionProductDetail: vista profunda completa con cabecera, navegación y animación Framer Motion.
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import "@testing-library/jest-dom";
import type { HTMLAttributes, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ProyeccionChart,
  ProyeccionChartTooltip,
  ProyeccionMetrics,
  ProyeccionProductDetail,
} from "../components";
import { MOCK_PROJECTION_PRODUCTS } from "../mockData";
import type { DayPoint, ProjectionProductOverview } from "../types";

// Mock de framer-motion para ejecución determinista y rápida en Vitest
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
        initial: _initial,
        animate: _animate,
        exit: _exit,
        transition: _transition,
        ...props
      }: HTMLAttributes<HTMLDivElement> & {
        readonly children?: ReactNode;
        readonly initial?: unknown;
        readonly animate?: unknown;
        readonly exit?: unknown;
        readonly transition?: unknown;
      }) => (
        <div className={className} onClick={onClick} {...props}>
          {children}
        </div>
      ),
    },
  };
});

// Mock de ResponsiveContainer de Recharts para entorno JSDOM
vi.mock("recharts", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { readonly children: ReactNode }) => (
      <div data-testid="recharts-responsive-container" style={{ width: 800, height: 350 }}>
        {children}
      </div>
    ),
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

  return function TestWrapper({ children }: { readonly children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe("Feature Projection - Phase 6 Chart, Tooltip, Metrics & Detail View", () => {
  const sampleProduct: ProjectionProductOverview = {
    ...MOCK_PROJECTION_PRODUCTS[0],
    id: "PRD-001",
    producto_id: "PRD-001",
    nombre: "Pechuga de Pollo Deshuesada",
    costo_unitario: 8900,
    current_qty: 45,
    projected_qty: -12,
    stock_minimo: 15,
    depletion_date: "2026-11-06",
    worst_status: "critical",
    worst_status_label: "Sin stock (día 5)",
    worst_day: 5,
    horizon_days: 30,
    daily_consumption_rate: 6.5,
    calculated_at: "2026-11-01T08:00:00Z",
    unidad: "kg",
  };

  const samplePoints: readonly DayPoint[] = [
    {
      date: "2026-11-01",
      day_index: 0,
      label: "Hoy",
      qty: 45,
      status: "normal",
      statusLabel: "Stock saludable",
    },
    {
      date: "2026-11-03",
      day_index: 2,
      label: "Mar 03/11",
      qty: 28,
      status: "warning",
      statusLabel: "Bajo stock",
      expiring: [
        {
          lote_id: "LOT-9901",
          numero_lote: "L-2026A",
          fecha_vencimiento: "2026-11-03",
          cantidad: 10,
        },
      ],
    },
    {
      date: "2026-11-06",
      day_index: 5,
      label: "Vie 06/11",
      qty: 0,
      status: "critical",
      statusLabel: "Quiebre de stock",
      events: [
        {
          id: "EV-101",
          name: "Banquete Matrimonio Soto",
          qty: 20,
        },
      ],
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("1. ProyeccionChartTooltip", () => {
    it("no debe renderizar nada si active es false o no hay payload", () => {
      const { container } = render(
        <ProyeccionChartTooltip active={false} payload={[]} unit="kg" costoUnitario={5000} />
      );
      expect(container.firstChild).toBeNull();
    });

    it("debe renderizar el stock proyectado y valor monetario estimado", () => {
      const payloadItem = {
        payload: samplePoints[0],
        value: 45,
      };

      render(
        <ProyeccionChartTooltip
          active={true}
          payload={[payloadItem]}
          unit="kg"
          costoUnitario={8900}
        />
      );

      expect(screen.getByTestId("proyeccion-chart-tooltip")).toBeInTheDocument();
      expect(screen.getByText("Hoy")).toBeInTheDocument();
      expect(screen.getByText("45 kg")).toBeInTheDocument();
      // 45 * 8900 = 400.500 CLP
      expect(screen.getByText("$400.500")).toBeInTheDocument();
      expect(screen.getByText("Stock saludable")).toBeInTheDocument();
    });

    it("debe renderizar el desglose de lotes por caducar (FEFO) con icono de alerta", () => {
      const payloadItem = {
        payload: samplePoints[1],
        value: 28,
      };

      render(
        <ProyeccionChartTooltip
          active={true}
          payload={[payloadItem]}
          unit="kg"
          costoUnitario={8900}
        />
      );

      const expiringSection = screen.getByTestId("tooltip-expiring-section");
      expect(expiringSection).toBeInTheDocument();
      expect(screen.getByText("Lote L-2026A")).toBeInTheDocument();
      expect(screen.getByText("-10 kg")).toBeInTheDocument();
    });

    it("debe renderizar el desglose de eventos agendados con icono de calendario", () => {
      const payloadItem = {
        payload: samplePoints[2],
        value: 0,
      };

      render(
        <ProyeccionChartTooltip
          active={true}
          payload={[payloadItem]}
          unit="kg"
          costoUnitario={8900}
        />
      );

      const eventsSection = screen.getByTestId("tooltip-events-section");
      expect(eventsSection).toBeInTheDocument();
      expect(screen.getByText("Banquete Matrimonio Soto")).toBeInTheDocument();
      expect(screen.getByText("-20 kg")).toBeInTheDocument();
    });
  });

  describe("2. ProyeccionChart", () => {
    it("debe mostrar el estado de carga cuando isLoading es true", () => {
      render(<ProyeccionChart data={[]} isLoading={true} />);
      expect(screen.getByTestId("proyeccion-chart-loading")).toBeInTheDocument();
    });

    it("debe mostrar el estado vacío cuando data está vacía", () => {
      render(<ProyeccionChart data={[]} isLoading={false} />);
      expect(screen.getByTestId("proyeccion-chart-empty")).toBeInTheDocument();
    });

    it("debe renderizar el contenedor de gráfico interactivo y la leyenda de stock mínimo", () => {
      render(
        <ProyeccionChart
          data={samplePoints}
          stockMinimo={15}
          unit="kg"
          costoUnitario={8900}
        />
      );

      expect(screen.getByTestId("proyeccion-chart-container")).toBeInTheDocument();
      expect(screen.getByTestId("recharts-responsive-container")).toBeInTheDocument();
      expect(screen.getByText("Mínimo (15 kg)")).toBeInTheDocument();
    });
  });

  describe("3. ProyeccionMetrics", () => {
    it("debe calcular y formatear correctamente el valor actual en inventario", () => {
      render(<ProyeccionMetrics product={sampleProduct} />);

      expect(screen.getByTestId("proyeccion-metrics-panel")).toBeInTheDocument();
      // 45 * 8900 = $400.500
      expect(screen.getByText("$400.500")).toBeInTheDocument();
      expect(screen.getByText("PPP: $8.900/kg")).toBeInTheDocument();
      expect(screen.getByText("Sin stock (día 5)")).toBeInTheDocument();
      expect(screen.getByText("Día 5")).toBeInTheDocument();
    });

    it("debe invocar onManagePurchase al hacer click en 'Gestionar Pedido / Compra'", () => {
      const handlePurchase = vi.fn();
      render(
        <ProyeccionMetrics
          product={sampleProduct}
          onManagePurchase={handlePurchase}
        />
      );

      const btnPurchase = screen.getByTestId("btn-manage-purchase");
      fireEvent.click(btnPurchase);
      expect(handlePurchase).toHaveBeenCalledTimes(1);
      expect(handlePurchase).toHaveBeenCalledWith(sampleProduct);
    });

    it("debe invocar onOpenTransfer al hacer click en 'Trasladar desde otra Bodega'", () => {
      const handleTransfer = vi.fn();
      render(
        <ProyeccionMetrics
          product={sampleProduct}
          onOpenTransfer={handleTransfer}
        />
      );

      const btnTransfer = screen.getByTestId("btn-open-transfer");
      fireEvent.click(btnTransfer);
      expect(handleTransfer).toHaveBeenCalledTimes(1);
      expect(handleTransfer).toHaveBeenCalledWith(sampleProduct);
    });
  });

  describe("4. ProyeccionProductDetail", () => {
    it("debe renderizar la vista de detalle completa e invocar onBack al pulsar retorno", async () => {
      const handleBack = vi.fn();
      const Wrapper = createWrapper();

      render(
        <Wrapper>
          <ProyeccionProductDetail
            product={sampleProduct}
            onBack={handleBack}
            horizonDays={30}
          />
        </Wrapper>
      );

      expect(screen.getByTestId("proyeccion-product-detail")).toBeInTheDocument();
      expect(screen.getByText(sampleProduct.nombre)).toBeInTheDocument();
      expect(screen.getByText("Horizonte: 30 días")).toBeInTheDocument();

      const backBtn = screen.getByTestId("btn-back-to-list");
      fireEvent.click(backBtn);
      expect(handleBack).toHaveBeenCalledTimes(1);

      // El panel de métricas y el gráfico deben estar en el documento
      expect(screen.getByTestId("proyeccion-metrics-panel")).toBeInTheDocument();
      expect(await screen.findByTestId("proyeccion-chart-container")).toBeInTheDocument();
    });
  });
});
