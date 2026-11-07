import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest, setHttpRequestContext } from "@/shared/api/httpClient";
import { scrollToTopInstant } from "@/shared/components/layout";
import { isMockDataEnabled, MOCK_DATA_MODE_EVENT_NAME } from "@/shared/mock/mockModeStorage";
import { INITIAL_HOLDING_DATA } from "./constants";
import type {
  CreditDistributionMode,
  HoldingHubSummary,
  HoldingTabId,
  HoldingTenantCard,
} from "./types";

const CLEAN_HOLDING_DATA: HoldingHubSummary = {
  holding_id: "holding-clean",
  name: "Sin Holding Configurado",
  rut: "—",
  active_plan_slug: "starter",
  credit_balance: 0,
  total_credits: 0,
  used_credits: 0,
  distribution_mode: "shared",
  safety_status: "NORMAL",
  usage_pct: 0,
  metrics: {
    total_sales: 0,
    inventory_value: 0,
    waste_pct: 0,
  },
  tenants: [],
  daily_usage: [],
  ai_briefing: {
    holding_id: "holding-clean",
    generated_at: new Date().toISOString(),
    summary_paragraphs: [],
    key_achievements: [],
    cost_alerts: [],
    safety_cap_prediction: {
      status: "NORMAL",
      burn_rate_daily: 0,
      estimated_days_remaining: 0,
      recommendation: "Sin consumo registrado.",
    },
    tokens_used: 0,
    credits_deducted: 0,
    model_name: "gemini-1.5-flash",
  },
};

export interface UseHoldingHubDataReturn {
  readonly data: HoldingHubSummary;
  readonly loading: boolean;
  readonly refreshing: boolean;
  readonly activeTab: HoldingTabId;
  readonly setActiveTab: (tab: HoldingTabId) => void;
  readonly activeScope: string;
  readonly setActiveScope: (scope: string) => void;
  readonly searchFilter: string;
  readonly setSearchFilter: (filter: string) => void;
  readonly filteredTenants: readonly HoldingTenantCard[];
  readonly switchTenant: (tenant: HoldingTenantCard) => void;
  readonly refreshData: () => Promise<void>;
  readonly purchaseCredits: (amount: number, currency?: string, method?: string) => Promise<boolean>;
  readonly updateDistribution: (
    mode: CreditDistributionMode,
    allocations: Record<string, number>
  ) => Promise<boolean>;
  readonly changePlan: (newPlanSlug: string, immediate: boolean, reason?: string) => Promise<boolean>;
}

