import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Coins,
  Cpu,
  Database,
  DollarSign,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Store,
  TrendingDown,
  X,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { TablePagination } from "@/shared/components/ui/TablePagination";
import { useJevConsumption } from "../hooks/useJevConsumption";

export interface OptionalJevColumnsConfig {
  readonly trace_id: boolean;
  readonly caller_feature: boolean;
  readonly primitive: boolean;
  readonly latency: boolean;
  readonly confidence: boolean;
  readonly cost: boolean;
  readonly model_name: boolean;
  readonly tenant_name: boolean;
}

export const DEFAULT_OPTIONAL_JEV_COLUMNS: OptionalJevColumnsConfig = {
  trace_id: false,
  caller_feature: true,
  primitive: true,
  latency: true,
  confidence: true,
  cost: true,
  model_name: true,
  tenant_name: true,
};

const STORAGE_KEY_JEV_COLS = "oppy_jev_consumption_cols";

export function JevConsumptionPage() {
  const { t } = useTranslation(["platform_admin", "common"]);

  const {
    holdings,
    tenants,
    logs,
    totalDecisionsAll,
    totalCostUsdAll,
    totalCostClpAll,
    avgLatencyMsAll,
    totalAutoAcceptedAll,
    totalFlaggedWarningAll,
    totalFallbackLlmAll,
    estimatedSavingsUsdAll,
    estimatedSavingsClpAll,
    isLoading,
    refetch,
    viewMode,
    setViewMode,
    page,
    setPage,
    pageSize,
    setPageSize,
    search,
    setSearch,
    callerFeature,
    setCallerFeature,
    decisionPrimitive,
    setDecisionPrimitive,
    calibratedAction,
    setCalibratedAction,
  } = useJevConsumption();

  // Popover de Columnas Opcionales
  const [showColumnsPopover, setShowColumnsPopover] = useState<boolean>(false);
  const columnsPopoverRef = useRef<HTMLDivElement>(null);

  // Columnas Opcionales con persistencia en localStorage
  const [optionalCols, setOptionalCols] = useState<OptionalJevColumnsConfig>(() => {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        const saved = window.localStorage.getItem(STORAGE_KEY_JEV_COLS);
        if (saved) {
          return { ...DEFAULT_OPTIONAL_JEV_COLUMNS, ...JSON.parse(saved) };
        }
      }
    } catch {
      // Ignorar error de lectura de localStorage
    }
    return DEFAULT_OPTIONAL_JEV_COLUMNS;
  });

  const saveOptionalCols = (newCols: OptionalJevColumnsConfig) => {
    setOptionalCols(newCols);
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem(STORAGE_KEY_JEV_COLS, JSON.stringify(newCols));
      }
    } catch {
      // Ignorar error de escritura
    }
  };

  // Desplegables de Holding abiertos
  const [expandedHoldings, setExpandedHoldings] = useState<Record<string, boolean>>({});

  // Expandir primer holding por defecto para mejor UX
  useEffect(() => {
    if (holdings && holdings.length > 0) {
      const firstHId = holdings[0]?.holding_id || "no_holding";
      setExpandedHoldings((prev) => {
        if (Object.keys(prev).length === 0) {
          return { [firstHId]: true };
        }
        return prev;
      });
    }
  }, [holdings]);

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

  const handleRefresh = async () => {
    try {
      await refetch();
      toast.success(
        t("platform_admin:jev.toolbar.refreshed", {
          defaultValue: "Telemetría y decisiones JEV actualizadas",
        })
      );
    } catch {
      toast.error(
        t("platform_admin:jev.toolbar.error_refresh", {
          defaultValue: "Error al refrescar decisiones JEV",
        })
      );
    }
  };

  // Cálculo de Porcentajes de Calibración
  const totalDecisionsForPct = Math.max(1, totalDecisionsAll);
  const autoAcceptedPct = ((totalAutoAcceptedAll / totalDecisionsForPct) * 100).toFixed(1);
  const flaggedWarningPct = ((totalFlaggedWarningAll / totalDecisionsForPct) * 100).toFixed(1);
  const fallbackLlmPct = ((totalFallbackLlmAll / totalDecisionsForPct) * 100).toFixed(1);

  // Filtrado local reactivo para complementar mock/live data
  const filteredHoldings = useMemo(() => {
    if (!search.trim()) return holdings;
    const q = search.toLowerCase();
    return holdings.filter(
      (h) =>
        h.holding_name.toLowerCase().includes(q) ||
        h.holding_id.toLowerCase().includes(q) ||
        h.tenants.some(
          (t) =>
            t.tenant_name.toLowerCase().includes(q) ||
            t.tenant_schema.toLowerCase().includes(q)
        )
    );
  }, [holdings, search]);

  const filteredTenants = useMemo(() => {
    let list = tenants;
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (t) =>
          t.tenant_name.toLowerCase().includes(q) ||
          t.tenant_schema.toLowerCase().includes(q) ||
          t.tenant_id.toLowerCase().includes(q)
      );
    }
    return list;
  }, [tenants, search]);

  const filteredLogs = useMemo(() => {
    let list = logs;
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (l) =>
          l.tenant_name.toLowerCase().includes(q) ||
          l.holding_name.toLowerCase().includes(q) ||
          l.caller_feature.toLowerCase().includes(q) ||
          l.decision_primitive.toLowerCase().includes(q) ||
          l.decision_id.toLowerCase().includes(q) ||
          l.input_summary.toLowerCase().includes(q) ||
          l.result_value.toLowerCase().includes(q)
      );
    }
    if (callerFeature && callerFeature !== "all") {
      list = list.filter((l) => l.caller_feature === callerFeature);
    }
    if (decisionPrimitive && decisionPrimitive !== "all") {
      list = list.filter((l) => l.decision_primitive === decisionPrimitive);
    }
    if (calibratedAction && calibratedAction !== "all") {
      const actNorm = calibratedAction.toUpperCase();
      list = list.filter((l) => l.calibrated_action.toUpperCase() === actNorm);
    }
    return list;
  }, [logs, search, callerFeature, decisionPrimitive, calibratedAction]);

  // Paginación local de logs
  const paginatedLogs = useMemo(() => {
    const startIndex = (page - 1) * pageSize;
    return filteredLogs.slice(startIndex, startIndex + pageSize);
  }, [filteredLogs, page, pageSize]);

  const renderActionBadge = (action: string) => {
    const upper = action.toUpperCase();
    if (upper.includes("AUTO") || upper.includes("ACCEPT")) {
      return (
        <span
          data-testid="badge-action-auto-accepted"
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
        >
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          <span>
            {t("platform_admin:jev.badges.auto_accepted", {
              defaultValue: "Auto-Aceptada",
            })}
          </span>
        </span>
      );
    }
    if (upper.includes("WARN") || upper.includes("FLAG")) {
      return (
        <span
          data-testid="badge-action-flagged-warning"
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30"
        >
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          <span>
            {t("platform_admin:jev.badges.flagged_warning", {
              defaultValue: "Advertencia",
            })}
          </span>
        </span>
      );
    }
    return (
      <span
        data-testid="badge-action-fallback-llm"
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30"
      >
        <Sparkles className="w-3 h-3 text-rose-400" />
        <span>
          {t("platform_admin:jev.badges.fallback_llm", {
            defaultValue: "Fallback LLM",
          })}
        </span>
      </span>
    );
  };

  return (
    <div
      data-testid="jev-consumption-page"
      className="p-4 md:p-8 space-y-6 max-w-[1600px] mx-auto animate-in fade-in duration-300"
    >
      {/* 1. CABECERA CANÓNICA */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border/60 pb-6">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-semibold text-xs uppercase tracking-wider mb-1">
            <Zap className="w-4 h-4" />
            <span>
              {t("platform_admin:jev.pretitle", {
                defaultValue: "FinOps & Optimización Sub-Simbólica",
              })}
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground flex flex-wrap items-center gap-3">
            <span>
              {t("platform_admin:jev.title", {
                defaultValue: "Consumo de Decisiones JEV",
              })}
            </span>
            <span
              data-testid="jev-subsymbolic-badge"
              className="inline-flex items-center rounded-full border border-cyan-500/30 text-cyan-400 bg-cyan-500/10 px-2.5 py-1 text-xs font-mono font-medium"
            >
              <Cpu className="w-3 h-3 mr-1" />
              {t("platform_admin:jev.badge_subsymbolic", {
                defaultValue: "Motor JEV Heurístico / Determinista",
              })}
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("platform_admin:jev.subtitle", {
              defaultValue:
                "Telemetría, calibración de confianza y ahorro FinOps por Holding, Sucursal y Bitácora.",
            })}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to="/admin/token-consumption"
            data-testid="token-consumption-link"
            className="touch-target inline-flex min-h-[38px] items-center gap-2 rounded-xl border border-border/80 bg-secondary/60 hover:bg-secondary px-3.5 py-1.5 text-xs font-medium text-foreground transition-colors cursor-pointer"
          >
            <Coins className="w-3.5 h-3.5 text-emerald-400" />
            <span>
              {t("platform_admin:jev.nav.token_consumption", {
                defaultValue: "Consumo Tokens LLM",
              })}
            </span>
          </Link>

          <button
            type="button"
            data-testid="refresh-jev-btn"
            onClick={handleRefresh}
            disabled={isLoading}
            className="touch-target inline-flex min-h-[38px] items-center gap-2 rounded-xl border border-border/80 bg-secondary/60 hover:bg-secondary px-3.5 py-1.5 text-xs font-medium text-foreground transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-cyan-400 ${isLoading ? "animate-spin" : ""}`}
            />
            <span>
              {t("platform_admin:jev.toolbar.btn_refresh", {
                defaultValue: "Actualizar",
              })}
            </span>
          </button>
        </div>
      </div>

      {/* 2. TARJETAS KPI SUPERIORES (HEAD METRICS) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Total de Decisiones JEV */}
        <div
          data-testid="kpi-total-decisions"
          className="p-4 rounded-2xl bg-card/60 border border-border/70 shadow-sm flex items-center justify-between"
        >
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase">
              {t("platform_admin:jev.kpi.total_decisions", {
                defaultValue: "Total de Decisiones JEV",
              })}
            </p>
            <p className="text-2xl font-black text-foreground mt-1">
              {totalDecisionsAll.toLocaleString("es-CL")}
            </p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center">
            <Zap className="w-5 h-5" />
          </div>
        </div>

        {/* KPI 2: Costo Real Proveedor */}
        <div
          data-testid="kpi-real-provider-cost"
          className="p-4 rounded-2xl bg-card/60 border border-border/70 shadow-sm flex items-center justify-between"
        >
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase">
              {t("platform_admin:jev.kpi.real_provider_cost", {
                defaultValue: "Costo Real Proveedor",
              })}
            </p>
            <p className="text-2xl font-black text-emerald-400 mt-1">
              ${Number(totalCostUsdAll).toFixed(4)}{" "}
              <span className="text-xs text-muted-foreground font-normal">
                (~${Math.round(Number(totalCostClpAll) || Number(totalCostUsdAll) * 950).toLocaleString("es-CL")} CLP)
              </span>
            </p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
            <DollarSign className="w-5 h-5" />
          </div>
        </div>

        {/* KPI 3: Latencia Promedio */}
        <div
          data-testid="kpi-avg-latency"
          className="p-4 rounded-2xl bg-card/60 border border-border/70 shadow-sm flex items-center justify-between"
        >
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase">
              {t("platform_admin:jev.kpi.avg_latency", {
                defaultValue: "Latencia Promedio",
              })}
            </p>
            <p className="text-2xl font-black text-indigo-400 mt-1">
              {Number(avgLatencyMsAll).toFixed(1)} ms
            </p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        {/* KPI 4: Calibración de Confianza */}
        <div
          data-testid="kpi-confidence-calibration"
          className="p-4 rounded-2xl bg-card/60 border border-border/70 shadow-sm flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-muted-foreground uppercase">
              {t("platform_admin:jev.kpi.confidence_calibration", {
                defaultValue: "Calibración de Confianza",
              })}
            </p>
            <div className="h-8 w-8 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 space-y-1.5">
            <div className="flex items-center justify-between text-xs font-medium">
              <span className="text-emerald-400 flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                {autoAcceptedPct}% Auto
              </span>
              <span className="text-amber-400 flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-amber-400" />
                {flaggedWarningPct}% Warn
              </span>
              <span className="text-rose-400 flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-rose-400" />
                {fallbackLlmPct}% LLM
              </span>
            </div>
            {/* Barra multi-segmento */}
            <div className="h-2 w-full bg-secondary/80 rounded-full overflow-hidden flex">
              <div
                style={{ width: `${autoAcceptedPct}%` }}
                className="bg-emerald-500 h-full"
                title={`Auto-Aceptadas: ${autoAcceptedPct}%`}
              />
              <div
                style={{ width: `${flaggedWarningPct}%` }}
                className="bg-amber-500 h-full"
                title={`Advertencias: ${flaggedWarningPct}%`}
              />
              <div
                style={{ width: `${fallbackLlmPct}%` }}
                className="bg-rose-500 h-full"
                title={`Fallback LLM: ${fallbackLlmPct}%`}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 3. TARJETA DE AHORRO ESTIMADO FINOPS */}
      <div
        data-testid="finops-savings-card"
        className="p-5 rounded-2xl bg-gradient-to-r from-cyan-950/30 via-card/70 to-card/40 border border-cyan-500/30 shadow-md space-y-3"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 flex items-center justify-center">
              <TrendingDown className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-foreground">
                  {t("platform_admin:jev.kpi.estimated_savings", {
                    defaultValue: "Ahorro Estimado FinOps por Motor JEV Sub-Simbólico",
                  })}
                </h3>
                <span className="inline-flex items-center rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                  {autoAcceptedPct}%{" "}
                  {t("platform_admin:jev.kpi.zero_cost_llm", {
                    defaultValue: "Cero-Costo LLM",
                  })}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("platform_admin:jev.kpi.savings_description", {
                  defaultValue:
                    "Ahorro directo calculado frente al costo alternativo de consultar modelos de lenguaje comerciales.",
                })}
              </p>
            </div>
          </div>

          <div className="text-right">
            <div className="text-2xl font-black font-mono text-cyan-400">
              +${Number(estimatedSavingsUsdAll).toFixed(2)} USD
            </div>
            <div className="text-xs font-mono text-muted-foreground">
              ~+${Math.round(Number(estimatedSavingsClpAll)).toLocaleString("es-CL")} CLP{" "}
              {t("platform_admin:jev.kpi.saved", {
                defaultValue: "ahorrados",
              })}
            </div>
          </div>
        </div>
      </div>

      {/* 4. BARRA DE HERRAMIENTAS, FILTROS Y SELECTOR DE PESTAÑAS (VIEW MODES) */}
      <div className="p-4 rounded-2xl bg-card/40 border border-border/80 shadow-xs space-y-4 md:space-y-0 md:flex md:items-center md:justify-between md:gap-4">
        {/* Buscador reactivo */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            data-testid="jev-consumption-search-input"
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder={t("platform_admin:jev.toolbar.search_placeholder", {
              defaultValue: "Buscar por Holding, Tenant, Decisión, Primitiva o Feature...",
            })}
            className="w-full pl-10 pr-4 py-2 bg-background/80 border border-border/80 focus:border-cyan-500/50 text-sm h-10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
          />
        </div>

        {/* Pestañas de Modo de Vista & Filtros */}
        <div className="flex flex-wrap items-center gap-2">
          {/* PESTAÑAS / VIEW MODES: 'holding' | 'tenant' | 'logs' */}
          <div className="flex items-center p-1 bg-secondary/80 border border-border/80 rounded-xl">
            <button
              type="button"
              data-testid="tab-view-holding"
              onClick={() => setViewMode("holding")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                viewMode === "holding"
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Building2 className="w-3.5 h-3.5" />
              <span>
                {t("platform_admin:jev.tabs.holding", {
                  defaultValue: "Holdings",
                })}
              </span>
            </button>
            <button
              type="button"
              data-testid="tab-view-tenant"
              onClick={() => setViewMode("tenant")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                viewMode === "tenant"
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Store className="w-3.5 h-3.5" />
              <span>
                {t("platform_admin:jev.tabs.tenant", {
                  defaultValue: "Tenants",
                })}
              </span>
            </button>
            <button
              type="button"
              data-testid="tab-view-logs"
              onClick={() => setViewMode("logs")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                viewMode === "logs"
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>
                {t("platform_admin:jev.tabs.logs", {
                  defaultValue: "Bitácora",
                })}
              </span>
            </button>
          </div>

          {/* Filtro por Primitiva */}
          <div className="relative">
            <select
              data-testid="filter-primitive-select"
              aria-label={t("platform_admin:jev.aria.filter_primitive", {
                defaultValue: "Filtro por primitiva JEV",
              })}
              value={decisionPrimitive || "all"}
              onChange={(e) => {
                const val = e.target.value;
                setDecisionPrimitive(val === "all" ? null : val);
                setPage(1);
              }}
              className="h-10 px-3 pr-8 bg-background/80 border border-border/80 text-xs rounded-xl text-foreground focus:outline-none focus:border-cyan-500/50 cursor-pointer"
            >
              <option value="all">
                {t("platform_admin:jev.toolbar.all_primitives", {
                  defaultValue: "Todas las Primitivas",
                })}
              </option>
              <option value="anomaly_score">anomaly_score</option>
              <option value="threshold_gate">threshold_gate</option>
              <option value="cost_optimality">cost_optimality</option>
              <option value="exact_match">exact_match</option>
              <option value="bayesian_filter">bayesian_filter</option>
            </select>
          </div>

          {/* Filtro por Feature */}
          <div className="relative">
            <select
              data-testid="filter-feature-select"
              aria-label={t("platform_admin:jev.aria.filter_feature", {
                defaultValue: "Filtro por feature llamadora",
              })}
              value={callerFeature || "all"}
              onChange={(e) => {
                const val = e.target.value;
                setCallerFeature(val === "all" ? null : val);
                setPage(1);
              }}
              className="h-10 px-3 pr-8 bg-background/80 border border-border/80 text-xs rounded-xl text-foreground focus:outline-none focus:border-cyan-500/50 cursor-pointer"
            >
              <option value="all">
                {t("platform_admin:jev.toolbar.all_features", {
                  defaultValue: "Todas las Features",
                })}
              </option>
              <option value="mermas_detection">mermas_detection</option>
              <option value="demand_prediction">demand_prediction</option>
              <option value="recipe_costing">recipe_costing</option>
              <option value="order_anomaly">order_anomaly</option>
              <option value="inventory_replenishment">inventory_replenishment</option>
            </select>
          </div>

          {/* Filtro por Acción Calibrada */}
          <div className="relative">
            <select
              data-testid="filter-action-select"
              aria-label={t("platform_admin:jev.aria.filter_action", {
                defaultValue: "Filtro por acción calibrada",
              })}
              value={calibratedAction || "all"}
              onChange={(e) => {
                const val = e.target.value;
                setCalibratedAction(val === "all" ? null : val);
                setPage(1);
              }}
              className="h-10 px-3 pr-8 bg-background/80 border border-border/80 text-xs rounded-xl text-foreground focus:outline-none focus:border-cyan-500/50 cursor-pointer"
            >
              <option value="all">
                {t("platform_admin:jev.toolbar.all_actions", {
                  defaultValue: "Todas las Acciones",
                })}
              </option>
              <option value="AUTO_ACCEPTED">
                {t("platform_admin:jev.toolbar.action_auto_accepted", {
                  defaultValue: "✅ Auto-Aceptadas",
                })}
              </option>
              <option value="FLAGGED_WARNING">
                {t("platform_admin:jev.toolbar.action_flagged_warning", {
                  defaultValue: "⚠️ Advertencias",
                })}
              </option>
              <option value="FALLBACK_LLM">
                {t("platform_admin:jev.toolbar.action_fallback_llm", {
                  defaultValue: "🔄 Fallback LLM",
                })}
              </option>
            </select>
          </div>

          {/* Popover de Columnas Opcionales para Bitácora */}
          {viewMode === "logs" && (
            <div className="relative" ref={columnsPopoverRef}>
              <button
                type="button"
                data-testid="toggle-columns-popover-btn"
                onClick={() => setShowColumnsPopover((prev) => !prev)}
                className="touch-target inline-flex min-h-[38px] items-center gap-2 rounded-xl border border-border/80 bg-background/80 hover:bg-secondary px-3 py-2 text-xs font-medium text-foreground transition-colors cursor-pointer"
              >
                <SlidersHorizontal className="w-3.5 h-3.5 text-cyan-400" />
                <span>
                  {t("platform_admin:jev.toolbar.btn_columns", {
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
                      {t("platform_admin:jev.columns.optional_title", {
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
                        checked={optionalCols.trace_id}
                        onChange={(e) =>
                          saveOptionalCols({ ...optionalCols, trace_id: e.target.checked })
                        }
                        className="h-4 w-4 rounded border-border text-cyan-500 focus:ring-cyan-500"
                      />
                      <span className="text-foreground">
                        {t("platform_admin:jev.columns.trace_id", {
                          defaultValue: "Trace ID",
                        })}
                      </span>
                    </label>

                    <label className="flex items-center space-x-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={optionalCols.caller_feature}
                        onChange={(e) =>
                          saveOptionalCols({ ...optionalCols, caller_feature: e.target.checked })
                        }
                        className="h-4 w-4 rounded border-border text-cyan-500 focus:ring-cyan-500"
                      />
                      <span className="text-foreground">
                        {t("platform_admin:jev.columns.caller_feature", {
                          defaultValue: "Caller Feature",
                        })}
                      </span>
                    </label>

                    <label className="flex items-center space-x-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={optionalCols.primitive}
                        onChange={(e) =>
                          saveOptionalCols({ ...optionalCols, primitive: e.target.checked })
                        }
                        className="h-4 w-4 rounded border-border text-cyan-500 focus:ring-cyan-500"
                      />
                      <span className="text-foreground">
                        {t("platform_admin:jev.columns.primitive", {
                          defaultValue: "Primitiva JEV",
                        })}
                      </span>
                    </label>

                    <label className="flex items-center space-x-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={optionalCols.latency}
                        onChange={(e) =>
                          saveOptionalCols({ ...optionalCols, latency: e.target.checked })
                        }
                        className="h-4 w-4 rounded border-border text-cyan-500 focus:ring-cyan-500"
                      />
                      <span className="text-foreground">
                        {t("platform_admin:jev.columns.latency", {
                          defaultValue: "Latencia (ms)",
                        })}
                      </span>
                    </label>

                    <label className="flex items-center space-x-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={optionalCols.cost}
                        onChange={(e) =>
                          saveOptionalCols({ ...optionalCols, cost: e.target.checked })
                        }
                        className="h-4 w-4 rounded border-border text-cyan-500 focus:ring-cyan-500"
                      />
                      <span className="text-foreground">
                        {t("platform_admin:jev.columns.cost", {
                          defaultValue: "Costo USD / CLP",
                        })}
                      </span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 5. VISTA POR PESTAÑA SELECCIONADA */}

      {/* 5.1 PESTAÑA 'holding': Acordeón Desplegable Holding -> Tenants -> Decisiones */}
      {viewMode === "holding" && (
        <div data-testid="jev-holding-view" className="space-y-4">
          {filteredHoldings.length === 0 ? (
            <div
              data-testid="jev-empty-state"
              className="p-12 text-center bg-card/40 rounded-2xl border border-border/80 space-y-2"
            >
              <Building2 className="w-10 h-10 mx-auto text-muted-foreground/60" />
              <h4 className="text-base font-bold text-foreground">
                {t("platform_admin:jev.empty.title", {
                  defaultValue: "No se encontraron registros de decisiones JEV",
                })}
              </h4>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                {t("platform_admin:jev.empty.description", {
                  defaultValue:
                    "Ajusta los filtros de búsqueda o verifica la actividad del motor heurístico determinista.",
                })}
              </p>
            </div>
          ) : (
            filteredHoldings.map((holding) => {
              const isExpanded = expandedHoldings[holding.holding_id] ?? false;
              return (
                <div
                  key={holding.holding_id}
                  data-testid={`holding-card-${holding.holding_id}`}
                  className="rounded-2xl border border-border/80 bg-card/60 shadow-xs overflow-hidden transition-all duration-200"
                >
                  {/* Encabezado del Holding */}
                  <div
                    className="p-4 md:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-secondary/40 select-none"
                    onClick={() => toggleHolding(holding.holding_id)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
                        <Building2 className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-base text-foreground">
                            {holding.holding_name}
                          </h3>
                          <span className="text-[10px] font-mono text-muted-foreground bg-secondary px-2 py-0.5 rounded border border-border">
                            {holding.holding_id}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {holding.tenants.length}{" "}
                          {t("platform_admin:jev.holding.assigned_tenants", {
                            defaultValue: "sucursal(es) adscrita(s)",
                          })}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <span className="text-[11px] uppercase font-semibold text-muted-foreground">
                          {t("platform_admin:jev.metrics.decisions", {
                            defaultValue: "Decisiones",
                          })}
                        </span>
                        <div className="font-mono font-bold text-sm text-foreground">
                          {holding.total_decisions.toLocaleString("es-CL")}
                        </div>
                      </div>

                      <div className="text-right">
                        <span className="text-[11px] uppercase font-semibold text-muted-foreground">
                          {t("platform_admin:jev.metrics.real_cost", {
                            defaultValue: "Costo Real",
                          })}
                        </span>
                        <div className="font-mono font-bold text-sm text-emerald-400">
                          ${Number(holding.total_cost_usd).toFixed(4)} USD
                        </div>
                      </div>

                      <div className="text-right hidden sm:block">
                        <span className="text-[11px] uppercase font-semibold text-muted-foreground">
                          {t("platform_admin:jev.metrics.avg_latency", {
                            defaultValue: "Latencia Prom.",
                          })}
                        </span>
                        <div className="font-mono font-bold text-sm text-indigo-400">
                          {Number(holding.avg_latency_ms).toFixed(1)} ms
                        </div>
                      </div>

                      <button
                        type="button"
                        data-testid={`toggle-holding-${holding.holding_id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleHolding(holding.holding_id);
                        }}
                        className="h-8 w-8 rounded-lg flex items-center justify-center border border-border bg-background hover:bg-secondary text-muted-foreground transition-colors"
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Detalle Acordeón: Tenants adscritos */}
                  {isExpanded && (
                    <div className="p-4 border-t border-border/60 bg-background/40 space-y-3">
                      <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                        {t("platform_admin:jev.holding.tenants_section", {
                          defaultValue: "Sucursales / Tenants",
                        })}
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {holding.tenants.map((tItem) => {
                          const tTotal = Math.max(1, tItem.total_decisions);
                          const tAutoPct = ((tItem.auto_accepted_count / tTotal) * 100).toFixed(1);
                          const tWarnPct = ((tItem.flagged_warning_count / tTotal) * 100).toFixed(1);
                          const tFallPct = ((tItem.fallback_llm_count / tTotal) * 100).toFixed(1);

                          return (
                            <div
                              key={tItem.tenant_id}
                              data-testid={`holding-tenant-${tItem.tenant_id}`}
                              className="p-3.5 rounded-xl border border-border/70 bg-card/70 space-y-2.5"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <Store className="w-4 h-4 text-emerald-400" />
                                  <span className="text-xs font-bold text-foreground">
                                    {tItem.tenant_name}
                                  </span>
                                </div>
                                <span className="text-[10px] font-mono text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
                                  {tItem.tenant_schema}
                                </span>
                              </div>

                              <div className="grid grid-cols-3 gap-2 text-center pt-1 border-t border-border/40">
                                <div>
                                  <span className="text-[10px] text-muted-foreground block">
                                    {t("platform_admin:jev.metrics.decisions", {
                                      defaultValue: "Decisiones",
                                    })}
                                  </span>
                                  <span className="text-xs font-mono font-bold text-foreground">
                                    {tItem.total_decisions.toLocaleString("es-CL")}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-[10px] text-muted-foreground block">
                                    {t("platform_admin:jev.metrics.cost_usd", {
                                      defaultValue: "Costo USD",
                                    })}
                                  </span>
                                  <span className="text-xs font-mono font-bold text-emerald-400">
                                    ${Number(tItem.total_cost_usd).toFixed(4)}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-[10px] text-muted-foreground block">
                                    {t("platform_admin:jev.metrics.latency", {
                                      defaultValue: "Latencia",
                                    })}
                                  </span>
                                  <span className="text-xs font-mono font-bold text-indigo-400">
                                    {Number(tItem.avg_latency_ms).toFixed(1)} ms
                                  </span>
                                </div>
                              </div>

                              {/* Barra de calibración del tenant */}
                              <div className="space-y-1 pt-1">
                                <div className="flex items-center justify-between text-[10px] font-medium text-muted-foreground">
                                  <span className="text-emerald-400">{tAutoPct}% Auto</span>
                                  <span className="text-amber-400">{tWarnPct}% Warn</span>
                                  <span className="text-rose-400">{tFallPct}% LLM</span>
                                </div>
                                <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden flex">
                                  <div
                                    style={{ width: `${tAutoPct}%` }}
                                    className="bg-emerald-500 h-full"
                                  />
                                  <div
                                    style={{ width: `${tWarnPct}%` }}
                                    className="bg-amber-500 h-full"
                                  />
                                  <div
                                    style={{ width: `${tFallPct}%` }}
                                    className="bg-rose-500 h-full"
                                  />
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* 5.2 PESTAÑA 'tenant': Grilla Directa de Tenants con Totales y Calibración */}
      {viewMode === "tenant" && (
        <div data-testid="jev-tenant-view">
          {filteredTenants.length === 0 ? (
            <div
              data-testid="jev-empty-state"
              className="p-12 text-center bg-card/40 rounded-2xl border border-border/80 space-y-2"
            >
              <Store className="w-10 h-10 mx-auto text-muted-foreground/60" />
              <h4 className="text-base font-bold text-foreground">
                {t("platform_admin:jev.empty_tenants.title", {
                  defaultValue: "No se encontraron sucursales",
                })}
              </h4>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                {t("platform_admin:jev.empty_tenants.description", {
                  defaultValue:
                    "Prueba a ajustar tu búsqueda de sucursales o recargar la consola.",
                })}
              </p>
            </div>
          ) : (
            <div
              data-testid="tenant-grid"
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            >
              {filteredTenants.map((tenantItem) => {
                const tTotal = Math.max(1, tenantItem.total_decisions);
                const tAutoPct = ((tenantItem.auto_accepted_count / tTotal) * 100).toFixed(1);
                const tWarnPct = ((tenantItem.flagged_warning_count / tTotal) * 100).toFixed(1);
                const tFallPct = ((tenantItem.fallback_llm_count / tTotal) * 100).toFixed(1);

                return (
                  <div
                    key={tenantItem.tenant_id}
                    data-testid={`tenant-card-${tenantItem.tenant_id}`}
                    className="p-5 rounded-2xl border border-border/80 bg-card/60 shadow-xs space-y-4 hover:border-cyan-500/40 transition-all duration-200"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                          <Store className="w-5 h-5" />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-foreground">
                            {tenantItem.tenant_name}
                          </h4>
                          <span className="text-[11px] font-mono text-muted-foreground">
                            {tenantItem.tenant_schema}
                          </span>
                        </div>
                      </div>
                      <span className="text-[10px] font-mono text-muted-foreground bg-secondary px-2 py-0.5 rounded border border-border">
                        {tenantItem.holding_id}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 p-2.5 rounded-xl bg-background/50 border border-border/60 text-center">
                      <div>
                        <span className="text-[10px] text-muted-foreground block font-medium">
                          {t("platform_admin:jev.metrics.decisions", {
                            defaultValue: "Decisiones",
                          })}
                        </span>
                        <span className="text-sm font-mono font-black text-foreground">
                          {tenantItem.total_decisions.toLocaleString("es-CL")}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted-foreground block font-medium">
                          {t("platform_admin:jev.metrics.cost_usd", {
                            defaultValue: "Costo USD",
                          })}
                        </span>
                        <span className="text-sm font-mono font-black text-emerald-400">
                          ${Number(tenantItem.total_cost_usd).toFixed(4)}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted-foreground block font-medium">
                          {t("platform_admin:jev.metrics.latency", {
                            defaultValue: "Latencia",
                          })}
                        </span>
                        <span className="text-sm font-mono font-black text-indigo-400">
                          {Number(tenantItem.avg_latency_ms).toFixed(1)} ms
                        </span>
                      </div>
                    </div>

                    <div className="space-y-1.5 pt-1">
                      <div className="flex items-center justify-between text-xs font-semibold">
                        <span className="text-emerald-400">{tAutoPct}% Auto</span>
                        <span className="text-amber-400">{tWarnPct}% Warn</span>
                        <span className="text-rose-400">{tFallPct}% Fallback</span>
                      </div>
                      <div className="h-2 w-full bg-secondary rounded-full overflow-hidden flex">
                        <div
                          style={{ width: `${tAutoPct}%` }}
                          className="bg-emerald-500 h-full"
                          title={`Auto: ${tAutoPct}%`}
                        />
                        <div
                          style={{ width: `${tWarnPct}%` }}
                          className="bg-amber-500 h-full"
                          title={`Warn: ${tWarnPct}%`}
                        />
                        <div
                          style={{ width: `${tFallPct}%` }}
                          className="bg-rose-500 h-full"
                          title={`Fallback: ${tFallPct}%`}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 5.3 PESTAÑA 'logs': Bitácora Tabular con Columnas Opcionales y TablePagination */}
      {viewMode === "logs" && (
        <div data-testid="jev-logs-view" className="space-y-4">
          <div className="rounded-2xl border border-border/80 bg-card/60 shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table
                data-testid="jev-logs-table"
                className="w-full text-left text-xs text-muted-foreground border-collapse"
              >
                <thead className="bg-secondary/40 text-[11px] uppercase tracking-wider text-muted-foreground font-semibold border-b border-border/60">
                  <tr>
                    <th scope="col" className="py-3 px-4">
                      {t("platform_admin:jev.table.date_time", {
                        defaultValue: "Fecha / Hora",
                      })}
                    </th>
                    {optionalCols.tenant_name && (
                      <th scope="col" className="py-3 px-4">
                        {t("platform_admin:jev.table.tenant", {
                          defaultValue: "Sucursal (Tenant)",
                        })}
                      </th>
                    )}
                    {optionalCols.caller_feature && (
                      <th scope="col" className="py-3 px-4">
                        {t("platform_admin:jev.table.caller_feature", {
                          defaultValue: "Feature",
                        })}
                      </th>
                    )}
                    {optionalCols.primitive && (
                      <th scope="col" className="py-3 px-4">
                        {t("platform_admin:jev.table.primitive", {
                          defaultValue: "Primitiva",
                        })}
                      </th>
                    )}
                    <th scope="col" className="py-3 px-4">
                      {t("platform_admin:jev.table.summary_result", {
                        defaultValue: "Resumen / Resultado",
                      })}
                    </th>
                    {optionalCols.confidence && (
                      <th scope="col" className="py-3 px-4">
                        {t("platform_admin:jev.table.score", {
                          defaultValue: "Score",
                        })}
                      </th>
                    )}
                    <th scope="col" className="py-3 px-4">
                      {t("platform_admin:jev.table.action", {
                        defaultValue: "Acción Calibrada",
                      })}
                    </th>
                    {optionalCols.model_name && (
                      <th scope="col" className="py-3 px-4">
                        {t("platform_admin:jev.table.model", {
                          defaultValue: "Modelo",
                        })}
                      </th>
                    )}
                    {optionalCols.latency && (
                      <th scope="col" className="py-3 px-4 text-right">
                        {t("platform_admin:jev.table.latency", {
                          defaultValue: "Latencia",
                        })}
                      </th>
                    )}
                    {optionalCols.cost && (
                      <th scope="col" className="py-3 px-4 text-right">
                        {t("platform_admin:jev.table.cost", {
                          defaultValue: "Costo",
                        })}
                      </th>
                    )}
                  </tr>
                </thead>

                <tbody className="divide-y divide-border/40 font-mono">
                  {paginatedLogs.length === 0 ? (
                    <tr>
                      <td
                        colSpan={10}
                        className="p-8 text-center text-muted-foreground"
                      >
                        <div
                          data-testid="jev-empty-state"
                          className="space-y-1 font-sans"
                        >
                          <p className="font-bold text-foreground">
                            {t("platform_admin:jev.empty_logs.title", {
                              defaultValue: "No se encontraron logs de decisiones",
                            })}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {t("platform_admin:jev.empty_logs.description", {
                              defaultValue: "Intenta cambiar los filtros seleccionados",
                            })}
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    paginatedLogs.map((log) => (
                      <tr
                        key={log.id}
                        data-testid={`jev-log-row-${log.id}`}
                        className="hover:bg-secondary/30 transition-colors"
                      >
                        {/* Fecha */}
                        <td className="py-3 px-4 whitespace-nowrap text-[11px]">
                          {new Date(log.created_at).toLocaleString("es-CL", {
                            dateStyle: "short",
                            timeStyle: "medium",
                          })}
                        </td>

                        {/* Tenant */}
                        {optionalCols.tenant_name && (
                          <td className="py-3 px-4 whitespace-nowrap font-sans font-medium text-foreground">
                            {log.tenant_name}
                          </td>
                        )}

                        {/* Caller Feature */}
                        {optionalCols.caller_feature && (
                          <td className="py-3 px-4 whitespace-nowrap">
                            <span className="inline-flex items-center rounded bg-secondary px-2 py-0.5 text-[10px] font-semibold text-foreground border border-border">
                              {log.caller_feature}
                            </span>
                          </td>
                        )}

                        {/* Primitiva */}
                        {optionalCols.primitive && (
                          <td className="py-3 px-4 whitespace-nowrap text-indigo-400 font-semibold text-[11px]">
                            {log.decision_primitive}
                          </td>
                        )}

                        {/* Resumen / Resultado */}
                        <td className="py-3 px-4 font-sans text-xs max-w-xs truncate">
                          <span className="font-semibold text-foreground block truncate">
                            {log.input_summary}
                          </span>
                          <span className="text-[11px] text-muted-foreground block truncate">
                            {log.result_value}
                          </span>
                        </td>

                        {/* Score Confianza */}
                        {optionalCols.confidence && (
                          <td className="py-3 px-4 whitespace-nowrap font-bold text-cyan-400">
                            {(Number(log.confidence_score) * 100).toFixed(0)}%
                          </td>
                        )}

                        {/* Acción Calibrada */}
                        <td className="py-3 px-4 whitespace-nowrap font-sans">
                          {renderActionBadge(log.calibrated_action)}
                        </td>

                        {/* Modelo */}
                        {optionalCols.model_name && (
                          <td className="py-3 px-4 whitespace-nowrap text-[11px] text-muted-foreground">
                            {log.model_name}
                          </td>
                        )}

                        {/* Latencia */}
                        {optionalCols.latency && (
                          <td className="py-3 px-4 whitespace-nowrap text-right font-bold text-indigo-400">
                            {log.latency_ms} ms
                          </td>
                        )}

                        {/* Costo */}
                        {optionalCols.cost && (
                          <td className="py-3 px-4 whitespace-nowrap text-right font-bold text-emerald-400">
                            ${Number(log.provider_cost_usd).toFixed(5)}
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* TablePagination canónica */}
            <TablePagination
              currentPage={page}
              totalItems={filteredLogs.length}
              pageSize={pageSize}
              pageSizeOptions={[10, 25, 50, 100]}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
              itemLabel={t("platform_admin:jev.table.pagination_item_label", {
                defaultValue: "decisiones JEV",
              })}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default JevConsumptionPage;
