---
spec_id: ENG-TENANCY-RBAC-AND-MIGRATIONS
title: "Tenancy, RBAC y Migraciones (ingeniería)"
audience: engineering_internal
domain_module: tenancy
paired_spec: null
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 3"
---

# Tenancy, RBAC y Migraciones (ingeniería) — Especificación de Ingeniería

## Contrato técnico
Alembic lineal 0001..N sin merge_heads; migraciones public vs tenant; db_migration.py new/rebase/verify/impact; bootstrap por tenant; RBAC seed.

## Invariantes
- Una sola cabeza Alembic.
- Migraciones tenant aplicadas a todos los esquemas.
- Prohibido editar migraciones ya aplicadas.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.95` (bajo umbral → revisión humana / camino determinista).
- Justificación: Linealidad de migraciones es verificación determinista.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/architecture/test_alembic_linear_history.py`
