---
title: "Bitácora Fase 3: Clean Architecture, RBAC Dual, OppyFy, JEV, i18n, FX y R2"
phase: "Fase 3"
date: "2026-10-19"
author_agent: "12-tech-writer-openspec-archify"
tags:
  - bitacora
  - fase-3
  - openspec
  - archify
  - rbac
  - clean-architecture
---

# Bitácora Fase 3

## Qué se construyó (en lenguaje simple)
- **Dos bóvedas de especificaciones espejo:** 13 documentos para clientes en `specs/business-domain/` (sin código ni SQL) y 15 para desarrolladores en `specs/engineering-code/`. Cada documento técnico declara si el motor `JEV` puede encargarse de la tarea (Sí/No), con qué primitiva y qué umbral de confianza.
- **Mapa 2 de Archify** ([abrir](../../architecture/atlas/02-rbac-quotas-and-audit.archify.html)): la ecuación de permisos `M_Plan ∩ ((P_Rol ∪ P_Temp) \ P_Deny)`, las 3 leyes de `hierarchy_rank`, cupos de usuarios con *soft-delete* y *kill-switch* en Redis, permisos editables de `OppyFy` y el doble libro de auditoría.
- **Mapa 3 de Archify** ([abrir](../../architecture/atlas/03-clean-architecture-and-domain.archify.html)): los 10 módulos, la regla de dependencias `domain ← application ← infrastructure ← presentation`, conversión `Decimal` de 3 capas, Kardex `ORDER BY id ASC FOR UPDATE`, `JEV`, `i18n`, `FX` y `R2` con WebP.
- **Snapshot Graphify:** `docs/architecture/graphify/v2_phase3_domain_graph.json`.

## Fricción
- El agente anterior se cortó por cuota sin dejar archivos; se retomó desde cero con commits WIP incrementales.

## Próximo paso
- Fase 4: sincronizar los specs con los endpoints reales cuando el backend de Fase 3 esté mergeado y regenerar los recibos `SHA-256`.
