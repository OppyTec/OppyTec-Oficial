# Base de Conocimiento Evolutiva — Agente 13: Especialista en Navegador E2E y Simulación Humana Playwright

> Lecciones aprendidas específicas de `13-browser-e2e-playwright-specialist` para perfeccionar la simulación de usuarios humanos y evitar fallos por asincronía o cambios en el DOM.

---

### 1. Lecciones Destiladas del Código Legacy (`tests/002_admin`)

- **[Legacy 002 — Desplazamiento Forzado en Modales con Contenedores Internos `overflow-y-auto`]:**
  En formularios modales con gran cantidad de campos (ej. creación de usuarios globales, entidades legales y tenants), los botones inferiores (`"Guardar"`, `"Cancelar"`) o switches quedan ocultos debajo del pliegue visible del modal.
  * *Patrón comprobado en Legacy:*
    ```python
    scroll_container = page.locator("form > div.overflow-y-auto")
    if await scroll_container.count() > 0:
        await scroll_container.evaluate("el => el.scrollTop = el.scrollHeight")
    ```
  * En React 19 / Tailwind, también es recomendable asegurar visibilidad individual con `await element.scroll_into_view_if_needed()` antes del clic.

- **[Legacy 002 — Manejo Seguro de Switches `aria-checked` para Evitar Deselecciones]:**
  Los switches accesibles (`button[role="switch"]`) invierten su estado con cada clic. En pruebas que se reintentan o estados pre-cargados, hacer clic ciego puede apagar un switch que ya estaba encendido.
  * *Patrón comprobado en Legacy:*
    ```python
    switches = page.locator("button[role='switch']")
    switch_count = await switches.count()
    for i in range(switch_count):
        sw = switches.nth(i)
        await sw.scroll_into_view_if_needed()
        if await sw.get_attribute("aria-checked") != "true":
            await sw.click(force=True)
    ```

- **[Legacy 002 — Interacción con Selects Dinámicos de Holdings y Entidades]:**
  Al poblar desplegables cuyos valores dependen de registros creados en pasos previos (ej. vincular una Entidad Legal a "Grupo Pacífico"), el selector debe esperar a que las opciones estén adjuntas en el DOM antes de intentar iterar o seleccionar:
  ```python
  holding_select = page.locator("select#holding_id")
  await holding_select.wait_for(state="attached", timeout=10000)
  ```

---

### 2. Adaptaciones al Stack Moderno de OppyTec v2.0

- **[React 19 & Radix UI — Portales Desplegables Fuera del Modal]:**
  Los componentes `<Select>` de Radix UI montan el menú de opciones (`[role="listbox"]`) a través de un `Portal` directamente como hijo de `document.body` (no dentro del modal `<form>`).
  * *Solución:* Para hacer clic en una opción de un Select de Radix UI, primero se hace clic en el disparador (`trigger`), y luego se localiza el item en el documento raíz:
    ```python
    await page.locator("button[role='combobox']").click()
    await page.locator("[role='option']:has-text('Grupo Pacífico')").click()
    ```

- **[TanStack Query — Invalidación Asíncrona de Caché tras Mutaciones]:**
  Tras enviar un formulario con `POST` o `PUT`, TanStack Query invalida la consulta (`queryClient.invalidateQueries(...)`) y re-ejecuta el `GET` en segundo plano. Si el test asume que los datos están en la tabla de inmediato, puede ocurrir una condición de carrera antes de que la nueva fila sea renderizada.
  * *Solución:* Usar aserciones con reintento automático de Playwright:
    ```python
    await expect(page.locator("td:has-text('nuevo_usuario')").first).to_be_visible(timeout=10000)
    ```
    No utilizar `sleep()` fijos; dejar que el matcher `expect` de Playwright sondee el DOM con backoff exponencial.

- **[Mobile-First y Responsive Breakpoints]:**
  En OppyTec v2.0, los paneles de navegación laterales se contraen en viewports móviles (< 768px, Tailwind `md:`), requiriendo abrir el drawer mediante el botón de menú hamburguesa (`button[aria-label="Abrir menú"]`).
  * *Configuración de Contexto:* Al simular escenarios móviles, configurar explícitamente:
    ```python
    context = await browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True)
    ```

- **[Validación Visual de Cuotas Comerciales (Planes y Capacidad)]:**
  En el Plan Básico (límite de 3 usuarios activos), al crear el 4to usuario, la UI reacciona mostrando el badge `OVER_QUOTA` (rojo) o una advertencia en el modal (`QuotaExceededError`).
  * El Agente 13 debe verificar tanto el camino feliz (usuarios 1 al 3 creados exitosamente) como el límite defensivo (intento de 4to usuario bloqueado con mensaje amigable sin crash de la aplicación).

- **[Gestión de Sesión, Tokens JWT y Encabezado `X-Tenant-Schema`]:**
  El frontend almacena el token JWT de sesión en `localStorage` o cookies seguras. En rutas del portal administrativo global se utiliza el esquema `public`, mientras que al ingresar al espacio de un inquilino específico se inyecta el slug del tenant. Al navegar directamente por URL (`page.goto`), asegurarse de que el estado de autenticación esté inicializado o pasar por el flujo de `/admin/login`.
