# Sub-Plan 3 — Etapa 2: Construcción Backend
## Consola Dinámica y Extensible de Tests Playwright en Platform Admin Sandbox

- **Agente Responsable:** Agente 04: Desarrollador Backend Senior (`04-backend-senior-dev`)
- **Fecha UTC:** 2026-11-06T00:15:00Z
- **Hito:** Sub-Plan 3 — Etapa 2 (Construcción Backend completada con 100% pruebas pasando)
- **Destinatarios:**
  - Orquestador General (`parent`)
  - Agente 05: Frontend Senior Dev (`05-frontend-senior-dev`)
  - Agente 13: Especialista en Navegador Real Playwright (`13-browser-e2e-playwright`)
  - Agente 09: QA Parity & Test Engineer (`09-qa-parity-and-test-engineer`)
  - Agente 10: Cybersecurity Red Team (`10-cybersecurity-redteam-auditor`)

---

### 1. Resumen Ejecutivo de Implementación

En cumplimiento de las especificaciones de arquitectura (`subplan3_etapa1_playwright_architecture_spec.md`) y la certificación de impacto cero en base de datos (`subplan3_etapa1_database_signoff.md`), se ha implementado el backend completo para la Consola Dinámica y Extensible de Playwright:

1. **Modelos Pydantic v2 en `schemas_sandbox.py`:**
   - `PlaywrightTestItemSchema`, `PlaywrightCatalogSummarySchema`, `PlaywrightDomainGroupSchema`, `PlaywrightCatalogResponseSchema`, `PlaywrightRunRequestSchema`, `PlaywrightRunTriggerResponseSchema`, `PlaywrightStreamStepEventSchema`.
   - Soporte estricto de serialización camelCase/snake_case con `extra="forbid"` y `populate_by_name=True`.
   - Zero `any`, validado 100% por `mypy` sin advertencias.

2. **Lógica de Catálogo Dinámico y Streaming en `sandbox_service.py`:**
   - 38 casos de prueba canónicos estructurados bajo los 7 dominios oficiales de negocio: `tenancy`, `auth_rbac`, `inventory`, `recipes`, `procurement`, `finops`, `pos`.
   - Estado inicial reflejando la realidad actual del proyecto (~5% de cobertura real):
     * Pruebas `ready` (2): `pw_tenancy_01_holding_creation` (Onboarding Holding & LegalEntity), `pw_auth_01_login_rbac_guard` (Login & Anti-IDOR RBAC 3-niveles).
     * Pruebas `in_progress` (2): `pw_inventory_01_fefo_alerts` (Alertas FEFO), `pw_finops_01_token_discount` (Descuento atómico tokens OppyFy).
     * Pruebas `planned` (34): ej. `pw_recipes_01_costing_ppp` (Cálculo PPP), `pw_procurement_01_dte_invoice` (DTE 33 Factura SII), `pw_pos_01_cashier_shift` (Apertura y Cierre POS).
   - Invariantes matemáticas cumplidas estrictamente:
     $$\text{Total} = 38 = \text{Ready (2)} + \text{InProgress (2)} + \text{Planned (34)}$$
     $$\text{CoveragePercentage} = \operatorname{round}\left(\frac{2}{38} \times 100, 1\right) = 5.3\%$$
   - Método `get_catalog()` con cálculo dinámico de resumen y desglose por dominio.
   - Método `trigger_run(request)` que encola corridas por `scope` (`domain`, `test`, `all`) y retorna `run_id` y `testsQueued`.
   - Generador asíncrono `stream_run_events(run_id)` bajo RFC 8895 Server-Sent Events (SSE) con eventos `step` y `completed`, screenshots y respeto del parámetro `slowMoMs`.

3. **Endpoints REST y SSE en `sandbox_router.py`:**
   - `GET /api/v1/platform-admin/sandbox/playwright/catalog` protegido por `RequireGlobalPermission(permission="platform_admin.sandbox.access")`.
   - `POST /api/v1/platform-admin/sandbox/playwright/run` protegido por `RequireGlobalPermission(permission="platform_admin.sandbox.manage")` con HTTP 202 Accepted.
   - `GET /api/v1/platform-admin/sandbox/playwright/stream/{run_id}` con `StreamingResponse(media_type="text/event-stream")` protegido por `RequireGlobalPermission(permission="platform_admin.sandbox.access")`.
   - Guardrails Fail-Fast preservados: bloqueo en `production` sin confirmación explícita (`confirmProductionRun=true` o `X-Sandbox-Confirm-Production: true`).

4. **Co-creación 1:1 de Pruebas Unitarias e Integración en `test_platform_admin_sandbox.py`:**
   - Nuevos casos: `test_get_playwright_catalog_success`, `test_playwright_catalog_rbac_denials`, `test_trigger_playwright_run_scopes`, `test_trigger_playwright_run_production_guardrail`, `test_stream_playwright_run_events_sse`, `test_stream_playwright_run_rbac_denials`, `test_playwright_schemas_bidirectional_and_strict_validation`.
   - Resultado: **30/30 tests pasados al 100%** (46/46 consolidado de sandbox).
   - Mypy: **0 errores**.

---

### 2. Evidencias de Verificación Automatizada

```bash
# Tests unitarios de sandbox:
oppytec-backend/.venv/bin/pytest oppytec-backend/tests/unit/test_platform_admin_sandbox.py oppytec-backend/tests/unit/test_sandbox_observability_and_environments.py -v
# Salida: 46 passed in 2.99s (100% verde)

# Mypy Typecheck:
oppytec-backend/.venv/bin/mypy oppytec-backend/src/modules/tenancy/presentation/schemas_sandbox.py oppytec-backend/src/modules/tenancy/application/sandbox_service.py oppytec-backend/src/modules/tenancy/presentation/sandbox_router.py
# Salida: Success: no issues found in 3 source files

# Integridad de Alembic:
oppytec-backend/.venv/bin/pytest oppytec-backend/tests/architecture/test_alembic_integrity.py
# Salida: 2 passed in 0.16s
```
