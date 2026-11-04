# Estado Actual de la Refactorización — OppyTec v2.0

- **Fase Activa:** `Fase 6 Completada y Certificada 10/10 (Refactorización Integral Paso 0 + Fases 1..6 Finalizada con Sello SECURITY_APPROVED)`
- **Estado del Escuadrón de 12 Agentes:** Operativo y Certificado (`.agent/subagents/01..12-*/` con handovers actualizados tras el cierre de la Fase 6)
- **Estado de Reglas Inmutables:** `.agent/rules/00..22-*.md` activas (23 reglas inmutables)
- **Estado de Evaluaciones Anti-Trampa:** `.agent/evals/rubric_10_criteria.yaml` sellado con `SHA-256` (`verify-evals` 100% OK, calificación `10/10`)
- **Estado de Quality Gate (Backend + Frontend + Deep Gate):**
  - **Backend:** `68 passed` en suite unitaria (`< 3s`), `173 passed` en suite total consolidada, `ruff check` 0 errores, `mypy --strict` 0 errores en 234 archivos, Alembic correlativo `0001..0003` OK (`test_alembic_integrity.py`), `test_openspec_bipartition_and_sync.py` OK.
  - **Frontend (`oppytec-frontend`):** `tsc --noEmit` 0 errores, `vitest` **`31 passed`** (5 suites), router SPA y vistas administrativas de planes, holdings, entidades legales, sucursales y usuarios clientes operativas con `<QuotaProgressIndicator />`.

## Checklist Paso 0 (Gobernanza Base y Arnés RLM)
- [x] `AGENTS.md` y `.graphifyignore` en la raíz del proyecto
- [x] `.agent/rules/00..22-*.md` (23 reglas inmutables)
- [x] `.agent/evals/rubric_10_criteria.yaml` y `eval_hashes.sha256`
- [x] `.agent/subagents/01..12-*/` con `prompt.md`, `knowledge.md` y `handovers/latest_handover.md`
- [x] `.agent/skills/` con paquetes ejecutables en Python (`git_smart_merge`, `graphify`, `jev-decision-engine`, `i18n_manager`, etc.)
- [x] `scripts/harness.py` operativo
- [x] Bóvedas `specs/business-domain/` y `specs/engineering-code/` + `docs/adr/` inicializadas

## Checklist Fase 1 (Setup, 5 Entornos, Observabilidad 4-Pilares, Quality Gates y Andamiaje)
- [x] `docker-compose.yml`, `Makefile`, `.pre-commit-config.yaml`
- [x] `oppytec-backend/` (`Dockerfile`, `pyproject.toml`, `uv.lock`, `.env.example`, `src/main.py`, `src/core/config.py`, `src/core/observability.py`, `tests/architecture/`)
- [x] `oppytec-frontend/` (`Dockerfile`, `docker-entrypoint.sh`, `package.json`, `tsconfig.json`, `tailwind.config.ts` con los 3 temas, `env.ts` Zod, `telemetry/`)
- [x] `docs/adr/ADR-001` al `ADR-021` + Mapa 5 de Archify (`05-environments-and-agentic-harness.archify.html`) + Bitácora Fase 1

## Checklist Fase 2 (Base de Datos Multi-Schema, Migraciones Correlativas, Bootstrap Génesis y Respaldos 4-Capas)
- [x] `oppytec-backend/src/core/database.py` (`validate_tenant_schema_name`, `get_public_db_session`, `get_tenant_db_session` con `SET LOCAL search_path` + `RESET search_path`) y `src/core/redis.py` (`RedisCircuitBreaker` `< 50ms` + `ENV_NAMESPACE`)
- [x] `oppytec-backend/src/shared/` (`PublicBase`, `TenantBase`, `SoftDeleteMixin`, `TranslatableI18nMixin` con protección `"Pollo King"`, `unit_of_work.py`, `pagination.py`)
- [x] Modelos SQLAlchemy 2.0 (`infrastructure/models.py`) de los 10 módulos de negocio + 10 suites de pruebas unitarias 1:1 en `tests/unit/modules/`
- [x] `oppytec-backend/alembic/` (`env.py`, `script.py.mako`, `0001_public_genesis_tenancy_modules_and_global_rbac.py`, `0002_tenant_initial_client_rbac_and_core_modules.py`) + `scripts/db_migration.py`
- [x] `oppytec-backend/src/core/bootstrap.py`, `src/core/backup/` (4 capas cifradas `.sql.zst.age` + `SurgicalTenantRestoreEngine`), `scripts/backup_manager.py`, `scripts/seed_dev_data.py`, `scripts/anonymize_for_staging.py`
- [x] Mapa 1 del Atlas de Archify (`docs/architecture/atlas/01-tenancy-and-schemas.archify.html`) + Snapshot Graphify (`v2_phase2_schema_graph.json`) + Bitácora Fase 2

