/**
 * oppytec-frontend/src/features/platform-admin/sandboxTypes.ts
 * Contratos de tipo TypeScript estrictos (0 `any`, `readonly` properties) para:
 * Consola "Lab & QA Sandbox" en Platform Admin de OppyTec v2.0.
 *
 * Arquitectura Clean Architecture & DDD:
 * - Capa de Presentación: Contratos de Vistas Base, Navegación y Breadcrumbs.
 * - Capa de Aplicación / Dominio: DTOs y Estados de Ejecución para Mock Data, Playwright Runner y FEFO Dates.
 * - Seguridad y RBAC: Permisos canónicos de 3 niveles `platform_admin.sandbox.access` y `platform_admin.sandbox.manage`.
 */

import type { LucideIcon } from "lucide-react";
import type { ThreeLevelPermission } from "@/shared/auth/usePermissions";

// ============================================================================
// 1. RBAC PERMISSIONS (3-NIVELES: modulo.submodulo.accion)
// ============================================================================

export const PLATFORM_ADMIN_SANDBOX_ACCESS: ThreeLevelPermission =
  "platform_admin.sandbox.access";
export const PLATFORM_ADMIN_SANDBOX_MANAGE: ThreeLevelPermission =
  "platform_admin.sandbox.manage";

export type SandboxPermission =
  | typeof PLATFORM_ADMIN_SANDBOX_ACCESS
  | typeof PLATFORM_ADMIN_SANDBOX_MANAGE;

// ============================================================================
// 2. IDENTIFICADORES Y NAVEGACIÓN DEL SANDBOX
// ============================================================================

export type SandboxTabId = "mock-data" | "playwright-runner" | "fefo-dates";

export interface SandboxNavItem {
  readonly id: SandboxTabId;
  readonly path: string;
  readonly label: string;
  readonly labelKey: string;
  readonly description: string;
  readonly descriptionKey: string;
  readonly icon: LucideIcon;
  readonly color: string;
  readonly rgb: string;
  readonly badge?: string;
  readonly requiredPermission: SandboxPermission;
}

// ============================================================================
// 3. CONTRATOS DOMINIO: MOCK DATA GENERATOR & SEEDER
// ============================================================================

export type MockDataEntityCategory =
  | "holdings"
  | "tenants"
  | "users"
  | "catalog"
  | "inventory_fefo"
  | "recipes"
  | "invoices"
  | "events"
  | "finops_credits"
  | "all";

export type MockDataVolume = "small" | "medium" | "large" | "stress";

export interface MockDataGenerationConfig {
  readonly tenantSchema: string;
  readonly categories: readonly MockDataEntityCategory[];
  readonly volume: MockDataVolume;
  readonly seedRandom: number | null;
  readonly preserveExisting: boolean;
  readonly dryRun: boolean;
  readonly injectFefoAnomalies: boolean;
  readonly confirmStagingAction?: boolean;
}

export type MockDataStatus = "idle" | "generating" | "success" | "failed";

export interface MockDataGenerationProgress {
  readonly step: string;
  readonly percent: number;
  readonly recordsCreated: Readonly<Record<string, number>>;
  readonly status: MockDataStatus;
  readonly errorMessage: string | null;
  readonly executionDurationMs: number;
}

export interface MockDataHistoryItem {
  readonly id: string;
  readonly createdAt: string;
  readonly executedBy: string;
  readonly tenantSchema: string;
  readonly recordsSummary: Readonly<Record<string, number>>;
  readonly durationMs: number;
  readonly status: "success" | "failed";
}

// ============================================================================
// 4. CONTRATOS DOMINIO: PLAYWRIGHT E2E TEST RUNNER
// ============================================================================

export type PlaywrightTestSuiteId =
  | "smoke"
  | "auth_rbac"
  | "tenant_isolation_idor"
  | "pos_consumo"
  | "inventory_fefo"
  | "recipes_escandallo"
  | "holding_hub"
  | "finops_tokens"
  | "all";

export type PlaywrightBrowserType = "chromium" | "firefox" | "webkit";

