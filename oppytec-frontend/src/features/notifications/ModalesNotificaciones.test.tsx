// oppytec-frontend/src/features/notifications/ModalesNotificaciones.test.tsx
import "@testing-library/jest-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import * as httpClient from "@/shared/api/httpClient";
import {
  PermissionsProvider,
  DEFAULT_RBAC_POLICY_STATE,
} from "@/shared/auth/usePermissions";
import {
  BuffetApprovalModal,
  ConteoRequestDetails,
  RechazoModal,
  SolicitudCard,
  NotificationsCompactTable,
} from "./components";
import type { Solicitud } from "./types";

// Mock de sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

const policyWithApprovalPermission = {
  ...DEFAULT_RBAC_POLICY_STATE,
  rolePermissions: [
    ...DEFAULT_RBAC_POLICY_STATE.rolePermissions,
    "operations.approvals.approve" as const,
    "operations.approvals.reject" as const,
  ],
};

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <PermissionsProvider initialPolicy={policyWithApprovalPermission}>
      {children}
    </PermissionsProvider>
  );
}

const mockBuffetSolicitud: Solicitud = {
  id: "buffet-sol-101",
  tipo: "consumo_buffet",
  categoria: "operaciones",
  estado: "pendiente",
  usuario_id: 12,
  bodega_id: 1,
  area_operativa_id: 1,
  creado_at: new Date().toISOString(),
  usuario: {
    id: 12,
    username: "matias_bar",
    first_name: "Matías",
    last_name: "Silva",
    email: "matias@restaurant.cl",
    role: "supervisor",
  },
  detalles: {
    sesion_buffet_id: 504,
    buffet_nombre: "Buffet Almuerzo Ejecutivo",
    pax_atendidos: 45,
    bodega_nombre: "Cocina Buffet",
    items: [
      {
        id: "it-1",
        item_type: "insumo",
        nombre: "Lomo Liso Vacuno",
        unidad: "kg",
        cantidad_apertura: 10,
        cantidad_reposiciones: 5,
        cantidad_cierre: 3,
        costo_unitario_ppp: 14500,
        accion_sobrante: "retornar",
        motivo_merma: null,
      },
      {
        id: "it-2",
        item_type: "insumo",
        nombre: "Salmón Grillado",
        unidad: "kg",
        cantidad_apertura: 8,
        cantidad_reposiciones: 4,
        cantidad_cierre: 2,
        costo_unitario_ppp: 12000,
        accion_sobrante: "merma",
        motivo_merma: "Caducidad en buffet / tiempo expuesto",
      },
    ],
  },
};

const mockConteoSolicitud: Solicitud = {
  id: "conteo-sol-202",
  tipo: "conteo",
  categoria: "inventario",
  estado: "pendiente",
  usuario_id: 14,
  bodega_id: 1,
  area_operativa_id: 1,
  creado_at: new Date().toISOString(),
  usuario: {
    id: 14,
    username: "bodega_roberto",
    first_name: "Roberto",
    last_name: "López",
    email: "roberto@restaurant.cl",
    role: "bodeguero",
  },
  detalles: {
    acta_conteo_id: 88,
    items_contados: 4,
    discrepancias_count: 2,
    delta_monetario: -14500,
    observaciones: "Diferencia física en cámara de carnes",
  },
};

const mockMermaSolicitud: Solicitud = {
  id: "merma-sol-303",
  tipo: "merma",
  categoria: "operaciones",
  estado: "pendiente",
  usuario_id: 10,
  bodega_id: 1,
  area_operativa_id: 1,
  creado_at: new Date().toISOString(),
  usuario: {
    id: 10,
    username: "chef_carlos",
    first_name: "Carlos",
    last_name: "Gómez",
    email: "carlos@restaurant.cl",
    role: "chef",
  },
  detalles: {
    producto_id: 101,
    producto_nombre: "Salmón Fresco Chileno",
    cantidad: 2.5,
    unidad: "kg",
    motivo: "vencimiento",
    lote: "LOTE-2026-N1",
    costo_unitario: 12500,
    costo_total: 31250,
  },
};

