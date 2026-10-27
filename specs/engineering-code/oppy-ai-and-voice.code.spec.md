---
spec_id: ENG-OPPY-AI-AND-VOICE
title: "Asistente OppyFy y Voz"
audience: engineering_internal
domain_module: oppy_ai
paired_spec: specs/business-domain/oppy-ai-and-voice.business.spec.md
jev_system1_evaluation: "Sí (Jev.choice, umbral 0.75)"
last_verified_phase: "Fase 7.6"
---

# Asistente OppyFy y Voz — Especificación de Ingeniería

## Contrato técnico

### 1. Dominio DDD (`oppytec-backend/src/modules/oppy_ai/domain/`)
- **`ContextMeter` (`domain/context_meter.py`):**
  - Entidad de cálculo determinista para la ventana de contexto de modelos LLM.
  - Umbrales semafóricos:
    - 🟢 Verde: `context_usage_percent < 65%` (operación nominal).
    - 🟡 Ámbar: `65% <= context_usage_percent <= 85%` (advertencia visual).
    - 🔴 Rojo: `context_usage_percent > 85%` (`is_input_blocked = True`).
  - Rollover asistido: `compact_thread_for_fresh_handover(thread_messages, summary_text)` emite una estructura de síntesis con un uso objetivo del `5%` de la ventana inicial para evitar alucinaciones por *Context Rot*.
- **`CreditWallet` (`domain/credit_wallet.py`):**
  - Value Objects y Entidades: `WorkerCreditWalletState`, `WalletTransactionLedger`.
  - Operaciones con precisión fija `Decimal`:
    - `deduct_worker_credits(wallet, cost_credits)` realiza la deducción atómica verificando `is_oppyfy_enabled` y cupo asignado (`assigned_credit_ceiling`).
    - Las billeteras no tienen caducidad mensual: el saldo se acumula aritméticamente (`1.000 + 10.000 = 11.000`).
- **`OppyfyRbac` (`domain/oppyfy_rbac.py`):**
  - Entidades: `OppyfyPermissionGrantSpec`, `OppyfySubdomainAccessDecision`.
  - Verificación jerárquica en dos niveles:
    1. Previo a la ejecución de herramientas: evalúa pertenencia de rol o asignación individual de usuario en `oppyfy_permission_grants`.
    2. Posterior a la obtención de datos (*Hard-Code Data Stripping*): evalúa `can_view_costs`. Si es `False`, se eliminan llaves financieras.
  - Triple condición de caducidad automática de permisos temporales:
    - `expires_at`: marca temporal UTC de vencimiento.
    - `max_prompts`: cota máxima de preguntas permitidas (`prompts_used >= max_prompts`).
    - `temp_credit_ceiling`: límite de créditos utilizables para el permiso temporal (`temp_credits_used >= temp_credit_ceiling`).
  - Constantes de resultado: `ALLOWED_PROMPT_STATUS = "ALLOWED"`, `BLOCKED_UNAUTHORIZED_PROMPT = "BLOCKED_UNAUTHORIZED_PROMPT"`, `OPPYFY_DISABLED_FOR_WORKER = "OPPYFY_DISABLED_FOR_WORKER"`.
- **`AiCreditPacks` (`domain/ai_credit_packs.py`):**
  - Entidades: `AICreditPackSpec`, `PackPurchaseQuote`.
  - Reglas de combinación con Planes Base SaaS (`/admin/plans`): descuentos porcentuales en paquetes según el nivel de suscripción y cálculo de margen comercial en USD y CLP.

---

### 2. Capa de Aplicación (`oppytec-backend/src/modules/oppy_ai/application/`)
- **`MeteredAIService` (`application/metered_ai_service.py`):**
  - Interceptor universal y obligatorio para cualquier invocación a LLMs (`SYSTEM_1_JEV`, `SYSTEM_2_LLM`, `EMBEDDING`).
  - Proceso de ejecución:
    1. Validación de RBAC del usuario y billetera mediante `OppyfyToolRouter` y `evaluate_oppyfy_subdomain_access`.
    2. Detección de intentos de inyección de prompt mediante el cortafuegos JEV (`decide_boolean`, umbral 0.85).
    3. Enrutamiento cognitivo de intención mediante JEV (`decide_choice`, umbral 0.75).
    4. Consulta RAG en 3 capas a través de `ThreeLayerRagService`.
    5. Invocación de herramientas operativas en código duro si la consulta es analítica.
    6. *Hard-Code Data Stripping*: purga de campos sensibles financieros si `can_view_costs == False`.
    7. Registro asíncrono o transaccional ineludible en `public.llm_request_logs` con `Decimal` exacto (`NUMERIC(14,6)` USD, `NUMERIC(14,2)` CLP, `NUMERIC(12,2)` créditos).
    8. Emisión de spans de observabilidad OpenTelemetry (`oppyfy.query`, `oppyfy.tool_router`, `oppyfy.data_stripping`, `oppyfy.metered_ai`).
