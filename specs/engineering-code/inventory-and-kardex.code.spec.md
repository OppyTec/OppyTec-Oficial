---
spec_id: ENG-INVENTORY-AND-KARDEX
title: "Inventario y Kardex"
audience: engineering_internal
domain_module: inventory
paired_spec: specs/business-domain/inventory-and-kardex.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 8"
---

# Inventario y Kardex — Especificación de Ingeniería

## Contrato técnico
- Módulo backend DDD: `oppytec-backend/src/modules/inventory/`.
- Router REST normalizado RFC 7807 (`oppytec-backend/src/modules/inventory/presentation/router.py`):
  - Kardex: `POST /api/v1/inventory/kardex/movements`, `GET /api/v1/inventory/kardex/movements`.
  - Stock: `GET /api/v1/inventory/stock/status`, `POST /api/v1/inventory/stock/bulk-transfer`, `POST /api/v1/inventory/stock/undo`, `POST /api/v1/inventory/stock/redo`.
  - Mermas: `POST /api/v1/inventory/mermas`, `POST /api/v1/inventory/mermas/{id}/approve`, `POST /api/v1/inventory/mermas/{id}/reject`.
  - Conteos y Auditorías: `POST /api/v1/inventory/counts`, `GET /api/v1/inventory/counts`, `POST /api/v1/inventory/counts/{id}/approve`, `POST /api/v1/inventory/counts/{id}/reject`.
- Persistencia multi-tenant en esquema dinámico `tenant_*`:
  - `kardex_movements` (Append-Only inmutable, sin soft-delete, con `ORDER BY id ASC FOR UPDATE`).
  - `stock_items` (Unique `producto_id, bodega_id`, semáforos mínimo/crítico/reorden).
  - `physical_count_sessions` y `physical_count_items` (Conteos ciegos y actas de discrepancia con PPP).
  - `stock_transfers` (Traslados atómicos inter-bodega).
- Sincronización en vivo: eventos publicados por Redis Pub/Sub al WebSocket `/api/v1/ws/realtime` y refresco reactivo en frontend con TanStack Query v5.
- Interfaz frontend (`oppytec-frontend/src/features/inventory/`):
  - Terminal de Stock (`/inventario/stock`), Conteo Ciego (`/contar-inventario`), Historial y Conciliación (`/recuentos`).
  - 5 Modales operativos de stock (`TransferDialog`, `AdjustmentDialog`, `MermaDialog`, `AddingMercaderiaDialog`, `SolicitudesDialog`).
  - Soporte i18n 100% `es`/`en` (`inventory.json`), Multi-Moneda FX (`MoneyBadge`, formateo con `Decimal`) y diseño Mobile-First con 3 temas corporativos.

## Invariantes
- Movimientos Kardex estrictamente append-only e inmutables.
- Prohibición de saldo negativo en salidas y transferencias (`InsufficientStockError`).
- Bloqueo canónico `ORDER BY id ASC FOR UPDATE` para evitar deadlocks transaccionales.
- Cero updates directos a tablas de stock: todo ajuste transiciona mediante asiento en Kardex.
- Aislamiento multi-tenant estricto con validación de pertenencia e intercepción IDOR (`CrossTenantAccessError` -> HTTP 403).
- Todos los cálculos monetarios y de cantidades operan con precisión `Decimal` (cero punto flotante).
- Trazas OpenTelemetry (`kardex.movement.insert`, `inventory.transfer.execute`, `inventory.count.reconcile`) y PII scrubbing en logs.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.95` (bajo umbral → revisión humana / camino determinista).
- Justificación: El cálculo de saldo y balance de Kardex es aritmética exacta; JEV no interviene directamente en la contabilidad del ledger.

## Pruebas (Co-Creación 1:1)
- **Backend (Pytest):**
  - `oppytec-backend/tests/modules/inventory/test_kardex_axioms.py` (5 axiomas matemáticos + Hypothesis property tests)
  - `oppytec-backend/tests/modules/inventory/test_inventory_observability.py` (OpenTelemetry spans, métricas y PII redaction)
  - `oppytec-backend/tests/security_redteam/test_12_inventory_offensive_security_and_rbac.py` (12 tests ofensivos, IDOR cross-tenant y RBAC 3 niveles)
  - `oppytec-backend/tests/domain/test_kardex_parity.py` (Paridad 1:1 con OppyTec-Legacy)
- **Frontend (Vitest):**
  - `oppytec-frontend/src/features/inventory/__tests__/StockRegistroPage.test.tsx`
  - `oppytec-frontend/src/features/inventory/__tests__/ContarInventarioPage.test.tsx`
  - `oppytec-frontend/src/features/inventory/__tests__/RecuentosPage.test.tsx`
  - `oppytec-frontend/src/features/inventory/__tests__/ModalesStock.test.tsx`
  - `oppytec-frontend/src/features/inventory/__tests__/hooks.test.ts`
