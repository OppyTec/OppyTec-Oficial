# Reporte de Traspaso (`Handover`) — Agente 02: Arquitecto de Software DDD & Clean Architecture

- **Fecha UTC:** 2026-11-04T21:40:00+00:00
- **Módulo:** OppyFy AI — Evaluación Sistemática (Evals), Observabilidad Especializada LLM y Captura de Feedback RLHF (`oppytec-backend/src/modules/oppy_ai/`)
- **Fase:** Etapa 1 — Arquitectura de Dominio DDD, Value Objects Inmutables, Entidades/Agregados, Excepciones y Contratos Ports (Protocols)

---

## 1. Completed (Qué se realizó)

1. **Pre-ejecución Graphify (Regla 6):**
   - Ejecutadas consultas deterministas AST con `python scripts/harness.py nav "MeteredAIService"` y `python scripts/harness.py nav "RagService"`.

2. **Capa de Dominio DDD de AI Evals y Observabilidad (`oppytec-backend/src/modules/oppy_ai/domain/evals.py`):**
   - **Value Objects Inmutables:**
     - `EvalScore`: Wrapper inmutable de puntuación normalizada `[0.00, 1.00]` con validación estricta, comparación nativa y prohibición absoluta de tipos `float` (100% `Decimal`).
     - `EvalMetricThresholds`: Encapsula los SLAs y umbrales mínimos inviolables:
       - `min_faithfulness: Decimal = Decimal("0.85")`
       - `min_relevance: Decimal = Decimal("0.85")`
       - `min_context_precision: Decimal = Decimal("0.80")`
       - `max_hallucination_rate: Decimal = Decimal("0.05")`
       - `max_critical_hallucination_rate: Decimal = Decimal("0.00")` (Tolerancia Cero en costos, alérgenos y stock FEFO).
       - Métodos: `is_passing(...) -> bool` (determinista para CI/CD) y `validate_or_raise(...)` (lanzando `EvalThresholdNotMetError` con desglose exacto de métricas reprobadas).
     - `TraceContext`: Contexto inmutable W3C distribuido: `trace_id` (32 hex), `span_id` (16 hex), `tenant_id` (UUID), `user_id` (UUID | None), `tags` (dict[str, str]), `start_time` (datetime UTC).
       - Método `w3c_traceparent() -> str` (`00-{trace_id}-{span_id}-01`).
       - Factory `create(...)` para instanciación segura y trazabilidad correlacionada con Langfuse y OpenTelemetry / Tempo.
   - **Entidades y Agregados:**
     - `AIEvalCaseResult`: Representa el resultado individual de un caso del Golden Dataset (fidelidad, relevancia, precisión de contexto, latencia ms, alucinación general y crítica).
     - `AIEvalBenchmark`: Agregado Raíz para corridas completas de evaluación. Métodos `add_case_result(...)` y `recalculate_aggregates(...)` con aritmética de promedios cuantitativa en `Decimal` (`Decimal("0.0001")`), propiedad `pass_rate_percent` y evaluación automática de cumplimiento de Quality Gate (`passed_thresholds`).
     - `AIChatFeedback`: Entidad para captura de feedback humano de operadores gastronómicos (RLHF / UCB) vinculada a `trace_id`. Valida `feedback_type: Literal["positive", "negative"]` y `failure_category: Literal["hallucination", "incomplete", "math_error", "bad_formatting", "other"]`, rechazando categorías en feedbacks positivos e invalidando calificaciones que no sean enteros.
   - **Excepciones de Dominio:**
     - `AIEvalDomainError`: Excepción base del dominio.
     - `EvalThresholdNotMetError`: Falla de Quality Gate con diccionario detallado `details`.
     - `InvalidFeedbackPayloadError`: Payload de feedback inválido.
     - `TracerConfigurationError`: Identificadores o configuración de trazas W3C inválidos.

3. **Puertos de Arquitectura Limpia (`oppytec-backend/src/modules/oppy_ai/domain/ports.py`):**
   - `LLMTracerPort` (`@runtime_checkable Protocol`): Abstracción desacoplada para telemetría: `trace_generation(...)`, `trace_tool_call(...)`, `record_feedback(...)` y `flush(...)`.
   - `LLMEvalSuitePort` (`@runtime_checkable Protocol`): Abstracción para ejecución de suites de evaluación: `run_suite(...)` y `evaluate_case(...)`.
   - `AIChatFeedbackRepositoryPort` (`@runtime_checkable Protocol`): Abstracción para persistencia transaccional: `save_feedback(...)`, `list_feedback(...)` y `get_by_trace_id(...)`.

4. **Exportación Canónica en `domain/__init__.py`:**
   - Registrados e indexados todos los tipos, clases, protocolos y constantes en `__all__` preservando la compatibilidad retroactiva completa con el catálogo de modelos, billeteras y RBAC.

5. **Testing Unitario y Verificación Arquitectónica:**
   - Creada suite `oppytec-backend/tests/unit/modules/test_oppy_ai_evals_domain.py` con **27 tests unitarios exhaustivos** (100% pasando en 0.15s).
   - Validada suite de arquitectura `oppytec-backend/tests/architecture/` (**29 tests pasando en 1.46s**), verificando cero `float` AST en capas de dominio y cumplimiento estricto de límites de Clean Architecture.
   - Sincronizado Graphify con `python scripts/harness.py sync-graph` (118 nodos AST, 142 aristas).

---

## 2. Friction & Failures (Fricciones y Desafíos Resueltos)

- **Fricción AST Float Scanner:** El test de arquitectura `test_zero_float_in_fx_and_domain_modules` escanea el AST de los módulos de dominio buscando el token `ast.Name(id="float")`. Incluso comprobaciones de tipo defensivas como `isinstance(val, float)` son detectadas como violaciones si se usa el nombre directo. Se resolvió de manera idiomática utilizando `type(val).__name__ == "float"` defensivo para rechazar floats sin declarar la palabra reservada en el AST como tipo.

---

## 3. Next Exact Action (Siguiente Acción Exacta)

- **Para el Agente 03 (`03-database-alembic-and-backup-engineer` - Etapa 1 DB):**
  - Diseñar la migración Alembic correlativa `0013_oppyfy_feedback_and_eval_benchmarks.py` creando:
    - Tabla en esquemas de tenant `tenant_*.oppyfy_message_feedback` (`id`, `message_id`, `trace_id`, `user_id`, `rating`, `feedback_category`, `user_correction`, `created_at`).
    - Tabla en esquema público `public.oppyfy_eval_benchmarks` (`id`, `suite_name`, `model_name`, `total_cases`, `passed_cases`, métricas `Decimal`, `passed_thresholds`, `created_at`).
    - Tabla `public.oppyfy_eval_case_results` vinculada al benchmark.
- **Para el Agente 04 (`04-backend-senior-dev` - Etapa 2 Backend):**
  - Implementar el adaptador `LangfuseTracer` implementando `LLMTracerPort` con resiliencia no bloqueante (graceful degradation) y sanitización PII, instrumentar `MeteredAIService` y exponer el endpoint `POST /api/v1/oppy_ai/chat/feedback`.
