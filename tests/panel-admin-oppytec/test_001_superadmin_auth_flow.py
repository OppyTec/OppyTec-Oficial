"""
tests/panel-admin-oppytec/test_001_superadmin_auth_flow.py
Flujo E2E 001: Autenticación de Superadmin Genesis, Barra Superior y Cierre de Sesión Seguro.

Criterios de Aceptación:
1. Navegación a `/admin/login` e ingreso con credenciales Genesis (`oppytec.admin@gmail.com` / `oppytec.2026`).
2. Redirección exitosa a `/admin` verificando renderizado de `[data-testid="admin-panel-root"]` o layout administrativo.
3. Validación de controles de la barra superior:
   - Dropdown de Moneda (`[data-testid="currency-selector"]`): opciones CLP, USD, EUR.
   - Dropdown de Idioma (`[data-testid="language-flag-selector"]`): banderas SVG y opciones Español/English.
4. Cierre de sesión seguro y guardado de `state_superadmin.json` para reutilización autenticada.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from playwright.sync_api import Page, expect

CURRENT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = CURRENT_DIR / "artifacts"
STATE_FILE = ARTIFACTS_DIR / "state_superadmin.json"


@pytest.mark.e2e
@pytest.mark.auth
def test_001_superadmin_auth_and_topbar_flow(
    page: Page,
    base_url: str,
    superadmin_credentials: dict[str, str],
) -> None:
    # 1. Navegación a la página de inicio de sesión administrativo
    login_url = f"{base_url}/admin/login"
    page.goto(login_url)
    page.wait_for_load_state("networkidle")

    # Verificar que estamos en la vista de login de admin
    expect(page.locator('[data-testid="admin-login-page"]')).to_be_visible(timeout=10000)

    # 2. Llenar credenciales con cadencia humana
    email_input = page.locator("#admin-email")
    password_input = page.locator("#admin-password")

    expect(email_input).to_be_visible()
    expect(password_input).to_be_visible()

    email_input.fill(superadmin_credentials["email"])
    password_input.fill(superadmin_credentials["password"])

    # 3. Enviar formulario y esperar navegación a /admin
    submit_btn = page.locator('button[type="submit"]')
    expect(submit_btn).to_be_enabled()
    submit_btn.click()

    # Verificar redirección hacia el panel administrativo
    page.wait_for_url("**/admin", timeout=12000)
    expect(page).to_have_url(f"{base_url}/admin")

    # Esperar que el root del panel administrativo esté visible
    admin_root = page.locator('[data-testid="admin-layout-root"]')
    expect(admin_root).to_be_visible(timeout=8000)

    # 4. Verificación de la Barra Superior (TopBar)
    # A. Dropdown de Moneda (CLP / USD / EUR)
    currency_selector = page.locator('[data-testid="currency-selector"]')
    expect(currency_selector).to_be_visible()

    # Abrir dropdown de moneda y verificar opciones
    currency_btn = currency_selector.locator("button").first
    currency_btn.click()
    expect(page.locator('[data-testid="currency-option-CLP"]')).to_be_visible()
    expect(page.locator('[data-testid="currency-option-USD"]')).to_be_visible()
    expect(page.locator('[data-testid="currency-option-EUR"]')).to_be_visible()

    # Seleccionar USD para probar reactividad
    page.locator('[data-testid="currency-option-USD"]').click()
    expect(currency_selector).to_have_attribute("data-active-currency", "USD")

    # B. Dropdown de Idioma (ES / EN)
    lang_selector = page.locator('[data-testid="language-flag-selector"]')
    expect(lang_selector).to_be_visible()

    # Abrir dropdown de idioma y verificar opciones
    lang_btn = lang_selector.locator("button").first
    lang_btn.click()
    expect(page.locator('[data-testid="lang-option-es"]')).to_be_visible()
    expect(page.locator('[data-testid="lang-option-en"]')).to_be_visible()

    # Cerrar dropdown haciendo clic fuera o seleccionando ES
    page.locator('[data-testid="lang-option-es"]').click()
    expect(lang_selector).to_have_attribute("data-active-lang", "es")

    # 5. Guardar estado de sesión autenticado para reutilización segura
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    page.context.storage_state(path=str(STATE_FILE))
    assert STATE_FILE.exists() and STATE_FILE.stat().st_size > 0, "No se generó state_superadmin.json"

    # 6. Cierre de sesión seguro
    # Buscar el botón de logout en el menú superior
    logout_btn = page.locator('header button:has-text("Cerrar Sesión"), header button:has-text("Salir"), header button:has(svg.lucide-log-out)')
    expect(logout_btn.first).to_be_visible()
    logout_btn.first.click()

    # Debe redirigir de vuelta a /admin/login o /login
    page.wait_for_url("**/login**", timeout=8000)
    assert "/login" in page.url, f"Redirección post logout inesperada: {page.url}"
