/**
 * oppytec-frontend/src/features/projection/__tests__/projectionEventAlertsAndIntegration.test.tsx
 * Pruebas Unitarias e Integración UI para la FASE 7 de Proyección:
 *   - ProyeccionEventAlerts: renderizado de alertas agendadas, déficit, colapso/expansión y fallback nulo.
 *   - ProyeccionTransferModal: diálogo ResponsiveDialog pre-poblado, edición de cantidad y feedback sonner.
 *   - ProyeccionView: integración completa de la vista maestra (Header, Banner, Alertas, Toolbar, Grid, Paginación, Detalle y Modal).
 * TypeScript estricto, 0 any, 0 hardcoded strings.
 */
import "@testing-library/jest-dom";
import type { HTMLAttributes, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ProyeccionEventAlerts,
  ProyeccionTransferModal,
} from "../components";
import { ProyeccionView } from "../index";
import {
  MOCK_PROJECTION_ALERTS,
  MOCK_TRANSFER_SUGGESTIONS,
} from "../mockData";
import type { EventProjectionAlert, TransferSuggestion } from "../types";

// Mock de sonner para espionaje de notificaciones toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

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
        layout: _layout,
        layoutId: _layoutId,
        whileHover: _whileHover,
        whileTap: _whileTap,
        ...props
      }: HTMLAttributes<HTMLDivElement> & {
        readonly children?: ReactNode;
        readonly initial?: unknown;
        readonly animate?: unknown;
        readonly exit?: unknown;
        readonly transition?: unknown;
        readonly layout?: unknown;
        readonly layoutId?: unknown;
        readonly whileHover?: unknown;
        readonly whileTap?: unknown;
      }) => (
        <div className={className} onClick={onClick} {...props}>
          {children}
        </div>
      ),
    },
  };
});

// Mock de recharts para JSDOM
vi.mock("recharts", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { readonly children: ReactNode }) => (
      <div data-testid="mock-responsive-container">{children}</div>
    ),
    LineChart: ({ children }: { readonly children: ReactNode }) => (
      <svg data-testid="mock-line-chart">{children}</svg>
    ),
    CartesianGrid: () => <g data-testid="mock-grid" />,
    XAxis: () => <g data-testid="mock-xaxis" />,
    YAxis: () => <g data-testid="mock-yaxis" />,
    Tooltip: () => <g data-testid="mock-tooltip" />,
    ReferenceLine: () => <g data-testid="mock-ref-line" />,
    Line: () => <g data-testid="mock-line" />,
  };
});

