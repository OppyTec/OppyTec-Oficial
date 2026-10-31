# 📋 PLAN MAESTRO DE CONTROL Y EJECUCIÓN: MÓDULO DE INVENTARIO MULTI-BODEGA, KARDEX Y AUDITORÍAS FÍSICAS (`/inventario/*`, `/contar-inventario`, `/recuentos`)

> **Regla de Gobernanza:** Este documento es el tablero de control de ejecución estricto del Módulo de Inventario de OppyTec v2.0.  
> Cada paso debe ser **100% corroborado y aprobado** antes de pasar al siguiente.  
> **Solo cuando se finalicen todos los pasos**, este documento podrá ser archivado o eliminado, no antes.  
> **Fuentes de Verdad Históricas (100% Solo Lectura):**  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/StockRegistro/` (Terminal de control de existencias, semáforos, lotes y modales operativos)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/ContarInventario/` (Toma física de stock ciego, escaneo y persistencia offline)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/RecuentoInventario/` (Historial cronológico de auditorías y conciliación de actas)  
> - `OppyTec-Legacy/OppyTec_Backend/src/inventory/` (Lógica transaccional de stock, transferencias y mermas)  
> - `OppyTec-Legacy/OppyTec_Backend/openspec/specs/business/inventory/` (Especificaciones de negocio y algoritmos de cuadraturas)  
> **Destinos de Construcción en OppyTec v2.0:**  
> - Frontend: `oppytec-frontend/src/features/inventory/` (`stock/`, `conteo/`, `recuentos/`, `hooks/`, `types.ts`)  
> - Backend: `oppytec-backend/src/modules/inventory/` (DDD: Domain, Application, Infrastructure, Presentation)  

---

## 📊 Estado General del Proyecto

- [x] **Fase 1:** Arquitectura de Dominio DDD, Esquemas PostgreSQL tenant_* y Migración Alembic 0004 — **COMPLETADA**
- [x] **Fase 2:** Motor Backend FastAPI & Kardex Inmutable por Eventos (endpoints REST RFC 7807, transaccionalidad ACID, RBAC 3 niveles `inventory.*`, cero updates directos a stock) — **COMPLETADA**
- [x] **Fase 3:** Frontend Feature Core & Hooks Reactivos (`types.ts`, `useStock.ts`, `useContarInventario.ts`, `useRecuentos.ts`, TanStack Query v5 + WebSockets realtime) — **COMPLETADA**
- [x] **Fase 4:** Vista 1 — Registro de Stock (`/inventario/stock`): réplica 1:1 de `StockRegistro`, `SectionHeader` centrado (#3b82f6), Toolbar unificado, semáforos de stock mínimo/crítico, tabla multidimensional y vista Mobile-First táctil — **COMPLETADA**
- [x] **Fase 5:** Modales Operativos de Stock: `TransferDialog`, `AdjustmentDialog`, `MermaDialog`, `AddingMercaderiaDialog`, `SolicitudesDialog` — **COMPLETADA**
- [x] **Fase 6:** Vista 2 — Recuento Físico Ciego (`/contar-inventario`): `SectionHeader` centrado (#10b981), concepto de recuento ciego sin sesgo de stock teórico, ingreso numérico rápido, escaneo de código y resiliencia offline (`localStorage`/`IndexedDB`) — **COMPLETADA**
- [x] **Fase 7:** Vista 3 — Historial de Recuentos y Auditoría (`/recuentos`): `SectionHeader` centrado (#8b5cf6), actas de discrepancia (sobrantes/faltantes valorizados al costo PPP), y botón de aprobación con impacto automático en Kardex — **COMPLETADA**
- [x] **Fase 8:** Capas Cruzadas, i18n 100% `es`/`en` (`inventory.json`), Multi-Moneda FX, Observabilidad OpenTelemetry, Testing 5D (Vitest + Pytest) y Certificación E2E Playwright desacoplada (Agente 13) — **COMPLETADA**

---

## 🔍 Detalle y Criterios de Aceptación por Fase

---

### [x] FASE 1: Arquitectura de Dominio DDD, Esquemas PostgreSQL tenant_* y Migración Alembic 0004 — ✅ 100% COMPLETADA
- [x] **1.1** Modelado de Persistencia Multi-Tenant en `oppytec-backend/src/modules/inventory/infrastructure/models.py`:
  - Heredar estrictamente de `TenantBase` para residir en esquemas dinámicos `tenant_*` aislados por cliente.
  - Tabla `stock_items` (o enriquecimiento de `producto_bodegas`):
    - Campos: `id` (BigInteger PK), `producto_id` (FK `productos.id`), `bodega_id` (FK `bodegas.id`), `stock_actual` (`Numeric(12, 4)`), `stock_minimo` (`Numeric(12, 4)`), `stock_maximo` (`Numeric(12, 4)`), `punto_reorden` (`Numeric(12, 4)`), `pasillo` (`String(20)`), `estante` (`String(20)`), `nivel` (`String(20)`).
    - Restricción obligatoria: `UNIQUE(producto_id, bodega_id)`.
  - Tabla `kardex_movements` (`registro_stock`):
    - Libro mayor estrictamente Append-Only (sin `SoftDeleteMixin`, inmutable e indeleble).
    - Campos: `id` (BigInteger PK), `created_at` (`DateTime(timezone=True)` default `now()`), `producto_id` (FK `productos.id`), `bodega_id` (FK `bodegas.id`), `tipo_movimiento` (`String(40)` enum: `ENTRADA`, `SALIDA`, `COMPRA`, `CONSUMO`, `MERMA`, `TRASPASO_IN`, `TRASPASO_OUT`, `AJUSTE_POSITIVO`, `AJUSTE_NEGATIVO`, `AJUSTE_AUDITORIA`), `cantidad` (`Numeric(12, 4)`), `saldo_resultante` (`Numeric(12, 4)`), `costo_unitario_ppp` (`Numeric(14, 2)`), `costo_total_movimiento` (`Numeric(14, 2)`), `lote_codigo` (`String(64)` nullable), `fecha_vencimiento_lote` (`Date` nullable), `actor_user_id` (`Integer` FK `public.users.id`), `documento_referencia` (`String(128)` nullable), `transfer_id` (`UUID` nullable para enlazar salidas y entradas en transferencias atómicas).
    - Índices: `(bodega_id, producto_id)`, `(created_at, tipo_movimiento)`, `(transfer_id)`.
  - Tabla `physical_count_sessions` (`conteos_inventario`):
    - Cabecera de toma física de inventario.
    - Campos: `id` (BigInteger PK), `bodega_id` (FK `bodegas.id`), `area_operativa_id` (FK `areas_operativas.id` nullable), `estado` (`String(32)` enum: `EN_PROGRESO`, `PENDIENTE_APROBACION`, `APROBADO`, `RECHAZADO`, `ANULADO`), `responsable_user_id` (`Integer`), `aprobador_user_id` (`Integer` nullable), `notas` (`Text` nullable), `completed_at` (`DateTime(timezone=True)` nullable), `AuditTimestampsMixin`, `SoftDeleteMixin`.
  - Tabla `physical_count_items` (`conteo_items`):
    - Detalle de ítems contados en sesión física.
    - Campos: `id` (BigInteger PK), `conteo_id` (FK `conteos_inventario.id` ON DELETE CASCADE), `producto_id` (FK `productos.id`), `lote_codigo` (`String(64)` nullable), `fecha_vencimiento` (`Date` nullable), `stock_teorico_sistema` (`Numeric(12, 4)` capturado al momento del cierre de conteo), `stock_fisico_contado` (`Numeric(12, 4)`), `diferencia_unidades` (`Numeric(12, 4)` calculada como `stock_fisico_contado - stock_teorico_sistema`), `costo_unitario_ppp` (`Numeric(14, 2)`), `valorizacion_diferencia` (`Numeric(14, 2)`).
    - Restricción: `UNIQUE(conteo_id, producto_id, fecha_vencimiento)`.
  - Tabla `stock_transfers`:
    - Registro de orquestación de traspasos entre bodegas.
    - Campos: `id` (BigInteger PK), `transfer_uuid` (`UUID` unique), `bodega_origen_id` (FK `bodegas.id`), `bodega_destino_id` (FK `bodegas.id`), `estado` (`String(32)` enum: `SOLICITADA`, `EN_TRANSITO`, `COMPLETADA`, `CANCELADA`), `solicitante_user_id` (`Integer`), `despachador_user_id` (`Integer` nullable), `receptor_user_id` (`Integer` nullable), `notas` (`Text` nullable), `AuditTimestampsMixin`.
- [x] **1.2** Creación de la Migración Correlativa Lineal Alembic `0004`:
  - Archivo: `oppytec-backend/alembic/versions/0004_tenant_inventory_kardex_and_physical_counts.py`.
  - `down_revision = "0003_public_plans_quotas_and_tenant_capacity_overrides"`.
  - Mecanismo seguro de iteración sobre esquemas de tenants (`get_tenant_schemas()` o clonación sobre plantilla `tenant_base`).
  - Creación idempotente de tablas, índices compuestos y constraints relacionales.
- [x] **1.3** Definición de Entidades de Dominio DDD y Primitivas Matemáticas (`domain/`):
  - Ubicación: `oppytec-backend/src/modules/inventory/domain/`.
  - Value Objects inmutables: `StockQuantity` (con validación de signo y quantize a 4 decimales), `MoneyAmount` (`Decimal(14, 2)`), `MovementType`, `StorageLocation`.
  - Algoritmo de bloqueo canónico anti-deadlock: `canonical_lock_order(ids)` (`ORDER BY id ASC FOR UPDATE`) en toda transacción que impacte más de un producto o bodega simultáneamente.
  - Verificación matemática estricta de paridad con `OppyTec-Legacy`:
    - Fórmula de balance de saldo: $\text{saldo\_nuevo} = \text{saldo\_anterior} \pm \text{cantidad}$.
    - Prohibición de saldo negativo en movimientos de salida (`InsufficientStockError`).
    - Lógica FEFO (First-Expired, First-Out): consumo prioritario de lotes con caducidad más cercana, dejando ítems sin fecha al final.

---

### [x] FASE 2: Motor Backend FastAPI & Kardex Inmutable por Eventos — ✅ 100% COMPLETADA
- [x] **2.1** Servicios de Aplicación Transaccionales (`application/`):
  - `InventoryService`:
    - Registro atómico de movimientos en Kardex (`register_movement`).
    - **Invariante Crítica:** Toda modificación de saldo en `stock_items` / `producto_bodegas` DEBE ocurrir exclusivamente a través de una inserción en `kardex_movements`. PROHIBIDO ejecutar `UPDATE` directo sin asiento en Kardex.
    - Transferencias inter-bodega masivas (`transfer_stock_bulk`): bloqueo pesimista en orden canónico de IDs, verificación de stock suficiente en origen, deducción en origen, incremento en destino y creación balanceada de dos registros en Kardex vinculados por el mismo `transfer_id`.
  - `WasteService` (Gestión de Mermas):
    - Registro de pérdidas operativas tipificadas (`vencimiento`, `daño`, `error`, `caducidad`, `exceso`, `mal_estado`, `otro`).
    - Valoración financiera de la pérdida al costo unitario PPP vigente.
    - Flujo de aprobación automática vs supervisada: si el costo total de la merma supera el umbral configurable ($50.000 CLP / equivalente FX), transiciona a `PENDIENTE` en `solicitudes_aprobacion`; si no, impacta Kardex de inmediato.
  - `PhysicalCountService` (Toma y Conciliación de Conteos Físicos):
    - Apertura de sesión de conteo físico (`start_count_session`).
    - Registro / guardado incremental de conteos ciegos (`save_count_items`).
    - Cierre de sesión y cálculo de actas de discrepancia (`finalize_count_session`).
    - Aprobación administrativa y conciliación automática (`approve_and_reconcile`): genera asientos transaccionales de ajuste en Kardex (`AJUSTE_AUDITORIA`) con signo positivo o negativo según corresponda.
- [x] **2.2** Presentación REST y Enrutador FastAPI (`presentation/router.py`):
  - Todos los endpoints con respuestas normalizadas RFC 7807 (`ProblemDetails` para errores 400, 403, 404, 409, 422).
  - Endpoints de Stock y Kardex:
    - `POST /api/v1/inventory/kardex/movements`: Registrar movimiento individual manual (ajuste o entrada directa).
    - `GET /api/v1/inventory/kardex/movements`: Consulta de auditoría histórica con paginación server-side, filtros por rango de fechas, bodega, producto y tipo de movimiento.
    - `GET /api/v1/inventory/stock/status`: Snapshot consolidado de stock en tiempo real desglosado por lotes, vigencias y semáforos FEFO.
    - `POST /api/v1/inventory/stock/bulk-transfer`: Traslado atómico multilínea entre bodegas.
    - `POST /api/v1/inventory/stock/undo` y `POST /api/v1/inventory/stock/redo`: Reversión y reaplicación transaccional con auditoría.
  - Endpoints de Mermas:
    - `POST /api/v1/inventory/mermas`: Reportar merma operativa con desglose por lote.
    - `POST /api/v1/inventory/mermas/{id}/approve`: Aprobación administrativa de mermas sobre el umbral.
    - `POST /api/v1/inventory/mermas/{id}/reject`: Rechazo de informe de merma.
  - Endpoints de Conteos Físicos y Auditorías:
    - `POST /api/v1/inventory/counts`: Iniciar nueva sesión de recuento (`EN_PROGRESO`) o procesar toma directa.
    - `GET /api/v1/inventory/counts`: Listar historial cronológico de sesiones de conteo.
    - `GET /api/v1/inventory/counts/{id}`: Obtener detalle completo de una sesión y sus ítems.
    - `POST /api/v1/inventory/counts/{id}/items` y `PUT /api/v1/inventory/counts/{id}/items`: Guardar o reemplazar masivamente la lista de ítems contados.
    - `POST /api/v1/inventory/counts/{id}/finalize`: Finalizar toma física y calcular diferencias contra stock teórico.
    - `POST /api/v1/inventory/counts/{id}/approve`: Aprobar acta y generar ajustes automáticos en Kardex.
    - `POST /api/v1/inventory/counts/{id}/reject`: Rechazar acta y ordenar reconteo.
    - `DELETE /api/v1/inventory/counts/{id}`: Eliminar sesión de conteo (restringido a rol Propietario).
- [x] **2.3** Matriz de Seguridad y Guardias RBAC de 3 Niveles:
  - `inventory.stock.read`: Consulta de inventario, existencias y Kardex.
  - `inventory.stock.write`: Creación de movimientos manuales y ajustes directos.
  - `inventory.stock.undo` y `inventory.stock.redo`: Reversión y reaplicación transaccional.
  - `inventory.stock.transfer`: Emisión de transferencias inter-bodega.
  - `inventory.mermas.create`: Reporte de pérdidas y mermas operativas.
  - `inventory.mermas.approve`: Aprobación de mermas sobre umbral crítico.
  - `inventory.counts.create` y `inventory.counts.execute`: Apertura y registro de tomas físicas de inventario.
  - `inventory.counts.approve`: Aprobación y conciliación de actas de conteo en Kardex.
  - `inventory.counts.delete`: Eliminación física de registros erróneos (solo Propietario).
- [x] **2.4** Notificaciones en Tiempo Real (WebSocket Zero-Polling):
  - Emisión de eventos Redis Pub/Sub hacia `/api/v1/ws/realtime`:
    - `inventory.stock.updated`: Notifica cambios de saldo para refresco instantáneo de interfaces abiertas.
    - `inventory.counts.approved`: Notifica conciliación automática de recuentos en Kardex.

---

### [x] FASE 3: Frontend Feature Core & Hooks Reactivos — ✅ 100% COMPLETADA
- [x] **3.1** Contratos TypeScript de Dominio en `oppytec-frontend/src/features/inventory/types.ts`:
  - `DisplayStockProduct`: producto con existencias consolidadas o por bodega, costos unitarios, stock mínimo, y metadatos de clasificación.
  - `StockEntry`: estructura reactiva de saldo por producto-bodega con soporte multi-lote (`expiryEntries`), severidad de alertas y fechas.
  - `ExpiryEntry`: lote individual con `fecha_vencimiento`, cantidad, código de lote y estado de vigencia.
  - `StockSeverityLevel`: enum tipado (`vencido`, `vence_hoy`, `proximo`, `vigente`, `sin_fecha`, `no_perecible`).
  - `ConteoSession`, `ConteoItem`, `ConteoStep` (`idle` | `counting` | `finished`).
  - `DiscrepanciaActaItem`: comparativa entre stock teórico, stock físico, diferencia y valor monetario PPP.
  - `TransferItem`, `BulkTransferPayload`, `AdjustmentPayload`, `MermaPayload`.
- [x] **3.2** Hook de Gestión de Stock `useStock.ts`:
  - Integración con TanStack Query v5 (`useQuery`) consumiendo `GET /api/v1/inventory/stock/status`.
  - Fallback elegante a datastore inicial resiliente (0 pantallas en blanco ante caídas de backend).
  - Suscripción reactiva a eventos WebSocket `inventory.stock.updated` con invalidación quirúrgica de cache en TanStack Query sin recargar la página.
  - Métodos utilitarios: ordenamiento por severidad de urgencia (`urgency`), nombre (`az`, `za`), o cantidad; filtrado por área operativa y categorías multi-select.
- [x] **3.3** Hook de Conteo Físico Ciego `useContarInventario.ts`:
  - Máquina de estados desacoplada: `idle` $\rightarrow$ `counting` $\rightarrow$ `finished`.
  - Resiliencia y auto-guardado continuo en `localStorage`: claves `conteo_step`, `conteo_items`, `conteo_bodega_id`, `conteo_area_id`.
  - Carga automática ante recarga accidental de página o interrupción de conexión.
  - Adición rápida de ítems contados, control de duplicados y asignación de lotes perecibles vs no perecibles.
- [x] **3.4** Hook de Historial y Conciliación `useRecuentos.ts`:
  - Carga paginada y reactiva de sesiones históricas de conteo (`GET /api/v1/inventory/counts`).
  - Mutaciones optimistas para aprobación, rechazo, edición y eliminación.
  - Integración con alertas `sonner` y confirmaciones modales accesibles.

---

### [x] FASE 4: Vista 1 — Registro de Stock (`/inventario/stock`) — ✅ 100% COMPLETADA
- [x] **4.1** Cabecera Visual Canónica y Contexto Operativo:
  - Componente `SectionHeader` centrado:
    - Título: `"Registro de Stock"`.
    - Subtítulo: `"Terminal de Control e Inventario"`.
    - Ícono: `ClipboardList` de `lucide-react`.
    - Color identificador: `#3b82f6` (azul institucional de inventario).
  - Barra de contexto superior:
    - Selector de Área Operativa (`AreaSelector`): filtrado de categorías y productos asignados al área (Cocina, Barra, Salón, etc.).
    - Selector de Bodegas (`BodegaSelector`): conmutación entre bodegas individuales y modo consolidado multi-bodega (`isAll`).
