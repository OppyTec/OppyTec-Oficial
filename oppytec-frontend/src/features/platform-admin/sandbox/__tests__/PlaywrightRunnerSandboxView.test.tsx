/**
 * oppytec-frontend/src/features/platform-admin/sandbox/__tests__/PlaywrightRunnerSandboxView.test.tsx
 * Co-creación 1:1 de Tests Unitarios y de Integración para el Sub-Plan 3 / Etapa 2:
 * Consola Dinámica y Extensible de Tests Playwright en Platform Admin Sandbox.
 *
 * Verificaciones:
 * 1. Renderizado correcto del resumen del catálogo (total, % de cobertura, badges de madurez).
 * 2. Renderizado de acordeones por dominio y visualización de pruebas según madurez (READY, IN_PROGRESS, PLANNED).
 * 3. Selector de modos de ejecución (Human Live Demo 500ms vs CI Headless 0ms) y navegador.
 * 4. Interacción de disparo granular de pruebas (all, domain, test) y observabilidad en la terminal de logs.
 * 5. Principio Zero-Code Frontend Addition: reactividad ante catálogos dinámicos provistos por la API.
 */

import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PermissionsProvider } from "@/shared/auth/usePermissions";
import * as httpClient from "@/shared/api/httpClient";
import type { PlaywrightCatalogResponse } from "../../sandboxTypes";
import {
  DEFAULT_PLAYWRIGHT_CATALOG,
  getPlaywrightCatalogApi,
  subscribePlaywrightStream,
  triggerPlaywrightRunApi,
} from "../sandboxApi";
import { PlaywrightRunnerSandboxView } from "../PlaywrightRunnerSandboxView";

// Mock de framer-motion para simplificar renderizado en jsdom
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
    initialRoute = "/admin/sandbox/playwright-runner",
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

