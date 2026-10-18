# Regla 19: Respaldos de Base de Datos en 4 Capas y Restauración Quirúrgica por Tenant
- Referencia: `.agent/estrategias/estrategia_respaldos_base_datos_y_recuperacion_001.md`.
- 4 Capas (Neon PITR, Cloudflare R2 cifrado `.sql.zst.age` por `tenant_<slug>`, VPS Secundario y Servidor Local de Oficina) con snapshot pre-migración Alembic y restauración quirúrgica de un solo cliente sin afectar a los demás.
