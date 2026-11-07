# Sub-Plan 3 — Etapa 1: Arquitectura y Contratos
## Consola Dinámica y Extensible de Tests Playwright para Platform Admin Sandbox

- **Fecha:** 2026-11-05
- **Agente Responsable:** Agente 02: Arquitecto de Software DDD & Clean Architecture (`02-software-architect`)
- **Agentes Destinatarios:**
  - Agente 13: Especialista en Navegador Real con Playwright (`13-browser-e2e-playwright`)
  - Agente 04: Backend Senior Dev (`04-backend-senior-dev`)
  - Agente 05: Frontend Senior Dev (`05-frontend-senior-dev`)
  - Agente 09: QA Parity & Test Engineer (`09-qa-parity-and-test-engineer`)
  - Agente 10: Cybersecurity Red Team (`10-cybersecurity-redteam-auditor`)
- **Estado:** `APPROVED_FOR_IMPLEMENTATION`
- **Quality Gate:** 10/10 en Rúbrica de Gobernanza, 0 errores `pnpm run typecheck`, 100% tests vitest de sandbox pasando (66/66).

---

## 1. Contexto y Objetivos del Sub-Plan 3

La consola **Lab & QA Sandbox** en el Platform Admin de OppyTec v2.0 cuenta actualmente con tres pilares funcionales:
1. **Mock Data Generator & Presets Gastronómicos** (Sub-Plan 2: Switch Maestro, Presets "Pollo King", "Cava Angus", "Hotel Buffet" y Factory Reset).
2. **FEFO Dates & Time-Warp Simulator** (Aceleración temporal y proyección de mermas/caducidad).
3. **Playwright E2E Test Runner** (Ejecución y observabilidad de pruebas browser en tiempo real).

### El Desafío Arquitectónico: Extensibilidad Dinámica vs. Listas Estáticas
En la implementación preliminar, los suites de prueba de Playwright se encontraban declarados de forma estática en el frontend (`PLAYWRIGHT_SUITES` en `PlaywrightRunnerSandboxView.tsx`), limitados a identificadores fijos (`smoke`, `auth_rbac`, etc.) y sin capacidad de autodescubrimiento.

El **Sub-Plan 3** revoluciona esta arquitectura desacoplando por completo el frontend del catálogo de pruebas. A través del **Catálogo Dinámico y Extensible de Tests Playwright**, el Agente 13 (`13-browser-e2e-playwright`) puede registrar, clasificar por dominio, modificar metadatos y agregar nuevos escenarios de prueba en el backend mediante un **Patrón de Registro Declarativo (Registry Pattern)**. El frontend consulta este catálogo reactivamente, agrupándolo por dominios de negocio y reflejando en tiempo real:
- Madurez de pruebas (`ready`, `in_progress`, `planned`).
- Porcentaje global de cobertura de automatización.
- Ejecuciones granulares (`all`, `domain`, `test`).
- Streaming en vivo paso a paso vía **Server-Sent Events (SSE)** con soporte de simulación humana (`slow_mo_ms`) y captura de screenshots.

---

## 2. Arquitectura Clean Architecture & DDD

```
+---------------------------------------------------------------------------------------+
|                                    PRESENTATION LAYER                                 |
|  [FastAPI sandbox_router.py] <--------------------> [React 19 PlaywrightRunnerView]  |
|   - GET /playwright/catalog                          - usePlaywrightCatalog()         |
|   - POST /playwright/run                             - usePlaywrightStream()          |
|   - GET /playwright/stream/{run_id} (SSE)            - Strict sandboxTypes.ts (0 any) |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                    APPLICATION LAYER                                  |
|   - PlaywrightCatalogService (Autodescubrimiento, agregación por dominios y métricas) |
|   - PlaywrightExecutionCoordinator (Encolado asíncrono, subprocesos, worker pool)     |
|   - PlaywrightStreamBroadcaster (Despacho reactivo SSE con heartbeat y backpressure)  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                      DOMAIN LAYER                                     |
|   - Value Objects: PlaywrightDomain, PlaywrightItemStatus, PlaywrightStreamLogLevel   |
|   - Entidades: PlaywrightTestItem, PlaywrightCatalogSummary, PlaywrightDomainGroup    |
|   - Agregado Raíz: PlaywrightTestCatalog (Garantía de invariantes matemáticas)        |
|   - Registry Declarativo: @register_playwright_test (Extensibilidad Agente 13)       |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                 INFRASTRUCTURE LAYER                                  |
|   - Playwright Subprocess Runner (pytest-playwright, CLI launcher, browser workers)   |
|   - Storage Adapter (Cloudflare R2 / Local artifacts para screenshots y trazas)      |
|   - Observabilidad (OpenTelemetry Spans, W3C traceparent, Structlog JSON)             |
+---------------------------------------------------------------------------------------+
```

