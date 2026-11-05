import { useEffect, useState } from "react";
import { scrollToTopInstant } from "@/shared/components/layout";
import { useTheme } from "@/shared/hooks";
import { translateKey } from "@/shared/i18n";
import { HoldingBriefingSection } from "./HoldingBriefingSection";
import { HoldingCentralSection } from "./HoldingCentralSection";
import { HoldingCreditsSection } from "./HoldingCreditsSection";
import { HoldingNavbar } from "./HoldingNavbar";
import { HoldingPlansSection } from "./HoldingPlansSection";
import { HoldingSidebar } from "./HoldingSidebar";
import { TenantCommandPalette } from "./TenantCommandPalette";
import { useHoldingHubData } from "./useHoldingHubData";
import type { HoldingTabId } from "./types";

export interface HoldingHubLayoutProps {
  readonly holdingId?: string;
}

export function HoldingHubLayout({ holdingId }: HoldingHubLayoutProps) {
  const { theme, toggleTheme } = useTheme();
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  const {
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
  } = useHoldingHubData(holdingId);

  // Global Keyboard Shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleTabChange = (tab: HoldingTabId) => {
    setActiveTab(tab);
    scrollToTopInstant();
  };

  if (loading) {
    return (
      <div
        data-testid="holding-loading"
        className="flex h-screen w-screen items-center justify-center bg-background"
      >
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-2xl border-4 border-primary border-t-transparent shadow-lg shadow-primary/20" />
          <p className="text-sm font-medium animate-pulse text-muted-foreground">
            {translateKey("common", "status.loading")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="holding-hub-layout"
      data-theme={theme}
      className={`relative min-h-screen w-full bg-background text-foreground flex flex-col font-sans transition-colors duration-300 selection:bg-primary/20 ${theme}`}
    >
      {/* Premium Atmospheric Ambient Lights */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden z-0">
        {theme === "ocean-blue" ? (
          <>
            <div className="absolute -top-40 left-1/4 h-[550px] w-[550px] rounded-full bg-cyan-500/10 blur-[130px]" />
            <div className="absolute top-1/2 -right-20 h-[450px] w-[450px] rounded-full bg-primary/10 blur-[120px]" />
            <div className="absolute -bottom-20 left-1/3 h-[400px] w-[400px] rounded-full bg-blue-600/10 blur-[140px]" />
          </>
        ) : theme === "dark" ? (
          <>
            <div className="absolute -top-40 left-1/4 h-[500px] w-[500px] rounded-full bg-primary/5 blur-[120px]" />
            <div className="absolute top-1/3 right-10 h-[400px] w-[400px] rounded-full bg-emerald-500/5 blur-[100px]" />
          </>
        ) : (
          <>
            <div className="absolute -top-40 left-1/3 h-[500px] w-[500px] rounded-full bg-emerald-500/5 blur-[100px]" />
            <div className="absolute bottom-10 right-1/4 h-[400px] w-[400px] rounded-full bg-primary/5 blur-[100px]" />
          </>
        )}
      </div>

      {/* 80px Executive Top Navbar */}
      <HoldingNavbar
        holdingData={data}
        refreshing={refreshing}
        onRefresh={refreshData}
        onOpenCommandPalette={() => setCommandPaletteOpen(true)}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {/* Body: Sidebar + Main Content */}
      <div className="relative z-10 flex flex-1 min-h-[calc(100vh-80px)] overflow-hidden">
        {/* Interactive Collapsible Sidebar */}
        <HoldingSidebar
          activeTab={activeTab}
          onTabChange={handleTabChange}
          holdingData={data}
        />

        {/* Dynamic Main Workspace Area */}
        <main
          data-testid="holding-main-content"
          className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8"
        >
          <div className="mx-auto max-w-7xl">
            {activeTab === "central" && (
              <HoldingCentralSection
                holdingData={data}
                searchFilter={searchFilter}
                onSearchChange={setSearchFilter}
                filteredTenants={filteredTenants}
                onSwitchTenant={switchTenant}
                onRefresh={refreshData}
                onNavigateTab={handleTabChange}
              />
            )}

            {activeTab === "briefing" && (
              <HoldingBriefingSection
                holdingData={data}
                onRefresh={refreshData}
                onNavigateTab={handleTabChange}
                refreshing={refreshing}
              />
            )}

            {activeTab === "planes" && (
              <HoldingPlansSection
                holdingData={data}
                onChangePlan={changePlan}
              />
            )}

            {activeTab === "creditos" && (
              <HoldingCreditsSection
                holdingData={data}
                activeScope={activeScope}
                onScopeChange={setActiveScope}
                onPurchaseCredits={purchaseCredits}
                onUpdateDistribution={updateDistribution}
              />
            )}
          </div>
        </main>
      </div>

      {/* Cmd+K Quick Tenant Command Palette */}
      <TenantCommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        tenants={data.tenants}
        onSelectTenant={switchTenant}
      />
    </div>
  );
}
