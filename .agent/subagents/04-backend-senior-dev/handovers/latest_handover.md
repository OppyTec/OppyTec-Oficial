# Reporte de Traspaso (`Handover`) — Agente 04: Backend Senior FastAPI, Clean Architecture & RBAC 3-Niveles

- **Fecha UTC:** 2026-11-02T19:05:00Z
- **Agente:** Agente 04 (`04-backend-senior-dev`)
- **Fase / Hito:** Fase 2 y 3 del Plan Maestro del Panel de Actividades — Backend Clean Architecture, Endpoints REST con RBAC de 3 Niveles y WebSockets para Notas, Tareas y Horarios.
- **Estado de Certificación:** `ACTIVIDADES_PANEL_PHASE_2_3_CERTIFIED` (10/10 tests unitarios y de integración passing al 100%, 0 errores `mypy --strict`, sincronizado con Graphify).

---

## 1. Completed (Qué se ejecutó y validó)

1. **Gestión de Dominio y Lógica de Aplicación (`ActividadesService`)**:
   - Implementado en `oppytec-backend/src/modules/operations/application/actividades_service.py`:
     * **Notas de Equipo (Bitácora Compartida)**:
       - `create_nota_equipo`: creación con autor, contenido, área, categoría, insumo, receta, foto R2 y menciones múltiples de colaboradores (`NotaEquipoMencion`).
       - `get_notas_equipo`: filtros multidimensionales (`area_id`, `categoria`, `search`, `user_id_mencionado`, `leido_por_user_id`), paginación y enriquecimiento con `leido_por_mi` y `total_lecturas`.
       - `mark_nota_as_read`: confirmación de lectura **100% idempotente** (`NotaEquipoLectura`). Si el usuario ya confirmó lectura, no genera error ni duplicados.
       - `update_nota_equipo` y `delete_nota_equipo` (soft-delete con `deleted_at`).
     * **Notas Personales (Apuntes Privados)**:
       - `create_nota_personal`, `get_notas_personales`, `update_nota_personal`, `delete_nota_personal`.
       - Privacidad estricta: un colaborador solo puede consultar, modificar o eliminar sus propias notas personales (los intentos ajenos lanzan `DomainValidationError`).
     * **Tareas Operativas y Checklists**:
       - `create_tarea`, `get_tareas` (filtros por estado, área, asignado, urgencia, búsqueda, completitud), `update_tarea`, `delete_tarea`.
       - **Validación Obligatoria Inviolable**: Si una tarea transiciona a `'incompleta'`, el campo `'nota_incompleta'` no puede ser vacío (arroja `DomainValidationError` RFC 7807).
       - Sincronización automática del flag booleano `completada` al transicionar a `'completada'`.
     * **Plantillas de Rutinas de Apertura/Cierre**:
       - `create_plantilla_rutina` y `get_plantillas_rutinas`.
       - `aplicar_plantilla_rutina`: genera e instancia automáticamente en lote todas las tareas del turno basadas en los items del checklist (`items_json`).
     * **Horarios, Turnos, Clonación y Auditoría Laboral**:
       - `create_turno_horario`, `get_turnos_horarios`, `update_turno_horario`, `delete_turno_horario`.
       - `clonar_semana(fecha_lunes_origen, fecha_lunes_destino)`: traslada atómicamente la grilla completa de turnos de una semana a otra desplazando días con delta exacto (valida que ambas fechas sean lunes).
       - `validar_alertas_laborales(usuario_id, nuevo_turno)`:
         * **Regla 1**: Alerta y bloqueo si el descanso es menor a 12 horas consecutivas entre jornadas contiguas (`DESCANSO_INSUFICIENTE`).
         * **Regla 2**: Alerta si la jornada proyectada excede las 40 horas semanales legales (`EXCESO_40_HORAS` - Ley 40 Horas / Código del Trabajo).
     * **Eventos en Tiempo Real (WebSocket)**:
       - Despacho reactivo mediante `get_realtime_publisher().publish_event(...)` para notas, tareas y turnos invalidando query keys de TanStack Query (`["actividades", ...]`).

