---
spec_id: ENG-WASTE-AND-MERMAS
title: "Mermas y Desperdicios"
audience: engineering_internal
domain_module: inventory
paired_spec: specs/business-domain/waste-and-mermas.business.spec.md
jev_system1_evaluation: "Sí (Jev.choice, umbral 0.80)"
last_verified_phase: "Fase 8"
---

# Mermas y Desperdicios — Especificación de Ingeniería

## Contrato técnico
- Integrado en el módulo de Inventario (`oppytec-backend/src/modules/inventory/application/waste_service.py` y `router.py`).
- Registro de merma vinculado transaccionalmente a un movimiento de Kardex tipo `MERMA` o `CONSUMO`.
- Motivos estandarizados en catálogo tipificado (`vencimiento`, `daño`, `error`, `caducidad`, `exceso`, `mal_estado`, `otro`).
- Flujo de aprobación automática vs supervisada si supera el umbral financiero ($50.000 CLP / equivalente FX).
- Valorización financiera precisa al Costo Promedio Ponderado (PPP) vigente en `Decimal`.
- Componente frontend: `MermaDialog.tsx` con soporte i18n (`inventory.json:mermas.*`), selección de insumo y lote, y validación visual.

## Invariantes
- Toda merma sin asiento balanceado en Kardex es rechazada.
- Motivo debe pertenecer al catálogo cerrado.
- Cero punto flotante en la valorización del desperdicio (`Decimal(14, 2)`).
- Validación de aislamiento multi-tenant e intercepción IDOR.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.choice`
- Umbral de confianza: `0.80` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV asiste en la clasificación y sugerencia del motivo de merma a partir de la descripción textual u operativa.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/unit/test_waste_valuation.py`
- `oppytec-backend/tests/security_redteam/test_12_inventory_offensive_security_and_rbac.py`
- `oppytec-frontend/src/features/inventory/__tests__/ModalesStock.test.tsx`
