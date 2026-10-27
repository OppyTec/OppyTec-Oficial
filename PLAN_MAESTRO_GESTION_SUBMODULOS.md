# 📋 PLAN MAESTRO DE CONTROL Y EJECUCIÓN: SUB-MÓDULOS DE GESTIÓN (PEDIDOS/COMPRAS, PROVEEDORES Y GESTIÓN DE MERMAS)

> **Regla de Gobernanza:** Este documento es el tablero de control de ejecución estricto de los sub-módulos de Gestión de OppyTec v2.0 (`/gestion?tab=pedidos`, `/proveedores` y `/gestion?tab=mermas`).  
> Cada paso debe ser **100% corroborado y aprobado** antes de pasar al siguiente.  
> **Solo cuando se finalicen todos los pasos**, este documento podrá ser archivado o marcado como completado.  
> **Excepción Acordada:** La **Etapa 5 (Certificación E2E Playwright en Navegador Real)** se omite temporalmente en esta fase por requerimiento explícito del usuario.
>
> **Fuentes de Verdad Históricas (100% Solo Lectura):**  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Compras/` (`ComprasDashboard`, `CompraTable`, `MercaderiaReceptionDialog`, `IncidenciaDialog`, `CatalogoPrecios`, `useCompras.ts`)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Proveedores/` (`ProveedoresPage`, `ProveedorDialog`, `ProveedorDashboardDialog`, `ProveedorProductosDialog`, `useProveedores.ts`)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/GestionarMerma/` (`GestionarMerma`, `KpiDashboard`, `MermaStats`, `MermaHistory`, `MermaDateRangePicker`, `useMerma.ts`)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Gestion/` (`index.tsx` pestañas `pedidos`, `compras`, `mermas`, borrador persistente y presets de vista)  
> - `OppyTec-Legacy/OppyTec_Backend/src/purchases/` (Lógica transaccional de compras, catálogo de insumos y recepción en almacén)  
> - `OppyTec-Legacy/OppyTec_Backend/src/inventory/` (Lógica operativa de mermas y ajustes de existencias)  
>
> **Destinos de Construcción en OppyTec v2.0:**  
> - Frontend Compras & Proveedores: `oppytec-frontend/src/features/procurement/` (`components/`, `dialogs/`, `hooks/`, `types.ts`)  
> - Frontend Mermas: `oppytec-frontend/src/features/gestion/mermas/` (o extensión en `features/inventory/`) y montaje en `GestionPage.tsx`  
> - Rutas Router: `oppytec-frontend/src/app/router.tsx` (`/gestion?tab=pedidos`, `/proveedores`, `/gestion?tab=mermas`)  
> - Backend Procurement: `oppytec-backend/src/modules/procurement/` (DDD: Domain, Application, Infrastructure, Presentation)  
> - Backend Inventory/Waste: `oppytec-backend/src/modules/inventory/` (DDD: `WasteService`, analítica de mermas y Kardex)  
> - Base de Datos: Migración Alembic `0009_tenant_procurement_purchases_and_suppliers.py`  

---

## 📊 Estado General del Proyecto

- [x] **Fase 1:** Arquitectura de Dominio DDD, Esquemas PostgreSQL `tenant_*` y Migración Alembic 0009 — **COMPLETADA**
- [x] **Fase 2:** Motor Backend FastAPI Procurement & Servicios de Aplicación (Compras, Proveedores, Recepción, Mermas Analíticas, RBAC 3 niveles RFC 7807 y WebSockets) — **COMPLETADA**
- [x] **Fase 3:** Frontend Core & Hooks Reactivos (`types.ts`, `useCompras.ts`, `useProveedores.ts`, `useMermaAnalytics.ts`, TanStack Query v5 + WebSockets realtime + Persistencia Offline) — **COMPLETADA**
- [x] **Fase 4:** Sub-módulo 1 — Pedidos y Compras (`/gestion?tab=pedidos`): `ComprasDashboard`, `CompraTable`, `MercaderiaReceptionDialog`, `IncidenciaDialog`, `CatalogoPrecios`, vistas Lista/Tarjetas y Borrador — **COMPLETADA**
- [x] **Fase 5:** Sub-módulo 2 — Directorio de Proveedores (`/proveedores` y subTab Compras): `ProveedoresPage`, `ProveedorDialog`, `ProveedorDashboardDialog`, `ProveedorProductosDialog`, regla "Pollo King" y Acuerdos de Precios — **COMPLETADA**
- [x] **Fase 6:** Sub-módulo 3 — Gestión Analítica de Mermas (`/gestion?tab=mermas`): `KpiDashboard`, `MermaStats`, `MermaHistory`, `MermaDateRangePicker` y Cuadraturas Financieras PPP — **COMPLETADA**
- [x] **Fase 7:** Capas Cruzadas, i18n 100% `es`/`en` (`procurement.json`, `gestion.json`), Multi-Moneda FX `Decimal`, Observabilidad OpenTelemetry, Testing 5D (Vitest + Pytest) & Auditoría Red Team Kali — **COMPLETADA**