- **`ThreeLayerRagService` (`application/rag_service.py`):**
  - **Capa 1 (Memoria de Sesión):** Ventana móvil con compresión de historial y evaluación semafórica de tokens.
  - **Capa 2 (Herramientas Operativas Deterministas):** Ejecución directa en Python sobre el esquema `tenant_*` (excluida de la caché por dinamismo transaccional).
  - **Capa 3 (Documentación y Memoria Semántica):**
    - Capa 3A: Bóveda pública de negocio `specs/business-domain/` vectorizada en `public.spec_chunks` (768 dims, pgvector con índice HNSW). **Muro de Fuego Anti-Fuga:** Queda estrictamente prohibida la indexación de `specs/engineering-code/` o código fuente.
    - Capa 3B: Documentos privados del tenant (`tenant_*.tenant_documents`).
    - Capa 3C: Hábitos y directivas del establecimiento (`tenant_*.tenant_ai_memory`).
  - Caché semántica en dos niveles: L1 Redis en memoria (TTL 48h) + L2 pgvector para preguntas conceptuales recurrentes.
- **`OppyfyToolRouter` (`application/tool_router.py`):**
  - Mapeo de intenciones a funciones tipadas en `operational_tools/`:
    - `inventory_tools.py`: `get_stock_health_and_reorder_alerts`, `get_expiring_batches_fefo`.
    - `procurement_tools.py`: `evaluate_supplier_lead_times_and_price_drift`, `build_optimal_purchase_order_draft`.
    - `events_tools.py`: `analyze_event_supply_feasibility`.
    - `waste_tools.py`: `get_sales_and_food_cost_variance`, `analyze_waste_and_merma_impact`.
    - `canvas_tools.py`: `render_canvas_table`, `render_canvas_chart`.
  - Cero generación de Text-to-SQL libre por el modelo.
- **`TokenConsumptionService` (`application/token_consumption_service.py`):**
  - Motor de agregación FinOps para el panel `Platform Admin` (`/admin/token-consumption`).
  - Agrupación por holding, tenant, modelo LLM, feature llamante y rango de fechas.
  - Cálculo de margen bruto: $\text{Margen} = \text{Ingresos Paquetes} - \text{Costo Real Proveedor (USD/CLP)}$.
- **`AiCreditPacksService` (`application/ai_credit_packs_service.py`):**
  - Gestión del catálogo de paquetes add-on independientes en `public.ai_credit_packs`.
  - Simulación y cotización de packs con reglas de descuento por plan base SaaS.

---

### 3. Persistencia e Infraestructura (`oppytec-backend/src/modules/oppy_ai/infrastructure/`)
- **Esquema Compartido `public` (`infrastructure/models.py`):**
  - `public.llm_request_logs`:
    - `id` (BigInteger PK autoincrementable).
    - `created_at` (DateTime UTC con server_default `func.now()`).
    - `holding_id` (UUID), `tenant_id` (UUID), `tenant_schema` (String 100), `user_id` (Integer).
    - `thread_id` (UUID nullable).
    - `engine_tier` (String 32: `SYSTEM_1_JEV`, `SYSTEM_2_LLM`, `EMBEDDING`).
    - `caller_feature` (String 64: `oppyfy_chat`, `tool_router`, `invoice_ocr`).
    - `model_name` (String 64).
    - `input_tokens`, `cached_tokens`, `output_tokens`, `total_tokens` (Integer).
    - `provider_cost_usd` (`Numeric(14, 6)` con garantía `Decimal`).
    - `provider_cost_clp` (`Numeric(14, 2)` con garantía `Decimal`).
    - `credits_deducted` (`Numeric(12, 2)` con garantía `Decimal`).
    - `request_duration_ms` (Integer), `api_success` (Boolean), `error_message` (Text nullable).
  - `public.audio_request_logs`: Telemetría STT/TTS con duración en segundos y costos monetarios en `Decimal`.
  - `public.ai_model_configs`: Tarifas por millón de tokens (`input_cost_per_1m_usd`, `cached_cost_per_1m_usd`, `output_cost_per_1m_usd`, `embedding_cost_per_1m_usd`).
  - `public.ai_credit_packs` y `public.ai_credit_packages`: Catálogo de paquetes add-on acumulables sin caducidad.
  - `public.spec_sync_metadata` y `public.spec_chunks`: Embeddings vectoriales (768 dims, pgvector HNSW) asociados exclusivamente a `specs/business-domain/`.
