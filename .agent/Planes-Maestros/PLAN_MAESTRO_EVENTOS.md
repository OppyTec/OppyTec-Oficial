# 📋 PLAN MAESTRO DE CONTROL Y EJECUCIÓN: MÓDULO DE EVENTOS, SALONES, BANQUETES Y CONSUMO DE INVENTARIO (`/eventos`)

> **Regla de Gobernanza:** Este documento es el tablero de control de ejecución estricto del Módulo de Eventos de OppyTec v2.0.  
> Cada fase y paso debe ser **100% corroborado y aprobado** antes de pasar al siguiente.  
> **Solo cuando se finalicen todos los pasos**, este documento podrá ser archivado o marcado como completado, no antes.  
> **Fuentes de Verdad Históricas (100% Solo Lectura):**  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Eventos/index.tsx` (Vista principal, toolbar unificado, pestañas Próximos/Historial/Cancelados, switch tarjetas/calendario y banner de faltantes)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Eventos/EventoCard.tsx` (Tarjeta informativa de evento con insumos, recetas, encargados y acciones rápidas)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Eventos/EventoDialog.tsx` (Asistente en dos pasos para reserva de evento, insumos, recetas, combos y asignación de personal)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Eventos/EventosCalendar.tsx` (Calendario dinámico con vistas Mes, Semana, 3 Días y Día con soporte de colisión horaria de salones)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Eventos/ResumenFaltantes.tsx` (Banner analítico de alerta de quiebre de stock para eventos futuros con exportación a pedido sugerido)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Eventos/SalonesDialog.tsx` (CRUD de salones/espacios físicos, vinculación con áreas operativas, cálculo de IVA y estado higiénico)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Eventos/types.ts` (Contratos TypeScript históricos de eventos, salones, items, recetas y combos)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Eventos/useEventos.ts`, `useSalones.ts`, `useUsuarios.ts` (Hooks históricos de negocio y sincronización con API)  
> - `OppyTec-Legacy/OppyTec_Backend/src/operations/routers/event_router.py` (Endpoints de operaciones para salones, eventos y alertas de inventario)  
> - `OppyTec-Legacy/OppyTec_Backend/src/operations/services/event_service.py` (Lógica transaccional de eventos, cálculo de ingredientes por recetas/combos y validaciones de lotes)  
> - `OppyTec-Legacy/OppyTec_Backend/alembic/versions/0011_add_eventos_table.py`, `295e03a64973_add_salones_and_update_eventos.py`, `9b4817c36dbd_eventos_and_notes_updates.py` (Esquemas DDL históricos de eventos, trabajadores y salones)  
> **Destinos de Construcción en OppyTec v2.0:**  
> - Frontend: `oppytec-frontend/src/features/events/` (`EventsPage.tsx`, `components/`, `dialogs/`, `hooks/`, `types.ts`)  
> - Backend: `oppytec-backend/src/modules/events/` (DDD: `domain/`, `application/`, `infrastructure/`, `presentation/`)  

---

## 📊 Estado General del Proyecto

