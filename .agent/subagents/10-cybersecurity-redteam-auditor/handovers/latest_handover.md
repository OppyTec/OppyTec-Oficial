# Reporte de Traspaso (`Handover`) — Agente 10: Auditor Estricto de Ciberseguridad Red Team

- **Fecha UTC:** 2026-10-25T18:15:00Z
- **Agente:** Agente 10 (`10-cybersecurity-redteam-auditor`)
- **Fase / Módulo:** Auditoría Ofensiva de Ciberseguridad, Aislamiento Multi-Tenant y RBAC en el Módulo de Inventario (Fase 10)
- **Estado de Certificación:** `SECURITY_INVENTORY_MODULE_HARDENED_AND_CERTIFIED` (0 bypasses, IDORs mitigados con parche en caliente, 11/11 vectores cubiertos, 71/71 tests de Red Team pasando al 100%, evals íntegros sin reward hacking).

---

## 1. Executive Summary & Poder de Veto de Seguridad

En el marco de la auditoría ofensiva de ciberseguridad sobre el Módulo de Inventario de OppyTec v2.0 (`router.py`, `inventory_service.py`, `physical_count_service.py`, `waste_service.py`), el Agente 10 identificó una brecha crítica de **IDOR Cross-Tenant**:
1. Las entidades `PhysicalCountSession`, `WasteRecord` y los asientos de `KardexEntry` no retenían ni validaban activamente el `tenant_id` en las operaciones en memoria (`/counts/{id}`, `/counts/{id}/items`, `/counts/{id}/finalize`, `/counts/{id}/approve`, `/counts/{id}/reject`, `/counts/{id}/delete`, `/stock/undo`, `/stock/redo`, `/mermas/{id}/approve`).
2. Esto permitía a un usuario legítimamente autenticado en `Tenant Beta` acceder, alterar o revertir actas y movimientos de `Tenant Alpha` enviando el `id` correspondiente.

