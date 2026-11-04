/**
 * oppytec-frontend/src/features/invoices/__tests__/FacturaReviewGrid.test.tsx
 * Pruebas unitarias para la grilla interactiva de 13 columnas:
 * Desacoplamiento de empaque mayorista, cálculo de stock físico y costos de inventario.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FacturaReviewGrid } from "../components/FacturaReviewGrid";
import { MOCK_INVOICES, MOCK_CATEGORIES, MOCK_WAREHOUSES, MOCK_CATALOG_PRODUCTS } from "../mockData";
import type { InvoiceLineItem } from "../types";

describe("FacturaReviewGrid Component", () => {
  it("renderiza correctamente las 13 columnas y los datos de empaque mayorista", () => {
    const items = MOCK_INVOICES[0]?.items || [];
    const handleChange = vi.fn();

    render(
      <FacturaReviewGrid
        items={items}
        onChangeItems={handleChange}
        categories={MOCK_CATEGORIES}
        warehouses={MOCK_WAREHOUSES}
        catalogProducts={MOCK_CATALOG_PRODUCTS}
      />
    );

    expect(screen.getByTestId("factura-review-grid")).toBeInTheDocument();
    expect(screen.getByText("1. Ítem Factura / Empaque")).toBeInTheDocument();
    expect(screen.getByText("LOMO VETADO ANGUS VACÍO CAJA 18KG")).toBeInTheDocument();
    expect(screen.getByText("Alias Exacto")).toBeInTheDocument();
  });

  it("calcula reactivamente el stock físico al cambiar el factor de empaque o cantidad", () => {
    const item: InvoiceLineItem = {
      id: "item-test-1",
      line_number: 1,
      raw_description: "ACEITE DE OLIVA CAJA 4 BIDONES 5L",
      quantity: 2,
      unit_name: "Caja",
      unit_price_net: 60000,
      tax_rate: 0.19,
      total_net: 120000,
      packaging_description: "Caja de 4 bidones de 5L (20L total)",
      factor_empaque: 20,
      kitchen_base_unit: "L",
      total_stock_fisico: 40,
      costo_unitario_inventario: 3000,
      match_status: "exact_alias",
      matched_product_id: "prod-ace-003",
      matched_product_name: "Aceite de Oliva Extra Virgen 5L",
      matched_product_sku: "ABA-ACE-003",
      suggested_categoria_id: "cat-abarrotes",
      product_action: "use_existing",
      nombre_negocio: "Aceite de Oliva Extra Virgen 5L",
      categoria_id: "cat-abarrotes",
      bodega_id: "bod-central",
      remember_alias: true,
      ultimo_costo_referencia: 3000,
      variacion_pct: 0,
      drift_status: "normal",
    };

    let updatedItems: InvoiceLineItem[] = [item];
    const handleChange = vi.fn((newItems: InvoiceLineItem[]) => {
      updatedItems = newItems;
    });

    render(
      <FacturaReviewGrid
        items={updatedItems}
        onChangeItems={handleChange}
        categories={MOCK_CATEGORIES}
        warehouses={MOCK_WAREHOUSES}
        catalogProducts={MOCK_CATALOG_PRODUCTS}
      />
    );

    // Ajuste directo de balanza física: cambiamos stock real a 38L (mermas de transporte)
    const stockInput = screen.getByTitle("Stock físico real a ingresar a inventario (modificable para ajuste de balanza)");
    fireEvent.change(stockInput, { target: { value: "38" } });

    expect(handleChange).toHaveBeenCalled();
    const lastCall = handleChange.mock.calls[handleChange.mock.calls.length - 1];
    expect(lastCall).toBeDefined();
    const firstItem = lastCall?.[0]?.[0];
    expect(firstItem?.total_stock_fisico).toBe(38);
    // Factor recalculado: 38 / 2 = 19
    expect(firstItem?.factor_empaque).toBe(19);
    // Costo unitario inventario recalculado: 120000 / 38 = 3157.89
    expect(firstItem?.costo_unitario_inventario).toBe(3157.89);
  });

  it("permite alternar el checkbox de recordar alias para aprendizaje futuro", () => {
    const item: InvoiceLineItem = { ...MOCK_INVOICES[0]!.items[0]!, remember_alias: true };
    const handleChange = vi.fn();

    render(
      <FacturaReviewGrid
        items={[item]}
        onChangeItems={handleChange}
        categories={MOCK_CATEGORIES}
        warehouses={MOCK_WAREHOUSES}
        catalogProducts={MOCK_CATALOG_PRODUCTS}
      />
    );

    const checkbox = screen.getByTitle("Memorizar alias de proveedor para próximas compras");
    expect(checkbox).toBeChecked();

    fireEvent.click(checkbox);
    expect(handleChange).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          remember_alias: false,
        }),
      ])
    );
  });
});
