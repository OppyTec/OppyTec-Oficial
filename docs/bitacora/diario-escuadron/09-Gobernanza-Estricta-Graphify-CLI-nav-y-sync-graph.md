# Bitácora 09 — Gobernanza Estricta de Graphify: CLI `nav`, `sync-graph` y Protocolo Obligatorio Pre y Post-Ejecución sin Excepción

> **Fecha:** 2026-10-23  
> **Autor:** Agente 12 (`12-tech-writer-openspec-archify`)  
> **Estado:** Implementado, Verificado y en Producción (`SYNC_APPROVED`)  
> **Hito:** Plan de Mejora de Graphify — Navegación AST Ultraligera y Sincronización Automática Determinista  

---

## 1. Contexto y Mandato del Usuario

Por instrucción formal y estricta del Usuario:
> *"Siempre todos los agentes deben antes de comenzar su trabajo consultar Graphify y al final de la ejecucion de todos los agentes involucrados, actualizarse este, es una regla estricta, obligatoria y sin ninguna excepción, debe hacerse siempre, por favor procede con el plan de mejora".*

Esta directriz elimina de raíz dos problemas críticos en el ecosistema multi-agente:
1. **Sobrecarga de contexto por lectura a ciegas:** Los agentes consumían miles de tokens leyendo archivos de código completos para inferir dependencias o contratos.
2. **Desincronización arquitectónica post-construcción:** Tras implementar nuevas funcionalidades o componentes (frontend, backend, migraciones), el grafo de arquitectura quedaba obsoleto si no se ejecutaba un paso manual de reindexación.

---

## 2. Implementación Técnica en `scripts/harness.py`

Se incorporaron dos nuevos subcomandos CLI de primer nivel en el arnés orquestador:

### A. Subcomando `nav`: Navegación AST Instantánea (< 150 Tokens)
- **Comando:** `python scripts/harness.py nav "<símbolo>"` (opcional: `--legacy` y `--limit N`).
- **Mecanismo:** Invoca `ASTGraphNavigator` desde `.agent/skills/graphify/graph_navigator.py`. Busca coincidencias por `id`, `label` y `path` de forma insensible a mayúsculas/minúsculas.
- **Salida:** JSON compacto y estructurado con el conteo de coincidencias, muestra ordenada de identificadores de nodo y lista acotada de aristas relacionales (`source`, `target`, `relation`).
- **Presupuesto de Tokens:** Estrictamente menor a 150 tokens, permitiendo que cualquier agente mapee con precisión quirúrgica su vecindad de trabajo en milisegundos sin consumir contexto.

### B. Subcomando `sync-graph`: Sincronización Automática Determinista
- **Comando:** `python scripts/harness.py sync-graph`.
- **Mecanismo de Escaneo:**
  1. **Migraciones Alembic (`oppytec-backend/alembic/versions/`):** Escanea e indexa `0001_genesis_public`, `0002_tenant_initial` y la nueva `0003_public_plans_quotas_and_tenant_capacity_overrides`, estableciendo sus relaciones de correlatividad y vinculación con `core:database` y `module:tenancy`.
  2. **Routers FastAPI (`oppytec-backend/src/modules/*/presentation/router.py` y `core/realtime/router.py`):** Indexa los 11 routers REST/WS y los enlaza bidireccionalmente con `app:backend_main` y sus módulos de dominio.
  3. **Componentes y Hooks Frontend React 19:**
     - `LanguageProvider` (`frontend:language_provider`)
     - `useLanguage` (`frontend:use_language`)
     - `LanguageFlagSelector` (`frontend:language_flag_selector`)
     - `CurrencySelector` (`frontend:currency_selector`)
     - `QuotaProgressIndicator` (`frontend:quota_progress_indicator`)
     - `AdminManagementViews` (`frontend:admin_management_views`)
     - `DynamicAdminTable` (`frontend:dynamic_admin_table`)
     - `DynamicAdminForm` (`frontend:dynamic_admin_form`)
  4. **Suites de Verificación Frontend:** Indexa las suites de Vitest (`suite:frontend_admin_views_test`, `suite:frontend_i18n_test`, `suite:frontend_currency_test`, `suite:frontend_env_test`, `suite:frontend_telemetry_test`) y las vincula con sus componentes objetivo.
  5. **Métricas en Vivo:** Recalcula automáticamente `nodes_count` (83), `edges_count` (111), `backend_routers` (11), `alembic_migrations` (3), `verification_suites` (14), manteniendo ordenamiento determinista por ID y registrando el evento inmutable `GRAPHIFY_SYNCED` en `.agent/memory/harness_events.jsonl`.
  6. **Persistencia Espejo:** Actualiza tanto `docs/architecture/graphify/graph.json` como `docs/architecture/graphify/v2_phase6_master_graph.json`.

