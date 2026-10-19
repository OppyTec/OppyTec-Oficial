# ADR-012: Asistente IA `OppyFy` con RAG en 3 Capas, RBAC Propio Editable, Funciones en Código Duro y Billetera de Créditos Acumulables

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md` / `.agent/rules/14-oppyfy-ai-assistant-rag-and-credits.md`

---

## 1. Contexto

Permitir que un asistente de IA genere consultas SQL libres (*Text-to-SQL*) sobre una base de datos multi-tenant o calcule costos/factibilidad de eventos inventando números en su ventana de contexto produce alucinaciones financieras y riesgos graves de seguridad. Asimismo, atar los créditos de IA a una caducidad mensual genera fricción comercial cuando un cliente compra recargas adicionales.

## 2. Decisión

Diseñar el asistente inteligente **`OppyFy`** (con identidad parametrizada en `settings.AI_ASSISTANT_DISPLAY_NAME = "OppyFy"`) bajo 5 pilares inmutables:

1. **Arquitectura Híbrida RAG en 3 Capas + Funciones Deterministas en Código Duro (Cero Text-to-SQL):**
   - **Capa 1 (Conocimiento Funcional):** RAG vectorial (`pgvector`) alimentado exclusivamente desde `specs/business-domain/*.business.spec.md`.
   - **Capa 2 (Memoria Semántica del Tenant):** Resúmenes pre-calculados y aislados estrictamente en el esquema `tenant_<slug>`.
   - **Capa 3 (Herramientas Deterministas en Código Duro):** `OppyFy` jamás escribe SQL libre; invoca a **`JEV` (Sistema 1)** para seleccionar e invocar funciones Python deterministas en `src/modules/oppy_ai/application/tools/` (ej. `check_event_stock_feasibility`, `analyze_supplier_lead_time_and_prices`, `get_inventory_valuation_and_alerts`).
2. **Panel RBAC Exclusivo y Editable de `OppyFy`:**
   - Separado de los permisos de pantallas del ERP: cada cliente puede crear y editar sus propios **Dominios y Sub-dominios de consulta IA** en su tenant y asignarlos por rol o trabajador, verificados en dos niveles (antes de ejecutar la herramienta en backend y al redactar la respuesta).
3. **Billetera de Créditos Independiente del Plan, Acumulable y Sin Caducidad:**
   - Los paquetes de créditos (`1.000`, `5.000`, `10.000+`) se compran de forma independiente al plan SaaS, **se suman aritméticamente (`1.000 + 10.000 = 11.000`) y jamás vencen a fin de mes**, operados mediante un libro mayor inmutable (`CreditLedgerService`) con bloqueo `SELECT ... FOR UPDATE`.
4. **Indicador Circular de Contexto (`%`) y Compactación Automática:**
   - La UI muestra un anillo visual del porcentaje de ventana de contexto utilizada; al alcanzar el `80%`, `OppyFy` resume y compacta automáticamente los mensajes antiguos sin perder el hilo de la conversación.
5. **Auditoría Financiera y Telemetría LLM (`public.llm_request_logs`):**
   - El 100% de las invocaciones a `OppyFy` y `JEV` registran `trace_id`, tenant, usuario, modelo, tokens de entrada/salida, latencia, costo en USD (`Decimal`) y créditos descontados.

## 3. Consecuencias

- **Positivas:**
  - Cero alucinaciones matemáticas en cálculos de stock, recetas, mermas o factibilidad de eventos para $N$ invitados.
  - Transparencia comercial total de márgenes de IA por cliente en el Panel SuperAdmin de OppyTec.
- **Negativas / Trade-offs:**
  - Toda nueva capacidad analítica de `OppyFy` debe registrarse como herramienta tipada en `tools/` con su permiso de sub-dominio `OppyFy` asociado.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca y Red Team:** `oppytec-backend/tests/architecture/test_oppyfy_telemetry_and_isolation.py` y `oppytec-backend/tests/security_redteam/test_11_oppyfy_rag_prompt_injection_and_credit_drain.py`.
- **Invariante Verificada:** Verifica que ninguna herramienta de `OppyFy` ejecute SQL dinámico sin parametrizar, que toda herramienta valide `OppyfyRbacEvaluator`, que los créditos se acumulen sin expirar y que toda llamada registre su fila en `public.llm_request_logs`.
