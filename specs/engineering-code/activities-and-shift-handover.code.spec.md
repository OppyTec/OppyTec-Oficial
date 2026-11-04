---
spec_id: ENG-ACTIVITIES-AND-SHIFT-HANDOVER
title: "Módulo de Actividades, Bitácora Operativa, Tareas, Horarios y Sinergia OppyFy"
audience: engineering_internal
domain_module: operations
paired_spec: specs/business-domain/activities-and-shift-handover.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 8"
---

# Panel de Actividades, Tareas Operativas, Horarios y Sinergia OppyFy — Especificación de Ingeniería

## Contrato Técnico

### 1. Persistencia Relacional Multi-Tenant y Migración Alembic 0015

La persistencia de datos reside en los esquemas aislados por inquilino (`tenant_*`), garantizando segregación física multi-tenant. La migración correlativa lineal `0015_tenant_actividades_triada_enriquecida.py` (`down_revision = "0014_tenant_projection_snapshots_and_consumption_rates"`) incorpora y enriquece las tablas del módulo:

#### A. Modelos ORM SQLAlchemy 2.0 Async (`src/modules/operations/infrastructure/models.py`)

1. **`TurnoHorario` (tabla `tenant_*.turnos_horarios`):**
   - Campos:
     - `id`: `Integer`, Primary Key, autoincremental.
     - `usuario_id` / `user_id`: `Integer`, nullable, indexado (soporta compatibilidad bidireccional entre la firma v2 y la heredada de legacy).
     - `area_id`: `String(64)`, nullable, indexado.
     - `fecha_inicio`: `Date`, nullable, indexado.
     - `fecha_fin`: `Date`, nullable, indexado.
     - `hora_inicio`: `Time`, nullable.
     - `hora_fin`: `Time`, nullable.
     - `inicio_turno`: `DateTime(timezone=True)`, nullable.
     - `fin_turno`: `DateTime(timezone=True)`, nullable.
     - `nota`: `String(500)`, nullable.
     - `color`: `String(20)`, nullable (código hexadecimal para renderizado en cuadrante).
     - `creado_por`: `Integer`, nullable, indexado.
     - `tenant_id`: `String(64)`, not null, indexado (aislamiento estricto fail-closed).
     - Mixins: `TenantBase`, `AuditTimestampsMixin`, `SoftDeleteMixin`, `TranslatableI18nMixin`.

2. **`NotaPersonal` (tabla `tenant_*.notas_personales`):**
   - Campos:
     - `id`: `Integer`, Primary Key.
     - `user_id`: `Integer`, not null, indexado (propietario exclusivo).
     - `area_id`: `String(64)`, nullable, indexado.
     - `fecha`: `DateTime(timezone=True)`, nullable.
     - `contenido`: `Text`, not null.
     - `tenant_id`: `String(64)`, not null, indexado.
     - `is_deleted`: `Boolean`, default `False` (soft-delete).
     - Property: `autor_id` mapeada a `user_id`.

3. **`NotaEquipo` (tabla `tenant_*.notas_equipo`):**
   - Campos:
     - `id`: `Integer`, Primary Key.
     - `autor_user_id`: `Integer`, not null, indexado.
     - `area_id`: `String(64)`, nullable, indexado.
     - `categoria`: `String(40)`, default `'general'`, indexado (`incidente`, `stock`, `produccion`, `servicio`, `general`).
     - `fecha`: `DateTime(timezone=True)`, nullable.
     - `contenido`: `Text`, not null.
     - `insumo_id`: `String(64)`, nullable, indexado.
     - `receta_id`: `Integer`, nullable, indexado.
     - `foto_url`: `String(500)`, nullable (referencia a objeto en Cloudflare R2).
     - `tenant_id`: `String(64)`, not null, indexado.
     - `is_deleted`: `Boolean`, default `False`.
   - Relaciones ORM (`cascade="all, delete-orphan"`):
     - `menciones`: Colección 1:N a `NotaEquipoMencion`.
     - `lecturas`: Colección 1:N a `NotaEquipoLectura`.

4. **`NotaEquipoMencion` (tabla `tenant_*.nota_equipo_menciones`):**
   - Campos: `id`, `nota_id` (FK a `notas_equipo.id` ON DELETE CASCADE), `user_id` (`Integer`, indexado), `created_at`, `updated_at`.
   - Restricción de Unicidad: `uq_nota_equipo_menciones_nota_user` sobre `(nota_id, user_id)`.

