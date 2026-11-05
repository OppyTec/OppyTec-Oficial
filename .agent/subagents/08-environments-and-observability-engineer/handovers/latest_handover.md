# Reporte de Traspaso (`Handover`) — Agente 08: Environments and Observability Engineer

- **Fecha UTC:** 2026-11-05T01:15:00Z
- **Fase / Tarea:** Etapa 3 — Plan Maestro de Evals y Observabilidad LLM con Langfuse Self-Hosted (`.agent/Planes-Maestros/PLAN_MAESTRO_LLM_EVALS_Y_OBSERVABILIDAD_LANGFUSE.md` - Fase 2)
- **Estado de Certificación:** `LANGFUSE_SELF_HOSTED_AND_OTEL_OBSERVABILITY_CERTIFIED`

---

## 1. Completed (Acciones de Infraestructura, Correlación OTel y Dashboards Realizadas)

1. **Pre-ejecución Graphify y Claim AST (Reglas 4, 5 y 6):**
   - Ejecutado `python scripts/harness.py nav "observability"` para mapeo de vecindad AST.
   - Reclamado atómicamente el símbolo `observability_langfuse` en `docker-compose.yml` con `python scripts/harness.py claim-ast`.

2. **Despliegue Self-Hosted de Langfuse v2 en `docker-compose.yml`:**
   - Servicio `langfuse-server` con imagen oficial `ghcr.io/langfuse/langfuse:2`.
   - Perfil opcional `profiles: [observability]` para arranque coordinado con `otel-lgtm`, `umami` y `glitchtip`.
   - Reutilización de PostgreSQL primario con esquema aislado `?schema=langfuse`.
   - Script de inicialización montado en Postgres: `docker/postgres/init-langfuse.sql` (`CREATE SCHEMA IF NOT EXISTS langfuse;`).
   - Reutilización de Redis en DB 2 (`redis://redis:6379/2`) para colas asíncronas de ingesta sin interferir con la app principal (DB 0) ni GlitchTip (DB 1).
   - Inyección de variables en `backend` (`LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`).
   - Verificada la sintaxis de Docker Compose con `docker compose config` y `docker compose --profile observability config` (100% OK sin advertencias ni errores).

3. **Variables de Entorno en `.env.example` y `oppytec-backend/.env.example`:**
   - Creado `.env.example` en la raíz con variables de infraestructura y observabilidad.
   - Actualizado `oppytec-backend/.env.example` con la sección oficial:
     * `LANGFUSE_HOST=http://localhost:3000`
     * `LANGFUSE_PORT=3000`
     * `LANGFUSE_PUBLIC_KEY=pk-lf-oppytec-dev-public-key`
     * `LANGFUSE_SECRET_KEY=sk-lf-oppytec-dev-secret-key-32`
     * `NEXTAUTH_SECRET=oppytec_langfuse_nextauth_secret_high_entropy_32`
     * `SALT=oppytec_langfuse_salt_key_min_16_chars`
     * `TELEMETRY_ENABLED=false`

4. **Correlación OpenTelemetry y W3C TraceContext:**
   - Soporte bidireccional en `ObservabilityMiddleware` y `extract_trace_id_from_headers`:
     * Ingesta de `traceparent` estándar W3C (`00-{trace_id}-{span_id}-01`).
     * Inyección en cabeceras de respuesta HTTP de `X-Trace-ID` y `traceparent`.
     * El `trace_id` de 32 caracteres hexadecimales es propagado a `TraceContext.create()` en `MeteredAIService`.
     * `LangfuseTracer` crea el evento `trace-create` con `id: context.trace_id`, garantizando coincidencia 1:1 entre las trazas de OpenTelemetry (Tempo) y Langfuse.

5. **Dashboard Grafana FinOps & Observabilidad AI:**
   - Creado aprovisionamiento automatizado: `docker/grafana/provisioning/dashboards/dashboards.yaml`.
   - Montaje de volúmenes en `otel-lgtm` para auto-descubrimiento en `/var/lib/grafana/dashboards`.
   - Dashboard completo JSON `docker/grafana/dashboards/oppyfy_llm_finops_observability.json`:
     * KPIs de FinOps: Total invocaciones, costo acumulado USD en tiempo real, total de tokens procesados y tasa de error global (< 5%).
     * Latencia P50, P95, P99 con línea de SLA de 2.5s (2500ms).
     * Consumo de tokens por modelo (Prompt vs Completion).
     * Satisfacción de usuarios (% pulgar arriba) y desglose de fallas gastronómicas reportadas (alucinaciones, datos incompletos).
     * Ranking de Top 10 tenants por consumo FinOps en USD.
     * Tabla exploradora forense de trazas con Deep-Link directo a Langfuse UI (`http://localhost:3000/project/oppytec-ai/traces/${__data.fields.trace_id}`) y Tempo APM.

6. **Verificación Determinista y Tests:**
   - Creada suite de correlación `oppytec-backend/tests/unit/test_langfuse_otel_correlation.py` (5/5 tests passing en 0.21s).
   - Verificados tests de arquitectura en `test_observability_pii_redaction_and_spans.py` (4/4 tests passing).
   - Verificada suite completa de feedback y telemetría de OppyFy (22 tests passing en 1.25s).
   - Sincronizado Grafo de Arquitectura Graphify: 119 nodos, 142 aristas.

---

## 2. Friction & Failures
- `ghcr.io/langfuse/langfuse:2` requiere Prisma sobre PostgreSQL; para prevenir colisiones con las tablas de Alembic de OppyTec, se aisló el servicio bajo el esquema `?schema=langfuse` y se proveyó el script `docker/postgres/init-langfuse.sql` en el punto de montaje `/docker-entrypoint-initdb.d/`.

---

## 3. Next Exact Action
- Despacho y entrega al Orquestador (Prime Agent) para coordinar el avance de la Etapa 3 con los agentes 06 (`06-ai-oppyfy-and-jev-engineer`) y 07 (`07-i18n-and-fx-currency-specialist`).
