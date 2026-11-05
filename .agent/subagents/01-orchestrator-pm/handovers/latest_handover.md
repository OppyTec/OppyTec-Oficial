# Handover: Agente 01 (`01-orchestrator-pm`) — Creación y Sincronización del Plan Maestro de LLM Evals y Observabilidad Langfuse

## Completed
- **Plan Maestro Creado y Certificado**:
  - Creado [.agent/Planes-Maestros/PLAN_MAESTRO_LLM_EVALS_Y_OBSERVABILIDAD_LANGFUSE.md](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/.agent/Planes-Maestros/PLAN_MAESTRO_LLM_EVALS_Y_OBSERVABILIDAD_LANGFUSE.md) con exhaustividad técnica de nivel de producción e ingeniería de IA estándar de oro.
  - Diseñada la arquitectura de Observabilidad Especializada de LLM con **Langfuse v2** (self-hosted en Docker, sin dependencias SaaS privativas de telemetría, reutilizando PostgreSQL y Redis).
  - Diseñado el Pipeline de Evaluación Continua (*LLM Evals*) con **DeepEval / Ragas** integrado en PyTest con un *Golden Dataset* gastronómico de 50+ preguntas curadas sobre recetas, banquetes, mermas, stock, FEFO y facturas.
  - Definidos los umbrales mínimos no negociables (*Quality Gates*) con política **Fail-Closed**: *Faithfulness* $\ge 0.85$, *Answer Relevance* $\ge 0.85$, *Context Precision/Recall* $\ge 0.80$, *Hallucination Rate* $\le 0.05$.
  - Mapeo de captura de feedback de usuario humano (👍 / 👎) en frontend React 19 (`/oppyfy`) con modal de reporte de alucinación/corrección vinculado al `trace_id` de Langfuse.
  - Gobernanza del DAG Canónico Completo de 12 Agentes (Etapas 1 a 4) rigurosamente detallada, excluyendo al Agente 13 (`13-browser-e2e-playwright`) que opera desacoplado en la Etapa 5 bajo demanda sin bloquear el pipeline.
  - Definición completa de las 8 Fases de Ejecución:
    - **Fase 1:** Arquitectura DDD, Interfaces Desacopladas (`LLMTracerPort`, `LLMEvalSuitePort`) y Migración Alembic `0013_oppyfy_feedback_and_eval_benchmarks.py`.
    - **Fase 2:** Infraestructura y Despliegue de Langfuse Self-Hosted en `docker-compose.yml` con OpenTelemetry y Grafana.
    - **Fase 3:** Adaptador Backend `LangfuseTracer`, Interceptor `MeteredAIService` y Endpoints REST `/api/v1/oppy_ai/chat/feedback`.
    - **Fase 4:** Frontend UI: Componentes de Feedback en React 19 (`ChatMessage.tsx`, `FeedbackModal.tsx`) con TanStack Query y accesibilidad.
    - **Fase 5:** Suite de Evals Continua con DeepEval y Ragas en `tests/ai_evals/` con Golden Dataset gastronómico curado (50+ casos).
    - **Fase 6:** Internacionalización y Paridad Multi-Moneda: Evals bilingües (`es`/`en`), regla inmutable "Pollo King" y FX con `Decimal`.
    - **Fase 7:** Auditoría Red Team Kali: Enmascaramiento estricto de PII en traces, aislamiento multi-tenant estricto y tests de prompt injection adversarial.
    - **Fase 8:** Automatización CI/CD (`harness.py eval-llm`), OpenSpec Bipartito (`ai_evals.business.spec.md` y `ai_evals.code.spec.md`), Graphify y Archify.
- **Sincronización del Grafo AST**:
  - Ejecutado `python scripts/harness.py sync-graph` con indexación exitosa de 118 nodos y 142 aristas en [docs/architecture/graphify/graph.json](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/docs/architecture/graphify/graph.json).
- **Verificación Anti-Trampa**:
  - Comprobado `python scripts/harness.py verify-evals` con 100% de integridad en hashes SHA-256.

## Friction & Failures
- Ninguna. La integración entre Langfuse, DeepEval/Ragas y OpenTelemetry se articula limpiamente sobre los puertos desacoplados ya existentes en OppyTec v2.0.

## Next Exact Action
- Proceder con la Etapa 1 del DAG: Despachar a los Agentes `02-software-architect` y `03-database-alembic-and-backup-engineer` para la especificación formal de interfaces desacopladas y la migración Alembic correlativa `0013_oppyfy_feedback_and_eval_benchmarks.py`.