---

## 🔍 Detalle y Criterios de Aceptación por Fase

---

### [x] FASE 1: Arquitectura de Dominio DDD, Esquemas PostgreSQL tenant_* y Migración Alembic 0007 — ✅ 100% COMPLETADA
- [x] **1.1** Modelado de Persistencia Multi-Tenant en `oppytec-backend/src/modules/procurement/infrastructure/models.py`:
  - Heredar de `TenantBase` para residir estrictamente en esquemas `tenant_*`.
  - Tabla `proveedores`:
    - Campos: `id` (BigInteger PK), `rut_tax_id` (`String(64)` unique), `razon_social` (`String(180)`), `nombre_fantasia` (`String(180)` nullable), `email_contacto` (`String(255)` nullable), `telefono` (`String(50)` nullable), `direccion` (`String(255)` nullable), `lead_time_dias` (`Integer` default 1), `estado` (`String(32)` default `ACTIVO`), `notas` (`Text` nullable), `AuditTimestampsMixin`, `SoftDeleteMixin`.
    - Metadato inmutable: `translatable: ClassVar[bool] = False` (Regla "Pollo King": nombres de proveedores no se traducen).
  - Tabla `producto_proveedores`:
    - Acuerdos de suministro y catálogo pactado.
    - Campos: `id` (BigInteger PK), `producto_id` (FK `productos.id` CASCADE), `proveedor_id` (FK `proveedores.id` CASCADE), `codigo_producto_proveedor` (`String(100)` nullable), `precio_pactado` (`Numeric(14, 2)` con `Decimal`), `tiempo_entrega_dias` (`Integer` nullable), `es_proveedor_principal` (`Boolean` default False), `AuditTimestampsMixin`.
    - Restricción: `UNIQUE(producto_id, proveedor_id)`.
  - Tabla `compras` (`ordenes_compra`):
    - Cabecera transaccional de pedidos de compra.
    - Campos: `id` (BigInteger PK), `numero_orden` (`String(64)` unique index), `proveedor_id` (FK `proveedores.id`), `bodega_destino_id` (FK `bodegas.id`), `estado` (`String(32)` enum: `BORRADOR`, `SOLICITADA`, `EN_CAMINO`, `RECIBIDA_PARCIAL`, `RECIBIDA_TOTAL`, `CANCELADA`), `fecha_emision` (`DateTime(timezone=True)` default `now()`), `fecha_entrega_estimada` (`Date` nullable), `fecha_recepcion_real` (`DateTime(timezone=True)` nullable), `monto_neto` (`Numeric(14, 2)`), `monto_impuestos` (`Numeric(14, 2)`), `monto_total` (`Numeric(14, 2)`), `moneda_codigo` (`String(3)` default `CLP`), `notas` (`Text` nullable), `solicitante_user_id` (`Integer` FK `public.users.id`), `receptor_user_id` (`Integer` nullable FK `public.users.id`), `AuditTimestampsMixin`, `SoftDeleteMixin`.
  - Tabla `compra_items`:
    - Líneas de detalle de la compra.
    - Campos: `id` (BigInteger PK), `compra_id` (FK `compras.id` ON DELETE CASCADE), `producto_id` (FK `productos.id`), `cantidad_solicitada` (`Numeric(12, 4)`), `cantidad_recibida` (`Numeric(12, 4)` default 0), `precio_unitario` (`Numeric(14, 2)`), `subtotal_linea` (`Numeric(14, 2)`), `lote_codigo` (`String(64)` nullable), `fecha_vencimiento` (`Date` nullable).
  - Tabla `compra_incidencias`:
    - Registro de discrepancias o productos dañados/rechazados en la recepción.
    - Campos: `id` (BigInteger PK), `compra_id` (FK `compras.id`), `compra_item_id` (FK `compra_items.id` nullable), `tipo_incidencia` (`String(50)` enum: `DIFERENCIA_CANTIDAD`, `PRODUCTO_DANADO`, `FECHA_CADUCADA`, `PRODUCTO_EQUIVOCADO`, `OTRO`), `cantidad_afectada` (`Numeric(12, 4)`), `monto_disputa` (`Numeric(14, 2)` nullable), `resolucion` (`String(50)` enum: `PENDIENTE`, `NOTA_CREDITO`, `REEMPLAZO`, `ACEPTADO_CON_DESCUENTO`, `DESESTIMADO`), `descripcion` (`Text`), `foto_evidencia_url` (`String(500)` nullable), `registrado_por_user_id` (`Integer`), `AuditTimestampsMixin`.
  - Enriquecimiento de `mermas` (`oppytec-backend/src/modules/inventory/infrastructure/models.py`):
    - Asegurar campos para analítica: `tipo_merma`, `categoria_id`, `costo_total_ppp`, `motivo_detalle`, `estado_aprobacion`, `fecha_merma`.
