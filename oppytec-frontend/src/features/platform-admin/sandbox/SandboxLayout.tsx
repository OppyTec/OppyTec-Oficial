import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  CalendarClock,
  Database,
  FlaskConical,
  Layers,
  type LucideIcon,
  PlayCircle,
  ShieldAlert,
} from "lucide-react";
import type { SandboxLayoutProps, SandboxTabId } from "../sandboxTypes";
import { translateKey, useLanguage } from "@/shared/i18n";
import { getRuntimeEnv } from "@/shared/config/env";

export interface SandboxTabDefinition {
  readonly id: SandboxTabId;
  readonly path: string;
  readonly label: string;
  readonly shortLabel: string;
  readonly badge: string;
  readonly description: string;
  readonly icon: LucideIcon;
  readonly color: string;
  readonly rgb: string;
}

export const SANDBOX_TABS: readonly SandboxTabDefinition[] = [
  {
    id: "mock-data",
    path: "/admin/sandbox/mock-data",
    label: "Mock Data & Presets",
    shortLabel: "Mock Data",
    badge: "DATA",
    description: "Generación e inyección controlada de datos sintéticos multi-tenant.",
    icon: Database,
    color: "#f59e0b",
    rgb: "245,158,11",
  },
  {
    id: "playwright-runner",
    path: "/admin/sandbox/playwright-runner",
    label: "Playwright Runner",
    shortLabel: "Playwright",
    badge: "E2E",
    description: "Disparador interactivo y terminal de ejecución de suites Playwright.",
    icon: PlayCircle,
    color: "#10b981",
    rgb: "16,185,129",
  },
  {
    id: "fefo-dates",
    path: "/admin/sandbox/fefo-dates",
    label: "Simulador FEFO",
    shortLabel: "FEFO Warp",
    badge: "WARP",
    description: "Time-Warp para proyección temporal de caducidad y auditoría de mermas.",
    icon: CalendarClock,
    color: "#8b5cf6",
    rgb: "139,92,246",
  },
] as const;

