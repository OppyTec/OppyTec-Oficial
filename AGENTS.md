# AGENTS.md — Enrutador Cognitivo Maestro y Gobernanza del Escuadrón Multi-Agente de OppyTec v2.0

> **Estado:** Activo e Inmutable  
> **Propósito:** Punto de entrada obligatorio en el milisegundo `0` para cualquier Agente de IA (**Prime Agent RLM**, **Pi**, **Claude Code**, **Codex**, **Gemini**) que opere en este monorepo.  

---

## 1. Regla de Oro Inviolable

1. **PROHIBIDO modificar, renombrar o eliminar archivos dentro de `OppyTec-Legacy/`:** `OppyTec-Legacy/` es la fuente de verdad histórica en modo **100% Solo Lectura** para consultar fórmulas y comportamiento de negocio (preferentemente a través de `LegacyGraph` en `.agent/skills/graphify/`).
2. **PROHIBIDO modificar `.agent/rules/`, `.agent/evals/` o `oppytec-backend/tests/architecture/` para relajar controles (*Anti-Reward-Hacking*):** Los agentes constructores pueden ejecutar las evaluaciones para autocalificarse (`10/10`), pero cualquier intento de alterar un test de arquitectura o una rúbrica de evaluación será bloqueado y revertido por `scripts/harness.py` y `JEV`.
3. **Co-Creación 1:1 Obligatoria:** Ningún código en `oppytec-backend/src/` o `oppytec-frontend/src/` existe sin sus pruebas unitarias, de integración y de seguridad creadas en el mismo paso, con `0` hardcoding (`SecretStr`), `i18n` en el 100% de textos (`es`/`en`), soporte Multi-Moneda FX (`Decimal`), evaluación obligatoria *"¿Lo puede hacer JEV (Sí/No)?"* y sincronización con **OpenSpec Bipartito**, **`Graphify`** y **`Archify`**.

---

## 2. Protocolo de Inicio de Sesión para Cada Agente (7 Pasos de Auto-Mejora)

Al iniciar cualquier tarea en el repositorio o dentro de un `Git Worktree` (`.worktrees/wt-<id>`):

1. **Lee el estado actual del proyecto:** `.agent/memory/current_state.md`.
2. **Identifica tu Rol en el Escuadrón de 12 Agentes (`.agent/subagents/01..12-*/`):**
   - Carga únicamente tu propio **`prompt.md`**, tu **`knowledge.md`** (lecciones aprendidas previas de tu especialidad) y tu **`handovers/latest_handover.md`**.
3. **Consulta el Grafo AST sin Gastar Tokens:** Usa `.agent/skills/graphify/graph_navigator.py` antes de leer archivos masivos.
4. **Reclama tus Nodos AST (`claims_registry.json`):** Antes de editar cualquier archivo compartido, registra tu reserva atómica (`fcntl.flock`) mediante `python scripts/harness.py claim-ast`.
5. **Ejecuta tu Autoevaluación (`Fast Gate < 15s` + `.agent/evals/rubric_10_criteria.yaml`):** Verifica que cumplas los 10 criterios antes de solicitar entrada al *Merge Train*.
6. **Escribe tu Reporte de Traspaso (`handovers/latest_handover.md`):** Registra *Completed*, *Friction & Failures* y *Next Exact Action*.
7. **Destila Aprendizajes (`/refine`):** Si descubriste un patrón reutilizable o corrigiste un fallo, regístralo en tu `knowledge.md` o empaquétalo en `.agent/skills/`.

---

## 3. Mapa del Escuadrón de 12 Agentes Especializados (`.agent/subagents/`)

| ID | Carpeta en `.agent/subagents/` | Especialidad y Estrategias a Cargo | Tier de Modelo |
|---|---|---|---|
| **01** | `01-orchestrator-pm/` | Orquestación DAG, `Git Worktrees`, `claims_registry.json` y corte de bucles | Gemini 4 Argon |
| **02** | `02-software-architect/` | DDD, Clean Architecture, Paridad Legacy, Pre-Spec y Gate `JEV (Sí/No)` | Gemini 4 Argon |
| **03** | `03-database-alembic-and-backup-engineer/` | Esquemas `public`/`tenant_*`, Alembic `0001..N` y Backups Cifrados 4-Capas | Gemini 3.8 Flash |
| **04** | `04-backend-senior-dev/` | FastAPI, SQLAlchemy 2 Async, RBAC Dual 3-Niveles, Auditoría y R2 Quotas | Gemini 3.8 Flash / Argon |
| **05** | `05-frontend-senior-dev/` | React 19, ADN Visual Legacy (3 temas `light`/`dark`/`ocean-blue`), *Mobile-First* y `<Can>` | Gemini 3.8 Flash |
| **06** | `06-ai-oppyfy-and-jev-engineer/` | Asistente `OppyFy` (RAG 3-Capas, RBAC propio editable, Créditos, `llm_request_logs`) y `JEV` | Gemini 3.8 Flash / Argon |
| **07** | `07-i18n-and-fx-currency-specialist/` | `i18n` Estático/Dinámico (`"Pollo King"`, patrón `Pi`, banderas SVG) y Multi-Moneda FX (BCCh/BCE) | Gemini 3.8 Flash |
| **08** | `08-environments-and-observability-engineer/` | 5 Entornos (`SHA-256`) y Observabilidad 4-Pilares (`OpenTelemetry`, `Grafana`, `Sentry`, `Umami`) | Gemini 3.8 Flash |
| **09** | `09-qa-parity-and-test-engineer/` | Testing 5 Dimensiones, Paridad Matemática con Legacy y **Bucle de Autoreparación QA** | Gemini 4 Argon / Flash |
| **10** | `10-cybersecurity-redteam-auditor/` | 11 Vectores Red Team (Kali), Semgrep/Trivy, **Autoparcheo y Poder de Veto Final** | Gemini 4 Argon |
| **11** | `11-git-worktree-merge-arbiter/` | *Merge Train* (`rebase + --ff-only`), resolución determinista y Árbitro Fresco de 4 vías | Gemini 4 Argon |
| **12** | `12-tech-writer-openspec-archify/` | Sincronización de Bóvedas OpenSpec (`business-domain/` y `engineering-code/`), `Graphify` y Atlas `Archify` | Gemini 3.8 Flash |

---

## 4. Índice de Reglas Inmutables (`.agent/rules/00..21`) y Estrategias Maestras (`_001.md`)

- **Reglas Inmutables:** `.agent/rules/00-meta-agent-instructions.md` al `.agent/rules/21-design-system-legacy-dna-and-mobile-first.md`.
- **Mapa Arquitectónico:** `propuesta_arquitectura_tree_001.md`.
- **16 Estrategias Maestras:** `.agent/estrategias/estrategia_*_001.md` en la raíz del repositorio.
