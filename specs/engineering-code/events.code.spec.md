---
spec_id: ENG-EVENTS-SALONES-BANQUETES
title: "Módulo de Eventos, Salones, Banquetes y Consumo Transaccional de Inventario"
audience: engineering_internal
domain_module: events
paired_spec: specs/business-domain/events.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 8"
---

# Gestión de Eventos, Salones y Consumo Transaccional de Inventario — Especificación de Ingeniería

## Contrato Técnico

### 1. Arquitectura de Dominio DDD (`oppytec-backend/src/modules/events/`)

#### A. Capa de Dominio (`domain/`)
- **Value Objects Inmutables con Precisión `Decimal`:**
  - `EventStatus`: Enum canónico (`AGENDADO`, `EN_CURSO`, `EJECUTADO`, `CANCELADO`).
  - `SalonState`: Enum de estado operativo/higiénico (`LIMPIO`, `EN_USO`, `MANTENIMIENTO`, `SUCIO`).
  - `EventTimeSlot`: Modela la fecha y franja horaria `(fecha, hora_inicio, hora_fin)`.
    - Método `overlaps(other: EventTimeSlot) -> bool`: Comprueba colisión temporal bidireccional estricta en la misma fecha cuando hay solapamiento de horas:
      $$\text{fecha} = \text{other.fecha} \land \text{hora\_inicio} < \text{other.hora\_fin} \land \text{hora\_fin} > \text{other.hora\_inicio}$$
  - `SalonCapacity`: Valida aforo máximo $(\text{capacidad} > 0)$ y emite advertencia ante sobrecupo.
  - `MoneyAmount`: Primitiva monetaria con precisión `Decimal` (dos decimales) para aranceles netos, IVA y precios brutos:
    $$\text{precio\_bruto} = \text{precio\_neto} \times \left(1 + \frac{\text{iva\_porcentaje}}{100}\right)$$
  - `ItemQuantity`: Modela cantidades requeridas de insumos y porciones con precisión `Decimal(12, 4)`.

- **Entidades y Agregados DDD (`domain/entities.py`):**
  - `Salon`: Entidad raíz de espacios físicos con nombre, capacidad, precio neto, IVA, precio bruto, estado higiénico y lista de áreas operativas vinculadas.
  - `EventoItem`: Ítem directo de bodega con `producto_id`, `bodega_id`, `cantidad` y costo unitario estimado.
  - `EventoReceta`: Receta gastronómica con `receta_id` y factor multiplicador de `cantidad` (porciones).
  - `EventoCombo`: Paquete promocional con `combo_id` y multiplicador de `cantidad`.
  - `EventoTrabajador`: Asignación de brigada con `usuario_id` y `rol_en_evento`.
  - `Evento` (Agregado Raíz):
    - Encabezado: `id` (UUID), `nombre`, `titular`, `encargado_id`, `salon_id`, `time_slot`, `lugar`, `cantidad_invitados`, `color`, `estado`, `ejecutado`, `cancelado`.
    - Colecciones anidadas: `items`, `recetas`, `combos`, `trabajadores`.
    - Invariantes de ciclo de vida:
      - `assert_can_be_executed()`: Rechaza ejecución si ya está ejecutado o si está cancelado.
      - `assert_can_be_edited()`: Impide modificar un evento ya ejecutado o cancelado.
      - `assert_can_be_reactivated()`: Solo permite reactivar eventos previamente cancelados.

- **Excepciones de Dominio Específicas (`domain/exceptions.py`):**
  - `OverbookingConflictError`: Conflicto 409 cuando dos eventos colisionan en salón y horario.
  - `EventAlreadyExecutedError`: Error 409 al intentar modificar o re-ejecutar un evento sellado.
  - `EventAlreadyCanceledError`: Error 409 al operar sobre un evento cancelado.
  - `EventNotExecutedError`: Error 400 al intentar revertir un evento que nunca fue ejecutado.
  - `SalonNotFoundError` / `EventNotFoundError`: Error 404 semántico.
  - `InvalidTimeRangeError`: Error 400 cuando `hora_fin <= hora_inicio`.

#### B. Capa de Aplicación (`application/services.py`)
- `SalonService`:
  - `list_salones(tenant_id, area_operativa_id=None)`: Lista salones con áreas operativas asociadas.
  - `create_salon(tenant_id, data)`: Alta de salón con recálculo determinista de IVA y vinculación de áreas.
  - `update_salon(tenant_id, salon_id, data)`: Modificación de recinto y sincronización M:N con áreas.
  - `delete_salon(tenant_id, salon_id)`: Soft-delete con verificación de eventos futuros pendientes.
