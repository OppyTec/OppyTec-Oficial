/**
 * oppytec-frontend/src/features/oppyfy/hooks/useOppyfyGovernance.ts
 * Hook integral de Gobernanza, RBAC Exclusivo, Billeteras de Créditos y Auditoría de OppyFy (v2.0):
 * - Árbol de Dominios y Subdominios jerárquicos con badges de módulos contratados
 * - Permisos Temporales con triple control de caducidad (expires_at, max_prompts, temp_credit_ceiling)
 * - Billeteras de Créditos y Cupos por Trabajador (sin caducidad, acumulables / rollover)
 * - Visor y filtrado de eventos de Bitácora de Auditoría (ALLOWED vs BLOCKED_UNAUTHORIZED_PROMPT)
 */

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getHttpRequestContext } from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import type {
  OppyfyDomainTreeResponse,
  OppyfyDomainCreateRequest,
  OppyfyGrantCreateRequest,
  OppyfyGrantResponse,
  OppyfyTemporaryGrantItem,
  OppyfyWorkerWalletItem,
  OppyfyWalletPatchRequest,
  OppyfyPromptAuditLogItem,
  AiCreditPackResponse,
  AiCreditPackQuoteResponse,
} from "../types";

// ============================================================================
// DATOS SEMILLA / FALLBACK ROBUSTOS PARA DESARROLLO Y TESTING
// ============================================================================

export const DEFAULT_GOVERNANCE_DOMAINS: readonly OppyfyDomainTreeResponse[] = [
  {
    id: 1,
    domain_key: "recipes",
    name_es: "Recetas y Cocina",
    name_en: "Recipes & Kitchen",
    icon: "ChefHat",
    is_active: true,
    sort_order: 1,
    subdomains: [
      {
        id: 101,
        subdomain_key: "recipes_kitchen",
        name_es: "Escandallos y Márgenes",
        name_en: "Recipe Costing & Margins",
        allowed_tool_functions: ["query_recipe_costs", "get_sales_and_food_cost_variance"],
        can_view_costs_default: true,
        is_active: true,
      },
      {
        id: 102,
        subdomain_key: "recipes_allergens",
        name_es: "Fichas Técnicas y Alérgenos",
        name_en: "Technical Sheets & Allergens",
        allowed_tool_functions: ["query_recipe_costs"],
        can_view_costs_default: false,
        is_active: true,
      },
    ],
  },
  {
    id: 2,
    domain_key: "inventory",
    name_es: "Inventario y Bodegas",
    name_en: "Inventory & Warehouses",
    icon: "Boxes",
    is_active: true,
    sort_order: 2,
    subdomains: [
      {
        id: 201,
        subdomain_key: "inventory_stock",
        name_es: "Stock y Rotación FEFO",
        name_en: "Stock & FEFO Rotation",
        allowed_tool_functions: ["get_stock_health_and_reorder_alerts", "get_expiring_batches_fefo"],
        can_view_costs_default: false,
        is_active: true,
      },
      {
        id: 202,
        subdomain_key: "inventory_valuation",
        name_es: "Valorización Kardex PPP",
        name_en: "Kardex Valuation PPP",
        allowed_tool_functions: ["get_stock_health_and_reorder_alerts"],
        can_view_costs_default: true,
        is_active: true,
      },
    ],
  },
  {
    id: 3,
    domain_key: "procurement",
    name_es: "Abastecimiento y Proveedores",
    name_en: "Procurement & Suppliers",
    icon: "Truck",
    is_active: true,
    sort_order: 3,
    subdomains: [
      {
        id: 301,
        subdomain_key: "abastecimiento_y_eventos",
        name_es: "Órdenes de Compra y Eventos",
        name_en: "Purchase Orders & Events",
        allowed_tool_functions: [
          "evaluate_supplier_lead_times_and_price_drift",
          "build_optimal_purchase_order_draft",
          "analyze_event_supply_feasibility",
        ],
        can_view_costs_default: false,
        is_active: true,
      },
    ],
  },
  {
    id: 4,
    domain_key: "finance",
    name_es: "Finanzas y Rentabilidad",
    name_en: "Finance & Profitability",
    icon: "BadgePercent",
    is_active: true,
    sort_order: 4,
    subdomains: [
      {
        id: 401,
        subdomain_key: "finance_ebitda",
        name_es: "EBITDA y Food Cost Holding",
        name_en: "EBITDA & Holding Food Cost",
        allowed_tool_functions: ["get_sales_and_food_cost_variance"],
        can_view_costs_default: true,
        is_active: false,
      },
    ],
  },
];

