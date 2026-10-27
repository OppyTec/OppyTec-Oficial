# ADR-012: Asistente IA `OppyFy` con RAG en 3 Capas, RBAC Propio Editable, Semáforo Anti-Alucinación, Billetera Acumulable y Telemetría FinOps

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19 (Actualizado y formalizado en Fase 7.6: 2026-10-26)
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md` / `.agent/rules/13-oppyfy-ai-governance-and-telemetry.md` / `PLAN_MAESTRO_OPPYFY_AI.md`

---

## 1. Contexto

Permitir que un asistente de inteligencia artificial opere sin restricciones en un ERP multi-tenant introduce riesgos críticos para la estabilidad, la seguridad y la sustentabilidad del negocio:
1. **Riesgo de Fuga de Propiedad Intelectual:** Si el asistente indexa código fuente, esquemas DDL o especificaciones técnicas de ingeniería interna, ataques de *Prompt Injection* pueden exponer la arquitectura del software o credenciales internas.
2. **Alucinaciones Financieras y Operativas (*Text-to-SQL*):** Si el LLM genera consultas SQL libres para responder sobre inventario, mermas o costos de recetas, inventa cifras, calcula promedios erróneos y puede alterar la integridad referencial.
3. **Degradación por Fatiga de Contexto (*Context Rot*):** En conversaciones continuadas de más de 10-15 turnos, los modelos de lenguaje pierden precisión matemática y sufren olvido catastrófico o alucinaciones acumulativas si el historial no se gestiona de forma determinista.
4. **Fricción Comercial de Créditos:** Atar los créditos de IA a una caducidad mensual de suscripción penaliza a los restaurantes que compran bolsas grandes de recarga y genera reclamos comerciales.
5. **Falta de Trazabilidad FinOps:** Sin un interceptor universal a nivel de transporte que registre tokens, tiempos y costos reales por llamada con precisión `Decimal`, la plataforma carece de visibilidad sobre sus márgenes reales de IA.

---

## 2. Decisión

Implementar el asistente inteligente de la plataforma bajo la arquitectura empresarial **`OppyFy` (v2.0)**, congelando los siguientes siete pilares arquitectónicos inmutables:

### 1. Desacoplamiento de Marca e Identidad
- La identidad visual y denominativa del copiloto está desacoplada del código fuente mediante la variable de entorno `settings.AI_ASSISTANT_BRAND_NAME` (con valor por defecto `"OppyFy"`), permitiendo personalización *white-label* sin refactorizar la lógica interna.

### 2. Muro de Fuego Infranqueable contra Fuga de Ingeniería Interna
- El subsistema RAG de documentación pública solo vectoriza la Bóveda 1 de OpenSpec (`specs/business-domain/*.business.spec.md`) en `public.spec_chunks` (768 dimensiones, índice `HNSW`).
- **Invariante de Seguridad:** Queda **estrictamente prohibida e interceptada por test de arquitectura AST** la indexación de la Bóveda 2 (`specs/engineering-code/`), de migraciones Alembic o de cualquier archivo fuente en `src/`.

### 3. Arquitectura RAG en 3 Capas + Herramientas Deterministas (Cero Text-to-SQL)
- **Capa 1 (Memoria Conversacional y Contexto):** Ventana de diálogo enriquecida con medidor semafórico y compactación de historial.
- **Capa 2 (Herramientas Operativas Deterministas):** `OppyFy` jamás redacta SQL libre. El motor **JEV (Sistema 1)** selecciona deterministamente funciones Python tipadas en `application/operational_tools/` (`analyze_event_supply_feasibility`, `get_stock_health_and_reorder_alerts`, `get_expiring_batches_fefo`, `evaluate_supplier_lead_times_and_price_drift`, `get_sales_and_food_cost_variance`, `render_canvas_table`, `render_canvas_chart`), ejecutadas sobre el esquema activo `tenant_*`.
- **Capa 3 (Documentación y Memoria Semántica):** Capa 3A (especificaciones de negocio en `public.spec_chunks`), Capa 3B (documentos privados en `tenant_*.tenant_documents`) y Capa 3C (hábitos del restaurante en `tenant_*.tenant_ai_memory`).
- **Caché Semántica en Dos Niveles:** Capa L1 Redis en memoria (TTL 48h) + L2 pgvector para preguntas conceptuales frecuentes.

### 4. Semáforo Anti-Alucinación y Rollover Asistido al 5% de Contexto
- El componente `ContextMeter` evalúa en cada interacción los tokens consumidos respecto a la ventana máxima del modelo:
  - 🟢 **Verde (<65%):** Operación nominal.
  - 🟡 **Ámbar (66-85%):** Advertencia de saturación.
  - 🔴 **Rojo (>85%):** Bloqueo automático de nuevas entradas crudas (`is_input_blocked = True`) para eliminar alucinaciones por *Context Rot*.
- **Rollover Asistido:** Se habilita la acción `compact_thread_for_fresh_handover`, la cual resume de forma estructurada los datos numéricos y acuerdos previos, creando un hilo nuevo limpio que consume únicamente el `5%` de la capacidad inicial.

### 5. Billetera de Créditos Acumulables Sin Vencimiento
- Los paquetes de recarga de créditos IA (`AiCreditPack`: 1.000, 5.000, 20.000+) son independientes del plan base SaaS recurrente.
- **Acumulación Aritmética:** Los créditos adquiridos se suman de forma indefinida (`1.000 + 10.000 = 11.000`) y **jamás caducan al cierre de mes**.
- **Gestión por Trabajador:** El dueño del establecimiento asigna cupos individuales o inhabilita el acceso en `tenant_*.oppyfy_worker_credit_wallets`. La deducción es atómica mediante `CreditLedgerService` con bloqueo transaccional `SELECT ... FOR UPDATE` y tipos `Decimal`.

### 6. Panel RBAC Exclusivo y Editable por Tenant con Hard-Code Data Stripping
- Cada local gestiona su propio árbol de dominios y subdominios en `tenant_*.oppyfy_domains` y `tenant_*.oppyfy_subdomains`.
- **Permisos Temporales con Triple Caducidad:** Los permisos asignados en `tenant_*.oppyfy_permission_grants` soportan expiración por fecha/hora (`expires_at`), por conteo de preguntas (`max_prompts`) o por tope de créditos (`temp_credit_ceiling`).
- **Hard-Code Data Stripping:** Si el permiso `can_view_costs` es `False`, el interceptor de backend elimina físicamente del resultado de las herramientas todas las claves monetarias (`costo_unitario`, `precio_compra`, `margen_bruto`, `total_neto`) antes de suministrar el contexto al LLM, impidiendo cualquier filtración inadvertida.

### 7. Telemetría Universal y FinOps de Plataforma (`public.llm_request_logs`)
- El wrapper ineludible `MeteredAIService` intercepta toda llamada al motor JEV o al proveedor LLM.
- Registra en la tabla Append-Only `public.llm_request_logs`: tokens (input, cached, output), duración en ms, costo real del proveedor en USD (`NUMERIC(14,6)`) y CLP (`NUMERIC(14,2)`), y créditos descontados (`NUMERIC(12,2)`).
- La consola `/admin/token-consumption` expone el consumo agregado por holding, tenant y modelo, calculando en tiempo real el margen bruto comercial de IA.
- Instrumentación semántica OpenTelemetry con spans tipados (`oppyfy.query`, `oppyfy.tool_router`, `oppyfy.data_stripping`, `oppyfy.metered_ai`), garantía estricta **Zero-Float** y sanitización PII preservando nombres de marcas y proveedores (como `"Pollo King"`).

---

## 3. Consecuencias

### Positivas
- Cero alucinaciones numéricas en cálculo de inventarios, recetas, mermas o costos de producción gastronómica.
- Inmunidad comprobada frente a ataques de *Prompt Injection* dirigidos a extraer código fuente o credenciales de la plataforma.
- Confianza comercial del cliente gracias a créditos acumulables que no se pierden al finalizar el mes.
- Control total del propietario sobre qué trabajadores acceden a qué información y si pueden visualizar costos o márgenes.
- Trazabilidad FinOps exacta al centavo de dólar para la administración de la plataforma.

### Negativas / Trade-offs
- Cualquier nueva capacidad analítica de OppyFy debe implementarse como una herramienta tipada en `operational_tools/` vinculada a un subdominio RBAC, descartando consultas libres no estructuradas.
- Mayor consumo de almacenamiento en `public.llm_request_logs` debido al registro minucioso de cada invocación.

---

## 4. Verificación Determinista en Tests

- **Arquitectura de Caja Blanca y Aislamiento RAG:** `oppytec-backend/tests/architecture/test_oppyfy_telemetry_and_isolation.py`.
- **Sincronización Bipartita OpenSpec:** `oppytec-backend/tests/architecture/test_openspec_bipartition_and_sync.py`.
- **Pruebas de Observabilidad, Zero-Float y PII:** `oppytec-backend/tests/unit/modules/test_oppyfy_observability.py`.
- **Pruebas Unitarias de Dominio y Billetera:** `oppytec-backend/tests/unit/modules/test_oppy_ai_domain.py`.
- **Pruebas Unitarias de Servicios y RAG:** `oppytec-backend/tests/unit/modules/test_oppy_ai_services.py`.
- **Pruebas de Endpoints de API REST:** `oppytec-backend/tests/unit/modules/test_oppy_ai_api.py`.
- **Auditoría Ofensiva Red Team Kali:** `oppytec-backend/tests/security_redteam/test_08_ai_prompt_injection_and_rag_isolation.py`.
- **Pruebas Frontend Vitest:** `oppytec-frontend/src/features/oppyfy/__tests__/useOppyfyHooks.test.ts`, `OppyfyView.test.tsx`, `OppyfyGovernance.test.tsx`, `OppyfyI18nAndFx.test.tsx`.