- `EventService`:
  - `list_events(tenant_id, estado=None, fecha_desde=None, fecha_hasta=None, salon_id=None)`: Búsqueda con filtros multi-parámetro.
  - `get_event_by_id(tenant_id, event_id)`: Detalle completo con items, recetas, combos y brigada.
  - `create_event(tenant_id, data, current_user_id)`:
    - Validación anti-overbooking transaccional contra la base de datos para el mismo salón y franja horaria.
    - Persistencia atómica de encabezado, insumos directos, recetas, combos y brigada.
    - Emisión de notificación WebSocket `events.changed`.
  - `update_event(tenant_id, event_id, data, current_user_id)`: Actualización con verificación de inmutabilidad ante eventos ejecutados y re-validación de sobrecupo/overbooking.
  - `delete_event(tenant_id, event_id, current_user_id)`: Soft-delete con liberación de salón y stock comprometido.
  - `cancel_event(tenant_id, event_id, motivo, current_user_id)`: Transición a `CANCELADO`, liberación de stock comprometido y auditoría.
  - `reactivate_event(tenant_id, event_id, current_user_id)`: Re-validación estricta de disponibilidad del salón antes de devolverlo a `AGENDADO`.
  - `execute_event(tenant_id, event_id, current_user_id)`:
    - Desglose BOM recursivo de materias primas (insumos directos + recetas + combos).
    - Agrupación por `(producto_id, bodega_id)`.
    - Generación de asientos inmutables en Kardex con tipo `CONSUMO_EVENTO` a costo PPP vigente.
    - Registro en tabla pivote de auditoría `evento_consumos_kardex`.
    - Marcado `ejecutado = True`, `estado = EJECUTADO`, `ejecutado_at = now()`.
    - Notificación en tiempo real via Redis Pub/Sub a WebSocket.
  - `reverse_event(tenant_id, event_id, motivo, current_user_id)`:
    - Reversión formal mediante asientos compensatorios en Kardex (`AJUSTE_EVENTO_REVERSA`).
    - Marcado `ejecutado = False`, `estado = CANCELADO`, `cancelado = True`.
  - `get_faltantes_analytics(tenant_id, area_operativa_id=None)`: Cálculo analítico de demanda consolidada futura vs stock disponible actual.
  - `get_committed_stock(tenant_id, product_id=None)`: Cálculo de stock comprometido para el módulo de inventario.
  - `get_event_alerts(tenant_id)`: Clasificación de alertas de abastecimiento en severidad `CRITICAL` (<48h) y `WARNING` (<=14d).
  - `generate_minuta_csv(tenant_id, event_id)`: Generación de acta y minuta de producción en formato CSV con UTF-8 BOM (`\ufeff`) para compatibilidad nativa con Excel.

#### C. Capa de Infraestructura y Persistencia Multi-Tenant (`infrastructure/models.py`)
- **Aislamiento Multi-Tenant:**
  Todas las entidades heredan de `TenantBase` para residir en esquemas PostgreSQL aislados dinámicos `tenant_*`.
