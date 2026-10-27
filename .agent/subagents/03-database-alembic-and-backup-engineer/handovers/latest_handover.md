# Reporte de Traspaso (`Handover`) — Agente 03: Especialista en Base de Datos, Alembic y Backups 4-Capas

- **Fecha UTC:** 2026-10-26T21:00:00Z
- **Fase / Hito:** Fase 1 del `PLAN_MAESTRO_OPPYFY_AI.md`: Modelado de Persistencia Multi-Tenant SQLAlchemy 2.0 Async (`TenantBase` / `PublicBase`), Migración Lineal Correlativa Alembic 0010 e Idempotencia DDL Multi-Tenant.
- **Estado de Certificación:** `OPPYFY_AI_PERSISTENCE_AND_ALEMBIC_0010_CERTIFIED` (Alembic 0001..0010 verificado, 2/2 tests de arquitectura correlativa pasando al 100% verde, 8/8 tests de modelos OppyFy pasando al 100% verde).

---

## 1. Completed (Qué se ejecutó y validó)

1. **Migración Lineal Correlativa Alembic 0010 (`0010_tenant_oppyfy_custom_rbac_and_credit_wallets.py`):**
   - Ubicación: [`oppytec-backend/alembic/versions/0010_tenant_oppyfy_custom_rbac_and_credit_wallets.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/alembic/versions/0010_tenant_oppyfy_custom_rbac_and_credit_wallets.py).
   - Metadatos:
     * `revision = "0010_tenant_oppyfy_custom_rbac_and_credit_wallets"`
     * `down_revision = "0009_tenant_procurement_purchases_and_suppliers"`
     * `migration_scope = "tenant"`
   - DDL en esquemas de cliente `tenant_*`:
     * `oppyfy_domains`: `id` (BigInteger PK autoincrement), `domain_key` (VARCHAR 100 UNIQUE), `name_es` (VARCHAR 150), `name_en` (VARCHAR 150), `icon` (VARCHAR 50), `is_active` (BOOL), `sort_order` (INT), timestamps.
     * `oppyfy_subdomains`: `id` (BigInteger PK), `domain_id` (FK a `oppyfy_domains.id` CASCADE), `subdomain_key` (VARCHAR 100 UNIQUE), `name_es`, `name_en`, `module_slug` (VARCHAR 100), `allowed_tool_functions` (JSONB), `can_view_costs_default` (BOOL), `sort_order` (INT), `is_active` (BOOL), timestamps.
     * `oppyfy_permission_grants`: `id` (UUID PK), `user_id` (INT), `subdomain_id` (FK a `oppyfy_subdomains.id` CASCADE), `role_id` (INT nullable), `effect` (VARCHAR 16 default 'ALLOW'), `can_query` (BOOL), `can_view_costs` (BOOL), `expires_at` (TIMESTAMPTZ nullable), `max_prompts` (INT nullable), `prompts_used` (INT default 0), `temp_credit_ceiling` (NUMERIC(12,2) nullable), `temp_credits_used` (NUMERIC(12,2) default 0.00), timestamps.
     * `oppyfy_worker_credit_wallets`: `id` (BigInteger PK), `user_id` (INT UNIQUE), `is_oppyfy_enabled` (BOOL default true), `assigned_credit_ceiling` (NUMERIC(12,2) nullable), `credits_spent_total` (NUMERIC(12,2) default 0.00), `balance_override` (NUMERIC(12,2) nullable), timestamps.
     * `oppyfy_prompt_audit_log`: `id` (BigInteger PK), `user_id` (INT), `prompt_text` (TEXT), `status` (VARCHAR 50: ALLOWED, BLOCKED_UNAUTHORIZED_PROMPT), `resolved_domain` (VARCHAR 100 nullable), `resolved_tools` (JSONB), `tokens_spent` (INT default 0), `credits_deducted` (NUMERIC(12,2) default 0.00), `created_at` (TIMESTAMPTZ).
     * `oppyfy_rbac_audit_log`: `id` (BigInteger PK), `actor_user_id` (INT), `target_user_id` (INT), `action` (VARCHAR 100), `details` (JSONB default '{}'), `created_at` (TIMESTAMPTZ).
   - DDL en esquema global `public`:
     * `public.ai_credit_packs`: Paquetes de créditos IA independientes para compra Add-On configurables por el Superadmin (`id`, `pack_name`, `credits_amount` NUMERIC(14,2), `price_clp` NUMERIC(14,2), `price_usd` NUMERIC(14,2), `is_popular` BOOL, `is_active` BOOL, `sort_order` INT, `created_at`, `updated_at`).
     * `public.ai_model_configs`: Columnas `cached_cost_per_1m_usd` (NUMERIC(12,6)) y `embedding_cost_per_1m_usd` (NUMERIC(12,6)).
     * `public.spec_chunks`: Columna `token_count` (INT default 0).
   - Introspección dinámica idempotente (`_has_table`, `_has_column`, `_has_index`) para soportar tanto esquemas vírgenes como inquilinos con tablas previas de 0002.
   - Reversibilidad LIFO simétrica con `downgrade()` real.

2. **Modelos SQLAlchemy 2.0 Async (`oppytec-backend/src/modules/oppy_ai/infrastructure/models.py`):**
   - Reflejo fiel de las tablas bajo `TenantBase` para esquemas `tenant_*` y `PublicBase` para `public`.
   - Propiedades de compatibilidad hacia atrás (`slug` <-> `domain_key`, `name` <-> `name_es`, `allocated_credits` <-> `assigned_credit_ceiling`, `consumed_credits` <-> `credits_spent_total`, `decision_status` <-> `status`, `credits_consumed` <-> `credits_deducted`).
   - Cero uso de `float`, todos los cálculos monetarios y de tokens en `Decimal` con `Numeric`.

3. **Verificación y Pruebas Ejecutadas:**
   - `python scripts/db_migration.py verify`: Alembic correlative migration chain verified OK.
   - `alembic heads`: Unico head activo `0010_tenant_oppyfy_custom_rbac_and_credit_wallets (head)`.
   - `uv run pytest tests/architecture/test_alembic_integrity.py`: 2/2 passed in 0.15s (100% verde).
   - `uv run pytest tests/unit/modules/test_oppy_ai_services.py`: 8/8 passed in 0.26s (100% verde).
   - `alembic upgrade head`: DDL ejecutado exitosamente contra PostgreSQL real en `public` y esquemas `tenant_*`.

---

## 2. Friction & Failures

- **Dependencias FK Preexistentes de 0002 al revertir `downgrade()`:**
  * Al auditar `downgrade()`, se detectó que tablas de 0002 (`tenant_documents`, `document_chunks`) tienen FKs hacia `oppyfy_subdomains`. Si un tenant posee estas tablas, hacer `DROP TABLE oppyfy_subdomains` provocaría `DependentObjectsStillExistError`.
  * Solución implementada: En el `downgrade()` de 0010, se verifica la presencia de `tenant_documents`. Si existe, se revierten únicamente las columnas e índices añadidos en 0010 sin destruir la tabla base requerida por 0002; si no existen dependencias, se realiza el drop completo de forma segura.

---

## 3. Next Exact Action

- **Para Agente 04 (`04-backend-senior-dev`) y Agente 06 (`06-ai-oppyfy-and-jev-engineer`):**
  * Continuar con la **Fase 2 de `PLAN_MAESTRO_OPPYFY_AI.md`**: Implementación de `MeteredAIService`, router JEV con herramientas deterministas (`operational_tools/`), redacción física de costos (*Hard-Code Data Stripping*) y endpoints REST RFC 7807 (`/api/v1/oppyfy/*` y `/api/v1/platform-admin/token-consumption`).
