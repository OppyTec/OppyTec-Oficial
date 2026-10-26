# 📋 PLAN MAESTRO DE CONTROL Y EJECUCIÓN: MÓDULO DE CONSUMO, MANOS LIBRES Y BUFFET INTELIGENTE (`/registro-de-consumo`, `/consumo/manos-libres`, `/consumo/buffet`)

> **Regla de Gobernanza:** Este documento es el tablero de control de ejecución estricto del Módulo de Consumo de OppyTec v2.0.  
> Cada paso debe ser **100% corroborado y aprobado** antes de pasar al siguiente.  
> **Solo cuando se finalicen todos los pasos**, este documento podrá ser archivado o eliminado, no antes.  
> **Fuentes de Verdad Históricas (100% Solo Lectura):**  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Consumo/` (Terminal de Registro de Consumo, Catálogo, Carrito flotante, Plantillas, Lotes y Contingencia)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Consumo/ManosLibresPage.tsx` (Comandos por voz en cocina/bar, operarios y bitácora)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Consumo/Buffet/` (Sesiones de buffet, estaciones, escáner con visión y costeo por Pax)  
> - `OppyTec-Legacy/OppyTec_Backend/src/inventory/router.py` y `src/inventory/services/stock_service.py` (Procesamiento batch de consumo FIFO)  
> - `OppyTec-Legacy/OppyTec_Backend/src/operations/routers/voice_kitchen_router.py` (Motor de comandos y audio de cocina por voz)  
> - `OppyTec-Legacy/OppyTec_Backend/src/operations/buffet_router.py` y `src/operations/buffet_service.py` (Sesiones y conciliación de buffet)  
> - `OppyTec-Legacy/OppyTec_Backend/openspec/specs/business/operations/operaciones-buffet-eventos-combos.md`  
> **Destinos de Construcción en OppyTec v2.0:**  
> - Frontend: `oppytec-frontend/src/features/consumo/` (`registro/`, `manos-libres/`, `buffet/`, `hooks/`, `types.ts`)  
> - Backend: `oppytec-backend/src/modules/operations/` y `oppytec-backend/src/modules/inventory/` (DDD: Domain, Application, Infrastructure, Presentation)  

---

## 📊 Estado General del Proyecto

- [x] **Fase 1:** Arquitectura de Dominio DDD, Esquemas PostgreSQL `tenant_*` y Migración Alembic 0005 — **COMPLETADA**
- [x] **Fase 2:** Motor Backend FastAPI & Kardex Inmutable por Eventos (endpoints REST RFC 7807, transaccionalidad ACID, RBAC 3 niveles `consumption.*`, cero updates directos a stock, bloqueo anti-deadlock) — **COMPLETADA**
- [x] **Fase 3:** Frontend Feature Core & Hooks Reactivos (`types.ts`, `useConsumo.ts`, `useManosLibres.ts`, `useBuffet.ts`, TanStack Query v5 + WebSockets realtime) — **COMPLETADA**
- [x] **Fase 4:** Vista 1 — Registro de Consumo (`/registro-de-consumo`): réplica 1:1 de `Consumo`, `SectionHeader` centrado (#eab308), Toolbar unificado (Desktop/Mobile), switcher de vistas (Productos/Recetas/Combos), toggle categorías, gestor de plantillas (públicas/privadas) y **Paginador `TablePagination` integrado al catálogo** — **COMPLETADA**
- [x] **Fase 5:** Modales Operativos y Carrito de Consumo: `ConsumoCart`, `BotonesFlotantes`, `ConsumoOptionsDialog`, `ConsumoTemplateModal`, `LocateStockDialog`, `ContingencyModal` y `ConsumoLog` — **COMPLETADA**
- [x] **Fase 6:** Vista 2 — Manos Libres (`/consumo/manos-libres`): `SectionHeader` centrado (#f97316), Estaciones de cocina/bar, reconocimiento por voz de operarios, feed de pedidos por voz y síntesis TTS — **COMPLETADA**
- [x] **Fase 7:** Vista 3 — Buffet Inteligente (`/consumo/buffet`): `SectionHeader` centrado (#06b6d4), Sesiones de buffet, estaciones de montaje, escáner con cámara y visión computacional (`StationCameraScanner`), tabla `BuffetItemsTable`, cálculo de comensales/Pax y liquidación transaccional — **COMPLETADA**
- [x] **Fase 8:** Capas Cruzadas, i18n 100% `es`/`en` (`operations.json`), Multi-Moneda FX (`Decimal`), Observabilidad OpenTelemetry, Testing 5D (Vitest + Pytest) y Certificación de Calidad — **COMPLETADA (100% FINALIZADO)**

---

## 🔍 Detalle y Criterios de Aceptación por Fase

---

### [x] FASE 1: Arquitectura de Dominio DDD, Esquemas PostgreSQL tenant_* y Migración Alembic 0005 — ✅ 100% COMPLETADA
- [x] **1.1** Modelado de Persistencia Multi-Tenant en `oppytec-backend/src/modules/operations/infrastructure/models.py`:
  - Heredar estrictamente de `TenantBase` para residir en esquemas dinámicos `tenant_*` aislados por cliente.
  - Tabla `consumption_records` (`registros_consumo`):
    - Cabecera de transacción de consumo directo.
    - Campos: `id` (BigInteger PK), `codigo_folio` (`String(32)` unique), `area_operativa_id` (FK `areas_operativas.id`), `bodega_id` (FK `bodegas.id`), `usuario_id` (`Integer` FK `public.users.id`), `tipo_origen` (`String(32)` enum: `MANUAL_TERMINAL`, `MANOS_LIBRES_VOZ`, `BUFFET_LIQUIDACION`, `VENTA_POS`), `notas` (`Text` nullable), `AuditTimestampsMixin`, `SoftDeleteMixin`.
  - Tabla `consumption_record_items` (`registro_consumo_items`):
    - Detalle de ítems descontados por transacción.
    - Campos: `id` (BigInteger PK), `consumption_record_id` (FK `consumption_records.id` ON DELETE CASCADE), `tipo_item` (`String(20)` enum: `PRODUCTO`, `RECETA`, `COMBO`), `item_id` (`UUID` o FK correspondiente), `cantidad` (`Numeric(12, 4)`), `unidad_medida` (`String(20)`), `costo_unitario_ppp` (`Numeric(14, 2)`), `costo_total` (`Numeric(14, 2)`), `lote_codigo` (`String(64)` nullable), `fecha_vencimiento_lote` (`Date` nullable), `kardex_movement_id` (FK `kardex_movements.id` para trazabilidad biyectiva), `opciones_seleccionadas` (`JSONB` nullable).
  - Tabla `consumption_templates` (`plantillas_consumo`):
    - Plantillas de catálogo personalizadas para turnos o cuadrillas.
    - Campos: `id` (BigInteger PK), `slug` (`String(64)` unique), `nombre` (`String(128)`), `descripcion` (`Text` nullable), `usuario_creador_id` (`Integer`), `is_public` (`Boolean` default False), `columnas_count` (`SmallInteger` default 8), `sort_mode` (`String(32)` default `alpha_asc`), `product_ids` (`JSONB` lista ordenada de IDs), `AuditTimestampsMixin`.
  - Tablas de Buffet Inteligente:
    - `buffet_sessions`: `id` (UUID PK), `area_operativa_id` (FK `areas_operativas.id`), `bodega_id` (FK `bodegas.id`), `usuario_creador_id` (`Integer`), `tipo_servicio` (`String(64)`: `DESAYUNO`, `ALMUERZO`, `BRUNCH`, `EVENTO`), `estado` (`String(32)`: `EN_PREPARACION`, `ACTIVO`, `CERRADO`, `CONCILIADO`), `pax_comensales` (`Integer` default 0), `costo_total_montaje` (`Numeric(14, 2)`), `valor_sobrante_reutilizable` (`Numeric(14, 2)`), `costo_neto_pax` (`Numeric(14, 2)`), `AuditTimestampsMixin`.
    - `buffet_stations`: `id` (BigInteger PK), `buffet_session_id` (FK `buffet_sessions.id` ON DELETE CASCADE), `nombre_estacion` (`String(64)`), `orden` (`Integer`).
    - `buffet_session_items`: `id` (BigInteger PK), `station_id` (FK `buffet_stations.id`), `tipo_item` (`PRODUCTO` o `RECETA`), `item_id` (`UUID`), `cantidad_montada` (`Numeric(12, 4)`), `cantidad_sobrante` (`Numeric(12, 4)`), `cantidad_merma` (`Numeric(12, 4)`), `cantidad_neta_consumida` (`Numeric(12, 4)`), `costo_unitario_ppp` (`Numeric(14, 2)`), `costo_total` (`Numeric(14, 2)`).
    - `buffet_templates`: `id` (UUID PK), `nombre` (`String(128)`), `descripcion` (`Text` nullable), `estaciones_json` (`JSONB`), `is_system` (`Boolean` default False), `is_public` (`Boolean` default True).
  - Tablas de Cocina por Voz / Manos Libres:
    - `voice_stations`: `id` (BigInteger PK), `area_operativa_id` (FK `areas_operativas.id`), `nombre_estacion` (`String(64)`), `voice_command` (`String(64)` clave fonética), `usuario_asignado_id` (`Integer` nullable).
    - `voice_order_logs`: `id` (BigInteger PK), `station_id` (FK `voice_stations.id`), `texto_transcrito` (`Text`), `accion_detectada` (`String(32)`: `CONSUMO`, `MERMA`), `confianza_ia` (`Numeric(5, 4)`), `items_interpretados_json` (`JSONB`), `estado` (`String(32)`: `PENDIENTE`, `CONFIRMADO`, `RECHAZADO`, `EJECUTADO`), `consumption_record_id` (FK `consumption_records.id` nullable), `AuditTimestampsMixin`.
- [x] **1.2** Creación de la Migración Correlativa Lineal Alembic `0005`:
  - Archivo: `oppytec-backend/alembic/versions/0005_tenant_consumption_buffet_and_voice_tables.py`.
  - `down_revision = "0004_tenant_inventory_kardex_and_physical_counts"`.
  - Mecanismo seguro de iteración sobre esquemas de tenants (`get_tenant_schemas()` o clonación sobre plantilla `tenant_base`).
  - Creación idempotente de tablas, índices compuestos y foreign keys.
- [x] **1.3** Definición de Entidades de Dominio DDD y Primitivas Matemáticas (`domain/`):
  - Ubicación: `oppytec-backend/src/modules/operations/domain/`.
  - Value Objects inmutables: `ConsumptionQuantity` (`Numeric(12, 4)` quantize), `PaxCount` (entero $\ge 0$), `BuffetPaxCost` (`Decimal(14, 2)`).
  - Axiomas de Consumo:
    1. Consumo por explosión de recetas: por cada unidad de receta consumida, se descuenta $\text{insumo\_qty} \times \text{cantidad} / \text{porciones}$.
    2. Consumo prioritario FEFO: se consumen lotes con fecha más cercana a caducar primero.
    3. Cero saldos negativos: toda salida sin stock o con stock insuficiente arroja `InsufficientStockError` atómico sin corromper el Kardex.
    4. Conciliación de Buffet: $\text{costo\_pax} = (\text{costo\_montaje} - \text{sobrante\_reutilizable}) / \text{pax}$.

---

### [x] FASE 2: Motor Backend FastAPI & Kardex Inmutable por Eventos — ✅ 100% COMPLETADA
- [x] **2.1** Servicios de Aplicación Transaccionales (`application/`):
  - `ConsumptionService`:
    - Procesamiento de lote de consumo mixto (`process_batch_consumption`): productos, recetas y combos.
    - Bloqueo pesimista en orden canónico de IDs (`canonical_lock_order`) para evitar deadlocks de base de datos en horas pico de servicio.
    - **Invariante Crítica:** El consumo de insumos inserta un asiento de tipo `CONSUMO` en `kardex_movements` por cada insumo y descuenta `stock_items`. Prohibido modificar stock sin asiento en Kardex.
    - Manejo de contingencia de lotes vencidos: rechazo estricto por defecto, permitiendo excepción autorizada bajo bitácora de auditoría o desvío a merma automática (`merma_expired_stock`).
  - `BuffetService`:
    - Apertura, actualización en vivo y liquidación de sesiones de buffet (`start_buffet_session`, `update_buffet_stage`, `finalize_buffet_session`).
    - Integración con cálculo de costos por comensal (`buffet_cost_per_pax`).
    - Generación automática de asientos de Kardex (`CONSUMO_BUFFET` y `MERMA_BUFFET`) al cerrar la sesión.
  - `VoiceKitchenService`:
    - Procesamiento fonético y parsing de intenciones gastronómicas (`parse_voice_intent`).
    - Ejecución de pedidos por voz confirmados hacia el `ConsumptionService`.
- [x] **2.2** Enrutador y Endpoints REST FastAPI (`presentation/router.py`):
  - Respuestas estandarizadas RFC 7807 (`ProblemDetails`).
  - Endpoints de Registro de Consumo:
    - `POST /api/v1/operations/consumption`: Registrar consumo batch mixto (productos, recetas y combos).
    - `GET /api/v1/operations/consumption/history`: Historial cronológico con filtros por rango de fecha, operario, bodega y área.
    - `GET /api/v1/operations/consumption/{id}`: Detalle de asiento de consumo y sus insumos.
    - `PUT /api/v1/operations/consumption/{id}`: Modificación justificada de consumo con ajuste diferencial en Kardex.
    - `DELETE /api/v1/operations/consumption/{id}`: Anulación/Reversión transaccional completa (`kardex_undo`).
    - `POST /api/v1/operations/consumption/merma-expired`: Mermar directamente lote vencido reportado desde la vista de consumo.
    - `GET /api/v1/operations/consumption/templates` y `POST /api/v1/operations/consumption/templates`: CRUD de plantillas de consumo públicas/privadas.
  - Endpoints de Manos Libres:
    - `GET /api/v1/operations/voice/stations`: Listar estaciones de cocina/bar y operarios asignados.
    - `POST /api/v1/operations/voice/orders`: Registrar orden por voz capturada por la terminal.
    - `POST /api/v1/operations/voice/orders/{id}/confirm`: Confirmar y procesar orden verbal.
    - `POST /api/v1/operations/voice/orders/{id}/reject`: Descartar orden verbal errónea.
  - Endpoints de Buffet Inteligente:
    - `POST /api/v1/operations/buffet/sessions/start`: Iniciar nueva sesión de buffet.
    - `GET /api/v1/operations/buffet/sessions`: Listar sesiones activas o históricas.
    - `GET /api/v1/operations/buffet/sessions/{id}`: Detalle completo de sesión, estaciones e ítems.
    - `PUT /api/v1/operations/buffet/sessions/{id}/items`: Actualizar conteos de montaje, reposición y sobrantes.
    - `POST /api/v1/operations/buffet/sessions/{id}/finalize`: Liquidar sesión de buffet, calcular Pax y generar impacto en Kardex.
    - `GET /api/v1/operations/buffet/templates` y `POST /api/v1/operations/buffet/templates`: CRUD de plantillas de estaciones buffet.
- [x] **2.3** Matriz de Seguridad y Guardias RBAC de 3 Niveles:
  - `consumption.register.read`: Consulta de catálogo de consumo e historial.
  - `consumption.register.create`: Registro de consumos manuales desde terminal.
  - `consumption.register.update`: Corrección de consumos registrados.
  - `consumption.register.delete`: Anulación y reversión transaccional en Kardex (restringido a Supervisor / Propietario).
  - `consumption.handsfree.use`: Uso de interfaz por voz en estaciones operativas.
  - `consumption.handsfree.manage`: Configuración de comandos fonéticos y operarios.
  - `consumption.buffet.manage`: Apertura, control de estaciones y recuento de buffet.
  - `consumption.buffet.approve`: Aprobación y liquidación contable de sesiones de buffet.
- [x] **2.4** Notificaciones en Tiempo Real (WebSocket Zero-Polling):
  - Emisión de eventos Redis Pub/Sub hacia `/api/v1/ws/realtime`:
    - `consumption.recorded`: Refresco instantáneo de existencias en terminales activas.
    - `voice.order_pending`: Notificación de orden de voz ingresada.
    - `buffet.session_changed`: Actualización en vivo de estaciones de buffet.

---

### [x] FASE 3: Frontend Feature Core & Hooks Reactivos — ✅ 100% COMPLETADA
- [x] **3.1** Contratos TypeScript de Dominio en `oppytec-frontend/src/features/consumo/types.ts`:
  - `ProductoConsumo`, `RecetaConsumo`, `ComboConsumo`, `CategoriaConsumo`.
  - `CartItem`: `id`, `cartItemId`, `name`, `type` (`producto` | `receta` | `combo`), `quantity`, `bodega_id`, `unit`, `price`, `selectedLot`, `ingredientLotOverrides`, `optionSelections`.
  - `ConsumoTemplate`: `id`, `name`, `description`, `isPublic`, `productIds`, `columnsCount`, `sortMode`, `customProductOrder`.
  - `ConsumptionRecord`: detalle de historial con insumos, costo total, usuario y estado.
  - `BuffetSession`, `BuffetStation`, `BuffetSessionItem`, `BuffetTemplate`.
  - `WorkerStation`, `VoiceOrderLog`.
- [x] **3.2** Hook Reactivo de Registro de Consumo `useConsumo.ts`:
  - Manejo integral de catálogo de productos, recetas y combos.
  - Filtrado contextual por Área Operativa y Bodegas de Consumo asignadas.
  - Carrito persistente en `localStorage` (`consumo_cart`) con sincronización multiventana mediante evento `cart-updated`.
  - Gestión de columnas de grilla persistentes (`consumo_cols_count`, de 5 a 10).
  - Verificación de contingencia: detección de lotes vencidos o sin stock antes de agregar al carrito.
  - Métodos CRUD para actualizar cantidad, asignar lotes específicos y customizar ingredientes con opciones.
- [x] **3.3** Hook Reactivo de Manos Libres `useManosLibres.ts`:
  - Conexión con motor de reconocimiento de voz (Web Speech API / Azure Speech Service con fallback resiliente).
  - Mapeo de operarios activos y comandos fonéticos.
  - Manejo de síntesis auditiva TTS (`voiceEngineService`).
- [x] **3.4** Hook Reactivo de Buffet Inteligente `useBuffet.ts`:
  - Carga y mutación de sesiones de buffet (`startSession`, `updateSessionItems`, `finalizeSession`).
  - Cálculo en vivo de cuadraturas por Pax y costos netos.
  - Sincronización con plantillas del sistema y personalizadas.

---

### [x] FASE 4: Vista 1 — Registro de Consumo (`/registro-de-consumo`) — ✅ 100% COMPLETADA
- [x] **4.1** Cabecera Canónica y Contexto Operativo:
  - Componente `SectionHeader` centrado:
    - Título: `"Registro de Consumo"`.
    - Subtítulo: `"Registra salidas de productos, consumo de personal y mermas en tiempo real"`.
    - Ícono: `UtensilsCrossed` de `lucide-react`.
    - Color identificador: `#eab308` (dorado/ámbar de consumo).
  - Selectores de contexto:
    - Selector de Área Operativa (`AreaSelector`).
    - Selector de Bodegas de Consumo (`BodegaSelector` limitado a bodegas del área).
