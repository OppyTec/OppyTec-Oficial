// oppytec-frontend/src/features/inventory/__tests__/ModalesStock.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import * as httpClient from "@/shared/api/httpClient";
import {
  TransferDialog,
  AdjustmentDialog,
  MermaDialog,
  AddingMercaderiaDialog,
  SolicitudesDialog,
} from "../stock/dialogs";
import { StockRegistroPage } from "../stock/StockRegistroPage";
import { MOCK_STOCK_ITEMS, MOCK_BODEGAS } from "../mockData";

// Mock de framer-motion
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
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <PermissionsProvider>{children}</PermissionsProvider>
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

describe("Modales Operativos Especializados de Stock (Fase 5)", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (_url, options) => {
      if (options?.fallbackData) {
        return {
          data: options.fallbackData,
          tenantId: "tenant_rest_central",
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          isFallback: false,
        };
      }
      return {
        data: { success: true },
        tenantId: "tenant_rest_central",
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        isFallback: false,
      };
    });
  });

  describe("1. TransferDialog (Traspaso Inter-Bodega)", () => {
    it("renderiza correctamente cuando open=true y muestra selección de bodegas", () => {
      const handleClose = vi.fn();
      const handleTransfer = vi.fn().mockResolvedValue({});

      render(
        <TransferDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          initialProduct={MOCK_STOCK_ITEMS[0]}
          onTransfer={handleTransfer}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId("dialog-transfer-container")).toBeInTheDocument();
      expect(screen.getByTestId("transfer-origen-select")).toBeInTheDocument();
      expect(screen.getByTestId("transfer-destino-select")).toBeInTheDocument();
      expect(screen.getByTestId("btn-confirm-transfer")).toBeInTheDocument();
    });

    it("valida y muestra error si la cantidad solicitada supera el stock disponible en origen", () => {
      const handleClose = vi.fn();
      const handleTransfer = vi.fn().mockResolvedValue({});
      const item = MOCK_STOCK_ITEMS[0]; // Stock = 35.0

      render(
        <TransferDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          initialProduct={item}
          onTransfer={handleTransfer}
        />,
        { wrapper: createWrapper() }
      );

      const qtyInput = screen.getByTestId("transfer-item-qty-0");
      // Asignar cantidad 500 (supera los 35 disponibles)
      fireEvent.change(qtyInput, { target: { value: "500" } });

      expect(screen.getByText(/supera el stock disponible/i)).toBeInTheDocument();
      expect(screen.getByTestId("btn-confirm-transfer")).toBeDisabled();
    });

    it("permite agregar otra fila de insumo y enviar transferencia exitosa", async () => {
      const handleClose = vi.fn();
      const handleTransfer = vi.fn().mockResolvedValue({ success: true });
      const item = MOCK_STOCK_ITEMS[0];

      render(
        <TransferDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          initialProduct={item}
          onTransfer={handleTransfer}
        />,
        { wrapper: createWrapper() }
      );

      // Agregar fila
      const btnAddRow = screen.getByTestId("btn-add-transfer-row");
      fireEvent.click(btnAddRow);

      expect(screen.getByTestId("transfer-row-1")).toBeInTheDocument();

      // Ajustar cantidades válidas
      const qty0 = screen.getByTestId("transfer-item-qty-0");
      fireEvent.change(qty0, { target: { value: "5" } });

      const qty1 = screen.getByTestId("transfer-item-qty-1");
      fireEvent.change(qty1, { target: { value: "2" } });

      // Enviar
      const btnConfirm = screen.getByTestId("btn-confirm-transfer");
      expect(btnConfirm).not.toBeDisabled();
      fireEvent.click(btnConfirm);

      await waitFor(() => {
        expect(handleTransfer).toHaveBeenCalledTimes(1);
        expect(handleClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe("2. AdjustmentDialog (Ajuste Positivo / Negativo)", () => {
    it("conmuta entre Ajuste Positivo y Ajuste Negativo actualizando estilos", () => {
      const handleClose = vi.fn();
      const handleMovement = vi.fn().mockResolvedValue({});

      render(
        <AdjustmentDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          initialProduct={MOCK_STOCK_ITEMS[0]}
          onRegisterMovement={handleMovement}
        />,
        { wrapper: createWrapper() }
      );

      const btnPositivo = screen.getByTestId("btn-ajuste-positivo");
      const btnNegativo = screen.getByTestId("btn-ajuste-negativo");

      expect(btnPositivo).toBeInTheDocument();
      expect(btnNegativo).toBeInTheDocument();

      // Click en negativo
      fireEvent.click(btnNegativo);
      expect(screen.getByText(/Salida/i)).toBeInTheDocument();
    });

    it("valida que en Ajuste Negativo la cantidad no supere el stock disponible", () => {
      const handleClose = vi.fn();
      const handleMovement = vi.fn().mockResolvedValue({});
      const item = MOCK_STOCK_ITEMS[0]; // Stock actual = 35.0

      render(
        <AdjustmentDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          initialProduct={item}
          onRegisterMovement={handleMovement}
        />,
        { wrapper: createWrapper() }
      );

      fireEvent.click(screen.getByTestId("btn-ajuste-negativo"));

      const qtyInput = screen.getByTestId("adjustment-quantity-input");
      fireEvent.change(qtyInput, { target: { value: "99" } });

      expect(screen.getByText(/Supera el stock actual/i)).toBeInTheDocument();
      expect(screen.getByTestId("btn-confirm-adjustment")).toBeDisabled();
    });

    it("ejecuta el ajuste llamando a onRegisterMovement con payload completo", async () => {
      const handleClose = vi.fn();
      const handleMovement = vi.fn().mockResolvedValue({ id: 99 });

      render(
        <AdjustmentDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          initialProduct={MOCK_STOCK_ITEMS[0]}
          onRegisterMovement={handleMovement}
        />,
        { wrapper: createWrapper() }
      );

      const qtyInput = screen.getByTestId("adjustment-quantity-input");
      fireEvent.change(qtyInput, { target: { value: "4" } });

      const notesInput = screen.getByTestId("adjustment-notes-input");
      fireEvent.change(notesInput, { target: { value: "Auditoría mensual autorizada" } });

      const btnConfirm = screen.getByTestId("btn-confirm-adjustment");
      fireEvent.click(btnConfirm);

      await waitFor(() => {
        expect(handleMovement).toHaveBeenCalledTimes(1);
        expect(handleMovement).toHaveBeenCalledWith(
          expect.objectContaining({
            cantidad: 4,
            tipo_movimiento: "AJUSTE_POSITIVO",
            reason: expect.stringContaining("Auditoría mensual autorizada"),
          })
        );
        expect(handleClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe("3. MermaDialog (Reporte de Mermas con Lotes y Umbral)", () => {
    it("muestra selector de lote y alerta de umbral cuando el monto supera $50.000", () => {
      const handleClose = vi.fn();
      const handleMerma = vi.fn().mockResolvedValue({});
      const item = MOCK_STOCK_ITEMS[0]; // Costo PPP = 14200

      render(
        <MermaDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          initialProduct={item}
          onReportMerma={handleMerma}
        />,
        { wrapper: createWrapper() }
      );

      // Si la cantidad es 1, monto = 14.200 (< 50.000), no debe haber alerta
      expect(screen.queryByTestId("merma-threshold-warning")).not.toBeInTheDocument();

      // Cambiamos cantidad a 5 -> monto = 5 * 14.200 = 71.000 (>= 50.000)
      const qtyInput = screen.getByTestId("merma-quantity-input");
      fireEvent.change(qtyInput, { target: { value: "5" } });

      expect(screen.getByTestId("merma-threshold-warning")).toBeInTheDocument();
      expect(screen.getByText(/Requiere Aprobación de Supervisor/i)).toBeInTheDocument();
    });

    it("permite seleccionar un lote específico y confirmar la merma", async () => {
      const handleClose = vi.fn();
      const handleMerma = vi.fn().mockResolvedValue({ id: 1 });
      const item = MOCK_STOCK_ITEMS[0]!;

      render(
        <MermaDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          initialProduct={item}
          onReportMerma={handleMerma}
        />,
        { wrapper: createWrapper() }
      );

      // Seleccionar segundo lote si existe
      if (item.lotes && item.lotes.length > 1) {
        const secondLot = item.lotes[1];
        if (secondLot) {
          const lotBadge = screen.getByTestId(`merma-lote-badge-${secondLot.lote_codigo}`);
          fireEvent.click(lotBadge);
        }
      }

      const notesInput = screen.getByTestId("merma-notes-input");
      fireEvent.change(notesInput, { target: { value: "Pérdida por corte de luz" } });

      const btnConfirm = screen.getByTestId("btn-confirm-merma");
      fireEvent.click(btnConfirm);

      await waitFor(() => {
        expect(handleMerma).toHaveBeenCalledTimes(1);
        expect(handleMerma).toHaveBeenCalledWith(
          expect.objectContaining({
            quantity: 1,
            unit_cost: item.costo_unitario_ppp,
            reason: expect.stringContaining("Pérdida por corte de luz"),
          })
        );
        expect(handleClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe("4. AddingMercaderiaDialog (Recepción Rápida / Ingreso Libre)", () => {
    it("conmuta entre pestaña de pedidos y pestaña de ingreso libre directo", () => {
      const handleClose = vi.fn();

      render(
        <AddingMercaderiaDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId("tab-receive-pedidos")).toBeInTheDocument();
      expect(screen.getByTestId("tab-receive-libre")).toBeInTheDocument();

      // Pestaña pedidos por defecto
      expect(screen.getByTestId("search-pedidos-input")).toBeInTheDocument();

      // Conmutar a libre
      fireEvent.click(screen.getByTestId("tab-receive-libre"));
      expect(screen.getByTestId("libre-quantity-input")).toBeInTheDocument();
      expect(screen.getByTestId("libre-lote-input")).toBeInTheDocument();
      expect(screen.getByTestId("libre-expiry-input")).toBeInTheDocument();
    });

    it("permite recepcionar una orden de compra pendiente", async () => {
      const handleClose = vi.fn();
      const handleMovement = vi.fn().mockResolvedValue({});

      render(
        <AddingMercaderiaDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          onRegisterMovement={handleMovement}
        />,
        { wrapper: createWrapper() }
      );

      const btnReceive = screen.getByTestId("btn-receive-purchase-101");
      fireEvent.click(btnReceive);

      await waitFor(() => {
        expect(handleMovement).toHaveBeenCalledTimes(1);
        expect(handleClose).toHaveBeenCalledTimes(1);
      });
    });

    it("permite registrar un ingreso libre directo con lote y fecha", async () => {
      const handleClose = vi.fn();
      const handleMovement = vi.fn().mockResolvedValue({});

      render(
        <AddingMercaderiaDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          onRegisterMovement={handleMovement}
        />,
        { wrapper: createWrapper() }
      );

      fireEvent.click(screen.getByTestId("tab-receive-libre"));

      const qtyInput = screen.getByTestId("libre-quantity-input");
      fireEvent.change(qtyInput, { target: { value: "15" } });

      const docInput = screen.getByTestId("libre-doc-input");
      fireEvent.change(docInput, { target: { value: "Factura 9912 Distribuidora" } });

      const btnConfirm = screen.getByTestId("btn-confirm-libre");
      fireEvent.click(btnConfirm);

      await waitFor(() => {
        expect(handleMovement).toHaveBeenCalledWith(
          expect.objectContaining({
            cantidad: 15,
            tipo_movimiento: "ENTRADA",
            documento_referencia: expect.stringContaining("Factura 9912"),
          })
        );
        expect(handleClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe("5. SolicitudesDialog (Gestión de Pedidos Internos)", () => {
    it("filtra por pestañas de estado (Pendientes, En Ruta, Recibidas, Canceladas)", () => {
      const handleClose = vi.fn();

      render(
        <SolicitudesDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId("solicitudes-tab-pendientes")).toBeInTheDocument();
      expect(screen.getByTestId("solicitudes-tab-en_ruta")).toBeInTheDocument();
      expect(screen.getByTestId("solicitudes-tab-recibidas")).toBeInTheDocument();
      expect(screen.getByTestId("solicitudes-tab-canceladas")).toBeInTheDocument();

      // Click en En Ruta
      fireEvent.click(screen.getByTestId("solicitudes-tab-en_ruta"));
      expect(screen.getByTestId("solicitud-item-2")).toBeInTheDocument();

      // Click en Canceladas
      fireEvent.click(screen.getByTestId("solicitudes-tab-canceladas"));
      expect(screen.getByTestId("solicitud-item-4")).toBeInTheDocument();
    });

    it("permite emitir una nueva solicitud de reposición", async () => {
      const handleClose = vi.fn();
      const handleCreated = vi.fn();

      render(
        <SolicitudesDialog
          open={true}
          onClose={handleClose}
          stockItems={MOCK_STOCK_ITEMS}
          bodegas={MOCK_BODEGAS}
          onRequestCreated={handleCreated}
        />,
        { wrapper: createWrapper() }
      );

      // Abrir formulario de nueva solicitud
      const btnToggle = screen.getByTestId("btn-toggle-nueva-solicitud");
      fireEvent.click(btnToggle);

      expect(screen.getByTestId("form-nueva-solicitud")).toBeInTheDocument();

      // Configurar cantidad y notas
      const qtyInput = screen.getByTestId("solicitud-quantity-input");
      fireEvent.change(qtyInput, { target: { value: "25" } });

      const notesInput = screen.getByTestId("solicitud-notes-input");
      fireEvent.change(notesInput, { target: { value: "Stock crítico de fin de semana" } });

      // Emitir pedido
      const btnSubmit = screen.getByTestId("btn-submit-solicitud");
      fireEvent.click(btnSubmit);

      await waitFor(() => {
        expect(handleCreated).toHaveBeenCalledTimes(1);
        expect(handleCreated).toHaveBeenCalledWith(
          expect.objectContaining({
            cantidad: 25,
            estado: "pendientes",
          })
        );
      });
    });
  });

  describe("6. Integración en StockRegistroPage", () => {
    it("abre y cierra cada uno de los 5 diálogos desde la Toolbar y filas", async () => {
      render(<StockRegistroPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("stock-registro-container")).toBeInTheDocument();
      });

      // 1. Abrir Ajustar desde toolbar
      const btnAjustar = screen.getAllByTestId("stock-action-adjustment")[0]!;
      fireEvent.click(btnAjustar);
      expect(screen.getByTestId("dialog-adjustment-container")).toBeInTheDocument();
      fireEvent.click(screen.getByTestId("responsive-dialog-close"));
      await waitFor(() => {
        expect(screen.queryByTestId("dialog-adjustment-container")).not.toBeInTheDocument();
      });

      // 2. Abrir Merma desde toolbar
      const btnMerma = screen.getAllByTestId("stock-action-merma")[0]!;
      fireEvent.click(btnMerma);
      expect(screen.getByTestId("dialog-merma-container")).toBeInTheDocument();
      fireEvent.click(screen.getByTestId("responsive-dialog-close"));
      await waitFor(() => {
        expect(screen.queryByTestId("dialog-merma-container")).not.toBeInTheDocument();
      });

      // 3. Abrir Recibir desde toolbar
      const btnRecibir = screen.getAllByTestId("stock-action-receive")[0]!;
      fireEvent.click(btnRecibir);
      expect(screen.getByTestId("dialog-adding-mercaderia-container")).toBeInTheDocument();
      fireEvent.click(screen.getByTestId("responsive-dialog-close"));
      await waitFor(() => {
        expect(screen.queryByTestId("dialog-adding-mercaderia-container")).not.toBeInTheDocument();
      });

      // 4. Abrir Solicitudes desde toolbar
      const btnSolicitudes = screen.getAllByTestId("stock-action-solicitar")[0]!;
      fireEvent.click(btnSolicitudes);
      expect(screen.getByTestId("dialog-solicitudes-container")).toBeInTheDocument();
      fireEvent.click(screen.getByTestId("responsive-dialog-close"));
      await waitFor(() => {
        expect(screen.queryByTestId("dialog-solicitudes-container")).not.toBeInTheDocument();
      });

      // 5. Abrir Transferencia desde acción de fila
      const btnTransferRow = screen.getAllByTestId(`btn-transferir-${MOCK_STOCK_ITEMS[0]!.id}`)[0]!;
      fireEvent.click(btnTransferRow);
      expect(screen.getByTestId("dialog-transfer-container")).toBeInTheDocument();
      fireEvent.click(screen.getByTestId("responsive-dialog-close"));
      await waitFor(() => {
        expect(screen.queryByTestId("dialog-transfer-container")).not.toBeInTheDocument();
      });
    });
  });
});