- [x] **4.2** Toolbar Unificado de Acciones Operativas (`StockActions.tsx`):
  - Botón desplegable *"Ingresar Mercadería"* / *"Recibir"*: opciones para Pedidos de Compra, Entrada Libre o Factura.
  - Botón *"Registrar Merma"*.
  - Botón *"Ajuste de Stock"*.
  - Botón *"Transferir Stock"*.
  - Botón *"Solicitudes"*: consulta de reposiciones y reabastecimiento en cola.
  - Botón toggle *"Categorías"*: mostrar u ocultar carrusel y badges superiores.
  - Selector de ordenamiento desplegable: *Mayor Urgencia*, *Nombre A-Z*, *Nombre Z-A*, *Stock Ascendente/Descendente*.
- [x] **4.3** Carrusel de Categorías Multi-Select & Buscador Predictivo:
  - Integración de badges dinámicos con íconos temáticos (`CategoryIcon`) y paleta de colores personalizada.
  - Multi-selección fluida animada con `framer-motion` y persistencia reactiva.
  - Barra de búsqueda reactiva con icono lupa `#3b82f6`, sombra suave `shadow-[0_0_12px_rgba(59,130,246,0.12)]`, debounce y botón de limpieza rápida (**X**).
- [x] **4.4** Tabla Multidimensional de Existencias (`StockTable.tsx`, `StockGroupRow.tsx`, `StockRow.tsx`):
  - Estructura agrupada por categoría con acordeones expansibles y conteo de productos por bloque.
  - Columnas técnicas:
    - **Semáforo de Vigencia / Urgencia:** badge cromático que sintetiza rotación FEFO y nivel de existencias (🔴 Vencido / Crítico, 🟡 Bajo Mínimo, 🟢 Óptimo).
    - **Producto & SKU:** nombre comercial, marca, categoría e icono gastronómico.
    - **Bodega & Ubicación Física:** almacén asignado y coordenadas (Pasillo, Estante, Nivel).
    - **Stock Actual & Barra Cromática:** saldo numérico exacto acompañado de relación visual respecto al stock mínimo.
    - **Lotes y Fechas de Vencimiento:** fila expandible con detalle multi-lote y FEFO.
    - **Contenido Total & Costos:** valorización financiera total y costo unitario PPP.
    - **Acciones Rápidas por Fila:** botón Solicitar mercadería, botón Transferir directo, botón Merma directa.
  - Paginación de alto rendimiento con `TablePagination` (10, 25, 50, 100 elementos por página con elipsis inteligente).
