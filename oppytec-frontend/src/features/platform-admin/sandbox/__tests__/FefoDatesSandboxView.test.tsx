/**
 * oppytec-frontend/src/features/platform-admin/sandbox/__tests__/FefoDatesSandboxView.test.tsx
 *
 * Suite de pruebas unitarias Vitest para la Consola FEFO Dates & Time-Travel Engine (Sub-Plan 4 / Etapa 2).
 * Cobertura de validación:
 * 1. Renderizado completo de controles (Header, Escenarios, Time-Travel Slider, KPIs, Matriz FEFO).
 * 2. Conmutación dinámica de los 3 escenarios calibrados (HEALTHY, WARNING, CRITICAL).
 * 3. Interacción con Time-Travel Slider y botones de acceso rápido ([-7d], [Hoy], [+7d], [+15d], [+30d]).
 * 4. Acción quirúrgica de Sincronización a Hoy ("⚡ Sincronizar Fechas a Hoy").
 * 5. Filtros reactivos por estado de semáforo en la Matriz de Lotes.
 * 6. Modal de confirmación para desplazamiento real en BD y permisos RBAC.
 */

import "@testing-library/jest-dom";
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { formatMoney } from "@/shared/lib";
import { FefoDatesSandboxView } from "../FefoDatesSandboxView";

// Mock de framer-motion para simplificar testing del DOM
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, layout: _l, layoutId: _li, initial: _i, animate: _a, exit: _e, transition: _t, ...props }: any) => (
      <div {...props}>{children}</div>
    ),
    button: ({ children, layout: _l, layoutId: _li, initial: _i, animate: _a, exit: _e, transition: _t, whileHover: _wh, whileTap: _wt, ...props }: any) => (
      <button {...props}>{children}</button>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

function renderWithProviders(
  ui: React.ReactElement,
  {
    initialRoute = "/admin/sandbox/fefo-dates",
    permissions = [
      "platform_admin.sandbox.access",
      "platform_admin.sandbox.manage",
    ],
  } = {}
) {
  const rbacState = {
    roleName: "SuperAdmin",
    isSuperUser: true,
    planModules: ["platform_admin"],
    rolePermissions: permissions as any,
    temporaryGrants: [],
    deniedPermissions: [],
  };

  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <PermissionsProvider initialPolicy={rbacState}>
        {ui}
      </PermissionsProvider>
    </MemoryRouter>
  );
}