- [x] **4.2** Toolbar Unificado (Desktop y Mobile):
  - Capa interna con `app-toolbar-inner-bar` idéntica a Legacy:
    - Switcher desplegable de Modo: **Productos** (amarillo), **Recetas** (morado) y **Combos** (azul marino `#1c4c96`).
    - Botón toggle de **Categorías** (`Tags`).
    - Botón destructivo **Merma** (`AlertTriangle`, rojo) que abre `MermaDialog`.
    - Menú de **Plantillas de Consumo** (`Bookmark`): selector de plantillas públicas (🌐) y privadas (⭐), opción "Ver Todo" y enlace a "+ Crear / Configurar...".
    - Botón **Historial de Consumo** (`History`, cian): abre drawer/modal con `ConsumoLog`.
  - Vista Mobile optimizada en tarjetas touch con acceso a todos los controles sin desbordamiento.
- [x] **4.3** Carrusel de Categorías & Buscador Predictivo:
  - Carrusel horizontal con selección múltiple de categorías animado con `framer-motion`.
  - Buscador reactivo en tiempo real con icono naranja `#f97316`, sombra suave y botón de limpieza rápida (**X**).
- [x] **4.4** Grilla Adaptativa de Catálogo (`ConsumoCatalog.tsx`):
  - Grilla de tarjetas cuadradas (`aspect-square`) con columnas dinámicas (de 5 a 10 columnas, configurable por plantilla o usuario).
  - Tarjetas interactivas con imagen WebP o ícono astronómico, nombre truncado a 2 líneas, stock disponible / porciones posibles, precio y semáforos de vigencia (crítico rojo pulsante, advertencia naranja, normal).
