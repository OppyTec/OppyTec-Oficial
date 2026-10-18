# Regla 06: Gobernanza de Migraciones Correlativas Alembic (`0001..NNNN`)
- Referencia: `estrategia_migraciones_alembic_001.md`.
- Formato único permitido: `NNNN_<public|tenant>_<slug>.py` (ej. `0001_public_...`, `0002_tenant_...`).
- Prohibido usar hashes aleatorios o `alembic merge heads`. En colisión de ramas usar `python scripts/db_migration.py rebase`.
- Toda migración debe tener `downgrade()` real y reversible.