- **Esquema Aislado de Tenant `tenant_*` (`infrastructure/models.py`):**
  - `oppyfy_domains`: Árbol de dominios configurables (`id`, `domain_key`, `name_es`, `name_en`, `icon`, `is_active`, `sort_order`).
  - `oppyfy_subdomains`: Subdominios vinculados a herramientas de código duro (`allowed_tool_functions`, `can_view_costs_default`, `module_slug`).
  - `oppyfy_permission_grants`: Permisos granulares por usuario o rol con triple caducidad (`expires_at`, `max_prompts`, `prompts_used`, `temp_credit_ceiling`, `temp_credits_used`, `can_view_costs`).
  - `oppyfy_worker_credit_wallets`: Cuotas y saldos por trabajador (`assigned_credit_ceiling`, `credits_spent_total`, `is_oppyfy_enabled`, `balance_override`).
  - `oppyfy_prompt_audit_log`: Bitácora inmutable Append-Only de consultas enviadas (`prompt_text`, `status` [ALLOWED|BLOCKED], `resolved_domain`, `resolved_tools`, `tokens_spent`, `credits_deducted`).
  - `oppyfy_rbac_audit_log`: Registro de asignaciones y modificaciones de gobernanza (`actor_user_id`, `target_user_id`, `action`, `details`).
  - `ai_chat_threads` y `ai_chat_messages`: Hilos de conversación y mensajes con metadatos de tokens y resumen de rollover.

---

### 4. Capa de Presentación REST RFC 7807 (`src/modules/oppy_ai/presentation/router.py`)
- `POST /api/v1/oppyfy/chat`:
  - Entrada: `OppyfyChatRequest` (`prompt_text`, `thread_id`, `subdomain_slug`).
  - Procesamiento: Validación RBAC, router JEV, ejecución de herramientas, stripping de costos y deducción atómica de créditos.
  - Salida: `OppyfyChatResponse` (`response_text`, `context_usage_percent`, `is_context_critical`, `credits_deducted`, `canvas_payload`).
- `POST /api/v1/oppyfy/threads/{thread_id}/rollover`:
  - Compactación inteligente del historial anterior y apertura de nuevo hilo fresco al 5% de contexto.
- `GET /api/v1/oppyfy/rbac/domains` y `POST /api/v1/oppyfy/rbac/domains`:
  - Consulta y administración del árbol de dominios/subdominios de OppyFy.
- `POST /api/v1/oppyfy/rbac/grants`:
  - Otorgamiento y actualización de permisos temporales con triple caducidad.
- `GET /api/v1/oppyfy/wallets/me` y `PATCH /api/v1/oppyfy/wallets/{user_id}`:
  - Consulta de saldo personal y administración de cuotas de créditos por trabajador.
- `GET /api/v1/oppyfy/telemetry/logs`:
  - Visor de auditoría de prompts (`oppyfy_prompt_audit_log`) para administradores del restaurante.
- `GET /api/v1/platform-admin/token-consumption`:
  - Consola FinOps de consumo de tokens, costos reales de proveedores y márgenes brutos de plataforma.
- `GET /api/v1/platform-admin/ai-packs` y `POST /api/v1/platform-admin/ai-packs`:
  - CRUD de paquetes de créditos de IA en Platform Admin.
- `GET /api/v1/platform-admin/ai-packs/{pack_id}/quote`:
  - Cotización con reglas de combinación ("hacer juego") según el plan SaaS contratado.

