---
title: "Bitácora Fase 4: Endpoints API REST FastAPI, 4 Guardias HTTP Deterministas, Resiliencia y 11 Vectores Red Team + Schemathesis"
phase: "Fase 4"
date: "2026-10-19"
author_agent: "12-tech-writer-openspec-archify"
tags:
  - bitacora
  - fase-4
  - fastapi
  - rbac-guards
  - red-team
  - schemathesis
  - resiliencia
  - archify
---

# 📓 Bitácora Fase 4: Cómo Se Construyeron los Endpoints API REST de los 10 Módulos, los 4 Guardias HTTP Deterministas y la Auditoría Ofensiva Red Team

> **Resumen en simple para personas:**  
> En la **Fase 4**, el Escuadrón conectó todo el cerebro de negocio (construido en la Fase 3) con el mundo exterior a través de **Endpoints HTTP REST en FastAPI (`/api/v1/...`)** para los **10 módulos de OppyTec v2.0**. Ninguna puerta quedó sin llave: cada ruta está blindada por **4 Guardias Deterministas de Seguridad (`RBAC de 3 niveles`, `Magic Bytes` para archivos, `Sanitizador Anti-XSS/SSTI` y `Rate Limiter` por canal)**, aislamiento transaccional de esquemas (`SET LOCAL search_path` $\to$ `RESET search_path`), resiliencia ante caídas de Redis (`< 50ms`) y prevención matemática de bloqueos (*deadlocks*). Además, el **Agente 10 (`Red Team`)** y el **Agente 09 (`QA`)** bombardearon la API con **11 vectores ofensivos estilo Kali Linux (`test_01..11`)** y fuzzing automático de contratos **OpenAPI con `Schemathesis`**.

---

## 1. ¿Qué Construyó Cada Agente del Escuadrón en la Fase 4?

### ⚙️ Agente 04 (`04-backend-senior-dev`) + Agente 06 (`06-ai-oppyfy-and-jev-engineer`) + Agente 07 (`07-i18n-and-fx-currency-specialist`) — Capa Presentation (`router.py` + `schemas.py`) y 4 Guardias HTTP
1. **Los 4 Guardias Deterministas en `oppytec-backend/src/core/guards/`:**
   - **`rbac_dependencies.py` (`RequireGlobalPermission` y `RequireTenantPermission`):** Ningún endpoint se ejecuta sin verificar el permiso exacto de 3 niveles (`<modulo>.<submodulo>.<funcion>`), la intersección con los módulos contratados en el Plan del Holding ($\mathbf{M}_{\text{Plan}} \cap ((\mathbf{P}_{\text{Rol}} \cup \mathbf{P}_{\text{Temp}}) \setminus \mathbf{P}_{\text{Deny}})$), las 3 leyes de rango (`hierarchy_rank`) y la vigencia de permisos temporales JIT.
   - **`file_magic_guard.py` (Inspección Binaria *Magic Bytes*):** Valida la firma binaria real de imágenes (`PNG`, `JPEG`, `WebP`), documentos (`PDF`) y planillas (`XLSX`), rechazando ejecutables disfrazados, `.svg` con scripts, *Zip Bombs* o inyecciones de fórmulas en Excel (`=CMD|`), y verificando la cuota en MB de Cloudflare R2 antes de procesar.
   - **`xss_sanitizer.py` (Sanitización Políglota):** Limpia etiquetas `<script>`, manejadores de eventos HTML, esquemas `javascript:`, intentos de *Server-Side Template Injection (`{{7*7}}`)* y *Path Traversal (`../`)*, conservando intactos los acentos y marcas propias como `"Pollo King"`.
   - **`rate_limiter.py` (Ventana Deslizante por Canal):** Limita intentos de login (`Auth: 5 req/min`), llamadas operativas (`API: 120 req/min`) y consultas al asistente `OppyFy` (`AI: 20 req/min`) aislando las llaves por `ENV_NAMESPACE` y Tenant.

2. **Routers y Contratos Pydantic v2 de los 10 Módulos (`oppytec-backend/src/modules/*/presentation/`):**
   - **`identity` y `tenancy`:** Login con `Argon2id`, emisión de JWT, revocación instantánea en Redis al hacer *soft-delete* de un trabajador (liberando el cupo comercial en el acto), gestión de Holdings, Entidades Legales (`1:1` con Tenant), sucursales y planes.
   - **`audit`:** Consulta forense inmutable (*Append-Only*) tanto para el SuperUser de OppyTec (`public`) como para el Propietario del restaurante (`tenant_<slug>`), mostrando el linaje de autorización (`authorization_lineage`).
   - **`catalog`, `inventory`, `recipes`, `procurement`, `operations` y `analytics`:** Endpoints completos con aritmética 100% `Decimal`, conversión de unidades en 3 capas, Kardex serializado con `ORDER BY id ASC FOR UPDATE` (cero *deadlocks*), escandallos recursivos, conciliación de compras/facturas, ventas POS, buffet, mermas y reportes ejecutivos.
   - **`oppy_ai` (`OppyFy`) + `i18n` + `FX`:** Endpoints para el chat `OppyFy` con RAG de 3 capas (indexando 0% de `engineering-code/`), panel RBAC propio editable por cliente, billetera acumulable de créditos sin caducidad, vistas FinOps (`llm_request_logs`), consola de tasas del Banco Central (`BCCh` + `BCE Frankfurter`) y traducción dinámica con protección de nombres propios.

