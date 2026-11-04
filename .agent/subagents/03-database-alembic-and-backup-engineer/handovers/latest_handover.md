# Reporte de Traspaso (`Handover`) — Agente 03: Especialista en Base de Datos, Alembic y Backups 4-Capas

- **Fecha UTC:** 2026-11-02T18:50:00Z
- **Fase / Hito:** FASE 1 del Plan Maestro del Panel de Actividades (Notas, Tareas y Horarios) — Extensión de modelos ORM en `oppytec-backend/src/modules/operations/infrastructure/models.py` y Migración Lineal Correlativa Alembic 0015 (`0015_tenant_actividades_triada_enriquecida.py`) en esquemas `tenant_*`.
- **Estado de Certificación:** `ACTIVIDADES_MODELS_AND_ALEMBIC_0015_CERTIFIED` (Alembic 0001..0015 estrictamente lineal, 29/29 tests de arquitectura al 100% verde, 9/9 tests de operaciones al 100% verde, cero errores de integridad).

---

## 1. Completed (Qué se ejecutó y validó)

1. **Consulta Graphify y AST Claims:**
   - Mapeo inicial de AST con `python scripts/harness.py nav "NotaEquipo"`.
   - Reserva atómica de símbolos AST (`fcntl.flock`): `NotaEquipo`, `Tarea`, `TurnoHorario` en `claims_registry.json`.

2. **Modelado de Persistencia Multi-Tenant SQLAlchemy 2.0 Async:**
   - Ubicación: [`oppytec-backend/src/modules/operations/infrastructure/models.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/operations/infrastructure/models.py).
   - Exportado en: [`oppytec-backend/src/modules/operations/infrastructure/__init__.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/operations/infrastructure/__init__.py).
   - Herencia estricta de `TenantBase`, `AuditTimestampsMixin`, `SoftDeleteMixin` y `TranslatableI18nMixin`.
   - **`TurnoHorario` (`turnos_horarios`):**
     * Enriquecido con: `usuario_id` (Integer nullable, indexado con sincronización bidireccional a `user_id`), `area_id` (String(64) nullable, indexado), `fecha_inicio` (Date nullable, indexado), `fecha_fin` (Date nullable, indexado), `hora_inicio` (Time nullable), `hora_fin` (Time nullable), `inicio_turno` / `fin_turno` flexibilizados a nullable, `nota` (String(500) nullable), `color` (String(20) nullable), `creado_por` (Integer nullable, indexado).
     * Constructor polimórfico que admite indistintamente la firma v2 y la heredada de legacy.
   - **`NotaPersonal` (`notas_personales`):**
     * Enriquecida con: `area_id` (String(64) nullable, indexado), `fecha` (DateTime nullable), property `autor_id` mapeada a `user_id`.
   - **`NotaEquipo` (`notas_equipo`):**
     * Enriquecida con: `area_id` (String(64) nullable, indexado), `categoria` (String(40), default 'general', indexado), `fecha` (DateTime nullable), `insumo_id` (String(64) nullable, indexado), `receta_id` (Integer nullable, indexado), `foto_url` (String(500) nullable), property `autor_id` mapeada a `autor_user_id`.
     * Relaciones ORM `cascade="all, delete-orphan"` a `menciones` (`NotaEquipoMencion`) y `lecturas` (`NotaEquipoLectura`).
   - **`NotaEquipoMencion` (`nota_equipo_menciones`):**
     * Tabla relacional con `id`, `nota_id` FK a `notas_equipo.id` ON DELETE CASCADE, `user_id`, `created_at`, `updated_at`.
     * Restricción de unicidad: `UniqueConstraint("nota_id", "user_id", name="uq_nota_equipo_menciones_nota_user")`.
   - **`NotaEquipoLectura` (`nota_equipo_lecturas`):**
     * Tabla relacional para auditoría de lecturas / vistos de novedades con `id`, `nota_id` FK a `notas_equipo.id` ON DELETE CASCADE, `user_id`, `read_at` (DateTime timezone=True, default func.now()), `created_at`, `updated_at`.
     * Restricción de unicidad: `UniqueConstraint("nota_id", "user_id", name="uq_nota_equipo_lecturas_nota_user")`.
   - **`PlantillaRutina` (`plantillas_rutinas`):**
     * Modelo para rutinas periódicas de apertura, cierre y mantenimiento con `id`, `nombre` (String(160)), `descripcion` (Text), `area_id` (String(64)), `tipo_rutina` (String(40), default 'APERTURA'), `frecuencia` (String(30), default 'DIARIA'), `items_json` (JSONB / JSONDictType), `is_active` (Boolean, default True), `usuario_creador_id` (Integer), `is_deleted` (SoftDeleteMixin), timestamps UTC.
     * Relación 1:N con `Tarea` (`tareas`).
   - **`Tarea` (`tareas`):**
     * Enriquecida con: `creador_user_id` (Integer nullable, indexado), `asignado_a_user_id` (Integer nullable, indexado), `area_id` (String(64) nullable, indexado), `descripcion` (Text nullable), `estado` (String(30), default 'pendiente': 'pendiente', 'progreso', 'completada', 'incompleta', indexado), `urgencia` (String(20), default 'media': 'alta', 'media', 'baja', indexado), `fecha_limite` (DateTime timezone=True nullable), `nota_incompleta` (Text nullable), `compra_id` (String(64) nullable, indexado), `foto_evidencia_url` (String(500) nullable), `plantilla_id` (Integer FK `plantillas_rutinas.id` ON DELETE SET NULL, indexado), `completada` (Boolean, default False).
     * Relación ORM a `plantilla` (`PlantillaRutina`), properties `creador_id` y `asignado_id`.