- [x] **1.2** Migración Correlativa Lineal Alembic `0009`:
  - Archivo: `oppytec-backend/alembic/versions/0009_tenant_procurement_purchases_and_suppliers.py`.
  - `down_revision = "0008_tenant_recipes_combos_dynamic_option_groups"`.
  - Iteración segura e idempotente sobre todos los esquemas `tenant_*`.
  - Índices compuestos: `(proveedor_id, estado)`, `(fecha_emision, estado)`, `(producto_id, proveedor_id)`.
- [x] **1.3** Primitivas de Dominio DDD (`domain/`):
  - Value Objects: `RutTaxId` (validación de dígito verificador y formato Módulo 11 + Tax ID internacional), `MoneyAmount` (`Decimal(14, 2)` con no-negatividad), `PurchaseStatus` (máquina de estados), `IncidenceType` e `IncidenceResolution`.
  - Invariante de Recepción: Recálculo matemático determinista del Costo Promedio Ponderado (PPP) mediante `calculate_reception_ppp` en `Decimal`, con prevención estricta de división por cero y rechazo de cantidades negativas.
  - Entidades de Dominio Puro: `Supplier` (con invariante "Pollo King" `translatable: ClassVar[bool] = False`), `PurchaseItem`, `PurchaseIncidence` y `PurchaseOrder`.
  - Suite de pruebas unitarias al 100% verde (`oppytec-backend/tests/modules/procurement/test_domain_primitives.py`, 31/31 passed).

---

### [x] FASE 2: Motor Backend FastAPI Procurement & Servicios de Aplicación — ✅ 100% COMPLETADA
- [x] **2.1** Servicios de Aplicación Transaccionales (`application/`):
  - `SupplierService`:
    - CRUD de proveedores con validación anti-duplicados por `rut_tax_id`.
    - Asignación masiva de productos y tarifas pactadas (`update_supplier_catalog`).
    - Métricas de rendimiento y cumplimiento por proveedor (KPIs de entrega, histórico de compras).
  - `ProcurementService`:
    - Flujo de vida de la orden: `create_draft` $\rightarrow$ `submit_order` $\rightarrow$ `mark_in_transit` $\rightarrow$ `receive_goods` $\rightarrow$ `cancel_order`.
    - Recepción atómica (`receive_purchase_order`):
      - Verificación de cantidades recibidas vs solicitadas.
      - Registro de incidencias si $\text{recibido} < \text{solicitado}$ o hay daños.
      - Generación automática de asientos de Kardex (`TIPO: COMPRA`) vinculando `transfer_id`/`documento_referencia`.
      - Recálculo del PPP: $\text{PPP}_{\text{nuevo}} = \frac{(\text{Stock}_{\text{actual}} \times \text{PPP}_{\text{ant}}) + (\text{Cant}_{\text{recibida}} \times \text{Precio}_{\text{compra}})}{\text{Stock}_{\text{actual}} + \text{Cant}_{\text{recibida}}}$.
  - `MermaAnalyticsService`:
    - Agregaciones analíticas de mermas por rango de fechas, área operativa, categoría de producto y motivo.
    - Cálculo de ratio financiero de merma respecto al costo total de inventario.
