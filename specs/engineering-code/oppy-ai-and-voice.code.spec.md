---
spec_id: ENG-OPPY-AI-AND-VOICE
title: "Asistente OppyFy y Voz"
audience: engineering_internal
domain_module: oppy_ai
paired_spec: specs/business-domain/oppy-ai-and-voice.business.spec.md
jev_system1_evaluation: "Sí (Jev.choice, umbral 0.75)"
last_verified_phase: "Fase 3"
---

# Asistente OppyFy y Voz — Especificación de Ingeniería

## Contrato técnico
RAG de 3 capas (3A docs de negocio, 3B datos del tenant, 3C memoria); RBAC propio de OppyFy editable; créditos con llm_request_logs; JEV Sistema 1 para clasificar, enrutar y moderar antes del LLM grande.

## Invariantes
- Capa 3A solo lee specs business-domain.
- Cada llamada LLM registra tokens y créditos.
- Moderación previa obligatoria.

## Evaluación JEV Sistema 1
jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.choice`
- Umbral de confianza: `0.75` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV enruta la intención (consulta, acción, charla) en 70-500 ms antes del LLM.

## Pruebas (Co-Creación 1:1)
- `oppytec-backend/tests/unit/test_oppyfy_rbac_and_credits.py`
