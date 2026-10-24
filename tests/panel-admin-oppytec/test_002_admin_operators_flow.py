"""
tests/panel-admin-oppytec/test_002_admin_operators_flow.py
Flujo E2E 002: Gestión de Operadores Administrativos y Usuarios Globales.

Criterios de Aceptación:
1. Inicio de sesión como Superadmin Genesis.
2. Navegación a `/admin/users` y verificación de `[data-testid="admin-global-users-view"]`.
3. Apertura del modal `[data-testid="admin-create-global-user-form"]` mediante `[data-testid="global-users-table-create-btn"]`.
4. Diligenciamiento de datos del operador `jcampillay`:
   - Campos de texto: username, first_name, last_name, email, password.
   - Rol: `admin`.
   - Switches/Toggles: `#field-is_superuser`, `#field-is_active`.
   - Scroll vertical asistido en modal `overflow-y-auto`.
5. Envío y verificación de persistencia en `[data-testid="global-users-table"]`.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from playwright.sync_api import Page, expect

CURRENT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = CURRENT_DIR / "artifacts"
STATE_FILE = ARTIFACTS_DIR / "state_superadmin.json"


def _login_as_superadmin(page: Page, base_url: str, creds: dict[str, str]) -> None:
    page.goto(f"{base_url}/admin/login")
    page.wait_for_load_state("networkidle")
    if "/admin" not in page.url or "/admin/login" in page.url:
        page.locator("#admin-email").fill(creds["email"])
        page.locator("#admin-password").fill(creds["password"])
        page.locator('button[type="submit"]').click()
        page.wait_for_url("**/admin", timeout=12000)


@pytest.mark.e2e
@pytest.mark.operators
def test_002_admin_operators_creation_and_listing_flow(
    page: Page,
    base_url: str,
    superadmin_credentials: dict[str, str],
) -> None:
    # 1. Autenticación como Superadmin
    _login_as_superadmin(page, base_url, superadmin_credentials)

    # 2. Navegar a /admin/users
    page.goto(f"{base_url}/admin/users")
    page.wait_for_load_state("networkidle")

    view_container = page.locator('[data-testid="admin-global-users-view"]')
    expect(view_container).to_be_visible(timeout=10000)

    # 3. Abrir modal de creación de usuario global
    create_btn = page.locator('[data-testid="global-users-table-create-btn"]')
    expect(create_btn).to_be_visible()
    create_btn.click()

    modal_form = page.locator('[data-testid="admin-create-global-user-form"]')
    expect(modal_form).to_be_visible(timeout=8000)

    # 4. Diligenciar campos del operador
    username_input = page.locator("#field-username")
    first_name_input = page.locator("#field-first_name")
    last_name_input = page.locator("#field-last_name")
    email_input = page.locator("#field-email")
    password_input = page.locator("#field-password")
    role_select = page.locator("#field-role")

    username_input.fill("jcampillay")
    first_name_input.fill("Jonathan")
    last_name_input.fill("Campillay")
    email_input.fill("jcampillay@oppytec.cl")
    password_input.fill("Operador#2026")
    role_select.select_option("admin")

    # Scroll hacia abajo en el modal para interactuar con los switches
    modal_form.evaluate("node => node.scrollTop = node.scrollHeight")

    # Activar switch de superuser si no está activo
    superuser_toggle = page.locator('[data-testid="field-toggle-is_superuser"]')
    if superuser_toggle.is_visible():
        superuser_toggle.click()

    # Activar switch de usuario activo
    active_toggle = page.locator('[data-testid="field-toggle-is_active"]')
    if active_toggle.is_visible():
        # Asegurar estado activo
        active_toggle.click()

    # 5. Enviar formulario
    submit_btn = page.locator('[data-testid="admin-create-global-user-form-submit-btn"]')
    expect(submit_btn).to_be_enabled()
    submit_btn.click()

    # Esperar que el modal se cierre
    expect(modal_form).not_to_be_visible(timeout=8000)

    # 6. Verificación en la tabla
    table = page.locator('[data-testid="global-users-table"]')
    expect(table).to_be_visible()

    # Buscar usuario 'jcampillay' en el buscador o en filas de la tabla
    search_input = page.locator('[data-testid="global-users-table-search-input"]')
    if search_input.is_visible():
        search_input.fill("jcampillay")

    # Validar que aparezca en el cuerpo de la tabla
    user_row = table.locator('tbody tr:has-text("jcampillay")')
    expect(user_row.first).to_be_visible(timeout=6000)