- [x] **2.2** Endpoints REST FastAPI RFC 7807 (`presentation/router.py`):
  - **Proveedores:**
    - `GET /api/v1/procurement/suppliers`: Listado paginado con búsqueda por nombre, RUT y estado.
    - `POST /api/v1/procurement/suppliers`: Alta de proveedor.
    - `GET /api/v1/procurement/suppliers/{id}`: Detalle de proveedor y estadísticas.
    - `PUT /api/v1/procurement/suppliers/{id}`: Edición de proveedor.
    - `DELETE /api/v1/procurement/suppliers/{id}`: Baja lógica (`SoftDelete`).
    - `GET /api/v1/procurement/suppliers/{id}/products`: Catálogo de productos y precios pactados.
    - `POST /api/v1/procurement/suppliers/{id}/products`: Actualización masiva de precios pactados.
  - **Compras / Pedidos:**
    - `GET /api/v1/procurement/orders`: Historial con filtros por estado, proveedor, rango de fechas y bodega destino.
    - `POST /api/v1/procurement/orders`: Crear orden de compra (borrador o emitida).
    - `GET /api/v1/procurement/orders/{id}`: Detalle completo de orden y líneas de ítem.
    - `PUT /api/v1/procurement/orders/{id}`: Modificar orden (restringido a estado `BORRADOR` o `SOLICITADA`).
    - `POST /api/v1/procurement/orders/{id}/receive`: Recepción de mercadería e impacto en Kardex.
    - `POST /api/v1/procurement/orders/{id}/incidences`: Registro de incidencias de recepción.
    - `POST /api/v1/procurement/orders/{id}/cancel`: Cancelación con justificación.
    - `GET /api/v1/procurement/dashboard`: KPIs consolidados de compras (monto total, órdenes activas, distribución por proveedor).
  - **Mermas Analíticas:**
    - `GET /api/v1/inventory/mermas/analytics`: Agregaciones analíticas (KPIs, desglose por motivo, series temporales para gráficos).
    - `GET /api/v1/inventory/mermas/history`: Historial cronológico paginado con filtros avanzados.
- [x] **2.3** Matriz de Seguridad y Guardias RBAC de 3 Niveles:
  - `procurement.suppliers.read`: Consulta de directorio de proveedores.
  - `procurement.suppliers.manage`: Alta, edición y acuerdos de precios de proveedores.
  - `procurement.orders.read`: Consulta de órdenes y dashboard de compras.
  - `procurement.orders.create`: Emisión de nuevas órdenes de compra.
  - `procurement.orders.receive`: Recepción física de mercadería e impacto en existencias.
  - `procurement.orders.cancel`: Cancelación de órdenes.
  - `inventory.mermas.view`: Visualización del dashboard analítico y estadísticas de mermas.
  - `inventory.mermas.approve`: Aprobación administrativa de mermas críticas.
- [x] **2.4** Notificaciones en Tiempo Real (WebSocket Zero-Polling):
  - Eventos emitidos en Redis Pub/Sub:
    - `procurement.order.updated`: Cambio de estado en orden de compra para refresco en tiempo real.
    - `procurement.supplier.updated`: Actualización de catálogo de proveedor.
    - `inventory.waste.registered`: Nueva merma para refresco instantáneo del dashboard analítico.

---

### [x] FASE 3: Frontend Core & Hooks Reactivos — ✅ 100% COMPLETADA
- [x] **3.1** Contratos TypeScript de Dominio en `oppytec-frontend/src/features/procurement/types.ts`:
  - `Proveedor`: `id`, `rut_tax_id`, `razon_social`, `nombre_fantasia`, `email_contacto`, `telefono`, `lead_time_dias`, `estado`, `total_compras_historicas`.
  - `ProductoProveedor`: `producto_id`, `proveedor_id`, `precio_pactado`, `tiempo_entrega_dias`, `es_proveedor_principal`.
  - `CompraOrder`: `id`, `numero_orden`, `proveedor_id`, `proveedor_nombre`, `bodega_destino_id`, `estado`, `fecha_emision`, `fecha_entrega_estimada`, `monto_total`, `moneda_codigo`, `items_count`.
  - `CompraItem`: `id`, `producto_id`, `producto_nombre`, `cantidad_solicitada`, `cantidad_recibida`, `precio_unitario`, `subtotal`.
  - `IncidenciaPayload`, `ReceptionPayload`.
  - `MermaAnalyticsData`: KPIs (`total_perdida_ppp`, `ratio_merma_ventas`, `items_mermados`), desglose por motivo, series cronológicas.