export interface PlaywrightRunConfig {
  readonly suiteId: PlaywrightTestSuiteId;
  readonly browser: PlaywrightBrowserType;
  readonly headless: boolean;
  readonly grepFilter: string | null;
  readonly retries: number;
  readonly workers: number;
  readonly targetTenantSchema: string;
  readonly baseUrl?: string;
  readonly confirmProductionRun?: boolean;
}

export type PlaywrightTestStatus =
  | "passed"
  | "failed"
  | "timedOut"
  | "skipped";

export interface PlaywrightTestStep {
  readonly title: string;
  readonly durationMs: number;
  readonly status: PlaywrightTestStatus;
  readonly error: string | null;
}

export interface PlaywrightTestCaseResult {
  readonly id: string;
  readonly title: string;
  readonly suite: string;
  readonly status: PlaywrightTestStatus;
  readonly durationMs: number;
  readonly steps: readonly PlaywrightTestStep[];
  readonly screenshotUrl: string | null;
  readonly traceUrl: string | null;
  readonly errorMessage: string | null;
}

export type PlaywrightExecutionStatus =
  | "idle"
  | "queued"
  | "running"
  | "completed"
  | "failed";

export interface PlaywrightExecutionState {
  readonly runId: string | null;
  readonly status: PlaywrightExecutionStatus;
  readonly startTime: string | null;
  readonly endTime: string | null;
  readonly totalTests: number;
  readonly passedTests: number;
  readonly failedTests: number;
  readonly skippedTests: number;
  readonly currentRunningTest: string | null;
  readonly testResults: readonly PlaywrightTestCaseResult[];
  readonly rawLogs: readonly string[];
}

// ============================================================================
// 4.1 CATÁLOGO DINÁMICO Y EXTENSIBLE DE TESTS PLAYWRIGHT (AGENTE 13 & SUB-PLAN 3)
// ============================================================================

export type PlaywrightDomain =
  | "tenancy"
  | "auth_rbac"
  | "inventory"
  | "recipes"
  | "procurement"
  | "finops"
  | "pos";

export type PlaywrightDomainId = PlaywrightDomain;

export type PlaywrightItemStatus = "ready" | "in_progress" | "planned";

export type PlaywrightTestRunStatus = "passed" | "failed" | "idle";

export interface PlaywrightTestRunResult {
  readonly status: PlaywrightTestRunStatus;
  readonly durationMs: number;
  readonly timestamp: string;
  readonly error: string | null;
  readonly duration_ms?: number;
}

export interface PlaywrightTestItem {
  readonly id: string;
  readonly domain: PlaywrightDomain;
  readonly title: string;
  readonly description: string;
  readonly status: PlaywrightItemStatus;
  readonly tags: readonly string[];
  readonly estimatedDurationSec: number;
  readonly lastRun?: PlaywrightTestRunResult | null;
  readonly estimated_duration_sec?: number;
  readonly last_run?: PlaywrightTestRunResult | null;
}

export interface PlaywrightCatalogSummary {
  readonly total: number;
  readonly ready: number;
  readonly inProgress: number;
  readonly planned: number;
  readonly coveragePercentage: number;
  readonly in_progress?: number;
  readonly coverage_percentage?: number;
}

export interface PlaywrightDomainGroup {
  readonly domain: PlaywrightDomain;
  readonly title: string;
  readonly readyCount: number;
  readonly totalCount: number;
  readonly tests: readonly PlaywrightTestItem[];
  readonly ready_count?: number;
  readonly total_count?: number;
}

export interface PlaywrightCatalogResponse {
  readonly summary: PlaywrightCatalogSummary;
  readonly domains: readonly PlaywrightDomainGroup[];
}

export type PlaywrightRunScope = "all" | "domain" | "test";

export interface PlaywrightRunRequestPayload {
  readonly scope: PlaywrightRunScope;
  readonly targetId?: string | null;
  readonly headless: boolean;
  readonly slowMoMs: number;
  readonly browser?: PlaywrightBrowserType;
  readonly targetTenantSchema?: string;
  readonly confirmProductionRun?: boolean;
  readonly target_id?: string | null;
  readonly slow_mo_ms?: number;
  readonly target_tenant_schema?: string;
  readonly confirm_production_run?: boolean;
}