describe("FASE 7: Consola de Alertas de Eventos Críticos (ProyeccionEventAlerts)", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("retorna null si la lista de alertas es undefined o null", () => {
    const { container } = render(<ProyeccionEventAlerts alerts={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("retorna null si la lista de alertas es un arreglo vacío", () => {
    const { container } = render(<ProyeccionEventAlerts alerts={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza el panel de alertas con título, contador y tarjetas de eventos agendados", () => {
    render(<ProyeccionEventAlerts alerts={MOCK_PROJECTION_ALERTS} />);

    expect(screen.getByTestId("proyeccion-event-alerts")).toBeInTheDocument();
    expect(screen.getByText("Alertas de Eventos Críticos y Banquetes")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument(); // Badge de cantidad de alertas

    // Tarjeta de alerta 101 (Pechuga de Pollo)
    expect(screen.getByTestId("event-alert-card-101")).toBeInTheDocument();
    expect(screen.getByText("Cena de Gala Corporativa Tech")).toBeInTheDocument();
    expect(screen.getByText("Pechuga de Pollo Deshuesada")).toBeInTheDocument();

    // Tarjeta de alerta 103 (Salmón Fresco)
    expect(screen.getByTestId("event-alert-card-103")).toBeInTheDocument();
    expect(screen.getByText("Matrimonio González-Larraín")).toBeInTheDocument();
    expect(screen.getByText("Salmón Fresco Filete")).toBeInTheDocument();
  });

  it("permite colapsar y expandir el panel mediante el botón de toggle", () => {
    render(<ProyeccionEventAlerts alerts={MOCK_PROJECTION_ALERTS} />);

    const toggleBtn = screen.getByTestId("toggle-alerts-btn");
    expect(screen.getByTestId("event-alert-card-101")).toBeInTheDocument();

    // Colapsar
    fireEvent.click(toggleBtn);
    expect(screen.queryByTestId("event-alert-card-101")).not.toBeInTheDocument();
    expect(screen.getByText("Ver alertas")).toBeInTheDocument();

    // Re-expandir
    fireEvent.click(toggleBtn);
    expect(screen.getByTestId("event-alert-card-101")).toBeInTheDocument();
    expect(screen.getByText("Ocultar")).toBeInTheDocument();
  });

  it("dispara onExecuteTransfer al presionar el botón de traspaso con la sugerencia correspondiente", () => {
    const onExecuteTransfer = vi.fn();
    render(
      <ProyeccionEventAlerts
        alerts={MOCK_PROJECTION_ALERTS}
        onExecuteTransfer={onExecuteTransfer}
      />
    );

    const transferBtn = screen.getByTestId("execute-transfer-btn-101");
    expect(transferBtn).toBeInTheDocument();

    fireEvent.click(transferBtn);
    expect(onExecuteTransfer).toHaveBeenCalledTimes(1);
    expect(onExecuteTransfer).toHaveBeenCalledWith(
      expect.objectContaining({
        producto_id: 101,
        bodega_origen_id: 2,
        bodega_destino_id: 1,
        cantidad_sugerida: 18.0,
      })
    );
  });

  it("utiliza fallback de sugerencia si la alerta no incluye sugerencias explícitas", () => {
    const onExecuteTransfer = vi.fn();
    const alertWithoutSuggestions: EventProjectionAlert = {
      producto_id: 999,
      producto_nombre: "Carne Vacuno Lomo Liso",
      bodega_id: 3,
      bodega_nombre: "Bodega Principal",
      status: "critical",
      status_label: "Quiebre inminente",
      current_stock: 5,
      projected_stock: -12,
      transfer_suggestions: [],
      event_name: "Catering Evento Anual",
      deficit_qty: 12,
    };

    render(
      <ProyeccionEventAlerts
        alerts={[alertWithoutSuggestions]}
        onExecuteTransfer={onExecuteTransfer}
      />
    );

    const btn = screen.getByTestId("execute-transfer-btn-999");
    fireEvent.click(btn);

    expect(onExecuteTransfer).toHaveBeenCalledTimes(1);
    expect(onExecuteTransfer).toHaveBeenCalledWith(
      expect.objectContaining({
        producto_id: 999,
        bodega_destino_id: 3,
        cantidad_sugerida: 12,
      })
    );
  });
});

describe("FASE 7: Modal de Traspaso Preventivo (ProyeccionTransferModal)", () => {
  const sampleSuggestion: TransferSuggestion = MOCK_TRANSFER_SUGGESTIONS[0]!;

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("retorna null si open es false", () => {
    const { container } = render(
      <ProyeccionTransferModal
        open={false}
        onClose={vi.fn()}
        suggestion={sampleSuggestion}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it("retorna null si suggestion es null aunque open sea true", () => {
    const { container } = render(
      <ProyeccionTransferModal
        open={true}
        onClose={vi.fn()}
        suggestion={null}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renderiza el diálogo con los datos pre-poblados de la sugerencia", () => {
    render(
      <ProyeccionTransferModal
        open={true}
        onClose={vi.fn()}
        suggestion={sampleSuggestion}
        productName="Pechuga de Pollo Deshuesada"
        productUnit="kg"
      />
    );

    expect(screen.getByTestId("proyeccion-transfer-modal")).toBeInTheDocument();
    expect(screen.getByText("Confirmar Traspaso Preventivo")).toBeInTheDocument();
    expect(screen.getByText("Pechuga de Pollo Deshuesada")).toBeInTheDocument();
    expect(screen.getByText("Bodega Bar & Grill")).toBeInTheDocument();
    expect(screen.getByText("16 días de cobertura")).toBeInTheDocument();

    const input = screen.getByTestId("transfer-qty-input") as HTMLInputElement;
    expect(input.value).toBe("18");
  });

  it("permite modificar la cantidad y llamar a onConfirm con la nueva cantidad", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(
      <ProyeccionTransferModal
        open={true}
        onClose={onClose}
        suggestion={sampleSuggestion}
        productName="Pechuga de Pollo Deshuesada"
        productUnit="kg"
        onConfirm={onConfirm}
      />
    );

    const input = screen.getByTestId("transfer-qty-input");
    fireEvent.change(input, { target: { value: "25.5" } });

    const confirmBtn = screen.getByTestId("confirm-transfer-btn");
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledTimes(1);
      expect(onConfirm).toHaveBeenCalledWith(sampleSuggestion, 25.5);
    });

    expect(toast.success).toHaveBeenCalledWith(
      "Traspaso preventivo registrado exitosamente en el inventario"
    );
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("bloquea el traspaso si la cantidad es 0 o negativa y muestra toast.error", async () => {
    const onConfirm = vi.fn();

    render(
      <ProyeccionTransferModal
        open={true}
        onClose={vi.fn()}
        suggestion={sampleSuggestion}
        onConfirm={onConfirm}
      />
    );

    const input = screen.getByTestId("transfer-qty-input");
    fireEvent.change(input, { target: { value: "0" } });

    const confirmBtn = screen.getByTestId("confirm-transfer-btn");
    fireEvent.click(confirmBtn);

    expect(onConfirm).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith(
      "La cantidad a transferir debe ser mayor a 0"
    );
  });

  it("cierra el diálogo al presionar el botón de Cancelar", () => {
    const onClose = vi.fn();

    render(
      <ProyeccionTransferModal
        open={true}
        onClose={onClose}
        suggestion={sampleSuggestion}
      />
    );

    const cancelBtn = screen.getByTestId("cancel-transfer-btn");
    fireEvent.click(cancelBtn);

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("FASE 7: Integración Completa de la Vista Maestra (ProyeccionView)", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: 0,
        },
      },
    });
  });

  afterEach(() => {
    cleanup();
    queryClient.clear();
    vi.clearAllMocks();
  });

  const renderWithProviders = (ui: ReactNode) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {ui}
      </QueryClientProvider>
    );
  };

  it("renderiza la pantalla completa con Header, Banner Ejecutivo, Alertas, Toolbar, Grid y Paginación", async () => {
    renderWithProviders(<ProyeccionView />);

    expect(screen.getByTestId("feature-proyeccion")).toBeInTheDocument();
    expect(screen.getByTestId("proyeccion-header")).toBeInTheDocument();
    expect(screen.getByTestId("proyeccion-toolbar")).toBeInTheDocument();

    // Verificamos que el grid carga o está en loading y luego resuelve
    await waitFor(() => {
      expect(screen.getByTestId("proyeccion-product-grid")).toBeInTheDocument();
      expect(screen.getByTestId("proyeccion-pagination")).toBeInTheDocument();
    });

    // Verificamos que las alertas de eventos se cargan e integran
    await waitFor(() => {
      expect(screen.getByTestId("proyeccion-event-alerts")).toBeInTheDocument();
    });
  });

  it("permite abrir y cerrar el filtro de categorías desde la barra de herramientas", async () => {
    renderWithProviders(<ProyeccionView />);

    // Esperar a que los datos iniciales se resuelvan y pueblen las categorías
    await waitFor(() => {
      expect(screen.getByTestId("proyeccion-product-grid")).toBeInTheDocument();
    });

    const toggleCategoriesBtn = screen.getByTestId("projection-toggle-categories");
    expect(screen.queryByTestId("proyeccion-category-filter")).not.toBeInTheDocument();

    // Abrir categorías
    fireEvent.click(toggleCategoriesBtn);
    await waitFor(() => {
      expect(screen.getByTestId("proyeccion-category-filter")).toBeInTheDocument();
    });

    // Cerrar categorías
    fireEvent.click(toggleCategoriesBtn);
    expect(screen.queryByTestId("proyeccion-category-filter")).not.toBeInTheDocument();
  });

  it("navega hacia la vista de detalle profundo al hacer click en una tarjeta de producto", async () => {
    renderWithProviders(<ProyeccionView />);

    // Buscar una tarjeta de producto en el grid
    const productCard = await screen.findByTestId("projection-product-card-101");
    expect(productCard).toBeInTheDocument();

    // Click para entrar en detalle
    fireEvent.click(productCard);

    // Debe mostrar la vista de detalle profundo
    await waitFor(() => {
      expect(screen.getByTestId("proyeccion-product-detail")).toBeInTheDocument();
      expect(screen.getByText("Volver al listado")).toBeInTheDocument();
    });

    // Click en volver al listado
    const backBtn = screen.getByRole("button", { name: /Volver al listado/i });
    fireEvent.click(backBtn);

    // Vuelve al grid principal
    await waitFor(() => {
      expect(screen.getByTestId("proyeccion-product-grid")).toBeInTheDocument();
    });
  });

  it("abre el modal de traspaso preventivo al clickear 'Ejecutar Traspaso Preventivo' en las alertas", async () => {
    renderWithProviders(<ProyeccionView />);

    const executeBtn = await screen.findByTestId("execute-transfer-btn-101");
    expect(executeBtn).toBeInTheDocument();

    fireEvent.click(executeBtn);

    // El modal de traspaso debe abrirse
    await waitFor(() => {
      expect(screen.getByTestId("proyeccion-transfer-modal")).toBeInTheDocument();
      expect(screen.getByText("Confirmar Traspaso Preventivo")).toBeInTheDocument();
    });

    // Cerrar modal
    const cancelBtn = screen.getByTestId("cancel-transfer-btn");
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(screen.queryByTestId("proyeccion-transfer-modal")).not.toBeInTheDocument();
    });
  });
});
