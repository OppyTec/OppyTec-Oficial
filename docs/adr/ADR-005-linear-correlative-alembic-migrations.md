# ADR-005: Migraciones Alembic Estrictamente Lineales, Correlativas (`0001..NNNN`) y Conscientes de Esquema

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_migraciones_alembic_001.md` / `.agent/skills/alembic-migration-manager/SKILL.md`

---

## 1. Contexto

En `OppyTec-Legacy` llegaron a coexistir 75 archivos de migración mezclando prefijos numéricos (`0001..0039`) con hashes hexadecimales aleatorios (`6d39f9f7b07f`) y múltiples revisiones de unión (`merge_heads`), provocando fallos al inicializar entornos limpios y confusión sobre qué tablas pertenecían al esquema `public` versus los esquemas de clientes.

## 2. Decisión

Imponer una política de **Migraciones Lineales Correlativas y Conscientes de Esquema** gobernada por `scripts/db_migration.py` y `oppytec-backend/alembic/env.py`:

1. **Nomenclatura Canónica Obligatoria:** Todo archivo en `alembic/versions/` debe cumplir el patrón `^(\d{4})_(public|tenant)_([a-z0-9_]+)\.py$` (ej. `0001_public_genesis_tenancy_modules_and_global_rbac.py`, `0002_tenant_initial_client_rbac_and_core_modules.py`).
2. **Atributo `migration_scope` Obligatorio:** Cada migración declara explícitamente `migration_scope: Literal["public", "tenant"]`. El ejecutor `alembic/env.py` aplica las migraciones `"public"` una sola vez sobre el esquema `public` y aplica las migraciones `"tenant"` iterando sobre todos los esquemas `tenant_<slug>`.
3. **Un Único Head Lineal (`Cero merge_heads`):** Se prohíben las ramificaciones y migraciones de unión. Cuando dos agentes en distintos `Git Worktrees` crean la migración `0004` en paralelo, el *Merge Train* ejecuta `python3 scripts/db_migration.py rebase` para renumerar automáticamente la segunda a `0005` y encadenar su `down_revision = "0004"`.
4. **Reversibilidad Garantizada:** Toda función `upgrade()` debe contar con su `downgrade()` simétrico funcional.

## 3. Consecuencias

- **Positivas:**
  - Historial de base de datos 100% lineal, legible cronológicamente y libre de conflictos de *multiple heads* en trabajo paralelo multi-agente.
  - Creación instantánea de nuevos tenants ejecutando únicamente las migraciones con `migration_scope == "tenant"`.
- **Negativas / Trade-offs:**
  - Prohibido ejecutar `alembic revision` manualmente sin pasar por `scripts/db_migration.py`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_alembic_integrity.py`.
- **Invariante Verificada:** Verifica en `< 1s` que todos los archivos en `alembic/versions/` sigan la regex `NNNN_(public|tenant)_slug.py`, que la secuencia numérica no tenga huecos ni duplicados, que exista exactamente 1 Head, que `migration_scope` coincida con el prefijo del archivo y que `downgrade()` no esté vacío (`pass`).
