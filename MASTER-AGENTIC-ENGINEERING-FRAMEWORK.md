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
| **Herdr** | Orquestación multi-agente y supervisión de enjambres autónomos. | **Situacional / Opcional (Tier 3)** | Si el desarrollo lo lideras tú interactuando con el agente en el IDE (pair-programming), Herdr agrega sobrecarga innecesaria. Solo aporta valor si lanzas tareas desatendidas de larga duración (ej. refactorización masiva nocturna). |
| **Jev** (TypeSafe AI) | Modelo de Decisión y Control *Sistema 1* (no generativo): evalúa estados y devuelve salidas tipadas (`Choice`, `Score`, `Noul/Boolean`) con confianza calibrada. | **Muy Recomendado / Clave en Guardrails (Tier 1-2)** | Resuelve el problema del costo y lentitud de los agentes: en lugar de llamar a un LLM generativo pesado para decidir si una herramienta es segura o clasificar un paso, Jev opera en 70-500 ms a un costo 400x menor, actuando como filtro de seguridad y enrutador antes de mutar código. |
| **Obsidian** | Base de conocimiento personal en Markdown. | **SOBRA en el pipeline del agente** | Obsidian es una herramienta de productividad humana. Los agentes no deben depender de tus notas privadas ni de vaults locales. Toda decisión y contexto del sistema debe residir en el repositorio Git (`specs/`, `docs/adr/`, `.agent/rules/`). |
| **REA (Reverse Engineer Anything)** | Deconstrucción e ingeniería inversa de binarios/código. | **SOBRA para el ciclo diario (Útil solo como tarea puntual)** | En OppyTec no tenemos binarios propietarios ni código ofuscado. Tenemos código Python y TypeScript legible en `OppyTec-Legacy`. Solo tiene sentido como script de un solo uso para extraer esquemas antiguos si faltara documentación, nunca como herramienta activa permanente. |

---

### 2.2 Las Piezas Críticas que FALTABAN (El Lado Determinista)

El diagnóstico acertó de lleno en lo que le falta a la mayoría de los desarrollos con IA: **Restricciones Deterministas**. Un LLM es probabilístico; la calidad de ingeniería exige herramientas que no admitan discusión:

```mermaid
flowchart LR
    subgraph Cognitiva["Capa Cognitiva Dual (Sistema 1 + Sistema 2)"]
        Spec["OpenSpec (Contratos)"]
        Rules[".agent/rules (Directrices)"]
        Graph["Graphify (Navegación AST)"]
        Jev["Jev / TypeSafe AI (Decisiones Sistema 1: Guardrails, Triage, Routing)"]
        LLM["Frontier LLMs (Razonamiento Sistema 2: Generación)"]
    end

    subgraph Determinista["Quality Gates Deterministas (No Negociables)"]
        Linter["Ruff / ESLint (Sintaxis y Estilo)"]
        TypeCheck["Mypy / TS Strict (Cero 'any')"]
        ArchLinter["pytest-archon / import-linter (Clean Architecture)"]
        SecCheck["Trivy / Gitleaks / Semgrep (Seguridad)"]
        ContractTest["Schemathesis (Fuzzing OpenAPI)"]
    end

    Jev -->|Valida Tool-Call y Routing| LLM
    LLM -->|Genera Código| Determinista
    Determinista -->|Fallo: Devuelve error exacto| LLM
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

---

## 3. Matriz Maestra del Ecosistema de Herramientas Recomendado

Para que el sistema sea profesional, robusto y eficiente en tokens, este es el ecosistema depurado:

| Categoría | Herramienta Recomendada | Propósito Concreto | ¿Activa en Prompt? | Momento de Uso |
|---|---|---|---|---|
| **Especificación (SDD)** | `specs/` (Markdown con OpenSpec) | Contrato de producto, endpoints, esquemas y DoD. | Sí (sólo la spec relevante a la tarea) | Fase 1 (Antes de codificar) |
| **Gobernanza y Reglas** | `.agent/rules/` y `AGENTS.md` | Restricciones negativas, estilo, convenciones y límites. | Sí (modularmente según contexto) | En todo momento |
| **Memoria de Decisiones** | `docs/adr/` (ADRs) | Registro inmutable de decisiones de arquitectura tomadas. | Sí (en consultas arquitectónicas) | Al decidir cambios estructurales |
| **Guardrails de Decisión (Sistema 1)** | `Jev` (TypeSafe AI) | Evaluación de seguridad de tool-calls, enrutamiento rápido y triage tipado (Choice/Score/Noul). | En runtime / Middleware agéntico | Antes de ejecutar mutaciones |
| **Exploración de Código** | `Graphify` | Grafo de dependencias y llamadas sin saturar tokens. | Bajo demanda (query específica) | Al analizar impacto en repos grandes |
| **Topología Estructural** | `Archify` / Diagramas Mermaid en specs | Vista de componentes y boundaries. | Bajo demanda | Al diseñar nuevos módulos |
| **Verificación Sintáctica** | `Ruff` (Python) + `ESLint` / `Prettier` (TS) | Formateo y corrección automática inmediata. | No (ejecución CLI determinista) | En cada guardado / pre-commit |
| **Tipado Estricto** | `mypy --strict` + `tsc --noEmit` | Garantizar cero `any` y contratos de tipos completos. | No (ejecución CLI determinista) | Pre-commit y CI |
| **Linter de Arquitectura** | `pytest-archon` + `dependency-cruiser` | Prevenir dependencias circulares y violaciones de capas. | No (ejecución CLI determinista) | Suite de tests |
| **Auditoría de Seguridad** | `security-audit-skill` + `gitleaks` + `semgrep` | Detección de secretos, XSS, SQLi y CVEs. | Al cierre de fase | Pre-commit / Quality Gate |
| **Testing de Contratos** | `schemathesis` + `pytest` + `vitest` | Pruebas de integración y cumplimiento de contratos API. | No (ejecución CLI determinista) | Validación de fases |

---

## 4. El Ciclo de Vida Agéntico en 4 Fases

Para desarrollar sin roturas, todo agente de IA (y desarrollador humano) en OppyTec debe ceñirse al siguiente pipeline:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                               PIPELINE AGÉNTICO                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

 [1. ESPECIFICACIÓN] ──▶ [2. VALIDACIÓN] ──▶ [3. CONSTRUCCIÓN] ──▶ [4. QUALITY GATE]
    (OpenSpec)              (Archify/ADRs)      (.agent/rules)         (Linters + Tests)
         │                         │                   │                      │
         ▼                         ▼                   ▼                      ▼
 - Leer o redactar spec    - Verificar límites  - Implementar código  - Ruff & Mypy
 - Validar inputs/outputs   entre capas.         siguiendo reglas.    - Vitest / Pytest
 - Acordar Definition      - Consultar ADRs si  - Si es complejo:     - pytest-archon
   of Done (DoD).            hay dudas.          consultar Graphify.  - Security Audit
         │                         │                   │                      │
         └─────────────────────────┴───────────────────┴──────────────────────┘
                                          │
                                 ¿Falla algún check?
                                    ├─ SI ──▶ Revertir / Corregir automáticamente
                                    └─ NO ──▶ Aprobado para commit / PR
```

