# Base de Conocimiento Evolutiva — Agente 03: Especialista en Base de Datos, Alembic y Backups 4-Capas

> Lecciones aprendidas específicas de `03-database-alembic-and-backup-engineer` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 2 — Separación `PublicBase` vs `TenantBase`]:** `PublicBase` declara `MetaData(schema="public")` mientras que `TenantBase` declara `MetaData()` sin `schema` fijo para operar dinámicamente sobre `SET LOCAL search_path TO "<tenant_schema>", public` con `RESET search_path` garantizado en checkin y en `finally`.
- **[Fase 2 — Regla "Pollo King" en Modelos]:** Las tablas `proveedores`, `marcas`, `holdings` y `legal_entities` deben declarar `translatable: ClassVar[bool] = False` y jamás incluir `TranslatableI18nMixin`.
- **[Fase 2 — Migraciones Correlativas y Backups 4-Capas]:** Toda migración en `alembic/versions/` cumple `NNNN_(public|tenant)_<slug>.py` con `migration_scope` explícito y `downgrade()` real. Todo artefacto de respaldo pasa por `zstd` + `age` (`.sql.zst.age`) verificando `SHA-256` y garantizando restauración quirúrgica aislada por `tenant_<slug>`.