- **Modelos de Persistencia (SQLAlchemy 2.0 Async):**
  - `salones`: `id` (UUID PK default `gen_random_uuid()`), `nombre` (`String(120)`), `capacidad_personas` (Integer), `precio_neto` (`Numeric(14, 2)`), `iva_porcentaje` (`Numeric(5, 2)` default 19.00), `precio_bruto` (`Numeric(14, 2)`), `notas` (Text), `estado` (`String(32)` default `'limpio'`), `color` (`String(32)`), `AuditTimestampsMixin`, `SoftDeleteMixin`.
  - `salon_areas_operativas`: `salon_id` (UUID FK `salones.id` ON DELETE CASCADE), `area_operativa_id` (BigInteger FK `areas_operativas.id` ON DELETE CASCADE), PK compuesta `(salon_id, area_operativa_id)`.
  - `eventos`: `id` (UUID PK), `nombre` (`String(180)`), `titular` (`String(180)`), `encargado_id` (BigInteger FK `usuarios.id` nullable), `salon_id` (UUID FK `salones.id` nullable), `fecha` (Date), `hora_inicio` (Time nullable), `hora_fin` (Time nullable), `lugar` (`String(255)`), `cantidad_invitados` (Integer), `estado` (`String(32)` default `'agendado'`), `color` (`String(32)`), `ejecutado` (Boolean default False), `cancelado` (Boolean default False), `ejecutado_at` (DateTime nullable), `valor_publico` (`Numeric(14, 2)`), `nota_visible` (Text), `nota_interna` (Text), `AuditTimestampsMixin`, `SoftDeleteMixin`.
    - Índices: `ix_eventos_tenant_fecha` en `(fecha)`, `ix_eventos_salon_fecha` en `(salon_id, fecha)`.
  - `evento_items`: `id` (UUID PK), `evento_id` (UUID FK `eventos.id` ON DELETE CASCADE), `producto_id` (BigInteger FK `productos.id`), `bodega_id` (BigInteger FK `bodegas.id`), `cantidad` (`Numeric(12, 4)`), `costo_unitario_estimado` (`Numeric(14, 2)`).
  - `evento_recetas`: `id` (UUID PK), `evento_id` (UUID FK `eventos.id` ON DELETE CASCADE), `receta_id` (BigInteger FK `recetas.id`), `cantidad` (`Numeric(12, 4)`).
  - `evento_combos`: `id` (UUID PK), `evento_id` (UUID FK `eventos.id` ON DELETE CASCADE), `combo_id` (BigInteger FK `combos.id`), `cantidad` (`Numeric(12, 4)`).
  - `evento_trabajadores`: `id` (UUID PK), `evento_id` (UUID FK `eventos.id` ON DELETE CASCADE), `usuario_id` (BigInteger FK `usuarios.id`), `rol_en_evento` (`String(64)`), `notas` (Text).
  - `evento_consumos_kardex`: `id` (UUID PK), `evento_id` (UUID FK `eventos.id`), `kardex_movement_id` (BigInteger FK `kardex_movements.id`), `created_at` (DateTime default now).
- **Migración Alembic Correlativa Lineal 0013:**
  - Archivo: `oppytec-backend/alembic/versions/0013_tenant_events_salones_and_reservations.py`.
  - Predecesora lineal: `0012_public_ai_model_configs_catalog_extension.py`.
  - Crea la totalidad de tablas en todos los esquemas `tenant_*` y en la plantilla `tenant_base`.

#### D. Capa de Presentación REST (`presentation/router.py`)
- Respuestas normalizadas **RFC 7807** (`ProblemDetails`) con códigos HTTP semánticos:
  - `200 OK` / `201 Created` / `204 No Content`.
  - `400 Bad Request`: Rango horario inválido o cantidad $\le 0$.
  - `403 Forbidden`: Intento de acceso cross-tenant o falta de privilegios RBAC.
  - `404 Not Found`: Evento o salón no encontrado.
  - `409 Conflict`: Sobreventa / colisión horaria (`OVERBOOKING_CONFLICT`) o evento ya ejecutado.
  - `422 Unprocessable Entity`: Fallo de validación Pydantic V2.
- **Rutas Principales:**
  - `GET /api/v1/events/salones`: Listado de salones.
  - `POST /api/v1/events/salones`: Creación de salón.
  - `GET /api/v1/events/salones/{salon_id}`: Consulta de salón.
  - `PUT /api/v1/events/salones/{salon_id}`: Actualización de salón.
  - `DELETE /api/v1/events/salones/{salon_id}`: Soft delete de salón.
  - `GET /api/v1/events`: Listado paginado/filtrado de eventos.
  - `POST /api/v1/events`: Creación de evento con verificación anti-overbooking.
  - `GET /api/v1/events/{event_id}`: Detalle de evento con BOM y brigada.
  - `PUT /api/v1/events/{event_id}`: Actualización de evento.
  - `DELETE /api/v1/events/{event_id}`: Soft delete de evento.
  - `POST /api/v1/events/{event_id}/execute`: Ejecución transaccional y rebaje en Kardex.
  - `POST /api/v1/events/{event_id}/cancel`: Cancelación y liberación de salón.
  - `POST /api/v1/events/{event_id}/reactivate`: Reactivación verificada.
  - `POST /api/v1/events/{event_id}/reverse`: Reversión con asientos compensatorios.
  - `GET /api/v1/events/{event_id}/minuta`: Minuta de producción estructurada.
  - `POST /api/v1/events/export/minuta-excel`: Descarga de acta/minuta en CSV/Excel.
  - `GET /api/v1/events/analytics/faltantes`: Resumen de quiebres futuros.
  - `GET /api/v1/events/analytics/committed-stock`: Stock comprometido por producto.
  - `GET /api/v1/events/alerts`: Alertas clasificadas CRITICAL/WARNING.

