# Plan Maestro y Framework de Ingeniería Agéntica para OppyTec

> **Documento:** Marco de Herramientas, Gobernanza de Contexto y Control de Calidad Agéntica  
> **Propósito:** Prevenir alucinaciones, roturas de arquitectura y degradación del código durante la refactorización de OppyTec v2.0  
> **Fecha:** Octubre 2026  
> **Estado:** Documento Normativo Activo  

---

## 1. Análisis Crítico del Diagnóstico Previo

El diagnóstico que recibiste de Gemini contiene una **verdad técnica fundamental en el desarrollo guiado por Inteligencia Artificial**:

> *"Más herramientas no significan mejor código; saturan la ventana de contexto (*context pollution*), aumentan la latencia/costo de tokens y provocan que el modelo sufra de dispersión de atención (*attention drift*), ignorando las restricciones críticas."*

### 1.1 ¿Por qué fallan los agentes cuando se les satura?
Los Modelos de Lenguaje (LLMs) procesan el contexto mediante mecanismos de atención (*self-attention*). Cuando un agente recibe 10 herramientas simultáneas, reglas desordenadas y transcripciones completas de repositorios:
1. **Pérdida de Restricciones Negativas:** Si el prompt tiene miles de líneas de contexto irrelevante, las prohibiciones explícitas (ej. *"Nunca uses `Any`"* o *"No toques `OppyTec-Legacy`"*) se diluyen en la zona media del contexto (*Lost in the Middle*).
2. **Uso Erróneo de Herramientas:** El agente intenta ejecutar herramientas accesorias o fuera de fase (ej. correr ingeniería inversa cuando sólo debe escribir un test unitario).
3. **Alucinación de Arquitectura:** Al no contar con validadores deterministas locales (linters mecánicos que fallen con código de salida distinto de 0), el LLM asume que su código es correcto si "se lee bien".

---

## 2. Auditoría Herramienta por Herramienta: ¿Sirve, Sobra o Falta?

A continuación se evalúa cada herramienta discutida, su viabilidad para OppyTec y su impacto en la calidad del software.

### 2.1 Herramientas Evaluadas

| Herramienta | Función Propuesta | Veredicto para OppyTec | Justificación Técnica y Riesgo de Contexto |
|---|---|---|---|
| **OpenSpec** | Especificación y Contratos (*Spec-Driven Development*). | **Indispensable (Tier 1)** | Es exactamente lo que ya se consolidó en la carpeta `specs/`. Obliga al agente a trabajar sobre contratos cerrados (endpoints, esquemas Pydantic/Zod, flujos de datos) antes de generar código. |
| **Archify** | Modelado y validación de topología de arquitectura en JSON/Mermaid. | **Muy Útil (Tier 2)** | Permite que el agente "vea" los límites entre capas (Dominio vs Aplicación vs Infraestructura) y la interacción multi-tenant sin tener que parsear cientos de archivos. |
| **security-audit-skill** | Puerta de calidad para OWASP, inyecciones, secretos y XSS. | **Indispensable (Tier 1)** | Vital en OppyTec. De hecho, en `OppyTec-Legacy` la auditoría ya detectó fallos XSS en plantillas (`var-in-href`). Esta habilidad debe ejecutarse como paso obligatorio antes de cada PR o commit. |
| **Graphify** | Grafo de conocimiento de dependencias de código (AST / llamadas). | **Muy Útil / Selectivo (Tier 2)** | OppyTec cuenta con decenas de módulos en Backend y Frontend. Graphify permite responder *"¿Qué rutas y modelos se ven afectados si modifico `registro_stock`?"* consultando el grafo en lugar de inyectar 50 archivos en el prompt. |
| **Herdr** | Orquestación multi-agente y supervisión de enjambres autónomos. | **Situacional / Reemplazado por Prime Agent (Tier 3)** | Si el desarrollo lo lideras tú interactuando con el agente en el IDE (pair-programming), Herdr agrega sobrecarga innecesaria. Para ejecución autónoma de largo alcance, **Prime Agent** ofrece una arquitectura superior. |
| **Prime Agent** (`PrimeIntellect-ai/prime-agent`) | *Self-Improving RLM Harness*: Entorno de ejecución recursivo (IPython REPL persistente) y arnés continuo auto-mejorable (`rlm.harness` / `/refine`). | **Altamente Recomendado / Evolución de Arnés (Tier 1-2)** | Ataca de raíz el problema de *context pollution* de la Sección 1:1) **RLM (Recursive Language Model):** trata el contexto como una variable programable en Python y delega subtareas a sub-agentes recursivos sin inflar la ventana de atención principal. 2) **Continual Harness:** permite hacer CRUD sobre sus propias `skills`, `memories` y `rules` en disco a partir de trayectorias exitosas (`/refine`), aprendiendo de los fallos en los Quality Gates. |
| **Jev** (TypeSafe AI) | Modelo de Decisión y Control *Sistema 1* (no generativo): evalúa estados y devuelve salidas tipadas (`Choice`, `Score`, `Noul/Boolean`) con confianza calibrada. | **Muy Recomendado / Clave en Guardrails (Tier 1-2)** | Resuelve el problema del costo y lentitud de los agentes: en lugar de llamar a un LLM generativo pesado para decidir si una herramienta es segura o clasificar un paso, Jev opera en 70-500 ms a un costo 400x menor, actuando como filtro de seguridad y enrutador antes de mutar código. |
| **Obsidian** | Base de conocimiento personal en Markdown. | **SOBRA en el pipeline del agente** | Obsidian es una herramienta de productividad humana. Los agentes no deben depender de tus notas privadas ni de vaults locales. Toda decisión y contexto del sistema debe residir en el repositorio Git (`specs/`, `docs/adr/`, `.agent/rules/`). |
| **REA (Reverse Engineer Anything)** | Deconstrucción e ingeniería inversa de binarios/código. | **SOBRA para el ciclo diario (Útil solo como tarea puntual)** | En OppyTec no tenemos binarios propietarios ni código ofuscado. Tenemos código Python y TypeScript legible en `OppyTec-Legacy`. Solo tiene sentido como script de un solo uso para extraer esquemas antiguos si faltara documentación, nunca como herramienta activa permanente. |

