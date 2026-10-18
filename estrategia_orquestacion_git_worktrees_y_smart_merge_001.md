# Estrategia Maestra de Orquestación Multi-Agente (Prime Agent RLM), Git Worktrees y Smart Merge Determinista (Versión 001)

> **Documento:** `estrategia_orquestacion_git_worktrees_y_smart_merge_001.md`  
> **Versión:** 001 (Especificación Normativa de Orquestación Paralela, Aislamiento en Git Worktrees, AST Claiming y Resolución Inteligente de Conflictos)  
> **Base Normativa:**  
> - `MASTER-AGENTIC-ENGINEERING-FRAMEWORK.md`  
> - `propuesta_arquitectura_tree_001.md`  
> - `estrategia_migraciones_alembic_001.md`  
> - `estrategia_rbac_y_auditoria_001.md`  
> - `estrategia_testing_calidad_y_seguridad_001.md`  
> - `estrategia_entornos_y_despliegue_001.md`  
> - **Prime Agent (`PrimeIntellect-ai/prime-agent`):** *A Self-Improving RLM Harness* (arXiv:2608.23552) + Arquitectura de Grafos de Fusión Determinista.  
> **Propósito:** Definir la arquitectura de `harness.py` y el motor de **Smart Merge** para que múltiples programadores humanos y múltiples agentes de IA trabajen simultáneamente sobre el mismo código (incluso el mismo archivo) usando **Git Worktrees**, reserva de nodos AST, colas de fusión secuenciales (*Merge Train*) y resolución semántica verificada por *Quality Gates* sin sobrescribir ni romper jamás el proyecto.  
> **Fecha:** Octubre 2026  

---

## 1. Principio Filosófico Rector

> **"El código decide siempre que puede; un modelo (LLM) sólo juzga cuando es estrictamente necesario, y cada juicio del modelo es verificado inmediatamente por código determinista."**

En el desarrollo colaborativo (entre varios programadores humanos, varios agentes autónomos o equipos híbridos), los problemas al hacer `git merge`, `git pull`, `git push` o integrar un Pull Request ocurren por **tres causas**:
1. **Colisión ciega de escritura:** Dos trabajadores editan el mismo archivo sin saber qué parte está tocando el otro.
2. **Resolución de conflictos sin contexto de intención:** Quien hace el merge ve las marcas `<<<<<<< HEAD` y `>>>>>>> branch`, pero desconoce qué regla de negocio o qué test buscaba cumplir cada autor.
3. **Conflictos semánticos silenciosos:** Git fusiona dos ramas automáticamente sin dar error porque se tocaron líneas distintas, pero la combinación rompe tipos (`mypy`/`tsc`), duplica el número de migración de Alembic o rompe un test de integración.

Esta estrategia resuelve las tres causas combinando un **Grafo de Flujo Fijo en Código (`scripts/harness.py`)** con las abstracciones nativas de **Prime Agent (`rlm.spawn`, REPL Python persistente, comunicación directa entre agentes, `/autonomous` y `/refine`)**.

---

## 2. Arquitectura del Grafo de Orquestación y Smart Merge (`harness.py` + Prime Agent)

