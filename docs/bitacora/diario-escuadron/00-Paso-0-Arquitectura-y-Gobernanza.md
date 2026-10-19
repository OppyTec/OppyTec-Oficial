---
title: "Bitácora Paso 0: Diseño Arquitectónico, las 17 Estrategias y el Escuadrón de 12 Agentes"
phase: "Paso 0"
date: "2026-10-18"
author_agent: "12-tech-writer-openspec-archify"
tags:
  - bitacora
  - paso-0
  - gobernanza
---

# 📓 Bitácora Paso 0: Cómo Se Diseñó el Nuevo Cerebro y la Arquitectura de OppyTec v2.0

> **Resumen en simple para personas:**  
> Antes de tocar o mover una sola línea de código de `OppyTec-Legacy`, dedicamos esta etapa fundacional (**Paso 0**) a analizar todos los dolores que tuvo la primera versión del proyecto y dejar escritas las reglas, planos y herramientas para que el equipo de desarrolladores y los **12 Agentes de IA** construyan OppyTec v2.0 con calidad bancaria, sin pisarse el trabajo y sin perder ni un solo detalle visual ni matemático del sistema original.

---

## 1. ¿Qué Problemas de `OppyTec-Legacy` Resolvimos en los Planos?

1. **El desorden de las migraciones de Base de Datos (Alembic):**
   - *Antes:* Había 75 archivos mezclando números (`0001..0039`) con códigos aleatorios (`6d39f9f7b07f`) y parches de unión (`merge_heads`).
   - *Ahora:* En v2.0 todas las migraciones son estrictamente correlativas (`0001`, `0002`, `0003`...) diferenciando si tocan el esquema global `public` o el de los restaurantes (`tenant`). Si dos programadores crean la `0004` al mismo tiempo en ramas distintas, un script automático renumera la segunda a `0005` sin conflictos.
2. **El control de accesos (RBAC), Cupos por Plan y Auditoría:**
   - *Antes:* El rol `admin` tenía acceso casi total igual que el dueño, y si un empleado trabajaba en el Hotel y en el Restaurante del mismo dueño había que duplicarle la cuenta.
   - *Ahora:* Separamos a los **Trabajadores de OppyTec (`public`, sin límite de cupos)** de los **Trabajadores del Cliente (`Holding` / `tenant_*`, sujetos al cupo de su plan)**. Si un cliente desactiva a un empleado (`soft-delete`), se le corta la sesión al instante, no se borra su historial pasado y **libera su cupo en el acto** para contratar a un reemplazo.
3. **El Asistente `OppyFy` y su Economía de Créditos:**
   - Rebautizado como **`OppyFy`** (con nombre configurable en 1 variable por si cambia a futuro).
   - Solo puede leer la documentación de negocio (`specs/business-domain/`) para ayudar al cliente, teniendo **bloqueado por completo revelar cómo está programado el código interno de OppyTec**.
   - Para responder sobre el restaurante (stock, ventas, demoras de proveedores o si alcanza la mercadería para un evento de 150 invitados), usa a **`JEV` (Sistema 1)** para elegir funciones matemáticas exactas en código duro, respetando un **Panel RBAC exclusivo de `OppyFy`** donde cada dueño puede crear y editar sus propios dominios y sub-dominios.
   - Se vende mediante **paquetes de créditos independientes del plan, acumulables (`1.000 + 10.000 = 11.000`) y sin fecha de caducidad**, registrando cada centavo y token en `public.llm_request_logs`.
4. **Idiomas (`i18n`) y Monedas (`FX`) Independientes:**
   - El usuario tiene en la barra superior un **Selector de Idioma con Bandera SVG (`🇪🇸 Español` / `🇺🇸 Inglés`)** que traduce tanto los botones del sistema como los productos y cargos creados por el cliente (`"Helado de Chocolate"` $\to$ `"Chocolate Ice Cream"`), pero **protege sin traducir los nombres propios y proveedores (`"Pollo King"`)**.
   - Y al lado tiene un **Selector de Moneda independiente (`CLP`, `USD`, `EUR`, `BRL`)** conectado gratuitamente al **Banco Central de Chile** y al **Banco Central Europeo**.
5. **Imágenes en Cloudflare R2, Respaldos en 4 Capas, Observabilidad y Tiempo Real:**
   - Las imágenes se comprimen automáticamente a `.webp` ultraligero en carpetas separadas por entorno y restaurante (`{env}/{holding}/{tenant}/`) con un medidor de memoria (`MB`) según el plan.
   - Los respaldos se guardan comprimidos y cifrados en **4 capas** permitiendo restaurar a **un solo restaurante** sin afectar a los demás.
   - Las notificaciones y saldos de stock viajan en vivo por **WebSockets + Redis Pub/Sub** (cero llamadas repetitivas).
   - Y se rescató el **ADN visual completo de Legacy** (incluyendo sus 3 temas: `light`, `dark` y el marino `ocean-blue`, sus 42 colores y sus 49 íconos) bajo diseño ***Mobile-First***.

---

## 2. ¿Qué Construimos Físicamente en el Paso 0?

- Se crearon las **17 Estrategias Maestras** dentro de `.agent/estrategias/`.
- Se crearon las **23 Reglas Inmutables** en `.agent/rules/00..22-*.md`.
- Se crearon las **12 Carpetas de los Agentes Especializados** en `.agent/subagents/01..12-*/`, donde cada agente tiene su `prompt.md`, su cuaderno de aprendizaje (`knowledge.md`) y su reporte de traspaso (`handovers/latest_handover.md`).
- Se selló la carpeta `.agent/evals/` con hashes `SHA-256` para que ningún agente pueda modificar las pruebas para "hacer trampa".
- Se programó `scripts/harness.py` con el comando `prepare-phase --phase N` para crear automáticamente los `Git Worktrees` y las órdenes de misión listas para usar en **Herdr**.

---

## 3. ¿Qué Sigue Ahora? (Próximo Paso)
- Iniciar la **Fase 1 (`specs/06-IMPLEMENTATION-PLAN.md`):** Levantar el andamiaje de contenedores Docker, `Makefile`, `src/core/config.py`, `src/core/observability.py`, el arranque de Backend y Frontend, y los tests de arquitectura del *Fast Gate*.
