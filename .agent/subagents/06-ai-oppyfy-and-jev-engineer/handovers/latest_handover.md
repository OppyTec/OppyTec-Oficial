# Reporte de Traspaso (`Handover`) — Agente 06: AI, OppyFy, FinOps & JEV Engineer

- **Fecha UTC:** 2026-11-07T01:30:00Z
- **Agente:** Agente 06 (`06-ai-oppyfy-and-jev-engineer`)
- **Fase / Módulo:** ETAPA 3 — Auditoría y Certificación de Aislamiento Clean Slate en IA (`oppy_ai`, `OppyFy`, `FinOps` y `JEV`) bajo ADR-022 y AGENTS.md.
- **Estado de Certificación:** `APPROVED_CLEAN_SLATE_HERMETIC_AND_GENESIS_INTACT` (0 logs sintéticos de tokens/JEV, 0 créditos gastados ficticios, `[]` en hilos/grants/wallets en modo Clean Slate; preservación íntegra de los 6 modelos fundacionales de IA y la política SaaS singleton como configuración Génesis del sistema; 34/34 tests backend y 121/121 tests frontend en verde).

---

## 1. Completed (Qué se auditó, verificó y certificó)

### 1.1 Pre-Ejecución Graphify AST Navigator
- Ejecución determinista de consultas de grafo previas a la auditoría:
  * `python3 scripts/harness.py nav "oppy_ai"`: Validada vecindad con `app:backend_main`, `service:ai_model_catalog`, `service:holding_briefing`, `core:jev_system1`, `core:code_mode_sandbox`, `core:mcp_bridge` y `openspec:business_domain_vault`.
  * `python3 scripts/harness.py nav "ai_model"`: Validada sincronización con `frontend:ai_models_page`, `migration:0012_public_ai_model`, `service:ai_model_catalog`, `suite:ai_model_catalog_unit_test`, `suite:ai_model_catalog_observability_test` y `suite:ai_model_catalog_security_test`.

### 1.2 Catálogo Fundacional de Modelos IA y Política Base SaaS (Génesis)
- **Preservación Invariable:**
  * En modo Clean Slate (`purge_all_runtime_mock_stores()` y `clean_and_seed_genesis_db.py`), el catálogo de 6 modelos LLM y motores cognitivos permanece 100% intacto como configuración Génesis del sistema en `public.ai_model_configs`:
    1. `gemini-3.8-flash` (Google DeepMind, SYSTEM_2_LLM, Default)
    2. `gemini-4-argon` (Google DeepMind, SYSTEM_2_LLM)
    3. `claude-3-7-sonnet` (Anthropic, SYSTEM_2_LLM)
    4. `gpt-4o` (OpenAI, SYSTEM_2_LLM, Fallback)
    5. `jev-fast-classifier` (JEV Internal, SYSTEM_1_JEV)
    6. `text-embedding-004` (Google DeepMind, EMBEDDING)
  * La política global SaaS singleton (`public.saas_ai_policy_config` con `id=1`, `tokens_per_credit=1000`, `default_monthly_credits=2000`) se conserva intacta sin ser vaciada.
  * Cero números de coma flotante (`float`): Todas las tarifas se manejan en `Decimal` con precisión de 6 decimales (`NUMERIC(14,6)`).

### 1.3 Endpoints y Vistas FinOps de Consumo de Tokens y JEV
- **Consumo de Tokens (`/api/v1/platform-admin/token-consumption` y `TokenConsumptionPage`):**
  * Al recibir `X-OppyTec-Mock-Mode: clean`, se filtran los registros demostrativos (`id < 100` y `DEMO_HOLDING_IDS`), retornando exactamente `holdings: []`, `logs: []`, `total_records: 0`, `total_tokens_all: 0`, `total_cost_usd_all: 0.000000`, `total_credits_used_all: 0`.
  * En frontend, `useTokenConsumption` conmuta automáticamente a `CLEAN_TOKEN_CONSUMPTION` renderizando el estado vacío sin inyectar datos sintéticos.
- **Consumo de Decisiones JEV (`/api/v1/platform-admin/jev-consumption` y `JevConsumptionPage`):**
  * Con `X-OppyTec-Mock-Mode: clean`, filtra los logs con prefijo `"jev-log-00"` y holdings demo, retornando `holdings: []`, `tenants: []`, `all_logs: []`, `total_decisions_all: 0`, `total_cost_usd_all: 0.000000`, `estimated_savings_usd_all: 0.000000`.
  * En frontend, `useJevConsumption` utiliza `CLEAN_JEV_CONSUMPTION` desplegando la consola en cero absoluto de actividad.