---

### 2.2 Las Piezas Críticas que FALTABAN (El Lado Determinista + Arnés Auto-Mejorable)

El diagnóstico acertó de lleno en lo que le falta a la mayoría de los desarrollos con IA: **Restricciones Deterministas** combinadas con una **Gestión Programática del Contexto**. Un LLM es probabilístico; la calidad de ingeniería exige herramientas que no admitan discusión y un arnés que aprenda de los errores sin contaminar el prompt base:

```mermaid
flowchart LR
    subgraph Cognitiva["Capa Cognitiva Dual y RLM (Sistema 1 + Sistema 2)"]
        Spec["OpenSpec (Contratos)"]
        Rules[".agent/rules (Directrices)"]
        Graph["Graphify (Navegación AST)"]
        Jev["Jev / TypeSafe AI (Decisiones Sistema 1: Guardrails, Triage, Routing)"]
        Prime["Prime Agent (RLM Harness: Contexto como Variable + Sub-Agentes + /refine)"]
        LLM["Frontier LLMs (Razonamiento Sistema 2: Generación)"]
    end

    subgraph Determinista["Quality Gates Deterministas (No Negociables)"]
        Linter["Ruff / ESLint (Sintaxis y Estilo)"]
        TypeCheck["Mypy / TS Strict (Cero 'any')"]
        ArchLinter["pytest-archon / import-linter (Clean Architecture)"]
        SecCheck["Trivy / Gitleaks / Semgrep (Seguridad)"]
        ContractTest["Schemathesis (Fuzzing OpenAPI)"]
    end

    Jev -->|Valida Tool-Call y Routing| Prime
    Prime <-->|Ejecución REPL y Delegación RLM| LLM
    LLM -->|Genera Código| Determinista
    Determinista -->|Fallo: Devuelve error exacto| Prime
    Prime -->|"/refine" (Destila aprendizaje en .agent/)| Rules
    Determinista -->|Éxito (Exit Code 0)| Commit["Aprobado para Producción"]
```

#### 1. Linters de Arquitectura (`import-linter` o `pytest-archon` para Python, `dependency-cruiser` para TS)
- **Por qué es crítico:** Los agentes tienden a acoplar capas por conveniencia (ej. importar una sesión de base de datos dentro de un componente de interfaz o un schema de FastAPI dentro del modelo de dominio).
- **Cómo actúa:** Un test automatizado que falla si `src.domain` importa de `src.infrastructure` o `src.api`. El agente no puede "argumentar": debe refactorizar hasta que el test pase.

