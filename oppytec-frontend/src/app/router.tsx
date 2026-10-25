import { type ReactNode, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import { AnalyticsFeatureView } from "@/features/analytics";
import { AdminLoginPage, LoginPage } from "@/features/auth";
import { CatalogFeatureView } from "@/features/catalog";
import { StockRegistroPage, ContarInventarioPage, RecuentosPage } from "@/features/inventory";
import { OperationsFeatureView } from "@/features/operations";
import { OppyFyFeatureView } from "@/features/oppyfy";
import {
  AdminBusinessTypesView,
  AdminClientUsersView,
  AdminDashboard,
  AdminGlobalUsersView,
  AdminHoldingsView,
  AdminLayout,
  AdminLegalEntitiesView,
  AdminModulesView,
  AdminPlansView,
  AdminTenantsView,
  PlatformAdminFeatureView,
} from "@/features/platform-admin";

import { ProcurementFeatureView } from "@/features/procurement";
import { RbacAndAuditFeatureView } from "@/features/rbac-and-audit";
import { RecipesFeatureView } from "@/features/recipes";
import { ConfiguracionPage } from "@/features/configuracion";
import { ProfilePage } from "@/features/profile";
import { UsuariosPage } from "@/features/users";
import { GestionPage } from "@/features/gestion";
import { useAuth } from "@/shared/auth/usePermissions";
import { HomeDashboard } from "@/features/home";
import {
  AppLayout,
  type FeatureRouteId,
  ModulePlaceholderView,
  OFFICIAL_TENANT_OPTIONS,
  OFFICIAL_WAREHOUSES,
  type TenantOption,
} from "@/shared/components/layout";
import { getRuntimeEnv } from "@/shared/config/env";
import { useTheme } from "@/shared/hooks";
import { getActiveLanguage, type SupportedLanguage, translateKey } from "@/shared/i18n";

export interface PrivateRouteProps {
  readonly children: ReactNode;
}

export function PrivateRoute({ children }: PrivateRouteProps) {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background" data-testid="auth-loading">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-2xl border-4 border-primary border-t-transparent shadow-lg shadow-primary/20" />
          <p className="text-sm font-medium animate-pulse">{translateKey("auth", "session.starting")}</p>
        </div>
      </div>
    );
  }

  return session ? <>{children}</> : <Navigate to="/login" replace />;
}

export function AdminPrivateRoute({ children }: PrivateRouteProps) {
  const { session, loading, isGlobalAdmin } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-zinc-950" data-testid="admin-auth-loading">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-2xl border-4 border-primary border-t-transparent shadow-lg shadow-primary/20" />
          <p className="text-sm font-medium animate-pulse text-zinc-400">
            {translateKey("auth", "session.verifying_admin")}
          </p>
        </div>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/admin/login" replace />;
  }

  if (!isGlobalAdmin) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

