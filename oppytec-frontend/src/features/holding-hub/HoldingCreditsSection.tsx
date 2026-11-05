import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  Bot,
  Cpu,
  Sliders,
  Sparkles,
  X,
  Zap,
} from "lucide-react";
import { useCurrencyFormatter } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";
import type {
  CreditDistributionMode,
  HoldingHubSummary,
} from "./types";

export interface HoldingCreditsSectionProps {
  readonly holdingData: HoldingHubSummary;
  readonly activeScope: string;
  readonly onScopeChange: (scope: string) => void;
  readonly onPurchaseCredits: (
    amount: number,
    currency?: string,
    method?: string
  ) => Promise<boolean>;
  readonly onUpdateDistribution: (
    mode: CreditDistributionMode,
    allocations: Record<string, number>
  ) => Promise<boolean>;
}

export function HoldingCreditsSection({
  holdingData,
  activeScope,
  onScopeChange,
  onPurchaseCredits,
  onUpdateDistribution,
}: HoldingCreditsSectionProps) {
  const { currency, convertAndFormat } = useCurrencyFormatter();
  // Chart range: 7, 14 or 30 days
  const [chartRange, setChartRange] = useState<7 | 14 | 30>(14);

  // Buy Credits Modal State
  const [showBuyModal, setShowBuyModal] = useState<boolean>(false);
  const [selectedPackage, setSelectedPackage] = useState<number>(2500);
  const [customAmount, setCustomAmount] = useState<string>("");
  const [isCustom, setIsCustom] = useState<boolean>(false);
  const [paymentMethod, setPaymentMethod] = useState<string>("credit_card");
  const [isBuying, setIsBuying] = useState<boolean>(false);
  const [buySuccess, setBuySuccess] = useState<string | null>(null);

  // Distribution Modal State
  const [showDistributeModal, setShowDistributeModal] = useState<boolean>(false);
  const [distMode, setDistMode] = useState<CreditDistributionMode>(
    holdingData.distribution_mode
  );
  const [allocations, setAllocations] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    for (const t of holdingData.tenants) {
      initial[t.id] = t.allocated_credits || Math.floor(holdingData.total_credits / holdingData.tenants.length);
    }
    return initial;
  });
  const [isDistributing, setIsDistributing] = useState<boolean>(false);
  const [distSuccess, setDistSuccess] = useState<string | null>(null);

  // Selected Scope Tenant
  const selectedTenant = useMemo(() => {
    if (activeScope === "all") return null;
    return holdingData.tenants.find((t) => t.id === activeScope) ?? null;
  }, [activeScope, holdingData.tenants]);

  // Dynamic KPIs according to Scope
  const kpis = useMemo(() => {
    if (selectedTenant) {
      const allocated = selectedTenant.allocated_credits || 0;
      const used = selectedTenant.used_credits;
      const available = Math.max(0, allocated - used);
      const estTokens = used * 250;
      return {
        available:
          allocated > 0
            ? available
            : translateKey("holding_hub", "central.shared_badge"),
        consumed: used,
        tokens: estTokens,
        requests: selectedTenant.bot_requests,
      };
    }
    const totalTokens = holdingData.daily_usage.reduce((acc, d) => acc + d.tokens, 0);
    const totalRequests = holdingData.tenants.reduce((acc, t) => acc + t.bot_requests, 0);
    return {
      available: holdingData.credit_balance,
      consumed: holdingData.used_credits,
      tokens: totalTokens,
      requests: totalRequests,
    };
  }, [selectedTenant, holdingData]);

  // Filtered Chart Data based on range
  const chartData = useMemo(() => {
    const usage = holdingData.daily_usage || [];
    const sliced = usage.slice(-chartRange);
    if (!selectedTenant) return sliced;
    // Scale proportionally for tenant
    const ratio = holdingData.used_credits > 0 ? selectedTenant.used_credits / holdingData.used_credits : 0.33;
    return sliced.map((d) => ({
      ...d,
      credits: Math.round(d.credits * ratio),
      tokens: Math.round(d.tokens * ratio),
      requests: Math.max(1, Math.round(d.requests * ratio)),
    }));
  }, [holdingData.daily_usage, holdingData.used_credits, chartRange, selectedTenant]);

  // Distribution calculations
  const totalAllocated = useMemo(() => {
    if (distMode === "shared") return 0;
    return Object.values(allocations).reduce((sum, val) => sum + (val || 0), 0);
  }, [distMode, allocations]);

  const remainingBalance = holdingData.total_credits - totalAllocated;
  const isOverAllocated = distMode === "allocated" && totalAllocated > holdingData.total_credits;

  // Final purchase credit count and cost ($15 CLP per credit)
  const finalPurchaseAmount = isCustom ? Number(customAmount) || 0 : selectedPackage;
  const purchaseCostClp = finalPurchaseAmount * 15;

  const handleConfirmPurchase = async () => {
    if (finalPurchaseAmount <= 0) return;
    setIsBuying(true);
    try {
      const ok = await onPurchaseCredits(finalPurchaseAmount, currency, paymentMethod);
      if (ok) {
        setBuySuccess(
          translateKey("holding_hub", "credits.buy_success", {
            amount: finalPurchaseAmount.toLocaleString(),
          })
        );
        setShowBuyModal(false);
        setTimeout(() => setBuySuccess(null), 5000);
      }
    } finally {
      setIsBuying(false);
    }
  };

  const handleSaveDistribution = async () => {
    if (isOverAllocated) return;
    setIsDistributing(true);
    try {
      const ok = await onUpdateDistribution(distMode, allocations);
      if (ok) {
        setDistSuccess(translateKey("holding_hub", "credits.dist_success"));
        setShowDistributeModal(false);
        setTimeout(() => setDistSuccess(null), 5000);
      }
    } finally {
      setIsDistributing(false);
    }
  };

  return (
    <div
      data-testid="holding-credits-section"
      className="space-y-8 animate-in fade-in duration-300"
    >
      {/* Top Header & Action Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-extrabold tracking-tight text-foreground">
            {translateKey("holding_hub", "credits.header_title")}
          </h2>
          <p className="text-xs md:text-sm text-muted-foreground">
            {translateKey("holding_hub", "credits.header_subtitle")}
          </p>
        </div>

        {/* Buttons: Buy & Distribute */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            data-testid="credits-distribute-trigger-btn"
            onClick={() => {
              setDistMode(holdingData.distribution_mode);
              setShowDistributeModal(true);
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-xs font-semibold text-foreground hover:bg-muted/70 transition shadow-xs"
          >
            <Sliders className="h-4 w-4 text-primary" />
            <span>{translateKey("holding_hub", "credits.action_distribute")}</span>
          </button>

          <button
            type="button"
            data-testid="credits-buy-trigger-btn"
            onClick={() => {
              setIsCustom(false);
              setSelectedPackage(2500);
              setShowBuyModal(true);
            }}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-primary to-emerald-600 px-4 py-2 text-xs font-bold text-primary-foreground shadow-md shadow-primary/25 hover:opacity-95 transition"
          >
            <Sparkles className="h-4 w-4" />
            <span>{translateKey("holding_hub", "credits.action_buy")}</span>
          </button>
        </div>
      </div>

      {/* Success Messages */}
      {buySuccess && (
        <div
          data-testid="credits-buy-success-alert"
          className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-center text-xs md:text-sm font-semibold text-emerald-500 animate-in fade-in"
        >
          {buySuccess}
        </div>
      )}

      {distSuccess && (
        <div
          data-testid="credits-dist-success-alert"
          className="rounded-2xl border border-primary/30 bg-primary/10 p-4 text-center text-xs md:text-sm font-semibold text-primary animate-in fade-in"
        >
          {distSuccess}
        </div>
      )}

      {/* Scope Selector Bar */}
      <div className="flex items-center gap-3 p-3 rounded-2xl border border-border/70 bg-card/60 backdrop-blur-xl">
        <span className="text-xs font-semibold text-muted-foreground whitespace-nowrap">
          {translateKey("holding_hub", "credits.scope_label")}:
        </span>
        <select
          data-testid="credits-scope-select"
          aria-label={translateKey("holding_hub", "credits.scope_label")}
          value={activeScope}
          onChange={(e) => onScopeChange(e.target.value)}
          className="min-h-[40px] flex-1 sm:max-w-xs rounded-xl border border-border/80 bg-background/60 px-3 py-1.5 text-xs font-semibold text-foreground focus:border-primary focus:outline-none"
        >
          <option value="all">
            {translateKey("holding_hub", "credits.scope_all")}
          </option>
          {holdingData.tenants.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} ({t.schema_name})
            </option>
          ))}
        </select>
      </div>

      {/* 4 Dynamic AI KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
        <div
          data-testid="credits-kpi-available"
          className="rounded-2xl border border-border/70 bg-card/60 p-5 backdrop-blur-xl shadow-md"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground">
              {translateKey("holding_hub", "credits.kpi_available")}
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/15 text-primary">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-primary">
            {typeof kpis.available === "number"
              ? kpis.available.toLocaleString()
              : kpis.available}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">
            {translateKey("holding_hub", "credits.kpi_available_sub")}
          </p>
        </div>

        <div
          data-testid="credits-kpi-consumed"
          className="rounded-2xl border border-border/70 bg-card/60 p-5 backdrop-blur-xl shadow-md"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground">
              {translateKey("holding_hub", "credits.kpi_consumed")}
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/15 text-cyan-500">
              <Cpu className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-foreground">
            {kpis.consumed.toLocaleString()}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">
            {translateKey("holding_hub", "credits.kpi_consumed_sub")}
          </p>
        </div>

        <div
          data-testid="credits-kpi-tokens"
          className="rounded-2xl border border-border/70 bg-card/60 p-5 backdrop-blur-xl shadow-md"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground">
              {translateKey("holding_hub", "credits.kpi_tokens")}
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-500">
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-foreground">
            {kpis.tokens.toLocaleString()}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">
            {translateKey("holding_hub", "credits.kpi_tokens_sub")}
          </p>
        </div>

        <div
          data-testid="credits-kpi-requests"
          className="rounded-2xl border border-border/70 bg-card/60 p-5 backdrop-blur-xl shadow-md"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground">
              {translateKey("holding_hub", "credits.kpi_requests")}
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-500/15 text-amber-500">
              <Bot className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-foreground">
            {kpis.requests.toLocaleString()}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">
            {translateKey("holding_hub", "credits.kpi_requests_sub")}
          </p>
        </div>
      </div>

      {/* Interactive Recharts AreaChart */}
      <div
        data-testid="credits-usage-chart-card"
        className="rounded-3xl border border-border/70 bg-card/60 p-6 backdrop-blur-xl shadow-xl"
      >
        {/* Chart Header & Range Switcher */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="text-base md:text-lg font-bold text-foreground">
              {translateKey("holding_hub", "credits.chart_title")}
            </h3>
            <p className="text-xs text-muted-foreground">
              {translateKey("holding_hub", "credits.chart_subtitle")}
            </p>
          </div>

          <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background/50 p-1">
            <button
              type="button"
              data-testid="credits-chart-range-7"
              onClick={() => setChartRange(7)}
              className={`rounded-lg px-3 py-1 text-xs font-semibold transition ${
                chartRange === 7
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {translateKey("holding_hub", "credits.range_7d")}
            </button>
            <button
              type="button"
              data-testid="credits-chart-range-14"
              onClick={() => setChartRange(14)}
              className={`rounded-lg px-3 py-1 text-xs font-semibold transition ${
                chartRange === 14
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {translateKey("holding_hub", "credits.range_14d")}
            </button>
            <button
              type="button"
              data-testid="credits-chart-range-30"
              onClick={() => setChartRange(30)}
              className={`rounded-lg px-3 py-1 text-xs font-semibold transition ${
                chartRange === 30
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {translateKey("holding_hub", "credits.range_30d")}
            </button>
          </div>
        </div>

        {/* Recharts Area Container with Cyan Glow */}
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="cyanOceanGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-border/40" />
              <XAxis
                dataKey="date"
                stroke="currentColor"
                className="text-[10px] text-muted-foreground font-mono"
                tickFormatter={(val: string) => val.slice(5)}
              />
              <YAxis
                stroke="currentColor"
                className="text-[10px] text-muted-foreground font-mono"
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length > 0 && payload[0]) {
                    const row = payload[0].payload as {
                      date: string;
                      credits: number;
                      tokens: number;
                      requests: number;
                    };
                    return (
                      <div className="rounded-xl border border-border bg-card/95 p-3 shadow-xl backdrop-blur-md text-xs font-mono space-y-1">
                        <div className="font-bold text-foreground border-b border-border/60 pb-1 font-sans">
                          {row.date}
                        </div>
                        <div className="text-cyan-400 flex items-center justify-between gap-4">
                          <span>{translateKey("holding_hub", "credits.chart_tooltip_credits")}</span>
                          <span className="font-bold">{row.credits.toLocaleString()}</span>
                        </div>
                        <div className="text-muted-foreground flex items-center justify-between gap-4">
                          <span>{translateKey("holding_hub", "credits.chart_tooltip_tokens")}</span>
                          <span>{row.tokens.toLocaleString()}</span>
                        </div>
                        <div className="text-muted-foreground flex items-center justify-between gap-4">
                          <span>{translateKey("holding_hub", "credits.chart_tooltip_requests")}</span>
                          <span>{row.requests}</span>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Area
                type="monotone"
                dataKey="credits"
                stroke="#06b6d4"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#cyanOceanGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Buy Credits Modal */}
      {showBuyModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={translateKey("holding_hub", "credits.buy_modal_title")}
          data-testid="credits-buy-modal"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setShowBuyModal(false)}
        >
          <div
            className="relative w-full max-w-lg rounded-3xl border border-border bg-card p-6 md:p-8 shadow-2xl backdrop-blur-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-foreground">
                  {translateKey("holding_hub", "credits.buy_modal_title")}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {translateKey("holding_hub", "credits.buy_modal_desc")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowBuyModal(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Packages Selector */}
            <div className="mt-6 space-y-3">
              <div className="grid grid-cols-2 gap-2.5">
                {[1000, 2500, 5000, 10000].map((pkg) => {
                  const isSelected = !isCustom && selectedPackage === pkg;
                  return (
                    <button
                      key={pkg}
                      type="button"
                      data-testid={`credit-pkg-${pkg}`}
                      onClick={() => {
                        setIsCustom(false);
                        setSelectedPackage(pkg);
                      }}
                      className={`flex flex-col items-center justify-center p-3 rounded-2xl border text-xs font-semibold transition ${
                        isSelected
                          ? "border-primary bg-primary/10 text-primary font-bold shadow-xs"
                          : "border-border bg-muted/20 text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <span className="font-mono text-base font-extrabold text-foreground">
                        {pkg.toLocaleString()}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {convertAndFormat(pkg * 15, "CLP", currency)}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Custom Amount Option */}
              <div
                className={`p-3 rounded-2xl border transition ${
                  isCustom
                    ? "border-primary bg-primary/10"
                    : "border-border bg-muted/20"
                }`}
              >
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="package_type"
                    checked={isCustom}
                    onChange={() => setIsCustom(true)}
                    className="accent-primary"
                  />
                  <span className="text-xs font-semibold text-foreground">
                    {translateKey("holding_hub", "credits.pkg_custom")}
                  </span>
                </label>

                {isCustom && (
                  <div className="mt-2 flex items-center gap-2">
                    <input
                      type="number"
                      data-testid="credit-custom-amount-input"
                      value={customAmount}
                      onChange={(e) => setCustomAmount(e.target.value)}
                      placeholder={translateKey(
                        "holding_hub",
                        "credits.custom_amount_placeholder"
                      )}
                      className="w-full rounded-xl border border-border bg-background px-3 py-1.5 text-xs font-mono font-bold text-foreground focus:border-primary focus:outline-none"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Payment Method Selector */}
            <div className="mt-4 space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground block">
                {translateKey("holding_hub", "credits.payment_method")}
              </label>
              <select
                data-testid="credit-payment-method-select"
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                className="w-full rounded-xl border border-border bg-background/60 p-2.5 text-xs font-medium text-foreground focus:border-primary focus:outline-none"
              >
                <option value="credit_card">
                  {translateKey("holding_hub", "credits.method_cc")}
                </option>
                <option value="invoice">
                  {translateKey("holding_hub", "credits.method_invoice")}
                </option>
              </select>
            </div>

            {/* Pricing Summary */}
            <div className="mt-6 rounded-2xl border border-border/80 bg-muted/30 p-4 flex items-center justify-between">
              <div>
                <span className="text-xs text-muted-foreground block">
                  {translateKey("holding_hub", "credits.total_to_pay")}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {translateKey("holding_hub", "credits.price_per_credit")}
                </span>
              </div>
              <div className="text-right">
                <span
                  data-testid="credits-buy-total-price"
                  className="text-2xl font-extrabold font-mono text-primary"
                >
                  {convertAndFormat(purchaseCostClp, "CLP", currency)}
                </span>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowBuyModal(false)}
                disabled={isBuying}
                className="rounded-xl border border-border px-4 py-2.5 text-xs font-semibold text-foreground hover:bg-muted/70 transition"
              >
                {translateKey("holding_hub", "plans.cancel_button")}
              </button>
              <button
                type="button"
                data-testid="credits-buy-confirm-btn"
                disabled={isBuying || finalPurchaseAmount <= 0}
                onClick={handleConfirmPurchase}
                className="rounded-xl bg-primary px-5 py-2.5 text-xs font-bold text-primary-foreground shadow-md shadow-primary/20 hover:bg-primary/90 transition disabled:opacity-50"
              >
                {isBuying
                  ? translateKey("common", "status.loading")
                  : translateKey("holding_hub", "credits.buy_confirm")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Distribution Modal */}
      {showDistributeModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={translateKey("holding_hub", "credits.dist_modal_title")}
          data-testid="credits-distribution-modal"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setShowDistributeModal(false)}
        >
          <div
            className="relative w-full max-w-2xl rounded-3xl border border-border bg-card p-6 md:p-8 shadow-2xl backdrop-blur-xl max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-foreground">
                  {translateKey("holding_hub", "credits.dist_modal_title")}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {translateKey("holding_hub", "credits.dist_modal_desc")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowDistributeModal(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Distribution Mode Switcher */}
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                data-testid="dist-mode-shared-btn"
                className={`flex flex-col p-4 rounded-2xl border cursor-pointer transition ${
                  distMode === "shared"
                    ? "border-primary bg-primary/10 shadow-xs"
                    : "border-border bg-muted/20 text-muted-foreground hover:border-border/80"
                }`}
              >
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="dist_mode"
                    checked={distMode === "shared"}
                    onChange={() => setDistMode("shared")}
                    className="accent-primary"
                  />
                  <span className="text-xs font-bold text-foreground">
                    {translateKey("holding_hub", "credits.mode_shared")}
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] text-muted-foreground">
                  {translateKey("holding_hub", "credits.mode_shared_desc")}
                </p>
              </label>

              <label
                data-testid="dist-mode-allocated-btn"
                className={`flex flex-col p-4 rounded-2xl border cursor-pointer transition ${
                  distMode === "allocated"
                    ? "border-primary bg-primary/10 shadow-xs"
                    : "border-border bg-muted/20 text-muted-foreground hover:border-border/80"
                }`}
              >
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="dist_mode"
                    checked={distMode === "allocated"}
                    onChange={() => setDistMode("allocated")}
                    className="accent-primary"
                  />
                  <span className="text-xs font-bold text-foreground">
                    {translateKey("holding_hub", "credits.mode_allocated")}
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] text-muted-foreground">
                  {translateKey("holding_hub", "credits.mode_allocated_desc")}
                </p>
              </label>
            </div>

            {/* Sliders for Allocated Mode */}
            {distMode === "allocated" && (
              <div className="mt-6 space-y-4">
                <div className="space-y-4">
                  {holdingData.tenants.map((t) => {
                    const currentAllocated = allocations[t.id] ?? 0;
                    return (
                      <div
                        key={t.id}
                        data-testid={`tenant-slider-box-${t.id}`}
                        className="rounded-2xl border border-border/80 bg-background/50 p-4"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div>
                            <span className="font-semibold text-xs text-foreground">
                              {t.name}
                            </span>
                            <span className="ml-2 font-mono text-[10px] text-muted-foreground">
                              {t.schema_name}
                            </span>
                          </div>
                          <span
                            data-testid={`tenant-slider-value-${t.id}`}
                            className="font-mono text-xs font-bold text-primary"
                          >
                            {translateKey("holding_hub", "credits.credits_count", {
                              count: currentAllocated.toLocaleString(),
                            })}
                          </span>
                        </div>

                        <input
                          type="range"
                          min={0}
                          max={holdingData.total_credits}
                          step={250}
                          value={currentAllocated}
                          data-testid={`tenant-slider-input-${t.id}`}
                          onChange={(e) => {
                            const val = Number(e.target.value);
                            setAllocations((prev) => ({
                              ...prev,
                              [t.id]: val,
                            }));
                          }}
                          className="w-full accent-primary cursor-pointer"
                        />
                      </div>
                    );
                  })}
                </div>

                {/* Pool Usage Meter */}
                <div className="rounded-2xl border border-border/80 bg-muted/30 p-4">
                  <div className="flex items-center justify-between text-xs mb-2">
                    <span className="text-muted-foreground">
                      {translateKey("holding_hub", "credits.dist_assigned")}:{" "}
                      <strong className="text-foreground font-mono">
                        {totalAllocated.toLocaleString()}
                      </strong>{" "}
                      / {holdingData.total_credits.toLocaleString()}
                    </span>
                    <span
                      className={`font-mono font-bold ${
                        isOverAllocated ? "text-rose-500" : "text-emerald-500"
                      }`}
                    >
                      {remainingBalance >= 0
                        ? translateKey("holding_hub", "credits.dist_remaining", {
                            count: remainingBalance.toLocaleString(),
                          })
                        : translateKey("holding_hub", "credits.dist_excess", {
                            count: Math.abs(remainingBalance).toLocaleString(),
                          })}
                    </span>
                  </div>

                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        isOverAllocated ? "bg-rose-500" : "bg-primary"
                      }`}
                      style={{
                        width: `${Math.min(
                          100,
                          (totalAllocated / holdingData.total_credits) * 100
                        )}%`,
                      }}
                    />
                  </div>

                  {isOverAllocated && (
                    <div
                      data-testid="credits-over-warning"
                      className="mt-3 flex items-center gap-2 text-xs font-semibold text-rose-500"
                    >
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                      <span>
                        {translateKey("holding_hub", "credits.dist_over_warning", {
                          diff: Math.abs(remainingBalance).toLocaleString(),
                        })}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="mt-6 flex items-center justify-end gap-3 border-t border-border/60 pt-4">
              <button
                type="button"
                onClick={() => setShowDistributeModal(false)}
                disabled={isDistributing}
                className="rounded-xl border border-border px-4 py-2.5 text-xs font-semibold text-foreground hover:bg-muted/70 transition"
              >
                {translateKey("holding_hub", "plans.cancel_button")}
              </button>
              <button
                type="button"
                data-testid="credits-dist-save-btn"
                disabled={isDistributing || isOverAllocated}
                onClick={handleSaveDistribution}
                className="rounded-xl bg-primary px-5 py-2.5 text-xs font-bold text-primary-foreground shadow-md shadow-primary/20 hover:bg-primary/90 transition disabled:opacity-50"
              >
                {isDistributing
                  ? translateKey("common", "status.loading")
                  : translateKey("holding_hub", "credits.dist_save")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
