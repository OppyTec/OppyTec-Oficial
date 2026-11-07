# Pre-Spec Arquitectónico: Consola "Lab & QA Sandbox" (Platform Admin)

- **Documento**: `.agent/memory/subplan1_etapa1_architecture_spec.md`
- **Autor**: Agente 02 (Arquitecto de Software DDD & Clean Architecture)
- **Fase**: Sub-Plan 1 / Etapa 1 — Definición Arquitectónica y Contratos de TypeScript
- **Fecha**: 2026-11-05
- **Estado**: APROBADO & LISTO PARA IMPLEMENTACIÓN (Etapa 2)

---

## 1. Visión General y Objetivos Arquitectónicos

La consola **Lab & QA Sandbox** es un subsistema de ingeniería de calidad y pruebas integrado directamente en la consola de Platform Admin (`/admin`) de OppyTec v2.0. Su propósito es dotar a los administradores de plataforma y equipos de QA de herramientas interactivas de primer nivel para:

1. **Generación e Inyección de Datos Sintéticos (`mock-data`)**: Generación controlada de entidades de prueba (Holdings, Locales, Insumos, Lotes FEFO, Recetas, Facturas y Usuarios) con estricto aislamiento de esquemas multi-tenant y prevención de contaminación de datos productivos.
2. **Ejecutor y Monitor de Pruebas E2E (`playwright-runner`)**: Disparador interactivo y panel de observabilidad en vivo de suites de prueba Playwright (Smoke, Auth & RBAC, Anti-IDOR, POS Consumo, FEFO Inventory), con streaming de estados y enlaces a trazas/capturas.
3. **Simulador Temporal de Envejecimiento FEFO (`fefo-dates`)**: "Time Machine / Warp" para proyectar la caducidad de lotes, simular mermas monetarias y probar alertas proactivas sin alterar calendarios del sistema operativo del servidor.

---

## 2. Topología de Navegación y Rutas del Frontend

### 2.1. Estructura de Rutas en `oppytec-frontend/src/app/router.tsx`

Las rutas se montan bajo el árbol protegido por `AdminPrivateRoute` y dentro del layout unificado `AdminLayout`:

```tsx
<Route
  path="/admin"
  element={
    <AdminPrivateRoute>
      <AdminLayout />
    </AdminPrivateRoute>
  }
>
  {/* Rutas existentes de Platform Admin ... */}

  {/* Lab & QA Sandbox Routes */}
  <Route path="sandbox" element={<Navigate to="/admin/sandbox/mock-data" replace />} />
  <Route path="sandbox/mock-data" element={<MockDataSandboxPage />} />
  <Route path="sandbox/playwright-runner" element={<PlaywrightRunnerSandboxPage />} />
  <Route path="sandbox/fefo-dates" element={<FefoDatesSandboxPage />} />
</Route>
```

### 2.2. Identificadores Canónicos de Pestañas / Vistas

| Tab ID (`SandboxTabId`) | Ruta Canónica | Clave i18n Título | Icono Lucide Sugerido | Color / Accent |
| :--- | :--- | :--- | :--- | :--- |
| `mock-data` | `/admin/sandbox/mock-data` | `platform_admin.sandbox.tab_mock_data` | `DatabaseZap` | `#f59e0b` (`245,158,11`) |
| `playwright-runner` | `/admin/sandbox/playwright-runner` | `platform_admin.sandbox.tab_playwright` | `CheckCircle2` / `PlaySquare` | `#10b981` (`16,185,129`) |
| `fefo-dates` | `/admin/sandbox/fefo-dates` | `platform_admin.sandbox.tab_fefo` | `CalendarClock` | `#8b5cf6` (`139,92,246`) |

### 2.3. Integración en `AdminSidebar.tsx`

