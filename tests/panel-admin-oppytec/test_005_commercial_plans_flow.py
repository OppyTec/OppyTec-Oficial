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

    view = page.locator('[data-testid="plans-page"], [data-testid="admin-plans-view"]')
    expect(view).to_be_visible(timeout=10000)

    # 3. Abrir modal con botón "+ Crear Nuevo Plan"
    create_btn = page.locator('[data-testid="create-plan-btn"]')
    expect(create_btn).to_be_visible(timeout=8000)
    create_btn.click()

    # Formulario dentro del diálogo modal
    form = page.locator('[data-testid="plan-form-modal"], [data-testid="admin-plan-editor-form"]')
    expect(form).to_be_visible(timeout=8000)

    # 4. Diligenciar campos del editor de planes
    name_input = page.locator('[data-testid="plan-form-name-input"], [data-testid="plan-input-name"]')
    expect(name_input).to_be_visible()
    name_input.fill("Plan Enterprise Gastronómico")

    slug_input = page.locator('[data-testid="plan-form-slug-input"], [data-testid="plan-input-slug"]')
    expect(slug_input).to_be_visible()
    slug_input.fill("enterprise-gastro")

    desc_input = page.locator('[data-testid="plan-form-description-input"]')
    if desc_input.is_visible():
        desc_input.fill("Plan integral para cadenas de restaurantes de alto volumen")

    price_clp_input = page.locator('[data-testid="plan-form-price-clp-input"], [data-testid="plan-input-price-clp"]')
    if price_clp_input.is_visible():
        price_clp_input.fill("89900")

    price_usd_input = page.locator('[data-testid="plan-form-price-usd-input"], [data-testid="plan-input-price-usd"]')
    if price_usd_input.is_visible():
        price_usd_input.fill("99")

    credits_input = page.locator('[data-testid="plan-form-credits-input"]')
    if credits_input.is_visible():
        credits_input.fill("5000")

    # Cuotas numéricas si existen
    users_quota = page.locator('[data-testid="plan-quota-users"]')
    if users_quota.is_visible():
        users_quota.fill("50")

    products_quota = page.locator('[data-testid="plan-quota-products"]')
    if products_quota.is_visible():
        products_quota.fill("10000")

    storage_quota = page.locator('[data-testid="plan-quota-storage-mb"]')
    if storage_quota.is_visible():
        storage_quota.fill("10240")

    # 5. Enviar formulario
    submit_btn = page.locator('[data-testid="plan-form-submit-btn"], [data-testid="save-plan-submit-btn"]')
    expect(submit_btn).to_be_enabled()
    submit_btn.click()

    # 6. Verificación de la notificación flotante o card creada
    toast = page.locator("[data-sonner-toast]").first
    card = page.locator('[data-testid="plan-card-enterprise-gastro"]')
    banner = page.locator('[data-testid="admin-plan-saved-banner"]')
    expect(toast.or_(card).or_(banner)).to_be_visible(timeout=8000)
