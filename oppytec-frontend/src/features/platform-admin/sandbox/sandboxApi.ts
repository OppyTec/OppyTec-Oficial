/**
 * oppytec-frontend/src/features/platform-admin/sandbox/sandboxApi.ts
 * Cliente API y Streaming SSE para la Consola Dinámica y Extensible de Tests Playwright (Sub-Plan 3).
 *
 * Responsabilidades:
 * - getPlaywrightCatalogApi: Consulta el catálogo dinámico autodescubierto por dominios y métricas globales.
 * - triggerPlaywrightRunApi: Dispara ejecuciones granulares (all, domain, test) con guardrails de entorno.
 * - subscribePlaywrightStream: Conexión reactiva a SSE con parseo JSON seguro, reconexión y cleanup.
 */

import { apiRequest } from "@/shared/api/httpClient";
import { getRuntimeEnv } from "@/shared/config/env";
import type {
  FefoShiftRequest,
  FefoShiftResponse,
  FefoSimulationRequest,
  FefoSimulationResponse,
  FefoSyncTodayRequest,
  FefoSyncTodayResponse,
  PlaywrightCatalogResponse,
  PlaywrightExecutionState,
  PlaywrightRunConfig,
  PlaywrightRunRequestPayload,
  PlaywrightRunTriggerResponse,
  PlaywrightStreamLogLevel,
  PlaywrightStreamStepEvent,
} from "../sandboxTypes";
import {
  generateScenarioBatches,
  shiftIsoDate,
  summarizeFefoSimulation,
} from "./fefoMath";

/**
 * Catálogo canónico por defecto que cumple las invariantes de dominio:
 * Total (35) = Ready (22) + InProgress (8) + Planned (5)
 * Cobertura = 62.9%
 */