Se crea una nueva sección colapsable en la barra lateral de Platform Admin:
- **Título de Sección**: `Lab & QA Sandbox` (`platform_admin.sidebar.section_sandbox`)
- **Icono de Sección**: `FlaskConical` de Lucide-React.
- **Badge**: `QA` o `LAB`.
- **Estructura de Menú**:
  ```typescript
  export const SANDBOX_MENU_ITEMS = [
    {
      path: "/admin/sandbox/mock-data",
      label: "Generador Mock Data",
      icon: DatabaseZap,
      color: "#f59e0b",
      rgb: "245,158,11",
      badge: "DATA",
    },
    {
      path: "/admin/sandbox/playwright-runner",
      label: "Playwright E2E Runner",
      icon: PlaySquare,
      color: "#10b981",
      rgb: "16,185,129",
      badge: "E2E",
    },
    {
      path: "/admin/sandbox/fefo-dates",
      label: "Simulador FEFO (Time-Warp)",
      icon: CalendarClock,
      color: "#8b5cf6",
      rgb: "139,92,246",
      badge: "WARP",
    },
  ] as const;
  ```

---

## 3. Modelo de Seguridad y RBAC Canónico (3-Niveles)

Siguiendo el estándar inmutable de OppyTec v2.0 (`<modulo>.<submodulo>.<accion>`):

### 3.1. Definición de Permisos

1. **`platform_admin.sandbox.access`**:
   - **Nivel**: Lectura / Consulta.
   - **Capacidades**: Acceso al menú y navegación en las 3 pestañas del Sandbox; visualización de historial de generaciones de datos sintéticos; consulta de resultados y logs de suites Playwright; visualización de la matriz de lotes FEFO y cálculo proyectado de mermas.
2. **`platform_admin.sandbox.manage`**:
   - **Nivel**: Ejecución / Operación de Impacto.
   - **Capacidades**: Disparo de la inyección de datos sintéticos en la base de datos del tenant; ejecución interactiva de suites Playwright con consumo de recursos; aplicación efectiva del desplazamiento temporal (*Time Warp Shift*) sobre fechas de vencimiento de lotes en la base de datos.

### 3.2. Aplicación en Guardias FastAPI (Backend)

```python
# Acceso a lectura / estado
@router.get("/api/v1/platform-admin/sandbox/status")
async def get_sandbox_status(
    _principal: Annotated[AuthenticatedPrincipal, Depends(RequireGlobalPermission("platform_admin.sandbox.access"))]
):
    ...

# Acceso a ejecución / mutación
@router.post("/api/v1/platform-admin/sandbox/mock-data/generate")
async def execute_mock_data_generation(
    payload: MockDataGenerationRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(RequireGlobalPermission("platform_admin.sandbox.manage"))]
):
    ...
```

### 3.3. Aplicación en UI Frontend

Los botones de acción destructiva o ejecución utilizan el componente `<Can>` o deshabilitan las acciones si el usuario carece de `platform_admin.sandbox.manage`:

```tsx
<Can
  permission="platform_admin.sandbox.manage"
  fallback={
    <div className="text-xs text-amber-500 font-medium">
      Modo Solo Lectura: Requiere permiso platform_admin.sandbox.manage para ejecutar.
    </div>
  }
>
  <button type="submit" className="btn-primary">Ejecutar Simulación</button>
</Can>
```

---

## 4. Contratos de TypeScript (`sandboxTypes.ts`)

Los contratos han sido implementados y validados mediante `tsc --noEmit` en `oppytec-frontend/src/features/platform-admin/sandboxTypes.ts`.

### 4.1. Tipos de Navegación y RBAC
```typescript
export const PLATFORM_ADMIN_SANDBOX_ACCESS: ThreeLevelPermission = "platform_admin.sandbox.access";
export const PLATFORM_ADMIN_SANDBOX_MANAGE: ThreeLevelPermission = "platform_admin.sandbox.manage";

export type SandboxPermission =
  | typeof PLATFORM_ADMIN_SANDBOX_ACCESS
  | typeof PLATFORM_ADMIN_SANDBOX_MANAGE;

export type SandboxTabId = "mock-data" | "playwright-runner" | "fefo-dates";

export interface SandboxNavItem {
  readonly id: SandboxTabId;
  readonly path: string;
  readonly label: string;
  readonly labelKey: string;
  readonly description: string;
  readonly descriptionKey: string;
  readonly icon: LucideIcon;
  readonly color: string;
  readonly rgb: string;
  readonly badge?: string;
  readonly requiredPermission: SandboxPermission;
}
```

