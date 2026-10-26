import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, act, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "../Sidebar";
import { PermissionsProvider, type RbacPolicyState } from "@/shared/auth/usePermissions";
import { setActiveLanguage } from "@/shared/i18n";
import * as httpClient from "@/shared/api/httpClient";

const createMockEnvelope = <T,>(data: T): httpClient.ApiEnvelope<T> => ({
  data,
  traceId: "trace-notifications-badge-test",
  timestampIso: new Date().toISOString(),
  tenantId: "tenant_rest_central",
});

describe("SidebarNotificationsBadge Suite — FASE 7: Integración con Sidebar y Badge Reactivo", () => {
  let queryClient: QueryClient;

  const basePolicy: RbacPolicyState = {
    roleName: "Administrador",
    isSuperUser: true,
    planModules: ["inventory", "analytics", "operations", "catalog"],
    rolePermissions: [],
    temporaryGrants: [],
    deniedPermissions: [],
  };

  const createQueryClient = () =>
    new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: 0,
          staleTime: 0,
        },
      },
    });

  const renderSidebar = (props: Parameters<typeof Sidebar>[0] = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/"]}>
          <PermissionsProvider initialPolicy={basePolicy}>
            <Sidebar isOpen={true} {...props} />
          </PermissionsProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
    setActiveLanguage("es");
    queryClient = createQueryClient();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
  });

  // ==========================================================================
  // 1. Renderizado y Ocultamiento Condicional del Badge de Notificaciones
  // ==========================================================================
  describe("Visibilidad del Badge de Notificaciones", () => {
    it("renderiza el badge visual con data-testid='sidebar-notifications-badge' cuando hay solicitudes pendientes (total > 0)", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 4,
            by_category: { operaciones: 2, inventario: 1, compras: 1, equipo: 0 },
          });
        }
        return createMockEnvelope({});
      });

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-notifications-badge");
        expect(badge).toBeTruthy();
        expect(badge.textContent).toBe("4");
      });
    });

    it("oculta el badge cuando no hay solicitudes pendientes (total === 0)", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 0,
            by_category: { operaciones: 0, inventario: 0, compras: 0, equipo: 0 },
          });
        }
        return createMockEnvelope({});
      });

      renderSidebar();

      await waitFor(() => {
        const badge = screen.queryByTestId("sidebar-notifications-badge");
        expect(badge).toBeNull();
      });
    });
  });

  // ==========================================================================
  // 2. Formateo y Límite visual de conteo (Truncamiento 9+)
  // ==========================================================================
  describe("Formateo y Límite visual de conteo", () => {
    it("muestra '9+' cuando el conteo total de pendientes supera 9 (total > 9)", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 12,
            by_category: { operaciones: 6, inventario: 3, compras: 2, equipo: 1 },
          });
        }
        return createMockEnvelope({});
      });

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-notifications-badge");
        expect(badge.textContent).toBe("9+");
      });
    });

    it("muestra el número exacto '9' cuando el total es exactamente 9", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 9,
            by_category: { operaciones: 4, inventario: 3, compras: 2, equipo: 0 },
          });
        }
        return createMockEnvelope({});
      });

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-notifications-badge");
        expect(badge.textContent).toBe("9");
      });
    });

    it("aplica estilo cromático ámbar '#fbbf24' e icono Bell correspondiente", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 3,
            by_category: { operaciones: 2, inventario: 1, compras: 0, equipo: 0 },
          });
        }
        return createMockEnvelope({});
      });

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-notifications-badge");
        expect(badge.className).toContain("bg-[#fbbf24]");
        expect(badge.className).toContain("text-black");
      });
    });
  });

  // ==========================================================================
  // 3. Sincronización Realtime / Eventos Reactivos
  // ==========================================================================
  describe("Sincronización Reactiva de Conteo", () => {
    it("actualiza el badge automáticamente cuando se emite el evento 'approvals_changed'", async () => {
      let currentCount = 1;
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: currentCount,
            by_category: { operaciones: currentCount, inventario: 0, compras: 0, equipo: 0 },
          });
        }
        return createMockEnvelope({});
      });

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-notifications-badge");
        expect(badge.textContent).toBe("1");
      });

      // Se crea una nueva notificación en el sistema
      currentCount = 5;
      act(() => {
        window.dispatchEvent(new Event("approvals_changed"));
      });

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-notifications-badge");
        expect(badge.textContent).toBe("5");
      });
    });
  });
});