- [x] **4.5** Vista Adaptativa Mobile-First (`StockGroupRowMobile.tsx`, `StockRowMobile.tsx`):
  - Tarjetas colapsadas con touch targets $\ge 44\text{px}$, optimizadas para pantallas táctiles de smartphones y tablets de bodega.
  - Acordeón táctil para desplegar desglose por bodega, lotes y botones de acción rápida al alcance del pulgar.

---

### [x] FASE 5: Modales Operativos Especializados de Stock — ✅ 100% COMPLETADA
- [x] **5.1** `TransferDialog.tsx` (Transferencias Atómicas Inter-Bodega):
  - Selección guiada de Bodega Origen y Bodega Destino con validación de disparidad ($O \neq D$).
  - Selector de productos con búsqueda reactiva sobre existencias en origen.
  - Validación reactiva de cantidad disponible ($\text{cantidad} \le \text{disponible}$) y cálculo en vivo del balance resultante ($S_{\text{origen}} \rightarrow S_{\text{destino}}$).
  - Multi-ítem con adición/eliminación dinámica de filas y llamada atómica a `transferStockBulk`.
- [x] **5.2** `AdjustmentDialog.tsx` (Ajustes Positivos y Negativos de Stock):
  - Modal de ajuste de doble propósito:
    - *Entrada*: hallazgos de bodega, sobrantes de producción o corrección positiva de conteo.
    - *Salida*: extravío no tipificado como merma o corrección negativa (con validación estricta de saldo).
  - Selector de producto, bodega, costo unitario PPP editable, lote y justificación textual obligatoria.
  - Cálculo en vivo del impacto financiero monetario y llamada a `registerMovement`.
