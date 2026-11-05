/**
 * Types & Contracts for Holding Hub Enterprise (Etapa 2)
 * Aligned with Backend Pydantic Schemas from schemas_holding_hub.py.
 */

export type HoldingTabType = "central" | "briefing" | "planes" | "creditos";
export type HoldingTabId = HoldingTabType;

export type CreditDistributionMode = "shared" | "allocated";

export type SafetyStatus = "NORMAL" | "WARNING" | "CRITICAL";

export interface HoldingDailyCreditUsageItem {
  readonly date: string;
  readonly credits: number;
  readonly tokens: number;
  readonly requests: number;
}

export interface HoldingTenantCard {
  readonly id: string;
  readonly name: string;
  readonly schema_name: string;
  readonly operational_status: "active" | "suspended" | "maintenance";
  readonly used_credits: number;
  readonly allocated_credits: number;
  readonly bot_requests: number;
  readonly usage_pct: number;
  readonly safety_status: SafetyStatus;
  readonly business_type?: string;
  readonly modules?: readonly string[];
  readonly rut?: string;
  readonly address?: string;
}

export interface HoldingMetrics {
  readonly total_sales: number;
  readonly inventory_value: number;
  readonly waste_pct: number;
}

export interface SafetyCapPredictiveStatus {
  readonly status: SafetyStatus;
  readonly burn_rate_daily: number;
  readonly estimated_days_remaining: number | null;
  readonly recommendation: string;
}

export interface HoldingBriefingResponse {
  readonly holding_id: string;
  readonly generated_at: string;
  readonly summary_paragraphs: readonly string[];
  readonly key_achievements: readonly string[];
  readonly cost_alerts: readonly string[];
  readonly safety_cap_prediction: SafetyCapPredictiveStatus;
  readonly tokens_used: number;
  readonly credits_deducted: number;
  readonly model_name: string;
}

export interface HoldingHubSummary {
  readonly holding_id: string;
  readonly name: string;
  readonly rut: string;
  readonly active_plan_slug: "starter" | "business" | "enterprise";
  readonly credit_balance: number;
  readonly total_credits: number;
  readonly used_credits: number;
  readonly distribution_mode: CreditDistributionMode;
  readonly safety_status: SafetyStatus;
  readonly usage_pct: number;
  readonly metrics: HoldingMetrics;
  readonly tenants: readonly HoldingTenantCard[];
  readonly daily_usage: readonly HoldingDailyCreditUsageItem[];
  readonly ai_briefing?: HoldingBriefingResponse | null;
}

export interface SaaSPlanTier {
  readonly slug: "starter" | "business" | "enterprise";
  readonly nameKey: string;
  readonly descKey: string;
  readonly priceClp: number;
  readonly priceUsd: number;
  readonly monthlyCredits: number;
  readonly maxTenants: number | "unlimited";
  readonly recommended?: boolean;
  readonly modules: readonly string[];
  readonly perks: readonly string[];
}

export interface HoldingPurchaseCreditsRequest {
  readonly holding_id: string;
  readonly credits_amount: number;
  readonly currency: "CLP" | "USD" | "EUR" | "BRL";
  readonly payment_method: string;
  readonly idempotency_key?: string;
}

export interface HoldingCreditDistributionRequest {
  readonly distribution_mode: CreditDistributionMode;
  readonly allocations: Readonly<Record<string, number>>;
}

export interface HoldingPlanChangeRequest {
  readonly holding_id: string;
  readonly new_plan_slug: string;
  readonly effective_immediately: boolean;
  readonly reason?: string;
}
