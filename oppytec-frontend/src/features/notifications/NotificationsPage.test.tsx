// oppytec-frontend/src/features/notifications/NotificationsPage.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import * as httpClient from "@/shared/api/httpClient";
import {
  PermissionsProvider,
  DEFAULT_RBAC_POLICY_STATE,
} from "@/shared/auth/usePermissions";
import { NotificationsPage } from "./components/NotificationsPage";
import {
  MOCK_PENDING_COUNTS,
  MOCK_SOLICITUDES,
} from "./types";

// Mock de sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock de framer-motion para tests estables
vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<any>("framer-motion");
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
    motion: {
      div: ({ children, className, onClick, id, ...props }: any) => (
        <div id={id} className={className} onClick={onClick} {...props}>
          {children}
        </div>
      ),
    },
  };
});

const policyWithApprovalPermission = {
  ...DEFAULT_RBAC_POLICY_STATE,
  rolePermissions: [
    ...DEFAULT_RBAC_POLICY_STATE.rolePermissions,
    "operations.approvals.approve" as const,
    "operations.approvals.reject" as const,
  ],
};

function createWrapper(initialUrl = "/notificaciones") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={[initialUrl]}>
        <QueryClientProvider client={queryClient}>
          <PermissionsProvider initialPolicy={policyWithApprovalPermission}>
            {children}
          </PermissionsProvider>
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