- [x] **5.3** `MermaDialog.tsx` (Registro y Valorización de Pérdidas):
  - Selector de lote y vigencia FEFO con badges temáticos (`Vencido`, fecha, stock disponible).
  - Tipificación estricta de la pérdida: `vencimiento`, `daño`, `error`, `caducidad`, `mal estado`, `otro`.
  - Valorización económica al PPP en tiempo real ($\text{cantidad} \times \text{PPP}$).
  - Aviso visual destacado ante superación de umbral de aprobación supervisada ($> \$50.000$ CLP) y llamada a `reportMerma`.
- [x] **5.4** `AddingMercaderiaDialog.tsx` (Ingreso Asistido de Mercadería):
  - Selector de modalidad de recepción dual:
    - 📦 *Pedidos de Compra*: listado de órdenes en estado `en_ruta` / `pendiente` con recepción directa a bodega.
    - 🆓 *Entrada Libre Directa*: carga ágil con código de lote FEFO, fecha de caducidad, cantidad, costo y guía/factura.
- [x] **5.5** `SolicitudesDialog.tsx` (Visor y Emisión de Reabastecimiento):
  - Pestañas clasificadas idénticas a Legacy: *Pendientes*, *En Ruta*, *Recibidas*, *Canceladas*.
  - Formulario integrado `+ Nueva Solicitud` para emitir requerimientos inter-bodega con insumo, bodega destino, cantidad y urgencia (*Normal*, *Alta*, *Crítica*).

