"""
oppytec-backend/src/modules/tenancy/presentation/schemas_sandbox.py
Esquemas Pydantic v2 (extra="forbid", populate_by_name=True) para la Consola "Lab & QA Sandbox":
- Estado global del sandbox (/api/v1/platform-admin/sandbox/status)
- Generador de Mock Data e Historial (/api/v1/platform-admin/sandbox/mock-data/*)
- Playwright E2E Runner (/api/v1/platform-admin/sandbox/playwright/*)
- Simulador FEFO Time-Warp (/api/v1/platform-admin/sandbox/fefo/*)
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# 1. ESTADO GENERAL DEL SANDBOX
# ============================================================================


class SandboxStatusResponse(BaseModel):
    """Estado operacional y herramientas disponibles en la consola Lab & QA Sandbox."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    status: Literal["ready", "active", "idle", "maintenance"] = Field(
        default="ready", description="Estado del entorno sandbox"
    )
    environment: str = Field(..., description="Ambiente de ejecución activo")
    available_tools: list[str] = Field(
        ...,
        alias="availableTools",
        description="Módulos y herramientas habilitadas en el sandbox",
    )
    active_runs: int = Field(
        default=0,
        alias="activeRuns",
        description="Cantidad de corridas o simulaciones activas",
    )
    timestamp: datetime = Field(..., description="Marca temporal del reporte")
    isolated_tenant_schemas: list[str] = Field(
        default_factory=list,
        alias="isolatedTenantSchemas",
        description="Esquemas de inquilino aislados disponibles para pruebas",
    )
    is_mutation_allowed: bool = Field(
        default=True,
        alias="isMutationAllowed",
        description="Indica si el entorno actual permite inyecciones o mutaciones destructivas",
    )
    environment_policy: str = Field(
        default="isolated_sandbox",
        alias="environmentPolicy",
        description="Política de aislamiento y blindaje del entorno canónico",
    )


# ============================================================================
# 2. GENERADOR E HISTORIAL DE MOCK DATA
# ============================================================================

MockDataEntityCategory = Literal[
    "holdings",
    "tenants",
    "users",
    "catalog",
    "inventory_fefo",
    "recipes",
    "invoices",
    "events",
    "finops_credits",
    "all",
]

MockDataVolume = Literal["small", "medium", "large", "stress"]
MockDataStatus = Literal["idle", "generating", "success", "failed"]


def _default_categories() -> list[MockDataEntityCategory]:
    return ["all"]


class MockDataGenerationRequest(BaseModel):
    """Configuración para disparar la generación o simulación (dryRun) de mock data."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tenant_schema: str = Field(..., alias="tenantSchema", min_length=3, max_length=64)
    categories: list[MockDataEntityCategory] = Field(
        default_factory=_default_categories,
        description="Categorías de entidades a generar",
    )
    volume: MockDataVolume = Field(
        default="small", description="Volumen de datos a sintetizar"
    )
    seed_random: int | None = Field(
        default=None, alias="seedRandom", description="Semilla pseudoaleatoria"
    )
    preserve_existing: bool = Field(
        default=True,
        alias="preserveExisting",
        description="Preserva registros existentes en el esquema",
    )
    dry_run: bool = Field(
        default=True,
        alias="dryRun",
        description="Simulación no destructiva sin escribir en base de datos",
    )
    inject_fefo_anomalies: bool = Field(
        default=False,
        alias="injectFefoAnomalies",
        description="Inyecta lotes caducados y anomalías de merma para pruebas de QA",
    )
    confirm_staging_action: bool = Field(
        default=False,
        alias="confirmStagingAction",
        description="Confirmación explícita requerida para mutaciones en entorno staging",
    )


class MockDataGenerationResponse(BaseModel):
    """Resultado del progreso o ejecución preliminar de mock data."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    step: str = Field(description="Etapa actual del proceso de generación")
    percent: int = Field(ge=0, le=100, description="Porcentaje completado")
    records_created: dict[str, int] = Field(
        default_factory=dict,
        alias="recordsCreated",
        description="Mapeo de entidad a conteo de registros sintetizados",
    )
    status: MockDataStatus = Field(description="Estado de la ejecución")
    error_message: str | None = Field(
        default=None, alias="errorMessage", description="Mensaje de error si falló"
    )
    execution_duration_ms: int = Field(
        default=0,
        alias="executionDurationMs",
        description="Duración de la ejecución en milisegundos",
    )
    dry_run: bool = Field(
        default=True, alias="dryRun", description="Indica si fue simulación no destructiva"
    )


