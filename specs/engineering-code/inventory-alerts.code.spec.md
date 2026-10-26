---
spec_id: ENG-INVENTORY-ALERTS
title: "Alertas de Inventario, Stock Crítico y Vencimientos"
audience: engineering_internal
domain_module: inventory
submodule: alerts
paired_spec: specs/business-domain/inventory-alerts.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 8"
---

# Alertas de Inventario, Stock Crítico y Vencimientos — Especificación de Ingeniería

## Contrato técnico

### 1. Ubicación Arquitectónica (Clean Architecture DDD)
- **Dominio Backend:** `oppytec-backend/src/modules/inventory/domain/alerts.py`
  - Value Objects inmutables:
    - `AlertSeverity`: enum canónico (`CRITICAL`, `WARNING`, `INFO`).
    - `StockHealthRatio`: valor porcentual validado con limitación estricta entre 0% y 100%.
    - `ExpiryUrgency`: cálculo de días restantes o transcurridos desde la fecha de expiración.
  - Entidades de Dominio:
    - `CriticalStockAlert`: `producto_id`, `bodega_id`, `stock_actual`, `stock_minimo`, `unidad_medida`, `ratio`, `is_depleted`.
    - `ExpiredLotAlert`: `producto_id`, `bodega_id`, `lote_codigo`, `fecha_vencimiento`, `cantidad_vencida`, `dias_vencido`, `costo_ppp`.
    - `UpcomingExpiryAlert`: `producto_id`, `bodega_id`, `lote_codigo`, `fecha_vencimiento`, `cantidad_en_riesgo`, `dias_restantes`, `costo_ppp`.
    - `AlertsConsolidatedSummary`: agregado raíz con contadores consolidados (`total_count`, `critical_count`, `expired_count`, `upcoming_count`, `has_critical`).
- **Servicio de Aplicación:** `oppytec-backend/src/modules/inventory/application/alerts_service.py`
  - `InventoryAlertsService`: orquesta la obtención agregada de alertas y el resumen para badges livianos con latencia $< 20\text{ms}$.
- **Infraestructura y Persistencia:** `oppytec-backend/src/modules/inventory/infrastructure/alerts_repository.py`
  - `PostgresAlertsRepository`: consultas agregadas optimizadas sobre esquemas dinámicos `tenant_*` utilizando índices compuestos `(bodega_id, producto_id)` y `(fecha_vencimiento_lote)`.
  - `InMemoryAlertsRepository`: particionamiento multi-tenant en memoria para suites de pruebas unitarias herméticas.

### 2. Endpoints REST FastAPI (RFC 7807 Normalizado)
- `oppytec-backend/src/modules/inventory/presentation/router_alerts.py` montado en `/api/v1/inventory/alerts`:
  - `GET /api/v1/inventory/alerts`:
    - Query params: `bodega_id` (opcional / repetible), `area_operativa_id` (opcional), `tipo` (`all`, `stock`, `upcoming`, `expired`).
    - Respuestas: `200 OK` (`AlertsResponseSchema`), `400 Bad Request`, `401 Unauthorized`, `403 Forbidden` (`RequireTenantPermission("inventory.alerts.read")`), `422 Unprocessable Entity`.
    - Esquemas Pydantic v2: `model_config = ConfigDict(extra="forbid")` para prevención estricta de Mass Assignment.
  - `GET /api/v1/inventory/alerts/badge`:
    - Endpoint ultraliviano ($< 5\text{ms}$) consumido por el Sidebar:
    - `{ "total_count": int, "has_critical": bool, "critical_stock_count": int, "expired_count": int, "upcoming_count": int }`.

### 3. Sincronización en Tiempo Real Zero-Polling
- Evento Redis Pub/Sub: `inventory.alerts.changed`.
- Despacho reactivo hacia WebSocket `/api/v1/ws/realtime`.
- Invocado tras cada transacción de Kardex (`register_movement`, `transfer_stock_bulk`, `finalize_count_session`, `report_merma`).
- Invalida selectivamente las queries `["inventory", "alerts"]` y `["inventory", "alerts", "badge"]` en TanStack Query v5 en el frontend sin recurrir a polling HTTP (`refetchInterval` prohibido).

### 4. Interfaz Frontend (`oppytec-frontend/src/features/inventory/alerts/`)
- Contratos TypeScript: `types.ts` (`AlertProductItem`, `AlertsSummary`, `AlertFilterType`, `AlertViewMode`, `CartPurchaseItem`).
- Hooks Reactivos:
  - `useAlertas.ts`: gestión de estado de filtros, ordenamiento, agrupación por bodega y persistencia de paginación.
  - `useAlertBadge.ts`: reactividad multi-pestaña escuchando eventos `storage` y `notif-updated` para sincronización instantánea.
