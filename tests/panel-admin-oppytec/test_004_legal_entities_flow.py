"""
tests/panel-admin-oppytec/test_004_legal_entities_flow.py
Flujo E2E 004: Gestión de Entidades Legales y RUT 1:1.

Criterios de Aceptación:
1. Inicio de sesión como Superadmin Genesis.
2. Navegación a `/admin/legal-entities` y verificación de `[data-testid="admin-legal-entities-view"]` y `[data-testid="legal-entities-table"]`.
3. Apertura del modal mediante `[data-testid="legal-entities-table-create-btn"]`.
4. Diligenciamiento de campos de la entidad legal:
   - RUT / Tax ID: `77.123.456-K`
   - Razón Social: `Inversiones Gastronómicas Pacífico SpA`
   - Dirección: `Av. Providencia 1200, Santiago`
5. Guardado y verificación de la notificación flotante Sonner Toast ("creada con éxito").
6. Cierre del modal y verificación de la fila en la tabla.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from playwright.sync_api import Page, expect

CURRENT_DIR = Path(__file__).resolve().parent


def _login_as_superadmin(page: Page, base_url: str, creds: dict[str, str]) -> None:
    page.goto(f"{base_url}/admin/login")
    page.wait_for_load_state("networkidle")
    if "/admin" not in page.url or "/admin/login" in page.url:
        page.locator("#admin-email").fill(creds["email"])
        page.locator("#admin-password").fill(creds["password"])
        page.locator('button[type="submit"]').click()
        page.wait_for_url("**/admin", timeout=12000)


@pytest.mark.e2e
@pytest.mark.legal_entities
def test_004_legal_entities_crud_flow(
    page: Page,
    base_url: str,
    superadmin_credentials: dict[str, str],
) -> None:
    # 1. Autenticación como Superadmin
    _login_as_superadmin(page, base_url, superadmin_credentials)

    # 2. Navegar a /admin/legal-entities
    page.goto(f"{base_url}/admin/legal-entities")
    page.wait_for_load_state("networkidle")

    view = page.locator('[data-testid="admin-legal-entities-view"]')
    expect(view).to_be_visible(timeout=10000)

    table = page.locator('[data-testid="legal-entities-table"]')
    expect(table).to_be_visible(timeout=10000)

    # 3. Abrir modal de nueva entidad legal
    create_btn = page.locator('[data-testid="legal-entities-table-create-btn"]')
    expect(create_btn).to_be_visible()
    create_btn.click()

    # El modal se renderiza con role="dialog"
    dialog = page.get_by_role("dialog").or_(page.locator('[role="dialog"]')).first
    expect(dialog).to_be_visible(timeout=8000)

    # 4. Diligenciar formulario de entidad legal dentro del diálogo
    # Campo RUT / Tax ID
    tax_input = (
        dialog.locator("#field-tax_id")
        .or_(dialog.get_by_placeholder("Ej: 76.543.210-K"))
        .or_(dialog.locator('input[type="text"]').nth(0))
    )
    expect(tax_input).to_be_visible()
    tax_input.fill("77.123.456-K")

    # Campo Razón Social
    name_input = (
        dialog.locator("#field-legal_name")
        .or_(dialog.get_by_placeholder("Ej: Inversiones Gastronómicas SpA"))
        .or_(dialog.locator('input[type="text"]').nth(1))
    )
    expect(name_input).to_be_visible()
    name_input.fill("Inversiones Gastronómicas Pacífico SpA")

    # Campo Dirección
    address_input = dialog.locator("#field-legal_address").or_(
        dialog.get_by_placeholder("Av. Providencia 1200, Santiago")
    )
    if address_input.is_visible():
        address_input.fill("Av. Providencia 1200, Santiago")

    # 5. Enviar formulario
    submit_btn = (
        dialog.get_by_role("button", name="Guardar")
        .or_(dialog.locator('button[type="submit"]'))
        .or_(dialog.locator('button:has-text("Guardar")'))
        .first
    )
    expect(submit_btn).to_be_enabled()
    submit_btn.click()

    # 6. Verificación de la card de notificación flotante (Sonner Toast)
    toast = page.locator("[data-sonner-toast]").first
    expect(toast).to_be_visible(timeout=7000)
    expect(toast).to_contain_text("creada con éxito")

    # Esperar que el diálogo se cierre
    expect(dialog).not_to_be_visible(timeout=8000)

    # 7. Verificación en la tabla
    search_input = page.locator('[data-testid="legal-entities-table-search-input"]')
    if search_input.is_visible():
        search_input.fill("77.123.456-K")

    entity_row = table.locator('tbody tr:has-text("77.123.456-K")')
    expect(entity_row.first).to_be_visible(timeout=6000)
