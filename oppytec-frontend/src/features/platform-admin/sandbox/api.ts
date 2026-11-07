/**
 * oppytec-frontend/src/features/platform-admin/sandbox/api.ts
 * Cliente HTTP y Adaptador de Observabilidad OpenTelemetry para la consola "Lab & QA Sandbox".
 *
 * Responsabilidades:
 * - Comunicación con los endpoints FastAPI `/api/v1/platform-admin/sandbox/*`.
 * - Inyección automática de cabeceras de telemetría W3C (`traceparent`, `X-Trace-ID`) mediante `buildApiHeaders`.
 * - Guardrails fail-fast del lado cliente para los 5 entornos canónicos (local, preview, ci, staging, production).
 * - Fallbacks defensivos y tipado estricto (0 `any`, `readonly`).
 */

import { apiRequest } from "@/shared/api/httpClient";
import { getRuntimeEnv } from "@/shared/config/env";
import {
  MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY,
  MOCK_DATA_RESET_EVENT_NAME,
} from "@/shared/mock/mockModeStorage";
import type {
  FefoSimulationResult,
  FefoWarpConfig,
  MockDataGenerationConfig,
  MockDataGenerationProgress,
  MockDataHistoryItem,
  PlaywrightExecutionState,
  SandboxStatusResponseDto,
} from "../sandboxTypes";
import {
  GASTRONOMIC_PRESET_METAS,
  type GastronomicPresetId,
  type GastronomicPresetMeta,
  type MockDataResetResponse,
} from "./presets";

export interface FefoShiftApiResponse {
  readonly tenantSchema: string;
  readonly shiftedBatchesCount: number;
  readonly offsetDays: number;
  readonly appliedAt: string;
  readonly status: "applied" | "preview_only";
}

/**
 * Validador preventivo fail-fast para blindar mutaciones según el entorno canónico activo.
 */
function validateClientEnvironmentGuardrails(
  action: string,
  dryRun: boolean,
  confirmStaging?: boolean
): void {
  const env = getRuntimeEnv();
  const currentEnv = env.VITE_ENVIRONMENT;

  if (currentEnv === "production" && !dryRun) {
    throw new Error(
      `[Fail-Fast Guardrail] Acción destructiva '${action}' bloqueada en entorno 'production'. Solo se permite simulación (dryRun=true).`
    );
  }

  if (currentEnv === "staging" && !dryRun && !confirmStaging) {
    throw new Error(
      `[Fail-Fast Guardrail] Acción destructiva '${action}' en entorno 'staging' requiere confirmación explícita (confirmStagingAction=true).`
    );
  }
}

/**
 * Consulta el estado operacional y salud del sandbox en el backend.
 */
export async function getSandboxStatusApi(): Promise<SandboxStatusResponseDto> {
  const env = getRuntimeEnv();
  const fallback: SandboxStatusResponseDto = {
    status: "ready",
    environment: env.VITE_ENVIRONMENT,
    availableTools: ["mock_data_generator", "playwright_e2e_runner", "fefo_time_warp"],
    activeRuns: 0,
    timestamp: new Date().toISOString(),
    isolatedTenantSchemas: ["tenant_genesis", "tenant_qa_lab", "tenant_sandbox_fefo"],
    isMutationAllowed: env.VITE_ENVIRONMENT !== "production",
    environmentPolicy:
      env.VITE_ENVIRONMENT === "production"
        ? "strict_read_only_protection"
        : env.VITE_ENVIRONMENT === "staging"
          ? "staging_confirmation_required"
          : "isolated_sandbox_permissive",
  };

  const response = await apiRequest<SandboxStatusResponseDto>(
    "/api/v1/platform-admin/sandbox/status",
    {
      method: "GET",
      fallbackData: fallback,
    }
  );

  return response.data;
}

/**
 * Obtiene el historial de generaciones de Mock Data.
 */
export async function getMockDataHistoryApi(): Promise<readonly MockDataHistoryItem[]> {
  const response = await apiRequest<readonly MockDataHistoryItem[]>(
    "/api/v1/platform-admin/sandbox/mock-data/history",
    {
      method: "GET",
      fallbackData: [],
    }
  );

  return response.data;
}

/**
 * Dispara la generación sintética o preview dry-run de datos.
 */
export async function generateMockDataApi(
  config: MockDataGenerationConfig
): Promise<MockDataGenerationProgress> {
  validateClientEnvironmentGuardrails(
    "MockDataGeneration",
    config.dryRun,
    config.confirmStagingAction
  );

  const response = await apiRequest<MockDataGenerationProgress>(
    "/api/v1/platform-admin/sandbox/mock-data/generate",
    {
      method: "POST",
      body: {
        tenantSchema: config.tenantSchema,
        categories: config.categories,
        volume: config.volume,
        seedRandom: config.seedRandom,
        preserveExisting: config.preserveExisting,
        dryRun: config.dryRun,
        injectFefoAnomalies: config.injectFefoAnomalies,
        confirmStagingAction: config.confirmStagingAction ?? false,
      },
    }
  );

  return response.data;
}

