# Base de Conocimiento Evolutiva — Agente 09: Ingeniero de QA, Tests 1:1 y Paridad con Legacy (Autoreparación)

> Lecciones aprendidas específicas de `09-qa-parity-and-test-engineer` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 4 — Caché de `Settings` al emitir JWT en Tests]:** `src/main.py:create_app()` invoca `get_settings.cache_clear()` para recargar las variables de entorno del fixture `default_test_env`. En pruebas de integración con `TestClient`, siempre debe instanciarse `app = create_app()` antes de invocar `create_access_token(...)` / `create_refresh_token(...)` para garantizar que la firma y la validación usen exactamente el mismo `JWT_ACCESS_SECRET_KEY`.
- **[Fase 4 — Paridad Matemática de Merma Técnica en Escandallos]:** En `src/modules/recipes/domain/escandallo_calculator.py`, la cantidad bruta aplica `gross = quantity * (1 + waste_pct / 100)` en `Decimal` con cuantización `0.0001` (`ROUND_HALF_UP`).
