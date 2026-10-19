---
spec_id: ENG-INVENTORY-AND-KARDEX
title: "Inventario y Kardex"
audience: engineering_internal
domain_module: inventory
paired_spec: specs/business-domain/inventory-and-kardex.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 3"
---

# Inventario y Kardex — Especificación de Ingeniería

## Contrato técnico
Tabla kardex_movements con lectura ORDER BY id ASC FOR UPDATE para serializar saldo y costo promedio ponderado; eventos de saldo publicados por Redis Pub/Sub al WebSocket y refrescados con TanStack Query.

## Invariantes
- Movimientos append-only.
- Bloqueo FOR UPDATE ordenado por id para evitar deadlocks.
- Costo promedio en Decimal.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.95` (bajo umbral → revisión humana / camino determinista).
- Justificación: El cálculo de saldo es aritmética exacta; JEV no interviene.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/integration/test_kardex_concurrency.py`
