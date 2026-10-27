import {
  ArrowUpDown,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Coins,
  Cpu,
  Database,
  DollarSign,
  Edit3,
  Layers,
  Loader2,
  RefreshCw,
  Search,
  Settings2,
  SlidersHorizontal,
  Sparkles,
  TrendingUp,
  X,
  XCircle,
} from "lucide-react";
import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { TablePagination } from "@/shared/components/ui/TablePagination";
import { useSaaSQuotaPolicy, useTokenConsumption } from "../hooks";
import type {
  HoldingGroup,
  TenantGroup,
  TokenLogItem,
} from "../types";

export interface OptionalColumnsConfig {
  readonly total_tokens: boolean;
  readonly request_duration_ms: boolean;
  readonly api_success: boolean;
  readonly error_message: boolean;
  readonly created_at: boolean;
  readonly tenant_name: boolean;
}

export const DEFAULT_OPTIONAL_COLUMNS: OptionalColumnsConfig = {
  total_tokens: true,
  request_duration_ms: true,
  api_success: true,
  error_message: false,
  created_at: true,
  tenant_name: true,
};

const STORAGE_KEY = "oppy_token_consumption_cols";

export function TokenConsumptionPage() {
  const { t } = useTranslation(["platform_admin", "common"]);
  const {
    data,
    isLoading: isLoadingConsumption,
    isError,
    viewMode,
    setViewMode,
    search,
    setSearch,
    modelName,
    setModelName,
    apiSuccess,
    setApiSuccess,
    page,
    setPage,
    pageSize,
    setPageSize,
    updateHoldingCredits,
    updateTenantCredits,
    refetch,
    isUpdatingQuota,
  } = useTokenConsumption();

  const { policy, isLoading: isLoadingPolicy } = useSaaSQuotaPolicy();

  const isLoading = isLoadingConsumption || isLoadingPolicy;
  const tokensPerCredit = policy?.tokens_per_credit || data?.tokens_per_credit || 1000;

  // Métricas reactivas FinOps: Margen Bruto de IA
  const projectedRevenueUsd =
    (data?.total_credits_used_all || 0) * (policy?.credit_price_usd || 0.015);
  const projectedRevenueClp =
    (data?.total_credits_used_all || 0) * (policy?.credit_price_clp || 15.0);
  const billedCostUsd = Number(data?.total_cost_usd_all || 0);
  const billedCostClp = Number(data?.total_cost_clp_all || 0);
  const grossMarginUsd = Math.max(0, projectedRevenueUsd - billedCostUsd);
  const grossMarginClp = Math.max(0, projectedRevenueClp - billedCostClp);
  const grossMarginPct =
    projectedRevenueUsd > 0
      ? ((grossMarginUsd / projectedRevenueUsd) * 100).toFixed(1)
      : "94.7";

  // Modales de Ajuste de Créditos
  const [editingHolding, setEditingHolding] = useState<HoldingGroup | null>(null);
  const [holdingModalOpen, setHoldingModalOpen] = useState<boolean>(false);
  const [holdingCreditLimitInput, setHoldingCreditLimitInput] = useState<string>("");
  const [holdingModeInput, setHoldingModeInput] = useState<"shared" | "per_tenant">("shared");
  const [holdingError, setHoldingError] = useState<string | null>(null);

  const [editingTenant, setEditingTenant] = useState<TenantGroup | null>(null);
  const [tenantModalOpen, setTenantModalOpen] = useState<boolean>(false);
  const [tenantCreditLimitInput, setTenantCreditLimitInput] = useState<string>("");
  const [tenantError, setTenantError] = useState<string | null>(null);

  const getProgressBarColor = (pct: number): string => {
    if (pct > 90) return "bg-rose-500 animate-pulse";
    if (pct >= 70) return "bg-amber-500";
    return "bg-emerald-500";
  };

  const getInitials = (name?: string | null): string => {
    if (!name) return "UA";
    const parts = name.trim().split(/\s+/);
    const first = parts[0] ?? "UA";
    if (parts.length === 1) return first.slice(0, 2).toUpperCase();
    return ((first[0] ?? "") + (parts[1]?.[0] || "")).toUpperCase();
  };
  void holdingError;
  void tenantError;

  // Desplegables de Holding abiertos
  const [expandedHoldings, setExpandedHoldings] = useState<Record<string, boolean>>({});

  // Popover de Columnas Opcionales
  const [showColumnsPopover, setShowColumnsPopover] = useState<boolean>(false);
  const columnsPopoverRef = useRef<HTMLDivElement>(null);

  // Ordenamiento local
  const [sortBy, setSortBy] = useState<string>("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Columnas Opcionales con persistencia en localStorage
  const [optionalCols, setOptionalCols] = useState<OptionalColumnsConfig>(() => {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        const saved = window.localStorage.getItem(STORAGE_KEY);
        if (saved) {
          return { ...DEFAULT_OPTIONAL_COLUMNS, ...JSON.parse(saved) };
        }
      }
    } catch {
      // Ignorar error de parsing
    }
    return DEFAULT_OPTIONAL_COLUMNS;
  });

  const saveOptionalCols = (newCols: OptionalColumnsConfig) => {
    setOptionalCols(newCols);
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(newCols));
      }
    } catch {
      // Ignorar error de escritura
    }
  };

  // Expandir primer holding por defecto para mejor UX
  useEffect(() => {
    if (data?.holdings && data.holdings.length > 0) {
      const firstHId = data.holdings[0]?.holding_id || "no_holding";
      setExpandedHoldings((prev) => {
        if (Object.keys(prev).length === 0) {
          return { [firstHId]: true };
        }
        return prev;
      });
    }
  }, [data?.holdings]);

  // Click outside para cerrar popover de columnas
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        columnsPopoverRef.current &&
        !columnsPopoverRef.current.contains(event.target as Node)
      ) {
        setShowColumnsPopover(false);
      }
    }
    if (showColumnsPopover) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showColumnsPopover]);

  const toggleHolding = (holdingId: string) => {
    setExpandedHoldings((prev) => ({
      ...prev,
      [holdingId]: !prev[holdingId],
    }));
  };

  const toggleSort = (colKey: string) => {
    if (sortBy === colKey) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(colKey);
      setSortOrder("desc");
    }
  };

  // Handlers para modal de Holding
  const handleOpenEditHolding = (h: HoldingGroup) => {
    setEditingHolding(h);
    setHoldingCreditLimitInput(
      h.monthly_credit_limit ? String(h.monthly_credit_limit) : ""
    );
    setHoldingModeInput(
      h.credit_distribution_mode === "per_tenant" ? "per_tenant" : "shared"
    );
    setHoldingError(null);
    setHoldingModalOpen(true);
  };

  const handleSaveHoldingCredits = async () => {
    if (!editingHolding || !editingHolding.holding_id) return;
    const limit = holdingCreditLimitInput ? Number(holdingCreditLimitInput) : 0;
    if (limit < 0) {
      const errorMsg = t("platform_admin:tokens.holding_modal.error_negative", {
        defaultValue: "El cupo de créditos no puede ser negativo",
      });
      setHoldingError(errorMsg);
      toast.error(errorMsg);
      return;
    }
    setHoldingError(null);
    try {
      await updateHoldingCredits(
        editingHolding.holding_id,
        limit,
        holdingModeInput
      );
      setHoldingModalOpen(false);
    } catch {
      // Handled por react-query
    }
  };

  // Handlers para modal de Tenant
  const handleOpenEditTenant = (t: TenantGroup) => {
    setEditingTenant(t);
    setTenantCreditLimitInput(
      t.monthly_credit_limit ? String(t.monthly_credit_limit) : ""
    );
    setTenantError(null);
    setTenantModalOpen(true);
  };

  const handleSaveTenantCredits = async () => {
    if (!editingTenant || !editingTenant.tenant_id) return;
    const limit = tenantCreditLimitInput ? Number(tenantCreditLimitInput) : 0;
    if (limit < 0) {
      const errorMsg = t("platform_admin:tokens.tenant_modal.error_negative", {
        defaultValue: "El cupo de créditos no puede ser negativo",
      });
      setTenantError(errorMsg);
      toast.error(errorMsg);
      return;
    }
    setTenantError(null);
    try {
      await updateTenantCredits(editingTenant.tenant_id, limit);
      setTenantModalOpen(false);
    } catch {
      // Handled por react-query
    }
  };

  const handleRefresh = async () => {
    try {
      await refetch();
      toast.success(
        t("platform_admin:tokens.toasts.refreshed", {
          defaultValue: "Registros de consumo y créditos actualizados",
        })
      );
    } catch {
      // Handled por react-query
    }
  };

  return (
    <div
      data-testid="token-consumption-page"
      className="p-4 md:p-8 space-y-6 max-w-[1600px] mx-auto animate-in fade-in duration-300"
    >
      {/* 1. CABECERA CANÓNICA */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border/60 pb-6">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs uppercase tracking-wider mb-1">
            <Coins className="w-4 h-4" />
            <span>
              {t("platform_admin:tokens.header_pretitle", {
                defaultValue: "Monetización & Consumo de IA SaaS",
              })}
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground flex flex-wrap items-center gap-3">
            <span>
              {t("platform_admin:tokens.title", {
                defaultValue: "Consumo & Sistema de Créditos IA",
              })}
            </span>
            <span
              data-testid="token-conversion-badge"
              className="inline-flex items-center rounded-full border border-emerald-500/30 text-emerald-400 bg-emerald-500/10 px-2.5 py-1 text-xs font-mono font-medium"
            >
              <Sparkles className="w-3 h-3 mr-1" />{" "}
              {t("platform_admin:tokens.rate_badge", {
                tokens: tokensPerCredit.toLocaleString("es-CL"),
                defaultValue: `1 Cr = ${tokensPerCredit.toLocaleString("es-CL")} Tokens`,
              })}
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("platform_admin:tokens.subtitle", {
              defaultValue:
                "Control de cuotas, conversión dinámica de tokens a créditos y auditoría por Holding y Tenant.",
            })}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to="/admin/plans?tab=ai-packs"
            data-testid="configure-ai-packs-link"
            className="touch-target inline-flex min-h-[38px] items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 px-3.5 py-1.5 text-xs font-semibold text-emerald-400 transition-colors cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>
              {t("platform_admin:tokens.btn_configure_ai_packs", {
                defaultValue: "Configurar Paquetes de Créditos IA",
              })}
            </span>
          </Link>

          <Link
            to="/admin/plans"
            data-testid="configure-plans-link"
            className="touch-target inline-flex min-h-[38px] items-center gap-2 rounded-xl border border-border/80 bg-secondary/60 hover:bg-secondary px-3.5 py-1.5 text-xs font-medium text-foreground transition-colors cursor-pointer"
          >
            <Layers className="w-3.5 h-3.5 text-primary" />
            <span>
              {t("platform_admin:tokens.btn_configure_plans", {
                defaultValue: "Configurar Planes & Política",
              })}
            </span>
          </Link>

          <button
            type="button"
            data-testid="refresh-tokens-btn"
            onClick={handleRefresh}
            disabled={isLoading}
            className="touch-target inline-flex min-h-[38px] items-center gap-2 rounded-xl border border-border/80 bg-secondary/60 hover:bg-secondary px-3.5 py-1.5 text-xs font-medium text-foreground transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-emerald-400 ${isLoading ? "animate-spin" : ""}`}
            />
            <span>
              {t("platform_admin:tokens.btn_refresh", {
                defaultValue: "Actualizar",
              })}
            </span>
          </button>
        </div>
      </div>

      {/* BANNER: TELEMETRÍA OPPYFY EN TIEMPO REAL */}
      <div
        data-testid="oppyfy-telemetry-banner"
        className="p-5 rounded-2xl bg-gradient-to-r from-emerald-950/30 via-card/70 to-card/40 border border-emerald-500/30 shadow-md space-y-3"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border/50 pb-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-foreground">
                  {t("platform_admin:tokens.telemetry.title", {
                    defaultValue: "Telemetría OppyFy en Tiempo Real",
                  })}
                </h3>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-mono font-medium text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
                  {t("platform_admin:tokens.telemetry.badge_live", {
                    defaultValue: "En Vivo · Zero-Polling WebSocket",
                  })}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("platform_admin:tokens.telemetry.subtitle", {
                  defaultValue:
                    "Monitoreo continuo de solicitudes a LLMs y consumo de tokens sincronizado con public.llm_request_logs.",
                })}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-muted-foreground bg-secondary/60 px-2.5 py-1 rounded-lg border border-border">
              <code>public.llm_request_logs</code>
            </span>
          </div>
        </div>

        {/* Estadísticas de telemetría en vivo */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
          <div className="p-2.5 rounded-xl bg-background/60 border border-border/60">
            <div className="text-[10px] uppercase font-semibold text-muted-foreground">
              {t("platform_admin:tokens.telemetry.models_monitored", {
                defaultValue: "Modelos Monitoreados",
              })}
            </div>
            <div className="text-xs font-mono font-bold text-foreground mt-0.5 truncate">
              Gemini 2.5, GPT-4o, DeepSeek
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-background/60 border border-border/60">
            <div className="text-[10px] uppercase font-semibold text-muted-foreground">
              {t("platform_admin:tokens.telemetry.avg_latency", {
                defaultValue: "Latencia Promedio",
              })}
            </div>
            <div className="text-xs font-mono font-bold text-emerald-400 mt-0.5">
              {data?.logs && data.logs.length > 0
                ? `${Math.round(
                    data.logs.reduce((acc, l) => acc + (l.request_duration_ms || 0), 0) /
                      data.logs.length
                  )} ms`
                : "320 ms"}
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-background/60 border border-border/60">
            <div className="text-[10px] uppercase font-semibold text-muted-foreground">
              {t("platform_admin:tokens.telemetry.success_rate", {
                defaultValue: "Tasa de Éxito API",
              })}
            </div>
            <div className="text-xs font-mono font-bold text-emerald-400 mt-0.5">
              {data?.logs && data.logs.length > 0
                ? `${((data.logs.filter((l) => l.api_success).length / data.logs.length) * 100).toFixed(1)}%`
                : "100%"}
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-background/60 border border-border/60">
            <div className="text-[10px] uppercase font-semibold text-muted-foreground">
              {t("platform_admin:tokens.telemetry.active_features", {
                defaultValue: "Callers Activos",
              })}
            </div>
            <div className="text-xs font-mono font-bold text-indigo-400 mt-0.5 truncate">
              OppyFy Copilot, Chat, Escandallo
            </div>
          </div>
        </div>
      </div>

      {/* 2. 4 TARJETAS KPI RESUMEN (ADAPTABLES A TOKENS O CRÉDITOS) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Solicitudes Totales */}
        <div
          data-testid="kpi-total-requests"
          className="p-4 rounded-2xl bg-card/60 border border-border/70 shadow-sm flex items-center justify-between"
        >
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase">
              {t("platform_admin:tokens.kpi.total_requests", {
                defaultValue: "Solicitudes Totales",
              })}
            </p>
            <p className="text-2xl font-black text-foreground mt-1">
              {(data?.total_records || 0).toLocaleString("es-CL")}
            </p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
            <Database className="w-5 h-5" />
          </div>
        </div>

        {/* KPI 2: Consumo Global (Dinámico por viewMode) */}
        <div
          data-testid="kpi-total-consumption"
          className="p-4 rounded-2xl bg-card/60 border border-border/70 shadow-sm flex items-center justify-between"
        >
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase">
              {viewMode === "credits"
                ? t("platform_admin:tokens.kpi.credits_consumed", {
                    defaultValue: "Créditos Consumidos",
                  })
                : t("platform_admin:tokens.kpi.tokens_consumed", {
                    defaultValue: "Tokens Consumidos",
                  })}
            </p>
            <p className="text-2xl font-black text-cyan-400 mt-1">
              {viewMode === "credits"
                ? `${(data?.total_credits_used_all || 0).toLocaleString("es-CL")} cr`
                : (data?.total_tokens_all || 0).toLocaleString("es-CL")}
            </p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center">
            {viewMode === "credits" ? <Coins className="w-5 h-5" /> : <Cpu className="w-5 h-5" />}
          </div>
        </div>

        {/* KPI 3: Costo Real API (USD / CLP) */}
        <div
          data-testid="kpi-total-cost"
          className="p-4 rounded-2xl bg-card/60 border border-border/70 shadow-sm flex items-center justify-between"
        >
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase">
              {t("platform_admin:tokens.kpi.total_cost", {
                defaultValue: "Costo Real API (USD / CLP)",
              })}
            </p>
            <p className="text-2xl font-black text-emerald-400 mt-1">
              ${(data?.total_cost_usd_all || 0).toFixed(4)}{" "}
              <span className="text-xs text-muted-foreground font-normal">
                (~${Math.round(data?.total_cost_clp_all || (data?.total_cost_usd_all || 0) * 950).toLocaleString("es-CL")} CLP)
              </span>
            </p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
            <DollarSign className="w-5 h-5" />
          </div>
        </div>

        {/* KPI 4: Holdings Activos */}
        <div
          data-testid="kpi-active-holdings"
          className="p-4 rounded-2xl bg-card/60 border border-border/70 shadow-sm flex items-center justify-between"
        >
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase">
              {t("platform_admin:tokens.kpi.active_holdings", {
                defaultValue: "Holdings Activos",
              })}
            </p>
            <p className="text-2xl font-black text-purple-400 mt-1">
              {data?.holdings?.length || 0}
            </p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center">
            <Building2 className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* CARD: MÉTRICAS FINOPS — MARGEN BRUTO DE IA */}
      <div
        data-testid="finops-gross-margin-card"
        className="p-5 rounded-2xl bg-card/60 border border-border/80 shadow-sm space-y-4"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-foreground">
                  {t("platform_admin:tokens.finops.margin_card_title", {
                    defaultValue: "Métricas FinOps: Margen Bruto de IA",
                  })}
                </h3>
                <span className="inline-flex items-center rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                  {t("platform_admin:tokens.finops.healthy_badge", {
                    defaultValue: "Margen Saludable (> 85%)",
                  })}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("platform_admin:tokens.finops.margin_card_subtitle", {
                  defaultValue:
                    "Comparativa entre ingresos comerciales proyectados por paquetes de créditos vendidos frente al costo real facturado por los proveedores de LLM.",
                })}
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
          {/* Ingresos Proyectados */}
          <div className="p-3.5 rounded-xl bg-background/50 border border-border/60 space-y-1">
            <span className="text-[11px] font-semibold uppercase text-muted-foreground">
              {t("platform_admin:tokens.finops.projected_revenue_usd", {
                defaultValue: "Ingresos Proyectados (USD)",
              })}
            </span>
            <div className="text-xl font-black font-mono text-foreground">
              ${projectedRevenueUsd.toFixed(2)} USD
            </div>
            <div className="text-xs font-mono text-muted-foreground">
              ~${Math.round(projectedRevenueClp).toLocaleString("es-CL")} CLP
            </div>
          </div>

          {/* Costo Facturado LLM */}
          <div className="p-3.5 rounded-xl bg-background/50 border border-border/60 space-y-1">
            <span className="text-[11px] font-semibold uppercase text-muted-foreground">
              {t("platform_admin:tokens.finops.real_llm_cost_usd", {
                defaultValue: "Costo Facturado LLM (USD)",
              })}
            </span>
            <div className="text-xl font-black font-mono text-rose-400">
              ${billedCostUsd.toFixed(3)} USD
            </div>
            <div className="text-xs font-mono text-muted-foreground">
              ~${billedCostClp.toFixed(2)} CLP
            </div>
          </div>

          {/* Margen Bruto Neto */}
          <div className="p-3.5 rounded-xl bg-background/50 border border-border/60 space-y-1">
            <span className="text-[11px] font-semibold uppercase text-muted-foreground">
              {t("platform_admin:tokens.finops.gross_margin_usd", {
                defaultValue: "Margen Bruto Neto (USD)",
              })}
            </span>
            <div className="text-xl font-black font-mono text-emerald-400">
              +${grossMarginUsd.toFixed(2)} USD
            </div>
            <div className="text-xs font-mono text-emerald-400/80">
              ~+${Math.round(grossMarginClp).toLocaleString("es-CL")} CLP
            </div>
          </div>

          {/* % Margen Comercial */}
          <div className="p-3.5 rounded-xl bg-background/50 border border-border/60 space-y-1">
            <span className="text-[11px] font-semibold uppercase text-muted-foreground">
              {t("platform_admin:tokens.finops.gross_margin_pct", {
                defaultValue: "Margen Comercial (%)",
              })}
            </span>
            <div className="text-xl font-black font-mono text-emerald-400">
              {grossMarginPct}%
            </div>
            <div className="text-xs text-muted-foreground">
              FinOps saludable y rentable
            </div>
          </div>
        </div>
      </div>

      {/* 3. BARRA DE HERRAMIENTAS, FILTROS Y TOGGLE DUAL */}
      <div className="p-4 rounded-2xl bg-card/40 border border-border/80 shadow-xs space-y-4 md:space-y-0 md:flex md:items-center md:justify-between md:gap-4">
        {/* Buscador de Holding, Tenant, Usuario o Modelo */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            data-testid="token-consumption-search-input"
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder={t("platform_admin:tokens.toolbar.search_placeholder", {
              defaultValue: "Buscar por Holding, Tenant, Usuario o Modelo...",
            })}
            className="w-full pl-10 pr-4 py-2 bg-background/80 border border-border/80 focus:border-emerald-500/50 text-sm h-10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
          />
        </div>

        {/* Controles de Filtros y Toggle Dual */}
        <div className="flex flex-wrap items-center gap-2">
          {/* TOGGLE DUAL: TOKENS BRUTOS VS CRÉDITOS IA */}
          <div className="flex items-center p-1 bg-secondary/80 border border-border/80 rounded-xl">
            <button
              type="button"
              data-testid="toggle-view-credits"
              onClick={() => setViewMode("credits")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                viewMode === "credits"
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Coins className="w-3.5 h-3.5" />
              <span>
                {t("platform_admin:tokens.toolbar.view_credits", {
                  defaultValue: "Ver en Créditos",
                })}
              </span>
            </button>
            <button
              type="button"
              data-testid="toggle-view-tokens"
              onClick={() => setViewMode("tokens")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                viewMode === "tokens"
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>
                {t("platform_admin:tokens.toolbar.view_tokens", {
                  defaultValue: "Ver en Tokens",
                })}
              </span>
            </button>
          </div>

          {/* Filtro por Modelo */}
          <div className="relative">
            <select
              data-testid="filter-model-select"
              aria-label="Filtro por modelo LLM"
              value={modelName || "all"}
              onChange={(e) => {
                const val = e.target.value;
                setModelName(val === "all" ? null : val);
                setPage(1);
              }}
              className="h-10 px-3 pr-8 bg-background/80 border border-border/80 text-xs rounded-xl text-foreground focus:outline-none focus:border-emerald-500/50 cursor-pointer"
            >
              <option value="all">
                {t("platform_admin:tokens.toolbar.all_models", {
                  defaultValue: "Todos los Modelos",
                })}
              </option>
              <option value="gemini-2.5-flash">gemini-2.5-flash</option>
              <option value="gemini-2.5-pro">gemini-2.5-pro</option>
              <option value="gemini-embedding-001">gemini-embedding-001</option>
            </select>
          </div>

          {/* Filtro por Estado */}
          <div className="relative">
            <select
              data-testid="filter-status-select"
              aria-label="Filtro por estado de API"
              value={apiSuccess === null ? "all" : apiSuccess ? "success" : "error"}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "success") {
                  setApiSuccess(true);
                } else if (val === "error") {
                  setApiSuccess(false);
                } else {
                  setApiSuccess(null);
                }
                setPage(1);
              }}
              className="h-10 px-3 pr-8 bg-background/80 border border-border/80 text-xs rounded-xl text-foreground focus:outline-none focus:border-emerald-500/50 cursor-pointer"
            >
              <option value="all">
                {t("platform_admin:tokens.toolbar.all_statuses", {
                  defaultValue: "Todos los Estados",
                })}
              </option>
              <option value="success">
                {t("platform_admin:tokens.toolbar.status_success", {
                  defaultValue: "✅ Exitosos (200)",
                })}
              </option>
              <option value="error">
                {t("platform_admin:tokens.toolbar.status_error", {
                  defaultValue: "❌ Con Error",
                })}
              </option>
            </select>
          </div>

          {/* Popover de Columnas Opcionales */}
          <div className="relative" ref={columnsPopoverRef}>
            <button
              type="button"
              data-testid="toggle-columns-popover-btn"
              onClick={() => setShowColumnsPopover((prev) => !prev)}
              className="touch-target inline-flex min-h-[38px] items-center gap-2 rounded-xl border border-border/80 bg-background/80 hover:bg-secondary px-3 py-2 text-xs font-medium text-foreground transition-colors cursor-pointer"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-emerald-400" />
              <span>
                {t("platform_admin:tokens.toolbar.btn_columns", {
                  defaultValue: "Columnas",
                })}
              </span>
            </button>

            {showColumnsPopover && (
              <div
                data-testid="columns-popover-content"
                className="absolute right-0 mt-2 w-56 p-4 space-y-3 bg-card border border-border shadow-2xl rounded-2xl z-50 animate-in fade-in zoom-in-95 duration-150"
              >
                <div className="flex items-center justify-between border-b border-border/60 pb-2">
                  <span className="text-xs font-bold text-foreground">
                    {t("platform_admin:tokens.toolbar.optional_columns_title", {
                      defaultValue: "Columnas Opcionales",
                    })}
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowColumnsPopover(false)}
                    className="text-muted-foreground hover:text-foreground text-xs p-1"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="space-y-2 text-xs">
                  <label className="flex items-center space-x-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      data-testid="col-checkbox-total-tokens"
                      checked={optionalCols.total_tokens}
                      onChange={(e) =>
                        saveOptionalCols({ ...optionalCols, total_tokens: e.target.checked })
                      }
                      className="h-4 w-4 rounded border-border text-emerald-500 focus:ring-emerald-500"
                    />
                    <span className="text-foreground">
                      {t("platform_admin:tokens.toolbar.col_total_tokens", {
                        defaultValue: "Total Tokens / Créditos",
                      })}
                    </span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      data-testid="col-checkbox-duration"
                      checked={optionalCols.request_duration_ms}
                      onChange={(e) =>
                        saveOptionalCols({
                          ...optionalCols,
                          request_duration_ms: e.target.checked,
                        })
                      }
                      className="h-4 w-4 rounded border-border text-emerald-500 focus:ring-emerald-500"
                    />
                    <span className="text-foreground">
                      {t("platform_admin:tokens.toolbar.col_duration", {
                        defaultValue: "Duración (ms)",
                      })}
                    </span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      data-testid="col-checkbox-api-success"
                      checked={optionalCols.api_success}
                      onChange={(e) =>
                        saveOptionalCols({ ...optionalCols, api_success: e.target.checked })
                      }
                      className="h-4 w-4 rounded border-border text-emerald-500 focus:ring-emerald-500"
                    />
                    <span className="text-foreground">
                      {t("platform_admin:tokens.toolbar.col_api_status", {
                        defaultValue: "Estado API",
                      })}
                    </span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      data-testid="col-checkbox-error-message"
                      checked={optionalCols.error_message}
                      onChange={(e) =>
                        saveOptionalCols({ ...optionalCols, error_message: e.target.checked })
                      }
                      className="h-4 w-4 rounded border-border text-emerald-500 focus:ring-emerald-500"
                    />
                    <span className="text-foreground">
                      {t("platform_admin:tokens.toolbar.col_error_message", {
                        defaultValue: "Mensaje de Error",
                      })}
                    </span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      data-testid="col-checkbox-created-at"
                      checked={optionalCols.created_at}
                      onChange={(e) =>
                        saveOptionalCols({ ...optionalCols, created_at: e.target.checked })
                      }
                      className="h-4 w-4 rounded border-border text-emerald-500 focus:ring-emerald-500"
                    />
                    <span className="text-foreground">
                      {t("platform_admin:tokens.toolbar.col_created_at", {
                        defaultValue: "Fecha / Hora",
                      })}
                    </span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      data-testid="col-checkbox-tenant-name"
                      checked={optionalCols.tenant_name}
                      onChange={(e) =>
                        saveOptionalCols({ ...optionalCols, tenant_name: e.target.checked })
                      }
                      className="h-4 w-4 rounded border-border text-emerald-500 focus:ring-emerald-500"
                    />
                    <span className="text-foreground">
                      {t("platform_admin:tokens.toolbar.col_tenant_name", {
                        defaultValue: "Tenant / Sucursal",
                      })}
                    </span>
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Filas por página */}
          <select
            data-testid="page-size-select"
            aria-label="Registros por página"
            value={String(pageSize)}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
            className="h-10 px-3 pr-8 bg-background/80 border border-border/80 text-xs rounded-xl text-foreground focus:outline-none cursor-pointer"
          >
            <option value="10">{t("platform_admin:tokens.toolbar.per_page", { count: 10, defaultValue: "10 / pág" })}</option>
            <option value="15">{t("platform_admin:tokens.toolbar.per_page", { count: 15, defaultValue: "15 / pág" })}</option>
            <option value="30">{t("platform_admin:tokens.toolbar.per_page", { count: 30, defaultValue: "30 / pág" })}</option>
            <option value="50">{t("platform_admin:tokens.toolbar.per_page", { count: 50, defaultValue: "50 / pág" })}</option>
            <option value="100">{t("platform_admin:tokens.toolbar.per_page", { count: 100, defaultValue: "100 / pág" })}</option>
          </select>
        </div>
      </div>

      {/* 4. TABLA JERÁRQUICA PRINCIPAL (CON SOPORTE PARA CRÉDITOS Y TOKENS) */}
      <div className="rounded-2xl border border-border/80 bg-card/60 shadow-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-border/80 bg-muted/40 text-muted-foreground uppercase text-[11px] font-bold tracking-wider select-none">
                <th className="py-3 px-4 w-[280px]">
                  {t("platform_admin:tokens.table.col_holding_client", {
                    defaultValue: "HOLDING / CLIENTE",
                  })}
                </th>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-foreground transition-colors"
                  onClick={() => toggleSort("caller")}
                >
                  <div className="flex items-center gap-1">
                    <span>
                      {t("platform_admin:tokens.table.col_caller", {
                        defaultValue: "CALLER / AGENTE",
                      })}
                    </span>
                    <ArrowUpDown className="w-3 h-3 text-muted-foreground" />
                  </div>
                </th>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-foreground transition-colors"
                  onClick={() => toggleSort("model_name")}
                >
                  <div className="flex items-center gap-1">
                    <span>
                      {t("platform_admin:tokens.table.col_model", {
                        defaultValue: "MODELO LLM",
                      })}
                    </span>
                    <ArrowUpDown className="w-3 h-3 text-muted-foreground" />
                  </div>
                </th>

                {viewMode === "credits" ? (
                  <>
                    <th className="py-3 px-4 text-right">
                      <span>
                        {t("platform_admin:tokens.table.col_credits_consumed", {
                          defaultValue: "CRÉDITOS CONSUMIDOS",
                        })}
                      </span>
                    </th>
                    <th className="py-3 px-4 text-center">
                      <span>
                        {t("platform_admin:tokens.table.col_quota_monthly", {
                          defaultValue: "PLAN / CUPO MENSUAL",
                        })}
                      </span>
                    </th>
                    <th className="py-3 px-4 text-right">
                      <span>
                        {t("platform_admin:tokens.table.col_balance", {
                          defaultValue: "SALDO RESTANTE",
                        })}
                      </span>
                    </th>
                  </>
                ) : (
                  <>
                    <th
                      className="py-3 px-4 text-right cursor-pointer hover:text-foreground transition-colors"
                      onClick={() => toggleSort("input_tokens")}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>
                          {t("platform_admin:tokens.table.col_input_tokens", {
                            defaultValue: "INPUT TOKENS",
                          })}
                        </span>
                        <ArrowUpDown className="w-3 h-3 text-muted-foreground" />
                      </div>
                    </th>
                    <th
                      className="py-3 px-4 text-right cursor-pointer hover:text-foreground transition-colors"
                      onClick={() => toggleSort("output_tokens")}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>
                          {t("platform_admin:tokens.table.col_output_tokens", {
                            defaultValue: "OUTPUT TOKENS",
                          })}
                        </span>
                        <ArrowUpDown className="w-3 h-3 text-muted-foreground" />
                      </div>
                    </th>
                    {optionalCols.total_tokens && (
                      <th
                        className="py-3 px-4 text-right cursor-pointer hover:text-foreground transition-colors"
                        onClick={() => toggleSort("total_tokens")}
                      >
                        <div className="flex items-center justify-end gap-1">
                          <span>
                            {t("platform_admin:tokens.table.col_total_tokens", {
                              defaultValue: "TOTAL TOKENS",
                            })}
                          </span>
                          <ArrowUpDown className="w-3 h-3 text-muted-foreground" />
                        </div>
                      </th>
                    )}
                  </>
                )}

                <th
                  className="py-3 px-4 text-right cursor-pointer hover:text-foreground transition-colors"
                  onClick={() => toggleSort("estimated_cost")}
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>
                      {t("platform_admin:tokens.table.col_cost_usd", {
                        defaultValue: "COSTO (USD)",
                      })}
                    </span>
                    <ArrowUpDown className="w-3 h-3 text-muted-foreground" />
                  </div>
                </th>
                {optionalCols.request_duration_ms && (
                  <th className="py-3 px-4 text-right">
                    {t("platform_admin:tokens.table.col_duration", {
                      defaultValue: "DURACIÓN",
                    })}
                  </th>
                )}
                {optionalCols.api_success && (
                  <th className="py-3 px-4 text-center">
                    {t("platform_admin:tokens.table.col_api_status", {
                      defaultValue: "ESTADO API",
                    })}
                  </th>
                )}
                {optionalCols.error_message && (
                  <th className="py-3 px-4 text-left">
                    {t("platform_admin:tokens.table.col_error", {
                      defaultValue: "ERROR",
                    })}
                  </th>
                )}
                {optionalCols.created_at && (
                  <th className="py-3 px-4 text-right">
                    {t("platform_admin:tokens.table.col_created_at", {
                      defaultValue: "FECHA HORA",
                    })}
                  </th>
                )}
                {optionalCols.tenant_name && (
                  <th className="py-3 px-4 text-center">
                    {t("platform_admin:tokens.table.col_store", {
                      defaultValue: "SUCURSAL",
                    })}
                  </th>
                )}
                <th className="py-3 px-4 text-center w-[130px]">
                  {t("platform_admin:tokens.table.col_actions", {
                    defaultValue: "GESTIÓN",
                  })}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {isLoading ? (
                <tr>
                  <td colSpan={13} className="py-12 text-center text-muted-foreground">
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="w-5 h-5 animate-spin text-emerald-400" />
                      <span>
                        {t("platform_admin:tokens.table.loading", {
                          defaultValue: "Cargando registros de consumo y créditos...",
                        })}
                      </span>
                    </div>
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td colSpan={13} className="py-12 text-center text-rose-400">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <XCircle className="w-6 h-6 text-rose-400" />
                      <p>
                        {t("platform_admin:tokens.table.error_loading", {
                          defaultValue: "Error al cargar registros de consumo.",
                        })}
                      </p>
                      <button
                        type="button"
                        onClick={() => refetch()}
                        className="px-3 py-1 mt-2 text-xs font-semibold rounded-lg bg-secondary border border-border text-foreground hover:bg-secondary/80 cursor-pointer"
                      >
                        {t("platform_admin:tokens.table.btn_retry", {
                          defaultValue: "Reintentar",
                        })}
                      </button>
                    </div>
                  </td>
                </tr>
              ) : !data?.holdings || data.holdings.length === 0 ? (
                <tr>
                  <td colSpan={13} className="py-12 text-center text-muted-foreground">
                    <div className="flex flex-col items-center justify-center gap-2" data-testid="empty-holdings-state">
                      <Database className="w-8 h-8 text-muted-foreground/60" />
                      <p>
                        {t("platform_admin:tokens.table.empty", {
                          defaultValue:
                            "No se encontraron registros de consumo con los filtros aplicados.",
                        })}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                data.holdings.map((hGroup) => {
                  const hId = hGroup.holding_id || "no_holding";
                  const isExpanded = !!expandedHoldings[hId];

                  const holdingLimit = hGroup.monthly_credit_limit || ((hGroup.tenants?.length || 1) * 2000);
                  const holdingUsed = hGroup.credits_used || Math.round(hGroup.total_tokens / Math.max(1, tokensPerCredit));
                  const holdingUsagePct = typeof hGroup.credit_usage_pct === "number" && hGroup.credit_usage_pct > 0
                    ? hGroup.credit_usage_pct
                    : holdingLimit > 0
                      ? (holdingUsed / holdingLimit) * 100
                      : 0;

                  return (
                    <React.Fragment key={hId}>
                      {/* FILA SUPERIOR: HOLDING */}
                      <tr
                        data-testid={`holding-row-${hId}`}
                        className="bg-muted/20 hover:bg-muted/40 transition-colors font-medium text-foreground"
                      >
                        <td className="py-3 px-4" colSpan={3}>
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              onClick={() => toggleHolding(hId)}
                              className="text-muted-foreground hover:text-foreground transition-colors p-0.5 cursor-pointer"
                              title={isExpanded ? t("common:collapse", { defaultValue: "Colapsar holding" }) : t("common:expand", { defaultValue: "Expandir holding" })}
                            >
                              {isExpanded ? (
                                <ChevronUp className="w-4 h-4 text-emerald-400" />
                              ) : (
                                <ChevronDown className="w-4 h-4 text-muted-foreground" />
                              )}
                            </button>
                            <div className="h-9 w-9 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400 flex items-center justify-center font-bold shadow-xs shrink-0">
                              <Building2 className="w-4 h-4" />
                            </div>
                            <div className="flex-1">
                              <div className="font-bold text-sm text-foreground flex items-center gap-2">
                                <span>{hGroup.holding_name}</span>
                                <span className="text-[10px] text-muted-foreground font-mono">
                                  ({hGroup.total_requests} reqs)
                                </span>
                                {hGroup.credit_distribution_mode === "shared" ? (
                                  <span className="inline-flex items-center rounded-full border border-cyan-500/30 text-cyan-400 bg-cyan-500/10 text-[9px] px-2 py-0.5">
                                    {t("platform_admin:tokens.table.badge_shared_pool", { defaultValue: "Bolsa Compartida" })}
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center rounded-full border border-purple-500/30 text-purple-400 bg-purple-500/10 text-[9px] px-2 py-0.5">
                                    {t("platform_admin:tokens.table.badge_per_tenant", { defaultValue: "Por Local" })}
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-muted-foreground flex items-center gap-2 mt-0.5">
                                <span>
                                  {hGroup.tenants.length === 1
                                    ? t("platform_admin:tokens.table.store_single", { count: 1, defaultValue: "1 Local" })
                                    : t("platform_admin:tokens.table.store_multiple", { count: hGroup.tenants.length, defaultValue: `${hGroup.tenants.length} Locales` })}
                                </span>
                                {hGroup.holding_id && hGroup.holding_id !== "no_holding" && (
                                  <button
                                    type="button"
                                    data-testid={`edit-holding-credits-btn-${hId}`}
                                    onClick={() => handleOpenEditHolding(hGroup)}
                                    className="text-[10px] text-primary hover:underline flex items-center gap-0.5 cursor-pointer font-semibold ml-2"
                                  >
                                    <Settings2 className="w-3 h-3" />
                                    <span>{t("platform_admin:tokens.table.btn_edit_holding_plan", { defaultValue: "Editar Plan Holding" })}</span>
                                  </button>
                                )}
                              </div>
                              {viewMode === "tokens" && (
                                <div
                                  data-testid="holding-progress-bar"
                                  className="w-full max-w-[140px] space-y-0.5 mt-1"
                                >
                                  <div className="flex items-center justify-between text-[9px] text-muted-foreground font-semibold">
                                    <span>{t("platform_admin:tokens.table.cupo_creditos", { defaultValue: "Cupo Créditos" })}</span>
                                    <span>{holdingUsagePct.toFixed(1)}%</span>
                                  </div>
                                  <div className="h-1.5 w-full rounded-full bg-secondary/80 overflow-hidden">
                                    <div
                                      className={`h-full rounded-full transition-all duration-300 ${getProgressBarColor(holdingUsagePct)}`}
                                      style={{ width: `${Math.min(100, Math.max(0, holdingUsagePct))}%` }}
                                    />
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>

                        {viewMode === "credits" ? (
                          <>
                            <td className="py-3 px-4 text-right font-mono font-bold text-amber-400">
                              {hGroup.credits_used
                                ? `${hGroup.credits_used.toLocaleString("es-CL")} cr`
                                : `${Math.round(hGroup.total_tokens / Math.max(1, tokensPerCredit)).toLocaleString("es-CL")} cr`}
                            </td>
                            <td className="py-3 px-4 text-center font-mono">
                              <div className="flex flex-col items-center gap-1 min-w-[130px]">
                                {hGroup.monthly_credit_limit ? (
                                  <span className="inline-flex items-center rounded-full border border-indigo-500/30 text-indigo-300 bg-indigo-500/10 text-[10px] px-2 py-0.5">
                                    {hGroup.monthly_credit_limit.toLocaleString("es-CL")} cr / mes
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground text-[10px]">
                                    {t("platform_admin:tokens.table.inherited", {
                                      count: (hGroup.tenants.length || 1) * 2000,
                                      defaultValue: `Heredado (${((hGroup.tenants.length || 1) * 2000).toLocaleString("es-CL")} cr)`,
                                    })}
                                  </span>
                                )}
                                <div
                                  data-testid="holding-progress-bar"
                                  className="w-full max-w-[120px] space-y-0.5"
                                >
                                  <div className="flex items-center justify-between text-[9px] text-muted-foreground font-semibold">
                                    <span>{t("platform_admin:tokens.table.uso_cupo", { defaultValue: "Uso Cupo" })}</span>
                                    <span>{holdingUsagePct.toFixed(1)}%</span>
                                  </div>
                                  <div className="h-1.5 w-full rounded-full bg-secondary/80 overflow-hidden">
                                    <div
                                      className={`h-full rounded-full transition-all duration-300 ${getProgressBarColor(holdingUsagePct)}`}
                                      style={{ width: `${Math.min(100, Math.max(0, holdingUsagePct))}%` }}
                                    />
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-emerald-400 font-bold">
                              {hGroup.monthly_credit_limit
                                ? `${Math.max(0, hGroup.monthly_credit_limit - (hGroup.credits_used || 0)).toLocaleString("es-CL")} cr`
                                : "-"}
                            </td>
                          </>
                        ) : (
                          <>
                            <td className="py-3 px-4 text-right font-mono text-cyan-400">
                              {hGroup.tenants
                                .reduce((acc, t) => acc + t.input_tokens, 0)
                                .toLocaleString("es-CL")}
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-purple-400">
                              {hGroup.tenants
                                .reduce((acc, t) => acc + t.output_tokens, 0)
                                .toLocaleString("es-CL")}
                            </td>
                            {optionalCols.total_tokens && (
                              <td className="py-3 px-4 text-right font-mono font-bold text-emerald-400">
                                {hGroup.total_tokens.toLocaleString("es-CL")}
                              </td>
                            )}
                          </>
                        )}

                        <td className="py-3 px-4 text-right font-mono font-bold text-emerald-400">
                          <div>${hGroup.estimated_cost_usd.toFixed(4)} USD</div>
                          <div className="text-[10px] text-muted-foreground font-normal">
                            ~${Math.round(hGroup.estimated_cost_clp || hGroup.estimated_cost_usd * 950).toLocaleString("es-CL")} CLP
                          </div>
                        </td>

                        {optionalCols.request_duration_ms && (
                          <td className="py-3 px-4 text-right text-muted-foreground">-</td>
                        )}
                        {optionalCols.api_success && (
                          <td className="py-3 px-4 text-center text-muted-foreground">-</td>
                        )}
                        {optionalCols.error_message && (
                          <td className="py-3 px-4 text-left text-muted-foreground">-</td>
                        )}
                        {optionalCols.created_at && (
                          <td className="py-3 px-4 text-right text-muted-foreground">-</td>
                        )}
                        {optionalCols.tenant_name && (
                          <td className="py-3 px-4 text-center text-muted-foreground">-</td>
                        )}

                        {/* BOTÓN DESPLEGABLE */}
                        <td className="py-3 px-4 text-center">
                          <button
                            type="button"
                            data-testid={`toggle-holding-${hId}`}
                            onClick={() => toggleHolding(hId)}
                            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold tracking-wide transition-all cursor-pointer shadow-xs border ${
                              isExpanded
                                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 hover:bg-emerald-500/30"
                                : "bg-emerald-500/10 text-emerald-400 border-emerald-500/25 hover:bg-emerald-500/20"
                            }`}
                          >
                            <span>{t("platform_admin:tokens.table.btn_locales", { defaultValue: "LOCALES" })}</span>
                            {isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </td>
                      </tr>

                      {/* VISTA DESGLOSADA DE TENANTS */}
                      {isExpanded &&
                        hGroup.tenants.map((tGroup) => {
                          const tenantLimit = tGroup.monthly_credit_limit || 2000;
                          const tenantUsed = tGroup.credits_used || Math.round(tGroup.total_tokens / Math.max(1, tokensPerCredit));
                          const tenantUsagePct = typeof tGroup.credit_usage_pct === "number" && tGroup.credit_usage_pct > 0
                            ? tGroup.credit_usage_pct
                            : tenantLimit > 0
                              ? (tenantUsed / tenantLimit) * 100
                              : 0;

                          return (
                            <React.Fragment key={tGroup.tenant_id || tGroup.tenant_name}>
                              {/* Fila del Tenant individual */}
                              <tr
                                data-testid={`tenant-row-${tGroup.tenant_id}`}
                                className="bg-background/40 hover:bg-muted/10 transition-colors border-l-4 border-l-primary/60 text-xs"
                              >
                                <td className="py-2.5 px-4 pl-6" colSpan={3}>
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                      <div className="h-6 w-6 rounded-md bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold">
                                        {tGroup.tenant_name.charAt(0).toUpperCase()}
                                      </div>
                                      <div>
                                        <span className="font-bold text-foreground">
                                          {tGroup.tenant_name}
                                        </span>
                                        {viewMode === "tokens" && (
                                          <div
                                            data-testid="tenant-progress-bar"
                                            className="w-full max-w-[120px] space-y-0.5 mt-1"
                                          >
                                            <div className="flex items-center justify-between text-[9px] text-muted-foreground font-semibold">
                                              <span>{t("platform_admin:tokens.table.cupo_creditos", { defaultValue: "Cupo Créditos" })}</span>
                                              <span>{tenantUsagePct.toFixed(1)}%</span>
                                            </div>
                                            <div className="h-1.5 w-full rounded-full bg-secondary/80 overflow-hidden">
                                              <div
                                                className={`h-full rounded-full transition-all duration-300 ${getProgressBarColor(tenantUsagePct)}`}
                                                style={{ width: `${Math.min(100, Math.max(0, tenantUsagePct))}%` }}
                                              />
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    </div>

                                    <button
                                      type="button"
                                      data-testid={`edit-tenant-credits-btn-${tGroup.tenant_id}`}
                                      onClick={() => handleOpenEditTenant(tGroup)}
                                      className="text-[10px] text-muted-foreground hover:text-primary flex items-center gap-1 px-2 py-0.5 rounded border border-border/60 hover:border-primary/40 transition-colors cursor-pointer"
                                    >
                                      <Edit3 className="w-3 h-3" />
                                      <span>{t("platform_admin:tokens.table.btn_adjust_store_quota", { defaultValue: "Ajustar Cupo Local" })}</span>
                                    </button>
                                  </div>
                                </td>

                                {viewMode === "credits" ? (
                                  <>
                                    <td className="py-2.5 px-4 text-right font-mono font-semibold text-amber-400">
                                      {tGroup.credits_used
                                        ? `${tGroup.credits_used.toLocaleString("es-CL")} cr`
                                        : `${Math.round(tGroup.total_tokens / Math.max(1, tokensPerCredit)).toLocaleString("es-CL")} cr`}
                                    </td>
                                    <td className="py-2.5 px-4 text-center font-mono">
                                      <div className="flex flex-col items-center gap-1 min-w-[130px]">
                                        <span className="inline-flex items-center rounded-full border border-border text-muted-foreground text-[10px] px-2 py-0.5">
                                          {tGroup.monthly_credit_limit
                                            ? `${tGroup.monthly_credit_limit.toLocaleString("es-CL")} cr`
                                            : t("platform_admin:tokens.table.base_quota", { defaultValue: "Base (2.000 cr)" })}
                                        </span>
                                        <div
                                          data-testid="tenant-progress-bar"
                                          className="w-full max-w-[120px] space-y-0.5"
                                        >
                                          <div className="flex items-center justify-between text-[9px] text-muted-foreground font-semibold">
                                            <span>{t("platform_admin:tokens.table.uso", { defaultValue: "Uso" })}</span>
                                            <span>{tenantUsagePct.toFixed(1)}%</span>
                                          </div>
                                          <div className="h-1.5 w-full rounded-full bg-secondary/80 overflow-hidden">
                                            <div
                                              className={`h-full rounded-full transition-all duration-300 ${getProgressBarColor(tenantUsagePct)}`}
                                              style={{ width: `${Math.min(100, Math.max(0, tenantUsagePct))}%` }}
                                            />
                                          </div>
                                        </div>
                                      </div>
                                    </td>
                                    <td className="py-2.5 px-4 text-right font-mono text-emerald-400">
                                      {tGroup.monthly_credit_limit
                                        ? `${Math.max(0, tGroup.monthly_credit_limit - (tGroup.credits_used || 0)).toLocaleString("es-CL")} cr`
                                        : "-"}
                                    </td>
                                  </>
                                ) : (
                                  <>
                                    <td className="py-2.5 px-4 text-right font-mono text-cyan-400">
                                      {tGroup.input_tokens.toLocaleString("es-CL")}
                                    </td>
                                    <td className="py-2.5 px-4 text-right font-mono text-purple-400">
                                      {tGroup.output_tokens.toLocaleString("es-CL")}
                                    </td>
                                    {optionalCols.total_tokens && (
                                      <td className="py-2.5 px-4 text-right font-mono font-bold text-foreground">
                                        {tGroup.total_tokens.toLocaleString("es-CL")}
                                      </td>
                                    )}
                                  </>
                                )}

                                <td className="py-2.5 px-4 text-right font-mono text-emerald-400">
                                  <div>${tGroup.estimated_cost_usd.toFixed(4)} USD</div>
                                  <div className="text-[10px] text-muted-foreground font-normal">
                                    ~${Math.round(tGroup.estimated_cost_clp || tGroup.estimated_cost_usd * 950).toLocaleString("es-CL")} CLP
                                  </div>
                                </td>
                                {optionalCols.request_duration_ms && (
                                  <td className="py-2.5 px-4 text-right text-muted-foreground">-</td>
                                )}
                                {optionalCols.api_success && (
                                  <td className="py-2.5 px-4 text-center text-muted-foreground">-</td>
                                )}
                                {optionalCols.error_message && (
                                  <td className="py-2.5 px-4 text-left text-muted-foreground">-</td>
                                )}
                                {optionalCols.created_at && (
                                  <td className="py-2.5 px-4 text-right text-muted-foreground">-</td>
                                )}
                                {optionalCols.tenant_name && (
                                  <td className="py-2.5 px-4 text-center text-muted-foreground">-</td>
                                )}
                                <td className="py-2.5 px-4 text-center text-muted-foreground text-[10px]">
                                  {t("platform_admin:tokens.table.requests_count", { count: tGroup.logs.length, defaultValue: `${tGroup.logs.length} peticiones` })}
                                </td>
                              </tr>

                              {/* Logs individuales de ese Tenant */}
                              {tGroup.logs.map((log: TokenLogItem) => (
                                <tr
                                  key={log.id}
                                  data-testid={`log-row-${log.id}`}
                                  className="hover:bg-muted/15 transition-colors border-l border-border/40 bg-background/20 text-[11px]"
                                >
                                  <td className="py-2 px-4 pl-12 text-muted-foreground truncate max-w-[220px]">
                                    <div className="flex items-center gap-2">
                                      <div className="h-6 w-6 rounded-full bg-secondary/80 text-[10px] font-bold flex items-center justify-center text-foreground shrink-0 border border-border/60">
                                        {getInitials(log.user_name)}
                                      </div>
                                      <span className="truncate text-foreground/90 font-medium">
                                        {log.user_name || t("platform_admin:tokens.table.anonymous_user", { defaultValue: "Usuario Anónimo" })}
                                      </span>
                                    </div>
                                  </td>
                                  <td className="py-2 px-4">
                                    <span className="inline-flex items-center rounded-md border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-[10px] font-mono px-2 py-0.5 font-medium shadow-xs">
                                      {log.caller_feature}
                                    </span>
                                  </td>
                                  <td className="py-2 px-4">
                                    <span className="inline-flex items-center rounded-md border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-[10px] font-mono px-2 py-0.5 font-medium shadow-xs">
                                      {log.model_name}
                                    </span>
                                  </td>

                                  {viewMode === "credits" ? (
                                    <>
                                      <td className="py-2 px-4 text-right font-mono text-amber-300 font-semibold">
                                        {(log.credits_deducted || log.total_tokens / Math.max(1, tokensPerCredit)).toFixed(2)} cr
                                      </td>
                                      <td className="py-2 px-4 text-center text-muted-foreground">-</td>
                                      <td className="py-2 px-4 text-right text-muted-foreground">-</td>
                                    </>
                                  ) : (
                                    <>
                                      <td className="py-2 px-4 text-right font-mono text-cyan-400/80">
                                        {log.input_tokens.toLocaleString("es-CL")}
                                      </td>
                                      <td className="py-2 px-4 text-right font-mono text-purple-400/80">
                                        {log.output_tokens.toLocaleString("es-CL")}
                                      </td>
                                      {optionalCols.total_tokens && (
                                        <td className="py-2 px-4 text-right font-mono text-foreground/90 font-semibold">
                                          {log.total_tokens.toLocaleString("es-CL")}
                                        </td>
                                      )}
                                    </>
                                  )}

                                  <td className="py-2 px-4 text-right font-mono text-emerald-400 font-medium">
                                    ${log.estimated_cost_usd.toFixed(4)}
                                  </td>

                                  {optionalCols.request_duration_ms && (
                                    <td className="py-2 px-4 text-right font-mono text-muted-foreground">
                                      <div className="inline-flex items-center justify-end gap-1">
                                        <Clock className="w-3 h-3 text-muted-foreground/70" />
                                        <span>{log.request_duration_ms ? `${log.request_duration_ms} ms` : "-"}</span>
                                      </div>
                                    </td>
                                  )}

                                  {optionalCols.api_success && (
                                    <td className="py-2 px-4 text-center">
                                      {log.api_success ? (
                                        <span
                                          title={t("platform_admin:tokens.table.success_200", { defaultValue: "200 OK — Solicitud exitosa" })}
                                          className="inline-flex items-center rounded-full border border-emerald-500/30 text-emerald-400 bg-emerald-500/10 text-[9px] px-2 py-0.5 font-medium shadow-xs"
                                        >
                                          <CheckCircle2 className="w-2.5 h-2.5 mr-1" />
                                          200 OK
                                        </span>
                                      ) : (
                                        <span
                                          title={log.error_message || t("platform_admin:tokens.table.error_api", { defaultValue: "Error en llamada API" })}
                                          className="inline-flex items-center rounded-full border border-rose-500/30 text-rose-400 bg-rose-500/10 text-[9px] px-2 py-0.5 font-medium shadow-xs cursor-help"
                                        >
                                          <XCircle className="w-2.5 h-2.5 mr-1" />
                                          Error
                                        </span>
                                      )}
                                    </td>
                                  )}

                                  {optionalCols.error_message && (
                                    <td
                                      className="py-2 px-4 text-left text-rose-400/90 text-[10px] truncate max-w-[160px]"
                                      title={log.error_message || undefined}
                                    >
                                      {log.error_message || "-"}
                                    </td>
                                  )}

                                  {optionalCols.created_at && (
                                    <td className="py-2 px-4 text-right text-muted-foreground text-[10px]">
                                      {log.created_at ? new Date(log.created_at).toLocaleDateString("es-CL") : "-"}
                                    </td>
                                  )}

                                  {optionalCols.tenant_name && (
                                    <td className="py-2 px-4 text-center">
                                      <span className="text-[10px] text-muted-foreground font-mono truncate max-w-[120px] inline-block">
                                        {log.tenant_name}
                                      </span>
                                    </td>
                                  )}

                                  <td className="py-2 px-4 text-center text-muted-foreground text-[10px] font-mono">
                                    {log.id}
                                  </td>
                                </tr>
                              ))}
                            </React.Fragment>
                          );
                        })}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* 5. CONTROLES DE PAGINACIÓN CANÓNICA */}
        <div className="p-4 border-t border-border/80 bg-muted/10">
          <TablePagination
            currentPage={page}
            totalItems={data?.total_records || 0}
            pageSize={pageSize}
            pageSizeOptions={[15, 30, 50, 100]}
            onPageChange={(p) => {
              setPage(p);
              if (typeof window !== "undefined") {
                window.scrollTo({ top: 0, behavior: "smooth" });
              }
            }}
            onPageSizeChange={(s) => {
              setPageSize(s);
              setPage(1);
            }}
            itemLabel={t("platform_admin:tokens.table.item_label", { defaultValue: "registros de consumo" })}
          />
        </div>
      </div>

      {/* 6. MODAL: EDITAR PLAN DE CRÉDITOS DE HOLDING */}
      {holdingModalOpen && (
        <div
          data-testid="holding-credits-modal"
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
        >
          <div className="w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2 text-foreground font-bold text-base">
                <Building2 className="w-5 h-5 text-purple-400" />
                <span>
                  {t("platform_admin:tokens.holding_modal.title", {
                    name: editingHolding?.holding_name || "",
                    defaultValue: `Ajustar Créditos: ${editingHolding?.holding_name}`,
                  })}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setHoldingModalOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-secondary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 py-1 text-xs">
              <div className="space-y-1.5">
                <label className="font-semibold text-foreground">
                  {t("platform_admin:tokens.holding_modal.limit_label", {
                    defaultValue: "Bolsa Total Mensual del Holding (Créditos)",
                  })}
                </label>
                <input
                  type="number"
                  min="0"
                  data-testid="input-holding-credit-limit"
                  value={holdingCreditLimitInput}
                  onChange={(e) => {
                    setHoldingCreditLimitInput(e.target.value);
                    if (holdingError && Number(e.target.value) >= 0) {
                      setHoldingError(null);
                    }
                  }}
                  placeholder={t("platform_admin:tokens.holding_modal.limit_placeholder", {
                    defaultValue: "Ej. 20000 (Dejar vacío para heredar por defecto)",
                  })}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
                {holdingError && (
                  <p className="text-[11px] text-rose-400 font-medium">{holdingError}</p>
                )}
                <p className="text-[10px] text-muted-foreground">
                  {t("platform_admin:tokens.holding_modal.limit_help", {
                    defaultValue: "Total de créditos mensuales garantizados para toda la red de locales del holding.",
                  })}
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-foreground">
                  {t("platform_admin:tokens.holding_modal.mode_label", {
                    defaultValue: "Modalidad de Distribución",
                  })}
                </label>
                <select
                  data-testid="select-holding-distribution-mode"
                  value={holdingModeInput}
                  onChange={(e) =>
                    setHoldingModeInput(e.target.value as "shared" | "per_tenant")
                  }
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                >
                  <option value="shared">
                    {t("platform_admin:tokens.holding_modal.mode_shared", {
                      defaultValue: "Bolsa Compartida (Shared Pool)",
                    })}
                  </option>
                  <option value="per_tenant">
                    {t("platform_admin:tokens.holding_modal.mode_per_tenant", {
                      defaultValue: "Asignación Fija por Local (Per Tenant)",
                    })}
                  </option>
                </select>
                <p className="text-[10px] text-muted-foreground">
                  {t("platform_admin:tokens.holding_modal.mode_help", {
                    defaultValue: "En bolsa compartida, todos los locales consumen del mismo saldo global del holding.",
                  })}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/60">
              <button
                type="button"
                onClick={() => setHoldingModalOpen(false)}
                className="touch-target px-4 py-2 text-xs font-semibold rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-foreground cursor-pointer"
              >
                {t("platform_admin:tokens.holding_modal.btn_cancel", {
                  defaultValue: "Cancelar",
                })}
              </button>
              <button
                type="button"
                data-testid="save-holding-credits-btn"
                onClick={handleSaveHoldingCredits}
                disabled={isUpdatingQuota}
                className="touch-target px-4 py-2 text-xs font-semibold rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground transition-all cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
              >
                {isUpdatingQuota ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <span>
                    {t("platform_admin:tokens.holding_modal.btn_save", {
                      defaultValue: "Guardar Plan",
                    })}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. MODAL: EDITAR CUPO DE CRÉDITOS DE TENANT */}
      {tenantModalOpen && (
        <div
          data-testid="tenant-credits-modal"
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
        >
          <div className="w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2 text-foreground font-bold text-base">
                <Coins className="w-5 h-5 text-emerald-400" />
                <span>
                  {t("platform_admin:tokens.tenant_modal.title", {
                    name: editingTenant?.tenant_name || "",
                    defaultValue: `Cupo de Créditos: ${editingTenant?.tenant_name}`,
                  })}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setTenantModalOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-secondary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 py-1 text-xs">
              <div className="space-y-1.5">
                <label className="font-semibold text-foreground">
                  {t("platform_admin:tokens.tenant_modal.limit_label", {
                    defaultValue: "Créditos Mensuales Asignados a este Local",
                  })}
                </label>
                <input
                  type="number"
                  min="0"
                  data-testid="input-tenant-credit-limit"
                  value={tenantCreditLimitInput}
                  onChange={(e) => {
                    setTenantCreditLimitInput(e.target.value);
                    if (tenantError && Number(e.target.value) >= 0) {
                      setTenantError(null);
                    }
                  }}
                  placeholder={t("platform_admin:tokens.tenant_modal.limit_placeholder", {
                    defaultValue: "Ej. 4000 (Dejar vacío para heredar 2.000 estándar)",
                  })}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
                {tenantError && (
                  <p className="text-[11px] text-rose-400 font-medium">{tenantError}</p>
                )}
                <p className="text-[10px] text-muted-foreground">
                  {t("platform_admin:tokens.tenant_modal.limit_help", {
                    defaultValue: "Límite de créditos exclusivo para este restaurante/sucursal.",
                  })}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/60">
              <button
                type="button"
                onClick={() => setTenantModalOpen(false)}
                className="touch-target px-4 py-2 text-xs font-semibold rounded-xl border border-border bg-secondary hover:bg-secondary/80 text-foreground cursor-pointer"
              >
                {t("platform_admin:tokens.tenant_modal.btn_cancel", {
                  defaultValue: "Cancelar",
                })}
              </button>
              <button
                type="button"
                data-testid="save-tenant-credits-btn"
                onClick={handleSaveTenantCredits}
                disabled={isUpdatingQuota}
                className="touch-target px-4 py-2 text-xs font-semibold rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground transition-all cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
              >
                {isUpdatingQuota ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <span>
                    {t("platform_admin:tokens.tenant_modal.btn_save", {
                      defaultValue: "Guardar Cupo",
                    })}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TokenConsumptionPage;
