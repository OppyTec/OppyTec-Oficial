---
spec_id: ENG-PROJECTION-AND-STOCKOUTS
title: "Proyección de Stock, Quiebres FEFO y Traspasos Preventivos"
audience: engineering_internal
domain_module: projection
paired_spec: specs/business-domain/projections-and-stockouts.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 8"
---

# Proyección de Stock, Quiebres FEFO y Traspasos Preventivos — Especificación de Ingeniería

## Contrato Técnico

### 1. Módulo Backend DDD (`oppytec-backend/src/modules/projection/`)

- **Domain Layer (`domain/`):**
  - **Entidades e Invariantes (`entities.py`):**
    - `UrgencyStatus`: Enum representativo del semáforo operativo (`normal`, `warning`, `critical`).
    - `ProjectionDayPoint`: Punto atómico de simulación temporal para el día relativo $t \in [0, \text{horizon\_days}]$, conteniendo fecha calendario, saldo físico de stock proyectado (`qty: Decimal`), cantidad caducada por FEFO (`expiring_qty: Decimal`), deducción por eventos de banquetería (`event_deduction: Decimal`), lista de eventos desglosados y lotes que vencen.
    - `ProductProjectionSeries`: Agregado que encapsula la curva completa para un producto y bodega, tasa de consumo diario promedio ponderado (`daily_consumption_rate`), fecha de agotamiento proyectada (`depletion_date`), y peor estado identificado dentro de la ventana (`worst_status`, `worst_day`).
    - `TransferSuggestionEntity`: Entidad que modela una recomendación de traspaso preventivo inter-bodega (`producto_id`, `bodega_origen_id`, `bodega_destino_id`, `cantidad_sugerida`, `dias_cobertura_restante_origen`, `urgencia`).
  - **Motor FEFO y Demanda de Eventos (`fefo_engine.py`):**
    - `FEFOEngine`: Algoritmo determinista First-Expired, First-Out. Consume prioritariamente los lotes con fecha de vencimiento más próxima.
    - Registra mermas proyectadas para insumos no consumidos antes de su caducidad y descuenta requerimientos brutos de eventos programados en su fecha de ejecución.

- **Application Layer (`application/`):**
  - **Motor de Proyección (`projection_engine.py`):**
    - `ProjectionEngine`: Orquesta el cálculo de la curva temporal día a día integrando el inventario actual, histórico de consumo de los últimos 30 días, lotes registrados y reservas de eventos.
    - `find_alternative_stock`: Algoritmo de detección de bodegas donantes dentro del mismo tenant que posean autonomía suficiente (> 20 días) para mitigar quiebres en bodegas deficitarias.
  - **Servicio de Snapshots y Paginación Server-Side (`snapshot_service.py`):**
    - `ProjectionSnapshotService`:
      - `get_paginated_snapshots`: Consulta optimizada con filtros dinámicos (búsqueda por nombre/SKU, categoría, bodega, semáforo de urgencia, ordenamiento) y paginación server-side de alto rendimiento (< 25 ms).
      - `recompute_tenant_snapshots`: Recálculo masivo por lotes con exclusión mutua distribuida mediante PostgreSQL Transaction-Level Advisory Lock (`pg_try_advisory_xact_lock`), previniendo condiciones de carrera ante invocaciones concurrentes.
      - `get_product_curve_detail`: Construcción detallada de la serie temporal para gráficos interactivos.
      - `get_projection_alerts`: Consola de alertas de quiebre crítico y advertencias de stock para el tenant.

- **Infrastructure Layer (`infrastructure/`):**
  - **Modelo Relacional en Esquema Multi-Tenant (`models.py`):**
    - Tabla `projection_snapshots` en esquema `tenant_*`:
      - `id`: BigInteger primario autoincremental.
      - `producto_id`: ForeignKey hacia `productos.id` (ON DELETE CASCADE).
      - `bodega_id`: ForeignKey opcional hacia `bodegas.id` (ON DELETE CASCADE, `NULL` para vista consolidada del local).
      - `horizon_days`: Integer que define la ventana proyectada (7, 15, 30, 60, 90).
      - `current_stock`: `Numeric(14, 4)` con el saldo de inventario al momento del cálculo.
      - `projected_stock`: `Numeric(14, 4)` con el saldo estimado al final del horizonte.
      - `depletion_date`: Date nullable con la fecha proyectada de quiebre absoluto.
      - `worst_status`: String(20) (`normal`, `warning`, `critical`).
      - `worst_day`: Integer relativo al día del peor estado.
      - `daily_consumption_rate`: `Numeric(14, 4)` con la tasa promedio diaria de consumo.
      - `is_stale`: Boolean que marca la necesidad de refresco ante nuevos movimientos de kardex.
      - `calculated_at`: DateTime con zona horaria UTC de la última ejecución.
    - **Índices de Alto Rendimiento:**
      - `ix_projection_snapshots_producto_bodega`: `(producto_id, bodega_id, horizon_days)`.
      - `ix_projection_snapshots_status_horizon`: `(worst_status, horizon_days)`.
      - `ix_projection_snapshots_stale`: `(is_stale)`.