export const DEFAULT_TEMPORARY_GRANTS: readonly OppyfyTemporaryGrantItem[] = [
  {
    grant_id: "grant-uuid-1",
    user_id: 1,
    user_name: "Juan Pérez (Chef Ejecutivo)",
    subdomain_id: 101,
    subdomain_slug: "recipes_kitchen",
    subdomain_name: "Escandallos y Márgenes",
    can_query: true,
    can_view_costs: true,
    expires_at: "2026-12-31T23:59:59Z",
    max_prompts: 50,
    temp_credit_ceiling: "75.00",
    is_active: true,
  },
  {
    grant_id: "grant-uuid-2",
    user_id: 2,
    user_name: "Ana Silva (Jefa de Bodega)",
    subdomain_id: 201,
    subdomain_slug: "inventory_stock",
    subdomain_name: "Stock y Rotación FEFO",
    can_query: true,
    can_view_costs: false,
    expires_at: "2026-11-15T18:00:00Z",
    max_prompts: 20,
    temp_credit_ceiling: "30.00",
    is_active: true,
  },
];

export const DEFAULT_WORKER_WALLETS: readonly OppyfyWorkerWalletItem[] = [
  {
    user_id: 1,
    full_name: "Juan Pérez",
    email: "juan.perez@pollooking.cl",
    role_name: "Chef Ejecutivo",
    is_oppyfy_enabled: true,
    assigned_credit_ceiling: "100.00",
    consumed_credits_total: "12.50",
    remaining_credits: "87.50",
  },
  {
    user_id: 2,
    full_name: "Ana Silva",
    email: "ana.silva@pollooking.cl",
    role_name: "Jefa de Bodega",
    is_oppyfy_enabled: true,
    assigned_credit_ceiling: "50.00",
    consumed_credits_total: "5.00",
    remaining_credits: "45.00",
  },
  {
    user_id: 3,
    full_name: "Carlos Mendoza",
    email: "carlos.mendoza@pollooking.cl",
    role_name: "Encargado de Compras",
    is_oppyfy_enabled: false,
    assigned_credit_ceiling: "25.00",
    consumed_credits_total: "0.00",
    remaining_credits: "25.00",
  },
  {
    user_id: 4,
    full_name: "Valentina Morales",
    email: "valentina.morales@pollooking.cl",
    role_name: "Auditora Financiera",
    is_oppyfy_enabled: true,
    assigned_credit_ceiling: "150.00",
    consumed_credits_total: "42.00",
    remaining_credits: "108.00",
  },
];

export const DEFAULT_AI_PACKS: readonly AiCreditPackResponse[] = [
  {
    id: 1,
    pack_name: "Pack PyME Gastronómico",
    credits_amount: "250.00",
    bonus_credits: "25.00",
    total_credits: "275.00",
    price_clp: "19990.00",
    price_usd: "22.00",
    is_popular: false,
    is_active: true,
    sort_order: 1,
    plan_tier_discounts: { pro: "10", enterprise: "20" },
  },
  {
    id: 2,
    pack_name: "Pack Enterprise Pollo King",
    credits_amount: "1000.00",
    bonus_credits: "200.00",
    total_credits: "1200.00",
    price_clp: "69990.00",
    price_usd: "75.00",
    is_popular: true,
    is_active: true,
    sort_order: 2,
    plan_tier_discounts: { pro: "15", enterprise: "25" },
  },
  {
    id: 3,
    pack_name: "Pack Booster Emergencia",
    credits_amount: "100.00",
    bonus_credits: "0.00",
    total_credits: "100.00",
    price_clp: "9990.00",
    price_usd: "11.00",
    is_popular: false,
    is_active: true,
    sort_order: 3,
    plan_tier_discounts: {},
  },
];

