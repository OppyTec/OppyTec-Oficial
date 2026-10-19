---
title: "Segundo Cerebro de OppyTec v2.0 — Mapa Maestro (MOC)"
tags:
  - oppytec-v2
  - segundo-cerebro
  - arquitectura
  - bitacora
updated: "2026-10-19"
---

# 🧠 Segundo Cerebro de OppyTec v2.0 — Mapa Maestro para Humanos (Obsidian Ready)

> **Cómo usar esta carpeta en Obsidian:**  
> Abre **Obsidian** $\to$ *"Abrir carpeta como bóveda (Open folder as vault)"* $\to$ selecciona la raíz del proyecto `/home/jcampillay/WorkArea/OppyTec/OppyTec-Code2`.  
> Si abres la **Vista de Grafo (`Ctrl+G`)** en Obsidian, verás cómo este documento conecta todas las estrategias, especificaciones de negocio, contratos de código y el diario de obra de los **12 Agentes Especializados**.

---

## 📓 1. Diario de Obra del Escuadrón de 12 Agentes (`docs/bitacora/diario-escuadron/`)
Aquí el **Agente 12 (`12-tech-writer-openspec-archify`)** documenta en lenguaje claro para personas qué se ha hecho en cada etapa, qué hizo cada agente, qué problemas surgieron y cómo se resolvieron:

- **[[00-Paso-0-Arquitectura-y-Gobernanza|Bitácora Paso 0: Diseño de las 17 Estrategias, Escuadrón de 12 Agentes y Arnés RLM]]** ✅ *(Completado)*
- **[[01-Fase-1-Setup-Entornos-Observabilidad-y-Andamiaje|Bitácora Fase 1: Setup de los 5 Entornos, Observabilidad 4-Pilares, Andamiaje Full-Stack, 21 ADRs y Mapa 5 de Archify]]** ✅ *(Completado)*
- *Próxima entrada:* `02-Fase-2-Base-de-Datos-Multi-Schema-Alembic-y-Backups-4-Capas.md` *(Se generará al cerrar la Fase 2)*

---

## 🏛️ 2. Planos Fundacionales, 21 ADRs y Atlas Visual Interactivo (`Archify`)
- **[AGENTS.md](../../AGENTS.md):** Punto de entrada cognitivo para todos los agentes.
- **[MASTER-AGENTIC-ENGINEERING-FRAMEWORK.md](../../MASTER-AGENTIC-ENGINEERING-FRAMEWORK.md):** Constitución de Ingeniería Agéntica.
- **[propuesta_arquitectura_tree_001.md](../../propuesta_arquitectura_tree_001.md):** El árbol (`tree`) completo de carpetas y archivos del proyecto.
- **Decisiones de Arquitectura Inmutables (`docs/adr/ADR-001..021`):** Colección completa desde [ADR-001 (Clean Architecture)](../adr/ADR-001-clean-architecture-modular-monolith.md) hasta [ADR-021 (WebSockets Redis Pub/Sub Zero-Polling)](../adr/ADR-021-redis-pubsub-websockets-rbac-filtered-and-zero-polling.md).
- **Atlas Visual Interactivo (`docs/architecture/atlas/`):**
  - **[Mapa 5 — Gobernanza Agéntica, 5 Entornos y Observabilidad 4-Pilares](../architecture/atlas/05-environments-and-agentic-harness.archify.html)** ✅ *(Disponible para abrir en navegador)*

---

