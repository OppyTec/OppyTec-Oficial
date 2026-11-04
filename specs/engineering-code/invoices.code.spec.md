---
spec_id: ENG-INVOICES-ACCOUNTING-DTE
title: "Módulo de Facturas, Ingesta Inteligente DTE, Alias de Proveedores y Conciliación Contable"
audience: engineering_internal
domain_module: invoices
paired_spec: specs/business-domain/invoices/invoices.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 8"
---

# Módulo de Facturas, DTE, Ingesta Multimodal y Conciliación Contable — Especificación de Ingeniería

## 1. Contrato Técnico y Arquitectura de Dominio DDD

El módulo de facturación y contabilidad está construido bajo los principios de Domain-Driven Design (DDD) y Clean Architecture, organizado en cuatro capas desacopladas dentro de `oppytec-backend/src/modules/invoices/`:

```
oppytec-backend/src/modules/invoices/
├── domain/
│   ├── value_objects.py    # Value Objects inmutables (TaxId, DTEType, InvoiceStatus, etc.)
│   ├── entities.py         # Entidades de dominio ricas (Invoice, InvoiceLineItem, Alias, PriceDrift)
│   ├── exceptions.py       # Excepciones semánticas del dominio (cuadre contable, BOLA, cuotas)
│   └── ports.py            # Interfaces abstractas (StoragePort, LLMExtractorPort, Repositories)
├── application/
│   ├── schemas.py          # DTOs Pydantic v2 con validación estricta y tipos Decimal
│   ├── services.py         # Orquestación de casos de uso (Ingesta, Kardex, Alias, PriceDrift)
│   └── gemini_extractor.py # Adaptador de inferencia multimodal Gemini con esquemas estructurados
├── infrastructure/
│   ├── models.py           # Modelos relacionales SQLAlchemy 2.0 Async en esquemas tenant_*
│   └── repositories.py     # Implementación de repositorios con pg_trgm y Unit of Work
└── presentation/
    └── router.py           # Endpoints FastAPI con ProblemDetails RFC 7807 y guardias RBAC
```

---

## 2. Value Objects y Entidades de Dominio

### A. Value Objects Inmutables (`domain/value_objects.py`)
1. **`TaxId`:** Encapsula y valida el identificador fiscal (RUT chileno mediante algoritmo Módulo 11 con dígito verificador `0-9, K`). Implementa sanitización automática eliminando puntos y guiones (`clean_tax_id`).
2. **`DTEType`:** Enumeración formal según la normativa del Servicio de Impuestos Internos de Chile:
   - `FACTURA_ELECTRONICA_33` = "33"
   - `FACTURA_EXENTA_34` = "34"
   - `GUIA_DESPACHO_52` = "52"
   - `BOLETA_ELECTRONICA_39` = "39"
   - `NOTA_DEBITO_56` = "56"
   - `NOTA_CREDITO_61` = "61"
3. **`InvoiceStatus`:** Ciclo de vida estricto del documento:
   - `UPLOADED`, `ANALYZING`, `ANALYZED`, `READY_FOR_REVIEW`, `CONFIRMED_STOCK`, `ERROR`, `REJECTED`.
4. **`ConfidenceScore`:** Puntuación de confianza entre $0.0000$ y $1.0000$ con umbral de revisión automática ($< 0.60$).
5. **`PackagingFactor`:** Multiplicador positivo no nulo que desacopla la unidad de compra mayorista de la unidad base culinaria (por ejemplo, caja de 18 kg a stock de kilogramos).
6. **`MoneyAmount`:** Encapsula el valor numérico en `Decimal` con 4 decimales y código ISO de divisa (`CLP`, `USD`, `EUR`, `UF`).

### B. Invariantes del Agregado `Invoice` (`domain/entities.py`)
- **Ecuación de Cuadre Contable:**
  $$\text{Diferencia} = |\text{total\_amount} - (\text{net\_amount} + \text{tax\_amount})|$$
  Si la diferencia supera $1\text{ CLP}$, el agregado activa la bandera de auditoría `AuditFlag.TAX_MISMATCH`.
- **Transición a Stock Confirmado:**
  El método `confirm_and_ingest_stock(...)` valida que el documento no esté ya confirmado, actualiza su estado a `CONFIRMED_STOCK`, estampa el usuario y timestamp UTC, y genera eventos de dominio para la persistencia en Kardex.

---

## 3. Persistencia Relacional Multi-Tenant y Migración Alembic 0016

### A. Esquemas Aislados y Migración
La persistencia física reside en los esquemas aislados por inquilino (`tenant_*`), garantizando segregación estricta de datos. La migración correlativa lineal `0016_tenant_invoices_dte_and_supplier_aliases.py` (con `down_revision = '0015_tenant_actividades_triada_enriquecida'`) crea las siguientes tablas:

