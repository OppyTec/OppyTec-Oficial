# 📋 PLAN MAESTRO DE CONTROL Y EJECUCIÓN: MÓDULO DE ALERTAS DE STOCK CRÍTICO, VENCIMIENTOS Y FEFO (`/alertas`)

> **Regla de Gobernanza:** Este documento es el tablero de control de ejecución estricto del Módulo de Alertas de OppyTec v2.0.  
> Cada paso debe ser **100% corroborado y aprobado** antes de pasar al siguiente.  
> **Solo cuando se finalicen todos los pasos**, este documento podrá ser archivado o eliminado, no antes.  
> **Fuentes de Verdad Históricas (100% Solo Lectura):**  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Alertas/index.tsx` (Vista principal, toolbar unificado, modo tarjetas, modo listado, carrito morado y badges de estado)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Alertas/useAlertas.ts` (Lógica histórica de extracción, cálculo de severidad y notificaciones inteligentes)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Alertas/types.ts` (Contratos de `ProductoAnalitico` y `SmartNotification`)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Alertas/StockCriticoTable.tsx` (Tabla tabular de existencias bajo mínimo con barras cromáticas de salud)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Alertas/VencimientosCard.tsx` (Tarjetas de productos vencidos y próximos a caducar con tiempo relativo)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/components/Sidebar.tsx` (Sincronización del badge reactivo en el ítem `/alertas`, pulsación destructiva `animate-pulse` y persistencia en `localStorage`)  
> **Destinos de Construcción en OppyTec v2.0:**  
> - Frontend: `oppytec-frontend/src/features/inventory/alerts/` (`AlertasPage.tsx`, `StockCriticoTable.tsx`, `VencimientosCard.tsx`, `hooks/useAlertas.ts`, `hooks/useAlertBadge.ts`, `types.ts`)  
> - Backend: `oppytec-backend/src/modules/inventory/` (`domain/alerts.py`, `application/alerts_service.py`, `presentation/router_alerts.py`, `presentation/schemas_alerts.py`)  

---

## 📊 Estado General del Proyecto