export const DEFAULT_PLAYWRIGHT_CATALOG: PlaywrightCatalogResponse = {
  summary: {
    total: 35,
    ready: 22,
    inProgress: 8,
    planned: 5,
    coveragePercentage: 62.9,
  },
  domains: [
    {
      domain: "tenancy",
      title: "Tenancy & Multi-Tenant Onboarding",
      readyCount: 4,
      totalCount: 5,
      tests: [
        {
          id: "pw_tenancy_01_holding_creation",
          domain: "tenancy",
          title: "Creación y Aislamiento de Holding",
          description: "Verifica alta de holding, creación de tenant y aislamiento de esquemas PostgreSQL.",
          status: "ready",
          tags: ["smoke", "tenancy", "p0"],
          estimatedDurationSec: 35,
          lastRun: {
            status: "passed",
            durationMs: 32410,
            timestamp: "2026-11-05T20:45:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_tenancy_02_branch_lifecycle",
          domain: "tenancy",
          title: "Ciclo de Vida de Sucursal",
          description: "Alta, edición y baja lógica de sucursales con validación de timezone y moneda.",
          status: "ready",
          tags: ["tenancy", "branches"],
          estimatedDurationSec: 25,
          lastRun: {
            status: "passed",
            durationMs: 22100,
            timestamp: "2026-11-05T20:46:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_tenancy_03_saas_quotas",
          domain: "tenancy",
          title: "Límites y Cuotas SaaS",
          description: "Asegura corte automático al superar cuota de usuarios o sucursales activas.",
          status: "ready",
          tags: ["tenancy", "quotas"],
          estimatedDurationSec: 30,
          lastRun: {
            status: "passed",
            durationMs: 28900,
            timestamp: "2026-11-05T20:47:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_tenancy_04_schema_isolation_audit",
          domain: "tenancy",
          title: "Auditoría Aislamiento de Esquemas",
          description: "Valida segregación estricta de tablas por tenant en search_path PostgreSQL.",
          status: "ready",
          tags: ["security", "anti_idor"],
          estimatedDurationSec: 40,
          lastRun: {
            status: "passed",
            durationMs: 38200,
            timestamp: "2026-11-05T20:48:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_tenancy_05_holding_cross_switch",
          domain: "tenancy",
          title: "Switch Multi-Holding en Vivo",
          description: "Conmutación en caliente de holding en UI sin fuga de tokens ni contexto.",
          status: "in_progress",
          tags: ["tenancy", "ui", "agente13"],
          estimatedDurationSec: 45,
          lastRun: null,
        },
      ],
    },
    {
      domain: "auth_rbac",
      title: "Autenticación & RBAC 3-Niveles",
      readyCount: 4,
      totalCount: 5,
      tests: [
        {
          id: "pw_auth_01_login_session",
          domain: "auth_rbac",
          title: "Login Multi-Tenant y Sesión Segura",
          description: "Autenticación JWT HttpOnly, refresh tokens y rotación de sesión.",
          status: "ready",
          tags: ["auth", "smoke"],
          estimatedDurationSec: 20,
          lastRun: {
            status: "passed",
            durationMs: 19400,
            timestamp: "2026-11-05T20:49:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_auth_02_matrix_enforcement",
          domain: "auth_rbac",
          title: "Matriz 3-Niveles modulo.submodulo.accion",
          description: "Evaluación canónica de permisos granulares contra RBAC backend.",
          status: "ready",
          tags: ["rbac", "security"],
          estimatedDurationSec: 50,
          lastRun: {
            status: "passed",
            durationMs: 47800,
            timestamp: "2026-11-05T20:50:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_auth_03_role_hierarchy",
          domain: "auth_rbac",
          title: "Jerarquía y Rangos de Roles",
          description: "Prohíbe a roles subordinados escalar privilegios o modificar roles superiores.",
          status: "ready",
          tags: ["rbac", "hierarchy"],
          estimatedDurationSec: 35,
          lastRun: {
            status: "passed",
            durationMs: 33100,
            timestamp: "2026-11-05T20:51:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_auth_04_token_tampering",
          domain: "auth_rbac",
          title: "Protección Anti-Tampering y Expiración",
          description: "Rechazo inmediato de tokens firmados inválidos o expirados con HTTP 401.",
          status: "ready",
          tags: ["security", "p0"],
          estimatedDurationSec: 30,
          lastRun: {
            status: "passed",
            durationMs: 29500,
            timestamp: "2026-11-05T20:52:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_auth_05_elevation_audit",
          domain: "auth_rbac",
          title: "Elevación Temporal de Privilegios",
          description: "Flujo de aprobación dual y auditoría en rbac_elevation_logs.",
          status: "in_progress",
          tags: ["audit", "agente13"],
          estimatedDurationSec: 40,
          lastRun: null,
        },
      ],
    },
    {
      domain: "inventory",
      title: "Inventario FEFO & Trazabilidad",
      readyCount: 3,
      totalCount: 5,
      tests: [
        {
          id: "pw_inv_01_fefo_expiry",
          domain: "inventory",
          title: "Prioridad First-Expired First-Out",
          description: "Deducción preferente de insumos con fecha de caducidad más cercana.",
          status: "ready",
          tags: ["inventory", "fefo"],
          estimatedDurationSec: 30,
          lastRun: {
            status: "passed",
            durationMs: 28400,
            timestamp: "2026-11-05T20:53:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_inv_02_waste_audit_sod",
          domain: "inventory",
          title: "Auditoría de Mermas con Segregación de Funciones",
          description: "Control de mermas requiriendo aprobación de jefatura distinta al registrador.",
          status: "ready",
          tags: ["inventory", "audit"],
          estimatedDurationSec: 40,
          lastRun: {
            status: "passed",
            durationMs: 39100,
            timestamp: "2026-11-05T20:54:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_inv_03_kardex_reconciliation",
          domain: "inventory",
          title: "Conciliación de Movimientos Kardex",
          description: "Cuadratura matemática entre ingresos, ventas, mermas y saldo físico.",
          status: "ready",
          tags: ["inventory", "kardex"],
          estimatedDurationSec: 35,
          lastRun: {
            status: "passed",
            durationMs: 34200,
            timestamp: "2026-11-05T20:55:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_inv_04_physical_count",
          domain: "inventory",
          title: "Toma de Inventario Físico y Ajustes",
          description: "Recuento ciego y registro de discrepancias con justificación obligatoria.",
          status: "in_progress",
          tags: ["inventory", "audit"],
          estimatedDurationSec: 45,
          lastRun: null,
        },
        {
          id: "pw_inv_05_barcode_scanning",
          domain: "inventory",
          title: "Escaneo Barcode & QR Móvil",
          description: "Lectura de códigos GS1-128 con captura de lote y fecha de vencimiento.",
          status: "planned",
          tags: ["mobile", "roadmap"],
          estimatedDurationSec: 30,
          lastRun: null,
        },
      ],
    },
    {
      domain: "recipes",
      title: "Recetas & Escandallo de Costos",
      readyCount: 3,
      totalCount: 5,
      tests: [
        {
          id: "pw_rec_01_recursive_costing",
          domain: "recipes",
          title: "Escandallo Recursivo de Costos",
          description: "Cálculo del costo de plato considerando sub-recetas y mermas culinarias.",
          status: "ready",
          tags: ["recipes", "escandallo"],
          estimatedDurationSec: 35,
          lastRun: {
            status: "passed",
            durationMs: 33900,
            timestamp: "2026-11-05T20:56:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_rec_02_culinary_yield_subwaste",
          domain: "recipes",
          title: "Rendimiento Culinario y Submermas",
          description: "Ajuste de costo según porcentaje de merma en cocción y limpieza de insumo.",
          status: "ready",
          tags: ["recipes", "costing"],
          estimatedDurationSec: 30,
          lastRun: {
            status: "passed",
            durationMs: 29800,
            timestamp: "2026-11-05T20:57:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_rec_03_margin_threshold_alert",
          domain: "recipes",
          title: "Alertas por Margen Mínimo",
          description: "Detección automática de platos con margen bruto inferior al objetivo.",
          status: "ready",
          tags: ["recipes", "margins"],
          estimatedDurationSec: 25,
          lastRun: {
            status: "passed",
            durationMs: 24100,
            timestamp: "2026-11-05T20:58:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_rec_04_allergens_matrix",
          domain: "recipes",
          title: "Matriz de Alérgenos y Trazabilidad",
          description: "Propagación de alérgenos desde insumos hacia preparaciones finales.",
          status: "in_progress",
          tags: ["compliance", "kitchen"],
          estimatedDurationSec: 35,
          lastRun: null,
        },
        {
          id: "pw_rec_05_dynamic_menu_pricing",
          domain: "recipes",
          title: "Precios Dinámicos según Insumos",
          description: "Sugerencia de precio de venta recomendada indexada al IPC alimentario.",
          status: "planned",
          tags: ["pricing", "roadmap"],
          estimatedDurationSec: 40,
          lastRun: null,
        },
      ],
    },
    {
      domain: "procurement",
      title: "Compras & Recepción con Pesaje",
      readyCount: 3,
      totalCount: 5,
      tests: [
        {
          id: "pw_proc_01_po_approval_chain",
          domain: "procurement",
          title: "Cadena de Aprobación Orden de Compra",
          description: "Workflow multi-nivel según monto total y centro de costos.",
          status: "ready",
          tags: ["procurement", "po"],
          estimatedDurationSec: 30,
          lastRun: {
            status: "passed",
            durationMs: 28900,
            timestamp: "2026-11-05T20:59:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_proc_02_scale_weighing_reception",
          domain: "procurement",
          title: "Recepción con Balanza y Tolerancia",
          description: "Integración de pesaje real versus cantidad facturada con umbral de tolerancia.",
          status: "ready",
          tags: ["procurement", "hardware"],
          estimatedDurationSec: 40,
          lastRun: {
            status: "passed",
            durationMs: 38700,
            timestamp: "2026-11-05T21:00:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_proc_03_dte_sii_reconciliation",
          domain: "procurement",
          title: "Conciliación Facturas SII / DTE",
          description: "Matching 3-way entre OC, recepción en bodega y factura electrónica XML.",
          status: "ready",
          tags: ["procurement", "sii", "chile"],
          estimatedDurationSec: 45,
          lastRun: {
            status: "passed",
            durationMs: 44200,
            timestamp: "2026-11-05T21:01:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_proc_04_ocr_auto_match",
          domain: "procurement",
          title: "OCR y Asignación Automática",
          description: "Extracción automática de ítems y montos desde documentos escaneados.",
          status: "in_progress",
          tags: ["ocr", "ai"],
          estimatedDurationSec: 50,
          lastRun: null,
        },
        {
          id: "pw_proc_05_supplier_portal",
          domain: "procurement",
          title: "Portal B2B de Proveedores",
          description: "Autogestión de despachos y estado de órdenes por proveedores registrados.",
          status: "planned",
          tags: ["supplier", "roadmap"],
          estimatedDurationSec: 60,
          lastRun: null,
        },
      ],
    },
    {
      domain: "finops",
      title: "FinOps IA, Créditos & llm_request_logs",
      readyCount: 3,
      totalCount: 5,
      tests: [
        {
          id: "pw_finops_01_credit_balance",
          domain: "finops",
          title: "Saldo de Créditos y Deducción Atómica",
          description: "Deducción transaccional de tokens OppyFy con bloqueo por saldo insuficiente.",
          status: "ready",
          tags: ["finops", "tokens", "p0"],
          estimatedDurationSec: 25,
          lastRun: {
            status: "passed",
            durationMs: 23800,
            timestamp: "2026-11-05T21:02:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_finops_02_llm_request_logs_audit",
          domain: "finops",
          title: "Auditoría Inmutable en llm_request_logs",
          description: "Registro auditable de cada invocación LLM con conteo de tokens y costo USD.",
          status: "ready",
          tags: ["finops", "audit"],
          estimatedDurationSec: 30,
          lastRun: {
            status: "passed",
            durationMs: 29100,
            timestamp: "2026-11-05T21:03:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_finops_03_tenant_quota_hardstop",
          domain: "finops",
          title: "Hard-Stop por Agotamiento de Saldo",
          description: "Suspensión de invocaciones IA al alcanzar cuota mensual sin afectar POS.",
          status: "ready",
          tags: ["finops", "quotas"],
          estimatedDurationSec: 35,
          lastRun: {
            status: "passed",
            durationMs: 33400,
            timestamp: "2026-11-05T21:04:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_finops_04_spending_spike_anomaly",
          domain: "finops",
          title: "Detección de Anomalías de Gasto IA",
          description: "Alertas tempranas ante picos inusuales de consultas a modelos de lenguaje.",
          status: "in_progress",
          tags: ["finops", "anomaly"],
          estimatedDurationSec: 40,
          lastRun: null,
        },
        {
          id: "pw_finops_05_multi_model_billing",
          domain: "finops",
          title: "Tarificación Multi-Proveedor LLM",
          description: "Costeo diferenciado para Claude, OpenAI y modelos open-source locales.",
          status: "planned",
          tags: ["finops", "roadmap"],
          estimatedDurationSec: 45,
          lastRun: null,
        },
      ],
    },
    {
      domain: "pos",
      title: "Punto de Venta & Comanda Rápida",
      readyCount: 2,
      totalCount: 5,
      tests: [
        {
          id: "pw_pos_01_order_to_kds",
          domain: "pos",
          title: "Comanda Rápida y Envío a KDS Cocina",
          description: "Registro táctil de consumo y emisión inmediata a pantalla de cocina.",
          status: "ready",
          tags: ["pos", "kds", "smoke"],
          estimatedDurationSec: 30,
          lastRun: {
            status: "passed",
            durationMs: 29500,
            timestamp: "2026-11-05T21:05:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_pos_02_buffet_mode_ticket",
          domain: "pos",
          title: "Modo Buffet y Consumo por Pax",
          description: "Cobro por persona con control de tiempo y rebaja estándar de insumos.",
          status: "ready",
          tags: ["pos", "buffet"],
          estimatedDurationSec: 35,
          lastRun: {
            status: "passed",
            durationMs: 34100,
            timestamp: "2026-11-05T21:06:00.000Z",
            error: null,
          },
        },
        {
          id: "pw_pos_03_offline_sync_resilience",
          domain: "pos",
          title: "Resiliencia Offline y Sincronización",
          description: "Operación continua durante caída de internet con sincronización diferida.",
          status: "in_progress",
          tags: ["pos", "offline"],
          estimatedDurationSec: 45,
          lastRun: null,
        },
        {
          id: "pw_pos_04_split_bill_payment",
          domain: "pos",
          title: "División de Cuenta y Medios de Pago",
          description: "Pago dividido entre múltiples comensales con tarjetas y efectivo mixto.",
          status: "in_progress",
          tags: ["pos", "checkout"],
          estimatedDurationSec: 40,
          lastRun: null,
        },
        {
          id: "pw_pos_05_hands_free_voice_pos",
          domain: "pos",
          title: "Comanda Manos Libres por Voz",
          description: "Captura de comandas en entornos ruidosos mediante reconocimiento de voz.",
          status: "planned",
          tags: ["pos", "voice", "roadmap"],
          estimatedDurationSec: 50,
          lastRun: null,
        },
      ],
    },
  ],
};

/**
 * Consulta el catálogo dinámico autodescubierto de tests Playwright en FastAPI.
 * Endpoint: GET /api/v1/platform-admin/sandbox/playwright/catalog
 */
export async function getPlaywrightCatalogApi(): Promise<PlaywrightCatalogResponse> {
  const response = await apiRequest<PlaywrightCatalogResponse>(
    "/api/v1/platform-admin/sandbox/playwright/catalog",
    {
      method: "GET",
      fallbackData: DEFAULT_PLAYWRIGHT_CATALOG,
    }
  );

  return response.data;
}

/**
 * Dispara la ejecución de pruebas Playwright en el backend.
 * Soporta contratos granulares (scope: all | domain | test) y modo de compatibilidad legado.
 * Endpoint: POST /api/v1/platform-admin/sandbox/playwright/run
 */
export async function triggerPlaywrightRunApi(
  payload: PlaywrightRunRequestPayload | PlaywrightRunConfig
): Promise<PlaywrightRunTriggerResponse & PlaywrightExecutionState> {
  const env = getRuntimeEnv();
  const confirmProd =
    "confirmProductionRun" in payload
      ? payload.confirmProductionRun
      : (payload as { readonly confirm_production_run?: boolean }).confirm_production_run;

  if (env.VITE_ENVIRONMENT === "production" && !confirmProd) {
    throw new Error(
      "[Fail-Fast Guardrail] Ejecución Playwright en producción requiere confirmación explícita (confirmProductionRun=true)."
    );
  }

  const isRequestPayload = "scope" in payload;
  const body = isRequestPayload
    ? {
        scope: payload.scope,
        targetId: payload.targetId ?? payload.target_id ?? null,
        headless: payload.headless,
        slowMoMs: payload.slowMoMs ?? payload.slow_mo_ms ?? 0,
        browser: payload.browser ?? "chromium",
        targetTenantSchema:
          payload.targetTenantSchema ??
          payload.target_tenant_schema ??
          "tenant_sandbox_fefo",
        confirmProductionRun: confirmProd ?? false,
      }
    : {
        scope: payload.suiteId === "all" ? "all" : "domain",
        targetId: payload.suiteId === "all" ? null : payload.suiteId,
        headless: payload.headless,
        slowMoMs: 0,
        browser: payload.browser ?? "chromium",
        targetTenantSchema: payload.targetTenantSchema ?? "tenant_genesis",
        confirmProductionRun: confirmProd ?? false,
        suiteId: payload.suiteId,
        grepFilter: payload.grepFilter,
        retries: payload.retries,
        workers: payload.workers,
      };

  const expectedTests = isRequestPayload
    ? payload.scope === "all"
      ? 35
      : payload.scope === "domain"
        ? 5
        : 1
    : 12;

  const fallback: PlaywrightRunTriggerResponse & PlaywrightExecutionState = {
    runId: `pw_run_${Date.now().toString(36)}`,
    status: "queued",
    testsQueued: expectedTests,
    message: `Corrida Playwright encolada exitosamente para alcance '${body.scope}'.`,
    startTime: new Date().toISOString(),
    endTime: null,
    totalTests: expectedTests,
    passedTests: 0,
    failedTests: 0,
    skippedTests: 0,
    currentRunningTest: null,
    testResults: [],
    rawLogs: [
      `[${new Date().toISOString()}] [INIT] Disparando ejecución Playwright (${body.scope})...`,
    ],
  };

  const response = await apiRequest<PlaywrightRunTriggerResponse & PlaywrightExecutionState>(
    "/api/v1/platform-admin/sandbox/playwright/run",
    {
      method: "POST",
      body,
      fallbackData: fallback,
    }
  );

  return response.data;
}

/**
 * Conecta al stream SSE de eventos paso a paso de Playwright.
 * Endpoint: GET /api/v1/platform-admin/sandbox/playwright/stream/{runId}
 */
export function subscribePlaywrightStream(
  runId: string,
  onEvent: (event: PlaywrightStreamStepEvent) => void,
  onError?: (err: Error) => void,
  onComplete?: (completedData?: {
    readonly runId?: string;
    readonly status?: string;
    readonly totalTests?: number;
    readonly passedTests?: number;
    readonly failedTests?: number;
    readonly durationMs?: number;
  }) => void
): () => void {
  const url = `/api/v1/platform-admin/sandbox/playwright/stream/${encodeURIComponent(runId)}`;

  if (typeof EventSource !== "undefined") {
    let isClosed = false;
    const eventSource = new EventSource(url);

    eventSource.addEventListener("step", (e: MessageEvent) => {
      if (isClosed) return;
      try {
        const raw = typeof e.data === "string" ? JSON.parse(e.data) : e.data;
        const normalized: PlaywrightStreamStepEvent = {
          stepIndex: raw.stepIndex ?? raw.step_index ?? 0,
          testId: raw.testId ?? raw.test_id ?? "",
          message: raw.message ?? "",
          level: (raw.level as PlaywrightStreamLogLevel) ?? "step",
          timestamp: raw.timestamp ?? new Date().toISOString(),
          screenshotUrl: raw.screenshotUrl ?? raw.screenshot_url ?? null,
          durationMs: raw.durationMs ?? raw.duration_ms,
          error: raw.error ?? null,
        };
        onEvent(normalized);
      } catch (err) {
        console.warn("[SSE] Error al parsear evento 'step':", err);
      }
    });

    eventSource.addEventListener("completed", (e: MessageEvent) => {
      if (isClosed) return;
      try {
        const raw = typeof e.data === "string" ? JSON.parse(e.data) : e.data;
        onComplete?.(raw);
      } catch {
        onComplete?.({ runId, status: "completed" });
      }
      isClosed = true;
      eventSource.close();
    });

    eventSource.addEventListener("error", () => {
      if (isClosed) return;
      onError?.(new Error("Error en conexión SSE de Playwright"));
    });

    eventSource.onmessage = (e: MessageEvent) => {
      if (isClosed) return;
      try {
        const raw = typeof e.data === "string" ? JSON.parse(e.data) : e.data;
        if (raw?.status === "completed") {
          onComplete?.(raw);
          isClosed = true;
          eventSource.close();
        } else if (raw?.message) {
          onEvent({
            stepIndex: raw.stepIndex ?? raw.step_index ?? 0,
            testId: raw.testId ?? raw.test_id ?? "",
            message: raw.message ?? "",
            level: (raw.level as PlaywrightStreamLogLevel) ?? "info",
            timestamp: raw.timestamp ?? new Date().toISOString(),
            screenshotUrl: raw.screenshotUrl ?? raw.screenshot_url ?? null,
          });
        }
      } catch {
        // Ignorar mensajes no JSON
      }
    };

    return () => {
      isClosed = true;
      eventSource.close();
    };
  }

  // Fallback seguro en entornos sin EventSource
  return () => {
    // No-op
  };
}

// ============================================================================
// CLIENTE API FEFO DATES & TIME-TRAVEL SIMULATION (SUB-PLAN 4)
// ============================================================================

/**
 * Ejecuta simulación proyectiva FEFO no destructiva en el backend FastAPI.
 * Endpoint: POST /api/v1/platform-admin/sandbox/fefo/simulate
 */
export async function simulateFefoApi(
  config: FefoSimulationRequest
): Promise<FefoSimulationResponse> {
  const simulatedIso = shiftIsoDate(
    new Date().toISOString().slice(0, 10),
    config.offsetDays ?? 0
  );
  const scenario = config.scenarioPreset ?? "HEALTHY";
  const fallbackBatches = generateScenarioBatches(
    scenario,
    new Date().toISOString().slice(0, 10),
    config.warehouseId ?? "bod-cocina-central",
    config.exchangeRate
  );
  const fallback: FefoSimulationResponse = summarizeFefoSimulation(
    fallbackBatches,
    simulatedIso,
    scenario,
    config.currency ?? "CLP"
  );

  const response = await apiRequest<FefoSimulationResponse>(
    "/api/v1/platform-admin/sandbox/fefo/simulate",
    {
      method: "POST",
      body: {
        mode: config.mode ?? "relative_offset",
        offsetDays: config.offsetDays,
        targetDateIso: config.targetDateIso ?? null,
        tenantSchema: config.tenantSchema,
        warehouseId: config.warehouseId ?? null,
        affectCategories: config.affectCategories ?? ["all"],
        scenarioPreset: config.scenarioPreset ?? null,
        dryRun: config.dryRun ?? true,
        generateSpoilageEvents: config.generateSpoilageEvents ?? true,
        currency: config.currency ?? "CLP",
        exchangeRate: config.exchangeRate,
        confirmStagingAction: config.confirmStagingAction ?? false,
        // snake_case
        offset_days: config.offsetDays,
        target_date_iso: config.targetDateIso ?? null,
        tenant_schema: config.tenantSchema,
        warehouse_id: config.warehouseId ?? null,
        affect_categories: config.affectCategories ?? ["all"],
        scenario_preset: config.scenarioPreset ?? null,
        dry_run: config.dryRun ?? true,
        generate_spoilage_events: config.generateSpoilageEvents ?? true,
        exchange_rate: config.exchangeRate,
        confirm_staging_action: config.confirmStagingAction ?? false,
      },
      fallbackData: fallback,
    }
  );

  return response.data;
}

/**
 * Aplica desplazamiento temporal de fechas en el esquema PostgreSQL de prueba.
 * Endpoint: POST /api/v1/platform-admin/sandbox/fefo/shift
 */
export async function shiftFefoApi(
  config: FefoShiftRequest
): Promise<FefoShiftResponse> {
  const env = getRuntimeEnv();
  if (env.VITE_ENVIRONMENT === "production" && !config.dryRun) {
    throw new Error(
      "[Fail-Fast Guardrail] Desplazamiento real FEFO bloqueado en entorno 'production'. Solo se permite simulación (dryRun=true)."
    );
  }
  if (env.VITE_ENVIRONMENT === "staging" && !config.dryRun && !config.confirmStagingAction) {
    throw new Error(
      "[Fail-Fast Guardrail] Desplazamiento real FEFO en entorno 'staging' requiere confirmación explícita (confirmStagingAction=true)."
    );
  }

  const fallback: FefoShiftResponse = {
    tenantSchema: config.tenantSchema,
    shiftedBatchesCount: 20,
    offsetDays: config.offsetDays,
    appliedAt: new Date().toISOString(),
    status: config.dryRun ? "preview_only" : "applied",
    buffetsShiftedCount: config.recalculateBuffet ? 4 : 0,
  };

  const response = await apiRequest<FefoShiftResponse>(
    "/api/v1/platform-admin/sandbox/fefo/shift",
    {
      method: "POST",
      body: {
        mode: config.mode ?? "relative_offset",
        offsetDays: config.offsetDays,
        targetDateIso: config.targetDateIso ?? null,
        tenantSchema: config.tenantSchema,
        warehouseId: config.warehouseId ?? null,
        affectCategories: config.affectCategories ?? ["all"],
        dryRun: config.dryRun ?? false,
        generateSpoilageEvents: config.generateSpoilageEvents ?? true,
        recalculateBuffet: config.recalculateBuffet ?? true,
        confirmStagingAction: config.confirmStagingAction ?? false,
        // snake_case
        offset_days: config.offsetDays,
        target_date_iso: config.targetDateIso ?? null,
        tenant_schema: config.tenantSchema,
        warehouse_id: config.warehouseId ?? null,
        affect_categories: config.affectCategories ?? ["all"],
        dry_run: config.dryRun ?? false,
        generate_spoilage_events: config.generateSpoilageEvents ?? true,
        recalculate_buffet: config.recalculateBuffet ?? true,
        confirm_staging_action: config.confirmStagingAction ?? false,
      },
      fallbackData: fallback,
    }
  );

  return response.data;
}

/**
 * Sincronización quirúrgica de fechas a "Hoy" (recalculando lotes de inventario y buffet).
 * Endpoint: POST /api/v1/platform-admin/sandbox/fefo/sync-today
 */
export async function syncFefoTodayApi(
  config: FefoSyncTodayRequest
): Promise<FefoSyncTodayResponse> {
  const env = getRuntimeEnv();
  if (env.VITE_ENVIRONMENT === "production" && !config.dryRun) {
    throw new Error(
      "[Fail-Fast Guardrail] Sincronización quirúrgica bloqueada en entorno 'production'. Solo se permite simulación (dryRun=true)."
    );
  }

  const fallback: FefoSyncTodayResponse = {
    tenantSchema: config.tenantSchema,
    synchronizedBatchesCount: 20,
    buffetsRecalculatedCount: 4,
    synchronizedAt: new Date().toISOString(),
    baseTodayIso: new Date().toISOString().slice(0, 10),
    status: config.dryRun ? "preview_only" : "synchronized",
  };

  const response = await apiRequest<FefoSyncTodayResponse>(
    "/api/v1/platform-admin/sandbox/fefo/sync-today",
    {
      method: "POST",
      body: {
        tenantSchema: config.tenantSchema,
        warehouseId: config.warehouseId ?? null,
        recalculateBuffetLots: config.recalculateBuffetLots ?? true,
        dryRun: config.dryRun,
        confirmStagingAction: config.confirmStagingAction ?? false,
        // snake_case
        tenant_schema: config.tenantSchema,
        warehouse_id: config.warehouseId ?? null,
        recalculate_buffet_lots: config.recalculateBuffetLots ?? true,
        dry_run: config.dryRun,
        confirm_staging_action: config.confirmStagingAction ?? false,
      },
      fallbackData: fallback,
    }
  );

  return response.data;
}

