# Diario del Escuadrón — 2026-11-05: Sub-Plan 1 Consola "Lab & QA Sandbox" (Platform Admin)

- **Fecha:** 5 de noviembre de 2026
- **Hito:** Finalización y Certificación del Sub-Plan 1 (Consola "Lab & QA Sandbox" en Platform Admin)
- **Escuadrón:** Agentes 02, 03, 04, 05, 07, 08 y 12.

---

## 1. El Problema de Negocio y Operación

Al evolucionar una plataforma SaaS gastronómica multi-inquilino de alta disponibilidad, los equipos de calidad, soporte y DevOps se enfrentaban a un dilema permanente: ¿cómo probar migraciones complejas, simular mermas masivas de productos por fecha FEFO y disparar pruebas de extremo a extremo sin arriesgar la consistencia de los datos productivos ni requerir scripts manuales en la terminal de cada servidor?

La consola **Lab & QA Sandbox** resuelve este desafío ofreciendo a los administradores de plataforma una consola visual protegida (`/admin/sandbox`) para generar datos sintéticos, correr suites Playwright en vivo y simular saltos temporales FEFO con estricto aislamiento de base de datos.

---

## 2. Aportes Clave por Agente del Escuadrón

- **Agente 02 (Arquitecto DDD):** Formuló el pre-spec arquitectónico en `.agent/memory/subplan1_etapa1_architecture_spec.md`, definió los contratos TypeScript en `sandboxTypes.ts`, las rutas de navegación bajo `AdminLayout` y el RBAC de 3 niveles (`platform_admin.sandbox.access` y `platform_admin.sandbox.manage`).
- **Agente 03 (Especialista en DB & Alembic):** Emitió la certificación `ZERO_DATABASE_IMPACT_CERTIFIED`, verificando que la consola no requería nuevas migraciones Alembic y manteniendo congelado el head `0018_public_holding_hub_credit_distribution_and_purchases`.
- **Agente 04 (Senior Backend Dev):** Implementó `sandbox_router.py` en `/api/v1/platform-admin/sandbox`, `sandbox_service.py` y `schemas_sandbox.py` con 100% tipado estricto Pydantic V2 y pruebas unitarias.
- **Agente 05 (Senior Frontend Dev):** Construyó las 3 vistas interactivas en `oppytec-frontend/src/features/platform-admin/sandbox/` (`MockDataSandboxView`, `PlaywrightRunnerSandboxView`, `FefoDatesSandboxView`), el layout de pestañas y la integración en `AdminSidebar.tsx`.
- **Agente 07 (Especialista i18n & FX):** Completó la paridad bilingüe ES/EN en `locales/*/platform_admin.json` y el formateo multimoneda contable sin números flotantes.
- **Agente 08 (Entornos & Observabilidad):** Blindó los 5 entornos canónicos con fail-fast estricto en producción (`PRODUCTION_MUTATION_FORBIDDEN`), confirmación en staging, instrumentación OpenTelemetry con W3C TraceContext y logs estructurados.
- **Agente 12 (Tech Writer & OpenSpec/Graphify):** Elaboró las especificaciones bipartitas (negocio e ingeniería), actualizó `scripts/harness.py`, sincronizó el grafo Graphify AST a 143 nodos y 36 suites, y cerró la bitácora de handover.

---

## 3. Estado de Calidad y Cierre

- **Tests Backend:** 22/22 tests pasando (13 unit API + 9 observabilidad y aislamiento de entornos).
- **Tests Frontend:** Suites Vitest pasando al 100% (`SandboxViews.test.tsx`, `SandboxApiAndTelemetry.test.ts`, `SandboxI18nAndFx.test.tsx`).
- **Graphify AST:** 143 nodos, 16 routers, 20 migraciones, 36 suites de prueba, 181 aristas.
- **Verify-Evals:** 100% verde (cero alteraciones en `.agent/rules/` y `.agent/evals/`).