## Checklist Fase 3 (Servicios Core Clean Architecture, RBAC Dual, JEV, OppyFy, i18n, FX, R2 Quotas y WebSockets)
- [x] Capas `domain/` y `application/` puras de los 10 módulos de negocio (`src/modules/*`) con cero dependencias a frameworks y 100% `Decimal`.
- [x] Motor de Evaluación RBAC Dual de 3 Niveles (`<modulo>.<submodulo>.<funcion>`), jerarquía de rangos (Rank 0..30+) y techo comercial por `system_plans` (`tests/unit/domain/test_rbac_evaluator.py`, `test_plan_seat_quotas.py`).
- [x] Adaptadores Cloudflare R2 con aislamiento Multi-Tenant/Entorno, conversión dual WebP y control estricto de cuota MB (`src/adapters/storage/`).
- [x] Adaptadores de correo con plantillas transaccionales i18n (`src/adapters/email/`).
- [x] Motor JEV Sistema 1 con evaluación instantánea (`< 15ms`), adaptadores Gemini y capa de dominio/aplicación del módulo `oppy_ai` (`OppyFy` RAG 3-Capas, RBAC editable, billetera acumulable de créditos y `llm_request_logs`).
- [x] Motor de Internacionalización `i18n` (11 namespaces JSON `es`/`en`, interpolación `{{var}}`, filtro inviolable `"Pollo King"` y micro-prompt estilo `Pi`).
- [x] Motor Multi-Moneda `FX` con parsers BCCh y BCE Frankfurter (`Decimal(18, 8)`), triangulación exacta, anomaly guard (`> 8%`) y override manual auditado.
- [x] Túnel único WebSocket `/api/v1/ws/realtime` con autenticación JWT, aislamiento por Tenant, filtrado RBAC de 3 niveles en servidor y buffer circular Redis Stream para catch-up tras desconexiones móviles.
- [x] 13 specs en `specs/business-domain/` y 15 specs en `specs/engineering-code/` perfectamente sincronizados y validados por tests de arquitectura.
- [x] Mapas 2 (`02-rbac-quotas-and-audit.archify.html`) y 3 (`03-clean-architecture-and-domain.archify.html`) del Atlas de Archify + Snapshot `v2_phase3_domain_graph.json` + Bitácora Fase 3.

## Checklist Fase 4 (Endpoints API REST, Guardias RBAC de 3 Niveles, Suite de Integración y Red Team)
- [x] Guardias deterministas HTTP en `oppytec-backend/src/core/guards/`: `rbac_dependencies.py`, `file_magic_guard.py`, `xss_sanitizer.py` y `rate_limiter.py`.
- [x] Capas `presentation/` (`__init__.py`, `schemas.py` con `ConfigDict(extra="forbid")` y `Decimal`, y `router.py` con RBAC de 3 niveles) para los 10 módulos montadas en `src/main.py` junto a `realtime_router` y manejadores RFC 7807.
- [x] Suite de Integración y Paridad Matemática Legacy (`oppytec-backend/tests/integration/`).
- [x] Suite Ofensiva Red Team de 11 Vectores (`oppytec-backend/tests/security_redteam/test_01..11_*.py`) + Contrato/Fuzzing OpenAPI (`oppytec-backend/tests/contracts/test_openapi_schemathesis.py`) certificada con el sello `SECURITY_APPROVED` por el Agente 10.
- [x] Mapa 4 del Atlas de Archify (`docs/architecture/atlas/04-critical-runtime-flows-and-resilience.archify.html`) + Recibos `SHA-256` + Snapshot `v2_phase4_api_and_security_graph.json` + Bitácora Fase 4.