### 1.4 Gobernanza OppyFy y Espacio de Trabajo Inmersivo
- **Backend (`src/modules/oppy_ai/presentation/router.py`):**
  * `GET /api/v1/oppyfy/wallets/me` y `GET /api/v1/oppyfy/credits/wallet`: Actualizados para detectar `is_clean_slate_active()` o `X-OppyTec-Mock-Mode: clean`, retornando para usuarios sin billetera previa un estado virgen de `0.00` créditos asignados y `0.00` créditos consumidos (evitando inyecciones arbitrarias de 100/12.5).
  * `GET /api/v1/oppyfy/rbac/domains`: Retorna `[]` en modo Clean Slate.
  * `GET /api/v1/platform-admin/ai-packs`: Retorna `[]` en modo Clean Slate.
  * `GET /api/v1/oppyfy/telemetry/logs`: Retorna `[]` en modo Clean Slate.
  * `_worker_wallets_store.clear()` y `_permission_grants_store.clear()` ejecutados atómicamente por `purge_all_runtime_mock_stores()`.
- **Frontend (`oppytec-frontend/src/features/oppyfy/`):**
  * `useOppyfyGovernance`: Estado reactivo a `isMockDataEnabled()`. En modo clean, `localDomains = []`, `localGrants = []`, `localWorkers = []`, `localAuditLogs = []`, `tenantCreditBag = { total_purchased_credits: 0, total_allocated_credits: 0, total_consumed_credits: 0, remaining_pool_credits: 0 }`.
  * `useOppyfyChat`: En modo clean, `messages = []`, `threads = []`, `remainingCredits = 0`, `contextPct = 0`.
  * `OppyFyFeatureView`: Despliega estados vacíos limpios y dominios en `[]`.
  * `OppyfyWorkspacePage`: Despliega el espacio de trabajo inmersivo con `0` hilos sintéticos, `0` mensajes pre-poblados, `contextPct: 0` y `remainingCredits: 0` cuando el modo es clean.

### 1.5 Evidencias Automatizadas y Quality Gates
- **Backend Pytest:**
  * `pytest oppytec-backend/tests/unit/modules/test_oppy_ai_api.py oppytec-backend/tests/unit/modules/test_ai_model_catalog.py oppytec-backend/tests/unit/test_mock_data_manager.py`: **34/34 tests pasados (100% verde)**.
- **Frontend Vitest:**
  * `vitest run src/features/oppyfy`: **6 suites, 70/70 tests pasados (100% verde)**.
  * `vitest run src/features/platform-admin/tokens src/features/platform-admin/jev src/features/platform-admin/ai-models`: **4 suites, 51/51 tests pasados (100% verde)**.
  * Total pruebas frontend ejecutadas y certificadas: **121 tests pasados**.
- **Graphify Synchronizer:** Ejecutado deterministamente vía `python3 scripts/harness.py sync-graph` (151 nodos, 196 aristas indexadas).

---

## 2. Friction & Failures (Dificultades y Resoluciones)

- **Fricción 1 (Fallback en Router Backend para Billetera Me):** Se identificó que `get_my_oppyfy_wallet_endpoint` utilizaba un fallback con `allocated_credits=Decimal("100.00")` y `consumed_credits=Decimal("12.50")` cuando el trabajador no estaba registrado en `_worker_wallets_store`, lo que generaba créditos sintéticos no deseados en modo Clean Slate.
  * **Solución:** Se añadió detección de `is_clean_slate_active()` y lectura del header `X-OppyTec-Mock-Mode: clean`, devolviendo una billetera virgen con `0.00` créditos en modo Clean Slate y conservando el fallback demo solo cuando el modo demostrativo esté explícitamente activo.
- **Fricción 2 (Preservación del Catálogo IA vs Mock Purge):** Era crítico asegurar que `purge_all_runtime_mock_stores()` no eliminara el catálogo de 6 modelos LLM/JEV de `AiModelCatalogService`, ya que los modelos constituyen infraestructura fundacional del sistema y no datos de prueba de un tenant.
  * **Solución:** Se verificó que `AiModelCatalogService` no sea vaciado en la purga y que conserve siempre los 6 modelos canónicos iniciales, validado exhaustivamente mediante `test_ai_model_catalog.py` (19 tests).

---

## 3. Next Steps & Instructions for Peer Agents

1. **Hacia Agente 07 (`07-i18n-and-fx-currency-specialist`):**
   - Certificar la paridad bilingüe `es`/`en` en los estados vacíos (*Empty States*) de las consolas de consumo de tokens y JEV cuando `total_records == 0`.
2. **Hacia Agente 08 (`08-environments-and-observability-engineer`):**
   - Confirmar que las trazas de OpenTelemetry en `platform_admin.token_consumption` y `platform_admin.jev_consumption.query` se emitan con atributos normalizados (`total_records: 0`) sin generar errores ni alertas de anomalía en Clean Slate.
3. **Hacia Agente 09 (`09-qa-parity-and-test-engineer`):**
   - Validar que las suites de integración y pruebas E2E mantengan el aislamiento de fixtures y utilicen `reset_default_demo_stores()` al requerir escenarios demostrativos.
4. **Hacia Agente 10 (`10-cybersecurity-redteam-auditor`):**
   - Los endpoints de IA y gobernanza OppyFy mantienen protección RBAC estricta con permisos de 3 niveles (`oppyfy.credits.read`, `oppyfy.rbac_domains.read`, `platform_admin.tokens.read`, `platform_admin.ai_models.read`).