- **Presentation Layer (Router REST RFC 7807: `presentation/router.py`):**
  - Prefijo base: `/api/v1/projection`
  - Tag OpenAPI: `Projection`
  - **Endpoints:**
    1. `GET /api/v1/projection/snapshots`:
       - Guard RBAC: `RequireTenantPermission("projection.demand.read", fallback_permission="inventory.kardex.read")`.
       - Parámetros Query:
         - `page: int` (Default: 1, `ge=1`).
         - `page_size: int` (Default: 30, `ge=1, le=100`).
         - `search: str | None` (Filtrado por nombre o SKU).
         - `category_id: int | None` (Filtrado por categoría).
         - `bodega_id: int | None` (Filtrado por bodega o consolidado).
         - `status: str | None` (Filtrado por semáforo: `normal`, `warning`, `critical`).
         - `sort_by: str | None` (`urgency_desc`, `name_asc`, `name_desc`, `projected_asc`, `current_desc`).
         - `horizon_days: int` (Default: 30, `ge=7, le=90`).
       - Retorno: `PaginatedProjectionSnapshotsResponse` (HTTP 200 OK).
    2. `POST /api/v1/projection/recompute`:
       - Guard RBAC: `RequireTenantPermission("projection.recompute.execute", fallback_permission="inventory.kardex.write")`.
       - Payload: `RecomputeRequest` (`horizon_days: int = 30`).
       - Retorno: `RecomputeResponse` (HTTP 200 OK) con métricas de productos procesados y estado.
       - Bloqueo de concurrencia: PostgreSQL Advisory Lock para prevenir recálculos redundantes simultáneos.
    3. `GET /api/v1/projection/products/{product_id}/curve`:
       - Guard RBAC: `RequireTenantPermission("projection.demand.read", fallback_permission="inventory.kardex.read")`.
       - Parámetros Path/Query: `product_id: int`, `bodega_id: int | None`, `horizon_days: int = 30`.
       - Retorno: `ProductCurveDetailResponse` (HTTP 200 OK) con la serie temporal completa `curve: list[DaySimulationPointResponse]`.
    4. `GET /api/v1/projection/alerts`:
       - Guard RBAC: `RequireTenantPermission("projection.alerts.read", fallback_permission="inventory.kardex.read")`.
       - Parámetros Query: `bodega_id: int | None`, `horizon_days: int = 30`.
       - Retorno: `list[ProjectionAlertResponse]` (HTTP 200 OK) con detalle de insumos en riesgo y sugerencias asociadas.
    5. `GET /api/v1/projection/products/{product_id}/transfer-suggestions`:
       - Guard RBAC: `RequireTenantPermission("projection.transfers.read", fallback_permission="inventory.kardex.read")`.
       - Parámetros Path/Query: `product_id: int`, `bodega_id: int` (obligatorio), `needed_qty: Decimal | None`, `date_needed: date | None`.
       - Retorno: `list[TransferRecommendationResponse]` (HTTP 200 OK).

---

### 2. Módulo Frontend React 19 (`oppytec-frontend/src/features/projection/`)

- **Modelos y Tipos TypeScript (`types.ts`):**
  - `ProjectionUrgencyStatus`: `'normal' | 'warning' | 'critical'`.
  - `DayPoint`: Modelo de cada punto temporal con fecha, cantidad proyectada, estado, lotes por vencer y eventos agendados.
  - `EventProjectionAlert`: Modelo de alerta de stock para banners y consolas operativas.
  - `ProjectionProductOverview`: Tarjeta de producto con métricas de autonomía y semáforo.
  - `ProductCurveDetail`: Detalle completo para renderizado en gráfico modal.
  - `TransferSuggestion`: Modelo de recomendación de transferencia inter-bodega.
  - `ProjectionFilters`: Estado de filtros (horizonte, bodega, búsqueda, categoría, orden, estado, paginación).
  - `PaginatedProjectionResponse`: Contrato genérico de paginación server-side.

- **Capa de Cliente API REST (`api/projectionApi.ts`):**
  - Métodos API:
    - `fetchProjectionSnapshots(filters: ProjectionFilters): Promise<PaginatedProjectionResponse<ProjectionProductOverview>>`
    - `fetchProductCurveDetail(productId: number, horizonDays: number, bodegaId?: number): Promise<ProductCurveDetail>`
    - `fetchProjectionAlerts(horizonDays: number, bodegaId?: number): Promise<readonly EventProjectionAlert[]>`
    - `fetchTransferSuggestions(productId: number, bodegaId: number, neededQty?: number, dateNeeded?: string): Promise<readonly TransferSuggestion[]>`
    - `recomputeProjectionSnapshots(horizonDays?: number): Promise<RecomputeResponsePayload>`
  - Resiliencia y Fallback: Integración con `apiRequest` de `@/shared/api/httpClient`, sanitización de números `Decimal` (evitando desbordamiento o NaN) y fallback transparente offline a datos sintéticos ante desconexión.