## 📋 3. Especificaciones Canónicas (`specs/`)
1. **[00-INDEX.md](../../specs/00-INDEX.md):** Índice maestro y glosario de términos del negocio.
2. **[01-PRD.md](../../specs/01-PRD.md):** Qué hace OppyTec a nivel de producto, usuarios, planes y paquetes de créditos.
3. **[02-TRD.md](../../specs/02-TRD.md):** Stack tecnológico (Python 3.12 + motores Rust `Pydantic v2`/`uv`/`Ruff`/`orjson`/`calamine` + React 19).
4. **[03-USER-FLOWS.md](../../specs/03-USER-FLOWS.md):** Mapa de rutas y recorridos paso a paso del usuario.
5. **[04-DESIGN-SYSTEM.md](../../specs/04-DESIGN-SYSTEM.md):** Los 3 temas (`light`, `dark`, `ocean-blue`), 42 colores, 49 íconos y diseño *Mobile-First*.
6. **[05-DATABASE-SCHEMA.md](../../specs/05-DATABASE-SCHEMA.md):** Todas las tablas del esquema `public` y de los esquemas `tenant_<slug>`.
7. **[06-IMPLEMENTATION-PLAN.md](../../specs/06-IMPLEMENTATION-PLAN.md):** El orden exacto de construcción de la Fase 1 a la Fase 6.

---

## 🧭 4. Las 17 Estrategias Maestras (`.agent/estrategias/`)

| # | Estrategia | Qué Resuelve en Palabras Simples |
|---|---|---|
| **1** | [Migraciones Alembic](../../.agent/estrategias/estrategia_migraciones_alembic_001.md) | Orden correlativo `0001, 0002...` sin conflictos cuando trabajan varios programadores o agentes. |
| **2** | [RBAC Dual y Auditoría](../../.agent/estrategias/estrategia_rbac_y_auditoria_001.md) | Permisos en 3 niveles (`Módulo -> Sub-módulo -> Función`), cupos por plan con `soft-delete` y registro de quién hizo qué. |
| **3** | [Testing y Seguridad Red Team](../../.agent/estrategias/estrategia_testing_calidad_y_seguridad_001.md) | Ningún código nace sin su test; 11 ataques estilo Kali Linux automatizados y cero secretos en el código. |
| **4** | [Los 5 Entornos](../../.agent/estrategias/estrategia_entornos_y_despliegue_001.md) | `local`, `preview`, `ci`, `staging` y `production` aislados para nunca romper datos reales. |
| **5** | [Git Worktrees y Smart Merge](../../.agent/estrategias/estrategia_orquestacion_git_worktrees_y_smart_merge_001.md) | Cómo varios agentes/programadores trabajan al mismo tiempo y unen su código sin sobrescribirse. |
| **6** | [Atlas Visual Archify](../../.agent/estrategias/estrategia_visualizacion_y_auditoria_archify_001.md) | 5 mapas interactivos en HTML para explorar visualmente la arquitectura en el navegador. |
| **7** | [OpenSpec Negocio vs. Código](../../.agent/estrategias/estrategia_openspec_negocio_vs_codigo_001.md) | Separa cómo funciona el negocio (para clientes) de cómo está programado el código (para desarrolladores). |
| **8** | [Asistente IA `OppyFy` y Créditos](../../.agent/estrategias/estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md) | Asistente con RAG de 3 capas, RBAC propio editable por cliente y paquetes de créditos acumulables sin caducidad. |
| **9** | [Motor `JEV` (Sistema 1)](../../.agent/estrategias/estrategia_motor_decisiones_jev_system1_001.md) | Modelo ultrarrápido (70–500 ms) que clasifica, enruta y modera ahorrando miles de tokens. |
| **10** | [Internacionalización `i18n`](../../.agent/estrategias/estrategia_internacionalizacion_i18n_multilenguaje_001.md) | Banderas SVG (`🇪🇸 ES` / `🇺🇸 EN`), traducción de la web y de los productos del cliente sin traducir marcas propias (`"Pollo King"`). |
| **11** | [Multi-Moneda FX y Precios](../../.agent/estrategias/estrategia_multimoneda_fx_precios_y_cobros_001.md) | Selector de moneda (`CLP`, `USD`, `EUR`, `BRL`) conectado al Banco Central de Chile y Banco Central Europeo. |
| **12** | [Observabilidad 4-Pilares](../../.agent/estrategias/estrategia_observabilidad_monitoreo_y_analitica_001.md) | `OpenTelemetry`, `Grafana`, `Sentry/GlitchTip` y `Umami` con 13 sub-vistas en el panel de administración. |
| **13** | [Imágenes en R2 y Cuotas MB](../../.agent/estrategias/estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md) | Fotos convertidas a `.webp` ligeras, sin mezclarse entre clientes y con límite de memoria según el plan. |
| **14** | [Respaldos de Base de Datos 4-Capas](../../.agent/estrategias/estrategia_respaldos_base_datos_y_recuperacion_001.md) | Copias cifradas en Neon, Cloudflare R2, VPS secundario y tu servidor local, permitiendo restaurar a 1 solo restaurante. |
| **15** | [Escuadrón de 12 Agentes](../../.agent/estrategias/estrategia_escuadron_multiagente_prompts_y_autoreparacion_001.md) | Los 12 agentes especialistas, sus memorias propias (`prompt.md`, `knowledge.md`, `handovers/`) y su autoreparación. |
| **16** | [Diseño UI/UX y *Mobile-First*](../../.agent/estrategias/estrategia_sistema_diseno_ux_ui_y_mobile_first_001.md) | Conserva los 3 temas de Legacy (`light`, `dark`, `ocean-blue`), sus efectos y diseña primero para celular. |
| **17** | [Tiempo Real con WebSockets](../../.agent/estrategias/estrategia_tiempo_real_websockets_y_notificaciones_001.md) | Notificaciones y saldos de stock en vivo con Redis Pub/Sub y TanStack Query, prohibiendo llamadas repetitivas (*polling*). |

