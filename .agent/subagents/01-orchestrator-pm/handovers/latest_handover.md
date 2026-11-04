# Handover: Agente 01 (`01-orchestrator-pm`) — Blindaje de Gobernanza: Prohibición Estricta de npm/yarn y Obligatoriedad de pnpm

## Completed
- **Gobernanza Maestra en `AGENTS.md`**:
  - Incorporada la Regla Inviolable N° 10: `PROHIBICIÓN ESTRICTA Y ABSOLUTA DEL USO DE 'npm' / 'yarn' (OBLIGATORIEDAD DE 'pnpm')`.
  - Establecida como Violación Crítica de Gobernanza de Nivel 1 cualquier ejecución de `npm`, `npx` (salvo vía `pnpm dlx`) o `yarn`.
- **Reglas Inmutables y Meta-Instrucciones**:
  - Actualizado `.agent/rules/00-meta-agent-instructions.md` especificando los gestores de paquetes autorizados: Backend con `uv` (prohibido `pip` directo) y Frontend con `pnpm` (prohibido `npm`/`yarn`).
  - Actualizado `.agent/rules/03-frontend-standards.md` con la directiva explícita de uso exclusivo de `pnpm`.
  - Recalculados y actualizados los hashes SHA-256 en `.agent/evals/eval_hashes.sha256`. Verificación `python scripts/harness.py verify-evals` exitosa al 100% (Cero Reward Hacking).
- **Hard Enforcement Mecánico en `oppytec-frontend`**:
  - Declarado `"packageManager": "pnpm@11.1.1"` en [package.json](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/package.json).
  - Añadido bloqueo de motor en `"engines"`: `"npm": "please-use-pnpm"` y `"pnpm": ">=9.0.0"`.
  - Añadido script `"preinstall"` en [package.json](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/package.json) que valida activamente `process.env.npm_config_user_agent` y aborta inmediatamente con código 1 y mensaje fatal ante cualquier intento de uso de npm o yarn.
  - Creado [.npmrc](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/.npmrc) con `engine-strict=true`.
  - Corregido override inconsistente en [pnpm-workspace.yaml](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/pnpm-workspace.yaml) (braces 3.0.4 inexistente).
- **Verificación y Pruebas**:
  - Verificado el bloqueo estricto con `npm install --dry-run`: bloqueado de inmediato con `npm error code 1` y mensaje de gobernanza.
  - Verificado el funcionamiento normal con `pnpm run typecheck` (`tsc --noEmit` completado exitosamente con código 0).
  - Verificada la ejecución de tests con `pnpm test` (vitest ejecutado limpiamente bajo pnpm).
  - Grafo de arquitectura Graphify sincronizado con éxito (`python scripts/harness.py sync-graph`).

## Friction & Failures
- Se detectó un override espurio en `pnpm-workspace.yaml` que referenciaba `braces@3.0.4` (versión inexistente en npmjs). Fue saneado para permitir la resolución limpia de dependencias en pnpm v11.

## Next Exact Action
- Mantener la vigilancia activa en todos los pipelines CI/CD y solicitudes de agentes para asegurar cumplimiento inmutable de `pnpm` en Frontend y `uv` en Backend.