export interface PlaywrightRunTriggerResponse {
  readonly runId: string;
  readonly status: PlaywrightExecutionStatus;
  readonly testsQueued: number;
  readonly message?: string;
  readonly run_id?: string;
  readonly tests_queued?: number;
}

export type PlaywrightStreamLogLevel =
  | "info"
  | "warn"
  | "error"
  | "debug"
  | "step"
  | "assert";

export interface PlaywrightStreamStepEvent {
  readonly stepIndex: number;
  readonly testId: string;
  readonly message: string;
  readonly level: PlaywrightStreamLogLevel;
  readonly timestamp: string;
  readonly screenshotUrl: string | null;
  readonly durationMs?: number;
  readonly error?: string | null;
  readonly step_index?: number;
  readonly test_id?: string;
  readonly screenshot_url?: string | null;
  readonly duration_ms?: number;
}

// ============================================================================
// 5. CONTRATOS DOMINIO: FEFO DATES & TIME-TRAVEL ENGINE (SUB-PLAN 4)
// ============================================================================

export type FefoWarpMode =
  | "relative_offset"
  | "absolute_date"
  | "spoilage_acceleration";

/**
 * 4 Estados canónicos del semáforo FEFO:
 * - OPTIMAL: >= 15 días restantes (frescura óptima, rotación normal).
 * - WARNING: 7 a 14 días restantes (ventana preventiva, priorizar en producción/buffet).
 * - CRITICAL: 1 a 6 días restantes (riesgo crítico, acción quirúrgica en cocina).
 * - EXPIRED: <= 0 días restantes (vencido/caducado sanitario, 100% computable como merma).
 */
export type FefoBatchCanonicalStatus =
  | "OPTIMAL"
  | "WARNING"
  | "CRITICAL"
  | "EXPIRED";

export type FefoBatchStatus =
  | "optimal"
  | "warning"
  | "critical"
  | "expired"
  | FefoBatchCanonicalStatus;

/**
 * 3 Escenarios de demostración preconfigurados para Platform Admin Sandbox:
 * - HEALTHY: Operación saludable (0% vencido, 10% advertencia, 90% óptimo).
 * - WARNING: Alerta preventiva de fin de semana (20% venciendo en 48h, alertas activas).
 * - CRITICAL: Rotura de cadena de frío / auditoría (15% caducado, 35% riesgo crítico de merma).
 */
export type FefoDemoScenarioId = "HEALTHY" | "WARNING" | "CRITICAL";

export interface FefoDemoScenarioDistribution {
  readonly optimalPct: number;
  readonly warningPct: number;
  readonly criticalPct: number;
  readonly expiredPct: number;
}

export interface FefoDemoScenarioConfig {
  readonly id: FefoDemoScenarioId;
  readonly code: string;
  readonly title: string;
  readonly subtitle: string;
  readonly description: string;
  readonly iconName: string;
  readonly badgeColor: string;
  readonly defaultOffsetDays: number;
  readonly distribution: FefoDemoScenarioDistribution;
  readonly estimatedRiskPct: number;
}

export const FEFO_DEMO_SCENARIO_CONFIGS: Readonly<
  Record<FefoDemoScenarioId, FefoDemoScenarioConfig>
