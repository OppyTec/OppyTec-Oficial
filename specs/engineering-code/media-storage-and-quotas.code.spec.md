---
spec_id: ENG-MEDIA-STORAGE-AND-QUOTAS
title: "Imágenes y Cuota de Almacenamiento"
audience: engineering_internal
domain_module: tenancy
paired_spec: specs/business-domain/media-storage-and-quotas.business.spec.md
jev_system1_evaluation: "Sí (Jev.boolean, umbral 0.90)"
last_verified_phase: "Fase 3"
---

# Imágenes y Cuota de Almacenamiento — Especificación de Ingeniería

## Contrato técnico
Cloudflare R2 con prefijo <env>/<tenant_slug>/; WebP dual (thumb + full); contador de MB por tenant contra cuota del plan.

## Invariantes
- Clave de objeto siempre con prefijo de tenant y entorno.
- Cuota verificada antes de subir.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.90` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV modera contenido de la imagen antes de almacenar.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/unit/test_r2_quota_and_webp.py`