1. **`invoices`:**
   - Cabecera del documento: `id` (UUID PK), `user_id` (FK a usuarios), `filename`, `file_path` (clave R2), `file_hash_sha256` (índice único para deduplicación), `vendor_name`, `vendor_tax_id` (índice B-Tree), `vendor_fiscal_address`, `invoice_number`, `dte_type`, `invoice_date`, `due_date`.
   - Campos monetarios (`Numeric(16, 4)`): `net_amount`, `tax_amount`, `total_amount`, `currency`.
   - Control operacional: `status` (índice B-Tree), `confidence_score` (`Numeric(5, 4)`), `audit_flags` (`JSONB`).
   - Métricas FinOps: `gemini_tokens_used`, `gemini_cost_usd` (`Numeric(12, 6)`), `gemini_model_used`, `gemini_processing_time_ms`.
   - Confirmación: `is_confirmed_to_inventory` (Boolean), `confirmed_at`, `confirmed_by_user_id`, `confirmed_bodega_id`.
2. **`invoice_line_items`:**
   - Líneas de detalle: `id` (UUID PK), `invoice_id` (FK `ON DELETE CASCADE`), `line_number`, `raw_description`, `sku_vendor`, `quantity` (`Numeric(14, 4)`), `unit_name`, `unit_price_net` (`Numeric(16, 4)`), `tax_rate` (`Numeric(5, 2)`), `total_net` (`Numeric(16, 4)`).
   - Conversión de empaque: `packaging_description`, `packaging_factor` (`Numeric(14, 4)` default 1.0), `kitchen_base_unit`, `real_kitchen_stock` (`Numeric(14, 4)`), `real_unit_cost` (`Numeric(16, 4)`).
   - Matching: `matched_product_id` (FK a `tenant_*.productos`), `match_status` (`exact_alias`, `suggested`, `unmatched`).
3. **`supplier_product_aliases`:**
   - Mapeo inteligente: `id` (UUID PK), `supplier_id` (FK a proveedores), `supplier_tax_id_normalized`, `alias_raw`, `alias_normalized` (con índice **Trigram GIN** para búsqueda difusa `gin_trgm_ops`), `producto_id` (FK a productos), `default_packaging_factor`, `default_kitchen_unit`, `times_used`, `last_matched_at`.
4. **`invoice_price_drift_logs`:**
   - Registro de inflación y desvíos: `id` (UUID PK), `invoice_id`, `producto_id`, `supplier_id`, `previous_unit_cost`, `new_unit_cost`, `drift_percentage` (`Numeric(8, 4)`), `severity` (`INFO`, `WARNING`, `CRITICAL`).
5. **`invoice_webhooks`:**
   - Integración contable externa: `id` (UUID PK), `url`, `secret_token` (HMAC-SHA256), `events` (`JSONB`), `is_active`.

---

## 4. Pipeline de Inferencia Multimodal Gemini OCR y FinOps

### A. Extracción Estructurada con Esquema Pydantic
El servicio `GeminiInvoiceProcessor` procesa documentos digitales (PDF o imagen):
- Renderizado de PDF multipágina a imágenes de alta definición (300 DPI) completamente en memoria (cero almacenamiento efímero en disco).
- Invocación de la API multimodal con `response_mime_type="application/json"` forzando la respuesta bajo el esquema Pydantic `ExtractedInvoiceDTO`.
- Extracción de empaques con soporte de expresiones regulares de contingencia:
  - Detección de bultos: `r'\(~?(\d+(?:[.,]\d+)?)\s*kg\)'`, `r'(?:caja|pieza|bolsa|saco)[^0-9]*(\d+(?:[.,]\d+)?)\s*kg'`.
- Registro de consumo FinOps en cada procesamiento:
  - `gemini_tokens_used`: prompt tokens + response tokens.
  - `gemini_cost_usd`: cálculo exacto con `Decimal(12, 6)` conforme a la tarificación oficial del modelo utilizado.

---

## 5. Algoritmo de Resolución de Alias y Desacoplamiento de Empaque

### A. Cascada de Resolución Semántica (4 Niveles)
1. **Nivel 1 (`exact_alias` - 100% Confianza):** Consulta directa a `supplier_product_aliases` mediante clave compuesta `(supplier_id, alias_normalized)`. Asigna de forma inmediata el producto, su factor de empaque y unidad de inventario.
2. **Nivel 2 (`exact_sku` / `exact_name` - 95% Confianza):** Búsqueda en el catálogo maestro de productos por coincidencia exacta de SKU o nombre normalizado.
3. **Nivel 3 (`suggested` - Similitud Trigram $\ge 0.50$):** Búsqueda difusa en base de datos mediante el operador `%` de `pg_trgm`:
   $$\text{similarity}(\text{alias\_normalized}, \text{p.nombre}) \ge 0.50$$
4. **Nivel 4 (`unmatched`):** Insumo no registrado. Se habilita en la interfaz la acción `create_new` permitiendo al usuario registrar el producto en el catálogo durante la misma revisión.

### B. Fórmula de Conversión a Stock de Bodega
$$\text{Stock Físico Entrante} = \text{Cantidad Facturada} \times \text{Factor de Empaque}$$
$$\text{Costo Unitario Real de Inventario} = \frac{\text{Total Neto de Línea}}{\text{Stock Físico Entrante}}$$

