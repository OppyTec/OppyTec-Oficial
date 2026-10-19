---
spec_id: ENG-CATALOG-AND-UNITS
title: "Catálogo de Productos e Ingredientes y Unidades"
audience: engineering_internal
domain_module: catalog
paired_spec: specs/business-domain/catalog-and-units.business.spec.md
jev_system1_evaluation: "Sí (Jev.choice, umbral 0.80)"
last_verified_phase: "Fase 3"
---

# Catálogo de Productos e Ingredientes y Unidades — Especificación de Ingeniería

## Contrato técnico
Entidades Product, Ingredient, Unit y UnitConversion en tenant_<slug>; conversión 3 capas (compra→base→receta) con Decimal; traducciones dinámicas en tabla de i18n con exclusión de marcas.

## Invariantes
- Prohibido float; todo Decimal con cuantización explícita.
- Conversión ida y vuelta sin pérdida visible.
- Nombres de marca marcados no_translate.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.choice`
- Umbral de confianza: `0.80` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV clasifica un ingrediente nuevo en la categoría más probable; el usuario confirma.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/unit/test_decimal_unit_conversion.py`
