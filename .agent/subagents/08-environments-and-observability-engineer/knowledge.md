# Base de Conocimiento Evolutiva — Agente 08: Especialista en 5 Entornos y Observabilidad 4-Pilares

> Lecciones aprendidas específicas de `08-environments-and-observability-engineer` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 1 — Configuración Fail-Fast y Observabilidad 4-Pilares]:**
  - En `pydantic_settings.BaseSettings` con `mypy --strict`, instanciar `Settings()` en pruebas unitarias sin pasar `_env_file=None` evita errores `[call-arg]` en el plugin de tipos de Pydantic v2.
  - La validación de secretos (`SECRET_KEY`, `JWT_ACCESS_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`) mediante entropía de Shannon ($\ge 3.0\text{ bits/char}$) y longitud mínima ($\ge 32$) bloquea claves débiles o repetitivas en el milisegundo `0`.
  - `scrub_telemetry_payload()` debe inspeccionar recursivamente tanto nombres de llaves sensibles como instancias de `SecretStr` en diccionarios, listas y tuplas anidadas, redactando con `"[REDACTED_PII]"` antes de serializar logs JSON o enviar eventos a Sentry/GlitchTip.
- **[Auditoría Plan Maestro Admin — Semáforo de Cuotas y Telemetría de Aprovisionamiento Tenancy]:**
  - El semáforo preventivo de cuotas de 4 estados (`NORMAL` < 80%, `WARNING` 80-94%, `CRITICAL` 95-99%, `OVER_QUOTA` 100% o límite 0) debe emitir tanto métricas tipadas en memoria (`QuotaSemaphoreMetric`) como spans OTel (`quota.semaphore.<resource_type>`) hacia `InMemorySpanExporter` y alertas estructuradas JSON en Loki, permitiendo correlación inmediata con `X-Trace-ID` y contexto Multi-Tenant.
  - Toda auditoría de aprovisionamiento de tenants (`tenant.provisioning.provision`), creación de planes comerciales (`plan.audit.upsert`) y eventos de saturación de cupo (`quota.audit.seat_limit_exceeded`) pasa obligatoriamente por `scrub_telemetry_payload()`, redactando `password`, `hashed_password`, `token`, `secret_key`, `rut`, `credit_card` y objetos `SecretStr` con `"[REDACTED_PII]"`.
  - En pruebas unitarias y de arquitectura donde `Settings()` se instancia sin sobrescribir el archivo `.env`, `SENTRY_DSN` puede resolver a `SecretStr("")` o `None`, requiriendo comprobación defensiva `(cfg.SENTRY_DSN is None or not cfg.SENTRY_DSN.get_secret_value())`.
