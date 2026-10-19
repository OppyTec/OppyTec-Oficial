---
title: "Bitácora Fase 2: Base de Datos Multi-Schema, Migraciones Correlativas Alembic 0001..N, Bootstrap Génesis y Respaldos en 4 Capas"
phase: "Fase 2"
date: "2026-10-19"
author_agent: "12-tech-writer-openspec-archify"
tags:
  - bitacora
  - fase-2
  - postgresql
  - multi-tenant
  - alembic
  - backups-4-capas
  - archify
---

# 📓 Bitácora Fase 2: Cómo Se Construyó la Base de Datos Multi-Schema, el Motor Alembic sin Conflictos y la Bóveda de Respaldos en 4 Capas

> **Resumen en simple para personas:**  
> En la **Fase 2**, el Escuadrón resolvió de raíz los problemas históricos de base de datos de `OppyTec-Legacy`. Ahora OppyTec v2.0 separa físicamente el **Plano de Control Global (`public`)** de cada **Sucursal Cliente (`tenant_<slug>`)**, garantiza una jerarquía corporativa exacta (`Holding -> Entidad Legal 1:1 -> Tenant`), reemplaza el desorden de hashes aleatorios de Alembic por **migraciones correlativas lineales (`0001_public_...`, `0002_tenant_...`)** con resolución automática de ramas paralelas (`make migration-rebase`), siembra al **SuperUser Génesis (`oppytec.admin`)** sin un solo secreto escrito en el código (`SecretStr`) y protege cada restaurante con **Respaldos Cifrados en 4 Capas (`.sql.zst.age`)** capaces de restaurar a un único local sin afectar a los demás.

---

## 1. ¿Qué Construyó Cada Agente del Escuadrón en la Fase 2?

### 🗄️ Agente 03 (`03-database-alembic-and-backup-engineer`) + Agente 02 (`02-software-architect`) — Persistencia Multi-Schema, Alembic Lineal y Backups 4-Capas

1. **Separación Estricta de Metadatos (`PublicBase` vs `TenantBase`):**
   - **`oppytec-backend/src/core/database.py`:** Configuró el motor asíncrono SQLAlchemy 2.0 con `get_public_db_session()` (apuntando a `public`) y `get_tenant_db_session(tenant_slug)` que ejecuta `SET LOCAL search_path TO "tenant_<slug>", public` dentro de la transacción y limpia automáticamente la conexión con `RESET search_path` al devolverla al pool (`checkin`).
   - **`oppytec-backend/src/core/redis.py`:** Pool asíncrono de Redis con prefijo por entorno (`ENV_NAMESPACE`) y *Circuit Breaker* para resiliencia.
   - **`oppytec-backend/src/shared/models_base.py` y `soft_delete_mixin.py`:** Creó `PublicBase`, `TenantBase`, `AuditTimestampsMixin`, `SoftDeleteMixin` (`is_deleted`, `deleted_at`, `deleted_by`) y `TranslatableI18nMixin` (`i18n_data` JSONB), blindando nombres propios (`proveedores` como `"Pollo King"`, `marcas` como `"Savory"`, `holdings` y `legal_entities`) con `translatable = False`.
   - **Modelos de los 10 Módulos (`oppytec-backend/src/modules/*/infrastructure/models.py`):**
     - **En `public` (`PublicBase`):** `global_users`, `global_roles`, `global_permissions`, `holdings`, `legal_entities` (con relación **1:1 estricta** con `tenants` vía `UNIQUE(legal_entity_id)`), `tenants`, `system_plans` (`max_active_users`, `max_storage_mb` y precios en `CLP`, `USD`, `EUR`, `BRL`), `client_users` (a nivel Holding, donde el `soft-delete` libera inmediatamente el cupo comercial), `client_user_tenant_access` (acceso transversal multi-sucursal), `llm_request_logs`, `spec_chunks` (solo `specs/business-domain/`), `i18n_translation_memory`, `fx_current_rates` y `backup_execution_logs`.
     - **En cada `tenant_<slug>` (`TenantBase`):** RBAC local de 3 niveles (`roles`, `cargos` con los 42 colores y 49 íconos de Legacy, `permissions`, `user_permission_grants` JIT y tablas `audit_*` *Append-Only*), gobernanza editable de **`OppyFy`** (`oppyfy_domains`, `oppyfy_subdomains`, `oppyfy_permission_grants`, `oppyfy_worker_credit_wallets`, `oppyfy_prompt_audit_log`), control de cuota de imágenes R2 (`tenant_media_assets`) y todas las tablas operativas con precisión `NUMERIC`/`Decimal` (productos de 3 capas, Kardex inmutable `registro_stock`, recetas, compras, facturas, ventas, mermas, eventos, buffet, turnos, notas y tareas).

2. **Motor de Migraciones Correlativas Lineales (`0001..NNNN` sin `merge_heads`):**
   - **`0001_public_genesis_tenancy_modules_and_global_rbac.py`:** Construye de una sola vez el esquema `public` (`migration_scope = "public"`).
   - **`0002_tenant_initial_client_rbac_and_core_modules.py`:** Construye de forma homogénea las tablas operativas en cada esquema `tenant_<slug>` (`migration_scope = "tenant"`).
   - **`oppytec-backend/scripts/db_migration.py`:** Herramienta CLI con `new`, `rebase` (renumera automáticamente a `NNNN+1` si dos programadores crearon el mismo número en ramas distintas), `verify` e `impact` (consulta `Graphify` a costo 0 tokens antes de tocar una columna).

