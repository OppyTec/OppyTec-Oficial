# Base de Conocimiento Evolutiva — Agente 07: Especialista en Internacionalización (i18n) y Multi-Moneda (FX)

> Lecciones aprendidas específicas de `07-i18n-and-fx-currency-specialist` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 3]:** Paridad de locales es/en se valida por archivos, llaves y variables `{{var}}`; FX sin `float` (solo Decimal, quantize 1e-8); RBAC realtime siempre server-side. Ejecutar checks `uv run` por separado (encadenados se cuelgan).