- [x] **4.5** **Integración del Paginador Canónico (`TablePagination`):**
  - **Requerimiento Fundamental:** Al pie de la grilla de catálogo, incorporar el componente [`TablePagination`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/shared/components/ui/TablePagination.tsx):
    - Selector de tamaño de página: 24, 48, 96 ítems (o 20, 40, 60 múltiplos ergonómicos de columnas).
    - Conteo exacto de ítems: *"Mostrando X a Y de Z productos/recetas/combos"*.
    - Botones de navegación: primera página, anterior, números con elipsis, siguiente y última página.
    - Preservar posición de scroll suave al cambiar de página.
    - Cero impacto negativo en el diseño visual de las tarjetas o en la velocidad de renderizado.

---

### [x] FASE 5: Modales Operativos y Carrito de Consumo — ✅ 100% COMPLETADA
- [x] **5.1** `ConsumoCart.tsx` (Carrito Lateral Flotante y Drawer Mobile):
  - Listado de ítems agregados con miniaturas, cantidades fraccionarias y selector de bodega.
  - Selector de lotes específicos con fecha de caducidad.
  - Para recetas: desglose de insumos y opción de override de lotes individuales.
  - Botón primario de registro: `"Registrar Consumo"` con confirmación transaccional y limpieza de carrito.