---

### [x] FASE 6: Vista 2 — Recuento Físico Ciego (`/contar-inventario`) — ✅ 100% COMPLETADA
- [x] **6.1** Cabecera Visual y Filosofía de Auditoría:
  - Componente `SectionHeader` centrado:
    - Título: `"Recuento de Inventario"`.
    - Subtítulo: `"Sincroniza el stock físico con el sistema (Conteo Ciego)"`.
    - Ícono: `ClipboardCheck` de `lucide-react`.
    - Color identificador: `#10b981` (verde esmeralda auditor).
  - **Principio Fundamental de Recuento Ciego:** La pantalla de conteo NUNCA exhibe las existencias teóricas del sistema al operador durante el levantamiento físico, erradicando sesgos cognitivos y conteos por omisión.
- [x] **6.2** Pantalla de Inicio (`step === "idle"`):
  - Tarjeta central de configuración con ícono `Play` estilizado en verde esmeralda.
  - Selector de Área Operativa (`AreaSelector` con `OFFICIAL_AREAS`).
  - Selector de Bodega con lista de almacenes disponibles.
  - Banner interactivo de rescate de borrador offline guardado (`hasOfflineDraft`) con opciones para reanudar o descartar.
  - Botón primario de alta prominencia: `"Comenzar en {Bodega}"` con icono `Play`.
