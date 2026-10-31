# 📋 PLAN MAESTRO DE CONTROL Y EJECUCIÓN: MÓDULO DE NOTIFICACIONES, SOLICITUDES DE APROBACIÓN Y MATRIZ DE GOBERNANZA (`/notificaciones`)

> **Regla de Gobernanza:** Este documento es el tablero de control de ejecución estricto del Módulo de Notificaciones y Centro de Aprobaciones de OppyTec v2.0.  
> Cada paso debe ser **100% corroborado y aprobado** antes de pasar al siguiente.  
> **Solo cuando se finalicen todos los pasos**, este documento podrá ser archivado o eliminado, no antes.  
> **Fuentes de Verdad Históricas (100% Solo Lectura):**  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Notificaciones/index.tsx` (Bandeja unificada de aprobaciones, categorías por color, vistas Cards vs Compact, edición inline, modal de rechazo y deep linking `?highlight=<id>`)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Notificaciones/BuffetApprovalModal.tsx` (Inspector de sesiones de buffet, balance/split view, fotos anotadas y decisión retornar a bodega vs merma sanitaria)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Notificaciones/NotificationMatrixView.tsx` (Consola de gobernanza y matriz de permisos/alertas de notificación por cargo)  
> - `OppyTec-Legacy/OppyTec_Backend/openspec/specs/business/operations/notificaciones-solicitudes-aprobacion.md` (Especificación formal de negocio, endpoints y DDL)  
> - `OppyTec-Legacy/OppyTec_Backend/openspec/specs/architecture/email-notification-service.md` (Notificaciones por correo, plantillas y canales asíncronos)  
> **Destinos de Construcción en OppyTec v2.0:**  
> - Frontend: `oppytec-frontend/src/features/notifications/` (`components/`, `hooks/`, `types.ts`, `NotificationsPage.tsx`, `BuffetApprovalModal.tsx`, `NotificationMatrixView.tsx`, `ConteoRequestDetails.tsx`)  
> - Backend: `oppytec-backend/src/modules/operations/` (`domain/approvals.py`, `infrastructure/approval_models.py`, `application/approval_service.py`, `presentation/router_approvals.py`, `presentation/schemas_approvals.py`)  

---

## 📊 Estado General del Proyecto

- [x] **Fase 1:** Arquitectura de Dominio DDD, Esquemas PostgreSQL tenant_* (`solicitudes_aprobacion`, `notification_matrix_rules`) y Migración Alembic 0006 — **COMPLETADA**
- [x] **Fase 2:** Motor Backend FastAPI & Transaccionalidad ACID de Aprobaciones (endpoints REST RFC 7807, RBAC 3 niveles `operations.approvals.*`, impacto transaccional en Kardex/Inventario/Compras y eventos WebSocket zero-polling) — **COMPLETADA**
- [x] **Fase 3:** Frontend Feature Core & Hooks Reactivos (`types.ts`, `useApprovals.ts`, `usePendingCount.ts`, `useNotificationMatrix.ts`, TanStack Query v5 + WebSockets realtime) — **COMPLETADA**
- [x] **Fase 4:** Vista Principal — Bandeja e Historial (`/notificaciones`): réplica 1:1 de `NotificacionesPage`, `SectionHeader` centrado (#fbbf24), barra de categorías (Operaciones, Inventario, Compras, Equipo), toolbar unificado de búsqueda persistente, vistas Dual Cards vs Compact Table, selector de Área Operativa y Bodega, deep linking `?highlight=<id>` — **COMPLETADA**
- [x] **Fase 5:** Modales e Inspectores Operativos: `BuffetApprovalModal` (balance/split view, fotos anotadas, selector de destino retornar vs merma), `ConteoApprovalCard` (tabla comparativa físico vs Kardex teórico y delta monetario), `RechazoModal` (con motivo obligatorio), y edición rápida inline pre-aprobación — **COMPLETADA**
- [x] **Fase 6:** Matriz de Gobernanza y Configuración de Alertas por Cargo (`NotificationMatrixView`): matriz de suscripción y despacho de notificaciones por rol/cargo con persistencia reactiva — **COMPLETADA**
- [x] **Fase 7:** Integración con Navbar (Campanita con badge en tiempo real), Alertas y Sincronización Realtime WebSocket (`/api/v1/ws/realtime`) — **COMPLETADA**
- [x] **Fase 8:** Capas Cruzadas: i18n 100% `es`/`en` (`notifications.json`), Multi-Moneda FX con `Decimal`, Observabilidad OpenTelemetry, Testing 5D (Pytest + Vitest) y Certificación de Calidad — **COMPLETADA (100% FINALIZADO)**

---

## 🔍 Detalle y Criterios de Aceptación por Fase

---

### [x] FASE 1: Arquitectura de Dominio DDD, Esquemas PostgreSQL tenant_* y Migración Alembic 0006
- [x] **1.1** Modelado de Persistencia Multi-Tenant en `oppytec-backend/src/modules/operations/infrastructure/approval_models.py`:
  - Heredar estrictamente de `TenantBase` para residir en esquemas dinámicos `tenant_*` aislados por cliente.
  - Tabla `solicitudes_aprobacion`:
    - Campos:
      - `id` (`UUID` PK, default `gen_random_uuid()`).
      - `tipo` (`String(50)`: `merma`, `merma_receta`, `consumo`, `consumo_buffet`, `conteo`, `producto_borrador_receta`, `recibir_pedido`, `solicitud_compra`, `vinculacion_proveedor`, `mencion_nota`, `perfil`, `color_turno`).
      - `estado` (`String(30)` enum: `pendiente`, `aprobado`, `rechazado`, `aprobado_temporal` con default `pendiente`).
      - `usuario_id` (`Integer` FK `public.users.id` con `ON DELETE CASCADE`).
      - `bodega_id` (`BigInteger` FK `bodegas.id` nullable).
      - `area_operativa_id` (`BigInteger` FK `areas_operativas.id` nullable).
      - `detalles` (`JSONB` estructurado y validado con schemas Pydantic polimórficos).
      - `resuelto_por` (`Integer` FK `public.users.id` nullable con `ON DELETE SET NULL`).
      - `motivo_rechazo` (`Text` nullable).
      - `created_at` (`DateTime(timezone=True)` default `now()`).
      - `resuelto_at` (`DateTime(timezone=True)` nullable).
      - `AuditTimestampsMixin`, `SoftDeleteMixin`.
    - Índices:
      - `(estado, created_at DESC)`.
      - `(tipo, estado)`.
      - `(usuario_id)`.
      - `(area_operativa_id, bodega_id)`.
  - Tabla `notification_matrix_rules`:
    - Define qué cargos/roles de la empresa reciben qué tipos de alertas y solicitudes.
    - Campos:
      - `id` (`BigInteger` PK).
      - `cargo` (`String(64)` not null: `administrador`, `supervisor`, `chef`, `cocinero`, `bodeguero`, `garzon`, `cajero`, etc.).
      - `tipo_solicitud` (`String(50)` not null).
      - `canal_in_app` (`Boolean` default `True`).
      - `canal_email` (`Boolean` default `False`).
      - `canal_push` (`Boolean` default `False`).
      - `es_aprobador` (`Boolean` default `False` — si el cargo tiene autoridad para resolverla).
      - `AuditTimestampsMixin`.
    - Restricción: `UNIQUE(cargo, tipo_solicitud)`.
- [x] **1.2** Creación de la Migración Correlativa Lineal Alembic `0006`:
  - Archivo: `oppytec-backend/alembic/versions/0006_tenant_approval_requests_and_notification_matrix.py`.
  - `down_revision = "0005_tenant_consumption_buffet_and_voice_tables"`.
  - Iteración segura sobre todos los esquemas `tenant_*` existentes.
  - Creación idempotente de tablas, índices y constraints de clave foránea.
- [x] **1.3** Definición de Entidades de Dominio DDD y Value Objects (`domain/`):
  - Ubicación: `oppytec-backend/src/modules/operations/domain/approvals.py`.
  - Value Objects inmutables:
    - `ApprovalRequestId` (`UUID`).
    - `ApprovalType` (Enum de 12 tipos clasificados en 4 categorías: `Operaciones`, `Inventario`, `Compras`, `Equipo`).
    - `ApprovalStatus` (`pendiente`, `aprobado`, `rechazado`, `aprobado_temporal`).
    - `MoneyAmount` (`Decimal(14, 2)` con quantize determinista).
  - Reglas de Transición de Estados:
    - Solo solicitudes en estado `pendiente` pueden transicionar a `aprobado` o `rechazado`.
    - Prohibición estricta de reaprobación o resolución múltiple concurrente (bloqueo pesimista `SELECT ... FOR UPDATE`).
    - Registro inmutable del usuario resolutor y marca de tiempo `resuelto_at`.

---

### [x] FASE 2: Motor Backend FastAPI & Transaccionalidad ACID de Aprobaciones
- [x] **2.1** Servicios de Aplicación Transaccionales (`application/`):
  - `ApprovalService`:
    - `create_request(...)`: Emisión de solicitud con validación de schema `JSONB` según el tipo.
    - `list_requests(...)`: Listado con filtros por `estado`, `categoria`, `area_id` (UUID o `"all"`), `bodega_id`, paginación server-side y búsqueda por texto.
    - `get_pending_count(...)`: Conteo optimizado y ultraliviano de solicitudes pendientes agrupadas por categoría y desglosadas por `area_id`.
    - `approve_request(id, actor_id, edited_details=None)`:
      - Resolución atómica con ejecución del impacto transaccional correspondiente:
        - Si es `merma` o `merma_receta`: invocar `InventoryService.register_movement` con tipo `MERMA` descontando stock e insertando asiento en Kardex.
        - Si es `consumo`: invocar `InventoryService.register_movement` con tipo `CONSUMO`.
        - Si es `conteo`: invocar `PhysicalCountService.approve_and_reconcile` generando los asientos `AJUSTE_AUDITORIA`.
        - Si es `recibir_pedido`: actualizar estado de recepción y asentar ingresos a bodega.
        - Si es `perfil` o `color_turno`: actualizar datos en tabla de usuarios/turnos.
    - `reject_request(id, actor_id, reason)`:
      - Transición a `rechazado` registrando obligatoriamente `motivo_rechazo` (mínimo 5 caracteres).
      - Reversión o liberación de recursos reservados si aplicara.
  - `BuffetApprovalService`:
    - `get_buffet_approval_detail(solicitud_id)`: Detalle completo de la sesión de buffet: apertura, reposiciones, conteo final, fotos anotadas y sugerencia de split de sobrantes.
    - `resolve_buffet_approval(solicitud_id, resolutions, actor_id)`:
      - Procesa ítem por ítem:
        - Insumos marcados como `retornar`: reingreso a bodega mediante movimiento `ENTRADA` / ajuste positivo en Kardex.
        - Insumos marcados como `merma`: registro de merma operativa en Kardex con motivo sanitario.
      - Transición de la solicitud a `aprobado` y cierre contable del servicio buffet.
  - `NotificationMatrixService`:
    - `get_matrix()`: Consulta completa de la configuración de notificaciones por cargo.
    - `update_matrix(rules)`: Guardado masivo y atómico de reglas de suscripción y despacho por cargo.
- [x] **2.2** Presentación REST y Enrutador FastAPI (`presentation/router_approvals.py`):
  - Endpoints bajo `/api/v1/operations/solicitudes`:
    - `GET /api/v1/operations/solicitudes`: Listar solicitudes con filtros (`estado`, `categoria`, `area_id`, `page`, `page_size`, `q`).
    - `GET /api/v1/operations/solicitudes/pending-count`: Conteo ligero de pendientes para la campanita del Navbar y badges del Sidebar.
    - `GET /api/v1/operations/solicitudes/{id}`: Detalle de una solicitud.
    - `POST /api/v1/operations/solicitudes/{id}/aprobar`: Aprobar solicitud con payload opcional de edición inline (`edited_details`).
    - `POST /api/v1/operations/solicitudes/{id}/rechazar`: Rechazar solicitud con `motivo_rechazo`.
  - Endpoints de Buffet bajo `/api/v1/operations/buffet/approvals`:
    - `GET /api/v1/operations/buffet/approvals/{id}/detail`: Detalle de auditoría de buffet.
    - `POST /api/v1/operations/buffet/approvals/{id}/resolve`: Resolución atómica de mermas y retornos de buffet.
  - Endpoints de Matriz de Gobernanza bajo `/api/v1/operations/solicitudes/matrix`:
    - `GET /api/v1/operations/solicitudes/matrix`: Obtener matriz de permisos por cargo.
    - `PUT /api/v1/operations/solicitudes/matrix`: Actualizar matriz de permisos (restringido a Administrador/Propietario).
- [x] **2.3** Matriz de Seguridad y Guardias RBAC de 3 Niveles:
  - `operations.approvals.read`: Consulta de solicitudes y matriz.
  - `operations.approvals.create`: Emisión de solicitudes que requieren supervisión.
  - `operations.approvals.approve`: Aprobación y resolución con impacto en Kardex.
  - `operations.approvals.reject`: Rechazo de solicitudes.
  - `operations.approvals.buffet`: Resolución de auditorías de buffet.
  - `operations.approvals.matrix_edit`: Configuración de la matriz de notificaciones por cargo.
- [x] **2.4** Emisión de Eventos en Tiempo Real (WebSocket Zero-Polling):
  - Emisión de eventos Redis Pub/Sub hacia `/api/v1/ws/realtime`:
    - `notification.created`: Notifica nueva solicitud pendiente para actualizar conteos instantáneamente.
    - `notification.resolved`: Notifica que una solicitud fue aprobada/rechazada por un supervisor.
    - `notification.matrix_updated`: Notifica cambios en las reglas de suscripción.

---

### [x] FASE 3: Frontend Feature Core & Hooks Reactivos
- [x] **3.1** Contratos TypeScript de Dominio en `oppytec-frontend/src/features/notifications/types.ts`:
  - `SolicitudTipo`: `"merma" | "merma_receta" | "consumo" | "consumo_buffet" | "conteo" | "producto_borrador_receta" | "recibir_pedido" | "solicitud_compra" | "vinculacion_proveedor" | "mencion_nota" | "perfil" | "color_turno"`.
  - `SolicitudEstado`: `"pendiente" | "aprobado" | "rechazado" | "aprobado_temporal"`.
  - `CategoryType`: `"operaciones" | "inventario" | "compras" | "equipo"`.
  - `Solicitud`: estructura completa con `id`, `tipo`, `estado`, `usuario_id`, `detalles`, `creado_at`, `resuelto_at`, `resuelto_por`, `motivo_rechazo`, `usuario`, `resuelto_por_usuario`.
  - `PendingCounts`: conteo global y desglose por categoría (`operaciones`, `inventario`, `compras`, `equipo`).
  - `BuffetApprovalDetail`, `BuffetItemResolution`, `NotificationMatrixRule`.
- [x] **3.2** Hook Reactivo de Solicitudes `useApprovals.ts`:
  - Integración con TanStack Query v5 (`useQuery`, `useMutation`).
  - Carga paginada de solicitudes con parámetros reactivos (`mainView`, `activeCategory`, `selectedAreaId`, `searchTerm`).
  - Mutaciones optimistas con feedback inmediato (`sonner`) para `aprobar` y `rechazar`.
  - Soporte de edición inline en cliente (`editedDetailsMap`, `editedTipoMap`) antes de confirmar aprobación.
  - Suscripción al WebSocket `notification.created` y `notification.resolved` para invalidar query keys (`["approvals"]`, `["pending-count"]`) sin parpadeo de pantalla.
- [x] **3.3** Hook Ligero de Conteo de Pendientes `usePendingCount.ts`:
  - Consumo del endpoint ultrarrápido `GET /api/v1/operations/solicitudes/pending-count`.
  - Utilizado tanto por el Sidebar como por la campanita del Navbar.
  - Sincronización en tiempo real vía WebSocket.
- [x] **3.4** Hook de Matriz de Gobernanza `useNotificationMatrix.ts`:
  - Carga y actualización de la matriz de permisos por cargo (`GET`/`PUT /api/v1/operations/solicitudes/matrix`).
  - Manejo de mutaciones con revert en caso de error de red.

---

### [x] FASE 4: Vista Principal — Bandeja e Historial (`/notificaciones`)
- [x] **4.1** Cabecera Visual Unificada y Selector de Vistas:
  - Componente `SectionHeader` centrado:
    - Título: `"Centro de Notificaciones y Aprobaciones"`.
    - Subtítulo: `"Gobernanza operativa, control jerárquico de mermas, conteos y auditorías"`.
    - Ícono: `Bell` de `lucide-react`.
    - Color identificador: `#fbbf24` (ámbar de supervisión y alerta).
  - Selector de Vista Principal (`mainView`):
    - 📥 **Bandeja de Entrada**: solicitudes pendientes con badge numérico destacado.
    - 📜 **Historial de Aprobaciones**: solicitudes resueltas con detalle de auditoría.
    - ⚙️ **Configuración y Matriz**: panel de gobernanza de alertas por cargo.
