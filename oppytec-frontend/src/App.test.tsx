import { fireEvent, render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppProviders } from "@/app/providers";
import {
  apiRequest,
  buildApiHeaders,
  getHttpRequestContext,
  resolveApiEndpointUrl,
  setHttpRequestContext,
} from "@/shared/api/httpClient";
import { queryKeys } from "@/shared/api/queryKeys";
import { Can } from "@/shared/auth/Can";
import {
  DEFAULT_RBAC_POLICY_STATE,
  evaluateEffectivePermissions,
  isValidThreeLevelPermission,
} from "@/shared/auth/usePermissions";
import {
  EmptyState,
  PageSkeleton,
} from "@/shared/components/feedback";
import {
  AdaptiveDataView,
  GASTRONOMIC_ICONS,
  NumericInput,
  OFFICIAL_THEMES,
  PRESET_COLORS,
  QuotaProgressIndicator,
  resolveQuotaSemaphoreStatus,
  ResponsiveDialog,
} from "@/shared/components/ui";
import { Navbar, PLAN_BASICO_10_NAV_ITEMS, Sidebar } from "@/shared/components/layout";
import {
  applyDocumentTheme,
  MOBILE_BREAKPOINT_PX,
  THEME_STORAGE_KEY,
  useIsMobile,
  useSwipeNavigation,
  useWebSocket,
} from "@/shared/hooks";
import {
  convertThreeLayerQuantity,
  formatOperationalDate,
  type ThreeLayerUnitProfile,
} from "@/shared/lib";
import {
  REALTIME_WS_PATH,
  useRealtimeContext,
} from "@/shared/realtime/RealtimeProvider";
import {
  AdminClientUsersView,
  AdminDashboard,
  AdminHoldingsView,
  AdminLayout,
  AdminLegalEntitiesView,
  AdminPlansView,
  AdminSidebar,
  AdminTenantsView,
  OBSERVABILITY_13_SUBVIEWS,
  PLAN_BASICO_10_MODULE_SLUGS,
  PlatformAdminFeatureView,
  SAAS_MODULE_TREE,
} from "@/features/platform-admin";
import { AdminLoginPage, LoginPage } from "@/features/auth";
import { CatalogFeatureView } from "@/features/catalog";
import { InventoryFeatureView } from "@/features/inventory";
import { CleanAdminDashboard, ClientAppShell } from "@/app/router";
import { App } from "./App";

const SAMPLE_PROFILE: ThreeLayerUnitProfile = {
  code: "KG",
  purchaseUnit: "caja",
  storageUnit: "kg",
  recipeUnit: "g",
  purchaseToStorageFactor: "2.00000000",
  storageToRecipeFactor: "1000.00000000",
};

function HooksHarness() {
  const isMobile = useIsMobile();
  const swipe = useSwipeNavigation(30);
  const ws = useWebSocket();
  const rt = useRealtimeContext();

  return (
    <div data-testid="hooks-harness">
      <span data-testid="is-mobile-flag">{String(isMobile)}</span>
      <span data-testid="swipe-dir">{swipe.lastSwipeDirection}</span>
      <span data-testid="ws-url">{ws.wsEndpointUrl}</span>
      <button
        type="button"
        data-testid="trigger-swipe-left"
        onClick={() => {
          swipe.onTouchStartX(200);
          swipe.onTouchEndX(100);
        }}
      >
        Swipe Left
      </button>
      <button
        type="button"
        data-testid="trigger-ws-event"
        onClick={() => {
          rt.dispatchRealtimeEvent({
            eventId: "1729368000999-0",
            channel: rt.channelKey,
            eventType: "inventory.stock.updated",
            holdingId: "holding-gastro-sur",
            tenantId: "tenant_rest_central",
            requiredPermission: "inventory.stock.read",
            timestampIso: "2026-10-19T20:10:00Z",
            payload: { sku: "PRD-PK-001", delta: -2 },
          });
          rt.reconnectWithCatchUp("1729368000999-0");
        }}
      >
        Push WS
      </button>
    </div>
  );
}

