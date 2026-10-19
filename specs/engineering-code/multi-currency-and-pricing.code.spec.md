---
spec_id: ENG-MULTI-CURRENCY-AND-PRICING
title: "Multi-Moneda y Precios"
audience: engineering_internal
domain_module: catalog
paired_spec: specs/business-domain/multi-currency-and-pricing.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 3"
---

# Multi-Moneda y Precios — Especificación de Ingeniería

## Contrato técnico
Servicio FX con BCCh (primario) y BCE Frankfurter (respaldo), cache diario, cuantización por moneda en Decimal; tabla fx_rates en public.

## Invariantes
- Fallback BCCh→BCE.
- Tasa histórica inmutable.
- Prohibido float.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.95` (bajo umbral → revisión humana / camino determinista).
- Justificación: Conversión aritmética determinista.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/unit/test_fx_decimal_rounding.py`