describe("NotificationsPage — Suite de Pruebas FASE 4 (Vitest)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof window !== "undefined") {
      window.HTMLElement.prototype.scrollIntoView = vi.fn();
      window.HTMLElement.prototype.hasPointerCapture = vi.fn();
      window.HTMLElement.prototype.setPointerCapture = vi.fn();
      window.HTMLElement.prototype.releasePointerCapture = vi.fn();
    }
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.clear();
    }

    // Mock API requests
    vi.spyOn(httpClient, "apiRequest").mockImplementation(
      async (url, _options) => {
        if (url.includes("/pending-count")) {
          return {
            data: MOCK_PENDING_COUNTS,
            traceId: "test-trace-count",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          };
        }
        if (url.includes("/aprobar")) {
          return {
            data: { ...MOCK_SOLICITUDES[0], estado: "aprobado" },
            traceId: "test-trace-approve",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          };
        }
        if (url.includes("/rechazar")) {
          return {
            data: { ...MOCK_SOLICITUDES[0], estado: "rechazado" },
            traceId: "test-trace-reject",
            timestampIso: new Date().toISOString(),
            tenantId: "tenant_rest_central",
          };
        }
        // Solicitudes list
        return {
          data: {
            items: MOCK_SOLICITUDES,
            total: MOCK_SOLICITUDES.length,
            page: 1,
            page_size: 10,
          },
          traceId: "test-trace-list",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    if (typeof localStorage !== "undefined") {
      localStorage.clear();
    }
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.clear();
    }
  });

  // ==========================================================================
  // 1. Renderizado de SectionHeader con color #fbbf24 y título
  // ==========================================================================
  it("renderiza SectionHeader con color #fbbf24 y el título canónico", async () => {
    const Wrapper = createWrapper();
    render(<NotificationsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(
        screen.getByText("Centro de Notificaciones y Aprobaciones")
      ).toBeInTheDocument();
    });

    const subtitles = screen.getAllByText(
      /Gobernanza operativa, control jerárquico de mermas/i
    );
    expect(subtitles.length).toBeGreaterThanOrEqual(1);

    const titleEl = screen.getByText("Centro de Notificaciones y Aprobaciones");
    expect(titleEl).toBeInTheDocument();
  });

  // ==========================================================================
  // 2. Pestañas de categoría y conteo de badges
  // ==========================================================================
  it("renderiza las pestañas de categorías y los badges con conteos correctos", async () => {
    const Wrapper = createWrapper();
    render(<NotificationsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("tab-category-all")).toBeInTheDocument();
      expect(screen.getByTestId("tab-category-operaciones")).toBeInTheDocument();
      expect(screen.getByTestId("tab-category-inventario")).toBeInTheDocument();
      expect(screen.getByTestId("tab-category-compras")).toBeInTheDocument();
      expect(screen.getByTestId("tab-category-equipo")).toBeInTheDocument();
    });

    // Validar badges de conteo desde MOCK_PENDING_COUNTS
    expect(screen.getByTestId("badge-category-all")).toHaveTextContent("4");
    expect(screen.getByTestId("badge-category-operaciones")).toHaveTextContent("2");
    expect(screen.getByTestId("badge-category-inventario")).toHaveTextContent("1");
    expect(screen.getByTestId("badge-category-compras")).toHaveTextContent("1");
  });

  // ==========================================================================
  // 3. Cambio de vista entre Bandeja, Historial y Configuración
  // ==========================================================================
  it("permite alternar entre Bandeja, Historial y Configuración", async () => {
    const Wrapper = createWrapper();
    render(<NotificationsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("mainview-bandeja")).toBeInTheDocument();
      expect(screen.getByTestId("mainview-historial")).toBeInTheDocument();
      expect(screen.getByTestId("mainview-configuracion")).toBeInTheDocument();
    });

    // Click en Historial
    fireEvent.click(screen.getByTestId("mainview-historial"));
    await waitFor(() => {
      expect(screen.getByTestId("mainview-historial")).toHaveClass("bg-primary");
    });

    // Click en Configuración
    fireEvent.click(screen.getByTestId("mainview-configuracion"));
    await waitFor(() => {
      expect(screen.getByTestId("notification-matrix-view")).toBeInTheDocument();
      expect(
        screen.getByText("Matriz de Notificaciones y Gobernanza")
      ).toBeInTheDocument();
    });

    // Volver a Bandeja
    fireEvent.click(screen.getByTestId("mainview-bandeja"));
    await waitFor(() => {
      expect(screen.getByTestId("category-tabs")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 4. Toggle de vista Cards vs Compact
  // ==========================================================================
  it("permite cambiar entre vista Cards y Compact Table", async () => {
    const Wrapper = createWrapper();
    render(<NotificationsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("notifications-cards-grid")).toBeInTheDocument();
    });

    // Toggle a vista compacta
    const toggleBtn = screen.getByTestId("toggle-view-layout");
    fireEvent.click(toggleBtn);

    await waitFor(() => {
      expect(
        screen.getByTestId("notifications-compact-table")
      ).toBeInTheDocument();
    });

    // Toggle de regreso a Cards
    fireEvent.click(toggleBtn);
    await waitFor(() => {
      expect(screen.getByTestId("notifications-cards-grid")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 5. Búsqueda y filtrado
  // ==========================================================================
  it("filtra las solicitudes según el término de búsqueda ingresado", async () => {
    const Wrapper = createWrapper();
    render(<NotificationsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("solicitud-card-sol-mock-001")).toBeInTheDocument();
      expect(screen.getByTestId("solicitud-card-sol-mock-003")).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId("notifications-search-input");
    fireEvent.change(searchInput, { target: { value: "Salmón" } });

    await waitFor(() => {
      expect(screen.getByTestId("solicitud-card-sol-mock-001")).toBeInTheDocument();
      expect(screen.queryByTestId("solicitud-card-sol-mock-003")).not.toBeInTheDocument();
    });

    // Limpiar búsqueda
    const clearBtn = screen.getByTestId("clear-search-button");
    fireEvent.click(clearBtn);

    await waitFor(() => {
      expect(screen.getByTestId("solicitud-card-sol-mock-003")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 6. Interacción de Aprobar y Rechazar (RBAC Protected)
  // ==========================================================================
  it("ejecuta la acción de Aprobar al interactuar con el botón correspondiente", async () => {
    const Wrapper = createWrapper();
    render(<NotificationsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("btn-aprobar-sol-mock-001")).toBeInTheDocument();
    });

    const approveBtn = screen.getByTestId("btn-aprobar-sol-mock-001");
    fireEvent.click(approveBtn);

    await waitFor(() => {
      expect(httpClient.apiRequest).toHaveBeenCalledWith(
        expect.stringContaining("/sol-mock-001/aprobar"),
        expect.anything()
      );
    });
  });

  it("abre el formulario de rechazo y confirma la acción con motivo obligatorio", async () => {
    const Wrapper = createWrapper();
    render(<NotificationsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("btn-rechazar-sol-mock-001")).toBeInTheDocument();
    });

    // Abrir panel de rechazo
    fireEvent.click(screen.getByTestId("btn-rechazar-sol-mock-001"));

    await waitFor(() => {
      expect(
        screen.getByTestId("rejection-panel-sol-mock-001")
      ).toBeInTheDocument();
    });

    // Intentar confirmar sin motivo -> muestra validación
    const confirmBtn = screen.getByTestId("confirm-reject-btn-sol-mock-001");
    fireEvent.click(confirmBtn);

    expect(
      screen.getByText("El motivo de rechazo es obligatorio")
    ).toBeInTheDocument();

    // Ingresar motivo válido (> 5 chars)
    const reasonInput = screen.getByTestId("reject-reason-input-sol-mock-001");
    fireEvent.change(reasonInput, {
      target: { value: "Producto en buen estado, no merma" },
    });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(httpClient.apiRequest).toHaveBeenCalledWith(
        expect.stringContaining("/sol-mock-001/rechazar"),
        expect.objectContaining({
          body: { motivo_rechazo: "Producto en buen estado, no merma" },
        })
      );
    });
  });

  // ==========================================================================
  // 7. Deep Linking ?highlight=<id>
  // ==========================================================================
  it("aplica scrollIntoView y efecto visual cromático con query param ?highlight=<id>", async () => {
    const Wrapper = createWrapper("/notificaciones?highlight=sol-mock-001");
    render(<NotificationsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      const card = screen.getByTestId("solicitud-card-sol-mock-001");
      expect(card).toBeInTheDocument();
      // Verifica clases de highlight ring
      expect(card).toHaveClass("ring-2");
      expect(card).toHaveClass("ring-amber-500");
    });

    await waitFor(() => {
      expect(window.HTMLElement.prototype.scrollIntoView).toHaveBeenCalledWith({
        behavior: "smooth",
        block: "center",
      });
    });
  });
});
