# Reporte de Traspaso (`Handover`) — Agente 03: Especialista en Base de Datos, Alembic y Backups 4-Capas

- **Fecha UTC:** 2026-10-25T19:40:00+00:00
- **Fase / Tarea:** Módulo de Consumo, Manos Libres y Buffet Inteligente (`/registro-de-consumo`, `/consumo/manos-libres`, `/consumo/buffet`) — FASE 1: Tareas 1.1 y 1.2 de `PLAN_MAESTRO_CONSUMO.md`
- **Estado:** ✅ Culminado con Éxito (100% Verificado con Pytest y Ruff en verde)

## 1. Completed (Qué se hizo)

### 1.1 Modelos de Persistencia SQLAlchemy 2.0 en `oppytec-backend/src/modules/operations/infrastructure/models.py`:
- Todos heredan estrictamente de `TenantBase` para operar en esquemas dinámicos `tenant_*` aislados con `SET LOCAL search_path`.
- **`ConsumptionRecord` (`consumption_records`):**
  - Cabecera transaccional de consumo directo, salidas operativas y mermas.
  - Campos: `id` (BigInteger PK), `codigo_folio` (String(64) unique), `folio_ticket` (String(64) nullable), `area_operativa_id` (FK `areas_operativas.id` ondelete SET NULL), `bodega_id` (FK `bodegas.id` ondelete SET NULL), `usuario_id` (Integer), `tipo_origen` (String(32), default "MANUAL_TERMINAL", enum: MANUAL_TERMINAL, MANOS_LIBRES_VOZ, BUFFET_LIQUIDACION, VENTA_POS), `costo_total` (Numeric(14, 2)), `notas` (Text nullable).
  - Mixins: `AuditTimestampsMixin`, `SoftDeleteMixin`.
  - Relación: `items` con cascada `all, delete-orphan`.
- **`ConsumptionRecordItem` (`consumption_record_items`):**
  - Desglose detallado de insumos/productos/recetas/combos consumidos por transacción.
  - Campos: `id` (BigInteger PK), `consumption_record_id` (FK `consumption_records.id` ondelete CASCADE), `tipo_item` (String(20): PRODUCTO, RECETA, COMBO), `item_id` (Integer), `cantidad` (Numeric(12, 4)), `unidad_medida` (String(20)), `costo_unitario_ppp` (Numeric(14, 2)), `costo_total` (Numeric(14, 2)), `lote_codigo` (String(64) nullable), `fecha_vencimiento_lote` (Date nullable), `kardex_movement_id` (BigInteger FK `registro_stock.id` ondelete SET NULL), `opciones_seleccionadas` (JSONDictType / JSONB).
  - Mixin: `AuditTimestampsMixin`.
  - Relación: `consumption_record`.
- **`ConsumptionTemplate` (`consumption_templates`):**
  - Plantillas de catálogo configurables por turno, cuadrilla o área operativa.
  - Campos: `id` (BigInteger PK), `slug` (String(64) unique), `nombre` (String(128)), `descripcion` (Text nullable), `usuario_creador_id` (Integer), `is_public` (Boolean default False), `columnas_count` (Integer default 8), `sort_mode` (String(32) default "alpha_asc"), `product_ids` (JSONDictType), `custom_product_order` (JSONDictType nullable).
  - Mixins: `AuditTimestampsMixin`, `SoftDeleteMixin`, `TranslatableI18nMixin`.
- **`BuffetTemplate` (Enriquecido):**
  - Campos agregados: `descripcion` (Text nullable), `estaciones_json` (JSONDictType nullable), `is_system` (Boolean default False), `is_public` (Boolean default True).
- **`BuffetSession` (Enriquecida):**
  - Campos agregados: `area_operativa_id` (FK `areas_operativas.id` ondelete SET NULL), `bodega_id` (FK `bodegas.id` ondelete SET NULL), `usuario_creador_id` (Integer nullable), `tipo_servicio` (String(64) default "DESAYUNO"), `pax_comensales` (Integer default 0), `costo_total_montaje` (Numeric(14, 2)), `valor_sobrante_reutilizable` (Numeric(14, 2)), `costo_neto_pax` (Numeric(14, 2)).
  - Relaciones: `stations`, `items` (ambas con cascade `all, delete-orphan`).
- **`BuffetStation` (Enriquecida):**
  - Campo agregado: `orden` (Integer default 0).
  - Relaciones: `session`, `items`.
