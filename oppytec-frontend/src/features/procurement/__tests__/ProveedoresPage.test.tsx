/**
 * oppytec-frontend/src/features/procurement/__tests__/ProveedoresPage.test.tsx
 * Suite de Pruebas Unitarias para el Directorio de Proveedores (Fase 5).
 * Valida ADN Visual Legacy, ResponsiveDialogs, Filtros predictivos,
 * Vista Dual persistente y la regla comercial inmutable "Pollo King".
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { CurrencyProvider } from "@/shared/currency";
import { ProveedoresPage } from "../ProveedoresPage";
import {
  MOCK_PROVEEDORES,
  MOCK_PRODUCTOS_PROVEEDOR,
  MOCK_COMPRAS,
} from "../mockData";

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

describe("Feature Procurement - Fase 5: Directorio de Proveedores Suite", () => {
  beforeEach(() => {
    mockLocalStorage.clear();
    vi.clearAllMocks();

    vi.spyOn(httpClient, "apiRequest").mockImplementation(
      async <T,>(url: string, options?: { fallbackData?: T }): Promise<httpClient.ApiEnvelope<T>> => {
        let returnData: unknown = options?.fallbackData;

        if (url.includes("/api/v1/procurement/suppliers/") && url.includes("/products")) {
          // Extraer supplier id
          const match = url.match(/\/suppliers\/(\d+)\/products/);
          const supplierId = match ? Number(match[1]) : 1;
          returnData = MOCK_PRODUCTOS_PROVEEDOR[supplierId] ?? [];
        } else if (url.includes("/api/v1/procurement/suppliers")) {
          returnData = MOCK_PROVEEDORES;
        } else if (url.includes("/api/v1/procurement/orders")) {
          returnData = MOCK_COMPRAS;
        }

        return {
          data: (returnData ?? options?.fallbackData) as T,
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
  // 1. RENDERIZADO DEL ENCABEZADO Y BUSCADOR
  // ==========================================================================
  describe("1. Renderizado de Encabezado y Buscador Predictivo", () => {
    it("renderiza el SectionHeader comercial completo cuando no es subTab", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage isSubTab={false} />
        </Wrapper>
      );

      // SectionHeader
      expect(screen.getByTestId("proveedores-section-header")).toBeDefined();
      expect(screen.getByText("Directorio de Proveedores")).toBeDefined();
      expect(
        screen.getAllByText("Gestión de alianzas comerciales, tiempos de entrega y catálogo pactado")[0]
      ).toBeDefined();

      // Buscador
      const searchInput = screen.getByTestId("input-search-proveedores");
      expect(searchInput).toBeDefined();

      // Botón nuevo proveedor
      expect(screen.getByTestId("btn-nuevo-proveedor")).toBeDefined();
    });

    it("omite el SectionHeader cuando isSubTab={true}", () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage isSubTab={true} />
        </Wrapper>
      );

      expect(screen.queryByTestId("proveedores-section-header")).toBeNull();
      expect(screen.getByTestId("input-search-proveedores")).toBeDefined();
    });

    it("permite filtrar predictivamente por razón social o RUT", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage />
        </Wrapper>
      );

      // Proveedores iniciales visibles
      await screen.findByText("Distribuidora Austral Food SpA");
      expect(screen.getByText("Lácteos del Sur S.A.")).toBeDefined();

      // Escribir en el buscador "Austral"
      const searchInput = screen.getByTestId("input-search-proveedores");
      fireEvent.change(searchInput, { target: { value: "Austral" } });

      await waitFor(() => {
        expect(screen.getByText("Distribuidora Austral Food SpA")).toBeDefined();
        expect(screen.queryByText("Lácteos del Sur S.A.")).toBeNull();
      });

      // Limpiar búsqueda con el botón X
      const clearBtn = screen.getByTestId("btn-clear-search-proveedores");
      fireEvent.click(clearBtn);

      await waitFor(() => {
        expect(screen.getByText("Lácteos del Sur S.A.")).toBeDefined();
      });
    });
  });

  // ==========================================================================
  // 2. ALTERNANCIA ENTRE VISTA DE TABLA Y TARJETAS
  // ==========================================================================
  describe("2. Selector Dual de Vista (Tabla vs Tarjetas Mobile-First)", () => {
    it("inicia en vista de tabla por defecto y permite cambiar a tarjetas con persistencia", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage />
        </Wrapper>
      );

      // Por defecto arranca en tabla
      await screen.findByTestId("proveedores-table-container");
      expect(screen.getByTestId("proveedores-table-container")).toBeDefined();
      expect(screen.queryByTestId("proveedores-cards-container")).toBeNull();

      // Cambiar a vista de tarjetas
      const btnCards = screen.getByTestId("btn-view-mode-cards");
      fireEvent.click(btnCards);

      await waitFor(() => {
        expect(screen.getByTestId("proveedores-cards-container")).toBeDefined();
        expect(screen.queryByTestId("proveedores-table-container")).toBeNull();
      });

      // Verificar persistencia en localStorage
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        "oppytec_proveedores_view_mode",
        "cards"
      );

      // Volver a vista de tabla
      const btnTable = screen.getByTestId("btn-view-mode-table");
      fireEvent.click(btnTable);

      await waitFor(() => {
        expect(screen.getByTestId("proveedores-table-container")).toBeDefined();
        expect(screen.queryByTestId("proveedores-cards-container")).toBeNull();
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        "oppytec_proveedores_view_mode",
        "table"
      );
    });
  });

  // ==========================================================================
  // 3. FILTRO POR ESTADO (ACTIVO / INACTIVO / TODOS)
  // ==========================================================================
  describe("3. Filtro por Estado Operativo", () => {
    it("filtra correctamente por estado ACTIVO e INACTIVO", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage />
        </Wrapper>
      );

      await screen.findByText("Distribuidora Austral Food SpA");
      expect(screen.getByText("Importadora y Distribuidora Gourmet Pacific")).toBeDefined();

      // Filtrar por ACTIVO
      const filterActivo = screen.getByTestId("filter-estado-activo");
      fireEvent.click(filterActivo);

      await waitFor(() => {
        expect(screen.getByText("Distribuidora Austral Food SpA")).toBeDefined();
        // Gourmet Pacific es INACTIVO
        expect(screen.queryByText("Importadora y Distribuidora Gourmet Pacific")).toBeNull();
      });

      // Filtrar por INACTIVO
      const filterInactivo = screen.getByTestId("filter-estado-inactivo");
      fireEvent.click(filterInactivo);

      await waitFor(() => {
        expect(screen.queryByText("Distribuidora Austral Food SpA")).toBeNull();
        expect(screen.getByText("Importadora y Distribuidora Gourmet Pacific")).toBeDefined();
      });

      // Volver a TODOS
      const filterTodos = screen.getByTestId("filter-estado-todos");
      fireEvent.click(filterTodos);

      await waitFor(() => {
        expect(screen.getByText("Distribuidora Austral Food SpA")).toBeDefined();
        expect(screen.getByText("Importadora y Distribuidora Gourmet Pacific")).toBeDefined();
      });
    });
  });

  // ==========================================================================
  // 4. APERTURA DE MODALES
  // ==========================================================================
  describe("4. Apertura y Operación de Modales", () => {
    it("abre el modal ProveedorDialog en modo creación al pulsar + Nuevo Proveedor", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage />
        </Wrapper>
      );

      const btnNuevo = screen.getByTestId("btn-nuevo-proveedor");
      fireEvent.click(btnNuevo);

      await waitFor(() => {
        expect(screen.getByText("Nuevo Proveedor")).toBeDefined();
        expect(screen.getByTestId("input-rut-tax-id")).toBeDefined();
        expect(screen.getByTestId("input-razon-social")).toBeDefined();
        expect(screen.getByTestId("btn-submit-proveedor")).toBeDefined();
      });
    });

    it("abre el modal ProveedorDialog en modo edición con datos precargados", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage />
        </Wrapper>
      );

      await screen.findByTestId("btn-edit-1");
      const btnEdit = screen.getByTestId("btn-edit-1");
      fireEvent.click(btnEdit);

      await waitFor(() => {
        expect(screen.getByText(/Editar Proveedor: Distribuidora Austral Food SpA/i)).toBeDefined();
        const inputRazon = screen.getByTestId("input-razon-social") as HTMLInputElement;
        expect(inputRazon.value).toBe("Distribuidora Austral Food SpA");
        const inputRut = screen.getByTestId("input-rut-tax-id") as HTMLInputElement;
        expect(inputRut.value).toBe("76.321.400-8");
      });
    });

    it("abre el modal ProveedorDashboardDialog con métricas 360° y compras acumuladas", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage />
        </Wrapper>
      );

      await screen.findByTestId("btn-dashboard-1");
      const btnDashboard = screen.getByTestId("btn-dashboard-1");
      fireEvent.click(btnDashboard);

      await waitFor(() => {
        expect(screen.getByText(/Dashboard 360°: Distribuidora Austral Food SpA/i)).toBeDefined();
        expect(screen.getByTestId("kpi-total-compras")).toBeDefined();
        expect(screen.getByTestId("kpi-cumplimiento-otif")).toBeDefined();
        expect(screen.getByTestId("kpi-tiempo-medio")).toBeDefined();
        expect(screen.getByTestId("kpi-ordenes-activas")).toBeDefined();
      });
    });

    it("abre el modal de confirmación de eliminación/desactivación", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage />
        </Wrapper>
      );

      await screen.findByTestId("btn-delete-1");
      const btnDelete = screen.getByTestId("btn-delete-1");
      fireEvent.click(btnDelete);

      await waitFor(() => {
        expect(screen.getByText("Desactivar Proveedor")).toBeDefined();
        expect(screen.getByTestId("btn-confirm-delete-proveedor")).toBeDefined();
      });
    });
  });

  // ==========================================================================
  // 5. RESPETO A LA REGLA COMERCIAL INMUTABLE "POLLO KING"
  // ==========================================================================
  describe("5. Regla Comercial Inmutable Pollo King", () => {
    it("al abrir el Catálogo Pactado muestra intacto el producto comercial 'Pollo King'", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage />
        </Wrapper>
      );

      await screen.findByTestId("btn-catalog-1");
      const btnCatalog = screen.getByTestId("btn-catalog-1");
      fireEvent.click(btnCatalog);

      await waitFor(() => {
        expect(screen.getByText(/Catálogo Pactado: Distribuidora Austral Food SpA/i)).toBeDefined();
        // El insumo Pollo King debe estar presente exactamente
        expect(screen.getByText("Pollo King")).toBeDefined();
        expect(screen.getByText("INS-POLL-001")).toBeDefined();
      });
    });

    it("permite añadir un nuevo insumo y mantenerlo en la lista editable", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <ProveedoresPage />
        </Wrapper>
      );

      await screen.findByTestId("btn-catalog-1");
      fireEvent.click(screen.getByTestId("btn-catalog-1"));

      await waitFor(() => {
        expect(screen.getByTestId("btn-add-product-toggle")).toBeDefined();
      });

      // Desplegar formulario
      fireEvent.click(screen.getByTestId("btn-add-product-toggle"));

      await waitFor(() => {
        expect(screen.getByTestId("form-add-product")).toBeDefined();
      });

      // Rellenar insumo
      fireEvent.change(screen.getByTestId("input-new-producto-nombre"), {
        target: { value: "Pechuga de Pollo King Deshuesada" },
      });
      fireEvent.change(screen.getByTestId("input-new-codigo-proveedor"), {
        target: { value: "AF-POL-99" },
      });
      fireEvent.change(screen.getByTestId("input-new-precio-pactado"), {
        target: { value: "4200" },
      });

      // Insertar
      fireEvent.click(screen.getByTestId("btn-confirm-add-product"));

      await waitFor(() => {
        expect(screen.getByText("Pechuga de Pollo King Deshuesada")).toBeDefined();
      });
    });
  });
});