- Componentes de Presentación:
  - `AlertasPage.tsx`: Vista principal con `SectionHeader` centrado en rojo/coral (#ef4444), selector de almacén y toggle de vistas (`cards` vs `list`).
  - `StockCriticoTable.tsx`: Tabla tabular de insumos con barras de salud cromáticas horizontales y acción de compra.
  - `VencimientosCard.tsx`: Tarjetas de lotes caducados y próximos a vencer con cálculo de tiempo relativo y botón de merma.
  - `SidebarAlertsBadge.tsx`: Badge flotante sobre el icono de Alertas con animación de pulso destructivo (`animate-pulse`) en rojo o aviso ámbar.
- Carrito de Compras Persistente: `localStorage.getItem("gestion_purchase_cart")`, disparo de evento `cart-updated` y notificación toast Sonner.

### 5. Capas Cruzadas y Gobernanza
- **Internacionalización (i18n):** Namespace dedicado `alerts.json` (69 claves 1:1 en `es`/`en`), 20 namespaces tipados en `i18next.d.ts`, 0 cadenas hardcodeadas en JSX o atributos de accesibilidad.
- **Multi-Moneda FX:** Costos unitarios y valorizaciones operan con `Decimal` en backend y `string` tipado / `MoneyBadge` en frontend (0% variables flotantes).
- **Observabilidad:** Traza de span OpenTelemetry `inventory.alerts.query`, spans en fetch/badge/broadcast, PII scrubbing en logs y payloads de telemetría.
- **Seguridad RBAC:** Permiso de 3 niveles `inventory.alerts.read` aplicado en enrutadores FastAPI y componentes `<Can>`. Rechazo inmediato a usuarios anónimos (401), sin permisos (403 `PERMISSION_DENIED`) o intentos cross-tenant (403 `CROSS_TENANT_ACCESS_VIOLATION`).

## Invariantes
- Aislamiento multi-tenant estricto: toda consulta SQL se ejecuta acotada al esquema `tenant_*` autenticado; suplantación de `X-Tenant-ID` es interceptada y denegada con HTTP 403.
- Cero deuda técnica de snapshot en el cliente: el cálculo de quiebres y vencimientos se delega a PostgreSQL con tiempo de respuesta inferior a 20 ms.
- Append-only e inmutabilidad contable: la vista de alertas no altera saldos directamente; las bajas operativas transicionan por el flujo oficial de mermas con su correspondiente asiento en Kardex.
- Integridad tipada: `extra="forbid"` en todos los esquemas Pydantic v2 y 0 errores de compilación TypeScript (`tsc --noEmit`).

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.95` (bajo umbral → camino determinista / revisión humana).
- Justificación: La clasificación de stock crítico y fechas de caducidad es lógica booleana y aritmética determinista sobre la base de datos; JEV no interviene en la categorización de alertas contables.

## Pruebas (Co-Creación 1:1)
- **Backend (Pytest):**
  - `oppytec-backend/tests/unit/modules/test_inventory_alerts_router.py` (8/8 tests de contrato REST y esquemas Pydantic).
  - `oppytec-backend/tests/modules/inventory/test_alerts_service.py` (cálculo analítico, umbrales mínimos y agregaciones FEFO).
  - `oppytec-backend/tests/security_redteam/test_13_alerts_security_and_rbac.py` (18/18 tests ofensivos, aislamiento cross-tenant, inyección SQL y RBAC 3 niveles).
  - `oppytec-backend/tests/architecture/test_observability_pii_redaction_and_spans.py` (validación de trazas OTel y redacción de PII).
- **Frontend (Vitest):**
  - `oppytec-frontend/src/features/inventory/alerts/__tests__/AlertasPage.test.tsx` (renderizado completo, toolbar, toggle de vistas y paginación).
  - `oppytec-frontend/src/features/inventory/alerts/__tests__/StockCriticoTable.test.tsx` (barras de salud cromáticas y botón de compras).
  - `oppytec-frontend/src/features/inventory/alerts/__tests__/VencimientosCard.test.tsx` (tarjetas FEFO, tiempo relativo y redirección a mermas).
  - `oppytec-frontend/src/features/inventory/alerts/__tests__/useAlertas.test.ts` (hook reactivo y cálculo de totales).
  - `oppytec-frontend/src/features/inventory/alerts/__tests__/useAlertBadge.test.ts` (reactividad multi-pestaña y persistencia).
  - `oppytec-frontend/src/shared/components/layout/__tests__/SidebarAlertsBadge.test.tsx` (badge reactivo pulsante en Sidebar expandido y colapsado).
