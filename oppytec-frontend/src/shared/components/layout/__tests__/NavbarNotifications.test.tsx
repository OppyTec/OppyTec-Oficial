import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent, act, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Navbar } from "../Navbar";
import { PermissionsProvider, type RbacPolicyState } from "@/shared/auth/usePermissions";
import { CurrencyProvider } from "@/shared/currency/CurrencyContext";
import { setActiveLanguage } from "@/shared/i18n";
import * as httpClient from "@/shared/api/httpClient";
import { MOCK_SOLICITUDES } from "@/features/notifications/types";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const createMockEnvelope = <T,>(data: T): httpClient.ApiEnvelope<T> => ({
  data,
  traceId: "trace-navbar-notif-test",
  timestampIso: new Date().toISOString(),
  tenantId: "tenant_rest_central",
});

describe("Navbar Notifications Suite — FASE 7: Campanita, Desplegable y Realtime", () => {
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

  const renderNavbar = (props: Parameters<typeof Navbar>[0] = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <CurrencyProvider>
          <MemoryRouter initialEntries={["/"]}>
            <PermissionsProvider initialPolicy={basePolicy}>
              <Navbar {...props} />
            </PermissionsProvider>
          </MemoryRouter>
        </CurrencyProvider>
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
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
  // 1. Campanita y Badges (Desktop y Mobile)
  // ==========================================================================
  describe("1. Campanita y Badges de Notificaciones", () => {
    it("muestra el badge con el conteo real en desktop cuando total > 0", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 4,
            by_category: { operaciones: 2, inventario: 1, compras: 1, equipo: 0 },
          });
        }
        return createMockEnvelope({ items: MOCK_SOLICITUDES, total: 4, page: 1, page_size: 5 });
      });

      renderNavbar();

      await waitFor(() => {
        const badge = screen.getByTestId("navbar-notifications-badge");
        expect(badge).toBeTruthy();
        expect(badge.textContent).toBe("4");
      });
    });

    it("trunca el badge a '9+' cuando el conteo total supera 9", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 15,
            by_category: { operaciones: 8, inventario: 4, compras: 3, equipo: 0 },
          });
        }
        return createMockEnvelope({ items: MOCK_SOLICITUDES, total: 15, page: 1, page_size: 5 });
      });

      renderNavbar();

      await waitFor(() => {
        const badge = screen.getByTestId("navbar-notifications-badge");
        expect(badge.textContent).toBe("9+");
      });
    });

    it("no renderiza el badge cuando total === 0", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 0,
            by_category: { operaciones: 0, inventario: 0, compras: 0, equipo: 0 },
          });
        }
        return createMockEnvelope({ items: [], total: 0, page: 1, page_size: 5 });
      });

      renderNavbar();

      await waitFor(() => {
        const badge = screen.queryByTestId("navbar-notifications-badge");
        expect(badge).toBeNull();
      });
    });
  });

  // ==========================================================================
  // 2. Desplegable / Popover de Notificaciones
  // ==========================================================================
  describe("2. Desplegable Popover de Notificaciones", () => {
    it("abre el desplegable al hacer clic en la campanita desktop y muestra conteo dinámico", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 4,
            by_category: { operaciones: 2, inventario: 1, compras: 1, equipo: 0 },
          });
        }
        return createMockEnvelope({ items: MOCK_SOLICITUDES, total: 4, page: 1, page_size: 5 });
      });

      renderNavbar();

      const bell = await screen.findByTestId("navbar-notifications-bell");
      fireEvent.click(bell);

      await waitFor(() => {
        const popover = screen.getByTestId("navbar-notifications-popover");
        expect(popover).toBeTruthy();
        const countLabel = screen.getByTestId("navbar-notifications-count-label");
        expect(countLabel.textContent).toContain("4 pendientes");
      });
    });

    it("muestra la lista reactiva de solicitudes con título, subtítulo e ícono", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 4,
            by_category: { operaciones: 2, inventario: 1, compras: 1, equipo: 0 },
          });
        }
        return createMockEnvelope({ items: MOCK_SOLICITUDES, total: 4, page: 1, page_size: 5 });
      });

      renderNavbar();

      const bell = await screen.findByTestId("navbar-notifications-bell");
      fireEvent.click(bell);

      await waitFor(() => {
        // En MOCK_SOLICITUDES hay una merma de Salmón Fresco Chileno
        expect(screen.getByText("Registro de Merma")).toBeTruthy();
        expect(screen.getByText(/Salmón Fresco Chileno/i)).toBeTruthy();
      });
    });

    it("ejecuta deep linking con navegación hacia /notificaciones?highlight=<id> al hacer clic en una solicitud", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 4,
            by_category: { operaciones: 2, inventario: 1, compras: 1, equipo: 0 },
          });
        }
        return createMockEnvelope({ items: MOCK_SOLICITUDES, total: 4, page: 1, page_size: 5 });
      });

      renderNavbar();

      const bell = await screen.findByTestId("navbar-notifications-bell");
      fireEvent.click(bell);

      const firstMockId = MOCK_SOLICITUDES[0]?.id ?? "sol-mock-001";
      const firstItemBtn = await screen.findByTestId(`navbar-notification-item-${firstMockId}`);
      fireEvent.click(firstItemBtn);

      expect(mockNavigate).toHaveBeenCalledWith(`/notificaciones?highlight=${firstMockId}`);
    });

    it("muestra estado vacío ('No hay solicitudes pendientes') con checkmark cuando total === 0", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 0,
            by_category: { operaciones: 0, inventario: 0, compras: 0, equipo: 0 },
          });
        }
        return createMockEnvelope({ items: [], total: 0, page: 1, page_size: 5 });
      });

      renderNavbar();

      const bell = await screen.findByTestId("navbar-notifications-bell");
      fireEvent.click(bell);

      await waitFor(() => {
        const emptyState = screen.getByTestId("navbar-notifications-empty");
        expect(emptyState).toBeTruthy();
        expect(screen.getByText("No hay solicitudes pendientes")).toBeTruthy();
        expect(screen.getByText(/0 pendientes/i)).toBeTruthy();
      });
    });

    it("incluye enlace al pie 'Ver todas en /notificaciones' que redirige a /notificaciones", async () => {
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: 2,
            by_category: { operaciones: 2, inventario: 0, compras: 0, equipo: 0 },
          });
        }
        return createMockEnvelope({ items: MOCK_SOLICITUDES.slice(0, 2), total: 2, page: 1, page_size: 5 });
      });

      renderNavbar();

      const bell = await screen.findByTestId("navbar-notifications-bell");
      fireEvent.click(bell);

      const viewAllBtn = await screen.findByTestId("navbar-notifications-view-all");
      expect(viewAllBtn.textContent).toContain("Ver todas en /notificaciones");

      fireEvent.click(viewAllBtn);
      expect(mockNavigate).toHaveBeenCalledWith("/notificaciones");
    });
  });

  // ==========================================================================
  // 3. Sincronización Realtime Zero-Polling
  // ==========================================================================
  describe("3. Sincronización Realtime Zero-Polling", () => {
    it("actualiza inmediatamente el contador de la campanita ante evento 'approvals_changed'", async () => {
      let currentPending = 2;
      vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url) => {
        if (typeof url === "string" && url.includes("/pending-count")) {
          return createMockEnvelope({
            total_pending: currentPending,
            by_category: { operaciones: currentPending, inventario: 0, compras: 0, equipo: 0 },
          });
        }
        return createMockEnvelope({ items: MOCK_SOLICITUDES.slice(0, currentPending), total: currentPending, page: 1, page_size: 5 });
      });

      renderNavbar();

      await waitFor(() => {
        const badge = screen.getByTestId("navbar-notifications-badge");
        expect(badge.textContent).toBe("2");
      });

      // Se genera un evento de cambio
      currentPending = 7;
      act(() => {
        window.dispatchEvent(new Event("approvals_changed"));
      });

      await waitFor(() => {
        const badge = screen.getByTestId("navbar-notifications-badge");
        expect(badge.textContent).toBe("7");
      });
    });
  });
});
