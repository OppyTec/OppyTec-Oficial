---
spec_id: ENG-PURCHASES-AND-INVOICES
title: "Compras, Proveedores y Facturas"
audience: engineering_internal
domain_module: procurement
paired_spec: specs/business-domain/purchases-and-invoices.business.spec.md
jev_system1_evaluation: "Sí (Jev.score, umbral 0.85)"
last_verified_phase: "Fase 3"
---

# Compras, Proveedores y Facturas — Especificación de Ingeniería

## Contrato técnico
Supplier, PurchaseOrder, Invoice, InvoiceLine; entrada al Kardex por línea; monto original + moneda + tasa FX congelada en Decimal.

## Invariantes
- Tasa FX congelada al registrar.
- Línea de factura genera exactamente un movimiento Kardex.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.score`
- Umbral de confianza: `0.85` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV puntúa la confianza de la extracción de líneas de factura; bajo umbral exige revisión humana.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/integration/test_invoice_to_kardex.py`
