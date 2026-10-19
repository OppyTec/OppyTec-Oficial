---
spec_id: ENG-WASTE-AND-MERMAS
title: "Mermas y Desperdicios"
audience: engineering_internal
domain_module: inventory
paired_spec: specs/business-domain/waste-and-mermas.business.spec.md
jev_system1_evaluation: "Sí (Jev.choice, umbral 0.80)"
last_verified_phase: "Fase 3"
---

# Mermas y Desperdicios — Especificación de Ingeniería

## Contrato técnico
WasteRecord vinculado a un movimiento del Kardex tipo salida; motivo en catálogo cerrado; valorización con costo promedio vigente en Decimal.

## Invariantes
- Merma sin movimiento Kardex asociado es inválida.
- Motivo ∈ catálogo cerrado.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.choice`
- Umbral de confianza: `0.80` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV sugiere el motivo de merma a partir de texto libre.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/unit/test_waste_valuation.py`