- [x] **5.2** `BotonesFlotantes.tsx` (Acceso Rápido en Smartphones):
  - Botón flotante para abrir el carrito con contador animado (`badge` numérico).
  - Botón flotante cian para abrir el historial de consumo.
- [x] **5.3** `ConsumoOptionsDialog.tsx` (Personalización de Grupos de Opciones):
  - Modal para seleccionar variantes, salsas, acompañamientos o sustituciones en recetas y combos.
  - Validación de selecciones mínimas y máximas obligatorias.
- [x] **5.4** `ConsumoTemplateModal.tsx` (Gestor de Plantillas de Consumo):
  - Crear o editar plantillas con nombre, descripción, selector público/privado, número de columnas y selector visual de productos incluidos con reordenamiento arrastrable (`drag and drop` o controles de flechas).
- [x] **5.5** `ContingencyModal` y `LocateStockDialog.tsx` (Gestión de Contingencias):
  - Diálogo de contingencia ante insumos con stock vencido o agotado:
    - *Opción A*: Forzar consumo bajo auditoría.
    - *Opción B*: Mermar lote vencido de inmediato.
    - *Opción C*: Buscar alternativas en otras bodegas (`LocateStockDialog`).
- [x] **5.6** `ConsumoLog.tsx` y `ConsumoEditDialog.tsx` (Historial y Auditoría):
  - Panel lateral con historial cronológico de consumos registrados.
  - Selector de fecha individual o rango de fechas (`logDate` a `logEndDate`).
  - Desglose detallado por transacción y operario.
  - Botón de edición de cantidad y justificación de merma (`ConsumoEditDialog`).
  - Botón de anulación / reversión con impacto directo en Kardex.