**Acción Inmediata (Remediación Preventiva sin Veto Bloqueante):**
Se aplicó un parche de seguridad en caliente que:
- Introduce `tenant_id` obligatorio en `PhysicalCountSession`, `StockTransfer`, `KardexEntry` y `WasteRecord`.
- Exige validación de pertenencia al inquilino en todos los métodos de servicio (`get_session`, `list_sessions`, `save_count_items`, `finalize_count_session`, `approve_and_reconcile`, `reject_session`, `delete_session`, `undo_movement`, `redo_movement`, `get_movement`, `report_waste`, `approve`, `reject`).
- Eleva `CrossTenantAccessError` (HTTP 403 `CROSS_TENANT_ACCESS_VIOLATION`) ante cualquier discrepancia de inquilino.
- Se implementó la nueva suite de pruebas ofensivas: [`test_12_inventory_offensive_security_and_rbac.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/tests/security_redteam/test_12_inventory_offensive_security_and_rbac.py) con 12/12 tests pasando.

---

## 2. Cobertura de los 11 Vectores de Seguridad Ofensiva en Inventario

| Vector de Seguridad | Mecanismo de Defensa / Ataque Evaluado | Resultado |
| :--- | :--- | :---: |
| **1. Escape de Tenant (Aislamiento de esquemas PostgreSQL)** | Validación de `schema_name` con regex estricto `^tenant_[a-z0-9_]{1,63}$` en `validate_tenant_schema_name`, `SET LOCAL search_path` y `RESET search_path` en checkin del pool. | **CERTIFICADO (0 fugas)** |
| **2. Concurrencia y Bypass de Stock Negativo** | Orden determinista anti-deadlock `canonical_lock_order` (`ORDER BY id ASC`), y bloqueo atómico con `InsufficientStockError` que impide sobregiro (*overdraft*). | **CERTIFICADO (0 saldos negativos)** |
| **3. RBAC de 3 Niveles en Endpoints Críticos** | Guardias `RequireTenantPermission` en `/stock/bulk-transfer`, `/mermas/{id}/approve`, `/counts/{id}/approve`, `/stock/undo`, `/stock/redo` retornan HTTP 403 `RBAC_PERMISSION_DENIED` a roles no autorizados. | **CERTIFICADO (HTTP 403 estricto)** |
| **4. IDOR en Conteo Físico y Traspasos** | Validación estricta de `tenant_id` en cabecera y cuerpo de sesión. Tentativas de lectura, mutación o borrado cruzado devuelven HTTP 403 `CROSS_TENANT_ACCESS_VIOLATION`. | **CERTIFICADO (Mitigado)** |
| **5. IDOR en Kardex Ledger y Reversión** | Filtrado estricto por inquilino en `/kardex/movements` y validación de propiedad en `/stock/undo` y `/stock/redo`. | **CERTIFICADO (Mitigado)** |
| **6. Segregación de Funciones (SoD) en Mermas** | Regla estricta `record.reporter_user_id != approver_user_id`. Intentos de auto-aprobación son bloqueados con HTTP 403. | **CERTIFICADO (SoD Activo)** |
| **7. Invariantes en Traspasos Inter-Bodega** | Rechazo de traspaso a la misma bodega (`TransferSameWarehouseError`, HTTP 400) y verificación previa de saldo origen. | **CERTIFICADO** |
| **8. Costos Negativos y Cantidades Anómalas** | Value Objects `StockQuantity` y `MoneyAmount` prohíben floats (IEEE 754), NaN, infinitos y valores negativos, forzando precisión `Decimal`. | **CERTIFICADO (0% floats)** |
| **9. Mass Assignment (`extra="forbid"`)** | Todos los esquemas Pydantic v2 en `schemas.py` tienen `extra="forbid"`, rechazando parámetros inyectados con HTTP 422. | **CERTIFICADO** |
| **10. Prevención XSS y SSTI** | Entradas libres (`notas`, `reason`) inspeccionadas con `sanitize_text_input`, bloqueando políglotas con HTTP 422 `XSS_PAYLOAD_BLOCKED`. | **CERTIFICADO** |
| **11. Inyección SQL en Filtros y Rutas** | Tipado estricto de parámetros de ruta y consulta (`int`, `gt=0`); validación regex de identificadores. | **CERTIFICADO** |

---

## 3. Calidad y Verificación de Evals

- **Suite de Seguridad Red Team Completa:**
  `pytest tests/security_redteam/` $\to$ **71/71 tests pasados (100% verde)** en 3.31s.
- **Suite de Inventario Completa:**
  `pytest tests/unit/ tests/modules/ tests/domain/` $\to$ **178/178 tests pasados (100% verde)** en 5.36s.
- **Integridad de Evals (Harness):**
  `python scripts/harness.py verify-evals` $\to$ **100% verificado (Cero Reward Hacking)**.

---

## 4. Archivos Modificados y Creados

- [`entities.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/inventory/domain/entities.py) (Adición de `tenant_id` a `PhysicalCountSession` y `StockTransfer`).
- [`inventory_service.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/inventory/application/inventory_service.py) (Validación de tenant en `KardexEntry`, `undo_movement`, `redo_movement`, `get_movement`, `ledger`).
- [`physical_count_service.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/inventory/application/physical_count_service.py) (Validación de tenant en ciclo completo de recuentos).
- [`waste_service.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/inventory/application/waste_service.py) (Validación de tenant en `WasteRecord`, `approve`, `reject`).
- [`router.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/inventory/presentation/router.py) (Inyección de `principal.tenant_id` en todas las llamadas a servicios de inventario, recuentos y mermas).
- [`test_12_inventory_offensive_security_and_rbac.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/tests/security_redteam/test_12_inventory_offensive_security_and_rbac.py) (Nueva suite ofensiva con 12 vectores exhaustivos).