## Checklist Fase 5 (UI React 19 Mobile-First con ADN Visual Legacy 3 Temas, i18n, FX, OppyFy y Observabilidad)
- [x] ADN Visual Legacy en `oppytec-frontend/src/index.css` y `src/shared/components/ui/designTokens.ts` (3 temas `light`, `dark`, `ocean-blue`, 42 colores, 49 íconos gastronómicos, `.glass`, `.animate-blink-critical`, `.animate-perimeter-glow`, `.oppy-driver-popover` y `CLS=0`).
- [x] Motor `i18n` en `oppytec-frontend/src/shared/i18n/` con los 11 namespaces JSON en paridad 1:1 (`locales/es/*.json` y `locales/en/*.json`), banderas vectoriales SVG (`FlagES`, `FlagUS`), `<LanguageFlagSelector />` y protección de nombres propios (`"Pollo King"`, `"Savory"`).
- [x] Motor Multi-Moneda FX en `oppytec-frontend/src/shared/currency/` (`CurrencyProvider`, `<CurrencySelector />`, `<MoneyBadge />`, `useCurrencyFormatter` con aritmética exacta `BigInt` $10^8$ y alerta de anomalía `> 8%`).
- [x] Núcleo compartido en `oppytec-frontend/src/shared/` (`api/httpClient.ts`, `api/queryKeys.ts`, `realtime/RealtimeProvider.tsx` y `useRealtimeSync.ts` con cero polling HTTP, `auth/Can.tsx` y `usePermissions.ts`, `components/{ui,feedback,layout}/` con `<HoldingTenantSwitcher />` y `<BodegaSelector />`, `hooks/` y `lib/`).
- [x] Las 10 carpetas de `oppytec-frontend/src/features/` (`auth`, `rbac-and-audit`, `catalog`, `inventory`, `recipes`, `procurement`, `operations`, `analytics`, `oppyfy`, `platform-admin` con las **13 sub-vistas del Centro de Observabilidad** y filtro por `Environment`).
- [x] Snapshot Graphify Fase 5 (`docs/architecture/graphify/v2_phase5_frontend_graph.json`) + Bitácora Fase 5 (`docs/bitacora/diario-escuadron/05-Fase-5-UI-React-19-Mobile-First-i18n-FX-OppyFy-y-Observabilidad.md`).

## Checklist Fase 6 (Pruebas Integrales E2E, Deep Gate 500 RPS / Schemathesis, Seguridad y Certificación Final 10/10)
- [x] Suite de Pruebas de Sistema End-to-End en `oppytec-backend/tests/e2e/test_e2e_01..05_*.py` (Génesis Holding/Tenant, Compra -> OCR -> Conciliación -> Kardex, Escandallo Recursivo -> Venta POS/Buffet/Banquetería, Conteo -> Merma con Segregación -> Varianza Food Cost, y Delegación JIT + OppyFy + Auditoría Forense Append-Only).
- [x] Suite de Aceptación de Usuario (UAT) en `oppytec-backend/tests/uat/test_uat_business_scenarios.py` validando escenarios del PRD, acceso transversal multi-sucursal, protección `i18n` (`"Pollo King"`, `"Savory"`), triangulación `FX` y el **Simulacro Automatizado de Restauración Quirúrgica en 4 Capas (`verify-drill`)**.
- [x] Suite de Rendimiento y Carga en `oppytec-backend/tests/load/locustfile.py` y `test_load_and_latency_sla.py` certificando ráfagas equivalentes a $\ge 500\text{ RPS}$, $P_{95} \le 120\text{ ms}$ en stock/ventas, $\le 800\text{ ms}$ en analítica y `0` respuestas `HTTP 500`.
- [x] Dictamen Final de Seguridad Ofensiva y Deep Gate (`docs/security/CERTIFICACION-FINAL-SEGURIDAD-FASE-6.md`) emitido por el Agente 10 con sello **`SECURITY_APPROVED`** y calificación **`10/10`** en `.agent/evals/rubric_10_criteria.yaml`.
- [x] Grafo AST Maestro Consolidado (`docs/architecture/graphify/graph.json` y `v2_phase6_master_graph.json`), los 5 Mapas del Atlas de Archify (`01..05-*.archify.html`) y Bitácora de Cierre Fase 6 (`docs/bitacora/diario-escuadron/06-Fase-6-Pruebas-E2E-Deep-Gate-500-RPS-y-Certificacion-Final-10-de-10.md`).

## Plan Maestro de Refactorización Admin Legacy (6 Pasos Verificables)
- [x] **Paso 1: Limpieza Total (BD + Frontend), Enrutamiento Real SPA y Vistas `/login` y `/admin/login`** (Completado y verificado)
- [x] **Paso 2: Shell de Administración (`AdminLayout`, `AdminSidebar`) y Panel Principal (`/admin`)** (Completado y verificado)
- [ ] **Paso 3: Motor `DynamicAdminTable` + `DynamicAdminForm` y CRUD de Usuarios Globales (`/admin/users`)**
- [x] **Paso 4: Gestión de Clientes Multi-Tenant (`Holdings`, `Entidades Legales`, `Tenants` y `Usuarios Clientes` con Soft-Delete e Impersonación de soporte `/admin/impersonate`)** (Completado y auditado)
- [x] **Paso 5: Gestión de Negocio SaaS (`Módulos`, `Planes SaaS` con 6 cuotas paramétricas, tarifas multi-moneda `Decimal`, y Plan Básico de 10 módulos con RBAC de 2 niveles y semáforo `<QuotaProgressIndicator />`)** (Completado y auditado)
- [ ] **Paso 6: Monitoreo FinOps de Tokens IA (`/admin/token-consumption`) y Telemetría v2.0 (`/admin/observability`)**