### Invariantes de Dominio
1. **Conservación de Conteos:**
   $$\text{Total} = \text{Ready} + \text{InProgress} + \text{Planned}$$
2. **Cálculo Determinista de Cobertura:**
   $$\text{CoveragePercentage} = \begin{cases} 0.0 & \text{si } \text{Total} = 0 \\ \operatorname{round}\left(\frac{\text{Ready}}{\text{Total}} \times 100, 1\right) & \text{si } \text{Total} > 0 \end{cases}$$
3. **Agrupación de Dominio Consistente:**
   Para cada dominio $d \in \text{Domains}$:
   $$\text{Domain}(d).\text{totalCount} = \operatorname{count}(\{t \in \text{Tests} \mid t.\text{domain} = d\})$$
   $$\text{Domain}(d).\text{readyCount} = \operatorname{count}(\{t \in \text{Tests} \mid t.\text{domain} = d \land t.\text{status} = \text{'ready'}\})$$

---

## 3. Modelo de Datos y Dominios de Negocio

### Dominios Oficiales de Prueba (`PlaywrightDomain`)
Los 7 dominios canónicos cubren la totalidad del ecosistema gastronómico y multi-tenant de OppyTec v2.0:
1. `tenancy`: Aislamiento estricto multi-tenant, ciclo de vida de holdings, sucursales y cuotas SaaS.
2. `auth_rbac`: Matriz exhaustiva de 3 niveles (`modulo.submodulo.accion`), rangos jerárquicos y seguridad de sesión.
3. `inventory`: Gestión FEFO, lotes perecibles, auditoría de mermas con segregación de funciones y recuentos físicos.
4. `recipes`: Escandallo recursivo de costos, submermas culinarias, alérgenos y cálculo de márgenes.
5. `procurement`: Ciclo de compras, recepción con balanza/pesaje, conciliación DTE / facturas SII y OCR.
6. `finops`: Gestión de créditos IA OppyFy, auditoría inmutable en `llm_request_logs` y límites por tenant.
7. `pos`: Registro rápido de consumo, comanda de cocina, modo Buffet, modo Manos Libres y Delivery.

### Metadatos Declarativos de Cada Prueba (`PlaywrightTestItem`)
Cada prueba expone:
- `id`: Identificador canónico único (ej: `pw_tenancy_01_holding_onboarding`).
- `domain`: Uno de los 7 dominios enumerados arriba.
- `title`: Nombre descriptivo legible para operadores humanos.
- `description`: Explicación detallada del flujo probado y aserciones clave.
- `status`: Estado de madurez del test (`ready`, `in_progress`, `planned`).
- `tags`: Etiquetas para filtrado granular (ej: `["smoke", "critical", "anti_idor", "mobile"]`).
- `estimated_duration_sec`: Duración estimada en segundos bajo ejecución estándar.
- `last_run`: Resultado de la última ejecución (`status: "passed" | "failed" | "idle"`, `duration_ms`, `timestamp`, `error`).

---

## 4. Contratos de Endpoints REST & Streaming

