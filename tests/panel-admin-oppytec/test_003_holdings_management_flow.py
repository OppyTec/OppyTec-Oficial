"""
tests/panel-admin-oppytec/test_003_holdings_management_flow.py
Flujo E2E 003: Gestión de Grupos Corporativos (Holdings) y Cuotas Comerciales.

Criterios de Aceptación:
1. Inicio de sesión como Superadmin Genesis.
2. Navegación a `/admin/holdings` y verificación de `[data-testid="admin-holdings-view"]`.
3. Apertura del modal `[data-testid="dynamic-admin-form"]` mediante `[data-testid="holdings-table-create-btn"]`.
4. Creación del Holding `Grupo Pacífico`:
   - Nombre: `Grupo Pacífico`
   - Plan comercial base: `starter` (Plan Esencial)
   - Cupo de Usuarios: `15`
   - Almacenamiento R2 (MB): `2048`
   - Switch de estado: Activo (`[data-testid="field-toggle-is_active"]`).
5. Guardado y verificación en la tabla `[data-testid="holdings-table"]`.
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
@pytest.mark.holdings
def test_003_holdings_creation_and_quota_flow(
    page: Page,
    base_url: str,
    superadmin_credentials: dict[str, str],
) -> None:
    # 1. Autenticación como Superadmin
    _login_as_superadmin(page, base_url, superadmin_credentials)

    # 2. Navegar a /admin/holdings
    page.goto(f"{base_url}/admin/holdings")
    page.wait_for_load_state("networkidle")

    holdings_view = page.locator('[data-testid="admin-holdings-view"]')
    expect(holdings_view).to_be_visible(timeout=10000)

    # 3. Abrir modal de nuevo holding
    create_btn = page.locator('[data-testid="holdings-table-create-btn"]')
    expect(create_btn).to_be_visible()
    create_btn.click()

    # El modal se renderiza con role="dialog"
    dialog = page.get_by_role("dialog").or_(page.locator('[role="dialog"]')).first
    expect(dialog).to_be_visible(timeout=8000)

    # 4. Diligenciar formulario de holding dentro del diálogo
    name_input = dialog.get_by_placeholder("Ej: Grupo Gastronómico Pacífico SpA").or_(dialog.locator('input[type="text"]').first)
    expect(name_input).to_be_visible()
    name_input.fill("Grupo Pacífico")

    plan_select = dialog.locator("select").or_(dialog.get_by_role("combobox")).first
    if plan_select.is_visible():
        plan_select.select_option("starter")

    # Inputs numéricos de cuotas
    num_inputs = dialog.locator('input[type="number"]')
    if num_inputs.count() >= 2:
        num_inputs.nth(0).fill("15")
        num_inputs.nth(1).fill("2048")
    else:
        users_input = dialog.locator("#field-max_active_users")
        if users_input.is_visible():
            users_input.fill("15")
        storage_input = dialog.locator("#field-max_storage_mb")
        if storage_input.is_visible():
            storage_input.fill("2048")

    # Scroll y verificación de switch de estado activo
    dialog.evaluate("node => node.scrollTop = node.scrollHeight")
    active_toggle = dialog.locator('[data-testid="field-toggle-is_active"]').or_(dialog.locator('button[role="switch"]')).or_(dialog.locator('button:has(span.rounded-full)'))
    if active_toggle.first.is_visible():
        active_toggle.first.click()

    # 5. Enviar formulario
    submit_btn = dialog.get_by_role("button", name="Guardar").or_(dialog.locator('button[type="submit"]')).or_(dialog.locator('button:has-text("Guardar")')).first
    expect(submit_btn).to_be_enabled()
    submit_btn.click()

    # Verificación de la card de notificación flotante (Sonner Toast)
    toast = page.locator("[data-sonner-toast]").first
    expect(toast).to_be_visible(timeout=7000)
    expect(toast).to_contain_text('Holding "Grupo Pacífico" creado con éxito')

    # Esperar que el diálogo se cierre
    expect(dialog).not_to_be_visible(timeout=8000)

    # 6. Verificación en la tabla
    table = page.locator('[data-testid="holdings-table"]')
    expect(table).to_be_visible()

    # Filtrar o buscar en la tabla
    search_input = page.locator('[data-testid="holdings-table-search-input"]')
    if search_input.is_visible():
        search_input.fill("Grupo Pacífico")

    # Verificar que aparezca la fila con "Grupo Pacífico"
    holding_row = table.locator('tbody tr:has-text("Grupo Pacífico")')
    expect(holding_row.first).to_be_visible(timeout=6000)