---

## 🤖 5. Directorio de los 12 Agentes Especializados (`.agent/subagents/`)
Cada agente tiene su carpeta propia con su instrucción (`prompt.md`), lo que ha aprendido (`knowledge.md`) y su último reporte de traspaso (`handovers/latest_handover.md`):

1. **[Agente 01 — Orquestador / PM](../../.agent/subagents/01-orchestrator-pm/prompt.md)**
2. **[Agente 02 — Arquitecto de Software DDD](../../.agent/subagents/02-software-architect/prompt.md)**
3. **[Agente 03 — Ingeniero de Base de Datos, Alembic y Backups](../../.agent/subagents/03-database-alembic-and-backup-engineer/prompt.md)**
4. **[Agente 04 — Programador Senior Backend, RBAC y R2](../../.agent/subagents/04-backend-senior-dev/prompt.md)**
5. **[Agente 05 — Programador Senior Frontend y *Mobile-First*](../../.agent/subagents/05-frontend-senior-dev/prompt.md)**
6. **[Agente 06 — Especialista en IA `OppyFy` y Motor `JEV`](../../.agent/subagents/06-ai-oppyfy-and-jev-engineer/prompt.md)**
7. **[Agente 07 — Especialista en `i18n` y Multi-Moneda `FX`](../../.agent/subagents/07-i18n-and-fx-currency-specialist/prompt.md)**
8. **[Agente 08 — Especialista en Entornos y Observabilidad](../../.agent/subagents/08-environments-and-observability-engineer/prompt.md)**
9. **[Agente 09 — Ingeniero de QA y Paridad con Legacy](../../.agent/subagents/09-qa-parity-and-test-engineer/prompt.md)**
10. **[Agente 10 — Auditor Estricto de Ciberseguridad (Red Team)](../../.agent/subagents/10-cybersecurity-redteam-auditor/prompt.md)**
11. **[Agente 11 — Especialista en Git Worktrees y Smart Merge](../../.agent/subagents/11-git-worktree-merge-arbiter/prompt.md)**
12. **[Agente 12 — Technical Writer, OpenSpec, Archify y Bitácora Humana](../../.agent/subagents/12-tech-writer-openspec-archify/prompt.md)**
