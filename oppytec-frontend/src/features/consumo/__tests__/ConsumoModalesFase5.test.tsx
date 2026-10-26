// oppytec-frontend/src/features/consumo/__tests__/ConsumoModalesFase5.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  ConsumoCart,
  BotonesFlotantes,
  ConsumoOptionsDialog,
  ConsumoTemplateModal,
  ContingencyModal,
  LocateStockDialog,
  ConsumoEditDialog,
  ConsumoLog,
} from "../components";
import {
  MOCK_PRODUCTOS_CONSUMO,
  MOCK_RECETAS_CONSUMO,
  MOCK_CATEGORIAS_CONSUMO,
} from "../mockData";
import type { CartItem, ConsumptionRecord } from "../types";

describe("Módulo de Consumo - Fase 5: Modales Operativos y Carrito de Consumo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==========================================================================
  // 1. BotonesFlotantes
  // ==========================================================================
  describe("BotonesFlotantes", () => {
    it("renders floating action buttons and triggers callbacks", () => {
      const handleOpenCart = vi.fn();
      const handleOpenLog = vi.fn();

      render(
        <BotonesFlotantes
          cartCount={3}
          onOpenCart={handleOpenCart}
          onOpenLog={handleOpenLog}
        />
      );

      expect(screen.getByTestId("floating-buttons-container")).toBeInTheDocument();
      expect(screen.getByTestId("floating-cart-badge")).toHaveTextContent("3");

      fireEvent.click(screen.getByTestId("floating-cart-btn"));
      expect(handleOpenCart).toHaveBeenCalledTimes(1);

      fireEvent.click(screen.getByTestId("floating-history-btn"));
      expect(handleOpenLog).toHaveBeenCalledTimes(1);
    });
  });

  // ==========================================================================
  // 2. ConsumoCart
  // ==========================================================================
  describe("ConsumoCart", () => {
    const mockCart: CartItem[] = [
      {
        id: "prod-salm-01",
        cartItemId: "cart-item-1",
        name: "Salmón Fresco Filete",
        type: "producto",
        quantity: 2,
        bodega_id: "1",
        unit: "kg",
        price: 15990,
      },
    ];

    it("renders empty cart state when cart has no items", () => {
      render(
        <ConsumoCart
          open={true}
          onOpenChange={vi.fn()}
          cart={[]}
          onUpdateQty={vi.fn()}
          onRemove={vi.fn()}
          onClearCart={vi.fn()}
          onSubmit={vi.fn()}
          getStock={() => 10}
        />
      );

      expect(screen.getByTestId("consumo-cart-drawer")).toBeInTheDocument();
      expect(screen.getByTestId("consumo-cart-empty")).toBeInTheDocument();
      expect(screen.getByText("Tu carrito está vacío")).toBeInTheDocument();
    });

    it("renders active items with quantity controls and triggers actions", () => {
      const handleUpdateQty = vi.fn();
      const handleRemove = vi.fn();
      const handleClear = vi.fn();
      const handleSubmit = vi.fn();

      render(
        <ConsumoCart
          open={true}
          onOpenChange={vi.fn()}
          cart={mockCart}
          allRecetas={MOCK_RECETAS_CONSUMO}
          productos={MOCK_PRODUCTOS_CONSUMO}
          onUpdateQty={handleUpdateQty}
          onRemove={handleRemove}
          onClearCart={handleClear}
          onSubmit={handleSubmit}
          getStock={() => 10}
        />
      );

      expect(screen.getByTestId("cart-item-cart-item-1")).toBeInTheDocument();
      expect(screen.getByText("Salmón Fresco Filete")).toBeInTheDocument();

      // Controles de cantidad
      fireEvent.click(screen.getByTestId("cart-qty-plus-cart-item-1"));
      expect(handleUpdateQty).toHaveBeenCalledWith("cart-item-1", 3);

      fireEvent.click(screen.getByTestId("cart-qty-minus-cart-item-1"));
      expect(handleUpdateQty).toHaveBeenCalledWith("cart-item-1", 1);

      // Eliminar y vaciar
      fireEvent.click(screen.getByTestId("cart-remove-btn-cart-item-1"));
      expect(handleRemove).toHaveBeenCalledWith("cart-item-1");

      fireEvent.click(screen.getByTestId("cart-clear-btn"));
      expect(handleClear).toHaveBeenCalledTimes(1);

      // Submit
      fireEvent.click(screen.getByTestId("cart-submit-btn"));
      expect(handleSubmit).toHaveBeenCalledTimes(1);
    });
  });

  // ==========================================================================
  // 3. ConsumoOptionsDialog
  // ==========================================================================
  describe("ConsumoOptionsDialog", () => {
    const mockGroups = [
      {
        id: "grp-salsas",
        nombre: "Elección de Salsa",
        seleccion_minima: 1,
        seleccion_maxima: 2,
        opciones: [
          {
            id: "opt-1",
            item_id: "prod-salsa-tartara",
            type: "producto" as const,
            nombre: "Salsa Tártara Artesanal",
            precio_adicional: 500,
          },
          {
            id: "opt-2",
            item_id: "prod-salsa-ajo",
            type: "producto" as const,
            nombre: "Salsa Alioli Ajo Suave",
            precio_adicional: 0,
          },
        ],
      },
    ];

    it("validates option limits and submits selected choices", () => {
      const handleConfirm = vi.fn();
      const mockRecipe = MOCK_RECETAS_CONSUMO[0];

      render(
        <ConsumoOptionsDialog
          open={true}
          onOpenChange={vi.fn()}
          item={mockRecipe || null}
          type="receta"
          gruposOpciones={mockGroups}
          onConfirm={handleConfirm}
        />
      );

      expect(screen.getByTestId("consumo-options-dialog")).toBeInTheDocument();
      expect(screen.getByText("Elección de Salsa")).toBeInTheDocument();

      // Botón confirmar deshabilitado al inicio (falta mínimo 1)
      const confirmBtn = screen.getByTestId("options-confirm-btn");
      expect(confirmBtn).toBeDisabled();

      // Agregar opción 1
      fireEvent.click(screen.getByTestId("option-plus-opt-1"));
      expect(screen.getByTestId("option-qty-opt-1")).toHaveTextContent("1");

      // Ahora cumple mínimo (1/2), botón habilitado
      expect(confirmBtn).not.toBeDisabled();

      fireEvent.click(confirmBtn);
      expect(handleConfirm).toHaveBeenCalledWith([
        expect.objectContaining({
          grupo_id: "grp-salsas",
          producto_id: "opt-1",
          cantidad: 1,
          nombre: "Salsa Tártara Artesanal",
          precio_adicional: 500,
        }),
      ]);
    });
  });

  // ==========================================================================
  // 4. ConsumoTemplateModal
  // ==========================================================================
  describe("ConsumoTemplateModal", () => {
    it("configures template name, columns, public toggle and product items", async () => {
      const handleSave = vi.fn();

      render(
        <ConsumoTemplateModal
          open={true}
          onOpenChange={vi.fn()}
          productos={MOCK_PRODUCTOS_CONSUMO}
          categorias={MOCK_CATEGORIAS_CONSUMO}
          onSaveTemplate={handleSave}
        />
      );

      expect(screen.getByTestId("consumo-template-modal")).toBeInTheDocument();

      // Llenar campos
      fireEvent.change(screen.getByTestId("template-name-input"), {
        target: { value: "Turno Mañana" },
      });
      fireEvent.change(screen.getByTestId("template-desc-input"), {
        target: { value: "Insumos críticos" },
      });

      // Toggle visibilidad pública
      fireEvent.click(screen.getByTestId("template-public-toggle"));

      // Seleccionar producto
      const salmonCheck = screen.getByTestId("template-product-checkbox-prod-salm-01");
      fireEvent.click(salmonCheck);

      // Guardar plantilla
      fireEvent.click(screen.getByTestId("template-save-btn"));

      await waitFor(() => {
        expect(handleSave).toHaveBeenCalledWith(
          expect.objectContaining({
            name: "Turno Mañana",
            description: "Insumos críticos",
            isPublic: true,
            productIds: ["prod-salm-01"],
          })
        );
      });
    });
  });

  // ==========================================================================
  // 5. ContingencyModal
  // ==========================================================================
  describe("ContingencyModal", () => {
    it("displays contingency alerts and handles the 3 action paths", () => {
      const handleForce = vi.fn();
      const handleMerma = vi.fn();
      const handleLocate = vi.fn();

      const contingency = {
        isContingency: true,
        reason: "expired_lots",
        hasExpiredLots: true,
        hasInsufficientStock: true,
        expiredProductNames: ["Salmón Fresco Lote Vencido"],
        insufficientStockNames: ["Queso Parmesano"],
      };

      render(
        <ContingencyModal
          open={true}
          onOpenChange={vi.fn()}
          contingencyResult={contingency}
          onForceConsume={handleForce}
          onTriggerMerma={handleMerma}
          onLocateStock={handleLocate}
        />
      );

      expect(screen.getByTestId("contingency-modal")).toBeInTheDocument();
      expect(screen.getByTestId("contingency-expired-section")).toBeInTheDocument();
      expect(screen.getByTestId("contingency-stock-section")).toBeInTheDocument();

      // Camino 1: Localizar
      fireEvent.click(screen.getByTestId("contingency-locate-btn"));
      expect(handleLocate).toHaveBeenCalledTimes(1);

      // Camino 2: Merma
      fireEvent.click(screen.getByTestId("contingency-merma-btn"));
      expect(handleMerma).toHaveBeenCalledTimes(1);

      // Camino 3: Forzar
      fireEvent.click(screen.getByTestId("contingency-force-btn"));
      expect(handleForce).toHaveBeenCalledTimes(1);
    });
  });

  // ==========================================================================
  // 6. LocateStockDialog
  // ==========================================================================
  describe("LocateStockDialog", () => {
    it("displays alternative warehouse stocks and requests transfer", async () => {
      const handleTransfer = vi.fn();

      render(
        <LocateStockDialog
          open={true}
          onOpenChange={vi.fn()}
          missingProducts={["prod-salm-01"]}
          productos={MOCK_PRODUCTOS_CONSUMO}
          currentBodegaId="1"
          onRequestTransfer={handleTransfer}
        />
      );

      expect(screen.getByTestId("locate-stock-dialog")).toBeInTheDocument();
      expect(screen.getByTestId("locate-product-card-prod-salm-01")).toBeInTheDocument();

      const transferBtn = screen.getByTestId(
        "locate-request-transfer-btn-prod-salm-01-bodega-central"
      );
      fireEvent.click(transferBtn);

      expect(handleTransfer).toHaveBeenCalledWith("prod-salm-01", "bodega-central");
    });
  });

  // ==========================================================================
  // 7. ConsumoEditDialog
  // ==========================================================================
  describe("ConsumoEditDialog", () => {
    const mockRecord: ConsumptionRecord = {
      id: "rec-101",
      codigo_folio: "CNS-2026-0001",
      bodega_id: "1",
      nombre_producto: "Salmón Fresco Filete",
      cantidad: 2.5,
      created_at: new Date().toISOString(),
      motivo_merma: "Salida para cocina",
    };

    it("populates record data and updates quantity and notes", async () => {
      const handleSave = vi.fn();

      render(
        <ConsumoEditDialog
          open={true}
          onOpenChange={vi.fn()}
          record={mockRecord}
          onSave={handleSave}
        />
      );

      expect(screen.getByTestId("consumo-edit-dialog")).toBeInTheDocument();
      expect(screen.getByTestId("edit-record-title")).toHaveTextContent("Salmón Fresco Filete");

      fireEvent.change(screen.getByTestId("edit-quantity-input"), {
        target: { value: "3.5" },
      });
      fireEvent.change(screen.getByTestId("edit-motivo-input"), {
        target: { value: "Ajuste de porciones reales" },
      });

      fireEvent.click(screen.getByTestId("edit-save-btn"));

      await waitFor(() => {
        expect(handleSave).toHaveBeenCalledWith("rec-101", {
          cantidad: 3.5,
          motivo_merma: "Ajuste de porciones reales",
          notas: "Ajuste de porciones reales",
        });
      });
    });
  });

  // ==========================================================================
  // 8. ConsumoLog
  // ==========================================================================
  describe("ConsumoLog", () => {
    const mockRecords: ConsumptionRecord[] = [
      {
        id: "log-1",
        codigo_folio: "FOLIO-001",
        bodega_id: "1",
        nombre_producto: "Filete de Salmón",
        cantidad: 4,
        costo_total: 63960,
        usuario_nombre: "Juan Chef",
        created_at: new Date().toISOString(),
      },
    ];

    it("renders record log, filters items, and allows edit and delete actions", () => {
      const handleEdit = vi.fn();
      const handleDelete = vi.fn();

      render(
        <ConsumoLog
          open={true}
          onOpenChange={vi.fn()}
          records={mockRecords}
          onEdit={handleEdit}
          onDelete={handleDelete}
          logDate={new Date()}
          setLogDate={vi.fn()}
        />
      );

      expect(screen.getByTestId("consumo-log-modal")).toBeInTheDocument();
      expect(screen.getByTestId("log-record-item-log-1")).toBeInTheDocument();
      expect(screen.getByText("Filete de Salmón")).toBeInTheDocument();

      fireEvent.click(screen.getByTestId("log-edit-btn-log-1"));
      expect(handleEdit).toHaveBeenCalledWith(mockRecords[0]);

      fireEvent.click(screen.getByTestId("log-delete-btn-log-1"));
      expect(handleDelete).toHaveBeenCalledWith(mockRecords[0]);
    });
  });
});