```mermaid
flowchart TD
    Goal["🎯 Objetivo / PR / git merge<br/>(/goal en Prime Agent o 'make smart-merge')"]
    Orchestrator["🧠 Orquestador Principal (REPL Python)<br/>Contexto como Variable (Cero Context Pollution)"]

    subgraph ParallelWorktrees["1. Ejecución Paralela Aislada (Git Worktrees + AST Claims)"]
        Registry["🔒 Registro de Reserva AST<br/>(.agent/memory/claims_registry.json)<br/>Reclama Funciones/Clases antes de escribir"]
        WT1["🌿 Worktree 1 (branch: wt-1)<br/>ENV_NAMESPACE='wt_1'<br/>Subagente vía rlm.spawn()"]
        WT2["🌿 Worktree 2 (branch: wt-2)<br/>ENV_NAMESPACE='wt_2'<br/>Subagente vía rlm.spawn()"]
        WTN["🌿 Worktree N / Rama Humana<br/>ENV_NAMESPACE='wt_n'<br/>Programador o Subagente"]
        Registry --> WT1 & WT2 & WTN
        WT1 <-->|Comunicación Directa P2P<br/>Acuerdo de Firmas/Contratos| WT2
    end

    subgraph MergeTrain["2. Cola de Fusión Secuencial ('Merge Train Sandbox Worktree')"]
        Queue["🚂 Toma 1 Rama a la vez sobre Base Limpia"]
        Triage["⚡ Clasificador Determinista + Jev (Sistema 1)<br/>¿Hay conflicto textual o de estructura?"]
        CodeResolve["🔧 Resolución 100% por Código:<br/>• Alembic -> db_migration.py rebase<br/>• Lockfiles -> uv lock / pnpm install<br/>• Imports -> AST Union + ruff/eslint"]
        Arbiter["⚖️ Agente Árbitro Fresco (rlm.spawn)<br/>Ventana Limpia + Contexto 4-Vías:<br/>(BASE + OURS + THEIRS + Specs/Tests)"]
        Gate["🛡️ Quality Gate Determinista<br/>(Fast Gate / Main Gate: Exit Code == 0?)"]
        Quarantine["🚨 Cuarentena de Rama + Reporte<br/>(Si falla tras max_retries = 3)"]
    end

    EventLog[("📜 Bitácora Event-Sourced Inmutable<br/>.agent/memory/harness_events.jsonl<br/>(Reconstrucción Total del Estado)")]
    Refine["✨ Prime Agent /refine<br/>Destila el patrón de merge en<br/>.agent/memory/ y skills/"]
    FinalBranch["✅ Rama Fusionada en Verde + Reporte Forense de Merge"]

    Goal --> Orchestrator
    Orchestrator --> ParallelWorktrees
    WT1 & WT2 & WTN --> Queue
    Queue --> Triage
    Triage -->|Alembic / Lockfile / Imports| CodeResolve
    Triage -->|Conflicto de Lógica de Negocio| Arbiter
    Triage -->|Merge Textual Limpio| Gate
    CodeResolve --> Gate
    Arbiter --> Gate
    Gate -->|Fallo (Exit Code != 0): Loop <= 3| Arbiter
    Gate -->|Fallo tras 3 intentos| Quarantine
    Gate -->|Éxito (Exit Code == 0)| Refine
    Refine --> FinalBranch
    Orchestrator & Queue & Gate & Refine -.->|Log con Timestamp y SHA| EventLog
```

---

## 3. Pilares Técnicos del Sistema

### 3.1 Aislamiento Físico mediante Git Worktrees + Reserva Previa de Nodos AST (`AST Claiming`)
Cuando **5 agentes de IA** (o varios programadores) deben trabajar en paralelo sobre el mismo repositorio —e incluso sobre el **mismo archivo**— sin sobrescribirse:

1. **Un Worktree y una Rama por Trabajador:**
   - El arnés nunca permite que dos agentes editen el mismo directorio de trabajo al mismo tiempo.
   - Antes de iniciar, ejecuta:
     ```bash
     git worktree add .worktrees/wt-<id> -b agent/<id>-<slug>
     ```
   - Cada worktree se asocia a su propio `ENV_NAMESPACE="wt_<id>"` (definido en `estrategia_entornos_y_despliegue_001.md`), aislando su esquema de base de datos y prefijo de Redis.