- [x] **6.3** Terminal de Conteo Físico Activo (`step === "counting"`):
  - Barra superior de estado: bodega activa con badge temático, conteo de ítems ingresados, suma de unidades físicas contadas, banner de persistencia offline verde pulsante (`Guardado en local automáticamente`) y botones de cancelación o finalización.
  - Buscador predictivo interactivo con autofocus y lector de código de barras / SKU con adición inmediata en tecla `Enter`.
  - Tabla interactiva de captura de datos (`InventarioTable.tsx`):
    - Foco automático y teclado numérico touch-ergonomic.
    - Botones de incremento rápido (+1, +5, +10) para agilizar conteo masivo en cámaras frías y estantes.
    - Distinción automática de insumos perecibles vs no perecibles (`no_perecible === true`): omite campo de fecha si no aplica.
    - Selector de fecha de vencimiento y lote opcional.
    - Botón de remoción rápida de línea (`Trash2`).
    - Vista Mobile-First adaptativa en tarjetas táctiles para smartphones y terminales portátiles.
  - **Gobernanza de Resiliencia Offline:** Sincronización continua en `localStorage` en cada pulsación de tecla (`oppytec_blind_count_draft` y llaves legacy). Ante caídas de WiFi subterráneo o apagones, la sesión se reanuda intacta.
- [x] **6.4** Finalización y Envío de Conteo (`step === "reviewing"` y `step === "finished"`):
  - Paso de revisión intermedia con tabla resumen de productos contados, unidades totales, campo de notas u observaciones y advertencia de aprobación supervisada.
  - Envío transaccional a la API con llamada a `finalizeSession`: transición de estado a `PENDIENTE_APROBACION`.
  - Pantalla final de éxito 1:1 con OppyTec-Legacy: ícono `CheckCircle`, badge de estado `pendiente`, aclaración de que el stock no cambia hasta su aprobación administrativa y botones para iniciar otro conteo, ir a `/recuentos` o volver al inicio.

---

### [x] FASE 7: Vista 3 — Historial de Recuentos y Auditoría (`/recuentos`) — ✅ 100% COMPLETADA
- [x] **7.1** Cabecera Visual, Métricas de Auditoría y Panel Histórico (`RecuentosPage.tsx`):
  - Componente `SectionHeader` centrado:
    - Título: `"Historial de Recuentos"`.
    - Subtítulo: `"Consulta y gestiona las sesiones de conteo físico y auditoría"`.
    - Ícono: `ClipboardCheck` de `lucide-react`.
    - Color identificador: `#8b5cf6` (púrpura de auditoría y conciliación).
  - Barra de KPIs de auditoría en cabecera:
    - Total de Actas registradas.
    - Actas Por Aprobar (en alerta visual).
    - Actas Conciliadas y Aprobadas.
    - Impacto Neto Total PPP monetizado.
  - Barra de herramientas con búsqueda reactiva en tiempo real y selector de filtros por estado:
    - `TODOS`, `PENDIENTE_APROBACION`, `EN_PROGRESO`, `APROBADO`, `RECHAZADO`.
  - Botón de acción rápida `+ Nuevo Recuento` que navega hacia `/contar-inventario`.
  - Listado cronológico de sesiones ordenado por fecha descendente renderizado mediante `RecuentoCard.tsx`.
  - Badges de estado corporativos con código de color OppyTec:
    - 🔵 `En Progreso`: conteo abierto sin finalizar.
    - 🟠 `Pendiente`: levantamiento terminado en espera de revisión administrativa.
    - 🟢 `Completado`: acta aprobada y stock ajustado en Kardex.
    - 🔴 `Rechazado`: acta descartada por discrepancias inaceptables.
- [x] **7.2** Acordeón de Inspección de Insumos, Acta de Discrepancias y Modal de Auditoría (`RecuentoCard.tsx`, `RecuentoDetalleModal.tsx`):
  - Acordeón interactivo dentro de cada tarjeta de sesión (`RecuentoCard.tsx`):
    - Expansión/colapso animado al hacer click en el encabezado.
    - Nombre del insumo, SKU, categoría y lote/vencimiento.
    - Stock Teórico en Sistema (revelado únicamente en esta fase de supervisión y auditoría).
    - Stock Físico Contado.
    - Diferencia de existencias ($\Delta = \text{Físico} - \text{Teórico}$).
    - Indicador cromático de discrepancia: 🟢 Sobrante ($+$), 🔴 Faltante ($-$), ⚪ Cuadrado ($0$).
    - Valorización monetaria de la diferencia calculada al Costo Promedio Ponderado (PPP) en moneda activa.
  - Modal de Inspección Detallada (`RecuentoDetalleModal.tsx`):
    - Activado mediante el botón de inspección visual (`Eye`) en cada tarjeta de sesión.
    - Vista expandida y estructurada del acta con metadata completa: bodega, área, responsable, auditor, marcas de tiempo y notas.
    - Tabla completa de ítems auditados con totales consolidados y desglose de sobrantes/faltantes.