- [x] **3.2** Hook Reactivo `useCompras.ts`:
  - Consumo reactivo de `GET /api/v1/procurement/orders` y `GET /api/v1/procurement/dashboard` con TanStack Query v5.
  - Persistencia de borrador de orden en `localStorage` (`oppytec_compra_draft`) con auto-recuperación y aviso *"Tienes un borrador guardado"*.
  - Mutaciones optimistas para crear, recepcionar y cancelar órdenes.
  - Suscripción al WebSocket `procurement.order.updated`.
- [x] **3.3** Hook Reactivo `useProveedores.ts`:
  - Carga y filtrado de proveedores con cache reactivo.
  - Mutaciones para alta, edición y guardado de catálogo pactado.
  - Búsqueda predictiva debounce por RUT, razón social o insumo abastecido.
- [x] **3.4** Hook Reactivo `useMermaAnalytics.ts`:
  - Integración con endpoints de analítica de mermas.
  - Manejo de filtros por rango de fechas (presets: hoy, 7d, 30d, mes actual, personalizado).

---

### [x] FASE 4: Sub-módulo 1 — Pedidos y Compras (`/gestion?tab=pedidos`) — ✅ 100% COMPLETADA
- [x] **4.1** Cabecera y Navegación de SubTabs:
  - SubTabs idénticas a Legacy: `Dashboard` (`BarChart3`), `Listado de Pedidos` (`FileText`), `Proveedores` (`Truck`), `Catálogo de Precios` (`Tag`).
  - Banner interactivo de recuperación de borrador (`hasDraft && recoveredDraftData`) con botón para restaurar o descartar.
  - Selector de vista dual: Tabla (`ListIcon`) / Tarjetas (`LayoutGrid`) con persistencia en `localStorage`.
- [x] **4.2** Dashboard de Compras (`ComprasDashboard.tsx`):
  - KPIs de cabecera: Gasto Total del período, Órdenes Pendientes de Recepción, Tiempo Promedio de Entrega, Proveedor Principal.
  - Gráfico o desglose de volumen de compra por categoría de insumos.
- [x] **4.3** Tabla y Tarjetas de Órdenes (`CompraTable.tsx` / `CompraCards.tsx`):
  - Columnas: Número de Orden, Proveedor, Fecha Emisión, Fecha Entrega Estimada, Estado (badge temático), Total Moneda FX, Acciones.
  - Badges cromáticos:
    - ⚪ `Borrador`
    - 🔵 `Solicitada`
    - 🟡 `En Camino`
    - 🟠 `Recibida Parcial`
    - 🟢 `Recibida Total`
    - 🔴 `Cancelada`
  - Acciones rápidas por fila: Ver detalle, Recepcionar mercadería, Registrar incidencia, Cancelar orden.
  - Vista adaptativa Mobile-First con touch targets $\ge 44\text{px}$.
- [x] **4.4** Modal de Recepción de Mercadería (`MercaderiaReceptionDialog.tsx`):
  - Listado de ítems de la orden con inputs de cantidad física recibida.
  - Selector de código de lote y fecha de vencimiento obligatoria para insumos perecibles.
  - Advertencia visual si la cantidad recibida difiere de la solicitada.
  - Confirmación atómica que dispara el impacto directo en Kardex y recálculo de PPP.
- [x] **4.5** Modal de Registro de Incidencias (`IncidenciaDialog.tsx`):
  - Tipificación de discrepancias (`Diferencia en Cantidad`, `Daño / Rotura`, `Vencimiento Próximo`, `Disconformidad`).
  - Campo de notas, resolución esperada (nota de crédito / reposición) y confirmación.
- [x] **4.6** Catálogo de Precios Históricos (`CatalogoPrecios.tsx`):
  - Tabla comparativa de precios históricos de compra por producto contra precios pactados.

---

### [x] FASE 5: Sub-módulo 2 — Directorio de Proveedores (`/proveedores` y subTab Compras) — ✅ 100% COMPLETADA
- [x] **5.1** Página Principal de Proveedores (`ProveedoresPage.tsx`):
  - Montaje como ruta de primer nivel en `/proveedores` y como subTab dentro de `/gestion?tab=pedidos&subTab=proveedores`.
  - `SectionHeader` centrado:
    - Título: `"Directorio de Proveedores"`.
    - Subtítulo: `"Gestión de alianzas comerciales, tiempos de entrega y catálogo pactado"`.
    - Ícono: `Truck` de `lucide-react`.
    - Color identificador: `#059669` (verde esmeralda comercial).
  - Buscador reactivo por RUT, Razón Social, Nombre de Fantasía o Insumo.
  - Conmutador de vista: Tabla / Tarjetas comerciales con persistencia en `localStorage`.
