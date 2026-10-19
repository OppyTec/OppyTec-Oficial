# Estado Actual de la Refactorización — OppyTec v2.0

- **Fase Activa:** `Fase 2 Completada y Certificada -> Listo para iniciar Fase 3 (Servicios Core Clean Architecture, RBAC Dual, JEV, OppyFy, i18n, FX, R2 Quotas y WebSockets)`
- **Estado del Escuadrón de 12 Agentes:** Operativo (`.agent/subagents/01..12-*/` con handovers actualizados tras Fase 2)
- **Estado de Reglas Inmutables:** `.agent/rules/00..22-*.md` activas (23 reglas inmutables)
- **Estado de Evaluaciones Anti-Trampa:** `.agent/evals/rubric_10_criteria.yaml` sellado con `SHA-256` (`verify-evals` 100% OK)
- **Estado de Quality Gate (`make fast-gate`):** `52 passed` (`tests/unit/`, `tests/architecture/`, `tests/smoke/`), `ruff check` 0 errores, `mypy --strict` 0 errores en 84 archivos (`< 3s`), `make migration-rebase` (`Alembic correlative migration chain verified OK`)

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