---

### [x] FASE 6: Vista 2 — Manos Libres (`/consumo/manos-libres`) — ✅ 100% COMPLETADA
- [x] **6.1** Cabecera Visual y Contexto de Cocina/Bar:
  - Componente `SectionHeader` centrado:
    - Título: `"Consumo Manos Libres"`.
    - Subtítulo: `"Registro operativo por voz para cocina, barra y preparación"`.
    - Ícono: `Mic` de `lucide-react`.
    - Color identificador: `#f97316` (naranja vibrante operativo).
  - Selectores superiores de Área Operativa y Bodega.
- [x] **6.2** Estaciones de Trabajo y Selección de Operario:
  - Grilla de tarjetas de cocineros/asistentes de estación con foto, nombre y clave de voz (`voice_command`).
  - Indicador de estado de escucha (Micrófono verde pulsante `Escuchando...` / Micrófono rojo `Silenciado`).
- [x] **6.3** Consola de Captura Verbal y Feed en Vivo:
  - Área visual de transcripción en tiempo real del comando de voz detectado.
  - Feed interactivo de pedidos verbales procesados (consumos y mermas).
  - Reproducción auditiva de confirmación (TTS) y alertas sonoras de éxito/error.
  - Botones táctiles de contingencia manual (+1, confirmar, anular) para asistencia rápida.