describe("Sub-Plan 4 / Etapa 2 — FefoDatesSandboxView & Time-Travel Engine", () => {
  beforeEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 1. RENDERIZADO INICIAL Y ELEMENTOS BASE
  // ==========================================================================
  describe("1. Renderizado Completo del Shell de Simulación FEFO", () => {
    it("debe montar el header base con fecha 'Hoy', selector de bodega, switch Dry-Run y botón quirúrgico", () => {
      renderWithProviders(<FefoDatesSandboxView />);

      expect(screen.getByTestId("fefo-dates-sandbox-view")).toBeInTheDocument();
      expect(screen.getByText("Simulador FEFO & Time-Travel Engine")).toBeInTheDocument();
      expect(screen.getByTestId("select-fefo-warehouse")).toBeInTheDocument();
      expect(screen.getByTestId("cb-fefo-dry-run")).toBeInTheDocument();
      expect(screen.getByTestId("btn-sync-fefo-today")).toBeInTheDocument();

      // Banners de fecha
      expect(screen.getByTestId("card-real-date")).toBeInTheDocument();
      expect(screen.getByTestId("card-simulated-date")).toBeInTheDocument();
      expect(screen.getByTestId("simulated-date-display")).toBeInTheDocument();
    });

    it("debe renderizar las 3 cards de escenarios calibrados y el control Time-Travel Slider", () => {
      renderWithProviders(<FefoDatesSandboxView />);

      expect(screen.getByTestId("fefo-scenarios-selector")).toBeInTheDocument();
      expect(screen.getByTestId("card-scenario-HEALTHY")).toBeInTheDocument();
      expect(screen.getByTestId("card-scenario-WARNING")).toBeInTheDocument();
      expect(screen.getByTestId("card-scenario-CRITICAL")).toBeInTheDocument();

      // Time-Travel Slider y botones rápidos
      expect(screen.getByTestId("slider-time-travel")).toBeInTheDocument();
      expect(screen.getByTestId("slider-offset-display")).toBeInTheDocument();
      expect(screen.getByTestId("btn-quick-offset-minus-7")).toBeInTheDocument();
      expect(screen.getByTestId("btn-quick-offset-0")).toBeInTheDocument();
      expect(screen.getByTestId("btn-quick-offset-plus-7")).toBeInTheDocument();
      expect(screen.getByTestId("btn-quick-offset-plus-15")).toBeInTheDocument();
      expect(screen.getByTestId("btn-quick-offset-plus-30")).toBeInTheDocument();
    });

    it("debe renderizar el panel de KPIs en vivo y la matriz de lotes FEFO", () => {
      renderWithProviders(<FefoDatesSandboxView />);

      // Panel KPIs
      expect(screen.getByTestId("fefo-summary-panel")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-fefo-total")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-fefo-optimal")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-fefo-warning")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-fefo-critical")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-fefo-expired")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-fefo-risk-amount")).toBeInTheDocument();

      // Matriz de lotes
      expect(screen.getByTestId("fefo-batches-table-card")).toBeInTheDocument();
      expect(screen.getByTestId("btn-run-fefo-simulation")).toBeInTheDocument();
      expect(screen.getByTestId("btn-apply-fefo-shift")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 2. CONMUTACIÓN DE ESCENARIOS DE DEMOSTRACIÓN (HEALTHY, WARNING, CRITICAL)
  // ==========================================================================
  describe("2. Selector de Escenarios de Demostración", () => {
    it("debe activar el escenario WARNING, calibrar offset a +7d y recalcular KPIs", () => {
      renderWithProviders(<FefoDatesSandboxView />);

      const cardWarning = screen.getByTestId("card-scenario-WARNING");
      fireEvent.click(cardWarning);

      // Verificamos offset calibrado (+7 días)
      expect(screen.getByTestId("slider-offset-display").textContent).toContain("+7 días");
      expect(screen.getByTestId("fefo-feedback-message")).toBeInTheDocument();

      // En escenario WARNING hay 20 lotes con críticos > 0 y 0 vencidos inicialmente
      expect(screen.getByTestId("kpi-fefo-total").textContent).toBe("20");
      expect(Number(screen.getByTestId("kpi-fefo-critical").textContent)).toBeGreaterThan(0);
    });

    it("debe activar el escenario CRITICAL, calibrar offset a +18d y proyectar mermas y caducidades", () => {
      renderWithProviders(<FefoDatesSandboxView />);

      const cardCritical = screen.getByTestId("card-scenario-CRITICAL");
      fireEvent.click(cardCritical);

      // Verificamos offset calibrado (+18 días)
      expect(screen.getByTestId("slider-offset-display").textContent).toContain("+18 días");

      // En escenario CRITICAL debe haber lotes caducados y merma en riesgo relevante
      const expiredCount = Number(screen.getByTestId("kpi-fefo-expired").textContent);
      expect(expiredCount).toBeGreaterThan(0);
      expect(screen.getByTestId("kpi-fefo-risk-amount").textContent).not.toBe(formatMoney(0, "CLP"));
    });

    it("debe retornar a escenario HEALTHY y restaurar frescura óptima sin caducidades", () => {
      renderWithProviders(<FefoDatesSandboxView initialScenario="CRITICAL" />);

      const cardHealthy = screen.getByTestId("card-scenario-HEALTHY");
      fireEvent.click(cardHealthy);

      expect(screen.getByTestId("slider-offset-display").textContent).toContain("0 días");
      expect(screen.getByTestId("kpi-fefo-expired").textContent).toBe("0");
    });
  });

  // ==========================================================================
  // 3. CONTROL TIME-TRAVEL SLIDER Y BOTONES RÁPIDOS
  // ==========================================================================
  describe("3. Control Time-Travel Slider & Quick Offsets", () => {
    it("debe reaccionar instantáneamente al mover el slider de tiempo a +15 días", () => {
      renderWithProviders(<FefoDatesSandboxView />);

      const slider = screen.getByTestId("slider-time-travel");
      fireEvent.change(slider, { target: { value: "15" } });

      expect(screen.getByTestId("slider-offset-display").textContent).toContain("+15 días");
      expect(screen.getByTestId("select-offset-days")).toHaveValue("15");
    });

    it("debe aplicar saltos temporales exactos con los botones de acceso rápido", () => {
      renderWithProviders(<FefoDatesSandboxView />);

      // Saltos: -7d (auditoría), Hoy (0), +30d (cierre de mes)
      const btnMinus7 = screen.getByTestId("btn-quick-offset-minus-7");
      fireEvent.click(btnMinus7);
      expect(screen.getByTestId("slider-offset-display").textContent).toContain("-7 días");

      const btnPlus30 = screen.getByTestId("btn-quick-offset-plus-30");
      fireEvent.click(btnPlus30);
      expect(screen.getByTestId("slider-offset-display").textContent).toContain("+30 días");

      const btnToday = screen.getByTestId("btn-quick-offset-0");
      fireEvent.click(btnToday);
      expect(screen.getByTestId("slider-offset-display").textContent).toContain("0 días");
    });
  });

  // ==========================================================================
  // 4. ACCIÓN QUIRÚRGICA: SINCRONIZAR FECHAS A HOY
  // ==========================================================================
  describe("4. Acción Quirúrgica '⚡ Sincronizar Fechas a Hoy'", () => {
    it("debe invocar onSyncToday, restablecer el offset a 0 y reactivar lotes caducados", async () => {
      const onSyncTodayMock = vi.fn().mockResolvedValue({
        tenantSchema: "tenant_genesis",
        synchronizedBatchesCount: 20,
        buffetsRecalculatedCount: 4,
        synchronizedAt: new Date().toISOString(),
        baseTodayIso: "2026-11-06",
        status: "synchronized",
      });

      renderWithProviders(
        <FefoDatesSandboxView onSyncToday={onSyncTodayMock} />
      );

      // Provocamos desplazamiento a +30d para que venzan varios lotes
      const btnPlus30 = screen.getByTestId("btn-quick-offset-plus-30");
      fireEvent.click(btnPlus30);

      // Presionamos el botón quirúrgico
      const syncBtn = screen.getByTestId("btn-sync-fefo-today");
      fireEvent.click(syncBtn);

      await waitFor(() => {
        expect(onSyncTodayMock).toHaveBeenCalledWith(
          expect.objectContaining({
            tenantSchema: "tenant_genesis",
            recalculateBuffetLots: true,
          })
        );
        // Debe haber restablecido el offset a 0d
        expect(screen.getByTestId("slider-offset-display").textContent).toContain("0 días");
        expect(screen.getByTestId("fefo-feedback-message")).toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // 5. FILTROS EN LA MATRIZ FEFO
  // ==========================================================================
  describe("5. Matriz de Lotes FEFO y Filtros de Semáforo", () => {
    it("debe permitir filtrar lotes por estado de semáforo", () => {
      renderWithProviders(<FefoDatesSandboxView initialScenario="CRITICAL" />);

      // Filtro Críticos
      const filterCriticalBtn = screen.getByRole("button", { name: "Críticos" });
      fireEvent.click(filterCriticalBtn);

      // Verificamos que solo se muestren lotes en estado CRITICAL o que el filtro esté activo
      expect(filterCriticalBtn.className).toContain("bg-orange-500");

      // Filtro Todos
      const filterAllBtn = screen.getByRole("button", { name: /Todos/i });
      fireEvent.click(filterAllBtn);
      expect(filterAllBtn.className).toContain("bg-foreground");
    });
  });

  // ==========================================================================
  // 6. DESPLAZAMIENTO REAL EN BD Y CONFIRMACIÓN MODAL
  // ==========================================================================
  describe("6. Desplazamiento Real en BD y Modal de Confirmación", () => {
    it("debe abrir el modal de confirmación, cancelar sin mutar y luego confirmar exitosamente", async () => {
      const onApplyShiftMock = vi.fn().mockResolvedValue({
        tenantSchema: "tenant_genesis",
        shiftedBatchesCount: 20,
        offsetDays: 15,
        appliedAt: new Date().toISOString(),
        status: "applied",
      });

      renderWithProviders(
        <FefoDatesSandboxView onApplyDateShift={onApplyShiftMock} />
      );

      // Ajustamos a +15d
      fireEvent.click(screen.getByTestId("btn-quick-offset-plus-15"));

      // Click en Aplicar Desplazamiento
      const applyBtn = screen.getByTestId("btn-apply-fefo-shift");
      fireEvent.click(applyBtn);

      // Modal debe estar visible
      expect(screen.getByTestId("modal-confirm-shift")).toBeInTheDocument();
      expect(screen.getByText("Confirmar Desplazamiento Temporal en BD")).toBeInTheDocument();

      // Cancelar
      const cancelBtn = screen.getByTestId("btn-cancel-shift-modal");
      fireEvent.click(cancelBtn);
      expect(screen.queryByTestId("modal-confirm-shift")).not.toBeInTheDocument();
      expect(onApplyShiftMock).not.toHaveBeenCalled();

      // Abrir de nuevo y confirmar
      fireEvent.click(applyBtn);
      const confirmBtn = screen.getByTestId("btn-confirm-shift-modal");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(onApplyShiftMock).toHaveBeenCalledWith(
          expect.objectContaining({
            offsetDays: 15,
            dryRun: false,
          })
        );
        expect(screen.queryByTestId("modal-confirm-shift")).not.toBeInTheDocument();
        expect(screen.getByTestId("fefo-feedback-message")).toBeInTheDocument();
      });
    });

    it("debe respetar RBAC ocultando el botón destructivo si el usuario carece de permiso manage", () => {
      renderWithProviders(<FefoDatesSandboxView />, {
        permissions: ["platform_admin.sandbox.access"], // Sin manage
      });

      expect(screen.getByText("Modo Solo Lectura")).toBeInTheDocument();
      expect(screen.queryByTestId("btn-apply-fefo-shift")).not.toBeInTheDocument();
      // El botón de simulación dry-run sigue disponible
      expect(screen.getByTestId("btn-run-fefo-simulation")).toBeInTheDocument();
    });
  });
});