> = {
  HEALTHY: {
    id: "HEALTHY",
    code: "healthy-01",
    title: "Operación Saludable",
    subtitle: "Rotación FEFO óptima y abastecimiento JIT",
    description:
      "Escenario de control de calidad impecable: 0% vencido, 10% en advertencia preventiva y 90% óptimo.",
    iconName: "ShieldCheck",
    badgeColor: "emerald",
    defaultOffsetDays: 0,
    distribution: {
      optimalPct: 90,
      warningPct: 10,
      criticalPct: 0,
      expiredPct: 0,
    },
    estimatedRiskPct: 0,
  },
  WARNING: {
    id: "WARNING",
    code: "warning-02",
    title: "Alerta Fin de Semana",
    subtitle: "20% en ventana crítica de 48h y alertas activas",
    description:
      "Simula acumulación de inventario perecible: 0% vencido, 20% crítico (1-2 días), 30% advertencia y 50% óptimo.",
    iconName: "AlertTriangle",
    badgeColor: "amber",
    defaultOffsetDays: 7,
    distribution: {
      optimalPct: 50,
      warningPct: 30,
      criticalPct: 20,
      expiredPct: 0,
    },
    estimatedRiskPct: 15,
  },
  CRITICAL: {
    id: "CRITICAL",
    code: "critical-03",
    title: "Auditoría / Rotura de Frío",
    subtitle: "15% caducado sanitario y 35% riesgo crítico de merma",
    description:
      "Escenario de auditoría forense o contingencia térmica: 15% caducado, 35% en riesgo inminente, 25% advertencia y 25% óptimo.",
    iconName: "Flame",
    badgeColor: "red",
    defaultOffsetDays: 18,
    distribution: {
      optimalPct: 25,
      warningPct: 25,
      criticalPct: 35,
      expiredPct: 15,
    },
    estimatedRiskPct: 42.5,
  },
} as const;

/**
 * Parámetros del Slider Time-Travel (-30 días a +60 días) con proyección en tiempo real.
 */
export interface FefoTimeTravelRange {
  readonly minDays: number;
  readonly maxDays: number;
  readonly defaultDays: number;
  readonly stepDays: number;
  readonly criticalThresholdDays: number; // 6
  readonly warningThresholdDays: number; // 14
  readonly optimalThresholdDays: number; // 15
}

export const FEFO_TIME_TRAVEL_RANGE: FefoTimeTravelRange = {
  minDays: -30,
  maxDays: 60,
  defaultDays: 0,
  stepDays: 1,
  criticalThresholdDays: 6,
  warningThresholdDays: 14,
  optimalThresholdDays: 15,
} as const;

export interface SandboxStatusResponseDto {
  readonly status: "ready" | "active" | "idle" | "maintenance";
  readonly environment: string;
  readonly availableTools: readonly string[];
  readonly activeRuns: number;
  readonly timestamp: string;
  readonly isolatedTenantSchemas: readonly string[];
  readonly isMutationAllowed: boolean;
  readonly environmentPolicy: string;
}

/**
 * Impacto individual proyectado y valorización financiera de merma por lote FEFO.
 */
export interface FefoBatchSimulationImpact {
  readonly batchId: string;
  readonly productSku: string;
  readonly productName: string;
  readonly category?: string;
  readonly warehouseId?: string;
  readonly isBuffetBatch?: boolean;
  readonly originalExpiryDate: string;
  readonly simulatedExpiryDate: string;
  readonly daysToExpiration: number;
  readonly status: FefoBatchStatus;
  readonly canonicalStatus?: FefoBatchCanonicalStatus;
  readonly stockQuantity: number;
  readonly unitMeasure: string;
  readonly unitCost: number;
  readonly estimatedLossAmount: number;
  readonly estimatedLossFxAmount?: number;
  readonly lossRateApplied?: number;
  // Propiedades snake_case para compatibilidad con backend REST
  readonly batch_id?: string;
  readonly product_sku?: string;
  readonly product_name?: string;
  readonly warehouse_id?: string;
  readonly is_buffet_batch?: boolean;
  readonly original_expiry_date?: string;
  readonly simulated_expiry_date?: string;
  readonly days_to_expiration?: number;
  readonly stock_quantity?: number;
  readonly unit_measure?: string;
  readonly unit_cost?: number;
  readonly estimated_loss_amount?: number;
  readonly estimated_loss_fx_amount?: number;
  readonly loss_rate_applied?: number;
}

/**
 * DTO para la petición de simulación temporal no destructiva FEFO.
 * Endpoint: POST /api/v1/platform-admin/sandbox/fefo/simulate
 */
