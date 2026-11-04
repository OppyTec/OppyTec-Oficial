# Reporte de Traspaso (`Handover`) — Agente 08: Environments and Observability Engineer

- **Fecha UTC:** 2026-11-04T18:30:00Z
- **Fase / Tarea:** Etapa 3 — Módulo de Facturas y Contabilidad (`/contabilidad/facturas`): Instrumentación OpenTelemetry 4-Pilares, Métricas FinOps, Censura Estricta PII y Structlog
- **Estado de Certificación:** `OBSERVABILITY_FINOPS_AND_PII_REDACTION_APPROVED`

---

## 1. Completed (Acciones de Observabilidad, Spans OTel y Métricas FinOps Realizadas)

1. **Pre-ejecución Graphify (Regla 6):**
   - Ejecutado `python scripts/harness.py nav "trace_span"` y `python scripts/harness.py nav "structlog"`.
   - Reclamados atómicamente los símbolos AST `trace_span` e `InvoiceService` vía `python scripts/harness.py claim-ast`.

2. **Instrumentación OpenTelemetry Spans Distribuidos (5 Spans Críticos):**
   - `invoices.upload`: Tiempo de subida y creación de DTE en `InvoiceService.create_invoice`, inyectando atributos semánticos.
   - `invoices.extract_gemini_ocr`: Latencia de inferencia y extracción de tokens en `GeminiInvoiceExtractor.extract_invoice_data`.
   - `invoices.resolve_aliases`: Resolución exacta y difusa de descripciones contra el catálogo en `SupplierAliasService.resolve_line_match`.
   - `invoices.auto_ingest_stock`: Traspaso transaccional al inventario físico en `InvoiceIngestionService.auto_ingest_to_inventory`.
   - `invoices.export_dte`: Generación de libros contables SII Chile F29 CSV, QuickBooks, Xero y Odoo en `DTEExportService.export_dte`.
   - Inyección de atributos semánticos estandarizados:
     * `invoice.id`: UUID correlacionado.
     * `invoice.dte_type`: Código oficial SII (33, 34, 39, 52, 56, 61).
     * `invoice.vendor_tax_id`: RUT emisor.
     * `invoice.gemini_tokens_used`: Conteo real de tokens consumidos.
     * `invoice.gemini_cost_usd`: Costo FinOps acumulado en USD con precisión `Decimal`.
     * `invoice.lines_count`: Cantidad de líneas de detalle del documento.

3. **Métricas Estructuradas FinOps y Monitoreo (OpenTelemetry / Prometheus / Grafana):**
   - `invoices_processed_total`: Counter clasificado por `tenant_id`, `dte_type` y `status`.
   - `invoice_ocr_duration_seconds`: Histogram de latencia de extracción OCR.
   - `invoice_ai_tokens_consumed_total`: Counter FinOps acumulativo de tokens consumidos.
   - `invoice_ai_cost_usd_total`: Counter FinOps acumulativo de costo monetario en USD.
   - Recopilador en memoria `_in_memory_invoice_metrics`, `get_in_memory_invoice_metrics()` y `clear_in_memory_invoice_metrics()`.

4. **Logs Estructurados JSON con Structlog y Censura Estricta de PII:**
   - Configuración de `structlog` con processor determinista `_structlog_pii_filter` que delega en `scrub_telemetry_payload`.
   - Función `get_invoice_logger(tenant_id, invoice_id)` para logs contextualizados de auditoría.
   - Censura reforzada de PII:
     * Cuentas bancarias (`bank_account`, `account_number`, `numero_cuenta`, `cuenta_bancaria`, `cta_cte`, regex `_BANK_ACCOUNT_PATTERN`).
     * RUTs de personas naturales y tarjetas de crédito.
     * Preservación de la regla de oro "Pollo King": nombres de proveedores y razones sociales inmutables.

5. **Suite de Pruebas Automatizadas y Verificación:**
   - Creada suite unitaria `oppytec-backend/tests/unit/modules/test_invoices_observability.py` (8 tests passing al 100%).
   - Verificados tests de arquitectura en `oppytec-backend/tests/architecture/test_observability_pii_redaction_and_spans.py` (100% verde).
   - Verificada la suite completa de facturas: 56 pruebas unitarias y de arquitectura pasando en verde (1.75s).
   - Sincronizado Grafo de Arquitectura Graphify: 118 nodos, 142 aristas (`python scripts/harness.py sync-graph`).

---

## 2. Friction & Failures
- `DTEType` enum en `value_objects.py` usa `DTEType.FACTURA_ELECTRONICA` (código numérico 33). Las aserciones fueron ajustadas correspondientemente.
- `TaxId` exige validación Módulo 11 estricta; se corrigieron los RUTs sintéticos de prueba para cumplir exactamente el dígito verificador.

---

## 3. Next Exact Action
- Dar paso al cierre de la Etapa 3 y dar inicio a la Etapa 4 (QA Parity, Red Team Security Audit, Merge Arbiter y Tech Writer OpenSpec).
