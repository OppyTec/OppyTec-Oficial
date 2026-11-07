"""
oppytec-backend/src/modules/tenancy/presentation/sandbox_router.py
Endpoints REST de la Consola "Lab & QA Sandbox" de Platform Admin:
- GET  /api/v1/platform-admin/sandbox/status
- GET  /api/v1/platform-admin/sandbox/mock-data/history
- POST /api/v1/platform-admin/sandbox/mock-data/generate
- GET  /api/v1/platform-admin/sandbox/playwright/status/{run_id}
- POST /api/v1/platform-admin/sandbox/playwright/run
- POST /api/v1/platform-admin/sandbox/fefo/simulate
- POST /api/v1/platform-admin/sandbox/fefo/shift

Protegido con:
- RBAC Dual de 3 niveles:
  * platform_admin.sandbox.access para lectura / simulación no destructiva.
  * platform_admin.sandbox.manage para mutaciones e inyecciones de datos.
- Guardrails Fail-Fast para los 5 entornos canónicos (local, preview, ci, staging, production):
  * Bloqueo estricto de mutaciones reales en production (403 Forbidden).
  * Confirmación obligatoria para mutaciones en staging (400 Bad Request).
  * Validación de esquemas multi-tenant aislados autorizados contra contaminación de datos.
- Observabilidad OpenTelemetry 4-Pilares:
  * Trazas distribuidas con trace_span y W3C traceparent / X-Trace-ID.
  * Logging estructurado JSON con structlog censurado.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from fastapi.responses import StreamingResponse

from src.core.config import get_settings
from src.core.exceptions import EnvironmentGuardViolationError
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireGlobalPermission,
)
from src.core.mock_data_manager import load_mock_data_backup
from src.core.observability import trace_span
from src.modules.tenancy.application.sandbox_service import SandboxApplicationService
from src.modules.tenancy.presentation.schemas_sandbox import (
    FactoryResetRequest,
    FactoryResetResponse,
    FefoShiftRequest,
    FefoShiftResponse,
    FefoSimulationRequest,
    FefoSimulationResponse,
    FefoSyncTodayRequest,
    FefoSyncTodayResponse,
    GastronomicPresetItem,
    GastronomicPresetListResponse,
    MockDataGenerationRequest,
    MockDataGenerationResponse,
    MockDataHistoryItem,
    PlaywrightCatalogResponseSchema,
    PlaywrightExecutionStateResponse,
    PlaywrightRunRequestSchema,
    PlaywrightRunTriggerResponseSchema,
    SandboxStatusResponse,
)

logger = structlog.get_logger("oppytec.sandbox")

router = APIRouter(tags=["platform_admin_sandbox"])

# Instancia singleton del servicio de Sandbox
_sandbox_service = SandboxApplicationService()


def get_sandbox_service() -> SandboxApplicationService:
    """Retorna la instancia activa del servicio de aplicación de Sandbox."""
    return _sandbox_service


def _enforce_sandbox_environment_guard(
    *,
    action_name: str,
    tenant_schema: str,
    dry_run: bool,
    confirm_staging_action: bool = False,
    confirm_staging_header: str | None = None,
) -> None:
    """
    Guardrail Fail-Fast de blindaje para los 5 entornos canónicos:
    1. 'production': Mutaciones reales (dry_run=False) prohibidas incondicionalmente.
    2. 'staging': Mutaciones reales requieren confirmación explícita (confirmStagingAction o Header).
    3. Todos los entornos: Si dry_run=False, el esquema tenant debe ser un esquema aislado autorizado.
    """
    settings = get_settings()
    env = settings.ENVIRONMENT.strip().lower()

    # 1. Bloqueo estricto e incondicional en Producción
    if env == "production" and not dry_run:
        logger.error(
            "sandbox_guard_blocked_production_mutation",
            action=action_name,
            tenant_schema=tenant_schema,
            environment=env,
        )
        raise EnvironmentGuardViolationError(
            message=(
                f"Acción destructiva rechazada: La operación '{action_name}' con dryRun=False "
                f"está estrictamente prohibida en entorno canónico 'production'. Solo se permiten "
                f"simulaciones de lectura o cálculos proyectivos (dryRun=True)."
            ),
            error_code="PRODUCTION_MUTATION_FORBIDDEN",
            status_code=403,
        )

    # 2. Requerimiento de confirmación en Staging
    if env == "staging":
        is_confirmed = confirm_staging_action or (
            confirm_staging_header is not None
            and confirm_staging_header.strip().lower() == "true"
        )
        if not dry_run and not is_confirmed:
            logger.warning(
                "sandbox_guard_blocked_unconfirmed_staging_action",
                action=action_name,
                tenant_schema=tenant_schema,
                environment=env,
            )
            raise EnvironmentGuardViolationError(
                message=(
                    f"Acción en staging denegada: La operación '{action_name}' con dryRun=False "
                    f"requiere confirmación estricta explícita en entorno 'staging' "
                    f"(confirmStagingAction=true o cabecera 'X-Sandbox-Confirm-Staging: true')."
                ),
                error_code="STAGING_CONFIRMATION_REQUIRED",
                status_code=400,
            )

    # 3. Aislamiento de esquemas autorizados contra contaminación
    if not dry_run:
        is_isolated_schema = (
            tenant_schema.startswith(
                ("tenant_qa_", "tenant_sandbox_", "tenant_test_", "tenant_integration_")
            )
            or tenant_schema in ("tenant_genesis", "tenant_qa_lab", "tenant_sandbox_fefo")
        )
        if not is_isolated_schema:
            logger.error(
                "sandbox_guard_blocked_non_isolated_schema",
                action=action_name,
                tenant_schema=tenant_schema,
                environment=env,
            )
            raise EnvironmentGuardViolationError(
                message=(
                    f"Aislamiento de esquema violado: El esquema destino '{tenant_schema}' "
                    f"no es un esquema de pruebas aislado autorizado para mutaciones físicas del sandbox. "
                    f"Los esquemas autorizados deben iniciar con 'tenant_qa_', 'tenant_sandbox_', 'tenant_test_' "
                    f"o pertenecer al conjunto canónico ('tenant_genesis', 'tenant_qa_lab', 'tenant_sandbox_fefo')."
                ),
                error_code="ISOLATED_SCHEMA_REQUIRED",
                status_code=400,
            )


def _enforce_playwright_guard(
    *,
    suite_id: str | None = None,
    target_id: str | None = None,
    target_tenant_schema: str | None = None,
    confirm_production_run: bool = False,
    confirm_production_header: str | None = None,
) -> None:
    """
    Guardrail para corridas de pruebas E2E en Sandbox:
    1. Aislamiento estricto de inquilinos: Rechazo de esquemas no aislados (anti-IDOR y protección FinOps).
    2. Confirmación explícita obligatoria en entorno de producción.
    """
    settings = get_settings()
    env = settings.ENVIRONMENT.strip().lower()

    # 1. Aislamiento de esquemas autorizados para pruebas
    if target_tenant_schema is not None:
        is_isolated_schema = (
            target_tenant_schema.startswith(
                ("tenant_qa_", "tenant_sandbox_", "tenant_test_", "tenant_integration_")
            )
            or target_tenant_schema in ("tenant_genesis", "tenant_qa_lab", "tenant_sandbox_fefo")
        )
        if not is_isolated_schema:
            logger.error(
                "sandbox_guard_blocked_non_isolated_playwright_schema",
                target_tenant_schema=target_tenant_schema,
                environment=env,
            )
            raise EnvironmentGuardViolationError(
                message=(
                    f"Aislamiento de esquema violado: El esquema destino '{target_tenant_schema}' "
                    f"no es un esquema de pruebas aislado autorizado para Playwright. "
                    f"Las pruebas deben ejecutarse exclusivamente en esquemas aislados autorizados "
                    f"('tenant_genesis', 'tenant_qa_lab', 'tenant_sandbox_fefo' o prefijados con 'tenant_qa_', 'tenant_sandbox_')."
                ),
                error_code="ISOLATED_SCHEMA_REQUIRED",
                status_code=400,
            )

    # 2. Protección en producción
    if env == "production":
        is_confirmed = confirm_production_run or (
            confirm_production_header is not None
            and confirm_production_header.strip().lower() == "true"
        )
        if not is_confirmed:
            target_label = suite_id or target_id or "all"
            logger.warning(
                "sandbox_guard_blocked_unconfirmed_production_playwright_run",
                suite_id=target_label,
                environment=env,
            )
            raise EnvironmentGuardViolationError(
                message=(
                    f"Ejecución Playwright en producción denegada: La suite/corrida '{target_label}' "
                    f"requiere confirmación explícita (confirmProductionRun=true o cabecera 'X-Sandbox-Confirm-Production: true')."
                ),
                error_code="PRODUCTION_CONFIRMATION_REQUIRED",
                status_code=400,
            )


# ============================================================================
# 1. ESTADO DEL SANDBOX
# ============================================================================


@router.get(
    "/api/v1/platform-admin/sandbox/status",
    response_model=SandboxStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener estado operacional y herramientas del Sandbox",
)
async def get_sandbox_status(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.access")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
) -> SandboxStatusResponse:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    with trace_span(
        "platform_admin_sandbox.get_status",
        tracer_name="oppytec.sandbox",
        attributes={"environment": env_name},
    ):
        return service.get_sandbox_status(environment=env_name)


# ============================================================================
# 2. GENERADOR E HISTORIAL DE MOCK DATA
# ============================================================================


@router.get(
    "/api/v1/platform-admin/sandbox/mock-data/history",
    response_model=list[MockDataHistoryItem],
    status_code=status.HTTP_200_OK,
    summary="Listar historial de generaciones de Mock Data",
)
async def get_mock_data_history(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.access")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
) -> list[MockDataHistoryItem]:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    with trace_span(
        "platform_admin_sandbox.mock_data.history",
        tracer_name="oppytec.sandbox",
        attributes={"environment": env_name},
    ):
        return service.get_mock_data_history()


@router.get(
    "/api/v1/platform-admin/sandbox/mock-data/backup",
    status_code=status.HTTP_200_OK,
    summary="Obtener respaldo JSON canónico de Mock Data para inspección o descarga",
)
async def get_mock_data_backup(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.access")),
    ],
    x_oppytec_mock_mode: Annotated[
        str | None, Header(alias="X-OppyTec-Mock-Mode")
    ] = None,
) -> dict[str, Any]:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    with trace_span(
        "platform_admin_sandbox.mock_data.backup",
        tracer_name="oppytec.sandbox",
        attributes={
            "environment": env_name,
            "mock_mode": x_oppytec_mock_mode or "demo",
        },
    ):
        return load_mock_data_backup()


@router.post(
    "/api/v1/platform-admin/sandbox/mock-data/generate",
    response_model=MockDataGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar o simular preliminarmente inyección de Mock Data",
)
async def generate_mock_data(
    payload: MockDataGenerationRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.manage")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
    x_sandbox_confirm_staging: Annotated[str | None, Header(alias="X-Sandbox-Confirm-Staging")] = None,
) -> MockDataGenerationResponse:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    _enforce_sandbox_environment_guard(
        action_name="mock_data_generate",
        tenant_schema=payload.tenant_schema,
        dry_run=payload.dry_run,
        confirm_staging_action=payload.confirm_staging_action,
        confirm_staging_header=x_sandbox_confirm_staging,
    )

    with trace_span(
        "platform_admin_sandbox.mock_data.generate",
        tracer_name="oppytec.sandbox",
        attributes={
            "environment": env_name,
            "tenant_schema": payload.tenant_schema,
            "volume": payload.volume,
            "dry_run": payload.dry_run,
            "is_destructive": not payload.dry_run,
            "user_id": principal.user_id,
        },
    ):
        actor = f"user_{principal.user_id}"
        logger.info(
            "sandbox_mock_data_generation_started",
            actor=actor,
            tenant_schema=payload.tenant_schema,
            volume=payload.volume,
            dry_run=payload.dry_run,
            environment=env_name,
        )
        return service.generate_mock_data(payload, actor_id=actor)


# ============================================================================
# 3. PLAYWRIGHT RUNNER & OBSERVABILIDAD
# ============================================================================


@router.get(
    "/api/v1/platform-admin/sandbox/playwright/catalog",
    response_model=PlaywrightCatalogResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Obtener catálogo dinámico de tests Playwright agrupados por dominio",
)
async def get_playwright_catalog(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.access")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
) -> PlaywrightCatalogResponseSchema:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    with trace_span(
        "platform_admin_sandbox.playwright.catalog",
        tracer_name="oppytec.sandbox",
        attributes={"environment": env_name},
    ):
        return service.get_catalog()


@router.get(
    "/api/v1/platform-admin/sandbox/playwright/status/{run_id}",
    response_model=PlaywrightExecutionStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar estado y trazas de corrida Playwright",
)
async def get_playwright_run_status(
    run_id: Annotated[str, Path(min_length=1, max_length=128)],
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.access")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
) -> PlaywrightExecutionStateResponse:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    with trace_span(
        "platform_admin_sandbox.playwright.get_status",
        tracer_name="oppytec.sandbox",
        attributes={"run_id": run_id, "environment": env_name},
    ):
        return service.get_playwright_run_status(run_id=run_id)


@router.post(
    "/api/v1/platform-admin/sandbox/playwright/run",
    response_model=PlaywrightRunTriggerResponseSchema,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Disparar ejecución de suite o corrida granular Playwright E2E",
)
async def trigger_playwright_run(
    payload: PlaywrightRunRequestSchema,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.manage")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
    x_sandbox_confirm_production: Annotated[str | None, Header(alias="X-Sandbox-Confirm-Production")] = None,
) -> PlaywrightRunTriggerResponseSchema:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    _enforce_playwright_guard(
        suite_id=payload.suite_id,
        target_id=payload.target_id,
        target_tenant_schema=payload.target_tenant_schema,
        confirm_production_run=payload.confirm_production_run,
        confirm_production_header=x_sandbox_confirm_production,
    )

    with trace_span(
        "platform_admin_sandbox.playwright.trigger",
        tracer_name="oppytec.sandbox",
        attributes={
            "environment": env_name,
            "scope": payload.scope,
            "target_id": payload.target_id or payload.suite_id or "all",
            "browser": payload.browser,
            "user_id": principal.user_id,
        },
    ):
        actor = f"user_{principal.user_id}"
        logger.info(
            "sandbox_playwright_run_triggered",
            actor=actor,
            scope=payload.scope,
            target_id=payload.target_id or payload.suite_id,
            browser=payload.browser,
            environment=env_name,
        )
        return service.trigger_run(payload, actor_id=actor)


@router.get(
    "/api/v1/platform-admin/sandbox/playwright/stream/{run_id}",
    status_code=status.HTTP_200_OK,
    summary="Streaming en vivo de pasos y asertos Playwright (SSE)",
)
async def stream_playwright_run(
    run_id: Annotated[str, Path(min_length=1, max_length=128)],
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.access")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
) -> StreamingResponse:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    with trace_span(
        "platform_admin_sandbox.playwright.stream",
        tracer_name="oppytec.sandbox",
        attributes={"run_id": run_id, "environment": env_name},
    ):
        return StreamingResponse(
            service.stream_run_events(run_id=run_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )


# ============================================================================
# 4. SIMULADOR FEFO TIME-WARP
# ============================================================================


@router.post(
    "/api/v1/platform-admin/sandbox/fefo/simulate",
    response_model=FefoSimulationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cálculo proyectivo no destructivo de impacto FEFO",
)
async def simulate_fefo_warp(
    payload: FefoSimulationRequest,
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.access")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
) -> FefoSimulationResponse:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    with trace_span(
        "platform_admin_sandbox.fefo.simulate",
        tracer_name="oppytec.sandbox",
        attributes={
            "environment": env_name,
            "offset_days": payload.offset_days,
            "tenant_schema": payload.tenant_schema,
            "scenario_preset": payload.scenario_preset or "none",
        },
    ):
        return service.simulate_fefo_warp(payload)


@router.post(
    "/api/v1/platform-admin/sandbox/fefo/shift",
    response_model=FefoShiftResponse,
    status_code=status.HTTP_200_OK,
    summary="Aplicar desplazamiento temporal efectivo a lotes FEFO",
)
async def apply_fefo_shift(
    payload: FefoShiftRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.manage")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
    x_sandbox_confirm_staging: Annotated[str | None, Header(alias="X-Sandbox-Confirm-Staging")] = None,
) -> FefoShiftResponse:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    _enforce_sandbox_environment_guard(
        action_name="fefo_shift",
        tenant_schema=payload.tenant_schema,
        dry_run=payload.dry_run,
        confirm_staging_action=payload.confirm_staging_action,
        confirm_staging_header=x_sandbox_confirm_staging,
    )

    with trace_span(
        "platform_admin_sandbox.fefo.shift",
        tracer_name="oppytec.sandbox",
        attributes={
            "environment": env_name,
            "offset_days": payload.offset_days,
            "tenant_schema": payload.tenant_schema,
            "dry_run": payload.dry_run,
            "is_destructive": not payload.dry_run,
            "user_id": principal.user_id,
        },
    ):
        actor = f"user_{principal.user_id}"
        logger.info(
            "sandbox_fefo_shift_applied",
            actor=actor,
            tenant_schema=payload.tenant_schema,
            offset_days=payload.offset_days,
            dry_run=payload.dry_run,
            environment=env_name,
        )
        is_staging_confirmed = (
            x_sandbox_confirm_staging is not None
            and x_sandbox_confirm_staging.strip().lower() == "true"
        )
        return service.apply_fefo_shift(
            payload, actor_id=actor, staging_confirmed=is_staging_confirmed
        )


@router.post(
    "/api/v1/platform-admin/sandbox/fefo/sync-today",
    response_model=FefoSyncTodayResponse,
    status_code=status.HTTP_200_OK,
    summary="Sincronizar quirúrgicamente lotes de inventario y buffet a 'Hoy'",
)
async def sync_batches_today(
    payload: FefoSyncTodayRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.manage")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
    x_sandbox_confirm_staging: Annotated[str | None, Header(alias="X-Sandbox-Confirm-Staging")] = None,
) -> FefoSyncTodayResponse:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    _enforce_sandbox_environment_guard(
        action_name="fefo_sync_today",
        tenant_schema=payload.tenant_schema,
        dry_run=payload.dry_run,
        confirm_staging_action=payload.confirm_staging_action,
        confirm_staging_header=x_sandbox_confirm_staging,
    )

    with trace_span(
        "platform_admin_sandbox.fefo.sync_today",
        tracer_name="oppytec.sandbox",
        attributes={
            "environment": env_name,
            "tenant_schema": payload.tenant_schema,
            "dry_run": payload.dry_run,
            "is_destructive": not payload.dry_run,
            "user_id": principal.user_id,
        },
    ):
        actor = f"user_{principal.user_id}"
        logger.info(
            "sandbox_fefo_sync_today_applied",
            actor=actor,
            tenant_schema=payload.tenant_schema,
            dry_run=payload.dry_run,
            environment=env_name,
        )
        is_staging_confirmed = (
            x_sandbox_confirm_staging is not None
            and x_sandbox_confirm_staging.strip().lower() == "true"
        )
        return service.sync_batches_today(
            payload, actor_id=actor, confirm_staging_action=is_staging_confirmed
        )


# ============================================================================
# 5. PRESETS GASTRONÓMICOS & FACTORY RESET
# ============================================================================


@router.get(
    "/api/v1/platform-admin/sandbox/mock-data/presets",
    response_model=GastronomicPresetListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar presets gastronómicos canónicos multi-tenant",
)
@router.get(
    "/api/v1/platform-admin/sandbox/presets",
    response_model=GastronomicPresetListResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_gastronomic_presets(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.access")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
    x_oppytec_mock_mode: Annotated[str | None, Header(alias="X-OppyTec-Mock-Mode")] = None,
) -> GastronomicPresetListResponse:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    with trace_span(
        "platform_admin_sandbox.mock_data.presets",
        tracer_name="oppytec.sandbox",
        attributes={
            "environment": env_name,
            "mock_mode": x_oppytec_mock_mode or "demo",
        },
    ):
        return service.get_gastronomic_presets()


@router.get(
    "/api/v1/platform-admin/sandbox/mock-data/presets/{preset_id}",
    response_model=GastronomicPresetItem,
    status_code=status.HTTP_200_OK,
    summary="Consultar detalle de un preset gastronómico canónico",
)
@router.get(
    "/api/v1/platform-admin/sandbox/presets/{preset_id}",
    response_model=GastronomicPresetItem,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_gastronomic_preset(
    preset_id: Annotated[str, Path(min_length=3, max_length=64)],
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.access")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
    x_oppytec_mock_mode: Annotated[str | None, Header(alias="X-OppyTec-Mock-Mode")] = None,
) -> GastronomicPresetItem:
    env_name = get_settings().ENVIRONMENT.strip().lower()
    with trace_span(
        "platform_admin_sandbox.mock_data.preset_detail",
        tracer_name="oppytec.sandbox",
        attributes={
            "preset_id": preset_id,
            "environment": env_name,
            "mock_mode": x_oppytec_mock_mode or "demo",
        },
    ):
        preset = service.get_gastronomic_preset(preset_id)
        if not preset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preset gastronómico '{preset_id}' no encontrado.",
            )
        return preset


@router.post(
    "/api/v1/platform-admin/sandbox/mock-data/reset",
    response_model=FactoryResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar Factory Reset de datos sintéticos y presets canónicos",
)
async def factory_reset_mock_data(
    payload: FactoryResetRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("platform_admin.sandbox.manage")),
    ],
    service: Annotated[SandboxApplicationService, Depends(get_sandbox_service)],
    x_sandbox_confirm_staging: Annotated[str | None, Header(alias="X-Sandbox-Confirm-Staging")] = None,
    x_oppytec_mock_mode: Annotated[str | None, Header(alias="X-OppyTec-Mock-Mode")] = None,
) -> FactoryResetResponse:
    env_name = get_settings().ENVIRONMENT.strip().lower()

    # 1. Blindaje Fail-Fast de Entornos Canónicos (evaluado en primera instancia):
    # - En 'production': rechazo inmediato 403 (PRODUCTION_MUTATION_FORBIDDEN)
    # - En 'staging': confirmación estricta requerida 400 (STAGING_CONFIRMATION_REQUIRED)
    # - En todos los entornos: aislamiento estricto de esquema 400 (ISOLATED_SCHEMA_REQUIRED)
    _enforce_sandbox_environment_guard(
        action_name="mock_data_reset",
        tenant_schema=payload.tenant_schema,
        dry_run=False,
        confirm_staging_action=payload.confirm_staging_action,
        confirm_staging_header=x_sandbox_confirm_staging,
    )

    if not payload.confirm_reset:
        raise EnvironmentGuardViolationError(
            message=(
                "Factory Reset rechazado: Se requiere confirmación obligatoria explícita "
                "(confirmReset=true) para ejecutar la purga y restablecimiento de datos sintéticos."
            ),
            error_code="RESET_CONFIRMATION_REQUIRED",
            status_code=400,
        )

    with trace_span(
        "platform_admin_sandbox.mock_data.reset",
        tracer_name="oppytec.sandbox",
        attributes={
            "environment": env_name,
            "tenant_schema": payload.tenant_schema,
            "target_preset_id": payload.target_preset_id,
            "is_destructive": True,
            "user_id": principal.user_id,
            "mock_mode": x_oppytec_mock_mode or "demo",
        },
    ):
        actor = f"user_{principal.user_id}"
        logger.info(
            "sandbox_factory_reset_started",
            actor=actor,
            tenant_schema=payload.tenant_schema,
            target_preset_id=payload.target_preset_id,
            mock_mode=x_oppytec_mock_mode or "demo",
            environment=env_name,
        )
        return service.factory_reset_mock_data(payload, actor_id=actor)

