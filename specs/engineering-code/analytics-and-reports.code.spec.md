---
spec_id: ENG-ANALYTICS-AND-REPORTS
title: "Analítica y Reportes"
audience: engineering_internal
domain_module: analytics
paired_spec: specs/business-domain/analytics-and-reports.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 3"
---

# Analítica y Reportes — Especificación de Ingeniería

## Contrato técnico
Módulo analytics con vistas agregadas por tenant; consultas de solo lectura; formateo de moneda en presentación con Decimal; permisos analytics.*.view.

## Invariantes
- Solo lectura sobre datos operativos.
- Sin agregación en float.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.95` (bajo umbral → revisión humana / camino determinista).
- Justificación: Agregaciones exactas; sin decisión probabilística.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/unit/test_analytics_aggregations.py`