#### 2. Type Checkers Estrictos (`mypy --strict` y TypeScript con `noImplicitAny: true`)
- **Por qué es crítico:** Un agente puede generar código sintácticamente válido pero con tipos ambiguos (`dict[str, Any]` o `any`), rompiendo la previsibilidad y autocompletado en producción.

#### 3. Architecture Decision Records (ADRs en `docs/adr/`)
- **Por qué es crítico:** Evita el "olvido histórico" y la regresión. Si en el ADR-002 se documentó *"Usamos esquemas dinámicos de PostgreSQL por tenant con `SET LOCAL search_path`"*, ningún agente futuro propondrá cambiarlo a una columna `tenant_id` en cada tabla sin una justificación de negocio formal.

#### 4. Validación de Contrato API en Vivo (`schemathesis` o `spectral`)
- **Por qué es crítico:** Fuzzing automático sobre el esquema OpenAPI generado por FastAPI para garantizar que no existan discrepancias entre los modelos documentados en `specs/05-DATABASE-SCHEMA.md` y las respuestas HTTP reales.

#### 5. Detección de Secretos y Vulnerabilidades Locales (`gitleaks` y `trivy`)
- **Por qué es crítico:** Evita que credenciales de pruebas, API keys de Gemini o URLs de bases de datos queden registradas en el historial de Git.

#### 6. Modelo de Decisión y Guardrail Rápido (`Jev` - TypeSafe AI)
- **Por qué es crítico:** En flujos agénticos, verificar si una acción del agente es segura o clasificar la intención no debe requerir una llamada lenta y cara de 10 segundos a un LLM generativo gigante. Jev actúa como un evaluador "Sistema 1" (rápido, determinista e intuitivo) que devuelve decisiones tipadas (`Choice`, `Score`, `Noul/Boolean`) con puntaje de confianza en milisegundos.

#### 7. Arnés RLM Auto-Mejorable (`Prime Agent` - PrimeIntellect-ai)
- **Por qué es crítico:** Resuelve los dos mayores cuellos de botella del desarrollo agéntico en proyectos grandes como OppyTec:
  1. **Contexto como Variable (RLM - *Recursive Language Models*):** En lugar de volcar archivos crudos al prompt (causando *attention drift*), el agente manipula el contexto programáticamente dentro de un REPL IPython persistente y lanza sub-agentes recursivos aislados para tareas acotadas (ej. migrar un módulo de inventario o escribir tests de un endpoint), devolviendo solo el resultado limpio al agente raíz.
  2. **Continual Harness (`/refine` y CRUD sobre el propio arnés):** Cuando el agente resuelve un problema complejo o corrige un error detectado por los *Quality Gates* (ej. un patrón específico de SQLAlchemy 2 Async con `search_path` multi-tenant), puede ejecutar operaciones CRUD sobre su estado en disco (`skills`, `memories`, `subagent blueprints`) para consolidar esa experiencia como una habilidad reutilizable sin inflar el prompt del sistema base.

---

## 3. Matriz Maestra del Ecosistema de Herramientas Recomendado

Para que el sistema sea profesional, robusto y eficiente en tokens, este es el ecosistema depurado:

| Categoría | Herramienta Recomendada | Propósito Concreto | ¿Activa en Prompt? | Momento de Uso |
|---|---|---|---|---|
| **Especificación (SDD)** | `specs/` (Markdown con OpenSpec) | Contrato de producto, endpoints, esquemas y DoD. | Sí (sólo la spec relevante a la tarea) | Fase 1 (Antes de codificar) |
| **Gobernanza y Reglas** | `.agent/rules/` y `AGENTS.md` | Restricciones negativas, estilo, convenciones y límites. | Sí (modularmente según contexto) | En todo momento |
| **Memoria de Decisiones** | `docs/adr/` (ADRs) | Registro inmutable de decisiones de arquitectura tomadas. | Sí (en consultas arquitectónicas) | Al decidir cambios estructurales |
| **Arnés y Orquestación RLM** | `Prime Agent` (`prime-agent`) | Gestión programática del contexto (REPL), delegación recursiva de sub-agentes y auto-mejora continua (`/refine`). | Sí (como runtime / arnés de ejecución) | Tareas multi-archivo, refactorización de fases y aprendizaje post-tarea |
| **Guardrails de Decisión (Sistema 1)** | `Jev` (TypeSafe AI) | Evaluación de seguridad de tool-calls, enrutamiento rápido y triage tipado (Choice/Score/Noul). | En runtime / Middleware agéntico | Antes de ejecutar mutaciones |
| **Exploración de Código** | `Graphify` | Grafo de dependencias y llamadas sin saturar tokens. | Bajo demanda (query específica) | Al analizar impacto en repos grandes |
| **Topología Estructural** | `Archify` / Diagramas Mermaid en specs | Vista de componentes y boundaries. | Bajo demanda | Al diseñar nuevos módulos |
| **Verificación Sintáctica** | `Ruff` (Python) + `ESLint` / `Prettier` (TS) | Formateo y corrección automática inmediata. | No (ejecución CLI determinista) | En cada guardado / pre-commit |
| **Tipado Estricto** | `mypy --strict` + `tsc --noEmit` | Garantizar cero `any` y contratos de tipos completos. | No (ejecución CLI determinista) | Pre-commit y CI |
| **Linter de Arquitectura** | `pytest-archon` + `dependency-cruiser` | Prevenir dependencias circulares y violaciones de capas. | No (ejecución CLI determinista) | Suite de tests |
| **Auditoría de Seguridad** | `security-audit-skill` + `gitleaks` + `semgrep` | Detección de secretos, XSS, SQLi y CVEs. | Al cierre de fase | Pre-commit / Quality Gate |
| **Testing de Contratos** | `schemathesis` + `pytest` + `vitest` | Pruebas de integración y cumplimiento de contratos API. | No (ejecución CLI determinista) | Validación de fases |

---

## 4. El Ciclo de Vida Agéntico en 4 Fases (+ Refinamiento Continuo)

Para desarrollar sin roturas, todo agente de IA (y desarrollador humano) en OppyTec debe ceñirse al siguiente pipeline:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PIPELINE AGÉNTICO CON RLM HARNESS                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

 [1. ESPECIFICACIÓN] ──▶ [2. VALIDACIÓN] ──▶ [3. CONSTRUCCIÓN RLM] ──▶ [4. QUALITY GATE] ──▶ [5. REFINE]
    (OpenSpec)            (Archify/ADRs)      (Prime Agent + Rules)     (Linters + Tests)    (Auto-Mejora)
         │                       │                      │                       │                  │
         ▼                       ▼                      ▼                       ▼                  ▼
 - Leer o redactar spec  - Verificar límites  - Contexto como variable  - Ruff & Mypy        - Destilar
 - Validar inputs/out    - Consultar ADRs     - Delegar subtareas a     - Vitest / Pytest      trayectoria
 - Acordar DoD           - Triage con Jev       sub-agentes aislados    - pytest-archon        en skills/
                                              - Consultar Graphify      - Security Audit       y memory/
         │                       │                      │                       │                  │
         └───────────────────────┴──────────────────────┴───────────────────────┴──────────────────┘
                                                        │
                                               ¿Falla algún check?
                                                  ├─ SI ──▶ Revertir / Corregir en REPL
                                                  └─ NO ──▶ Ejecutar /refine y Aprobar PR
