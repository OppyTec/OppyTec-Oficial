import { useState } from "react";
import {
  ArrowRight,
  Bot,
  Building2,
  DollarSign,
  ExternalLink,
  Layers,
  MapPin,
  Package,
  Percent,
  Search,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import { useCurrencyFormatter } from "@/shared/currency";
import { translateKey } from "@/shared/i18n";
import type { HoldingHubSummary, HoldingTabId, HoldingTenantCard } from "./types";

export interface HoldingCentralSectionProps {
  readonly holdingData: HoldingHubSummary;
  readonly searchFilter: string;
  readonly onSearchChange: (query: string) => void;
  readonly filteredTenants: readonly HoldingTenantCard[];
  readonly onSwitchTenant: (tenant: HoldingTenantCard) => void;
  readonly onRefresh?: () => void;
  readonly onNavigateTab?: (tab: HoldingTabId) => void;
}

export function HoldingCentralSection({
  holdingData,
  searchFilter,
  onSearchChange,
  filteredTenants,
  onSwitchTenant,
}: HoldingCentralSectionProps) {
  const { currency, convertAndFormat } = useCurrencyFormatter();
  const [selectedTenantForModal, setSelectedTenantForModal] =
    useState<HoldingTenantCard | null>(null);

  const kpis = [
    {
      id: "total_sales",
      titleKey: "central.kpi_total_sales",
      value: convertAndFormat(holdingData.metrics.total_sales, "CLP", currency),
      subtext: translateKey("holding_hub", "central.kpi_sales_sub"),
      icon: DollarSign,
      trend: "up" as const,
      color: "text-emerald-500",
      bgColor: "bg-emerald-500/10",
      borderColor: "border-emerald-500/20",
    },
    {
      id: "inventory_value",
      titleKey: "central.kpi_inventory_value",
      value: convertAndFormat(holdingData.metrics.inventory_value, "CLP", currency),
      subtext: translateKey("holding_hub", "central.kpi_inventory_sub"),
      icon: Package,
      trend: "neutral" as const,
      color: "text-cyan-500",
      bgColor: "bg-cyan-500/10",
      borderColor: "border-cyan-500/20",
    },
    {
      id: "waste_pct",
      titleKey: "central.kpi_waste_pct",
      value: `${holdingData.metrics.waste_pct.toFixed(1)}%`,
      subtext: translateKey("holding_hub", "central.kpi_waste_status_good"),
      icon: Percent,
      trend: "down" as const,
      color: "text-amber-500",
      bgColor: "bg-amber-500/10",
      borderColor: "border-amber-500/20",
    },
    {
      id: "ai_credits",
      titleKey: "central.kpi_ai_credits",
      value: holdingData.credit_balance.toLocaleString(),
      subtext: translateKey("holding_hub", "central.kpi_credits_sub", {
        available: holdingData.credit_balance.toLocaleString(),
        total: holdingData.total_credits.toLocaleString(),
      }),
      icon: Sparkles,
      trend: "up" as const,
      color: "text-primary",
      bgColor: "bg-primary/10",
      borderColor: "border-primary/20",
      showProgress: true,
      pct: holdingData.usage_pct,
    },
  ];

  return (
    <div
      data-testid="holding-central-section"
      className="space-y-8 animate-in fade-in duration-300"
    >
      {/* 4 Glassmorphism KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.id}
              data-testid={`holding-kpi-${kpi.id}`}
              className="relative overflow-hidden rounded-2xl border border-border/70 bg-card/60 p-5 backdrop-blur-xl shadow-lg transition-all duration-300 hover:border-primary/40 hover:shadow-primary/5 group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground">
                  {translateKey("holding_hub", kpi.titleKey)}
                </span>
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-xl ${kpi.bgColor} ${kpi.color} border ${kpi.borderColor} transition-transform group-hover:scale-110`}
                >
                  <Icon className="h-5 w-5" />
                </div>
              </div>

              <div className="mt-3">
                <h3 className="text-2xl font-extrabold tracking-tight text-foreground font-mono">
                  {kpi.value}
                </h3>
                <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
                  {kpi.trend === "up" && (
                    <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                  )}
                  {kpi.trend === "down" && (
                    <TrendingDown className="h-3.5 w-3.5 text-emerald-500" />
                  )}
                  <span className="truncate">{kpi.subtext}</span>
                </div>
              </div>

              {kpi.showProgress && (
                <div className="mt-4 space-y-1">
                  <div className="flex justify-between text-[11px] font-mono">
                    <span className="text-muted-foreground">
                      {translateKey("holding_hub", "central.period_usage")}
                    </span>
                    <span className="font-bold text-primary">{kpi.pct}%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-500"
                      style={{ width: `${Math.min(100, kpi.pct ?? 0)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Network of Branches Section */}
      <div className="space-y-4">
        {/* Header with Search and Counters */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-foreground">
              {translateKey("holding_hub", "central.tenants_header")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {translateKey("holding_hub", "central.tenants_count", {
                count: filteredTenants.length,
              })}
            </p>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              data-testid="holding-tenants-search"
              value={searchFilter}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={translateKey(
                "holding_hub",
                "central.tenants_search"
              )}
              className="w-full rounded-xl border border-border/80 bg-background/50 pl-10 pr-9 py-2 text-xs md:text-sm font-medium text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary shadow-xs"
            />
            {searchFilter && (
              <button
                type="button"
                onClick={() => onSearchChange("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Branches Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {filteredTenants.map((tenant) => {
            const usagePct =
              tenant.allocated_credits > 0
                ? Math.round((tenant.used_credits / tenant.allocated_credits) * 100)
                : tenant.usage_pct;

            return (
              <div
                key={tenant.id}
                data-testid={`holding-tenant-card-${tenant.id}`}
                className="flex flex-col justify-between rounded-2xl border border-border/70 bg-card/60 p-5 backdrop-blur-xl shadow-md transition-all duration-300 hover:border-primary/50 hover:shadow-lg group"
              >
                <div>
                  {/* Top: Branch Name, Schema and Status */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-primary shrink-0" />
                        <h3 className="font-bold text-base text-foreground truncate">
                          {tenant.name}
                        </h3>
                      </div>
                      <p className="mt-1 font-mono text-xs text-muted-foreground truncate">
                        {tenant.schema_name}
                      </p>
                    </div>

                    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-500 shrink-0">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      {translateKey("holding_hub", "central.status_active")}
                    </span>
                  </div>

                  {/* Business Type & Address */}
                  {tenant.business_type && (
                    <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="rounded-md bg-secondary px-2 py-0.5 font-medium text-foreground">
                        {tenant.business_type}
                      </span>
                      {tenant.address && (
                        <span className="flex items-center gap-1 truncate">
                          <MapPin className="h-3 w-3 shrink-0" />
                          <span className="truncate">{tenant.address}</span>
                        </span>
                      )}
                    </div>
                  )}

                  {/* Enabled Modules Badges */}
                  {tenant.modules && tenant.modules.length > 0 && (
                    <div className="mt-4">
                      <div className="flex flex-wrap gap-1.5">
                        {tenant.modules.map((mod) => (
                          <span
                            key={mod}
                            className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/40 px-2 py-0.5 text-[10px] font-medium text-foreground/80"
                          >
                            <Layers className="h-2.5 w-2.5 text-primary" />
                            {mod}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* AI Consumption Meter */}
                  <div className="mt-5 rounded-xl border border-border/60 bg-background/40 p-3">
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="flex items-center gap-1.5 font-semibold text-foreground">
                        <Bot className="h-3.5 w-3.5 text-primary" />
                        {translateKey("holding_hub", "central.ai_consumption")}
                      </span>
                      <span className="font-mono text-muted-foreground">
                        {tenant.used_credits.toLocaleString()} /{" "}
                        {tenant.allocated_credits > 0
                          ? tenant.allocated_credits.toLocaleString()
                          : translateKey("holding_hub", "central.shared_badge")}
                      </span>
                    </div>

                    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary transition-all duration-300"
                        style={{ width: `${Math.min(100, usagePct)}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between mt-2 text-[11px] text-muted-foreground">
                      <span>
                        {tenant.bot_requests}{" "}
                        {translateKey("holding_hub", "central.bot_requests")}
                      </span>
                      <span className="font-mono font-semibold text-foreground">
                        {usagePct}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Bottom Action Buttons */}
                <div className="mt-5 pt-4 border-t border-border/60 flex items-center justify-between gap-3">
                  <button
                    type="button"
                    data-testid={`tenant-detail-btn-${tenant.id}`}
                    onClick={() => setSelectedTenantForModal(tenant)}
                    className="flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground transition"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    <span>{translateKey("holding_hub", "central.view_detail")}</span>
                  </button>

                  <button
                    type="button"
                    data-testid={`tenant-enter-btn-${tenant.id}`}
                    onClick={() => onSwitchTenant(tenant)}
                    className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-md shadow-primary/20 transition hover:bg-primary/90 focus:outline-none"
                  >
                    <span>{translateKey("holding_hub", "central.enter_tenant")}</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Branch Detail Modal */}
      {selectedTenantForModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={translateKey("holding_hub", "central.modal_title", {
            name: selectedTenantForModal.name,
          })}
          data-testid="tenant-detail-modal"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setSelectedTenantForModal(null)}
        >
          <div
            className="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl backdrop-blur-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <span className="rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-bold uppercase text-primary">
                  {selectedTenantForModal.schema_name}
                </span>
                <h3 className="mt-1 text-lg font-bold text-foreground">
                  {selectedTenantForModal.name}
                </h3>
              </div>
              <button
                type="button"
                data-testid="tenant-detail-modal-close"
                onClick={() => setSelectedTenantForModal(null)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content Details */}
            <div className="mt-5 space-y-3 text-xs md:text-sm">
              <div className="flex justify-between py-2 border-b border-border/60">
                <span className="text-muted-foreground">
                  {translateKey("holding_hub", "central.modal_rut")}
                </span>
                <span className="font-mono font-semibold text-foreground">
                  {selectedTenantForModal.rut || "76.543.210-1"}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-border/60">
                <span className="text-muted-foreground">
                  {translateKey("holding_hub", "central.modal_business_type")}
                </span>
                <span className="font-semibold text-foreground">
                  {selectedTenantForModal.business_type || "Restaurante"}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-border/60">
                <span className="text-muted-foreground">
                  {translateKey("holding_hub", "central.modal_address")}
                </span>
                <span className="font-medium text-foreground text-right truncate max-w-[260px]">
                  {selectedTenantForModal.address || "Av. Providencia 1420, Santiago"}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-border/60">
                <span className="text-muted-foreground">
                  {translateKey("holding_hub", "central.modal_used_credits")}
                </span>
                <span className="font-mono font-bold text-primary">
                  {translateKey("holding_hub", "central.modal_credits_unit", {
                    count: selectedTenantForModal.used_credits.toLocaleString(),
                  })}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-border/60">
                <span className="text-muted-foreground">
                  {translateKey("holding_hub", "central.modal_bot_requests")}
                </span>
                <span className="font-mono font-bold text-foreground">
                  {selectedTenantForModal.bot_requests.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setSelectedTenantForModal(null)}
                className="rounded-xl border border-border px-4 py-2 text-xs font-semibold text-foreground hover:bg-muted/70 transition"
              >
                {translateKey("holding_hub", "central.modal_close")}
              </button>
              <button
                type="button"
                data-testid="tenant-detail-modal-switch-btn"
                onClick={() => {
                  const target = selectedTenantForModal;
                  setSelectedTenantForModal(null);
                  onSwitchTenant(target);
                }}
                className="rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground hover:bg-primary/90 transition shadow-md shadow-primary/20"
              >
                {translateKey("holding_hub", "central.modal_switch")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