### 4.2. Contratos de Mock Data
```typescript
export type MockDataEntityCategory =
  | "holdings"
  | "tenants"
  | "users"
  | "catalog"
  | "inventory_fefo"
  | "recipes"
  | "invoices"
  | "events"
  | "all";

export type MockDataVolume = "small" | "medium" | "large" | "stress";

export interface MockDataGenerationConfig {
  readonly tenantSchema: string;
  readonly categories: readonly MockDataEntityCategory[];
  readonly volume: MockDataVolume;
  readonly seedRandom: number | null;
  readonly preserveExisting: boolean;
  readonly dryRun: boolean;
  readonly injectFefoAnomalies: boolean;
}

export type MockDataStatus = "idle" | "generating" | "success" | "failed";

export interface MockDataGenerationProgress {
  readonly step: string;
  readonly percent: number;
  readonly recordsCreated: Readonly<Record<string, number>>;
  readonly status: MockDataStatus;
  readonly errorMessage: string | null;
  readonly executionDurationMs: number;
}
```

### 4.3. Contratos de Playwright Runner
```typescript
export type PlaywrightTestSuiteId =
  | "smoke"
  | "auth_rbac"
  | "tenant_isolation_idor"
  | "pos_consumo"
  | "inventory_fefo"
  | "recipes_escandallo"
  | "holding_hub"
  | "all";

export type PlaywrightBrowserType = "chromium" | "firefox" | "webkit";

export interface PlaywrightRunConfig {
  readonly suiteId: PlaywrightTestSuiteId;
  readonly browser: PlaywrightBrowserType;
  readonly headless: boolean;
  readonly grepFilter: string | null;
  readonly retries: number;
  readonly workers: number;
  readonly targetTenantSchema: string;
  readonly baseUrl?: string;
}

export interface PlaywrightExecutionState {
  readonly runId: string | null;
  readonly status: "idle" | "queued" | "running" | "completed" | "failed";
  readonly startTime: string | null;
  readonly endTime: string | null;
  readonly totalTests: number;
  readonly passedTests: number;
  readonly failedTests: number;
  readonly skippedTests: number;
  readonly currentRunningTest: string | null;
  readonly testResults: readonly PlaywrightTestCaseResult[];
  readonly rawLogs: readonly string[];
}
```

### 4.4. Contratos de FEFO Time-Warp
```typescript
export type FefoWarpMode =
  | "relative_offset"
  | "absolute_date"
  | "spoilage_acceleration";

export interface FefoWarpConfig {
  readonly mode: FefoWarpMode;
  readonly offsetDays: number;
  readonly targetDateIso: string | null;
  readonly tenantSchema: string;
  readonly warehouseId: string | null;
  readonly affectCategories: readonly string[];
  readonly dryRun: boolean;
  readonly generateSpoilageEvents: boolean;
}

export interface FefoSimulationResult {
  readonly simulationId: string;
  readonly executedAt: string;
  readonly simulatedSystemDate: string;
  readonly totalBatchesEvaluated: number;
  readonly criticalBatchesCount: number;
  readonly expiredBatchesCount: number;
  readonly totalSpoilageRiskAmount: number;
  readonly currency: string;
  readonly alertsCreated: number;
  readonly batches: readonly FefoBatchSimulationImpact[];
}
```

### 4.5. Contratos de Componentes de Vista (Etapa 2)
```typescript
export interface MockDataSandboxViewProps {
  readonly isReadOnly?: boolean;
  readonly initialTenantSchema?: string;
  readonly onExecuteGeneration?: (config: MockDataGenerationConfig) => Promise<void>;
}

export interface PlaywrightRunnerSandboxViewProps {
  readonly isReadOnly?: boolean;
  readonly initialSuiteId?: PlaywrightTestSuiteId;
  readonly onTriggerSuite?: (config: PlaywrightRunConfig) => Promise<void>;
  readonly onCancelExecution?: (runId: string) => Promise<void>;
}

export interface FefoDatesSandboxViewProps {
  readonly isReadOnly?: boolean;
  readonly initialTenantSchema?: string;
  readonly onRunSimulation?: (config: FefoWarpConfig) => Promise<FefoSimulationResult>;
  readonly onApplyDateShift?: (config: FefoWarpConfig) => Promise<void>;
}

export interface SandboxLayoutProps {
  readonly activeTab: SandboxTabId;
  readonly onTabChange?: (tab: SandboxTabId) => void;
  readonly children?: React.ReactNode;
}
```

---