```

### Fase 1: Especificación y Contratos (*Spec First*)
- **Regla:** Ningún agente escribe una sola línea de código en `src/` sin antes tener la especificación aprobada en `specs/`.
- **Salida esperada:** Esquemas de entrada y salida (Pydantic / Zod), endpoints exactos, comportamiento ante errores y criterios de aceptación verificables.

### Fase 2: Arquitectura y Límites
- **Regla:** Verificar contra `specs/02-TRD.md`, `specs/05-DATABASE-SCHEMA.md` y los ADRs existentes.
- **Salida esperada:** Identificación clara de qué módulos se modifican y verificación de que no se introducen dependencias circulares ni violaciones de esquemas multi-tenant.

### Fase 3: Construcción Guiada con RLM (*Prime Agent*)
- **Regla:** El agente opera bajo las reglas de `.agent/rules/` y los principios de **Prime Agent**:
  - **Cero contaminación de contexto:** En vez de volcar archivos masivos al prompt principal, usa el entorno programático (REPL) o sub-agentes recursivos dedicados por subtarea.
  - **Mutaciones quirúrgicas:** No reescribe módulos completos cuando solo necesita editar una función; `Jev` valida que las llamadas a herramientas no violen restricciones.
  - **Navegación por grafo:** Si necesita comprender un impacto indirecto, consulta `Graphify` en lugar de leer el repositorio entero.

### Fase 4: Quality Gate Determinista y Refinamiento Continuo (`/refine`)
- **Regla:** La tarea no se considera "Terminada" porque el agente diga que está lista; se considera terminada cuando los comandos deterministas devuelven código `0`:
  1. `ruff check .` && `mypy src/` (Backend en verde)
  2. `pnpm lint` && `pnpm tsc --noEmit` (Frontend en verde)
  3. `pytest` (Tests de dominio y arquitectura pasando)
  4. Auditoría de seguridad sin hallazgos bloqueantes.
  5. **Destilación de Aprendizaje (`Prime Agent /refine`):** Si durante la fase se resolvió un problema no trivial o se descubrió un caso borde de OppyTec, el arnés actualiza de forma controlada `.agent/skills/` o `.agent/memory/` para que ninguna sesión futura repita el mismo error.

---

## 5. Estructura Canónica de Reglas y Continual Harness para OppyTec (`.agent/`)

Para desacoplar el contexto, no sobrecargar la memoria de trabajo y permitir la auto-mejora continua inspirada en **Prime Agent (`rlm.harness`)**, la carpeta `.agent/` se estructura de forma modular con permisos diferenciados (Inmutable vs. Auto-Mejorable por CRUD):

```plaintext
.agent/
├── estrategias/                                        # [LAS 16 ESTRATEGIAS MAESTRAS DE REFACTORIZACIÓN (_001.md)]
│   └── estrategia_*_001.md                             # Diseño normativo profundo de cada subsistema de OppyTec v2.0
├── rules/                                              # [INMUTABLE POR EL AGENTE - Solo lectura en ejecución normal]
│   ├── 00-meta-agent-instructions.md                   # Prioridad de lectura, protocolo RLM y límites de autonomía
│   ├── 01-architecture-boundaries.md                   # Clean Architecture, separación dominio/infra, multi-tenant schemas
│   ├── 02-backend-standards.md                         # FastAPI, Pydantic v2, SQLAlchemy 2 Async, Zero-Any, Pydantic Settings
│   ├── 03-frontend-standards.md                        # React 19, TypeScript estricto, TanStack Query v5, Zod, Design System
│   ├── 04-security-guardrails.md                       # Zero-Trust, Magic Bytes, sanitización XSS, tokens JWT, no-hardcode
│   ├── 05-testing-and-dod.md                           # Co-Creación 1:1 de tests, cobertura >= 85%, Quality Gates en 3 niveles
│   ├── 06-alembic-and-schema-governance.md             # Migraciones correlativas NNNN_<public|tenant>, cero merge_heads
│   ├── 07-rbac-least-privilege-and-audit.md            # RBAC Dual de 3 niveles (mod.sub.fn), cupos soft-delete y auditoría
│   ├── 08-offensive-security-and-qa-gates.md           # Vectores Red Team (Kali), Semgrep, Trivy, pip-audit, Schemathesis y Knip
│   ├── 09-environments-and-deployment-governance.md    # 5 Entornos, Fail-Fast, Sinkhole de salida e invarianza SHA-256
│   ├── 10-git-worktrees-and-smart-merge.md             # Git Worktrees, AST Claiming (fcntl.flock), Merge Train y Agente Árbitro
│   ├── 11-visual-architecture-and-archify-atlas.md     # Atlas Visual Interactivo HTML (Archify alimentado desde Graphify)
│   ├── 12-openspec-bipartition-and-sync.md             # Bipartición OpenSpec (Negocio vs Código) y sincronización continua
│   ├── 13-oppyfy-ai-governance-and-telemetry.md        # OppyFy (RAG 3-Capas, RBAC propio editable, créditos y llm_request_logs)
│   ├── 14-jev-system1-mandatory-gate.md                # Evaluación autónoma obligatoria: "¿Lo puede hacer JEV (Sí/No)?"
│   ├── 15-i18n-multilanguage-and-dynamic-translation.md# i18n Full-Stack (ES/EN + futuros), traducción de datos cliente y patrón Pi
│   ├── 16-multi-currency-fx-and-pricing-governance.md  # Multi-Moneda FX (BCCh + BCE), selector independiente y precios
│   ├── 17-observability-opentelemetry-sentry-and-umami.md # Observabilidad 4-Pilares y Centro de Mando en platform-admin
│   ├── 18-media-storage-r2-and-quota-governance.md     # Almacenamiento R2 aislado por Tenant/Env, WebP 2-capas y cuota MB
│   ├── 19-database-backups-and-disaster-recovery.md    # Respaldos en 4 Capas cifrados (zstd+age) y restauración por Tenant
│   ├── 20-multiagent-squad-and-self-healing-loops.md   # Escuadrón de 12 Agentes, paridad con Legacy y bucles de autoreparación
│   ├── 21-design-system-legacy-dna-and-mobile-first.md # ADN Visual de Legacy (3 temas) y arquitectura Mobile-First
│   └── 22-realtime-websockets-and-zero-polling.md      # Tiempo Real con WebSockets (Redis Pub/Sub), filtro RBAC y cero polling
├── skills/                                             # [PAQUETES EJECUTABLES EN REPL + CRUD CONTROLADO VÍA /refine]
│   ├── git_smart_merge/                                # Orquestación de Git Worktrees, AST Claiming y Smart Merge Train
│   ├── jev-decision-engine/                            # Primitivas tipadas de JEV (Boolean, Choice, Score + confianza)
│   ├── i18n_manager/                                   # Sincronización atómica de diccionarios JSON de idiomas
│   ├── fx_currency_manager/                            # Conversión multi-moneda con tasas oficiales y Decimal
│   ├── observability_telemetry/                        # Instrumentación OpenTelemetry, Grafana, Sentry/GlitchTip y Umami
│   ├── r2_media_storage/                               # Compresión WebP y gestión de cuotas en Cloudflare R2
│   ├── db_backup_recovery/                             # Backups en 4 capas y restauración quirúrgica por esquema
│   ├── alembic-migration-manager/                      # Creación, rebase correlativo y análisis de impacto de migraciones
│   ├── rbac-permission-guard/                          # Registro y auditoría de permisos de 3 niveles
│   ├── security-audit/                                 # Reglas de Semgrep / OWASP / Gitleaks / cloudflare security-audit-skill
│   ├── graphify/                                       # Navegador AST en REPL (LegacyGraph read-only + V2Graph live)
│   ├── archify/                                        # Generador de mapas interactivos HTML para el Atlas de Arquitectura
│   ├── openspec-sync/                                  # Validador de bóvedas espejo (business-domain vs engineering-code)
│   └── learned-patterns/                               # Patrones destilados por Prime Agent de trayectorias exitosas en OppyTec
├── evals/                                              # [INMUTABLE / SOLO LECTURA ANTI-TRAMPA - Verificado por SHA-256]
│   ├── rubric_10_criteria.yaml                         # Rúbrica de 10 criterios que el agente corre pero NO puede editar
│   └── eval_hashes.sha256                              # Hashes de integridad contra Reward Hacking
├── subagents/                                          # [LAS 12 CARPETAS DE SUB-AGENTES RLM: prompt.md + knowledge.md + handovers/]
│   ├── 01-orchestrator-pm/                             # Orquestador PM (`prompt.md`, `knowledge.md`, `handovers/latest_handover.md`)
│   ├── 02-software-architect/                          # Arquitecto DDD, Clean Architecture, paridad Legacy y gate JEV
│   ├── 03-database-alembic-and-backup-engineer/        # Esquemas public/tenant_*, Alembic 0001..N y Backups 4-Capas
│   ├── 04-backend-senior-dev/                          # FastAPI, SQLAlchemy Async, RBAC 3-niveles y R2 Quotas
│   ├── 05-frontend-senior-dev/                         # React 19, ADN Visual Legacy (3 temas), Mobile-First y <Can>
│   ├── 06-ai-oppyfy-and-jev-engineer/                  # OppyFy RAG 3-Capas, RBAC propio, Créditos y JEV Sistema 1
│   ├── 07-i18n-and-fx-currency-specialist/             # i18n estático/dinámico ("Pollo King"), banderas SVG y FX BCCh/BCE
│   ├── 08-environments-and-observability-engineer/     # 5 Entornos, SHA-256 y Observabilidad 4-Pilares
│   ├── 09-qa-parity-and-test-engineer/                 # Co-Creación 1:1, paridad matemática Legacy y bucle de autoreparación
│   ├── 10-cybersecurity-redteam-auditor/               # 11 vectores Red Team, autoparcheo autónomo y poder de veto final
│   ├── 11-git-worktree-merge-arbiter/                  # Merge Train (rebase + --ff-only) y Árbitro Fresco de 4 vías
│   └── 12-tech-writer-openspec-archify/                # Bóvedas OpenSpec (Negocio/Código), Graphify y Atlas HTML Archify
└── memory/                                             # [ESTADO PERSISTENTE DEL HARNESS]
    ├── current_state.md                                # Estado de la fase activa actual según el plan de implementación
    ├── trajectory_lessons.md                           # Memoria suplementaria destilada tras fallos/correcciones en Quality Gates
    ├── claims_registry.json                            # Reservas activas de símbolos AST por worktree
    └── harness_events.jsonl                            # Bitácora Event-Sourced inmutable (timestamp + Git SHA)