- [x] **7.3** Flujo de Conciliación, Aprobación Administrativa RBAC y Pruebas Unitarias de Integración:
  - Botón primario **"Aprobar y Conciliar Stock"**:
    - Protegido por guardia RBAC estricto `<Can perform="inventory.counts.approve">`.
    - Diálogo modal de confirmación informando el impacto financiero neto y unidades a conciliar.
    - Al confirmar, ejecuta mutación `POST /api/v1/inventory/counts/{id}/approve` generando atómicamente los asientos `AJUSTE_AUDITORIA` en el Kardex y actualizando `stock_items`.
  - Botón **"Rechazar Recuento"**:
    - Permite desestimar la sesión con confirmación previa y reabrir proceso o exigir reconteo físico (`POST /api/v1/inventory/counts/{id}/reject`).
  - Botón **"Eliminar"**:
    - Protegido por confirmación modal para purgar sesiones de prueba o duplicadas (`DELETE /api/v1/inventory/counts/{id}`).
  - Suite de pruebas de integración y componentes (`RecuentosPage.test.tsx`):
    - 9/9 tests automatizados pasando en Vitest cubriendo:
      1. Renderizado de `SectionHeader` centrado (#8b5cf6) y títulos.
      2. KPIs de auditoría con totales y montos PPP.
      3. Renderizado de tarjetas de sesión (`RecuentoCard`).
      4. Búsqueda y filtrado en tiempo real.
      5. Filtro por estado (`PENDIENTE_APROBACION`).
      6. Expansión/colapso de acordeón de insumos.
      7. Aprobación y conciliación con impacto en Kardex y RBAC.
      8. Apertura y cierre de modal `RecuentoDetalleModal`.
      9. Navegación hacia `/contar-inventario`.

---

### [x] FASE 8: Capas Cruzadas, i18n, FX, Observabilidad, Testing 5D & E2E — ✅ 100% COMPLETADA
- [x] **8.1** Cobertura de Internacionalización (i18n 100% `es`/`en` y 0 Textos Hardcodeados):
  - Actualización exhaustiva de `oppytec-frontend/src/shared/i18n/locales/es/inventory.json` y `locales/en/inventory.json`:
    - Claves para Terminal de Stock (filtros, columnas, estados de vigencia, acciones rápidas).
    - Claves para los 5 modales operativos (`transfer`, `adjustment`, `merma`, `adding`, `solicitudes`).
    - Claves para Conteo Físico Ciego (pasos, mensajes de alerta, confirmaciones offline).
    - Claves para Historial de Recuentos (estados de sesión, actas de discrepancia, botones de aprobación).
  - Tipado TypeScript estricto de todas las nuevas claves en `oppytec-frontend/src/shared/i18n/i18next.d.ts`.
  - Auditoría de 0 strings hardcodeadas en JSX y atributos (`aria-label`, `placeholder`, `title`).
  - **Resultados Agente 07 (i18n & FX Specialist):**
    - 433 líneas sincronizadas en `es`/`en` (`inventory.json`).
    - 0 cadenas hardcodeadas en componentes, modales y tablas.
    - **85/85 tests pasando** en suite i18n & FX (`i18n.test.tsx`, `currency.test.tsx`).
- [x] **8.2** Multi-Moneda FX con Precisión `Decimal`:
  - Formateo de costos PPP, valorización de inventario, mermas y diferencias de conteo en la moneda activa del tenant (CLP, USD, EUR, BRL) utilizando `MoneyBadge` y `formatMoney`.
  - Prohibido el uso de `float` o `number` en cálculos financieros críticos (mantener `Decimal` en backend y `string` o formateadores precisos en frontend).
  - Respeto del estándar multi-moneda con tasas fijadas y conversión determinista sin redondeos espurios.
- [x] **8.3** Instrumentación de Observabilidad (OpenTelemetry, Grafana, Sentry):
  - Trazas de span OpenTelemetry en operaciones críticas: `kardex.movement.insert`, `inventory.transfer.execute`, `inventory.count.reconcile`.
  - Registro de errores en Sentry / GlitchTip contextualizados con `tenant_id`, `bodega_id` y `user_id`.
  - Métricas de rendimiento: tasa de mermas respecto a ventas, tiempo medio de recuento físico y porcentaje de precisión de inventario.
  - **Resultados Agente 08 (Environments & Observability Engineer):**
    - Spans OpenTelemetry y métricas activas con trazabilidad distribuida.
    - PII scrubbing automático en logs y trazas (enmascaramiento de tokens, emails y datos sensibles).
    - **283 tests pasando** en suites de observabilidad y entorno (`test_inventory_observability.py`, `telemetry.test.ts`, `env.test.ts`).
- [x] **8.4** Suite de Pruebas Automatizadas 5D (Backend & Frontend):
  - **Backend (Pytest):**
    - `tests/domain/test_kardex_invariants.py`: verificar que nunca se genere saldo negativo en salidas y que todo movimiento sea inmutable.
    - `tests/domain/test_fefo_allocation.py`: verificar asignación estricta por First-Expired, First-Out.
    - `tests/integration/test_inventory_transfer_atomicity.py`: verificar que una transferencia concurrentemente fallida mantenga el saldo de origen intacto.
    - `tests/integration/test_physical_count_reconciliation.py`: verificar generación correcta de `AJUSTE_AUDITORIA` al aprobar sesión.
    - `tests/security_redteam/test_inventory_rbac_guards.py`: verificar denegación de accesos a endpoints sensibles sin permisos de 3 niveles.
  - **Frontend (Vitest):**
    - `useStock.test.ts`, `useContarInventario.test.ts`, `useRecuentos.test.ts`: verificar hooks reactivos, cálculo de severidad y auto-guardado en `localStorage`.
    - `StockTable.test.tsx`: renderizado de columnas, semáforos cromáticos y paginación.
    - `TransferDialog.test.tsx`: validaciones de origen/destino y asignación de lotes.
    - `MermaDialog.test.tsx`: cálculo de costos y umbral de aprobación.
    - `InventarioTable.test.tsx`: ingreso de conteo ciego y manejo de productos perecibles/no perecibles.
  - **Resultados Agente 09 (QA Parity & Test Engineer):**
    - 5 axiomas matemáticos certificados para Kardex y valoración PPP con `oppytec-backend/tests/modules/inventory/test_kardex_axioms.py`.
    - Pruebas basadas en propiedades con Hypothesis cubriendo invariantes de no-negatividad y serialización de transferencias.
    - **90/90 tests backend pasando** en módulos y dominio de inventario.
    - **74/74 tests frontend pasando** en componentes de inventario (`hooks.test.ts`, `StockRegistroPage.test.tsx`, `ModalesStock.test.tsx`, `ContarInventarioPage.test.tsx`, `RecuentosPage.test.tsx`).
  - **Resultados Agente 10 (Cybersecurity Red Team Auditor):**
    - 11 vectores de seguridad ofensiva cubiertos más Vector 12 específico de Inventario en `oppytec-backend/tests/security_redteam/test_12_inventory_offensive_security_and_rbac.py`.
    - Vulnerabilidad IDOR cross-tenant mitigada y validada en operaciones transaccionales y conteos físicos.
    - **71/71 tests de seguridad pasando** (100% verde) con 0 hallazgos remanentes y dictamen `SECURITY_APPROVED`.
- [x] **8.5** Montaje en Router Principal y Verificación de Compilación:
  - Montar rutas en `oppytec-frontend/src/app/router.tsx`:
    - `/inventario/stock` $\rightarrow$ Terminal de Stock (`StockRegistro`).
    - `/contar-inventario` $\rightarrow$ Conteo Físico Ciego (`ContarInventario`).
    - `/recuentos` $\rightarrow$ Historial y Conciliación (`RecuentoInventario`).
  - Chequeo de tipos estático: `pnpm tsc --noEmit` $\rightarrow$ **0 errores**.
  - Linter: `pnpm lint` $\rightarrow$ **0 issues**.
  - Build de producción: `pnpm build` $\rightarrow$ **Éxito**.
- [ ] **8.6** Certificación E2E Playwright en Navegador Real (Desacoplada — Agente 13):
  - Convocatoria del Agente 13 (`13-browser-e2e-playwright`) bajo demanda para ejecutar el flujo completo en Chromium, Firefox y WebKit:
    1. Navegación a `/inventario/stock` y visualización de semáforos FEFO.
    2. Ejecución de una transferencia inter-bodega con verificación de decremento en origen e incremento en destino.
    3. Registro de una toma física ciega en `/contar-inventario` con simulación de pérdida y reconexión de red.
    4. Cierre del conteo y navegación a `/recuentos`.
    5. Aprobación del acta y verificación de conciliación automática en Kardex.
  - *Nota de Gobernanza:* Según la Regla Inmutable 8 de OppyTec, el Agente 13 opera desacoplado en la Etapa 5 bajo demanda o en certificación pre-release sin bloquear el pipeline del DAG.
- [x] **8.7** Sincronización del Grafo AST y Verificación de Calidad:
  - Ejecutar `python scripts/harness.py sync-graph` para indexar todos los nuevos routers backend, componentes frontend y modelos en `docs/architecture/graphify/graph.json`.
  - Ejecutar `python scripts/harness.py verify-evals` para validar el 100% de integridad y ausencia de reward-hacking.

---

## 🎯 Protocolo de Ejecución y Traspaso entre Agentes

| Etapa | Agente Líder | Tareas a Cargo | Entregables Principales |
| :---: | :--- | :--- | :--- |
| **Etapa 1** | `02-software-architect` & `03-database-alembic` | FASE 1: DDL `tenant_*`, Alembic `0004`, DDD Kardex | Modelos SQLAlchemy, Migración `0004`, Primitivas FEFO |
| **Etapa 2** | `04-backend-senior-dev` | FASE 2: Servicios de Aplicación y Endpoints REST | Routers FastAPI, Guards RBAC, Transaccionalidad ACID |
| **Etapa 2** | `05-frontend-senior-dev` | FASE 3, 4, 5, 6, 7: UI React 19, Hooks, Modales | Vistas de Stock, Conteo Ciego, Historial y Modales |
| **Etapa 3** | `07-i18n-fx` & `08-environments-observability` | FASE 8: i18n 100%, Multi-Moneda FX, OpenTelemetry | `inventory.json` (es/en), Trazas OTel, Sentry |
| **Etapa 4** | `09-qa-test` & `10-security-redteam` | FASE 8: Testing 5D, SAST/DAST, Paridad Matemática | Tests Pytest + Vitest, Auditoría Kali, 0 Vulnerabilidades |
| **Etapa 4** | `11-git-arbiter` & `12-tech-writer` | Cierre: Merge Train, OpenSpec, Graphify & Archify | Smart Merge, Bóvedas OpenSpec, Grafo AST sincronizado |
| **Etapa 5** | `13-browser-e2e-playwright` | FASE 8: Certificación E2E en Navegador Real (Desacoplada) | Reporte Playwright HTML, Video y Traza de Navegación |

> **Nota Final:** Toda modificación de código debe ejecutarse previa consulta de Graphify (`python scripts/harness.py nav "<símbolo>"`) y concluir con la sincronización obligatoria `python scripts/harness.py sync-graph`.
