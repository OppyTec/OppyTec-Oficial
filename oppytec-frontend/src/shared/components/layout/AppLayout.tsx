import type { ReactNode } from "react";
import type { OppyTecTheme } from "@/shared/components/ui/designTokens";
import { BottomNav } from "./BottomNav";
import type { TenantOption } from "./HoldingTenantSwitcher";
import { Navbar } from "./Navbar";
import { type FeatureRouteId, Sidebar } from "./Sidebar";

export interface AppLayoutProps {
  readonly brandName: string;
  readonly environmentLabel: string;
  readonly activeTheme: OppyTecTheme;
  readonly onSelectTheme: (theme: OppyTecTheme) => void;
  readonly activeTenantId: string;
  readonly onSelectTenant: (tenant: TenantOption) => void;
  readonly activeWarehouseId: string;
  readonly onSelectWarehouse: (warehouseId: string) => void;
  readonly activeFeature: FeatureRouteId;
  readonly onSelectFeature: (feature: FeatureRouteId) => void;
  readonly showAllFeatures: boolean;
  readonly onToggleShowAll: () => void;
  readonly language: "es" | "en";
  readonly onLanguageChanged: (lang: "es" | "en") => void;
  readonly children: ReactNode;
}

export function AppLayout({
  brandName,
  environmentLabel,
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
  return (
    <div
      data-testid="app-layout"
      className="min-h-dvh w-full overflow-x-hidden p-3 pb-20 md:p-6 md:pb-8"
    >
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
      />
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-3">
          <Sidebar
            activeFeature={activeFeature}
            onSelectFeature={onSelectFeature}
            showAllFeatures={showAllFeatures}
            onToggleShowAll={onToggleShowAll}
            language={language}
          />
        </div>
        <main className="space-y-4 lg:col-span-9">{children}</main>
      </div>
      <BottomNav
        activeFeature={activeFeature}
        onSelectFeature={onSelectFeature}
      />
    </div>
  );
}
