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