### 4.1. Catálogo Dinámico
- **Método y Ruta:** `GET /api/v1/platform-admin/sandbox/playwright/catalog`
- **Permiso RBAC Requerido:** `platform_admin.sandbox.access`
- **Cabeceras Soportadas:** `Authorization: Bearer <token>`, `traceparent`, `X-Trace-ID`
- **Código HTTP de Éxito:** `200 OK`
- **Estructura del Payload JSON:**
```json
{
  "summary": {
    "total": 35,
    "ready": 22,
    "inProgress": 8,
    "planned": 5,
    "coveragePercentage": 62.9
  },
  "domains": [
    {
      "domain": "tenancy",
      "title": "Tenancy & Multi-Tenant Onboarding",
      "readyCount": 4,
      "totalCount": 5,
      "tests": [
        {
          "id": "pw_tenancy_01_holding_creation",
          "domain": "tenancy",
          "title": "Creación y Aislamiento de Holding",
          "description": "Verifica alta de holding, creación de tenant y aislamiento de esquemas PostgreSQL.",
          "status": "ready",
          "tags": ["smoke", "tenancy", "p0"],
          "estimatedDurationSec": 35,
          "lastRun": {
            "status": "passed",
            "durationMs": 32410,
            "timestamp": "2026-11-05T20:45:00.000Z",
            "error": null
          }
        }
      ]
    }
  ]
}
```

### 4.2. Disparo de Ejecución Playwright
- **Método y Ruta:** `POST /api/v1/platform-admin/sandbox/playwright/run`
- **Permiso RBAC Requerido:** `platform_admin.sandbox.manage`
- **Cabeceras Especiales:**
  - `X-Sandbox-Confirm-Production: true` (Obligatorio si `ENVIRONMENT == 'production'`)
- **Código HTTP de Éxito:** `202 Accepted`
- **Payload Request:**
```json
{
  "scope": "domain",
  "targetId": "inventory",
  "headless": true,
  "slowMoMs": 0,
  "browser": "chromium",
  "targetTenantSchema": "tenant_sandbox_fefo",
  "confirmProductionRun": false
}
```
- **Campos del Request:**
  - `scope`: `"all"` | `"domain"` | `"test"` (Discriminante de alcance).
  - `targetId`: Opcional. ID del dominio (ej: `"inventory"`) si `scope == "domain"`, o ID del test (ej: `"pw_tenancy_01_holding_creation"`) si `scope == "test"`.
  - `headless`: Booleano. `true` para ejecución optimizada en segundo plano; `false` para modo visual en vivo (*Human Live Demo*).
  - `slowMoMs`: Entero $\ge 0$. Retardo en milisegundos entre acciones de Playwright (por defecto `500` ms en modo interactivo humano, `0` ms en CI).
  - `browser`: `"chromium"` | `"firefox"` | `"webkit"`.
  - `targetTenantSchema`: Esquema multi-tenant aislado donde se ejecutarán las pruebas.
  - `confirmProductionRun`: Booleano de confirmación explícita para evitar ejecuciones accidentales en producción.
- **Payload Response (202 Accepted):**
```json
{
  "runId": "pw_run_7b9d31f0",
  "status": "queued",
  "testsQueued": 6,
  "message": "Corrida encolada exitosamente para dominio 'inventory' (6 pruebas)."
}
```

### 4.3. Streaming en Vivo Paso a Paso (Server-Sent Events)
- **Método y Ruta:** `GET /api/v1/platform-admin/sandbox/playwright/stream/{run_id}`
- **Permiso RBAC Requerido:** `platform_admin.sandbox.access`
- **Content-Type:** `text/event-stream; charset=utf-8`
- **Protocolo:** Server-Sent Events (SSE) según RFC 8895 con soporte de reconnect (`id`, `retry: 3000`).
- **Heartbeat:** Envío periódico de ping cada 15s (`: keep-alive\n\n`) para evitar desconexiones por proxies o routers.
- **Formato de Eventos:**
```
event: step
id: 1
data: {"stepIndex": 1, "testId": "pw_inv_01_fefo_expiry", "message": "Iniciando navegación a /inventario/lotes...", "level": "step", "timestamp": "2026-11-05T20:50:01.120Z", "screenshotUrl": null, "durationMs": 420}

event: step
id: 2
data: {"stepIndex": 2, "testId": "pw_inv_01_fefo_expiry", "message": "Selector [data-testid='btn-recalcular-fefo'] visible y habilitado.", "level": "assert", "timestamp": "2026-11-05T20:50:02.050Z", "screenshotUrl": "/api/v1/platform-admin/sandbox/playwright/artifacts/pw_run_7b9d31f0/step_2.png", "durationMs": 850}

event: completed
id: 3
data: {"runId": "pw_run_7b9d31f0", "status": "completed", "totalTests": 6, "passedTests": 6, "failedTests": 0, "durationMs": 18450}
```

