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
  traceId: "trace-alerts-badge-test",
  timestampIso: new Date().toISOString(),
  tenantId: "tenant_rest_central",
});

describe("SidebarAlertsBadge Suite — FASE 7: Integración con Sidebar y Badge Reactivo", () => {
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
  // 1. Renderizado y Ocultamiento Condicional
  // ==========================================================================
  describe("Visibilidad del Badge de Alertas", () => {
    it("renderiza el badge visual cuando hay alertas activas (totalCount > 0)", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope({
          total_count: 5,
          has_critical: false,
          critical_stock_count: 0,
          expired_count: 0,
          upcoming_count: 5,
        })
      );

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-alerts-badge");
        expect(badge).toBeTruthy();
        expect(badge.textContent).toBe("5");
      });
    });

    it("oculta el badge cuando no hay alertas activas (totalCount === 0)", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope({
          total_count: 0,
          has_critical: false,
          critical_stock_count: 0,
          expired_count: 0,
          upcoming_count: 0,
        })
      );

      renderSidebar();

      await waitFor(() => {
        const badge = screen.queryByTestId("sidebar-alerts-badge");
        expect(badge).toBeNull();
      });
    });
  });

  // ==========================================================================
  // 2. Límite visual de desbordamiento (Truncamiento 9+)
  // ==========================================================================
  describe("Formateo y Límite visual de conteo", () => {
    it("muestra '9+' cuando el conteo total de alertas supera 9 (totalCount > 9)", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope({
          total_count: 15,
          has_critical: true,
          critical_stock_count: 10,
          expired_count: 3,
          upcoming_count: 2,
        })
      );

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-alerts-badge");
        expect(badge.textContent).toBe("9+");
      });
    });

    it("muestra el número exacto cuando totalCount es exactamente 9", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope({
          total_count: 9,
          has_critical: false,
          critical_stock_count: 0,
          expired_count: 0,
          upcoming_count: 9,
        })
      );

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-alerts-badge");
        expect(badge.textContent).toBe("9");
      });
    });

    it("muestra '9+' cuando totalCount es 10", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope({
          total_count: 10,
          has_critical: true,
          critical_stock_count: 5,
          expired_count: 5,
          upcoming_count: 0,
        })
      );

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-alerts-badge");
        expect(badge.textContent).toBe("9+");
      });
    });
  });

  // ==========================================================================
  // 3. Estilos Cromáticos: Crítico (Rojo Pulsante) vs Preventivo (Ámbar)
  // ==========================================================================
  describe("Estilos Cromáticos según criticidad", () => {
    it("aplica animate-pulse y clase roja destructiva cuando hasCritical === true", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope({
          total_count: 3,
          has_critical: true,
          critical_stock_count: 2,
          expired_count: 1,
          upcoming_count: 0,
        })
      );

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-alerts-badge");
        expect(badge.className).toContain("bg-red-500");
        expect(badge.className).toContain("animate-pulse");
        expect(badge.className).toContain("text-white");
        expect(badge.className).toContain("shadow-red-500/50");
      });
    });

    it("aplica estilo de aviso preventivo en ámbar sin animate-pulse cuando hasCritical === false", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope({
          total_count: 4,
          has_critical: false,
          critical_stock_count: 0,
          expired_count: 0,
          upcoming_count: 4,
        })
      );

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-alerts-badge");
        expect(badge.className).toContain("bg-amber-500");
        expect(badge.className).not.toContain("animate-pulse");
        expect(badge.className).not.toContain("bg-red-500");
      });
    });
  });

  // ==========================================================================
  // 4. Reactividad Event-Driven y Zero-Polling (notif-updated y storage)
  // ==========================================================================
  describe("Reactividad ante eventos de ventana y Zero-Polling", () => {
    it("actualiza dinámicamente el badge al emitir el evento 'notif-updated'", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope({
          total_count: 0,
          has_critical: false,
          critical_stock_count: 0,
          expired_count: 0,
          upcoming_count: 0,
        })
      );

      renderSidebar();

      await waitFor(() => {
        expect(screen.queryByTestId("sidebar-alerts-badge")).toBeNull();
      });

      // Emular actualización reactiva vía notif-updated
      act(() => {
        localStorage.setItem("notif_total_count", "6");
        localStorage.setItem("notif_has_critical", "true");
        window.dispatchEvent(new Event("notif-updated"));
      });

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-alerts-badge");
        expect(badge.textContent).toBe("6");
        expect(badge.className).toContain("animate-pulse");
        expect(badge.className).toContain("bg-red-500");
      });

      // Emular limpieza a 0
      act(() => {
        localStorage.setItem("notif_total_count", "0");
        localStorage.setItem("notif_has_critical", "false");
        window.dispatchEvent(new Event("notif-updated"));
      });

      await waitFor(() => {
        expect(screen.queryByTestId("sidebar-alerts-badge")).toBeNull();
      });
    });

    it("sincroniza en tiempo real ante el evento 'storage' para soporte multi-pestaña", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope({
          total_count: 2,
          has_critical: false,
          critical_stock_count: 0,
          expired_count: 0,
          upcoming_count: 2,
        })
      );

      renderSidebar();

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-alerts-badge");
        expect(badge.textContent).toBe("2");
        expect(badge.className).not.toContain("animate-pulse");
      });

      // Modificación desde otra pestaña emulando 'storage'
      act(() => {
        localStorage.setItem("notif_total_count", "14");
        localStorage.setItem("notif_has_critical", "true");
        window.dispatchEvent(new Event("storage"));
      });

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-alerts-badge");
        expect(badge.textContent).toBe("9+");
        expect(badge.className).toContain("animate-pulse");
        expect(badge.className).toContain("bg-red-500");
      });
    });
  });

  // ==========================================================================
  // 5. Soporte en Sidebar Colapsado
  // ==========================================================================
  describe("Renderizado en Sidebar Colapsado", () => {
    it("mantiene el badge visible en el riel de iconos cuando el Sidebar está colapsado", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValue(
        createMockEnvelope({
          total_count: 7,
          has_critical: true,
          critical_stock_count: 4,
          expired_count: 2,
          upcoming_count: 1,
        })
      );

      renderSidebar({ isCollapsed: true });

      await waitFor(() => {
        const badge = screen.getByTestId("sidebar-alerts-badge");
        expect(badge).toBeTruthy();
        expect(badge.textContent).toBe("7");
        expect(badge.className).toContain("animate-pulse");
      });
    });
  });
});
