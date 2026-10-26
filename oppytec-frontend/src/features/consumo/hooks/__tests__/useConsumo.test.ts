// oppytec-frontend/src/features/consumo/hooks/__tests__/useConsumo.test.ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as httpClient from "@/shared/api/httpClient";
import { useConsumo } from "../useConsumo";
import {
  MOCK_PRODUCTOS_CONSUMO,
  MOCK_RECETAS_CONSUMO,
} from "../../mockData";

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

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

async function renderConsumoHook(options?: Parameters<typeof useConsumo>[0]) {
  const rendered = renderHook(() => useConsumo(options), {
    wrapper: createWrapper(),
  });
  await waitFor(() => {
    expect(rendered.result.current.loading).toBe(false);
  });
  return rendered;
}

describe("Módulo de Consumo - useConsumo Hook Reactivo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    localStorage.clear();
    await new Promise((r) => setTimeout(r, 20));
  });

  // ==========================================================================
  // 1. Carrito Persistente y Sincronización Multiventana
  // ==========================================================================
  describe("Carrito Persistente y Sincronización Multiventana", () => {
    it("starts with empty cart when localStorage is clean", async () => {
      const { result } = await renderConsumoHook();
      expect(result.current.cart).toEqual([]);
    });

    it("adds an item to the cart and persists to localStorage and dispatches cart-updated event", async () => {
      const dispatchSpy = vi.spyOn(window, "dispatchEvent");
      const { result } = await renderConsumoHook();

      const prod = MOCK_PRODUCTOS_CONSUMO[0]!;

      act(() => {
        result.current.addToCart(prod, "producto", "1");
      });

      expect(result.current.cart.length).toBe(1);
      expect(result.current.cart[0]?.id).toBe(prod.id);
      expect(result.current.cart[0]?.quantity).toBe(1);

      // Verificación en localStorage
      const stored = JSON.parse(localStorage.getItem("consumo_cart") || "[]");
      expect(stored.length).toBe(1);
      expect(stored[0].id).toBe(prod.id);

      // Evento nativo disparado
      expect(dispatchSpy).toHaveBeenCalledWith(expect.any(Event));
    });

    it("increments quantity when the same item and bodega are added again", async () => {
      const { result } = await renderConsumoHook();
      const prod = MOCK_PRODUCTOS_CONSUMO[0]!;

      act(() => {
        result.current.addToCart(prod, "producto", "1");
        result.current.addToCart(prod, "producto", "1");
      });

      expect(result.current.cart.length).toBe(1);
      expect(result.current.cart[0]?.quantity).toBe(2);
    });

    it("updates quantity directly and removes item when requested", async () => {
      const { result } = await renderConsumoHook();
      const prod = MOCK_PRODUCTOS_CONSUMO[0]!;

      act(() => {
        result.current.addToCart(prod, "producto", "1");
      });

      const cartItemId = result.current.cart[0]!.cartItemId;

      act(() => {
        result.current.updateQuantity(cartItemId, 5);
      });
      expect(result.current.cart[0]?.quantity).toBe(5);

      act(() => {
        result.current.removeFromCart(cartItemId);
      });
      expect(result.current.cart.length).toBe(0);
    });

    it("updates item lot selection and ingredient lot overrides", async () => {
      const { result } = await renderConsumoHook();
      const receta = MOCK_RECETAS_CONSUMO[0]!;

      act(() => {
        result.current.addToCart(receta, "receta", "1");
      });

      const cartItemId = result.current.cart[0]!.cartItemId;

      act(() => {
        result.current.updateCartItemLot(cartItemId, "LOT-CUSTOM-01");
        result.current.updateIngredientLotOverride(
          cartItemId,
          "prod-salm-01",
          "2026-12-31",
          "LOT-ING-99"
        );
      });

      expect(result.current.cart[0]?.selectedLot).toBe("LOT-CUSTOM-01");
      expect(result.current.cart[0]?.ingredientLotOverrides?.length).toBe(1);
      expect(
        result.current.cart[0]?.ingredientLotOverrides?.[0]?.producto_id
      ).toBe("prod-salm-01");
    });

    it("clears cart completely", async () => {
      const { result } = await renderConsumoHook();
      const prod = MOCK_PRODUCTOS_CONSUMO[0]!;

      act(() => {
        result.current.addToCart(prod, "producto", "1");
      });
      expect(result.current.cart.length).toBe(1);

      act(() => {
        result.current.clearCart();
      });

      expect(result.current.cart.length).toBe(0);
      expect(localStorage.getItem("consumo_cart")).toBe("[]");
    });
  });

  // ==========================================================================
  // 2. Grilla y Configuración de Columnas (5 a 10)
  // ==========================================================================
  describe("Configuración de Columnas", () => {
    it("defaults to 8 columns and clamps values between 5 and 10", async () => {
      const { result } = await renderConsumoHook();

      expect(result.current.colsCount).toBe(8);

      act(() => {
        result.current.setColsCount(12); // excede max
      });
      expect(result.current.colsCount).toBe(10);

      act(() => {
        result.current.setColsCount(2); // menor que min
      });
      expect(result.current.colsCount).toBe(5);

      act(() => {
        result.current.setColsCount(7);
      });
      expect(result.current.colsCount).toBe(7);
      expect(localStorage.getItem("consumo_cols_count")).toBe("7");
    });
  });

  // ==========================================================================
  // 3. Funciones Matemáticas, Disponibilidad y Stock No Vencido
  // ==========================================================================
  describe("Cálculos Matemáticos de Stock y Disponibilidad", () => {
    it("computes getStock correctly", async () => {
      const { result } = await renderConsumoHook();

      // Salmón tiene 14.5 kg disponibles en MOCK_PRODUCTOS_CONSUMO
      expect(result.current.getStock("prod-salm-01")).toBe(14.5);
      // Producto inexistente devuelve 0
      expect(result.current.getStock("non-existent")).toBe(0);
    });

    it("computes getNonExpiredStock filtering out expired batches", async () => {
      const { result } = await renderConsumoHook();

      // Leche Entera tiene stock_disponible: 32, pero lote LOT-LEC-VENC (2026-01-01) tiene 4 vencidos
      // Por tanto, el stock no vencido debe ser 32 - 4 = 28
      const nonExpired = result.current.getNonExpiredStock("prod-leche-ent");
      expect(nonExpired).toBe(28);
    });

    it("evaluates alert status (critical when stock <= 0, warning when soon or <= min)", async () => {
      const { result } = await renderConsumoHook();

      // prod-harina-000 tiene stock 0 -> critical
      expect(result.current.getAlertStatus("prod-harina-000")).toBe("critical");

      // prod-leche-ent tiene un lote vencido en el pasado -> critical
      expect(result.current.getAlertStatus("prod-leche-ent")).toBe("critical");

      // prod-salm-01 tiene 14.5 (min 5, alerta 7 dias, vence en noviembre) -> normal
      expect(result.current.getAlertStatus("prod-salm-01")).toBe("normal");
    });

    it("calculates recipe availability based on ingredient ratios", async () => {
      const { result } = await renderConsumoHook();

      // rec-salmon-parmesano requiere:
      // - prod-salm-01: 0.25 kg por porción. Stock: 14.5 kg -> 14.5 / 0.25 = 58 porciones
      // - prod-queso-parm: 0.05 kg por porción. Stock: 8.0 kg -> 8.0 / 0.05 = 160 porciones
      // El cuello de botella es el salmón (58 porciones)
      const availability = result.current.getRecipeAvailability("rec-salmon-parmesano");
      expect(availability).toBe(58);
    });
  });

  // ==========================================================================
  // 4. Verificación de Contingencias (Lotes Vencidos y Quiebre de Stock)
  // ==========================================================================
  describe("Verificación de Contingencias (checkContingency)", () => {
    it("detects out_of_stock contingency when total stock is 0", async () => {
      const { result } = await renderConsumoHook();
      const harina = MOCK_PRODUCTOS_CONSUMO.find((p) => p.id === "prod-harina-000")!;

      const contingency = result.current.checkContingency(harina, 1);
      expect(contingency.isContingency).toBe(true);
      expect(contingency.reason).toBe("out_of_stock");
      expect(contingency.totalStock).toBe(0);
    });

    it("detects expired_lots contingency when requested quantity exceeds non-expired stock", async () => {
      const { result } = await renderConsumoHook();
      const leche = MOCK_PRODUCTOS_CONSUMO.find((p) => p.id === "prod-leche-ent")!;

      // Leche tiene 28 no vencidos y 4 vencidos.
      // Si solicitamos 30 unidades (> 28 no vencidos), dispara contingencia
      const contingency = result.current.checkContingency(leche, 30);
      expect(contingency.isContingency).toBe(true);
      expect(contingency.reason).toBe("expired_lots");
      expect(contingency.expiredLots?.length).toBeGreaterThan(0);
      expect(contingency.nonExpiredStock).toBe(28);
    });

    it("returns isContingency: false when fresh stock is plenty", async () => {
      const { result } = await renderConsumoHook();
      const salmon = MOCK_PRODUCTOS_CONSUMO.find((p) => p.id === "prod-salm-01")!;

      const contingency = result.current.checkContingency(salmon, 2);
      expect(contingency.isContingency).toBe(false);
      expect(contingency.nonExpiredStock).toBe(14.5);
    });
  });

  // ==========================================================================
  // 5. Mutaciones Transaccionales
  // ==========================================================================
  describe("Mutaciones Transaccionales", () => {
    it("calls registerConsumption API and clears cart on success", async () => {
      const apiSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockImplementation(async (path, options) => {
          if (
            path.includes("/operations/consumption") &&
            options?.method === "POST"
          ) {
            return {
              data: {
                id: "rec-new-999",
                codigo_folio: "FOL-NEW",
                costo_total: 1000,
              } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          return {
            data: options?.fallbackData,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          } as any;
        });

      const { result } = await renderConsumoHook();

      act(() => {
        result.current.addToCart(MOCK_PRODUCTOS_CONSUMO[0]!, "producto", "1");
      });
      expect(result.current.cart.length).toBe(1);

      await act(async () => {
        await result.current.registerConsumption({
          bodega_id: 1,
          items: [
            {
              tipo_item: "producto",
              item_id: "prod-salm-01",
              cantidad: 1,
            },
          ],
        });
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/consumption",
        expect.objectContaining({ method: "POST" })
      );
      // Carrito limpiado automáticamente
      expect(result.current.cart.length).toBe(0);
    });

    it("calls mermaExpiredStock API successfully", async () => {
      const apiSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockImplementation(async (path, options) => {
          if (
            path.includes("/operations/consumption/merma-expired") &&
            options?.method === "POST"
          ) {
            return {
              data: { kardex_entry_id: 888, quantity: 4 } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          return {
            data: options?.fallbackData,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          } as any;
        });

      const { result } = await renderConsumoHook();

      await act(async () => {
        await result.current.mermaExpiredStock({
          producto_id: "prod-leche-ent",
          bodega_id: 1,
          quantity: 4,
          motivo: "VENCIMIENTO",
        });
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/consumption/merma-expired",
        expect.objectContaining({ method: "POST" })
      );
    });

    it("calls updateConsumption and deleteConsumption", async () => {
      const apiSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockImplementation(async (path, options) => {
          if (
            path.includes("/operations/consumption/rec-1001") &&
            options?.method === "PUT"
          ) {
            return {
              data: { id: "rec-1001", notas: "Notas actualizadas" } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          if (
            path.includes("/operations/consumption/rec-1001") &&
            options?.method === "DELETE"
          ) {
            return {
              data: { id: "rec-1001", is_undone: true } as any,
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "tenant_rest_central",
            };
          }
          return {
            data: options?.fallbackData,
            traceId: "test-trace",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          } as any;
        });

      const { result } = await renderConsumoHook();

      await act(async () => {
        await result.current.updateConsumption({
          id: "rec-1001",
          notas: "Notas actualizadas",
        });
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/consumption/rec-1001",
        expect.objectContaining({ method: "PUT" })
      );

      await act(async () => {
        await result.current.deleteConsumption({
          id: "rec-1001",
          reason: "Error de ingreso",
        });
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/operations/consumption/rec-1001?reason=Error%20de%20ingreso",
        expect.objectContaining({ method: "DELETE" })
      );
    });
  });
});
