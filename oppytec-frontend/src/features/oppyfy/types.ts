/**
 * oppytec-frontend/src/features/oppyfy/types.ts
 * Contratos TypeScript exhaustivos para OppyFy (v2.0):
 * - Paridad 1:1 con esquemas Pydantic del backend FastAPI
 * - Tipos para mensajes de chat y estado conversacional
 * - Medidor semafórico de salud de contexto (<65% verde, 66-85% ámbar, >85% rojo)
 * - Artefactos tipados para el Split-View Canvas (tablas, gráficos, action cards)
 */

// ============================================================================
// 1. CONSTANTES DEL SEMÁFORO Y SALUD DE CONTEXTO
// ============================================================================

export const CONTEXT_HEALTH_OPTIMUM_THRESHOLD = 65;
export const CONTEXT_HEALTH_WARNING_THRESHOLD = 85;
export const FRESH_THREAD_CONTEXT_PCT = 5;

export type ContextTrafficStatus = "green" | "amber" | "red";

export interface ContextHealthState {
  readonly pct: number;
  readonly status: ContextTrafficStatus;
  readonly requiresCompaction: boolean;
  readonly isAntiHallucinationBlocked: boolean;
}

/**
 * Calcula deterministamente el estado del medidor semafórico de contexto:
 * - <65%: 'green' (óptimo)
 * - 66-85%: 'amber' (preventivo)
 * - >85%: 'red' (bloqueo anti-alucinación / Context Rot)
 */
export function calculateContextHealth(rawPct: number): ContextHealthState {
  const pct = Math.max(0, Math.min(100, Math.round(rawPct * 100) / 100));
  if (pct < CONTEXT_HEALTH_OPTIMUM_THRESHOLD) {
    return {
      pct,
      status: "green",
      requiresCompaction: false,
      isAntiHallucinationBlocked: false,
    };
  }
  if (pct <= CONTEXT_HEALTH_WARNING_THRESHOLD) {
    return {
      pct,
      status: "amber",
      requiresCompaction: false,
      isAntiHallucinationBlocked: false,
    };
  }
  return {
    pct,
    status: "red",
    requiresCompaction: true,
    isAntiHallucinationBlocked: true,
  };
}

// ============================================================================
// 2. ARTEFACTOS DEL SPLIT-VIEW CANVAS
// ============================================================================

export type CanvasArtifactType = "table" | "chart" | "action_card";

export interface CanvasTableColumn {
  readonly key: string;
  readonly label: string;
  readonly type?: "string" | "number" | "currency" | "date" | "badge";
}

export interface CanvasArtifact {
  readonly type: CanvasArtifactType;
  readonly title: string;
  readonly data: unknown;
  readonly columns?: (string | CanvasTableColumn)[];
  readonly summary?: string;
  readonly chartType?: "bar" | "line" | "pie";
  readonly actionId?: string;
}

// ============================================================================
// 3. MENSAJES Y CONVERSACIÓN DE CHAT
// ============================================================================

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  readonly id: string;
  readonly role: ChatRole;
  readonly content: string;
  readonly citations?: string[];
  readonly canvasPayload?: CanvasArtifact | null;
  readonly contextUsagePct?: number;
  readonly creditsSpent?: number;
  readonly timestamp: string;
  readonly isBlocked?: boolean;
  readonly status?: "pending" | "success" | "error" | "blocked";
  readonly threadId?: string;
  readonly subdomainSlug?: string;
  readonly toolExecuted?: string | null;
}

// ============================================================================
// 4. PARIDAD 1:1 CON ESQUEMAS PYDANTIC DEL BACKEND
// ============================================================================

export interface OppyfyChatRequest {
  prompt_text: string;
  target_subdomain_slug?: string;
  can_view_costs?: boolean;
  prior_thread_tokens?: number;
  remaining_credits?: string | number;
  estimated_credit_cost?: string | number;
  thread_id?: string | null;
}

export interface OppyfyChatResponse {
  allowed: boolean;
  status_code: string;
  subdomain_slug: string;
  answer_text: string;
  credits_deducted: string | number;
  remaining_credits: string | number;
  context_usage_percent: string | number;
  requires_new_thread: boolean;
  tool_executed?: string | null;
  tool_payload?: Record<string, unknown> | null;
}

export interface OppyfyThreadRolloverRequest {
  summary_notes?: string | null;
  prior_thread_tokens?: number;
}

export interface OppyfyThreadRolloverResponse {
  new_thread_id: string;
  previous_thread_id: string;
  fresh_context_usage_percent: string | number;
  summary_artifact: string;
  message: string;
}

export interface OppyfySubdomainItemSchema {
  subdomain_key: string;
  name_es: string;
  name_en?: string;
  allowed_tool_functions: string[];
  can_view_costs_default?: boolean;
  is_active?: boolean;
}

export interface OppyfyDomainCreateRequest {
  domain_key: string;
  name_es: string;
  name_en?: string;
  icon?: string;
  is_active?: boolean;
  sort_order?: number;
  subdomains?: OppyfySubdomainItemSchema[];
}