2. **Reserva de Regiones/Símbolos AST en Código (`claims_registry.json`) con Bloqueo Atómico (`fcntl.flock`):**
   - Antes de que cualquier sub-agente escriba una sola línea en un archivo compartido (ej. `src/modules/inventory/application/stock_service.py`), debe reclamar el símbolo AST que va a crear o modificar:
     ```json
     {
       "file": "oppytec-backend/src/modules/inventory/application/stock_service.py",
       "symbol_type": "FunctionDef",
       "symbol_path": "StockService.register_merma",
       "claimed_by": "wt-2",
       "intent": "Implementar validación de umbral de aprobación de merma y registro en Kardex",
       "claimed_at": "2026-10-17T15:00:00Z"
     }
     ```
   - **Serialización Atómica contra Condiciones de Carrera (`ast_claimer.py`):** Cuando 5 sub-agentes lanzados con `rlm.spawn()` intentan reservar símbolos en el mismo milisegundo, `ast_claimer.py` adquiere obligatoriamente un **candado exclusivo a nivel de kernel Linux (`fcntl.flock(lock_fd, fcntl.LOCK_EX)`)** (o un lock distribuido en Redis `SET harness:claims_lock NX EX 5`) y escribe el archivo mediante reemplazo atómico (`tempfile` + `os.replace`), impidiendo lecturas sucias o sobrescrituras de reclamos.
   - **Análisis de Radio de Impacto con `Graphify` (*1-Hop Blast Radius Claiming*):** Antes de confirmar un reclamo en `claims_registry.json`, `ast_claimer.py` consulta en el REPL a `.agent/skills/graphify/graph_navigator.py` (`v2_graph.neighbors(symbol_path, depth=1)`) con costo `0` de tokens LLM para registrar qué funciones/clases llaman o son llamadas por ese símbolo. Si otro agente (`wt-3`) intenta reclamar un nodo vecino acoplado a 1 salto de distancia, el arnés emite una advertencia inmediata para que ambos sub-agentes sincronicen el contrato de la firma por mensajería directa.
   - Si otro agente (`wt-3`) necesita tocar el mismo archivo, el registro le asigna únicamente su propio símbolo (`StockService.run_physical_count`) y bloquea mecánicamente la edición de símbolos reclamados por `wt-2`.
3. **Negociación Directa Agente-a-Agente (Capacidad Nativa de Prime Agent):**
   - Si `wt-3` necesita que un método reclamado por `wt-2` exponga un parámetro adicional, utiliza la mensajería directa entre agentes de **Prime Agent** para acordar el contrato de la firma en vivo antes de emitir su commit.
4. **Desmontaje Seguro de Git Worktrees en Linux (`worktree_manager.py`):**
   - Al finalizar un worktree, antes de ejecutar `git worktree remove --force .worktrees/wt-<id>` y `git worktree prune`, `worktree_manager.py` realiza un barrido preventivo de descriptores abiertos sobre el directorio (`fuser -k .worktrees/wt-<id>` / `lsof`) para terminar procesos huérfanos (LSPs, watchers de Vite o runners de pytest) y garantizar una limpieza 100% libre de errores.

---

### 3.2 El Árbol de Decisión de Merge en 5 Niveles (El Código Decide Primero)
Cuando llega el momento de unir ramas (ya sea de 5 sub-agentes en el *Merge Train* o de 2 programadores humanos haciendo `git pull` / `git merge` / PR), el motor **`SmartMergeEngine`** clasifica cada archivo modificado o en conflicto siguiendo este orden estricto:

| Nivel | Tipo de Conflicto / Archivo | ¿Interviene el LLM? | Acción Automática Determinista |
|---|---|---|---|
| **Nivel 1** | **Rutas Inmutables o Prohibidas Anti-Trampa** (`.agent/rules/*`, `.agent/evals/*`, `tests/architecture/*`, `OppyTec-Legacy/*`, `.env`) | **NO (0 tokens)** | **Jev (Sistema 1)** y el verificador `SHA-256` de `harness.py` abortan inmediatamente la fusión y revierten cualquier intento de un agente constructor de alterar reglas o pruebas de evaluación (*Reward Hacking*). |
| **Nivel 2** | **Colisión de Migraciones Alembic** (`alembic/versions/NNNN_*.py`) | **NO (0 tokens)** | Invoca automáticamente `python scripts/db_migration.py rebase`: detecta que dos ramas usaron el mismo número `NNNN`, renumera la rama entrante a `NNNN+1` y enlaza su `down_revision` a `NNNN`. |
| **Nivel 3** | **Archivos de Lock de Dependencias** (`uv.lock`, `pnpm-lock.yaml`) | **NO (0 tokens)** | Descarta el conflicto textual de lockfile, fusiona `pyproject.toml` / `package.json` y regenera el lockfile ejecutando `uv lock` o `pnpm install --lockfile-only`. |
| **Nivel 4** | **Colisión de Imports, Listas de Exportación o Diccionarios `i18n`** (`__init__.py`, registro de routers, `locales/{es,en}/*.json`) | **NO (0 tokens)** | Parsea ambos árboles AST o JSONs de idiomas (`i18n_tool.py` con `fcntl.flock`), calcula la unión ordenada sin duplicados de los nodos `Import` / `ImportFrom` / llaves `i18n` verificando paridad 1:1 `es <-> en`, y aplica `ruff check --select I --fix` o `eslint --fix`. |
| **Nivel 5** | **Conflicto Real de Lógica de Negocio** (Textual en la misma función o Semántico al fallar el Quality Gate) | **SÍ (Agente Árbitro Fresco vía `rlm.spawn`)** | Se instancia un **Agente Árbitro con ventana de contexto limpia** que recibe el **Paquete Semántico de 4 Vías**, sintetiza la solución y la somete al bucle de pruebas. |

---

### 3.3 El "Agente Árbitro Fresco" y el Paquete de Evidencia de 4 Vías (*4-Way Semantic Merge*)
Cuando dos programadores o dos agentes modifican la misma línea o función (Nivel 5), el arnés **nunca** le pide al mismo agente cansado que llevaba 40 turnos programando que resuelva el conflicto. En su lugar, usa `rlm.spawn(...)` en **Prime Agent** para crear un **Agente Árbitro Fresco (*Fresh Context Window*)** pasándole como variables de Python en el REPL estas **4 fuentes de verdad**:

```plaintext
┌────────────────────────────────────────────────────────────────────────────┐
│            PAQUETE DE EVIDENCIA DE 4 VÍAS PARA EL AGENTE ÁRBITRO           │
├────────────────────────────────────────────────────────────────────────────┤
│ 1. BASE (Ancestro Común):                                                  │
│    - Código exacto en `git merge-base OURS THEIRS` antes de separarse.     │
│                                                                            │
│ 2. OURS (Rama Base / Programador 1):                                       │
│    - Diff AST de OURS + Mensajes de Commit + Intención declarada           │
│    - Tests unitarios/integración añadidos o modificados por OURS.          │
│                                                                            │
│ 3. THEIRS (Rama Entrante / Programador 2):                                 │
│    - Diff AST de THEIRS + Mensajes de Commit + Intención declarada         │
│    - Tests unitarios/integración añadidos o modificados por THEIRS.        │
│                                                                            │
│ 4. CONTRATO NORMATIVO (OpenSpec + Reglas):                                 │
│    - Sección relevante de `specs/` + `.agent/rules/` + Lecciones previas   │
│      de `.agent/memory/trajectory_lessons.md`.                             │
└────────────────────────────────────────────────────────────────────────────┘
```