describe("Fase 5 — Suite de Pruebas: Modales e Inspectores Operativos", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. BuffetApprovalModal: Renderizado, Vistas y Resolución
  // ==========================================================================
  describe("BuffetApprovalModal", () => {
    it("renderiza el modal en la pestaña Balance y calcula consumo neto y PPP en tiempo real", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
        data: {
          id: "buffet-sol-101",
          detalles: mockBuffetSolicitud.detalles,
        },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "test-tenant",
      });

      render(
        <BuffetApprovalModal
          open={true}
          solicitudId="buffet-sol-101"
          solicitud={mockBuffetSolicitud}
          onResolved={vi.fn()}
        />,
        { wrapper: Wrapper }
      );

      // Esperar a que se carguen los datos
      await waitFor(() => {
        expect(screen.getByTestId("buffet-approval-modal")).toBeInTheDocument();
      });

      expect(screen.getByText(/Auditoría de Buffet/i)).toBeInTheDocument();
      expect(screen.getByTestId("balance-view")).toBeInTheDocument();

      // Consumo neto item 1: 10 (apertura) + 5 (repo) - 3 (cierre) = 12
      const consumoNeto0 = screen.getByTestId("consumo-neto-0");
      expect(consumoNeto0).toHaveTextContent("12 kg");

      // Actualizar apertura de 10 a 12
      const inputApertura0 = screen.getByTestId("input-apertura-0");
      fireEvent.change(inputApertura0, { target: { value: "12" } });

      // Ahora el consumo neto debe recalcularse a: 12 + 5 - 3 = 14
      expect(screen.getByTestId("consumo-neto-0")).toHaveTextContent("14 kg");
    });

    it("permite alternar entre pestaña 'Balance Consolidado' y 'Auditoría Split-View'", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
        data: {
          id: "buffet-sol-101",
          detalles: mockBuffetSolicitud.detalles,
        },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "test-tenant",
      });

      render(
        <BuffetApprovalModal
          open={true}
          solicitudId="buffet-sol-101"
          solicitud={mockBuffetSolicitud}
          onResolved={vi.fn()}
        />,
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(screen.getByTestId("tab-split-view")).toBeInTheDocument();
      });

      // Hacer click en Split-View
      fireEvent.click(screen.getByTestId("tab-split-view"));

      // Vista Split-View visible
      expect(screen.getByTestId("split-view")).toBeInTheDocument();
      expect(screen.getByText(/1\. Apertura \/ Montaje/i)).toBeInTheDocument();
      expect(screen.getByText(/2\. Cierre \/ Desmontaje/i)).toBeInTheDocument();

      // Volver a Balance
      fireEvent.click(screen.getByTestId("tab-balance"));
      expect(screen.getByTestId("balance-view")).toBeInTheDocument();
    });

    it("permite cambiar la decisión de sobrante (retornar vs merma) y envía el payload a /resolve", async () => {
      const apiSpy = vi.spyOn(httpClient, "apiRequest").mockImplementation(
        async (url, _opts) => {
          if (url.includes("/detail")) {
            return {
              data: {
                id: "buffet-sol-101",
                detalles: mockBuffetSolicitud.detalles,
              },
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "test-tenant",
            };
          }
          if (url.includes("/resolve")) {
            return {
              data: { status: "success" },
              traceId: "test-trace",
              timestampIso: new Date().toISOString(),
              tenantId: "test-tenant",
            };
          }
          return { data: {} } as any;
        }
      );

      const onResolvedMock = vi.fn();

      render(
        <BuffetApprovalModal
          open={true}
          solicitudId="buffet-sol-101"
          solicitud={mockBuffetSolicitud}
          onResolved={onResolvedMock}
        />,
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(screen.getByTestId("toggle-sobrante-0")).toBeInTheDocument();
      });

      // Item 0 inicialmente es 'retornar'. Hacemos toggle para pasarlo a 'merma'
      fireEvent.click(screen.getByTestId("toggle-sobrante-0"));
      expect(screen.getByTestId("select-motivo-merma-0")).toBeInTheDocument();

      // Cambiar motivo
      fireEvent.change(screen.getByTestId("select-motivo-merma-0"), {
        target: { value: "Temperatura fuera de rango" },
      });

      // Confirmar aprobación
      const confirmBtn = screen.getByTestId("buffet-confirm-btn");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(apiSpy).toHaveBeenCalledWith(
          expect.stringContaining("/api/v1/operations/buffet/approvals/buffet-sol-101/resolve"),
          expect.objectContaining({
            method: "POST",
            body: expect.objectContaining({
              accion: "aprobar",
              items_override: expect.arrayContaining([
                expect.objectContaining({
                  nombre: "Lomo Liso Vacuno",
                  accion_sobrante: "merma",
                  motivo_merma: "Temperatura fuera de rango",
                }),
              ]),
            }),
          })
        );
        expect(onResolvedMock).toHaveBeenCalled();
      });
    });
  });

  // ==========================================================================
  // 2. ConteoRequestDetails: Comparación Kardex vs Físico y Severidad
  // ==========================================================================
  describe("ConteoRequestDetails", () => {
    it("calcula discrepancias en unidades, delta monetario e indica severidad crítica si supera tolerancia", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
        data: {
          items: [
            {
              id: "c-1",
              producto_nombre: "Carne Vacuno Lomo Vetado",
              stock_teorico: 15.0,
              stock_fisico: 13.0, // Discrepancia: -2.0
              costo_unitario_ppp: 14500, // Delta CLP: -29.000 (supera umbral $5.000)
              unidad: "kg",
            },
            {
              id: "c-2",
              producto_nombre: "Salmón Atlántico Fresco",
              stock_teorico: 8.0,
              stock_fisico: 8.0, // Cuadrado: 0
              costo_unitario_ppp: 12000,
              unidad: "kg",
            },
          ],
        },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "test-tenant",
      });

      render(
        <ConteoRequestDetails
          open={true}
          solicitud={mockConteoSolicitud}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />,
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(screen.getByTestId("conteo-request-details")).toBeInTheDocument();
      });

      // Discrepancia en unidades item 0: -2 kg
      expect(screen.getByTestId("delta-units-0")).toHaveTextContent("-2 kg");

      // Impacto financiero delta item 0: -2 * 14500 = -$29.000
      expect(screen.getByTestId("delta-clp-0")).toHaveTextContent("-$29.000");

      // Como -$29.000 supera la tolerancia de $5.000, badge de severidad debe ser rojo
      expect(screen.getByTestId("badge-severity-red")).toBeInTheDocument();
      expect(screen.getByText(/Supera Tolerancia/i)).toBeInTheDocument();
    });

    it("muestra badge verde 'Sin Discrepancias' cuando el conteo físico coincide 100% con Kardex", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
        data: {
          items: [
            {
              id: "c-1",
              producto_nombre: "Carne Vacuno Lomo Vetado",
              stock_teorico: 15.0,
              stock_fisico: 15.0,
              costo_unitario_ppp: 14500,
              unidad: "kg",
            },
          ],
        },
        traceId: "test-trace",
        timestampIso: new Date().toISOString(),
        tenantId: "test-tenant",
      });

      render(
        <ConteoRequestDetails
          open={true}
          solicitud={mockConteoSolicitud}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />,
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(screen.getByTestId("badge-severity-green")).toBeInTheDocument();
      });
      expect(screen.getByText(/Sin Discrepancias/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 3. RechazoModal: Diálogo Accesible y Validación
  // ==========================================================================
  describe("RechazoModal", () => {
    it("valida justificación obligatoria mayor o igual a 5 caracteres antes de confirmar", async () => {
      const onConfirmRejectMock = vi.fn();
      const onCloseMock = vi.fn();

      render(
        <RechazoModal
          open={true}
          solicitud={mockMermaSolicitud}
          onClose={onCloseMock}
          onConfirmReject={onConfirmRejectMock}
        />,
        { wrapper: Wrapper }
      );

      expect(screen.getByTestId("rechazo-modal")).toBeInTheDocument();
      const textarea = screen.getByTestId("rechazo-modal-textarea");
      const confirmBtn = screen.getByTestId("rechazo-modal-confirm");

      // Intento enviar con menos de 5 caracteres
      fireEvent.change(textarea, { target: { value: "No" } });
      fireEvent.click(confirmBtn);

      // Debe aparecer mensaje de error y no llamar a onConfirmReject
      expect(screen.getByTestId("rechazo-modal-error")).toBeInTheDocument();
      expect(onConfirmRejectMock).not.toHaveBeenCalled();

      // Ingreso motivo válido con >= 5 caracteres
      fireEvent.change(textarea, {
        target: { value: "Cantidad no corresponde al turno" },
      });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(onConfirmRejectMock).toHaveBeenCalledWith(
          "merma-sol-303",
          "Cantidad no corresponde al turno"
        );
        expect(onCloseMock).toHaveBeenCalled();
      });
    });
  });

  // ==========================================================================
  // 4. Edición Inline Pre-Aprobación en SolicitudCard y CompactTable
  // ==========================================================================
  describe("Edición Inline Pre-Aprobación", () => {
    it("permite reclasificar de merma a consumo, ajustar cantidad y lote en SolicitudCard antes de aprobar", async () => {
      const onApproveMock = vi.fn();

      render(
        <SolicitudCard
          solicitud={mockMermaSolicitud}
          onApprove={onApproveMock}
          onReject={vi.fn()}
        />,
        { wrapper: Wrapper }
      );

      // Abrir modo edición inline
      const editBtn = screen.getByTestId("btn-edit-inline-merma-sol-303");
      fireEvent.click(editBtn);

      expect(screen.getByTestId("inline-edit-panel-merma-sol-303")).toBeInTheDocument();

      // Reclasificar naturaleza: pasar de merma a consumo
      const selectTipo = screen.getByTestId("select-inline-tipo-merma-sol-303");
      fireEvent.change(selectTipo, { target: { value: "consumo" } });

      // Ajustar cantidad de 2.5 a 3.0
      const inputCantidad = screen.getByTestId("input-inline-cantidad-merma-sol-303");
      fireEvent.change(inputCantidad, { target: { value: "3" } });

      // Modificar lote
      const inputLote = screen.getByTestId("input-inline-lote-merma-sol-303");
      fireEvent.change(inputLote, { target: { value: "LOTE-2026-N2-CORREGIDO" } });

      // Guardar y Aprobar
      const saveBtn = screen.getByTestId("btn-save-inline-merma-sol-303");
      fireEvent.click(saveBtn);

      expect(onApproveMock).toHaveBeenCalledWith(
        "merma-sol-303",
        expect.objectContaining({
          tipo: "consumo",
          cantidad: 3,
          lote: "LOTE-2026-N2-CORREGIDO",
          editado_pre_aprobacion: true,
        })
      );
    });

    it("permite edición inline en NotificationsCompactTable", async () => {
      const onApproveMock = vi.fn();

      render(
        <NotificationsCompactTable
          solicitudes={[mockMermaSolicitud]}
          onApprove={onApproveMock}
        />,
        { wrapper: Wrapper }
      );

      // Botón editar en tabla compacta
      const editBtn = screen.getByTestId("compact-edit-merma-sol-303");
      fireEvent.click(editBtn);

      // Cambiar tipo y cantidad en fila compacta
      const selectTipo = screen.getByTestId("compact-select-tipo-merma-sol-303");
      fireEvent.change(selectTipo, { target: { value: "consumo" } });

      const inputCantidad = screen.getByTestId("compact-input-cantidad-merma-sol-303");
      fireEvent.change(inputCantidad, { target: { value: "4.5" } });

      // Guardar edición y aprobar
      const saveBtn = screen.getByTestId("compact-save-edit-merma-sol-303");
      fireEvent.click(saveBtn);

      expect(onApproveMock).toHaveBeenCalledWith(
        "merma-sol-303",
        expect.objectContaining({
          tipo: "consumo",
          cantidad: 4.5,
          editado_pre_aprobacion: true,
        })
      );
    });
  });
});
