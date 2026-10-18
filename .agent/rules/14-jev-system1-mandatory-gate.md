# Regla 14: Evaluación Autónoma Obligatoria de `JEV (Sistema 1)`
- Referencia: `estrategia_motor_decisiones_jev_system1_001.md`.
- En todo módulo actual o futuro, el agente debe responder en el spec y en el diseño: *"¿Esta tarea la puede realizar JEV (Sí/No)?"* (Clasificación, Enrutamiento, Moderación, Puntuación/Juez, Model Cascading). Si es **Sí**, debe inyectar `JevDecisionPort` automáticamente y registrarlo en `public.llm_request_logs`.
