# OppyTec v2.0 — Plataforma SaaS de Gestión Gastronómica y Comercial

> **Monorepo Oficial de OppyTec**  
> Arquitectura Multi-Tenant desacoplada para gestión de inventarios, recetas (escandallos), mermas, compras y analítica en tiempo real para restaurantes, hoteles y cadenas multilocales (Holdings).

---

## 🏛️ Documentación Maestra y Estrategias Normativas

Antes de modificar cualquier línea de código, todo desarrollador y agente de IA debe regirse por el marco normativo del monorepo:

- **[`MASTER-AGENTIC-ENGINEERING-FRAMEWORK.md`](MASTER-AGENTIC-ENGINEERING-FRAMEWORK.md):** Constitución de Ingeniería Agéntica, RLM Harness (**Prime Agent**), **JEV** y Quality Gates.
- **[`propuesta_arquitectura_tree_001.md`](propuesta_arquitectura_tree_001.md):** Árbol completo (`tree`) de directorios, subdirectorios y archivos críticos de OppyTec v2.0.
- **Las 13 Estrategias Maestras de Refactorización (`_001.md`):**
  1. [`.agent/estrategias/estrategia_migraciones_alembic_001.md`](.agent/estrategias/estrategia_migraciones_alembic_001.md) — Migraciones correlativas `0001..NNNN`, esquemas `public` vs `tenant_*` y Bootstrap Génesis (`oppytec.admin`).
  2. [`.agent/estrategias/estrategia_rbac_y_auditoria_001.md`](.agent/estrategias/estrategia_rbac_y_auditoria_001.md) — RBAC Dual de 3 niveles (`<modulo>.<submodulo>.<funcion>`), acceso transversal en el Holding, cupos con `soft-delete` y auditoría forense.
  3. [`.agent/estrategias/estrategia_testing_calidad_y_seguridad_001.md`](.agent/estrategias/estrategia_testing_calidad_y_seguridad_001.md) — Co-Creación 1:1 de tests, 5 dimensiones, Gates estratificados, Cero Hardcoding y 11 vectores Red Team (Kali + Caos).
  4. [`.agent/estrategias/estrategia_entornos_y_despliegue_001.md`](.agent/estrategias/estrategia_entornos_y_despliegue_001.md) — Los 5 entornos (`local`, `preview`, `ci`, `staging`, `production`), invarianza `SHA-256` (`runtime-env.js`) y configuración *Fail-Fast*.
  5. [`.agent/estrategias/estrategia_orquestacion_git_worktrees_y_smart_merge_001.md`](.agent/estrategias/estrategia_orquestacion_git_worktrees_y_smart_merge_001.md) — Orquestación paralela con **Prime Agent (`rlm.spawn`)**, Git Worktrees, AST Claiming (`fcntl.flock`) y *Smart Merge Train*.
  6. [`.agent/estrategias/estrategia_visualizacion_y_auditoria_archify_001.md`](.agent/estrategias/estrategia_visualizacion_y_auditoria_archify_001.md) — Atlas Visual Interactivo HTML (`Archify` alimentado desde `Graphify` a costo 0 de tokens).
  7. [`.agent/estrategias/estrategia_openspec_negocio_vs_codigo_001.md`](.agent/estrategias/estrategia_openspec_negocio_vs_codigo_001.md) — Bipartición de `specs/` (`business-domain/` para clientes/futuro RAG clientes vs `engineering-code/` para devs/futuro RAG ingeniería).
  8. [`.agent/estrategias/estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md`](.agent/estrategias/estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md) — Asistente **`OppyFy`** (marca configurable), RAG de 3 capas, RBAC propio editable por cliente, paquetes de créditos acumulables sin caducidad, medidor `% contexto` y FinOps `llm_request_logs`.
  9. [`.agent/estrategias/estrategia_motor_decisiones_jev_system1_001.md`](.agent/estrategias/estrategia_motor_decisiones_jev_system1_001.md) — Motor global **JEV (Sistema 1)** con los 4 candados automáticos *"¿Lo puede hacer JEV (Sí/No)?"*.
  10. [`.agent/estrategias/estrategia_internacionalizacion_i18n_multilenguaje_001.md`](.agent/estrategias/estrategia_internacionalizacion_i18n_multilenguaje_001.md) — `i18n` Full-Stack (`es` 🇪🇸 / `en` 🇺🇸 + futuros), selector de banderas SVG, traducción dinámica de datos cliente protegiendo nombres propios (`Pollo King`) y patrón minimalista `Pi`.
  11. [`.agent/estrategias/estrategia_multimoneda_fx_precios_y_cobros_001.md`](.agent/estrategias/estrategia_multimoneda_fx_precios_y_cobros_001.md) — Motor Multi-Moneda FX (Bancos Centrales BCCh + BCE), selector independiente del idioma, consola admin con override manual y gestión de precios.
  12. [`.agent/estrategias/estrategia_observabilidad_monitoreo_y_analitica_001.md`](.agent/estrategias/estrategia_observabilidad_monitoreo_y_analitica_001.md) — Los 4 pilares (`OpenTelemetry`, `Grafana LGTM`, `Sentry/GlitchTip`, `Umami`) y Centro de Observabilidad con 13 sub-vistas y filtro por `Environment` en `platform-admin`.
  13. [`.agent/estrategias/estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md`](.agent/estrategias/estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md) — Almacenamiento Cloudflare R2 aislado por Tenant/Entorno, compresión WebP en 2 capas y cuota de memoria MB por plan.
  14. [`.agent/estrategias/estrategia_respaldos_base_datos_y_recuperacion_001.md`](.agent/estrategias/estrategia_respaldos_base_datos_y_recuperacion_001.md) — Respaldos en 4 Capas cifrados (`zstd+age` en Neon PITR, R2 Vault, VPS Secundario y Servidor Local) con restauración quirúrgica de un solo Tenant.
  15. [`.agent/estrategias/estrategia_escuadron_multiagente_prompts_y_autoreparacion_001.md`](.agent/estrategias/estrategia_escuadron_multiagente_prompts_y_autoreparacion_001.md) — Los **12 Agentes Especializados**, System Prompts, jerarquía Gemini Argon/Flash + JEV y bucles de autoreparación en QA y Ciberseguridad.
  16. [`.agent/estrategias/estrategia_sistema_diseno_ux_ui_y_mobile_first_001.md`](.agent/estrategias/estrategia_sistema_diseno_ux_ui_y_mobile_first_001.md) — Rescate exhaustivo del ADN visual de `OppyTec-Legacy` (3 temas `light`/`dark`/`ocean-blue`, animaciones, 42 colores, 49 íconos, gestos) y filosofía *"Mobile-First, Then Web"*.
  17. [`.agent/estrategias/estrategia_tiempo_real_websockets_y_notificaciones_001.md`](.agent/estrategias/estrategia_tiempo_real_websockets_y_notificaciones_001.md) — Tiempo Real con WebSockets (`/api/v1/ws/realtime`), Redis Pub/Sub + Streams, filtro RBAC de 3 niveles, sincronización con TanStack Query v5 y prohibición de polling HTTP.

