/**
 * oppytec-frontend/src/features/invoices/__tests__/useInvoices.test.tsx
 * Pruebas unitarias para los hooks reactivos del Módulo de Facturas:
 * useInvoices, useInvoiceDetail y useInvoiceWebhooks.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { useInvoices, useInvoiceDetail, useInvoiceWebhooks } from "../useInvoices";
import { MOCK_INVOICES, MOCK_INVOICE_STATS, MOCK_PRICE_DRIFT_ITEMS } from "../mockData";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useInvoices Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("carga la lista de facturas, estadísticas y datos de price drift", async () => {
    const { result } = renderHook(() => useInvoices(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoadingInvoices).toBe(false);
    });

    expect(result.current.invoices.length).toBeGreaterThan(0);
    expect(result.current.invoices[0]?.invoice_number).toBe(MOCK_INVOICES[0]?.invoice_number);

    await waitFor(() => {
      expect(result.current.isLoadingStats).toBe(false);
    });
    expect(result.current.stats?.total_invoices).toBe(MOCK_INVOICE_STATS.total_invoices);

    await waitFor(() => {
      expect(result.current.isLoadingPriceDrift).toBe(false);
    });
    expect(result.current.priceDriftItems.length).toBe(MOCK_PRICE_DRIFT_ITEMS.length);
  });

  it("permite actualizar filtros y restablecerlos", async () => {
    const { result } = renderHook(() => useInvoices(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.setFilter("status", "READY_FOR_REVIEW");
    });
    expect(result.current.filters.status).toBe("READY_FOR_REVIEW");

    act(() => {
      result.current.resetFilters();
    });
    expect(result.current.filters.status).toBe("ALL");
    expect(result.current.searchInput).toBe("");
  });
});

describe("useInvoiceDetail Hook", () => {
  it("carga el detalle de una factura y permite editar y descartar borrador", async () => {
    const testId = MOCK_INVOICES[0]?.id || "inv-2026-001";
    const { result } = renderHook(() => useInvoiceDetail(testId), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.invoice?.id).toBe(testId);
    expect(result.current.editableItems.length).toBeGreaterThan(0);
    expect(result.current.hasUnsavedChanges).toBe(false);

    // Modificar un ítem
    act(() => {
      const updated = [...result.current.editableItems];
      if (updated[0]) {
        updated[0] = { ...updated[0], total_stock_fisico: 50 };
      }
      result.current.setEditableItems(updated);
    });

    expect(result.current.hasUnsavedChanges).toBe(true);
    expect(result.current.editableItems[0]?.total_stock_fisico).toBe(50);

    // Descartar borrador
    act(() => {
      result.current.discardDraft();
    });

    expect(result.current.hasUnsavedChanges).toBe(false);
  });

  it("confirma el ingreso de stock físico a bodega", async () => {
    const testId = MOCK_INVOICES[0]?.id || "inv-2026-001";
    const { result } = renderHook(() => useInvoiceDetail(testId), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.confirmStockIngest({
        bodega_id: "bod-central",
        items: [
          {
            item_id: "item-001-1",
            product_action: "use_existing",
            product_id: "prod-lom-001",
            product_name: "Lomo Vetado Angus Premium",
            categoria_id: "cat-carnes",
            bodega_id: "bod-camara-fria",
            factor_empaque: 18,
            kitchen_base_unit: "kg",
            total_stock_fisico: 36,
            costo_unitario_inventario: 14200,
            remember_alias: true,
          },
        ],
      });
    });

    expect(result.current.hasUnsavedChanges).toBe(false);
  });
});

describe("useInvoiceWebhooks Hook", () => {
  it("lista webhooks registrados y permite ping de prueba", async () => {
    const { result } = renderHook(() => useInvoiceWebhooks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.webhooks.length).toBeGreaterThan(0);

    let pingResult: any = null;
    await act(async () => {
      pingResult = await result.current.pingWebhook(result.current.webhooks[0]?.id || "hook-1");
    });

    expect(pingResult?.success).toBe(true);
    expect(pingResult?.status_code).toBe(200);
  });
});
