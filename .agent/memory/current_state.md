# Estado Actual de la Refactorización — OppyTec v2.0

- **Fase Activa:** `Fase 1 Completada y Certificada -> Listo para iniciar Fase 2 (Base de Datos Multi-Schema, Migraciones Correlativas Alembic 0001..N, Bootstrap Génesis y Respaldos 4-Capas)`
- **Estado del Escuadrón de 12 Agentes:** Operativo (`.agent/subagents/01..12-*/` con handovers actualizados tras Fase 1)
- **Estado de Reglas Inmutables:** `.agent/rules/00..22-*.md` activas (23 reglas inmutables)
- **Estado de Evaluaciones Anti-Trampa:** `.agent/evals/rubric_10_criteria.yaml` sellado con `SHA-256` (`verify-evals` 100% OK)
- **Estado de Quality Gate (`make fast-gate`):** `36 passed` (`tests/unit/`, `tests/architecture/`, `tests/smoke/`), `ruff check` 0 errores, `mypy --strict` 0 errores en 28 archivos (`< 3s`)

## Checklist Paso 0 (Gobernanza Base y Arnés RLM)
- [x] `AGENTS.md` y `.graphifyignore` en la raíz del proyecto
- [x] `.agent/rules/00..22-*.md` (23 reglas inmutables)
- [x] `.agent/evals/rubric_10_criteria.yaml` y `eval_hashes.sha256`
- [x] `.agent/subagents/01..12-*/` con `prompt.md`, `knowledge.md` y `handovers/latest_handover.md`
- [x] `.agent/skills/` con paquetes ejecutables en Python (`git_smart_merge`, `graphify`, `jev-decision-engine`, `i18n_manager`, etc.)
- [x] `scripts/harness.py` operativo
- [x] Bóvedas `specs/business-domain/` y `specs/engineering-code/` + `docs/adr/` inicializadas

## Checklist Fase 1 (Setup, 5 Entornos, Observabilidad 4-Pilares, Quality Gates y Andamiaje)
- [x] `docker-compose.yml` (`postgres` 16 + `pgvector`, `redis` 7, `mailpit`, `backend`, `frontend` + `--profile observability` con `otel-lgtm`, `glitchtip`, `umami`)
- [x] `Makefile` (`fast-gate`, `main-gate`, `deep-gate`, `check`, `smart-merge`, `migration-rebase`, `verify-evals`, `up`, `up-obs`, `down`)
- [x] `.pre-commit-config.yaml` (`gitleaks`, `ruff`, `mypy`, `eslint`, `tsc`, `verify-evals`)
- [x] `oppytec-backend/` (`Dockerfile`, `pyproject.toml`, `uv.lock`, `.env.example`, `src/main.py`, `src/core/config.py` *Fail-Fast* `SecretStr`, `src/core/observability.py` `X-Trace-ID` + redactor PII)
- [x] `oppytec-backend/tests/` (`conftest.py`, `tests/unit/test_config_and_observability.py`, `tests/smoke/test_system_boot_and_health.py` y los 16 tests de Caja Blanca en `tests/architecture/test_*.py`)
- [x] `oppytec-frontend/` (`Dockerfile`, `docker-entrypoint.sh` para `/runtime-env.js`, `package.json`, `tsconfig.json` strict, `tailwind.config.ts` con los 3 temas `light`/`dark`/`ocean-blue`, `src/shared/config/env.ts` Zod y `src/shared/telemetry/{otel,sentry,umami}.ts` + tests)
- [x] `docs/adr/ADR-001` al `ADR-021` + Mapa 5 del Atlas de Archify (`docs/architecture/atlas/05-environments-and-agentic-harness.archify.html`) + Bitácora Fase 1 (`docs/bitacora/diario-escuadron/01-Fase-1-Setup-Entornos-Observabilidad-y-Andamiaje.md`)
