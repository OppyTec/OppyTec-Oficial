# ADR-019: Escuadrón de 12 Agentes Especializados, *Model Tiering* Inteligente y Bucles de Autoreparación con Poder de Veto

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_escuadron_multiagente_prompts_y_autoreparacion_001.md` / `AGENTS.md`

---

## 1. Contexto

Utilizar un único agente generalista con una ventana de contexto saturada para diseñar arquitectura, migrar bases de datos, programar backend/frontend, auditar seguridad y escribir documentación produce degradación cognitiva (*Context Rot*), olvido de reglas de negocio y altos costos de inferencia.

## 2. Decisión

Estructurar la ingeniería agéntica de OppyTec v2.0 en un **Escuadrón de 12 Agentes Especializados (`.agent/subagents/01..12-*/`)** con **Memoria Evolutiva Propia**, **Asignación Óptima de Modelos (*Model Tiering*)** y **2 Bucles Cerrados de Autoreparación**:

1. **Aislamiento Cognitivo y Memoria por Especialidad (`01` al `12`):**
   - Cada uno de los 12 agentes posee su propio directorio con 3 artefactos exclusivos:
     - `prompt.md`: Rol, estrategias a cargo, herramientas permitidas y reglas inmutables.
     - `knowledge.md`: Lecciones aprendidas destiladas en su especialidad para no repetir errores.
     - `handovers/latest_handover.md`: Estado exacto al cerrar cada sesión (*Completed*, *Friction & Failures*, *Next Exact Action*).
2. **Estrategia de *Model Tiering* (Máxima Calidad con Mínimo Costo de Tokens):**
   - **Modelos de Razonamiento Profundo (`Gemini 4 Argon` / `Pro`):** Reservados para decisiones estructurales y arbitraje crítico: Agente 01 (Orquestador PM), Agente 02 (Arquitecto DDD), Agente 09 (QA Paridad Matemática), Agente 10 (Ciberseguridad Red Team) y Agente 11 (Árbitro de Merge de 4 Vías).
   - **Modelos de Alta Velocidad (`Gemini 3.8 Flash`):** Asignados a ejecución intensiva guiada por especificaciones: Agente 03 (DB/Alembic/Backups), Agente 04 (Backend), Agente 05 (Frontend), Agente 06 (IA `OppyFy`/`JEV`), Agente 07 (`i18n`/`FX`), Agente 08 (Entornos/Observabilidad) y Agente 12 (OpenSpec/Archify/Bitácora).
3. **Bucle 1 — Autoreparación Funcional y Matemática (`Agente 09 QA` $\leftrightarrow$ `Constructores 03..08`):**
   - Si un test unitario, de integración o de paridad contra `OppyTec-Legacy` falla, el Agente 09 diagnostica la causa raíz exacta y devuelve el ticket con el diff requerido hasta lograr `100%` de aprobación (máximo 3 iteraciones antes de cortar bucle).
4. **Bucle 2 — Autoparcheo Ofensivo y Poder de Veto Final (`Agente 10 Ciberseguridad`):**
   - El **Agente 10** posee **Poder de Veto Absoluto (`SECURITY_VETO` vs `SECURITY_APPROVED`)**. Ninguna fase se cierra ni se fusiona si existe una vulnerabilidad en los 11 vectores Red Team o en `Semgrep`/`Trivy`/`Gitleaks`.

## 3. Consecuencias

- **Positivas:**
  - Cada agente arranca en el milisegundo `0` leyendo únicamente el contexto de su especialidad, logrando máxima precisión y mínimo consumo de tokens.
  - Autoreparación determinista de bugs y vulnerabilidades sin intervención humana manual.
- **Negativas / Trade-offs:**
  - Requiere mantener actualizados los `handovers/latest_handover.md` al finalizar cada intervención.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_subagent_strategy_coverage.py`.
- **Invariante Verificada:** Verifica que las 12 carpetas `.agent/subagents/01..12-*/` contengan sus archivos `prompt.md`, `knowledge.md` y `handovers/latest_handover.md`, y que las 17 estrategias maestras estén asignadas sin brechas de cobertura.