---

### 2. Notificaciones en Tiempo Real (WebSocket Zero-Polling)

- Publicación asíncrona mediante Redis Pub/Sub hacia el canal `/api/v1/ws/realtime`:
  - `events.events.changed`: Emitido ante creación, edición, cancelación o ejecución de cualquier evento. Invalida queries TanStack Query `["events"]`, `["events_faltantes"]` y `["inventory"]`.
  - `events.salones.changed`: Emitido ante creación, edición o borrado de salones. Invalida `["salones"]`.
  - `events.changed`: Evento paraguas para refresco reactivo general de alertas y badges de navegación.

---

### 3. Matriz RBAC Dual de 3 Niveles

| Clave de Permiso | Descripción Operativa | Nivel de Riesgo |
|---|---|---|
| `events.salones.read` | Visualización del catálogo y estados de salones | Bajo |
| `events.salones.manage` | Creación, edición, tarifas y borrado de salones | Medio |
| `events.events.read` | Consulta de programación, calendario y minutas | Bajo |
| `events.events.create` | Reserva de salones y creación de eventos | Medio |
| `events.events.edit` | Modificación de horarios, insumos y brigada | Medio |
| `events.events.delete` | Eliminación lógica de eventos programados | Alto |
| `events.events.execute` | Deducción transaccional en inventario Kardex | Crítico |
| `events.events.cancel` | Cancelación de eventos y reversión compensatoria | Alto |

---

### 4. Observabilidad OpenTelemetry & Sentry

- **Spans Instrumentados:**
  - `events.create`: Duración de validación anti-overbooking y persistencia atómica.
  - `events.execute`: Desglose recursivo BOM y generación de movimientos en Kardex.
  - `events.bom_explosion`: Tiempo de recursión sobre árboles de recetas y combos.
  - `events.faltantes.compute`: Tiempo de cruce entre demanda agregada y saldos de bodega.
  - `events.reversal`: Ejecución de asientos compensatorios en Kardex.
- **Atributos de Contexto:**
  - `tenant_id`, `event_id`, `salon_id`, `items_count`, `recetas_count`, `combos_count`, `guests_count`.
  - Sanitización de datos personales sensibles (nombres de comensales, notas privadas).

---

### 5. Interfaz Frontend React 19 (`oppytec-frontend/src/features/events/`)