---

## 5. Tipos de TypeScript en Frontend (`sandboxTypes.ts`)

Los contratos de TypeScript han sido integrados con **0 `any`** y modificadores `readonly` inmutables en [sandboxTypes.ts](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/features/platform-admin/sandboxTypes.ts#L173-L285):

```typescript
export type PlaywrightDomain =
  | "tenancy"
  | "auth_rbac"
  | "inventory"
  | "recipes"
  | "procurement"
  | "finops"
  | "pos";

export type PlaywrightDomainId = PlaywrightDomain;
export type PlaywrightItemStatus = "ready" | "in_progress" | "planned";
export type PlaywrightTestRunStatus = "passed" | "failed" | "idle";

export interface PlaywrightTestRunResult {
  readonly status: PlaywrightTestRunStatus;
  readonly durationMs: number;
  readonly timestamp: string;
  readonly error: string | null;
  readonly duration_ms?: number;
}

export interface PlaywrightTestItem {
  readonly id: string;
  readonly domain: PlaywrightDomain;
  readonly title: string;
  readonly description: string;
  readonly status: PlaywrightItemStatus;
  readonly tags: readonly string[];
  readonly estimatedDurationSec: number;
  readonly lastRun?: PlaywrightTestRunResult | null;
  readonly estimated_duration_sec?: number;
  readonly last_run?: PlaywrightTestRunResult | null;
}

export interface PlaywrightCatalogSummary {
  readonly total: number;
  readonly ready: number;
  readonly inProgress: number;
  readonly planned: number;
  readonly coveragePercentage: number;
  readonly in_progress?: number;
  readonly coverage_percentage?: number;
}

export interface PlaywrightDomainGroup {
  readonly domain: PlaywrightDomain;
  readonly title: string;
  readonly readyCount: number;
  readonly totalCount: number;
  readonly tests: readonly PlaywrightTestItem[];
  readonly ready_count?: number;
  readonly total_count?: number;
}

export interface PlaywrightCatalogResponse {
  readonly summary: PlaywrightCatalogSummary;
  readonly domains: readonly PlaywrightDomainGroup[];
}

export type PlaywrightRunScope = "all" | "domain" | "test";

export interface PlaywrightRunRequestPayload {
  readonly scope: PlaywrightRunScope;
  readonly targetId?: string | null;
  readonly headless: boolean;
  readonly slowMoMs: number;
  readonly browser?: PlaywrightBrowserType;
  readonly targetTenantSchema?: string;
  readonly confirmProductionRun?: boolean;
  readonly target_id?: string | null;
  readonly slow_mo_ms?: number;
  readonly target_tenant_schema?: string;
  readonly confirm_production_run?: boolean;
}

export interface PlaywrightRunTriggerResponse {
  readonly runId: string;
  readonly status: PlaywrightExecutionStatus;
  readonly testsQueued: number;
  readonly message?: string;
  readonly run_id?: string;
  readonly tests_queued?: number;
}

export type PlaywrightStreamLogLevel =
  | "info"
  | "warn"
  | "error"
  | "debug"
  | "step"
  | "assert";

export interface PlaywrightStreamStepEvent {
  readonly stepIndex: number;
  readonly testId: string;
  readonly message: string;
  readonly level: PlaywrightStreamLogLevel;
  readonly timestamp: string;
  readonly screenshotUrl: string | null;
  readonly durationMs?: number;
  readonly error?: string | null;
  readonly step_index?: number;
  readonly test_id?: string;
  readonly screenshot_url?: string | null;
  readonly duration_ms?: number;
}
```

---

## 6. Guardrails de Seguridad y Fail-Fast de Entornos

1. **Aislamiento de Entorno `production`:**
   - La ejecución de pruebas Playwright en `production` requiere autorización global de administrador y cabecera explícita `X-Sandbox-Confirm-Production: true` o campo booleano `confirmProductionRun: true`.
   - Cualquier intento de corrida destructiva o sin confirmación resulta en aborto preventivo inmediato con HTTP `400 Bad Request` / `403 Forbidden` (`EnvironmentGuardViolationError`).
2. **Anti-IDOR Cross-Tenant:**
   - `targetTenantSchema` debe coincidir con la lista de esquemas de pruebas autorizados (`tenant_sandbox_*`, `tenant_genesis`, `tenant_qa_lab`). Esquemas de producción activos de clientes reales son rechazados de inmediato.
3. **Control de Recursos y Denegación de Servicio (DoS Guard):**
   - Límite de workers simultáneos: máximo 4 en entornos locales/preview, 2 en staging/production.
   - Timeout estricto de ejecución: Cada prueba unitaria tiene un timeout máximo de 90 segundos; el lote completo un máximo de 10 minutos.

---

## 7. Plan de Implementación de Etapas Subsiguientes

| Etapa | Responsable | Entregables Principales |
|---|---|---|
| **Etapa 2 (Backend)** | Agente 04 (`04-backend-senior-dev`) | - Servicio de catálogo extensible y registro de pruebas en `sandbox_service.py`<br>- Schemas Pydantic v2 en `schemas_sandbox.py`<br>- Endpoints `/catalog`, `/run` y `/stream/{run_id}` con SSE en `sandbox_router.py`<br>- Tests unitarios y de integración de endpoints |
| **Etapa 3 (Frontend)** | Agente 05 (`05-frontend-senior-dev`) | - Métodos en `api.ts` (`getPlaywrightCatalogApi`, `streamPlaywrightRun`)<br>- Refactorización de `PlaywrightRunnerSandboxView.tsx` para consumir catálogo dinámico<br>- Filtros por dominio, barra de cobertura general y visor de stream en vivo con screenshots<br>- Selector de velocidad (Headless vs. Visual Live Demo `slowMo=500ms`) |
| **Etapa 4 (Playwright Specs)** | Agente 13 (`13-browser-e2e-playwright`) | - Implementación de tests browser reales cubriendo los 7 dominios<br>- Decoradores de registro para descubrimiento automático<br>- Captura automatizada de screenshots por paso |
| **Etapa 5 (Auditoría & OpenSpec)** | Agente 10 & Agente 12 | - Veto de seguridad Red Team Kali y validación OpenSpec bipartita |

---

## 8. Verificación y Evidencias de Calidad (Etapa 1)

1. **Typecheck en Frontend:**
   - Comando: `cd oppytec-frontend && pnpm run typecheck` (`tsc --noEmit`)
   - Resultado: **0 errores**. Salida con código 0.
2. **Suites Unitarias de Sandbox en Frontend:**
   - Comando: `cd oppytec-frontend && pnpm test src/features/platform-admin/sandbox/`
   - Resultado: **4 suites pasadas, 66 tests pasados (100%)**.
3. **Navegación AST con Harness:**
   - Consulta: `python scripts/harness.py nav "sandbox_router"`
   - Resultado: Verificación de relaciones con `schemas_sandbox`, `sandbox_manager` y vistas de frontend.
4. **Reglas Inmutables Cumplidas:**
   - OppyTec-Legacy intacto (0 modificaciones).
   - Zero `any` en tipado TypeScript.
   - Zero secretos expuestos.
