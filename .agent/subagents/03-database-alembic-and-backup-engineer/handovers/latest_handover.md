# Reporte de Traspaso (`Handover`) — Agente 03: Especialista en Base de Datos, Alembic y Backups 4-Capas

- **Fecha UTC:** 2026-11-07T00:18:00Z
- **Fase / Hito:** Etapa 1 — Extracción/Respaldo Maestro de Mock Data (`mock_data_backup.json`), Limpieza Total (`Clean Slate`) y Bootstrap Génesis Idempotente (`clean_and_seed_genesis_db.py`) en vivo sobre PostgreSQL (`oppytec-postgres`).
- **Estado de Certificación:** `CLEAN_SLATE_GENESIS_CERTIFIED` (100% verificado en `oppytec-postgres`: `holdings=0`, `legal_entities=0`, `tenants=0`, `client_users=0`, `global_users=1`, `app_modules=7`, `global_roles=4`, `global_permissions=1`, `system_plans=3`, `ai_model_configs=6`, `saas_ai_policy_config=1`).

---

## 1. Completed (Qué se ejecutó y validó)

1. **Gobernanza Pre-ejecución Obligatoria con Graphify (`python3 scripts/harness.py nav`):**
   - Ejecutado `python3 scripts/harness.py nav "bootstrap"` y `python3 scripts/harness.py nav "tenancy"` antes de tocar cualquier archivo.
   - Reclamados los nodos AST con `python3 scripts/harness.py claim-ast --worker 03-database-alembic-and-backup-engineer`.

2. **Extracción y Creación del Documento Maestro de Respaldo Mock Data (`mock_data_backup.json`):**
   - Extraída el 100% de la data mock histórica/demostrativa estructurada en 3 grandes bloques:
     * `postgresql_pre_clean_snapshot`: Respaldo íntegro de las filas existentes antes de la limpieza en `public.holdings` (7), `public.legal_entities` (14) y `public.tenants` (14).
     * `backend_modules`: Datos extraídos de `tenancy/presentation/router.py` (`_PLANS`, `_HOLDINGS`, `_TENANTS`), `identity/presentation/router.py` (`_ROLES`, `_USERS`), `catalog/presentation/router.py` (`_CATEGORIES`, `_SUPPLIERS`, `_PRODUCTS`, `_RECIPES`, `_COMBOS`, `_PURCHASE_INVOICES`, `_INVENTORY_ALERTS`, `_IMPORT_HISTORY`), `oppy_ai/presentation/router.py` (`_AI_MODELS`, `_CREDIT_PACKS`, `_HOLDING_QUOTAS`, `_TENANT_QUOTAS`, `_USAGE_SERIES`, `_OPPYFY_RECS`, `_JEV_MATRIX`), y `sandbox_service.py` (`_SANDBOX_DATA_PROFILES`, `_SANDBOX_R2_QUOTAS`, `_SANDBOX_FEFO_BATCHES`, `_SANDBOX_WEBHOOKS`).
     * `frontend_modules`: Datos extraídos de los 15 archivos de datos mock del frontend (`inventory/mockData.ts`, `inventory/alerts/mockData.ts`, `activities/mockData.ts`, `consumo/mockData.ts`, `events/mockData.ts`, `historial/mockData.ts`, `invoices/mockData.ts`, `procurement/mockData.ts`, `projection/mockData.ts`, `gestion/useGestion.ts`, `gestion/hooks/useRecetas.ts`, `gestion/hooks/useCombos.ts`, `gestion/hooks/useGruposOpciones.ts`, `holding-hub/constants.ts`, `platform-admin/types.ts`).
   - Guardado en copias idénticas (353,050 bytes) en:
     * [`oppytec-backend/fixtures/mock_data_backup.json`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/fixtures/mock_data_backup.json)
     * [`oppytec-frontend/src/shared/mock/mock_data_backup.json`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/shared/mock/mock_data_backup.json)

