# ADR-018: Respaldos Cifrados en 4 Capas (`zstd` + `age`) y Restauración Quirúrgica por Tenant

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_respaldos_base_datos_y_recuperacion_001.md` / `.agent/skills/db_backup_recovery/SKILL.md`

---

## 1. Contexto

Depender de un único proveedor cloud para las copias de seguridad o realizar únicamente respaldos monolíticos de toda la base de datos impide recuperarse ante un fallo catastrófico de cuenta cloud y obliga a sobrescribir los datos de todos los clientes si un único restaurante solicita revertir un error operativo ocurrido hace dos horas.

## 2. Decisión

Implementar una arquitectura de **Respaldos Inmutables en 4 Capas Independientes (`3-2-1-1-0`)** con compresión **`zstd`**, cifrado asimétrico moderno **`age` (`X25519` + `ChaCha20-Poly1305`)** y **Restauración Quirúrgica por Esquema `tenant_<slug>`**:

1. **Las 4 Capas de Respaldo Independientes (`oppytec-backend/src/core/backup/`):**
   - **Capa 1 — Instantáneas Cloud Continuas (`neon_pitr_adapter.py`):** Point-in-Time Recovery (PITR) nativo con ramas instantáneas para recuperación a cualquier segundo.
   - **Capa 2 — Bóveda Object Storage Inmutable (`r2_vault_adapter.py`):** Volcados lógicos separados por esquema (`public` y cada `tenant_<slug>`) comprimidos y cifrados (`.sql.zst.age`) en un bucket R2 con *Object Lock* (WORM).
   - **Capa 3 — Servidor VPS Secundario Independiente (`secondary_vps_adapter.py`):** Réplica fuera de la nube principal en proveedor distinto vía SFTP/SSH restringido (*append-only*).
   - **Capa 4 — Bóveda Física Local / Oficina (`pull-to-local-office`):** Sincronización pull automatizada hacia almacenamiento físico controlado por el propietario de OppyTec, inmune a bloqueos de cuentas cloud.
2. **Restauración Quirúrgica de un Solo Restaurante (`restore-tenant`):**
   - Gracias al aislamiento por esquemas (`ADR-002`), `scripts/backup_manager.py restore-tenant --tenant <slug>` descarga y descifra únicamente el archivo `tenant_<slug>.sql.zst.age`, lo restaura primero en un esquema temporal `tenant_<slug>_restore_verify`, valida su integridad de conteos y realiza un swap atómico de esquemas (`ALTER SCHEMA ... RENAME TO ...`) en milisegundos sin interrumpir a ningún otro cliente.
3. **Snapshot Pre-Migración Obligatorio y Simulacros Automatizados (`verify-drill`):**
   - Ninguna migración Alembic se ejecuta en `staging` o `production` sin crear antes un `pre-migration-snapshot` verificado con checksum `SHA-256`.

## 3. Consecuencias

- **Positivas:**
  - Sobrevivencia garantizada del negocio incluso ante caída total o bloqueo del proveedor cloud primario.
  - Capacidad de restaurar a un único restaurante en menos de 60 segundos sin afectar a los demás tenants del Holding.
- **Negativas / Trade-offs:**
  - Ningún archivo de respaldo puede escribirse en disco o red en texto plano; todo el pipeline opera por streaming (`pg_dump | zstd | age`) validando el manifiesto `SHA-256`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_backup_encryption_and_tenant_restore.py`.
- **Invariante Verificada:** Verifica que `crypto_stream.py` nunca genere volcados `.sql` sin cifrar, que los adaptadores de las 4 capas cumplan el protocolo `BackupStorageAdapter`, y que `restore-tenant` aísle estrictamente el esquema objetivo.