export const DEFAULT_AUDIT_LOGS: readonly OppyfyPromptAuditLogItem[] = [
  {
    id: 1001,
    created_at: "2026-10-26T18:30:15Z",
    user_id: 1,
    user_name: "Juan Pérez",
    prompt_text: "¿Cuáles lotes están críticos según FEFO en Pollo King?",
    status: "ALLOWED",
    resolved_domain: "inventory_stock",
    resolved_tools: ["get_expiring_batches_fefo"],
    tokens_spent: 420,
    credits_deducted: "1.00",
  },
  {
    id: 1002,
    created_at: "2026-10-26T18:35:22Z",
    user_id: 2,
    user_name: "Ana Silva",
    prompt_text: "¿Cuál es el EBITDA y margen neto de la sucursal este mes?",
    status: "BLOCKED_UNAUTHORIZED_PROMPT",
    resolved_domain: "finance_ebitda",
    resolved_tools: [],
    tokens_spent: 0,
    credits_deducted: "0.00",
  },
  {
    id: 1003,
    created_at: "2026-10-26T18:40:05Z",
    user_id: 1,
    user_name: "Juan Pérez",
    prompt_text: "Calcula la varianza de Food Cost teórico vs real en Pollo King",
    status: "ALLOWED",
    resolved_domain: "recipes_kitchen",
    resolved_tools: ["get_sales_and_food_cost_variance"],
    tokens_spent: 680,
    credits_deducted: "1.50",
  },
  {
    id: 1004,
    created_at: "2026-10-26T18:45:50Z",
    user_id: 3,
    user_name: "Carlos Mendoza",
    prompt_text: "Ver balance consolidado bancario del Holding",
    status: "BLOCKED_UNAUTHORIZED_PROMPT",
    resolved_domain: "finanzas_y_rentabilidad",
    resolved_tools: [],
    tokens_spent: 0,
    credits_deducted: "0.00",
  },
];

export interface UseOppyfyGovernanceOptions {
  readonly tenantId?: string;
}

