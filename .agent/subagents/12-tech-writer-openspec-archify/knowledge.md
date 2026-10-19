# Base de Conocimiento Evolutiva — Agente 12: Technical Writer, OpenSpec Bipartito, Graphify y Archify

> Lecciones aprendidas específicas de `12-tech-writer-openspec-archify` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Fase 1 — ADRs 001..021 y Trazabilidad Test-First]:** Cada `ADR-001..021` debe vincular explícitamente en su sección 4 (*Verificación Determinista en Tests*) el archivo exacto de `oppytec-backend/tests/architecture/` o `tests/security_redteam/` que impide su regresión en el *Fast/Main Gate*.
- **[Fase 1 — Sinergia Archify + Receipt SHA-256]:** Todo mapa interactivo en `docs/architecture/atlas/*.archify.html` debe compilarse desde su fuente tipada en `sources/*.archify.json` y sellarse con el digest `SHA-256` exacto en `sources/*.receipt.json`, aplicando la regla *"Details in Cards, Not Excessive Edges"* (máximo 16–20 nodos semánticos, alojando invariantes, rutas y tests dentro de `card`) e incluyendo los 3 temas del ADN Visual Legacy (`ocean-blue`, `dark`, `light`).