---

## 6. Endpoints REST RFC 7807 y Seguridad Dual RBAC

Todos los endpoints residen bajo el prefijo `/api/v1/invoices` y retornan errores en formato RFC 7807 (`ProblemDetails`):

| Método | Ruta | Permiso RBAC | Descripción Técnica |
|---|---|---|---|
| `GET` | `/api/v1/invoices` | `invoices.invoices.read` | Listado paginado con filtros de fecha, estado, emisor y tipo DTE. |
| `POST` | `/api/v1/invoices/upload` | `invoices.invoices.upload` | Carga multipart, validación Magic Bytes, persistencia en R2 y análisis OCR. |
| `GET` | `/api/v1/invoices/{id}` | `invoices.invoices.read` | Detalle del documento con ítems, flags, proveedor y URL presignada temporal ($\le 15$ min). |
| `POST` | `/api/v1/invoices/{id}/process` | `invoices.invoices.edit` | Re-procesamiento con motor OCR Gemini. |
| `PUT` | `/api/v1/invoices/{id}` | `invoices.invoices.edit` | Actualización de cabecera o edición manual de líneas. |
| `POST` | `/api/v1/invoices/{id}/confirm-stock` | `invoices.invoices.confirm_stock` | Transacción ACID: ingesta a inventario, creación de asiento Kardex y memorización de aliases. |
| `DELETE` | `/api/v1/invoices/{id}` | `invoices.invoices.delete` | Eliminación lógica (restringida si el stock ya fue confirmado). |
| `POST` | `/api/v1/invoices/bulk-process` | `invoices.invoices.upload` | Procesamiento masivo por lote de documentos en cola. |
| `POST` | `/api/v1/invoices/bulk-delete` | `invoices.invoices.delete` | Eliminación masiva con validación de estado. |
| `GET` | `/api/v1/invoices/stats` | `invoices.invoices.read` | KPIs del dashboard, métricas contables y consumo acumulado FinOps. |
| `GET` | `/api/v1/invoices/price-drift` | `invoices.invoices.read` | Reporte analítico de variación de precios unitarios. |
| `POST` | `/api/v1/invoices/export` | `invoices.invoices.export` | Exportación multiformato (CSV, Excel, QuickBooks, Xero, Odoo). |
| `GET` | `/api/v1/invoices/export/sii/compras` | `invoices.invoices.export` | Generador oficial de archivo de Registro de Compras del SII (formato CSV ANSI/ISO-8859-1). |
| `GET` | `/api/v1/invoices/export/sii/ventas` | `invoices.invoices.export` | Generador oficial de Registro de Ventas del SII. |
| `GET/POST/DELETE` | `/api/v1/invoices/webhooks` | `invoices.webhooks.manage` | Gestión y prueba de webhooks salientes con firma HMAC-SHA256. |

---

## 7. Interfaz de Usuario React 19: Inspector Dual y Grilla de 13 Columnas

### A. Inspector Dual en Pantalla Dividida (`InvoiceDetailPage.tsx`)
- Renderizado adaptativo (50% / 50% en desktop $\ge 1280\text{px}$, apilado en móvil):
  - **Panel Izquierdo (`InvoicePreview.tsx`):** Visor interactivo PDF/imagen con controles de zoom, rotación 90°, ajuste automático y paginación.
  - **Panel Derecho (`FacturaReviewGrid.tsx`):** Grilla interactiva de 13 columnas con cabeceras y primera columna congeladas (`sticky`), sincronizada reactivamente con los cálculos de empaque y stock físico.
- **Formateo Monetario:** Integración con `<MoneyBadge />` y `useCurrencyFormatter`, garantizando cero redondeos incorrectos en visualización.
- **Internacionalización:** Cobertura 100% en `invoices.json` (`es`/`en`) con estricta preservación de marcas comerciales ("Pollo King", "Savory").

---

## 8. Seguridad Ofensiva y Auditoría Red Team (11 Vectores Kali)

1. **Magic Bytes y Anti-Malware en R2:** Inspección de encabezados binarios con `FileMagicGuard` en la subida, bloqueando extensiones falsas o ejecutables encubiertos.
2. **Defensa Anti-BOLA / IDOR:** Verificación criptográfica y de tenant en cada solicitud; ninguna factura, imagen o movimiento de bodega puede ser consultada fuera del `tenant_id` autenticado.
3. **Defensa Anti-SSRF en Webhooks:** El despachador de webhooks resuelve DNS mediante validador estricto que rechaza direcciones privadas (RFC 1918), bucle local (`127.0.0.1`, `::1`) y servicios de metadatos de proveedores cloud (`169.254.169.254`).
4. **Firma Criptográfica HMAC-SHA256:** Cada evento enviado a webhooks incluye la cabecera `X-OppyTec-Signature` calculada con el secreto compartido del cliente.
5. **Sanitización XSS:** Todas las descripciones textuales y nombres de proveedores se escapan mediante `xss_sanitizer` previo a su almacenamiento y visualización.
