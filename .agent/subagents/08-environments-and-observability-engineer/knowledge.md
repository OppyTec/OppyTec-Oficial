# Base de Conocimiento Evolutiva — Agente 08: Especialista en 5 Entornos y Observabilidad 4-Pilares

> Lecciones aprendidas específicas de `08-environments-and-observability-engineer` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 1 — Configuración Fail-Fast y Observabilidad 4-Pilares]:**
  - En `pydantic_settings.BaseSettings` con `mypy --strict`, instanciar `Settings()` en pruebas unitarias sin pasar `_env_file=None` evita errores `[call-arg]` en el plugin de tipos de Pydantic v2.
  - La validación de secretos (`SECRET_KEY`, `JWT_ACCESS_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`) mediante entropía de Shannon ($\ge 3.0\text{ bits/char}$) y longitud mínima ($\ge 32$) bloquea claves débiles o repetitivas en el milisegundo `0`.
  - `scrub_telemetry_payload()` debe inspeccionar recursivamente tanto nombres de llaves sensibles como instancias de `SecretStr` en diccionarios, listas y tuplas anidadas, redactando con `"[REDACTED_PII]"` antes de serializar logs JSON o enviar eventos a Sentry/GlitchTip.
