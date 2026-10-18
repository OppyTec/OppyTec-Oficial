# Propuesta de Arquitectura Completa (Tree) — OppyTec v2.0 (Versión 001 Consolidada)

> **Documento:** `propuesta_arquitectura_tree_001.md`  
> **Versión:** 001 (Actualizada con las estrategias de Migraciones Alembic, Tenancy, Cupos por Plan, RBAC Dual y Auditoría Forense)  
> **Base Normativa:**  
> - `MASTER-AGENTIC-ENGINEERING-FRAMEWORK.md`  
> - `specs/00-INDEX.md` al `specs/06-IMPLEMENTATION-PLAN.md`  
> - `estrategia_migraciones_alembic_001.md`  
> - `estrategia_rbac_y_auditoria_001.md`  
> - `estrategia_testing_calidad_y_seguridad_001.md`  
> - `estrategia_entornos_y_despliegue_001.md`  
> - `estrategia_orquestacion_git_worktrees_y_smart_merge_001.md`  
> - `estrategia_visualizacion_y_auditoria_archify_001.md`  
> - `estrategia_openspec_negocio_vs_codigo_001.md`  
> - `estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md`  
> - `estrategia_motor_decisiones_jev_system1_001.md`  
> - `estrategia_internacionalizacion_i18n_multilenguaje_001.md`  
> - `estrategia_multimoneda_fx_precios_y_cobros_001.md`  
> - `estrategia_observabilidad_monitoreo_y_analitica_001.md`  
> - `estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md`  
> - `estrategia_respaldos_base_datos_y_recuperacion_001.md`  
> - `estrategia_escuadron_multiagente_prompts_y_autoreparacion_001.md`  
> - `estrategia_sistema_diseno_ux_ui_y_mobile_first_001.md`  
> **Propósito:** Definir el mapa estructural completo de directorios, subdirectorios y archivos críticos para la refactorización paso a paso desde `OppyTec-Legacy` hacia `OppyTec v2.0`.  
> **Fecha:** Octubre 2026  

---

## 1. Principios Rectores de la Estructura

1. **Gobernanza Agéntica + RLM Harness + Evaluación JEV, `i18n`, Multi-Moneda, Observabilidad, Cuotas R2 y Backups 4-Capas (`.agent/`, `specs/`, `docs/adr/`, `scripts/harness.py`):** Separación estricta entre reglas inmutables (`.agent/rules/00..19`), memoria auto-mejorable (`/refine`), orquestación paralela con **Prime Agent (`rlm.spawn`)** en Git Worktrees, evaluación obligatoria *"¿Esto lo puede hacer JEV (Sí/No)?"*, internacionalización `i18n` + Multi-Moneda FX + Observabilidad 4-Pilares + Almacenamiento R2 con cuotas + Respaldos en 4 Capas cifrados por Tenant, y sincronización entre **OpenSpec Bipartito (`business-domain/` vs `engineering-code/`)**, **`Graphify`** y **`Archify`**.
2. **Clean Architecture Pragmática (Backend) y Feature-Driven Architecture (Frontend):** El dominio de negocio nunca importa de FastAPI, SQLAlchemy ni React; los *linters* de arquitectura (`pytest-archon` / `import-linter` y `dependency-cruiser`) lo imponen mecánicamente con código de salida determinista.
3. **Aislamiento Multi-Tenant Determinista y Migraciones Correlativas Lineales (`0001..NNNN`):**
   - Separación explícita entre el esquema global (`public`: Trabajadores Globales de OppyTec, Holdings, Entidades Legales 1:1 con Tenant, Tenants, Planes, Catálogo de Módulos, Identidad de Clientes a nivel Holding y Acceso Transversal Multi-Tenant) y los esquemas por sucursal (`tenant_*`: RBAC del local, Catálogo, Inventario, Recetas/Escandallos, Mermas, Compras, Buffet, POS, RAG, Auditoría del local).
   - Nomenclatura correlativa estricta `NNNN_<public|tenant>_<slug>.py` sin hashes aleatorios ni `merge_heads`, protegida por `scripts/db_migration.py` (`new`, `rebase`, `verify`) y `test_alembic_integrity.py`.
4. **RBAC Dual de 3 Niveles (`<modulo>.<submodulo>.<funcion>`), Cupos por Plan con Soft-Delete y Auditoría Forense:**
   - Intersección obligatoria entre **Módulos Contratados en el Plan** $\cap$ **Permisos del Rol / Temporales (JIT)** $\setminus$ **Restricciones Explícitas (`DENY`)**.
   - Delegación jerárquica controlada (`hierarchy_rank`), cupos de trabajadores editables por plan (`max_active_users`) donde el `soft-delete` libera inmediatamente el cupo y corta sesiones en Redis, y doble libro de auditoría inmutable (*Append-Only*).
5. **Co-Creación 1:1 de Pruebas, Gates Estratificados y Seguridad Ofensiva (Red Team):**
   - Ningún código nace sin su par de pruebas (`test_module_test_parity.py`), con ejecución estratificada en **Fast Gate (`< 15s`)**, **Main Gate (`< 3m`)** y **Deep Gate**, más 11 vectores de seguridad y resiliencia (`tests/security_redteam/test_01..11`).
6. **Arquitectura de 5 Entornos, Cero Hardcoding e Invarianza de Artefactos (`SHA-256`):**
   - Promoción inmutable (`local`, `preview`/`worktree`, `ci`, `staging`, `production`), configuración *Fail-Fast* con `SecretStr` en `src/core/config.py`, inyección runtime (`runtime-env.js`) en Frontend y *Sinkhole* de salida en entornos no productivos.
7. **Inviolabilidad de Legacy:** `OppyTec-Legacy/` permanece como referencia estática de solo lectura (apoyada por sus grafos AST en `grafos-legacy/`) hasta completar las 6 fases de validación.

---

## 2. Árbol Completo de Arquitectura (`OppyTec-Code2`)