class MockDataHistoryItem(BaseModel):
    """Registro histórico de una generación de mock data."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(description="Identificador único del registro histórico")
    created_at: datetime = Field(alias="createdAt", description="Fecha de creación")
    executed_by: str = Field(
        alias="executedBy", description="Identificador del operador/usuario"
    )
    tenant_schema: str = Field(
        alias="tenantSchema", description="Esquema destino de la inyección"
    )
    records_summary: dict[str, int] = Field(
        alias="recordsSummary", description="Resumen de registros generados por categoría"
    )
    duration_ms: int = Field(
        alias="durationMs", description="Duración total en milisegundos"
    )
    status: Literal["success", "failed"] = Field(description="Estado final")
    dry_run: bool = Field(
        default=True, alias="dryRun", description="Indica si fue dryRun"
    )


# ============================================================================
# 3. PLAYWRIGHT E2E TEST RUNNER & DINAMIC CATALOG
# ============================================================================

PlaywrightDomain = Literal[
    "tenancy",
    "auth_rbac",
    "inventory",
    "recipes",
    "procurement",
    "finops",
    "pos",
]

PlaywrightItemStatus = Literal["ready", "in_progress", "planned"]
PlaywrightTestRunStatus = Literal["passed", "failed", "idle"]
PlaywrightRunScope = Literal["all", "domain", "test"]

PlaywrightTestSuiteId = Literal[
    "smoke",
    "auth_rbac",
    "tenant_isolation_idor",
    "pos_consumo",
    "inventory_fefo",
    "recipes_escandallo",
    "holding_hub",
    "finops_tokens",
    "all",
]

PlaywrightBrowserType = Literal["chromium", "firefox", "webkit"]
PlaywrightTestStatus = Literal["passed", "failed", "timedOut", "skipped"]
PlaywrightExecutionStatus = Literal["idle", "queued", "running", "completed", "failed"]
PlaywrightStreamLogLevel = Literal[
    "info",
    "warn",
    "error",
    "debug",
    "step",
    "assert",
]


class PlaywrightTestRunResultSchema(BaseModel):
    """Resultado histórico o reciente de una ejecución unitaria de test."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    status: PlaywrightTestRunStatus = Field(default="idle", description="Estado de la corrida")
    duration_ms: int = Field(default=0, alias="durationMs", description="Duración en milisegundos")
    timestamp: str = Field(description="ISO timestamp de la última ejecución")
    error: str | None = Field(default=None, description="Mensaje de error en caso de fallo")


class PlaywrightTestItemSchema(BaseModel):
    """Metadatos declarativos de un caso de prueba Playwright registrado."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(description="Identificador único del test")
    domain: PlaywrightDomain = Field(description="Dominio canónico de negocio")
    title: str = Field(description="Título descriptivo")
    description: str = Field(description="Explicación detallada del flujo y asertos")
    status: PlaywrightItemStatus = Field(default="planned", description="Madurez del caso de prueba")
    tags: list[str] = Field(default_factory=list, description="Etiquetas de búsqueda y taxonomía")
    estimated_duration_sec: int = Field(
        default=15, alias="estimatedDurationSec", description="Duración estimada en segundos"
    )
    last_run: PlaywrightTestRunResultSchema | None = Field(
        default=None, alias="lastRun", description="Resultado de la última ejecución"
    )


class PlaywrightCatalogSummarySchema(BaseModel):
    """Resumen consolidado y métricas de cobertura del catálogo."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    total: int = Field(ge=0, description="Total de pruebas registradas")
    ready: int = Field(ge=0, description="Pruebas operacionales listas")
    in_progress: int = Field(
        default=0, alias="inProgress", ge=0, description="Pruebas en desarrollo activo"
    )
    planned: int = Field(default=0, ge=0, description="Pruebas planificadas en roadmap")
    coverage_percentage: float = Field(
        default=0.0,
        alias="coveragePercentage",
        ge=0.0,
        le=100.0,
        description="Porcentaje global de automatización (ready / total * 100)",
    )