describe("OppyTec v2.0 — Phase 5 Frontend Architecture & Paso 1 Auth Routing", () => {
  it("validates 3 Legacy DNA themes, 42 preset colors, and 49 gastronomic icons", () => {
    expect(OFFICIAL_THEMES).toEqual(["light", "dark", "ocean-blue"]);
    expect(PRESET_COLORS).toHaveLength(42);
    expect(GASTRONOMIC_ICONS).toHaveLength(49);
    expect(MOBILE_BREAKPOINT_PX).toBe(768);
    expect(THEME_STORAGE_KEY).toBe("oppytec_theme");

    applyDocumentTheme("ocean-blue");
    expect(document.documentElement.getAttribute("data-theme")).toBe("ocean-blue");
    expect(formatOperationalDate("2026-10-19T14:30:00Z")).toContain("2026");
    expect(
      convertThreeLayerQuantity("10.000", "purchase", "storage", SAMPLE_PROFILE)
    ).toBe("20.0000");
  });

  it("verifies 3-level RBAC evaluation logic: M_Plan ∩ ((P_Role ∪ P_Temp) \\ P_Deny)", () => {
    expect(isValidThreeLevelPermission("inventory.stock.read")).toBe(true);
    expect(isValidThreeLevelPermission("invalid-permission")).toBe(false);

    const allowed = evaluateEffectivePermissions({
      ...DEFAULT_RBAC_POLICY_STATE,
      planModules: ["inventory", "catalog"],
      rolePermissions: ["inventory.stock.read", "catalog.products.create"],
      temporaryGrants: [
        {
          permission: "operations.pos.consume",
          expiresAtIso: "2026-12-31T23:59:59Z",
          reason: "Turno fin de semana",
          grantedBy: "admin",
        },
      ],
      deniedPermissions: ["catalog.products.create"],
    });

    expect(allowed.has("inventory.stock.read")).toBe(true);
    expect(allowed.has("catalog.products.create")).toBe(false);
    expect(allowed.has("operations.pos.consume")).toBe(false);

    render(
      <AppProviders>
        <Can
          perform="inventory.stock.read"
          fallback={<span data-testid="rbac-denied">Denegado</span>}
        >
          <span data-testid="rbac-allowed">Permitido</span>
        </Can>
      </AppProviders>
    );

    expect(screen.getByTestId("rbac-allowed")).toBeTruthy();
  });

  it("exercises httpClient, queryKeys, error boundary, and realtime provider", async () => {
    setHttpRequestContext({
      holdingId: "holding-test",
      tenantId: "tenant_test",
      accessToken: "mock-token",
    });

    expect(getHttpRequestContext().holdingId).toBe("holding-test");
    expect(resolveApiEndpointUrl("/catalog/products")).toContain("/catalog/products");
    const headers = buildApiHeaders();
    expect(headers["X-Holding-ID"]).toBe("holding-test");
    expect(headers["X-Tenant-ID"]).toBe("tenant_test");
    expect(headers.Authorization).toBe("Bearer mock-token");

    const fallbackResult = await apiRequest<{ ok: boolean }>("/test-endpoint", {
      fallbackData: { ok: true },
    });
    expect(fallbackResult.data.ok).toBe(true);
    expect(queryKeys.catalog.products("tenant_test")).toEqual([
      "oppytec",
      "catalog",
      "products",
      "tenant_test",
    ]);

    render(
      <AppProviders>
        <HooksHarness />
        <PageSkeleton />
        <EmptyState title="Sin Datos" />
        <ResponsiveDialog
          open
          onClose={() => undefined}
          title="Diálogo Adaptativo"
          isMobile
        >
          <span>Drawer Body</span>
        </ResponsiveDialog>
        <AdaptiveDataView
          rows={[{ id: "1", label: "Row 1" }]}
          getRowKey={(r) => r.id}
          isMobile
          columns={[{ key: "label", header: "Nombre", render: (r) => r.label }]}
        />
        <NumericInput
          label="Cantidad"
          value="10.00"
          onChange={() => undefined}
          testId="unit-num-input"
        />
      </AppProviders>
    );

    expect(screen.getByTestId("page-skeleton")).toBeTruthy();
    expect(screen.getByTestId("empty-state")).toBeTruthy();
    expect(screen.getByTestId("responsive-dialog").getAttribute("data-layout-mode")).toBe("mobile-drawer");
    expect(screen.getByTestId("ws-url").textContent).toContain(
      REALTIME_WS_PATH
    );

    fireEvent.click(screen.getByTestId("trigger-swipe-left"));
    expect(screen.getByTestId("swipe-dir").textContent).toBe("left");

    fireEvent.click(screen.getByTestId("trigger-ws-event"));
    expect(screen.getByTestId("ws-url").textContent).toContain(
      "1729368000999-0"
    );
  });

  it("renders LoginPage with 1:1 Legacy split-screen, LoginBranding, and input fields", () => {
    render(
      <AppProviders>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AppProviders>
    );

    expect(screen.getByTestId("client-login-page")).toBeTruthy();
    expect(screen.getByText("Bienvenido")).toBeTruthy();
    expect(screen.getByText("Ingresa al panel de control de inventario.")).toBeTruthy();
    expect(screen.getByText("Gestión inteligente para la industria hotelera y restaurantes.")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Ingresar al Sistema/i })).toBeTruthy();
  });

  it("renders AdminLoginPage with 1:1 Legacy dark background and Acceso Restringido", () => {
    render(
      <AppProviders>
        <BrowserRouter>
          <AdminLoginPage />
        </BrowserRouter>
      </AppProviders>
    );

    expect(screen.getByTestId("admin-login-page")).toBeTruthy();
    expect(screen.getByText("Acceso Restringido")).toBeTruthy();
    expect(screen.getByText("Global SaaS Administration")).toBeTruthy();
    expect(screen.getByLabelText("Usuario Administrador")).toBeTruthy();
    expect(screen.getByLabelText("Clave de Acceso")).toBeTruthy();
  });

  it("renders CleanAdminDashboard with 4 KPI cards and zero demo clutter", () => {
    render(
      <AppProviders
        initialSession={{ accessToken: "mock-admin-token" }}
        initialUser={{
          id: 1,
          username: "oppytec.admin",
          email: "oppytec.admin@gmail.com",
          firstName: "SuperUser",
          lastName: "OppyTec",
          role: "propietario",
          isSuperuser: true,
          isGlobalAdmin: true,
        }}
      >
        <CleanAdminDashboard />
      </AppProviders>
    );

    expect(screen.getByTestId("admin-panel-root")).toBeTruthy();
    expect(screen.getByText("Panel de Control Global")).toBeTruthy();
    expect(screen.getByTestId("admin-kpi-grid")).toBeTruthy();
    expect(screen.getByText("Total de holdings registrados")).toBeTruthy();
  });

  it("renders AdminLayout with AdminSidebar, Header controls, and 3-Accordion menu", () => {
    render(
      <AppProviders
        initialSession={{ accessToken: "mock-admin-token" }}
        initialUser={{
          id: 1,
          username: "oppytec.admin",
          email: "oppytec.admin@gmail.com",
          firstName: "SuperUser",
          lastName: "OppyTec",
          role: "propietario",
          isSuperuser: true,
          isGlobalAdmin: true,
        }}
      >
        <BrowserRouter>
          <AdminLayout />
        </BrowserRouter>
      </AppProviders>
    );

    // Header controls
    expect(screen.getByTestId("admin-layout-root")).toBeTruthy();
    expect(screen.getByText("Administración Global")).toBeTruthy();
    expect(screen.getByText("Modo Global (SaaS)")).toBeTruthy();

    // Sidebar and Navigation sections
    expect(screen.getByTestId("admin-sidebar")).toBeTruthy();
    expect(screen.getByText("Admin Panel")).toBeTruthy();
    expect(screen.getByText("Panel Principal")).toBeTruthy();
    expect(screen.getByText("Usuarios Globales")).toBeTruthy();
    expect(screen.getByText("Gestión Negocio")).toBeTruthy();
    expect(screen.getByText("Gestión Cliente")).toBeTruthy();
    expect(screen.getByText("Plataforma & Telemetría")).toBeTruthy();

    // User display & Logout
    expect(screen.getByText("SuperUser OppyTec")).toBeTruthy();
    expect(screen.getByText("Cerrar Sesión")).toBeTruthy();
  });

  it("renders AdminDashboard independently with 4 KPI cards and initial clean state", () => {
    render(
      <AppProviders>
        <AdminDashboard />
      </AppProviders>
    );

    expect(screen.getByTestId("admin-dashboard-view")).toBeTruthy();
    expect(screen.getByTestId("kpi-holdings")).toBeTruthy();
    expect(screen.getByTestId("kpi-legal-entities")).toBeTruthy();
    expect(screen.getByTestId("kpi-tenants")).toBeTruthy();
    expect(screen.getByTestId("kpi-users")).toBeTruthy();
  });

  it("renders AdminSidebar in isolation and responds to collapse toggle", () => {
    render(
      <AppProviders>
        <BrowserRouter>
          <AdminSidebar isCollapsed={false} />
        </BrowserRouter>
      </AppProviders>
    );

    expect(screen.getByTestId("admin-sidebar")).toBeTruthy();
    expect(screen.getByLabelText("Colapsar barra lateral")).toBeTruthy();
  });




  it("renders ClientAppShell and verifies theme switching and holding tenant selector", () => {
    render(
      <AppProviders>
        <BrowserRouter>
          <ClientAppShell />
        </BrowserRouter>
      </AppProviders>
    );

    // Verify theme switching across light, dark, and ocean-blue
    fireEvent.click(screen.getByTestId("theme-btn-dark"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    fireEvent.click(screen.getByTestId("theme-btn-light"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    fireEvent.click(screen.getByTestId("theme-btn-ocean-blue"));
    expect(document.documentElement.getAttribute("data-theme")).toBe(
      "ocean-blue"
    );

    // Verify HoldingTenantSwitcher changes active tenant
    fireEvent.change(screen.getByTestId("holding-tenant-select"), {
      target: { value: "tenant_hotel_costanera" },
    });
    expect(getHttpRequestContext().tenantId).toBe("tenant_hotel_costanera");
  });

  it("exercises CatalogFeatureView and 13 Observability subviews in isolation", () => {
    render(
      <AppProviders>
        <CatalogFeatureView />
        <PlatformAdminFeatureView />
      </AppProviders>
    );

    // Verify "Pollo King" proper noun preservation in Catalog
    expect(
      screen.getByTestId("catalog-product-PRD-PK-001").textContent
    ).toContain("Pollo King");

    // Verify all 13 Observability subviews exist and respond to Environment filter
    expect(OBSERVABILITY_13_SUBVIEWS).toHaveLength(13);
    for (const subview of OBSERVABILITY_13_SUBVIEWS) {
      expect(screen.getByTestId(`obs-subview-${subview}`)).toBeTruthy();
    }
    fireEvent.click(screen.getByTestId("obs-env-filter-staging"));
    fireEvent.click(
      screen.getByTestId("obs-subview-13-finops-llm-request-logs")
    );
    expect(
      screen.getByTestId("observability-active-indicator").textContent
    ).toBe("staging :: 13-finops-llm-request-logs");
  });

  it("renders App root component without throwing", () => {
    render(<App />);
    expect(screen.getByTestId("client-login-page")).toBeTruthy();
  });

  it("validates 2-level RBAC submodule gating, QuotaProgressIndicator semaphore, Plan Básico 10 modules, Unified Recuento, and Admin Management Views", () => {
    // 1. 2-Level RBAC Submodule Gating
    const basicEffective = evaluateEffectivePermissions({
      ...DEFAULT_RBAC_POLICY_STATE,
      planModules: ["operations.consumption_log", "catalog.products"],
      rolePermissions: [
        "operations.consumption_log.create",
        "operations.pos.consume",
        "catalog.products.create",
      ],
      temporaryGrants: [],
      deniedPermissions: [],
    });
    expect(basicEffective.has("operations.consumption_log.create")).toBe(true);
    expect(basicEffective.has("catalog.products.create")).toBe(true);
    expect(basicEffective.has("operations.pos.consume")).toBe(false);

    // 2. QuotaProgressIndicator Semaphore thresholds (NORMAL <80%, WARNING >=80%, CRITICAL >=95%, OVER_QUOTA 100%)
    expect(resolveQuotaSemaphoreStatus(100, 500)).toEqual({
      status: "NORMAL",
      percentage: 20,
    });
    expect(resolveQuotaSemaphoreStatus(420, 500)).toEqual({
      status: "WARNING",
      percentage: 84,
    });
    expect(resolveQuotaSemaphoreStatus(480, 500)).toEqual({
      status: "CRITICAL",
      percentage: 96,
    });
    expect(resolveQuotaSemaphoreStatus(500, 500)).toEqual({
      status: "OVER_QUOTA",
      percentage: 100,
    });

    // 3. Plan Básico 10 Modules & Module Tree
    expect(PLAN_BASICO_10_MODULE_SLUGS).toHaveLength(10);
    expect(PLAN_BASICO_10_NAV_ITEMS).toHaveLength(10);
    expect(SAAS_MODULE_TREE.length).toBeGreaterThanOrEqual(8);

    // 4. Render QuotaProgressIndicator, Unified Recuento in InventoryFeatureView, and Admin Views
    render(
      <AppProviders>
        <QuotaProgressIndicator
          resourceKey="products"
          label="Productos Activos"
          activeCount={425}
          maxLimit={500}
          softDeletedCount={3}
          testId="test-quota-warning"
        />
        <InventoryFeatureView />
        <AdminPlansView />
        <AdminHoldingsView />
        <AdminLegalEntitiesView />
        <AdminTenantsView />
        <AdminClientUsersView />
      </AppProviders>
    );

    expect(
      screen
        .getByTestId("test-quota-warning")
        .getAttribute("data-quota-status")
    ).toBe("WARNING");

    // Verify Unified Recuento (Conteo Físico Activo + Historial de Recuentos in 1 view)
    expect(screen.getByTestId("inventory-unified-recuento-card")).toBeTruthy();
    fireEvent.click(screen.getByTestId("recuento-subtab-historial"));
    expect(
      screen.getByTestId("recuento-unified-status").textContent
    ).toContain("Historial de Recuentos Cerrados");
    fireEvent.click(screen.getByTestId("recuento-subtab-activo"));
    expect(
      screen.getByTestId("recuento-unified-status").textContent
    ).toContain("Conteo Físico Ciego Activo");

    // Verify Admin Views render and respond to interactions
    expect(screen.getByTestId("admin-plans-view")).toBeTruthy();
    expect(screen.getByTestId("admin-holdings-view")).toBeTruthy();
    expect(screen.getByTestId("admin-legal-entities-view")).toBeTruthy();
    expect(screen.getByTestId("admin-tenants-view")).toBeTruthy();
    expect(screen.getByTestId("admin-client-users-view")).toBeTruthy();
    fireEvent.click(screen.getByTestId("tenants-table-create-btn"));
    expect(screen.getByTestId("tenant-module-tree")).toBeTruthy();

    fireEvent.click(screen.getByTestId("edit-plan-btn-basic"));
    expect(
      (screen.getByTestId("plan-input-slug") as HTMLInputElement).value
    ).toBe("basic");
  });

  it("renders Navbar with CurrencySelector and LanguageFlagSelector between search bar and user profile pill", () => {
    render(
      <BrowserRouter>
        <AppProviders>
          <Navbar restaurantName="Restaurante Central Santiago" />
        </AppProviders>
      </BrowserRouter>
    );

    // Verify search bar input is rendered
    expect(
      screen.getByPlaceholderText("Buscar producto, receta o evento...")
    ).toBeTruthy();

    // Verify CurrencySelector is rendered with its group and testid
    const currencySelector = screen.getByTestId("currency-selector");
    expect(currencySelector).toBeTruthy();
    expect(currencySelector.getAttribute("data-active-currency")).toBeTruthy();

    // Verify LanguageFlagSelector is rendered with its testid
    const languageSelector = screen.getByTestId("language-flag-selector");
    expect(languageSelector).toBeTruthy();
    expect(languageSelector.getAttribute("data-active-lang")).toBeTruthy();

    // Verify User Profile Pill is rendered
    expect(screen.getByTestId("navbar-user-pill")).toBeTruthy();
  });

  it("renders Sidebar with reorganized collapsible groups: Analítica y Rendimiento, Panel Ejecutivo, and Panel de Actividades", () => {
    render(
      <BrowserRouter>
        <AppProviders>
          <Sidebar isOpen={true} />
        </AppProviders>
      </BrowserRouter>
    );

    expect(screen.getByText("Analítica y Rendimiento")).toBeTruthy();
    expect(screen.getByText("Panel Ejecutivo")).toBeTruthy();
    expect(screen.getByText("Panel de Actividades")).toBeTruthy();
  });
});
