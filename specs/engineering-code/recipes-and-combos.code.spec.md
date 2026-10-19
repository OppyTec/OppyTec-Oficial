---
spec_id: ENG-RECIPES-AND-COMBOS
title: "Recetas, Costeo y Combos"
audience: engineering_internal
domain_module: recipes
paired_spec: specs/business-domain/recipes-and-combos.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 3"
---

# Recetas, Costeo y Combos — Especificación de Ingeniería

## Contrato técnico
Recipe, RecipeLine y Combo; costeo recursivo con Decimal usando la conversión 3 capas; detección de ciclos receta→sub-receta.

## Invariantes
- Prohibidos ciclos de sub-recetas.
- Costeo sin float.
- Rendimiento (yield) > 0.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.95` (bajo umbral → revisión humana / camino determinista).
- Justificación: El costeo es determinista y debe igualar al Legacy.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/unit/test_recipe_costing_parity.py`
