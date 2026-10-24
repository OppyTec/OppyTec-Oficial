"""
tests/panel-admin-oppytec/conftest.py
Infraestructura de Fixtures de Pytest + Playwright para el Panel Administrativo OppyTec v2.0.

Responsabilidades:
1. Fixture de sesión `db_lifecycle`:
   - Respaldo de salvaguarda mediante `db_harness.backup_database_safety_snapshot()`.
   - Reseteo a estado Génesis idempotente mediante `db_harness.reset_to_genesis_clean_slate()`.
2. Fixtures de navegación Playwright (`browser`, `context`, `page`):
   - Soporte headless / visual con `slow_mo` configurable.
   - Captura automática de capturas de pantalla en `artifacts/screenshots/` si un test falla.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

# Importar arnés de base de datos
try:
    from . import db_harness
except ImportError:
    import db_harness  # type: ignore

CURRENT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = CURRENT_DIR / "artifacts"
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Cargar variables de entorno desde .env.e2e si existe
ENV_E2E = CURRENT_DIR / ".env.e2e"
if ENV_E2E.exists():
    for line in ENV_E2E.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip("'\"")
        if k not in os.environ and v:
            os.environ[k] = v

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5173")
HEADLESS = os.environ.get("PLAYWRIGHT_HEADLESS", "true").lower() in ("true", "1", "yes")
SLOW_MO = int(os.environ.get("PLAYWRIGHT_SLOW_MO", "500"))


# =============================================================================
# HOOKS DE PYTEST PARA DETECTAR FALLOS Y CAPTURAR PANTALLA
# =============================================================================
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: Any, call: Any) -> Generator[None, Any, None]:
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# =============================================================================
# FIXTURE DE CICLO DE VIDA DE BASE DE DATOS
# =============================================================================
@pytest.fixture(scope="session", autouse=True)
def db_lifecycle() -> Generator[dict[str, Any], None, None]:
    """
    Garantiza el estado Génesis limpio y seguro antes de iniciar la suite E2E:
    1. Respaldo de salvaguarda de oppytec_dev con pg_dump.
    2. Reseteo a Génesis idempotente (< 0.25s) en PostgreSQL oppytec-postgres.
    """
    print("\n[DB LIFECYCLE] 1. Ejecutando respaldo de seguridad preventivo...")
    backup_file = db_harness.backup_database_safety_snapshot()
    print(f"[DB LIFECYCLE] [OK] Respaldo generado en: {backup_file.name}")

    print("[DB LIFECYCLE] 2. Ejecutando reseteo a Génesis (clean slate)...")
    report = db_harness.reset_to_genesis_clean_slate()
    print(f"[DB LIFECYCLE] [OK] Reseteo completado en {report['elapsed_seconds']}s")

    yield report


# =============================================================================
# FIXTURES DE CONFIGURACIÓN Y CREDENCIALES
# =============================================================================
@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def superadmin_credentials() -> dict[str, str]:
    return {
        "email": os.environ.get("SUPERADMIN_EMAIL", "oppytec.admin@gmail.com"),
        "username": os.environ.get("SUPERADMIN_USERNAME", "oppytec.admin"),
        "password": os.environ.get("SUPERADMIN_PASSWORD", "oppytec.2026"),
    }


# =============================================================================
# FIXTURES PLAYWRIGHT: NAVEGADOR, CONTEXTO Y PÁGINA
# =============================================================================
@pytest.fixture(scope="session")
def playwright_instance() -> Generator[Playwright, None, None]:
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright) -> Generator[Browser, None, None]:
    browser_obj = playwright_instance.chromium.launch(
        headless=HEADLESS,
        slow_mo=SLOW_MO if not HEADLESS else 0,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    yield browser_obj
    browser_obj.close()


@pytest.fixture(scope="function")
def browser_context(
    browser: Browser, request: pytest.FixtureRequest
) -> Generator[BrowserContext, None, None]:
    # Aísla la IP simulada por cada prueba para evitar colisiones en Rate Limiting (HTTP 429)
    test_hash = abs(hash(request.node.name)) % 200 + 10
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        ignore_https_errors=True,
        extra_http_headers={"X-Forwarded-For": f"192.168.10.{test_hash}"},
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(
    browser_context: BrowserContext, request: pytest.FixtureRequest
) -> Generator[Page, None, None]:
    page_obj = browser_context.new_page()
    yield page_obj

    # Hook para captura automática de screenshots en caso de fallo
    rep_call = getattr(request.node, "rep_call", None)
    if rep_call and rep_call.failed:
        test_name = request.node.name.replace("/", "_").replace("::", "_")
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        shot_path = SCREENSHOTS_DIR / f"failure_{test_name}_{timestamp}.png"
        try:
            page_obj.screenshot(path=str(shot_path), full_page=True)
            print(f"\n[SCREENSHOT ERROR] Captura guardada en: {shot_path}")
        except Exception as ex:
            print(f"\n[SCREENSHOT ERROR] No se pudo guardar la captura: {ex}")

    page_obj.close()
