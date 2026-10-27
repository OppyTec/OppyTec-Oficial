# Base de Conocimiento Evolutiva — Agente 07: Especialista en Internacionalización (i18n) y Multi-Moneda (FX)

> Lecciones aprendidas específicas de `07-i18n-and-fx-currency-specialist` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 3]:** Paridad de locales es/en se valida por archivos, llaves y variables `{{var}}`; FX sin `float` (solo Decimal, quantize 1e-8); RBAC realtime siempre server-side. Ejecutar checks `uv run` por separado (encadenados se cuelgan).
- **[Auditoría Plan Maestro - Cuotas y Planes SaaS]:**
  - Modelos y schemas de planes comerciales (`SystemPlan`, `SystemPlanResponse`, `SystemPlanUpsertRequest`) cumplen la regla inviolable de 0 `float`, empleando `Decimal` en todas las monedas ancla y derivadas (`price_clp`, `price_usd`, `price_eur`, `price_brl`).
  - Paridad 1:1 total entre `locales/es/*.json` y `locales/en/*.json` en backend (`common.json`, `errors.json`) y frontend (11 namespaces) con idénticos marcadores de interpolación `{{var}}`.
  - Fallback y remapeo inteligente en `translator.py`: Soporta `module:errors.sub_key` resolviéndolo en `errors.json` bajo la clave `module.sub_key`, permitiendo que excepciones con `default_i18n_key = "tenancy:errors.seat_quota_exceeded"` se traduzcan de inmediato sin requerir un catálogo separado por micro-módulo.
  - Vistas de administración (`AdminPlansView` en `AdminManagementViews.tsx`) parametrizadas con `translateKey("platform_admin", ...)` y formateo monetario exacto vía `<MoneyBadge amount={String(price)} baseCurrency="CLP" />`.
- **[Fase 7 — Plan Maestro Gestión Submódulos (Pedidos, Proveedores 360° y Mermas Analíticas)]:**
  - Paridad 1:1 recursiva total entre `es/procurement.json` y `en/procurement.json` cubriendo las 14 secciones de los 3 submódulos (`orders`, `dashboard`, `reception`, `incidences`, `catalog`, `draft`, `suppliers`, `supplierDialog`, `supplierCatalog`, `supplierDashboard`, `wasteAnalytics`, `kpiDashboard`, `mermaStats`, `mermaHistory`, `dateRangePicker`), además de las pestañas `pedidos` y `mermas` en `gestion.json`, `inventory.json` y `recipes.json`.
  - Regla "Pollo King" reforzada en `IMMUTABLE_PROPER_NOUNS` (`config.ts`) incluyendo razones sociales de proveedores (`"Distribuidora Austral Food SpA"`, `"Agrícola y Comercial Valle Central Ltda"`, `"Lácteos del Sur S.A."`, `"Importadora y Distribuidora Gourmet Pacific"`) para impedir traducciones accidentales en `resolveDynamicFieldI18n`.
  - Exportado alias `formatMoney` junto a `formatCurrencyAmount` y `useCurrencyFormatter` en `src/shared/currency/`, manteniendo 0 floats contables en todos los cálculos de OC, precios pactados y PPP de mermas.