- **Hooks Reactivos TanStack Query v5 (`hooks/`):**
  - `useProyeccionData(filters, options)`:
    - Query principal con clave determinista `["projection", "snapshots", filters]`.
    - Query secundaria de alertas con clave `["projection", "alerts", filters.horizonDays, filters.bodegaId]`.
    - Mutación de recálculo (`recomputeMutation`) que invalida automáticamente la caché de snapshots al finalizar.
    - Soporte de `keepPreviousData: true` para transiciones fluidas de página sin parpadeos.
  - `useProyeccionChart(productId, horizonDays, bodegaId)`:
    - Query reactiva para el modal de detalle con clave `["projection", "curve", productId, horizonDays, bodegaId]`.
    - Pre-procesamiento de puntos críticos (quiebres, eventos y lotes caducados) para anotaciones visuales en Recharts.
  - `useProyeccionState()`:
    - Estado de interfaz de usuario desacoplado: control de filtros, cambio de horizonte temporal, selección de producto activo para el modal de curva y gestión del modal de traspaso.

- **Componentes UI (ADN Visual Legacy + Mobile-First: `components/`):**
  - `ProyeccionHeader`: Barra superior con título, selector de horizonte temporal (7, 15, 30, 60, 90 días) y disparador de recálculo forzado.
  - `ProyeccionToolbar`: Buscador con debounce de 300 ms, selector de bodega, filtro desplegable y selector de ordenamiento.
  - `ProyeccionCategoryFilter`: Píldoras de filtrado horizontal táctil con scroll suave y conteo de ítems por categoría.
  - `ProyeccionExecutiveBanner`: Métricas resumen de alta visibilidad (quiebres críticos en rojo, advertencias en amarillo e insumos estables en verde).
  - `ProyeccionProductGrid`: Rejilla responsiva adaptable (1 columna en móvil, 2 en tablet, 3-4 en escritorio) que renderiza tarjetas `ProyeccionProductCard`.
  - `ProyeccionProductCard`: Tarjeta de insumo con semáforo cromático, días de autonomía, fecha estimada de quiebre y botón de análisis de curva.
  - `ProyeccionPagination`: Control server-side con navegación por páginas, selector de tamaño de página (10, 30, 50, 100) y resumen textual accesible.
  - `ProyeccionProductDetail`: Modal de análisis profundo con gráfico interactivo Recharts (`ProyeccionChart`), tooltips enriquecidos (`ProyeccionChartTooltip`) y desglose de métricas (`ProyeccionMetrics`).
  - `ProyeccionEventAlerts`: Panel lateral/inferior de alertas específicas por eventos masivos o caducidades inminentes.
  - `ProyeccionTransferModal`: Modal para confirmar la transferencia sugerida entre bodegas con validación de saldo disponible.

---

### 3. Matriz de Permisos RBAC de 3 Niveles

| Código de Permiso | Fallback Legacy | Nivel Módulo | Operación Autorizada |
|---|---|---|---|
| `projection.demand.read` | `inventory.kardex.read` | Lectura | Consulta de grid de proyecciones y detalle de curva de producto |
| `projection.recompute.execute` | `inventory.kardex.write` | Ejecución | Disparo de recálculo masivo con advisory lock |
| `projection.alerts.read` | `inventory.kardex.read` | Lectura | Visualización de consola de alertas y riesgos de stockout |
| `projection.transfers.read` | `inventory.kardex.read` | Lectura | Consulta de sugerencias de traspaso preventivo entre bodegas |

---

### 4. Integración con el Asistente OppyFy (Capa 3A / Operational Tools)

- **Herramienta Operacional (`oppytec-backend/src/modules/oppy_ai/application/operational_tools/projection_tools.py`):**
  - Herramienta registrada en OppyFy para responder consultas en lenguaje natural del chef o administrador:
    - Análisis de quiebres previstos para la semana actual o próxima.
    - Días de autonomía exacta para insumos estratégicos.
    - Recomendaciones proactivas de traspaso entre bodegas antes de compras de emergencia.
  - Sanitización de datos sensibles: ofuscación de valores financieros si el token no dispone del permiso `finance.costs.read`.

---

### 5. Cobertura de Pruebas Automatizadas

- **Backend:**
  - `oppytec-backend/tests/unit/projection/`: Pruebas de dominio sobre `FEFOEngine`, detección de quiebres y cálculo de consumo promedio ponderado.
  - `oppytec-backend/tests/integration/projection/`: Pruebas de integración sobre `ProjectionSnapshotService` con advisory lock, paginación server-side y endpoints FastAPI con autenticación multi-tenant y RBAC.
- **Frontend:**
  - `projectionHooks.test.ts`: Pruebas unitarias sobre `useProyeccionData`, `useProyeccionChart` y `useProyeccionState`.
  - `projectionComponents.test.tsx`, `projectionGridAndCard.test.tsx`: Pruebas de renderizado de la grilla de productos, semáforos y tarjetas.
  - `projectionChartAndDetail.test.tsx`: Pruebas del modal de detalle y curva temporal Recharts.
  - `projectionEventAlertsAndIntegration.test.tsx`: Pruebas de alertas de eventos y traspasos preventivos.
  - `projectionI18n.test.tsx`: Validación de traducción completa de cadenas en namespaces `es` y `en`.