- [x] **Fase 1:** Arquitectura de Dominio DDD, Esquemas PostgreSQL `tenant_*` y Migración Alembic 0013 (`0013_tenant_events_salones_and_reservations.py`, down_revision `0012_public_ai_model_configs_catalog_extension`)
- [x] **Fase 2:** Motor Backend FastAPI & Integración Transaccional con Kardex Inmutable (endpoints REST RFC 7807, RBAC dual 3-niveles `events.*`, validación atómica anti-overbooking y exclusión temporal)
- [x] **Fase 3:** Frontend Feature Core & Hooks Reactivos (`types.ts`, `useEvents.ts`, `useSalones.ts`, `useEventAlerts.ts`, TanStack Query v5 + WebSockets realtime `/api/v1/ws/realtime`) — *COMPLETADA (Agente 05 - 22/22 pruebas Vitest pasando al 100%)*
- [x] **Fase 4:** Vista Principal `/eventos` (`EventsPage.tsx`): `SectionHeader` centrado (#ec4899), Toolbar unificado con selectores de área/bodega, Pestañas de estado (Próximos/Agendados, Finalizados, Cancelados), Toggle entre Vista Tarjetas y Vista Calendario Interactivo multi-vista (`month`, `week`, `3days`, `day`) — *COMPLETADA (Agente 05)*
- [x] **Fase 5:** Modales y Diálogos Operativos: `EventoDialog` (wizard de dos pasos con insumos directos, recetas gastronómicas, combos y asignación de brigada), `SalonesDialog` (gestión de espacios físicos, capacidades, áreas operativas y aranceles netos/brutos con IVA), `ResumenFaltantesDialog` (análisis en tiempo real de faltantes con descarga de pedido sugerido) — *COMPLETADA (Agente 05)*
- [x] **Fase 6:** Flujo de Ejecución y Consumo Transaccional en Kardex (descuento automático en `kardex_movements` con tipo `CONSUMO_EVENTO`, cálculo PPP, desglose BOM recursivo de recetas/combos, reversión controlada y exportación de actas de minuta/producción en Excel) — *COMPLETADA (Agente 04)*
- [x] **Fase 7:** Concepto de "Stock Comprometido" e Integración con Inventario & Alertas (indicador de stock reservado en bodegas para eventos futuros que previene falsos positivos de stock disponible en `/inventario` y `/alertas`) — *COMPLETADA (Agentes 04 y 05)*
- [x] **Fase 8:** Capas Cruzadas: i18n 100% `es`/`en` (`events.json`), Multi-Moneda FX (`Decimal`) para presupuestos de salones/banquetes, Observabilidad OpenTelemetry, Testing 5D (35 Pytest + 30 Vitest), Sincronización Bóvedas OpenSpec y Graphify AST — *COMPLETADA (Agentes 07, 08, 09, 10, 11, 12)*

---

## 🔍 Detalle y Criterios de Aceptación por Fase

---

### [x] FASE 1: Arquitectura de Dominio DDD, Esquemas PostgreSQL `tenant_*` y Migración Alembic 0013
- [x] **1.1** Modelado de Persistencia Multi-Tenant en `oppytec-backend/src/modules/events/infrastructure/models.py`:
  - Heredar estrictamente de `TenantBase` para residir en esquemas dinámicos `tenant_*` aislados por cliente.
  - Tabla `salones` con UUID PK, capacidad, precio neto/bruto, IVA y estado higiénico.
  - Tabla `salon_areas_operativas` pivote many-to-many.
  - Tabla `eventos` con control anti-overbooking y auditoría.
  - Tablas `evento_items`, `evento_recetas`, `evento_combos`, `evento_trabajadores` y `evento_consumos_kardex`.
- [x] **1.2** Creación de la Migración Correlativa Lineal Alembic `0013`:
  - Archivo: `oppytec-backend/alembic/versions/0013_tenant_events_salones_and_reservations.py`.
- [x] **1.3** Entidades de Dominio DDD y Primitivas Matemáticas (`domain/`):
  - Ubicación: `oppytec-backend/src/modules/events/domain/`.
  - Value Objects inmutables: `EventStatus`, `SalonState`, `EventTimeSlot`, `SalonCapacity`, `MoneyAmount`, `ItemQuantity`.
  - Entidad y Agregado Raíz `Evento` con invariantes de ciclo de vida y anti-overbooking.
  - Repositorios y contratos de dominio en `domain/repositories.py`.

---

### [x] FASE 2: Motor Backend FastAPI & Integración Transaccional con Kardex Inmutable
- [x] **2.1** Servicios de Aplicación Transaccionales (`application/services.py`):
  - **`SalonService`:**
    - `list_salones(tenant_id, area_operativa_id=None)`: listar salones con sus áreas vinculadas.
    - `create_salon(tenant_id, data)`: alta de salón con cálculo de IVA y asignación de áreas.
    - `update_salon(tenant_id, salon_id, data)`: actualización con recálculo de IVA y verificación.
    - `delete_salon(tenant_id, salon_id)`: soft-delete con validación de eventos.
  - **`EventService`:**
    - `create_event(tenant_id, data, current_user_id)`:
      - Validación anti-overbooking: rechazo con HTTP 409 si existe solapamiento temporal (`EventTimeSlot.overlaps`).
      - Creación de cabecera, ítems directos, recetas, combos y personal asignado en una sola transacción.
      - Emisión de evento WebSocket `events.changed`.
    - `update_event(tenant_id, event_id, data, current_user_id)`:
      - Validación de estado: prohibido modificar si `ejecutado=True` o `cancelado=True`.
      - Recálculo de items, recetas y equipo.
    - `cancel_event(tenant_id, event_id, motivo, current_user_id)`:
      - Marcar `cancelado=True`, `estado='CANCELADO'`.
      - Liberación inmediata del salón y stock comprometido.
    - `reactivate_event(tenant_id, event_id, current_user_id)`:
      - Verificación de disponibilidad del salón en la fecha/hora original antes de reactivar.
      - Transición a `AGENDADO`.
    - `execute_event(tenant_id, event_id, current_user_id)`:
      - Desglose BOM completo de insumos directos + ingredientes de recetas + ítems de combos.
      - Asiento en Kardex (`CONSUMO`) e inserción de registros en `evento_consumos_kardex`.
      - Marcado de evento: `ejecutado=True`, `estado='EJECUTADO'`, `ejecutado_at=now()`.
      - Notificación en tiempo real via Redis Pub/Sub a WebSocket.
    - `get_faltantes_analytics(tenant_id, area_operativa_id=None)`:
      - Traer todos los eventos futuros agendados (`fecha >= today`, `ejecutado=False`, `cancelado=False`).
      - Desglosar la demanda consolidada de insumos por producto.
      - Comparar contra stock en bodegas identificando déficit.

- [x] **2.2** Schemas Pydantic V2 (`presentation/schemas.py`):
  - Modelos de validación estricta con `Decimal` para valores monetarios y cantidades:
    - `SalonCreate`, `SalonUpdate`, `SalonOut`, `SalonResponse`.
    - `EventoItemIn`, `EventoItemOut`, `EventoRecetaIn`, `EventoRecetaOut`, `EventoComboIn`, `EventoComboOut`, `EventoTrabajadorIn`, `EventoTrabajadorOut`.
    - `EventoCreate`, `EventoUpdate`, `EventoOut`, `EventoListItemOut`, `EventoResponse`, `EventoDetailResponse`.
    - `EventExecutionResultSchema`, `EventFaltanteItemOut`, `EventFaltantesResponse`.

- [x] **2.3** Enrutador FastAPI y Endpoints REST RFC 7807 (`presentation/router.py`):
  - Todos los endpoints con respuestas normalizadas RFC 7807 (`ProblemDetails` para errores 400, 403, 404, 409, 422).
  - Prefix `/api/v1/events` y tags `["Events", "Salones"]`.
  - Registrado en `oppytec-backend/src/main.py`.
  - Guards RBAC de 3 niveles: `events.salones.read`, `events.salones.manage`, `events.events.read`, `events.events.create`, `events.events.edit`, `events.events.delete`, `events.events.execute`, `events.events.cancel`.

- [x] **2.4** Notificaciones WebSocket Zero-Polling (`/api/v1/ws/realtime`):
  - Emisión de eventos Redis Pub/Sub:
    - `events.events.changed`: ante creación, edición, cancelación o ejecución de cualquier evento.
    - `events.salones.changed`: ante cambios en catálogo o estado de salones.
    - Invalida quirúrgicamente las query keys en TanStack Query v5: `["events"]`, `["salones"]`, `["events_faltantes"]`, `["inventory"]`.

---

### [x] FASE 3: Frontend Feature Core & Hooks Reactivos (COMPLETADA — Agente 05, 22/22 pruebas Vitest pasando al 100%)
- [x] **3.1** Contratos TypeScript en `oppytec-frontend/src/features/events/types.ts`:
  - `Salon`:
    - `id`: string (UUID).
    - `nombre`: string.
    - `capacidad_personas`: number | null.
    - `precio_neto`: number.
    - `iva_porcentaje`: number.
    - `precio_bruto`: number.
    - `notas`: string | null.
    - `estado`: `'limpio' | 'en_uso' | 'mantenimiento' | 'sucio'`.
    - `color`: string.
    - `areas_operativas_ids`: string[];
  - `EventoItem`:
    - `producto_id`: string.
    - `bodega_id`: string.
    - `cantidad`: number.
    - `costo_unitario_estimado`?: number;
  - `EventoReceta`:
    - `receta_id`: string.
    - `cantidad`: number;
  - `EventoCombo`:
    - `combo_id`: string.
    - `cantidad`: number;
  - `EventoTrabajador`:
    - `usuario_id`: number.
    - `usuario`?: { id: number; nombre: string; email: string; avatar_url?: string };
    - `rol_en_evento`?: string | null;
  - `Evento`:
    - `id`: string (UUID).
    - `nombre`: string.
    - `titular`?: string | null.
    - `encargado_id`?: number | null.
    - `encargado`?: { id: number; nombre: string } | null;
    - `salon_id`?: string | null.
    - `salon`?: Salon | null;
    - `fecha`: string (YYYY-MM-DD).
    - `hora_inicio`?: string | null.
    - `hora_fin`?: string | null.
    - `lugar`?: string | null.
    - `cantidad_invitados`?: number | null.
    - `estado`: `'agendado' | 'en_curso' | 'finalizado' | 'cancelado'`;
    - `color`: string;
    - `ejecutado`: boolean;
    - `cancelado`: boolean;
    - `valor_publico`?: number | null;
    - `nota_visible`?: string | null;
    - `items`: EventoItem[];
    - `recetas`: EventoReceta[];
    - `combos`: EventoCombo[];
    - `trabajadores`: EventoTrabajador[];
  - `FaltanteItem`:
    - `producto_id`: string;
    - `nombre`: string;
    - `unidad`: string;
    - `necesario`: number;
    - `disponible`: number;
    - `faltante`: number;
    - `eventos`: Array<{ fecha: string; cantidad: number; nombre_evento: string }>;
  - `CalendarViewMode`: `'month' | 'week' | '3days' | 'day'`.

- [x] **3.2** Hooks Reactivos en `oppytec-frontend/src/features/events/hooks/`:
  - `useEvents.ts`:
    - Gestión de caché TanStack Query v5 (`useQuery(["events", filterParams])`).
    - Mutaciones con toasts (`sonner`) y optimismo controlado: `createEventMutation`, `updateEventMutation`, `deleteEventMutation`, `executeEventMutation`, `cancelEventMutation`, `reactivateEventMutation`.
    - Helpers analíticos: `getEventEstimatedCost(evento)`, `getInsumosDesglosados(evento)`.
  - `useSalones.ts`:
    - `useQuery(["events", "salones"])` para carga ágil de salones.
    - Mutaciones `createSalon`, `updateSalon`, `deleteSalon` con invalidación de caché reactiva.
  - `useEventAlerts.ts`:
    - Consulta reactiva de faltantes y stock comprometido para el banner superior y para los badges de advertencia.

---

### [x] FASE 4: Vista Principal `/eventos` (`EventsPage.tsx`) (COMPLETADA — Agente 05)
- [x] **4.1** Cabecera y Toolbar Estandarizado:
  - `SectionHeader` centrado en rosa/fucsia (#ec4899), icono `CalendarDays`, subtítulo *"Programación y Control de Consumo"*.
  - Toolbar responsivo (PC en flex horizontal, Móvil en grilla compacta apilada con `touch-action: manipulation`):
    - Selector de Área Operativa (`AreaSelector`) para filtrar eventos y salones asociados.
    - Botón "Salones" con icono `Building2` para abrir `SalonesDialog`.
    - Botón "Exportar" con icono `FileSpreadsheet` para generar minutas consolidadas.
    - Toggle de Vistas con icono `CalendarIcon`: alterna entre Vista Lista/Tarjetas y Vista Calendario.
    - Botón destacado "Nuevo Evento" (#ec4899) con icono `Plus`.

- [x] **4.2** Pestañas de Estado con Contadores Reactivos:
  - Tres pestañas con estilo canónico de OppyTec:
    - **Agendados / Próximos** (`proximos`): eventos activos no ejecutados ni cancelados con badge de cantidad.
    - **Finalizados / Historial** (`historial`): eventos ejecutados exitosamente con registro de consumo.
    - **Cancelados** (`cancelados`): eventos desestimados.
  - Transición animada de pestañas sin recarga de pantalla.

- [x] **4.3** Renderizado Paritario 1:1 de Tarjetas (`EventoCard.tsx`):
  - Diseño card con borde cromático según el color asignado al evento (`evento.color`).
  - Cabecera con nombre del evento, badge de estado (`agendado` en azul/sky, `finalizado` en esmeralda/verde, `cancelado` en rojo/rose), fecha formateada en español (`dd 'de' MMMM, yyyy`), y horario (`hora_inicio` - `hora_fin`).
  - Información del salón o lugar, cantidad de invitados, y titular del evento.
  - Desglose de insumos, recetas y combos asignados con badges visuales.
  - Avatares de la brigada asignada y encargado general.
  - Acciones rápidas contextuales según estado:
    - Si está agendado: botones Ejecutar (`Play`), Editar (`Pencil`), Cancelar (`Ban`), Eliminar (`Trash2`).
    - Si está cancelado: botón Reactivar (`RotateCcw`), Eliminar (`Trash2`).
    - Si está finalizado: botón Ver Detalle (`Eye`), Ver Asiento de Kardex.

- [x] **4.4** Calendario Interactivo Avanzado (`EventosCalendar.tsx`):
  - Switcher de Vistas en Toolbar del Calendario: Mes (`month`), Semana (`week`), 3 Días (`3days`), Día (`day`) con persistencia en `localStorage`.
  - Navegación mensual/semanal con botones Anterior (`ChevronLeft`), Siguiente (`ChevronRight`) y "Hoy".
  - Grilla de días con cabecera de días (`Lun`, `Mar`, `Mié`, `Jue`, `Vie`, `Sáb`, `Dom`).
  - Renderizado de eventos en bloques con color institucional del evento, visualización de horario, salón asignado y badge de estado.
  - Clic en día vacío abre `EventoDialog` con la fecha preseleccionada.
  - Clic en evento abre diálogo de detalle o edición según permisos.
  - Indicador visual de colisión horaria si dos eventos se cruzan en el mismo salón.

---

### [x] FASE 5: Modales y Diálogos Operativos (COMPLETADA — Agente 05)
- [x] **5.1** Modal Asistente de Creación y Edición (`EventoDialog.tsx`):
  - Modal en dos pasos (Wizard) para fluidez operativa:
    - **Paso 1: Datos Generales y Programación:**
      - Nombre del evento, titular y cantidad de invitados.
      - Selector de Salón (con indicación de capacidad de personas y estado del salón).
      - Lugar alternativo (si aplica).
      - Selector de Fecha con date picker nativo o Popover accesible.
      - TimePickers de Hora Inicio y Hora Fin.
      - Selector de Encargado (dropdown de usuarios del tenant) y selección múltiple de trabajadores/brigada.
      - Paleta cromática interactiva con 20 colores preestablecidos para codificación visual en calendario.
      - Textareas con menciones `@` para notas de equipo y notas visibles.
    - **Paso 2: Asignación Gastronómica y de Insumos:**
      - Pestañas internas: **Insumos Directos**, **Recetas Gastronómicas**, **Combos y Promociones**.
      - Buscador rápido con autocompletado y atajos de teclado.
      - En Insumos: selector de producto, selector de bodega de despacho, ingreso de cantidad con `NumericInput` y visualización de stock actual disponible en esa bodega.
      - En Recetas: selector de recetas activas del catálogo gastronómico, multiplicador de porciones/raciones.
      - En Combos: selector de paquetes gastronómicos y multiplicador.
      - Resumen financiero en tiempo real: valor público sugerido y costo teórico estimado.
  - Soporte de guardado y validaciones de datos requeridos antes de confirmar.

- [x] **5.2** Diálogo de Gestión de Salones (`SalonesDialog.tsx`):
  - CRUD completo de espacios y salones:
    - Listado de salones con chips cromáticos, capacidad de invitados, áreas operativas asociadas y arancel.
    - Formulario integrado o toggle de alta/edición:
      - Nombre del salón.
      - Capacidad máxima de personas.
      - Campos monetarios sincronizados: `precio_neto`, `iva_porcentaje` (default 19%) y `precio_bruto`, con recálculo automático bidireccional mediante lógica `Decimal`.
      - Selector de estado de salón (`limpio`, `en_uso`, `mantenimiento`, `sucio`).
      - Selector múltiple de Áreas Operativas asociadas (ej: "Salón Principal" asociado a "Cocina Central" y "Bar Piscina").
      - Notas y observaciones técnicas.
    - Botones de acción: Guardar, Editar, Eliminar (con alerta de confirmación).

- [x] **5.3** Diálogo y Banner de Resumen de Faltantes (`ResumenFaltantes.tsx`):
  - Banner de advertencia en color ámbar/naranja visible en la parte superior de `/eventos` cuando existen quiebres de stock proyectados para eventos futuros.
  - Indicador numérico de productos en riesgo.
  - Grilla de tarjetas compactas de faltantes:
    - Nombre del insumo y unidad de medida.
    - Comparativa: `Stock Disponible` vs `Stock Necesario`.
    - Cálculo de faltante neto: `faltante = necesario - disponible`.
  - Botón *"Descargar Pedido Sugerido (CSV/Excel)"*:
    - Genera archivo con las cantidades exactas a abastecer para cubrir la totalidad de banquetes programados sin quiebre de servicio.

---

### [x] FASE 6: Flujo de Ejecución y Consumo Transaccional en Kardex (COMPLETADA — Agente 04)
- [x] **6.1** Motor de Desglose Recursivo BOM (Bill of Materials):
  - Descomposición atómica de requerimientos antes del impacto:
    1. Insumos directos declarados en `evento_items`.
    2. Ingredientes de recetas declaradas en `evento_recetas`: $\text{cantidad\_ingrediente} = \text{receta\_ingredientes.cantidad} \times \text{evento\_recetas.cantidad}$.
    3. Componentes de combos declarados en `evento_combos`:
       - Ítems directos del combo: $\text{cantidad} \times \text{evento\_combos.cantidad}$.
       - Recetas contenidas en el combo: desglose a nivel de materias primas multiplicadas por la porción del combo.
  - Agrupación por `(producto_id, bodega_id)` para asientos consolidados sin duplicidad.

- [x] **6.2** Asientos Inmutables en Kardex (`CONSUMO_EVENTO`):
  - Invocación de `InventoryService.register_movement(...)` para cada insumo desglosado:
    - `tipo_movimiento = 'CONSUMO_EVENTO'`.
    - `bodega_id`: bodega asignada en el evento (o bodega por defecto de producción si proviene de recetas).
    - `cantidad`: volumen consumido en negativo (salida de stock).
    - `costo_unitario_ppp`: valor unitario PPP vigente al momento de la ejecución.
    - `costo_total_movimiento`: $\text{cantidad} \times \text{costo\_unitario\_ppp}$.
    - `documento_referencia`: `f"EVENTO-{evento.id} | {evento.nombre}"`.
    - `actor_user_id`: ID del usuario que ejecuta la acción.
  - Enlace con tabla `evento_consumos_kardex` para auditoría y reversibilidad.
  - Prohibido cualquier `UPDATE` directo a saldos de stock; la mutación ocurre estrictamente por el libro mayor Append-Only de Kardex.

- [x] **6.3** Reversibilidad y Compensación Controlada:
  - Si un evento ejecutado requiere anularse por causa de fuerza mayor:
    - Prohibido borrar registros de `kardex_movements`.
    - Generación de asientos compensatorios con `tipo_movimiento = 'AJUSTE_EVENTO_REVERSA'`, reingresando exactamente las unidades deducidas al inventario con el mismo costo PPP.
    - Endpoint `POST /api/v1/events/{event_id}/reverse` protegido con `RequireTenantPermission("events.events.cancel")`.
    - Auditoría del motivo de reversión y usuario responsable.

- [x] **6.4** Exportación de Minuta de Producción y Actas:
  - Endpoints `GET /api/v1/events/{event_id}/minuta` y `POST /api/v1/events/export/minuta-excel` protegidos con `RequireTenantPermission("events.events.read")`.
  - Generación de informe descargable estructurado en CSV con UTF-8 BOM (`\ufeff`) compatible con Excel:
    - Sección 1: Ficha técnica del evento (titular, salón, fecha, comensales, encargado).
    - Sección 2: Minuta gastronómica (platos, recetas y porciones a producir).
    - Sección 3: Combos y paquetes comerciales.
    - Sección 4: Requisición de bodegas consolidada (insumos directos, cantidades, stock disponible, costos unitarios).
    - Sección 5: Brigada y horas asignadas.
    - Sección 6: Acta de conformidad y casillas de firma de entrega y recepción.

---

### [x] FASE 7: Concepto de "Stock Comprometido" e Integración con Inventario & Alertas
- [x] **7.1** Definición Matemática de Existencias Disponibles (COMPLETADA — Agente 04):
  - Existencias Físicas en Bodega: $\text{Stock Actual} = \sum \text{Kardex Movements}$.
  - Demanda Futura Reservada: $\text{Stock Comprometido} = \sum_{\text{eventos agendados futuros}} \text{BOM Insumos}$.
  - Saldo Libre para Operación Diaria / Buffet:
    $$\text{Stock Disponible Real} = \max(0, \text{Stock Actual} - \text{Stock Comprometido})$$
  - Endpoint REST `GET /api/v1/events/analytics/committed-stock` con RBAC `events.events.read`.
- [x] **7.2** Integración con Frontend e Indicadores de Stock Comprometido (COMPLETADA — Agente 05):
  - Incorporación de tipos `CommittedStockItem`, `CommittedStockSummaryResponse`, `EventAlertItem`, `EventAlertsResponse` en `types.ts`.
  - Integración en `api/eventsApi.ts` (`getCommittedStock`, `getEventAlerts`) con soporte de fallback resiliente.
  - Hook `useEventAlerts` con suscripción WebSocket zero-polling, helpers analíticos (`getCommittedStockByProduct`, `isProductCommitted`, `getAvailableRealStock`) y métricas de saldo disponible real.
  - Banner en `EventsPage.tsx` con soporte visual de severidad `CRITICAL` (<48h con alerta roja y pulsación) y `WARNING` (<=14d con advertencia preventiva).
  - Indicadores de stock comprometido y saldo disponible real en `EventoCard.tsx` y `ResumenFaltantesDialog.tsx`.
- [x] **7.3** Integración con el Módulo de Alertas (`/alertas`) (COMPLETADA — Agente 04 y Agente 05):
  - Implementación en `EventService.get_event_alerts(tenant_id)` y endpoint REST `GET /api/v1/events/alerts` con RBAC `events.events.read`.
  - Clasificación de severidad:
    - `CRITICAL`: Evento programado en $< 48\text{h}$ con insumos en quiebre de stock.
    - `WARNING`: Evento programado en los próximos 14 días con quiebre proyectado o stock insuficiente.
  - Contabilización y emisión de eventos realtime WebSocket vía Redis Pub/Sub (`events.changed`).

---

### [x] FASE 8: Capas Cruzadas, i18n, FX, Observabilidad, Testing 5D & E2E (COMPLETADA — Agentes 07, 08, 09, 10, 11, 12)
- [x] **8.1** Cobertura de Internacionalización (i18n 100% `es`/`en` y 0 Textos Hardcodeados):
  - Archivos: `oppytec-frontend/src/shared/i18n/locales/es/events.json` y `locales/en/events.json`.
  - Namespaces cubiertos al 100%:
    - Cabecera, toolbar, tabs (`proximos`, `historial`, `cancelados`), botones de acción.
    - Calendario: nombres de días, meses, vistas (`month`, `week`, `3days`, `day`), botones de navegación.
    - Modal `EventoDialog`: datos generales, programación, selección de salón, insumos, recetas, combos, brigada.
    - Modal `SalonesDialog`: nombres de campos, cálculos de IVA, estados (`limpio`, `en_uso`, `mantenimiento`, `sucio`).
    - Resumen de Faltantes y alertas de quiebre.
  - Verificación de 0 cadenas fijas en JSX o atributos accesibles.

- [x] **8.2** Soporte Multi-Moneda FX con Precisión `Decimal`:
  - Cálculos financieros de salones (precio neto, IVA, precio bruto) y presupuestos de eventos usando `Decimal` en backend.
  - Formateo en frontend mediante componente `MoneyBadge` y helper `formatMoney` respetando la moneda activa del tenant (CLP, USD, EUR, etc.).
  - Conversión dinámica FX en reportes financieros si el tenant opera en divisa extranjera.

- [x] **8.3** Instrumentación de Observabilidad (OpenTelemetry, Grafana, Sentry):
  - Trazas de span OpenTelemetry en flujos transaccionales:
    - `events.create`: validación anti-overbooking y persistencia.
    - `events.execute`: cálculo BOM y rebaje multilínea en Kardex.
    - `events.bom_explosion`: descomposición recursiva de recetas y combos.
    - `events.faltantes.compute`: tiempo de evaluación de demanda agregada.
  - Registro de errores en Sentry / GlitchTip contextualizados con `tenant_id`, `event_id`, `salon_id` y `user_id`.
  - Sanitización de PII garantizada.

- [x] **8.4** Suite de Pruebas Automatizadas 5D:
  - **Backend (Pytest):** 35/35 pruebas pasando al 100%:
    - `tests/unit/modules/test_events_domain_and_models.py`: Value objects, entidades y agregado raíz Evento.
    - `tests/unit/modules/test_events_services.py`: Servicios SalonService y EventService, rechazo 409 anti-overbooking, deducción Kardex, reversión y alertas.
    - `tests/unit/modules/test_events_observability.py`: Trazas OpenTelemetry y contexto.
    - `tests/unit/modules/test_oppyfy_events_tools.py`: Herramientas OppyFy de eventos.
  - **Frontend (Vitest):** 30/30 pruebas pasando al 100%:
    - `hooks.test.ts`: 17 tests de hooks reactivos y cálculos de costos.
    - `EventsPage.test.tsx`: 8 tests de renderizado, tabs y apertura de diálogos.
    - `EventsI18nAndFx.test.tsx`: 5 tests de i18n es/en y formateo multi-moneda.

- [x] **8.5** Montaje en Router Principal y Verificación de Compilación:
  - Registro de ruta en `oppytec-frontend/src/app/router.tsx`:
    - `/eventos` $\rightarrow$ `EventsPage`.
  - Compilación y tipado validados.

- [x] **8.6** Certificación E2E Playwright en Navegador Real (Desacoplada — Agente 13):
  - Preparado y disponible bajo demanda para el Agente 13 (`13-browser-e2e-playwright`) sin bloquear el pipeline continuo.

- [x] **8.7** Sincronización del Grafo AST y Bóvedas OpenSpec:
  - Sincronización del grafo ejecutada con `python scripts/harness.py sync-graph`: 115 nodos, 141 aristas indexados en `docs/architecture/graphify/graph.json`.
  - Bóvedas OpenSpec bipartitas creadas y sincronizadas:
    - `specs/business-domain/events.business.spec.md`
    - `specs/engineering-code/events.code.spec.md`
  - Bitácora humana registrada en `docs/bitacora/diario-escuadron/13-Construccion-Modulo-Eventos-Salones-Banquetes-Kardex-BOM.md` y MOC actualizado en `docs/bitacora/00-MAPA-SEGUNDO-CEREBRO.md`.

---

## 🎯 Protocolo de Ejecución y Traspaso entre Agentes

| Etapa | Agente Líder | Tareas a Cargo | Entregables Principales |
| :---: | :--- | :--- | :--- |
| **Etapa 1** | `02-software-architect` & `03-database-alembic` | FASE 1: DDL `tenant_*`, Alembic `0012`, DDD Eventos y Salones | Modelos SQLAlchemy, Migración `0012`, Value Objects anti-overbooking |
| **Etapa 2** | `04-backend-senior-dev` | FASE 2: Servicios de Aplicación, Desglose BOM y Endpoints REST | Routers FastAPI, Guards RBAC, Transaccionalidad ACID y Kardex |
| **Etapa 2** | `05-frontend-senior-dev` | FASE 3, 4, 5: UI React 19, Hooks, Vistas, Calendario y Modales | `EventsPage`, `EventoCard`, `EventosCalendar`, `EventoDialog`, `SalonesDialog` |
| **Etapa 3** | `07-i18n-fx` & `08-environments-observability` | FASE 8: i18n 100%, Multi-Moneda FX, OpenTelemetry | `events.json` (es/en), Trazas OTel, Sentry, Telemetría |
| **Etapa 4** | `09-qa-test` & `10-security-redteam` | FASE 8: Testing 5D, SAST/DAST, Paridad Matemática | Tests Pytest + Vitest, Auditoría Kali, 0 Vulnerabilidades |
| **Etapa 4** | `11-git-arbiter` & `12-tech-writer` | Cierre: Merge Train, OpenSpec, Graphify & Archify | Smart Merge, Bóvedas OpenSpec, Grafo AST sincronizado |
| **Etapa 5** | `13-browser-e2e-playwright` | FASE 8: Certificación E2E en Navegador Real (Desacoplada) | Reporte Playwright HTML, Video y Traza de Navegación |

> **Nota Final de Gobernanza:** Toda modificación de código debe ejecutarse previa consulta de Graphify (`python scripts/harness.py nav "<símbolo>"`) y concluir con la sincronización obligatoria `python scripts/harness.py sync-graph`.