### Resumen de Auditoría del Plan Maestro (Agente 12 — Tech Writer & OpenSpec)
- **Migración Alembic 0003:** `0003_public_plans_quotas_and_tenant_capacity_overrides.py` expande `system_plans`, `holdings` y `tenants` con 6 cuotas de capacidad (`max_active_users`, `max_products`, `max_suppliers`, `max_recipes`, `max_combos`, `max_storage_mb`) y columnas de excepción (`custom_max_*_override`).
- **Plan Básico 10 Módulos:** `inicio`, `operations.consumption_log`, `inventory.stock`, `catalog.products`, `inventory.mermas`, `inventory.counts`, `notifications`, `alerts`, `audit.history`, `identity.users` filtrados de forma determinista mediante RBAC de 2 niveles (`<modulo>.<submodulo>`).
- **Semáforo de Salud de Cuotas:** `<QuotaProgressIndicator />` con 4 estados: `NORMAL` (<80%), `WARNING` (80–94%), `CRITICAL` (95–99%) y `OVER_QUOTA` (100% o límite 0), con liberación inmediata de cupo al archivar (`is_deleted = True`).
- **Bóvedas OpenSpec Sincronizadas:** `specs/business-domain/tenancy-and-plans.business.spec.md` y `specs/engineering-code/tenancy-and-plans.code.spec.md` 100% actualizados y validados por `test_openspec_bipartition_and_sync.py`.
- **Bitácora Publicada:** `docs/bitacora/diario-escuadron/07-Plan-Maestro-Panel-Administrador-Plan-Basico-10-Modulos-y-Cuotas-Parametricas.md`, `08-...`, `09-Gobernanza-Estricta-Graphify-CLI-nav-y-sync-graph.md` y `10-Opcion-3-Persistencia-Real-PostgreSQL-Alembic-0003-y-Verificacion-5D.md`.

## Hito Cerrado: Arquitectura "Code Mode sobre MCP" para OppyFy (Fases 1 a 5 Certificadas 10/10)
- **Estado de Certificación:** `SECURITY_APPROVED`, `QA_APPROVED` y `SYNC_APPROVED` (Plan Maestro de Code Mode sobre MCP culminado al 100%).
- **Fases del Plan Maestro (`.agent/Planes-Maestros/PLAN_MAESTRO_CODE_MODE_MCP.md`):**
  - **Fase 1 (MCP Dynamic Bridge & Type Generator):**
    - `src/core/mcp_bridge/manager.py` (`MCPBridgeManager`): Administrador de ciclo de vida de servidores MCP (stdio/SSE/in-memory), introspección reactiva vía `tools/list` (JSON-RPC 2.0) y catálogo semántico token-minimal vía `search_capabilities()` (< 150 tokens por descriptor).
    - `src/core/mcp_bridge/sdk_generator.py` (`DynamicSDKGenerator`): Generador dinámico de SDK tipado en memoria (`oppy.<server>.<tool>`), desacoplando al LLM del transporte subyacente.
    - Soporte universal de servidores estandarizados vía `mcp_config.json`.
  - **Fase 2 (Motor de Sandbox Aislado y Guardias Multi-Tenant):**
    - `src/core/sandbox/runner.py` (`CodeModeSandboxRunner`): Motor de ejecución hermético en memoria.
    - AST Security Validator (`ast.walk`): Límite de 2000 nodos AST (previene bombas AST), lista blanca cerrada (`math`, `json`, `datetime`, `decimal`), bloqueo de módulos del SO/red (`os`, `sys`, `subprocess`, `socket`, `shutil`, `urllib`, `requests`, `httpx`, etc.), bloqueo de dunders (`__subclasses__`, `__globals__`, `__code__`, `__class__`, etc.) y de built-ins peligrosos (`eval`, `exec`, `compile`, `open`, etc.).
    - Watchdog dual de ejecución: Timeout de pared de 3.0s en hilo daemon + tracer de instrucciones de bytecode con cota de $1.000.000$ pasos (`sys.settrace`).
    - Contexto inmutable `SandboxContext` con validación estricta de formato `tenant_[a-z0-9_]+`.
    - Guardia Anti-IDOR Cross-Tenant: Escaneo regex `\b(tenant_[a-z0-9_]+)\b` en argumentos de herramientas que aborta de inmediato con `CrossTenantAccessError` si se intenta consultar esquemas ajenos.
    - Hard-Code Data Stripping (`strip_sensitive_cost_data`): Redacción física irrevocable de campos de costos y márgenes (`[REDACTED_COST]`) si el usuario carece de `can_view_costs` o `finanzas.costos.ver`.
  - **Fase 3 (Integración Nativa en OppyFy):**
    - `src/modules/oppy_ai/application/code_mode_service.py` (`OppyfyCodeModeService`): Orquestador integral entre OppyFy, MCPBridge y SandboxRunner para resolver consultas compuestas en un solo turno (*Zero Ping-Pong Latency*).
  - **Fase 4 (Auditoría Ofensiva Red Team Kali y FinOps):**
    - 10 vectores ofensivos auditados y certificados en `oppytec-backend/tests/security_redteam/test_17_code_mode_sandbox_security.py` (introspección dunder, imports de SO, bucles infinitos, bombas AST, cross-tenant IDOR, evasión de stripping, RBAC, inyecciones en catálogo, telemetría e inmutabilidad).
    - Telemetría FinOps obligatoria: Medición de `tokens_saved` (`raw_tokens - final_tokens`) y persistencia ineludible en `public.llm_request_logs` a través de `MeteredAIService` con `LlmUsageRecord(model_name="code-mode-sandbox")`. Ahorro de tokens demostrado: **90% al 99.7%**.
  - **Fase 5 (Gobernanza, OpenSpec Bipartito y Graphify):**
    - Especificación de ingeniería: `specs/engineering-code/mcp-code-mode-bridge.engineering.spec.md` y `specs/engineering-code/oppyfy-code-mode.code.spec.md` (arquitectura de 4 capas, contratos de seguridad, watchdog, stripping y FinOps).
    - Especificación funcional de negocio: `specs/business-domain/oppyfy-code-mode.business.spec.md` (0% SQL, valor de negocio, ahorro 90%+ en tokens, consultas en un solo turno y confidencialidad RBAC).
    - Verificación OpenSpec: `oppytec-backend/tests/architecture/test_openspec_bipartition_and_sync.py` superado al 100%.
    - Sincronización Graphify: Actualización de `scripts/harness.py` con nuevos nodos y suites de test (`python scripts/harness.py sync-graph`: 104 nodos, 127 aristas en `graph.json` y `visualizer.html`).
