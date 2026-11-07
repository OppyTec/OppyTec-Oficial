# Sub-Plan 3 — Etapa 2: Construcción Frontend
## Consola Dinámica y Extensible de Tests Playwright en Platform Admin Sandbox

- **Agente Responsable:** Agente 05: Desarrollador Frontend Senior (`05-frontend-senior-dev`)
- **Fecha UTC:** 2026-11-06T00:18:00Z
- **Hito:** Sub-Plan 3 — Etapa 2 (Construcción Frontend completada con 100% pruebas pasando)
- **Destinatarios:**
  - Orquestador General (`parent`)
  - Agente 13: Especialista en Navegador Real Playwright (`13-browser-e2e-playwright`)
  - Agente 04: Backend Senior Dev (`04-backend-senior-dev`)
  - Agente 09: QA Parity & Test Engineer (`09-qa-parity-and-test-engineer`)
  - Agente 10: Cybersecurity Red Team (`10-cybersecurity-redteam-auditor`)

---

### 1. Resumen Ejecutivo de Implementación

En estricto cumplimiento de la arquitectura DDD (`subplan3_etapa1_playwright_architecture_spec.md`), las invariantes de contratos TypeScript (`sandboxTypes.ts`), el ADN Visual de OppyTec v2.0 (Tailwind tokens, soporte de 3 temas, diseño mobile-first) y el **Principio Zero-Code Frontend Addition**, se ha completado la construcción y certificación de la Consola Dinámica y Extensible de Tests Playwright:

1. **Módulo API y Streaming SSE (`sandboxApi.ts` y re-export en `api.ts`):**
   - `getPlaywrightCatalogApi()`: Invocación a `GET /api/v1/platform-admin/sandbox/playwright/catalog` con `DEFAULT_PLAYWRIGHT_CATALOG` como fallback defensivo.
   - `triggerPlaywrightRunApi(payload)`: Disparo de pruebas con soporte bidireccional estricto (contrato granular Sub-Plan 3 `scope: "all" | "domain" | "test"` y compatibilidad con `PlaywrightRunConfig`). Implementa guardrail client-side fail-fast para entorno `production`.
   - `subscribePlaywrightStream(runId, onEvent, onError, onComplete)`: Conexión reactiva a Server-Sent Events (`GET /api/v1/platform-admin/sandbox/playwright/stream/{runId}`) con reconexión segura, parseo JSON defensivo y retorno de función de cleanup / cancelación.

2. **Refactorización de la Vista `PlaywrightRunnerSandboxView.tsx`:**
   - **Header de Métricas Globales:** Total de tests (`summary.total`), % de cobertura real con barra de progreso visual interactiva, badges diferenciados por madurez (`🟢 Ready`, `🟡 In Progress (Agente 13)`, `⚪ Planned (Roadmap)`), y botón superior `[▶ Ejecutar Todos los Tests Ready]`.
   - **Selector de Modo de Ejecución:** Conmutador interactivo `Modo Human Live Demo (slow-mo 500ms)` vs `Modo CI Headless (0ms)`, selector de navegador (`Chromium`, `Firefox`, `WebKit`), inputs de target tenant, workers y retries.
   - **Acordeones Colapsables por los 7 Dominios:** Iteración dinámica de `catalog.domains` (`tenancy`, `auth_rbac`, `inventory`, `recipes`, `procurement`, `finops`, `pos`) sin listas estáticas fijas en frontend. Cada acordeón muestra icono por dominio, título, badge de progreso `(X ready / Y total)` y botón de suite de dominio `[▶ Ejecutar Suite]`.
   - **Badges de Madurez Granulares:**
     * `🟢 READY`: Permite ejecución individual inmediata mediante botón `[▶ Correr]`.
     * `🟡 IN PROGRESS`: Indicador ámbar con spinner y etiqueta "Agente 13: En desarrollo activo".
     * `⚪ PLANNED`: Indicador gris con etiqueta "Roadmap".
   - **Consola / Terminal de Streaming en Vivo:**
     * Fondo oscuro `bg-slate-950 font-mono text-xs`, auto-scroll reactivo en `terminal-body`.
     * Logs coloreados por nivel semántico (`info` en sky, `step` en amber, `assert` en emerald con checks, `warn` en orange, `error` en rose).
     * Soporte para enlaces a capturas de pantalla (`screenshotUrl`).
     * Stepper visual reactivo (`Setup Entorno` -> `Aislamiento Tenant` -> `Motor Playwright` -> `Artefactos & Traces`) con checks animados.
     * Barra de estado de conexión (`Desconectado`, `Conectando...`, `Ejecutando`, `Completado`, `Error`) con loader spin.
     * Botón para limpiar terminal y botón para cancelar ejecución activa.

3. **Co-Creación 1:1 de Tests Unitarios e Integración (`PlaywrightRunnerSandboxView.test.tsx`):**
   - 15 casos de prueba unitarios e integrados cubriendo las 6 áreas funcionales:
     * Resumen del catálogo y métricas globales.
     * Selectores de modo (Human Live Demo vs CI Headless) y selector de navegador.
     * Acordeones colapsables por dominio y filtrado por madurez (READY, IN_PROGRESS, PLANNED).
     * Interacción de disparo granular (all, domain, test) y observabilidad en la terminal.
     * Principio Zero-Code Frontend Addition (inyección de catálogos dinámicos).
     * Cliente API y streaming SSE con mock de EventSource.
   - Resultado: **15/15 tests pasando al 100%**.
   - Consolidado Sandbox: **5 test files pasados, 81/81 tests pasados (100% de éxito)**.
   - Typecheck estricto: **0 errores con `tsc --noEmit`**.

---

### 2. Evidencias de Verificación Automatizada

```bash
# 1. Typecheck estricto en frontend:
cd oppytec-frontend && pnpm run typecheck
# Salida: $ tsc --noEmit (Exit Code 0, 0 errores)

# 2. Suites de pruebas Sandbox en frontend:
cd oppytec-frontend && pnpm exec vitest run src/features/platform-admin/sandbox/
# Salida:
# ✓ src/features/platform-admin/sandbox/__tests__/SandboxApiAndTelemetry.test.ts (14 tests)
# ✓ src/features/platform-admin/sandbox/__tests__/MockDataMasterSwitchAndPresets.test.tsx (21 tests)
# ✓ src/features/platform-admin/sandbox/__tests__/SandboxI18nAndFx.test.tsx (17 tests)
# ✓ src/features/platform-admin/sandbox/__tests__/SandboxViews.test.tsx (14 tests)
# ✓ src/features/platform-admin/sandbox/__tests__/PlaywrightRunnerSandboxView.test.tsx (15 tests)
# Test Files: 5 passed (5)
# Tests: 81 passed (81)
```

---

### 3. Traspaso hacia Etapas Subsiguientes

- **Hacia Agente 13 (`13-browser-e2e-playwright`):**
  La consola de frontend está completamente lista y cableada para recibir los tests reales que implementará en los 7 dominios. Cualquier nuevo test registrado en el backend aparecerá inmediatamente en los acordeones del dominio correspondiente con sus badges de madurez (`ready`, `in_progress`, `planned`), sin necesidad de tocar una sola línea de código frontend.
- **Hacia Agente 09 (`09-qa-parity-and-test-engineer`):**
  La suite de 81 tests de sandbox cubre exhaustivamente la reactividad del UI, los contratos SSE y los guardrails fail-fast.
