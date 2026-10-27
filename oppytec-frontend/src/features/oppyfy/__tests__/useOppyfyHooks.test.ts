/**
 * oppytec-frontend/src/features/oppyfy/__tests__/useOppyfyHooks.test.ts
 * Pruebas unitarias para los hooks reactivos de OppyFy (v2.0):
 * 1. Flujo de envío de chat y actualización reactiva del porcentaje de contexto.
 * 2. Bloqueo anti-alucinación cuando el contexto supera 85% (semáforo rojo).
 * 3. Rollover asistido a nuevo hilo fresco que restablece el contexto al 5.00%.
 * 4. Gestión de billetera de créditos, asignación de cupos y cotizador de paquetes Add-On.
 * 5. Árbol de dominios RBAC propio, creación de dominios y concesiones con triple caducidad.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import {
  useOppyfyChat,
  useOppyfyCredits,
  useOppyfyRbac,
  calculateContextHealth,
  type ChatMessage,
  type OppyfyChatResponse,
  type OppyfyThreadRolloverResponse,
  type OppyfyDomainTreeResponse,
  type OppyfyGrantResponse,
  type OppyfyWalletResponse,
  type AiCreditPackResponse,
  type AiCreditPackQuoteResponse,
} from "../index";

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

const createMockEnvelope = <T>(data: T): httpClient.ApiEnvelope<T> => ({
  data,
  traceId: "trace-oppyfy-test-1234",
  timestampIso: new Date().toISOString(),
  tenantId: "tenant_rest_central",
});

describe("OppyFy v2.0 - Core TypeScript & Reactive Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.clear();
    }
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("calculateContextHealth - Medidor Semafórico de Salud de Contexto", () => {
    it("clasifica <65% como 'green' (óptimo, sin bloqueo)", () => {
      const state0 = calculateContextHealth(0);
      expect(state0.status).toBe("green");
      expect(state0.requiresCompaction).toBe(false);
      expect(state0.isAntiHallucinationBlocked).toBe(false);

      const state64 = calculateContextHealth(64.99);
      expect(state64.status).toBe("green");
      expect(state64.requiresCompaction).toBe(false);
      expect(state64.isAntiHallucinationBlocked).toBe(false);
    });

    it("clasifica 66% a 85% como 'amber' (preventivo, sin bloqueo)", () => {
      const state65 = calculateContextHealth(65);
      expect(state65.status).toBe("amber");
      expect(state65.requiresCompaction).toBe(false);
      expect(state65.isAntiHallucinationBlocked).toBe(false);

      const state85 = calculateContextHealth(85);
      expect(state85.status).toBe("amber");
      expect(state85.requiresCompaction).toBe(false);
      expect(state85.isAntiHallucinationBlocked).toBe(false);
    });

    it("clasifica >85% como 'red' (bloqueo anti-alucinación y requiere compactación)", () => {
      const state851 = calculateContextHealth(85.01);
      expect(state851.status).toBe("red");
      expect(state851.requiresCompaction).toBe(true);
      expect(state851.isAntiHallucinationBlocked).toBe(true);

      const state95 = calculateContextHealth(95);
      expect(state95.status).toBe("red");
      expect(state95.requiresCompaction).toBe(true);
      expect(state95.isAntiHallucinationBlocked).toBe(true);
    });
  });

  describe("useOppyfyChat - Envío de Chat y Actualización de Contexto", () => {
    it("envía un mensaje a POST /api/v1/oppyfy/chat, actualiza créditos y porcentaje de contexto", async () => {
      const mockChatResponse: OppyfyChatResponse = {
        allowed: true,
        status_code: "ALLOWED",
        subdomain_slug: "recipes_kitchen",
        answer_text: "El Food Cost de Pollo King esta semana es de 29.4%, dentro del rango meta.",
        credits_deducted: "1.50",
        remaining_credits: "98.50",
        context_usage_percent: "35.20",
        requires_new_thread: false,
        tool_executed: "get_sales_and_food_cost_variance",
        tool_payload: {
          title: "Varianza Food Cost Pollo King",
          data: [{ item: "Pollo King", theoretical: 28.0, actual: 29.4 }],
        },
      };

      const spyApi = vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope(mockChatResponse)
      );

      const { result } = renderHook(() =>
        useOppyfyChat({
          initialRemainingCredits: 100,
          initialContextPct: 10,
        })
      );

      expect(result.current.contextHealth.pct).toBe(10);
      expect(result.current.contextHealth.status).toBe("green");
      expect(result.current.remainingCredits).toBe(100);

      let msgResult: ChatMessage | null = null;
      await act(async () => {
        const sent = await result.current.sendMessage(
          "¿Cuál es el Food Cost de Pollo King?"
        );
        msgResult = sent;
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/oppyfy/chat",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            prompt_text: "¿Cuál es el Food Cost de Pollo King?",
            target_subdomain_slug: "recipes_kitchen",
          }),
        })
      );

      expect(msgResult).not.toBeNull();
      // Verificación de actualización reactiva
      expect(result.current.remainingCredits).toBe(98.5);
      expect(result.current.contextHealth.pct).toBe(35.2);
      expect(result.current.contextHealth.status).toBe("green");
      expect(result.current.messages).toHaveLength(2); // user + assistant
      expect(result.current.messages[1]?.content).toContain("Pollo King");
      expect(result.current.messages[1]?.canvasPayload?.type).toBe("table");
      expect(result.current.activeCanvasArtifact?.title).toBe("Varianza Food Cost Pollo King");
    });

    it("bloquea el envío con semáforo rojo cuando el contexto supera el 85% (Anti-Hallucination Guard)", async () => {
      const spyApi = vi.spyOn(httpClient, "apiRequest");

      const { result } = renderHook(() =>
        useOppyfyChat({
          initialRemainingCredits: 50,
          initialContextPct: 88.5, // >85% Rojo
        })
      );

      expect(result.current.contextHealth.status).toBe("red");
      expect(result.current.contextHealth.isAntiHallucinationBlocked).toBe(true);

      let blockedMsg: ChatMessage | null = null;
      await act(async () => {
        const sent = await result.current.sendMessage(
          "Pregunta posterior a saturación de ventana"
        );
        blockedMsg = sent;
      });

      // NO debe haber llamado al backend para evitar Context Rot y consumo inútil
      expect(spyApi).not.toHaveBeenCalled();
      expect(result.current.error).toContain("Bloqueo anti-alucinación activo");
      const castBlocked = blockedMsg as ChatMessage | null;
      expect(castBlocked?.isBlocked).toBe(true);
      expect(castBlocked?.status).toBe("blocked");
      expect(result.current.messages).toHaveLength(1);
    });

    it("ejecuta rolloverToFreshThread restableciendo el contexto al 5.00% con resumen estructurado", async () => {
      const mockRolloverResponse: OppyfyThreadRolloverResponse = {
        new_thread_id: "thread-uuid-fresh-999",
        previous_thread_id: "thread-uuid-old-111",
        fresh_context_usage_percent: "5.00",
        summary_artifact: "Síntesis compacta: Análisis de inventario FEFO y Food Cost verificado de Pollo King.",
        message: "Hilo traspasado exitosamente al 5.00% de contexto.",
      };

      const spyApi = vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope(mockRolloverResponse)
      );

      const { result } = renderHook(() =>
        useOppyfyChat({
          initialThreadId: "thread-uuid-old-111",
          initialContextPct: 89.0, // saturado
        })
      );

      expect(result.current.contextHealth.status).toBe("red");

      let freshThreadId = "";
      await act(async () => {
        freshThreadId = await result.current.rolloverToFreshThread(
          "Continuación de auditoría semanal"
        );
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/oppyfy/threads/thread-uuid-old-111/rollover",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            summary_notes: "Continuación de auditoría semanal",
          }),
        })
      );

      expect(freshThreadId).toBe("thread-uuid-fresh-999");
      expect(result.current.currentThreadId).toBe("thread-uuid-fresh-999");
      // Verificación estricta del 5.00% y semáforo verde
      expect(result.current.contextHealth.pct).toBe(5);
      expect(result.current.contextHealth.status).toBe("green");
      expect(result.current.contextHealth.isAntiHallucinationBlocked).toBe(false);
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0]?.content).toContain("Síntesis compacta");
    });
  });

  describe("useOppyfyCredits - Billetera, Cupos y Cotizador Add-On", () => {
    it("carga la billetera de créditos sin caducidad y permite ajustar cupos de trabajadores", async () => {
      const mockWalletResponse: OppyfyWalletResponse = {
        user_id: 42,
        is_oppyfy_enabled: true,
        assigned_credits_balance: "250.00",
        consumed_credits_total: "45.00",
        remaining_credits: "205.00",
      };

      const mockPatchedWallet: OppyfyWalletResponse = {
        ...mockWalletResponse,
        assigned_credits_balance: "500.00",
        remaining_credits: "455.00",
      };

      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(
        async (url: string, opts) => {
          if (url === "/api/v1/oppyfy/wallets/me") {
            return createMockEnvelope(mockWalletResponse);
          }
          if (url === "/api/v1/oppyfy/wallets/42" && opts?.method === "PATCH") {
            return createMockEnvelope(mockPatchedWallet);
          }
          throw new Error(`Unhandled route ${url}`);
        }
      );

      const { result } = renderHook(() => useOppyfyCredits(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoadingWallet).toBe(false);
      });

      expect(result.current.remainingCredits).toBe(205);
      expect(result.current.allocatedCredits).toBe(250);
      expect(result.current.consumedCredits).toBe(45);
      expect(result.current.isOppyfyEnabled).toBe(true);

      // Mutación de cupo
      await act(async () => {
        await result.current.updateWorkerWallet({
          userId: 42,
          patch: { assigned_credit_ceiling: 500 },
        });
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/oppyfy/wallets/42",
        expect.objectContaining({
          method: "PATCH",
          body: { assigned_credit_ceiling: 500 },
        })
      );
    });

    it("consulta el catálogo de paquetes Add-On y cotiza con descuento de plan SaaS", async () => {
      const mockPacksResponse: AiCreditPackResponse[] = [
        {
          id: 1,
          pack_name: "Pack Inicial 5.000",
          credits_amount: "5000.00",
          bonus_credits: "500.00",
          total_credits: "5500.00",
          price_clp: "15000.00",
          price_usd: "16.00",
          is_popular: false,
          is_active: true,
          sort_order: 1,
          plan_tier_discounts: { ENTERPRISE: "15.00", PRO: "5.00" },
        },
      ];

      const mockQuoteResponse: AiCreditPackQuoteResponse = {
        pack_id: 1,
        pack_name: "Pack Inicial 5.000",
        base_plan_tier: "ENTERPRISE",
        original_price_usd: "16.00",
        original_price_clp: "15000.00",
        discount_pct: "15.00",
        final_price_usd: "13.60",
        final_price_clp: "12750.00",
        total_credits: "5500.00",
      };

      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(
        async (url: string) => {
          if (url.startsWith("/api/v1/platform-admin/ai-packs/1/quote")) {
            return createMockEnvelope(mockQuoteResponse);
          }
          if (url.startsWith("/api/v1/platform-admin/ai-packs")) {
            return createMockEnvelope(mockPacksResponse);
          }
          if (url === "/api/v1/oppyfy/wallets/me") {
            return createMockEnvelope({
              user_id: 1,
              is_oppyfy_enabled: true,
              assigned_credits_balance: "100.00",
              consumed_credits_total: "0.00",
              remaining_credits: "100.00",
            });
          }
          throw new Error(`Unhandled route ${url}`);
        }
      );

      const { result } = renderHook(() => useOppyfyCredits(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoadingPacks).toBe(false);
      });

      expect(result.current.aiPacks).toHaveLength(1);
      expect(result.current.aiPacks[0]?.pack_name).toBe("Pack Inicial 5.000");

      // Cotización con plan Enterprise
      let quote: AiCreditPackQuoteResponse | null = null;
      await act(async () => {
        const q = await result.current.quotePack(1, "ENTERPRISE");
        quote = q;
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/platform-admin/ai-packs/1/quote?base_plan_tier=ENTERPRISE"
      );
      const castQuote = quote as AiCreditPackQuoteResponse | null;
      expect(castQuote?.discount_pct).toBe("15.00");
      expect(castQuote?.final_price_usd).toBe("13.60");
      expect(castQuote?.total_credits).toBe("5500.00");
    });
  });

  describe("useOppyfyRbac - Árbol Jerárquico y Permisos Temporales", () => {
    it("obtiene el árbol de dominios/subdominios y crea un nuevo dominio", async () => {
      const mockDomainTree: OppyfyDomainTreeResponse[] = [
        {
          id: 1,
          domain_key: "gastronomia",
          name_es: "Gastronomía y Cocina",
          name_en: "Kitchen",
          icon: "ChefHat",
          is_active: true,
          sort_order: 1,
          subdomains: [
            {
              id: 1,
              subdomain_key: "recipes_kitchen",
              name_es: "Recetas y Cocina",
              name_en: "Recipes",
              allowed_tool_functions: ["query_recipe_costs"],
              can_view_costs_default: true,
              is_active: true,
            },
          ],
        },
      ];

      const createdDomain: OppyfyDomainTreeResponse = {
        id: 2,
        domain_key: "seguridad",
        name_es: "Seguridad y Auditoría",
        name_en: "Security",
        icon: "Shield",
        is_active: true,
        sort_order: 2,
        subdomains: [],
      };

      const spyApi = vi.spyOn(httpClient, "apiRequest").mockImplementation(
        async (url: string, opts) => {
          if (url === "/api/v1/oppyfy/rbac/domains") {
            if (opts?.method === "POST") {
              return createMockEnvelope(createdDomain);
            }
            return createMockEnvelope(mockDomainTree);
          }
          throw new Error(`Unhandled route ${url}`);
        }
      );

      const { result } = renderHook(() => useOppyfyRbac(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoadingDomains).toBe(false);
      });

      expect(result.current.domains).toHaveLength(1);
      expect(result.current.domains[0]?.domain_key).toBe("gastronomia");

      await act(async () => {
        await result.current.createDomain({
          domain_key: "seguridad",
          name_es: "Seguridad y Auditoría",
          icon: "Shield",
        });
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/oppyfy/rbac/domains",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({ domain_key: "seguridad" }),
        })
      );
    });

    it("valida triple caducidad al otorgar permisos temporales (expires_at, max_prompts, temp_credit_ceiling)", async () => {
      const mockGrantResponse: OppyfyGrantResponse = {
        grant_id: "grant-uuid-999",
        user_id: 10,
        subdomain_id: 1,
        subdomain_slug: "recipes_kitchen",
        can_query: true,
        can_view_costs: true,
        expires_at: "2026-12-31T23:59:59Z",
        max_prompts: 50,
        temp_credit_ceiling: "25.00",
        is_active: true,
      };

      const spyApi = vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope(mockGrantResponse)
      );

      const { result } = renderHook(() => useOppyfyRbac(), {
        wrapper: createWrapper(),
      });

      // 1. Error con max_prompts inválido
      await expect(
        result.current.createGrant({
          user_id: 10,
          subdomain_id: 1,
          subdomain_slug: "recipes_kitchen",
          max_prompts: 0,
        })
      ).rejects.toThrow("El límite de consultas (max_prompts) debe ser mayor a 0.");

      // 2. Error con créditos negativos
      await expect(
        result.current.createGrant({
          user_id: 10,
          subdomain_id: 1,
          subdomain_slug: "recipes_kitchen",
          temp_credit_ceiling: -10,
        })
      ).rejects.toThrow("El tope de créditos temporales debe ser un número no negativo.");

      // 3. Éxito con parámetros válidos
      let grant: OppyfyGrantResponse | null = null;
      await act(async () => {
        const g = await result.current.createGrant({
          user_id: 10,
          subdomain_id: 1,
          subdomain_slug: "recipes_kitchen",
          can_view_costs: true,
          expires_at: "2026-12-31T23:59:59Z",
          max_prompts: 50,
          temp_credit_ceiling: "25.00",
        });
        grant = g;
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/oppyfy/rbac/grants",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            user_id: 10,
            can_view_costs: true,
            max_prompts: 50,
          }),
        })
      );
      const castGrant = grant as OppyfyGrantResponse | null;
      expect(castGrant?.grant_id).toBe("grant-uuid-999");
    });
  });
});
