---
title: "Bitácora Fase 1: Setup de los 5 Entornos, Observabilidad 4-Pilares, Andamiaje Full-Stack y Atlas Archify"
phase: "Fase 1"
date: "2026-10-19"
author_agent: "12-tech-writer-openspec-archify"
tags:
  - bitacora
  - fase-1
  - entornos
  - observabilidad
  - archify
  - adr
---

# 📓 Bitácora Fase 1: Cómo Se Levantó la Infraestructura, la Observabilidad y el Andamiaje de OppyTec v2.0

> **Resumen en simple para personas:**  
> En la **Fase 1**, el Escuadrón de Agentes pasó de los planos del **Paso 0** a construir los cimientos reales y ejecutables del proyecto trabajando en paralelo desde sus propios **Git Worktrees** aislados. Al terminar esta fase, OppyTec v2.0 ya cuenta con sus contenedores listos (`PostgreSQL 16 + pgvector`, `Redis 7`, `Backend`, `Frontend` y el centro de monitoreo con `Grafana`, `GlitchTip` y `Umami`), un arranque blindado que oculta contraseñas (`SecretStr`), las **15 pruebas automáticas de Caja Blanca** que protegen la arquitectura en menos de 15 segundos, las **21 Decisiones de Arquitectura (`ADR-001` al `ADR-021`)** y el **Mapa 5 Interactivo de Archify**.

---

## 1. ¿Qué Construyó Cada Agente del Escuadrón en la Fase 1?

### 🛠️ Agente 08 (`08-environments-and-observability-engineer`) — Entornos, Docker, Makefile y Observabilidad
- **`docker-compose.yml` con Perfil de Observabilidad:** Configuró la base de datos `PostgreSQL 16 + pgvector`, `Redis 7`, `Backend`, `Frontend` y el perfil `--profile observability` que enciende `Grafana LGTM` (`Loki`, `Grafana`, `Tempo`, `Mimir`), `GlitchTip` (compatible con Sentry), `Umami` (analítica sin cookies) y `Mailpit`.
- **`Makefile` y `.pre-commit-config.yaml`:** Dejó listos los comandos deterministas (`make fast-gate`, `make main-gate`, `make deep-gate`, `make smart-merge`, `make migration-rebase`) y los candados pre-commit (`gitleaks`, `ruff`, `mypy`, `eslint`, `tsc`).
- **Configuración *Fail-Fast* (`oppytec-backend/src/core/config.py`):** Si falta una variable crítica al encender el servidor, el sistema avisa en el milisegundo `0`. Todas las llaves secretas usan `SecretStr` para que jamás aparezcan escritas por error en un log. Además, en `production` se apaga automáticamente la pantalla pública de Swagger (`docs_url=None`).
- **Observabilidad con Filtro Anti-Filtraciones (`oppytec-backend/src/core/observability.py`):** Cada petición lleva un código de rastreo único (`X-Trace-ID`) y pasa por `scrub_telemetry_payload()`, que borra automáticamente contraseñas, tokens, tarjetas o RUTs (`"[REDACTED]"`) antes de guardar cualquier log.

### ⚙️ Agente 04 (`04-backend-senior-dev`) — Andamiaje Backend y 15 Guardianes de Arquitectura
- **Base del Servidor (`oppytec-backend/`):** Creó el `Dockerfile` multi-etapa seguro (usuario sin permisos de root), `pyproject.toml` (con `uv`, `ruff`, `mypy --strict`, `pytest`, `import-linter`), `.env.example` y `src/main.py` con el endpoint `/health`.
- **Las 15 Pruebas de Caja Blanca (`oppytec-backend/tests/architecture/`):** Programó los 15 tests automáticos que revisan el código fuente en pocos segundos para impedir que alguien rompa Clean Architecture, olvide un permiso RBAC, use decimales inexactos (`float`), deje textos sin traducir o altere las migraciones de Alembic.

### 🎨 Agente 05 (`05-frontend-senior-dev`) — Andamiaje Frontend React 19 e Invarianza `SHA-256`
- **Base Web *Mobile-First* (`oppytec-frontend/`):** Configuró React 19, TypeScript estricto (`noImplicitAny: true`), Vite, Tailwind CSS con los **3 temas de Legacy (`light`, `dark`, `ocean-blue`)**, `knip.json` y `.dependency-cruiser.cjs`.
- **Invarianza de Imagen con `/runtime-env.js` (`docker-entrypoint.sh`):** Logró que la misma imagen compilada y probada en `ci` se promueva intacta a `staging` y `production` inyectando las variables públicas al arrancar el contenedor y validándolas con `Zod` en `src/shared/config/env.ts`.
- **Telemetría en el Navegador (`src/shared/telemetry/`):** Conectó `otel.ts`, `sentry.ts` y `umami.ts` respetando privacidad y propagando `X-Trace-ID`.

### 🏛️ Agente 12 (`12-tech-writer-openspec-archify`) — Los 21 ADRs, Mapa 5 de Archify y Segundo Cerebro
- **21 Architecture Decision Records (`docs/adr/ADR-001` al `ADR-021`):** Documentó de forma inmutable las 21 grandes decisiones técnicas de OppyTec v2.0 y qué test automático vigila cada una.
- **Mapa 5 del Atlas Visual Interactivo (`docs/architecture/atlas/05-environments-and-agentic-harness.archify.html`):** Construyó el tablero interactivo autocontenido en HTML (con su fuente tipada `.archify.json` y recibo `.receipt.json` sellado con `SHA-256`) para explorar visualmente los 5 entornos, los Git Worktrees, los Quality Gates y la Observabilidad de 4 Pilares.
- **Actualización de esta Bitácora en Obsidian (`docs/bitacora/`):** Conectó el Mapa Maestro del Segundo Cerebro con los entregables reales de la Fase 1.

---

## 2. ¿Cómo Auditar Visualmente lo Construido en esta Fase?

Puedes abrir directamente en tu navegador (sin necesitar ningún servidor encendido) el archivo:
- [`docs/architecture/atlas/05-environments-and-agentic-harness.archify.html`](../../architecture/atlas/05-environments-and-agentic-harness.archify.html)

Allí podrás filtrar por las 4 lentes (**5 Entornos**, **RLM Harness & Worktrees**, **Observabilidad 4-Pilares** y **Quality Gates**), alternar entre los 3 temas de OppyTec (`ocean-blue`, `dark`, `light`) y hacer clic en cualquiera de los 16 nodos para ver qué archivo exacto lo implementa y qué test lo protege.

---

## 3. ¿Qué Sigue Ahora? (Rumbo a la Fase 2)
- Ejecutar el *Smart Merge Train* para unir los worktrees de la Fase 1 en `master` verificando `make fast-gate` (`< 15s`).
- Iniciar la **Fase 2 (`specs/06-IMPLEMENTATION-PLAN.md`):** Construir el motor de base de datos Multi-Schema (`public` vs `tenant_<slug>`), las migraciones correlativas `0001_public` y `0002_tenant`, el Bootstrap Génesis (`oppytec.admin`), los respaldos cifrados en 4 capas (`zstd + age`) y el **Mapa 1 de Archify (`01-tenancy-and-schemas.archify.html`)**.