3. **Bootstrap Génesis Idempotente (`oppytec-backend/src/core/bootstrap.py`):**
   - Siembra los 4 roles globales base (`superuser`, `admin`, `supervisor`, `developer`), el catálogo de los 10 módulos y el **SuperUser Génesis (`oppytec.admin@gmail.com`)** leyendo sus credenciales desde variables de entorno con `SecretStr` (cero contraseñas escritas en código) y hasheando con `Argon2id`.
   - En cada sucursal `tenant_<slug>`, siembra los 5 roles cliente base editables (`propietario`, `superuser`, `admin`, `usuario`, `cajero`).

4. **Bóveda de Respaldos Cifrados en 4 Capas y Restauración Quirúrgica (`oppytec-backend/src/core/backup/` y `scripts/backup_manager.py`):**
   - Implementó la tubería criptográfica en streaming `pg_dump -> zstd -> age (AES-256)` generando artefactos `.sql.zst.age` con manifiesto `SHA-256`.
   - **Las 4 Capas (`3-2-1-1-0`):**
     - **Capa 1 (`neon_pitr_adapter.py`):** Retención continua WAL y ramas instantáneas `pre_alembic_NNNN` antes de cada migración.
     - **Capa 2 (`r2_vault_adapter.py`):** Bóveda privada `oppytec-backups-vault` en Cloudflare R2 guardando por separado `public` y cada `tenant_<slug>` individual.
     - **Capa 3 (`secondary_vps_adapter.py`):** Réplica en nube secundaria lista para encender con `BACKUP_SECONDARY_VPS_ENABLED=true`.
     - **Capa 4 (`pull-to-local-office`):** Descarga automática *Pull-Only* hacia el servidor local de oficina.
   - **Restauración Quirúrgica (`restore-tenant`) y Simulacro (`verify-drill`):** Permite devolver en el tiempo a **1 solo restaurante** (creando primero un `pre_restore_safety_snapshot` automático) con **0% de impacto** sobre los otros 499 restaurantes del cluster.

### 🏛️ Agente 12 (`12-tech-writer-openspec-archify`) — Mapa 1 del Atlas Archify, Snapshot Graphify y Segundo Cerebro
- **Mapa 1 del Atlas Visual Interactivo (`docs/architecture/atlas/01-tenancy-and-schemas.archify.html`):** Construyó el tablero interactivo HTML autocontenido (con su fuente tipada `01-tenancy-and-schemas.archify.json` y recibo `01-tenancy-and-schemas.receipt.json` sellado con `SHA-256`) con 18 nodos semánticos, 22 aristas, 4 zonas de confianza y 5 lentes interactivas.
- **Snapshot AST de Fase 2 (`docs/architecture/graphify/v2_phase2_schema_graph.json`):** Registró el grafo estructural de modelos, migraciones y adaptadores de backup para consultas deterministas a costo 0 tokens.
- **Actualización del Segundo Cerebro (`docs/bitacora/`):** Documentó esta entrada y actualizó `00-MAPA-SEGUNDO-CEREBRO.md`.

---

## 2. ¿Cómo Auditar Visualmente la Base de Datos, Alembic y los Respaldos?

Abre directamente en tu navegador web el **Mapa 1 del Atlas Interactivo de Archify**:
- [`docs/architecture/atlas/01-tenancy-and-schemas.archify.html`](../../architecture/atlas/01-tenancy-and-schemas.archify.html)

Allí puedes alternar entre las lentes:
1. **Esquema Public vs Tenant** (`PublicBase` vs `TenantBase` y `SET LOCAL search_path`).
2. **Jerarquía Holding -> LegalEntity 1:1 -> Tenant** (incluyendo cupos `max_active_users` con `soft-delete` y acceso transversal).
3. **Alembic Lineal 0001..N** (`0001_public_*`, `0002_tenant_*`, `db_migration.py` y `bootstrap.py`).
4. **Backups 4-Capas (`.sql.zst.age`)** (`Neon PITR`, `Cloudflare R2 Vault`, `VPS Secundario`, `Oficina Local` y `restore-tenant`).

---

## 3. ¿Qué Sigue Ahora? (Rumbo a la Fase 3)
- Fusionar los worktrees de la Fase 2 en `master` mediante el *Smart Merge Train* verificando `make fast-gate` y la integridad de Alembic (`0001 -> 0002 -> downgrade -> upgrade`).
- Iniciar la **Fase 3 (`specs/06-IMPLEMENTATION-PLAN.md`):** Construir las **2 Bóvedas Espejo de OpenSpec (`business-domain/` y `engineering-code/`)**, los motores transversales (`RBAC Dual` de 3 niveles, `OppyFy` con RAG de 3 capas y créditos, `JEV` Sistema 1, `i18n` con filtro `"Pollo King"`, `FX` Banco Central y cuotas R2), la lógica de dominio/aplicación de los 10 módulos y el **Mapa 2 de Archify (`02-rbac-quotas-and-audit.archify.html`)**.