- **Estructura Modular:**
  - `types.ts`: Tipos TypeScript canónicos (`Salon`, `Evento`, `EventoItem`, `EventoReceta`, `EventoCombo`, `EventoTrabajador`, `FaltanteItem`, `CommittedStockItem`, `EventAlertItem`).
  - `api/eventsApi.ts`: Cliente HTTP Axios con manejo de errores RFC 7807 y soporte de fallback resiliente.
  - `hooks/`:
    - `useEvents.ts`: Cache TanStack Query v5, mutaciones reactivas y helpers de costeo.
    - `useSalones.ts`: Catálogo de salones y sincronización con áreas operativas.
    - `useEventAlerts.ts`: Suscripción WebSocket, cómputo de stock comprometido y cálculo de saldo disponible real.
  - `components/`:
    - `EventsPage.tsx`: Vista principal con `SectionHeader` rosa (#ec4899), toolbar unificado, pestañas con contadores reactivos (`proximos`, `historial`, `cancelados`) y toggle tarjetas/calendario.
    - `EventoCard.tsx`: Tarjetas de eventos con borde cromático dinámico, desglose de insumos/recetas, brigada asignada y botones de acción rápida contextuales.
    - `EventosCalendar.tsx`: Calendario dinámico multi-vista (`month`, `week`, `3days`, `day`), navegación temporal, detección visual de colisión y apertura de creación por clic en celda.
  - `dialogs/`:
    - `EventoDialog.tsx`: Wizard en 2 pasos (Paso 1: Datos y brigada; Paso 2: Insumos directos, recetas y combos con búsqueda predictiva).
    - `SalonesDialog.tsx`: CRUD de salones con cálculo bidireccional de IVA (neto/IVA/bruto) y selector de áreas operativas.
    - `ResumenFaltantesDialog.tsx`: Banner de alerta, comparativa disponible vs necesario y descarga de pedido sugerido.
    - `EventoDetailDialog.tsx`: Vista detallada de evento con acta de minuta y enlace a Kardex.
  - `shared/i18n/locales/{es,en}/events.json`: 100% de cobertura bilingüe en títulos, labels, botones y mensajes de error.
  - Soporte Multi-Moneda FX mediante precisión `Decimal` en backend y componentes `MoneyBadge` y `formatMoney` en frontend.

---

## Invariantes

1. **Cero Coma Flotante IEEE 754:** Todos los valores monetarios (aranceles de salón, precios públicos, costos estimados) y cantidades físicas de insumos operan con `Decimal` en backend y manipulación matemática exacta en frontend.
2. **Exclusión Temporal Anti-Overbooking:** Es físicamente imposible registrar dos eventos con superposición horaria en el mismo salón para la misma fecha calendario.
3. **Inmutabilidad de Kardex Append-Only:** Prohibido realizar `UPDATE` directo sobre existencias de inventario; el consumo ocurre estrictamente mediante asientos `CONSUMO_EVENTO` y la anulación mediante `AJUSTE_EVENTO_REVERSA`.
4. **Sellado de Eventos Ejecutados:** Un evento con `ejecutado = True` no puede ser editado ni eliminado; únicamente revertido mediante el flujo formal compensatorio.
5. **No Negatividad de Stock Comprometido:** $\text{Stock Comprometido} \ge 0$.
6. **Saldo Disponible Real Protegido:** $\text{Stock Disponible Real} = \max(0, \text{Stock Físico} - \text{Stock Comprometido})$.
7. **Aislamiento Multi-Tenant e Inmunidad IDOR:** Acceso estrictamente acotado al esquema del tenant autenticado; cualquier acceso cruzado resulta en HTTP 403.

---

## Evaluación JEV Sistema 1

jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- **Primitiva:** `Jev.boolean`
- **Umbral de confianza:** `0.95` (bajo umbral → revisión humana / camino determinista).
- **Justificación:** La gestión de reservas de salones con exclusión horaria anti-overbooking, el desglose recursivo de listas de materiales (BOM) gastronómicas, la deducción contable en el libro mayor inmutable de Kardex a costo PPP y las transacciones ACID multi-tabla son procesos computacionales deterministas e inmutables que no admiten heurísticas probabilísticas ni inferencias de lenguaje.

---

## Pruebas (Co-Creación 1:1)

### Backend (Pytest)
- `oppytec-backend/tests/unit/modules/test_events_domain_and_models.py`: Value Objects de dominio (`EventTimeSlot`, `SalonCapacity`, `MoneyAmount`), entidades y agregado raíz `Evento`, validaciones de solapamiento y modelos SQLAlchemy 2.0.
- `oppytec-backend/tests/unit/modules/test_events_services.py`: Servicios de aplicación transaccionales (`SalonService`, `EventService`), validación anti-overbooking (HTTP 409), ejecución y deducción en Kardex, reversión compensatoria, alertas de stock comprometido y exportación de minuta CSV.
- `oppytec-backend/tests/unit/modules/test_events_observability.py`: Trazas OpenTelemetry, atributos contextuales y sanitización PII.
- `oppytec-backend/tests/unit/modules/test_oppyfy_events_tools.py`: Integración de herramientas de consulta de eventos con el asistente OppyFy.

### Frontend (Vitest)
- `oppytec-frontend/src/features/events/__tests__/hooks.test.ts`: 17 pruebas unitarias de hooks reactivos (`useEvents`, `useSalones`, `useEventAlerts`), mutaciones optimistas y cálculo de costos.
- `oppytec-frontend/src/features/events/__tests__/EventsPage.test.tsx`: 8 pruebas de renderizado de la vista principal, navegación de pestañas (`proximos`, `historial`, `cancelados`), toggle entre tarjetas y calendario, y apertura de diálogos.
- `oppytec-frontend/src/features/events/__tests__/EventsI18nAndFx.test.tsx`: 5 pruebas de cobertura de internacionalización (`es`/`en`), cero cadenas hardcodeadas y formateo de aranceles multi-moneda con `MoneyBadge`.
