# ADR-003: SQLAlchemy 2.0 Asíncrono y Conmutación Transaccional de `search_path`

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_entornos_y_despliegue_001.md` / `.agent/rules/04-database-and-alembic-migrations.md`

---

## 1. Contexto

En un entorno asíncrono de alta concurrencia (`FastAPI` + `asyncpg`) donde las conexiones de base de datos se reciclan en un pool compartido (`AsyncAdaptedQueuePool`) o a través de un pooler externo (`PgBouncer` en Neon con `NullPool`), modificar el `search_path` a nivel de sesión (`SET search_path`) sin limpiarlo al devolver la conexión contamina las peticiones subsiguientes (*Connection Pool Poisoning*).

## 2. Decisión

Adoptar **SQLAlchemy 2.0 Async (`AsyncEngine` + `async_sessionmaker`)** con una disciplina inmutable de aislamiento transaccional en `oppytec-backend/src/core/database.py`:

1. **Validación Estricta del Nombre de Esquema:** Antes de interpolar el nombre del esquema tenant, se valida contra la expresión regular `^tenant_[a-z0-9_]{1,50}$` verificando su existencia activa.
2. **Conmutación Local a la Transacción (`SET LOCAL search_path`):** La dependencia `get_tenant_db_session` ejecuta `SET LOCAL search_path TO tenant_<slug>, public` dentro del bloque transaccional activo, asegurando que el alcance expire automáticamente al hacer `COMMIT` o `ROLLBACK`.
3. **Sanitización Obligatoria en Check-In del Pool:** Se registra un listener en el evento `checkin` del pool de SQLAlchemy que ejecuta `RESET search_path` antes de que cualquier conexión regrese al pool.
4. **Ordenamiento Canónico de Locks (`ORDER BY id ASC FOR UPDATE`):** Toda transacción que bloquee múltiples filas de inventario o billeteras de créditos debe ordenar los IDs de forma ascendente antes de adquirir los locks para eliminar matemáticamente los *deadlocks* AB-BA.

## 3. Consecuencias

- **Positivas:**
  - Cero contaminación de `search_path` entre peticiones concurrentes bajo `500 RPS`.
  - Compatibilidad transparente tanto con `AsyncAdaptedQueuePool` (entornos `local`/`ci`) como con `NullPool` detrás de PgBouncer (`staging`/`production`).
- **Negativas / Trade-offs:**
  - Prohibición absoluta de sesiones implícitas o *lazy loading* fuera del contexto `async with` de la unidad de trabajo (`expire_on_commit=False`).

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca y Red Team:** `oppytec-backend/tests/security_redteam/test_01_cross_tenant_schema_escape.py` y `test_05_kardex_race_condition_and_deadlocks.py`.
- **Invariante Verificada:** Pruebas concurrentes con `asyncio.gather` verifican que tras 100 peticiones intercaladas entre distintos tenants y fallos inducidos, ninguna conexión devuelta al pool conserva un `search_path` distinto del predeterminado.
