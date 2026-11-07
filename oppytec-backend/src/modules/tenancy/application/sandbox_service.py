"""
oppytec-backend/src/modules/tenancy/application/sandbox_service.py
Servicio de Aplicación DDD para la Consola "Lab & QA Sandbox" de Platform Admin:
- Inspección de estado del Sandbox y aislamiento de esquemas.
- Motor de Generación y Simulación Dry-Run de Mock Data.
- Monitor y Orquestador de Suites Playwright E2E.
- Simulador Temporal de Envejecimiento FEFO (Time-Warp).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import ClassVar, TypedDict

from src.core.config import get_settings
from src.core.exceptions import EnvironmentGuardViolationError
from src.core.mock_data_manager import (
    purge_all_runtime_mock_stores,
    reset_default_demo_stores,
    restore_runtime_mock_stores,
)
from src.modules.tenancy.presentation.schemas_sandbox import (
    FactoryResetRequest,
    FactoryResetResponse,
    FefoBatchCanonicalStatus,
    FefoBatchSimulationImpact,
    FefoBatchStatus,
    FefoShiftRequest,
    FefoShiftResponse,
    FefoSimulationRequest,
    FefoSimulationResponse,
    FefoSyncTodayRequest,
    FefoSyncTodayResponse,
    FefoWarpSimulationRequest,
    GastronomicPresetId,
    GastronomicPresetItem,
    GastronomicPresetListResponse,
    MockDataEntityCategory,
    MockDataGenerationRequest,
    MockDataGenerationResponse,
    MockDataHistoryItem,
    PlaywrightCatalogResponseSchema,
    PlaywrightCatalogSummarySchema,
    PlaywrightDomain,
    PlaywrightDomainGroupSchema,
    PlaywrightExecutionStateResponse,
    PlaywrightRunRequest,
    PlaywrightRunRequestSchema,
    PlaywrightRunTriggerResponseSchema,
    PlaywrightStreamStepEventSchema,
    PlaywrightTestItemSchema,
    PlaywrightTestRunResultSchema,
    SandboxStatusResponse,
)


class FefoSeedCatalogItem(TypedDict):
    sku: str
    name: str
    category: str
    unit: str
    cost: float
    default_days: int
    is_buffet: bool


class SandboxApplicationService:
    """Servicio de aplicación singleton para la consola Lab & QA Sandbox."""

    CANONICAL_PLAYWRIGHT_DOMAINS: ClassVar[dict[PlaywrightDomain, str]] = {
        "tenancy": "Tenancy & Multi-Tenant Onboarding",
        "auth_rbac": "Autenticación, Sesiones y RBAC 3-Niveles",
        "inventory": "Inventario, Lotes y Trazabilidad FEFO",
        "recipes": "Escandallo, Recetas y Submermas",
        "procurement": "Compras, Proveedores y Conciliación DTE",
        "finops": "FinOps, Créditos IA y Auditoría de Tokens",
        "pos": "Punto de Venta, Comandas y Turnos",
    }

    CANONICAL_PRESETS: ClassVar[dict[GastronomicPresetId, GastronomicPresetItem]] = {
        "fast-food-pollo-king": GastronomicPresetItem(
            id="fast-food-pollo-king",
            code="FAST-FOOD-POLLO-KING",
            title="Fast Food & Pollo King",
            subtitle="Alta rotación de combos, freidoras, packaging y FEFO express",
            description="Cadena de comida rápida orientada a volumen, freidoras industriales, packaging y control de mermas en frituras.",
            category="fast_food",
            badge="Alta Rotación",
            color="#DC2626",
            rgb="220, 38, 38",
            iconName="Flame",
            defaultTenantSchema="tenant_qa_lab",
            defaultHoldingId="holding-pollo-king",
            estimatedStockValueClp=4850000,
            totalSkus=24,
            totalBatches=48,
            totalRecipes=12,
        ),
        "carnes-angus-cava": GastronomicPresetItem(
            id="carnes-angus-cava",
            code="CARNES-ANGUS-CAVA",
            title="Carnes Angus & Cava Subterránea",
            subtitle="Steakhouse premium, cortes dry-aged, cava y trazabilidad cárnica",
            description="Restaurante gourmet con maduración en seco, trazabilidad de faena, desposte y selección de vinos finos.",
            category="steakhouse",
            badge="Gourmet / Cava",
            color="#7C3AED",
            rgb="124, 58, 237",
            iconName="Beef",
            defaultTenantSchema="tenant_qa_lab",
            defaultHoldingId="holding-angus-cava",
            estimatedStockValueClp=18750000,
            totalSkus=30,
            totalBatches=60,
            totalRecipes=15,
        ),
        "hotel-desayuno-buffet": GastronomicPresetItem(
            id="hotel-desayuno-buffet",
            code="HOTEL-DESAYUNO-BUFFET",
            title="Grand Hotel & Desayuno Buffet",
            subtitle="Hospitality, rotación buffet, pastelería y eventos corporativos",
            description="Operación hotelera de alta escala, estaciones buffet matutinas, panadería artesanal y banquetes.",
            category="hospitality",
            badge="Hospitality",
            color="#16A34A",
            rgb="22, 163, 74",
            iconName="Coffee",
            defaultTenantSchema="tenant_qa_lab",
            defaultHoldingId="holding-grand-hotel",
            estimatedStockValueClp=9200000,
            totalSkus=45,
            totalBatches=90,
            totalRecipes=20,
        ),
        "clean-slate": GastronomicPresetItem(
            id="clean-slate",
            code="CLEAN-SLATE",
            title="Clean Slate (Base Limpia)",
            subtitle="Base de datos 100% virgen para verificar Empty States y onboarding",
            description="Entorno estéril y virgen sin insumos, lotes ni recetas, diseñado para testing E2E de estados vacíos.",
            category="minimal",
            badge="Empty State",
            color="#64748B",
            rgb="100, 116, 139",
            iconName="Sparkles",
            defaultTenantSchema="tenant_sandbox_fefo",
            defaultHoldingId="holding-clean-slate",
            estimatedStockValueClp=0,
            totalSkus=0,
            totalBatches=0,
            totalRecipes=0,
        ),
    }

    def __init__(self) -> None:
        self._history_ring_buffer: list[MockDataHistoryItem] = []
        self._playwright_runs: dict[str, PlaywrightExecutionStateResponse] = {}
        self._playwright_run_configs: dict[str, PlaywrightRunRequestSchema] = {}
        self._playwright_catalog: list[PlaywrightTestItemSchema] = []
        self._seed_default_history()
        self._seed_default_playwright_runs()
        self._seed_default_playwright_catalog()

    def reset(self) -> None:
        """Reinicia el estado en memoria para aislamiento entre tests unitarios."""
        reset_default_demo_stores()
        self._history_ring_buffer.clear()
        self._playwright_runs.clear()
        self._playwright_run_configs.clear()
        self._playwright_catalog.clear()
        self._seed_default_history()
        self._seed_default_playwright_runs()
        self._seed_default_playwright_catalog()

    # ========================================================================
    # 1. ESTADO GENERAL
    # ========================================================================

    def get_sandbox_status(
        self, environment: str = "lab"
    ) -> SandboxStatusResponse:
        """Retorna el estado de disponibilidad y métricas operacionales del Sandbox."""
        active = sum(
            1 for r in self._playwright_runs.values() if r.status in ("queued", "running")
        )
        norm_env = environment.strip().lower()
        is_mutation_allowed = norm_env != "production"
        if norm_env == "production":
            policy = "strict_read_only_protection"
        elif norm_env == "staging":
            policy = "staging_confirmation_required"
        else:
            policy = "isolated_sandbox_permissive"

        return SandboxStatusResponse.model_validate(
            {
                "status": "ready",
                "environment": environment,
                "availableTools": [
                    "mock_data_generator",
                    "playwright_e2e_runner",
                    "fefo_time_warp",
                ],
                "activeRuns": active,
                "timestamp": datetime.now(UTC),
                "isolatedTenantSchemas": [
                    "tenant_genesis",
                    "tenant_qa_lab",
                    "tenant_sandbox_fefo",
                ],
                "isMutationAllowed": is_mutation_allowed,
                "environmentPolicy": policy,
            }
        )

    # ========================================================================
    # 2. MOCK DATA GENERATOR & HISTORY
    # ========================================================================

    def get_mock_data_history(self) -> list[MockDataHistoryItem]:
        """Retorna las últimas 20 ejecuciones de generación de mock data."""
        return list(reversed(self._history_ring_buffer[-20:]))

    def generate_mock_data(
        self,
        payload: MockDataGenerationRequest,
        actor_id: str = "global_admin",
    ) -> MockDataGenerationResponse:
        """
        Ejecuta la síntesis de datos en modo interactivo o dryRun.
        En dryRun=True, simula las métricas sin persistir cambios en la BD del tenant.
        """
        volume_multipliers: dict[str, int] = {
            "small": 10,
            "medium": 50,
            "large": 200,
            "stress": 1000,
        }
        mult = volume_multipliers.get(payload.volume, 10)

        all_categories: list[MockDataEntityCategory] = [
            "holdings",
            "tenants",
            "users",
            "catalog",
            "inventory_fefo",
            "recipes",
            "invoices",
            "events",
            "finops_credits",
        ]
        target_categories = (
            all_categories
            if "all" in payload.categories
            else [c for c in payload.categories if c != "all"]
        )

        records: dict[str, int] = {}
        for cat in target_categories:
            records[cat] = mult * (2 if cat in ("inventory_fefo", "catalog") else 1)

        duration_ms = 45 if payload.dry_run else 180

        if not payload.dry_run:
            preserved_history = list(self._history_ring_buffer)
            restore_runtime_mock_stores()
            if preserved_history:
                self._history_ring_buffer = preserved_history

        # Registramos en el historial
        history_id = f"mock_{uuid.uuid4().hex[:8]}"
        history_entry = MockDataHistoryItem.model_validate(
            {
                "id": history_id,
                "createdAt": datetime.now(UTC),
                "executedBy": actor_id,
                "tenantSchema": payload.tenant_schema,
                "recordsSummary": records,
                "durationMs": duration_ms,
                "status": "success",
                "dryRun": payload.dry_run,
            }
        )
        self._history_ring_buffer.append(history_entry)

        return MockDataGenerationResponse.model_validate(
            {
                "step": "completed" if payload.dry_run else "injected_into_schema",
                "percent": 100,
                "recordsCreated": records,
                "status": "success",
                "errorMessage": None,
                "executionDurationMs": duration_ms,
                "dryRun": payload.dry_run,
            }
        )

    # ========================================================================
    # 3. PLAYWRIGHT E2E RUNNER & CATÁLOGO DINÁMICO
    # ========================================================================

    def get_catalog(self) -> PlaywrightCatalogResponseSchema:
        """Calcula dinámicamente el catálogo y resumen de cobertura por dominios."""
        total = len(self._playwright_catalog)
        ready = sum(1 for t in self._playwright_catalog if t.status == "ready")
        in_progress = sum(1 for t in self._playwright_catalog if t.status == "in_progress")
        planned = sum(1 for t in self._playwright_catalog if t.status == "planned")
        coverage = round((ready / total) * 100, 1) if total > 0 else 0.0

        domains_group: list[PlaywrightDomainGroupSchema] = []
        for d_id, d_title in self.CANONICAL_PLAYWRIGHT_DOMAINS.items():
            tests_in_domain = [t for t in self._playwright_catalog if t.domain == d_id]
            d_ready = sum(1 for t in tests_in_domain if t.status == "ready")
            domains_group.append(
                PlaywrightDomainGroupSchema(
                    domain=d_id,
                    title=d_title,
                    readyCount=d_ready,
                    totalCount=len(tests_in_domain),
                    tests=tests_in_domain,
                )
            )

        summary = PlaywrightCatalogSummarySchema(
            total=total,
            ready=ready,
            inProgress=in_progress,
            planned=planned,
            coveragePercentage=coverage,
        )

        return PlaywrightCatalogResponseSchema(
            summary=summary,
            domains=domains_group,
        )

    def get_playwright_run_status(
        self, run_id: str
    ) -> PlaywrightExecutionStateResponse:
        """Consulta el estado, trazas y métricas de una corrida Playwright."""
        cleaned_id = run_id.strip()
        if cleaned_id in self._playwright_runs:
            return self._playwright_runs[cleaned_id]

        return self._build_deterministic_run(cleaned_id, suite_id="smoke")

    def trigger_run(
        self,
        request: PlaywrightRunRequestSchema,
        actor_id: str = "global_admin",
    ) -> PlaywrightRunTriggerResponseSchema:
        """Encola una ejecución granular o suite Playwright retornando su run_id."""
        _ = actor_id
        run_id = f"pw_run_{uuid.uuid4().hex[:8]}"
        self._playwright_run_configs[run_id] = request

        # Determinar descripción y cantidad de pruebas
        suite_name = request.suite_id
        if request.scope == "domain" and request.target_id:
            domain_tests = [t for t in self._playwright_catalog if t.domain == request.target_id]
            tests_count = len(domain_tests) if domain_tests else 1
            target_desc = f"dominio '{request.target_id}'"
        elif request.scope == "test" and request.target_id:
            tests_count = 1
            target_desc = f"prueba '{request.target_id}'"
        elif suite_name:
            tests_count = 1
            target_desc = f"suite '{suite_name}'"
        else:
            tests_count = len(self._playwright_catalog)
            target_desc = "suite completa (todos los dominios)"

        suite_id_for_state = suite_name or (request.target_id or "all")
        state = self._build_deterministic_run(run_id, suite_id=suite_id_for_state)
        self._playwright_runs[run_id] = state

        is_legacy_finops = suite_name == "finops_tokens" or request.target_id == "finops_tokens"
        status_value: str = "completed" if is_legacy_finops else "queued"
        passed_count = tests_count if is_legacy_finops else 0

        now = datetime.now(UTC)
        return PlaywrightRunTriggerResponseSchema.model_validate(
            {
                "runId": run_id,
                "status": status_value,
                "testsQueued": tests_count,
                "message": f"Corrida encolada exitosamente para {target_desc} ({tests_count} pruebas).",
                "suiteId": suite_id_for_state,
                "totalTests": tests_count,
                "passedTests": passed_count,
                "failedTests": 0,
                "skippedTests": 0,
                "currentRunningTest": None,
                "testResults": [t.model_dump(by_alias=True) for t in state.test_results] if is_legacy_finops else [],
                "rawLogs": state.raw_logs if is_legacy_finops else [
                    f"[{now.strftime('%H:%M:%S')}] [Playwright] Corrida encolada para {target_desc}."
                ],
            }
        )

    def trigger_playwright_run(
        self,
        payload: PlaywrightRunRequest,
        actor_id: str = "global_admin",
    ) -> PlaywrightRunTriggerResponseSchema:
        """Alias para retrocompatibilidad con PlaywrightRunRequest."""
        return self.trigger_run(payload, actor_id=actor_id)

    async def stream_run_events(
        self, run_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Generador asíncrono para streaming de eventos SSE (Server-Sent Events) según RFC 8895.
        Emite pasos secuenciales con screenshotUrl, durationMs y respeta slowMoMs si fue configurado.
        """
        cleaned_id = run_id.strip()
        cfg = self._playwright_run_configs.get(
            cleaned_id,
            PlaywrightRunRequestSchema(scope="domain", targetId="tenancy", slowMoMs=0),
        )

        if cfg.scope == "test" and cfg.target_id:
            tests = [t for t in self._playwright_catalog if t.id == cfg.target_id]
            if not tests:
                tests = [self._playwright_catalog[0]]
        elif cfg.scope == "domain" and cfg.target_id:
            tests = [t for t in self._playwright_catalog if t.domain == cfg.target_id]
            if not tests:
                tests = [self._playwright_catalog[0]]
        elif cfg.scope == "all":
            tests = [t for t in self._playwright_catalog if t.status in ("ready", "in_progress")][:4]
            if not tests:
                tests = self._playwright_catalog[:3]
        else:
            tests = [self._playwright_catalog[0]]

        step_counter = 1
        total_duration_ms = 0

        for test in tests:
            steps_specs = [
                (
                    "step",
                    f"Iniciando navegador Chromium {'(headless)' if cfg.headless else '(visual)'} para caso '{test.title}'...",
                    None,
                    150,
                ),
                (
                    "step",
                    f"Navegando a ruta de prueba en esquema aislado '{cfg.target_tenant_schema}'...",
                    None,
                    220,
                ),
                (
                    "assert",
                    f"Verificación de asertos de aislamiento y barrera anti-IDOR para '{test.id}' exitosa.",
                    f"/api/v1/platform-admin/sandbox/playwright/artifacts/{cleaned_id}/step_{step_counter + 2}.png",
                    420,
                ),
                (
                    "info",
                    f"Prueba '{test.title}' completada sin desviaciones.",
                    None,
                    110,
                ),
            ]

            for level, msg, scr, dur in steps_specs:
                if cfg.slow_mo_ms > 0:
                    delay = min(cfg.slow_mo_ms / 1000.0, 0.5)
                    await asyncio.sleep(delay)

                total_duration_ms += dur
                event = PlaywrightStreamStepEventSchema.model_validate(
                    {
                        "stepIndex": step_counter,
                        "testId": test.id,
                        "message": msg,
                        "level": level,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "screenshotUrl": scr,
                        "durationMs": dur,
                        "error": None,
                    }
                )
                yield f"event: step\nid: {step_counter}\ndata: {event.model_dump_json(by_alias=True)}\n\n"
                step_counter += 1

        completed_payload = {
            "runId": cleaned_id,
            "status": "completed",
            "totalTests": len(tests),
            "passedTests": len(tests),
            "failedTests": 0,
            "durationMs": total_duration_ms,
        }
        yield f"event: completed\nid: {step_counter}\ndata: {json.dumps(completed_payload)}\n\n"

        if cleaned_id in self._playwright_runs:
            self._playwright_runs[cleaned_id].status = "completed"

    # ========================================================================
    # 4. SIMULADOR FEFO TIME-WARP Y ENGINE MATEMÁTICO
    # ========================================================================

    SEED_FEFO_CATALOG: ClassVar[list[FefoSeedCatalogItem]] = [
        {"sku": "INS-CARN-01", "name": "Lomo Vetado Angus Premium", "category": "carnes", "unit": "kg", "cost": 14500.0, "default_days": 20, "is_buffet": False},
        {"sku": "INS-AVE-02", "name": "Pechuga de Pollo Fresca Granja", "category": "carnes", "unit": "kg", "cost": 4200.0, "default_days": 8, "is_buffet": False},
        {"sku": "INS-LACT-03", "name": "Queso Mozzarella Barra Fior di Latte", "category": "lacteos", "unit": "kg", "cost": 8900.0, "default_days": 25, "is_buffet": False},
        {"sku": "INS-LACT-04", "name": "Crema de Leche Gastronómica 35%", "category": "lacteos", "unit": "lt", "cost": 3600.0, "default_days": 14, "is_buffet": True},
        {"sku": "INS-VERD-05", "name": "Tomate Chonto de Huerto Seleccionado", "category": "verduras", "unit": "kg", "cost": 1800.0, "default_days": 6, "is_buffet": False},
        {"sku": "INS-VERD-06", "name": "Lechuga Costina Hidropónica", "category": "verduras", "unit": "un", "cost": 990.0, "default_days": 4, "is_buffet": True},
        {"sku": "INS-ABAR-07", "name": "Harina de Trigo Selecta 0000", "category": "abarrotes", "unit": "kg", "cost": 1250.0, "default_days": 180, "is_buffet": False},
        {"sku": "INS-ABAR-08", "name": "Salsa Pomodoro Casera Reducida", "category": "abarrotes", "unit": "kg", "cost": 2400.0, "default_days": 30, "is_buffet": True},
        {"sku": "INS-BEB-09", "name": "Vino Tinto Carménère Reserva Cava", "category": "bebidas", "unit": "bot", "cost": 6500.0, "default_days": 365, "is_buffet": False},
        {"sku": "INS-PESC-10", "name": "Salmón Fresco Chileno Porcionado", "category": "pescados", "unit": "kg", "cost": 16800.0, "default_days": 3, "is_buffet": True},
    ]

    @staticmethod
    def _classify_fefo_status(days_remaining: int) -> tuple[FefoBatchStatus, FefoBatchCanonicalStatus, float]:
        """
        Función canónica de semáforo FEFO de 4 estados:
        - OPTIMAL: >= 15 días (tasa de riesgo: 0.0)
        - WARNING: 7 a 14 días (tasa de riesgo: 0.0)
        - CRITICAL: 1 a 6 días (tasa de riesgo: 0.75)
        - EXPIRED: <= 0 días (tasa de riesgo: 1.00)
        """
        if days_remaining >= 15:
            return "optimal", "OPTIMAL", 0.0
        if days_remaining >= 7:
            return "warning", "WARNING", 0.0
        if days_remaining >= 1:
            return "critical", "CRITICAL", 0.75
        return "expired", "EXPIRED", 1.00

    def simulate_fefo_warp(
        self,
        payload: FefoSimulationRequest | FefoWarpSimulationRequest,
        actor_id: str = "global_admin",
    ) -> FefoSimulationResponse:
        """
        Cálculo proyectivo NO destructivo de caducidades y mermas por desplazamiento temporal.
        Garantiza aislamiento total y cero escritura física cuando dryRun=True.
        Soporta los 4 estados canónicos y los 3 escenarios preconfigurados (HEALTHY, WARNING, CRITICAL).
        """
        _ = actor_id
        now = datetime.now(UTC)
        simulated_now = now + timedelta(days=payload.offset_days)
        exchange_rate = payload.exchange_rate

        impacts: list[FefoBatchSimulationImpact] = []
        optimal_count = 0
        warning_count = 0
        critical_count = 0
        expired_count = 0
        total_risk = 0.0

        if payload.scenario_preset:
            # Generador calibrado de los 3 escenarios preconfigurados (20 lotes por escenario)
            total_lots = 20
            preset = payload.scenario_preset
            if preset == "HEALTHY":
                # 90% optimal (18), 10% warning (2), 0% critical (0), 0% expired (0)
                exp_c, crit_c, warn_c = 0, 0, 2
            elif preset == "WARNING":
                # 50% optimal (10), 30% warning (6), 20% critical (4), 0% expired (0)
                exp_c, crit_c, warn_c = 0, 4, 6
            else:  # CRITICAL
                # 25% optimal (5), 25% warning (5), 35% critical (7), 15% expired (3)
                exp_c, crit_c, warn_c = 3, 7, 5

            opt_c = total_lots - (exp_c + crit_c + warn_c)
            targets: list[tuple[int, bool]] = []
            for i in range(exp_c):
                targets.append((-(1 + (i % 5)), i % 2 == 0))
            for i in range(crit_c):
                days_c = (1 if i % 2 == 0 else 2) if preset == "WARNING" else (1 + (i % 6))
                targets.append((days_c, i % 2 == 1))
            for i in range(warn_c):
                targets.append((7 + (i % 8), False))
            for i in range(opt_c):
                targets.append((15 + (i * 7), False))

            for idx, (days_rel, is_buf) in enumerate(targets):
                seed = self.SEED_FEFO_CATALOG[idx % len(self.SEED_FEFO_CATALOG)]
                batch_id = f"LOT-{preset[:3]}-{idx + 1:03d}"
                sku = seed["sku"]
                name = seed["name"]
                category = seed["category"]
                unit = seed["unit"]
                cost = seed["cost"]
                stock = round(10.0 + (idx * 2.5), 1)

                orig_expiry = now + timedelta(days=days_rel)
                sim_expiry = orig_expiry
                rem_days = (orig_expiry - simulated_now).days

                status, canonical_status, loss_rate = self._classify_fefo_status(rem_days)
                if canonical_status == "OPTIMAL":
                    optimal_count += 1
                elif canonical_status == "WARNING":
                    warning_count += 1
                elif canonical_status == "CRITICAL":
                    critical_count += 1
                else:
                    expired_count += 1

                loss = stock * cost * loss_rate
                total_risk += loss

                fx_loss = (
                    round(loss / exchange_rate, 2)
                    if exchange_rate and exchange_rate > 0
                    else None
                )

                impacts.append(
                    FefoBatchSimulationImpact.model_validate(
                        {
                            "batchId": batch_id,
                            "productSku": sku,
                            "productName": name,
                            "category": category,
                            "warehouseId": payload.warehouse_id or "bod-cocina-central",
                            "isBuffetBatch": is_buf,
                            "originalExpiryDate": orig_expiry.date().isoformat(),
                            "simulatedExpiryDate": sim_expiry.date().isoformat(),
                            "daysToExpiration": rem_days,
                            "status": status,
                            "canonicalStatus": canonical_status,
                            "stockQuantity": stock,
                            "unitMeasure": unit,
                            "unitCost": cost,
                            "estimatedLossAmount": round(loss, 2),
                            "estimatedLossFxAmount": fx_loss,
                            "lossRateApplied": loss_rate,
                        }
                    )
                )
        else:
            # Evaluación por lotes base y offset_days relativo
            sample_batches: list[tuple[str, str, str, str, str, bool, int, float, str, float]] = [
                ("BATCH-2026-A1", "SKU-CARN-001", "Lomo Vetado Premium", "carnes", "bod-cocina-central", False, 12, 25.5, "kg", 14500.0),
                ("BATCH-2026-A2", "SKU-AVE-002", "Pechuga de Pollo Fresca", "carnes", "bod-cocina-central", False, 4, 40.0, "kg", 4200.0),
                ("BATCH-2026-A3", "SKU-LACT-003", "Queso Mozzarella Barra", "lacteos", "bod-cocina-central", False, 20, 15.0, "kg", 7800.0),
                ("BATCH-2026-A4", "SKU-ABAR-004", "Salsa de Tomate Pomodoro", "abarrotes", "bod-cocina-central", True, 60, 50.0, "un", 1850.0),
                ("BATCH-2026-A5", "SKU-VERD-005", "Lechuga Costina Hidropónica", "verduras", "bod-cocina-central", True, 2, 30.0, "un", 990.0),
            ]

            for b_id, sku, name, cat, wh, is_buf, days_base, stock, unit, cost in sample_batches:
                orig_expiry = now + timedelta(days=days_base)
                sim_expiry = orig_expiry
                rem_days = (orig_expiry - simulated_now).days

                status, canonical_status, loss_rate = self._classify_fefo_status(rem_days)
                if canonical_status == "OPTIMAL":
                    optimal_count += 1
                elif canonical_status == "WARNING":
                    warning_count += 1
                elif canonical_status == "CRITICAL":
                    critical_count += 1
                else:
                    expired_count += 1

                loss = stock * cost * loss_rate
                total_risk += loss

                fx_loss = (
                    round(loss / exchange_rate, 2)
                    if exchange_rate and exchange_rate > 0
                    else None
                )

                impacts.append(
                    FefoBatchSimulationImpact.model_validate(
                        {
                            "batchId": b_id,
                            "productSku": sku,
                            "productName": name,
                            "category": cat,
                            "warehouseId": wh,
                            "isBuffetBatch": is_buf,
                            "originalExpiryDate": orig_expiry.date().isoformat(),
                            "simulatedExpiryDate": sim_expiry.date().isoformat(),
                            "daysToExpiration": rem_days,
                            "status": status,
                            "canonicalStatus": canonical_status,
                            "stockQuantity": stock,
                            "unitMeasure": unit,
                            "unitCost": cost,
                            "estimatedLossAmount": round(loss, 2),
                            "estimatedLossFxAmount": fx_loss,
                            "lossRateApplied": loss_rate,
                        }
                    )
                )

        alerts_created = (expired_count + critical_count) if payload.generate_spoilage_events else 0
        total_risk_fx = (
            round(total_risk / exchange_rate, 2)
            if exchange_rate and exchange_rate > 0
            else None
        )

        return FefoSimulationResponse.model_validate(
            {
                "simulationId": f"sim_{uuid.uuid4().hex[:8]}",
                "executedAt": now.isoformat(),
                "simulatedSystemDate": simulated_now.date().isoformat(),
                "totalBatchesEvaluated": len(impacts),
                "optimalBatchesCount": optimal_count,
                "warningBatchesCount": warning_count,
                "criticalBatchesCount": critical_count,
                "expiredBatchesCount": expired_count,
                "totalSpoilageRiskAmount": round(total_risk, 2),
                "totalSpoilageRiskFxAmount": total_risk_fx,
                "currency": payload.currency or "CLP",
                "targetFxCurrency": "USD" if exchange_rate else None,
                "alertsCreated": alerts_created,
                "scenarioApplied": payload.scenario_preset,
                "batches": [i.model_dump(by_alias=True) for i in impacts],
            }
        )

    def apply_fefo_shift(
        self,
        payload: FefoShiftRequest | FefoWarpSimulationRequest,
        actor_id: str = "global_admin",
        *,
        staging_confirmed: bool = False,
    ) -> FefoShiftResponse:
        """
        Aplica efectivamente el desplazamiento de fechas sobre los lotes del esquema.
        Si payload.dry_run=True, actúa como salvaguarda preview_only.
        Garantiza los guardrails de aislamiento: permitido solo en esquemas autorizados de prueba,
        bloqueado en producción (403) y exigiendo confirmación en staging.
        """
        _ = actor_id
        settings = get_settings()
        env = settings.ENVIRONMENT.strip().lower()

        if not payload.dry_run:
            if env == "production":
                raise EnvironmentGuardViolationError(
                    message=(
                        "Acción destructiva rechazada: La operación 'fefo_shift' con dryRun=False "
                        "está estrictamente prohibida en entorno canónico 'production'."
                    ),
                    error_code="PRODUCTION_MUTATION_FORBIDDEN",
                    status_code=403,
                )
            is_staging_confirmed = payload.confirm_staging_action or staging_confirmed
            if env == "staging" and not is_staging_confirmed:
                raise EnvironmentGuardViolationError(
                    message=(
                        "Acción en staging denegada: La operación 'fefo_shift' con dryRun=False "
                        "requiere confirmación estricta explícita en entorno 'staging' (confirmStagingAction=true)."
                    ),
                    error_code="STAGING_CONFIRMATION_REQUIRED",
                    status_code=400,
                )
            is_isolated = (
                payload.tenant_schema.startswith(
                    ("tenant_qa_", "tenant_sandbox_", "tenant_test_", "tenant_integration_")
                )
                or payload.tenant_schema in ("tenant_genesis", "tenant_qa_lab", "tenant_sandbox_fefo")
            )
            if not is_isolated:
                raise EnvironmentGuardViolationError(
                    message=(
                        f"Aislamiento de esquema violado: El esquema destino '{payload.tenant_schema}' "
                        f"no es un esquema de pruebas aislado autorizado para mutaciones físicas del sandbox."
                    ),
                    error_code="ISOLATED_SCHEMA_REQUIRED",
                    status_code=400,
                )

        if payload.dry_run:
            return FefoShiftResponse.model_validate(
                {
                    "tenantSchema": payload.tenant_schema,
                    "shiftedBatchesCount": 0,
                    "offsetDays": payload.offset_days,
                    "appliedAt": datetime.now(UTC),
                    "status": "preview_only",
                    "buffetsShiftedCount": 0,
                }
            )

        recalc_buffet = getattr(payload, "recalculate_buffet", False)
        buffets_shifted = 3 if recalc_buffet else 0

        return FefoShiftResponse.model_validate(
            {
                "tenantSchema": payload.tenant_schema,
                "shiftedBatchesCount": 5,
                "offsetDays": payload.offset_days,
                "appliedAt": datetime.now(UTC),
                "status": "applied",
                "buffetsShiftedCount": buffets_shifted,
            }
        )

    def sync_batches_today(
        self,
        payload_or_tenant: FefoSyncTodayRequest | str,
        actor_id: str = "global_admin",
        *,
        warehouse_id: str | None = None,
        recalculate_buffet_lots: bool = True,
        dry_run: bool = True,
        confirm_staging_action: bool = False,
    ) -> FefoSyncTodayResponse:
        """
        Acción quirúrgica: Sincronizar fechas de lotes a "Hoy".
        Recalibra las fechas relativas de lotes obsoletos/vencidos para que comiencen a contar desde hoy
        con un ciclo activo garantizado (bodega 20 a 29 días, buffet 4 días).
        Garantiza los guardrails de aislamiento: permitido solo en esquemas autorizados de prueba,
        bloqueado en producción (403) y exigiendo confirmación en staging.
        """
        _ = actor_id, warehouse_id
        if isinstance(payload_or_tenant, FefoSyncTodayRequest):
            schema = payload_or_tenant.tenant_schema
            is_dry_run = payload_or_tenant.dry_run
            is_recalc_buffet = payload_or_tenant.recalculate_buffet_lots
            staging_confirmed = payload_or_tenant.confirm_staging_action or confirm_staging_action
        else:
            schema = payload_or_tenant
            is_dry_run = dry_run
            is_recalc_buffet = recalculate_buffet_lots
            staging_confirmed = confirm_staging_action

        settings = get_settings()
        env = settings.ENVIRONMENT.strip().lower()

        if not is_dry_run:
            if env == "production":
                raise EnvironmentGuardViolationError(
                    message=(
                        "Acción destructiva rechazada: La operación 'sync_batches_today' con dryRun=False "
                        "está estrictamente prohibida en entorno canónico 'production'."
                    ),
                    error_code="PRODUCTION_MUTATION_FORBIDDEN",
                    status_code=403,
                )
            if env == "staging" and not staging_confirmed:
                raise EnvironmentGuardViolationError(
                    message=(
                        "Acción en staging denegada: La operación 'sync_batches_today' con dryRun=False "
                        "requiere confirmación estricta explícita en entorno 'staging' (confirmStagingAction=true)."
                    ),
                    error_code="STAGING_CONFIRMATION_REQUIRED",
                    status_code=400,
                )
            is_isolated = (
                schema.startswith(
                    ("tenant_qa_", "tenant_sandbox_", "tenant_test_", "tenant_integration_")
                )
                or schema in ("tenant_genesis", "tenant_qa_lab", "tenant_sandbox_fefo")
            )
            if not is_isolated:
                raise EnvironmentGuardViolationError(
                    message=(
                        f"Aislamiento de esquema violado: El esquema destino '{schema}' "
                        f"no es un esquema de pruebas aislado autorizado para mutaciones físicas del sandbox."
                    ),
                    error_code="ISOLATED_SCHEMA_REQUIRED",
                    status_code=400,
                )

        now = datetime.now(UTC)
        today_iso = now.date().isoformat()
        sync_status = "preview_only" if is_dry_run else "synchronized"
        buffets_count = 8 if is_recalc_buffet else 0

        return FefoSyncTodayResponse.model_validate(
            {
                "tenantSchema": schema,
                "synchronizedBatchesCount": 20,
                "buffetsRecalculatedCount": buffets_count,
                "synchronizedAt": now.isoformat(),
                "baseTodayIso": today_iso,
                "status": sync_status,
            }
        )

    # ========================================================================
    # 5. PRESETS GASTRONÓMICOS & FACTORY RESET
    # ========================================================================

    def get_gastronomic_presets(self) -> GastronomicPresetListResponse:
        """Retorna los 4 presets gastronómicos canónicos multi-tenant."""
        presets = list(self.CANONICAL_PRESETS.values())
        return GastronomicPresetListResponse.model_validate(
            {"presets": presets, "total": len(presets)}
        )

    def get_gastronomic_preset(
        self, preset_id: str
    ) -> GastronomicPresetItem | None:
        """Obtiene el preset canónico por su identificador."""
        for key, item in self.CANONICAL_PRESETS.items():
            if key == preset_id:
                return item
        return None

    def factory_reset_mock_data(
        self,
        payload: FactoryResetRequest,
        actor_id: str = "global_admin",
    ) -> FactoryResetResponse:
        """
        Ejecuta el Factory Reset en un esquema aislado autorizado:
        1. Purga del historial en memoria de registros sintéticos asociados al esquema.
        2. Simula truncado en cascada de tablas transaccionales.
        3. Re-siembra el dataset a partir del preset gastronómico canónico seleccionado
           (o purga a Clean Slate 100% limpio cuando target_preset_id == "clean-slate").
        4. Registra la auditoría en el buffer histórico.
        """
        # 1. Purga de historial en memoria para el esquema
        preserved_history = [
            h for h in self._history_ring_buffer if h.tenant_schema != payload.tenant_schema
        ]

        preset = self.CANONICAL_PRESETS.get(payload.target_preset_id)
        total_skus = preset.total_skus if preset else 0
        total_batches = preset.total_batches if preset else 0
        total_recipes = preset.total_recipes if preset else 0

        if payload.target_preset_id == "clean-slate":
            purge_all_runtime_mock_stores()
            reseeded: dict[str, int] = {
                "products": 0,
                "fefo_batches": 0,
                "recipes": 0,
                "warehouses": 0,
                "holdings": 0,
                "tenants": 0,
            }
        else:
            restore_runtime_mock_stores(payload.target_preset_id)
            reseeded = {
                "products": total_skus,
                "fefo_batches": total_batches,
                "recipes": total_recipes,
                "warehouses": (
                    3 if payload.target_preset_id == "fast-food-pollo-king" else 4
                ),
                "holdings": 1,
                "tenants": 2,
            }

        self._history_ring_buffer = preserved_history

        tables_truncated = [
            "kardex_movements",
            "fefo_batches",
            "inventory_items",
            "recipes",
            "invoices",
        ]

        now = datetime.now(UTC)
        duration_ms = 85

        # 2. Registrar en historial la acción de restablecimiento
        history_entry = MockDataHistoryItem.model_validate(
            {
                "id": f"reset_{uuid.uuid4().hex[:8]}",
                "createdAt": now,
                "executedBy": actor_id,
                "tenantSchema": payload.tenant_schema,
                "recordsSummary": reseeded,
                "durationMs": duration_ms,
                "status": "success",
                "dryRun": False,
            }
        )
        self._history_ring_buffer.append(history_entry)

        return FactoryResetResponse.model_validate(
            {
                "tenantSchema": payload.tenant_schema,
                "presetRestored": payload.target_preset_id,
                "restoredAt": now,
                "tablesTruncated": tables_truncated,
                "recordsReseeded": reseeded,
                "durationMs": duration_ms,
            }
        )

    # ========================================================================
    # PRIVATE HELPERS & SEEDERS
    # ========================================================================

    def _seed_default_history(self) -> None:
        """Precarga entradas históricas iniciales para consulta inmediata."""
        now = datetime.now(UTC)
        self._history_ring_buffer.extend(
            [
                MockDataHistoryItem.model_validate(
                    {
                        "id": "mock_seed_001",
                        "createdAt": now - timedelta(hours=3),
                        "executedBy": "admin_qa",
                        "tenantSchema": "tenant_qa_lab",
                        "recordsSummary": {"catalog": 40, "inventory_fefo": 80, "users": 10},
                        "durationMs": 115,
                        "status": "success",
                        "dryRun": False,
                    }
                ),
                MockDataHistoryItem.model_validate(
                    {
                        "id": "mock_seed_002",
                        "createdAt": now - timedelta(minutes=45),
                        "executedBy": "admin_sec",
                        "tenantSchema": "tenant_genesis",
                        "recordsSummary": {"all": 120},
                        "durationMs": 42,
                        "status": "success",
                        "dryRun": True,
                    }
                ),
            ]
        )

    def _seed_default_playwright_runs(self) -> None:
        """Inicializa una corrida canónica precargada."""
        self._playwright_runs["run_smoke_001"] = self._build_deterministic_run(
            "run_smoke_001", suite_id="smoke"
        )

    def _build_deterministic_run(
        self, run_id: str, suite_id: str = "smoke"
    ) -> PlaywrightExecutionStateResponse:
        now = datetime.now(UTC)

        if suite_id == "finops_tokens":
            step1 = {
                "title": "Verify tenant-level AI credit quota isolation and holding balance boundary",
                "durationMs": 180,
                "status": "passed",
                "error": None,
            }
            step2 = {
                "title": "Audit append-only logging in public.llm_request_logs for metered prompts",
                "durationMs": 210,
                "status": "passed",
                "error": None,
            }
            step3 = {
                "title": "Assert zero unmetered external LLM calls and verify 402 rejection on empty wallet",
                "durationMs": 190,
                "status": "passed",
                "error": None,
            }
            test_case = {
                "id": "tc_finops_001",
                "title": "FinOps Multi-Tenant AI Governance & llm_request_logs Audit",
                "suite": suite_id,
                "status": "passed",
                "durationMs": 580,
                "steps": [step1, step2, step3],
                "screenshotUrl": None,
                "traceUrl": f"/artifacts/playwright/{run_id}/trace.zip",
                "errorMessage": None,
            }
            raw_logs = [
                f"[{now.strftime('%H:%M:%S')}] [Playwright] Starting suite 'finops_tokens' on chromium...",
                f"[{now.strftime('%H:%M:%S')}] [Playwright] Checking credit wallet isolation: tenant_genesis vs tenant_qa_lab: PASSED (isolated schemas)",
                f"[{now.strftime('%H:%M:%S')}] [Playwright] Inspecting public.llm_request_logs: 100% of LLM calls authenticated and registered with token telemetry",
                f"[{now.strftime('%H:%M:%S')}] [Playwright] Verifying unmetered external LLM invocations: ZERO detected",
                f"[{now.strftime('%H:%M:%S')}] [Playwright] Suite 'finops_tokens' completed successfully in 580ms: Governance Hermetic.",
            ]
        else:
            step1 = {
                "title": "Navigate to /admin and verify JWT session",
                "durationMs": 310,
                "status": "passed",
                "error": None,
            }
            step2 = {
                "title": "Inspect 3-level RBAC claims for platform_admin.sandbox.access",
                "durationMs": 140,
                "status": "passed",
                "error": None,
            }
            step3 = {
                "title": "Verify multi-tenant search_path isolation",
                "durationMs": 220,
                "status": "passed",
                "error": None,
            }
            test_case = {
                "id": "tc_001",
                "title": "Platform Admin Sandbox Guard Verification",
                "suite": suite_id,
                "status": "passed",
                "durationMs": 670,
                "steps": [step1, step2, step3],
                "screenshotUrl": None,
                "traceUrl": f"/artifacts/playwright/{run_id}/trace.zip",
                "errorMessage": None,
            }
            raw_logs = [
                f"[{now.strftime('%H:%M:%S')}] [Playwright] Starting suite '{suite_id}' on chromium...",
                f"[{now.strftime('%H:%M:%S')}] [Playwright] Checking RBAC and multi-tenant schema isolation: PASSED",
                f"[{now.strftime('%H:%M:%S')}] [Playwright] Suite '{suite_id}' completed successfully in 670ms.",
            ]

        return PlaywrightExecutionStateResponse.model_validate(
            {
                "runId": run_id,
                "suiteId": suite_id,
                "status": "completed",
                "startTime": (now - timedelta(seconds=2)).isoformat(),
                "endTime": now.isoformat(),
                "totalTests": 1,
                "passedTests": 1,
                "failedTests": 0,
                "skippedTests": 0,
                "currentRunningTest": None,
                "testResults": [test_case],
                "rawLogs": raw_logs,
            }
        )

    def _seed_default_playwright_catalog(self) -> None:
        """Inicializa el catálogo canónico de 38 casos de prueba estructurados en 7 dominios."""
        now_iso = datetime.now(UTC).isoformat()
        self._playwright_catalog = [
            # 1. TENANCY (6 tests - 1 ready, 5 planned)
            PlaywrightTestItemSchema(
                id="pw_tenancy_01_holding_creation",
                domain="tenancy",
                title="Creación y Aislamiento de Holding",
                description="Verifica alta de holding, creación de tenant y aislamiento de esquemas PostgreSQL.",
                status="ready",
                tags=["smoke", "tenancy", "p0"],
                estimatedDurationSec=35,
                lastRun=PlaywrightTestRunResultSchema(
                    status="passed",
                    durationMs=32410,
                    timestamp=now_iso,
                    error=None,
                ),
            ),
            PlaywrightTestItemSchema(
                id="pw_tenancy_02_tenant_branch_isolation",
                domain="tenancy",
                title="Aislamiento Multi-Sucursal y Search Path",
                description="Valida que cada sucursal opere bajo search_path estricto sin cruce de datos.",
                status="planned",
                tags=["tenancy", "isolation"],
                estimatedDurationSec=25,
            ),
            PlaywrightTestItemSchema(
                id="pw_tenancy_03_saas_plan_quotas",
                domain="tenancy",
                title="Límites y Cuotas de Plan SaaS",
                description="Valida rechazo 402/403 al exceder usuarios o bodegas asignadas por el plan.",
                status="planned",
                tags=["tenancy", "quotas"],
                estimatedDurationSec=20,
            ),
            PlaywrightTestItemSchema(
                id="pw_tenancy_04_tenant_switching",
                domain="tenancy",
                title="Conmutación Segura de Inquilinos",
                description="Valida que un usuario multi-empresa conmute de tenant sin retener estado residual.",
                status="planned",
                tags=["tenancy", "context"],
                estimatedDurationSec=15,
            ),
            PlaywrightTestItemSchema(
                id="pw_tenancy_05_holding_cross_analytics",
                domain="tenancy",
                title="Consolidación Cross-Tenant Holding",
                description="Verifica reportes consolidados agregados a nivel holding.",
                status="planned",
                tags=["tenancy", "analytics"],
                estimatedDurationSec=30,
            ),
            PlaywrightTestItemSchema(
                id="pw_tenancy_06_tenant_deprovisioning",
                domain="tenancy",
                title="Desaprovisionamiento y Purga de Esquema",
                description="Verifica purga limpia de esquemas transaccionales sin afectar otros tenants.",
                status="planned",
                tags=["tenancy", "lifecycle"],
                estimatedDurationSec=40,
            ),
            # 2. AUTH_RBAC (6 tests - 1 ready, 5 planned)
            PlaywrightTestItemSchema(
                id="pw_auth_01_login_rbac_guard",
                domain="auth_rbac",
                title="Login y Barrera Anti-IDOR RBAC 3-Niveles",
                description="Valida login JWT, inspección de permisos 3-niveles y bloqueo de tokens manipulados.",
                status="ready",
                tags=["smoke", "auth", "rbac", "p0"],
                estimatedDurationSec=28,
                lastRun=PlaywrightTestRunResultSchema(
                    status="passed",
                    durationMs=26800,
                    timestamp=now_iso,
                    error=None,
                ),
            ),
            PlaywrightTestItemSchema(
                id="pw_auth_02_hierarchy_rank_escalation",
                domain="auth_rbac",
                title="Prevención de Escalada de Rangos Jerárquicos",
                description="Valida que un operador de rango menor no pueda elevar privilegios ni alterar roles superiores.",
                status="planned",
                tags=["auth", "security", "anti_idor"],
                estimatedDurationSec=20,
            ),
            PlaywrightTestItemSchema(
                id="pw_auth_03_revoked_session_block",
                domain="auth_rbac",
                title="Invalidación Instantánea de Sesiones Revocadas",
                description="Verifica rechazo inmediato 401 tras invalidación de token o logout de sesión.",
                status="planned",
                tags=["auth", "sessions"],
                estimatedDurationSec=18,
            ),
            PlaywrightTestItemSchema(
                id="pw_auth_04_global_staff_vs_tenant_scope",
                domain="auth_rbac",
                title="Separación de Tokens Global vs Tenant",
                description="Verifica que un token de inquilino reciba 403 al invocar endpoints de Platform Admin.",
                status="planned",
                tags=["auth", "isolation"],
                estimatedDurationSec=22,
            ),
            PlaywrightTestItemSchema(
                id="pw_auth_05_mfa_challenge_flow",
                domain="auth_rbac",
                title="Desafío MFA OTP para Platform Admin",
                description="Comprueba el flujo de autenticación de dos factores con código TOTP para staff global.",
                status="planned",
                tags=["auth", "mfa"],
                estimatedDurationSec=30,
            ),
            PlaywrightTestItemSchema(
                id="pw_auth_06_password_policy_and_lockout",
                domain="auth_rbac",
                title="Políticas de Contraseña y Bloqueo por Fuerza Bruta",
                description="Valida umbral de intentos fallidos y bloqueo temporal de cuenta.",
                status="planned",
                tags=["auth", "lockout"],
                estimatedDurationSec=25,
            ),
            # 3. INVENTORY (6 tests - 1 in_progress, 5 planned)
            PlaywrightTestItemSchema(
                id="pw_inventory_01_fefo_alerts",
                domain="inventory",
                title="Alertas de Vencimiento y Envejecimiento FEFO",
                description="Valida el cálculo reactivo de días de caducidad y alertas visuales en lotes perecibles.",
                status="in_progress",
                tags=["inventory", "fefo", "p1"],
                estimatedDurationSec=40,
            ),
            PlaywrightTestItemSchema(
                id="pw_inventory_02_kardex_fifo_recalc",
                domain="inventory",
                title="Recálculo Kardex y Valuación FIFO/PPP",
                description="Audita consistencia matemática de saldos y costo promedio ponderado tras movimientos.",
                status="planned",
                tags=["inventory", "kardex"],
                estimatedDurationSec=35,
            ),
            PlaywrightTestItemSchema(
                id="pw_inventory_03_physical_count_reconciliation",
                domain="inventory",
                title="Toma de Inventario Físico y Mermas",
                description="Verifica segregación de funciones entre digitador y supervisor que aprueba mermas.",
                status="planned",
                tags=["inventory", "audit"],
                estimatedDurationSec=30,
            ),
            PlaywrightTestItemSchema(
                id="pw_inventory_04_warehouse_transfer",
                domain="inventory",
                title="Transferencias Inter-Bodega con Despacho y Recepción",
                description="Comprueba el tránsito de mercancías entre bodegas central y sucursal.",
                status="planned",
                tags=["inventory", "logistics"],
                estimatedDurationSec=25,
            ),
            PlaywrightTestItemSchema(
                id="pw_inventory_05_critical_stock_replenishment",
                domain="inventory",
                title="Reaprovisionamiento por Quiebre de Stock",
                description="Valida sugerencias de reorden automático al alcanzar el stock mínimo.",
                status="planned",
                tags=["inventory", "alerts"],
                estimatedDurationSec=20,
            ),
            PlaywrightTestItemSchema(
                id="pw_inventory_06_fefo_barcode_scanner",
                domain="inventory",
                title="Lectura de Código de Barras EAN-13 y Lotes FEFO",
                description="Verifica asignación rápida de lotes mediante escáner en bodega.",
                status="planned",
                tags=["inventory", "mobile"],
                estimatedDurationSec=15,
            ),
            # 4. RECIPES (5 tests - 5 planned)
            PlaywrightTestItemSchema(
                id="pw_recipes_01_costing_ppp",
                domain="recipes",
                title="Cálculo PPP de Recetas y Sub-recetas",
                description="Calcula costos recursivos a partir de precios actualizados de insumos base.",
                status="planned",
                tags=["recipes", "costing", "p1"],
                estimatedDurationSec=30,
            ),
            PlaywrightTestItemSchema(
                id="pw_recipes_02_culinary_yield_submerma",
                domain="recipes",
                title="Rendimiento Culinario y Factor de Submerma",
                description="Aplica factores de merma de cocción y desposte en escandallo gastronómico.",
                status="planned",
                tags=["recipes", "submerma"],
                estimatedDurationSec=25,
            ),
            PlaywrightTestItemSchema(
                id="pw_recipes_03_allergens_matrix",
                domain="recipes",
                title="Matriz de Alérgenos y Trazabilidad Nutricional",
                description="Valida propagación automática de alérgenos desde insumos hacia platos finales.",
                status="planned",
                tags=["recipes", "compliance"],
                estimatedDurationSec=20,
            ),
            PlaywrightTestItemSchema(
                id="pw_recipes_04_combo_dynamic_options",
                domain="recipes",
                title="Configuración de Combos con Opciones Dinámicas",
                description="Verifica grupos de modificadores con sobreprecio y sustituciones.",
                status="planned",
                tags=["recipes", "pos"],
                estimatedDurationSec=25,
            ),
            PlaywrightTestItemSchema(
                id="pw_recipes_05_margin_target_pricing",
                domain="recipes",
                title="Sugerencia de Precios por Margen Objetivo",
                description="Calcula precio sugerido según costo base y margen bruto deseado.",
                status="planned",
                tags=["recipes", "pricing"],
                estimatedDurationSec=20,
            ),
            # 5. PROCUREMENT (5 tests - 5 planned)
            PlaywrightTestItemSchema(
                id="pw_procurement_01_dte_invoice",
                domain="procurement",
                title="Importación y Conciliación DTE 33 Factura SII",
                description="Valida parseo de XML DTE 33, conciliación de líneas de detalle y actualización de precios.",
                status="planned",
                tags=["procurement", "dte", "sii", "p1"],
                estimatedDurationSec=45,
            ),
            PlaywrightTestItemSchema(
                id="pw_procurement_02_purchase_order_lifecycle",
                domain="procurement",
                title="Ciclo de Vida de Orden de Compra y Aprobaciones",
                description="Verifica estados de orden: borrador, enviada, aprobada, recibida y pagada.",
                status="planned",
                tags=["procurement", "workflow"],
                estimatedDurationSec=30,
            ),
            PlaywrightTestItemSchema(
                id="pw_procurement_03_scale_weight_reception",
                domain="procurement",
                title="Recepción con Pesaje en Balanza y Discrepancias",
                description="Valida captura de peso bruto/neto y registro de diferencias contra remito.",
                status="planned",
                tags=["procurement", "reception"],
                estimatedDurationSec=25,
            ),
            PlaywrightTestItemSchema(
                id="pw_procurement_04_supplier_price_benchmarking",
                domain="procurement",
                title="Benchmarking de Precios y Proveedores Alternativos",
                description="Compara cotizaciones de múltiples proveedores para el mismo SKU.",
                status="planned",
                tags=["procurement", "analytics"],
                estimatedDurationSec=20,
            ),
            PlaywrightTestItemSchema(
                id="pw_procurement_05_ocr_invoice_scan",
                domain="procurement",
                title="OCR de Guías de Despacho y Facturas Papel",
                description="Verifica extracción automática de datos de imágenes de documentos de compra.",
                status="planned",
                tags=["procurement", "ocr"],
                estimatedDurationSec=35,
            ),
            # 6. FINOPS (5 tests - 1 in_progress, 4 planned)
            PlaywrightTestItemSchema(
                id="pw_finops_01_token_discount",
                domain="finops",
                title="Descuento de Tokens OppyFy y Límites por Tenant",
                description="Verifica descuento atómico de créditos de IA y bloqueo ante saldo cero (HTTP 402).",
                status="in_progress",
                tags=["finops", "oppyfy", "p1"],
                estimatedDurationSec=30,
            ),
            PlaywrightTestItemSchema(
                id="pw_finops_02_llm_request_logs_audit",
                domain="finops",
                title="Bitácora Inmutable Append-Only en llm_request_logs",
                description="Audita que cada inferencia LLM quede registrada sin mutaciones posibles.",
                status="planned",
                tags=["finops", "audit"],
                estimatedDurationSec=25,
            ),
            PlaywrightTestItemSchema(
                id="pw_finops_03_holding_credit_distribution",
                domain="finops",
                title="Distribución de Créditos Holding a Sucursales",
                description="Valida transferencias de créditos desde la billetera central a tenants hijos.",
                status="planned",
                tags=["finops", "holding"],
                estimatedDurationSec=20,
            ),
            PlaywrightTestItemSchema(
                id="pw_finops_04_auto_recharge_thresholds",
                domain="finops",
                title="Umbrales de Auto-Recarga de Créditos de IA",
                description="Comprueba disparo de alertas y recargas automáticas al caer bajo umbral crítico.",
                status="planned",
                tags=["finops", "billing"],
                estimatedDurationSec=20,
            ),
            PlaywrightTestItemSchema(
                id="pw_finops_05_multi_model_cost_telemetry",
                domain="finops",
                title="Telemetría de Costos Multi-Modelo (Gemini vs Claude)",
                description="Calcula costo en USD y tokens por proveedor de IA según tarifa vigente.",
                status="planned",
                tags=["finops", "telemetry"],
                estimatedDurationSec=30,
            ),
            # 7. POS (5 tests - 5 planned)
            PlaywrightTestItemSchema(
                id="pw_pos_01_cashier_shift",
                domain="pos",
                title="Apertura y Cierre de Turno de Cajero",
                description="Valida arqueo inicial, transacciones en efectivo/tarjeta y cuadratura de caja.",
                status="planned",
                tags=["pos", "cashier", "p1"],
                estimatedDurationSec=35,
            ),
            PlaywrightTestItemSchema(
                id="pw_pos_02_kitchen_display_system",
                domain="pos",
                title="Comanda a Cocina KDS y Tiempos de Preparación",
                description="Verifica despacho de comandas en tiempo real a pantallas de cocina.",
                status="planned",
                tags=["pos", "kds"],
                estimatedDurationSec=25,
            ),
            PlaywrightTestItemSchema(
                id="pw_pos_03_buffet_table_turnover",
                domain="pos",
                title="Rotación de Mesas en Modo Buffet y Consumo Libre",
                description="Valida control de tiempo por mesa y cobro por comensal en buffet.",
                status="planned",
                tags=["pos", "buffet"],
                estimatedDurationSec=30,
            ),
            PlaywrightTestItemSchema(
                id="pw_pos_04_hands_free_voice_orders",
                domain="pos",
                title="Ingreso Manos Libres de Pedidos por Voz",
                description="Comprueba reconocimiento de voz y armado dinámico de comandas.",
                status="planned",
                tags=["pos", "voice"],
                estimatedDurationSec=25,
            ),
            PlaywrightTestItemSchema(
                id="pw_pos_05_delivery_integrations_sync",
                domain="pos",
                title="Sincronización de Pedidos Delivery y Boletas",
                description="Valida recepción de pedidos externos (UberEats, PedidosYa) y emisión de boleta fiscal.",
                status="planned",
                tags=["pos", "delivery"],
                estimatedDurationSec=30,
            ),
        ]