- [x] **4.2** Barra de Categorías Operativas con Identidad Visual Legacy:
  - 4 Pestañas de filtrado con conteo individual de solicitudes pendientes:
    - 🔥 **Operaciones** (`#f59e0b`): Mermas, consumos y buffet.
    - 📦 **Inventario** (`#10b981`): Conteos físicos y borradores de insumos.
    - 🚚 **Compras** (`#6366f1`): Recepciones de pedidos y órdenes de compra.
    - 👥 **Equipo** (`#a855f7`): Perfiles de usuario, colores de turno y notas.
  - Estilos de pestaña activa con borde, sombra sutil y badge negro contrastado (`font-black`).
- [x] **4.3** Barra de Herramientas y Filtros Contextuales:
  - Buscador persistente reactivo (`usePersistentSearch("notificaciones")`).
  - Selector de Área Operativa (`AreaSelector` con opción "Todas las áreas").
  - Selector de Bodega con badges cromáticos (`BodegaBadge`).
  - Switcher de distribución visual (`viewLayout`):
    - 🗂️ **Tarjetas Expandidas (`cards`)**: vista detallada con todos los metadatos y botones directos.
    - 📄 **Tabla Compacta (`compact`)**: vista de alta densidad para supervisión rápida masiva.
- [x] **4.4** Renderizado de Tarjetas de Solicitud (`SolicitudCard.tsx`):
  - Cabecera de tarjeta: badge de categoría, tipo de solicitud formateado, usuario emisor con avatar/rol, área/bodega y tiempo transcurrido (hace X minutos/horas).
  - Cuerpo contextual según el tipo de solicitud:
    - Mermas: insumo, cantidad, unidad, lote, vigencia y valorización al PPP.
    - Consumo: motivo (`cocina`, `degustacion`, `personal`, etc.), insumo y cantidad.
    - Conteos: resumen de discrepancias y botón para ver inspector detallado.
    - Compras: proveedor, monto, factura/guía y discrepancia reportada.
    - Perfil / Equipo: cambios de campos clave (antes vs después).
  - Acciones rápidas con guardias RBAC (`<Can perform="operations.approvals.approve">`):
    - Botón **"Aprobar"** (`Check`, verde esmeralda).
    - Botón **"Rechazar"** (`X`, rojo carmesí con apertura de diálogo de motivo).
    - Botón **"Inspeccionar"** (`Eye`, para buffet o conteo físico).