class PlaywrightDomainGroupSchema(BaseModel):
    """Grupo de casos de prueba asociados a un dominio de negocio específico."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    domain: PlaywrightDomain = Field(description="Identificador del dominio")
    title: str = Field(description="Título legible del dominio")
    ready_count: int = Field(
        default=0, alias="readyCount", ge=0, description="Conteo de pruebas listas en el dominio"
    )
    total_count: int = Field(
        default=0, alias="totalCount", ge=0, description="Conteo total de pruebas en el dominio"
    )
    tests: list[PlaywrightTestItemSchema] = Field(
        default_factory=list, description="Casos de prueba que componen el dominio"
    )


class PlaywrightCatalogResponseSchema(BaseModel):
    """Respuesta completa del catálogo dinámico de tests Playwright."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    summary: PlaywrightCatalogSummarySchema = Field(description="Métricas de resumen global")
    domains: list[PlaywrightDomainGroupSchema] = Field(
        default_factory=list, description="Desglose agrupado por los 7 dominios oficiales"
    )


class PlaywrightTestStep(BaseModel):
    """Paso unitario dentro de un caso de prueba Playwright."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    title: str
    duration_ms: int = Field(alias="durationMs")
    status: PlaywrightTestStatus
    error: str | None = None


class PlaywrightTestCaseResult(BaseModel):
    """Resultado individual de un caso de prueba Playwright."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    title: str
    suite: str
    status: PlaywrightTestStatus
    duration_ms: int = Field(alias="durationMs")
    steps: list[PlaywrightTestStep] = Field(default_factory=list)
    screenshot_url: str | None = Field(default=None, alias="screenshotUrl")
    trace_url: str | None = Field(default=None, alias="traceUrl")
    error_message: str | None = Field(default=None, alias="errorMessage")