export function useOppyfyGovernance(options?: UseOppyfyGovernanceOptions) {
  const queryClient = useQueryClient();
  const context = getHttpRequestContext();
  const tenantId = options?.tenantId ?? context.tenantId;

  // Estado local para mutaciones en UI que actualizan de forma inmediata
  const [localDomains, setLocalDomains] = useState<OppyfyDomainTreeResponse[]>([
    ...DEFAULT_GOVERNANCE_DOMAINS,
  ]);
  const [localGrants, setLocalGrants] = useState<OppyfyTemporaryGrantItem[]>([
    ...DEFAULT_TEMPORARY_GRANTS,
  ]);
  const [localWorkers, setLocalWorkers] = useState<OppyfyWorkerWalletItem[]>([
    ...DEFAULT_WORKER_WALLETS,
  ]);
  const [localAuditLogs] = useState<OppyfyPromptAuditLogItem[]>([
    ...DEFAULT_AUDIT_LOGS,
  ]);

  // 1. Árbol de Dominios
  const domainsQuery = useQuery({
    queryKey: queryKeys.oppyfy.rbacDomains(tenantId),
    queryFn: async (): Promise<OppyfyDomainTreeResponse[]> => {
      const resp = await apiRequest<OppyfyDomainTreeResponse[]>(
        "/api/v1/oppyfy/rbac/domains",
        { fallbackData: localDomains }
      );
      return resp.data;
    },
    staleTime: 1000 * 60 * 5,
  });

  const domains = localDomains;

  // 2. Creación de Dominio
  const createDomainMutation = useMutation({
    mutationFn: async (payload: OppyfyDomainCreateRequest): Promise<OppyfyDomainTreeResponse> => {
      const newDomainId = Math.max(0, ...localDomains.map((d) => d.id)) + 1;
      const fallbackCreated: OppyfyDomainTreeResponse = {
        id: newDomainId,
        domain_key: payload.domain_key,
        name_es: payload.name_es,
        name_en: payload.name_en || payload.name_es,
        icon: payload.icon || "Sparkles",
        is_active: payload.is_active ?? true,
        sort_order: payload.sort_order ?? localDomains.length + 1,
        subdomains: (payload.subdomains || []).map((s, idx) => ({
          id: newDomainId * 100 + idx + 1,
          subdomain_key: s.subdomain_key,
          name_es: s.name_es,
          name_en: s.name_en || s.name_es,
          allowed_tool_functions: s.allowed_tool_functions,
          can_view_costs_default: s.can_view_costs_default ?? false,
          is_active: s.is_active ?? true,
        })),
      };

      setLocalDomains((prev) => [...prev, fallbackCreated]);

      await apiRequest<OppyfyDomainTreeResponse>(
        "/api/v1/oppyfy/rbac/domains",
        {
          method: "POST",
          body: payload,
          fallbackData: fallbackCreated,
        }
      );

      return fallbackCreated;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.oppyfy.rbacDomains(tenantId),
      });
    },
  });

  // 3. Toggle de estado de subdominio
  const toggleSubdomainActive = (domainId: number, subdomainId: number) => {
    setLocalDomains((prev) =>
      prev.map((d) => {
        if (d.id !== domainId) return d;
        return {
          ...d,
          subdomains: d.subdomains.map((sub) =>
            sub.id === subdomainId ? { ...sub, is_active: !sub.is_active } : sub
          ),
        };
      })
    );
  };

  const toggleSubdomainCanViewCosts = (domainId: number, subdomainId: number) => {
    setLocalDomains((prev) =>
      prev.map((d) => {
        if (d.id !== domainId) return d;
        return {
          ...d,
          subdomains: d.subdomains.map((sub) =>
            sub.id === subdomainId
              ? { ...sub, can_view_costs_default: !sub.can_view_costs_default }
              : sub
          ),
        };
      })
    );
  };

  // 4. Permisos Temporales
  const createGrantMutation = useMutation({
    mutationFn: async (payload: OppyfyGrantCreateRequest): Promise<OppyfyGrantResponse> => {
      // Validaciones de triple caducidad
      if (payload.max_prompts !== undefined && payload.max_prompts !== null && payload.max_prompts <= 0) {
        throw new Error("El límite de consultas (max_prompts) debe ser mayor a 0.");
      }
      if (payload.temp_credit_ceiling !== undefined && payload.temp_credit_ceiling !== null) {
        const ceilingNum = Number(payload.temp_credit_ceiling);
        if (isNaN(ceilingNum) || ceilingNum < 0) {
          throw new Error("El tope de créditos temporales debe ser un número no negativo.");
        }
      }
      if (payload.expires_at) {
        const expDate = new Date(payload.expires_at);
        if (isNaN(expDate.getTime())) {
          throw new Error("La fecha de expiración proporcionada no es válida.");
        }
      }

      const generatedGrantId = `grant-uuid-${Date.now()}`;
      const fallbackGrant: OppyfyGrantResponse = {
        grant_id: generatedGrantId,
        user_id: payload.user_id,
        subdomain_id: payload.subdomain_id,
        subdomain_slug: payload.subdomain_slug,
        can_query: payload.can_query ?? true,
        can_view_costs: payload.can_view_costs ?? false,
        expires_at: payload.expires_at ?? null,
        max_prompts: payload.max_prompts ?? null,
        temp_credit_ceiling: payload.temp_credit_ceiling ?? null,
        is_active: true,
      };

      const resp = await apiRequest<OppyfyGrantResponse>("/api/v1/oppyfy/rbac/grants", {
        method: "POST",
        body: payload,
        fallbackData: fallbackGrant,
      });

      // Enriquecer y registrar en la lista local de permisos
      const workerMatch = localWorkers.find((w) => w.user_id === payload.user_id);
      let subName = payload.subdomain_slug;
      for (const d of domains) {
        const found = d.subdomains.find((s) => s.id === payload.subdomain_id || s.subdomain_key === payload.subdomain_slug);
        if (found) {
          subName = found.name_es;
          break;
        }
      }

      const newGrantItem: OppyfyTemporaryGrantItem = {
        grant_id: resp.data.grant_id,
        user_id: resp.data.user_id,
        user_name: workerMatch ? `${workerMatch.full_name} (${workerMatch.role_name})` : `Usuario #${resp.data.user_id}`,
        subdomain_id: resp.data.subdomain_id,
        subdomain_slug: resp.data.subdomain_slug,
        subdomain_name: subName,
        can_query: resp.data.can_query,
        can_view_costs: resp.data.can_view_costs,
        expires_at: resp.data.expires_at ?? null,
        max_prompts: resp.data.max_prompts ?? null,
        temp_credit_ceiling: resp.data.temp_credit_ceiling ?? null,
        is_active: resp.data.is_active,
      };

      setLocalGrants((prev) => [newGrantItem, ...prev]);
      return resp.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.oppyfy.rbacGrants(tenantId),
      });
    },
  });

  const revokeGrant = (grantId: string) => {
    setLocalGrants((prev) =>
      prev.map((g) => (g.grant_id === grantId ? { ...g, is_active: false } : g))
    );
  };

  // 5. Billeteras de Trabajadores
  const updateWorkerWallet = async (userId: number, patch: OppyfyWalletPatchRequest) => {
    setLocalWorkers((prev) =>
      prev.map((w) => {
        if (w.user_id !== userId) return w;
        const newCeilingNum =
          patch.assigned_credit_ceiling !== undefined && patch.assigned_credit_ceiling !== null
            ? Number(patch.assigned_credit_ceiling)
            : Number(w.assigned_credit_ceiling);
        const newCeiling = isNaN(newCeilingNum) ? String(w.assigned_credit_ceiling) : newCeilingNum.toFixed(2);
        const newEnabled =
          patch.is_oppyfy_enabled !== undefined && patch.is_oppyfy_enabled !== null
            ? patch.is_oppyfy_enabled
            : w.is_oppyfy_enabled;
        const remaining = Math.max(0, Number(newCeiling) - Number(w.consumed_credits_total));
        return {
          ...w,
          assigned_credit_ceiling: newCeiling,
          is_oppyfy_enabled: newEnabled,
          remaining_credits: remaining.toFixed(2),
        };
      })
    );

    await apiRequest(`/api/v1/oppyfy/wallets/${String(userId)}`, {
      method: "PATCH",
      body: patch,
      fallbackData: { user_id: userId, ...patch },
    });
  };

  // 6. Bolsa Global de Créditos del Tenant
  const tenantCreditBag = useMemo(() => {
    const totalAllocated = localWorkers.reduce(
      (sum, w) => sum + Number(w.assigned_credit_ceiling),
      0
    );
    const totalConsumed = localWorkers.reduce(
      (sum, w) => sum + Number(w.consumed_credits_total),
      0
    );
    const totalPurchased = 1000.0; // Bolsa adquirida sin caducidad
    const remainingPool = Math.max(0, totalPurchased - totalAllocated);

    return {
      total_purchased_credits: totalPurchased,
      total_allocated_credits: totalAllocated,
      total_consumed_credits: totalConsumed,
      remaining_pool_credits: remainingPool,
    };
  }, [localWorkers]);

  // 7. Catálogo de paquetes Add-On
  const aiPacksQuery = useQuery({
    queryKey: queryKeys.oppyfy.aiPacks(true),
    queryFn: async (): Promise<AiCreditPackResponse[]> => {
      const fallbackPacks: AiCreditPackResponse[] = [
        {
          id: 1,
          pack_name: "Pack PyME Gastronómico",
          credits_amount: "250.00",
          bonus_credits: "25.00",
          total_credits: "275.00",
          price_clp: "19990.00",
          price_usd: "22.00",
          is_popular: false,
          is_active: true,
          sort_order: 1,
          plan_tier_discounts: { pro: "10", enterprise: "20" },
        },
        {
          id: 2,
          pack_name: "Pack Enterprise Pollo King",
          credits_amount: "1000.00",
          bonus_credits: "200.00",
          total_credits: "1200.00",
          price_clp: "69990.00",
          price_usd: "75.00",
          is_popular: true,
          is_active: true,
          sort_order: 2,
          plan_tier_discounts: { pro: "15", enterprise: "25" },
        },
        {
          id: 3,
          pack_name: "Pack Booster Emergencia",
          credits_amount: "100.00",
          bonus_credits: "0.00",
          total_credits: "100.00",
          price_clp: "9990.00",
          price_usd: "11.00",
          is_popular: false,
          is_active: true,
          sort_order: 3,
          plan_tier_discounts: {},
        },
      ];
      const resp = await apiRequest<AiCreditPackResponse[]>(
        "/api/v1/platform-admin/ai-packs?is_active_only=true",
        { fallbackData: fallbackPacks }
      );
      return resp.data;
    },
    staleTime: 1000 * 60 * 10,
  });

  const quotePack = async (packId: number, basePlanTier?: string): Promise<AiCreditPackQuoteResponse> => {
    const selected = (aiPacksQuery.data ?? []).find((p) => p.id === packId);
    const originalClp = selected ? Number(selected.price_clp) : 19990;
    const originalUsd = selected ? Number(selected.price_usd) : 22;
    const discount = basePlanTier === "enterprise" ? 25 : basePlanTier === "pro" ? 15 : 0;
    const finalClp = originalClp * (1 - discount / 100);
    const finalUsd = originalUsd * (1 - discount / 100);

    const fallbackQuote: AiCreditPackQuoteResponse = {
      pack_id: packId,
      pack_name: selected?.pack_name ?? "Pack Add-On",
      base_plan_tier: basePlanTier ?? "estandar",
      original_price_usd: originalUsd.toFixed(2),
      original_price_clp: originalClp.toFixed(0),
      discount_pct: String(discount),
      final_price_usd: finalUsd.toFixed(2),
      final_price_clp: finalClp.toFixed(0),
      total_credits: selected?.total_credits ?? "250.00",
    };

    const resp = await apiRequest<AiCreditPackQuoteResponse>(
      `/api/v1/platform-admin/ai-packs/${String(packId)}/quote`,
      { fallbackData: fallbackQuote }
    );
    return resp.data;
  };

  return {
    // Dominios
    domains,
    isLoadingDomains: domainsQuery.isLoading,
    createDomain: createDomainMutation.mutateAsync,
    isCreatingDomain: createDomainMutation.isPending,
    toggleSubdomainActive,
    toggleSubdomainCanViewCosts,

    // Permisos Temporales
    grants: localGrants,
    createGrant: createGrantMutation.mutateAsync,
    isCreatingGrant: createGrantMutation.isPending,
    revokeGrant,

    // Billeteras de Trabajadores & Tenant Bag
    workers: localWorkers,
    tenantCreditBag,
    updateWorkerWallet,

    // Paquetes Add-On
    aiPacks: aiPacksQuery.data ?? DEFAULT_AI_PACKS,
    quotePack,

    // Bitácora de Auditoría
    auditLogs: localAuditLogs,
  };
}
