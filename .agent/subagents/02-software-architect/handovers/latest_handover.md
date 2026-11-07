# Reporte de Traspaso (`Handover`) — Agente 02: Arquitecto de Software DDD & Clean Architecture

- **Fecha UTC:** 2026-11-07T00:05:00Z
- **Módulo:** Transversal Full-Stack — Estado Virgen por Defecto (*Clean Slate*), Bóveda de Respaldo Mock Data en JSON y Desacoplamiento Reactivo
- **Fase:** Etapa 1 — Definición de Arquitectura y Contratos (`ADR-022`)
- **Evaluación Rúbrica:** 10/10 (Aprobado sin reservas)

---

## 1. Completed (Qué se realizó)

1. **Pre-ejecución Graphify (Regla 6 de `AGENTS.md`):**
   - Ejecutado `python3 scripts/harness.py nav "sandbox"` (21 nodos mapeados: `frontend:sandbox_mock_data_view`, `service:sandbox_manager`, `router:platform_admin_sandbox`, `frontend:canonical_gastronomic_presets`) y `python3 scripts/harness.py nav "bootstrap"` (`core:bootstrap`).
   - Reservados atómicamente los nodos AST con `python3 scripts/harness.py claim-ast`.

2. **Creación del Contrato Arquitectónico Canónico ([`ADR-022-clean-slate-and-mock-data-backup-architecture.md`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/docs/adr/ADR-022-clean-slate-and-mock-data-backup-architecture.md)):**
   - **Bóveda de Respaldo Mock Data (`mock_data_backup.json`):** Definido el contrato de esquema JSON dual (`oppytec-backend/fixtures/mock_data_backup.json` y `oppytec-frontend/src/shared/mock/mock_data_backup.json`) que preserva los 22 datasets operativos y de plano de control (`holdings`, `legal_entities`, `tenants`, `client_users`, `catalog`, `inventory`, `fefo_batches`, `kardex`, `counts`, `mermas`, `alerts`, `recipes`, `combos`, `option_groups`, `procurement`, `invoices`, `events`, `consumo`, `activities`, `projection`, `oppyfy`, `finops_logs`) junto con los 4 presets gastronómicos (`RESTAURANT_FINE_DINING`, `HOTEL_BUFFET`, `DARK_KITCHEN`, `FAST_CASUAL_CHAIN`).
   - **Estado Base "Clean Slate" (100% Virgen por Defecto):** Formalizada la invariante donde en PostgreSQL (`oppytec_dev`) y en la memoria del Backend solo persiste la semilla Génesis (`OppyTec.Admin@gmail.com` / `oppytec.admin`, 7 módulos base, 4 roles globales con permiso `*.*.*`, 3 planes comerciales SaaS y 6 modelos IA + política FinOps), manteniendo `0` holdings, `0` entidades legales, `0` sucursales/tenants, `0` usuarios clientes y `0` registros transaccionales/operativos.
   - **Desacoplamiento Reactivo en Frontend (`oppytec-frontend`):** Especificado el selector funcional `selectByMockMode(demoData, cleanData)` en [`mockModeStorage.ts`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/shared/mock/mockModeStorage.ts), la inicialización por defecto en `"clean"` para navegadores reales (preservando compatibilidad con suites `Vitest`) y la prohibición de inyectar `MOCK_*`, `INITIAL_*_MOCK` o `FALLBACK_*` cuando `isMockDataEnabled() === false`.
   - **Evaluación Gate JEV (`¿Lo puede hacer JEV (Sí/No)?`):** Documentado y justificado por qué la hidratación/purga de Mock Data es una operación transaccional 100% determinista en runtime.

---

## 2. Friction & Failures (Fricciones y Desafíos Resueltos)

- **Equilibrio entre Estado Clean Slate en Navegador Real y Suites de Tests Existentes:** Muchas suites unitarias de `Vitest` asumen el modo `"demo"` si no configuran `localStorage` explícitamente. En `ADR-022` se diseñó la estrategia de migración controlada (`MOCK_DATA_CLEAN_SLATE_MIGRATED_KEY`) que distingue el entorno de navegador interactivo real (iniciando en `"clean"`) del runner de pruebas unitarias, evitando regresiones artificiales en tests legacy mientras garantiza que el usuario real vea el sistema 100% limpio por defecto.

---

## 3. Next Exact Action (Siguiente Acción Exacta)

1. **Agente 03 (`03-database-alembic-and-backup-engineer`):** Ejecutar la limpieza quirúrgica de PostgreSQL (`oppytec_dev`) eliminando todo esquema `tenant_*` residual y truncando las tablas no-Génesis (`holdings`, `legal_entities`, `tenants`, etc.), preservando únicamente `OppyTec.Admin@gmail.com` y catálogos Génesis, y respaldando los datos en `oppytec-backend/fixtures/mock_data_backup.json`.
2. **Agente 04 (`04-backend-senior-dev`):** Inicializar las tiendas en memoria del Backend (`sandbox_manager.py`, `tenants`, `users`, `catalog`, `inventory`, `operations`, `recipes`, `procurement`, `analytics`, `oppyfy`, `finops`) en estado Clean Slate (`mode="clean"`, listas vacías `[]`), cargando datos desde `oppytec-backend/fixtures/mock_data_backup.json` únicamente cuando se active el modo Demo en `/admin/sandbox/mock-data`.
3. **Agente 05 (`05-frontend-senior-dev`):** Crear `oppytec-frontend/src/shared/mock/mock_data_backup.json`, implementar `selectByMockMode` y migración a `"clean"` en `mockModeStorage.ts`, y desacoplar todos los arreglos `MOCK_*` / `INITIAL_*_MOCK` / `FALLBACK_*` en todas las vistas, hooks y `httpClient.ts`.
