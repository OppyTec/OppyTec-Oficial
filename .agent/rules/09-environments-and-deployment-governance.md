# Regla 09: Gobernanza de los 5 Entornos e Invarianza de Artefactos (`SHA-256`)
- Referencia: `.agent/estrategias/estrategia_entornos_y_despliegue_001.md`.
- 5 entornos: `local`, `preview` (`ENV_NAMESPACE`), `ci` (cero internet externo), `staging` (datos anonimizados + Sinkhole) y `production` (Secret Manager + `/docs` oculto).
- Invarianza *Build Once, Deploy Everywhere* en Frontend mediante `/runtime-env.js` validado con Zod.
