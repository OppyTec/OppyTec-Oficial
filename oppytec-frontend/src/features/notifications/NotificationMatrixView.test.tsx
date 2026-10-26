// oppytec-frontend/src/features/notifications/NotificationMatrixView.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { toast } from "sonner";
import { NotificationMatrixView } from "./components/NotificationMatrixView";
import { NotificationsPage } from "./components/NotificationsPage";
import {
  MOCK_PENDING_COUNTS,
  MOCK_SOLICITUDES,
  MOCK_NOTIFICATION_MATRIX,
} from "./types";
import * as httpClient from "@/shared/api/httpClient";

// Mock de sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

function renderWithProviders(ui: React.ReactElement) {
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

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </MemoryRouter>
  );
}

describe("Fase 6: Matriz de Gobernanza y Configuración de Alertas por Cargo (NotificationMatrixView)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();

    vi.spyOn(httpClient, "apiRequest").mockImplementation(async (url: string): Promise<any> => {
      if (url.includes("/operations/solicitudes/matrix")) {
        return {
          status: 200,
          data: MOCK_NOTIFICATION_MATRIX,
          traceId: "test-trace-matrix",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
          headers: new Headers(),
          statusText: "OK",
        };
      }
      if (url.includes("/operations/solicitudes/pendientes/count")) {
        return {
          status: 200,
          data: MOCK_PENDING_COUNTS,
          traceId: "test-trace-counts",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
          headers: new Headers(),
          statusText: "OK",
        };
      }
      if (url.includes("/operations/solicitudes")) {
        return {
          status: 200,
          data: {
            items: MOCK_SOLICITUDES,
            total: MOCK_SOLICITUDES.length,
            page: 1,
            page_size: 10,
          },
          traceId: "test-trace-solicitudes",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
          headers: new Headers(),
          statusText: "OK",
        };
      }
      return {
        status: 200,
        data: {} as any,
        traceId: "test-trace-default",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
        headers: new Headers(),
        statusText: "OK",
      };
    });
  });

  afterEach(async () => {
    cleanup();
    vi.restoreAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    await new Promise((r) => setTimeout(r, 20));
  });

  // ==========================================================================
  // 1. Cabecera y Navegación
  // ==========================================================================
  describe("Cabecera y Navegación", () => {
    it("renders header bar with title, subtitle and back button", () => {
      const handleBack = vi.fn();
      renderWithProviders(<NotificationMatrixView onBack={handleBack} />);

      expect(
        screen.getByText("Matriz de Notificaciones y Gobernanza")
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          "Configura las notificaciones permitidas por cargo y tus preferencias personales"
        )
      ).toBeInTheDocument();
      expect(screen.getByTestId("btn-back-matrix")).toBeInTheDocument();
    });

    it("calls onBack when back button is clicked", () => {
      const handleBack = vi.fn();
      renderWithProviders(<NotificationMatrixView onBack={handleBack} />);

      const backBtn = screen.getByTestId("btn-back-matrix");
      fireEvent.click(backBtn);

      expect(handleBack).toHaveBeenCalledTimes(1);
    });

    it("renders dual tabs: Mis Notificaciones y Gobernanza de Cargos", () => {
      renderWithProviders(<NotificationMatrixView onBack={vi.fn()} />);

      expect(screen.getByTestId("tab-mis-notificaciones")).toBeInTheDocument();
      expect(screen.getByTestId("tab-gobernanza-cargos")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 2. Pestaña "Mis Notificaciones" (Preferencias Personales)
  // ==========================================================================
  describe("Pestaña Mis Notificaciones", () => {
    it("renders the 4 operational categories (operaciones, inventario, compras, equipo)", () => {
      renderWithProviders(<NotificationMatrixView onBack={vi.fn()} />);

      expect(screen.getByTestId("category-card-operaciones")).toBeInTheDocument();
      expect(screen.getByTestId("category-card-inventario")).toBeInTheDocument();
      expect(screen.getByTestId("category-card-compras")).toBeInTheDocument();
      expect(screen.getByTestId("category-card-equipo")).toBeInTheDocument();

      expect(screen.getByText("Operaciones y Cocina")).toBeInTheDocument();
      expect(screen.getByText("Inventario y Recetas")).toBeInTheDocument();
      expect(screen.getByText("Compras y Pedidos")).toBeInTheDocument();
      expect(screen.getByText("Equipo y Actividades")).toBeInTheDocument();
    });

    it("allows toggling personal notification preference with switch and toast feedback", () => {
      renderWithProviders(<NotificationMatrixView onBack={vi.fn()} />);

      const toggleMerma = screen.getByTestId("toggle-user-pref-merma");
      expect(toggleMerma).toHaveAttribute("aria-checked", "true");

      fireEvent.click(toggleMerma);

      expect(toggleMerma).toHaveAttribute("aria-checked", "false");
      expect(toast.success).toHaveBeenCalledWith("Preferencia actualizada");
    });
  });

  // ==========================================================================
  // 3. Pestaña "Gobernanza de Cargos" (Administración Multi-Rol)
  // ==========================================================================
  describe("Pestaña Gobernanza de Cargos", () => {
    it("switches to Gobernanza de Cargos tab and renders cargo list", async () => {
      renderWithProviders(<NotificationMatrixView onBack={vi.fn()} />);

      const tabGobernanza = screen.getByTestId("tab-gobernanza-cargos");
      fireEvent.click(tabGobernanza);

      expect(await screen.findByTestId("tab-content-gobernanza")).toBeInTheDocument();

      // Verifica presencia de cargos estándar del negocio
      expect(screen.getByTestId("cargo-item-1")).toBeInTheDocument();
      expect(screen.getByTestId("cargo-item-2")).toBeInTheDocument();
      expect(screen.getByTestId("cargo-item-3")).toBeInTheDocument();
      expect(screen.getByTestId("cargo-item-4")).toBeInTheDocument();
      expect(screen.getByTestId("cargo-item-5")).toBeInTheDocument();
      expect(screen.getByTestId("cargo-item-6")).toBeInTheDocument();
      expect(screen.getByTestId("cargo-item-7")).toBeInTheDocument();

      expect(screen.getByText("Supervisor de Turno")).toBeInTheDocument();
      expect(screen.getByText("Cocinero de Estación")).toBeInTheDocument();
      expect(screen.getByText("Encargado de Bodega")).toBeInTheDocument();
      expect(screen.getByText("Garzón de Sala")).toBeInTheDocument();
      expect(screen.getByText("Cajero / POS")).toBeInTheDocument();
    });

    it("selects a different cargo and updates the active cargo view", async () => {
      renderWithProviders(<NotificationMatrixView onBack={vi.fn()} />);

      fireEvent.click(screen.getByTestId("tab-gobernanza-cargos"));

      // Seleccionar Chef Ejecutivo (id: 3)
      const chefCargoBtn = screen.getByTestId("cargo-item-3");
      fireEvent.click(chefCargoBtn);

      expect(
        await screen.findByText(/Permisos para:/i)
      ).toHaveTextContent("Chef Ejecutivo");
    });

    it("toggles permission for an alert in cargo draft and saves with feedback", async () => {
      renderWithProviders(<NotificationMatrixView onBack={vi.fn()} />);

      fireEvent.click(screen.getByTestId("tab-gobernanza-cargos"));

      // Seleccionar Chef Ejecutivo
      fireEvent.click(screen.getByTestId("cargo-item-3"));

      // Alternar permiso para 'conteo' (inicialmente false para chef)
      const toggleConteo = screen.getByTestId("toggle-cargo-perm-conteo");
      fireEvent.click(toggleConteo);

      // Guardar permisos
      const saveBtn = screen.getByTestId("btn-save-cargo-perms");
      fireEvent.click(saveBtn);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          expect.stringContaining("Permisos de notificación actualizados para Chef Ejecutivo")
        );
      });
    });
  });

  // ==========================================================================
  // 4. Integración en NotificationsPage
  // ==========================================================================
  describe("Integración en NotificationsPage", () => {
    it("renders NotificationMatrixView when mainView is 'configuracion' and onBack returns to bandeja", async () => {
      renderWithProviders(<NotificationsPage />);

      // Cambiar a vista 'configuracion' desde la toolbar
      const configViewBtn = await screen.findByTestId("mainview-configuracion");
      fireEvent.click(configViewBtn);

      // Se renderiza NotificationMatrixView
      expect(await screen.findByTestId("notification-matrix-view")).toBeInTheDocument();

      // Al hacer clic en Volver, regresa a la bandeja de entrada
      const backBtn = screen.getByTestId("btn-back-matrix");
      fireEvent.click(backBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("notification-matrix-view")).not.toBeInTheDocument();
      });
    });
  });
});
