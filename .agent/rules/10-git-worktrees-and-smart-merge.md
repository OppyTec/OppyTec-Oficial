# Regla 10: Orquestación en Git Worktrees, Reserva AST y Smart Merge Train
- Referencia: `estrategia_orquestacion_git_worktrees_y_smart_merge_001.md`.
- Cada agente paralelo opera en su propio `Git Worktree` (`.worktrees/wt-<id>`) y reclama sus símbolos AST en `claims_registry.json` (`fcntl.flock`).
- Integración secuencial mediante `git rebase` + `git merge --ff-only` en el *Merge Train* y arbitraje de 4 vías en conflictos de Nivel 5.