5. **`NotaEquipoLectura` (tabla `tenant_*.nota_equipo_lecturas`):**
   - Campos: `id`, `nota_id` (FK a `notas_equipo.id` ON DELETE CASCADE), `user_id` (`Integer`, indexado), `read_at` (`DateTime(timezone=True)` default `now()`), `created_at`, `updated_at`.
   - Restricción de Unicidad: `uq_nota_equipo_lecturas_nota_user` sobre `(nota_id, user_id)` (garantiza idempotencia total en confirmación de visto).

6. **`PlantillaRutina` (tabla `tenant_*.plantillas_rutinas`):**
   - Campos: `id`, `nombre` (`String(160)`), `descripcion` (`Text`), `area_id` (`String(64)`), `tipo_rutina` (`String(40)` default `'APERTURA'`), `frecuencia` (`String(30)` default `'DIARIA'`), `items_json` (`JSONB` / `JSONDictType`), `is_active` (`Boolean` default `True`), `usuario_creador_id` (`Integer`), `tenant_id` (`String(64)`).
   - Relaciones: 1:N con `Tarea`.

7. **`Tarea` (tabla `tenant_*.tareas`):**
   - Campos:
     - `id`: `Integer`, Primary Key.
     - `creador_user_id`: `Integer`, nullable, indexado.
     - `asignado_a_user_id`: `Integer`, nullable, indexado.
     - `area_id`: `String(64)`, nullable, indexado.
     - `descripcion`: `Text`, not null.
     - `estado`: `String(30)`, default `'pendiente'`, indexado (`pendiente`, `progreso`, `completada`, `incompleta`).
     - `urgencia`: `String(20)`, default `'media'`, indexado (`alta`, `media`, `baja`).
     - `fecha_limite`: `DateTime(timezone=True)`, nullable.
     - `nota_incompleta`: `Text`, nullable.
     - `compra_id`: `String(64)`, nullable, indexado.
     - `foto_evidencia_url`: `String(500)`, nullable.
     - `plantilla_id`: `Integer`, nullable, FK a `plantillas_rutinas.id` ON DELETE SET NULL, indexado.
     - `completada`: `Boolean`, default `False`, indexado.
     - `tenant_id`: `String(64)`, not null, indexado.
     - `is_deleted`: `Boolean`, default `False`.

---

### 2. Capa de Aplicación Clean Architecture (`ActividadesService`)

Implementada en `oppytec-backend/src/modules/operations/application/actividades_service.py`:

1. **Gestión de Notas de Equipo y Bitácora:**
   - `create_nota_equipo(db, data, current_user_id, tenant_id)`: Registra la nota, persiste menciones `@` con prevención de duplicados, publica evento WebSocket `operations.nota.created`.
   - `get_notas_equipo(db, tenant_id, area_id, categoria, search, user_id_mencionado, current_user_id, skip, limit)`: Filtra por tenant de forma estricta, enriquece con `leido_por_mi: bool` y `total_lecturas: int`.
   - `mark_nota_as_read(db, nota_id, current_user_id, tenant_id)`: Inserción idempotente de `NotaEquipoLectura`. Si ya existe el registro, retorna estado exitoso sin alterar la base ni lanzar error.
   - `update_nota_equipo` y `delete_nota_equipo`: Mutaciones con soft-delete y control de pertenencia.

2. **Gestión de Notas Personales (Privacidad Estricta):**
   - `create_nota_personal`, `get_notas_personales`, `update_nota_personal`, `delete_nota_personal`.
   - **Invariante de Confidencialidad:** Toda consulta o mutación exige `nota.user_id == current_user_id`. Intentos de acceso o modificación sobre notas personales ajenas lanzan `DomainValidationError` (HTTP 400).

3. **Gestión de Tareas y Validación Inviolable:**
   - `create_tarea`, `get_tareas`, `update_tarea`, `update_tarea_estado`, `delete_tarea`.
   - **Invariante de Justificación Obligatoria:** Si el estado transiciona a `'incompleta'`, se exige `nota_incompleta` con al menos una cadena no vacía (valida espacios en blanco y nulos). Cualquier violación lanza `DomainValidationError` RFC 7807.
   - Sincronización automática de `completada = True` al marcar `'completada'`.

4. **Plantillas de Rutina y Generación en Lote:**
   - `create_plantilla_rutina` y `get_plantillas_rutinas`.
   - `aplicar_plantilla_rutina(db, plantilla_id, fecha, tenant_id, current_user_id)`: Instancia atómicamente todas las tareas del turno especificadas en `items_json`.

