---
spec_id: ENG-INVENTORY-AND-KARDEX
title: "Inventario y Kardex"
audience: engineering_internal
domain_module: inventory
paired_spec: specs/business-domain/inventory-and-kardex.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 8"
---

# Inventario, Kardex y Trazabilidad Histórica — Especificación de Ingeniería

## Contrato técnico

### 1. Módulo Backend DDD (`oppytec-backend/src/modules/inventory/`)
- **Domain Layer:**
  - Entidades e Invariantes: `registro_stock` / `kardex_movements`, `StockItem`, `PhysicalCountSession`, `PhysicalCountItem`, `StockTransfer`.
  - Value Objects de Auditoría: `MovementSign` (signo según tipo de movimiento), `TimezoneConverter` (proyección determinista a huso horario de operaciones `America/Santiago`), y `AuditDelta` (cálculo de saldo anterior y posterior: $\text{saldo\_anterior} = \text{saldo\_resultante} - \text{cantidad}$).
- **Application Layer:**
  - `InventoryService` y servicios de consulta histórica: paginación server-side, filtros compuestos, cálculo de deltas y proyecciones enriquecidas.
  - Streaming CSV: generación reactiva por fragmentos (`StreamingResponse`) con cabecera `Content-Disposition: attachment; filename="auditoria_inventario_{fecha}.csv"`, UTF-8 BOM (`\uFEFF`) y sanitización CWE-1236.
- **Infrastructure Layer:**
  - Persistencia multi-tenant en esquema dinámico `tenant_*`:
    - `registro_stock` / `kardex_movements` (Append-Only inmutable, sin soft-delete, con `ORDER BY id ASC FOR UPDATE`).
    - Índices de alto rendimiento: `ix_registro_stock_bodega_producto`, `ix_registro_stock_created_tipo`, `ix_registro_stock_fecha_recuento`, `ix_registro_stock_usuario_created`, `ix_registro_stock_transfer_id`.
    - Estrategia anti-N+1: carga ansiosa `joinedload` / `selectinload` en SQLAlchemy asíncrono sobre `producto`, `bodega` y `usuario`.
    - `stock_items` (Unique `(producto_id, bodega_id)`, semáforos mínimo/crítico/reorden).
    - `physical_count_sessions` y `physical_count_items` (Conteos ciegos y actas de discrepancia con PPP).
    - `stock_transfers` (Traslados atómicos inter-bodega con UUID de correlación `transfer_id`).
- **Presentation Layer (Router REST normalizado RFC 7807):**
  - **Historial y Auditoría de Kardex (`presentation/router.py`):**
    - `GET /api/v1/inventory/history/paginated`:
      - Guard RBAC: `RequireTenantPermission("inventory.history.read")`.
      - Query params: `bodega_id`, `producto_id`, `tipo_movimiento`, `fecha_desde`, `fecha_hasta`, `user_search`, `skip`, `limit` (cota máxima 100).
      - Anonimización: si el token no posee permiso `inventory.history.view_users`, el campo `user_display_name` se ofusca a `"Operador Autorizado"`.
      - Ordenamiento determinista: `ORDER BY registro_stock.created_at DESC, registro_stock.id DESC`.
    - `GET /api/v1/inventory/history/export-csv`:
      - Guard RBAC: `RequireTenantPermission("inventory.history.export")`.
      - Streaming CSV con UTF-8 BOM (`\uFEFF`) y sanitización anti-fórmulas.
    - `DELETE /api/v1/inventory/history`:
      - Guard RBAC: `RequireTenantPermission("inventory.history.purge")` y rol Propietario.
      - Retorno: HTTP 204 No Content y evento de auditoría de seguridad crítico.
  - **Operaciones de Kardex y Stock:**
    - `POST /api/v1/inventory/kardex/movements`, `GET /api/v1/inventory/kardex/movements`.
    - `GET /api/v1/inventory/stock/status`, `POST /api/v1/inventory/stock/bulk-transfer`, `POST /api/v1/inventory/stock/undo`, `POST /api/v1/inventory/stock/redo`.
    - `POST /api/v1/inventory/mermas`, `POST /api/v1/inventory/mermas/{id}/approve`, `POST /api/v1/inventory/mermas/{id}/reject`.
    - `POST /api/v1/inventory/counts`, `GET /api/v1/inventory/counts`, `POST /api/v1/inventory/counts/{id}/approve`, `POST /api/v1/inventory/counts/{id}/reject`.
    - `GET /api/v1/inventory/alerts`, `GET /api/v1/inventory/alerts/badge` (especificación dedicada: `inventory-alerts.code.spec.md`).

### 2. Notificaciones en Tiempo Real (WebSocket Zero-Polling)
- Canal Redis Pub/Sub `/api/v1/ws/realtime`:
  - Evento `inventory.stock.updated`: al confirmarse cualquier transacción de Kardex, los clientes frontend invalidan las claves TanStack Query `["inventory", "history"]` y `["inventory", "stock"]` para actualización en vivo sin sondeo.

### 3. Matriz de Permisos RBAC de 3 Niveles
- `inventory.history.read`: acceso a la vista `/historial` y consumo de endpoint paginado.
- `inventory.history.export`: descarga de auditorías en archivo CSV (navegador y streaming).
- `inventory.history.purge`: depuración de registros históricos (exclusivo rol Propietario).
- `inventory.history.view_users`: visualización de identidades de operadores responsables.
- `inventory.stock.view`: consulta de niveles y semáforos de stock.
- `inventory.stock.transfer`: ejecución de traslados inter-bodega.
- `inventory.counts.create`, `inventory.counts.approve`: ciclo de toma física ciega y acta.
- `inventory.mermas.create`, `inventory.mermas.approve`: ciclo de bajas por merma.

