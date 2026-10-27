/**
 * oppytec-frontend/src/features/oppyfy/__tests__/OppyfyView.test.tsx
 * Pruebas unitarias para la interfaz de usuario de OppyFy (v2.0):
 * 1. Renderizado del workspace completo (Header, ChatPane, CanvasPanel, RBAC).
 * 2. Medidor semafórico de contexto en verde (<65%), ámbar (66-85%) y rojo (>85%).
 * 3. Despliegue de artefactos tipados en el Split-View Canvas (tabla y gráfico con regla inmutable "Pollo King").
 * 4. Apertura y flujo interactivo del modal de rollover asistido al superar el 85% de contexto.
 */

import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import React from "react";
import { describe, it, expect, beforeEach, afterEach, beforeAll, vi } from "vitest";
import { PermissionsProvider, type RbacPolicyState } from "@/shared/auth/usePermissions";
import { CurrencyProvider } from "@/shared/currency";
import * as httpClient from "@/shared/api/httpClient";
import {
  OppyFyFeatureView,
  ContextHealthMeter,
  OppyfyCanvasPanel,
  OppyfyRolloverModal,
  calculateContextHealth,
  type CanvasArtifact,
} from "../index";

// Mock ResizeObserver para compatibilidad con Recharts en jsdom
beforeAll(() => {
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

const mockPolicy: RbacPolicyState = {
  roleName: "Gerente Operaciones",
  planModules: ["oppyfy", "inventory", "recipes", "procurement"],
  rolePermissions: ["oppyfy.workspace.query"],
  temporaryGrants: [],
  deniedPermissions: [],
  isSuperUser: true,
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <CurrencyProvider initialCurrency="CLP">
        <PermissionsProvider initialPolicy={mockPolicy}>
          {ui}
        </PermissionsProvider>
      </CurrencyProvider>
    </QueryClientProvider>
  );
}

describe("OppyFy v2.0 - Split-View Workspace & Interactive UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.clear();
    }
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. WORKSPACE COMPLETO
  // ==========================================================================
  describe("Renderizado del Workspace Completo de OppyFy", () => {
    it("renderiza el workspace, chat pane, canvas, billetera de créditos y controles RBAC", () => {
      renderWithProviders(<OppyFyFeatureView initialRemainingCredits={1250} />);

      expect(screen.getByTestId("feature-oppyfy")).toBeInTheDocument();
      expect(screen.getByTestId("oppyfy-chat-pane")).toBeInTheDocument();
      expect(screen.getByTestId("oppyfy-split-canvas")).toBeInTheDocument();
      expect(screen.getByTestId("oppyfy-credit-wallet")).toBeInTheDocument();
      expect(screen.getByTestId("oppyfy-context-meter")).toBeInTheDocument();
      expect(screen.getByTestId("oppyfy-prompt-input")).toBeInTheDocument();
      expect(screen.getByTestId("oppyfy-send-btn")).toBeInTheDocument();
      expect(screen.getByTestId("oppyfy-rbac-domains")).toBeInTheDocument();

      // Muestra sugerencias de preguntas rápidas
      expect(screen.getByTestId("quick-suggestion-fefo")).toBeInTheDocument();
      expect(screen.getByTestId("quick-suggestion-banquet")).toBeInTheDocument();
      expect(screen.getByTestId("quick-suggestion-food-cost")).toBeInTheDocument();
    });

    it("permite seleccionar una sugerencia rápida e insertarla en el input de consulta", () => {
      renderWithProviders(<OppyFyFeatureView />);

      const fefoChip = screen.getByTestId("quick-suggestion-fefo");
      fireEvent.click(fefoChip);

      const input = screen.getByTestId("oppyfy-prompt-input") as HTMLInputElement;
      expect(input.value).toContain("Pollo King");
    });
  });

  // ==========================================================================
  // 2. MEDIDOR SEMAFÓRICO EN VERDE, ÁMBAR Y ROJO
  // ==========================================================================
  describe("Medidor Semafórico de Contexto RAG (Verde, Ámbar, Rojo)", () => {
    it("renderiza en 🟢 Verde (<65%): óptimo, sin badge de bloqueo ni botón de rollover", () => {
      const health = calculateContextHealth(45);
      renderWithProviders(
        <ContextHealthMeter
          contextHealth={health}
          onOpenRolloverModal={vi.fn()}
        />
      );

      const statusEl = screen.getByTestId("context-traffic-status");
      expect(statusEl).toHaveTextContent("45%");
      expect(statusEl).toHaveTextContent("Óptimo");

      const bar = screen.getByTestId("context-meter-bar");
      expect(bar).toHaveClass("bg-emerald-500");

      expect(
        screen.queryByTestId("anti-hallucination-badge")
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("rollover-prompt-btn")
      ).not.toBeInTheDocument();
    });

    it("renderiza en 🟡 Ámbar (66% - 85%): advertencia preventiva recomendando nuevo hilo", () => {
      const health = calculateContextHealth(78);
      renderWithProviders(
        <ContextHealthMeter
          contextHealth={health}
          onOpenRolloverModal={vi.fn()}
        />
      );

      const statusEl = screen.getByTestId("context-traffic-status");
      expect(statusEl).toHaveTextContent("78%");
      expect(statusEl).toHaveTextContent("Advertencia");

      const bar = screen.getByTestId("context-meter-bar");
      expect(bar).toHaveClass("bg-amber-500");

      expect(
        screen.queryByTestId("anti-hallucination-badge")
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("rollover-prompt-btn")
      ).not.toBeInTheDocument();
    });

    it("renderiza en 🔴 Rojo (>85%): límite crítico, muestra badge de bloqueo y botón destacado de traspaso", () => {
      const onOpenModalMock = vi.fn();
      const health = calculateContextHealth(92);
      renderWithProviders(
        <ContextHealthMeter
          contextHealth={health}
          onOpenRolloverModal={onOpenModalMock}
        />
      );

      const statusEl = screen.getByTestId("context-traffic-status");
      expect(statusEl).toHaveTextContent("92%");
      expect(statusEl).toHaveTextContent("Límite crítico");

      const bar = screen.getByTestId("context-meter-bar");
      expect(bar).toHaveClass("bg-destructive");

      // Badge y botón destacado
      const badge = screen.getByTestId("anti-hallucination-badge");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent("Bloqueo Anti-Alucinación");

      const rolloverBtn = screen.getByTestId("rollover-prompt-btn");
      expect(rolloverBtn).toBeInTheDocument();

      fireEvent.click(rolloverBtn);
      expect(onOpenModalMock).toHaveBeenCalledTimes(1);
    });
  });

  // ==========================================================================
  // 3. DESPLIEGUE DE ARTEFACTOS EN EL SPLIT-VIEW CANVAS (TABLA Y GRÁFICO)
  // ==========================================================================
  describe("Despliegue de Artefactos en Split-View Canvas", () => {
    it("muestra empty state cuando no hay ningún artefacto activo", () => {
      renderWithProviders(<OppyfyCanvasPanel artifact={null} />);
      expect(screen.getByTestId("canvas-empty-state")).toBeInTheDocument();
    });

    it("despliega artefacto de tipo 'table' respetando el nombre propio inmutable 'Pollo King'", () => {
      const tableArtifact: CanvasArtifact = {
        type: "table",
        title: "Lotes Críticos FEFO — Pollo King",
        summary: "Listado de lotes próximos a vencer clasificados por riesgo.",
        columns: [
          { key: "lote", label: "Lote FEFO" },
          { key: "producto", label: "Producto" },
          { key: "dias_venc", label: "Días Restantes" },
          { key: "costo_total", label: "Valorización", type: "currency" },
        ],
        data: [
          {
            lote: "FEFO-881",
            producto: "Pollo King Pechuga Deshuesada",
            dias_venc: 2,
            costo_total: 489000,
          },
          {
            lote: "FEFO-882",
            producto: "Pollo King Trutro Entero",
            dias_venc: 4,
            costo_total: 215000,
          },
        ],
      };

      renderWithProviders(<OppyfyCanvasPanel artifact={tableArtifact} />);

      expect(screen.getByTestId("canvas-table-artifact")).toBeInTheDocument();
      expect(screen.getByText("Lotes Críticos FEFO — Pollo King")).toBeInTheDocument();
      expect(screen.getByText("Pollo King Pechuga Deshuesada")).toBeInTheDocument();
      expect(screen.getByText("Pollo King Trutro Entero")).toBeInTheDocument();
      expect(screen.getByTestId("canvas-table-row-0")).toBeInTheDocument();
      expect(screen.getByTestId("canvas-table-row-1")).toBeInTheDocument();
    });

    it("despliega artefacto de tipo 'chart' con costos teóricos vs reales", () => {
      const chartArtifact: CanvasArtifact = {
        type: "chart",
        title: "Varianza Food Cost Semanal — Pollo King",
        summary: "Comparación entre costo teórico y real por categoría.",
        chartType: "bar",
        data: [
          { name: "Lun", teorico: 120000, real: 125000 },
          { name: "Mar", teorico: 140000, real: 139000 },
          { name: "Mie", teorico: 160000, real: 175000 },
        ],
      };

      renderWithProviders(<OppyfyCanvasPanel artifact={chartArtifact} />);

      expect(screen.getByTestId("canvas-chart-artifact")).toBeInTheDocument();
      expect(
        screen.getByText("Varianza Food Cost Semanal — Pollo King")
      ).toBeInTheDocument();
    });

    it("despliega artefacto de tipo 'action_card' y permite ejecutar la acción con feedback", async () => {
      const onActionMock = vi.fn().mockResolvedValue(undefined);
      const actionArtifact: CanvasArtifact = {
        type: "action_card",
        title: "Borrador de Orden de Compra",
        summary: "Generar pedido automático de reposición para Pollo King.",
        actionId: "po_draft_pollo_king_001",
        data: {},
      };

      renderWithProviders(
        <OppyfyCanvasPanel
          artifact={actionArtifact}
          onExecuteAction={onActionMock}
        />
      );

      expect(
        screen.getByTestId("canvas-action-card-artifact")
      ).toBeInTheDocument();

      const execBtn = screen.getByTestId("canvas-action-execute-btn");
      fireEvent.click(execBtn);

      await waitFor(() => {
        expect(onActionMock).toHaveBeenCalledWith("po_draft_pollo_king_001");
      });

      expect(
        await screen.findByText("Borrador de pedido generado exitosamente")
      ).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 4. APERTURA Y FLUJO DEL MODAL DE ROLLOVER (>85% DE CONTEXTO)
  // ==========================================================================
  describe("Apertura y Flujo del Modal de Rollover Asistido", () => {
    it("abre el modal de rollover asistido cuando el contexto supera 85% y el usuario pulsa continuar", async () => {
      renderWithProviders(<OppyFyFeatureView initialContextPct={89} />);

      // Verificar que el banner de advertencia está presente en el chat pane
      expect(
        screen.getByTestId("anti-hallucination-warning-banner")
      ).toBeInTheDocument();

      // Pulsar el botón de rollover en el medidor
      const rolloverBtn = screen.getByTestId("rollover-prompt-btn");
      fireEvent.click(rolloverBtn);

      // El modal debe estar en pantalla
      const modal = await screen.findByTestId("oppyfy-rollover-modal");
      expect(modal).toBeInTheDocument();
      expect(
        screen.getByText("Contexto inicial garantizado al 5.00%")
      ).toBeInTheDocument();

      // Contiene el textarea con resumen editable
      const summaryInput = screen.getByTestId("rollover-summary-input");
      expect(summaryInput).toBeInTheDocument();
      expect((summaryInput as HTMLTextAreaElement).value).toContain("Pollo King");

      // Botón cancelar cierra el modal
      const cancelBtn = screen.getByTestId("rollover-cancel-btn");
      fireEvent.click(cancelBtn);

      await waitFor(() => {
        expect(
          screen.queryByTestId("oppyfy-rollover-modal")
        ).not.toBeInTheDocument();
      });
    });

    it("ejecuta rollover asistido confirmando el modal y llamando al endpoint de rollover", async () => {
      vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
        data: {
          new_thread_id: "thread-fresh-999",
          previous_thread_id: "thread-old-111",
          fresh_context_usage_percent: "5.00",
          summary_artifact: "Resumen estructurado traspasado con éxito.",
          message: "Hilo nuevo creado con contexto limpio.",
        },
        traceId: "trace-rollover-001",
        timestampIso: new Date().toISOString(),
        tenantId: "tenant_rest_central",
      });

      const onConfirmMock = vi.fn().mockResolvedValue(undefined);

      renderWithProviders(
        <OppyfyRolloverModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={onConfirmMock}
          initialSummary="Síntesis de acuerdos de cocina y lotes críticos."
        />
      );

      const summaryInput = screen.getByTestId("rollover-summary-input");
      fireEvent.change(summaryInput, {
        target: {
          value: "Síntesis actualizada: stock de pechuga Pollo King resuelto.",
        },
      });

      const confirmBtn = screen.getByTestId("rollover-confirm-btn");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(onConfirmMock).toHaveBeenCalledWith(
          "Síntesis actualizada: stock de pechuga Pollo King resuelto."
        );
      });
    });
  });
});
