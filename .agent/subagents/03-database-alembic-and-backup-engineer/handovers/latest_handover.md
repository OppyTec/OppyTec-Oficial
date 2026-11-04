# Reporte de Traspaso (`Handover`) — Agente 03: Especialista en Base de Datos, Alembic y Backups 4-Capas

- **Fecha UTC:** 2026-11-04T22:20:00Z
- **Fase / Hito:** ETAPA 1 y HOTFIX del Plan Maestro Oficial de Facturas y Contabilidad (`.agent/Planes-Maestros/PLAN_MAESTRO_FACTURAS_CONTABILIDAD.md`) — Corrección de tipo en Foreign Key `fk_invoice_lines_target_bodega_id_bodegas` (de `UUID` a `Integer`) en modelos ORM SQLAlchemy 2.0 Async en [`oppytec-backend/src/modules/invoices/infrastructure/models.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/src/modules/invoices/infrastructure/models.py) y en Migración Correlativa Lineal Alembic 0016 ([`0016_tenant_invoices_dte_and_supplier_aliases.py`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-backend/alembic/versions/0016_tenant_invoices_dte_and_supplier_aliases.py)) en esquemas dinámicos `tenant_*`.
- **Estado de Certificación:** `INVOICES_MODELS_AND_ALEMBIC_0016_CERTIFIED` (Alembic 0001..0016 estrictamente lineal correlativa sin bifurcaciones, migración ejecutada al 100% en contenedor Docker PostgreSQL, 29/29 tests de arquitectura al 100% verde, 97/97 tests de facturas y seguridad al 100% verde, índices Trigram GIN para búsqueda difusa, sincronización Graphify completa).

---

## 1. Completed (Qué se ejecutó y validó)

1. **Corrección de Tipo en FK a `bodegas.id`:**
   - La tabla `bodegas.id` es de tipo `INTEGER`. Se actualizó `target_bodega_id` de `UUID` a `sa.Integer()` en Alembic y `Mapped[int | None]` en SQLAlchemy.
   - Actualizadas entidades y esquemas DTO para admitir `int | None`.

2. **Modelos SQLAlchemy 2.0 Async (`oppytec-backend/src/modules/invoices/infrastructure/models.py`):**
   - **`InvoiceModel` (tabla `invoices`):**
     * Clave primaria `id` (UUID v4) con default `uuid.uuid4`.
     * `tenant_id` (UUID no nulo, indexado).
     * Metadatos de archivo: `file_path`, `file_name`, `file_type`.
     * Identificación de emisor: `vendor_name` (con índice Trigram GIN `gin_trgm_ops`), `vendor_tax_id`, `vendor_address`.
     * Datos DTE: `invoice_number`, `invoice_date`, `due_date`, `currency`, `dte_type`.
     * Montos exactos: `exchange_rate`, `net_amount`, `tax_amount`, `total_amount` con `Numeric(14, 4)`. Cero float.
     * FinOps IA: `status`, `confidence_score`, `gemini_tokens_used`, `gemini_cost_usd` con `Numeric(10, 6)`, `is_stock_ingested`.
   - **`InvoiceLineItemModel` (tabla `invoice_lines`):**
     * Clave primaria `id` (UUID v4).
     * `invoice_id` (UUID FK a `invoices.id` ON DELETE CASCADE, indexado).
     * `line_number`, `raw_description` (con índice Trigram GIN `gin_trgm_ops`).
     * `quantity`, `unit`, `unit_price`, `line_total`, `vat_rate`.
     * Desacoplamiento de empaque mayorista a cocina: `matched_catalog_item_id` (UUID nullable FK a `catalog_items.id` ON DELETE SET NULL), `match_status`, `suggested_catalog_item_id`, `packaging_factor`, `calculated_stock_qty`, `inventory_unit`, `inventory_unit_cost`, `target_bodega_id` (`Integer` nullable FK a `bodegas.id` ON DELETE SET NULL).
   - **`SupplierProductAliasModel` (tabla `supplier_product_aliases`):**
     * `raw_vendor_product_name` con índice Trigram GIN `gin_trgm_ops`, `catalog_item_id` FK a `catalog_items.id`, `default_packaging_factor`.
   - **`InvoiceAuditFlagModel` (tabla `invoice_audit_flags`):**
     * Registro estructurado de discrepancias tributarias y descalces de IVA.

3. **Ejecución de Migración en Docker:**
   - `docker compose exec backend alembic upgrade head` ejecutado con éxito total (código 0). Aplicado a todos los esquemas `tenant_*`.

4. **Verificación de Tests:**
   - `./oppytec-backend/.venv/bin/pytest oppytec-backend/tests/architecture/test_alembic_integrity.py oppytec-backend/tests/unit/modules/test_invoices_models.py`: 8/8 pasados (100%).
   - `./oppytec-backend/.venv/bin/pytest oppytec-backend/tests/architecture/`: 29/29 pasados (100%).
   - Suite completa de facturas: 97/97 pasados (100%).

5. **Sincronización Graphify:**
   - Ejecutado `python scripts/harness.py sync-graph`. 118 nodos y 142 aristas.

---

## 2. Friction & Failures
- `DatatypeMismatchError` al intentar enlazar `UUID` con `INTEGER` en la FK a `bodegas.id`. Resuelto inmediatamente ajustando a `sa.Integer()` en la migración y el modelo.
