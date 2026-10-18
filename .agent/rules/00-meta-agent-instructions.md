# Regla 00: Instrucciones Meta-Agente, Protocolo RLM y Límites de Autonomía
- Prioridad de lectura: `AGENTS.md` -> `.agent/memory/current_state.md` -> tu propio `prompt.md`, `knowledge.md` y `handovers/latest_handover.md`.
- **Inviolabilidad:** Prohibido modificar `OppyTec-Legacy/`, `.agent/rules/`, `.agent/evals/` o `oppytec-backend/tests/architecture/`.
- **Contexto como Variable:** En el REPL de Prime Agent, nunca vuelques archivos gigantes ni `graph.json` crudo al prompt; usa `.agent/skills/graphify/graph_navigator.py`.
- **Compacción Temprana:** Mantén `compaction.thresholdPercent: 75` para prevenir *attention drift*.