---

### 5. Frontend UI/UX (`oppytec-frontend/src/features/oppyfy/`)
- **Hooks Reactivos:**
  - `useOppyfyChat.ts`: Gestión de hilos de conversación, envío de preguntas, streaming reactivo y monitoreo continuo de `context_usage_percent`.
  - `useOppyfyRbac.ts` & `useOppyfyGovernance.ts`: Mutación del árbol de dominios, asignación de permisos temporales y auditoría de consultas.
  - `useOppyfyCredits.ts`: Consulta reactiva del saldo disponible, consumo histórico y cupo asignado al usuario.
- **Componentes Visuales:**
  - `ContextHealthMeter.tsx`: Anillo circular semafórico (<65% verde, 66-85% ámbar, >85% rojo con bloqueo de input).
  - `OppyfyChatPane.tsx`: Espacio principal de conversación con renderizado Markdown y citaciones a especificaciones.
  - `OppyfyCanvasPanel.tsx`: Panel lateral en pantalla dividida (*Split-View*) para tablas Recharts interactivas y exportación de datos.
  - `OppyfyRolloverModal.tsx`: Diálogo guiado para iniciar un hilo limpio preservando la síntesis estructurada al 5% de contexto.
  - `OppyfyGovernancePanel.tsx`: Panel de gobernanza con árbol drag-and-drop de dominios, asignación de permisos temporales y bitácora de auditoría.

---

### 6. Observabilidad OpenTelemetry y Sanitización PII
- **Spans Semánticos:**
  - `oppyfy.query`: Span raíz con atributos `tenant.schema`, `user.id`, `thread.id`, `prompt.status`, `tokens.total`, `credits.deducted`.
  - `oppyfy.tool_router`: Span de selección de herramienta con `tool.selected` y `router.duration_ms`.
  - `oppyfy.data_stripping`: Span de sanitización con `costs.redacted: bool` y `fields.scrubbed_count: int`.
  - `oppyfy.metered_ai`: Span de proveedor LLM con `provider.model`, `provider.cost_usd`, `tokens.input`, `tokens.output`.
  - `oppyfy.tool.<tool_name>`: Spans individuales emitidos por cada una de las 9 herramientas operativas en `operational_tools/`.
- **Garantía Zero-Float:** Ningún atributo financiero o de créditos en OpenTelemetry puede ser tipo `float` (uso estricto de `Decimal` o string formateado).
- **Sanitización de PII:** Purgado automático de emails, números de teléfono, RUTs, números de tarjetas bancarias y claves sin alterar nombres propios comerciales (`"Pollo King"`).

---

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.choice`
- Umbral de confianza: `0.75` (bajo umbral → camino determinista seguro o rechazo por falta de claridad).
- Justificación: JEV Sistema 1 clasifica y enruta la intención del usuario hacia la herramienta operativa especializada o hacia el RAG funcional en 70-500 ms con costo infinitesimal antes de activar el modelo de lenguaje de Sistema 2.

---

## Pruebas (Co-Creación 1:1)
- **Unitarias de Dominio:** `oppytec-backend/tests/unit/modules/test_oppy_ai_domain.py`
- **Unitarias de Servicios y RAG:** `oppytec-backend/tests/unit/modules/test_oppy_ai_services.py`
- **Unitarias de Observabilidad y Telemetría:** `oppytec-backend/tests/unit/modules/test_oppyfy_observability.py`
- **Integración de API REST:** `oppytec-backend/tests/unit/modules/test_oppy_ai_api.py`
- **Arquitectura de Caja Blanca:** `oppytec-backend/tests/architecture/test_oppyfy_telemetry_and_isolation.py`
- **Sincronización Bipartita:** `oppytec-backend/tests/architecture/test_openspec_bipartition_and_sync.py`
- **Seguridad Ofensiva Red Team:** `oppytec-backend/tests/security_redteam/test_08_ai_prompt_injection_and_rag_isolation.py`
- **Frontend Vitest:** `oppytec-frontend/src/features/oppyfy/__tests__/useOppyfyHooks.test.ts`, `OppyfyView.test.tsx`, `OppyfyGovernance.test.tsx`, `OppyfyI18nAndFx.test.tsx`