describe("Sub-Plan 3 / Etapa 2 — Consola Dinámica y Extensible de Playwright (PlaywrightRunnerSandboxView)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // ==========================================================================
  // 1. RESUMEN DEL CATÁLOGO & MÉTRICAS GLOBALES
  // ==========================================================================
  describe("1. Resumen del Catálogo y Métricas Globales", () => {
    it("debe renderizar el total de tests, porcentaje de cobertura real y badges de madurez", async () => {
      renderWithProviders(
        <PlaywrightRunnerSandboxView initialCatalog={DEFAULT_PLAYWRIGHT_CATALOG} />
      );

      // Verificamos que el contenedor raíz exista
      expect(screen.getByTestId("playwright-runner-sandbox-view")).toBeInTheDocument();

      // Métricas de Total y Cobertura
      const totalMetric = screen.getByTestId("metric-total-tests");
      expect(totalMetric.textContent).toBe("35");

      const coverageMetric = screen.getByTestId("metric-coverage-percentage");
      expect(coverageMetric.textContent).toBe("62.9%");

      // Badges con conteo de pruebas por estado de madurez
      const readyBadge = screen.getByTestId("badge-count-ready");
      expect(readyBadge.textContent).toBe("22");

      const inProgressBadge = screen.getByTestId("badge-count-in-progress");
      expect(inProgressBadge.textContent).toBe("8");

      const plannedBadge = screen.getByTestId("badge-count-planned");
      expect(plannedBadge.textContent).toBe("5");

      // Invariante matemática: Total = Ready + InProgress + Planned (35 = 22 + 8 + 5)
      const sum =
        Number(readyBadge.textContent) +
        Number(inProgressBadge.textContent) +
        Number(plannedBadge.textContent);
      expect(sum).toBe(Number(totalMetric.textContent));

      // Botón global para ejecutar todos los tests ready
      expect(screen.getByTestId("btn-run-all-ready")).toBeInTheDocument();
    });

    it("debe cargar reactivamente el catálogo desde API cuando no se provee initialCatalog", async () => {
      const apiSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: DEFAULT_PLAYWRIGHT_CATALOG,
          traceId: "trace-pw-cat",
          timestampIso: "2026-11-05T00:00:00Z",
          tenantId: "tenant_genesis",
        });

      renderWithProviders(<PlaywrightRunnerSandboxView />);

      await waitFor(() => {
        expect(apiSpy).toHaveBeenCalledWith(
          "/api/v1/platform-admin/sandbox/playwright/catalog",
          expect.objectContaining({ method: "GET" })
        );
        expect(screen.getByTestId("metric-total-tests").textContent).toBe("35");
      });
    });
  });

  // ==========================================================================
  // 2. SELECTOR DE MODO (HUMAN LIVE DEMO VS CI HEADLESS) Y NAVEGADORES
  // ==========================================================================
  describe("2. Selectores de Modo de Ejecución y Navegadores", () => {
    it("debe conmutar entre Modo Human Live Demo (500ms) y Modo CI Headless (0ms)", () => {
      renderWithProviders(
        <PlaywrightRunnerSandboxView initialCatalog={DEFAULT_PLAYWRIGHT_CATALOG} />
      );

      const liveBtn = screen.getByTestId("mode-human-live");
      const ciBtn = screen.getByTestId("mode-ci-headless");
      const cbHeadless = screen.getByTestId("cb-pw-headless") as HTMLInputElement;

      // Por defecto en CI Headless
      expect(ciBtn.className).toContain("bg-emerald-500");
      expect(cbHeadless.checked).toBe(true);

      // Conmutar a Live Demo
      fireEvent.click(liveBtn);
      expect(liveBtn.className).toContain("bg-emerald-500");
      expect(cbHeadless.checked).toBe(false);

      // Volver a CI Headless
      fireEvent.click(ciBtn);
      expect(ciBtn.className).toContain("bg-emerald-500");
      expect(cbHeadless.checked).toBe(true);
    });

    it("debe permitir seleccionar entre los 3 navegadores (Chromium, Firefox, WebKit)", () => {
      renderWithProviders(
        <PlaywrightRunnerSandboxView initialCatalog={DEFAULT_PLAYWRIGHT_CATALOG} />
      );

      const btnChromium = screen.getByTestId("btn-browser-chromium");
      const btnFirefox = screen.getByTestId("btn-browser-firefox");
      const btnWebKit = screen.getByTestId("btn-browser-webkit");

      expect(btnChromium.className).toContain("bg-emerald-500");

      fireEvent.click(btnFirefox);
      expect(btnFirefox.className).toContain("bg-emerald-500");
      expect(btnChromium.className).not.toContain("bg-emerald-500");

      fireEvent.click(btnWebKit);
      expect(btnWebKit.className).toContain("bg-emerald-500");
      expect(btnFirefox.className).not.toContain("bg-emerald-500");
    });
  });

  // ==========================================================================
  // 3. ACORDEONES POR DOMINIO Y FILTRADO POR MADUREZ DE PRUEBAS
  // ==========================================================================
  describe("3. Acordeones por Dominio y Filtrado por Madurez", () => {
    it("debe renderizar los 7 dominios canónicos con sus respectivos conteos de progreso", () => {
      renderWithProviders(
        <PlaywrightRunnerSandboxView initialCatalog={DEFAULT_PLAYWRIGHT_CATALOG} />
      );

      const canonicalDomains = [
        "tenancy",
        "auth_rbac",
        "inventory",
        "recipes",
        "procurement",
        "finops",
        "pos",
      ];

      for (const d of canonicalDomains) {
        expect(screen.getByTestId(`card-suite-${d}`)).toBeInTheDocument();
        expect(screen.getByTestId(`badge-progress-${d}`)).toBeInTheDocument();
        expect(screen.getByTestId(`btn-run-domain-${d}`)).toBeInTheDocument();
      }

      // Conteo específico de Tenancy: (4 ready / 5 total)
      expect(screen.getByTestId("badge-progress-tenancy").textContent).toBe(
        "(4 ready / 5 total)"
      );

      // Conteo específico de POS: (2 ready / 5 total)
      expect(screen.getByTestId("badge-progress-pos").textContent).toBe(
        "(2 ready / 5 total)"
      );
    });

    it("debe diferenciar visualmente las pruebas READY, IN_PROGRESS y PLANNED", () => {
      renderWithProviders(
        <PlaywrightRunnerSandboxView initialCatalog={DEFAULT_PLAYWRIGHT_CATALOG} />
      );

      // Prueba READY: Debe tener badge verde y botón [▶ Correr] individual
      const readyBadge = screen.getByTestId(
        "badge-status-ready-pw_tenancy_01_holding_creation"
      );
      expect(readyBadge).toBeInTheDocument();
      expect(readyBadge.textContent).toContain("READY");

      const runTestBtn = screen.getByTestId(
        "btn-run-test-pw_tenancy_01_holding_creation"
      );
      expect(runTestBtn).toBeInTheDocument();

      // Prueba IN_PROGRESS: Debe indicar que el Agente 13 está en desarrollo activo
      const inProgressBadge = screen.getByTestId(
        "badge-status-in-progress-pw_tenancy_05_holding_cross_switch"
      );
      expect(inProgressBadge).toBeInTheDocument();
      expect(inProgressBadge.textContent).toContain("IN PROGRESS");
      expect(inProgressBadge.textContent).toContain("Agente 13");
      expect(
        screen.queryByTestId(
          "btn-run-test-pw_tenancy_05_holding_cross_switch"
        )
      ).not.toBeInTheDocument();

      // Prueba PLANNED: Debe tener etiqueta de Roadmap
      const plannedBadge = screen.getByTestId(
        "badge-status-planned-pw_inv_05_barcode_scanning"
      );
      expect(plannedBadge).toBeInTheDocument();
      expect(plannedBadge.textContent).toContain("PLANNED");
      expect(plannedBadge.textContent).toContain("Roadmap");
    });
  });

  // ==========================================================================
  // 4. INTERACCIÓN DE DISPARO Y CONSOLA TERMINAL DE LOGS
  // ==========================================================================
  describe("4. Disparo de Pruebas y Visualización en Terminal", () => {
    it("debe permitir disparar una prueba individual y mostrar la salida en vivo en la terminal", async () => {
      const onTriggerRunMock = vi.fn().mockResolvedValue(undefined);
      renderWithProviders(
        <PlaywrightRunnerSandboxView
          initialCatalog={DEFAULT_PLAYWRIGHT_CATALOG}
          onTriggerRun={onTriggerRunMock}
        />
      );

      const runTestBtn = screen.getByTestId(
        "btn-run-test-pw_tenancy_01_holding_creation"
      );
      fireEvent.click(runTestBtn);

      await waitFor(() => {
        expect(onTriggerRunMock).toHaveBeenCalledWith(
          expect.objectContaining({
            scope: "test",
            targetId: "pw_tenancy_01_holding_creation",
            browser: "chromium",
          })
        );
        expect(
          screen.queryByTestId("terminal-empty-state")
        ).not.toBeInTheDocument();
        expect(
          screen.getByText(/Iniciando runner Playwright con motor chromium/i)
        ).toBeInTheDocument();
      });
    });

    it("debe permitir disparar la suite completa de un dominio mediante Ejecutar Suite", async () => {
      const onTriggerRunMock = vi.fn().mockResolvedValue(undefined);
      renderWithProviders(
        <PlaywrightRunnerSandboxView
          initialCatalog={DEFAULT_PLAYWRIGHT_CATALOG}
          onTriggerRun={onTriggerRunMock}
        />
      );

      const runDomainBtn = screen.getByTestId("btn-run-domain-inventory");
      fireEvent.click(runDomainBtn);

      await waitFor(() => {
        expect(onTriggerRunMock).toHaveBeenCalledWith(
          expect.objectContaining({
            scope: "domain",
            targetId: "inventory",
          })
        );
        expect(
          screen.getByText(/Scope: domain \| Target: inventory/i)
        ).toBeInTheDocument();
      });
    });

    it("debe permitir disparar todos los tests ready mediante el botón superior", async () => {
      const onTriggerRunMock = vi.fn().mockResolvedValue(undefined);
      renderWithProviders(
        <PlaywrightRunnerSandboxView
          initialCatalog={DEFAULT_PLAYWRIGHT_CATALOG}
          onTriggerRun={onTriggerRunMock}
        />
      );

      const runAllBtn = screen.getByTestId("btn-run-all-ready");
      fireEvent.click(runAllBtn);

      await waitFor(() => {
        expect(onTriggerRunMock).toHaveBeenCalledWith(
          expect.objectContaining({
            scope: "all",
          })
        );
        expect(screen.getByText(/Scope: all \| Target: all/i)).toBeInTheDocument();
      });
    });

    it("debe limpiar la terminal de logs al presionar el botón de basura", async () => {
      renderWithProviders(
        <PlaywrightRunnerSandboxView initialCatalog={DEFAULT_PLAYWRIGHT_CATALOG} />
      );

      // Disparar para poblar logs
      const runAllBtn = screen.getByTestId("btn-run-all-ready");
      fireEvent.click(runAllBtn);

      await waitFor(() => {
        expect(
          screen.queryByTestId("terminal-empty-state")
        ).not.toBeInTheDocument();
      });

      // Limpiar terminal
      const clearBtn = screen.getByTestId("btn-clear-terminal-logs");
      fireEvent.click(clearBtn);

      expect(screen.getByTestId("terminal-empty-state")).toBeInTheDocument();
    });

    it("debe permitir cancelar la ejecución en curso", async () => {
      const onCancelMock = vi.fn().mockResolvedValue(undefined);
      renderWithProviders(
        <PlaywrightRunnerSandboxView
          initialCatalog={DEFAULT_PLAYWRIGHT_CATALOG}
          onCancelExecution={onCancelMock}
        />
      );

      // Disparar
      const runAllBtn = screen.getByTestId("btn-run-all-ready");
      fireEvent.click(runAllBtn);

      // Verificar que se muestre el botón cancelar
      const cancelBtn = await screen.findByTestId("btn-cancel-pw-execution");
      expect(cancelBtn).toBeInTheDocument();

      fireEvent.click(cancelBtn);

      await waitFor(() => {
        expect(screen.getByText(/Ejecución cancelada por el usuario/i)).toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // 5. PRINCIPIO ZERO-CODE FRONTEND ADDITION
  // ==========================================================================
  describe("5. Principio Zero-Code Frontend Addition", () => {
    it("debe renderizar un catálogo personalizado extendido devuelto por backend sin modificar código frontend", () => {
      const customExtendedCatalog: PlaywrightCatalogResponse = {
        summary: {
          total: 10,
          ready: 8,
          inProgress: 1,
          planned: 1,
          coveragePercentage: 80.0,
        },
        domains: [
          {
            domain: "inventory",
            title: "Inventario Satélite",
            readyCount: 4,
            totalCount: 5,
            tests: [
              {
                id: "pw_custom_sat_01",
                domain: "inventory",
                title: "Traspaso Entre Bodegas Satélite",
                description: "Test generado dinámicamente por backend",
                status: "ready",
                tags: ["custom", "warehouse"],
                estimatedDurationSec: 15,
                lastRun: null,
              },
            ],
          },
          {
            domain: "finops",
            title: "FinOps Hub Extendida",
            readyCount: 4,
            totalCount: 5,
            tests: [
              {
                id: "pw_custom_fin_01",
                domain: "finops",
                title: "Presupuesto por Unidad de Negocio",
                description: "Validación de presupuesto dinámico",
                status: "ready",
                tags: ["custom", "budget"],
                estimatedDurationSec: 20,
                lastRun: null,
              },
            ],
          },
        ],
      };

      renderWithProviders(
        <PlaywrightRunnerSandboxView initialCatalog={customExtendedCatalog} />
      );

      // Las métricas deben reflejar el catálogo inyectado sin listas hardcodeadas
      expect(screen.getByTestId("metric-total-tests").textContent).toBe("10");
      expect(screen.getByTestId("metric-coverage-percentage").textContent).toBe("80%");
      expect(screen.getByTestId("badge-count-ready").textContent).toBe("8");

      // Deben renderizarse los títulos dinámicos
      expect(screen.getByText("Inventario Satélite")).toBeInTheDocument();
      expect(screen.getByText("Traspaso Entre Bodegas Satélite")).toBeInTheDocument();
      expect(screen.getByText("FinOps Hub Extendida")).toBeInTheDocument();
      expect(screen.getByText("Presupuesto por Unidad de Negocio")).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 6. CLIENTE API Y STREAMING SSE (sandboxApi.ts)
  // ==========================================================================
  describe("6. Cliente API y Streaming SSE (sandboxApi)", () => {
    it("getPlaywrightCatalogApi debe invocar GET /api/v1/platform-admin/sandbox/playwright/catalog", async () => {
      const apiSpy = vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
        data: DEFAULT_PLAYWRIGHT_CATALOG,
        traceId: "trace-cat",
        timestampIso: "2026-11-05T00:00:00Z",
        tenantId: "tenant_genesis",
      });

      const res = await getPlaywrightCatalogApi();

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/sandbox/playwright/catalog",
        expect.objectContaining({ method: "GET" })
      );
      expect(res.summary.total).toBe(35);
      expect(res.domains.length).toBe(7);
    });

    it("triggerPlaywrightRunApi debe invocar POST con scope y targetId", async () => {
      const apiSpy = vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
        data: {
          runId: "pw_run_xyz123",
          status: "queued",
          testsQueued: 5,
          message: "Corrida encolada",
        },
        traceId: "trace-run",
        timestampIso: "2026-11-05T00:00:00Z",
        tenantId: "tenant_genesis",
      });

      const res = await triggerPlaywrightRunApi({
        scope: "domain",
        targetId: "recipes",
        headless: true,
        slowMoMs: 0,
        browser: "firefox",
        targetTenantSchema: "tenant_genesis",
      });

      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/sandbox/playwright/run",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            scope: "domain",
            targetId: "recipes",
            browser: "firefox",
          }),
        })
      );
      expect(res.runId).toBe("pw_run_xyz123");
    });

    it("subscribePlaywrightStream debe conectar a EventSource y parsear eventos step y completed", () => {
      const listeners: Record<string, (e: any) => void> = {};
      const closeMock = vi.fn();

      class MockEventSource {
        constructor(public url: string) {}
        addEventListener(event: string, callback: (e: any) => void) {
          listeners[event] = callback;
        }
        close() {
          closeMock();
        }
      }

      vi.stubGlobal("EventSource", MockEventSource as any);

      const onEventMock = vi.fn();
      const onCompleteMock = vi.fn();

      const unsubscribe = subscribePlaywrightStream(
        "run_test_sse",
        onEventMock,
        undefined,
        onCompleteMock
      );

      // Simular recepción de evento 'step'
      expect(listeners["step"]).toBeDefined();
      listeners["step"]?.({
        data: JSON.stringify({
          stepIndex: 1,
          testId: "pw_tenancy_01",
          message: "Navegando a login",
          level: "step",
          timestamp: "2026-11-05T00:00:00Z",
        }),
      });

      expect(onEventMock).toHaveBeenCalledWith(
        expect.objectContaining({
          stepIndex: 1,
          message: "Navegando a login",
          level: "step",
        })
      );

      // Simular evento 'completed'
      expect(listeners["completed"]).toBeDefined();
      listeners["completed"]?.({
        data: JSON.stringify({
          runId: "run_test_sse",
          status: "completed",
          totalTests: 1,
          passedTests: 1,
          failedTests: 0,
        }),
      });

      expect(onCompleteMock).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "completed",
        })
      );

      // Desuscribirse
      unsubscribe();
      expect(closeMock).toHaveBeenCalled();

      vi.unstubAllGlobals();
    });
  });
});
