# ADR-022 — Etapa 2: Construcción Backend
## Gestor Central de Mock Data vs Clean Slate y Respaldo Canónico en Sandbox

- **Agente Responsable:** Agente 04: Desarrollador Backend Senior (`04-backend-senior-dev`)
- **Fecha UTC:** 2026-11-07T00:48:00Z
- **Hito:** ADR-022 — Etapa 2 (Construcción Backend completada con 100% pruebas pasando, Ruff 0 errores, Mypy 0 errores)
- **Destinatarios:**
  - Orquestador General (`parent`)
  - Agente 05: Frontend Senior Dev (`05-frontend-senior-dev`)
  - Agente 09: QA Parity & Test Engineer (`09-qa-parity-and-test-engineer`)
  - Agente 10: Cybersecurity Red Team (`10-cybersecurity-redteam-auditor`)
  - Agente 12: Tech Writer OpenSpec & Archify (`12-tech-writer-openspec-archify`)

---

### 1. Completed

1. **Gobernanza Pre-ejecución Obligatoria (Graphify):**
   - Ejecutadas consultas AST `python3 scripts/harness.py nav "sandbox"` y `python3 scripts/harness.py nav "tenancy"` antes de editar código, y reservados los nodos AST con `claim-ast`.

2. **Gestor Central de Mock Data y Clean Slate (`oppytec-backend/src/core/mock_data_manager.py`):**
   - `load_mock_data_backup() -> dict[str, Any]`: carga y valida `oppytec-backend/fixtures/mock_data_backup.json` (secciones `metadata`, `postgresql_pre_clean_snapshot`, `backend_modules`) retornando copias profundas aisladas (`copy.deepcopy`).
   - `purge_all_runtime_mock_stores() -> dict[str, int]`: vacía en memoria todos los datos mock/demostrativos de routers y servicios para dejar el sistema en estado **Clean Slate 100% limpio**:
     * `src/modules/tenancy/presentation/router.py`: vacía `_holdings_store`, `_legal_entities_store`, `_tenants_store`, conservando `_plans_store` con los 3 planes base (`DEFAULT_SYSTEM_PLANS`).
     * `src/modules/identity/presentation/router.py`: vacía `_CLIENT_USERS_STORE` y asegura que `_GLOBAL_USERS_STORE` contenga únicamente la entrada `1` del SuperUser Génesis (`OppyTec.Admin@gmail.com` / `oppytec.admin`, contraseña `oppytec2026`) y los 5 roles base (`TENANT_BASE_ROLES`).
     * `src/modules/catalog/presentation/router.py`: vacía `_products_store`, `_categories_store`, `_brands_store`, `_container_types_store` y reinicia sus secuencias.
     * `src/modules/oppy_ai/presentation/router.py`: vacía `_worker_wallets_store` y `_permission_grants_store`.
     * `src/modules/operations/presentation/router_actividades.py`: limpia `_actividades_service` (notas, tareas, plantillas, turnos).
     * `src/modules/inventory/presentation/router.py`: limpia `_inventory_service`, `_waste_service`, `_physical_count_service`, `_merma_analytics_service`.
     * `src/modules/events/presentation/router.py`: limpia `_salon_service` y `_event_service` si están inicializados.
     * `src/modules/tenancy/presentation/sandbox_router.py`: limpia `_sandbox_service._history_ring_buffer`.
     * `src/modules/tenancy/presentation/platform_admin_router.py`: limpia `_token_consumption_service._logs` y `_jev_consumption_service._logs`.
   - `restore_runtime_mock_stores(preset_id: str | None = None) -> dict[str, int]`: restaura bajo demanda en memoria todos los stores desde `oppytec-backend/fixtures/mock_data_backup.json`.
   - `reset_default_demo_stores() -> dict[str, int]`: restaura el estado predeterminado demostrativo para aislamiento determinista en suites `pytest`.

3. **Integración con `src/main.py`, `tenancy/presentation/router.py`, `platform_admin_router.py`, `sandbox_service.py` y `sandbox_router.py`:**
   - En `src/main.py`: incorporado `_app_lifespan` que invoca automáticamente `purge_all_runtime_mock_stores()` cuando no se ejecuta bajo `pytest` (`"PYTEST_CURRENT_TEST" not in os.environ` y `os.environ.get("OPPYTEC_DEMO_MODE") != "1"`).
   - En `src/modules/tenancy/presentation/router.py` y `platform_admin_router.py`: soporte de la cabecera `X-OppyTec-Mock-Mode: clean` en `GET /api/v1/tenancy/holdings`, `GET /api/v1/tenancy/legal-entities`, `GET /api/v1/tenancy/tenants`, `GET /api/v1/tenancy/client-users`, `GET /api/v1/tenancy/dashboard/summary`, `GET /api/v1/platform-admin/token-consumption` y `GET /api/v1/platform-admin/jev-consumption`, retornando colecciones vacías y contadores en `0` cuando no existen registros reales creados tras el Clean Slate.
   - En `src/modules/tenancy/application/sandbox_service.py` y `sandbox_router.py`:
     * `factory_reset_mock_data`: invoca `purge_all_runtime_mock_stores()` cuando `target_preset_id == "clean-slate"` (0 holdings, 0 tenants, 0 productos, 0 lotes, 0 recetas) y `restore_runtime_mock_stores(payload.target_preset_id)` en caso contrario.
     * `generate_mock_data`: invoca `restore_runtime_mock_stores()` cuando `payload.dry_run is False`.
     * Nuevo endpoint `GET /api/v1/platform-admin/sandbox/mock-data/backup` en `sandbox_router.py` protegido por `RequireGlobalPermission("platform_admin.sandbox.access")`.

4. **Pruebas Unitarias Co-creadas 1:1 (`oppytec-backend/tests/unit/test_mock_data_manager.py`):**
   - Cobertura completa de carga e inmutabilidad del JSON de respaldo, purga total a Clean Slate, preservación exclusiva del SuperUser `OppyTec.Admin@gmail.com` (`oppytec2026`), restauración bajo demanda, cabecera `X-OppyTec-Mock-Mode: clean` y endpoints de Sandbox.
   - Resultado: **98/98 tests pasados** (`test_mock_data_manager.py`, `test_platform_admin_sandbox.py`, `test_sandbox_observability_and_environments.py`, `tests/architecture/`), **Ruff 0 errores**, **Mypy 0 errores**.

---

### 2. Friction & Failures

- **Resolución de Submódulos vs `APIRouter` en Mypy:** Importar `from src.modules.<mod>.presentation import router as ...` resolvía la instancia `APIRouter` re-exportada en `__init__.py` en lugar del submódulo `router.py`. Se corrigió importando directamente las colecciones desde `src.modules.<mod>.presentation.router` y accediendo a `sys.modules` cuando se requerían contadores de secuencia a nivel de módulo.

---

### 3. Next Exact Action

- **Etapa 3 y 4 del DAG:** Validación por especialistas de capas cruzadas (Agentes 06, 07, 08) y certificación QA/Seguridad/Documentación (Agentes 09, 10, 11, 12).