export interface OppyfySubdomainDetailResponse {
  id: number;
  subdomain_key: string;
  name_es: string;
  name_en: string;
  allowed_tool_functions: string[];
  can_view_costs_default: boolean;
  is_active: boolean;
}

export interface OppyfyDomainTreeResponse {
  id: number;
  domain_key: string;
  name_es: string;
  name_en: string;
  icon: string;
  is_active: boolean;
  sort_order: number;
  subdomains: OppyfySubdomainDetailResponse[];
}

export interface OppyfyDomainItemResponse {
  domain_slug: string;
  subdomain_slug: string;
  display_name: string;
  supports_cost_redaction: boolean;
}

export interface OppyfyGrantCreateRequest {
  user_id: number;
  subdomain_id: number;
  subdomain_slug: string;
  can_query?: boolean;
  can_view_costs?: boolean;
  expires_at?: string | null;
  max_prompts?: number | null;
  temp_credit_ceiling?: string | number | null;
}

/** Alias retrocompatible para el request de otorgamiento de permisos RBAC */
export type OppyfyPermissionGrantCreateRequest = OppyfyGrantCreateRequest;

export interface OppyfyGrantResponse {
  grant_id: string;
  user_id: number;
  subdomain_id: number;
  subdomain_slug: string;
  can_query: boolean;
  can_view_costs: boolean;
  expires_at?: string | null;
  max_prompts?: number | null;
  temp_credit_ceiling?: string | number | null;
  is_active: boolean;
}

export interface OppyfyWalletPatchRequest {
  assigned_credit_ceiling?: string | number | null;
  is_oppyfy_enabled?: boolean | null;
}

export interface OppyfyWalletResponse {
  user_id: number;
  is_oppyfy_enabled: boolean;
  assigned_credits_balance: string | number;
  consumed_credits_total: string | number;
  remaining_credits: string | number;
}

export interface AiCreditPackCreateRequest {
  pack_name: string;
  credits_amount: string | number;
  price_clp: string | number;
  price_usd: string | number;
  bonus_credits?: string | number;
  is_popular?: boolean;
  is_active?: boolean;
  sort_order?: number;
  plan_tier_discounts?: Record<string, string | number>;
}

export interface AiCreditPackResponse {
  id: number;
  pack_name: string;
  credits_amount: string | number;
  bonus_credits: string | number;
  total_credits: string | number;
  price_clp: string | number;
  price_usd: string | number;
  is_popular: boolean;
  is_active: boolean;
  sort_order: number;
  plan_tier_discounts: Record<string, string | number>;
}

/** Alias retrocompatible para ítems de catálogo de paquetes Add-On */
export type AiCreditPackItem = AiCreditPackResponse;

export interface AiCreditPackQuoteResponse {
  pack_id: number;
  pack_name: string;
  base_plan_tier: string;
  original_price_usd: string | number;
  original_price_clp: string | number;
  discount_pct: string | number;
  final_price_usd: string | number;
  final_price_clp: string | number;
  total_credits: string | number;
}

export interface OppyfyTelemetryLogItemResponse {
  request_id: string;
  caller_feature: string;
  model_name: string;
  total_tokens: number;
  estimated_cost_usd: string | number;
  credits_deducted: string | number;
}

// ============================================================================
// 5. GOBERNANZA, PERMISOS TEMPORALES, AUDITORÍA Y BILLETERAS DE TRABAJADORES
// ============================================================================

export type OppyfyGovernanceTab = "domains" | "grants" | "wallets" | "audit";

export interface OppyfyPromptAuditLogItem {
  readonly id: number;
  readonly created_at: string;
  readonly user_id: number;
  readonly user_name?: string;
  readonly prompt_text: string;
  readonly status: "ALLOWED" | "BLOCKED_UNAUTHORIZED_PROMPT" | string;
  readonly resolved_domain: string | null;
  readonly resolved_tools: string[];
  readonly tokens_spent: number;
  readonly credits_deducted: string | number;
}

export interface OppyfyWorkerWalletItem {
  readonly user_id: number;
  readonly full_name: string;
  readonly email: string;
  readonly role_name: string;
  readonly is_oppyfy_enabled: boolean;
  readonly assigned_credit_ceiling: string | number;
  readonly consumed_credits_total: string | number;
  readonly remaining_credits: string | number;
}

export interface OppyfyTenantCreditBagSummary {
  readonly total_purchased_credits: number;
  readonly total_allocated_credits: number;
  readonly total_consumed_credits: number;
  readonly remaining_pool_credits: number;
}

export interface OppyfyTemporaryGrantItem {
  readonly grant_id: string;
  readonly user_id: number;
  readonly user_name?: string;
  readonly subdomain_id: number;
  readonly subdomain_slug: string;
  readonly subdomain_name?: string;
  readonly can_query: boolean;
  readonly can_view_costs: boolean;
  readonly expires_at: string | null;
  readonly max_prompts: number | null;
  readonly temp_credit_ceiling: string | number | null;
  readonly is_active: boolean;
}