class PlaywrightRunRequestSchema(BaseModel):
    """Parámetros para disparar una ejecución granular o suite Playwright."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    scope: PlaywrightRunScope = Field(
        default="all", description="Alcance de la corrida ('all', 'domain', 'test')"
    )
    target_id: str | None = Field(
        default=None,
        alias="targetId",
        description="ID del dominio o del test específico cuando scope no es 'all'",
    )
    headless: bool = Field(
        default=True, description="Ejecución en segundo plano o modo visual interactivo"
    )
    slow_mo_ms: int = Field(
        default=0,
        alias="slowMoMs",
        ge=0,
        description="Retardo artificial entre pasos para inspección visual humana",
    )
    browser: PlaywrightBrowserType = Field(default="chromium", description="Navegador destino")
    target_tenant_schema: str = Field(
        default="tenant_qa_lab",
        alias="targetTenantSchema",
        description="Esquema multi-tenant aislado autorizado para pruebas",
    )
    confirm_production_run: bool = Field(
        default=False,
        alias="confirmProductionRun",
        description="Confirmación explícita para ejecuciones en entorno de producción",
    )
    suite_id: str | None = Field(
        default=None,
        alias="suiteId",
        description="Identificador de suite compatible retroactivo",
    )
    grep_filter: str | None = Field(
        default=None, alias="grepFilter", description="Filtro opcional de regex"
    )
    retries: int = Field(default=0, ge=0, le=5)
    workers: int = Field(default=1, ge=1, le=8)
    base_url: str | None = Field(default=None, alias="baseUrl")


class PlaywrightRunTriggerResponseSchema(BaseModel):
    """Confirmación asíncrona de encolado de ejecución Playwright (202 Accepted)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    run_id: str = Field(alias="runId", description="Identificador único de la corrida")
    status: PlaywrightExecutionStatus = Field(
        default="queued", description="Estado inicial de la ejecución"
    )
    tests_queued: int = Field(
        default=0, alias="testsQueued", description="Cantidad de pruebas encoladas"
    )
    message: str = Field(
        default="", description="Mensaje informativo para el operador"
    )
    # Retrocompatibilidad completa con PlaywrightExecutionStateResponse para pruebas previas
    suite_id: str | None = Field(default=None, alias="suiteId")
    total_tests: int | None = Field(default=None, alias="totalTests")
    passed_tests: int | None = Field(default=None, alias="passedTests")
    failed_tests: int | None = Field(default=None, alias="failedTests")
    skipped_tests: int | None = Field(default=None, alias="skippedTests")
    current_running_test: str | None = Field(default=None, alias="currentRunningTest")
    test_results: list[PlaywrightTestCaseResult] = Field(
        default_factory=list, alias="testResults"
    )
    raw_logs: list[str] = Field(default_factory=list, alias="rawLogs")


class PlaywrightStreamStepEventSchema(BaseModel):
    """Evento individual emitido por SSE durante la ejecución en vivo."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    step_index: int = Field(
        alias="stepIndex", description="Índice ordinal del paso en la corrida"
    )
    test_id: str = Field(alias="testId", description="Identificador de la prueba en curso")
    message: str = Field(description="Descripción de la acción o aserto realizado")
    level: PlaywrightStreamLogLevel = Field(
        default="step", description="Nivel semántico del evento"
    )
    timestamp: str = Field(description="Marca temporal ISO del evento")
    screenshot_url: str | None = Field(
        default=None, alias="screenshotUrl", description="URL relativa del screenshot capturado"
    )
    duration_ms: int = Field(
        default=0, alias="durationMs", description="Duración en milisegundos del paso"
    )
    error: str | None = Field(
        default=None, description="Mensaje de error en caso de fallo en el aserto"
    )


class PlaywrightExecutionStateResponse(BaseModel):
    """Estado y observabilidad en tiempo real de una ejecución Playwright."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    run_id: str = Field(alias="runId")
    suite_id: str = Field(default="all", alias="suiteId")
    status: PlaywrightExecutionStatus = Field(default="completed")
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")
    total_tests: int = Field(default=0, alias="totalTests")
    passed_tests: int = Field(default=0, alias="passedTests")
    failed_tests: int = Field(default=0, alias="failedTests")
    skipped_tests: int = Field(default=0, alias="skippedTests")
    current_running_test: str | None = Field(default=None, alias="currentRunningTest")
    test_results: list[PlaywrightTestCaseResult] = Field(
        default_factory=list, alias="testResults"
    )
    raw_logs: list[str] = Field(default_factory=list, alias="rawLogs")


# Aliases canónicos para flexibilidad y compatibilidad
PlaywrightTestItem = PlaywrightTestItemSchema
PlaywrightCatalogSummary = PlaywrightCatalogSummarySchema
PlaywrightDomainGroup = PlaywrightDomainGroupSchema
PlaywrightCatalogResponse = PlaywrightCatalogResponseSchema
PlaywrightRunRequest = PlaywrightRunRequestSchema
PlaywrightRunTriggerResponse = PlaywrightRunTriggerResponseSchema
PlaywrightStreamStepEvent = PlaywrightStreamStepEventSchema


# ============================================================================
# 4. SIMULADOR TEMPORAL FEFO (TIME-WARP)
# ============================================================================