---

### [x] FASE 7: Vista 3 — Buffet Inteligente (`/consumo/buffet`) — ✅ 100% COMPLETADA
- [x] **7.1** Cabecera Visual y Panel de Sesiones:
  - Componente `SectionHeader` centrado:
    - Título: `"Buffet Inteligente"`.
    - Subtítulo: `"Control de estaciones, pesaje y liquidación de consumo por comensal"`.
    - Ícono: `ScanLine` / `UtensilsCrossed`.
    - Color identificador: `#06b6d4` (cian tecnológico).
  - Selector de plantillas preconfiguradas (Desayuno Buffet, Almuerzo Ejecutivo, Brunch/Eventos).
- [x] **7.2** Estaciones de Montaje y Escáner Visual (`StationCameraScanner.tsx`):
  - Pestañas por estación de servicio (Calientes, Fríos, Postres, Ensaladas, Panadería).
  - Módulo de cámara web / terminal fotográfica para escaneo de bandejas gastronorm.
  - Estimación de tara, pesaje o porcentaje de consumo servido con modo simulación asistida por IA.
- [x] **7.3** Tabla de Conciliación de Insumos (`BuffetItemsTable.tsx`) y Costeo Pax:
  - Tabla con producto/receta, cantidad inicial montada, reposiciones en vivo, sobrante devuelto y merma no recuperable.
  - Panel financiero en vivo: Costo total de preparación, valor de sobrante rescatado y **Costo Neto por Pax**.
  - Flujo de cierre con modal `BuffetConciliationDialog.tsx` y botón `"Finalizar y Liquidar Buffet"`, enviando insumos consumidos a Kardex bajo RBAC supervisado.

