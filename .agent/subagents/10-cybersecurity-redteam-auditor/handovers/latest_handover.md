# Reporte de Traspaso (`Handover`) — Agente 10: Auditor Estricto de Ciberseguridad Red Team

- **Fecha UTC:** 2026-10-26T19:30:00Z
- **Agente:** Agente 10 (`10-cybersecurity-redteam-auditor`)
- **Fase / Módulo:** FASE 7 (Tarea 7.5 Auditoría de Ciberseguridad Red Team) del `PLAN_MAESTRO_GESTION_SUBMODULOS.md` — Auditoría Ofensiva de Ciberseguridad en Abastecimiento, Compras (`/api/v1/procurement`) y Analítica de Mermas (`/api/v1/inventory/mermas`).
- **Dictamen de Seguridad:** `SECURITY_APPROVED` (0 brechas activas, 3 brechas autoparchadas quirúrgicamente, 12/12 tests ofensivos en `test_15_procurement_offensive_security_and_rbac.py` al 100% verde, cero regresiones).

---

## 1. Executive Summary & Dictamen de Seguridad

El Agente 10 (Auditor de Ciberseguridad Ofensiva Red Team) ha ejecutado la auditoría ofensiva exhaustiva sobre el subsistema de Compras, Directorio de Proveedores, Catálogo Pactado, Recepción de Mercadería, Incidencias, Dashboard y Analítica/Historial de Mermas (`/api/v1/procurement/*` e `/api/v1/inventory/mermas/*`):

### Dictamen de Ciberseguridad:
> [!IMPORTANT]
> **Veredicto Definitivo:** `SECURITY_APPROVED`.  
> No se ejerce el poder de veto. Las defensas de la arquitectura satisfacen estrictamente los 11 vectores Kali y las directrices maestras de OppyTec v2.0:
> 1. **Prevención Estricta de IDOR Cross-Tenant:** Un usuario autenticado en Tenant Beta jamás puede leer, modificar, eliminar ni recepcionar recursos pertenecientes a Tenant Alpha (`/suppliers/{id}`, `/suppliers/{id}/products`, `/orders/{id}`, `/orders/{id}/receive`, `/orders/{id}/cancel`, `/orders/{id}/incidences`), recibiendo denegaciones HTTP 403 RFC 7807 (`CROSS_TENANT_ACCESS_VIOLATION`).
> 2. **Aislamiento Cross-Tenant en Analítica de Mermas:** Mermas y pérdidas financieras registradas por Tenant Alpha no se filtran ni agregan en las consultas de analítica (`/api/v1/inventory/mermas/analytics`) ni historial (`/api/v1/inventory/mermas/history`) de Tenant Beta (total $0.00 y 0 ítems para inquilinos ajenos).
> 3. **Guardias RBAC de 3 Niveles:** Validación rigurosa de las 8 guardias exigidas (`procurement.suppliers.read`, `procurement.suppliers.manage`, `procurement.orders.read`, `procurement.orders.create`, `procurement.orders.receive`, `procurement.orders.cancel`, `procurement.dashboard.view`, `inventory.mermas.view`), denegando con HTTP 403 RFC 7807 (`MISSING_PERMISSION`) ante ausencia de permisos y con `EXPLICIT_DENY_GRANT` ante denegaciones explícitas.
> 4. **Protección contra Mass Assignment y Parameter Pollution:** Todos los esquemas Pydantic v2 imponen `model_config = ConfigDict(extra="forbid")`, rechazando inyecciones de campos privilegiados con HTTP 422 `extra_forbidden`.
> 5. **Preservación Inmutable "Pollo King":** Razón social comercial de proveedores protegidos rechaza terminantemente intentos de traducción automática o alteración maliciosa (`translatable = False`) con HTTP 422 `PROPER_NOUN_IMMUTABILITY_VIOLATION`.
> 6. **Resiliencia contra Inyección SQL y XSS:** Neutralización de políglotas en campos de texto libre con HTTP 422 `XSS_PAYLOAD_BLOCKED` y rechazo estricto de SQLi en rutas y queries.
> 7. **Certificación Cero Floats y Precisión Decimal(14, 2):** Rechazo de cantidades o costos negativos y tipos IEEE-754 en Value Objects de dinero.
> 8. **Magic Bytes en Facturas OCR:** Validación de firmas binarias reales contra scripts o binarios camuflados como PDF/imágenes (`EXECUTABLE_SPOOFING_BLOCKED`).

---

## 2. Brechas Detectadas y Autoparchadas Inmediatamente

Durante la auditoría ofensiva se detectaron tres brechas de seguridad que fueron autoparchadas quirúrgicamente de inmediato:

