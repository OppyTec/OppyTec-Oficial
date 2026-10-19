# Base de Conocimiento Evolutiva — Agente 10: Auditor Estricto de Ciberseguridad Red Team (Autoparcheo y Veto)

> Lecciones aprendidas específicas de `10-cybersecurity-redteam-auditor` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 4 — Certificación Ofensiva Red Team 11 Vectores + Contratos OpenAPI Schemathesis]:**
  - Para auditar `alg: none` y adulteración de firmas HMAC en `PyJWT`, construir el token falsificado codificando cabeceras/payloads con `base64.urlsafe_b64encode` sin padding (`rstrip("=")`), verificando que `decode_access_token` lance `AuthenticationError` (HTTP 401).
  - En pruebas asíncronas que comparten el singleton `get_rate_limiter()` o el registro en memoria de sesiones revocadas (`_REVOKED_JTIS`, `_REVOKED_USER_IDS`), invocar siempre `clear_revoked_sessions()` y `get_rate_limiter().reset()` al inicio y cierre de cada test para evitar contaminación cruzada de ventanas deslizantes.
  - Los schemas Pydantic de entrada (`*Request`) deben imponer `extra="forbid"`, lo cual se traduce en `additionalProperties: false` dentro de `/openapi.json` y rechazo determinista HTTP 422 ante ataques de *Mass Assignment*.
- **[Fase 6 — Deep Gate Integral, Simulacro Criptográfico 4-Capas y Certificación Final 10/10]:**
  - El target `deep-gate` en `Makefile` debe encadenar tras `main-gate` tanto la validación de contratos/E2E/UAT/Load (`pytest tests/contracts tests/e2e tests/uat tests/load -q`) como el simulacro en vivo de restauración quirúrgica por tenant (`python scripts/backup_manager.py verify-drill --schema tenant_pacifico_centro`), garantizando que ningún release llegue a producción sin probar su recuperación `.sql.zst.age`.
  - La certificación final `10/10` exige auditar conjuntamente las fronteras estáticas de Backend (`ruff check`, `mypy --strict` en 222 archivos) y Frontend (`tsc --noEmit`, `eslint --max-warnings 0`, `knip`, `depcruise` en 96 módulos) además de verificar la integridad `SHA-256` de `.agent/evals/rubric_10_criteria.yaml` mediante `python3 scripts/harness.py verify-evals`.