### Fase 1: Especificación y Contratos (*Spec First*)
- **Regla:** Ningún agente escribe una sola línea de código en `src/` sin antes tener la especificación aprobada en `specs/`.
- **Salida esperada:** Esquemas de entrada y salida (Pydantic / Zod), endpoints exactos, comportamiento ante errores y criterios de aceptación verificables.

### Fase 2: Arquitectura y Límites
- **Regla:** Verificar contra `specs/02-TRD.md`, `specs/05-DATABASE-SCHEMA.md` y los ADRs existentes.
- **Salida esperada:** Identificación clara de qué módulos se modifican y verificación de que no se introducen dependencias circulares ni violaciones de esquemas multi-tenant.

### Fase 3: Construcción Guiada y Restringida
- **Regla:** El agente opera bajo las reglas de `.agent/rules/`:
  - Solo accede a los archivos involucrados directamente.
  - No reescribe módulos completos cuando solo necesita editar una función.
  - Si necesita comprender un impacto indirecto, consulta `Graphify` en lugar de leer el repositorio entero.

### Fase 4: Quality Gate Determinista (La Puerta Infranqueable)
- **Regla:** La tarea no se considera "Terminada" porque el agente diga que está lista; se considera terminada cuando los comandos deterministas devuelven código `0`:
  1. `ruff check .` && `mypy src/` (Backend en verde)
  2. `pnpm lint` && `pnpm tsc --noEmit` (Frontend en verde)
  3. `pytest` (Tests de dominio y arquitectura pasando)
  4. Auditoría de seguridad sin hallazgos bloqueantes.

---

## 5. Estructura Canónica de Reglas para OppyTec (`.agent/`)

Para desacoplar el contexto y no sobrecargar la memoria de trabajo de los agentes, la carpeta de reglas de gobernanza se estructura de forma modular:

```plaintext
.agent/
├── rules/
│   ├── 00-meta-agent-instructions.md   # Prioridad de lectura, flujo de trabajo y límites de autonomía
│   ├── 01-architecture-boundaries.md   # Clean Architecture, separación dominio/infra, multi-tenant schemas
│   ├── 02-backend-standards.md         # FastAPI, Pydantic v2, SQLAlchemy 2 Async, Zero-Any, Pydantic Settings
│   ├── 03-frontend-standards.md        # React 19, TypeScript estricto, TanStack Query v5, Zod, Design System
│   ├── 04-security-guardrails.md       # Zero-Trust, Magic Bytes, sanitización XSS, tokens JWT, no-hardcode
│   └── 05-testing-and-dod.md           # Criterios de aceptación, cobertura mínima 80%, fixtures deterministas
├── skills/
│   ├── security-audit/                 # Scripts/reglas de escaneo de seguridad
│   └── graphify/                       # Herramienta de navegación semántica de grafos de código
└── memory/
    └── current_state.md                # Estado de la fase activa actual según el plan de implementación
```

---

## 6. Plan de Acción Recomendado para OppyTec

1. **Aprobar este marco agéntico:** Adoptar esta jerarquía y descartar formalmente herramientas que saturan contexto (como Obsidian o REA en el trabajo cotidiano).
2. **Consolidar los Quality Gates locales:** Asegurar que los comandos de linting, tipado y arquitectura estén configurados y listos en la raíz del proyecto.
3. **Ejecutar la Fase 1 de `specs/06-IMPLEMENTATION-PLAN.md`:** Levantar el entorno de contenedores limpio (Postgres con `pgvector`, Redis, backend, frontend) y validar las variables de entorno sin modificar la lógica existente en `OppyTec-Legacy`.
