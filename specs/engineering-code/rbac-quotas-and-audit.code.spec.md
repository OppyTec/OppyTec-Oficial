---
spec_id: ENG-RBAC-QUOTAS-AND-AUDIT
title: "Permisos, Cupos de Usuarios y Auditoría"
audience: engineering_internal
domain_module: identity
paired_spec: specs/business-domain/rbac-quotas-and-audit.business.spec.md
jev_system1_evaluation: "Sí (Jev.score, umbral 0.85)"
last_verified_phase: "Fase 3"
---

# Permisos, Cupos de Usuarios y Auditoría — Especificación de Ingeniería

## Contrato técnico
Ecuación M_Plan ∩ ((P_Rol ∪ P_Temp) \ P_Deny); códigos <modulo>.<submodulo>.<funcion>; 3 leyes de hierarchy_rank; max_active_users con soft-delete; kill-switch en Redis; doble libro audit global_audit_log y tenant audit_log.

## Invariantes
- hierarchy_rank menor = mayor poder; ley 1 no operar sobre rank <= propio.
- Soft-delete libera cupo, nunca borra auditoría.
- Kill-switch consultado en cada request.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.score`
- Umbral de confianza: `0.85` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV puede puntuar riesgo de patrones de acceso anómalos; la decisión de permiso permanece determinista.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/architecture/test_rbac_and_audit_coverage.py`
