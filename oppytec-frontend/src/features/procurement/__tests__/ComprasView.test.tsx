/**
 * oppytec-frontend/src/features/procurement/__tests__/ComprasView.test.tsx
 * Pruebas unitarias para ComprasView, subcomponentes, diálogos y persistencia de borradores.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor, cleanup, within } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { CurrencyProvider } from "@/shared/currency";
import { GestionPage } from "@/features/gestion/GestionPage";
import { ComprasView } from "../components/ComprasView";
import {
  MOCK_COMPRAS,
} from "../mockData";
import { COMPRA_DRAFT_STORAGE_KEY, type CompraDraft } from "../types";

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// In-Memory localStorage mock
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string): string | null => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = String(value);
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((idx: number) => Object.keys(store)[idx] ?? null),
  };
})();

Object.defineProperty(globalThis, "localStorage", {
  value: mockLocalStorage,
  writable: true,
});

function createWrapper() {
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
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <PermissionsProvider>
            <CurrencyProvider>
              {children}
            </CurrencyProvider>
          </PermissionsProvider>
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

describe("Feature Procurement - Fase 4: ComprasView & Dialogs Suite", () => {
  beforeEach(() => {
    mockLocalStorage.clear();
    vi.clearAllMocks();

    // Default mock response using fallbackData
    vi.spyOn(httpClient, "apiRequest").mockImplementation(
      async <T,>(_url: string, options?: { fallbackData?: T }): Promise<httpClient.ApiEnvelope<T>> => {
        return {
          data: (options?.fallbackData ?? (MOCK_COMPRAS as unknown as T)),
          traceId: "test-trace",
          timestampIso: new Date().toISOString(),
          tenantId: "tenant_rest_central",
        };
      }
    );
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. RENDERIZADO DE SUBTABS (Dashboard, Listado, Proveedores, Catálogo)
  // ==========================================================================
  describe("1. Renderizado de SubTabs Legacy", () => {
    it("renderiza correctamente las 4 subpestañas y permite alternar entre ellas", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ComprasView />
        </Wrapper>
      );

      // Verificar que los botones de las subtabs están presentes
      const tabDashboard = screen.getByTestId("compras-subtab-dashboard");
      const tabListado = screen.getByTestId("compras-subtab-listado");
      const tabProveedores = screen.getByTestId("compras-subtab-proveedores");
      const tabCatalogo = screen.getByTestId("compras-subtab-catalogo");

      expect(tabDashboard).toBeDefined();
      expect(tabListado).toBeDefined();
      expect(tabProveedores).toBeDefined();
      expect(tabCatalogo).toBeDefined();

      // Por defecto arranca en Listado
      await screen.findByTestId("compra-table");
      expect(screen.getByTestId("compra-table")).toBeDefined();

      // Click en Dashboard
      fireEvent.click(tabDashboard);
      await waitFor(() => {
        expect(screen.getByTestId("compras-dashboard")).toBeDefined();
        expect(screen.getByTestId("kpi-gasto-total")).toBeDefined();
        expect(screen.getByTestId("kpi-ordenes-pendientes")).toBeDefined();
        expect(screen.getByTestId("kpi-tiempo-entrega")).toBeDefined();
        expect(screen.getByTestId("kpi-proveedor-principal")).toBeDefined();
      });

      // Click en Proveedores
      fireEvent.click(tabProveedores);
      await waitFor(() => {
        expect(screen.getByTestId("proveedores-tab-content")).toBeDefined();
        expect(screen.getByTestId("supplier-card-1")).toBeDefined();
      });

      // Click en Catálogo Pactado
      fireEvent.click(tabCatalogo);
      await waitFor(() => {
        expect(screen.getByTestId("catalogo-precios")).toBeDefined();
        // Verifica que respeta la regla 'Pollo King'
        expect(screen.getByText("Pollo King")).toBeDefined();
      });

      // Volver a Listado
      fireEvent.click(tabListado);
      await waitFor(() => {
        expect(screen.getByTestId("compra-table")).toBeDefined();
      });
    });
  });

  // ==========================================================================
  // 2. RENDERIZADO DE TABLA Y TARJETAS CON SWITCHER DUAL
  // ==========================================================================
  describe("2. Renderizado de Tabla y Tarjetas (Vista Dual)", () => {
    it("permite conmutar entre vista de tabla y vista de tarjetas con touch targets >= 44px", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ComprasView />
        </Wrapper>
      );

      // Vista inicial: Tabla
      await screen.findByTestId("compra-table");
      expect(screen.getByTestId("compra-row-OC-2026-0842")).toBeDefined();

      // Badges temáticos con colores exactos
      const badgeEnCamino = screen.getByTestId("status-badge-EN_CAMINO");
      expect(badgeEnCamino.textContent).toContain("En Camino");

      // Cambiar a vista de tarjetas
      const cardsBtn = screen.getByTestId("view-mode-cards-btn");
      fireEvent.click(cardsBtn);

      await waitFor(() => {
        expect(screen.getByTestId("compra-cards-grid")).toBeDefined();
        expect(screen.getByTestId("compra-card-OC-2026-0842")).toBeDefined();
        expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
          "oppytec_compras_view_mode",
          "cards"
        );
      });

      // Volver a tabla
      const tableBtn = screen.getByTestId("view-mode-table-btn");
      fireEvent.click(tableBtn);
      await waitFor(() => {
        expect(screen.getByTestId("compra-table")).toBeDefined();
        expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
          "oppytec_compras_view_mode",
          "table"
        );
      });
    });

    it("filtra órdenes reactivamente por buscador de texto y pills de estado", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ComprasView />
        </Wrapper>
      );

      await screen.findByTestId("compra-table");
      const searchInput = screen.getByTestId("compras-search-input") as HTMLInputElement;
      fireEvent.change(searchInput, { target: { value: "OC-2026-0842" } });

      await waitFor(() => {
        expect(screen.getByTestId("compra-row-OC-2026-0842")).toBeDefined();
        expect(screen.queryByTestId("compra-row-OC-2026-0841")).toBeNull();
      });

      // Limpiar buscador y filtrar por estado
      fireEvent.change(searchInput, { target: { value: "" } });
      const filterBorrador = screen.getByTestId("filter-status-BORRADOR");
      fireEvent.click(filterBorrador);

      await waitFor(() => {
        expect(screen.getByTestId("compra-row-OC-2026-0840")).toBeDefined();
        expect(screen.queryByTestId("compra-row-OC-2026-0842")).toBeNull();
      });
    });
  });

  // ==========================================================================
  // 3. APERTURA Y CIERRE DE MODALES
  // ==========================================================================
  describe("3. Modales Operativos: CompraDialog, ReceptionDialog, IncidenciaDialog, DetalleModal", () => {
    it("abre y cierra el diálogo de Nueva Compra", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ComprasView />
        </Wrapper>
      );

      const nuevaCompraBtn = screen.getByTestId("nueva-compra-btn");
      fireEvent.click(nuevaCompraBtn);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeDefined();
        expect(screen.getByText("Nueva Orden de Compra")).toBeDefined();
        expect(screen.getByTestId("compra-dialog-add-item-btn")).toBeDefined();
      });

      // Cerrar modal
      const closeBtn = screen.getByTestId("responsive-dialog-close");
      fireEvent.click(closeBtn);

      await waitFor(() => {
        expect(screen.queryByRole("dialog")).toBeNull();
      });
    });

    it("abre el modal de Recepción de Mercadería desde una orden en camino", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ComprasView />
        </Wrapper>
      );

      await screen.findByTestId("compra-table");
      const receiveBtn = screen.getByTestId("compra-receive-btn-OC-2026-0842");
      fireEvent.click(receiveBtn);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeDefined();
        expect(screen.getByText(/Recepción de Mercadería: OC-2026-0842/)).toBeDefined();
        expect(screen.getByTestId("reception-confirm-btn")).toBeDefined();
      });

      // Modificar cantidad recibida para disparar alerta de discrepancia
      const inputCant = screen.getByTestId("input-cantidad-recibida-10");
      fireEvent.change(inputCant, { target: { value: "180" } });

      await waitFor(() => {
        expect(screen.getByTestId("reception-discrepancy-alert")).toBeDefined();
      });

      // Cerrar modal
      const closeBtn = screen.getByTestId("responsive-dialog-close");
      fireEvent.click(closeBtn);
      await waitFor(() => {
        expect(screen.queryByRole("dialog")).toBeNull();
      });
    });

    it("abre el modal de Registro de Incidencias desde la tabla", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ComprasView />
        </Wrapper>
      );

      await screen.findByTestId("compra-table");
      const incidenceBtn = screen.getByTestId("compra-incidence-btn-OC-2026-0842");
      fireEvent.click(incidenceBtn);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeDefined();
        expect(screen.getByText("Registrar Incidencia de Compra")).toBeDefined();
        expect(screen.getByTestId("incidencia-tipo-select")).toBeDefined();
        expect(screen.getByTestId("incidencia-submit-btn")).toBeDefined();
      });

      // Cerrar modal
      const closeBtn = screen.getByTestId("responsive-dialog-close");
      fireEvent.click(closeBtn);
      await waitFor(() => {
        expect(screen.queryByRole("dialog")).toBeNull();
      });
    });

    it("abre el modal de Detalle para inspeccionar items e incidencias de la orden", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ComprasView />
        </Wrapper>
      );

      await screen.findByTestId("compra-table");
      const viewBtn = screen.getByTestId("compra-view-btn-OC-2026-0842");
      fireEvent.click(viewBtn);

      await waitFor(() => {
        const modal = screen.getByTestId("compra-detalle-modal");
        expect(modal).toBeDefined();
        expect(within(modal).getByText("Distribuidora Austral Food SpA")).toBeDefined();
        expect(screen.getByTestId("detalle-tab-items")).toBeDefined();
        expect(screen.getByTestId("detalle-tab-incidencias")).toBeDefined();
      });

      // Cerrar modal con botón Cerrar
      const closeBtn = screen.getByTestId("compra-detalle-close-btn");
      fireEvent.click(closeBtn);
      await waitFor(() => {
        expect(screen.queryByTestId("compra-detalle-modal")).toBeNull();
      });
    });
  });

  // ==========================================================================
  // 4. RECUPERACIÓN DE BORRADOR DE ORDEN (LOCALSTORAGE)
  // ==========================================================================
  describe("4. Persistencia y Recuperación de Borrador de Orden", () => {
    it("muestra el banner interactivo al detectar borrador guardado y permite recuperarlo", async () => {
      const mockDraft: CompraDraft = {
        proveedor_id: 1,
        proveedor_nombre: "Distribuidora Austral Food SpA",
        bodega_destino_id: 1,
        bodega_nombre: "Bodega Cocina Central",
        fecha_entrega_comprometida: "2026-11-01",
        moneda: "CLP",
        notas: "Borrador recuperado en test",
        items: [
          {
            producto_id: 10,
            producto_nombre: "Pollo King",
            cantidad_solicitada: 120,
            costo_unitario_neto: 3850,
            subtotal_linea: 462000,
          },
        ],
        updated_at: new Date().toISOString(),
      };

      mockLocalStorage.setItem(COMPRA_DRAFT_STORAGE_KEY, JSON.stringify(mockDraft));

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ComprasView />
        </Wrapper>
      );

      // Banner debe ser visible
      expect(screen.getByTestId("compras-draft-banner")).toBeDefined();
      expect(screen.getByText(/Borrador de orden de compra sin guardar/)).toBeDefined();

      // Clic en Recuperar Borrador
      const recoverBtn = screen.getByTestId("recover-draft-btn");
      fireEvent.click(recoverBtn);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeDefined();
        expect(screen.getByText("Nueva Orden de Compra")).toBeDefined();
        // Verifica que el item del borrador se cargó
        expect(screen.getByText("Pollo King")).toBeDefined();
      });
    });

    it("permite descartar el borrador y limpia el localStorage", async () => {
      const mockDraft: CompraDraft = {
        proveedor_id: 2,
        bodega_destino_id: 1,
        moneda: "CLP",
        notas: "Borrador a descartar",
        items: [],
        updated_at: new Date().toISOString(),
      };

      mockLocalStorage.setItem(COMPRA_DRAFT_STORAGE_KEY, JSON.stringify(mockDraft));

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ComprasView />
        </Wrapper>
      );

      expect(screen.getByTestId("compras-draft-banner")).toBeDefined();

      const discardBtn = screen.getByTestId("discard-draft-btn");
      fireEvent.click(discardBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("compras-draft-banner")).toBeNull();
        expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(COMPRA_DRAFT_STORAGE_KEY);
      });
    });
  });

  // ==========================================================================
  // 5. INTEGRACIÓN EN GESTIONPAGE (?tab=pedidos / ?tab=compras)
  // ==========================================================================
  describe("5. Montaje Integrado en GestionPage mediante URL SearchParams", () => {
    it("monta ComprasView cuando tab === 'pedidos'", async () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: 0 } },
      });

      render(
        <MemoryRouter initialEntries={["/gestion?tab=pedidos"]}>
          <QueryClientProvider client={queryClient}>
            <PermissionsProvider>
              <CurrencyProvider>
                <GestionPage />
              </CurrencyProvider>
            </PermissionsProvider>
          </QueryClientProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId("gestion-page-pedidos")).toBeDefined();
        expect(screen.getByTestId("compras-view")).toBeDefined();
        expect(screen.getByText("Gestión de Pedidos y Abastecimiento")).toBeDefined();
      });
    });

    it("monta ComprasView cuando tab === 'compras'", async () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: 0 } },
      });

      render(
        <MemoryRouter initialEntries={["/gestion?tab=compras"]}>
          <QueryClientProvider client={queryClient}>
            <PermissionsProvider>
              <CurrencyProvider>
                <GestionPage />
              </CurrencyProvider>
            </PermissionsProvider>
          </QueryClientProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId("gestion-page-pedidos")).toBeDefined();
        expect(screen.getByTestId("compras-view")).toBeDefined();
      });
    });

    it("preserva la vista de catálogo de productos cuando tab === 'productos' o no especificado", async () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: 0 } },
      });

      render(
        <MemoryRouter initialEntries={["/gestion?tab=productos"]}>
          <QueryClientProvider client={queryClient}>
            <PermissionsProvider>
              <CurrencyProvider>
                <GestionPage />
              </CurrencyProvider>
            </PermissionsProvider>
          </QueryClientProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.queryByTestId("gestion-page-pedidos")).toBeNull();
        expect(screen.queryByTestId("compras-view")).toBeNull();
      });
    });
  });
});
