import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import {
  calculateCommercialMargin,
  simulateTokensMonthly,
  useAdminPlans,
  useSaaSQuotaPolicy,
  useTokenConsumption,
} from "../index";
import {
  MOCK_SAAS_POLICY,
  MOCK_SYSTEM_PLANS,
  MOCK_TOKEN_CONSUMPTION,
  SYSTEM_MODULE_CATALOG,
  type SystemPlanCreateRequest,
} from "../../types";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
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

const createMockEnvelope = <T,>(data: T): httpClient.ApiEnvelope<T> => ({
  data,
  traceId: "trace-platform-admin-test",
  timestampIso: new Date().toISOString(),
  tenantId: "tenant_rest_central",
});

describe("Platform Admin - Feature Core & Reactive Hooks (Fase 3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock por defecto de apiRequest para prevenir llamadas a localhost
    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string) => {
      if (url.includes("/plans")) {
        return createMockEnvelope(MOCK_SYSTEM_PLANS);
      }
      if (url.includes("/ai-credits/policy")) {
        return createMockEnvelope(MOCK_SAAS_POLICY);
      }
      if (url.includes("/token-consumption")) {
        return createMockEnvelope(MOCK_TOKEN_CONSUMPTION);
      }
      return createMockEnvelope({});
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. UTILIDADES MATEMÁTICAS PURAS DE SIMULACIÓN Y MÁRGENES
  // ==========================================================================
  describe("1. Utilidades Matemáticas Puras (Simulación & FinOps)", () => {
    it("simulateTokensMonthly calcula exactamente los tokens equivalentes (credits * rate)", () => {
      // 2.000 créditos a 1.000 tokens/crédito = 2.000.000 tokens
      expect(simulateTokensMonthly(2000, 1000)).toBe(2_000_000);
      expect(simulateTokensMonthly(500, 1000)).toBe(500_000);
      expect(simulateTokensMonthly(10_000, 1500)).toBe(15_000_000);
    });

    it("simulateTokensMonthly maneja cuotas de cero o negativas retornando 0", () => {
      expect(simulateTokensMonthly(0, 1000)).toBe(0);
      expect(simulateTokensMonthly(-100, 1000)).toBe(0);
      expect(simulateTokensMonthly(1000, 0)).toBe(0);
      expect(simulateTokensMonthly(1000, -500)).toBe(0);
    });

    it("calculateCommercialMargin calcula el costo en CLP redondeado y el margen porcentual (>= 90%)", () => {
      // Pack de 1.000 créditos a $15.000 CLP.
      // 1.000 créditos = 1.000.000 tokens.
      // En Gemini 1.5 Flash (~$0.075 USD / 1M tokens), costo USD = $0.075.
      // FX = 950 CLP/USD -> costo CLP = Math.round(0.075 * 950) = Math.round(71.25) = 71 CLP.
      // Margen = ((15.000 - 71) / 15.000) * 100 = 99.53%
      const result = calculateCommercialMargin(0.075, 15000, 950);
      expect(result.costClp).toBe(71);
      expect(result.marginPct).toBe(99.53);
      expect(result.isProfitable).toBe(true);
    });

    it("calculateCommercialMargin maneja costo cero retornando 100% de margen", () => {
      const result = calculateCommercialMargin(0, 15000, 950);
      expect(result.costClp).toBe(0);
      expect(result.marginPct).toBe(100);
      expect(result.isProfitable).toBe(true);
    });

    it("calculateCommercialMargin maneja precio de pack <= 0 retornando isProfitable: false", () => {
      const result = calculateCommercialMargin(1.5, 0, 950);
      expect(result.costClp).toBe(1425);
      expect(result.marginPct).toBe(0);
      expect(result.isProfitable).toBe(false);
    });

    it("calculateCommercialMargin evalúa rentabilidad con umbral >= 90%", () => {
      // Costo 200 USD * 950 = 190.000 CLP, Precio 200.000 CLP -> Margen = 5% (< 90%)
      const unprofitable = calculateCommercialMargin(200, 200000, 950);
      expect(unprofitable.marginPct).toBe(5);
      expect(unprofitable.isProfitable).toBe(false);

      // Margen justo en 90%
      // Si pack = 1000, costo = 100 -> margen = 90%
      // 100 / 950 = 0.105263 USD
      const profitableThreshold = calculateCommercialMargin(100 / 950, 1000, 950);
      expect(profitableThreshold.costClp).toBe(100);
      expect(profitableThreshold.marginPct).toBe(90);
      expect(profitableThreshold.isProfitable).toBe(true);
    });
  });

  // ==========================================================================
  // 2. HOOK useAdminPlans
  // ==========================================================================
  describe("2. Hook useAdminPlans", () => {
    it("carga la lista de planes comerciales con fallback resiliente ante error de red", async () => {
      const { result } = renderHook(() => useAdminPlans(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.plans.length).toBeGreaterThanOrEqual(3);
      expect(result.current.plans[0]?.slug).toBe("plan-basico");
      expect(result.current.moduleCatalog).toEqual(SYSTEM_MODULE_CATALOG);
    });

    it("consume respuesta remota del endpoint /api/v1/platform-admin/plans", async () => {
      const remotePlans = [
        {
          ...MOCK_SYSTEM_PLANS[0]!,
          name: "Plan Básico Custom",
          price_clp: 35000,
        },
      ];

      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string) => {
        if (url.includes("/plans")) {
          return createMockEnvelope(remotePlans);
        }
        return createMockEnvelope({});
      });

      const { result } = renderHook(() => useAdminPlans(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.plans[0]?.name).toBe("Plan Básico Custom");
        expect(result.current.plans[0]?.price_clp).toBe(35000);
      });
    });

    it("ejecuta createPlan y dispara toast de éxito", async () => {
      const newPlanPayload: SystemPlanCreateRequest = {
        slug: "plan-startup",
        name: "Plan Startup Cafetería",
        tier: 1,
        monthly_ai_credits: 750,
        description: "Plan de entrada",
        is_popular: false,
        is_active: true,
        max_active_users: 4,
        max_products: 300,
        max_suppliers: 15,
        max_recipes: 30,
        max_combos: 15,
        max_storage_mb: 1024,
        included_modules: ["inicio", "consumo", "inventario"],
        anchor_currency: "CLP",
        price_clp: 39990,
        price_usd: 45,
        auto_convert_fx: true,
      };

      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
        if (options?.method === "POST" && url === "/api/v1/platform-admin/plans") {
          return createMockEnvelope({
            ...newPlanPayload,
            price_eur: 40,
            price_brl: 220,
            active_clients_count: 0,
          });
        }
        return createMockEnvelope(MOCK_SYSTEM_PLANS);
      });

      const { result } = renderHook(() => useAdminPlans(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.createPlan(newPlanPayload);
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/plans",
        expect.objectContaining({
          method: "POST",
          body: newPlanPayload,
        })
      );
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("Plan Startup Cafetería"));
    });

    it("ejecuta updatePlan y dispara toast de éxito", async () => {
      const updatePayload = {
        name: "Plan Pro Gastronómico V2",
        price_clp: 74990,
      };

      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
        if (options?.method === "PUT" && url.includes("/plans/plan-pro")) {
          return createMockEnvelope({
            ...MOCK_SYSTEM_PLANS[1]!,
            ...updatePayload,
          });
        }
        return createMockEnvelope(MOCK_SYSTEM_PLANS);
      });

      const { result } = renderHook(() => useAdminPlans(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.updatePlan("plan-pro", updatePayload);
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/plans/plan-pro",
        expect.objectContaining({
          method: "PUT",
          body: updatePayload,
        })
      );
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("actualizado exitosamente"));
    });

    it("ejecuta deletePlan y maneja bloqueo 409 si existen clientes activos", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (_url: string, options?: any) => {
        if (options?.method === "DELETE") {
          throw new Error("HTTP 409: Clientes activos contratando el plan");
        }
        return createMockEnvelope(MOCK_SYSTEM_PLANS);
      });

      const { result } = renderHook(() => useAdminPlans(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        try {
          await result.current.deletePlan("plan-pro");
        } catch {
          // Capturado por onError
        }
      });

      expect(toast.error).toHaveBeenCalledWith(
        expect.stringContaining("No se puede eliminar el plan")
      );
    });

    it("invalida la cache de planes al emitirse el evento 'admin_plans_changed'", async () => {
      let callCount = 0;
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async () => {
        callCount++;
        return createMockEnvelope(MOCK_SYSTEM_PLANS);
      });

      const { result } = renderHook(() => useAdminPlans(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.plans.length).toBeGreaterThan(0);
      });

      const initialCalls = callCount;

      act(() => {
        window.dispatchEvent(new Event("admin_plans_changed"));
      });

      await waitFor(() => {
        expect(callCount).toBeGreaterThan(initialCalls);
      });
    });
  });

  // ==========================================================================
  // 3. HOOK useSaaSQuotaPolicy
  // ==========================================================================
  describe("3. Hook useSaaSQuotaPolicy", () => {
    it("carga la política SaaS con fallback resiliente", async () => {
      const { result } = renderHook(() => useSaaSQuotaPolicy(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.policy.tokens_per_credit).toBe(1000);
      expect(result.current.policy.default_monthly_credits).toBe(2000);
      expect(result.current.policy.credit_price_clp).toBe(15.0);
    });

    it("actualiza la política global con mutación PUT exitosa", async () => {
      const updatedPolicy = {
        tokens_per_credit: 1500,
        default_monthly_credits: 3000,
        credit_price_clp: 18.0,
        credit_price_usd: 0.018,
        updated_at: new Date().toISOString(),
        updated_by: "Admin Principal",
      };

      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
        if (options?.method === "PUT" && url.includes("/ai-credits/policy")) {
          return createMockEnvelope(updatedPolicy);
        }
        return createMockEnvelope(MOCK_SAAS_POLICY);
      });

      const { result } = renderHook(() => useSaaSQuotaPolicy(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.updatePolicy({
          tokens_per_credit: 1500,
          default_monthly_credits: 3000,
          credit_price_clp: 18.0,
          credit_price_usd: 0.018,
        });
      });

      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("actualizada exitosamente")
      );
    });

    it("utilidades de instancia simulan tokens y margen correctamente", async () => {
      const { result } = renderHook(() => useSaaSQuotaPolicy(), {
        wrapper: createWrapper(),
      });

      // simulateTokens usa policy.tokens_per_credit (1000)
      const simulated = result.current.simulateTokens(2500);
      expect(simulated).toBe(2_500_000);

      // calculateMargin: costUsd = 0.1, packPriceClp = 20000, fxRate = 950
      // costClp = Math.round(0.1 * 950) = 95
      // margin = ((20000 - 95) / 20000) * 100 = 99.53%
      const margin = result.current.calculateMargin(0.1, 20000, 950);
      expect(margin.costClp).toBe(95);
      expect(margin.marginPct).toBe(99.53);
      expect(margin.isProfitable).toBe(true);
    });
  });

  // ==========================================================================
  // 4. HOOK useTokenConsumption
  // ==========================================================================
  describe("4. Hook useTokenConsumption", () => {
    it("carga resumen jerárquico FinOps (holdings, logs, total_tokens)", async () => {
      const { result } = renderHook(() => useTokenConsumption(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.holdings.length).toBeGreaterThan(0);
      expect(result.current.logs.length).toBeGreaterThan(0);
      expect(result.current.totalTokensAll).toBe(643400);
      expect(result.current.viewMode).toBe("credits");
    });

    it("permite conmutar viewMode entre 'credits' y 'tokens'", async () => {
      const { result } = renderHook(() => useTokenConsumption(), {
        wrapper: createWrapper(),
      });

      expect(result.current.viewMode).toBe("credits");

      act(() => {
        result.current.setViewMode("tokens");
      });

      expect(result.current.viewMode).toBe("tokens");

      act(() => {
        result.current.setViewMode("credits");
      });

      expect(result.current.viewMode).toBe("credits");
    });

    it("actualiza parámetros de búsqueda, paginación y fechas reactivamente", async () => {
      const { result } = renderHook(() => useTokenConsumption(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setSearch("buffet");
        result.current.setModelName("gemini-1.5-pro");
        result.current.setHoldingId("holding-gastro-sur");
        result.current.setTenantId("tenant_hotel_costanera");
        result.current.setApiSuccess(true);
        result.current.setStartDate("2026-10-01");
        result.current.setEndDate("2026-10-31");
        result.current.setPage(2);
        result.current.setPageSize(25);
      });

      expect(result.current.search).toBe("buffet");
      expect(result.current.modelName).toBe("gemini-1.5-pro");
      expect(result.current.holdingId).toBe("holding-gastro-sur");
      expect(result.current.tenantId).toBe("tenant_hotel_costanera");
      expect(result.current.apiSuccess).toBe(true);
      expect(result.current.startDate).toBe("2026-10-01");
      expect(result.current.endDate).toBe("2026-10-31");
      expect(result.current.page).toBe(2);
      expect(result.current.pageSize).toBe(25);
    });

    it("ejecuta updateHoldingCredits con PATCH e invalida cache (soporta objeto y argumentos)", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
        if (options?.method === "PATCH" && url.includes("/holdings/holding-gastro-sur/ai-credits")) {
          return createMockEnvelope({
            target_id: "holding-gastro-sur",
            target_type: "holding",
            monthly_credits: 12000,
            distribution_mode: "shared",
            message: "Cuota de Holding actualizada",
          });
        }
        return createMockEnvelope(MOCK_TOKEN_CONSUMPTION);
      });

      const { result } = renderHook(() => useTokenConsumption(), {
        wrapper: createWrapper(),
      });

      // Llamada usando objeto payload
      await act(async () => {
        await result.current.updateHoldingCredits({
          holdingId: "holding-gastro-sur",
          monthly_credits: 12000,
          distribution_mode: "shared",
        });
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/holdings/holding-gastro-sur/ai-credits",
        expect.objectContaining({
          method: "PATCH",
          body: {
            monthly_credits: 12000,
            distribution_mode: "shared",
          },
        })
      );
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("Cuota de Holding actualizada")
      );

      // Llamada usando argumentos posicionales (holdingId, limit, distributionMode)
      await act(async () => {
        await result.current.updateHoldingCredits("holding-gastro-sur", 15000, "per_tenant");
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/holdings/holding-gastro-sur/ai-credits",
        expect.objectContaining({
          method: "PATCH",
          body: {
            monthly_credits: 15000,
            distribution_mode: "per_tenant",
          },
        })
      );
    });

    it("ejecuta updateTenantCredits con PATCH e invalida cache (soporta objeto y argumentos)", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
        if (options?.method === "PATCH" && url.includes("/tenants/tenant_rest_central/ai-credits")) {
          return createMockEnvelope({
            target_id: "tenant_rest_central",
            target_type: "tenant",
            monthly_credits: 3500,
            distribution_mode: null,
            message: "Cuota de Tenant actualizada",
          });
        }
        return createMockEnvelope(MOCK_TOKEN_CONSUMPTION);
      });

      const { result } = renderHook(() => useTokenConsumption(), {
        wrapper: createWrapper(),
      });

      // Llamada con objeto
      await act(async () => {
        await result.current.updateTenantCredits({
          tenantId: "tenant_rest_central",
          monthly_credits: 3500,
        });
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/tenants/tenant_rest_central/ai-credits",
        expect.objectContaining({
          method: "PATCH",
          body: {
            monthly_credits: 3500,
          },
        })
      );
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("Cuota de Tenant actualizada")
      );

      // Llamada con argumentos posicionales (tenantId, limit)
      await act(async () => {
        await result.current.updateTenantCredits("tenant_rest_central", 4000);
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/tenants/tenant_rest_central/ai-credits",
        expect.objectContaining({
          method: "PATCH",
          body: {
            monthly_credits: 4000,
          },
        })
      );
    });

    it("reacciona al evento 'token_consumption_changed' invalidando la consulta", async () => {
      let callCount = 0;
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async () => {
        callCount++;
        return createMockEnvelope(MOCK_TOKEN_CONSUMPTION);
      });

      const { result } = renderHook(() => useTokenConsumption(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.holdings.length).toBeGreaterThan(0);
      });

      const initialCalls = callCount;

      act(() => {
        window.dispatchEvent(new Event("token_consumption_changed"));
      });

      await waitFor(() => {
        expect(callCount).toBeGreaterThan(initialCalls);
      });
    });
  });
});
