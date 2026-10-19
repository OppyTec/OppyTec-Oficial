# ADR-016: Observabilidad de 4 Pilares (`OpenTelemetry`, `Grafana LGTM`, `Sentry/GlitchTip`, `Umami`) y Redacción PII

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_observabilidad_monitoreo_y_analitica_001.md` / `.agent/skills/observability_telemetry/SKILL.md`

---

## 1. Contexto

Operar una plataforma SaaS multi-tenant sin trazabilidad distribuida entre Frontend, Backend, PostgreSQL, Redis y proveedores LLM impide diagnosticar cuellos de botella ($P_{95}$) o auditar consumos por cliente. Por otro lado, enviar payloads crudos a sistemas de logs o errores puede filtrar contraseñas, tokens JWT o datos personales (PII).

## 2. Decisión

Instrumentar una arquitectura de **Observabilidad Full-Stack en 4 Pilares** gobernada desde `oppytec-backend/src/core/observability.py` y `oppytec-frontend/src/shared/telemetry/`, centralizada en las **13 Sub-Vistas del Centro de Mando del SuperAdmin**:

1. **Pilar 1 — Trazas, Métricas y Logs Estructurados (`OpenTelemetry` + `structlog` JSON):**
   - Propagación extremo a extremo del encabezado `X-Trace-ID` / `traceparent` desde React hasta FastAPI, SQLAlchemy, Redis y llamadas a `OppyFy`/`JEV`.
   - Logs 100% en JSON estructurado enriquecidos automáticamente con `trace_id`, `span_id`, `env`, `tenant_slug` y `user_id`.
2. **Pilar 2 — Visualización Operativa y APM (`Grafana LGTM`: Loki + Grafana + Tempo + Mimir/Prometheus):**
   - Levanta localmente bajo `docker compose --profile observability up -d` para inspeccionar latencias $P_{50}/P_{95}/P_{99}$, pool de conexiones, salud de Redis y métricas de negocio.
3. **Pilar 3 — Rastreo de Excepciones y Crashes (`Sentry SDK` compatible con `GlitchTip` Auto-Alojado):**
   - Captura excepciones no controladas en Backend y Error Boundaries en React adjuntando el `X-Trace-ID` exacto.
4. **Pilar 4 — Analítica de Producto Ética y Sin Cookies (`Umami`):**
   - Mide adopción de funcionalidades por módulo y flujo de usuario respetando la privacidad (GDPR/LGPD) sin trackers invasivos.
5. **Filtro Inmutable de Redacción PII y Secretos (`scrub_telemetry_payload()`):**
   - Antes de emitir cualquier log, span de OpenTelemetry o evento de Sentry, el procesador redacta recursivamente cualquier campo sensible (`password`, `secret`, `token`, `authorization`, `api_key`, `credit_card`, `rut`, `tax_id`) reemplazándolo por `"[REDACTED]"`.

## 3. Consecuencias

- **Positivas:**
  - Correlación inmediata entre un error reportado en pantalla (`X-Trace-ID`), la traza SQL en Tempo y el consumo de tokens en `public.llm_request_logs`.
  - Cumplimiento estricto de privacidad con cero filtración de credenciales en telemetría.
- **Negativas / Trade-offs:**
  - Prohibido usar `print()` o `console.log()` en código de producción; todo evento debe pasar por el logger estructurado.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_observability_pii_redaction_and_spans.py` y `tests/smoke/test_system_boot_and_health.py`.
- **Invariante Verificada:** Verifica que toda respuesta HTTP incluya el header `X-Trace-ID`, que `scrub_telemetry_payload()` purgue diccionarios anidados con claves sensibles y que no existan llamadas `print()` en `src/`.