#### Reglas de Razonamiento del Agente Árbitro:
1. **Preservación de Doble Intención:** El código resultante debe satisfacer simultáneamente los invariantes y tests de `OURS` y los invariantes y tests de `THEIRS`. Está prohibido "resolver" un conflicto borrando silenciosamente la funcionalidad de uno de los dos programadores.
2. **Verificación Empírica Inmediata (El Bucle del Quality Gate):**
   - Una vez que el Agente Árbitro escribe el código unificado en el worktree de integración (`.worktrees/wt-merge-train`), el código del arnés ejecuta automáticamente:
     - `ruff check` + `mypy --strict` (o `eslint` + `tsc --noEmit`).
     - Todos los tests de `tests/architecture/`.
     - **Todos los tests de la Rama `OURS` + Todos los tests de la Rama `THEIRS`**.
   - Si algún test o linter falla (`Exit Code != 0`), el arnés le devuelve el traceback exacto al Agente Árbitro y repite el ciclo (máximo `3` intentos).
   - Si al tercer intento no logra `Exit Code 0`, el arnés **aborta limpiamente**, deja las ramas originales intactas, pone esa fusión en estado `QUARANTINED` y entrega un diagnóstico detallado para revisión humana.

---

### 3.4 Cola de Fusión Secuencial (*Merge Train*) para Eliminar Conflictos Semánticos Silenciosos
Incluso cuando `git merge` reporta **"0 conflictos de texto"**, dos ramas pueden romperse mutuamente si una cambió el tipo de retorno de un servicio y la otra lo consume con el tipo antiguo.

Por ello, `harness.py` procesa las ramas en una **Cola Secuencial Estricta con Historial Lineal (*Rebase + Fast-Forward Merge Train*)**:
1. Parte de `main` en `.worktrees/wt-merge-train`.
2. Toma `Rama 1`, ejecuta `git rebase main` y corre **Fast Gate + Tests de Integración del módulo**. Si pasa (`Exit Code 0`), avanza el puntero acumulado a `M1` mediante `git merge --ff-only` (evitando *merge bubbles* redundantes en el historial de Git).
3. Toma `Rama 2` y ejecuta `git rebase M1` dentro del sandbox de integración, seguido de **Fast Gate + Tests de `Rama 1` y `Rama 2`**:
   - Si hay conflicto durante el rebase o si falla un test por incompatibilidad semántica entre `Rama 1` y `Rama 2`, se activa el **Agente Árbitro Fresco** para armonizar las firmas/llamadas entre ambas ramas hasta que los tests de ambas pasen en verde, completando luego el `--ff-only` hacia `M2`.
4. Repite hasta integrar la `Rama N` y entrega **una única rama final con historial 100% lineal y certificado + el Reporte Forense de Fusión**.

---

## 4. Integración Profunda con `Prime Agent` (`PrimeIntellect-ai/prime-agent`)

Aprovechamos todas las capacidades de arquitectura de **Prime Agent** dentro de OppyTec v2.0:

### 4.1 *Prompt-as-a-Variable* en el REPL Python Persistente + Navegación AST con `Graphify`
- **Prohibición de Volcar Archivos o Grafos Crudos al Prompt:** En lugar de leer 30 archivos del repositorio o hacer `read("graph.json")` (lo que contaminaría decenas de miles de tokens), `harness.py` y los sub-agentes consultan el grafo AST a través del paquete ejecutable **`.agent/skills/graphify/graph_navigator.py`** directamente como variables de Python en el REPL:
  - **`LegacyGraph` (Solo Lectura sobre `OppyTec-Legacy/grafos-legacy/`):** Permite responder en `< 10ms` y `< 150 tokens` qué hacía una función o modelo en Legacy sin abrir archivos viejos.
  - **`V2Graph` (Vivo sobre `docs/architecture/graphify/graph.json`, filtrado por `.graphifyignore`):** Entrega únicamente la vecindad exacta (`callers`, `callees`, `tests`) de los símbolos en conflicto para el paquete de 4 vías del Agente Árbitro, y se actualiza incrementalmente (vía `ast_hash` en `manifest.json`) tras cada paso exitoso del *Merge Train*.
  ```python
  # Ejemplo dentro del REPL persistente de Prime Agent
  from skills.git_smart_merge import WorktreeHarness, ConflictExtractor
  from skills.graphify import v2_graph

  wt = WorktreeHarness(base_branch="main")
  conflicts = ConflictExtractor.inspect_branches("feature/inventory-v2", "feature/recipes-v2")
  impact_subgraph = v2_graph.get_impact_subgraph(conflicts.symbol_names, depth=1)

  # Solo el nodo AST en conflicto + su vecindad Graphify de 1 salto se envían al sub-agente árbitro:
  resolution = rlm.spawn(
      subagent="merge-arbiter",
      prompt_vars={
          "conflict_ast": conflicts.only_colliding_functions(),
          "graph_neighbors": impact_subgraph,
          "specs": conflicts.related_specs(),
      }
  )
  ```