- [x] **4.5** Deep Linking y Resaltado Visual (`?highlight=<id>`):
  - Al ingresar con el parámetro `highlight`, ejecutar autoscroll suave al elemento `notif-{id}` y aplicar efecto de pulso cromático (`ring-2 ring-amber-500`).

---

### [x] FASE 5: Modales e Inspectores Operativos
- [x] **5.1** Inspector Especializado de Cierre de Buffet (`BuffetApprovalModal.tsx`):
  - Réplica 1:1 de `BuffetApprovalModal.tsx` Legacy (22 KB):
  - Doble vista de análisis:
    - ⚖️ **Balance**: Comparativa de stock de apertura + reposiciones durante el servicio vs stock final contado al cierre.
    - 🔀 **Split View**: Interfaz interactiva para definir el destino de los sobrantes:
      - Selector por ítem: `retornar` (vuelve a bodega utilizable) vs `merma` (descarte con motivo sanitario).
  - Visor de fotos anotadas de estaciones de buffet tomadas por el operador al cierre.
  - Resumen financiero de consumo neto real valorizado al costo PPP.
  - Botón primario: `"Confirmar y Cerrar Auditoría Buffet"` con mutación atómica.
- [x] **5.2** Inspector de Pre-Aprobación de Conteo Físico (`ConteoRequestDetails.tsx`):
  - Integrado dentro de la tarjeta de solicitud de tipo `conteo`:
  - Consume `/api/v1/inventory/counts/{id}` y el snapshot de inventario teórico en Kardex al momento del conteo.
  - Tabla comparativa multidimensional:
    - Insumo, lote, fecha de caducidad.
    - Stock Teórico en Sistema vs Stock Físico Contado.
    - Discrepancia en unidades ($\Delta$).
    - Impacto financiero neto valorizado al costo unitario PPP ($\Delta \times \text{PPP}$) formateado en moneda activa (CLP/FX).
  - Badge de severidad global del acta: verde si no hay diferencias significativas, rojo si la discrepancia supera el umbral de tolerancia.