export function AdminPlaceholderView({
  title,
  description,
}: {
  readonly title: string;
  readonly description?: string;
}) {
  return (
    <div
      data-testid={`admin-placeholder-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
      className="p-6 md:p-8 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500"
    >
      <div className="space-y-1">
        <h2 className="text-3xl font-bold tracking-tight text-foreground">{title}</h2>
        {description && (
          <p className="text-muted-foreground text-sm">{description}</p>
        )}
      </div>
      <div className="rounded-xl border border-dashed border-border bg-card/50 p-12 text-center text-muted-foreground text-sm">
        {title} — OppyTec SaaS Cloud Infrastructure
      </div>
    </div>
  );
}

export function CleanAdminDashboard() {
  return (
    <div data-testid="admin-panel-root" className="h-full w-full">
      <AdminDashboard />
    </div>
  );
}


export function ClientAppShell() {
  const runtimeEnv = getRuntimeEnv();
  const { theme, setTheme } = useTheme("ocean-blue");
  const [activeTenant, setActiveTenant] = useState<TenantOption>(
    () =>
      OFFICIAL_TENANT_OPTIONS[0] ?? {
        holdingId: "holding-genesis",
        holdingName: "Holding Principal",
        tenantId: "tenant_genesis",
        tenantName: "Local Principal",
        rut: "76.000.000-1",
      }
  );
  const [activeWarehouseId, setActiveWarehouseId] = useState<string>(
    OFFICIAL_WAREHOUSES[0]?.id ?? "bod-cocina-central"
  );
  const [activeFeature, setActiveFeature] = useState<FeatureRouteId>("analytics");
  const [language, setLanguage] = useState<SupportedLanguage>(() => getActiveLanguage());

  return (
    <AppLayout
      brandName={runtimeEnv.VITE_AI_ASSISTANT_BRAND_NAME}
      environmentLabel={`${runtimeEnv.VITE_ENVIRONMENT}:${runtimeEnv.VITE_ENV_NAMESPACE}`}
      activeTheme={theme}
      onSelectTheme={setTheme}
      activeTenantId={activeTenant.tenantId}
      onSelectTenant={setActiveTenant}
      activeWarehouseId={activeWarehouseId}
      onSelectWarehouse={setActiveWarehouseId}
      activeFeature={activeFeature}
      onSelectFeature={setActiveFeature}
      showAllFeatures={false}
      onToggleShowAll={() => {}}
      language={language}
      onLanguageChanged={setLanguage}
    >
      <Routes>
        <Route index element={<HomeDashboard />} />
        <Route path="/" element={<HomeDashboard />} />
        <Route path="/consumo/*" element={<ModulePlaceholderView title="Consumo y Operaciones" moduleSlug="module:consumo" />} />
        <Route path="/registro-de-consumo" element={<ModulePlaceholderView title="Registro de Consumo" moduleSlug="module:consumo:registro_de_consumo" />} />
        <Route path="/ventas/*" element={<ModulePlaceholderView title="Punto de Venta (Ventas Comerciales)" moduleSlug="module:ventas" />} />
        <Route path="/inventario/stock" element={<StockRegistroPage />} />
        <Route path="/inventario" element={<StockRegistroPage />} />
        <Route path="/inventario/*" element={<StockRegistroPage />} />
        <Route path="/contar-inventario" element={<ContarInventarioPage />} />
        <Route path="/recuentos" element={<RecuentosPage />} />
        <Route path="/gestion/*" element={<GestionPage />} />
        <Route path="/gestion" element={<GestionPage />} />
        <Route path="/proveedores" element={<ModulePlaceholderView title="Directorio de Proveedores" moduleSlug="module:gestion:proveedores" />} />
        <Route path="/notificaciones/*" element={<ModulePlaceholderView title="Centro de Notificaciones y Solicitudes" moduleSlug="module:notificaciones" />} />
        <Route path="/alertas/*" element={<ModulePlaceholderView title="Alertas Críticas de Stock & Vencimiento" moduleSlug="module:alertas" />} />
        <Route path="/eventos/*" element={<ModulePlaceholderView title="Planificación de Eventos y Banquetes" moduleSlug="module:eventos" />} />
        <Route path="/proyeccion/*" element={<ModulePlaceholderView title="Proyección de Demanda y Análisis Financiero" moduleSlug="module:proyeccion" />} />
        <Route path="/historial/*" element={<ModulePlaceholderView title="Historial de Movimientos y Auditoría" moduleSlug="module:historial" />} />
        <Route path="/contabilidad/*" element={<ModulePlaceholderView title="Contabilidad y Facturas DTE" moduleSlug="module:contabilidad" />} />
        <Route path="/reportes/*" element={<ModulePlaceholderView title="Panel Ejecutivo y Reportes Estratégicos" moduleSlug="module:panel_ejecutivo" />} />
        <Route path="/actividades/usuarios" element={<UsuariosPage />} />
        <Route path="/usuarios" element={<UsuariosPage />} />
        <Route path="/actividades/*" element={<ModulePlaceholderView title="Panel de Actividades y Turnos" moduleSlug="module:panel_de_actividades" />} />
        <Route path="/oppybot" element={<ModulePlaceholderView title="OppyBot Workspace (Copiloto IA)" moduleSlug="module:oppybot" />} />
        <Route path="/perfil" element={<ProfilePage />} />
        <Route path="/holding-hub" element={<ModulePlaceholderView title="Holding Hub — Visión Consolidada" moduleSlug="module:holding_hub" />} />
        <Route path="/configuracion" element={<ConfiguracionPage />} />
        <Route path="*" element={<ModulePlaceholderView title="Módulo en preparación" />} />
      </Routes>
    </AppLayout>
  );
}

export interface ClientFeatureRouterProps {
  readonly activeFeature: FeatureRouteId;
}

export function ClientFeatureRouter({ activeFeature }: ClientFeatureRouterProps) {
  switch (activeFeature) {
    case "analytics":
      return <AnalyticsFeatureView />;
    case "catalog":
      return <CatalogFeatureView />;
    case "inventory":
      return <StockRegistroPage />;
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
      return <LoginPage />;
  }
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route
          path="/admin"
          element={
            <AdminPrivateRoute>
              <AdminLayout />
            </AdminPrivateRoute>
          }
        >
          <Route index element={<CleanAdminDashboard />} />
          <Route path="users" element={<AdminGlobalUsersView />} />
          <Route path="business-types" element={<AdminBusinessTypesView />} />
          <Route path="modules" element={<AdminModulesView />} />
          <Route path="plans" element={<AdminPlansView />} />
          <Route
            path="token-consumption"
            element={
              <AdminPlaceholderView
                title="Consumo Tokens Cliente"
                description="Monitoreo FinOps y créditos OppyFy"
              />
            }
          />
          <Route path="holdings" element={<AdminHoldingsView />} />
          <Route path="legal-entities" element={<AdminLegalEntitiesView />} />
          <Route path="tenants" element={<AdminTenantsView />} />
          <Route path="client-users" element={<AdminClientUsersView />} />
          <Route path="observability" element={<PlatformAdminFeatureView />} />
          <Route
            path="fx-rates"
            element={
              <AdminPlaceholderView
                title="Tasas FX Centrales"
                description="Sincronización con Banco Central de Chile y BCE Frankfurter"
              />
            }
          />
          <Route
            path="backups"
            element={
              <AdminPlaceholderView
                title="Bóveda de Respaldos"
                description="Respaldos cifrados en 4 capas (.sql.zst.age)"
              />
            }
          />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Route>
        <Route
          path="/*"
          element={
            <PrivateRoute>
              <ClientAppShell />
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