export function SandboxLayout({
  activeTab,
  onTabChange,
  children,
}: SandboxLayoutProps) {
  useLanguage();
  const location = useLocation();
  const navigate = useNavigate();

  const dynamicTabs: readonly SandboxTabDefinition[] = SANDBOX_TABS.map((tab) => {
    if (tab.id === "mock-data") {
      return {
        ...tab,
        label: translateKey("platform_admin", "sandbox.tabs.mock_data"),
        shortLabel: translateKey("platform_admin", "sandbox.tabs.mock_data_short"),
        description: translateKey("platform_admin", "sandbox.tabs.mock_data_desc"),
      };
    }
    if (tab.id === "playwright-runner") {
      return {
        ...tab,
        label: translateKey("platform_admin", "sandbox.tabs.playwright_runner"),
        shortLabel: translateKey("platform_admin", "sandbox.tabs.playwright_runner_short"),
        description: translateKey("platform_admin", "sandbox.tabs.playwright_runner_desc"),
      };
    }
    return {
      ...tab,
      label: translateKey("platform_admin", "sandbox.tabs.fefo_dates"),
      shortLabel: translateKey("platform_admin", "sandbox.tabs.fefo_dates_short"),
      description: translateKey("platform_admin", "sandbox.tabs.fefo_dates_desc"),
    };
  });

  // Resolve current active tab from prop or URL
  const currentTabId: SandboxTabId = activeTab || (() => {
    if (location.pathname.includes("playwright-runner")) return "playwright-runner";
    if (location.pathname.includes("fefo-dates")) return "fefo-dates";
    return "mock-data";
  })();

  const fallbackTab = dynamicTabs[0] as SandboxTabDefinition;
  const currentTab: SandboxTabDefinition =
    dynamicTabs.find((tab) => tab.id === currentTabId) ?? fallbackTab;

  const handleTabClick = (tabId: SandboxTabId, tabPath: string) => {
    if (onTabChange) {
      onTabChange(tabId);
    }
    navigate(tabPath);
  };

  return (
    <div
      data-testid="sandbox-layout-root"
      className="flex-1 flex flex-col w-full min-h-screen bg-background text-foreground animate-in fade-in duration-300"
    >
      {/* Top Header & Breadcrumbs Bar */}
      <header className="border-b border-border bg-card/60 backdrop-blur-md px-4 sm:px-6 lg:px-8 py-5">
        <div className="max-w-7xl mx-auto space-y-4">
          {/* Breadcrumbs & Env Tag */}
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <nav
              aria-label="Breadcrumb"
              data-testid="sandbox-breadcrumbs"
              className="flex items-center gap-2 text-muted-foreground font-medium"
            >
              <Link
                to="/admin"
                className="hover:text-primary transition-colors flex items-center gap-1.5"
              >
                <Layers size={14} />
                <span>{translateKey("platform_admin", "sandbox.breadcrumb_admin")}</span>
              </Link>
              <span>/</span>
              <span className="text-foreground flex items-center gap-1.5 font-semibold">
                <FlaskConical size={14} className="text-pink-500" />
                <span>{translateKey("platform_admin", "sandbox.title")}</span>
              </span>
              <span>/</span>
              <span
                data-testid="sandbox-active-breadcrumb"
                className="text-primary font-bold"
              >
                {currentTab.label}
              </span>
            </nav>

            {/* Sandbox Environment Isolation Badge */}
            {(() => {
              const runtimeEnv = getRuntimeEnv();
              const isProd = runtimeEnv.VITE_ENVIRONMENT === "production";
              const isStaging = runtimeEnv.VITE_ENVIRONMENT === "staging";
              return (
                <div
                  data-testid="sandbox-env-badge"
                  className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-mono font-semibold shadow-sm ${
                    isProd
                      ? "bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30"
                      : isStaging
                        ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                        : "bg-pink-500/10 text-pink-600 dark:text-pink-400 border border-pink-500/20"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full animate-pulse ${
                      isProd ? "bg-red-500" : isStaging ? "bg-amber-500" : "bg-pink-500"
                    }`}
                  />
                  <span>
                    {runtimeEnv.VITE_ENVIRONMENT.toUpperCase()} ·{" "}
                    {translateKey("platform_admin", "sandbox.env_isolated_badge")}
                  </span>
                </div>
              );
            })()}
          </div>

          {/* Title and Summary */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-pink-500/20 to-purple-600/20 border border-pink-500/30 text-pink-500 shadow-sm">
                  <FlaskConical size={24} />
                </div>
                <div>
                  <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground flex items-center gap-2">
                    {translateKey("platform_admin", "sandbox.title")}
                    <span className="text-xs px-2 py-0.5 rounded-md font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
                      {translateKey("platform_admin", "sandbox.version_badge")}
                    </span>
                  </h1>
                  <p className="text-sm text-muted-foreground">
                    {translateKey("platform_admin", "sandbox.subtitle")}
                  </p>
                </div>
              </div>
            </div>

            {/* Safety Notice Warning */}
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300 text-xs max-w-md">
              <ShieldAlert size={16} className="shrink-0 text-amber-500" />
              <span>
                {translateKey("platform_admin", "sandbox.safety_warning")}
              </span>
            </div>
          </div>

          {/* Top Navigation Tabs */}
          <div
            data-testid="sandbox-top-tabs"
            className="flex items-center gap-2 border-b border-border/60 pt-2 overflow-x-auto no-scrollbar"
          >
            {dynamicTabs.map((tab) => {
              const isActive = tab.id === currentTabId;
              const TabIcon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  data-testid={`sandbox-tab-${tab.id}`}
                  onClick={() => handleTabClick(tab.id, tab.path)}
                  className={`touch-target relative min-h-[44px] px-4 py-2.5 rounded-t-xl text-xs sm:text-sm font-semibold transition-all duration-200 flex items-center gap-2.5 whitespace-nowrap ${
                    isActive
                      ? "text-foreground bg-card border-t border-x border-border shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary/40"
                  }`}
                  style={{
                    borderTopColor: isActive ? tab.color : undefined,
                    borderTopWidth: isActive ? "2px" : undefined,
                  }}
                >
                  <TabIcon
                    size={18}
                    className="shrink-0 transition-colors"
                    style={{ color: isActive ? tab.color : undefined }}
                  />
                  <span>{tab.label}</span>
                  <span
                    className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded font-bold"
                    style={{
                      backgroundColor: isActive ? `rgba(${tab.rgb}, 0.15)` : "rgba(128,128,128,0.1)",
                      color: isActive ? tab.color : "inherit",
                    }}
                  >
                    {tab.badge}
                  </span>

                  {isActive && (
                    <div
                      data-testid="sandbox-tab-active-indicator"
                      className="absolute bottom-0 left-0 right-0 h-0.5"
                      style={{ backgroundColor: tab.color }}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </header>

      {/* Main View Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {children ?? <Outlet />}
      </main>
    </div>
  );
}
