# Base de Conocimiento Evolutiva — Agente 10: Auditor Estricto de Ciberseguridad Red Team (Autoparcheo y Veto)

> Lecciones aprendidas específicas de `10-cybersecurity-redteam-auditor` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 4 — Certificación Ofensiva Red Team 11 Vectores + Contratos OpenAPI Schemathesis]:**
  - Para auditar `alg: none` y adulteración de firmas HMAC en `PyJWT`, construir el token falsificado codificando cabeceras/payloads con `base64.urlsafe_b64encode` sin padding (`rstrip("=")`), verificando que `decode_access_token` lance `AuthenticationError` (HTTP 401).
  - En pruebas asíncronas que comparten el singleton `get_rate_limiter()` o el registro en memoria de sesiones revocadas (`_REVOKED_JTIS`, `_REVOKED_USER_IDS`), invocar siempre `clear_revoked_sessions()` y `get_rate_limiter().reset()` al inicio y cierre de cada test para evitar contaminación cruzada de ventanas deslizantes.
  - Los schemas Pydantic de entrada (`*Request`) deben imponer `extra="forbid"`, lo cual se traduce en `additionalProperties: false` dentro de `/openapi.json` y rechazo determinista HTTP 422 ante ataques de *Mass Assignment*.