- [x] **5.2** Modal de Alta y Edición (`ProveedorDialog.tsx`):
  - Formulario estructurado con validación estricta de RUT/Tax ID.
  - Razón social, nombre de fantasía, email de contacto, teléfono, dirección comercial y plazo de entrega habitual en días (*lead time*).
  - Selector de estado: `Activo` / `Inactivo`.
- [x] **5.3** Modal de Catálogo Pactado (`ProveedorProductosDialog.tsx`):
  - Asignación de insumos suministrados por el proveedor.
  - Definición de precio pactado con formateo FX y marcado de proveedor prioritario/principal.
- [x] **5.4** Dashboard Analítico Individual (`ProveedorDashboardDialog.tsx`):
  - Vista 360° del proveedor: volumen acumulado de compra, índice de cumplimiento en entregas (*On-Time In-Full*), historial de órdenes e incidencias asociadas.

---

### [x] FASE 6: Sub-módulo 3 — Gestión Analítica de Mermas (`/gestion?tab=mermas`) — ✅ 100% COMPLETADA
- [x] **6.1** Integración y Montaje en `GestionPage.tsx`:
  - Activación cuando `viewTab === "mermas"`.
  - `SectionHeader` centrado:
    - Título: `"Gestión y Control de Mermas"`.
    - Subtítulo: `"Monitoreo analítico de pérdidas operativas, caducidades y motivos"`.
    - Ícono: `TrendingDown` o `AlertTriangle` de `lucide-react`.
    - Color identificador: `#ef4444` (rojo crítico de control de pérdidas).
- [x] **6.2** Selector de Rango de Fechas (`MermaDateRangePicker.tsx`):
  - Presets rápidos: *Hoy*, *Últimos 7 días*, *Este Mes*, *Mes Anterior*, *Rango Personalizado*.
  - Refresco reactivo sin recargar la pantalla.
- [x] **6.3** Dashboard de KPIs de Pérdida (`KpiDashboard.tsx`):
  - Tarjetas de métricas:
    - Pérdida Neta Total valorizada a PPP (con formateador FX `formatMoney`).
    - Unidades Totales Descartadas.
    - Ratio de Pérdida respecto a Inventario / Ventas.
    - Motivo Principal de Merma (ej. 42% por caducidad).
- [x] **6.4** Gráficos y Distribución de Mermas (`MermaStats.tsx`):
  - Gráfico de barras / líneas con la evolución diaria o semanal del desperdicio.
  - Gráfico de dona / distribución porcentual por tipología: `vencimiento`, `daño`, `error de preparación`, `mal estado`, `otro`.
- [x] **6.5** Historial Detallado y Auditoría de Mermas (`MermaHistory.tsx`):
  - Tabla de registros de merma: fecha y hora, producto, lote afectado, cantidad, costo PPP unitario, valor total de la pérdida, operador responsable y estado de aprobación.
  - Filtro interactivo por tipo de merma y búsqueda por nombre de producto.
  - Conexión con el diálogo operativo `MermaDialog` de Inventario para emitir nuevas mermas con el botón rápido `+ Registrar Merma`.

---

### [x] FASE 7: Capas Cruzadas, i18n, FX, Observabilidad, Testing 5D & Red Team — ✅ 100% COMPLETADA
- [x] **7.1** Internacionalización (i18n 100% `es`/`en` y Regla "Pollo King"):
  - Archivo de localización `oppytec-frontend/src/shared/i18n/locales/{es,en}/procurement.json`.
  - Actualización de `gestion.json` e `inventory.json`.
  - Respeto estricto de la regla *"Pollo King"*: nombres de proveedores y marcas no se traducen.
  - 0 textos hardcodeados en JSX, tooltips, placeholders o atributos de accesibilidad.
- [x] **7.2** Multi-Moneda FX con Precisión `Decimal`:
  - Todos los montos de compra, precios pactados, costos PPP y valorización de mermas formateados en la moneda del tenant mediante `formatMoney` y `MoneyBadge`.
  - Prohibido el uso de operaciones de punto flotante en cálculos de totales e impuestos en backend (`Decimal(14, 2)`).
