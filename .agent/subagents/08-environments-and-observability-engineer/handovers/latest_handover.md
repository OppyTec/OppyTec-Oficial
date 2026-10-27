# Reporte de Traspaso (`Handover`) — Agente 08: Especialista en 5 Entornos y Observabilidad 4-Pilares

- **Fecha UTC:** 2026-10-26T20:15:00Z
- **Fase:** Fase 7 — Tarea 7.3: Observabilidad OpenTelemetry y Sanitización PII para OppyFy (`PLAN_MAESTRO_OPPYFY_AI.md`)
- **Estado de Certificación:** `OPPYFY_OPENTELEMETRY_AND_PII_SANITIZATION_CERTIFIED` (8/8 tests de observabilidad OppyFy 100% verdes, 29/29 tests de regresión suites relacionadas 100% verdes).

## 1. Completed (Qué se hizo)
- **Instrumentación de Spans Semánticos OpenTelemetry en `OppyFy`:**
  - `oppyfy.query` (Span raíz en `MeteredAIService.execute_oppyfy_query`):
    - Atributos semánticos: `tenant.schema`, `user.id`, `thread.id`, `prompt.status`, `tokens.total`, `credits.deducted`.
    - Garantía Zero-Float: `credits.deducted` formateado estrictamente como string Decimal (e.g. `"1.00"` / `"0.00"`), nunca `float`.
  - `oppyfy.tool_router` (Span en `OppyfyToolRouter.classify_tool_and_subdomain`):
    - Atributos semánticos: `tool.selected` (código de herramienta seleccionado), `router.duration_ms` (duración exacta en ms de clasificación JEV).
  - `oppyfy.data_stripping` (Span en `OppyfyToolRouter.execute_hardcoded_tool`):
    - Atributos semánticos: `costs.redacted: bool` (indica si se aplicó redacción de costos por RBAC `can_view_costs=False`), `fields.scrubbed_count: int` (conteo exacto de campos reemplazados por `"[REDACTED_COST]"`).
  - `oppyfy.metered_ai` (Span en Paso 5 de `MeteredAIService.execute_oppyfy_query`):
    - Atributos semánticos: `provider.model`, `provider.cost_usd` (formateado con 6 decimales como string Decimal, cero `float`), `tokens.input: int`, `tokens.output: int`.
  - Spans de herramientas operativas (`operational_tools/`):
    - Instrumentadas las 9 herramientas con span semántico `oppyfy.tool.<tool_name>`:
      * `oppyfy.tool.get_stock_health_and_reorder_alerts`
      * `oppyfy.tool.get_expiring_batches_fefo`
      * `oppyfy.tool.evaluate_supplier_lead_times_and_price_drift`
      * `oppyfy.tool.build_optimal_purchase_order_draft`
      * `oppyfy.tool.analyze_event_supply_feasibility`
      * `oppyfy.tool.get_sales_and_food_cost_variance`
      * `oppyfy.tool.analyze_waste_and_merma_impact`
      * `oppyfy.tool.render_canvas_table`
      * `oppyfy.tool.render_canvas_chart`
- **Sanitización Estricta PII y Regla Pollo King (`src/core/observability.py`):**
  - Incorporadas exclusiones semánticas en `_is_sensitive_key` (`AI_METRIC_KEY_EXEMPTIONS`) para que contadores LLM (`tokens.total`, `tokens.input`, `tokens.output`, `tokens.*`) permanezcan tipados como `int` y no sean censurados como tokens de autenticación.
  - Añadidos tokens sensibles `"card_number"` y `"tarjeta"` a `SENSITIVE_KEY_TOKENS`.
  - Mejorado `_CREDIT_CARD_PATTERN` con soporte para tarjetas de 15 y 16 dígitos.
  - Creada métrica determinista `OppyfyOperationMetric` acumulable en `_in_memory_oppyfy_metrics`.
  - Verificada la preservación inmutable de la razón social `"Pollo King SpA"` sin redacción PII.
- **Suite de Pruebas Unitarias de Observabilidad:**
  - Creada `oppytec-backend/tests/unit/modules/test_oppyfy_observability.py` con 8 tests completos:
    1. `test_oppyfy_full_query_semantic_spans_success`: flujo exitoso con jerarquía completa de spans.
    2. `test_oppyfy_query_with_costs_allowed`: `can_view_costs=True` genera `costs.redacted=False` y `fields.scrubbed_count=0`.
    3. `test_oppyfy_query_blocked_by_rbac_observability`: bloqueo RBAC emite `BLOCKED_UNAUTHORIZED_PROMPT` y cero cobro sin spans hijos.
    4. `test_oppyfy_query_blocked_by_injection_guard`: bloqueo anti-inyección JEV emite `BLOCKED_UNAUTHORIZED_PROMPT` y telemetría de bloqueo.
    5. `test_oppyfy_query_blocked_disabled_worker`: bloqueo de billetera inactiva o sin cupo emite status correspondiente.
    6. `test_oppyfy_strict_pii_scrubbing_and_brand_preservation`: scrubbing de correos, tarjetas, teléfonos, RUTs y contraseñas.
    7. `test_oppyfy_zero_float_financial_metrics_guarantee`: garantía de cero float en todas las métricas financieras de OTel.
    8. `test_operational_tools_direct_span_emission`: emisión correcta de spans en las 9 herramientas operativas.
- **Ejecución y Verificación 100% Verde:**
  - `oppytec-backend/.venv/bin/pytest oppytec-backend/tests/unit/modules/test_oppyfy_observability.py` -> **8 passed in 0.20s (100% verde)**.
  - Verificación conjunta con tests de arquitectura y módulos de OppyFy: **29 passed in 0.33s (100% verde)**.

## 2. Friction & Failures (Qué cuidar)
- En `WorkerCreditWalletState`, los argumentos del constructor dataclass son `user_id`, `allocated_credits`, `consumed_credits`, `is_oppyfy_enabled`, y `assigned_credit_ceiling`. No se debe confundir con el modelo ORM `OppyfyWorkerCreditWallet` que posee `wallet_id` y `spent_credits`.

## 3. Next Exact Action
- Enviar reporte final al agente orquestador/parent (`d0212433-cb68-4d01-aea7-ef017fe152b9`).