FefoWarpMode = Literal["relative_offset", "absolute_date", "spoilage_acceleration"]
FefoBatchCanonicalStatus = Literal["OPTIMAL", "WARNING", "CRITICAL", "EXPIRED"]
FefoBatchStatus = Literal[
    "optimal",
    "warning",
    "critical",
    "expired",
    "OPTIMAL",
    "WARNING",
    "CRITICAL",
    "EXPIRED",
]
FefoDemoScenarioId = Literal["HEALTHY", "WARNING", "CRITICAL"]


class FefoSimulationRequest(BaseModel):
    """Parámetros para la simulación temporal de caducidad FEFO y Time-Travel."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    mode: FefoWarpMode = Field(default="relative_offset")
    offset_days: int = Field(
        default=0,
        alias="offsetDays",
        ge=-30,
        le=60,
        description="Desplazamiento temporal acotado en días [-30, +60]",
    )
    target_date_iso: str | None = Field(default=None, alias="targetDateIso")
    tenant_schema: str = Field(..., alias="tenantSchema")
    warehouse_id: str | None = Field(default=None, alias="warehouseId")
    affect_categories: list[str] = Field(
        default_factory=list, alias="affectCategories"
    )
    scenario_preset: FefoDemoScenarioId | None = Field(
        default=None, alias="scenarioPreset"
    )
    dry_run: bool = Field(default=True, alias="dryRun")
    generate_spoilage_events: bool = Field(
        default=False, alias="generateSpoilageEvents"
    )
    currency: str = Field(default="CLP")
    exchange_rate: float | None = Field(default=None, alias="exchangeRate")
    confirm_staging_action: bool = Field(
        default=False,
        alias="confirmStagingAction",
        description="Confirmación explícita requerida para desplazar fechas en staging",
    )


# Alias canónico retrocompatible
FefoWarpSimulationRequest = FefoSimulationRequest


class FefoBatchSimulationImpact(BaseModel):
    """Impacto individual proyectado sobre un lote de inventario FEFO."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    batch_id: str = Field(alias="batchId")
    product_sku: str = Field(alias="productSku")
    product_name: str = Field(alias="productName")
    category: str | None = Field(default="insumos")
    warehouse_id: str | None = Field(default=None, alias="warehouseId")
    is_buffet_batch: bool = Field(default=False, alias="isBuffetBatch")
    original_expiry_date: str = Field(alias="originalExpiryDate")
    simulated_expiry_date: str = Field(alias="simulatedExpiryDate")
    days_to_expiration: int = Field(alias="daysToExpiration")
    status: FefoBatchStatus
    canonical_status: FefoBatchCanonicalStatus | None = Field(
        default=None, alias="canonicalStatus"
    )
    stock_quantity: float = Field(alias="stockQuantity")
    unit_measure: str = Field(alias="unitMeasure")
    unit_cost: float = Field(alias="unitCost")
    estimated_loss_amount: float = Field(alias="estimatedLossAmount")
    estimated_loss_fx_amount: float | None = Field(
        default=None, alias="estimatedLossFxAmount"
    )
    loss_rate_applied: float | None = Field(
        default=None, alias="lossRateApplied"
    )


# Alias canónico interoperable
FefoBatchItemSchema = FefoBatchSimulationImpact


