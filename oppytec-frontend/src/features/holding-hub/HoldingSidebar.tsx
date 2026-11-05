import { useState } from "react";
import {
  Bot,
  ChevronLeft,
  ChevronRight,
  Layers,
  LayoutDashboard,
  Sparkles,
} from "lucide-react";
import { motion } from "framer-motion";
import { translateKey } from "@/shared/i18n";
import type { HoldingHubSummary, HoldingTabId } from "./types";

export interface HoldingSidebarProps {
  readonly activeTab: HoldingTabId;
  readonly onTabChange: (tab: HoldingTabId) => void;
  readonly holdingData: HoldingHubSummary;
}

export function HoldingSidebar({
  activeTab,
  onTabChange,
  holdingData,
}: HoldingSidebarProps) {
  const [collapsed, setCollapsed] = useState<boolean>(false);

  const tabs: readonly {
    id: HoldingTabId;
    labelKey: string;
    icon: typeof LayoutDashboard;
    color?: string;
    badgeKey?: string;
  }[] = [
    {
      id: "central",
      labelKey: "sidebar.tab_central",
      icon: LayoutDashboard,
    },
    {
      id: "briefing",
      labelKey: "sidebar.tab_briefing",
      icon: Sparkles,
      color: "#8b5cf6",
      badgeKey: "sidebar.briefing_badge",
    },
    {
      id: "planes",
      labelKey: "sidebar.tab_plans",
      icon: Layers,
    },
    {
      id: "creditos",
      labelKey: "sidebar.tab_credits",
      icon: Bot,
    },
  ];

  const safetyColor =
    holdingData.safety_status === "CRITICAL"
      ? "bg-rose-500"
      : holdingData.safety_status === "WARNING"
      ? "bg-amber-500"
      : "bg-primary";

  return (
    <motion.aside
      data-testid="holding-sidebar"
      animate={{ width: collapsed ? 80 : 280 }}
      transition={{ duration: 0.25, ease: "easeInOut" }}
      className="relative flex flex-col justify-between border-r border-border/70 bg-card/70 backdrop-blur-xl transition-colors select-none z-30 shrink-0"
    >
      {/* Top Holding Header */}
      <div>
        <div className="flex items-center justify-between p-4 border-b border-border/60">
          {!collapsed && (
            <div className="min-w-0 flex-1 pr-2 animate-in fade-in duration-200">
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block truncate">
                {translateKey("holding_hub", "sidebar.holding_title")}
              </span>
              <h2
                data-testid="sidebar-holding-name"
                className="text-sm font-bold text-foreground truncate"
              >
                {holdingData.name}
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[11px] font-mono text-muted-foreground">
                  {holdingData.rut}
                </span>
                <span
                  data-testid="sidebar-active-plan-badge"
                  className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary uppercase"
                >
                  {holdingData.active_plan_slug}
                </span>
              </div>
            </div>
          )}

          <button
            type="button"
            data-testid="holding-sidebar-collapse-btn"
            onClick={() => setCollapsed((prev) => !prev)}
            aria-label={
              collapsed
                ? translateKey("holding_hub", "sidebar.expand")
                : translateKey("holding_hub", "sidebar.collapse")
            }
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border/70 bg-background/50 text-muted-foreground hover:bg-muted/70 hover:text-foreground transition shrink-0"
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Tab Navigation List */}
        <nav
          aria-label={translateKey("holding_hub", "sidebar.title")}
          className="p-3 space-y-1.5"
        >
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const isBriefing = tab.id === "briefing";
            return (
              <button
                key={tab.id}
                type="button"
                data-testid={`holding-tab-${tab.id}`}
                onClick={() => onTabChange(tab.id)}
                className={`relative flex w-full items-center gap-3.5 px-3 py-3 rounded-xl text-sm font-semibold transition-colors ${
                  isActive
                    ? isBriefing
                      ? "bg-purple-500/15 text-purple-400 shadow-xs"
                      : "bg-primary/15 text-primary shadow-xs"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                } ${collapsed ? "justify-center px-0" : ""}`}
              >
                {isActive && (
                  <motion.div
                    layoutId="sidebarActivePill"
                    className={`absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-md ${
                      isBriefing ? "bg-[#8b5cf6]" : "bg-primary"
                    }`}
                    transition={{ type: "spring", stiffness: 350, damping: 30 }}
                  />
                )}
                <Icon
                  className={`h-5 w-5 shrink-0 ${
                    isActive
                      ? isBriefing
                        ? "text-[#8b5cf6]"
                        : "text-primary"
                      : isBriefing
                      ? "text-[#8b5cf6]/80"
                      : "text-muted-foreground"
                  }`}
                  aria-hidden="true"
                />
                {!collapsed && (
                  <>
                    <span className="truncate">
                      {translateKey("holding_hub", tab.labelKey)}
                    </span>
                    {tab.badgeKey && (
                      <span
                        data-testid="holding-sidebar-briefing-badge"
                        className="ml-auto flex items-center justify-center rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-purple-500/15 text-[#8b5cf6] border border-purple-500/30 shrink-0"
                      >
                        {translateKey("holding_hub", tab.badgeKey)}
                      </span>
                    )}
                  </>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom AI Quota Widget */}
      <div className="p-4 border-t border-border/60">
        {!collapsed ? (
          <div
            data-testid="sidebar-credit-pool-widget"
            className="rounded-2xl border border-border/80 bg-background/50 p-3.5 shadow-xs"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                {translateKey("holding_hub", "sidebar.credit_pool")}
              </span>
              <span
                data-testid="sidebar-credit-pct"
                className="text-xs font-mono font-bold text-primary"
              >
                {holdingData.usage_pct}%
              </span>
            </div>

            {/* Progress Bar */}
            <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full rounded-full transition-all duration-500 ${safetyColor}`}
                style={{ width: `${Math.min(100, holdingData.usage_pct)}%` }}
              />
            </div>

            <p className="mt-2 text-[11px] text-muted-foreground truncate">
              {translateKey("holding_hub", "sidebar.used_credits", {
                used: holdingData.used_credits.toLocaleString(),
                total: holdingData.total_credits.toLocaleString(),
              })}
            </p>
          </div>
        ) : (
          <div
            data-testid="sidebar-credit-pool-mini"
            title={translateKey("holding_hub", "sidebar.credit_consumed_title", {
              pct: holdingData.usage_pct,
            })}
            className="flex flex-col items-center justify-center p-2 rounded-xl bg-background/50 border border-border/60"
          >
            <Sparkles className="h-4 w-4 text-primary mb-1" />
            <span className="text-[10px] font-mono font-bold text-primary">
              {holdingData.usage_pct}%
            </span>
          </div>
        )}
      </div>
    </motion.aside>
  );
}