export interface FefoSimulationRequest {
  readonly mode?: FefoWarpMode;
  readonly offsetDays: number;
  readonly targetDateIso?: string | null;
  readonly tenantSchema: string;
  readonly warehouseId?: string | null;
  readonly affectCategories?: readonly string[];
  readonly scenarioPreset?: FefoDemoScenarioId | null;
  readonly dryRun?: boolean;
  readonly generateSpoilageEvents?: boolean;
  readonly currency?: string;
  readonly exchangeRate?: number;
  readonly confirmStagingAction?: boolean;
  // Propiedades snake_case para interoperabilidad HTTP
  readonly offset_days?: number;
  readonly target_date_iso?: string | null;
  readonly tenant_schema?: string;
  readonly warehouse_id?: string | null;
  readonly affect_categories?: readonly string[];
  readonly scenario_preset?: FefoDemoScenarioId | null;
  readonly dry_run?: boolean;
  readonly generate_spoilage_events?: boolean;
  readonly exchange_rate?: number;
  readonly confirm_staging_action?: boolean;
}

/**
 * Alias retrocompatible con vistas preexistentes
 */
export type FefoWarpConfig = FefoSimulationRequest;

/**
 * DTO para la respuesta de simulación temporal no destructiva FEFO.
 * Endpoint: POST /api/v1/platform-admin/sandbox/fefo/simulate
 */
export interface FefoSimulationResponse {
  readonly simulationId: string;
  readonly executedAt: string;
  readonly simulatedSystemDate: string;
  readonly totalBatchesEvaluated: number;
  readonly optimalBatchesCount?: number;
  readonly warningBatchesCount?: number;
  readonly criticalBatchesCount: number;
  readonly expiredBatchesCount: number;
  readonly totalSpoilageRiskAmount: number;
  readonly totalSpoilageRiskFxAmount?: number;
  readonly currency: string;
  readonly targetFxCurrency?: string;
  readonly alertsCreated: number;
  readonly scenarioApplied?: FefoDemoScenarioId | null;
  readonly batches: readonly FefoBatchSimulationImpact[];
  // Propiedades snake_case para paridad backend
  readonly simulation_id?: string;
  readonly executed_at?: string;
  readonly simulated_system_date?: string;
  readonly total_batches_evaluated?: number;
  readonly optimal_batches_count?: number;
  readonly warning_batches_count?: number;
  readonly critical_batches_count?: number;
  readonly expired_batches_count?: number;
  readonly total_spoilage_risk_amount?: number;
  readonly total_spoilage_risk_fx_amount?: number;
  readonly target_fx_currency?: string;
  readonly alerts_created?: number;
  readonly scenario_applied?: FefoDemoScenarioId | null;
}

/**
 * Alias retrocompatible con vistas preexistentes
 */
export type FefoSimulationResult = FefoSimulationResponse;

/**
 * DTO para la petición de desplazamiento temporal destructivo (Shift).
 * Endpoint: POST /api/v1/platform-admin/sandbox/fefo/shift
 */
export interface FefoShiftRequest {
  readonly mode?: FefoWarpMode;
  readonly offsetDays: number;
  readonly targetDateIso?: string | null;
  readonly tenantSchema: string;
  readonly warehouseId?: string | null;
  readonly affectCategories?: readonly string[];
  readonly dryRun?: boolean;
  readonly generateSpoilageEvents?: boolean;
  readonly recalculateBuffet?: boolean;
  readonly confirmStagingAction?: boolean;
  // Propiedades snake_case
  readonly offset_days?: number;
  readonly target_date_iso?: string | null;
  readonly tenant_schema?: string;
  readonly warehouse_id?: string | null;
  readonly affect_categories?: readonly string[];
  readonly dry_run?: boolean;
  readonly generate_spoilage_events?: boolean;
  readonly recalculate_buffet?: boolean;
  readonly confirm_staging_action?: boolean;
}

/**
 * DTO para la respuesta de desplazamiento temporal destructivo (Shift).
 * Endpoint: POST /api/v1/platform-admin/sandbox/fefo/shift
 */