### 4.2 Configuración de Compacción Temprana (`compaction.thresholdPercent = 75%`)
- Aunque el valor por defecto de Prime Agent en `/settings` es `95%`, en tareas de ingeniería de alta precisión y resolución de conflictos esperar al `95%` aumenta el riesgo de *attention drift* (*Lost in the Middle*).
- En OppyTec v2.0 configuramos **`compaction.thresholdPercent: 75`** como override de proyecto para garantizar que el agente compacte su historial manteniendo siempre libre al menos el 25% de la ventana efectiva para razonamiento profundo y respetando las restricciones negativas de `.agent/rules/`.

### 4.3 Continuidad por Demonio (`prime-agent attach`), `/goal`, `/heartbeat` y `/autonomous`
- **Objetivos Persistentes (`/goal`):** Al iniciar una fase o migración de módulo de `specs/06-IMPLEMENTATION-PLAN.md`, se fija en `/goal` con su checklist de *Definition of Done*.
- **Modo Autónomo Acotado (`/autonomous`):** Se configura con límites estrictos de turnos, tokens y tiempo, vinculando el *user-defined quality gate* de Prime Agent a `make fast-gate` y `make main-gate`. Tal como establece la documentación de Prime Agent, alcanzar el límite de presupuesto **jamás se interpreta como éxito**: sólo un `Exit Code 0` del Quality Gate aprueba el paso.
- **Auto-Mejora Continua (`/refine`):** Tras cada resolución exitosa en el *Merge Train*, se ejecuta `/refine` para destilar la lección aprendida en `.agent/memory/trajectory_lessons.md` y `.agent/skills/learned-patterns/` con snapshots reversibles, sin alterar jamás las reglas inmutables de `.agent/rules/`.

### 4.4 Seguridad de Ejecución de Prime Agent
- Atendiendo a la advertencia oficial de seguridad de Prime Agent (*"Its worker and kernel processes improve lifecycle isolation and recovery; they are not a security sandbox"*):
  1. Prime Agent se ejecuta siempre dentro del entorno contenerizado de desarrollo o sobre **Git Worktrees desechables** (`.worktrees/*`).
  2. El middleware **Jev (Sistema 1)** audita cada comando shell/Python antes de su ejecución, bloqueando cualquier intento de acceder a rutas fuera del repositorio, modificar `.agent/rules/`, alterar `OppyTec-Legacy/` o leer credenciales fuera del `.env` de desarrollo.

---

## 5. Flujo de Uso para Programadores Humanos (`git pull`, `git merge`, `git push` y PRs)

Para que cualquier programador del equipo aproveche este motor sin complejidad:

1. **Sincronizar su rama local con `main` de forma inteligente (`make smart-pull`):**
   - Crea un worktree temporal en `.worktrees/wt-human-sync` (sin tocar los archivos abiertos en el IDE del programador).
   - Prueba el merge con `origin/main`.
   - Si hay colisión de migración Alembic (`0004`), la renumera automáticamente a `0005`.
   - Si hay conflicto de código, el Agente Árbitro propone la fusión, corre `ruff`, `mypy`, `eslint`, `tsc` y `pytest`, y cuando todo está en `0 errores`, actualiza la rama del programador y muestra el reporte.
