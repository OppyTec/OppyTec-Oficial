"""
tests/panel-admin-oppytec/test_005_commercial_plans_flow.py
Flujo E2E 005: Planes Comerciales y Parametrización de Cuotas SaaS.

Criterios de Aceptación:
1. Inicio de sesión como Superadmin Genesis.
2. Navegación a `/admin/plans` y verificación de `[data-testid="admin-plans-view"]`.
3. Verificación del formulario de parametrización `[data-testid="admin-plan-editor-form"]`.
4. Diligenciamiento de nuevo plan o actualización:
   - Slug: `enterprise-gastro`
   - Nombre: `Plan Enterprise Gastronómico`
   - Precio CLP: `89900`
   - Precio USD: `99.00`
   - Cuotas: users=`50`, products=`10000`, storage_mb=`10240`
5. Guardado con `[data-testid="save-plan-submit-btn"]`.
6. Verificación de la card Sonner Toast ("Plan Comercial guardado con éxito").
7. Verificación del banner confirmatorio `[data-testid="admin-plan-saved-banner"]`.
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
@pytest.mark.plans
def test_005_commercial_plans_customization_flow(
    page: Page,
    base_url: str,
    superadmin_credentials: dict[str, str],
) -> None:
    # 1. Autenticación como Superadmin
    _login_as_superadmin(page, base_url, superadmin_credentials)

    # 2. Navegar a /admin/plans
    page.goto(f"{base_url}/admin/plans")
    page.wait_for_load_state("networkidle")

    view = page.locator('[data-testid="admin-plans-view"]')
    expect(view).to_be_visible(timeout=10000)

    form = page.locator('[data-testid="admin-plan-editor-form"]')
    expect(form).to_be_visible(timeout=10000)

    # 3. Diligenciar campos del editor de planes
    slug_input = page.locator('[data-testid="plan-input-slug"]')
    expect(slug_input).to_be_visible()
    slug_input.fill("enterprise-gastro")

    name_input = page.locator('[data-testid="plan-input-name"]')
    expect(name_input).to_be_visible()
    name_input.fill("Plan Enterprise Gastronómico")

    price_clp_input = page.locator('[data-testid="plan-input-price-clp"]')
    if price_clp_input.is_visible():
        price_clp_input.fill("89900")

    price_usd_input = page.locator('[data-testid="plan-input-price-usd"]')
    if price_usd_input.is_visible():
        price_usd_input.fill("99.00")

    # Cuotas numéricas
    users_quota = page.locator('[data-testid="plan-quota-users"]')
    if users_quota.is_visible():
        users_quota.fill("50")

    products_quota = page.locator('[data-testid="plan-quota-products"]')
    if products_quota.is_visible():
        products_quota.fill("10000")

    storage_quota = page.locator('[data-testid="plan-quota-storage-mb"]')
    if storage_quota.is_visible():
        storage_quota.fill("10240")

    # 4. Enviar formulario
    submit_btn = page.locator('[data-testid="save-plan-submit-btn"]')
    expect(submit_btn).to_be_enabled()
    submit_btn.click()

    # 5. Verificación de la notificación flotante Sonner Toast
    toast = page.locator("[data-sonner-toast]").first
    expect(toast).to_be_visible(timeout=7000)
    expect(toast).to_contain_text("Plan Comercial guardado con éxito")

    # 6. Verificación del banner de confirmación
    saved_banner = page.locator('[data-testid="admin-plan-saved-banner"]')
    expect(saved_banner).to_be_visible(timeout=6000)
    expect(saved_banner).to_contain_text("Plan Enterprise Gastronómico")