- [x] **7.3** Instrumentación de Observabilidad (OpenTelemetry & Sentry):
  - Spans distribuidos: `procurement.order.create`, `procurement.order.receive`, `inventory.waste.analytics_query`.
  - Sanitización estricta de PII en logs y trazas (RUTs, teléfonos, emails de proveedores).
- [x] **7.4** Suite de Pruebas Automatizadas 5D:
  - **Backend (Pytest):**
    - `tests/modules/procurement/test_order_lifecycle.py`: flujo completo de orden desde borrador hasta recepción.
    - `tests/modules/procurement/test_reception_kardex_integration.py`: verificación de que la recepción impacta Kardex y recalcula PPP matemáticamente.
    - `tests/modules/procurement/test_supplier_contracts.py`: unicidad de RUT y consistencia de precios pactados.
    - `tests/modules/inventory/test_waste_analytics.py`: agregaciones y ratios de mermas.
  - **Frontend (Vitest):**
    - `useCompras.test.ts`, `useProveedores.test.ts`, `useMermaAnalytics.test.ts`: hooks, estados de carga y auto-guardado en `localStorage`.
    - `CompraTable.test.tsx`, `MercaderiaReceptionDialog.test.tsx`: renderizado, validación de diferencias y modales.
    - `ProveedoresPage.test.tsx`, `ProveedorDialog.test.tsx`: validación de RUT y catálogo.
    - `GestionarMerma.test.tsx`, `KpiDashboard.test.tsx`: métricas y selector de fechas.
- [x] **7.5** Auditoría de Ciberseguridad Red Team (Agente 10):
  - Verificación contra los 11 vectores Kali.
  - Prevención estricta de IDOR cross-tenant en acceso a proveedores, órdenes de compra y actas de merma.
  - Validación de guardias RBAC de 3 niveles (`procurement.orders.receive`, `procurement.suppliers.manage`).
  - Emisión de dictamen `SECURITY_APPROVED` previo al cierre.
- [x] **7.6** Sincronización AST con Graphify & Verificación de Calidad:
  - Ejecución de `python scripts/harness.py sync-graph` para indexar modelos, componentes y routers.
  - Ejecución de `python scripts/harness.py verify-evals` para certificar calidad 10/10 sin reward-hacking.

---

## 🎯 Protocolo de Ejecución y Traspaso entre Agentes

| Etapa | Agente Líder | Tareas a Cargo | Entregables Principales |
| :---: | :--- | :--- | :--- |
| **Etapa 1** | `02-software-architect` & `03-database-alembic` | FASE 1: DDL `tenant_*`, Alembic `0007`, DDD Procurement | Modelos SQLAlchemy, Migración `0007`, Value Objects |
| **Etapa 2** | `04-backend-senior-dev` | FASE 2: Servicios de Aplicación y Endpoints REST | Routers FastAPI, Guards RBAC, Transaccionalidad de Recepción |
| **Etapa 2** | `05-frontend-senior-dev` | FASE 3, 4, 5, 6: UI React 19, Hooks, Modales y Vistas | Vistas `/gestion?tab=pedidos`, `/proveedores`, `/gestion?tab=mermas` |
| **Etapa 3** | `07-i18n-fx` & `08-environments-observability` | FASE 7: i18n 100%, Multi-Moneda FX, OpenTelemetry | `procurement.json` (es/en), Trazas OTel, Sentry PII scrubbing |
| **Etapa 4** | `09-qa-test` & `10-security-redteam` | FASE 7: Testing 5D, SAST/DAST, Paridad y Seguridad | Suites Pytest + Vitest, Auditoría Kali, 0 Vulnerabilidades |
| **Etapa 4** | `11-git-arbiter` & `12-tech-writer` | Cierre: Merge Train, OpenSpec, Graphify & Archify | Smart Merge, Bóvedas OpenSpec, Grafo AST sincronizado |
| *Etapa 5* | *13-browser-e2e-playwright* | *Omitida en esta fase según requerimiento* | *(Postergada para pre-release)* |

> **Nota Final:** Toda modificación de código en los siguientes pasos debe ejecutarse previa consulta de Graphify (`python scripts/harness.py nav "<símbolo>"`) y concluir con la sincronización obligatoria `python scripts/harness.py sync-graph`.