- **`BuffetSessionItem` (`buffet_session_items`):**
  - Campos: `id` (BigInteger PK), `session_id` (FK `buffet_sessions.id` ondelete CASCADE), `station_id` (FK `buffet_stations.id` ondelete CASCADE), `tipo_item` (String(20): PRODUCTO, RECETA), `item_id` (Integer), `cantidad_montada` (Numeric(12, 4)), `cantidad_sobrante` (Numeric(12, 4)), `cantidad_merma` (Numeric(12, 4)), `cantidad_neta_consumida` (Numeric(12, 4)), `costo_unitario_ppp` (Numeric(14, 2)), `costo_total` (Numeric(14, 2)).
  - Mixin: `AuditTimestampsMixin`.
- **`VoiceStation` (`voice_stations`):**
  - Campos: `id` (BigInteger PK), `area_operativa_id` (FK `areas_operativas.id` ondelete SET NULL), `nombre_estacion` (String(64)), `voice_command` (String(64) clave fonética), `usuario_asignado_id` (Integer nullable), `is_active` (Boolean default True).
  - Mixins: `AuditTimestampsMixin`, `SoftDeleteMixin`.
  - Relación: `order_logs`.
- **`VoiceOrderLog` (`voice_order_logs`):**
  - Campos: `id` (BigInteger PK), `station_id` (FK `voice_stations.id` ondelete CASCADE), `texto_transcrito` (Text), `accion_detectada` (String(32): CONSUMO, MERMA), `confianza_ia` (Numeric(5, 4)), `items_interpretados_json` (JSONDictType), `estado` (String(32): PENDIENTE, CONFIRMADO, RECHAZADO, EJECUTADO), `consumption_record_id` (FK `consumption_records.id` ondelete SET NULL).
  - Mixin: `AuditTimestampsMixin`.
  - Relaciones: `station`, `consumption_record`.

### 1.2 Migración Correlativa Alembic Lineal `0005`:
- Archivo: `oppytec-backend/alembic/versions/0005_tenant_consumption_buffet_and_voice_tables.py`.
- `revision = "0005_tenant_consumption_buffet_and_voice_tables"`.
- `down_revision = "0004_tenant_inventory_kardex_and_physical_counts"`.
- `migration_scope = "tenant"`.
- Enlace lineal continuo asegurado con `0006_tenant_approval_requests_and_notification_matrix.py` (`down_revision = "0005_tenant_consumption_buffet_and_voice_tables"`).
- Funciones seguras e idempotentes: `_has_table`, `_has_column`, `_has_index`, `_get_tenant_schemas(bind)`.
- Crea de forma idempotente las 6 tablas nuevas, enriquece las 3 tablas de buffet existentes y genera vistas de compatibilidad en español (`registros_consumo`, `registro_consumo_items`, `plantillas_consumo`).
- Reversibilidad LIFO simétrica completa en `downgrade()`.

### 1.3 Testing y Calidad de Código:
- Pruebas unitarias en `oppytec-backend/tests/unit/modules/test_operations_services.py` y `oppytec-backend/tests/modules/operations/test_migration_0005.py`.
- 13/13 tests pasando en verde.
- Verificación de compilación limpia con `python -m py_compile`.
- Verificación de linting con `ruff check` sin advertencias ni errores.

## 2. Friction & Failures (Qué salió mal / Qué cuidar)
- En tests unitarios sin PostgreSQL activo, `op.get_bind()` requiere un mock explicito para que Alembic no lance `NameError: name '_proxy' is not defined`. Se configuró adecuadamente en los tests de simulación de migración.
- Nomenclatura bilingüe: Para respetar tanto el esquema canónico en inglés (`consumption_records`, `consumption_record_items`, `consumption_templates`) como las referencias en español (`registros_consumo`, `registro_consumo_items`, `plantillas_consumo`), la migración crea automáticamente vistas PostgreSQL `CREATE OR REPLACE VIEW` en cada esquema tenant.

## 3. Next Exact Action (Siguiente paso exacto)
- Proceder a la Fase 2 de `PLAN_MAESTRO_CONSUMO.md`: Desarrollo de los servicios de aplicación transaccionales (`ConsumptionService`, `BuffetService`, `VoiceKitchenService`), guardias RBAC `consumption.*` y endpoints REST RFC 7807 en `src/modules/operations/`.