---

### [x] FASE 8: Capas Cruzadas, i18n, Testing 5D y Certificación E2E — ✅ 100% COMPLETADA
- [x] **8.1** Internacionalización Atómica 100% `es`/`en` (`operations.json`):
  - Cobertura total de claves estáticas y dinámicas en ambos idiomas con paridad 1:1 verificada en test unitario.
  - Cero textos hardcodeados en plantillas, diálogos, estados, paginación (`TablePagination`) y mensajes de toast.
- [x] **8.2** Multi-Moneda FX (`Decimal`):
  - Formateo de costos por porción, costos de recetas y costos netos por Pax con soporte de divisas activas (CLP, USD, EUR) vía `useCurrencyFormatter`.
- [x] **8.3** Observabilidad OpenTelemetry & Sentry:
  - Spans distribuidos para transacciones de consumo batch (`consumption.batch.process`), liquidaciones de buffet (`buffet.session.finalize`) y órdenes de voz (`voice.order.register`, `voice.order.confirm`).
  - Métricas de tiempo de respuesta de órdenes de voz y tasas de reconocimiento validadas en suite automatizada.
- [x] **8.4** Testing 5D (Backend Pytest & Frontend Vitest):
  - Pruebas unitarias de Kardex FIFO y explosión de recetas en backend (68 tests pytest en `tests/unit/operations` y `test_consumption_api.py` aprobados al 100%).
  - Pruebas unitarias de componentes y hooks reactivos en frontend (78 tests vitest en `src/features/consumo` y `src/shared/i18n` aprobados al 100%).
  - Verificación estricta de TypeScript (`npx tsc --noEmit`) sin advertencias ni errores (0 errores de tipos).
- [x] **8.5** Certificación Quality Gate 5D Finalizada:
  - Flujo completo verificado: selección de bodega, explosión de recetas, paginación, catálogo reactivo, carrito de consumo, contingencia con mermas, órdenes verbales por voz y liquidación de buffet por Pax.
  - Contratos de API REST idempotentes y seguros bajo RBAC de 3 niveles con control multi-tenant y observabilidad activa.

---

## 🏆 Certificación de Cierre — Quality Gate 5D Aprobado al 100%

| Dimensión de Calidad | Criterio de Verificación | Resultado | Certificación |
|---|---|---|---|
| **D1: Dominio & Lógica** | Kardex FIFO inmutable, explosión de recetas, cálculo exacto de costo Pax con `Decimal` | 68/68 Pytest OK | ✅ APROBADO |
| **D2: Contratos & Tipos** | Paridad TypeScript estricta `npx tsc --noEmit`, Pydantic v2 en FastAPI, RFC 7807 | 0 Errores TS | ✅ APROBADO |
| **D3: Componentes & Hooks** | Pruebas de integración Vitest (`RegistroConsumoPage`, `ManosLibresPage`, `BuffetPage`, modales) | 78/78 Vitest OK | ✅ APROBADO |
| **D4: Trazabilidad & Métricas** | Spans OpenTelemetry (`consumption.batch.process`, `buffet.session.finalize`, `voice.order.*`) | Exportador OTel verificado | ✅ APROBADO |
| **D5: Multi-Tenant & RBAC** | Aislamiento por esquema `tenant_*`, control granular de 3 niveles (`consumption.*`) | Casos 403 / RBAC validados | ✅ APROBADO |
