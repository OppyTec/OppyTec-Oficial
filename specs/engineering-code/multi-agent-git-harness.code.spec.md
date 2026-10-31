---
spec_id: ENG-MULTI-AGENT-GIT-HARNESS
title: "Arnés Multi-Agente, Enrutamiento Dinámico LLM y Git Worktrees (ingeniería)"
audience: engineering_internal
domain_module: tenancy
paired_spec: null
jev_system1_evaluation: "Sí (Jev.choice, umbral 0.85)"
last_verified_phase: "Fase 7.7"
---

# Arnés Multi-Agente, Enrutamiento Dinámico LLM y Git Worktrees (ingeniería) — Especificación de Ingeniería

## Contrato técnico
- **Arnés CLI (`scripts/harness.py`):**
  - Comandos de gobernanza: `claim-ast`, `release-ast`, `verify-evals`, `fast-gate`, `nav`, `sync-graph`.
  - Comandos de modelos LLM: `route-task` (con `--explain-complexity`), `escalate-model`, `trigger-fallback`.
- **Git Worktrees:** `.worktrees/wt-<id>` con `claims_registry.json` y bloqueo atómico con `fcntl.flock`.
- **Merge Train:** `rebase + --ff-only` con resolución determinista y Árbitro de 4 vías.
- **Enrutador Dinámico de Modelos LLM (`.agent/config/model_router.json`):**
  - Gestión multi-proveedor con 3 Tiers abstractos:
    - `tier_lightweight`: Gemini 3.8 Flash, Gemini Flash-Lite.
    - `tier_fast_execution`: Gemini 3.8 Flash, GPT-4o-mini, Claude 3.5 Haiku.
    - `tier_reasoning_heavy`: Gemini 4 Argon, Claude 3.7 Sonnet, GPT-4o, Gemini 2.5 Pro.
- **Evaluador de Complejidad Cognitiva JEV (`.agent/skills/jev-decision-engine/complexity_evaluator.py`):**
  - Fórmula matemática en tiempo constante ($< 15\text{ ms}$, SLA real $< 0.2\text{ ms}$):
    $$\mathcal{C}_{task} = \min\left(1.0,\; 0.35 \cdot S_{graph} + 0.30 \cdot S_{domain} + 0.20 \cdot S_{scope} + 0.15 \cdot S_{context}\right)$$
  - Umbrales de asignación y promoción:
    - $\mathcal{C}_{task} \le 0.34 \implies \text{tier\_lightweight}$ (tareas cosméticas, labels, badges, traducciones i18n).
    - $0.35 \le \mathcal{C}_{task} \le 0.69 \implies \text{tier\_fast\_execution}$ (CRUD estándar, endpoints, filtros, modales UI).
    - $\mathcal{C}_{task} \ge 0.70 \implies \text{tier\_reasoning\_heavy}$ (kardex, FX, esquemas BD multi-tenant, auditoría red team).
- **Auto-escalado reactivo (`escalate_model_tier`):**
  - Progresión ascendente reactiva ante fallas en Fast Gate o déficit de razonamiento:
    `tier_lightweight` $\to$ `tier_fast_execution` $\to$ `tier_reasoning_heavy`.
  - Emisión del evento auditativo inmutable `MODEL_TIER_ESCALATED` en `.agent/memory/harness_events.jsonl`.

## Invariantes
- Claim atómico antes de editar archivos compartidos.
- Evals con SHA-256 inmutable (Cero *Reward Hacking*).
- Merge solo fast-forward (`--ff-only`).
- Los agentes con piso arquitectónico crítico (`01-orchestrator-pm`, `02-software-architect`, `10-cybersecurity-redteam-auditor`, `11-git-worktree-merge-arbiter`, `13-browser-e2e-playwright`) jamás son degradados por debajo de `tier_reasoning_heavy`.
- Consulta obligatoria de Graphify CLI (`nav`) antes de comenzar (Pre-ejecución) y actualización obligatoria (`sync-graph`) al concluir (Post-ejecución) según Regla 6 de `AGENTS.md`.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.choice`
- Umbral de confianza: `0.85` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV evalúa intenciones y asigna dinámicamente modelos y pipelines en tiempo constante $< 15\text{ ms}$.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/architecture/test_harness_integrity.py`
- `oppytec-backend/tests/architecture/test_harness_and_merge_integrity.py`
- `oppytec-backend/tests/unit/agent_governance/test_dynamic_model_router.py` (7/7 tests)
- `oppytec-backend/tests/unit/agent_governance/test_jev_cognitive_task_router.py` (4/4 tests)