export interface FefoShiftResponse {
  readonly tenantSchema: string;
  readonly shiftedBatchesCount: number;
  readonly offsetDays: number;
  readonly appliedAt: string;
  readonly status: "applied" | "preview_only";
  readonly buffetsShiftedCount?: number;
  // Propiedades snake_case
  readonly tenant_schema?: string;
  readonly shifted_batches_count?: number;
  readonly offset_days?: number;
  readonly applied_at?: string;
  readonly buffets_shifted_count?: number;
}

/**
 * DTO para la sincronización quirúrgica de fechas a "Hoy" (recalculando lotes de inventario y buffet).
 * Endpoint: POST /api/v1/platform-admin/sandbox/fefo/sync-today
 */
export interface FefoSyncTodayRequest {
  readonly tenantSchema: string;
  readonly warehouseId?: string | null;
  readonly recalculateBuffetLots?: boolean;
  readonly dryRun: boolean;
  readonly confirmStagingAction?: boolean;
  // snake_case
  readonly tenant_schema?: string;
  readonly warehouse_id?: string | null;
  readonly recalculate_buffet_lots?: boolean;
  readonly dry_run?: boolean;
  readonly confirm_staging_action?: boolean;
}

/**
 * DTO para el resultado de sincronización quirúrgica a "Hoy".
 */
export interface FefoSyncTodayResponse {
  readonly tenantSchema: string;
  readonly synchronizedBatchesCount: number;
  readonly buffetsRecalculatedCount: number;
  readonly synchronizedAt: string;
  readonly baseTodayIso: string;
  readonly status: "synchronized" | "preview_only";
  // snake_case
  readonly tenant_schema?: string;
  readonly synchronized_batches_count?: number;
  readonly buffets_recalculated_count?: number;
  readonly synchronized_at?: string;
  readonly base_today_iso?: string;
}

// ============================================================================
// 6. CONTRATOS DE COMPONENTES DE PRESENTACIÓN (VISTAS BASE ETAPA 2)
// ============================================================================

export interface MockDataSandboxViewProps {
  readonly isReadOnly?: boolean;
  readonly initialTenantSchema?: string;
  readonly onExecuteGeneration?: (config: MockDataGenerationConfig) => Promise<void>;
}

export interface PlaywrightRunnerSandboxViewProps {
  readonly isReadOnly?: boolean;
  readonly initialSuiteId?: PlaywrightTestSuiteId;
  readonly initialCatalog?: PlaywrightCatalogResponse;
  readonly onTriggerSuite?: (config: PlaywrightRunConfig) => Promise<void>;
  readonly onTriggerRun?: (payload: PlaywrightRunRequestPayload) => Promise<void>;
  readonly onCancelExecution?: (runId: string) => Promise<void>;
}

export interface FefoDatesSandboxViewProps {
  readonly isReadOnly?: boolean;
  readonly initialTenantSchema?: string;
  readonly initialOffsetDays?: number;
  readonly initialScenario?: FefoDemoScenarioId;
  readonly onRunSimulation?: (config: FefoSimulationRequest) => Promise<FefoSimulationResponse>;
  readonly onApplyDateShift?: (config: FefoShiftRequest | FefoSimulationRequest) => Promise<FefoShiftResponse | void>;
  readonly onSyncToday?: (config: FefoSyncTodayRequest) => Promise<FefoSyncTodayResponse>;
}

export interface SandboxLayoutProps {
  readonly activeTab: SandboxTabId;
  readonly onTabChange?: (tab: SandboxTabId) => void;
  readonly children?: React.ReactNode;
}

// ============================================================================
// 7. PRESETS GASTRONÓMICOS Y DATASETS EDITABLES (SUB-PLAN 2)
// ============================================================================

export type {
  GastronomicPresetId,
  GastronomicPresetCategory,
  GastronomicPresetKpisSummary,
  GastronomicPresetMeta,
  EditableHoldingDto,
  EditableTenantDto,
  EditableWarehouseDto,
  EditableProductDto,
  EditableFefoBatchDto,
  EditableRecipeIngredientDto,
  EditableRecipeDto,
  EditableFinOpsAllocationDto,
  GastronomicDatasetPayload,
  GastronomicPresetDefinition,
  MockDataResetResponse,
} from "./sandbox/presets/types";