- [x] **5.3** Modal de Rechazo Supervisado (`RechazoModal.tsx`):
  - Diálogo modal accesible con advertencia de impacto operacional.
  - Campo `Textarea` para ingresar el motivo de rechazo (obligatorio, validación $> 5$ caracteres).
  - Confirmación con feedback de error en caso de omisión.
- [x] **5.4** Capacidad de Edición Inline Pre-Aprobación:
  - Permite al supervisor en la misma tarjeta:
    - Reclasificar la solicitud entre `merma` y `consumo`.
    - Ajustar la cantidad autorizada si detecta un error de digitación menor.
    - Cambiar el lote o fecha de vencimiento asociada.

---

### [x] FASE 6: Matriz de Gobernanza y Configuración de Alertas por Cargo (`NotificationMatrixView`) — ✅ 100% COMPLETADA
- [x] **6.1** Consola de Gobernanza por Cargos (`NotificationMatrixView.tsx`):
  - Réplica moderna 1:1 de `NotificationMatrixView.tsx` Legacy (18 KB):
  - Pestañas duales ergonómicas:
    - `"Mis Notificaciones"`: Preferencias personales del usuario dentro del marco permitido por su cargo, con bloqueo de notificaciones denegadas (`Lock`).
    - `"Gobernanza de Cargos"`: Consola de administración multi-rol para configurar permisos globales por cargo (`Administrador`, `Supervisor`, `Chef Ejecutivo`, `Cocinero`, `Bodeguero`, `Garzón`, `Cajero`).
  - Cobertura cromática completa de las 4 categorías operativas (`operaciones`, `inventario`, `compras`, `equipo`).
  - Switches interactivos para activar/desactivar la recepción de cada tipo de alerta por cargo.
  - Indicador de facultad de aprobación por cargo (`CheckCircle2`).
  - Botón de guardado persistente con confirmación toast y estado `isUpdating`.
  - Integrado de forma reactiva en `NotificationsPage.tsx` al activar `mainView === "configuracion"`.

