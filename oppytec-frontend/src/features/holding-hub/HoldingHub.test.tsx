import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { type ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CurrencyProvider } from "@/shared/currency";
import holdingHubEn from "@/shared/i18n/locales/en/holding_hub.json";
import holdingHubEs from "@/shared/i18n/locales/es/holding_hub.json";
import { HoldingHubLayout } from "./HoldingHubLayout";
import { HoldingHubPage } from "./HoldingHubPage";

// Mock Recharts ResponsiveContainer for JSDOM
vi.mock("recharts", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { readonly children: ReactNode }) => (
      <div data-testid="recharts-responsive-container" style={{ width: 800, height: 350 }}>
        {children}
      </div>
    ),
  };
});

function renderWithProviders(ui: ReactNode) {
  return render(
    <MemoryRouter initialEntries={["/holding-hub"]}>
      <CurrencyProvider>
        {ui}
      </CurrencyProvider>
    </MemoryRouter>
  );
}

describe("Holding Hub Enterprise — Suite de Pruebas Frontend (Etapa 2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("1. Renderiza el layout corporativo con Navbar de 80px, Sidebar con 3 pestañas y 4 KPIs glassmorphism", () => {
    renderWithProviders(<HoldingHubLayout />);

    // Executive Navbar (80px)
    const navbar = screen.getByTestId("holding-navbar");
    expect(navbar).toBeInTheDocument();
    expect(navbar.className).toContain("min-h-[80px]");
    expect(screen.getByTestId("holding-enterprise-badge")).toHaveTextContent("ENTERPRISE CORP");

    // Sidebar with 4 navigation tabs
    expect(screen.getByTestId("holding-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("holding-tab-central")).toBeInTheDocument();
    expect(screen.getByTestId("holding-tab-briefing")).toBeInTheDocument();
    expect(screen.getByTestId("holding-tab-planes")).toBeInTheDocument();
    expect(screen.getByTestId("holding-tab-creditos")).toBeInTheDocument();
    expect(screen.getByTestId("sidebar-credit-pool-widget")).toBeInTheDocument();

    // 4 Glassmorphism KPIs in Central view
    expect(screen.getByTestId("holding-kpi-total_sales")).toBeInTheDocument();
    expect(screen.getByTestId("holding-kpi-inventory_value")).toBeInTheDocument();
    expect(screen.getByTestId("holding-kpi-waste_pct")).toBeInTheDocument();
    expect(screen.getByTestId("holding-kpi-ai_credits")).toBeInTheDocument();

    // Branch Cards rendered
    expect(screen.getByTestId("holding-tenant-card-tenant_rest_central")).toBeInTheDocument();
    expect(screen.getByTestId("holding-tenant-card-tenant_hotel_costanera")).toBeInTheDocument();
    expect(screen.getByTestId("holding-tenant-card-tenant_dark_kitchen_norte")).toBeInTheDocument();
  });

  it("2. Soporta cambio de los 3 temas (ocean-blue, dark, light) y colapso de sidebar", () => {
    renderWithProviders(<HoldingHubLayout />);

    const themeToggle = screen.getByTestId("holding-theme-toggle");
    const layout = screen.getByTestId("holding-hub-layout");

    // Initial theme (ocean-blue default)
    expect(layout.getAttribute("data-theme")).toBe("ocean-blue");

    // Toggle to next theme
    fireEvent.click(themeToggle);
    expect(layout.getAttribute("data-theme")).toBe("light");

    fireEvent.click(themeToggle);
    expect(layout.getAttribute("data-theme")).toBe("dark");

    // Sidebar collapse and expand toggle
    const collapseBtn = screen.getByTestId("holding-sidebar-collapse-btn");
    fireEvent.click(collapseBtn);
    expect(screen.getByTestId("sidebar-credit-pool-mini")).toBeInTheDocument();

    fireEvent.click(collapseBtn);
    expect(screen.getByTestId("sidebar-credit-pool-widget")).toBeInTheDocument();
  });

  it("3. Filtra sucursales en tiempo real y abre modal de detalle con cambio de tenant", () => {
    renderWithProviders(<HoldingHubLayout />);

    const searchInput = screen.getByTestId("holding-tenants-search");
    fireEvent.change(searchInput, { target: { value: "Costanera" } });

    // Only Costanera should remain
    expect(screen.getByTestId("holding-tenant-card-tenant_hotel_costanera")).toBeInTheDocument();
    expect(screen.queryByTestId("holding-tenant-card-tenant_rest_central")).not.toBeInTheDocument();

    // Open branch detail modal
    const detailBtn = screen.getByTestId("tenant-detail-btn-tenant_hotel_costanera");
    fireEvent.click(detailBtn);

    const modal = screen.getByTestId("tenant-detail-modal");
    expect(modal).toBeInTheDocument();
    expect(modal).toHaveTextContent("Hotel & Buffet Costanera");

    // Close modal
    const closeBtn = screen.getByTestId("tenant-detail-modal-close");
    fireEvent.click(closeBtn);
    expect(screen.queryByTestId("tenant-detail-modal")).not.toBeInTheDocument();

    // Enter tenant button
    const enterBtn = screen.getByTestId("tenant-enter-btn-tenant_hotel_costanera");
    fireEvent.click(enterBtn);
  });

  it("4. Navega a la pestaña de Planes SaaS y procesa cambio de plan comercial", async () => {
    renderWithProviders(<HoldingHubLayout />);

    // Click tab "planes"
    const plansTab = screen.getByTestId("holding-tab-planes");
    fireEvent.click(plansTab);

    // Verify plans section rendered
    expect(screen.getByTestId("holding-plans-section")).toBeInTheDocument();
    expect(screen.getByTestId("saas-plan-card-starter")).toBeInTheDocument();
    expect(screen.getByTestId("saas-plan-card-business")).toBeInTheDocument();
    expect(screen.getByTestId("saas-plan-card-enterprise")).toBeInTheDocument();

    // Active plan badge on Business
    expect(screen.getByTestId("active-plan-badge-business")).toBeInTheDocument();
    expect(screen.getByTestId("plan-action-active-business")).toBeInTheDocument();

    // Recommended badge on Business
    expect(screen.getByTestId("recommended-plan-badge-business")).toBeInTheDocument();

    // Click switch to Enterprise plan
    const subscribeEnterpriseBtn = screen.getByTestId("plan-action-subscribe-enterprise");
    fireEvent.click(subscribeEnterpriseBtn);

    // Confirmation modal
    const modal = screen.getByTestId("plan-change-modal");
    expect(modal).toBeInTheDocument();

    // Toggle effective mode radio
    const nextCycleRadio = screen.getByTestId("plan-effective-next-cycle");
    fireEvent.click(nextCycleRadio);

    // Fill reason
    const reasonInput = screen.getByTestId("plan-change-reason-input");
    fireEvent.change(reasonInput, { target: { value: "Ampliación de cadena" } });

    // Confirm plan change
    const confirmBtn = screen.getByTestId("plan-change-confirm-btn");
    fireEvent.click(confirmBtn);

    await waitFor(
      () => {
        expect(screen.getByTestId("plan-change-success-banner")).toBeInTheDocument();
      },
      { timeout: 4000 }
    );
  });

  it("5. Navega a la pestaña de Créditos IA, cambia alcance, rangos del gráfico y compra créditos", async () => {
    renderWithProviders(<HoldingHubLayout />);

    // Click tab "creditos"
    const creditsTab = screen.getByTestId("holding-tab-creditos");
    fireEvent.click(creditsTab);

    // Verify credits section rendered
    expect(screen.getByTestId("holding-credits-section")).toBeInTheDocument();
    expect(screen.getByTestId("credits-kpi-available")).toBeInTheDocument();
    expect(screen.getByTestId("credits-kpi-consumed")).toBeInTheDocument();
    expect(screen.getByTestId("credits-kpi-tokens")).toBeInTheDocument();
    expect(screen.getByTestId("credits-kpi-requests")).toBeInTheDocument();

    // Chart and range controls
    expect(screen.getByTestId("credits-usage-chart-card")).toBeInTheDocument();
    const range7Btn = screen.getByTestId("credits-chart-range-7");
    fireEvent.click(range7Btn);

    // Scope change to individual tenant
    const scopeSelect = screen.getByTestId("credits-scope-select");
    fireEvent.change(scopeSelect, { target: { value: "tenant_rest_central" } });

    // Open Buy Credits modal
    const buyTriggerBtn = screen.getByTestId("credits-buy-trigger-btn");
    fireEvent.click(buyTriggerBtn);

    expect(screen.getByTestId("credits-buy-modal")).toBeInTheDocument();

    // Select 5,000 package
    const pkg5k = screen.getByTestId("credit-pkg-5000");
    fireEvent.click(pkg5k);
    expect(screen.getByTestId("credits-buy-total-price")).toHaveTextContent("$75.000");

    // Confirm purchase
    const confirmBuyBtn = screen.getByTestId("credits-buy-confirm-btn");
    fireEvent.click(confirmBuyBtn);

    await waitFor(() => {
      expect(screen.getByTestId("credits-buy-success-alert")).toBeInTheDocument();
    });
  });

  it("6. Modal de distribución de créditos: conmuta entre shared y allocated con sliders y validación de tope", async () => {
    renderWithProviders(<HoldingHubLayout />);

    // Go to credits tab
    fireEvent.click(screen.getByTestId("holding-tab-creditos"));

    // Open distribution modal
    const distTriggerBtn = screen.getByTestId("credits-distribute-trigger-btn");
    fireEvent.click(distTriggerBtn);

    expect(screen.getByTestId("credits-distribution-modal")).toBeInTheDocument();

    // Switch mode to shared
    const sharedBtn = screen.getByTestId("dist-mode-shared-btn");
    fireEvent.click(sharedBtn);

    // Switch back to allocated
    const allocatedBtn = screen.getByTestId("dist-mode-allocated-btn");
    fireEvent.click(allocatedBtn);

    // Adjust slider of tenant_rest_central to exceed total pool (e.g. 25000)
    const sliderInput = screen.getByTestId("tenant-slider-input-tenant_rest_central");
    fireEvent.change(sliderInput, { target: { value: "25000" } });

    // Warning alert should appear
    expect(screen.getByTestId("credits-over-warning")).toBeInTheDocument();

    // Save button should be disabled when over-allocated
    const saveBtn = screen.getByTestId("credits-dist-save-btn");
    expect(saveBtn).toBeDisabled();

    // Adjust back within budget (e.g. 5000)
    fireEvent.change(sliderInput, { target: { value: "5000" } });
    expect(screen.queryByTestId("credits-over-warning")).not.toBeInTheDocument();
    expect(saveBtn).not.toBeDisabled();

    // Save
    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(screen.getByTestId("credits-dist-success-alert")).toBeInTheDocument();
    });
  });

  it("7. TenantCommandPalette responde al atajo Cmd+K y permite seleccionar sucursal", () => {
    renderWithProviders(<HoldingHubLayout />);

    // Trigger via keyboard shortcut Cmd+K
    fireEvent.keyDown(window, { key: "k", metaKey: true });

    const palette = screen.getByTestId("tenant-command-palette-modal");
    expect(palette).toBeInTheDocument();

    const input = screen.getByTestId("tenant-command-input");
    expect(input).toBeInTheDocument();

    // Filter by dark kitchen
    fireEvent.change(input, { target: { value: "Kitchen" } });
    expect(screen.getByTestId("tenant-command-option-tenant_dark_kitchen_norte")).toBeInTheDocument();

    // Select with Enter
    fireEvent.keyDown(window, { key: "Enter" });
    expect(screen.queryByTestId("tenant-command-palette-modal")).not.toBeInTheDocument();
  });

  it("8. HoldingHubPage renderiza limpiamente como página principal", () => {
    renderWithProviders(<HoldingHubPage />);
    expect(screen.getByTestId("holding-hub-layout")).toBeInTheDocument();
  });

  it("9. Renderiza la tarjeta de Oppy Daily Holding Briefing con los 2 párrafos inteligentes, aciertos y alertas en su pestaña dedicada", () => {
    renderWithProviders(<HoldingHubLayout />);

    // Central view does not contain the briefing card (clean viewport for KPIs & branches)
    expect(screen.queryByTestId("holding-ai-briefing-card")).not.toBeInTheDocument();

    // Navigate to dedicated briefing tab
    const briefingTab = screen.getByTestId("holding-tab-briefing");
    fireEvent.click(briefingTab);

    expect(screen.getByTestId("holding-briefing-section")).toBeInTheDocument();
    const briefingCard = screen.getByTestId("holding-ai-briefing-card");
    expect(briefingCard).toBeInTheDocument();

    // Check Safety Cap badge
    const safetyBadge = screen.getByTestId("holding-ai-briefing-safety-badge");
    expect(safetyBadge).toBeInTheDocument();
    expect(safetyBadge).toHaveTextContent("Salud Operativa Óptima");

    // Check 2 smart executive paragraphs
    const p0 = screen.getByTestId("holding-ai-briefing-paragraph-0");
    expect(p0).toBeInTheDocument();
    expect(p0).toHaveTextContent("Ventas & Merma");
    expect(p0).toHaveTextContent("184.500.000");

    const p1 = screen.getByTestId("holding-ai-briefing-paragraph-1");
    expect(p1).toBeInTheDocument();
    expect(p1).toHaveTextContent("Créditos IA & Safety Cap");
    expect(p1).toHaveTextContent("14.250");

    // Check operational achievements and cost alerts
    expect(screen.getByTestId("holding-ai-briefing-achievements")).toBeInTheDocument();
    expect(screen.getByTestId("holding-ai-briefing-alerts")).toBeInTheDocument();
  });

  it("10. Soporta colapso/expansión del Briefing de IA y navegación rápida a gestión de créditos", () => {
    renderWithProviders(<HoldingHubLayout />);

    // Navigate to briefing tab
    const briefingTab = screen.getByTestId("holding-tab-briefing");
    fireEvent.click(briefingTab);

    const toggleBtn = screen.getByTestId("holding-ai-briefing-toggle");
    expect(screen.getByTestId("holding-ai-briefing-content")).toBeInTheDocument();

    // Collapse
    fireEvent.click(toggleBtn);
    expect(screen.queryByTestId("holding-ai-briefing-content")).not.toBeInTheDocument();

    // Expand again
    fireEvent.click(toggleBtn);
    expect(screen.getByTestId("holding-ai-briefing-content")).toBeInTheDocument();

    // Action button navigates to creditos tab
    const manageCreditsBtn = screen.getByTestId("holding-briefing-manage-credits-btn");
    fireEvent.click(manageCreditsBtn);

    // Verify credits section is now active
    expect(screen.getByTestId("holding-credits-section")).toBeInTheDocument();
  });

  it("11. Auditoría i18n: 100% paridad de claves JSON entre locales/es y locales/en para holding_hub", () => {
    function extractLeafKeys(obj: Record<string, unknown>, prefix = ""): string[] {
      const keys: string[] = [];
      for (const [k, v] of Object.entries(obj)) {
        const fullKey = prefix ? `${prefix}.${k}` : k;
        if (v && typeof v === "object" && !Array.isArray(v)) {
          keys.push(...extractLeafKeys(v as Record<string, unknown>, fullKey));
        } else {
          keys.push(fullKey);
        }
      }
      return keys.sort();
    }

    const esKeys = extractLeafKeys(holdingHubEs as Record<string, unknown>);
    const enKeys = extractLeafKeys(holdingHubEn as Record<string, unknown>);

    expect(esKeys.length).toBeGreaterThan(150);
    expect(enKeys.length).toEqual(esKeys.length);

    const missingInEn = esKeys.filter((k) => !enKeys.includes(k));
    const missingInEs = enKeys.filter((k) => !esKeys.includes(k));

    expect(missingInEn).toEqual([]);
    expect(missingInEs).toEqual([]);
  });

  it("12. Auditoría Multi-Moneda FX: CurrencySelector conmuta reactivamente ventas consolidadas a CLP, USD, EUR y BRL con tasas exactas", () => {
    renderWithProviders(<HoldingHubLayout />);

    const salesKpi = screen.getByTestId("holding-kpi-total_sales");
    expect(salesKpi).toBeInTheDocument();

    // Default currency CLP: 184.500.000 CLP
    expect(salesKpi).toHaveTextContent("$184.500.000");

    // Open CurrencySelector dropdown
    const currencySelector = screen.getByTestId("currency-selector");
    const currencyTriggerBtn = currencySelector.querySelector("button")!;
    fireEvent.click(currencyTriggerBtn);

    // Select USD (rate: 960 CLP/USD -> 184,500,000 / 960 = 192,187.50)
    const usdOption = screen.getByTestId("currency-option-USD");
    fireEvent.click(usdOption);
    expect(salesKpi).toHaveTextContent("US$192,187.50");

    // Select EUR (rate: 1040 CLP/EUR -> 184,500,000 / 1040 = 177,403.85)
    fireEvent.click(currencyTriggerBtn);
    const eurOption = screen.getByTestId("currency-option-EUR");
    fireEvent.click(eurOption);
    expect(salesKpi).toHaveTextContent("€177.403,85");

    // Select BRL (rate: 192 CLP/BRL -> 184,500,000 / 192 = 960,937.50)
    fireEvent.click(currencyTriggerBtn);
    const brlOption = screen.getByTestId("currency-option-BRL");
    fireEvent.click(brlOption);
    expect(salesKpi).toHaveTextContent("R$960.937,50");

    // Switch back to CLP
    fireEvent.click(currencyTriggerBtn);
    const clpOption = screen.getByTestId("currency-option-CLP");
    fireEvent.click(clpOption);
    expect(salesKpi).toHaveTextContent("$184.500.000");
  });

  it("13. Regla Pollo King: Nombres de holding, sucursales y esquemas físicos son estrictamente inmutables (translatable = False)", () => {
    renderWithProviders(<HoldingHubLayout />);

    // Holding Corporate Name
    expect(screen.getByTestId("sidebar-holding-name")).toHaveTextContent(
      "Holding Gastronómico Sur SpA"
    );

    // Tenant commercial names in Central view
    expect(
      screen.getByTestId("holding-tenant-card-tenant_rest_central")
    ).toHaveTextContent("Restaurante Central Santiago");
    expect(
      screen.getByTestId("holding-tenant-card-tenant_hotel_costanera")
    ).toHaveTextContent("Hotel & Buffet Costanera");
    expect(
      screen.getByTestId("holding-tenant-card-tenant_dark_kitchen_norte")
    ).toHaveTextContent("Comisariato & Dark Kitchen Norte");

    // Schemas
    expect(
      screen.getByTestId("holding-tenant-card-tenant_rest_central")
    ).toHaveTextContent("tenant_rest_central");
    expect(
      screen.getByTestId("holding-tenant-card-tenant_hotel_costanera")
    ).toHaveTextContent("tenant_hotel_costanera");

    // Master RUT
    expect(screen.getByTestId("holding-sidebar")).toHaveTextContent("76.543.210-K");
  });

  it("14. Scroll-to-Top: conmuta posición superior instantáneamente en cambios de tab y navegación", () => {
    const scrollToSpy = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    renderWithProviders(<HoldingHubLayout />);

    // Switch tab to briefing
    fireEvent.click(screen.getByTestId("holding-tab-briefing"));
    expect(scrollToSpy).toHaveBeenCalledWith(
      expect.objectContaining({ top: 0, left: 0, behavior: "instant" })
    );

    scrollToSpy.mockRestore();
  });
});
