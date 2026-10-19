---
spec_id: ENG-DATA-SECURITY-AND-BACKUPS
title: "Seguridad de Datos y Respaldos"
audience: engineering_internal
domain_module: tenancy
paired_spec: specs/business-domain/data-security-and-backups.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 3"
---

# Seguridad de Datos y Respaldos — Especificación de Ingeniería

## Contrato técnico
Respaldos .sql.zst.age en Neon, R2, VPS y local; restore-tenant quirúrgico por esquema; secretos SecretStr; Argon2id.

## Invariantes
- Backups siempre cifrados con age.
- Restore por tenant en esquema temporal y swap atómico.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.95` (bajo umbral → revisión humana / camino determinista).
- Justificación: Operaciones criptográficas deterministas.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/integration/test_backup_restore_tenant.py`
