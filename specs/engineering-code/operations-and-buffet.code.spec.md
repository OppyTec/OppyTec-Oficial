---
spec_id: ENG-OPERATIONS-AND-BUFFET
title: "Operación Diaria y Buffet"
audience: engineering_internal
domain_module: operations
paired_spec: specs/business-domain/operations-and-buffet.business.spec.md
jev_system1_evaluation: "Sí (Jev.score, umbral 0.80)"
last_verified_phase: "Fase 3"
---

# Operación Diaria y Buffet — Especificación de Ingeniería

## Contrato técnico
ProductionBatch, SalesRecord, BuffetSession; descuentos Kardex derivados de receta; cierre diario idempotente.

## Invariantes
- Cierre diario idempotente.
- Producción referencia receta versionada.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.score`
- Umbral de confianza: `0.80` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV puntúa desviaciones de rendimiento para alertar.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/integration/test_daily_close.py`