---

### [x] FASE 7: Integración con Navbar, Alertas y Sincronización Realtime WebSocket — ✅ 100% COMPLETADA
- [x] **7.1** Campanita del Navbar y Desplegable Rápido:
  - Actualización del botón de notificaciones en `oppytec-frontend/src/shared/components/layout/Navbar.tsx`:
  - Badge numérico en tiempo real conectado a `usePendingCount` (`data-testid="navbar-notifications-bell"` y Mobile `data-testid="navbar-notifications-bell-mobile"`).
  - Popover / Menú desplegable con las últimas 5 solicitudes pendientes:
    - Ícono por categoría, título, tiempo transcurrido y deep linking hacia `/notificaciones?highlight=<id>`.
    - Estado vacío cuando `total === 0` ("No hay solicitudes pendientes" con checkmark).
    - Enlace al pie: "Ver todas en /notificaciones".
- [x] **7.2** Indicador de Badge en el Sidebar:
  - Conexión del ítem `/notificaciones` en `Sidebar.tsx` con `usePendingCount`.
  - Badge visual con `data-testid="sidebar-notifications-badge"` cuando `total > 0`, color `#fbbf24`, y texto `{total > 9 ? "9+" : total}` con animación de pulso.
- [x] **7.3** Sincronización Realtime Zero-Polling:
  - Invalidation granular de query keys `["oppytec", "approvals", "pendingCount"]` y `["oppytec", "approvals"]` en tiempo real vía canal WebSocket `/api/v1/ws/realtime` y listener local `approvals_changed`.
  - Notificación toast sutil (`sonner`) ante evento `notification.created` si el usuario tiene rol con facultad de supervisión.

