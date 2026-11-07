# Diario del Escuadrón — 2026-11-05: Sub-Plan 3 Consola Dinámica y Extensible de Tests Playwright

- **Fecha:** 5 de noviembre de 2026
- **Hito:** Finalización y Certificación del Sub-Plan 3 (Consola Dinámica y Extensible de Tests Playwright en Platform Admin Sandbox, Catálogo Desacoplado, 7 Dominios de Negocio, Streaming SSE y Certificación FinOps)
- **Escuadrón:** Agentes 02, 03, 04, 05, 06, 07, 08, 12 y 13.

---

## 1. El Problema de Negocio y Operación

Hasta el Sub-Plan 2, las pruebas de extremo a extremo en el Sandbox de Platform Admin dependían de un listado estático cableado en el frontend (`PLAYWRIGHT_SUITES` en `PlaywrightRunnerSandboxView.tsx`), con identificadores fijos y sin capacidad de autodescubrimiento. Cada vez que los ingenieros de calidad agregaban o modificaban una prueba E2E, se requería alterar el código fuente de los componentes visuales de React. Adicionalmente, no existía visibilidad del ciclo de madurez de las pruebas (`ready`, `in_progress`, `planned`), ni un desglose de cobertura por áreas funcionales del restaurante, ni un canal reactivo de streaming que permitiera ver el avance paso a paso con retardos para demostraciones ejecutivas en vivo (*Human Live Demo*).

El **Sub-Plan 3** revoluciona esta arquitectura mediante:
1. **Catálogo Dinámico y Extensible (Patrón Registry):** Desacoplamiento total entre frontend y backend bajo el principio *Zero-Code Frontend Addition*. Los casos de prueba se declaran en el backend y el frontend los descubre reactivamente.
2. **Los 7 Dominios Canónicos de Negocio Gastronómico:** Clasificación exhaustiva en `tenancy`, `auth_rbac`, `inventory`, `recipes`, `procurement`, `finops` y `pos`, estructurando 38 casos de prueba canónicos.
3. **Métricas de Madurez y Cobertura en Tiempo Real:** Barra de progreso interactiva con porcentaje global de cobertura y badges diferenciados por madurez (`🟢 Ready`, `🟡 In Progress (Agente 13)`, `⚪ Planned (Roadmap)`).
4. **Streaming Reactivo en Vivo (RFC 8895 Server-Sent Events):** Conexión SSE con eventos `step` y `completed`, capturas visuales de pantalla automáticas y soporte para pausas humanas de 500ms (`slowMoMs`) frente al modo CI optimizado (0ms).
5. **Certificación FinOps y Aislamiento Absoluto:** Guardrail estricto que restringe ejecuciones a esquemas de prueba autorizados (`tenant_qa_lab`, `tenant_genesis`, `tenant_sandbox_fefo`), garantizando $\Delta \text{Balance} = 0$ en clientes reales y cero polución en `public.llm_request_logs`.

---

## 2. Aportes Clave por Agente del Escuadrón

- **Agente 02 (Arquitecto DDD):** Diseñó la arquitectura limpia y contratos en `.agent/memory/subplan3_etapa1_playwright_architecture_spec.md`, definió los tipos inmutables en `sandboxTypes.ts` (0 `any`), las invariantes matemáticas de conteo/cobertura y los contratos REST/SSE.
- **Agente 03 (Especialista en DB & Alembic):** Emitió la certificación `ZERO_DATABASE_IMPACT_CERTIFIED` (`.agent/memory/subplan3_etapa1_database_signoff.md`), comprobando que el orquestador Playwright y streaming SSE operan efímeramente sin alterar esquemas DDL ni requerir nuevas migraciones Alembic (Head 0018 preservado inmutable).
- **Agente 04 (Senior Backend Dev):** Implementó en `sandbox_service.py` el catálogo `_PLAYWRIGHT_TESTS_REGISTRY` con 38 casos, el método `get_catalog()`, `trigger_run()` con scopes (`all`, `domain`, `test`), el generador asíncrono SSE `stream_run_events()` y los endpoints en `sandbox_router.py` respaldados por schemas Pydantic v2 en `schemas_sandbox.py`.
- **Agente 05 (Senior Frontend Dev):** Construyó el cliente API y conector SSE en `sandboxApi.ts`, refactorizó `PlaywrightRunnerSandboxView.tsx` con acordeones colapsables por dominio, barra de cobertura global, selector Live Demo (500ms) vs CI Headless (0ms), selector de navegadores (Chromium/Firefox/WebKit) y terminal oscura de streaming con enlaces a screenshots y 15 tests Vitest.
- **Agente 06 (Ingeniero de IA OppyFy, RAG & FinOps):** Emitió la certificación formal `APPROVED_ZERO_CREDIT_LEAK_AND_ISOLATED` (`.agent/memory/subplan3_etapa3_ai_finops_signoff.md`), auditando la suite del dominio `finops` (`pw_finops_01_token_discount`), la invariante de balance financiero intacto en producción y el streaming 100% efímero en memoria sin contaminación analítica.
- **Agente 07 (Especialista i18n & FX):** Certificó la paridad bilingüe ES/EN de títulos, descripciones y badges de los 7 dominios en `platform_admin.json`, asegurando consistencia cultural gastronómica y formateo de latencias.
- **Agente 08 (Entornos & Observabilidad):** Certificó la observabilidad distribuida (`.agent/memory/subplan3_etapa3_environments_observability_signoff.md`), verificando propagación simétrica W3C `traceparent` y `X-Trace-ID`, fail-fast en producción ante corridas no confirmadas (HTTP 400), timestamps ISO 8601 UTC y cómputo de SLA percentil P95.
- **Agente 13 (Navegador Real Playwright):** Tomó la asignación de desarrollo activo de las pruebas `in_progress` en navegadores reales (`pw_inventory_01_fefo_alerts` y `pw_finops_01_token_discount`), integrándose sin fricciones con el nuevo catálogo dinámico.
- **Agente 12 (Tech Writer & OpenSpec/Graphify):** Actualizó las especificaciones OpenSpec en las dos bóvedas (`business-domain` y `engineering-code`), sincronizó el grafo de conocimiento Graphify AST con la nueva suite Playwright, validó los gates de arquitectura y consolidó el diario y reporte de traspaso.

---

## 3. Estado de Calidad y Cierre

- **Tests Backend:** 51/51 tests pasando (31 unitarios de API y guardrails en `test_platform_admin_sandbox.py` + 20 de observabilidad, W3C traceparent y fail-fast en `test_sandbox_observability_and_environments.py`).
- **Tests Frontend:** 84/84 tests Vitest pasando al 100% (15 tests en `PlaywrightRunnerSandboxView.test.tsx`, 21 en `MockDataMasterSwitchAndPresets.test.tsx`, 20 en `SandboxI18nAndFx.test.tsx`, 14 en `SandboxViews.test.tsx` y 14 en `SandboxApiAndTelemetry.test.ts`).
- **Fast-Test Harness:** 703/703 tests pasando al 100% en `python scripts/harness.py test-fast`.
- **Typecheck Estricto:** 0 errores en backend (`mypy` en schemas, service y router) y 0 errores en frontend (`tsc --noEmit`).
- **Arquitectura OpenSpec:** 100% verde en `oppytec-backend/tests/architecture/test_openspec_bipartition_and_sync.py` (cero SQL/código técnico en bóveda de negocio y emparejamiento 1:1 con ingeniería).
- **Graphify AST:** 148 nodos, 191 aristas, visualizador interactivo HTML actualizado.
- **Integridad Anti-Trampa:** 100% verificado (`python scripts/harness.py verify-evals`).