- [x] **Fase 1:** Arquitectura de Dominio DDD y Agregaciones en Backend (cálculo en PostgreSQL de stock crítico, vencidos y próximos a vencer en <20ms, eliminando la deuda técnica de snapshot en el cliente de Legacy) — **COMPLETADA (100% Agente 02)**
- [x] **Fase 2:** Presentación REST FastAPI y WebSockets (`GET /api/v1/inventory/alerts`, RFC 7807, RBAC 3 niveles `inventory.alerts.read`, eventos WS en tiempo real) — **COMPLETADA (100% Agente 04)**
- [x] **Fase 3:** Frontend Feature Core & Hooks Reactivos (`types.ts`, `mockData.ts`, `useAlertas.ts`, `useAlertBadge.ts`, TanStack Query v5 + WebSockets realtime) — **COMPLETADA (100% Agente 05)**
- [x] **Fase 4:** Vista Principal `/alertas` (`AlertasPage.tsx`): `SectionHeader` centrado en rojo/coral (#ef4444), Toolbar Unificado con selectores de área/bodega, dropdown de filtro de alertas y toggle de vistas (`cards` vs `list`) — **COMPLETADA (100% Agente 05)**
- [x] **Fase 5:** Renderizado Paritario 1:1 de Vistas: Modo Tarjetas (`cards`) con barras de salud de stock, ratios porcentuales, carrito morado de compras con animación y toast, tarjetas de vencidos con tiempo relativo y botón de merma, tarjetas de próximos a vencer; y Modo Listado (`list`) con `StockCriticoTable` y `VencimientosCard` — **COMPLETADA (100% Agente 05)**
- [x] **Fase 6:** Flujos Operativos y Paginación: Carrito de compras persistente (`gestion_purchase_cart`), navegación hacia `/gestion?tab=mermas`, y control `TablePagination` integrado — **COMPLETADA (100% Agente 05)**
- [x] **Fase 7:** Integración con el Sidebar y Badge Reactivo: sincronización del badge numérico en `/alertas` en el Sidebar — **COMPLETADA (100% Agente 05)**
- [x] **Fase 8:** Capas Cruzadas: i18n 100% `es`/`en` (`alerts.json`), Multi-Moneda FX con precisión Decimal, Observabilidad OpenTelemetry, Testing 5D (Pytest + Vitest) y sincronización con Graphify/Archify — **COMPLETADA**

---

## 🔍 Detalle y Criterios de Aceptación por Fase

---

### [x] FASE 1: Arquitectura de Dominio DDD y Agregaciones en Backend — Eliminación de Deuda Técnica Legacy
- [x] **1.1** Erradicación de la Deuda Técnica del Snapshot en el Cliente:
  - *Diagnóstico Histórico Legacy:* En `OppyTec-Legacy/OppyTec_Frontend/src/pages/Alertas/useAlertas.ts`, el frontend descargaba en cada carga tres endpoints completos (`/inventory/products`, `/inventory/history`, `/operations/events/alerts`) y recalculaba en el hilo principal del navegador mediante `buildInventorySnapshot(...)` el saldo histórico de cada insumo. Esto generaba congelamiento de UI en catálogos grandes, uso excesivo de datos móviles y un retardo de 3 a 8 segundos.
  - *Solución Arquitectónica v2.0:* El cálculo analítico de saldos y alertas se ejecuta en el motor de base de datos PostgreSQL en esquemas `tenant_*` mediante consultas agregadas indexadas con tiempo de respuesta inferior a **20 milisegundos**, devolviendo un payload directo y liviano.
- [x] **1.2** Modelado de Consultas Agregadas en PostgreSQL (`infrastructure/`):
  - Consulta atómica que evalúa en una sola pasada:
    1. **Stock Crítico / Quiebre:**
       - Condición: `stock_items.stock_actual <= stock_items.stock_minimo` (o `stock_actual <= 0` si `stock_minimo = 0`).
       - Clasificación: `agotado` (`stock_actual <= 0`) vs `bajo_minimo` (`stock_actual > 0 AND stock_actual <= stock_minimo`).
       - Ratio de salud de existencias: $(\text{stock\_actual} / \text{stock\_minimo}) \times 100$.
    2. **Productos Vencidos:**
       - Condición: lotes en Kardex o registros de lotes activos donde `fecha_vencimiento < CURRENT_DATE` y saldo disponible $> 0$.
       - Agregación de `cantidad_vencida` agrupada por producto y bodega.
    3. **Próximos a Vencer (Ventana de Urgencia FEFO):**
       - Condición: lotes donde `CURRENT_DATE <= fecha_vencimiento <= CURRENT_DATE + INTERVAL '30 days'` (o umbral configurado por tenant) y saldo disponible $> 0$.
       - Identificación del lote más crítico con su fecha exacta y días restantes para caducar.
  - Optimización de índices compuestos existentes: `(bodega_id, producto_id)`, `(fecha_vencimiento_lote)` en `kardex_movements` y `stock_items`.
- [x] **1.3** Entidades de Dominio DDD y Value Objects (`domain/alerts.py`):
  - Ubicación: `oppytec-backend/src/modules/inventory/domain/alerts.py`.
  - Value Objects inmutables:
    - `AlertSeverity`: enum (`CRITICAL`, `WARNING`, `INFO`).
    - `StockHealthRatio`: valor porcentual validado con clamp entre 0% y 100% para renderizado de barras cromáticas.
    - `ExpiryUrgency`: cálculo de días restantes o días transcurridos desde el vencimiento.
  - Entidades de Dominio:
    - `CriticalStockAlert`: `producto_id`, `bodega_id`, `stock_actual`, `stock_minimo`, `unidad_medida`, `ratio`, `is_depleted`.
    - `ExpiredLotAlert`: `producto_id`, `bodega_id`, `lote_codigo`, `fecha_vencimiento`, `cantidad_vencida`, `dias_vencido`, `costo_ppp`.
    - `UpcomingExpiryAlert`: `producto_id`, `bodega_id`, `lote_codigo`, `fecha_vencimiento`, `cantidad_en_riesgo`, `dias_restantes`, `costo_ppp`.
    - `AlertsConsolidatedSummary`: agregado raíz con contadores de alertas activas (`total_count`, `critical_count`, `expired_count`, `upcoming_count`, `has_critical`).

---

### [x] FASE 2: Presentación REST FastAPI y WebSockets en Tiempo Real
- [x] **2.1** Servicio de Aplicación (`application/alerts_service.py`):
  - Implementación de `InventoryAlertsService`:
    - `get_alerts(tenant_id: str, bodega_ids: list[int] | None, area_operativa_id: int | None, filter_type: str | None) -> AlertsPayload`.
    - `get_badge_summary(tenant_id: str) -> AlertBadgeSummary`: consulta ultraliviana para el Sidebar y la cabecera global que responde en $< 5\text{ms}$.
  - Manejo de caché en memoria / Redis con invalidación orientada a eventos.
- [x] **2.2** Enrutador FastAPI y Endpoints REST RFC 7807 (`presentation/router_alerts.py` / `router.py`):
  - Respuestas estandarizadas con RFC 7807 `ProblemDetails` ante fallos.
  - **`GET /api/v1/inventory/alerts`**:
    - Parámetros query:
      - `bodega_id`: entero opcional (o repetible para multi-bodega).
      - `area_operativa_id`: entero opcional.
      - `tipo`: enum opcional (`all`, `stock`, `upcoming`, `expired`).
    - Retorna `AlertsResponseSchema`:
      - `summary`: total general, quiebres críticos, vencidos, próximos y flag `has_critical`.
      - `critical_stock`: lista de insumos bajo mínimo o agotados.
      - `expired_products`: lista de lotes caducados con saldo.
      - `upcoming_expiries`: lista de lotes por caducar dentro del umbral FEFO.
  - **`GET /api/v1/inventory/alerts/badge`**:
    - Endpoint ultraliviano consumido por el Sidebar:
      - `{ "total_count": int, "has_critical": bool, "critical_stock_count": int, "expired_count": int, "upcoming_count": int }`.
- [x] **2.3** Matriz de Seguridad y Guardias RBAC de 3 Niveles:
  - Guardias requeridos:
    - `RequireTenantPermission("inventory.alerts.read")` sobre ambos endpoints.
    - Validación de aislamiento multi-tenant: prohibido consultar datos de esquemas ajenos (`CrossTenantAccessError`).
- [x] **2.4** Notificaciones WebSocket Zero-Polling (`/api/v1/ws/realtime`):
  - Emisión de evento Redis Pub/Sub:
    - Evento: `inventory.alerts.changed`.
    - Disparadores: toda transacción de Kardex (`register_movement`, `transfer_stock_bulk`, `finalize_count_session`, `report_merma`) que altere existencias de productos en estado crítico o modifique lotes con caducidad.
    - Notifica a los clientes conectados para la invalidación quirúrgica inmediata de las consultas `["inventory", "alerts"]` y `["inventory", "alerts", "badge"]` en TanStack Query v5 sin incurrir en polling HTTP (`refetchInterval`).

---

### [x] FASE 3: Frontend Feature Core & Hooks Reactivos
- [x] **3.1** Contratos TypeScript en `oppytec-frontend/src/features/inventory/alerts/types.ts`:
  - `AlertProductItem`: modelo unificado con paridad con `ProductoAnalitico` histórico:
    - `id`: identificador compuesto `${producto_id}::${bodega_id}`.
    - `producto_id`: entero / string identificador.
    - `nombre`: nombre comercial del producto.
    - `unidad`: unidad de medida oficial (`un`, `kg`, `lt`, etc.).
    - `stock_minimo`: número decimal de existencias mínimas.
    - `cantidad`: saldo actual disponible.
    - `cantidad_vencida`: volumen total caducado.
    - `fecha_vencimiento`: fecha ISO del lote más crítico.
    - `bodega_id`: identificador de la bodega asignada.
    - `bodega_nombre`: nombre del almacén.
    - `bodega_color`: color institucional de la bodega.
    - `bodega_icono`: icono asignado a la bodega.
    - `costo_promedio`: costo unitario PPP para valorización de compra o pérdida.
  - `AlertsSummary`: `{ total_count: number; has_critical: boolean; critical_count: number; expired_count: number; upcoming_count: number }`.
  - `AlertFilterType`: `'all' | 'stock' | 'upcoming' | 'expired'`.
  - `AlertViewMode`: `'cards' | 'list'`.
  - `CartPurchaseItem`: contrato del ítem añadido a la orden de compra (`gestion_purchase_cart`).
- [x] **3.2** Hook Reactivo Principal `useAlertas.ts`:
  - Integración con TanStack Query v5 (`useQuery`) consumiendo `GET /api/v1/inventory/alerts`.
  - Conexión al contexto reactivo de `AreaSelector` (`useAreaOperativa`) y `BodegaSelector` (`useBodega`).
  - Fallback elegante a datos locales de contingencia ante desconexión o arranque en frío.
  - Suscripción al bus WebSocket en tiempo real (`inventory.alerts.changed` e `inventory.stock.updated`) con invalidación quirúrgica de cache.
  - Retorno estructurado:
    - `data`: lista analítica completa de insumos (`AlertProductItem[]` / `ProductoAnalitico`).
    - `stockCritico`: insumos filtrados bajo mínimo o agotados.
    - `vencidos`: insumos con existencias caducadas.
    - `vencimientosProximos`: insumos con vencimientos futuros dentro de la ventana de advertencia.
    - `summary`: totalizadores numéricos y flags de criticidad.
    - `loading`: indicador booleano de carga.
    - `refresh`: función de re-sincronización manual.
- [x] **3.3** Hook Desacoplado para el Sidebar `useAlertBadge.ts`:
  - Hook liviano especializado que consume `GET /api/v1/inventory/alerts/badge` o se alimenta del cache global (`staleTime: 60_000`).
  - Sincroniza atómicamente las claves de `localStorage`:
    - `notif_total_count`: conteo total de alertas activas.
    - `notif_has_critical`: booleano (`true` si hay quiebres de stock o productos vencidos).
  - Emisión del evento `window.dispatchEvent(new Event("notif-updated"))` para compatibilidad transparente con componentes heredados y el Sidebar.
  - Actualización reactiva instantánea por WebSocket push y eventos `notif-updated`/`storage`.

---

### [x] FASE 4: Vista Principal `/alertas` (`AlertasPage.tsx`)
- [x] **4.1** Cabecera Visual Canónica y ADN OppyTec:
  - Componente `SectionHeader` centrado:
    - Título: `"Alertas"`.
    - Subtítulo: `"Estado de Stock y Vencimientos del Sistema"`.
    - Ícono: `AlertTriangle` de `lucide-react`.
    - Color identificador: `#ef4444` (rojo coral institucional de alertas).
- [x] **4.2** Toolbar Unificado de Control (`AlertasToolbar`):
  - Tarjeta contenedora con efecto cristal y layout animado con `framer-motion`:
    - `layoutId="app-toolbar-outer-card"` y `layoutId="app-toolbar-inner-bar"`.
  - Distribución de columnas en escritorio (`hidden lg:block`):
    - **Columna Izquierda (4 columnas):** `AreaSelector` para filtrar áreas de trabajo y `BodegaSelector` con soporte multi-bodega (`all` o selección individual).
    - **Columna Central (5 columnas):** Menú desplegable `DropdownMenu` con ícono `Filter` y botón con texto dinámico:
      - `"Todas las alertas"`, `"Stock Crítico"`, `"Próximos a vencer"`, `"Productos Vencidos"`.
    - **Columna Derecha (3 columnas):** Toggle de Vistas con micro-interacción animada:
      - Botón *"Tarjetas"* (`LayoutGrid`) vs Botón *"Listado"* (`LayoutList`).
      - Persistencia inmediata de la preferencia en `localStorage.getItem("alerts_view_mode")`.
- [x] **4.3** Toolbar Adaptativo Mobile-First:
  - Versión táctil para smartphones y tablets (`block lg:hidden`):
    - Selectores de área y bodega en cuadrícula de 2 columnas.
    - Dropdown de filtro full-width y toggle de vistas contiguo con touch targets $\ge 44\text{px}$.
- [x] **4.4** Estado de Carga y Transiciones:
  - Spinner institucional con texto en mayúsculas `CARGANDO ALERTAS...` en color `text-muted-foreground`.
  - Transición fluida con `AnimatePresence mode="popLayout"` entre filtros y vistas.

---

### [x] FASE 5: Renderizado Paritario 1:1 de Vistas (Tarjetas vs Listado)
- [x] **5.1** Modo Tarjetas (`viewMode === "cards"`):
  - **Sección 1: Stock Crítico:**
    - Encabezado de sección con badge píldora: `bg-red-500/10 text-red-500 border border-red-500/20` con conteo exacto y línea divisoria degradada.
    - Estado vacío elegante: *"Todo bajo control. No hay productos en stock crítico."*
    - Cuadrícula responsiva: 1 columna en móvil, 2 en tablet, 3 en desktop, 4 en pantallas amplias (`xl:grid-cols-4`).
    - Tarjeta de insumo (`h-48`, esquinas redondeadas `rounded-3xl`, `bg-card/60 backdrop-blur-sm`, hover scale `1.02` y sombra profunda):
      - Barra indicadora inferior fija: `bg-destructive`.
      - Título del producto con tooltip y corte a 2 líneas (`line-clamp-2 h-12`).
      - Barra cromática de salud de existencias:
        - Ratio porcentual calculado contra el stock mínimo: $\text{ratio} = (\text{cantidad} / \text{stock\_minimo}) \times 100$.
        - Etiqueta de estado: `"Agotado"` (rojo destructivo) si cantidad $\le 0$, `"Bajo Mínimo"` (naranja) en caso contrario.
        - Barra de progreso rellena con clamp visual mínimo del 5%: color `bg-destructive` si $\le 0$, `bg-orange-500` si $\le 50\%$, `bg-amber-500` si $> 50\%$.
      - Franja inferior integrada (`bg-secondary/10 p-2 rounded-2xl`):
        - `BodegaBadge`: nombre, color e icono de la bodega.
        - Bloque de Stock Actual: número prominente y unidad de medida.
        - Bloque de Stock Mínimo: umbral referencial en color muted.
        - Botón Carrito de Compra Morado:
          - Color base: `bg-purple-500/10 text-purple-600 hover:bg-purple-500/20`.
          - Animación al clickear: transición a `bg-purple-600 text-white scale-110 shadow-md shadow-purple-500/40` durante 400ms.
          - Acción: inserción en `gestion_purchase_cart`, despacho de evento `cart-updated` y toast Sonner de confirmación.
  - **Sección 2: Productos Vencidos:**
    - Encabezado de sección con badge píldora: `bg-red-600/10 text-red-600 border border-red-600/20`.
    - Tarjeta de lote caducado (`border-red-500/20`, barra inferior `bg-red-600`):
      - Fecha de vencimiento formateada (`dd-MM-yyyy`) en color destructivo.
      - Tiempo relativo transcurrido (`formatDistanceToNow` en español/inglés vía i18n, ej: *"hace 3 días"*).
      - Stock afectado en unidades o kg.
      - `BodegaBadge` institucional.
      - Botón de acción rápida `ArrowRight`: redirección a `/gestion?tab=mermas` con tooltip *"Reportar Merma"*.
  - **Sección 3: Próximos a Vencer:**
    - Encabezado de sección con badge píldora: `bg-amber-500/10 text-amber-500 border border-amber-500/20`.
    - Tarjeta de lote próximo (`border-amber-500/20`, barra inferior `bg-amber-500`):
      - Fecha de caducidad en color ámbar.
      - Tiempo relativo restante (ej: *"en 5 días"*).
      - Stock total comprometido.
      - `BodegaBadge` institucional.
      - Botón `ArrowRight` que navega hacia la gestión de consumo/mermas.
- [x] **5.2** Modo Listado (`viewMode === "list"`):
  - **Componente `StockCriticoTable.tsx`:**
    - Encabezado de tabla con ícono `AlertCircle` rojo y badge destructivo con el conteo de alertas activas.
    - Columnas técnicas:
      1. *Producto:* Nombre comercial con `BodegaBadge` escalado al 75%.
      2. *Estado / Salud:* Barra cromática horizontal animada, etiqueta de estado (`Agotado` o `Bajo Mínimo`) y ratio porcentual.
      3. *Actual:* Cantidad física disponible alineada a la derecha con unidad de medida.
      4. *Mínimo:* Umbral mínimo registrado.
      5. *Acción:* Botón carrito de compras morado con micro-animación.
  - **Componente `VencimientosCard.tsx`:**
    - Distribución en 2 columnas paralelas en desktop (`grid md:grid-cols-2 gap-6`) o individual según el filtro seleccionado.
    - Cabecera de tarjeta: ícono `AlertTriangle` para vencidos o `Clock` para próximos a vencer, acompañado del contador en badge.
    - Lista vertical con scroll interno optimizado (`max-h-[300px] scrollbar-thin`):
      - Fila compacta con nombre del producto, fecha exacta, tiempo relativo y badge de stock afectado.
    - Banner de recomendación operativa en tarjetas de vencidos:  
      `⚠️ Se recomienda realizar una baja de inventario (Merma) para estos productos.`

---

### [x] FASE 6: Flujos Operativos, Carrito de Compras y Paginación
- [x] **6.1** Carrito de Compras Persistente (`gestion_purchase_cart`):
  - Algoritmo de persistencia reactiva en `addToCart`:
    - Extracción limpia de IDs (manejando identificadores simples y compuestos `${producto_id}::${bodega_id}`).
    - Lectura segura de `localStorage.getItem("gestion_purchase_cart")`.
    - Si el ítem ya existe para esa bodega: incrementa la cantidad en `+1`.
    - Si es nuevo: registra `{ producto_id, bodega_id, bodega_nombre, nombre, cantidad: 1, precio: costo_ppp, unidad }`.
    - Guarda en `localStorage` y dispara el evento `window.dispatchEvent(new Event("cart-updated"))`.
    - Emite toast Sonner de confirmación: `"{Nombre} ({Bodega}) agregado al carrito de compras"`.
- [x] **6.2** Navegación Operativa hacia Mermas:
  - Los botones de acción rápida en tarjetas de vencidos invocan `navigate("/gestion?tab=mermas")` para facilitar la inmediata tramitación de la merma operativa sin fricción.
- [x] **6.3** Control de Paginación Integrado (`TablePagination`):
  - Integración del componente canónico `TablePagination`:
    - Opciones de tamaño de página: 10, 30, 50, 100 elementos por página.
    - Persistencia de `alerts_page_size` en `localStorage`.
    - Reseteo automático a la página 1 al cambiar el tipo de filtro o la modalidad de vista (`cards` / `list`).
    - Cálculo dinámico de `totalItems` según el filtro activo.

---

### [x] FASE 7: Integración con el Sidebar y Badge Reactivo
- [x] **7.1** Sincronización del Badge en el Menú Principal:
  - En `LEGACY_MENU_ITEMS` de `oppytec-frontend/src/shared/components/layout/Sidebar.tsx`:
    - Entrada `/alertas` con `icon: AlertTriangle`, `color: "#ef4444"`, `rgb: "239,68,68"`, `hasBadge: true`.
  - Renderizado del badge numérico flotante sobre el icono de Alertas:
    - Conexión reactiva con el hook `useAlertBadge()` de `@/features/inventory/alerts/hooks/useAlertBadge`.
    - Si `hasCritical` es verdadero: estilo `bg-red-500 text-white animate-pulse shadow-sm shadow-red-500/50` (alerta roja pulsante para quiebres y vencimientos).
    - Si no hay elementos críticos (solo próximos a vencer): estilo de aviso preventivo `bg-amber-500 text-white shadow-sm shadow-amber-500/30`.
    - Límite visual de desbordamiento: muestra `"9+"` si el conteo supera 9, manteniendo el diseño compacto.
    - Soporte visual paritario tanto en el Sidebar expandido como en modo colapsado (`isCollapsed`).
- [x] **7.2** Reactividad Multi-Pestaña y Zero-Polling:
  - El Sidebar y su hook `useAlertBadge` escuchan activamente los eventos `storage` y `notif-updated`:
    - Al emitirse cambios desde `useAlertas` o modificaciones en `localStorage`, el badge del Sidebar se actualiza en el mismo milisegundo en todas las pestañas abiertas sin polling HTTP (`setInterval` prohibido).
    - Sincronización con WebSocket push `inventory.alerts.changed` e invalidación del cache TanStack Query v5.
- [x] **7.3** Cobertura de Pruebas Unitarias y de Integración:
  - Creación de la suite `oppytec-frontend/src/shared/components/layout/__tests__/SidebarAlertsBadge.test.tsx`:
    - 10/10 pruebas aprobadas (visibilidad condicional, truncamiento `"9+"`, criticidad pulsante, aviso preventivo ámbar, eventos de ventana y colapso).
    - 89/89 pruebas aprobadas en el conjunto completo de layout y alertas.

---

### [x] FASE 8: Capas Cruzadas, i18n, FX, Observabilidad, Testing 5D & E2E — COMPLETADA (100% Escuadrón)
- [x] **8.1** Cobertura de Internacionalización (i18n 100% `es`/`en` y 0 Textos Hardcodeados):
  - Creación del namespace dedicado `oppytec-frontend/src/shared/i18n/locales/es/alerts.json` y `locales/en/alerts.json`:
    - Claves para títulos, subtítulos, selectores de área/bodega y filtros de alertas.
    - Claves para estados de tarjetas: `out_of_stock`, `low_stock`, `expired`, `upcoming`, `health_ratio`, `affected_stock`.
    - Claves para botones de acción: agregar al carrito, reportar merma, gestionar.
    - Claves para notificaciones toast y mensajes de estado vacío.
  - Tipado TypeScript de todas las claves en `oppytec-frontend/src/shared/i18n/i18next.d.ts` (20 namespaces tipados).
  - Verificación estricta de 0 textos hardcodeados en JSX o atributos de accesibilidad (`aria-label`, `title`).
  - **Certificación Agente 07 (i18n & FX):** 69 claves 1:1 en `es`/`en`, 20 namespaces tipados, 0 cadenas hardcodeadas, 88/88 tests pasando al 100%.
- [x] **8.2** Multi-Moneda FX con Precisión `Decimal`:
  - Los costos unitarios PPP y montos valorizados en el carrito de compras y las listas de mermas se formatean mediante `MoneyBadge` y `formatMoney`.
  - Prohibición estricta de variables de coma flotante (`float`/`number`) para montos financieros; uso de `Decimal` en backend y `string` tipado en frontend.
  - Validación de paridad de divisas y precisión decimal garantizada al 100% (0% floats).
- [x] **8.3** Instrumentación de Observabilidad (OpenTelemetry, Grafana, Sentry):
  - Traza de span OpenTelemetry: `inventory.alerts.query` registrando latencia de consulta en Postgres y cardinalidad de quiebres; spans en fetch, badge y broadcast WebSocket.
  - Registro de excepciones en Sentry/GlitchTip contextualizadas con `tenant_id` y `bodega_id`.
  - Métricas de salud: ratio de quiebres de stock sobre catálogo activo y porcentaje de mermas por vencimiento.
  - PII scrubbing exhaustivo en logs y payloads de telemetría.
  - **Certificación Agente 08 (Observabilidad):** OpenTelemetry spans en alerts fetch/badge/broadcast, PII scrubbing validado, 17/17 tests de observabilidad pasando, 97 tests de backend inventario total en verde.
- [x] **8.4** Suite de Pruebas Automatizadas 5D:
  - **Backend (Pytest):**
    - `test_alerts_calculation_invariants.py`: verificar que la consulta SQL calcule con precisión matemática los quiebres de stock y lotes vencidos en $< 20\text{ms}$.
    - `test_alerts_fefo_urgency.py`: validar clasificación por fecha de caducidad y exclusión de lotes sin existencia.
    - `test_alerts_rbac_and_isolation.py`: verificar denegación 403 a usuarios sin `inventory.alerts.read` y aislamiento estricto cross-tenant.
    - `test_13_alerts_security_and_rbac.py`: 18/18 tests ofensivos aprobados (0 fugas cross-tenant, sanitización SQL, model_config extra="forbid", RFC 7807).
  - **Frontend (Vitest):**
    - `useAlertas.test.ts`: verificar hook reactivo, conmutación de filtros y cálculo de totales.
    - `useAlertBadge.test.ts`: verificar emisión de eventos `notif-updated` y persistencia en `localStorage`.
    - `AlertasPage.test.tsx`: suite completa de renderizado (SectionHeader #ef4444, toolbar, toggle tarjetas/listado, paginación).
    - `StockCriticoTable.test.tsx`: renderizado de tabla, barras cromáticas y adición a compras.
    - `VencimientosCard.test.tsx`: renderizado de tarjetas de vencimiento, fechas relativas y botón de merma.
    - `SidebarAlertsBadge.test.tsx`: validación del badge reactivo en el Sidebar con animación de pulso rojo.
  - **Certificación Agente 09 (QA Parity & Test):** Calidad 5D y paridad matemática con Legacy, 54/54 tests backend alertas, 88/88 tests frontend alertas, 162/162 inventario total, 0 errores TypeScript, 0% floats.
  - **Certificación Agente 10 (Ciberseguridad Red Team):** 18/18 tests en `test_13_alerts_security_and_rbac.py`, 89/89 suite red team total, 0 fugas de tenant, RBAC 3 niveles estricto, dictamen `SECURITY_APPROVED`.
- [x] **8.5** Montaje en el Router Principal y Verificación de Compilación:
  - En `oppytec-frontend/src/app/router.tsx`:
    - Reemplazar la ruta placeholder `/alertas/*` por el montaje de `AlertasPage`.
  - Verificación de calidad:
    - Chequeo de tipos estático: `pnpm tsc --noEmit` $\rightarrow$ **0 errores**.
    - Linter: `pnpm lint` $\rightarrow$ **0 issues**.
    - Build de producción: `pnpm build` $\rightarrow$ **Éxito**.
- [x] **8.6** Certificación E2E Playwright en Navegador Real (Desacoplada — Agente 13):
  - Convocatoria del Agente 13 (`13-browser-e2e-playwright`) bajo demanda para ejecutar el flujo completo en Chromium, Firefox y WebKit:
    1. Carga de la aplicación e inspección del badge numérico en el Sidebar para `/alertas`.
    2. Navegación a `/alertas` y verificación de `SectionHeader` en rojo (#ef4444).
    3. Filtrado por "Stock Crítico" y adición de un insumo al carrito morado con toast de confirmación.
    4. Conmutación a "Listado" y validación de `StockCriticoTable` y `VencimientosCard`.
    5. Clic en botón de merma en lote vencido y comprobación de redirección a `/gestion?tab=mermas`.
  - *Nota de Gobernanza:* Según la Regla Inmutable 8 de OppyTec, el Agente 13 opera desacoplado en la Etapa 5 bajo demanda o en certificación pre-release sin bloquear el pipeline del DAG.
- [x] **8.7** Sincronización del Grafo AST y Verificación de Calidad:
  - **Certificación Agente 12 (Tech Writer & OpenSpec/Archify):**
    - Sincronización de especificaciones bipartitas OpenSpec en `specs/business-domain/` y `specs/engineering-code/` para reflejar el módulo de Alertas con frontmatter RAG-ready y evaluación JEV Sistema 1.
    - Ejecutar `python scripts/harness.py sync-graph` para indexar todos los nuevos routers backend, componentes frontend y modelos en `docs/architecture/graphify/graph.json`.
    - Ejecutar `python scripts/harness.py verify-evals` para validar el 100% de integridad y ausencia de reward-hacking.

---

## 🎯 Protocolo de Ejecución y Traspaso entre Agentes

| Etapa | Agente Líder | Tareas a Cargo | Entregables Principales |
| :---: | :--- | :--- | :--- |
| **Etapa 1** | `02-software-architect` & `03-database-alembic` | FASE 1: Dominio DDD y Consultas Agregadas en Postgres | `domain/alerts.py`, CTEs SQL optimizadas, modelos de datos |
| **Etapa 2** | `04-backend-senior-dev` | FASE 2: Servicio de Aplicación, Endpoints REST y WebSockets | `alerts_service.py`, `router_alerts.py`, Guards RBAC, WS events |
| **Etapa 2** | `05-frontend-senior-dev` | FASE 3, 4, 5, 6, 7: Feature Core, Vistas, Modales y Sidebar | `AlertasPage.tsx`, `useAlertas.ts`, `useAlertBadge.ts`, Sidebar badge |
| **Etapa 3** | `07-i18n-fx` & `08-environments-observability` | FASE 8: i18n 100%, Multi-Moneda FX, OpenTelemetry | `alerts.json` (es/en), Trazas OTel, Sentry context |
| **Etapa 4** | `09-qa-test` & `10-security-redteam` | FASE 8: Testing 5D, SAST/DAST, Paridad Matemática | Tests Pytest + Vitest, Auditoría RBAC, 0 Vulnerabilidades |
| **Etapa 4** | `11-git-arbiter` & `12-tech-writer` | Cierre: Merge Train, OpenSpec, Graphify & Archify | Smart Merge, Bóvedas OpenSpec, Grafo AST sincronizado |
| **Etapa 5** | `13-browser-e2e-playwright` | FASE 8: Certificación E2E en Navegador Real (Desacoplada) | Reporte Playwright HTML, Video y Traza de Navegación |

> **Nota Final:** Toda modificación de código debe ejecutarse previa consulta de Graphify (`python scripts/harness.py nav "<símbolo>"`) y concluir con la sincronización obligatoria `python scripts/harness.py sync-graph`.
