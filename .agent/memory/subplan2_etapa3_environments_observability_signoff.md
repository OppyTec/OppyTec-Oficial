# Certificación Formal de Aislamiento de Entornos y Observabilidad: Switch Maestro de Mock Data y Presets Gastronómicos

- **Documento**: `.agent/memory/subplan2_etapa3_environments_observability_signoff.md`
- **Autor**: Agente 08 (Ingeniero de Entornos y Observabilidad)
- **Fase**: Sub-Plan 2 / Etapa 3 — Auditoría de Blindaje de Entornos Canónicos, Telemetría Distribuida y Guardrails de Factory Reset
- **Fecha**: 2026-11-05
- **Estado**: **APROBADO & CERTIFICADO (100% CUMPLIDO)**

---

## 1. Resumen Ejecutivo de la Auditoría

Se auditó, blindó e instrumentó el flujo integral de datos sintéticos, conmutador maestro de telemetría (*Mock Mode Switch*), presets gastronómicos canónicos y la operación destructiva *Factory Reset* en **OppyTec v2.0**:

1. **Propagación de Telemetría Distribuida W3C & Mock Mode**:
   - `buildApiHeaders()` inyecta de forma reactiva y determinista la cabecera `X-OppyTec-Mock-Mode: "demo" | "clean"`, coordinada con `localStorage` (`oppytec_mock_data_mode`) y el hook `useMockDataMode`.
   - Inyección y preservación de cabeceras W3C `traceparent` (`00-${traceId}-${spanId}-01`) y `X-Trace-ID` (128 bits hex) a través de todo el ciclo de vida HTTP.
   - En FastAPI (`src.main.py`), el middleware HTTP y el manejador de excepciones de dominio (`oppytec_domain_exception_handler`) capturan, validan y reflejan `X-OppyTec-Mock-Mode`, `X-Trace-ID` y `traceparent` en todas las respuestas (éxitos y códigos de error RFC 7807).

2. **Blindaje Fail-Fast de Entornos Canónicos para Factory Reset (`POST /mock-data/reset`)**:
   - **`production`**: Bloqueo incondicional inmediato con código HTTP 403 y `error_code: PRODUCTION_MUTATION_FORBIDDEN`.
   - **`staging`**: Exigencia estricta de doble confirmación mediante payload (`confirmStagingAction=true`) o cabecera HTTP (`X-Sandbox-Confirm-Staging: true`), retornando HTTP 400 `STAGING_CONFIRMATION_REQUIRED` si falta.
   - **Todos los entornos (`local`, `preview`, `ci`, `staging`, `production`)**: Exigencia inquebrantable de aislamiento de esquema multi-tenant (`tenant_qa_*`, `tenant_sandbox_*`, `tenant_test_*`, `tenant_integration_*` o canónicos `tenant_genesis`, `tenant_qa_lab`, `tenant_sandbox_fefo`). Cualquier intento sobre esquemas no aislados (ej. `public`, `tenant_restaurante_real`) es rechazado con HTTP 400 `ISOLATED_SCHEMA_REQUIRED`.
   - Requerimiento de confirmación explícita de purga (`confirmReset=true`), previniendo disparos accidentales.

---

## 2. Matriz de Blindaje de Entornos: Factory Reset y Presets Gastronómicos

| Entorno Canónico | Consulta Catálogo Presets (`GET /presets`) | Inyección Dataset Sintético (`POST /mock-data/generate`) | Factory Reset (`POST /mock-data/reset`) | Cabeceras Requeridas / Evaluadas | Código de Fallo por Violación |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`local`** | Habilitado | Permitido (Solo esquemas aislados autorizados) | Permitido (Requiere `confirmReset=True` y esquema aislado) | `X-OppyTec-Mock-Mode`, `X-Trace-ID` | 400 `ISOLATED_SCHEMA_REQUIRED` / `RESET_CONFIRMATION_REQUIRED` |
| **`preview`** | Habilitado | Permitido (Solo esquemas aislados autorizados) | Permitido (Requiere `confirmReset=True` y esquema aislado) | `X-OppyTec-Mock-Mode`, `X-Trace-ID` | 400 `ISOLATED_SCHEMA_REQUIRED` / `RESET_CONFIRMATION_REQUIRED` |
| **`ci`** | Habilitado | Permitido (Solo esquemas aislados autorizados) | Permitido (Requiere `confirmReset=True` y esquema aislado) | `X-OppyTec-Mock-Mode`, `X-Trace-ID` | 400 `ISOLATED_SCHEMA_REQUIRED` / `RESET_CONFIRMATION_REQUIRED` |
| **`staging`** | Habilitado | **Requiere Confirmación Estricta** (`confirmStagingAction=true` o `X-Sandbox-Confirm-Staging: true`) | **Requiere Confirmación Estricta** (`confirmStagingAction=true` o `X-Sandbox-Confirm-Staging: true`) | `X-Sandbox-Confirm-Staging: true`, `X-OppyTec-Mock-Mode` | **400 `STAGING_CONFIRMATION_REQUIRED`** |
| **`production`** | Habilitado (Lectura catálogo metadatos) | **BLOQUEO FAIL-FAST INCONDICIONAL** | **BLOQUEO FAIL-FAST INCONDICIONAL** | `X-Trace-ID`, `traceparent` (preservados en respuesta 403) | **403 `PRODUCTION_MUTATION_FORBIDDEN`** |

---

## 3. Instrumentación de Trazabilidad OpenTelemetry y Flujo de Cabeceras