```plaintext
OppyTec-Code2/
├── AGENTS.md                                           # ★ Punto de entrada cognitivo para cualquier Agente (router de contexto)
├── MASTER-AGENTIC-ENGINEERING-FRAMEWORK.md             # ★ Constitución de ingeniería agéntica, RLM y Quality Gates
├── propuesta_arquitectura_tree_001.md                  # ★ Mapa maestro de la arquitectura objetivo v2.0 (este archivo)
├── estrategia_migraciones_alembic_001.md               # ★ Estrategia de migraciones correlativas, schemas y Bootstrap Génesis
├── estrategia_rbac_y_auditoria_001.md                  # ★ Estrategia de RBAC Dual 3-niveles, cupos por plan, JIT y auditoría
├── estrategia_testing_calidad_y_seguridad_001.md       # ★ Estrategia Co-Creación 1:1 de Tests, 5 Dimensiones, Semgrep, Trivy y Red Team
├── estrategia_entornos_y_despliegue_001.md             # ★ Estrategia de 5 Entornos (local, preview/worktree, ci, staging, prod) e ISO 27001
├── estrategia_orquestacion_git_worktrees_y_smart_merge_001.md # ★ Estrategia Prime Agent RLM, Git Worktrees, AST Claiming y Smart Merge Train
├── estrategia_visualizacion_y_auditoria_archify_001.md # ★ Estrategia del Atlas Visual Interactivo HTML (Archify + Graphify) para auditoría humana
├── estrategia_openspec_negocio_vs_codigo_001.md        # ★ Estrategia OpenSpec Bipartito (Negocio vs Código) preparado para futuro RAG Dual
├── estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md # ★ Estrategia OppyFy (IA), RBAC Propio Editable, Créditos Acumulables y FinOps llm_request_log
├── estrategia_motor_decisiones_jev_system1_001.md      # ★ Estrategia JEV (Sistema 1): Regla "¿Lo puede hacer JEV: Sí/No?", Enrutador y Telemetría
├── estrategia_internacionalizacion_i18n_multilenguaje_001.md # ★ Estrategia i18n Full-Stack (ES/EN + futuros), Traducción Dinámica de Datos Cliente y Patrón Pi
├── estrategia_multimoneda_fx_precios_y_cobros_001.md   # ★ Estrategia Multi-Moneda (BCCh + BCE), Selector Independiente, Consola FX Admin y Precios
├── estrategia_observabilidad_monitoreo_y_analitica_001.md # ★ Estrategia Observabilidad 4-Pilares (OpenTelemetry, Grafana LGTM, Sentry/GlitchTip y Umami)
├── estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md  # ★ Estrategia Imágenes R2: Aislamiento Tenant/Env, Compresión WebP 2-capas y Cuota MB por Plan
├── estrategia_respaldos_base_datos_y_recuperacion_001.md  # ★ Estrategia Backups 4-Capas (Neon PITR, R2 Cifrado, VPS Secundario y Local) + Restore por Tenant
├── estrategia_escuadron_multiagente_prompts_y_autoreparacion_001.md # ★ Estrategia de los 12 Agentes Especializados (Cobertura 100% de las estrategias + Autoreparación)
├── estrategia_sistema_diseno_ux_ui_y_mobile_first_001.md   # ★ Estrategia UI/UX: Rescate del ADN Visual de Legacy (3 temas, animaciones, 42 colores) y Mobile-First
├── README.md                                           # Visión general del monorepo y comandos rápidos
├── docker-compose.yml                                  # ★ Orquestación local + `--profile observability` (grafana/otel-lgtm, glitchtip, umami)
├── Makefile                                            # ★ Comandos deterministas (make check, make smart-merge, make migration-rebase)
├── scripts/
│   └── harness.py                                      # ★ Orquestador Multi-Agente RLM, Git Worktrees, AST Claims y Merge Train
├── .pre-commit-config.yaml                             # Hooks deterministas (gitleaks, ruff, mypy, eslint, tsc)
├── .graphifyignore                                     # ★ Excluye node_modules, .venv, dist, tinymce, *.sql, .worktrees y Legacy del grafo v2
├── .gitignore
│
├── .agent/                                             # 🧠 CAPA DE GOBERNANZA AGÉNTICA Y CONTINUAL HARNESS (Prime Agent + Jev)
│   ├── rules/                                          # [INMUTABLE - Solo lectura para agentes]
│   │   ├── 00-meta-agent-instructions.md               # ★ Protocolo RLM, prohibición de tocar OppyTec-Legacy, flujo en 4 fases
│   │   ├── 01-architecture-boundaries.md               # ★ Reglas de capas (Domain -> Application -> Infrastructure -> Presentation)
│   │   ├── 02-backend-standards.md                     # Python 3.12, FastAPI, SQLAlchemy 2 Async, Pydantic v2, Zero-Any
│   │   ├── 03-frontend-standards.md                    # React 19, TS Strict, TanStack Query v5, RHF + Zod, Design System
│   │   ├── 04-security-guardrails.md                   # ★ Magic Bytes, SET LOCAL search_path, sanitización XSS, Rate Limiting
│   │   ├── 05-testing-and-dod.md                       # Cobertura >= 85%, Co-Creación 1:1, criterios de cierre de fase
│   │   ├── 06-alembic-and-schema-governance.md         # ★ Regla de migraciones correlativas NNNN_<public|tenant>, cero merge_heads
│   │   ├── 07-rbac-least-privilege-and-audit.md        # ★ Regla de RBAC 3 niveles (mod.sub.fn), cupos soft-delete y auditoría
│   │   ├── 08-offensive-security-and-qa-gates.md       # ★ Regla de Red Team (Kali vectors), Semgrep, Trivy, pip-audit, Schemathesis y Knip
│   │   ├── 09-environments-and-deployment-governance.md# ★ Regla de 5 entornos, Fail-Fast, Sinkhole de salida e invarianza SHA-256
│   │   ├── 10-git-worktrees-and-smart-merge.md         # ★ Regla de Git Worktrees, AST Claiming, Merge Train y Agente Árbitro 4-Vías
│   │   ├── 11-visual-architecture-and-archify-atlas.md # ★ Regla de generación del Atlas Interactivo Archify alimentado desde Graphify
│   │   ├── 12-openspec-bipartition-and-sync.md         # ★ Regla de actualización simultánea de OpenSpec (Negocio + Código), Graphify y Archify
│   │   ├── 13-oppyfy-ai-governance-and-telemetry.md    # ★ Regla de OppyFy: 0% fuga de código, RBAC propio editable, créditos y llm_request_logs
│   │   ├── 14-jev-system1-mandatory-gate.md            # ★ Regla autónoma: evaluar siempre "¿Lo puede hacer JEV (Sí/No)?" e integrarlo si es Sí
│   │   ├── 15-i18n-multilanguage-and-dynamic-translation.md # ★ Regla i18n: 0 strings quemados, JSON es/en en paridad 1:1 y traducción dinámica de datos cliente
│   │   ├── 16-multi-currency-fx-and-pricing-governance.md # ★ Regla Multi-Moneda: Decimal estricto, <CurrencySelector />, insignia FX y Bancos Centrales
│   │   ├── 17-observability-opentelemetry-sentry-and-umami.md # ★ Regla Observabilidad: X-Trace-ID, contexto Tenant, filtro PII y 4 pilares por entorno
│   │   ├── 18-media-storage-r2-and-quota-governance.md # ★ Regla Imágenes R2: llaves {env}/{holding}/{tenant}/, WebP thumb+display, 0 huérfanos y cuota MB
│   │   ├── 19-database-backups-and-disaster-recovery.md # ★ Regla Backups 4-Capas: cifrado zstd+age, dump quirúrgico por tenant_* y snapshot pre-Alembic
│   │   ├── 20-multiagent-squad-and-self-healing-loops.md # ★ Regla del Escuadrón de 12 Agentes: paridad matemática Legacy, autoreparación QA y veto de Seguridad
│   │   └── 21-design-system-legacy-dna-and-mobile-first.md # ★ Regla UI/UX: Rescate visual de Legacy (light/dark/ocean-blue, glass, blink-*) y Mobile-First
│   ├── skills/                                         # [PAQUETES PYTHON EJECUTABLES EN REPL + CRUD VÍA /refine]
│   │   ├── git_smart_merge/                            # ★ Skill ejecutable (Prime Agent REPL + CLI humano) para Worktrees y Smart Merge
│   │   │   ├── SKILL.md
│   │   │   ├── __init__.py
│   │   │   ├── worktree_manager.py
│   │   │   ├── ast_claimer.py
│   │   │   ├── merge_train.py
│   │   │   └── conflict_arbiter.py
│   │   ├── jev-decision-engine/                        # ★ Skill ejecutable para integrar JEV (Boolean, Choice, Score + confianza) en cualquier módulo
│   │   │   ├── SKILL.md
│   │   │   ├── __init__.py
│   │   │   └── contracts.py
│   │   ├── i18n_manager/                               # ★ Skill ejecutable con lock atómico (fcntl.flock) para actualizar JSONs de idiomas en paridad
│   │   │   ├── SKILL.md
│   │   │   ├── __init__.py
│   │   │   └── i18n_tool.py
│   │   ├── fx_currency_manager/                        # ★ Skill para conversión multi-moneda (BCCh/BCE), override manual y formateo reactivo
│   │   │   └── SKILL.md
│   │   ├── observability_telemetry/                    # ★ Skill para OpenTelemetry spans, Grafana dashboards, Sentry/GlitchTip y eventos Umami
│   │   │   └── SKILL.md
│   │   ├── r2_media_storage/                           # ★ Skill para subida R2 aislada por Tenant/Env, compresión WebP y control de cuota MB
│   │   │   └── SKILL.md
│   │   ├── db_backup_recovery/                         # ★ Skill para respaldos 4-capas, restauración quirúrgica de 1 Tenant y simulacros DRP
│   │   │   └── SKILL.md
│   │   ├── ui_ux_design_system/                        # ★ Skill con el ADN visual de Legacy (3 temas, 42 colores, 49 íconos, animaciones) y Mobile-First
│   │   │   └── SKILL.md
│   │   ├── alembic-migration-manager/                  # ★ Skill para crear, renumerar (rebase) y verificar migraciones correlativas
│   │   │   └── SKILL.md
│   │   ├── rbac-permission-guard/                      # ★ Skill para registrar permisos de 3 niveles y auditar cobertura en rutas
│   │   │   └── SKILL.md
│   │   ├── security-audit/                             # Reglas de Semgrep / OWASP / Gitleaks / cloudflare security-audit-skill
│   │   ├── graphify/                                   # ★ Skill ejecutable en REPL (LegacyGraph read-only + V2Graph live) para ahorrar tokens
│   │   │   ├── SKILL.md
│   │   │   ├── __init__.py
│   │   │   └── graph_navigator.py                      # Consultas de vecinos 1-hop/2-hop, análisis de impacto y TIA sin volcar JSON crudo
│   │   ├── archify/                                    # ★ Skill de visualización interactiva HTML (tt-a1i/archify) para el Atlas de Auditoría
│   │   │   └── SKILL.md
│   │   ├── openspec-sync/                              # ★ Skill para redactar y validar specs bipartitos (business-domain vs engineering-code)
│   │   │   └── SKILL.md
│   │   └── learned-patterns/                           # Patrones destilados tras superar Quality Gates y resoluciones de Merge
│   ├── evals/                                          # 🔒 [INMUTABLE / SOLO LECTURA ANTI-TRAMPA - Verificado por SHA-256 en harness.py]
│   │   ├── rubric_10_criteria.yaml                     # ★ Los 10 criterios deterministas de aceptación (los agentes los corren pero NO pueden editarlos)
│   │   └── eval_hashes.sha256                          # ★ Hashes de integridad de evals y tests/architecture/ para impedir Reward Hacking
│   ├── subagents/                                      # [LAS 12 CARPETAS DE SUB-AGENTES CON AUTO-MEJORA: prompt.md + knowledge.md + handovers/]
│   │   ├── 01-orchestrator-pm/                         # ★ Agente 01 (Argon): Orquestador PM, DAG, Git Worktrees y reservas AST
│   │   │   ├── prompt.md
│   │   │   ├── knowledge.md
│   │   │   └── handovers/latest_handover.md
│   │   ├── 02-software-architect/                      # ★ Agente 02 (Argon): Arquitecto DDD, Clean Arch, paridad Legacy y gate JEV (`prompt.md`, `knowledge.md`, `handovers/`)
│   │   ├── 03-database-alembic-and-backup-engineer/    # ★ Agente 03 (Flash): Esquemas public/tenant_*, Alembic 0001..N y Backups 4-Capas (`prompt.md`, `knowledge.md`, `handovers/`)
│   │   ├── 04-backend-senior-dev/                      # ★ Agente 04 (Flash/Argon): FastAPI, SQLAlchemy Async, RBAC 3-niveles y R2 Quotas (`prompt.md`, `knowledge.md`, `handovers/`)
│   │   ├── 05-frontend-senior-dev/                     # ★ Agente 05 (Flash): React 19, ADN Visual Legacy (3 temas), Mobile-First y <Can> (`prompt.md`, `knowledge.md`, `handovers/`)
│   │   ├── 06-ai-oppyfy-and-jev-engineer/              # ★ Agente 06 (Flash/Argon): OppyFy RAG 3-Capas, RBAC propio, Créditos y JEV Sistema 1 (`prompt.md`, `knowledge.md`, `handovers/`)
│   │   ├── 07-i18n-and-fx-currency-specialist/         # ★ Agente 07 (Flash): i18n estático/dinámico ("Pollo King"), banderas SVG y FX BCCh/BCE (`prompt.md`, `knowledge.md`, `handovers/`)
│   │   ├── 08-environments-and-observability-engineer/ # ★ Agente 08 (Flash): 5 Entornos, SHA-256 y Observabilidad 4-Pilares (`prompt.md`, `knowledge.md`, `handovers/`)
│   │   ├── 09-qa-parity-and-test-engineer/             # ★ Agente 09 (Argon/Flash): Co-Creación 1:1, paridad matemática Legacy y bucle de autoreparación (`prompt.md`, `knowledge.md`, `handovers/`)
│   │   ├── 10-cybersecurity-redteam-auditor/           # ★ Agente 10 (Argon): 11 vectores Red Team, autoparcheo autónomo y poder de veto final (`prompt.md`, `knowledge.md`, `handovers/`)
│   │   ├── 11-git-worktree-merge-arbiter/              # ★ Agente 11 (Argon): Merge Train (rebase + --ff-only) y Árbitro Fresco de 4 vías (`prompt.md`, `knowledge.md`, `handovers/`)
│   │   └── 12-tech-writer-openspec-archify/            # ★ Agente 12 (Flash): Bóvedas OpenSpec (Negocio/Código), Graphify y Atlas HTML Archify (`prompt.md`, `knowledge.md`, `handovers/`)
│   ├── guardrails/
│   │   └── jev_policies.yaml                           # ★ Políticas Sistema 1 (Jev) para validar tool-calls antes de mutar disco
│   └── memory/                                         # [ESTADO PERSISTENTE DEL HARNESS Y EVENT LOG]
│       ├── current_state.md                            # ★ Checklist vivo de en qué Fase/Sub-etapa estamos exactamente
│       ├── trajectory_lessons.md                       # Bitácora de errores corregidos y patrones de merge destilados con /refine
│       ├── claims_registry.json                        # ★ Registro activo de reservas de archivos/nodos AST por cada worktree
│       └── harness_events.jsonl                        # ★ Bitácora Event-Sourced inmutable (timestamp + Git SHA) para reconstruir estado
│
├── specs/                                              # 📋 FUENTE DE VERDAD BIPARTITA (OpenSpec - Spec-Driven Development & RAG-Ready)
│   ├── openspec.config.yaml                            # ★ Configuración unificada del monorepo (fin de la duplicación Backend/Frontend)
│   ├── 00-INDEX.md                                     # Índice maestro y glosario ubicuo (Holding, Tenant, Bodega, Escandallo)
│   ├── 01-PRD.md                                       # Casos de uso, roles y reglas de negocio
│   ├── 02-TRD.md                                       # Stack cerrado, NFRs (P95 <= 120ms) y variables de entorno
│   ├── 03-USER-FLOWS.md                                # Mapa de rutas y estados UI
│   ├── 04-DESIGN-SYSTEM.md                             # Tokens visuales, componentes base y accesibilidad
│   ├── 05-DATABASE-SCHEMA.md                           # ★ Contratos de tablas: esquema `public` vs esquema `tenant_*`
│   ├── 06-IMPLEMENTATION-PLAN.md                       # ★ Hoja de ruta secuencial de las 6 Fases y sus Checklists
│   ├── business-domain/                                # 🟢 BÓVEDA 1: "CÓMO FUNCIONA EL NEGOCIO Y CÓMO USAR OPPYTEC" (Futuro RAG Clientes)
│   │   ├── tenancy-and-plans.business.spec.md          # (0% SQL / 0% rutas de código: 100% seguro para usuarios finales)
│   │   ├── rbac-quotas-and-audit.business.spec.md      # Roles, permisos de 3 niveles, cupos por plan, baja de personal y auditoría
│   │   ├── catalog-and-units.business.spec.md          # Productos, Familias vs Categorías vs Etiquetas, 3 capas de unidades
│   │   ├── inventory-and-kardex.business.spec.md       # Bodegas, Áreas Operativas, Kardex, Conteos físicos y FEFO
│   │   ├── waste-and-mermas.business.spec.md           # Registro de mermas, umbrales de aprobación e impacto en Food Cost
│   │   ├── recipes-and-combos.business.spec.md         # Escandallos, sub-recetas, combos y grupos de opciones
│   │   ├── purchases-and-invoices.business.spec.md     # Pedidos a proveedores, presupuestos, recepción y facturas con IA
│   │   ├── operations-and-buffet.business.spec.md      # Consumo, Ventas POS, Buffet, Eventos, Salones, Turnos y Notas
│   │   ├── analytics-and-reports.business.spec.md      # Paneles ejecutivos, visión financiera y proyecciones
│   │   ├── oppy-ai-and-voice.business.spec.md          # Uso de OppyFy, documentos del local y comandos Manos Libres / Alexa
│   │   ├── multi-currency-and-pricing.business.spec.md # Selector de moneda (CLP/USD/EUR/BRL), tasas de Banco Central y simulador de precios
│   │   ├── media-storage-and-quotas.business.spec.md   # Gestión de imágenes de catálogo, cuota de memoria (MB/GB) por plan y liberación de espacio
│   │   └── data-security-and-backups.business.spec.md  # Garantías de protección de datos, continuidad operativa y recuperación por sucursal
│   └── engineering-code/                               # 🔵 BÓVEDA 2: "CÓMO FUNCIONA EL CÓDIGO Y ARQUITECTURA" (Futuro RAG Desarrolladores)
│       ├── tenancy-rbac-and-migrations.code.spec.md    # ★ Espejo técnico: Bootstrap Génesis, Holding-LegalEntity-Tenant y Alembic
│       ├── rbac-quotas-and-audit.code.spec.md          # ★ Espejo técnico: Motor RBAC 3-niveles, acceso transversal, cupos y auditoría
│       ├── catalog-and-units.code.spec.md              # ★ Espejo técnico: Modelos, conversión Decimal 3-capas e importador Excel
│       ├── inventory-and-kardex.code.spec.md           # ★ Espejo técnico: Transacciones Kardex, locks canónicos y conteos
│       ├── waste-and-mermas.code.spec.md               # ★ Espejo técnico: Flujo de aprobación, umbrales y KPIs de mermas
│       ├── recipes-and-combos.code.spec.md             # ★ Espejo técnico: Cálculo recursivo de costos y deducción de ingredientes
│       ├── purchases-and-invoices.code.spec.md         # ★ Espejo técnico: Órdenes de compra, Magic Bytes y OCR/IA de facturas
│       ├── operations-and-buffet.code.spec.md          # ★ Espejo técnico: Ventas, Buffet, Eventos, Turnos y WebSockets
│       ├── analytics-and-reports.code.spec.md          # ★ Espejo técnico: Consultas agregadas ($P_{95} \le 800\text{ ms}$) y reportes
│       ├── oppy-ai-and-voice.code.spec.md              # ★ Espejo técnico: Orquestador RAG (`pgvector`), audio TTS/STT y guardrails LLM
│       ├── multi-currency-and-pricing.code.spec.md     # ★ Espejo técnico: Motor FX (BCCh/BCE), circuit breaker > 8%, historial y triangulación Decimal
│       ├── media-storage-and-quotas.code.spec.md       # ★ Espejo técnico: Llaves R2 `{env}/{holding}/{tenant}/`, WebP dual, deduplicación SHA-256 y cuotas
│       ├── data-security-and-backups.code.spec.md      # ★ Espejo técnico: Backups 4-Capas (`zstd` + `age`), restore quirúrgico por `tenant_*` y drills
│       └── multi-agent-git-harness.code.spec.md        # ★ Contrato interno de ingeniería: Git Worktrees, AST Claiming y Merge Train
│
├── docs/                                               # 🏛️ MEMORIA ARQUITECTÓNICA Y TOPOLOGÍA
│   ├── adr/                                            # Architecture Decision Records (Inmutables una vez aprobados)
│   │   ├── ADR-001-clean-architecture-modular-monolith.md
│   │   ├── ADR-002-multi-tenant-postgres-schema-isolation.md
│   │   ├── ADR-003-async-sqlalchemy-and-search-path.md
│   │   ├── ADR-004-three-layer-units-and-weighted-costing.md
│   │   ├── ADR-005-linear-correlative-alembic-migrations.md
│   │   ├── ADR-006-dual-hierarchical-rbac-and-forensic-audit.md
│   │   ├── ADR-007-co-creation-testing-and-offensive-security-gates.md
│   │   ├── ADR-008-five-tier-environments-and-artifact-invariance.md
│   │   ├── ADR-009-prime-agent-rlm-worktrees-and-smart-merge.md
│   │   ├── ADR-010-interactive-architecture-atlas-with-archify.md
│   │   ├── ADR-011-bipartite-openspec-business-vs-code-rag-ready.md
│   │   ├── ADR-012-oppyfy-dual-rag-custom-rbac-and-credit-ledger.md
│   │   ├── ADR-013-jev-system1-global-decision-and-routing-engine.md
│   │   ├── ADR-014-fullstack-i18n-dynamic-data-translation-and-pi-minimalism.md
│   │   ├── ADR-015-central-bank-fx-engine-and-multi-currency-pricing.md
│   │   ├── ADR-016-four-pillar-observability-otel-grafana-sentry-umami.md
│   │   ├── ADR-017-multi-tenant-r2-media-storage-webp-and-plan-quotas.md
│   │   ├── ADR-018-four-layer-encrypted-backups-and-per-tenant-restore.md
│   │   ├── ADR-019-twelve-agent-squad-model-tiering-and-self-healing.md
│   │   └── ADR-020-legacy-visual-dna-three-themes-and-mobile-first.md
│   └── architecture/
│       ├── atlas/                                      # ★ ATLAS VISUAL INTERACTIVO (Archify HTML autocontenidos + fuentes JSON tipadas)
│       │   ├── sources/                                # Fuentes JSON tipadas y recibos de validación (*.archify.json / *.receipt.json)
│       │   ├── 01-tenancy-and-schemas.archify.html     # Mapa 1: Esquema `public` vs `tenant_*`, Holdings, LegalEntity (1:1) y Alembic
│       │   ├── 02-rbac-quotas-and-audit.archify.html   # Mapa 2: RBAC Dual 3-niveles, cupos por plan, soft-delete, JIT y Auditoría
│       │   ├── 03-clean-architecture-and-domain.archify.html # Mapa 3: Los 10 módulos, límites de capas y motor matemático 3-capas
│       │   ├── 04-critical-runtime-flows-and-resilience.archify.html # Mapa 4: Flujos E2E, Circuit Breaker Redis y ordenamiento de locks
│       │   └── 05-environments-and-agentic-harness.archify.html      # Mapa 5: Worktrees, Merge Train y promoción en los 5 entornos
│       └── graphify/                                   # Snapshots del grafo de dependencias AST del nuevo código v2 (0 tokens)
│
├── oppytec-backend/                                    # ⚙️ BACKEND v2.0 (Python 3.12 + FastAPI + SQLAlchemy 2.0 Async)
│   ├── Dockerfile                                      # Multi-stage build (python:3.12-slim, non-root user)
│   ├── pyproject.toml                                  # ★ Configuración unificada: uv, ruff, mypy --strict, pytest, import-linter
│   ├── uv.lock
│   ├── .env.example                                    # ★ Plantilla validada contra 02-TRD.md + credenciales SuperUser Génesis
│   ├── alembic.ini
│   ├── alembic/                                        # 🗄️ MIGRACIONES CORRELATIVAS CONSCIENTES DE ESQUEMA (`public` vs `tenant`)
│   │   ├── env.py                                      # ★ Ejecutor consciente de `migration_scope`: `public` (1 vez) vs `tenant_*`
│   │   ├── script.py.mako                              # ★ Plantilla obligatoria con `migration_scope: Literal["public", "tenant"]`
│   │   └── versions/
│   │       ├── 0001_public_genesis_tenancy_modules_and_global_rbac.py
│   │       └── 0002_tenant_initial_client_rbac_and_core_modules.py
│   │
│   ├── src/
│   │   ├── main.py                                     # ★ App Factory de FastAPI, Lifespan (DB/Redis pools + Bootstrap), Middlewares
│   │   ├── core/                                       # 🔒 NÚCLEO TRANSVERSAL
│   │   │   ├── config.py                               # ★ Pydantic Settings v2 (validación estricta al arrancar)
│   │   │   ├── database.py                             # ★ AsyncEngine, `get_public_db_session` y `get_tenant_db_session`
│   │   │   ├── bootstrap.py                            # ★ Semilla idempotente Génesis: crea `oppytec.admin`, módulos y roles base
│   │   │   ├── redis.py                                # Pool asíncrono (sesiones, kill-switch de soft-delete, rate-limit, PubSub)
│   │   │   ├── security.py                             # JWT (PyJWT), Argon2/Bcrypt, OAuth2
│   │   │   ├── observability.py                        # ★ Instrumentación central: OpenTelemetry, structlog JSON, Sentry/GlitchTip y filtro PII
│   │   │   ├── exceptions.py                           # Excepciones de dominio mapeadas a respuestas RFC 7807 / HTTP 4xx con `i18n_key`
│   │   │   ├── i18n/                                   # ★ Motor i18n Backend (`Accept-Language`), Memoria Global `i18n_translation_memory`, filtro de nombres propios (`Pollo King`) y traductor estilo `Pi`
│   │   │   ├── fx/                                     # ★ Motor Cambiario Institucional (`BCCh` + `BCE Frankfurter`), Circuit Breaker > 8%, Override Manual del SuperUser e historial `fx_rate_history`
│   │   │   ├── backup/                                 # ★ Motor de Respaldos 4-Capas (`Neon PITR`, `R2 Vault Cifrado`, `VPS Secundario`, `Oficina Local`), compresión `zstd` + cifrado `age` y restore quirúrgico por Tenant
│   │   │   └── guards/                                 # Guardrails deterministas de seguridad y autorización
│   │   │       ├── rbac_dependencies.py                # ★ `RequireGlobalPermission("m.s.f")` y `RequireTenantPermission("m.s.f")`
│   │   │       ├── file_magic_guard.py                 # ★ Validación binaria Magic Bytes (PDF/WebP/PNG/XLSX)
│   │   │       ├── xss_sanitizer.py                    # Sanitización de inputs de texto y plantillas HTML
│   │   │       └── rate_limiter.py                     # Sliding Window en Redis (Auth: 5/min, API: 120/min, AI: 20/min)
│   │   │
│   │   ├── shared/                                     # Modelos base y utilidades compartidas sin acoplamiento
│   │   │   ├── models_base.py                          # ★ DeclarativeBase separada: `PublicBase` (schema="public") y `TenantBase`
│   │   │   ├── soft_delete_mixin.py                    # ★ Mixin estandarizado (`is_deleted`, `deleted_at`, `deleted_by`)
│   │   │   ├── unit_of_work.py                         # Patrón UoW para transacciones atómicas
│   │   │   └── pagination.py                           # Esquemas genéricos tipados (`PaginatedResponse[T]`)
│   │   │
│   │   ├── adapters/                                   # 🔌 PUERTOS Y ADAPTADORES DE INFRAESTRUCTURA EXTERNA (Fase 3)
│   │   │   ├── storage/
│   │   │   │   ├── protocol.py                         # Interfaz `StoragePort` (upload, delete, presigned_url, check_quota)
│   │   │   │   ├── image_optimizer.py                  # ★ Limpieza EXIF/GPS + compresión dual a `thumb.webp` (256px) y `display.webp` (1024px)
│   │   │   │   ├── r2_storage.py                       # ★ Cloudflare R2 asíncrono con prefijo `{env}/{holding_id}/{tenant_id}/`
│   │   │   │   └── local_storage.py                    # Implementación local aislada por `ENV_NAMESPACE` para desarrollo/tests
│   │   │   ├── ai/
│   │   │   │   ├── protocol.py                         # Interfaz `LLMProviderPort` & `EmbeddingPort` (Sistema 2)
│   │   │   │   ├── gemini_adapter.py                   # Cliente Google Gemini + Audio/Voice + Embeddings (Medido en `llm_request_logs`)
│   │   │   │   ├── jev_protocol.py                     # ★ Interfaz `JevDecisionPort`: `decide_boolean`, `decide_choice`, `decide_score` (Sistema 1)
│   │   │   │   └── jev_adapter.py                      # ★ Adaptador `MeteredJevAdapter` con umbrales de confianza y registro en `llm_request_logs`
│   │   │   └── email/
│   │   │       ├── protocol.py
│   │   │       ├── resend_smtp_adapter.py
│   │   │       └── sinkhole_mailpit_adapter.py         # ★ Interceptor de correos salientes para local/preview/ci/staging
│   │   │
│   │   └── modules/                                    # 📦 MÓDULOS DE NEGOCIO (Clean Architecture interna por cada módulo)
│   │       ├── identity/                               # [Dual: `public` + `tenant_*`] Usuarios, RBAC 3-Niveles, Delegación y JIT
│   │       │   ├── domain/                             # ★ `rbac_evaluator.py`: Ecuación M_Plan ∩ ((P_Rol ∪ P_Temp) \ P_Deny) y Ranks
│   │       │   ├── application/                        # ★ `delegation_service.py` (Grant Ceiling, JIT grants) y `session_killswitch.py`
│   │       │   ├── infrastructure/                     # Modelos `GlobalUser`/`GlobalRole` (`PublicBase`) y `Role`/`Grant` (`TenantBase`)
│   │       │   └── presentation/                       # `router.py` y `schemas.py`
│   │       │
│   │       ├── tenancy/                                # [Esquema `public`] Holdings, Entidad Legal (1:1), Tenants, Planes, Cupos y Módulos
│   │       │   ├── domain/                             # ★ Reglas de cardinalidad Holding->LegalEntity->Tenant, cupos de usuarios y cuotas MB R2
│   │       │   ├── application/                        # ★ `schema_provisioner.py`, `quota_service.py` (Usuarios) y `storage_quota_service.py` (Memoria Imágenes MB)
│   │       │   ├── infrastructure/                     # Modelos `Holding`, `LegalEntity`, `Tenant`, `SystemPlan`, `AppModule`, `TenantModule`
│   │       │   └── presentation/
│   │       │
│   │       ├── audit/                                  # [Dual Append-Only: `public` + `tenant_*`] Doble Libro de Auditoría Forense
│   │       │   ├── domain/                             # Entidades inmutables `RbacAuditEntry` y `ActivityAuditEntry` (`authorization_lineage`)
│   │       │   ├── application/                        # ★ `audit_service.py`: captura before/after y quién otorgó el permiso usado
│   │       │   ├── infrastructure/                     # Tablas Append-Only sin métodos de UPDATE/DELETE
│   │       │   └── presentation/                       # Endpoints de consulta forense para SuperUser (`public`) y Propietario (`tenant_*`)
│   │       │
│   │       ├── catalog/                                # [Esquema `tenant_*`] Productos, Categorías, Unidades 3-Capas, Proveedores
│   │       │   ├── domain/                             # ★ Conversión de unidades (Compra -> Almacén -> Receta) y costos
│   │       │   ├── application/                        # Importador Excel validado, gestión de etiquetas, marcas y alias
│   │       │   ├── infrastructure/
│   │       │   └── presentation/
│   │       │
│   │       ├── inventory/                              # [Esquema `tenant_*`] Bodegas, Áreas Operativas, Kardex, Conteos, Mermas
│   │       │   ├── domain/                             # ★ Cálculo atómico de stock, reglas de aprobación de mermas
│   │       │   ├── application/                        # Movimientos, transferencias entre bodegas, alertas de vencimiento
│   │       │   ├── infrastructure/
│   │       │   └── presentation/
│   │       │
│   │       ├── recipes/                                # [Esquema `tenant_*`] Escandallos, Sub-recetas, Combos, Grupos de Opciones
│   │       │   ├── domain/                             # ★ Cálculo de costo ponderado recursivo y margen gastronómico
│   │       │   ├── application/
│   │       │   ├── infrastructure/
│   │       │   └── presentation/
│   │       │
│   │       ├── procurement/                            # [Esquema `tenant_*`] Órdenes de Compra, Recepción, Facturas, Presupuestos
│   │       │   ├── domain/                             # Conciliación Orden vs Recepción vs Factura e incidencias de proveedor
│   │       │   ├── application/                        # Extracción OCR/IA de facturas e ingreso automático a stock
│   │       │   ├── infrastructure/
│   │       │   └── presentation/
│   │       │
│   │       ├── operations/                             # [Esquema `tenant_*`] Ventas/Consumo, Buffet, Eventos, Salones, Turnos, Notas
│   │       │   ├── domain/                             # Descuento atómico de insumos por venta de receta/combo
│   │       │   ├── application/
│   │       │   ├── infrastructure/
│   │       │   └── presentation/
│   │       │
│   │       ├── analytics/                              # [Esquema `tenant_*` / Holding] Reportes Ejecutivos, Financieros, Mermas
│   │       │   ├── domain/
│   │       │   ├── application/
│   │       │   ├── infrastructure/
│   │       │   └── presentation/
│   │       │
│   │       └── oppy_ai/                                # [Dual: `public` + `tenant_*`] Asistente `OppyFy` (Marca Configurable), RAG y FinOps
│   │           ├── domain/                             # ★ Evaluador RBAC propio de OppyFy (Dominios/Sub-dominios editables + JIT), Billetera Acumulable sin caducidad y Medidor de Contexto %
│   │           ├── application/                        # ★ Tool-Router Agent, Herramientas en código duro (Ventas, Stock, Eventos, Demoras, Costos) con redacción de campos y `MeteredAIService` (`llm_request_logs`)
│   │           ├── infrastructure/                     # `spec_chunks` (solo `business-domain/`), `oppyfy_domains`, `oppyfy_prompt_audit_log`, `llm_request_logs`
│   │           └── presentation/                       # Chat SSE, Canvas Artifacts, Panel RBAC OppyFy, Compra/Distribución de Créditos y 2 Vistas FinOps Admin
│   │
│   ├── scripts/
│   │   ├── db_migration.py                             # ★ CLI para migraciones correlativas: `new`, `rebase` (multi-dev), `verify` e `impact` (Graphify)
│   │   ├── backup_manager.py                           # ★ CLI de Respaldos 4-Capas: `backup-all`, `backup-tenant`, `restore-tenant`, `verify-drill` y `pull-to-local-office`
│   │   ├── seed_dev_data.py                            # ★ Seeder determinista Fase 2 (1 Holding, 1 LegalEntity, 1 Tenant, 3 Bodegas, 20 Insumos, 5 Recetas)
│   │   └── anonymize_for_staging.py                    # ★ Anonimizador determinista ISO 27001 (cero PII real ni tokens en Staging)
│   │
│   └── tests/                                          # 🧪 SUITE DETERMINISTA DE VERIFICACIÓN (5 DIMENSIONES + RED TEAM)
│       ├── conftest.py                                 # Fixtures asíncronas aisladas por transacción y tenant de prueba
│       ├── architecture/                               # ★ CAJA BLANCA: QUALITY GATES ARQUITECTÓNICOS (< 2s en cada commit/PR)
│       │   ├── test_clean_architecture.py              # Verifica que `domain/` nunca importe de `fastapi` ni `sqlalchemy`
│       │   ├── test_alembic_integrity.py               # ★ Verifica secuencia 0001..NNNN, Single-Head, migration_scope y downgrade()
│       │   ├── test_rbac_and_audit_coverage.py         # ★ Verifica que ningún endpoint carezca de RBAC 3-niveles (`mod.sub.fn`)
│       │   ├── test_module_test_parity.py              # ★ Verifica la Ley de Co-Creación 1:1 (todo módulo/servicio tiene su test)
│       │   ├── test_harness_and_merge_integrity.py     # ★ Verifica ausencia de marcas de conflicto y consistencia de claims AST
│       │   ├── test_openspec_bipartition_and_sync.py   # ★ Verifica espejo 1:1 (business vs code), cero SQL/código en business y paridad con Graphify
│       │   ├── test_oppyfy_telemetry_and_isolation.py  # ★ Verifica registro obligatorio en `llm_request_logs`, RBAC en cada tool y 0% indexación de `engineering-code/`
│       │   ├── test_jev_system1_enforcement.py         # ★ Verifica que todo módulo evalúe `can_jev_handle_it`, use `JevDecisionPort` y registre en `llm_request_logs`
│       │   ├── test_i18n_keys_parity_and_no_hardcoded_strings.py # ★ Verifica paridad 1:1 entre `locales/es/*.json` y `en/*.json`, variables `{{var}}` y 0 strings quemados
│       │   ├── test_fx_currency_precision_and_governance.py      # ★ Verifica triangulación FX con `Decimal`, circuit breaker > 8% y auditoría de overrides manuales
│       │   ├── test_observability_pii_redaction_and_spans.py     # ★ Verifica generación de `X-Trace-ID`, contexto Tenant y redacción PII al 100% en Sentry/OTel
│       │   ├── test_media_storage_isolation_and_quotas.py        # ★ Verifica aislamiento de llaves R2 por Tenant/Env, límite `max_storage_mb` y limpieza de huérfanos
│       │   ├── test_backup_encryption_and_tenant_restore.py      # ★ Verifica cifrado obligatorio `.sql.zst.age`, restore quirúrgico de 1 Tenant sin afectar a otros y checksum SHA-256
│       │   ├── test_subagent_strategy_coverage.py                # ★ Verifica que los 12 sub-agentes existan y cubran las 16 estrategias sin huérfanos
│       │   └── test_ui_design_tokens_and_mobile_first.py         # ★ Verifica los 3 temas (`light`/`dark`/`ocean-blue`), animaciones, 42 colores y reglas Mobile-First
│       ├── smoke/                                      # ★ HUMO (< 3s): Arranque FastAPI, OpenAPI, DB/Redis y Login SuperUser Génesis
│       ├── unit/                                       # ★ UNITARIAS + HYPOTHESIS (< 5s): Fórmulas Decimal, RBAC evaluator, cupos
│       ├── integration/                                # ★ INTEGRACIÓN: Aislamiento multi-tenant, soft-delete + Redis kill-switch
│       ├── security_redteam/                           # ★ SEGURIDAD OFENSIVA (Vectores Kali Linux + ISO 27001 + OWASP):
│       │   ├── test_01_cross_tenant_and_holding_isolation_idor.py
│       │   ├── test_02_jwt_cryptographic_and_session_attacks.py
│       │   ├── test_03_rbac_privilege_escalation_and_delegation.py
│       │   ├── test_04_polyglot_injections_sqli_xss_ssti_lfi.py
│       │   ├── test_05_malicious_file_uploads_and_excel_exploits.py
│       │   ├── test_06_concurrency_race_conditions_double_spend.py
│       │   ├── test_07_information_disclosure_and_headers.py
│       │   ├── test_08_ai_prompt_injection_and_rag_isolation.py
│       │   ├── test_09_zero_hardcoding_and_secrets_guard.py # ★ AST: Cero hardcoding, SecretStr obligatorio y solo lectura desde .env/Secret Manager
│       │   ├── test_10_resilience_chaos_and_circuit_breakers.py # ★ CAOS: Fallback si cae Redis, RESET search_path en pool y Circuit Breakers
│       │   └── test_11_environment_boundary_and_failfast.py     # ★ ENTORNOS: Bloqueo cross-environment, entropía de claves y OpenAPI oculto en Prod
│       ├── contracts/
│       │   └── test_openapi_schemathesis.py            # ★ CAJA GRIS: Fuzzing automático contra `/openapi.json` multi-rol
│       ├── e2e/                                        # ★ SISTEMA (E2E): Flujos críticos de negocio de punta a punta
│       ├── uat/                                        # ★ ACEPTACIÓN (UAT): Escenarios validados contra el PRD
│       └── load/
│           └── locustfile.py                           # ★ RENDIMIENTO Y ESTRÉS: 500 RPS y validación P95 <= 120ms
│
├── oppytec-frontend/                                   # 💻 FRONTEND v2.0 (React 19 + TypeScript 5 + Vite 6 + TanStack Query v5)
│   ├── Dockerfile                                      # Multi-stage build inmutable (Build Once, Deploy Everywhere SHA-256)
│   ├── docker-entrypoint.sh                            # ★ Genera `/runtime-env.js` al arrancar el contenedor según el entorno
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json                                   # ★ Strict mode: `noImplicitAny: true`, `strictNullChecks: true`
│   ├── vite.config.ts
│   ├── tailwind.config.ts                              # Tokens alineados con `specs/04-DESIGN-SYSTEM.md`
│   ├── eslint.config.js
│   ├── knip.json                                       # ★ Detector de código, tipos, exports y dependencias muertas (`pnpm dlx knip`)
│   ├── .dependency-cruiser.cjs                         # ★ Linter de arquitectura Frontend (evita imports circulares entre features)
│   ├── .env.example
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── app/                                        # Bootstrap global, Providers (QueryClient, Auth, Tenant, Bodega, Theme)
│       │   ├── router.tsx                              # ★ Árbol de rutas con Lazy Loading y guardia RBAC de Módulo/Sub-Módulo
│       │   └── providers.tsx
│       ├── shared/                                     # 🧱 SISTEMA DE DISEÑO, SEGURIDAD UI, i18n Y UTILIDADES COMPARTIDAS
│       │   ├── config/
│       │   │   └── env.ts                              # ★ Validación Zod de `import.meta.env.VITE_*` (Cero hardcoding de URLs/Keys)
│       │   ├── i18n/                                   # ★ MOTOR MULTILENGUAJE (`es` 🇪🇸, `en` 🇺🇸 + preparado para `pt`, `fr`, `it`, `de`)
│       │   │   ├── config.ts                           # Inicialización `react-i18next` y sincronización con `Accept-Language`
│       │   │   ├── i18next.d.ts                        # Tipado estricto TypeScript para llaves `t("namespace:key")`
│       │   │   ├── flags/                              # Banderas SVG vectoriales nítidas (`FlagUS.tsx`, `FlagES.tsx`...)
│       │   │   └── locales/                            # 11 archivos JSON por carpeta de idioma (`es/*.json` <-> `en/*.json`)
│       │   ├── currency/                               # ★ MOTOR MULTI-MONEDA (`CLP`, `USD`, `EUR`, `BRL`, `UF` independientes del idioma)
│       │   │   ├── CurrencyContext.tsx                 # Estado de moneda activa, tasa oficial del Banco Central y moneda base del Tenant
│       │   │   ├── CurrencySelector.tsx                # Selector de moneda en Navbar junto al selector de bandera de idioma
│       │   │   ├── MoneyBadge.tsx                      # Insignia visible que informa en qué moneda y tasa están expresados los valores
│       │   │   └── useCurrencyFormatter.ts             # Formateador reactivo de montos con precisión Decimal
│       │   ├── telemetry/                              # ★ TELEMETRÍA Y ANALÍTICA FRONTEND (`OpenTelemetry`, `Sentry/GlitchTip` y `Umami`)
│       │   │   ├── otel.ts                             # Propaga cabecera W3C `traceparent` hacia FastAPI
│       │   │   ├── sentry.ts                           # Conecta `ErrorBoundary` con filtro PII y `X-Trace-ID`
│       │   │   └── umami.ts                            # Analítica de producto sin cookies inyectada vía `/runtime-env.js`
│       │   ├── api/
│       │   │   ├── httpClient.ts                       # ★ Cliente Axios con interceptor de JWT, `X-Tenant-ID` y silent refresh
│       │   │   └── queryKeys.ts                        # ★ Fábrica centralizada de claves de TanStack Query (`['stock', tenantId, bodegaId]`)
│       │   ├── auth/                                   # ★ MOTOR RBAC EN FRONTEND (Sincronizado con el Tenant activo del Holding)
│       │   │   ├── Can.tsx                             # Componente `<Can perform="modulo.submodulo.funcion">` para ocultar vistas/botones
│       │   │   └── usePermissions.ts                   # Hook para evaluar acceso a Módulos, Sub-módulos y Funciones en tiempo real
│       │   ├── components/
│       │   │   ├── ui/                                 # Primitivas Radix UI + Tailwind (Button, Dialog, Skeleton, DataTable...)
│       │   │   ├── feedback/                           # ★ Estados canónicos: `PageSkeleton`, `EmptyState`, `ErrorBoundary`, Sonner
│       │   │   └── layout/                             # `AppLayout`, `Sidebar`, `Navbar`, `LanguageFlagSelector`, `CurrencySelector`, `HoldingTenantSwitcher`, `BodegaSelector`
│       │   ├── hooks/                                  # Hooks transversales (`useDebounce`, `useBarcodeScanner`, `useWebSocket`)
│       │   └── lib/                                    # Formateadores de moneda/unidades, zonas horarias y validadores Zod base
│       │
│       └── features/                                   # 🧩 MÓDULOS FUNCIONALES (Espejo de dominios del Backend)
│           ├── auth/                                   # Login, OAuth, Conmutador de Tenants del Holding, ImpersonationBanner
│           ├── rbac-and-audit/                         # ★ Gestión de Roles, Matriz 3-Niveles, Permisos Temporales (JIT), Cupos del Plan y Visor de Auditoría Forense
│           ├── catalog/                                # Productos, Categorías, Importador Excel, Unidades de medida
│           ├── inventory/                              # Registro de Stock, Recuento/Auditoría Física, Mermas, Transferencias
│           ├── recipes/                                # Escandallos, Calculadora de Costos, Combos y Grupos de Opciones
│           ├── procurement/                            # Compras, Proveedores, Subida y validación de Facturas
│           ├── operations/                             # Consumo/Ventas, Buffet, Eventos, Turnos, Actividades/Notas
│           ├── analytics/                              # HomeDashboard, Informes Ejecutivos, Proyecciones y Alertas
│           ├── oppyfy/                                 # ★ Workspace de `OppyFy` (Marca Configurable), Medidor de Contexto %, Canvas (Tablas/Gráficos), Panel RBAC Editable de Dominios/Sub-dominios, Billetera de Créditos y Auditoría de Prompts
│           └── platform-admin/                         # ★ Panel Global OppyTec (`public`): Holdings, Entidades Legales, Tenants, Planes (`max_active_users`), Módulos, Staff, Consola FX de Monedas, las 2 Vistas FinOps IA (`llm_request_logs`) y el Centro de Observabilidad (13 sub-vistas de OTel, Grafana, Sentry y Umami con filtro por Environment)
│
└── OppyTec-Legacy/                                     # 🏛️ REFERENCIA DE SOLO LECTURA (Congelado - Inviolable según `00-INDEX.md`)
    ├── OppyTec_Backend/                                # Código fuente original para consulta de reglas de negocio y fórmulas
    ├── OppyTec_Frontend/                               # UI original para consulta de flujos y componentes
    └── grafos-legacy/                                  # ★ Grafos AST pre-generados para consultar impacto sin leer todo Legacy
```

---

## 3. Archivos Críticos a Tener en Cuenta (Por Capa y Fase)

### 3.1 Capa de Gobernanza Agéntica y Especificación (El "Cerebro")
| Archivo | Rol Crítico en la Refactorización |
|---|---|
| **`.agent/rules/00..19-*.md`** | Leyes inmutables que todo agente lee antes de actuar. Prohiben modificar `OppyTec-Legacy`, obligan a usar tipado estricto (`Zero-Any`), migraciones correlativas (`Regla 06`), RBAC de 3 niveles (`Regla 07`), Co-Creación 1:1 + Red Team (`Regla 08`), aislamiento de los 5 entornos (`Regla 09`), orquestación en Git Worktrees + Smart Merge (`Regla 10`), Atlas Visual con Archify (`Regla 11`), sincronización bipartita de OpenSpec (`Regla 12`), gobernanza de `OppyFy` (`Regla 13`), evaluación obligatoria de `JEV Sistema 1` (`Regla 14`), internacionalización `i18n` Full-Stack (`Regla 15`), gobernanza Multi-Moneda FX (`Regla 16`), Observabilidad 4-Pilares (`Regla 17`), Almacenamiento R2 con Cuota (`Regla 18`) y Respaldos en 4 Capas (`Regla 19`). |
| **`estrategia_*_001.md` (13 documentos maestros)** | Especifican el diseño detallado de Migraciones Alembic, RBAC Dual + Cupos + Auditoría Forense, Testing en 5 Dimensiones + Red Team, Cadena de 5 Entornos DevSecOps, Orquestación RLM con Prime Agent + Smart Merge, Atlas Visual con Archify, OpenSpec Bipartito, el ecosistema `OppyFy`, el motor global `JEV (Sistema 1)`, la Internacionalización `i18n`, el Motor Multi-Moneda FX, la Observabilidad 4-Pilares, el Almacenamiento R2 y los Respaldos de Base de Datos en 4 Capas. |
| **`specs/business-domain/`** y **`specs/engineering-code/`** | Las dos bóvedas espejo de OpenSpec protegidas por `test_openspec_bipartition_and_sync.py`: la primera 100% libre de código técnico (lista para un futuro RAG de Clientes) y la segunda con el detalle técnico exacto (lista para un futuro RAG de Desarrolladores). |
| **`docs/architecture/atlas/01..05-*.archify.html`** | Los 5 tableros interactivos en HTML autocontenido generados con **Archify** (alimentados a costo `0` desde **Graphify**) para que audites visualmente modelos, schemas, RBAC y rutas con *Route Probe* y *Lenses* al cierre de cada fase. |
| **`scripts/harness.py`** y **`.agent/skills/git_smart_merge/`** | Orquestador de Git Worktrees, reserva de símbolos AST (`claims_registry.json`), Cola de Fusión Secuencial (*Merge Train*), Agente Árbitro de 4 vías (`merge-arbiter.md`) y bitácora Event-Sourced (`harness_events.jsonl`). |
| **`.agent/memory/current_state.md`** | Brújula de continuidad entre sesiones. Registra qué fase y qué tarea de `specs/06-IMPLEMENTATION-PLAN.md` está activa y qué *Quality Gates* ya se superaron. |
| **`OppyTec-Legacy/grafos-legacy/graphify-out/graph.json`** y **`.agent/skills/graphify/graph_navigator.py`** | Permiten consultar dependencias, fórmulas y llamadas de `OppyTec-Legacy` (`LegacyGraph`) y del nuevo código v2.0 (`V2Graph`) desde el REPL de Python en `< 150 tokens`, **prohibiendo volcar `graph.json` crudo al prompt** y filtrando ruido con `.graphifyignore`. |

### 3.2 Capa Determinista, Entornos, Base de Datos y Migraciones (Fases 1 y 2)
| Archivo | Rol Crítico en la Refactorización |
|---|---|
| **`Makefile`** + **`oppytec-backend/pyproject.toml`** | Concentran los **Quality Gates Estratificados** (*Fast Gate < 15s*, *Main Gate < 3m*, *Deep Gate*). |
| **`oppytec-backend/src/core/config.py`** | Validación *Fail-Fast* en el milisegundo `0`: exige `SecretStr` con entropía $\ge 256\text{ bits}$, soporta `ENV_NAMESPACE` para worktrees paralelos, gestiona `DB_POOL_CLASS` (`AsyncAdaptedQueuePool` vs `NullPool`) y bloquea conexiones cruzadas entre `local`/`ci` y `staging`/`production`. |
| **`oppytec-backend/src/shared/models_base.py`** y **`soft_delete_mixin.py`** | Separan explícitamente `PublicBase` (`schema="public"`) y `TenantBase` (esquemas `tenant_*`) y estandarizan el `soft-delete` (`is_deleted`, `deleted_at`, `deleted_by`) en todas las entidades. |
| **`oppytec-backend/src/core/database.py`** y **`bootstrap.py`** | `database.py` provee `get_public_db_session` y `get_tenant_db_session` (`SET LOCAL search_path` + `RESET search_path` en checkin). `bootstrap.py` siembra de forma idempotente al SuperUser Génesis desde variables de entorno (`SUPERUSER_GENESIS_*`). |
| **`oppytec-backend/alembic/env.py`** y **`scripts/db_migration.py`** | Ejecutan migraciones conscientes de alcance (`public` una sola vez vs `tenant_*` iterado) y mantienen la numeración correlativa `0001..NNNN` entre múltiples programadores sin `merge_heads`. |
| **`oppytec-backend/tests/architecture/test_*.py`** | Suite de Caja Blanca (`< 2s`) que bloquea el commit si se viola Clean Architecture, la secuencia correlativa de Alembic, la cobertura RBAC de 3 niveles o la paridad 1:1 de tests (`test_module_test_parity.py`). |

### 3.3 Capa de RBAC Dual, Cupos, Dominio y Seguridad (Fases 3 y 4)
| Archivo | Rol Crítico en la Refactorización |
|---|---|
| **`oppytec-backend/src/modules/identity/domain/rbac_evaluator.py`** | Evalúa matemáticamente $\mathbf{M}_{\text{Plan}} \cap ((\mathbf{P}_{\text{Rol}} \cup \mathbf{P}_{\text{Temp}}) \setminus \mathbf{P}_{\text{Deny}})$, verifica las 3 leyes de rango (`hierarchy_rank`), gestiona permisos temporales JIT y genera la huella `authorization_lineage`. |
| **`oppytec-backend/src/modules/tenancy/application/quota_service.py`** | Controla los cupos de trabajadores del plan (`max_active_users` + `custom_max_users_override`), asegura que los trabajadores en `soft-delete` no consuman cupo y revoca sesiones en Redis al desactivar empleados. |
| **`oppytec-backend/src/modules/audit/application/audit_service.py`** | Registra de forma inmutable (*Append-Only*) quién hizo qué acción operativa y quién otorgó cada permiso o acceso temporal. |
| **`oppytec-backend/tests/architecture/test_rbac_and_audit_coverage.py`** | Bloquea el CI si algún desarrollador o agente crea un endpoint en FastAPI sin `RequireTenantPermission` / `RequireGlobalPermission` o con un permiso que no tenga los 3 niveles `<modulo>.<submodulo>.<funcion>`. |
| **`oppytec-backend/src/modules/{catalog,inventory,recipes}/domain/`** | Núcleo matemático de OppyTec: conversión de unidades en 3 capas (compra $\to$ almacén $\to$ porción), cálculo de costo ponderado de escandallos y saldo atómico de Kardex. |

### 3.4 Capa de Frontend React 19 (Fase 5)
| Archivo | Rol Crítico en la Refactorización |
|---|---|
| **`oppytec-frontend/src/shared/auth/Can.tsx`** y **`usePermissions.ts`** | Ocultan o habilitan declarativamente Módulos en el Sidebar, Sub-Módulos en pestañas y Funciones en botones/columnas sensibles según los permisos del usuario en el Tenant activo del Holding. |
| **`oppytec-frontend/src/shared/components/layout/HoldingTenantSwitcher.tsx`** | Permite a un Propietario o a un trabajador con acceso transversal (ej. Hotel + Restaurante del mismo Holding) cambiar de sucursal recalculando en caliente su matriz de permisos y caché de TanStack Query. |
| **`oppytec-frontend/.dependency-cruiser.cjs`** | Garantiza que las *features* de React se mantengan desacopladas sin imports circulares. |

---

## 4. Secuencia de Ejecución Paso a Paso Vinculada al Árbol (Con Cuadriga `OpenSpec + Código/Tests + Graphify + Archify`)

1. **Paso 0 (Gobernanza Base y Arnés RLM):** Materializar `.agent/` (`rules/00..19`, `memory/`, `skills/git_smart_merge/`, `skills/jev-decision-engine/`, `skills/i18n_manager/`, `skills/fx_currency_manager/`, `skills/observability_telemetry/`, `skills/r2_media_storage/`, `skills/db_backup_recovery/`, `skills/graphify/`, `skills/archify/`, `skills/openspec-sync/`, `subagents/`), `.graphifyignore`, `specs/openspec.config.yaml`, `scripts/harness.py` y `AGENTS.md`.
2. **Fase 1 (Setup, Entornos y Andamiaje):** Materializar `docker-compose.yml`, `Makefile`, `oppytec-backend/pyproject.toml`, `oppytec-frontend/package.json`, `src/core/config.py` (*Fail-Fast* + `SecretStr`), `.env.example` y el **Mapa 5 de Archify (`05-environments-and-agentic-harness.archify.html`)**.
3. **Fase 2 (Base de Datos, Migraciones Correlativas y Bootstrap Génesis):** Redactar/validar los specs bipartitos de `tenancy`, materializar `src/core/database.py`, `src/shared/models_base.py`, `scripts/db_migration.py`, `alembic/env.py`, las migraciones `0001_public_...` y `0002_tenant_...`, `src/core/bootstrap.py`, `scripts/seed_dev_data.py`, validar con `test_alembic_integrity.py` y actualizar `Graphify` + **Mapa 1 de Archify (`01-tenancy-and-schemas.archify.html`)**.
4. **Fase 3 (Motor RBAC Dual, Cupos, Auditoría y Servicios Core):** Redactar/destilar los pares espejo en `specs/business-domain/` y `specs/engineering-code/` para cada módulo, materializar `modules/identity/`, `modules/tenancy/`, `modules/audit/`, `src/adapters/` y las capas `domain/` y `application/` con Co-Creación 1:1 de tests (`tests/unit/` + `Hypothesis` + `tests/architecture/`), actualizando `Graphify` + **Mapas 2 y 3 de Archify**.
5. **Fase 4 (Endpoints API, Guardias RBAC de 3 Niveles y Seguridad):** Materializar las capas `presentation/` (`router.py`, `schemas.py`), `src/core/guards/`, validar con `test_rbac_and_audit_coverage.py`, `test_openspec_bipartition_and_sync.py`, `tests/integration/`, `tests/security_redteam/` (`test_01..11`) y actualizar `Graphify` + **Mapa 4 de Archify**.
6. **Fase 5 (UI React 19, `<Can>`, Conmutador Multi-Tenant y Features):** Materializar `oppytec-frontend/src/shared/` (`auth/Can.tsx`, `httpClient.ts`, `env.ts`) y construir progresivamente `features/platform-admin`, `features/rbac-and-audit` y los módulos operativos, manteniendo sincronizados los guías de flujo en `specs/business-domain/` y validando con `Vitest` y `knip`.
7. **Fase 6 (Pruebas Integrales, Seguridad, Deep Gate y Certificación Final):** Ejecutar el **Deep Gate** completo (`Schemathesis`, `Locust 500 RPS`, `Playwright E2E`, `Semgrep`, `Trivy`, `pip-audit`, `pnpm audit`), consolidar `docs/architecture/graphify/` y certificar los **5 Mapas del Atlas Visual de Archify** y las **2 Bóvedas de OpenSpec** listas para los futuros RAGs de Clientes y Desarrolladores.