class FefoSimulationResponse(BaseModel):
    """Resultado del cálculo proyectivo no destructivo FEFO."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    simulation_id: str = Field(alias="simulationId")
    executed_at: str = Field(alias="executedAt")
    simulated_system_date: str = Field(alias="simulatedSystemDate")
    total_batches_evaluated: int = Field(alias="totalBatchesEvaluated")
    optimal_batches_count: int = Field(default=0, alias="optimalBatchesCount")
    warning_batches_count: int = Field(default=0, alias="warningBatchesCount")
    critical_batches_count: int = Field(alias="criticalBatchesCount")
    expired_batches_count: int = Field(alias="expiredBatchesCount")
    total_spoilage_risk_amount: float = Field(alias="totalSpoilageRiskAmount")
    total_spoilage_risk_fx_amount: float | None = Field(
        default=None, alias="totalSpoilageRiskFxAmount"
    )
    currency: str = Field(default="CLP")
    target_fx_currency: str | None = Field(default="USD", alias="targetFxCurrency")
    alerts_created: int = Field(default=0, alias="alertsCreated")
    scenario_applied: FefoDemoScenarioId | None = Field(
        default=None, alias="scenarioApplied"
    )
    batches: list[FefoBatchSimulationImpact] = Field(default_factory=list)


class FefoShiftRequest(BaseModel):
    """Parámetros para la aplicación de corrimiento temporal de lotes FEFO."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    mode: FefoWarpMode = Field(default="relative_offset")
    offset_days: int = Field(
        default=0,
        alias="offsetDays",
        ge=-30,
        le=60,
        description="Desplazamiento temporal acotado en días [-30, +60]",
    )
    target_date_iso: str | None = Field(default=None, alias="targetDateIso")
    tenant_schema: str = Field(..., alias="tenantSchema")
    warehouse_id: str | None = Field(default=None, alias="warehouseId")
    affect_categories: list[str] = Field(
        default_factory=list, alias="affectCategories"
    )
    dry_run: bool = Field(default=True, alias="dryRun")
    generate_spoilage_events: bool = Field(
        default=False, alias="generateSpoilageEvents"
    )
    recalculate_buffet: bool = Field(default=False, alias="recalculateBuffet")
    confirm_staging_action: bool = Field(
        default=False,
        alias="confirmStagingAction",
        description="Confirmación explícita requerida para desplazar fechas en staging",
    )


class FefoShiftResponse(BaseModel):
    """Resultado de la aplicación destructiva del corrimiento de fechas en BD."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tenant_schema: str = Field(alias="tenantSchema")
    shifted_batches_count: int = Field(alias="shiftedBatchesCount")
    offset_days: int = Field(alias="offsetDays")
    applied_at: datetime = Field(alias="appliedAt")
    status: Literal["applied", "preview_only"]
    buffets_shifted_count: int | None = Field(
        default=None, alias="buffetsShiftedCount"
    )


class FefoSyncTodayRequest(BaseModel):
    """Parámetros para la sincronización quirúrgica de lotes a fecha actual ('Hoy')."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tenant_schema: str = Field(..., alias="tenantSchema")
    warehouse_id: str | None = Field(default=None, alias="warehouseId")
    recalculate_buffet_lots: bool = Field(
        default=True, alias="recalculateBuffetLots"
    )
    dry_run: bool = Field(default=True, alias="dryRun")
    confirm_staging_action: bool = Field(
        default=False,
        alias="confirmStagingAction",
        description="Confirmación explícita requerida para sincronizar fechas en staging",
    )