### 4. Interfaz Frontend (`oppytec-frontend/src/features/historial/` y `inventory/`)
- **Módulo de Historial (`/historial`):**
  - Componentes: `HistorialPage.tsx`, `HistorialToolbar.tsx`, `FiltrosHistorial.tsx`, `TablaHistorial.tsx`, `exportCSV.ts`.
  - Hook reactivo `useHistorial.ts`: sincronización con URL search params (`?search=`), debounce predictivo en búsqueda de usuarios, selección sincronizada y paginación server-side.
  - Columnas canónicas de auditoría: Fecha y hora, Bodega, Producto, Tipo de movimiento, Cantidad, Unidad, Usuario, Motivo/Notas, Saldo resultante.
  - Semáforos cromáticos por tipo de movimiento, flechas direccionales de traspaso (`↑` saliente, `↓` entrante), y renderizado comparativo Before/After (`[Before] -> [After]`).
  - Internacionalización: 100% `es`/`en` mediante namespace `history.json` tipado en 22 namespaces con 0 textos hardcodeados.
  - Multi-Moneda FX: integración de `MoneyBadge` y formateo con tipo `Decimal` en la divisa activa del tenant.
  - Responsive y Accesible: diseño Mobile-First y soporte de los 3 temas corporativos (`light`, `dark`, `ocean-blue`).

## Invariantes
- Movimientos Kardex estrictamente append-only e inmutables (prohibición de `UPDATE` o `DELETE` individual).
- Prohibición de saldo negativo en salidas, ventas, transferencias y consumos (`InsufficientStockError`).
- Bloqueo transaccional canónico `ORDER BY id ASC FOR UPDATE` para inmunidad contra deadlocks.
- Cero actualizaciones directas a existencias: todo cambio transiciona mediante asiento en Kardex.
- Aislamiento multi-tenant estricto con validación de pertenencia e intercepción IDOR (`CrossTenantAccessError` -> HTTP 403).
- Todos los cálculos monetarios y de cantidades operan con precisión `Decimal` (cero punto flotante).
- Sanitización anti-inyección CSV (CWE-1236): anteponer comilla simple `'` si el primer carácter es `=`, `+`, `-`, `@`, `\t` o `\r`.
- Exportación universal con inclusión obligatoria de UTF-8 BOM (`\uFEFF`).
- Trazas OpenTelemetry (`kardex.movement.insert`, `kardex.history.query`, `kardex.history.export_csv`, `inventory.transfer.execute`) con PII scrubbing en logs (`[REDACTED_PII]`).

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.95` (bajo umbral → revisión humana / camino determinista).
- Justificación: El cálculo de saldo y balance de Kardex es aritmética exacta de libro mayor; JEV no interviene directamente en la contabilidad del ledger ni en la inmutabilidad de los registros de auditoría.

## Pruebas (Co-Creación 1:1)

### Backend (Pytest)
- `oppytec-backend/tests/modules/inventory/test_history_endpoints.py` (Paginación server-side, ordenamiento `created_at DESC`, filtros combinados y anonimización de identidad)
- `oppytec-backend/tests/modules/inventory/test_kardex_audit_domain.py` (Invariantes del libro mayor, algoritmo Before/After y carga ansiosa anti-N+1)
- `oppytec-backend/tests/modules/inventory/test_history_observability.py` (Spans OpenTelemetry `kardex.history.query` y `kardex.history.export_csv`, PII scrubbing de parámetros)
- `oppytec-backend/tests/modules/inventory/test_kardex_axioms.py` (5 axiomas matemáticos + Hypothesis property tests de balance)
- `oppytec-backend/tests/security_redteam/test_14_history_security_and_rbac.py` (16 tests ofensivos Red Team, RBAC 3 niveles, IDOR cross-tenant, sanitización CSV injection CWE-1236 y purga exclusiva de Propietario)
- `oppytec-backend/tests/domain/test_kardex_parity.py` (Paridad 1:1 con OppyTec-Legacy)

### Frontend (Vitest)
- `oppytec-frontend/src/features/historial/__tests__/HistorialPage.test.tsx` (14 tests: renderizado de cabecera, toolbar, badge de inmutabilidad y orquestación)
- `oppytec-frontend/src/features/historial/__tests__/HistorialToolbar.test.tsx` (Toolbar de gobernanza y exportación)
- `oppytec-frontend/src/features/historial/__tests__/FiltrosHistorial.test.tsx` (14 tests: filtros por bodega, producto, tipo, fechas, debounce predictivo y limpieza)
- `oppytec-frontend/src/features/historial/__tests__/TablaHistorial.test.tsx` (27 tests: semáforos cromáticos, flechas de traspaso, Before/After, timezone America/Santiago y visibilidad RBAC)
- `oppytec-frontend/src/features/historial/__tests__/HistorialExportCSV.test.tsx` (26 tests: 9 columnas canónicas, UTF-8 BOM, sanitización anti-inyección CSV, formato de archivo y revocación de URL)
- `oppytec-frontend/src/features/historial/__tests__/useHistorial.test.tsx` (18 tests: reactividad, URL search params, sincronización y debounce)
- `oppytec-frontend/src/features/inventory/__tests__/StockRegistroPage.test.tsx`
- `oppytec-frontend/src/features/inventory/__tests__/ContarInventarioPage.test.tsx`
- `oppytec-frontend/src/features/inventory/__tests__/RecuentosPage.test.tsx`
- `oppytec-frontend/src/features/inventory/__tests__/ModalesStock.test.tsx`
