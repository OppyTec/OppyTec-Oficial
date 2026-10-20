import { Building, Briefcase, Store, Users, ShieldAlert, LogOut, Sun, Moon, Waves, UserCircle } from "lucide-react";
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
import { InventoryFeatureView } from "@/features/inventory";
import { OperationsFeatureView } from "@/features/operations";
import { OppyFyFeatureView } from "@/features/oppyfy";
import { PlatformAdminFeatureView } from "@/features/platform-admin";
import { ProcurementFeatureView } from "@/features/procurement";
import { RbacAndAuditFeatureView } from "@/features/rbac-and-audit";
import { RecipesFeatureView } from "@/features/recipes";
import { useAuth } from "@/shared/auth/usePermissions";
import {
  AppLayout,
  type FeatureRouteId,
  OFFICIAL_TENANT_OPTIONS,
  OFFICIAL_WAREHOUSES,
  type TenantOption,
} from "@/shared/components/layout";
import { getRuntimeEnv } from "@/shared/config/env";
import {
  SUPPORTED_CURRENCIES,
  type SupportedCurrency,
  useCurrency,
} from "@/shared/currency";
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

export function CleanAdminDashboard() {
  const { user, signOut } = useAuth();
  const { theme, setTheme } = useTheme("ocean-blue");
  const { currency, setCurrency } = useCurrency();
  const [activeLang, setActiveLang] = useState<SupportedLanguage>(() => getActiveLanguage());

  const toggleTheme = (): void => {
    setTheme(theme === "light" ? "dark" : theme === "dark" ? "ocean-blue" : "light");
  };

  const [counts] = useState({
    holdings: 0,
    legalEntities: 0,
    tenants: 0,
    users: 1, // SuperUser Génesis
  });

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground" data-testid="admin-panel-root">
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden relative">
        <header className="h-20 flex items-center justify-between px-6 border-b border-border bg-background/95 backdrop-blur-sm z-40 shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 bg-primary/10 rounded-xl flex items-center justify-center border border-primary/20">
              <ShieldAlert className="w-5 h-5 text-primary" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-primary uppercase tracking-widest leading-none block">
                OppyTec SaaS
              </span>
              <h1 className="text-base font-bold text-foreground">
                {translateKey("auth", "admin_dashboard.header")}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <select
              aria-label="Selector de Moneda"
              value={currency}
              onChange={(e) => setCurrency(e.target.value as SupportedCurrency)}
              className="h-9 rounded-lg border border-border bg-background px-2 text-xs font-semibold focus-visible:outline-none"
            >
              {SUPPORTED_CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>

            <select
              aria-label="Selector de Idioma"
              value={activeLang}
              onChange={(e) => setActiveLang(e.target.value as SupportedLanguage)}
              className="h-9 rounded-lg border border-border bg-background px-2 text-xs font-semibold focus-visible:outline-none"
            >
              <option value="es">🇪🇸 ES</option>
              <option value="en">🇺🇸 EN</option>
            </select>

            <button
              type="button"
              onClick={toggleTheme}
              className="h-9 w-9 rounded-lg flex items-center justify-center border border-border hover:bg-secondary transition-colors"
              title="Cambiar tema"
            >
              {theme === "light" && <Sun className="w-4 h-4 text-foreground" />}
              {theme === "dark" && <Moon className="w-4 h-4" />}
              {theme === "ocean-blue" && <Waves className="w-4 h-4 text-sky-400" />}
            </button>

            <div className="h-6 w-px bg-border mx-1" />

            <div className="flex items-center gap-2 text-xs font-medium">
              <UserCircle className="w-5 h-5 text-muted-foreground" />
              <span className="hidden sm:inline font-semibold">{user?.email || "oppytec.admin@gmail.com"}</span>
            </div>

            <button
              type="button"
              onClick={() => void signOut()}
              className="touch-target inline-flex items-center rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-1.5 text-xs font-semibold text-destructive hover:bg-destructive/20 transition-colors"
            >
              <LogOut className="w-4 h-4 mr-1.5" />
              {translateKey("auth", "session.logout")}
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8">
          <div className="space-y-1">
            <h2 className="text-3xl font-bold tracking-tight">
              {translateKey("auth", "admin_dashboard.title")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {translateKey("auth", "admin_dashboard.subtitle")}
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4" data-testid="admin-kpi-grid">
            <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground">
                  {translateKey("auth", "admin_dashboard.holdings_title")}
                </span>
                <Building className="h-4 w-4 text-primary" />
              </div>
              <div className="text-3xl font-extrabold text-foreground">{counts.holdings}</div>
              <p className="text-xs text-muted-foreground">
                {translateKey("auth", "admin_dashboard.holdings_subtitle")}
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground">
                  {translateKey("auth", "admin_dashboard.legal_entities_title")}
                </span>
                <Briefcase className="h-4 w-4 text-orange-500" />
              </div>
              <div className="text-3xl font-extrabold text-foreground">{counts.legalEntities}</div>
              <p className="text-xs text-muted-foreground">
                {translateKey("auth", "admin_dashboard.legal_entities_subtitle")}
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground">
                  {translateKey("auth", "admin_dashboard.tenants_title")}
                </span>
                <Store className="h-4 w-4 text-emerald-500" />
              </div>
              <div className="text-3xl font-extrabold text-foreground">{counts.tenants}</div>
              <p className="text-xs text-muted-foreground">
                {translateKey("auth", "admin_dashboard.tenants_subtitle")}
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground">
                  {translateKey("auth", "admin_dashboard.users_title")}
                </span>
                <Users className="h-4 w-4 text-pink-500" />
              </div>
              <div className="text-3xl font-extrabold text-foreground">{counts.users}</div>
              <p className="text-xs text-muted-foreground">
                {translateKey("auth", "admin_dashboard.users_subtitle")}
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-dashed border-border bg-card/50 p-12 text-center text-muted-foreground text-sm">
            Estado limpio OppyTec SaaS v2.0: Listo para configurar Holdings, Entidades Legales y Tenants en el Paso 2.
          </div>
        </main>
      </div>
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
      <ClientFeatureRouter activeFeature={activeFeature} />
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
          path="/admin/*"
          element={
            <AdminPrivateRoute>
              <CleanAdminDashboard />
            </AdminPrivateRoute>
          }
        />
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
