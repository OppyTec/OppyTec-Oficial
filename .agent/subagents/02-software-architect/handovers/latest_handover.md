# Reporte de Traspaso (`Handover`) — Agente 02: Arquitecto de Software DDD & Clean Architecture

- **Fecha UTC:** 2026-11-04T19:40:00+00:00
- **Módulo:** Módulo de Facturas, DTE, Memoria de Proveedores y Conciliación Contable (`/contabilidad/facturas`)
- **Fase:** Etapa 1 — Arquitectura de Dominio DDD, Entidades, Value Objects con Validación Estricta, Excepciones RFC 7807 y Contratos Ports

---

## 1. Completed (Qué se realizó)

1. **Estructura Modular DDD Canónica (`oppytec-backend/src/modules/invoices/`):**
   - `__init__.py`: Paquete raíz del módulo.
   - `domain/__init__.py`: Exportación canónica de todas las entidades, value objects, excepciones y contratos.
   - `domain/exceptions.py`:
     - `InvoiceDomainError`: Excepción base mapeable a RFC 7807 (`invoices:errors.domain_error`).
     - `InvalidRUTError`: Validación formal de RUT chileno (módulo 11) e identificador fiscal internacional (`422 Unprocessable Entity`).
     - `InvoiceTotalMismatchError`: Violación de la invariante contable de cuadre Total vs Neto + IVA (`422 Unprocessable Entity`).
     - `InvalidPackagingFactorError`: Factor de empaque no positivo (`<= 0`) (`422 Unprocessable Entity`).
     - `SupplierAliasAlreadyExistsError`: Conflicto de unicidad de alias de producto de proveedor (`409 Conflict`).
     - `InvalidInvoiceStatusTransitionError`: Transición no permitida en la máquina de estados de factura.
     - `PriceDriftThresholdExceededError`: Alerta de variación porcentual de precio sobre umbral tolerable.
   - `domain/value_objects.py`:
     - `TaxId`: Value Object inmutable con validación estricta de RUT chileno mediante algoritmo Módulo 11 (`calculate_chilean_dv`), formateo canónico (`XX.XXX.XXX-X`), propiedad `clean` / `clean_tax_id`, extracción de `body` y `dv`, y compatibilidad internacional (`INTL_TAX_ID_PATTERN`). Cero uso de `float` (100% `Decimal` o strings canónicos).
     - `DTEType`: `IntEnum` con códigos oficiales del SII Chile: `FACTURA_ELECTRONICA` (33), `FACTURA_EXENTA` (34), `BOLETA_ELECTRONICA` (39), `GUIA_DESPACHO` (52), `NOTA_DEBITO` (56), `NOTA_CREDITO` (61), con resolución por código/nombre (`from_code`) y propiedad fiscal `requires_vat`.
     - `InvoiceStatus`: `str, Enum` del ciclo de vida (`PENDING`, `UPLOADED`, `PARSED`, `ANALYZED`, `REVIEWING`, `READY_FOR_REVIEW`, `APPROVED`, `CONFIRMED_STOCK`, `INGESTED`, `REJECTED`, `ERROR`) con predicados `is_terminal` e `is_reviewable`.
     - `MatchStatus`: `str, Enum` (`exact_alias`, `suggested`, `unmatched`).
     - `AuditSeverity` (`info`, `warning`, `critical`) y `AuditRuleCode` (`RUT_MISMATCH`, `VAT_19_DISCREPANCY`, `TOTAL_NET_MISMATCH`, `PRICE_DRIFT_HIGH`, `DUPLICATE_FOLIO`).
     - `PackagingFactor`: Inmutable que encapsula `Decimal > 0`, unidades de empaque e inventario, con métodos `to_physical_stock(quantity)` y `calculate_inventory_unit_cost(total, quantity)`.
     - `PriceDrift`: Inmutable para cálculo exacto de variación `((new - last) / last) * 100` con clasificación semafórica (`INFO`, `WARNING >= 10%`, `CRITICAL >= 25%`).
   - `domain/entities.py`:
     - `InvoiceAuditFlag`: Entidad de advertencia o hallazgo tributario/matemático con serialización `to_dict()`.
     - `InvoiceLineItem`: Línea de detalle con cálculo de stock físico (`quantity * packaging_factor`) y costo unitario de cocina (`line_total / stock_fisico`), y método `apply_packaging()`.
     - `SupplierProductAlias`: Memoria semántica entre descripción del proveedor y catálogo maestro, con normalización sin tildes (`normalize_name`), `times_used` y `last_matched_at`.
     - `Invoice`: Agregado Raíz con validación de invariante contable `validate_accounting_invariants(strict=True)` (tolerancia de 1 CLP por redondeo), auditoría de IVA 19% `validate_vat_19_rate()`, recálculo sumatorio de líneas `recalculate_totals_from_lines()`, adición de banderas de auditoría `add_audit_flag()` y confirmación de ingreso a bodega `confirm_stock_ingestion()`.
   - `domain/ports.py`:
     - Puertos Clean Architecture `@runtime_checkable Protocol`: `InvoiceRepositoryPort`, `SupplierAliasRepositoryPort`, `InvoiceStoragePort`, `DTEValidatorPort`.

2. **Testing y Calidad 1:1 Co-Creation:**
   - Creada suite unitaria `oppytec-backend/tests/unit/modules/test_invoices_domain.py` con 19 tests unitarios (100% pasando en 0.15s).
   - Validada suite de arquitectura `oppytec-backend/tests/architecture/` (29 tests pasando en 1.46s), incluyendo verificación estricta AST de 0% floats en capas de dominio y FX (`test_zero_float_in_fx_and_domain_modules`).
   - Sincronizado el grafo de arquitectura con `python scripts/harness.py sync-graph`.

---

## 2. Friction & Failures (Fricciones y Desafíos Resueltos)

- **Cero Float AST Gate (`test_zero_float_in_fx_and_domain_modules`):** El gate de arquitectura analiza el AST buscando cualquier símbolo `float`. Incluso `isinstance(value, float)` dispara una violación. Se refactorizó la inicialización de `PackagingFactor` para admitir `Decimal | str | int` y usar `Decimal(str(value))` defensivo, superando el gate al 100%.
- **Vector de Prueba Módulo 11 con Dígito K:** Se corroboró matemáticamente mediante `calculate_chilean_dv` que el cuerpo `10000013` produce residuo 1 en módulo 11, resultando en DV 'K' canónico (`10.000.013-K`), validando la integridad del algoritmo sin falsos positivos.

---

## 3. Next Exact Action (Siguiente Acción Exacta)

- **Para el Agente 03 (`03-database-alembic-and-backup-engineer`):**
  - Implementar la migración correlativa Alembic `0016_tenant_invoices_dte_and_supplier_aliases.py` sobre los esquemas `tenant_*` dinámicos, modelando las tablas `invoices`, `invoice_line_items`, `supplier_product_aliases`, `invoice_price_drift_logs` e `invoice_webhooks` con índices Trigram GIN (`pg_trgm`) para búsqueda difusa.
- **Para el Agente 04 (`04-backend-senior-dev`):**
  - Desarrollar la capa de aplicación e infraestructura implementando los puertos `InvoiceRepositoryPort`, `SupplierAliasRepositoryPort` y `InvoiceStoragePort` (Cloudflare R2), junto a los endpoints FastAPI RFC 7807 y eventos WebSocket.
