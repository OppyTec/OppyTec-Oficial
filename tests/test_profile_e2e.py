import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

SCREENSHOT_PATH = Path("/home/jcampillay/.gemini/antigravity-cli/brain/202f6db5-d371-42a9-a3a7-75de42b066d6/profile_view.png")
SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

def run():
    print("[E2E] Starting Playwright browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1350})
        page = context.new_page()

        # Step 1: Login
        print("[E2E] Navigating to http://localhost:5173/admin/login ...")
        page.goto("http://localhost:5173/admin/login")
        page.wait_for_load_state("networkidle")

        expect(page.locator('[data-testid="admin-login-page"]')).to_be_visible(timeout=10000)
        page.locator("#admin-email").fill("oppytec.admin@gmail.com")
        page.locator("#admin-password").fill("oppytec.2026")
        page.locator('button[type="submit"]').click()

        page.wait_for_url("**/admin", timeout=12000)
        print("[E2E] Logged in successfully. Current URL:", page.url)

        # Step 2: Ir a /admin/tenants -> Entrar -> Ir al Local
        print("[E2E] Navigating to /admin/tenants ...")
        page.goto("http://localhost:5173/admin/tenants")
        page.wait_for_load_state("networkidle")
        expect(page.locator('[data-testid="admin-tenants-view"]')).to_be_visible(timeout=10000)

        # Click on 'Entrar'
        entrar_btn = page.locator('button:has-text("Entrar")').first
        if entrar_btn.is_visible():
            print("[E2E] Clicking 'Entrar' on tenant...")
            entrar_btn.click()
            time.sleep(1)

        # Click on 'Ir al Local'
        ir_local_btn = page.locator('button:has-text("Ir al Local")').first
        if ir_local_btn.is_visible():
            print("[E2E] Clicking 'Ir al Local'...")
            ir_local_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)

        # Step 3: Open user pill in AppBar and click 'Ver Perfil' or go to /perfil
        print("[E2E] Checking user pill / profile navigation...")
        user_pill = page.locator('button:has([data-testid="avatar-fallback"]), button:has-text("Admin"), button:has-text("Super")').first
        if user_pill.is_visible():
            user_pill.click()
            time.sleep(0.5)
            ver_perfil_btn = page.locator('button:has-text("Ver Perfil"), button:has-text("Ver Mi Perfil")').first
            if ver_perfil_btn.is_visible():
                print("[E2E] Clicking 'Ver Perfil'...")
                ver_perfil_btn.click()
            else:
                page.goto("http://localhost:5173/perfil")
        else:
            page.goto("http://localhost:5173/perfil")

        page.wait_for_load_state("networkidle")
        time.sleep(1.5)

        # Step 4: Verify rendering of profile view components
        print("[E2E] Verifying Profile View components...")
        expect(page.locator('[data-testid="profile-page-root"]')).to_be_visible(timeout=10000)

        # Check Avatar & Role
        avatar_btn = page.locator('button[aria-label="Cambiar foto de perfil"], button[title="Cambiar foto de perfil"]').first
        expect(avatar_btn).to_be_visible()
        print("[E2E] Avatar & camera button visible: OK")

        # Check Voice command
        voice_box = page.locator('text="Comando de Voz Oppy (Modo Manos Libres)"').first
        expect(voice_box).to_be_visible()
        print("[E2E] Voice command box visible: OK")

        # Check Operational Summary
        summary_title = page.locator('text="Resumen Operativo"').first
        expect(summary_title).to_be_visible()
        print("[E2E] Operational summary visible: OK")

        # Check Templates Section & Tabs
        templates_title = page.locator('text="Mis Plantillas Personalizadas"').first
        expect(templates_title).to_be_visible()
        print("[E2E] Templates section visible: OK")

        # Check '+ Nueva Plantilla' button and modal
        new_template_btn = page.locator('button:has-text("+ Nueva Plantilla")').first
        expect(new_template_btn).to_be_visible()
        new_template_btn.click()
        time.sleep(0.5)
        expect(page.locator('[data-testid="responsive-dialog"]')).to_be_visible()
        print("[E2E] ResponsiveDialog for + Nueva Plantilla visible: OK")

        # Close dialog
        cancel_btn = page.locator('button:has-text("Cancelar")').last
        if cancel_btn.is_visible():
            cancel_btn.click()
            time.sleep(0.5)

        # Switch to Consumo Interno tab
        consumo_tab = page.locator('button:has-text("Consumo Interno")').first
        if consumo_tab.is_visible():
            consumo_tab.click()
            time.sleep(0.5)
            print("[E2E] Switched to Consumo Interno tab: OK")

        # Switch back to Tablas
        tablas_tab = page.locator('button:has-text("Vista de Tablas")').first
        if tablas_tab.is_visible():
            tablas_tab.click()
            time.sleep(0.5)

        # Step 5: Scroll to the very top and capture viewport
        print(f"[E2E] Scrolling to top and saving screenshot to {SCREENSHOT_PATH}...")
        page.evaluate("() => { window.scrollTo(0, 0); document.documentElement.scrollTop = 0; document.body.scrollTop = 0; const m = document.querySelector('main'); if (m) m.scrollTop = 0; }")
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOT_PATH))
        print("[E2E] Screenshot saved successfully!")

        browser.close()

if __name__ == "__main__":
    run()