5. **Cuadrante Semanal de Horarios y Legal Guard Laboral:**
   - `create_turno_horario`, `get_turnos_horarios`, `update_turno_horario`, `delete_turno_horario`.
   - `clonar_semana(db, fecha_lunes_origen, fecha_lunes_destino, tenant_id, current_user_id)`: Desplaza por delta de días exacto todos los turnos de la semana origen hacia la semana destino. Exige que ambas fechas correspondan a un día lunes (`weekday() == 0`).
   - `validar_alertas_laborales(db, usuario_id, nuevo_turno, tenant_id)`:
     * **Alerta `DESCANSO_INSUFICIENTE`:** Verifica que entre la hora de fin de la jornada previa y la hora de inicio de la nueva jornada medien $\ge 12$ horas continuas.
     * **Alerta `EXCESO_40_HORAS`:** Acumula con aritmética `Decimal` la duración de todos los turnos del colaborador en la semana calendario ISO. Si excede $40.0$ horas, emite alerta legal.

6. **Sinergia OppyFy — Minuta de Traspaso de Turno:**
   - `generar_minuta_traspaso(db, fecha, area_id, tenant_id)`:
     - Filtra y clasifica notas de equipo del día en sus categorías operacionales.
     - Agrupa tareas completadas y tareas incompletas (extrayendo urgencia y motivo).
     - Consolida colaboradores en turno y franjas horarias.
     - Sintetiza la estructura de los **4 Puntos Clave**:
       1. `incidentes`
       2. `produccion`
       3. `tareas_pendientes`
       4. `dotacion`
     - Genera `resumen_markdown` listo para exportación ejecutiva.

---

### 3. Contratos DTO Pydantic v2 y Sanitización (`schemas_actividades.py`)

Implementado en `oppytec-backend/src/modules/operations/presentation/schemas_actividades.py`:
- `ConfigDict(extra="forbid")` en el 100% de esquemas de entrada.
- `ConfigDict(from_attributes=True)` en esquemas de salida.
- `@field_validator` universal con `sanitize_text_input(..., block_polyglots=True)` para neutralizar payloads XSS (`<script>`, `<iframe>`, `javascript:`, `<img onerror=...>`) y SSTI (`{{...}}`, `${...}`).
- Tipado `Decimal` para cómputos horarios.
- DTOs principales:
  - `NotaEquipoCreateRequest`, `NotaEquipoUpdateRequest`, `NotaEquipoResponse`, `NotaLecturaResponse`.
  - `NotaPersonalCreateRequest`, `NotaPersonalUpdateRequest`, `NotaPersonalResponse`.
  - `TareaCreateRequest`, `TareaEstadoUpdateRequest`, `TareaUpdateRequest`, `TareaResponse`.
  - `PlantillaRutinaCreateRequest`, `PlantillaRutinaResponse`, `AplicarPlantillaRequest`.
  - `TurnoHorarioCreateRequest`, `TurnoHorarioUpdateRequest`, `TurnoHorarioResponse`, `ClonarSemanaRequest`.
  - `ValidarTurnoAlertaRequest`, `ValidacionLaboralResponse`, `AlertaLaboralItem`.
  - `MinutaTraspasoRequest`, `MinutaTraspasoResponse`, `MinutaPuntosClave`, `MinutaEstadisticas`.

---

### 4. Enrutador REST FastAPI y Matriz RBAC de 3 Niveles (`router_actividades.py`)

Montado en `src/main.py` bajo el prefijo `/api/v1/actividades`:

