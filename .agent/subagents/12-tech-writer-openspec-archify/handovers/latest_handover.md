# Reporte de Traspaso (`Handover`) — Agente 12: Technical Writer, OpenSpec Bipartito, Graphify y Archify

- **Fecha UTC:** 2026-10-26T23:25:00Z
- **Agente:** Agente 12 (`12-tech-writer-openspec-archify`)
- **Fase / Módulo:** FASE 7.6 (Documentación OpenSpec Bipartito, ADR-012 y Sincronización Graphify) del `PLAN_MAESTRO_OPPYFY_AI.md` — Asistente IA OppyFy (RAG 3-Capas, RBAC Especializado, Billetera de Créditos y FinOps en Platform Admin).
- **Estado de Certificación:** `OPPYFY_PHASE_7_6_DOCUMENTATION_AND_SPECS_SYNCHRONIZED` (Bóvedas OpenSpec 1:1 sincronizadas y validadas con 0% patrones prohibidos, ADR-012 formalizado e inmutable, 96 nodos y 116 aristas en Graphify AST, 26/26 tests de arquitectura pasando 100% verde).

---

## 1. Completed (Qué se ejecutó y validó)

1. **Sincronización de Especificación de Negocio OpenSpec:**
   - [`specs/business-domain/oppy-ai-and-voice.business.spec.md`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/specs/business-domain/oppy-ai-and-voice.business.spec.md)
   - Audiencia: clientes, propietarios de restaurantes y hoteles, administradores, soporte y RAG OppyFy Capa 3A.
   - **0% código técnico y SQL** (cero mención a `CREATE TABLE`, `ALTER TABLE`, `SELECT `, `sqlalchemy`, `FastAPI`, `.py`, `.tsx`).
   - Detalle integral de reglas de negocio:
     - Misión doble (conocimiento funcional del sistema vs inteligencia operativa del restaurante) con aislamiento multi-tenant estricto.
     - Preservación inmutable de marcas y proveedores (regla "Pollo King").
     - Medidor semafórico de salud de contexto (<65% verde, 66-85% ámbar, >85% rojo con bloqueo de inputs para erradicar *Context Rot*) y acción guiada de rollover a hilo fresco con síntesis al 5% de contexto inicial.
     - Economía de paquetes de créditos acumulables sin vencimiento mensual (suma aritmética permanente `1.000 + 10.000 = 11.000`).
     - Panel de gobernanza RBAC exclusivo con árbol editable de dominios/subdominios, asignación de permisos temporales con triple caducidad (tiempo, prompts, créditos) y ocultación física de costos (`can_view_costs`).
     - Visor de auditoría de consultas (`oppyfy_prompt_audit_log`) con trazabilidad de mensajes permitidos y bloqueados.
     - Espacio de trabajo con pantalla dividida (Split-View Canvas) para tablas y gráficos interactivos.

2. **Sincronización de Especificación de Ingeniería OpenSpec:**
   - [`specs/engineering-code/oppy-ai-and-voice.code.spec.md`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/specs/engineering-code/oppy-ai-and-voice.code.spec.md)
   - Frontmatter estricto YAML: `spec_id: ENG-OPPY-AI-AND-VOICE`, `domain_module: oppy_ai`, `paired_spec: specs/business-domain/oppy-ai-and-voice.business.spec.md`, `jev_system1_evaluation: "Sí (Jev.choice, umbral 0.75)"`, `last_verified_phase: "Fase 7.6"`.
   - Contratos técnicos exhaustivos:
     - Dominio DDD: `ContextMeter` (evaluación y compactación), `CreditWallet` (billetera transaccional con tipos `Decimal`), `OppyfyRbac` (verificación jerárquica de permisos y triple caducidad), `AICreditPack` (packs add-on y cotización con margen comercial).
     - Aplicación: Wrapper universal ineludible `MeteredAIService`, `ThreeLayerRagService` (Capa 1 memoria, Capa 2 herramientas deterministas sobre `tenant_*`, Capa 3A/3B/3C multi-fuente con caché semántica L1 Redis + L2 pgvector), `OppyfyToolRouter` con JEV Sistema 1, 9 herramientas operativas tipadas (`operational_tools/`), *Hard-Code Data Stripping* ineludible si `can_view_costs == False`, `TokenConsumptionService` (FinOps agregado) y `AiCreditPacksService`.
     - Persistencia e Infraestructura: Esquema `public` (`llm_request_logs` con `NUMERIC(14,6)` USD, `NUMERIC(14,2)` CLP, `NUMERIC(12,2)` créditos; `audio_request_logs`, `ai_model_configs`, `ai_credit_packs`, `spec_chunks` pgvector HNSW 768 dims exclusivo para `specs/business-domain/`) y esquemas `tenant_*` (`oppyfy_domains`, `oppyfy_subdomains`, `oppyfy_permission_grants`, `oppyfy_worker_credit_wallets`, `oppyfy_prompt_audit_log`, `oppyfy_rbac_audit_log`, `tenant_documents`, `ai_chat_threads`, `ai_chat_messages`).
     - Presentación REST RFC 7807: Endpoints `/api/v1/oppyfy/chat`, `/threads/{id}/rollover`, `/rbac/domains`, `/rbac/grants`, `/wallets/me`, `/wallets/{id}`, `/telemetry/logs`, `/platform-admin/token-consumption`, `/platform-admin/ai-packs`.
     - Frontend UI: Hooks reactivos (`useOppyfyChat`, `useOppyfyRbac`, `useOppyfyCredits`, `useOppyfyGovernance`), componentes (`ContextHealthMeter`, `OppyfyChatPane`, `OppyfyCanvasPanel`, `OppyfyRolloverModal`, `OppyfyGovernancePanel`).
     - Observabilidad OTel: Spans semánticos (`oppyfy.query`, `oppyfy.tool_router`, `oppyfy.data_stripping`, `oppyfy.metered_ai`, `oppyfy.tool.<name>`), garantía Zero-Float en métricas financieras y PII scrubbing preservando `"Pollo King"`.
     - Co-Creación de Tests: Referencias cruzadas a suites unitarias, de integración, arquitectura AST y auditoría ofensiva Red Team.