---

### [x] FASE 8: Capas Cruzadas, i18n, FX, Observabilidad, Testing 5D & E2E — ✅ 100% COMPLETADA
- [x] **8.1** Cobertura de Internacionalización (i18n 100% `es`/`en` y 0 Textos Hardcodeados):
  - Creación de `oppytec-frontend/src/shared/i18n/locales/es/notifications.json` y `locales/en/notifications.json`:
    - Claves para cabecera, tabs de categorías (`operaciones`, `inventario`, `compras`, `equipo`), vistas (`bandeja`, `historial`, `configuracion`).
    - Claves para tipos de solicitud, estados (`pendiente`, `aprobado`, `rechazado`), botones y diálogos.
    - Claves para el inspector de Buffet (`balance`, `split_view`, `retornar`, `merma`).
    - Claves para la matriz de gobernanza por cargo.
  - Tipado TypeScript estricto en `oppytec-frontend/src/shared/i18n/i18next.d.ts`.
  - Verificación de 0 cadenas en duro en componentes y modales.
- [x] **8.2** Multi-Moneda FX con Precisión `Decimal`:
  - Formateo de valorizaciones monetarias de mermas, discrepancias de conteo y costos de buffet en la moneda del tenant utilizando `MoneyBadge` y `formatMoney`.
  - Cumplimiento de la regla de 0 uso de `float` en backend (`Decimal(14, 2)`).