| Método | Endpoint | Permiso Canónico (3 Niveles) | Permiso Fallback |
| :--- | :--- | :--- | :--- |
| `GET` | `/notas/equipo` | `actividades.notas.view` | `operations.notas.read` |
| `POST` | `/notas/equipo` | `actividades.notas.create` | `operations.notas.create` |
| `POST` | `/notas/equipo/{id}/read` | `actividades.notas.view` | `operations.notas.read` |
| `PUT` | `/notas/equipo/{id}` | `actividades.notas.create` | `operations.notas.update` |
| `DELETE` | `/notas/equipo/{id}` | `actividades.notas.delete` | `operations.notas.delete` |
| `GET` | `/notas/personales` | `actividades.notas.view` | `operations.notas.read` |
| `POST` | `/notas/personales` | `actividades.notas.create` | `operations.notas.create` |
| `PUT` | `/notas/personales/{id}` | `actividades.notas.create` | `operations.notas.update` |
| `DELETE` | `/notas/personales/{id}` | `actividades.notas.delete` | `operations.notas.delete` |
| `GET` | `/tareas` | `actividades.tareas.view` | `operations.tareas.read` |
| `POST` | `/tareas` | `actividades.tareas.create` | `operations.tareas.create` |
| `PATCH` | `/tareas/{id}/estado` | `actividades.tareas.update` | `operations.tareas.update` |
| `PUT` | `/tareas/{id}` | `actividades.tareas.update` | `operations.tareas.update` |
| `DELETE` | `/tareas/{id}` | `actividades.tareas.update` | `operations.tareas.delete` |
| `GET` | `/plantillas-rutinas` | `actividades.tareas.view` | `operations.tareas.read` |
| `POST` | `/plantillas-rutinas` | `actividades.tareas.create` | `operations.tareas.create` |
| `POST` | `/plantillas-rutinas/{id}/aplicar` | `actividades.tareas.create` | `operations.tareas.create` |
| `GET` | `/horarios` | `actividades.horarios.view` | `operations.turnos.read` |
| `POST` | `/horarios` | `actividades.horarios.manage` | `operations.turnos.create` |
| `PUT` | `/horarios/{id}` | `actividades.horarios.manage` | `operations.turnos.update` |
| `DELETE` | `/horarios/{id}` | `actividades.horarios.manage` | `operations.turnos.delete` |
| `POST` | `/horarios/clonar-semana` | `actividades.horarios.manage` | `operations.turnos.create` |
| `POST` | `/horarios/validar-alertas` | `actividades.horarios.view` | `operations.turnos.read` |
| `POST` | `/minuta-traspaso` | `actividades.notas.view` | `operations.notas.read` |

---

### 5. Frontend React 19 y Experiencia Mobile-First (`oppytec-frontend/src/features/activities/`)

1. **Rutas Integradas en `AppRouter` (`router.tsx`):**
   - `/actividades/notas` -> `<NotasPage />`
   - `/actividades/tareas` -> `<TareasPage />`
   - `/actividades/horarios` -> `<HorariosPage />`
   - `/actividades` -> Redirección automática a `/actividades/notas`.
2. **Componentes Clave:**
   - `NotasPage.tsx`: Feed interactivo, tabs 'Notas de Equipo' vs 'Personales', selector horizontal de categorías operativas, menciones interactivas `@` y tags `#`, y botón "🤖 Resumen de Traspaso (OppyFy)".
   - `NotaCard.tsx`: Avatar gastronómico, insignias de rol, lectura idempotente con contador visual de vistos y menú de acciones.
   - `MinutaTraspasoDialog.tsx`: Diálogo modal/drawer adaptativo con resumen de los 4 puntos clave, KPIs y acciones de copiar al portapapeles o guardar como nota de equipo.
   - `TareasPage.tsx`: Doble modo Kanban de 4 columnas y Checklist ultracompacto para smartphones.
   - `IncompleteTaskDialog.tsx`: Modal obligatorio que bloquea la marcación de tarea incompleta sin justificación de al menos 5 caracteres.
   - `HorariosPage.tsx`: Cuadrante semanal interactivo, vista móvil deslizable de 3 días con gestos swipe, simulación en vivo de alertas laborales y botón de clonación semanal.

---

### 6. Ciberseguridad Ofensiva Red Team (`test_18_actividades_security_and_idor.py`)

Aprobado con veredicto `SECURITY_APPROVED` sin vetos sobre 6 vectores:
1. **Vector 1 (Cross-Tenant IDOR Isolation):** Aislamiento estricto por `tenant_id`; denegación 404 semántica sin fuga de existencia de recursos cruzados.
2. **Vector 2 (Personal Notes Strict Privacy):** Imposibilidad de listar o modificar notas personales de otros colaboradores.
3. **Vector 3 (Task Incompleta Mandatory Justification):** Rechazo determinista de tareas incompletas sin justificación válida.
4. **Vector 4 (RBAC 3-Level Permission Enforcement):** Bloqueo 403 Forbidden RFC 7807 ante carencia de permisos específicos.
5. **Vector 5 (Polyglot Injection Neutralization):** Bloqueo de inyecciones XSS y SSTI con HTTP 422 `SecurityValidationError`.
6. **Vector 6 (Labor Audit & Schedule Isolation):** Auditoría laboral de 12 horas y 40 horas circunscrita estrictamente al inquilino autenticado.
