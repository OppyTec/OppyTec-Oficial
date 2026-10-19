---
spec_id: ENG-TENANCY-AND-PLANS
title: "Empresas, Restaurantes y Planes"
audience: engineering_internal
domain_module: tenancy
paired_spec: specs/business-domain/tenancy-and-plans.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.90)"
last_verified_phase: "Fase 3"
---

# Empresas, Restaurantes y Planes — Especificación de Ingeniería

## Contrato técnico
Jerarquía public.holdings -> legal_entities 1:1 -> tenants; aislamiento por esquema tenant_<slug> con SET LOCAL search_path y RESET search_path al cerrar la transacción; tabla plans con modules y max_active_users.

## Invariantes
- Prohibido compartir tablas operativas entre tenants.
- Relación legal_entity->tenant UNIQUE.
- search_path se resetea siempre en finally.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.90` (bajo umbral → revisión humana / camino determinista).
- Justificación: Alta de tenants es operación determinista de SuperUser; JEV solo valida el slug propuesto.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/architecture/test_multi_schema_isolation.py`