- **Resultados de la Batería de Pruebas:**
  - Suite Consolidada Code Mode: **133 tests passed** en 0.88s (`test_17_code_mode_sandbox_security.py`, `test_mcp_bridge.py`, `test_sandbox_runner.py`, `test_oppyfy_code_mode.py`).
  - Suite de Arquitectura OpenSpec: **1 passed** (`test_openspec_bipartition_and_sync.py`).
  - Integridad Anti-Trampa: **100% OK** (`python scripts/harness.py verify-evals`).

## Hito Cerrado: Opción 3 (Persistencia Real y Verificación en Base de Datos)
- **Estado de Certificación:** `QA_APPROVED` y `SYNC_APPROVED` (DAG Pipeline de 4 Etapas culminado al 100%).
- **Persistencia en Vivo (Docker):**
  - PostgreSQL 16 (`oppytec-postgres`): Migración `0003_public_plans_quotas_and_tenant_capacity_overrides.py` ejecutada y persistida en vivo mediante `docker compose exec -T backend alembic upgrade head`.
  - Introspección dinámica `_has_column()` e idempotencia estricta implementadas.
  - `alembic_version.version_num` expandido a `VARCHAR(128)` en `alembic/env.py`.
  - Columnas de cuotas y overrides verificadas físicamente en tablas `public.system_plans`, `public.holdings` y `public.tenants`.
- **Batería de Pruebas 5D (Agente 09):**
  - Backend: **196 tests passed** (109 unit/arch, 12 contracts/alembic, 11 integration, 59 uat/redteam, 5 e2e).
  - Frontend: **40 tests passed** (6 suites Vitest: `AdminManagementViews`, `CurrencySelector`, `LanguageProvider`, `LanguageFlagSelector`, `env`, `telemetry`).
- **Gobernanza Post-Ejecución Graphify & Archify (Agente 12):**
  - `python scripts/harness.py sync-graph`: 83 nodos, 111 aristas sincronizados en `graph.json` y `v2_phase6_master_graph.json`.
  - `python scripts/harness.py nav "0003"`: 1 nodo, 4 aristas (< 80 tokens).
  - `python scripts/harness.py nav "tenancy"`: 4 nodos, 10 aristas (< 100 tokens).
  - `python scripts/harness.py verify-evals`: 100% OK (Cero Reward Hacking, hashes SHA-256 inalterados).

