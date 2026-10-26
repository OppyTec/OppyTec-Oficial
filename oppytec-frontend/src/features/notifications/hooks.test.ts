// oppytec-frontend/src/features/notifications/hooks.test.ts
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as httpClient from "@/shared/api/httpClient";
import {
  useApprovals,
  useNotificationMatrix,
  usePendingCount,
} from "./hooks";
import {
  CATEGORIES_CONFIG,
  CATEGORY_MAP,
  MOCK_NOTIFICATION_MATRIX,
  MOCK_PENDING_COUNTS,
  MOCK_SOLICITUDES,
  type NotificationMatrixRule,
  type Solicitud,
  type SolicitudTipo,
} from "./types";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

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
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

describe("Feature Notifications - Core & Reactive Hooks (Fase 3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. Contratos TypeScript y Mapeo Canónico de Categorías
  // ==========================================================================
  describe("1. Contratos y Mapeo de Categorías (types.ts)", () => {
    it("mapea exactamente los 12 tipos de solicitud a las 4 categorías canónicas", () => {
      const typesList: SolicitudTipo[] = [
        "merma",
        "merma_receta",
        "consumo",
        "consumo_buffet",
        "conteo",
        "producto_borrador_receta",
        "recibir_pedido",
        "solicitud_compra",
        "vinculacion_proveedor",
        "mencion_nota",
        "perfil",
        "color_turno",
      ];

      expect(typesList.length).toBe(12);

      // Operaciones
      expect(CATEGORY_MAP.merma).toBe("operaciones");
      expect(CATEGORY_MAP.merma_receta).toBe("operaciones");
      expect(CATEGORY_MAP.consumo).toBe("operaciones");
      expect(CATEGORY_MAP.consumo_buffet).toBe("operaciones");

      // Inventario
      expect(CATEGORY_MAP.conteo).toBe("inventario");
      expect(CATEGORY_MAP.producto_borrador_receta).toBe("inventario");

      // Compras
      expect(CATEGORY_MAP.recibir_pedido).toBe("compras");
      expect(CATEGORY_MAP.solicitud_compra).toBe("compras");
      expect(CATEGORY_MAP.vinculacion_proveedor).toBe("compras");

      // Equipo
      expect(CATEGORY_MAP.mencion_nota).toBe("equipo");
      expect(CATEGORY_MAP.perfil).toBe("equipo");
      expect(CATEGORY_MAP.color_turno).toBe("equipo");
    });

    it("valida la configuración de las 4 categorías con colores e iconos correctos", () => {
      expect(CATEGORIES_CONFIG.length).toBe(4);

      const op = CATEGORIES_CONFIG.find((c) => c.id === "operaciones");
      expect(op).toBeDefined();
      expect(op?.color).toBe("#f59e0b");
      expect(op?.icon).toBeDefined();

      const inv = CATEGORIES_CONFIG.find((c) => c.id === "inventario");
      expect(inv).toBeDefined();
      expect(inv?.color).toBe("#10b981");

      const comp = CATEGORIES_CONFIG.find((c) => c.id === "compras");
      expect(comp).toBeDefined();
      expect(comp?.color).toBe("#6366f1");

      const eq = CATEGORIES_CONFIG.find((c) => c.id === "equipo");
      expect(eq).toBeDefined();
      expect(eq?.color).toBe("#a855f7");
    });

    it("posee datos mock robustos de fallback para evitar pantallas en blanco", () => {
      expect(MOCK_SOLICITUDES.length).toBeGreaterThan(0);
      expect(MOCK_PENDING_COUNTS.total).toBe(4);
      expect(MOCK_NOTIFICATION_MATRIX.catalog.length).toBeGreaterThan(0);
      expect(MOCK_NOTIFICATION_MATRIX.cargos.length).toBeGreaterThan(0);
    });
  });

  // ==========================================================================
  // 2. Hook Principal useApprovals
  // ==========================================================================
  describe("2. Hook useApprovals", () => {
    it("carga solicitudes pendientes por defecto con fallback si el backend no responde", async () => {
      const { result } = renderHook(() => useApprovals(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.solicitudes.length).toBeGreaterThan(0);
      expect(
        result.current.solicitudes.every((s) => s.estado === "pendiente")
      ).toBe(true);
      expect(result.current.page).toBe(1);
      expect(result.current.pageSize).toBe(20);
    });

    it("consume exitosamente la respuesta remota del endpoint /api/v1/operations/solicitudes", async () => {
      const mockBackendItem: Solicitud = {
        id: "remote-uuid-1",
        tipo: "merma",
        categoria: "operaciones",
        estado: "pendiente",
        usuario_id: 99,
        bodega_id: 1,
        area_operativa_id: 2,
        creado_at: "2026-10-25T12:00:00Z",
        detalles: { producto_nombre: "Carne Premium", cantidad: 5 },
      };

      vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
        data: {
          items: [mockBackendItem],
          total: 1,
          page: 1,
          page_size: 20,
        },
        traceId: "test-trace",
        timestampIso: "2026-10-25T12:00:00Z",
        tenantId: "tenant_test",
      });

      const { result } = renderHook(() => useApprovals(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.solicitudes.length).toBe(1);
      expect(result.current.solicitudes[0]?.id).toBe("remote-uuid-1");
      expect(result.current.total).toBe(1);
    });

    it("aplica filtros de categoría, área operativa, bodega y búsqueda en cliente y query", async () => {
      const { result } = renderHook(
        () =>
          useApprovals({
            activeCategory: "operaciones",
            selectedAreaId: 1,
            selectedBodegaId: 1,
            searchTerm: "Salmón",
          }),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.solicitudes.length).toBe(1);
      expect(result.current.solicitudes[0]?.tipo).toBe("merma");
      expect(result.current.solicitudes[0]?.categoria).toBe("operaciones");
      expect(result.current.solicitudes[0]?.area_operativa_id).toBe(1);
    });

    it("permite filtrar por vista 'historial' mostrando solicitudes no pendientes", async () => {
      const { result } = renderHook(
        () => useApprovals({ mainView: "historial" }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Como los mocks iniciales son pendientes, historial debe retornar array vacío
      expect(result.current.solicitudes.length).toBe(0);
    });

    it("gestiona el estado temporal de edición inline antes de aprobar", () => {
      const { result } = renderHook(() => useApprovals(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setEditedDetail("sol-mock-001", "cantidad", 3.8);
        result.current.setEditedTipo("sol-mock-001", "consumo");
      });

      expect(
        result.current.getEditedDetails("sol-mock-001")
      ).toEqual({ cantidad: 3.8 });
      expect(result.current.getEditedTipo("sol-mock-001")).toBe("consumo");

      act(() => {
        result.current.resetEdited("sol-mock-001");
      });

      expect(result.current.getEditedDetails("sol-mock-001")).toEqual({});
      expect(result.current.getEditedTipo("sol-mock-001")).toBeUndefined();
    });

    it("aprueba una solicitud enviando payload y mostrando toast de éxito", async () => {
      const spyApi = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: {
            items: MOCK_SOLICITUDES,
            total: MOCK_SOLICITUDES.length,
            page: 1,
            page_size: 20,
          },
          traceId: "t1",
          timestampIso: "2026-10-25T12:00:00Z",
          tenantId: "tenant_test",
        })
        .mockResolvedValueOnce({
          data: {
            ...MOCK_SOLICITUDES[0],
            estado: "aprobado",
            resuelto_at: "2026-10-25T12:05:00Z",
          },
          traceId: "t2",
          timestampIso: "2026-10-25T12:05:00Z",
          tenantId: "tenant_test",
        });

      const { result } = renderHook(() => useApprovals(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let approved: Solicitud | undefined;
      await act(async () => {
        approved = await result.current.approveRequest("sol-mock-001", {
          cantidad: 3.0,
        });
      });

      expect(approved).toBeDefined();
      expect(approved?.estado).toBe("aprobado");
      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/operations/solicitudes/sol-mock-001/aprobar",
        expect.objectContaining({
          method: "POST",
          body: { edited_details: { cantidad: 3.0 } },
        })
      );
      expect(toast.success).toHaveBeenCalledWith(
        "Solicitud aprobada correctamente"
      );
    });

    it("rechaza una solicitud exigiendo motivo mínimo de 5 caracteres", async () => {
      const spyApi = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: {
            items: MOCK_SOLICITUDES,
            total: MOCK_SOLICITUDES.length,
            page: 1,
            page_size: 20,
          },
          traceId: "t1",
          timestampIso: "2026-10-25T12:00:00Z",
          tenantId: "tenant_test",
        })
        .mockResolvedValueOnce({
          data: {
            ...MOCK_SOLICITUDES[0],
            estado: "rechazado",
            motivo_rechazo: "Insumo en buen estado verificado",
          },
          traceId: "t3",
          timestampIso: "2026-10-25T12:10:00Z",
          tenantId: "tenant_test",
        });

      const { result } = renderHook(() => useApprovals(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Validación de longitud menor a 5 caracteres
      await expect(
        result.current.rejectRequest("sol-mock-001", "no")
      ).rejects.toThrow("al menos 5 caracteres");

      // Rechazo válido
      let rejected: Solicitud | undefined;
      await act(async () => {
        rejected = await result.current.rejectRequest(
          "sol-mock-001",
          "Insumo en buen estado verificado"
        );
      });

      expect(rejected).toBeDefined();
      expect(rejected?.estado).toBe("rechazado");
      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/operations/solicitudes/sol-mock-001/rechazar",
        expect.objectContaining({
          method: "POST",
          body: { motivo_rechazo: "Insumo en buen estado verificado" },
        })
      );
      expect(toast.success).toHaveBeenCalledWith(
        "Solicitud rechazada correctamente"
      );
    });

    it("notifica error si la mutación de aprobación falla en backend", async () => {
      vi.spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: {
            items: MOCK_SOLICITUDES,
            total: MOCK_SOLICITUDES.length,
            page: 1,
            page_size: 20,
          },
          traceId: "t1",
          timestampIso: "2026-10-25T12:00:00Z",
          tenantId: "tenant_test",
        })
        .mockRejectedValueOnce(new Error("Stock insuficiente en Kardex"));

      const { result } = renderHook(() => useApprovals(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        result.current.approveRequest("sol-mock-001")
      ).rejects.toThrow("Stock insuficiente en Kardex");

      expect(toast.error).toHaveBeenCalledWith("Stock insuficiente en Kardex");
    });
  });

  // ==========================================================================
  // 3. Hook Ligero usePendingCount
  // ==========================================================================
  describe("3. Hook usePendingCount", () => {
    it("retorna conteo consolidado y desglose por las 4 categorías con fallback seguro", async () => {
      const { result } = renderHook(() => usePendingCount(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.total).toBe(4);
      expect(result.current.operaciones).toBe(2);
      expect(result.current.inventario).toBe(1);
      expect(result.current.compras).toBe(1);
      expect(result.current.equipo).toBe(0);
    });

    it("consume respuesta remota del endpoint /pending-count", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
        data: {
          total_pending: 10,
          by_category: {
            operaciones: 4,
            inventario: 3,
            compras: 2,
            equipo: 1,
          },
          area_id: "2",
        },
        traceId: "cnt-trace",
        timestampIso: "2026-10-25T12:00:00Z",
        tenantId: "tenant_test",
      });

      const { result } = renderHook(() => usePendingCount({ areaId: 2 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.total).toBe(10);
      });

      expect(result.current.operaciones).toBe(4);
      expect(result.current.inventario).toBe(3);
      expect(result.current.compras).toBe(2);
      expect(result.current.equipo).toBe(1);
    });
  });

  // ==========================================================================
  // 4. Hook de Matriz de Gobernanza useNotificationMatrix
  // ==========================================================================
  describe("4. Hook useNotificationMatrix", () => {
    it("carga catálogo, cargos y reglas de gobernanza con fallback ante caída de red", async () => {
      const { result } = renderHook(() => useNotificationMatrix(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.catalog.length).toBeGreaterThan(0);
      expect(result.current.cargos.length).toBeGreaterThan(0);
      expect(result.current.rules.length).toBeGreaterThan(0);
      expect(result.current.isAdmin).toBe(true);
    });

    it("actualiza masivamente las reglas de gobernanza con mutación PUT exitosa", async () => {
      const updatedRules: NotificationMatrixRule[] = [
        {
          cargo: "supervisor",
          tipo_solicitud: "merma",
          canal_in_app: true,
          canal_email: true,
          canal_push: true,
          es_aprobador: true,
        },
      ];

      const spyApi = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: MOCK_NOTIFICATION_MATRIX,
          traceId: "m1",
          timestampIso: "2026-10-25T12:00:00Z",
          tenantId: "tenant_test",
        })
        .mockResolvedValueOnce({
          data: {
            ...MOCK_NOTIFICATION_MATRIX,
            rules: updatedRules,
          },
          traceId: "m2",
          timestampIso: "2026-10-25T12:01:00Z",
          tenantId: "tenant_test",
        });

      const { result } = renderHook(() => useNotificationMatrix(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.updateMatrix(updatedRules);
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/operations/solicitudes/matrix",
        expect.objectContaining({
          method: "PUT",
          body: { rules: updatedRules },
        })
      );
      expect(toast.success).toHaveBeenCalledWith(
        "Matriz de gobernanza guardada exitosamente"
      );
    });

    it("actualiza permisos de notificación individuales por cargo con /matrix/cargo/{id}", async () => {
      const spyApi = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: MOCK_NOTIFICATION_MATRIX,
          traceId: "m1",
          timestampIso: "2026-10-25T12:00:00Z",
          tenantId: "tenant_test",
        })
        .mockResolvedValueOnce({
          data: { status: "ok", cargo_id: 2 },
          traceId: "m3",
          timestampIso: "2026-10-25T12:02:00Z",
          tenantId: "tenant_test",
        });

      const { result } = renderHook(() => useNotificationMatrix(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.updateCargoPermissions(2, {
          merma: true,
          consumo: false,
        });
      });

      expect(spyApi).toHaveBeenCalledWith(
        "/api/v1/operations/solicitudes/matrix/cargo/2",
        expect.objectContaining({
          method: "PUT",
          body: {
            notification_permissions: { merma: true, consumo: false },
          },
        })
      );
      expect(toast.success).toHaveBeenCalledWith(
        "Permisos del cargo actualizados"
      );
    });
  });
});
