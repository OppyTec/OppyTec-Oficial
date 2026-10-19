import { fireEvent, render, screen } from "@testing-library/react";
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
  PermissionsProvider,
} from "@/shared/auth/usePermissions";
import {
  EmptyState,
  ErrorBoundary,
  PageSkeleton,
} from "@/shared/components/feedback";
import {
  AdaptiveDataView,
  GASTRONOMIC_ICONS,
  NumericInput,
  OFFICIAL_THEMES,
  PRESET_COLORS,
  ResponsiveDialog,
} from "@/shared/components/ui";
import {
  applyDocumentTheme,
  MOBILE_BREAKPOINT_PX,
  THEME_STORAGE_KEY,
  useIsMobile,
  useSwipeNavigation,
  useWebSocket,
} from "@/shared/hooks";
import { convertThreeLayerQuantity, formatOperationalDate } from "@/shared/lib";
import {
  REALTIME_WS_PATH,
  useRealtimeContext,
} from "@/shared/realtime/RealtimeProvider";
import { OBSERVABILITY_13_SUBVIEWS } from "@/features/platform-admin";
import { App } from "./App";

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

describe("OppyTec v2.0 — Phase 5 Frontend Architecture & 10 Feature Modules", () => {
  it("validates 3 Legacy DNA themes, 42 preset colors, and 49 gastronomic icons", () => {
    expect(OFFICIAL_THEMES).toEqual(["light", "dark", "ocean-blue"]);
    expect(PRESET_COLORS).toHaveLength(42);
    expect(GASTRONOMIC_ICONS).toHaveLength(49);
    expect(MOBILE_BREAKPOINT_PX).toBe(768);
    expect(THEME_STORAGE_KEY).toBe("oppytec_theme");

    applyDocumentTheme("ocean-blue");
    expect(document.documentElement.getAttribute("data-theme")).toBe(
      "ocean-blue"
    );
    expect(document.documentElement.classList.contains("ocean-blue")).toBe(
      true
    );

    applyDocumentTheme("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("evaluates 3-level RBAC intersection M_Plan ∩ ((P_Role ∪ P_Temp) - P_Deny) and <Can>", () => {
    expect(isValidThreeLevelPermission("inventory.mermas.approve")).toBe(true);
    expect(isValidThreeLevelPermission("invalid_two.levels")).toBe(false);

    const effective = evaluateEffectivePermissions(
      {
        ...DEFAULT_RBAC_POLICY_STATE,
        deniedPermissions: ["inventory.mermas.approve"],
      },
      "2026-10-19T00:00:00Z"
    );
    expect(effective.has("inventory.mermas.approve")).toBe(false);
    expect(effective.has("inventory.mermas.override_threshold")).toBe(true);

    render(
      <PermissionsProvider
        initialPolicy={{
          ...DEFAULT_RBAC_POLICY_STATE,
          deniedPermissions: ["catalog.products.delete"],
        }}
      >
        <Can perform="catalog.products.create">
          <span>Create Allowed</span>
        </Can>
        <Can perform="catalog.products.delete" showDeniedBadge>
          <span>Delete Allowed</span>
        </Can>
      </PermissionsProvider>
    );

    expect(
      screen.getByTestId("rbac-allowed-catalog.products.create")
    ).toBeTruthy();
    expect(
      screen.getByTestId("rbac-denied-catalog.products.delete")
    ).toBeTruthy();
  });

  it("builds canonical API headers, queryKeys, and 3-layer unit conversions", async () => {
    setHttpRequestContext({
      holdingId: "holding-gastro-sur",
      tenantId: "tenant_rest_central",
      warehouseId: "bod-camara-fria",
      accessToken: "jwt-test-token",
    });
    expect(getHttpRequestContext().warehouseId).toBe("bod-camara-fria");

    const headers = buildApiHeaders();
    expect(headers["X-Holding-ID"]).toBe("holding-gastro-sur");
    expect(headers["X-Tenant-ID"]).toBe("tenant_rest_central");
    expect(headers["X-Warehouse-ID"]).toBe("bod-camara-fria");
    expect(headers["X-Trace-ID"]).toHaveLength(32);
    expect(headers.Authorization).toBe("Bearer jwt-test-token");
    expect(resolveApiEndpointUrl("/health")).toContain("/api/v1/health");

    const fallbackResp = await apiRequest("/health", {
      fallbackData: { status: "ok" },
    });
    expect(fallbackResp.data.status).toBe("ok");

    expect(queryKeys.auth.session()).toEqual(["oppytec", "auth", "session"]);
    expect(queryKeys.rbac.roles("t1")[3]).toBe("t1");
    expect(queryKeys.audit.forensicLogs("t1")[3]).toBe("t1");
    expect(queryKeys.catalog.products("t1")[3]).toBe("t1");
    expect(
      queryKeys.inventory.stock({ holdingId: "h1", tenantId: "t1" })[4]
    ).toBe("t1");
    expect(queryKeys.recipes.escandallos("t1")[3]).toBe("t1");
    expect(queryKeys.procurement.invoices("t1")[3]).toBe("t1");
    expect(queryKeys.operations.alerts("t1")[3]).toBe("t1");
    expect(queryKeys.analytics.kpis("t1", "2026-10")[4]).toBe("2026-10");
    expect(queryKeys.oppyfy.credits("t1")[3]).toBe("t1");
    expect(
      queryKeys.platformAdmin.observability("01-health-overview", "local")[3]
    ).toBe("01-health-overview");

    const grams = convertThreeLayerQuantity("1.5", "purchase", "recipe", {
      code: "BOX-KG-G",
      purchaseUnit: "Box",
      storageUnit: "kg",
      recipeUnit: "g",
      purchaseToStorageFactor: "10",
      storageToRecipeFactor: "1000",
    });
    expect(grams).toBe("15000.0000");
    expect(formatOperationalDate("2026-10-19T12:00:00Z", "es")).toBe(
      "19-10-2026"
    );
  });

  it("renders shared UI, feedback components, and WebSocket RealtimeProvider without polling", () => {
    let dialogOpen = true;
    render(
      <AppProviders>
        <HooksHarness />
        <PageSkeleton rows={2} />
        <EmptyState />
        <ErrorBoundary>
          <div>Protected Child</div>
        </ErrorBoundary>
        <ResponsiveDialog
          open={dialogOpen}
          onClose={() => {
            dialogOpen = false;
          }}
          title="Test Modal"
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

  it("renders App with all 10 feature modules, 13 Observability subviews, and Pollo King preservation", () => {
    render(<App />);

    // Verify all 10 feature modules are rendered in the shell
    expect(screen.getByTestId("feature-analytics")).toBeTruthy();
    expect(screen.getByTestId("feature-catalog")).toBeTruthy();
    expect(screen.getByTestId("feature-inventory")).toBeTruthy();
    expect(screen.getByTestId("feature-recipes")).toBeTruthy();
    expect(screen.getByTestId("feature-procurement")).toBeTruthy();
    expect(screen.getByTestId("feature-operations")).toBeTruthy();
    expect(screen.getByTestId("feature-oppyfy")).toBeTruthy();
    expect(screen.getByTestId("feature-rbac-and-audit")).toBeTruthy();
    expect(screen.getByTestId("feature-platform-admin")).toBeTruthy();
    expect(screen.getByTestId("feature-auth")).toBeTruthy();

    // Verify "Pollo King" proper noun preservation in Catalog
    expect(
      screen.getByTestId("catalog-product-PRD-PK-001").textContent
    ).toContain("Pollo King");

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
});