3. **Migración Correlativa Lineal Alembic 0015:**
   - Ubicación: [`oppytec-backend/alembic/versions/0015_tenant_actividades_triada_enriquecida.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/alembic/versions/0015_tenant_actividades_triada_enriquecida.py).
   - Metadatos:
     * `revision = "0015_tenant_actividades_triada_enriquecida"`
     * `down_revision = "0014_tenant_projection_snapshots_and_consumption_rates"`
     * `migration_scope: Literal["public", "tenant"] = "tenant"`
   - DDL e Idempotencia:
     * Detección dinámica y multi-esquema con `_get_tenant_schemas(bind)`.
     * Inspección idempotente de tablas, columnas e índices con `_has_table`, `_has_column`, `_has_index`.
     * Sincronización y backfill de compatibilidad en `turnos_horarios`, `notas_equipo` y `tareas`.
     * Función `downgrade()` estrictamente simétrica y reversible.

4. **Pruebas Automatizadas de Arquitectura y Modelos:**
   - Pruebas añadidas en [`oppytec-backend/tests/unit/modules/test_operations_services.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/tests/unit/modules/test_operations_services.py):
     * `test_alembic_0015_migration_metadata`: Validación de cadena de revisions y callables `upgrade`/`downgrade`.
     * `test_operations_actividades_triada_enriquecida_models`: Cobertura exhaustiva de instanciación, propiedades y relaciones de `TurnoHorario`, `NotaPersonal`, `NotaEquipo`, `NotaEquipoMencion`, `NotaEquipoLectura`, `PlantillaRutina`, `Tarea`.
   - Resultados de ejecución:
     * `oppytec-backend/.venv/bin/pytest tests/architecture/test_alembic_integrity.py`: 2 passed (100% verde).
     * `oppytec-backend/.venv/bin/pytest tests/architecture/`: 29 passed (100% verde).
     * `oppytec-backend/.venv/bin/pytest tests/unit/modules/test_operations_services.py`: 7 passed (100% verde).

---

## 2. Friction & Failures (Invariantes observadas y resueltas)

- **Compatibilidad de Nombres de Columnas (v2 vs Legacy):** En `TurnoHorario`, v2 utilizaba `user_id` mientras que legacy usaba `usuario_id`. Se agregaron ambas columnas al esquema de BD junto con un constructor kwargs sincronizador y backfill automático, asegurando cero fallos tanto en código existente como en contratos legacy.
- **Relaciones con Plantillas:** En `Tarea`, `plantilla_id` referencia `plantillas_rutinas.id` con `ondelete="SET NULL"` para no romper tareas históricas si una rutina es dada de baja.
- **Auditoría de Vistos:** Se crearon restricciones únicas `(nota_id, user_id)` en `nota_equipo_menciones` y `nota_equipo_lecturas` para garantizar idempotencia en confirmaciones de lectura.

---

## 3. Next Exact Action (Para los siguientes agentes en el DAG)

1. **Agente 04 (Backend Senior Dev):** Implementar o actualizar los endpoints y servicios de aplicación de Actividades (`src/modules/operations/presentation/` y `application/`) para soportar CRUD completo de notas de equipo con menciones, checklist de tareas y cuadrante de horarios.
2. **Agente 05 (Frontend Senior Dev):** Conectar la interfaz de `/actividades` con los nuevos campos (menciones, filtros por área, urgencia y estados de tareas, cuadrante de turnos).
3. **Agente 12 (Tech Writer / OpenSpec / Graphify):** Ejecutar `python scripts/harness.py sync-graph` para indexar los nuevos modelos y migración en `graph.json`.