```

> **Guardrail de Seguridad para Auto-Modificación (`Continual Harness`):**  
> El agente tiene permiso de escritura (CRUD) sobre `.agent/memory/` y `.agent/skills/learned-patterns/` para mejorar continuamente, pero **NUNCA** puede modificar ni eliminar las reglas base en `.agent/rules/` ni relajar los *Quality Gates* deterministas sin aprobación humana explícita.

---

## 6. Índice Maestro de Estrategias Normativas de OppyTec v2.0

Todas las decisiones arquitectónicas y reglas operativas están detalladas en los siguientes documentos estratégicos en la raíz del monorepo:

1. **[`propuesta_arquitectura_tree_001.md`](propuesta_arquitectura_tree_001.md):** Mapa completo de directorios, subdirectorios y archivos críticos.
2. **[`.agent/estrategias/estrategia_migraciones_alembic_001.md`](.agent/estrategias/estrategia_migraciones_alembic_001.md):** Migraciones correlativas `0001..NNNN`, separación `public` vs `tenant_*` y Bootstrap Génesis (`oppytec.admin`).
3. **[`.agent/estrategias/estrategia_rbac_y_auditoria_001.md`](.agent/estrategias/estrategia_rbac_y_auditoria_001.md):** RBAC Dual de 3 niveles, acceso transversal en el Holding, cupos por plan con `soft-delete` y auditoría forense.
4. **[`.agent/estrategias/estrategia_testing_calidad_y_seguridad_001.md`](.agent/estrategias/estrategia_testing_calidad_y_seguridad_001.md):** Co-Creación 1:1 de tests, 5 dimensiones, Gates estratificados, Cero Hardcoding y 11 vectores Red Team (Kali + Caos).
5. **[`.agent/estrategias/estrategia_entornos_y_despliegue_001.md`](.agent/estrategias/estrategia_entornos_y_despliegue_001.md):** Los 5 entornos (`local`, `preview`, `ci`, `staging`, `production`), invarianza `SHA-256` y configuración *Fail-Fast*.
6. **[`.agent/estrategias/estrategia_orquestacion_git_worktrees_y_smart_merge_001.md`](.agent/estrategias/estrategia_orquestacion_git_worktrees_y_smart_merge_001.md):** Orquestación con **Prime Agent RLM**, Git Worktrees, AST Claiming y *Smart Merge Train*.
7. **[`.agent/estrategias/estrategia_visualizacion_y_auditoria_archify_001.md`](.agent/estrategias/estrategia_visualizacion_y_auditoria_archify_001.md):** Atlas Visual Interactivo HTML (`Archify` alimentado desde `Graphify`).
8. **[`.agent/estrategias/estrategia_openspec_negocio_vs_codigo_001.md`](.agent/estrategias/estrategia_openspec_negocio_vs_codigo_001.md):** Bipartición de `specs/` (`business-domain/` vs `engineering-code/`) lista para futuro RAG Dual.
9. **[`.agent/estrategias/estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md`](.agent/estrategias/estrategia_asistente_ai_oppyfy_rag_y_creditos_001.md):** Asistente `OppyFy` (RAG 3-Capas, RBAC propio editable, paquetes de créditos sin caducidad y `llm_request_logs`).
10. **[`.agent/estrategias/estrategia_motor_decisiones_jev_system1_001.md`](.agent/estrategias/estrategia_motor_decisiones_jev_system1_001.md):** Motor global `JEV (Sistema 1)` con los 4 candados automáticos *"¿Lo puede hacer JEV (Sí/No)?"*.
11. **[`.agent/estrategias/estrategia_internacionalizacion_i18n_multilenguaje_001.md`](.agent/estrategias/estrategia_internacionalizacion_i18n_multilenguaje_001.md):** `i18n` Full-Stack (`es`/`en` + futuros), selector de banderas SVG, traducción dinámica de datos cliente y patrón `Pi`.
12. **[`.agent/estrategias/estrategia_multimoneda_fx_precios_y_cobros_001.md`](.agent/estrategias/estrategia_multimoneda_fx_precios_y_cobros_001.md):** Motor Multi-Moneda FX (Bancos Centrales BCCh + BCE), selector independiente, consola admin y gestión de precios.
13. **[`.agent/estrategias/estrategia_observabilidad_monitoreo_y_analitica_001.md`](.agent/estrategias/estrategia_observabilidad_monitoreo_y_analitica_001.md):** Los 4 pilares (`OpenTelemetry`, `Grafana`, `Sentry/GlitchTip`, `Umami`) y Centro de Observabilidad en `platform-admin`.
14. **[`.agent/estrategias/estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md`](.agent/estrategias/estrategia_almacenamiento_imagenes_r2_y_cuotas_001.md):** Almacenamiento Cloudflare R2 aislado por Tenant/Entorno, compresión WebP en 2 capas y cuota de memoria MB por plan.
15. **[`.agent/estrategias/estrategia_respaldos_base_datos_y_recuperacion_001.md`](.agent/estrategias/estrategia_respaldos_base_datos_y_recuperacion_001.md):** Respaldos en 4 Capas cifrados (`zstd+age`) y restauración quirúrgica de un solo Tenant.
16. **[`.agent/estrategias/estrategia_escuadron_multiagente_prompts_y_autoreparacion_001.md`](.agent/estrategias/estrategia_escuadron_multiagente_prompts_y_autoreparacion_001.md):** Los **12 Agentes Especializados**, cobertura 100% de las estrategias, System Prompts, asignación Gemini Argon/Flash + JEV y bucles de autoreparación autónoma.
17. **[`.agent/estrategias/estrategia_sistema_diseno_ux_ui_y_mobile_first_001.md`](.agent/estrategias/estrategia_sistema_diseno_ux_ui_y_mobile_first_001.md):** Rescate exhaustivo del ADN visual de `OppyTec-Legacy` (3 temas `light`/`dark`/`ocean-blue`, `.glass`, animaciones, 42 colores, 49 íconos, `framer-motion`, `useSwipeNavigation`) y arquitectura estricta *"Mobile-First, Then Web"*.
18. **[`.agent/estrategias/estrategia_tiempo_real_websockets_y_notificaciones_001.md`](.agent/estrategias/estrategia_tiempo_real_websockets_y_notificaciones_001.md):** Motor de Tiempo Real con WebSockets (`/api/v1/ws/realtime`), bus **Redis Pub/Sub + Streams**, filtrado por permisos RBAC de 3 niveles, sincronización con TanStack Query v5 y prohibición de polling HTTP.

---

## 7. Plan de Acción Recomendado para OppyTec

1. **Aprobar este marco agéntico:** Adoptar esta jerarquía integrando **Prime Agent** (gestión RLM de contexto y auto-mejora) y **Jev** (guardrails rápidos Sistema 1), descartando formalmente herramientas que saturan contexto (como Obsidian o REA en el trabajo cotidiano).
2. **Consolidar los Quality Gates locales y estructura `.agent/` (Paso 0):** Materializar `.agent/rules/00..19`, las skills ejecutables y `scripts/harness.py`.
3. **Ejecutar la Fase 1 de `specs/06-IMPLEMENTATION-PLAN.md`:** Levantar el entorno de contenedores limpio (Postgres con `pgvector`, Redis, backend, frontend y perfil opcional `--profile observability`) y validar las variables de entorno sin modificar la lógica existente en `OppyTec-Legacy`.
