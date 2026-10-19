import { AnalyticsFeatureView } from "@/features/analytics";
import { AuthFeatureView } from "@/features/auth";
import { CatalogFeatureView } from "@/features/catalog";
import { InventoryFeatureView } from "@/features/inventory";
import { OperationsFeatureView } from "@/features/operations";
import { OppyFyFeatureView } from "@/features/oppyfy";
import { PlatformAdminFeatureView } from "@/features/platform-admin";
import { ProcurementFeatureView } from "@/features/procurement";
import { RbacAndAuditFeatureView } from "@/features/rbac-and-audit";
import { RecipesFeatureView } from "@/features/recipes";
import type { FeatureRouteId } from "@/shared/components/layout/Sidebar";

export interface AppRouterProps {
  readonly activeFeature: FeatureRouteId;
  readonly showAllFeatures: boolean;
}

export function AppRouter({ activeFeature, showAllFeatures }: AppRouterProps) {
  if (showAllFeatures) {
    return (
      <div data-testid="app-router-all-features" className="space-y-6">
        <AnalyticsFeatureView />
        <CatalogFeatureView />
        <InventoryFeatureView />
        <RecipesFeatureView />
        <ProcurementFeatureView />
        <OperationsFeatureView />
        <OppyFyFeatureView />
        <RbacAndAuditFeatureView />
        <PlatformAdminFeatureView />
        <AuthFeatureView />
      </div>
    );
  }

  switch (activeFeature) {
    case "analytics":
      return <AnalyticsFeatureView />;
    case "catalog":
      return <CatalogFeatureView />;
    case "inventory":
      return <InventoryFeatureView />;
    case "recipes":
      return <RecipesFeatureView />;
    case "procurement":
      return <ProcurementFeatureView />;
    case "operations":
      return <OperationsFeatureView />;
    case "oppyfy":
      return <OppyFyFeatureView />;
    case "rbac-and-audit":
      return <RbacAndAuditFeatureView />;
    case "platform-admin":
      return <PlatformAdminFeatureView />;
    case "auth":
      return <AuthFeatureView />;
  }
}