### 3.1. Frontend (`httpClient.ts` y `api.ts`)
- `buildApiHeaders()`:
  - `X-OppyTec-Mock-Mode`: Sincronizado reactivamente con `getMockDataMode()` (`"demo"` o `"clean"`).
  - `X-Trace-ID`: 32 caracteres hexadecimales generados por `createTraceHeaders()`.
  - `traceparent`: Encabezado estándar W3C TraceContext formato `00-${traceId}-${spanId}-01`.
  - `X-Holding-ID` y `X-Tenant-ID`: Contexto del inquilino activo.
- `executeFactoryReset(tenantSchema, targetPresetId, confirmReset, confirmStagingAction)`:
  - Inyecta cabecera `X-Sandbox-Confirm-Staging: "true"` cuando se opera con confirmación en staging.
  - Al completar el reset, limpia automáticamente la memoria de trabajo local (`localStorage.removeItem(MOCK_DATA_CUSTOM_DATASET_STORAGE_KEY)`) y despacha el evento desacoplado `CustomEvent("oppytec_mock_reset")`.

### 3.2. Backend (`src/main.py` y `sandbox_router.py`)
- Middleware `trace_id_and_security_headers_middleware`:
  - Captura `X-OppyTec-Mock-Mode`, almacenándolo en `request.state.mock_mode`.
  - Si el cliente envía `traceparent`, extrae el `trace_id` de forma compatible.
  - Refleja `X-Trace-ID`, `traceparent` y `X-OppyTec-Mock-Mode` en las cabeceras HTTP de respuesta.
- Endpoints canónicos de Sandbox:
  - `GET /api/v1/platform-admin/sandbox/mock-data/presets` y `GET /presets/{id}`:
    - Ejecutados bajo `trace_span("platform_admin_sandbox.mock_data.presets", attributes={"environment": env_name, "mock_mode": mock_mode})`.
  - `POST /api/v1/platform-admin/sandbox/mock-data/reset`:
    - Ejecutado bajo `trace_span("platform_admin_sandbox.mock_data.reset", attributes={"environment": env_name, "tenant_schema": payload.tenant_schema, "target_preset_id": payload.target_preset_id, "mock_mode": mock_mode, "is_destructive": True})`.
- Logs estructurados con `structlog.get_logger("oppytec.sandbox")`, auditando al actor (`user_{id}`), esquema, preset restaurado y modo mock activo.

---

## 4. Resultados de la Batería de Pruebas Automatizadas

### 4.1. Backend Pytest (`oppytec-backend`)
- **Suite**: `tests/unit/test_platform_admin_sandbox.py` (23 pruebas) -> **23 PASSED**
- **Suite**: `tests/unit/test_sandbox_observability_and_environments.py` (16 pruebas) -> **16 PASSED**
  - `test_production_environment_blocks_factory_reset_mock_data` -> **PASSED** (HTTP 403 `PRODUCTION_MUTATION_FORBIDDEN`)
  - `test_staging_environment_requires_explicit_confirmation_for_factory_reset` -> **PASSED** (HTTP 400 `STAGING_CONFIRMATION_REQUIRED` y HTTP 200 con confirmación)
  - `test_factory_reset_blocks_non_isolated_schema_in_all_environments` -> **PASSED** (HTTP 400 `ISOLATED_SCHEMA_REQUIRED`)
  - `test_factory_reset_requires_confirm_reset_flag` -> **PASSED** (HTTP 400 `RESET_CONFIRMATION_REQUIRED`)
  - `test_opentelemetry_and_mock_mode_propagation_on_presets` -> **PASSED** (W3C traceparent y X-OppyTec-Mock-Mode propagados)
  - `test_opentelemetry_and_mock_mode_propagation_on_factory_reset` -> **PASSED** (W3C traceparent y X-OppyTec-Mock-Mode reflejados)
  - `test_opentelemetry_headers_preserved_on_forbidden_production_error` -> **PASSED** (Preservación en RFC 7807 error responses)
- **Total Backend**: **39 PASSED / 0 FAILED (100% de éxito)**

### 4.2. Frontend Vitest (`oppytec-frontend`)
- **Suite**: `src/features/platform-admin/sandbox/__tests__/MockDataMasterSwitchAndPresets.test.tsx` (21 pruebas) -> **21 PASSED**
- **Suite**: `src/features/platform-admin/sandbox/__tests__/SandboxApiAndTelemetry.test.ts` (14 pruebas) -> **14 PASSED**
- **Suite**: `src/features/platform-admin/sandbox/__tests__/SandboxViews.test.tsx` (14 pruebas) -> **14 PASSED**
- **Suite**: `src/features/platform-admin/sandbox/__tests__/SandboxI18nAndFx.test.tsx` (12 pruebas) -> **12 PASSED**
- **Total Frontend**: **61 PASSED / 0 FAILED (100% de éxito)**
- **Verificación de Tipos TypeScript (`tsc --noEmit`)**: **0 errores**.

---

## 5. Declaración de Certificación Formal

El **Agente 08 (Ingeniero de Entornos y Observabilidad)** certifica formalmente que la implementación del **Switch Maestro de Mock Data, Editor, Presets Gastronómicos Canónicos y Factory Reset**:
1. Cumple rigurosamente con los guardrails fail-fast para los 5 entornos canónicos (`local`, `preview`, `ci`, `staging`, `production`).
2. Protege de forma inexpugnable los entornos de producción contra operaciones de purga o mutación sintética no autorizada.
3. Garantiza la trazabilidad distribuida W3C (`traceparent`, `X-Trace-ID`, `X-OppyTec-Mock-Mode`) en todas las interacciones de frontend y backend.
4. Ha superado exitosamente el 100% de los tests automatizados unitarios y de integración.
