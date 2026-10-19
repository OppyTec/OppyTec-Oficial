# Base de Conocimiento Evolutiva — Agente 04: Programador Senior Backend, RBAC Dual y Almacenamiento R2

> Lecciones aprendidas específicas de `04-backend-senior-dev` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 1 — App Factory & Desacoplamiento Entre Worktrees]:** En `oppytec-backend/src/main.py`, el uso de `importlib.import_module("src.core.config")` y `importlib.import_module("src.core.observability")` junto con `_FallbackBootstrapSettings(BaseSettings)` permite que `create_app()` funcione tanto de forma autónoma antes del merge como integrado con `src/core/config.py` y `src/core/observability.py` del Agente 08, manteniendo `0` llamadas a `os.getenv`/`os.environ` y `0` errores bajo `mypy --strict` (`disallow_any_explicit = true`).
- **[Fase 1 — Invocación Universal de Pytest]:** Insertar `_BACKEND_DIR` en `sys.path` dentro de `oppytec-backend/tests/conftest.py` garantiza que `pytest` resuelva `src.*` tanto si se ejecuta desde la raíz del monorepo (`pytest oppytec-backend/tests/...`) como desde `oppytec-backend/`.