---

## 3. Actualización de Gobernanza en `AGENTS.md`

Se actualizaron los dos pilares normativos de `AGENTS.md`:
1. **Regla de Oro Inviolable (Punto 6):**
   - **Pre-ejecución:** SIEMPRE, todos los agentes deben antes de comenzar su trabajo consultar Graphify mediante `python scripts/harness.py nav "<símbolo>"` para mapear la vecindad AST relevante (< 150 tokens) antes de leer archivos masivos.
   - **Post-ejecución:** SIEMPRE, al concluir la ejecución de todos los agentes involucrados en cualquier modificación de código, debe actualizarse el grafo mediante `python scripts/harness.py sync-graph` (o delegando al Agente 12). Esta regla es estricta, obligatoria y no admite ninguna excepción.
2. **Protocolo de Inicio de Sesión y Enrutamiento JEV (Paso 4 y Paso 7):**
   - **Paso 4:** Consulta obligatoria de Graphify CLI antes de cualquier lectura extensiva.
   - **Paso 7:** Ejecución mandatoria de `sync-graph` al cierre de cualquier tarea técnica.

*(Nota de Seguridad: `.agent/rules/` y `.agent/evals/` permanecieron 100% inalteradas, manteniendo intacto el hash SHA-256 de anti-reward-hacking).*

---

## 4. Resultados de Verificación y Validación

```bash
# 1. Sincronización del grafo
$ python3 scripts/harness.py sync-graph
🔄 Grafo de Arquitectura Graphify sincronizado con éxito:
   • Nodos totales: 83 (Routers: 11, Migraciones: 3, Suites: 14)
   • Aristas totales: 111
   • Destino: docs/architecture/graphify/graph.json

# 2. Navegación AST rápida de i18n/idioma
$ python3 scripts/harness.py nav "language"
{
  "query": "language",
  "matched_count": 4,
  "sample_matches": [
    "frontend:language_flag_selector",
    "frontend:language_provider",
    "frontend:use_language",
    "suite:frontend_i18n_test"
  ],
  "edges": [ ... 9 aristas compactas ... ]
}

# 3. Navegación AST rápida de vistas de administración
$ python3 scripts/harness.py nav "admin"
{
  "query": "admin",
  "matched_count": 5,
  "sample_matches": [
    "frontend:admin_management_views",
    "frontend:dynamic_admin_form",
    "frontend:dynamic_admin_table",
    "frontend:feature_platform_admin",
    "suite:frontend_admin_views_test"
  ],
  "edges": [ ... 10 aristas compactas ... ]
}

# 4. Verificación de integridad anti-trampa
$ python3 scripts/harness.py verify-evals
✅ Integridad de .agent/rules/ y .agent/evals/ verificada al 100% (Cero Reward Hacking).

# 5. Puertas de arquitectura
$ oppytec-backend/.venv/bin/pytest oppytec-backend/tests/architecture/test_harness_and_merge_integrity.py
2 passed in 0.14s
$ oppytec-backend/.venv/bin/pytest oppytec-backend/tests/architecture/test_openspec_bipartition_and_sync.py
1 passed in 0.12s
```