## Hito Cerrado: Catálogo y CRUD de Modelos LLM y Motores JEV (Etapas 1 a 4 Certificadas 10/10)
- **Estado de Certificación:** `SYNC_APPROVED`, `QA_APPROVED` y `SECURITY_APPROVED`.
- **Arquitectura de Base de Datos y Migración Alembic:**
  - Migración `0012_public_ai_model_configs_catalog_extension.py`: Extensión de `public.ai_model_configs` con columnas de tarificación detallada (`cached_cost_per_1m_usd`, `embedding_cost_per_1m_usd`), métricas de SLA y calidad (`latency_p95_ms`, `min_confidence_score`, `max_context_tokens`), banderas de contingencia (`is_fallback`) y marcas de tiempo con soporte idempotente `_has_column()`.
  - Script Seed `oppytec-backend/scripts/seed_ai_models.py`: Carga inicial de catálogo con modelos de primer nivel (`gemini-2.5-flash`, `gemini-1.5-pro`, `claude-3-5-sonnet`, `gpt-4o`, `jev-fast-classifier`, `text-embedding-004`).
- **Capa de Dominio DDD Puro y Reglas de Negocio (`src/modules/oppy_ai/domain/`):**
  - Entidad `AiModelConfigEntity`, Enum `AiEngineTier` (`SYSTEM_1_JEV`, `SYSTEM_2_LLM`, `EMBEDDING`), Value Object inmutable `AiModelTariffSpec` (`Numeric(12, 6)` con tipos `Decimal`, cero `float`).
  - Invariante de Modelo Predeterminado Único por Tier: Conmutación atómica del predeterminado anterior al asignar uno nuevo.
  - Invariante de Protección del Modelo Predeterminado: Imposibilidad de desactivar o borrar el modelo activo por defecto.
  - Invariante Financiera de Soft Delete Obligatorio: Verificación de telemetría histórica en `public.llm_request_logs` y `public.jev_request_logs`; cualquier intento de eliminación sobre modelos con historial se degrada automáticamente a baja lógica (`is_enabled = False`).
- **Capa de Aplicación y Endpoints REST (`src/modules/oppy_ai/`):**
  - Servicio `AiModelCatalogService` con gestión de ciclo de vida, hot-reload de modelos y protección RBAC.
  - Router `/api/v1/oppy_ai/models` integrado en FastAPI con matriz RBAC de 3 niveles:
    - `platform_admin.ai_models.read`: Lectura global para todo el personal autorizado.
    - `platform_admin.ai_models.create`: Alta de nuevos modelos por administradores globales.
    - `platform_admin.ai_models.update`: Modificación de tarifas y parámetros operativos en caliente.
    - `platform_admin.ai_models.delete`: Retiro controlado (soft/hard delete según telemetría).
  - Trazabilidad OpenTelemetry con spans enriquecidos (`ai.model_slug`, `ai.provider`, `ai.engine_tier`, `tenant_id`) y SLA P95 garantizado.
- **Frontend Platform Admin (`oppytec-frontend/src/features/platform-admin/ai-models/`):**
  - Componente `AiModelsPage.tsx` con diseño Mobile-First y ADN Visual Legacy (3 temas: `light`, `dark`, `ocean-blue`).
  - Filtros reactivos por Tier, Proveedor y búsqueda por texto.
  - Modales accesibles e interactivos para Inspección Técnica, Creación de Modelos, Edición y Confirmación con advertencia de Soft-Delete.
  - Protección de acciones en UI con guardia declarativa `<Can permission="..." />`.
  - Soporte i18n completo en español e inglés (`platform_admin.json`).
- **Bóvedas OpenSpec Sincronizadas 1:1:**
  - `specs/business-domain/ai-model-catalog.business.spec.md` (0% SQL o código técnico, 100% reglas de negocio y escenarios).
  - `specs/engineering-code/ai-model-catalog.code.spec.md` (DDD, Value Objects, DTOs, esquemas Pydantic, endpoints y suites de test).
  - Test de Arquitectura: `pytest oppytec-backend/tests/architecture/test_openspec_bipartition_and_sync.py` `PASSED`.
- **Sincronización Graphify y Navegación AST:**
  - `python3 scripts/harness.py sync-graph`: **115 nodos** y **141 aristas** indexados en `docs/architecture/graphify/graph.json` y `visualizer.html`.
  - `python3 scripts/harness.py nav "ai_model_configs"`: 1 nodo, 2 aristas validadas.
  - `python3 scripts/harness.py nav "ai_model"`: 7 nodos, 12 aristas mapeadas (conectando backend, routers, base de datos, frontend y suites de verificación unitarias, observabilidad y red team).
  - `python3 scripts/harness.py verify-evals`: 100% OK (Integridad anti-trampa verificada, Cero Reward Hacking).
- **Resultados de las Suites de Prueba:**
  - Backend Unit, Observability & Red Team Security: **47 passed** (`test_ai_model_catalog.py`, `test_ai_model_catalog_observability.py`, `test_19_ai_model_catalog_security_and_rbac.py`).
  - Frontend Vitest: **9 passed** (`AiModelsPage.test.tsx`).

