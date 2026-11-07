# Diario del Escuadrón — 2026-11-05: Sub-Plan 2 Switch Maestro de Mock Data y Presets Gastronómicos Canónicos

- **Fecha:** 5 de noviembre de 2026
- **Hito:** Finalización y Certificación del Sub-Plan 2 (Switch Maestro `demo` vs `clean`, 4 Presets Gastronómicos Canónicos y Acción Factory Reset en Platform Admin)
- **Escuadrón:** Agentes 02, 03, 04, 05, 07, 08 y 12.

---

## 1. El Problema de Negocio y Operación

Hasta el Sub-Plan 1, las demostraciones comerciales y pruebas de onboarding convivían con un problema recurrente: el cliente HTTP recurría de manera opaca a datos simulados de respaldo (*fallbackData*) ante cualquier respuesta vacía o fallo de red. Esto impedía auditar fehacientemente los estados vacíos auténticos (*Empty States*) de la plataforma, un requisito indispensable para verificar la experiencia inicial de nuevos restaurantes clientes.

El **Sub-Plan 2** solventa esta problemática mediante:
1. **Switch Maestro Reactivo (`demo` vs `clean`)**: Permite conmutar con un clic entre un modo asistido de venta/capacitación (*Demo Mode*) y un modo estricto de base de datos virgen (*Clean DB Mode*) que suprime incondicionalmente cualquier fallback simulado.
2. **Los 4 Presets Gastronómicos Canónicos**: Arquetipos realistas para Comida Rápida (Pollo King), Carnes Angus & Cava, Hotel & Desayuno Buffet y Base Virgen (Clean Slate).
3. **Acción Factory Reset**: Restauración idempotente e instantánea de fábrica en esquemas de laboratorio aislados con confirmación dialogal explícita.

---

## 2. Aportes Clave por Agente del Escuadrón

- **Agente 02 (Arquitecto DDD):** Formuló el pre-spec arquitectónico en `.agent/memory/subplan2_etapa1_mockdata_architecture_spec.md`, definió los contratos TypeScript en `mockDataContracts.ts`, el esquema del Switch Maestro y la matriz de datos de los 4 presets canónicos.
- **Agente 03 (Especialista en DB & Alembic):** Certificó `ZERO_DATABASE_IMPACT_CERTIFIED`, confirmando que los presets y la acción de reset reutilizan los esquemas existentes (`tenant_qa_*`, `tenant_sandbox_*`) sin requerir migraciones DDL adicionales.
- **Agente 04 (Senior Backend Dev):** Implementó en `sandbox_router.py` los endpoints `GET /presets`, `GET /presets/{id}` y `POST /mock-data/reset`, junto a schemas Pydantic v2 en `schemas_sandbox.py` y lógica de purga y resembrado en `sandbox_service.py`.
- **Agente 05 (Senior Frontend Dev):** Construyó el almacenamiento reactivo `mockModeStorage.ts`, inyectó la cabecera `X-OppyTec-Mock-Mode` en `httpClient.ts`, creó los módulos de presets en `presets/` y los componentes UI `MockDataMasterSwitch.tsx` y modal Factory Reset en `MockDataSandboxView.tsx`.
- **Agente 07 (Especialista i18n & FX):** Completó la sincronización bilingüe (ES/EN) de los títulos, subtítulos, descripciones y badges de los 4 presets en `platform_admin.json`.
- **Agente 08 (Entornos & Observabilidad):** Instrumentó los guardrails de entorno canónico (`_enforce_sandbox_environment_guard`), bloqueando Factory Reset en producción (403), exigiendo confirmación en staging (400) y creando spans OpenTelemetry dedicados.
- **Agente 12 (Tech Writer & OpenSpec/Graphify):** Actualizó las especificaciones OpenSpec en las bóvedas de negocio e ingeniería, extendió `scripts/harness.py`, sincronizó el grafo Graphify AST a 147 nodos y 189 aristas, y documentó el cierre en la bitácora de traspaso.

---

## 3. Estado de Calidad y Cierre

- **Tests Backend:** 39/39 tests pasando (unit API, presets, reset y aislamiento de entornos).
- **Tests Frontend:** Suites Vitest pasando al 100% (21 tests en `MockDataMasterSwitchAndPresets.test.tsx`, además de suites de vistas, telemetría e i18n).
- **Graphify AST:** 147 nodos, 16 routers, 20 migraciones, 37 suites de prueba, 189 aristas.
- **Verify-Evals:** 100% verde (cero alteraciones en `.agent/rules/` y `.agent/evals/`).