---

## 🛠️ Stack Tecnológico

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (Async con `asyncpg`), Pydantic v2, Alembic, Redis 7.
- **Frontend:** React 19, TypeScript 5.x, Vite 6, Tailwind CSS, Radix UI, TanStack React Query v5.
- **Base de Datos:** PostgreSQL 16 con aislamiento Multi-Tenant por esquemas dinámicos y extensión `pgvector`.
- **Gobernanza Agéntica:** OpenSpec (Spec-Driven Development), **Prime Agent** (Self-Improving RLM Harness), Jev (Guardrails Sistema 1), Linters estrictos (`ruff`, `mypy`, `eslint`, `tsc`).

---

## 📋 Plan de Desarrollo

El desarrollo se ejecuta siguiendo el orden estricto de [specs/06-IMPLEMENTATION-PLAN.md](specs/06-IMPLEMENTATION-PLAN.md):
1. **Fase 1:** Setup, Andamiaje y Contenedores Docker
2. **Fase 2:** Base de Datos, Esquemas y Fixtures
3. **Fase 3:** Servicios Core y Clean Architecture
4. **Fase 4:** Endpoints API y Validaciones HTTP
5. **Fase 5:** UI, Estado Asíncrono y Componentes React
6. **Fase 6:** Pruebas Integrales, Seguridad y Auditoría
