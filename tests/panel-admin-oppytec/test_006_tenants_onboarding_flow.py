"""
tests/panel-admin-oppytec/test_006_tenants_onboarding_flow.py
Flujo E2E 006: Aprovisionamiento de Tenants y Asignación de Módulos SaaS.

Criterios de Aceptación:
1. Inicio de sesión como Superadmin Genesis.
2. Navegación a `/admin/tenants` y verificación de `[data-testid="admin-tenants-view"]` y `[data-testid="tenants-table"]`.
3. Apertura del modal con `[data-testid="tenants-table-create-btn"]`.
4. Diligenciamiento en `[data-testid="admin-create-tenant-form"]`:
   - Nombre Comercial: `Restaurante Costanera Gourmet`
   - Slug: `costanera_gourmet`
   - Moneda base: `CLP`
   - Aplicación de preset del Plan Básico (10 módulos) vía `[data-testid="tenant-apply-plan-basico-btn"]`.
5. Envío mediante `[data-testid="tenant-provision-submit-btn"]`.
6. Verificación de Sonner Toast ("aprovisionado con éxito").
7. Cierre del modal y verificación del nuevo tenant en `[data-testid="tenants-table"]`.
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
@pytest.mark.tenants
def test_006_tenants_onboarding_and_modules_flow(
    page: Page,
    base_url: str,
    superadmin_credentials: dict[str, str],
) -> None:
    # 1. Autenticación como Superadmin
    _login_as_superadmin(page, base_url, superadmin_credentials)

    # 2. Navegar a /admin/tenants
    page.goto(f"{base_url}/admin/tenants")
    page.wait_for_load_state("networkidle")

    view = page.locator('[data-testid="admin-tenants-view"]')
    expect(view).to_be_visible(timeout=10000)

    table = page.locator('[data-testid="tenants-table"]')
    expect(table).to_be_visible(timeout=10000)

    # 3. Abrir modal de nuevo tenant
    create_btn = page.locator('[data-testid="tenants-table-create-btn"]')
    expect(create_btn).to_be_visible()
    create_btn.click()

    # El modal se renderiza con role="dialog" conteniendo admin-create-tenant-form
    form = page.locator('[data-testid="admin-create-tenant-form"]')
    expect(form).to_be_visible(timeout=8000)

    # 4. Diligenciar campos del tenant
    name_input = (
        form.get_by_placeholder("Ej: Sucursal Costanera")
        .or_(form.locator('input[type="text"]').nth(0))
        .or_(form.locator("input").first)
    )
    expect(name_input).to_be_visible()
    name_input.fill("Restaurante Costanera Gourmet")

    slug_input = (
        form.get_by_placeholder("costanera_centro")
        .or_(form.locator('input[type="text"]').nth(1))
    )
    expect(slug_input).to_be_visible()
    slug_input.fill("costanera_gourmet")

    # Selección de moneda CLP
    currency_select = form.locator("select").nth(2).or_(form.locator("select:has(option[value='CLP'])"))
    if currency_select.first.is_visible():
        currency_select.first.select_option("CLP")

    # Aplicar preset de 10 módulos básicos dentro del formulario modal
    apply_preset_btn = form.locator('[data-testid="tenant-apply-plan-basico-btn"]')
    if apply_preset_btn.is_visible():
        apply_preset_btn.click()

    # 5. Enviar aprovisionamiento
    submit_btn = form.locator('[data-testid="tenant-provision-submit-btn"]')
    expect(submit_btn).to_be_enabled()
    submit_btn.click()

    # 6. Verificación de la card de notificación flotante (Sonner Toast)
    toast = page.locator("[data-sonner-toast]").first
    expect(toast).to_be_visible(timeout=7000)
    expect(toast).to_contain_text("aprovisionado con éxito")

    # Esperar que el modal se cierre
    expect(form).not_to_be_visible(timeout=8000)

    # 7. Verificación en la tabla
    search_input = page.locator('[data-testid="tenants-table-search-input"]')
    if search_input.is_visible():
        search_input.fill("Costanera Gourmet")

    tenant_row = table.locator('tbody tr:has-text("Restaurante Costanera Gourmet")')
    expect(tenant_row.first).to_be_visible(timeout=6000)
