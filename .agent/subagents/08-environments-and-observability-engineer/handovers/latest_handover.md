# Reporte de Traspaso (`Handover`) — Agente 08: Especialista en Observabilidad, Docker y Entornos

- **Fecha UTC:** 2026-11-07T01:13:30Z
- **Fase / Tarea:** Etapa 3 (ADR-022) — Auditoría de Telemetría OpenTelemetry, Guardrails de 5 Entornos, Reconstrucción Docker y Certificación Clean Slate en Vivo
- **Estado de Certificación:** `ADR022_CLEAN_SLATE_DOCKER_AND_OBSERVABILITY_CERTIFIED`

---

## 1. Completed (Auditoría OTel, Guardrails de 5 Entornos y Despliegue en Vivo)

1. **Gobernanza Pre-ejecución Obligatoria (Graphify):**
   - Ejecutado `python3 scripts/harness.py nav "observability"` (5 nodos / 9 aristas mapeadas).
   - Ejecutado `python3 scripts/harness.py nav "sandbox"` (21 nodos / 10 aristas mapeadas).
   - Reserva atómica AST registrada (`claim-ast`) para `oppytec-backend/Dockerfile` y `oppytec-backend/tests/unit/test_sandbox_observability_and_environments.py`.

2. **Auditoría e Instrumentación OpenTelemetry y Guardrails de 5 Entornos (`sandbox_router.py`):**
   - Verificado que `GET /api/v1/platform-admin/sandbox/mock-data/backup` emite su `trace_span("platform_admin_sandbox.mock_data.backup", tracer_name="oppytec.sandbox")` registrando `environment` y `mock_mode` (`X-OppyTec-Mock-Mode`).
   - Verificado que `POST /api/v1/platform-admin/sandbox/mock-data/reset` ejecuta en primera instancia `_enforce_sandbox_environment_guard(action_name="mock_data_reset", dry_run=False)` (bloqueo 403 en `production`, confirmación 400 en `staging`, aislamiento de esquema 400 en todos los entornos) y emite su `trace_span("platform_admin_sandbox.mock_data.reset")` propagando `X-Trace-ID`, `traceparent` y `X-OppyTec-Mock-Mode`.
   - Añadido test unitario `test_opentelemetry_and_mock_mode_propagation_on_mock_data_backup` en `oppytec-backend/tests/unit/test_sandbox_observability_and_environments.py` (26 passed / 0 failed).

3. **Actualización de Imagen Docker y Reconstrucción en Vivo (`docker compose up -d --build backend frontend`):**
   - Actualizado `oppytec-backend/Dockerfile` para incluir `COPY --chown=oppytec:oppytec fixtures ./fixtures` y `COPY --chown=oppytec:oppytec scripts ./scripts` dentro del contenedor runtime (`/app/fixtures/mock_data_backup.json` y `/app/scripts/clean_and_seed_genesis_db.py`).
   - Reconstruidos y recreados los contenedores `oppytec-backend` (`http://localhost:8000`, `healthy`) y `oppytec-frontend` (`http://localhost:5173`, `running`).

4. **Ejecución de `clean_and_seed_genesis_db.py` y Evidencias de Verificación en Vivo:**
   - Ejecutado `oppytec-backend/scripts/clean_and_seed_genesis_db.py` contra `oppytec-postgres`:
     * `purged_tables_count`: `21`
     * `holdings`: `0`, `legal_entities`: `0`, `tenants`: `0`, `client_users`: `0`
     * `global_users`: `1` (`OppyTec.Admin@gmail.com` / `oppytec.admin`)
     * `app_modules`: `7`, `global_roles`: `4`, `global_permissions`: `1`, `system_plans`: `3`, `ai_model_configs`: `6`, `saas_ai_policy_config`: `1`
   - **Verificación HTTP en Vivo contra `http://localhost:8000` y `http://localhost:5173`:**
     1) `POST http://localhost:8000/api/v1/auth/login` (`OppyTec.Admin@gmail.com` / `oppytec2026`) -> `200 OK` (JWT emitido).
     2) `GET http://localhost:8000/api/v1/tenancy/holdings` -> `200 OK` (`[]`).
     3) `GET http://localhost:8000/api/v1/tenancy/tenants` -> `200 OK` (`[]`).
     4) `GET http://localhost:8000/api/v1/tenancy/client-users` -> `200 OK` (`[]`).
     5) `GET http://localhost:8000/api/v1/tenancy/plans` -> `200 OK` (`['basic', 'starter', 'enterprise']`).
     6) `GET http://localhost:8000/api/v1/platform-admin/sandbox/mock-data/backup` -> `200 OK` (`X-Trace-ID` y `X-OppyTec-Mock-Mode: clean` preservados).
     7) `POST http://localhost:8000/api/v1/platform-admin/sandbox/mock-data/reset` (`targetPresetId: "clean-slate"`) -> `200 OK` (`X-Trace-ID` preservado, `presetRestored: "clean-slate"`).
     8) `GET http://localhost:5173/admin/sandbox/mock-data` -> `200 OK`.

5. **Post-ejecución Graphify (`sync-graph`):**
   - Ejecutado `python3 scripts/harness.py sync-graph` (151 nodos, 196 aristas sincronizadas).

---

## 2. Friction & Failures
- Se detectó preventivamente que `oppytec-backend/Dockerfile` solo copiaba `alembic`, `alembic.ini` y `src`, omitiendo `fixtures/` y `scripts/`. Se incorporó `COPY --chown=oppytec:oppytec fixtures ./fixtures` y `COPY --chown=oppytec:oppytec scripts ./scripts` antes de reconstruir la imagen para garantizar que `/api/v1/platform-admin/sandbox/mock-data/backup` y `restore_runtime_mock_stores` dispongan de `/app/fixtures/mock_data_backup.json` dentro del contenedor en vivo.

---

## 3. Next Exact Action
- Despachar reporte de certificación al Orquestador (`e2a1390c-b5aa-4770-893e-4f3d652ff3c0`) para habilitar la Etapa 4 (QA Parity, Red Team Security, Git Merge Arbiter y Tech Writer).