3. **Formalización de ADR-012:**
   - [`docs/adr/ADR-012-oppyfy-dual-rag-custom-rbac-and-credit-ledger.md`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/docs/adr/ADR-012-oppyfy-dual-rag-custom-rbac-and-credit-ledger.md)
   - Decisión arquitectónica congelando:
     1. Desacoplamiento de marca e identidad mediante `settings.AI_ASSISTANT_BRAND_NAME` (default "OppyFy").
     2. Muro de fuego infranqueable contra fugas de ingeniería interna (0% de acceso a código fuente y `specs/engineering-code/`; solo `specs/business-domain/` en `public.spec_chunks`).
     3. RAG en 3 capas + herramientas deterministas en código duro sin Text-to-SQL arbitrario.
     4. Semáforo anti-alucinación (<65%, 66-85%, >85% con bloqueo) y rollover asistido al 5% de contexto.
     5. Billetera de créditos acumulables sin vencimiento mensual, operada con `SELECT FOR UPDATE` y `Decimal`.
     6. Panel RBAC exclusivo y editable por tenant con Hard-Code Data Stripping ineludible.
     7. Telemetría universal y FinOps de plataforma en `public.llm_request_logs` con precisión `Decimal` conectada a `/admin/token-consumption`.

4. **Validación Determinista de Puertas de Arquitectura:**
   - Ejecutado `oppytec-backend/.venv/bin/pytest oppytec-backend/tests/architecture/test_openspec_bipartition_and_sync.py`: **1 passed (100% verde)**.
   - Ejecutado `oppytec-backend/.venv/bin/pytest oppytec-backend/tests/architecture/test_oppyfy_telemetry_and_isolation.py`: **1 passed (100% verde)**.
   - Ejecutado suite completa `oppytec-backend/.venv/bin/pytest oppytec-backend/tests/architecture/`: **26 passed (100% verde)**.

5. **Sincronización del Grafo AST Graphify:**
   - Ejecutado `python3 scripts/harness.py sync-graph`: **96 nodos totales, 116 aristas** sincronizados en `docs/architecture/graphify/graph.json`.

---

## 2. Friction & Failures (Qué cuidar)

- **Pureza de la Bóveda de Negocio:** En `specs/business-domain/oppy-ai-and-voice.business.spec.md`, el linter de arquitectura prohíbe taxativamente la subcadena `"SELECT "` (con espacio) para evitar la filtración de sentencias SQL. Se redactó cuidadosamente usando términos funcionales en español ("seleccionar", "elegir" o "marcar").
- **Frontmatter de Ingeniería:** La clave `jev_system1_evaluation` en `specs/engineering-code/oppy-ai-and-voice.code.spec.md` es requerida por `test_openspec_bipartition_and_sync.py` y debe corresponder exactamente a una de las primitivas de JEV (`Jev.choice` en este caso, con umbral `0.75`).

---

## 3. Next Exact Action (Siguiente paso exacto)

- Fase 7.6 de `PLAN_MAESTRO_OPPYFY_AI.md` completada exitosamente.
- El módulo `oppy_ai` cuenta con todas sus especificaciones OpenSpec sincronizadas, ADR-012 congelado e indexación AST Graphify actualizada.
- Notificar al Orquestador (`d0212433-cb68-4d01-aea7-ef017fe152b9`) con el reporte de cierre.