class FefoSyncTodayResponse(BaseModel):
    """Resultado de la sincronización quirúrgica de lotes a fecha actual ('Hoy')."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tenant_schema: str = Field(alias="tenantSchema")
    synchronized_batches_count: int = Field(alias="synchronizedBatchesCount")
    buffets_recalculated_count: int = Field(
        default=0, alias="buffetsRecalculatedCount"
    )
    synchronized_at: str = Field(alias="synchronizedAt")
    base_today_iso: str = Field(alias="baseTodayIso")
    status: Literal["synchronized", "preview_only"]


# ============================================================================
# 5. PRESETS GASTRONÓMICOS & FACTORY RESET
# ============================================================================

GastronomicPresetId = Literal[
    "fast-food-pollo-king",
    "carnes-angus-cava",
    "hotel-desayuno-buffet",
    "clean-slate",
]


class GastronomicPresetItem(BaseModel):
    """Metadatos canónicos de un preset gastronómico multi-tenant."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: GastronomicPresetId = Field(description="Identificador único del preset")
    code: str = Field(description="Código canónico del preset")
    title: str = Field(description="Título descriptivo del preset")
    subtitle: str = Field(description="Subtítulo y resumen de enfoque")
    description: str = Field(description="Descripción detallada del modelo gastronómico")
    category: str = Field(description="Categoría gastronómica")
    badge: str = Field(description="Etiqueta visual del preset")
    color: str = Field(description="Color hexadecimal primario")
    rgb: str = Field(description="Valores RGB para canal alfa")
    icon_name: str = Field(alias="iconName", description="Nombre del icono Lucide")
    default_tenant_schema: str = Field(
        alias="defaultTenantSchema", description="Esquema tenant por defecto"
    )
    default_holding_id: str = Field(
        alias="defaultHoldingId", description="Holding asociado por defecto"
    )
    estimated_stock_value_clp: int = Field(
        alias="estimatedStockValueClp", description="Valorización estimada del stock en CLP"
    )
    total_skus: int = Field(alias="totalSkus", description="Total de SKUs provistos")
    total_batches: int = Field(
        alias="totalBatches", description="Total de lotes FEFO provistos"
    )
    total_recipes: int = Field(
        alias="totalRecipes", description="Total de recetas y escandallos"
    )


class GastronomicPresetListResponse(BaseModel):
    """Listado consolidado de presets gastronómicos canónicos."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    presets: list[GastronomicPresetItem] = Field(
        description="Lista de presets canónicos disponibles"
    )
    total: int = Field(description="Total de presets disponibles")


class FactoryResetRequest(BaseModel):
    """Solicitud de Factory Reset para restaurar un esquema tenant a estado canónico."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tenant_schema: str = Field(
        ...,
        alias="tenantSchema",
        min_length=3,
        max_length=64,
        description="Esquema tenant autorizado a restablecer",
    )
    target_preset_id: GastronomicPresetId = Field(
        ...,
        alias="targetPresetId",
        description="Preset gastronómico a aplicar como nuevo estado base",
    )
    confirm_reset: bool = Field(
        default=True,
        alias="confirmReset",
        description="Confirmación obligatoria para ejecutar el reset destructivo",
    )
    confirm_staging_action: bool = Field(
        default=False,
        alias="confirmStagingAction",
        description="Confirmación explícita requerida para entornos staging",
    )


class FactoryResetResponse(BaseModel):
    """Resultado de la ejecución de Factory Reset."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tenant_schema: str = Field(
        alias="tenantSchema", description="Esquema tenant restablecido"
    )
    preset_restored: GastronomicPresetId = Field(
        alias="presetRestored", description="Identificador del preset restaurado"
    )
    restored_at: datetime = Field(
        alias="restoredAt", description="Marca temporal del restablecimiento"
    )
    tables_truncated: list[str] = Field(
        alias="tablesTruncated", description="Tablas transaccionales purgadas"
    )
    records_reseeded: dict[str, int] = Field(
        alias="recordsReseeded", description="Conteo de registros re-sembrados por entidad"
    )
    duration_ms: int = Field(
        alias="durationMs", description="Duración total de la operación en milisegundos"
    )


class MockDataCustomInjectRequest(BaseModel):
    """Inyección de dataset sintético personalizado por el editor."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tenant_schema: str = Field(..., alias="tenantSchema", min_length=3, max_length=64)
    preset_id: GastronomicPresetId = Field(alias="presetId")
    dataset_json: dict[str, object] = Field(..., alias="datasetJson")
    dry_run: bool = Field(default=False, alias="dryRun")
    confirm_staging_action: bool = Field(
        default=False, alias="confirmStagingAction"
    )


# Compatibilidad y equivalencias semánticas
GastronomicPresetMetaResponse = GastronomicPresetItem
MockDataResetRequest = FactoryResetRequest
MockDataResetResponse = FactoryResetResponse

