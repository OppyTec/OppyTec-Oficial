# Certificación Formal de Aislamiento de Entornos y Observabilidad: Consola "Lab & QA Sandbox"

- **Documento**: `.agent/memory/subplan1_etapa3_environments_observability_signoff.md`
- **Autor**: Agente 08 (Ingeniero de Entornos y Observabilidad)
- **Fase**: Sub-Plan 1 / Etapa 3 — Auditoría de Blindaje de Entornos Canónicos y Trazabilidad OpenTelemetry
- **Fecha**: 2026-11-05
- **Estado**: **APROBADO & CERTIFICADO (100% CUMPLIDO)**

---

## 1. Resumen Ejecutivo de la Auditoría

Se auditó, blindó e instrumentó la consola **Lab & QA Sandbox** en el plano de backend (FastAPI) y frontend (React/TypeScript) de acuerdo con los estándares canónicos de OppyTec v2.0:

1. **Aislamiento Canónico de los 5 Entornos**: Blindaje fail-fast para `local`, `preview`, `ci`, `staging`, y `production`.
2. **Prevención de Contaminación de Datos (Anti-Data Contamination)**: Restricción estricta de esquemas multi-tenant en operaciones de escritura sintética.
3. **Observabilidad 4-Pilares & OpenTelemetry**: Instrumentación de correlación extremo a extremo con inyección de cabeceras W3C `traceparent` y `X-Trace-ID` en cliente y middleware FastAPI, con logs estructurados JSON censurados vía `structlog`.

---

## 2. Matriz de Blindaje de Entornos Canónicos

| Entorno Canónico | Lectura / Simulación (`dryRun=True`) | Inyección Mock Data (`dryRun=False`) | Desplazamiento FEFO (`dryRun=False`) | Playwright Runner E2E | Código de Fallo si se viola Guardrail |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`local`** | Habilitado | Permitido (Solo esquemas aislados autorizados) | Permitido (Solo esquemas aislados) | Permitido | 400 `ISOLATED_SCHEMA_REQUIRED` si target es no aislado |
| **`preview`** | Habilitado | Permitido (Solo esquemas aislados autorizados) | Permitido (Solo esquemas aislados) | Permitido | 400 `ISOLATED_SCHEMA_REQUIRED` si target es no aislado |
| **`ci`** | Habilitado | Permitido (Solo esquemas aislados autorizados) | Permitido (Solo esquemas aislados) | Permitido | 400 `ISOLATED_SCHEMA_REQUIRED` si target es no aislado |
| **`staging`** | Habilitado | **Requiere Confirmación Estricta** (`confirmStagingAction=true` o header `X-Sandbox-Confirm-Staging: true`) | **Requiere Confirmación Estricta** (`confirmStagingAction=true` o header `X-Sandbox-Confirm-Staging: true`) | Permitido | **400 `STAGING_CONFIRMATION_REQUIRED`** si falta confirmación |
| **`production`** | Habilitado (Cálculos no destructivos) | **BLOQUEO FAIL-FAST INCONDICIONAL** | **BLOQUEO FAIL-FAST INCONDICIONAL** | **Requiere Confirmación Estricta** (`confirmProductionRun=true` o header `X-Sandbox-Confirm-Production: true`) | **403 `PRODUCTION_MUTATION_FORBIDDEN`** / **400 `PRODUCTION_CONFIRMATION_REQUIRED`** |

### Esquemas Aislados Autorizados para Mutación (`dryRun=False`):
- Prefijos permitidos: `tenant_qa_*`, `tenant_sandbox_*`, `tenant_test_*`, `tenant_integration_*`
- Esquemas canónicos explícitos: `tenant_genesis`, `tenant_qa_lab`, `tenant_sandbox_fefo`
- Esquemas protegidos/bloqueados: `public`, esquemas transaccionales o esquemas de producción.

---

## 3. Instrumentación de Observabilidad (OpenTelemetry & Structured Logging)

### 3.1. Frontend HTTP Client (`api.ts` y `httpClient.ts`)
- Todas las llamadas al backend pasan por `apiRequest(...)` y `buildApiHeaders(...)`.
- `buildApiHeaders()` inyecta automáticamente:
  - `X-Trace-ID`: Identificador determinista de 32 caracteres hex (128 bits).
  - `traceparent`: Encabezado estándar W3C `00-${traceId}-${spanId}-01`.
  - `X-Tenant-ID` y `X-Holding-ID`: Contexto multi-tenant de la sesión.
- Validaciones fail-fast del lado cliente en `api.ts` para interceptar mutaciones no autorizadas en `production` y `staging` antes de enviar la petición de red.

### 3.2. Backend FastAPI (`sandbox_router.py` y `observability.py`)
- Middleware `trace_id_and_security_headers_middleware`:
  - Extrae `X-Trace-ID` entrante o genera UUID hex.
  - Enlaza el contexto en `bind_tenant_telemetry_context(...)`.
  - Inyecta `X-Trace-ID` en las cabeceras de respuesta HTTP.
- Cada endpoint de Sandbox ejecuta dentro de un contexto `trace_span(tracer_name="oppytec.sandbox", attributes={...})`.
- Logs estructurados con `structlog.get_logger("oppytec.sandbox")`, con censura automática de credenciales y PII.

---

## 4. Evidencia de Ejecución de Pruebas Automatizadas

### Backend Pytest (`oppytec-backend`)
- **Archivo**: `tests/unit/test_platform_admin_sandbox.py` (14 pruebas) -> **14 PASSED**
- **Archivo**: `tests/unit/test_sandbox_observability_and_environments.py` (9 pruebas) -> **9 PASSED**
- **Total Backend**: **23 PASSED (100% éxito)**

### Frontend Vitest (`oppytec-frontend`)
- **Archivo**: `src/features/platform-admin/sandbox/__tests__/SandboxApiAndTelemetry.test.ts` (10 pruebas) -> **10 PASSED**
- **Archivo**: `src/features/platform-admin/sandbox/__tests__/SandboxViews.test.tsx` (14 pruebas) -> **14 PASSED**
- **Archivo**: `src/features/platform-admin/sandbox/__tests__/SandboxI18nAndFx.test.tsx` (12 pruebas) -> **12 PASSED**
- **Total Frontend**: **36 PASSED (100% éxito)**
- **Verificación de Tipos TypeScript (`tsc --noEmit`)**: **0 errores**.

---

## 5. Declaración de Certificación Formal

El Agente 08 certifica formalmente que la consola **Lab & QA Sandbox** cumple con todos los requisitos de seguridad de aislamiento para los 5 entornos canónicos y cuenta con instrumentación de observabilidad OpenTelemetry completa y verificada.
