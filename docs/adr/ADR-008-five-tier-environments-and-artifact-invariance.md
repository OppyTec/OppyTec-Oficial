# ADR-008: Cadena de 5 Entornos Aislados e Invarianza de Artefactos (`SHA-256`)

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_entornos_y_despliegue_001.md` / `.agent/rules/09-five-environments-and-deployment.md`

---

## 1. Contexto

Recompilar imágenes de Docker por cada entorno o permitir que entornos inferiores (`local`, `preview`) se conecten accidentalmente a bases de datos o buckets de producción representa un riesgo crítico de corrupción de datos y discrepancias entre lo probado en QA y lo desplegado en producción.

## 2. Decisión

Establecer una topología de **5 Entornos Estrictamente Aislados** (`local`, `preview`, `ci`, `staging`, `production`) gobernada por **Invarianza de Artefactos (`SHA-256`)** y validación *Fail-Fast* en el milisegundo `0`:

1. **Los 5 Entornos y su Aislamiento:**
   - `local`: Docker Compose local con `AsyncAdaptedQueuePool`, Mailpit y datos sintéticos (`seed_dev_data.py`).
   - `preview`: Entorno efímero por Pull Request / Git Worktree con rama aislada de base de datos y prefijo `ENV_NAMESPACE=pr_<id>`.
   - `ci`: Contenedores efímeros (`Testcontainers`) para ejecución determinista de *Fast/Main/Deep Gates*.
   - `staging`: Pre-producción con topología idéntica a producción (`NullPool` + PgBouncer) y datos anonimizados (`anonymize_for_staging.py`).
   - `production`: Entorno productivo blindado (`docs_url=None`, `redoc_url=None`, `openapi_url=None`, HSTS estricto, respaldos 4-capas activos).
2. **Invarianza de Artefacto (`Build Once, Promote Everywhere`):**
   - La imagen Docker de Backend y Frontend se construye **una única vez** en `ci` y se promueve mediante su digest inmutable `sha256:...` hacia `staging` y `production`.
   - En el Frontend, `docker-entrypoint.sh` inyecta las variables públicas de entorno en `/runtime-env.js` al arrancar el contenedor Nginx, evitando recompilar el bundle de Vite.
3. **Configuración *Fail-Fast* y `SecretStr`:**
   - `oppytec-backend/src/core/config.py` valida todas las variables en el milisegundo `0` usando Pydantic Settings v2 y envuelve toda credencial sensible en `SecretStr` para impedir su filtración en logs o trazas.

## 3. Consecuencias

- **Positivas:**
  - Garantía matemática de que el binario certificado en `ci` y `staging` es bit a bit idéntico al que se ejecuta en `production`.
  - Cero secretos o URLs quemadas en el código fuente.
- **Negativas / Trade-offs:**
  - Las variables de entorno en el Frontend deben leerse desde `window.__OPPYTEC_ENV__` (validado con Zod en `src/shared/config/env.ts`) con fallback a `import.meta.env` en modo desarrollo.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca y Humo:** `oppytec-backend/tests/smoke/test_system_boot_and_health.py` y `oppytec-backend/tests/security_redteam/test_09_zero_hardcoding_and_secrets_guard.py`.
- **Invariante Verificada:** Verifica que en `APP_ENV=production` la documentación OpenAPI/Swagger esté deshabilitada (`404`), que `str(settings)` oculte todos los `SecretStr` con `**********`, y que no existan URLs ni credenciales hardcodeadas en `src/`.
