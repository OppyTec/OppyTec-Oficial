# Base de Conocimiento Evolutiva — Agente 06: Especialista en IA OppyFy (RAG 3-Capas, Créditos) y Motor JEV

> Lecciones aprendidas específicas de `06-ai-oppyfy-and-jev-engineer` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 3 — Motor JEV Sistema 1 y Módulo `oppy_ai`]:**
  - `MeteredJevAdapter` implementa las 3 primitivas inmutables (`decide_boolean`, `decide_choice`, `decide_score`) con tiempo de ejecución `< 500 ms`, umbral de confianza calibrado (`default=Decimal("0.85")`) y registro obligatorio en `public.llm_request_logs` con `engine_tier="SYSTEM_1_JEV"`.
  - `MeteredGeminiAdapter` construye micro-prompts quirúrgicos estilo `Pi` (60-80% menos tokens de entrada) y registra llamadas de generación (`SYSTEM_2_LLM`), embeddings (`EMBEDDING`) y audio (`AudioUsageRecord`) usando exclusivamente `decimal.Decimal`.
  - En `src/modules/oppy_ai/domain/`, se mantiene pureza 100% Clean Architecture (cero imports de infraestructura, cero `float`) en `oppyfy_rbac.py` (triple caducidad por `expires_at`, `max_prompts` y `temp_credit_ceiling`, código `"BLOCKED_UNAUTHORIZED_PROMPT"` y redacción física `"[REDACTED_COST]"` cuando `can_view_costs=False`), `credit_wallet.py` (acumulación sin caducidad `1000 + 10000 = 11000`) y `context_meter.py` (alerta preventiva `> 80%` y compactación hacia hilo fresco al `5.00%`).
  - `ThreeLayerRagService` garantiza aislamiento estricto de `document_chunks` por `oppyfy_subdomain_id` y de `spec_chunks` hacia la bóveda pública de negocio, sin referenciar jamás la bóveda de ingeniería interna.
- **[Asignación Dinámica de Modelos LLM por Complejidad Cognitiva JEV & Graphify AST]:**
  - **Lógica Matemática Cuatri-Dimensional:** $C_{task} = \min(1.0, 0.35 \cdot S_{graph} + 0.30 \cdot S_{domain} + 0.20 \cdot S_{scope} + 0.15 \cdot S_{context})$. Cómputo instantáneo (< 0.2 ms promedio) sin bloqueos I/O.
  - **Mapeo de Tiers:** $C_{task} \le 0.34 \to$ `tier_lightweight` (ahorro masivo de tokens/cuotas en tareas cosméticas o catálogos planos), $0.35 \le C_{task} \le 0.69 \to$ `tier_fast_execution` (desarrollo estándar CRUD y componentes), $C_{task} \ge 0.70 \to$ `tier_reasoning_heavy` (promoción automática de constructores a Gemini 4 Argon / Claude 3.7 Sonnet para transacciones complejas, kardex, FX, esquemas DB o seguridad).
  - **Pisos de Arquitectura Inviolables:** Agentes con roles puramente estratégicos (`02-software-architect`, `10-cybersecurity-redteam-auditor`, `11-git-worktree-merge-arbiter`) conservan su piso crítico en `tier_reasoning_heavy` y nunca son degradados ante prompts breves.
  - **Auto-escalado Reactivo (`escalate_model_tier`):** Si un subagente en tier medio falla validaciones críticas o Fast Gate < 15s por déficit de razonamiento, se escala reactivamente al tier superior de forma determinista para el siguiente intento.

  - **Aislamiento Comercial de `oppy_ai`:** En `PLAN_BASICO_10_MODULES`, `oppy_ai` está estrictamente desactivado por defecto para evitar consumos de créditos imprevistos en locales pequeños.
  - **Activación Opcional Híbrida:** El modelo soporta activación opcional mediante `TenantModulesAndQuotasUpdateRequest` (añadiendo `oppy_ai` a `enabled_modules` como add-on) o mediante upgrade formal al Plan Corporativo (`enterprise`).
  - **JEV Sistema 1 Inmutable y Transversal:** JEV opera a nivel de infraestructura para todos los tenants independientemente de su plan. Las 3 primitivas inmutables (`decide_boolean`, `decide_choice`, `decide_score`) mantienen un SLA P95 < 0.1ms (muy por debajo del SLA contractual < 5ms).
  - **Candados de Arquitectura:** `test_jev_system1_enforcement.py` valida la obligatoriedad de la evaluación JEV en todas las especificaciones de código, mientras que `test_oppyfy_telemetry_and_isolation.py` asegura que `specs/engineering-code/` jamás sea indexado en el RAG del cliente.
- **[Fase 3 — Code Mode sobre MCP para OppyFy]:**
  - **Zero-Prompt Overhead con `search_capabilities`:** El catálogo de MCP tools se expone a través de meta-herramientas token-minimal (< 150 tokens por descriptor). El LLM no requiere 50 esquemas JSON gigantes en su prompt de sistema.
  - **Ejecución y Agregación in-Sandbox:** `OppyfyCodeModeService` ejecuta scripts Python compilados en `CodeModeSandboxRunner`. Los bucles, filtros y sumas ocurren en memoria hermética, reduciendo el consumo de tokens de salida en más de un 90% (FinOps Token Reduction).
  - **Aislamiento Multi-Tenant & Anti-IDOR:** El contexto `SandboxContext` valida expresiones regulares de schema `tenant_[a-z0-9_]+` e intercepta llamadas a herramientas bloqueando intentos de consultar otros tenants (`CrossTenantAccessError` con error_code `"CROSS_TENANT_ACCESS_VIOLATION"`).
  - **Hard-Code Data Stripping Recursivo:** Si el usuario carece de `can_view_costs=True` o `"finanzas.costos.ver"`, tanto las entradas del MCP como el resultado final devuelto por el sandbox redactan físicamente todas las columnas de costo a `"[REDACTED_COST]"`.
  - **Telemetría FinOps Completa en `MeteredAIService`:** Cada invocación de Code Mode genera un `LlmUsageRecord` en `public.llm_request_logs` con `tokens_saved`, costo en USD/CLP derivado de `ai_model_configs` y duración de ejecución en milisegundos.