### 🛡️ Agente 10 (`10-cybersecurity-redteam-auditor`) + Agente 09 (`09-qa-parity-and-test-engineer`) — Los 11 Vectores Ofensivos Red Team y Fuzzing OpenAPI con Schemathesis
1. **Suite Ofensiva Automatizada (`oppytec-backend/tests/security_redteam/test_01..11_*.py`):**
   - **`test_01` (IDOR Multi-Tenant y Multi-Holding):** Certifica que un token de `tenant_a` jamás pueda leer ni modificar datos de `tenant_b`.
   - **`test_02` (Ataques Criptográficos JWT y Sesiones):** Certifica el rechazo de `alg=none`, firmas alteradas, tokens expirados y sesiones revocadas por *soft-delete*.
   - **`test_03` (Escalada de Privilegios RBAC y Delegación):** Certifica que ningún usuario pueda autoasignarse ni delegar un permiso que no posee o de rango superior.
   - **`test_04` (Inyecciones Políglotas SQLi, XSS, SSTI, LFI):** Bombardea filtros, buscadores y notas verificando neutralización total.
   - **`test_05` (Subida de Archivos Maliciosos y Exploits Excel):** Verifica bloqueo por *Magic Bytes*, *Zip Bombs* y sanitización de celdas DDE/CSV.
   - **`test_06` (Condiciones de Carrera y *Double-Spend*):** Lanza ráfagas concurrentes contra stock de Kardex, cupos de usuarios del plan y créditos de `OppyFy`, comprobando cero sobregiros y cero *deadlocks*.
   - **`test_07` (Fuga de Información y Cabeceras HTTP):** Verifica cabeceras de seguridad (`CSP`, `HSTS`, `X-Frame-Options`, `X-Trace-ID`) y redacción del 100% de datos personales (PII) y secretos en logs/errores.
   - **`test_08` (Prompt Injection y Aislamiento RAG en `OppyFy`):** Certifica que `OppyFy` nunca filtre código fuente ni documentos de `specs/engineering-code/` y respete el RBAC de sub-dominios.
   - **`test_09` (Escáner AST de Cero Hardcoding y `SecretStr`):** Audita el árbol sintáctico de todo el backend garantizando 0 secretos quemados en el código.
   - **`test_10` (Ingeniería del Caos y Circuit Breakers):** Simula la caída súbita de Redis (`RedisCircuitBreaker < 50ms`), saltos cambiarios anómalos (`> 8%`) y reciclaje del pool de conexiones (`RESET search_path`).
   - **`test_11` (Frontera de los 5 Entornos y *Fail-Fast*):** Verifica que entornos no productivos usen el *Sinkhole* de correo (`Mailpit`) y que producción oculte `/docs` y exija claves de alta entropía.
2. **Fuzzing de Contratos con `Schemathesis` (`oppytec-backend/tests/contracts/test_openapi_schemathesis.py`):**
   - Valida automáticamente el esquema `/openapi.json` y genera miles de combinaciones de entradas bordes comprobando que ningún endpoint responda jamás con un error no controlado (`HTTP 500`).

### 🏛️ Agente 12 (`12-tech-writer-openspec-archify`) — Mapa 4 del Atlas Interactivo Archify y Segundo Cerebro
- **Mapa 4 del Atlas Visual Interactivo (`docs/architecture/atlas/04-critical-runtime-flows-and-resilience.archify.html`):** Construyó el tablero interactivo HTML autocontenido (con su fuente tipada `04-critical-runtime-flows-and-resilience.archify.json` y recibo `04-critical-runtime-flows-and-resilience.receipt.json` sellado con `SHA-256`), incorporando **20 nodos semánticos**, **23 aristas**, **4 zonas de confianza**, **5 lentes** y la **Sonda de Ruta Dirigida (*Route Probe*)** para trazar paso a paso el flujo E2E desde la petición HTTP hasta el broadcast WebSocket.

---

## 2. ¿Cómo Auditar Visualmente los Flujos E2E, los 4 Guardias y los 11 Vectores Red Team?

Abre directamente en tu navegador web el **Mapa 4 del Atlas Interactivo de Archify**:
- [`docs/architecture/atlas/04-critical-runtime-flows-and-resilience.archify.html`](../../architecture/atlas/04-critical-runtime-flows-and-resilience.archify.html)

En la barra superior del mapa puedes usar:
1. **Las 5 Lentes Interactivas:** *Vista Completa*, *Flujos Críticos E2E Runtime*, *4 Guardias HTTP Deterministas*, *Resiliencia y Caos*, y *11 Vectores Red Team + Schemathesis*.
2. **La Sonda de Ruta Dirigida (*Route Probe*):** Selecciona por ejemplo `1. Auth, JWT PyJWT & X-Tenant-ID Header` como origen y `5. WebSocket Realtime Broadcast & Catch-Up` como destino, y pulsa **"Trazar Ruta"** para ver iluminados los 7 eslabones exactos por los que viaja cada transacción en OppyTec v2.0.

---

## 3. ¿Qué Sigue Ahora? (Rumbo a la Fase 5)
- Consolidar todas las ramas de la Fase 4 en `master` mediante el *Smart Merge Train* verificando `make fast-gate` y `make main-gate`.
- Iniciar la **Fase 5 (`specs/06-IMPLEMENTATION-PLAN.md`):** Construcción completa de las vistas e interfaces en **React 19 (`oppytec-frontend/`)** conservando el **ADN Visual de Legacy** (los 3 temas `light`, `dark`, `ocean-blue`, 42 colores, 49 íconos, efectos glassmorphism y diseño *Mobile-First*), el componente `<Can perform="modulo.submodulo.funcion">`, el conmutador multi-sucursal `<HoldingTenantSwitcher />`, los selectores de bandera SVG (`i18n`) y moneda (`FX`), y la sincronización en vivo por WebSockets con TanStack Query v5.