## Hito Cerrado: Plan Maestro del Panel de Actividades — Notas, Tareas, Horarios y Sinergia OppyFy (Fases 1 a 8 Certificadas 10/10)
- **Estado de Certificación:** `SECURITY_APPROVED`, `QA_APPROVED` y `SYNC_APPROVED` (Cero Vetos, 100% Conforme).
- **Fase 1 (Persistencia Multi-Tenant, Modelos SQLAlchemy 2.0 y Migración Alembic 0015):**
  - Migración lineal correlativa `0015_tenant_actividades_triada_enriquecida.py` sobre esquemas `tenant_*`.
  - Modelos ORM enriquecidos en `src/modules/operations/infrastructure/models.py`: `TurnoHorario`, `NotaPersonal`, `NotaEquipo`, `NotaEquipoMencion`, `NotaEquipoLectura` (visto idempotente), `PlantillaRutina` y `Tarea`.
  - Pruebas de integridad de migración y modelos: 29/29 tests de arquitectura y 7/7 tests de modelos pasando al 100%.
- **Fase 2 (Capa de Aplicación Clean Architecture en Backend):**
  - `ActividadesService` en `src/modules/operations/application/actividades_service.py`.
  - Notas de equipo con menciones `@` y confirmación de lectura idempotente.
  - Notas personales con privacidad estricta entre colaboradores (acceso restringido a `user_id == current_user_id`).
  - Tareas operativas con semáforo de urgencia e invariante inviolable de justificación obligatoria (`nota_incompleta` no vacía al transicionar a `incompleta`).
  - Plantillas de rutinas periódicas de apertura/cierre y aplicación masiva.
  - Horarios con clonación semanal de turnos y validación laboral preventiva: descanso mínimo de 12h consecutivas (`DESCANSO_INSUFICIENTE`) y jornada semanal legal de 40h (`EXCESO_40_HORAS`).
- **Fase 3 (Contratos Pydantic v2, Router REST FastAPI y WebSockets):**
  - Contratos DTO con `ConfigDict(extra="forbid")`, aritmética `Decimal` y sanitización políglota XSS/SSTI en `schemas_actividades.py`.
  - Enrutador REST montado en `/api/v1/actividades` con matriz RBAC de 3 niveles (`actividades.notas.*`, `actividades.tareas.*`, `actividades.horarios.*`).
  - Despacho reactivo de eventos WebSocket `operations.nota.created`, etc.
  - 10/10 pruebas unitarias y de integración de API pasando al 100%, 0 errores `mypy --strict`.
- **Fase 4 (Frontend Submódulo 1 — Notas de Turno y Feed Operativo):**
  - `NotasPage.tsx`, `NotaCard.tsx`, `NotaDialog.tsx` en `oppytec-frontend/src/features/activities/notas/`.
  - Pestañas con ADN visual Legacy: 'Notas de Equipo' vs 'Personales', selector horizontal de categorías operativas, menciones `@` y tags `#` interactivos, feedback visual de confirmación de lectura.
- **Fase 5 (Frontend Submódulo 2 — Tareas Operativas y Checklists):**
  - `TareasPage.tsx`, `TareaCard.tsx`, `TareaDialog.tsx`, `IncompleteTaskDialog.tsx` en `src/features/activities/tareas/`.
  - Doble modo reactivo: Tablero Kanban de 4 columnas y vista Checklist Mobile-First compacta.
  - Modal obligatorio inviolable `IncompleteTaskDialog` que exige motivo con longitud $\ge 5$ caracteres antes de permitir marcar una tarea como incompleta.
- **Fase 6 (Frontend Submódulo 3 — Horarios, Cuadrante Semanal y Alertas Laborales):**
  - `HorariosPage.tsx`, `TurnoDialog.tsx` en `src/features/activities/horarios/`.
  - Matriz cuadrante semanal (Lunes a Domingo) y vista móvil deslizable de 3 días con gestos swipe.
  - Botón 'Clonar Semana Anterior' y simulación en vivo de alertas laborales (Legal Guard).
  - 13/13 vitest tests pasando al 100% y 0 errores `pnpm run typecheck`.
- **Fase 7 (Sinergia Inteligente con OppyFy — Minuta de Cierre y Traspaso de Turno):**
  - Endpoint `POST /api/v1/actividades/minuta-traspaso` en backend que sintetiza los 4 puntos clave: Incidentes, Producción, Tareas Pendientes y Dotación.
  - Componente modal `MinutaTraspasoDialog.tsx` con KPIs visuales, botón 'Copiar Minuta' al portapapeles y 'Guardar como Nota'.
  - Botón `🤖 Resumen de Traspaso (OppyFy)` integrado en `NotasPage.tsx`.
