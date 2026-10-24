import { useState, type ReactNode } from "react";
import { Outlet } from "react-router-dom";
import { cn } from "@/shared/lib";
import { useSwipeNavigation } from "@/shared/hooks/useSwipeNavigation";
import type { OppyTecTheme } from "@/shared/components/ui/designTokens";
import { Navbar } from "./Navbar";
import { Sidebar, type FeatureRouteId } from "./Sidebar";
import type { TenantOption } from "./HoldingTenantSwitcher";

export interface AppLayoutProps {
  readonly brandName?: string;
  readonly environmentLabel?: string;
  readonly activeTheme?: OppyTecTheme;
  readonly onSelectTheme?: (theme: OppyTecTheme) => void;
  readonly activeTenantId?: string;
  readonly onSelectTenant?: (tenant: TenantOption) => void;
  readonly activeWarehouseId?: string;
  readonly onSelectWarehouse?: (warehouseId: string) => void;
  readonly activeFeature?: FeatureRouteId;
  readonly onSelectFeature?: (feature: FeatureRouteId) => void;
  readonly showAllFeatures?: boolean;
  readonly onToggleShowAll?: () => void;
  readonly language?: "es" | "en";
  readonly onLanguageChanged?: (lang: "es" | "en") => void;
  readonly children?: ReactNode;
}

export function AppLayout({
  brandName = "OppyTec v2.0",
  environmentLabel = "PROD:SaaS",
  activeTheme,
  onSelectTheme,
  activeTenantId,
  onSelectTenant,
  activeWarehouseId,
  onSelectWarehouse,
  activeFeature,
  onSelectFeature,
  showAllFeatures,
  onToggleShowAll,
  language,
  onLanguageChanged,
  children,
}: AppLayoutProps) {
  useSwipeNavigation();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  return (
    <div
      data-testid="app-layout"
      className="flex min-h-screen bg-background text-foreground antialiased selection:bg-primary/20 selection:text-primary"
    >
      {/* Sidebar with collapse and mobile slide-in drawer */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        isCollapsed={isSidebarCollapsed}
        onCollapseChange={setIsSidebarCollapsed}
        activeFeature={activeFeature}
        onSelectFeature={onSelectFeature}
        showAllFeatures={showAllFeatures}
        onToggleShowAll={onToggleShowAll}
        language={language}
      />

      {/* Main Content Column */}
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar
          brandName={brandName}
          environmentLabel={environmentLabel}
          activeTheme={activeTheme}
          onSelectTheme={onSelectTheme}
          activeTenantId={activeTenantId}
          onSelectTenant={onSelectTenant}
          activeWarehouseId={activeWarehouseId}
          onSelectWarehouse={onSelectWarehouse}
          onLanguageChanged={onLanguageChanged}
          onMenuClick={() => setIsSidebarOpen(true)}
        />

        <main className="flex-1 p-4 md:p-8 lg:p-10 overflow-x-clip">
          <div
            className={cn(
              "max-w-[1400px] mx-auto transition-transform duration-300 ease-out",
              !isSidebarCollapsed && "min-[1840px]:-translate-x-[90px]"
            )}
          >
            {children ?? <Outlet />}
          </div>
        </main>
      </div>
    </div>
  );
}

export default AppLayout;