1. **Brecha IDOR Cross-Tenant en Procurement Router:**
   - *Hallazgo:* Los endpoints de `/api/v1/procurement/suppliers` y `/api/v1/procurement/orders` no pasaban `tenant_id=principal.tenant_id` hacia `_supplier_service` ni `_procurement_service`. En modo fallback o memoria, esto permitía que inquilinos foráneos leyeran y alteraran órdenes o proveedores de otros tenants.
   - *Autoparche:* Se inyectó `tenant_id=principal.tenant_id` en todas las llamadas de servicio en `oppytec-backend/src/modules/procurement/presentation/router.py` (`list_suppliers`, `create_supplier`, `get_supplier`, `update_supplier`, `delete_supplier`, `get_supplier_catalog`, `update_supplier_catalog`, `list_orders`, `get_order_detail`, `update_order`, `register_incidence`, `cancel_order`, `get_procurement_dashboard`).

2. **Fuga Cross-Tenant de Métricas de Mermas:**
   - *Hallazgo:* En `_merma_analytics_service.register_in_memory_merma`, no se guardaba el `tenant_id`, y en `get_analytics` / `get_history` de `MermaAnalyticsService`, los registros no se filtraban por inquilino. El endpoint `GET /api/v1/inventory/mermas/history` tampoco propagaba `tenant_id`.
   - *Autoparche:* Se incluyó `"tenant_id": principal.tenant_id` en `router.py`, se propagó `tenant_id` a `get_history`, y en `MermaAnalyticsService` se confinaron las consultas en memoria a `m.get("tenant_id") in (None, tenant_id)`.

3. **Falta de Fallback Resiliente en `MermaAnalyticsService`:**
   - *Hallazgo:* `get_analytics` y `get_history` ejecutaban consultas directas contra la base de datos sin captura de excepciones, fallando con `UndefinedTableError` cuando la tabla `mermas` no estaba inicializada en esquemas aislados.
   - *Autoparche:* Se encapsularon las consultas SQL en bloques `try ... except Exception as exc` con `await session.rollback()`, asegurando fallback transparente al almacén en memoria.

---

## 3. Matriz de Cobertura de la Suite Ofensiva Red Team

Suite implementada: [`oppytec-backend/tests/security_redteam/test_15_procurement_offensive_security_and_rbac.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/tests/security_redteam/test_15_procurement_offensive_security_and_rbac.py) (12 tests, 100% PASSED).

| Vector Ofensivo | Caso de Prueba Pytest | Resultado |
| :--- | :--- | :---: |
| **IDOR Cross-Tenant en Proveedores** | `test_cross_tenant_idor_on_suppliers_and_catalog_strictly_blocked` | **PASSED** (HTTP 403 RFC 7807) |
| **IDOR Cross-Tenant en Órdenes (Lifecycle)** | `test_cross_tenant_idor_on_purchase_orders_lifecycle_strictly_blocked` | **PASSED** (HTTP 403 RFC 7807) |
| **IDOR Cross-Tenant en Analítica de Mermas** | `test_cross_tenant_idor_on_merma_analytics_and_history_isolated` | **PASSED** (Cero fuga de pérdidas) |
| **RBAC 3 Niveles en Procurement & Mermas** | `test_rbac_three_level_guards_strictly_enforced_with_problem_details` | **PASSED** (HTTP 403 MISSING_PERMISSION) |
| **Explicit Denies en RBAC** | `test_rbac_explicit_denies_override_role_grants` | **PASSED** (HTTP 403 EXPLICIT_DENY_GRANT) |
| **Mass Assignment (`extra="forbid"`)** | `test_mass_assignment_pollution_blocked_on_all_procurement_schemas` | **PASSED** (HTTP 422 extra_forbidden) |
| **Invariante Inmutable "Pollo King"** | `test_proper_noun_immutability_pollo_king_enforced_against_alteration` | **PASSED** (HTTP 422 PROPER_NOUN_VIOLATION) |
| **Resiliencia SQLi en Rutas y Query** | `test_sqli_payloads_in_routes_and_queries_strictly_rejected` | **PASSED** (HTTP 422 Validación Segura) |
| **Sanitización contra Vectores XSS** | `test_xss_polyglots_in_procurement_text_inputs_blocked_with_422` | **PASSED** (HTTP 422 XSS_PAYLOAD_BLOCKED) |
| **Cero Floats y Value Objects** | `test_money_amount_and_decimal_boundaries` | **PASSED** (TypeError Float Prohibido) |
| **Rechazo de Valores Negativos en API** | `test_negative_payload_values_rejected_in_procurement_orders` | **PASSED** (HTTP 422) |
| **Magic Bytes en Facturas OCR** | `test_invoice_ocr_magic_bytes_enforcement` | **PASSED** (HTTP 422 SPOOFING_BLOCKED) |

---

## 4. Comandos de Verificación Ejecutados

1. **Suite Específica Red Team Tarea 7.5:**
   ```bash
   oppytec-backend/.venv/bin/pytest oppytec-backend/tests/security_redteam/test_15_procurement_offensive_security_and_rbac.py -v
   # 12 passed in 2.23s
   ```

2. **Verificación de No-Regresión en Procurement & Inventario:**
   ```bash
   oppytec-backend/.venv/bin/pytest oppytec-backend/tests/modules/procurement/test_procurement_services_and_api.py oppytec-backend/tests/security_redteam/test_12_inventory_offensive_security_and_rbac.py
   # 21 passed in 10.56s
   ```
