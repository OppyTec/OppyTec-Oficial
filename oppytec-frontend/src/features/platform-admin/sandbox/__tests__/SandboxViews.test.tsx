import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import { SandboxLayout } from "../SandboxLayout";
import { MockDataSandboxView } from "../MockDataSandboxView";
import { PlaywrightRunnerSandboxView } from "../PlaywrightRunnerSandboxView";
import { FefoDatesSandboxView } from "../FefoDatesSandboxView";
import { AdminSidebar } from "../../AdminSidebar";

// Mock framer-motion to simplify DOM testing
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
    initialRoute = "/admin/sandbox/mock-data",
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

describe("Lab & QA Sandbox — Vistas Base Frontend (Etapa 2)", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("1. SandboxLayout", () => {
    it("debe montar el header base con título, badge de aislamiento de entorno y breadcrumbs", () => {
      renderWithProviders(
        <SandboxLayout activeTab="mock-data">
          <div data-testid="child-content">Vista Mock Data</div>
        </SandboxLayout>
      );

      expect(screen.getByTestId("sandbox-layout-root")).toBeInTheDocument();
      expect(screen.getAllByText("Lab & QA Sandbox").length).toBeGreaterThanOrEqual(2);
      expect(screen.getByTestId("sandbox-env-badge")).toBeInTheDocument();
      expect(screen.getByTestId("sandbox-breadcrumbs")).toBeInTheDocument();
      expect(screen.getByTestId("child-content")).toBeInTheDocument();
    });

    it("debe renderizar las 3 pestañas principales de navegación superior con badges", () => {
      renderWithProviders(
        <SandboxLayout activeTab="mock-data">
          <div>Contenido</div>
        </SandboxLayout>
      );

      expect(screen.getByTestId("sandbox-tab-mock-data")).toBeInTheDocument();
      expect(screen.getByTestId("sandbox-tab-playwright-runner")).toBeInTheDocument();
      expect(screen.getByTestId("sandbox-tab-fefo-dates")).toBeInTheDocument();

      expect(screen.getByText("DATA")).toBeInTheDocument();
      expect(screen.getByText("E2E")).toBeInTheDocument();
      expect(screen.getByText("WARP")).toBeInTheDocument();
    });

    it("debe invocar onTabChange al hacer clic en una pestaña", () => {
      const onTabChangeMock = vi.fn();
      renderWithProviders(
        <SandboxLayout activeTab="mock-data" onTabChange={onTabChangeMock}>
          <div>Contenido</div>
        </SandboxLayout>
      );

      const playwrightTab = screen.getByTestId("sandbox-tab-playwright-runner");
      fireEvent.click(playwrightTab);

      expect(onTabChangeMock).toHaveBeenCalledWith("playwright-runner");
    });
  });

  describe("2. MockDataSandboxView", () => {
    it("debe renderizar el selector de modo, presets cards y panel de estado", () => {
      renderWithProviders(<MockDataSandboxView />);

      expect(screen.getByTestId("mock-data-sandbox-view")).toBeInTheDocument();
      expect(screen.getByTestId("mock-mode-selector")).toBeInTheDocument();
      expect(screen.getByTestId("btn-mode-synthetic")).toBeInTheDocument();
      expect(screen.getByTestId("btn-mode-isolated-db")).toBeInTheDocument();

      // Presets
      expect(screen.getByTestId("card-preset-preset-full-restaurant")).toBeInTheDocument();
      expect(screen.getByTestId("card-preset-preset-fefo-stress")).toBeInTheDocument();
      expect(screen.getByTestId("card-preset-preset-finops-isolation")).toBeInTheDocument();

      // Status Panel
      expect(screen.getByTestId("mock-data-status-panel")).toBeInTheDocument();
      expect(screen.getByTestId("btn-execute-mock-generation")).toBeInTheDocument();
    });

    it("debe permitir cambiar de preset y ejecutar simulación de generación", async () => {
      const onExecuteMock = vi.fn().mockResolvedValue(undefined);
      renderWithProviders(
        <MockDataSandboxView onExecuteGeneration={onExecuteMock} />
      );

      const stressPreset = screen.getByTestId("card-preset-preset-fefo-stress");
      fireEvent.click(stressPreset);

      const executeBtn = screen.getByTestId("btn-execute-mock-generation");
      fireEvent.click(executeBtn);

      await waitFor(() => {
        expect(onExecuteMock).toHaveBeenCalledWith(
          expect.objectContaining({
            volume: "large",
            dryRun: true,
            injectFefoAnomalies: true,
          })
        );
      });
    });

    it("debe deshabilitar la ejecución si el usuario carece del permiso platform_admin.sandbox.manage", () => {
      renderWithProviders(<MockDataSandboxView />, {
        permissions: ["platform_admin.sandbox.access"], // Sin permiso manage
      });

      expect(
        screen.getByText("Solo Lectura (Sin Permiso Manage)")
      ).toBeInTheDocument();
      expect(
        screen.queryByTestId("btn-execute-mock-generation")
      ).not.toBeInTheDocument();
    });
  });

  describe("3. PlaywrightRunnerSandboxView", () => {
    it("debe renderizar selector de navegadores, stepper de pasos y terminal de logs", () => {
      renderWithProviders(<PlaywrightRunnerSandboxView />);

      expect(screen.getByTestId("playwright-runner-sandbox-view")).toBeInTheDocument();
      expect(screen.getByTestId("browser-selector")).toBeInTheDocument();
      expect(screen.getByTestId("btn-browser-chromium")).toBeInTheDocument();
      expect(screen.getByTestId("btn-browser-firefox")).toBeInTheDocument();
      expect(screen.getByTestId("btn-browser-webkit")).toBeInTheDocument();

      // Stepper
      expect(screen.getByTestId("playwright-stepper")).toBeInTheDocument();

      // Terminal
      expect(screen.getByTestId("playwright-logs-terminal")).toBeInTheDocument();
      expect(screen.getByTestId("terminal-empty-state")).toBeInTheDocument();

      // Suite FinOps
      expect(screen.getByTestId("card-suite-finops_tokens")).toBeInTheDocument();
    });

    it("debe permitir seleccionar y disparar la suite finops_tokens", async () => {
      const onTriggerMock = vi.fn().mockResolvedValue(undefined);
      renderWithProviders(
        <PlaywrightRunnerSandboxView onTriggerSuite={onTriggerMock} />
      );

      const finopsSuiteCard = screen.getByTestId("card-suite-finops_tokens");
      fireEvent.click(finopsSuiteCard);

      const runBtn = screen.getByTestId("btn-trigger-pw-suite");
      fireEvent.click(runBtn);

      await waitFor(() => {
        expect(onTriggerMock).toHaveBeenCalledWith(
          expect.objectContaining({
            suiteId: "finops_tokens",
            browser: "chromium",
          })
        );
      });
    });

    it("debe permitir disparar una suite E2E e imprimir logs en la terminal", async () => {
      renderWithProviders(<PlaywrightRunnerSandboxView />);

      const runBtn = screen.getByTestId("btn-trigger-pw-suite");
      fireEvent.click(runBtn);

      // Verificamos que se inicie la ejecución y se pueblen logs
      await waitFor(() => {
        expect(screen.queryByTestId("terminal-empty-state")).not.toBeInTheDocument();
        expect(screen.getByText(/Iniciando runner Playwright/i)).toBeInTheDocument();
      });
    });

    it("debe permitir limpiar la terminal con el botón de trash", async () => {
      renderWithProviders(<PlaywrightRunnerSandboxView />);

      const runBtn = screen.getByTestId("btn-trigger-pw-suite");
      fireEvent.click(runBtn);

      await waitFor(() => {
        expect(screen.queryByTestId("terminal-empty-state")).not.toBeInTheDocument();
      });

      const clearBtn = screen.getByTestId("btn-clear-terminal-logs");
      fireEvent.click(clearBtn);

      expect(screen.getByTestId("terminal-empty-state")).toBeInTheDocument();
    });
  });

  describe("4. FefoDatesSandboxView", () => {
    it("debe renderizar fecha real vs fecha simulada Time-Warp y panel resumen", () => {
      renderWithProviders(<FefoDatesSandboxView />);

      expect(screen.getByTestId("fefo-dates-sandbox-view")).toBeInTheDocument();
      expect(screen.getByTestId("card-real-date")).toBeInTheDocument();
      expect(screen.getByTestId("card-simulated-date")).toBeInTheDocument();
      expect(screen.getByTestId("fefo-summary-panel")).toBeInTheDocument();
      expect(screen.getByTestId("fefo-batches-table-card")).toBeInTheDocument();
    });

    it("debe cambiar la fecha simulada al modificar el desplazamiento de días", () => {
      renderWithProviders(<FefoDatesSandboxView />);

      const selectOffset = screen.getByTestId("select-offset-days");
      fireEvent.change(selectOffset, { target: { value: "30" } });

      expect(screen.getByText(/Desplazamiento proyectado: \+30 días/i)).toBeInTheDocument();
    });

    it("debe ejecutar la simulación de impacto FEFO al presionar Simular", async () => {
      const onRunSimulationMock = vi.fn().mockResolvedValue({
        simulationId: "test-sim",
        executedAt: new Date().toISOString(),
        simulatedSystemDate: "2026-12-05",
        totalBatchesEvaluated: 10,
        criticalBatchesCount: 3,
        expiredBatchesCount: 2,
        totalSpoilageRiskAmount: 950000,
        currency: "CLP",
        alertsCreated: 5,
        batches: [],
      });

      renderWithProviders(
        <FefoDatesSandboxView onRunSimulation={onRunSimulationMock} />
      );

      const simBtn = screen.getByTestId("btn-run-fefo-simulation");
      fireEvent.click(simBtn);

      await waitFor(() => {
        expect(onRunSimulationMock).toHaveBeenCalled();
        expect(screen.getByTestId("kpi-fefo-total").textContent).toBe("10");
        expect(screen.getByTestId("kpi-fefo-critical").textContent).toBe("3");
        expect(screen.getByTestId("kpi-fefo-expired").textContent).toBe("2");
      });
    });
  });

  describe("5. AdminSidebar — Integración de Sección 'Lab & QA Sandbox'", () => {
    it("debe renderizar la sección 'Lab & QA Sandbox' con badge QA y los 3 submenús", () => {
      renderWithProviders(<AdminSidebar isOpen={true} />);

      // Section Header
      expect(screen.getByText("Lab & QA Sandbox")).toBeInTheDocument();
      expect(screen.getByTestId("section-badge-qa")).toBeInTheDocument();

      // Submenu Items
      expect(screen.getByTestId("admin-nav-item-sandbox-mock-data")).toBeInTheDocument();
      expect(screen.getByTestId("admin-nav-item-sandbox-playwright-runner")).toBeInTheDocument();
      expect(screen.getByTestId("admin-nav-item-sandbox-fefo-dates")).toBeInTheDocument();

      expect(screen.getByText("Mock Data & Presets")).toBeInTheDocument();
      expect(screen.getByText("Playwright Runner")).toBeInTheDocument();
      expect(screen.getByText("Simulador FEFO")).toBeInTheDocument();
    });
  });
});