2. **Contratos y Schemas Pydantic V2 (`schemas_actividades.py`)**:
   - Implementado en `oppytec-backend/src/modules/operations/presentation/schemas_actividades.py`:
     * `ConfigDict(extra="forbid")` en el 100% de request payloads.
     * `ConfigDict(from_attributes=True)` en modelos de respuesta.
     * Strict Decimal (0 floats) para cálculo de horas y auditoría laboral.
     * Schemas implementados: `NotaEquipoCreateRequest`, `NotaEquipoUpdateRequest`, `NotaEquipoResponse`, `NotaMencionResponse`, `NotaLecturaResponse`, `NotaPersonalCreateRequest`, `NotaPersonalUpdateRequest`, `NotaPersonalResponse`, `TareaCreateRequest`, `TareaEstadoUpdateRequest`, `TareaUpdateRequest`, `TareaResponse`, `PlantillaRutinaCreateRequest`, `PlantillaRutinaUpdateRequest`, `PlantillaRutinaResponse`, `AplicarPlantillaRequest`, `TurnoHorarioCreateRequest`, `TurnoHorarioUpdateRequest`, `TurnoHorarioResponse`, `ClonarSemanaRequest`, `AlertaLaboralItem`, `ValidacionLaboralResponse`, `ValidarTurnoAlertaRequest`.

3. **Enrutador REST FastAPI (`router_actividades.py`)**:
   - Implementado en `oppytec-backend/src/modules/operations/presentation/router_actividades.py` con prefijo `/api/v1/actividades`:
     * Guardias RBAC de 3 niveles con `RequireTenantPermission` y fallback:
       - `actividades.notas.view`, `actividades.notas.create`, `actividades.notas.delete`
       - `actividades.tareas.view`, `actividades.tareas.create`, `actividades.tareas.update`
       - `actividades.horarios.view`, `actividades.horarios.manage`
     * Montado en `src/main.py` y exportado en `src/modules/operations/presentation/__init__.py`.

4. **Suite de Pruebas Unitarias y de Integración**:
   - Implementado en `oppytec-backend/tests/unit/modules/test_actividades_services.py`:
     * `test_notas_equipo_lifecycle_and_idempotent_read`
     * `test_notas_personales_privacy`
     * `test_tarea_lifecycle_and_incompleta_validation`
     * `test_plantillas_rutinas_and_aplicar`
     * `test_turnos_horarios_and_clonar_semana`
     * `test_validar_alertas_laborales_descanso_12h`
     * `test_validar_alertas_laborales_exceso_40_horas`
     * `test_rest_api_notas_equipo_rbac`
     * `test_rest_api_tareas_rbac_and_incompleta_rule`
     * `test_rest_api_horarios_and_validar_alertas`
   - Resultados: **10/10 tests passing al 100%**.
   - Verificación global de operaciones: **17/17 tests passing**.
   - Tipado estricto: **0 errores con `mypy --strict`**.

5. **Gobernanza y Sincronización Graphify**:
   - Sincronizado AST con `python scripts/harness.py sync-graph` (116 nodos, 141 aristas).

---

## 2. Friction & Failures (Fricciones o Aprendizajes)

- Se identificó que la expresión regular canónica `THREE_LEVEL_PERMISSION_REGEX` exige estrictamente 3 niveles `<modulo>.<submodulo>.<funcion>`. Por lo tanto, los permisos se normalizaron a `actividades.notas.*`, `actividades.tareas.*` y `actividades.horarios.*`, configurando fallback backward-compatible a `operations.*`.

---

## 3. Next Exact Action (Siguiente Acción Exacta)

- Notificar al Orquestador (`cd95f53f-d053-4962-92d5-5c31df5bfe58`) del cierre exitoso de las Fases 2 y 3 para habilitar la Fase 4 de Frontend UI/UX con el Agente 05 (`05-frontend-senior-dev`).