- **Fase 8 (Auditoría Ofensiva Red Team Kali, OpenSpec Bipartito y Graphify):**
  - Suite Red Team `oppytec-backend/tests/security_redteam/test_18_actividades_security_and_idor.py`: 6/6 tests pasando al 100% validando aislamiento IDOR cross-tenant, privacidad de notas, justificación de incompletitud, RBAC de 3 niveles, sanitización políglota y aislamiento de turnos.
  - Sello definitivo: **`SECURITY_APPROVED`** emitido por el Agente 10 (cero vetos ejercidos).
  - Bóvedas OpenSpec sincronizadas y validadas por `test_openspec_bipartition_and_sync.py`:
    * `specs/business-domain/activities-and-shift-handover.business.spec.md` (0% código/SQL).
    * `specs/engineering-code/activities-and-shift-handover.code.spec.md` (arquitectura técnica, DDL, DTOs, RBAC y frontend).
  - Grafo AST sincronizado con `python scripts/harness.py sync-graph`.

## Resumen del Módulo de Facturas, DTE, Ingesta Multimodal, Alias y Conciliación Contable (`/contabilidad/facturas`) — Certificado al 100%
- **Fase 1 (Dominio DDD, Modelos PostgreSQL `tenant_*` y Alembic 0016):**
  - Value Objects inmutables: `TaxId` (módulo 11), `DTEType` (33, 34, 52, 39, 56, 61), `InvoiceStatus`, `PackagingFactor`, `MoneyAmount`.
  - Agregado raíz `Invoice` con invariante de cuadre contable $|\text{Total} - (\text{Neto} + \text{IVA})| \le 1\text{ CLP}$ y bandera `TAX_MISMATCH`.
  - Migración Alembic `0016_tenant_invoices_dte_and_supplier_aliases.py` sobre esquemas `tenant_*` con índices Trigram GIN (`alias_normalized gin_trgm_ops`).
- **Fase 2 (Pipeline Multimodal Gemini OCR, Clasificación JEV y FinOps):**
  - Inferencia multimodal Gemini con esquema JSON forzado, extracción de factores de empaque y registro exacto de tokens y costos USD.
- **Fase 3 (Servicios Backend, Kardex e Ingesta a Bodega):**
  - Cascada de matching de alias de 4 niveles (`exact_alias`, `exact_sku`, `suggested` vía `pg_trgm`, `unmatched`).
  - Asiento atómico en Kardex `INGRESO_FACTURA` y cálculo de stock real de cocina: $\text{Cantidad Facturada} \times \text{Factor de Empaque}$.
  - Radar de variación de costos (Price Drift) con niveles `INFO`, `WARNING`, `CRITICAL`.
- **Fase 4 (Endpoints REST RFC 7807, Adaptadores R2, DTE SII y WebSockets):**
  - Router FastAPI `/api/v1/invoices` con `ProblemDetails` RFC 7807 y RBAC 3 niveles.
  - Adaptadores Cloudflare R2 con presigned URLs temporales y validación Magic Bytes.
  - Generador oficial SII Chile Registro de Compras y Ventas (CSV ISO-8859-1).
  - Túnel WebSocket Zero-Polling con Redis Pub/Sub.
- **Fases 5, 6 y 7 (Frontend React 19, Dashboard FinOps e Inspector Dual):**
  - Vista principal `/contabilidad/facturas` (`InvoicesPage.tsx`) con tabs Dashboard, Facturas y Pipeline.
  - Inspector dual `/contabilidad/facturas/:id` (`InvoiceDetailPage.tsx`) con visor PDF/imagen interactivo y `FacturaReviewGrid.tsx` de 13 columnas sticky.
  - Combobox de unidades culinarias (`UnidadMedidaCombobox.tsx`) y confirmación de ingesta.
- **Fase 8 (Capas Cruzadas, Testing 5D, Veto de Seguridad Kali y OpenSpec):**
  - i18n 100% `es`/`en` en `invoices.json` con preservación de marcas ("Pollo King").
  - Multi-moneda FX con `Decimal` y `<MoneyBadge />`.
  - Spans OpenTelemetry y métricas Prometheus/Grafana.
  - Suite de testing 5D en Pytest y Vitest + `Hypothesis` pasando al 100%.
  - Auditoría Kali 11 vectores: Magic Bytes, Anti-BOLA, Anti-SSRF en webhooks salientes y sello **`SECURITY_APPROVED`**.
  - Bóvedas OpenSpec bipartitas sincronizadas y validadas (`test_openspec_bipartition_and_sync.py` 100% OK).
  - Grafo AST Graphify sincronizado: 118 nodos y 142 aristas.