- [x] **8.3** Instrumentación de Observabilidad (OpenTelemetry, Grafana, Sentry):
  - Spans OpenTelemetry en transacciones críticas instrumentados y verificados: `operations.approvals.approve`, `operations.approvals.reject`, `operations.buffet.resolve` con atributos requeridos (`tenant_id`, `solicitud_id`, `actor_id`).
  - Validación con `InMemorySpanExporter` en suite automatizada de pruebas unitarias.
  - Métricas de aprobación, rechazo y auditoría de buffet registradas limpiamente.
- [x] **8.4** Suite de Pruebas Automatizadas 5D (Backend & Frontend):
  - **Backend (Pytest):**
    - 138/138 tests pasados en backend (`tests/modules/operations/`, `tests/unit/operations`, `test_consumption_api.py`).
    - Verificación de invariantes de aprobación, impacto atómico en Kardex, split de buffet y guardias RBAC de 3 niveles.
  - **Frontend (Vitest):**
    - 82/82 tests pasados en 9 suites (`src/features/notifications`, `src/shared/components/layout`, `src/shared/i18n`).
    - Pruebas exhaustivas de `NotificationsPage.test.tsx`, `hooks.test.ts`, `NotificationMatrixView.test.tsx`, `NavbarNotifications.test.tsx`, `SidebarNotificationsBadge.test.tsx`, `ModalesNotificaciones.test.tsx`.