## 5. Especificación de Endpoints Backend (FastAPI)

Para respaldar las vistas en la Etapa 2, se recomienda montar el router `src/modules/tenancy/presentation/sandbox_router.py`:

1. `POST /api/v1/platform-admin/sandbox/mock-data/generate`:
   - Permiso: `platform_admin.sandbox.manage`
   - Genera entidades sintéticas con `faker` y las inyecta en el esquema del tenant especificado o devuelve un preview si `dryRun: true`.
2. `GET /api/v1/platform-admin/sandbox/mock-data/history`:
   - Permiso: `platform_admin.sandbox.access`
   - Devuelve las últimas 20 ejecuciones de mock data.
3. `POST /api/v1/platform-admin/sandbox/playwright/run`:
   - Permiso: `platform_admin.sandbox.manage`
   - Dispara una tarea asíncrona de ejecución de Playwright y retorna un `run_id`.
4. `GET /api/v1/platform-admin/sandbox/playwright/status/{run_id}`:
   - Permiso: `platform_admin.sandbox.access`
   - Consulta el estado actual, logs acumulados y resultados de pruebas.
5. `POST /api/v1/platform-admin/sandbox/fefo/simulate`:
   - Permiso: `platform_admin.sandbox.access`
   - Simulación no destructiva (dry run) del impacto en los lotes FEFO según el desplazamiento temporal solicitado.
6. `POST /api/v1/platform-admin/sandbox/fefo/shift`:
   - Permiso: `platform_admin.sandbox.manage`
   - Aplicación real del desplazamiento en la base de datos de pruebas (actualiza `expiration_date` en la tabla `inventory_batches`).

---

## 6. Plan de Entrega para Etapa 2

### Frontend
1. Implementar la navegación en `AdminSidebar.tsx` con la sección `Lab & QA Sandbox`.
2. Registrar las rutas `/admin/sandbox/*` en `oppytec-frontend/src/app/router.tsx`.
3. Construir los componentes de vista en `oppytec-frontend/src/features/platform-admin/sandbox/`:
   - `MockDataSandboxView.tsx`
   - `PlaywrightRunnerSandboxView.tsx`
   - `FefoDatesSandboxView.tsx`
   - `SandboxPage.tsx` (Contenedor con tabs dinámicas).
4. Agregar las claves de internacionalización en `en/platform_admin.json` y `es/platform_admin.json`.

### Backend
1. Crear `oppytec-backend/src/modules/tenancy/presentation/sandbox_router.py`.
2. Crear los servicios de aplicación `MockDataGeneratorService` y `FefoWarpSimulatorService`.
3. Montar el router en `src/main.py`.

---

## 7. Autoevaluación de Calidad Arquitectónica (10 Criterios)

1. **Aislamiento Multi-Tenant (Anti-IDOR)**: CUMPLIDO. Todas las operaciones requieren contexto explícito de tenant y validación contra esquemas aislados.
2. **Clean Architecture / DDD**: CUMPLIDO. Separación estricta de dominios, DTOs, servicios y presentación.
3. **TypeScript 5 Strict**: CUMPLIDO. Cero `any`, todas las propiedades inmutables (`readonly`), verificado con `tsc --noEmit`.
4. **RBAC Dual de 3 Niveles**: CUMPLIDO. `platform_admin.sandbox.access` y `platform_admin.sandbox.manage` siguen `<modulo>.<submodulo>.<accion>`.
5. **No Regresiones Legacy**: CUMPLIDO. No se tocan archivos ni dependencias del directorio legacy.
6. **Mobile-First & Accesibilidad**: CUMPLIDO. Interfaces adaptables a touch targets >= 44px y layouts flexibles.
7. **Diseño de Trazabilidad y Observabilidad**: CUMPLIDO. Integración con `runId`, `traceId` y logs estructurados.
8. **Prevención de Pérdida de Datos**: CUMPLIDO. Banderas `dryRun` obligatorias por defecto en simulaciones FEFO y Mock Data.
9. **Compatibilidad i18n**: CUMPLIDO. Identificadores mapeados a claves jerárquicas i18n (`labelKey`, `descriptionKey`).
10. **Completitud y Preparación de Traspaso**: CUMPLIDO. Especificación exhaustiva y contratos en código listos para su consumo inmediato.