3. **Script Idempotente de Limpieza Total y Bootstrap Génesis (`oppytec-backend/scripts/clean_and_seed_genesis_db.py`) y Ejecución en Vivo (`oppytec-postgres`):**
   - Creado [`oppytec-backend/scripts/clean_and_seed_genesis_db.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/scripts/clean_and_seed_genesis_db.py) y actualizado `oppytec-backend/.env` (`SUPERUSER_GENESIS_EMAIL=OppyTec.Admin@gmail.com`, `SUPERUSER_GENESIS_PASSWORD=oppytec2026`).
   - Ejecutado contra `oppytec-postgres` (`oppytec_dev`, usuario `db_user`):
     * Eliminación de cualquier esquema `tenant_*` (`DROP SCHEMA IF EXISTS ... CASCADE`).
     * Purga total (`TRUNCATE TABLE ... RESTART IDENTITY CASCADE`) de las 21 tablas contaminadas/transaccionales en `public` (`holding_credit_distributions`, `holding_credit_purchases`, `client_user_tenant_access`, `client_users`, `tenant_modules`, `tenants`, `legal_entities`, `holdings`, `llm_request_logs`, `jev_request_logs`, `audio_request_logs`, `global_audit_activity_log`, `global_audit_rbac_changes`, `fx_audit_log`, `fx_rate_history`, `fx_current_rates`, `ai_credit_packages`, `ai_credit_packs`, `ai_eval_case_results`, `ai_eval_benchmarks`, `backup_execution_logs`).
     * En `public.global_users`: único SuperUser Génesis con `email='OppyTec.Admin@gmail.com'`, `username='oppytec.admin'`, `hashed_password` Argon2id válido para `oppytec2026` (`PasswordHash.recommended().hash("oppytec2026")`), `is_superuser_god=True`, `is_deleted=False`, `preferred_language='es'`, `preferred_currency='CLP'`.
     * En `public.app_modules`: sembrados los 7 módulos de `DEFAULT_APP_MODULES` (`catalog`, `inventory`, `recipes`, `procurement`, `operations`, `analytics`, `oppy_ai`).
     * En `public.global_roles`: sembrados los 4 roles base de `GLOBAL_BASE_ROLES` (`superuser`, `admin`, `supervisor`, `developer`).
     * En `public.global_permissions`: sembrado el permiso comodín `*.*.*`.
     * En `public.system_plans`: asegurados únicamente los 3 planes base (`basic`, `starter`, `enterprise`) de `DEFAULT_SYSTEM_PLANS`.
     * En `public.ai_model_configs` y `public.saas_ai_policy_config`: preservados los 6 modelos IA iniciales y la política SaaS (`id=1`).

4. **Co-Creación 1:1 de Pruebas y Verificación SQL en Vivo:**
   - Creado [`oppytec-backend/tests/unit/test_clean_and_seed_genesis_db.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/tests/unit/test_clean_and_seed_genesis_db.py).
   - Verificado con `ruff check`, `mypy --strict`, y `pytest tests/unit/test_clean_and_seed_genesis_db.py tests/architecture/ -q` (`32 passed, 0 failed`).
   - Verificado directamente por SQL en `oppytec-postgres`: `holdings=0, legal_entities=0, tenants=0, client_users=0, global_users=1, app_modules=7, global_roles=4, global_permissions=1, system_plans=3, ai_model_configs=6, saas_ai_policy_config=1`.

---

## 2. Friction & Failures
- En `public.global_permissions`, la tercera columna de slug en PostgreSQL se denomina `action_slug` (mientras algunos contratos hacen referencia a `function_slug`). El script detecta dinámicamente las columnas de `information_schema.columns` y ejecuta la sentencia estática correspondiente con soporte completo.
- En `tests/conftest.py`, el fixture `default_test_env` sobreescribe `SUPERUSER_GENESIS_PASSWORD` con un valor dummy de test; `_seed_genesis_superuser` fue ajustado para garantizar que el hash Argon2id del usuario Génesis sea siempre el de `oppytec2026` salvo override explícito en `OPPYTEC_GENESIS_RAW_PASSWORD`.

---

## 3. Next Exact Action (Handoff a Etapa 2)
- **Agente 04 (`04-backend-senior-dev`):** Conectar los routers de Backend (`tenancy`, `identity`, `catalog`, `oppy_ai`) a consultas reales SQLAlchemy 2.0 Async contra PostgreSQL (retornando listas vacías `[]` cuando no existan holdings/tenants/productos en lugar de diccionarios mock en memoria) y verificar login real con `OppyTec.Admin@gmail.com` / `oppytec2026`.
- **Agente 05 (`05-frontend-senior-dev`):** Eliminar la inicialización con mock data por defecto en las vistas y hooks del Frontend para reflejar el estado real de la base de datos (0 holdings, 0 tenants, 0 productos) y permitir poblar bajo demanda desde `mock_data_backup.json` en el Sandbox.