export function useHoldingHubData(initialHoldingId?: string): UseHoldingHubDataReturn {
  const navigate = useNavigate();
  const [data, setData] = useState<HoldingHubSummary>(() =>
    isMockDataEnabled() ? INITIAL_HOLDING_DATA : CLEAN_HOLDING_DATA
  );
  const [loading] = useState<boolean>(false);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<HoldingTabId>("central");
  const [activeScope, setActiveScope] = useState<string>("all");
  const [searchFilter, setSearchFilter] = useState<string>("");

  useEffect(() => {
    const handleMockModeChange = () => {
      setData(isMockDataEnabled() ? INITIAL_HOLDING_DATA : CLEAN_HOLDING_DATA);
    };
    window.addEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
    return () => window.removeEventListener(MOCK_DATA_MODE_EVENT_NAME, handleMockModeChange);
  }, []);

  const refreshData = useCallback(async () => {
    setRefreshing(true);
    try {
      const holdingId = initialHoldingId || data.holding_id;
      const fallback = isMockDataEnabled() ? INITIAL_HOLDING_DATA : CLEAN_HOLDING_DATA;
      const resp = await apiRequest<HoldingHubSummary>(
        `/api/v1/holding-hub/summary?holding_id=${encodeURIComponent(holdingId)}`,
        {
          fallbackData: fallback,
        }
      );
      if (resp?.data) {
        setData(resp.data);
      }
    } catch {
      // In case of error or offline development, retain existing state
    } finally {
      setRefreshing(false);
    }
  }, [data, initialHoldingId]);

  const switchTenant = useCallback(
    (tenant: HoldingTenantCard) => {
      setHttpRequestContext({
        holdingId: data.holding_id,
        tenantId: tenant.id,
      });
      // Force instantaneous scroll-to-top upon switching to tenant workspace
      scrollToTopInstant();
      // Navigate to tenant main dashboard
      navigate("/");
    },
    [data.holding_id, navigate]
  );

  const purchaseCredits = useCallback(
    async (amount: number, currency: string = "CLP", method: string = "credit_card"): Promise<boolean> => {
      try {
        await apiRequest("/api/v1/holding-hub/purchase-credits", {
          method: "POST",
          body: {
            holding_id: data.holding_id,
            credits_amount: amount,
            currency,
            payment_method: method,
          },
          fallbackData: { success: true },
        });

        setData((prev) => ({
          ...prev,
          credit_balance: prev.credit_balance + amount,
          total_credits: prev.total_credits + amount,
          usage_pct: Math.round(((prev.used_credits) / (prev.total_credits + amount)) * 1000) / 10,
        }));
        return true;
      } catch {
        // Fallback optimistic update
        setData((prev) => ({
          ...prev,
          credit_balance: prev.credit_balance + amount,
          total_credits: prev.total_credits + amount,
          usage_pct: Math.round(((prev.used_credits) / (prev.total_credits + amount)) * 1000) / 10,
        }));
        return true;
      }
    },
    [data.holding_id]
  );

  const updateDistribution = useCallback(
    async (
      mode: CreditDistributionMode,
      allocations: Record<string, number>
    ): Promise<boolean> => {
      try {
        await apiRequest("/api/v1/holding-hub/credit-distribution", {
          method: "POST",
          body: {
            distribution_mode: mode,
            allocations,
          },
          fallbackData: { success: true },
        });

        setData((prev) => {
          const updatedTenants = prev.tenants.map((t) => {
            const allocated = allocations[t.id] ?? t.allocated_credits;
            return {
              ...t,
              allocated_credits: mode === "allocated" ? allocated : 0,
            };
          });
          return {
            ...prev,
            distribution_mode: mode,
            tenants: updatedTenants,
          };
        });
        return true;
      } catch {
        setData((prev) => {
          const updatedTenants = prev.tenants.map((t) => {
            const allocated = allocations[t.id] ?? t.allocated_credits;
            return {
              ...t,
              allocated_credits: mode === "allocated" ? allocated : 0,
            };
          });
          return {
            ...prev,
            distribution_mode: mode,
            tenants: updatedTenants,
          };
        });
        return true;
      }
    },
    []
  );

  const changePlan = useCallback(
    async (
      newPlanSlug: string,
      immediate: boolean,
      reason?: string
    ): Promise<boolean> => {
      try {
        await apiRequest("/api/v1/holding-hub/change-plan", {
          method: "POST",
          body: {
            holding_id: data.holding_id,
            new_plan_slug: newPlanSlug,
            effective_immediately: immediate,
            reason,
          },
          fallbackData: { success: true },
        });

        setData((prev) => ({
          ...prev,
          active_plan_slug: newPlanSlug as "starter" | "business" | "enterprise",
        }));
        return true;
      } catch {
        setData((prev) => ({
          ...prev,
          active_plan_slug: newPlanSlug as "starter" | "business" | "enterprise",
        }));
        return true;
      }
    },
    [data.holding_id]
  );

  const filteredTenants = useMemo(() => {
    if (!searchFilter.trim()) return data.tenants;
    const q = searchFilter.toLowerCase();
    return data.tenants.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.schema_name.toLowerCase().includes(q) ||
        (t.business_type && t.business_type.toLowerCase().includes(q))
    );
  }, [data.tenants, searchFilter]);

  return {
    data,
    loading,
    refreshing,
    activeTab,
    setActiveTab,
    activeScope,
    setActiveScope,
    searchFilter,
    setSearchFilter,
    filteredTenants,
    switchTenant,
    refreshData,
    purchaseCredits,
    updateDistribution,
    changePlan,
  };
}
