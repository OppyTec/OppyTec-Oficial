---
spec_id: ENG-MULTI-AGENT-GIT-HARNESS
title: "Arnés Multi-Agente y Git Worktrees (ingeniería)"
audience: engineering_internal
domain_module: tenancy
paired_spec: null
jev_system1_evaluation: "Sí (Jev.choice, umbral 0.85)"
last_verified_phase: "Fase 3"
---

# Arnés Multi-Agente y Git Worktrees (ingeniería) — Especificación de Ingeniería

## Contrato técnico
scripts/harness.py claim-ast, verify-evals, Fast Gate; Git Worktrees .worktrees/wt-<id>; claims_registry.json con fcntl.flock; Merge Train rebase + ff-only.

## Invariantes
- Claim atómico antes de editar archivos compartidos.
- Evals con SHA-256 inmutable.
- Merge solo fast-forward.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.choice`
- Umbral de confianza: `0.85` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV elige estrategia de resolución de conflictos propuesta; el Árbitro valida.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/architecture/test_harness_integrity.py`