2. **Integrar dos ramas de funcionalidades (`make smart-merge SOURCE=feature/a TARGET=feature/b`):**
   - Ejecuta el *Merge Train* completo entre ambas ramas y entrega la rama unificada y certificada por los Quality Gates.

---

## 6. Bitácora Event-Sourced Inmutable (`.agent/memory/harness_events.jsonl`)

Siguiendo la regla de oro del diseño de arneses (*"Every action is logged with its time, so the state can always be rebuilt"*), cada paso del orquestador y del motor de merge escribe un registro JSON por línea en `.agent/memory/harness_events.jsonl`:

```json
{"ts": "2026-10-17T16:10:01.120Z", "run_id": "run_89a1", "event": "WORKTREE_CREATED", "worker": "wt-1", "branch": "agent/wt-1-inventory", "base_sha": "a4f91c2"}
{"ts": "2026-10-17T16:10:02.450Z", "run_id": "run_89a1", "event": "AST_CLAIMED", "worker": "wt-1", "file": "src/modules/inventory/application/stock_service.py", "symbol": "StockService.register_entry"}
{"ts": "2026-10-17T16:14:20.005Z", "run_id": "run_89a1", "event": "MERGE_TRAIN_STEP", "branch": "agent/wt-2-recipes", "conflict_tier": 5, "arbiter_spawned": true}
{"ts": "2026-10-17T16:14:48.910Z", "run_id": "run_89a1", "event": "QUALITY_GATE_PASSED", "gate": "fast_gate", "exit_code": 0, "result_sha": "f82b09e"}
```

Gracias a este registro y a los hashes SHA de Git, el comando `python scripts/harness.py rebuild --run-id run_89a1` o `rollback` puede reconstruir o revertir el estado exacto del repositorio a cualquier segundo.

---

## 7. Artefactos a Construir en el Proyecto (Nombres, Rutas y Contratos)

| # | Artefacto | Ruta Exacta en el Proyecto | Propósito |
|---|---|---|---|
| **1** | **ADR de Orquestación y Smart Merge** | `docs/adr/ADR-009-prime-agent-rlm-worktrees-and-smart-merge.md` | Documenta la arquitectura de Git Worktrees, AST Claiming, Merge Train y Prime Agent RLM. |
| **2** | **Contract Spec (OpenSpec)** | `specs/engineering-code/multi-agent-git-harness.code.spec.md` | Contrato formal del esquema de `claims_registry.json`, `harness_events.jsonl`, paquete de 4 vías del Agente Árbitro y formato del Reporte de Merge. |
| **3** | **Regla Agéntica Inmutable** | `.agent/rules/10-git-worktrees-and-smart-merge.md` | Obliga a usar Git Worktrees para trabajo paralelo, registrar claims AST antes de editar archivos compartidos y pasar por el Merge Train. |
| **4** | **Skill Ejecutable en Python (Prime Agent)** | `.agent/skills/git_smart_merge/` (`SKILL.md`, `__init__.py`, `worktree_manager.py`, `ast_claimer.py`, `merge_train.py`, `conflict_arbiter.py`) | Paquete Python importable desde el REPL de Prime Agent y ejecutable desde CLI por los programadores humanos. |
| **5** | **Blueprint de Sub-Agente Árbitro** | `.agent/subagents/merge-arbiter.md` | Especificación dedicada para el sub-agente fresco que resuelve conflictos de Nivel 5 con el contexto de 4 vías. |
| **6** | **Orquestador CLI Principal** | `scripts/harness.py` (en la raíz del monorepo) | Punto de entrada para `harness.py spawn`, `harness.py merge`, `harness.py train` y `harness.py rebuild`. |
| **7** | **Quality Gate del Arnés** | `oppytec-backend/tests/architecture/test_harness_and_merge_integrity.py` | Verifica que no queden marcas de conflicto (`<<<<<<<`), que `claims_registry.json` no tenga colisiones activas y que el historial de Git y Alembic esté limpio. |