/**
 * Consulta el estado y trazas de una corrida Playwright.
 */
export async function getPlaywrightRunStatusApi(
  runId: string
): Promise<PlaywrightExecutionState> {
  const response = await apiRequest<PlaywrightExecutionState>(
    `/api/v1/platform-admin/sandbox/playwright/status/${encodeURIComponent(runId)}`,
    {
      method: "GET",
    }
  );

  return response.data;
}

export {
  DEFAULT_PLAYWRIGHT_CATALOG,
  getPlaywrightCatalogApi,
  triggerPlaywrightRunApi,
  subscribePlaywrightStream,
  simulateFefoApi,
  shiftFefoApi,
  syncFefoTodayApi,
} from "./sandboxApi";

/**
 * Ejecuta simulación no destructiva de Time-Warp FEFO.
 */
export async function simulateFefoWarpApi(
  config: FefoWarpConfig
): Promise<FefoSimulationResult> {
  const response = await apiRequest<FefoSimulationResult>(
    "/api/v1/platform-admin/sandbox/fefo/simulate",
    {
      method: "POST",
      body: {
        mode: config.mode,
        offsetDays: config.offsetDays,
        targetDateIso: config.targetDateIso,
        tenantSchema: config.tenantSchema,
        warehouseId: config.warehouseId,
        affectCategories: config.affectCategories,
        dryRun: config.dryRun,
        generateSpoilageEvents: config.generateSpoilageEvents,
      },
    }
  );

  return response.data;
}

/**
 * Aplica el desplazamiento temporal físico a los lotes en el esquema de prueba.
 */
export async function applyFefoShiftApi(
  config: FefoWarpConfig
): Promise<FefoShiftApiResponse> {
  validateClientEnvironmentGuardrails(
    "FefoShift",
    Boolean(config.dryRun),
    config.confirmStagingAction
  );

  const response = await apiRequest<FefoShiftApiResponse>(
    "/api/v1/platform-admin/sandbox/fefo/shift",
    {
      method: "POST",
      body: {
        mode: config.mode,
        offsetDays: config.offsetDays,
        targetDateIso: config.targetDateIso,
        tenantSchema: config.tenantSchema,
        warehouseId: config.warehouseId,
        affectCategories: config.affectCategories,
        dryRun: config.dryRun,
        generateSpoilageEvents: config.generateSpoilageEvents,
        confirmStagingAction: config.confirmStagingAction ?? false,
      },
    }
  );

  return response.data;
}

/**
 * Consulta el catálogo de presets gastronómicos disponibles en el backend.
 * Utiliza fallback defensivo con los presets canónicos estáticos.
 */
export async function fetchGastronomicPresets(): Promise<readonly GastronomicPresetMeta[]> {
  const response = await apiRequest<readonly GastronomicPresetMeta[]>(
    "/api/v1/platform-admin/sandbox/presets",
    {
      method: "GET",
      fallbackData: GASTRONOMIC_PRESET_METAS,
    }
  );

  return response.data;
}

/**
 * Ejecuta el Factory Reset en el backend y limpia mutaciones locales en el cliente.
 * Restaura las tablas del esquema seleccionado a su dataset canónico original.
 */
export async function executeFactoryReset(
  tenantSchema: string,
  targetPresetId: GastronomicPresetId,
  confirmReset = true,
  confirmStagingAction = false
): Promise<MockDataResetResponse> {
  validateClientEnvironmentGuardrails("FactoryReset", false, confirmStagingAction);

  const fallback: MockDataResetResponse = {
    tenantSchema,
    presetRestored: targetPresetId,
    restoredAt: new Date().toISOString(),
    tablesTruncated: [
      "kardex_movements",
      "fefo_batches",
      "inventory_items",
      "recipes",
      "invoices",
    ],
    recordsReseeded: {
      products: targetPresetId === "clean-slate" ? 0 : 6,
      batches: targetPresetId === "clean-slate" ? 0 : 6,
      recipes: targetPresetId === "clean-slate" ? 0 : 2,
    },
    durationMs: 85,
  };

  const response = await apiRequest<MockDataResetResponse>(
    "/api/v1/platform-admin/sandbox/mock-data/reset",
    {
      method: "POST",
      body: {
        tenantSchema,
        targetPresetId,
        confirmReset,
        confirmStagingAction,
      },
      headers: confirmStagingAction
        ? { "X-Sandbox-Confirm-Staging": "true" }
        : undefined,
      fallbackData: fallback,
    }
  );

  // Limpieza en cliente (localStorage y notificación de evento)
  if (typeof window !== "undefined" && typeof window.localStorage !== "undefined") {
    try {
      window.localStorage.removeItem(MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY);
    } catch {
      // Ignorar restricciones en entornos aislados
    }
    if (typeof window.dispatchEvent === "function") {
      window.dispatchEvent(
        new CustomEvent(MOCK_DATA_RESET_EVENT_NAME, {
          detail: { tenantSchema, targetPresetId },
        })
      );
    }
  }

  return response.data;
}
