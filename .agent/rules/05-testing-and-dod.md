# Regla 05: Co-Creación 1:1 de Pruebas y Quality Gates Estratificados
- Ningún código en `src/` se crea sin sus tests en `tests/unit/` (`Hypothesis`), `tests/integration/` y `tests/security_redteam/`.
- Estratificación de ejecución: *Fast Gate* (< 15s en cada paso), *Main Gate* (< 3m en PR/push) y *Deep Gate* (cierre de fase / Staging).
