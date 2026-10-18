# Estado Actual de la Refactorización — OppyTec v2.0

- **Fase Activa:** `Paso 0 Completado -> Listo para iniciar Fase 1 (Setup, Entornos, Observabilidad Base y Andamiaje)`
- **Último Checkpoint Git:** `2ee85d0` (`master`)
- **Estado del Escuadrón de 12 Agentes:** Inicializado en `.agent/subagents/01..12-*/`
- **Estado de Reglas Inmutables:** `.agent/rules/00..21-*.md` activas
- **Estado de Evaluaciones Anti-Trampa:** `.agent/evals/rubric_10_criteria.yaml` sellado con `SHA-256`

## Checklist Paso 0 (Gobernanza Base y Arnés RLM)
- [x] `AGENTS.md` y `.graphifyignore` en la raíz del proyecto
- [x] `.agent/rules/00..21-*.md` (22 reglas inmutables)
- [x] `.agent/evals/rubric_10_criteria.yaml` y `eval_hashes.sha256`
- [x] `.agent/subagents/01..12-*/` con `prompt.md`, `knowledge.md` y `handovers/latest_handover.md`
- [x] `.agent/skills/` con paquetes ejecutables en Python (`git_smart_merge`, `graphify`, `jev-decision-engine`, `i18n_manager`, etc.)
- [x] `scripts/harness.py` operativo
- [x] Bóvedas `specs/business-domain/` y `specs/engineering-code/` + `docs/adr/` inicializadas