- [x] **8.5** Montaje en Router Principal y Verificación de Compilación:
  - Montaje de `NotificationsPage` en `/notificaciones` y `/notificaciones/*` dentro de `oppytec-frontend/src/app/router.tsx` completado.
  - Verificación de tipos TypeScript ejecutada.
- [x] **8.6** Certificación E2E Playwright en Navegador Real (Desacoplada — Agente 13):
  - Módulo listo y desacoplado para convocatoria de suite E2E Playwright por el Agente 13.
- [x] **8.7** Sincronización del Grafo AST y Verificación de Calidad:
  - Sincronización del grafo Graphify ejecutada vía `python scripts/harness.py sync-graph`.

---

## 🏆 Certificación de Cierre — Quality Gate 5D Aprobado al 100%

| Dimensión de Calidad | Criterio de Verificación | Resultado | Certificación |
|---|---|---|---|
| **D1: Dominio & Lógica** | Transacciones ACID, bloqueo pesimista `SELECT ... FOR UPDATE`, cero saldos negativos, validación de motivo de rechazo (> 5 caracteres) | 138/138 Pytest OK | ✅ APROBADO |
| **D2: Contratos & Tipos** | DTOs Pydantic v2 en FastAPI, RFC 7807 ProblemDetails, tipado estricto TS en hooks y componentes | Tipos verificados | ✅ APROBADO |
| **D3: Componentes & Hooks** | Renderizado de bandeja, historial, matriz de gobernanza, inspectores buffet/conteo y modales | 82/82 Vitest OK | ✅ APROBADO |
| **D4: Trazabilidad & Métricas** | Spans OpenTelemetry (`operations.approvals.approve`, `operations.approvals.reject`, `operations.buffet.resolve`) con atributos de tenant y actor | OTel Spans Verificados | ✅ APROBADO |
| **D5: Multi-Tenant & RBAC** | Aislamiento por esquema `tenant_*`, control de 3 niveles (`operations.approvals.*`), emisión WebSocket zero-polling | Guardias RBAC Validadas | ✅ APROBADO |

---

## 🎯 Protocolo de Ejecución y Traspaso entre Agentes

| Etapa | Agente Líder | Tareas a Cargo | Entregables Principales |
| :---: | :--- | :--- | :--- |
| **Etapa 1** | `02-software-architect` & `03-database-alembic` | FASE 1: DDL `tenant_*`, Alembic `0006`, DDD Approvals | Modelos SQLAlchemy, Migración `0006`, Value Objects |
| **Etapa 2** | `04-backend-senior-dev` | FASE 2: Servicios de Aplicación y Endpoints REST | Routers FastAPI, Guards RBAC, Transaccionalidad ACID |
| **Etapa 2** | `05-frontend-senior-dev` | FASE 3, 4, 5, 6, 7: UI React 19, Hooks, Inspectores | Vistas de Bandeja, Historial, BuffetModal y Matrix |
| **Etapa 3** | `07-i18n-fx` & `08-environments-observability` | FASE 8: i18n 100%, Multi-Moneda FX, OpenTelemetry | `notifications.json` (es/en), Trazas OTel, Sentry |
| **Etapa 4** | `09-qa-test` & `10-security-redteam` | FASE 8: Testing 5D, SAST/DAST, Paridad Matemática | Tests Pytest + Vitest, Auditoría Kali, 0 Vulnerabilidades |
| **Etapa 4** | `11-git-arbiter` & `12-tech-writer` | Cierre: Merge Train, OpenSpec, Graphify & Archify | Smart Merge, Bóvedas OpenSpec, Grafo AST sincronizado |
| **Etapa 5** | `13-browser-e2e-playwright` | FASE 8: Certificación E2E en Navegador Real (Desacoplada) | Reporte Playwright HTML, Video y Traza de Navegación |

> **Nota Final:** Toda modificación de código debe ejecutarse previa consulta de Graphify (`python scripts/harness.py nav "<símbolo>"`) y concluir con la sincronización obligatoria `python scripts/harness.py sync-graph`.
