# Estado Actual de la Refactorización — OppyTec v2.0

- **Fase Activa:** `Fase 4 Completada y Certificada (SECURITY_APPROVED) -> Listo para iniciar Fase 5 (UI React 19 Mobile-First con ADN Visual Legacy 3 Temas, i18n, FX, OppyFy y Centro de Observabilidad)`
- **Estado del Escuadrón de 12 Agentes:** Operativo (`.agent/subagents/01..12-*/` con handovers actualizados tras Fase 4)
- **Estado de Reglas Inmutables:** `.agent/rules/00..22-*.md` activas (23 reglas inmutables)
- **Estado de Evaluaciones Anti-Trampa:** `.agent/evals/rubric_10_criteria.yaml` sellado con `SHA-256` (`verify-evals` 100% OK)
- **Estado de Quality Gate (`make fast-gate` + Suite Completa):** `91 passed` en `fast-gate` (`< 3s`), **`163 passed`** en la suite total (`unit`, `architecture`, `smoke`, `integration`, `security_redteam`, `contracts`), `ruff check` 0 errores, `mypy --strict` 0 errores en 222 archivos, `make migration-rebase` (`Alembic correlative migration chain verified OK`)

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
- [x] Suite de pruebas unitarias y de propiedades matemáticas (Hypothesis) pasando al 100% en `fast-gate`.

## Checklist Fase 4 (Endpoints API REST, Guardias RBAC de 3 Niveles, Suite de Integración y Red Team)
- [x] Guardias deterministas HTTP en `oppytec-backend/src/core/guards/`: `rbac_dependencies.py` (`RequireGlobalPermission`, `RequireTenantPermission`, `AuthenticatedPrincipal`), `file_magic_guard.py` (Magic Bytes, anti-Zip Bomb, anti-Excel DDE/formula injection), `xss_sanitizer.py` (anti-XSS/SSTI/SQLi/LFI/null-byte) y `rate_limiter.py` (`SlidingWindowRateLimiter` con perfiles `auth`, `api`, `ai` y `Retry-After`).
- [x] Capas `presentation/` (`__init__.py`, `schemas.py` con `ConfigDict(extra="forbid")` y `Decimal`, y `router.py` con RBAC de 3 niveles) para los 10 módulos (`identity`, `tenancy`, `audit`, `catalog`, `inventory`, `recipes`, `procurement`, `operations`, `analytics`, `oppy_ai`) montadas en `src/main.py` junto a `realtime_router` y manejadores RFC 7807.
- [x] Suite de Integración y Paridad Matemática Legacy (`oppytec-backend/tests/integration/`): `test_multi_tenant_schema_isolation.py`, `test_soft_delete_and_redis_killswitch.py`, `test_cross_tenant_holding_access.py` y `modules/test_api_modules_and_legacy_parity.py`.
- [x] Suite Ofensiva Red Team de 11 Vectores (`oppytec-backend/tests/security_redteam/test_01..11_*.py`) + Contrato/Fuzzing OpenAPI (`oppytec-backend/tests/contracts/test_openapi_schemathesis.py`) certificada con el sello `SECURITY_APPROVED` por el Agente 10.
- [x] Mapa 4 del Atlas de Archify (`docs/architecture/atlas/04-critical-runtime-flows-and-resilience.archify.html`) + Recibos `SHA-256` + Snapshot `v2_phase4_api_and_security_graph.json` + Bitácora Fase 4 (`docs/bitacora/diario-escuadron/04-Fase-4-Endpoints-API-Guardias-RBAC-y-Red-Team.md`).
