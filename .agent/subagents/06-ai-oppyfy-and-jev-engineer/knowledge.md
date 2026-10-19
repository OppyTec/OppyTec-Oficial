# Base de Conocimiento Evolutiva — Agente 06: Especialista en IA OppyFy (RAG 3-Capas, Créditos) y Motor JEV

> Lecciones aprendidas específicas de `06-ai-oppyfy-and-jev-engineer` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 3 — Motor JEV Sistema 1 y Módulo `oppy_ai`]:**
  - `MeteredJevAdapter` implementa las 3 primitivas inmutables (`decide_boolean`, `decide_choice`, `decide_score`) con tiempo de ejecución `< 500 ms`, umbral de confianza calibrado (`default=Decimal("0.85")`) y registro obligatorio en `public.llm_request_logs` con `engine_tier="SYSTEM_1_JEV"`.
  - `MeteredGeminiAdapter` construye micro-prompts quirúrgicos estilo `Pi` (60-80% menos tokens de entrada) y registra llamadas de generación (`SYSTEM_2_LLM`), embeddings (`EMBEDDING`) y audio (`AudioUsageRecord`) usando exclusivamente `decimal.Decimal`.
  - En `src/modules/oppy_ai/domain/`, se mantiene pureza 100% Clean Architecture (cero imports de infraestructura, cero `float`) en `oppyfy_rbac.py` (triple caducidad por `expires_at`, `max_prompts` y `temp_credit_ceiling`, código `"BLOCKED_UNAUTHORIZED_PROMPT"` y redacción física `"[REDACTED_COST]"` cuando `can_view_costs=False`), `credit_wallet.py` (acumulación sin caducidad `1000 + 10000 = 11000`) y `context_meter.py` (alerta preventiva `> 80%` y compactación hacia hilo fresco al `5.00%`).
  - `ThreeLayerRagService` garantiza aislamiento estricto de `document_chunks` por `oppyfy_subdomain_id` y de `spec_chunks` hacia la bóveda pública de negocio, sin referenciar jamás la bóveda de ingeniería interna.
