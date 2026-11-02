# Reporte de Traspaso (`Handover`) — Agente 03: Especialista en Base de Datos, Alembic y Backups 4-Capas

- **Fecha UTC:** 2026-11-01T20:00:00Z
- **Fase / Hito:** FASE 1 del PLAN_MAESTRO_PROYECCION.md — Persistencia SQLAlchemy 2.0 Async en `oppytec-backend/src/modules/projection/infrastructure/models.py` y Migración Lineal Correlativa Alembic 0014 (`0014_tenant_projection_snapshots_and_consumption_rates.py`) en esquemas `tenant_*`.
- **Estado de Certificación:** `PROJECTION_MODELS_AND_ALEMBIC_0014_CERTIFIED` (Alembic 0001..0014 estrictamente lineal, 2/2 tests de arquitectura correlativa al 100% verde, 3/3 tests unitarios de modelos/migración al 100% verde, 10/10 tests de dominio FEFO al 100% verde).

---

## 1. Completed (Qué se ejecutó y validó)

1. **Modelado de Persistencia Multi-Tenant SQLAlchemy 2.0 Async:**
   - Ubicación: [`oppytec-backend/src/modules/projection/infrastructure/models.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/projection/infrastructure/models.py).
   - Exportado en: [`oppytec-backend/src/modules/projection/infrastructure/__init__.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/projection/infrastructure/__init__.py).
   - Herencia estricta de `TenantBase` y `AuditTimestampsMixin` (`created_at`, `updated_at` en UTC con `func.now()`).
   - **`ProjectionSnapshot` (`projection_snapshots`):**
     * `id`: `BigInteger` PK autoincremental.
     * `producto_id`: `BigInteger` FK `productos.id` (`ON DELETE CASCADE`), indexado.
     * `bodega_id`: `BigInteger` FK `bodegas.id` (`ON DELETE CASCADE`), nullable para consolidado multi-bodega, indexado.
     * `horizon_days`: `Integer` (`7`, `15`, `30`, `60`, `90`), default 30.
     * `current_stock`: `Numeric(12, 4)`.
     * `projected_stock`: `Numeric(12, 4)`.
     * `depletion_date`: `Date`, nullable.
     * `worst_status`: `String(20)` (`NORMAL`, `WARNING`, `CRITICAL`).
     * `worst_status_label`: `String(64)`.
     * `worst_day`: `Integer`, nullable.
     * `daily_consumption_rate`: `Numeric(12, 4)`.
     * `projection_curve`: `JSONB` / `JSONDictType` con serie temporal día a día.
     * `calculated_at`: `DateTime(timezone=True)` default UTC `func.now()`.
     * `is_stale`: `Boolean` default False.
     * `metadata_payload`: `JSONB` / `JSONDictType`, nullable.
     * Restricción de unicidad: `UniqueConstraint("producto_id", "bodega_id", "horizon_days", name="uq_proj_snapshots_prod_bod_horiz")`.
     * Índices compuestos: `idx_proj_snapshots_lookup` (bodega_id, horizon_days, worst_status), `idx_proj_snapshots_prod` (producto_id, horizon_days), `idx_proj_snapshots_calc` (calculated_at, is_stale).
     * Relaciones ORM con `Producto` y `Bodega`.
   - **`DailyConsumptionRate` (`daily_consumption_rates`):**
     * `id`: `BigInteger` PK autoincremental.
     * `producto_id`: `BigInteger` FK `productos.id` (`ON DELETE CASCADE`), indexado.
     * `bodega_id`: `BigInteger` FK `bodegas.id` (`ON DELETE CASCADE`), nullable, indexado.
     * `rate_7d`, `rate_30d`, `rate_90d`: `Numeric(12, 4)` default 0.0000.
     * `last_calculated_at`: `DateTime(timezone=True)` default UTC `func.now()`.
     * Restricción de unicidad: `UniqueConstraint("producto_id", "bodega_id", name="uq_daily_consumption_rates_prod_bod")`.
     * Relaciones ORM con `Producto` y `Bodega`.

2. **Migración Correlativa Lineal Alembic 0014:**
   - Ubicación: [`oppytec-backend/alembic/versions/0014_tenant_projection_snapshots_and_consumption_rates.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/alembic/versions/0014_tenant_projection_snapshots_and_consumption_rates.py).
   - Metadatos:
     * `revision = "0014_tenant_projection_snapshots_and_consumption_rates"`
     * `down_revision = "0013_tenant_events_salones_and_reservations"`
     * `migration_scope: Literal["public", "tenant"] = "tenant"`
   - DDL e Idempotencia:
     * Implementa `_get_tenant_schemas(bind)` para aplicar sobre todos los esquemas `tenant_*`.
     * Creación segura e idempotente con `_has_table` e `_has_index`.
     * Función `downgrade()` completa y simétrica con eliminación ordenada de índices y tablas.

3. **Pruebas Automatizadas de Arquitectura y Persistencia:**
   - Creación de [`oppytec-backend/tests/unit/modules/test_projection_models_and_migration.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/tests/unit/modules/test_projection_models_and_migration.py).
   - `pytest test_alembic_integrity.py`: 2/2 tests passed (100% verde).
   - `python scripts/db_migration.py verify`: Verificación OK sin saltos ni duplicados.
   - `pytest test_projection_models_and_migration.py`: 3/3 tests passed (100% verde).
   - `pytest test_projection_domain.py`: 10/10 tests passed (100% verde).

4. **Sincronización Graphify:**
   - Ejecución de `python3 scripts/harness.py sync-graph`.
   - Nodos indexados: 107 (Routers: 11, Migraciones: 16, Suites: 19).

---

## 2. Friction & Failures (Resolución de Secuenciamiento Correlativo)

- **Correlatividad Lineal Continua:**
  * Al verificar la cadena en `alembic/versions/`, se confirmó la existencia de `0012_public_ai_model_configs_catalog_extension.py` y `0013_tenant_events_salones_and_reservations.py`.
  * Siguiendo la regla de oro de secuenciamiento estricto `0001..NNNN` (Regla 06) y la especificación de `PLAN_MAESTRO_PROYECCION.md` (*"o número secuencial inmediatamente posterior a la última migración registrada"*), la migración se nombró y estructuró como `0014_tenant_projection_snapshots_and_consumption_rates.py` encadenada a `0013`, garantizando cero bifurcaciones (0 heads extras) y pasando todos los linters y validaciones de AST.

---

## 3. Next Exact Action (Siguiente paso exacto)

- Traspasar la ejecución al Agente 04 (`04-backend-senior-dev`) para iniciar la **FASE 2** del PLAN_MAESTRO_PROYECCION.md:
  1. Construcción del servicio `ProjectionEngine` en `src/modules/projection/application/services.py` con recálculo batch, lock anti-concurrencia y deducción FEFO.
  2. Implementación de los endpoints REST en `src/modules/projection/presentation/router.py`:
     - `GET /api/v1/projection/snapshots` (paginado server-side < 25ms)
     - `POST /api/v1/projection/recompute` (lock distribuido)
     - `GET /api/v1/projection/products/{id}/curve` (curva día a día 1..90)
     - `GET /api/v1/projection/alerts` (quiebres preventivos y sugerencias de traspaso)
