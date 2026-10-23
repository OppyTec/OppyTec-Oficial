# Base de Conocimiento Evolutiva — Agente 11: Especialista en Git Worktrees y Árbitro de Smart Merge

> Lecciones aprendidas específicas de `11-git-worktree-merge-arbiter` para no repetir errores y mejorar cada semana.

- **[Inicialización Paso 0]:** Agente configurado y alineado con las estrategias maestras `_001.md`.
- **[Aislamiento Atómico con fcntl.flock]:** La gestión de concurrencia multi-agente a través de `claims_registry.json` con locks de kernel Linux (`fcntl.flock(LOCK_EX)`) previene eficazmente colisiones en archivos compartidos antes de que ocurra cualquier conflicto de merge en Git.
- **[Merge Train Lineal y Fast-Forward]:** Toda integración a `master` debe respetar la política estricta de `git rebase master` seguido de `git merge --ff-only`. Esto mantiene un árbol de commits determinista, legible y 100% compatible con `git bisect` forense.
- **[Higiene de Worktrees y Claims]:** Al concluir cada fase o ciclo de trabajo paralelo, es obligatorio remover los worktrees de `.worktrees/` (`git worktree remove`) y vaciar los nodos en `claims_registry.json` para evitar claims zombis que bloqueen futuras ejecuciones del arnés.
- **[Guardia Anti-Reward-Hacking Integrada]:** El chequeo de SHA-256 en `scripts/harness.py verify-evals` garantiza que ningún subagente relaje rúbricas o reglas inmutables. Debe ser ejecutado como pre-condición obligatoria en cualquier auditoría o preparación de fase.
