/**
 * oppytec-frontend/src/features/platform-admin/sandbox/__tests__/SandboxApiAndTelemetry.test.ts
 * Pruebas unitarias de Cliente API, Guardrails de Entorno y Propagación de Telemetría OpenTelemetry.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  applyFefoShiftApi,
  executeFactoryReset,
  fetchGastronomicPresets,
  generateMockDataApi,
  getMockDataHistoryApi,
  getPlaywrightRunStatusApi,
  getSandboxStatusApi,
  simulateFefoWarpApi,
  triggerPlaywrightRunApi,
} from "../api";
import * as httpClient from "@/shared/api/httpClient";
import * as envConfig from "@/shared/config/env";

describe("Sandbox API & OpenTelemetry Client (Etapa 3)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("1. getSandboxStatusApi", () => {
    it("debe invocar apiRequest al endpoint GET /api/v1/platform-admin/sandbox/status", async () => {
      const apiRequestSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: {
            status: "ready",
            environment: "local",
            availableTools: ["mock_data_generator"],
            activeRuns: 0,
            timestamp: "2026-11-05T00:00:00Z",
            isolatedTenantSchemas: ["tenant_genesis"],
            isMutationAllowed: true,
            environmentPolicy: "isolated_sandbox_permissive",
          },
          traceId: "test_trace_123",
          timestampIso: "2026-11-05T00:00:00Z",
          tenantId: "tenant_rest_central",
        });

      const res = await getSandboxStatusApi();

      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/sandbox/status",
        expect.objectContaining({ method: "GET" })
      );
      expect(res.environment).toBe("local");
      expect(res.isMutationAllowed).toBe(true);
    });

    it("debe invocar getMockDataHistoryApi correctamente", async () => {
      const apiRequestSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: [
            {
              id: "hist_1",
              createdAt: "2026-11-05T00:00:00Z",
              executedBy: "admin",
              tenantSchema: "tenant_qa_lab",
              recordsSummary: { catalog: 10 },
              durationMs: 50,
              status: "success",
            },
          ],
          traceId: "test_trace_123",
          timestampIso: "2026-11-05T00:00:00Z",
          tenantId: "tenant_rest_central",
        });

      const history = await getMockDataHistoryApi();
      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/sandbox/mock-data/history",
        expect.objectContaining({ method: "GET" })
      );
      expect(history.length).toBe(1);
    });
  });

  describe("2. generateMockDataApi & Client-Side Guardrails", () => {
    it("debe bloquear fail-fast en cliente si entorno es 'production' y dryRun=false", async () => {
      vi.spyOn(envConfig, "getRuntimeEnv").mockReturnValue({
        VITE_ENVIRONMENT: "production",
        VITE_ENV_NAMESPACE: "prod",
        VITE_API_BASE_URL: "https://api.oppytec.com",
        VITE_WS_BASE_URL: "wss://api.oppytec.com/ws",
        VITE_UMAMI_ENABLED: false,
      } as any);

      await expect(
        generateMockDataApi({
          tenantSchema: "tenant_qa_lab",
          categories: ["catalog"],
          volume: "small",
          seedRandom: null,
          preserveExisting: true,
          dryRun: false, // Intento de mutación destructiva
          injectFefoAnomalies: false,
        })
      ).rejects.toThrow(/Acción destructiva 'MockDataGeneration' bloqueada en entorno 'production'/i);
    });

    it("debe bloquear fail-fast en cliente si entorno es 'staging' y no se confirma confirmStagingAction", async () => {
      vi.spyOn(envConfig, "getRuntimeEnv").mockReturnValue({
        VITE_ENVIRONMENT: "staging",
        VITE_ENV_NAMESPACE: "stg",
        VITE_API_BASE_URL: "https://stg-api.oppytec.com",
        VITE_WS_BASE_URL: "wss://stg-api.oppytec.com/ws",
        VITE_UMAMI_ENABLED: false,
      } as any);

      await expect(
        generateMockDataApi({
          tenantSchema: "tenant_qa_lab",
          categories: ["catalog"],
          volume: "small",
          seedRandom: null,
          preserveExisting: true,
          dryRun: false,
          injectFefoAnomalies: false,
          confirmStagingAction: false,
        })
      ).rejects.toThrow(/requiere confirmación explícita \(confirmStagingAction=true\)/i);
    });

    it("debe ejecutar exitosamente si dryRun=true en production", async () => {
      vi.spyOn(envConfig, "getRuntimeEnv").mockReturnValue({
        VITE_ENVIRONMENT: "production",
        VITE_ENV_NAMESPACE: "prod",
        VITE_API_BASE_URL: "https://api.oppytec.com",
        VITE_WS_BASE_URL: "wss://api.oppytec.com/ws",
        VITE_UMAMI_ENABLED: false,
      } as any);

      const apiRequestSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: {
            step: "completed",
            percent: 100,
            recordsCreated: { catalog: 20 },
            status: "success",
            errorMessage: null,
            executionDurationMs: 40,
            dryRun: true,
          },
          traceId: "test_trace_123",
          timestampIso: "2026-11-05T00:00:00Z",
          tenantId: "tenant_rest_central",
        });

      const res = await generateMockDataApi({
        tenantSchema: "tenant_qa_lab",
        categories: ["catalog"],
        volume: "small",
        seedRandom: null,
        preserveExisting: true,
        dryRun: true,
        injectFefoAnomalies: false,
      });

      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/sandbox/mock-data/generate",
        expect.objectContaining({ method: "POST" })
      );
      expect(res.status).toBe("success");
    });
  });

  describe("3. applyFefoShiftApi", () => {
    it("debe bloquear fail-fast en cliente si entorno es 'production' y dryRun=false", async () => {
      vi.spyOn(envConfig, "getRuntimeEnv").mockReturnValue({
        VITE_ENVIRONMENT: "production",
        VITE_ENV_NAMESPACE: "prod",
        VITE_API_BASE_URL: "https://api.oppytec.com",
        VITE_WS_BASE_URL: "wss://api.oppytec.com/ws",
        VITE_UMAMI_ENABLED: false,
      } as any);

      await expect(
        applyFefoShiftApi({
          mode: "relative_offset",
          offsetDays: 10,
          targetDateIso: null,
          tenantSchema: "tenant_qa_lab",
          warehouseId: null,
          affectCategories: [],
          dryRun: false,
          generateSpoilageEvents: false,
        })
      ).rejects.toThrow(/Acción destructiva 'FefoShift' bloqueada en entorno 'production'/i);
    });
  });

  describe("4. triggerPlaywrightRunApi", () => {
    it("debe disparar la suite mediante POST /api/v1/platform-admin/sandbox/playwright/run", async () => {
      const apiRequestSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: {
            runId: "pw_test_1",
            suiteId: "smoke",
            status: "completed",
            startTime: "2026-11-05T00:00:00Z",
            endTime: "2026-11-05T00:00:01Z",
            totalTests: 1,
            passedTests: 1,
            failedTests: 0,
            skippedTests: 0,
            currentRunningTest: null,
            testResults: [],
            rawLogs: ["Suite completed"],
          },
          traceId: "test_trace_123",
          timestampIso: "2026-11-05T00:00:00Z",
          tenantId: "tenant_rest_central",
        });

      const res = await triggerPlaywrightRunApi({
        suiteId: "smoke",
        browser: "chromium",
        headless: true,
        grepFilter: null,
        retries: 0,
        workers: 1,
        targetTenantSchema: "tenant_qa_lab",
      });

      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/sandbox/playwright/run",
        expect.objectContaining({ method: "POST" })
      );
      expect(res.runId).toBe("pw_test_1");
    });

    it("debe consultar getPlaywrightRunStatusApi mediante GET", async () => {
      const apiRequestSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: {
            runId: "pw_test_1",
            suiteId: "smoke",
            status: "completed",
            startTime: "2026-11-05T00:00:00Z",
            endTime: "2026-11-05T00:00:01Z",
            totalTests: 1,
            passedTests: 1,
            failedTests: 0,
            skippedTests: 0,
            currentRunningTest: null,
            testResults: [],
            rawLogs: [],
          },
          traceId: "test_trace_123",
          timestampIso: "2026-11-05T00:00:00Z",
          tenantId: "tenant_rest_central",
        });

      const res = await getPlaywrightRunStatusApi("pw_test_1");
      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/sandbox/playwright/status/pw_test_1",
        expect.objectContaining({ method: "GET" })
      );
      expect(res.runId).toBe("pw_test_1");
    });
  });

  describe("5. simulateFefoWarpApi", () => {
    it("debe invocar POST /api/v1/platform-admin/sandbox/fefo/simulate", async () => {
      const apiRequestSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: {
            simulationId: "sim_123",
            executedAt: "2026-11-05T00:00:00Z",
            simulatedSystemDate: "2026-11-15",
            totalBatchesEvaluated: 5,
            criticalBatchesCount: 1,
            expiredBatchesCount: 1,
            totalSpoilageRiskAmount: 50000,
            currency: "CLP",
            alertsCreated: 2,
            batches: [],
          },
          traceId: "test_trace_123",
          timestampIso: "2026-11-05T00:00:00Z",
          tenantId: "tenant_rest_central",
        });

      const res = await simulateFefoWarpApi({
        mode: "relative_offset",
        offsetDays: 10,
        targetDateIso: null,
        tenantSchema: "tenant_qa_lab",
        warehouseId: null,
        affectCategories: [],
        dryRun: true,
        generateSpoilageEvents: false,
      });

      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/sandbox/fefo/simulate",
        expect.objectContaining({ method: "POST" })
      );
      expect(res.simulationId).toBe("sim_123");
      expect(res.totalBatchesEvaluated).toBe(5);
    });
  });

  describe("6. OpenTelemetry Header Integration con httpClient", () => {
    it("buildApiHeaders debe generar cabeceras con X-Trace-ID y traceparent", () => {
      const headers = httpClient.buildApiHeaders();
      expect(headers).toHaveProperty("X-Trace-ID");
      expect(headers).toHaveProperty("traceparent");
      const traceId = headers["X-Trace-ID"];
      expect(typeof traceId).toBe("string");
      expect(traceId?.length).toBe(32);
      expect(headers.traceparent).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
    });

    it("buildApiHeaders debe inyectar X-OppyTec-Mock-Mode según el estado activo", () => {
      const headers = httpClient.buildApiHeaders();
      expect(headers).toHaveProperty("X-OppyTec-Mock-Mode");
      expect(["demo", "clean"]).toContain(headers["X-OppyTec-Mock-Mode"]);
    });
  });

  describe("7. Sub-Plan 2: Factory Reset Guardrails y Telemetría Distribuida", () => {
    it("executeFactoryReset debe bloquear fail-fast en cliente si entorno es 'production'", async () => {
      vi.spyOn(envConfig, "getRuntimeEnv").mockReturnValue({
        VITE_ENVIRONMENT: "production",
        VITE_ENV_NAMESPACE: "prod",
        VITE_API_BASE_URL: "https://api.oppytec.com",
        VITE_WS_BASE_URL: "wss://api.oppytec.com/ws",
        VITE_UMAMI_ENABLED: false,
      } as any);

      await expect(
        executeFactoryReset("tenant_qa_lab", "fast-food-pollo-king", true, true)
      ).rejects.toThrow(/Acción destructiva 'FactoryReset' bloqueada en entorno 'production'/);
    });

    it("executeFactoryReset debe exigir confirmación explícita en 'staging'", async () => {
      vi.spyOn(envConfig, "getRuntimeEnv").mockReturnValue({
        VITE_ENVIRONMENT: "staging",
        VITE_ENV_NAMESPACE: "staging",
        VITE_API_BASE_URL: "https://staging-api.oppytec.com",
        VITE_WS_BASE_URL: "wss://staging-api.oppytec.com/ws",
        VITE_UMAMI_ENABLED: false,
      } as any);

      // Sin confirmación de staging -> rechazo fail-fast
      await expect(
        executeFactoryReset("tenant_qa_lab", "carnes-angus-cava", true, false)
      ).rejects.toThrow(/requiere confirmación explícita/);

      // Con confirmación de staging -> ejecución permitida e inyección de header X-Sandbox-Confirm-Staging
      const apiRequestSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: {
            tenantSchema: "tenant_qa_lab",
            presetRestored: "carnes-angus-cava",
            restoredAt: "2026-11-05T00:00:00Z",
            tablesTruncated: ["inventory_items"],
            recordsReseeded: { products: 6 },
            durationMs: 40,
          },
          traceId: "test_trace_staging_reset",
          timestampIso: "2026-11-05T00:00:00Z",
          tenantId: "tenant_qa_lab",
        });

      const res = await executeFactoryReset(
        "tenant_qa_lab",
        "carnes-angus-cava",
        true,
        true
      );
      expect(res.presetRestored).toBe("carnes-angus-cava");
      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/sandbox/mock-data/reset",
        expect.objectContaining({
          method: "POST",
          headers: { "X-Sandbox-Confirm-Staging": "true" },
          body: expect.objectContaining({
            tenantSchema: "tenant_qa_lab",
            confirmStagingAction: true,
          }),
        })
      );
    });

    it("fetchGastronomicPresets debe invocar /api/v1/platform-admin/sandbox/presets", async () => {
      const apiRequestSpy = vi
        .spyOn(httpClient, "apiRequest")
        .mockResolvedValueOnce({
          data: [
            {
              id: "fast-food-pollo-king",
              name: "Fast Food Pollo King",
              description: "Test",
              tag: "QSR",
              color: "amber",
              productsCount: 6,
              batchesCount: 6,
              recipesCount: 2,
            },
          ] as any,
          traceId: "test_trace_presets",
          timestampIso: "2026-11-05T00:00:00Z",
          tenantId: "tenant_rest_central",
        });

      const presets = await fetchGastronomicPresets();
      expect(presets.length).toBe(1);
      expect(apiRequestSpy).toHaveBeenCalledWith(
        "/api/v1/platform-admin/sandbox/presets",
        expect.objectContaining({ method: "GET" })
      );
    });
  });
});
