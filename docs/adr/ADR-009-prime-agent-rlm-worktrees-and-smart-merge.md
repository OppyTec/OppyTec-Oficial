# ADR-009: Orquestación Multi-Agente con Prime Agent RLM, `Git Worktrees`, Reserva AST (`fcntl.flock`) y *Smart Merge Train*

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_orquestacion_git_worktrees_y_smart_merge_001.md` / `.agent/skills/git_smart_merge/SKILL.md`

---

## 1. Contexto

Cuando múltiples agentes de IA (o desarrolladores trabajando en paralelo mediante **Herdr**) editan simultáneamente el mismo árbol de archivos de un repositorio Git, se producen condiciones de carrera en el sistema de archivos, contaminación cruzada del índice de Git (`git add`), colisiones en números de migración de Alembic y conflictos de fusión destructivos.

## 2. Decisión

Implementar el arnés determinista `scripts/harness.py` basado en el paradigma **Recursive Language Model (RLM)**, aislamiento físico con **`Git Worktrees`**, reserva semántica de nodos AST con bloqueo de kernel (`fcntl.flock`) y una **Cola de Fusión Secuencial (*Smart Merge Train*)**:

1. **Aislamiento Físico por `Git Worktree`:**
   - Ningún agente constructor edita directamente la rama `master`. Cada agente opera en su propio worktree `.worktrees/phase<N>-<agent-id>` sobre su rama dedicada `agent/phase<N>-<agent-id>` con su propio `ENV_NAMESPACE` aislado.
2. **Reserva Atómica de Símbolos AST (`claims_registry.json` + `fcntl.flock`):**
   - Antes de modificar un archivo o símbolo compartido, el agente registra su reclamo atómico mediante `python3 scripts/harness.py claim-ast`, utilizando `fcntl.flock(LOCK_EX)` y reemplazo atómico `os.replace()` para impedir colisiones concurrentes.
3. **Cola de Fusión Secuencial (*Smart Merge Train*):**
   - La integración hacia `master` es estrictamente serie (FIFO):
     1. Verifica candados anti-trampa (`verify-evals`).
     2. Ejecuta `git rebase master` dentro del worktree del agente.
     3. Si hay colisión de número correlativo en Alembic, ejecuta `scripts/db_migration.py rebase`.
     4. Ejecuta el *Fast Gate* (`< 15s`) y el *Main Gate* sobre el código rebasado.
     5. Fusiona a `master` exclusivamente con `git merge --ff-only` para preservar una historia 100% lineal.
4. **Agente Árbitro Fresco de 4 Vías (`11-git-worktree-merge-arbiter`):**
   - Si ocurre un conflicto semántico durante el rebase, ningún agente constructor resuelve su propio conflicto; se invoca al **Agente 11** con contexto limpio recibiendo las 4 piezas de evidencia (`BASE`, `OURS`, `THEIRS` y el contrato OpenSpec).

## 3. Consecuencias

- **Positivas:**
  - Paralelismo real sin pisarse archivos entre los agentes del escuadrón ni en sesiones multi-terminal de Herdr.
  - Historia de Git 100% lineal (`--ff-only`) donde cada commit en `master` está garantizado de pasar los Quality Gates.
- **Negativas / Trade-offs:**
  - Requiere disciplina de ejecución a través de `scripts/harness.py` y `Makefile`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_harness_and_merge_integrity.py`.
- **Invariante Verificada:** Verifica la existencia y funcionamiento de `scripts/harness.py`, la integridad de `.agent/memory/claims_registry.json`, el bloqueo `fcntl.flock` y el candado `SHA-256` sobre `.agent/evals/eval_hashes.sha256`.
