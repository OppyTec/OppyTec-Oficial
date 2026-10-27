import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppProviders } from "@/app/providers";
import * as httpClient from "@/shared/api/httpClient";
import type { AuthenticatedUser, AuthSession } from "@/shared/auth/usePermissions";
import { AdminLayout } from "../AdminLayout";
import { AdminSidebar } from "../AdminSidebar";
import { PlansPage } from "../plans/PlansPage";
import { TokenConsumptionPage } from "../tokens/TokenConsumptionPage";
import {
  MOCK_SAAS_POLICY,
  MOCK_SYSTEM_PLANS,
  MOCK_TOKEN_CONSUMPTION,
} from "../types";

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, layout: _l, layoutId: _li, initial: _i, animate: _a, exit: _e, transition: _t, ...props }: any) => (
      <div {...props}>{children}</div>
    ),
    button: ({ children, layout: _l, layoutId: _li, initial: _i, animate: _a, exit: _e, transition: _t, whileHover: _wh, whileTap: _wt, ...props }: any) => (
      <button {...props}>{children}</button>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

vi.mock("sonner", async (importOriginal) => {
  const actual = await importOriginal<typeof import("sonner")>();
  return {
    ...actual,
    toast: {
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
      warning: vi.fn(),
    },
    Toaster: () => <div data-testid="sonner-toaster" />,
  };
});

const mockAdminUser: AuthenticatedUser = {
  id: 1,
  username: "global_admin",
  email: "admin@oppytec.dev",
  firstName: "Super",
  lastName: "Admin",
  role: "superadmin",
  isSuperuser: true,
  isGlobalAdmin: true,
};

const mockAdminSession: AuthSession = {
  accessToken: "mock-jwt-token-admin",
};

describe("AdminNavigation — Navegación Canónica de Planes y Consumo de Tokens (Fase 7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string, options?: any) => {
      if (url.includes("/plans")) {
        return {
          data: MOCK_SYSTEM_PLANS,
          traceId: "test-trace-plans",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      if (url.includes("/ai-credits/policy")) {
        return {
          data: MOCK_SAAS_POLICY,
          traceId: "test-trace-policy",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      if (url.includes("/token-consumption")) {
        return {
          data: MOCK_TOKEN_CONSUMPTION,
          traceId: "test-trace-tokens",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      if (url.includes("/tenancy/tenants")) {
        return {
          data: [
            { schema_name: "tenant_rest_central", display_name: "Rest Central" },
          ],
          traceId: "test-trace-tenants",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
      return {
        data: options?.fallbackData ?? [],
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      };
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe("7.2 Renderizado y Badges en AdminSidebar", () => {
    it("renderiza los enlaces de Planes y Consumo de Tokens con sus badges informativos", async () => {
      await act(async () => {
        render(
          <AppProviders initialSession={mockAdminSession} initialUser={mockAdminUser}>
            <MemoryRouter initialEntries={["/admin"]}>
              <AdminSidebar />
            </MemoryRouter>
          </AppProviders>
        );
      });

      // Validar enlace a Planes
      const plansLink = screen.getByTestId("admin-nav-item-plans");
      expect(plansLink).toBeTruthy();
      expect(plansLink.getAttribute("href")).toBe("/admin/plans");
      expect(screen.getByTestId("badge-saas")).toBeTruthy();
      expect(screen.getByTestId("badge-saas").textContent).toBe("SaaS");

      // Validar enlace a Consumo de Tokens
      const tokensLink = screen.getByTestId("admin-nav-item-token-consumption");
      expect(tokensLink).toBeTruthy();
      expect(tokensLink.getAttribute("href")).toBe("/admin/token-consumption");
      expect(screen.getByTestId("badge-finops")).toBeTruthy();
      expect(screen.getByTestId("badge-finops").textContent).toBe("FinOps");
    });

    it("detecta el estado visual activo cuando location es /admin/plans", async () => {
      await act(async () => {
        render(
          <AppProviders initialSession={mockAdminSession} initialUser={mockAdminUser}>
            <MemoryRouter initialEntries={["/admin/plans"]}>
              <AdminSidebar />
            </MemoryRouter>
          </AppProviders>
        );
      });

      const plansLink = screen.getByTestId("admin-nav-item-plans");
      const tokensLink = screen.getByTestId("admin-nav-item-token-consumption");

      // En /admin/plans, el enlace de Planes debe tener el indicador visual activo
      const activeIndicator = plansLink.querySelector('[data-testid="active-nav-indicator"]');
      expect(activeIndicator).toBeTruthy();

      // El enlace de Tokens NO debe tener el indicador activo
      const tokensActiveIndicator = tokensLink.querySelector('[data-testid="active-nav-indicator"]');
      expect(tokensActiveIndicator).toBeNull();
    });

    it("detecta el estado visual activo cuando location es /admin/token-consumption", async () => {
      await act(async () => {
        render(
          <AppProviders initialSession={mockAdminSession} initialUser={mockAdminUser}>
            <MemoryRouter initialEntries={["/admin/token-consumption"]}>
              <AdminSidebar />
            </MemoryRouter>
          </AppProviders>
        );
      });

      const plansLink = screen.getByTestId("admin-nav-item-plans");
      const tokensLink = screen.getByTestId("admin-nav-item-token-consumption");

      // En /admin/token-consumption, el enlace de Tokens debe tener el indicador visual activo
      const tokensActiveIndicator = tokensLink.querySelector('[data-testid="active-nav-indicator"]');
      expect(tokensActiveIndicator).toBeTruthy();

      // El enlace de Planes NO debe tener el indicador activo
      const plansActiveIndicator = plansLink.querySelector('[data-testid="active-nav-indicator"]');
      expect(plansActiveIndicator).toBeNull();
    });

    it("no activa ninguno de los dos sub-enlaces cuando se navega a /admin/users", async () => {
      await act(async () => {
        render(
          <AppProviders initialSession={mockAdminSession} initialUser={mockAdminUser}>
            <MemoryRouter initialEntries={["/admin/users"]}>
              <AdminSidebar />
            </MemoryRouter>
          </AppProviders>
        );
      });

      const plansLink = screen.getByTestId("admin-nav-item-plans");
      const tokensLink = screen.getByTestId("admin-nav-item-token-consumption");

      expect(plansLink.querySelector('[data-testid="active-nav-indicator"]')).toBeNull();
      expect(tokensLink.querySelector('[data-testid="active-nav-indicator"]')).toBeNull();
    });
  });

  describe("7.1 y 7.4 Integración de Rutas dentro de AdminLayout", () => {
    it("monta PlansPage canónicamente cuando la ruta es /admin/plans", async () => {
      await act(async () => {
        render(
          <AppProviders initialSession={mockAdminSession} initialUser={mockAdminUser}>
            <MemoryRouter initialEntries={["/admin/plans"]}>
              <Routes>
                <Route path="/admin" element={<AdminLayout />}>
                  <Route path="plans" element={<PlansPage />} />
                  <Route path="token-consumption" element={<TokenConsumptionPage />} />
                </Route>
              </Routes>
            </MemoryRouter>
          </AppProviders>
        );
      });

      // Verifica que el contenedor de PlansPage se montó
      await waitFor(() => {
        expect(screen.getByTestId("plans-page")).toBeTruthy();
      });

      // Verifica que el sidebar dentro del layout refleja el estado activo
      const plansLink = screen.getByTestId("admin-nav-item-plans");
      expect(plansLink.querySelector('[data-testid="active-nav-indicator"]')).toBeTruthy();
    });

    it("monta TokenConsumptionPage canónicamente cuando la ruta es /admin/token-consumption", async () => {
      await act(async () => {
        render(
          <AppProviders initialSession={mockAdminSession} initialUser={mockAdminUser}>
            <MemoryRouter initialEntries={["/admin/token-consumption"]}>
              <Routes>
                <Route path="/admin" element={<AdminLayout />}>
                  <Route path="plans" element={<PlansPage />} />
                  <Route path="token-consumption" element={<TokenConsumptionPage />} />
                </Route>
              </Routes>
            </MemoryRouter>
          </AppProviders>
        );
      });

      // Verifica que el contenedor de TokenConsumptionPage se montó
      await waitFor(() => {
        expect(screen.getByTestId("token-consumption-page")).toBeTruthy();
      });

      // Verifica que el sidebar dentro del layout refleja el estado activo
      const tokensLink = screen.getByTestId("admin-nav-item-token-consumption");
      expect(tokensLink.querySelector('[data-testid="active-nav-indicator"]')).toBeTruthy();
    });

    it("permite navegar de /admin/plans a /admin/token-consumption mediante clic en AdminSidebar", async () => {
      await act(async () => {
        render(
          <AppProviders initialSession={mockAdminSession} initialUser={mockAdminUser}>
            <MemoryRouter initialEntries={["/admin/plans"]}>
              <Routes>
                <Route path="/admin" element={<AdminLayout />}>
                  <Route path="plans" element={<PlansPage />} />
                  <Route path="token-consumption" element={<TokenConsumptionPage />} />
                </Route>
              </Routes>
            </MemoryRouter>
          </AppProviders>
        );
      });

      await waitFor(() => {
        expect(screen.getByTestId("plans-page")).toBeTruthy();
      });

      // Hacer clic en el enlace de Consumo de Tokens en el sidebar
      const tokensLink = screen.getByTestId("admin-nav-item-token-consumption");
      await act(async () => {
        fireEvent.click(tokensLink);
      });

      // Verificar que se desmontó PlansPage y se montó TokenConsumptionPage
      await waitFor(() => {
        expect(screen.getByTestId("token-consumption-page")).toBeTruthy();
      });
      expect(screen.queryByTestId("plans-page")).toBeNull();
    });

    it("permite navegar desde TokenConsumptionPage hacia /admin/plans mediante el botón de enlace directo", async () => {
      await act(async () => {
        render(
          <AppProviders initialSession={mockAdminSession} initialUser={mockAdminUser}>
            <MemoryRouter initialEntries={["/admin/token-consumption"]}>
              <Routes>
                <Route path="/admin" element={<AdminLayout />}>
                  <Route path="plans" element={<PlansPage />} />
                  <Route path="token-consumption" element={<TokenConsumptionPage />} />
                </Route>
              </Routes>
            </MemoryRouter>
          </AppProviders>
        );
      });

      await waitFor(() => {
        expect(screen.getByTestId("token-consumption-page")).toBeTruthy();
      });

      // Hacer clic en el enlace interno configure-plans-link
      const configPlansLink = screen.getByTestId("configure-plans-link");
      await act(async () => {
        fireEvent.click(configPlansLink);
      });

      // Verificar que se monta PlansPage
      await waitFor(() => {
        expect(screen.getByTestId("plans-page")).toBeTruthy();
      });
      expect(screen.queryByTestId("token-consumption-page")).toBeNull();
    });
  });
});
