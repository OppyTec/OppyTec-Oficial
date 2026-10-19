# ADR-007: Co-Creación 1:1 de Testing en 5 Dimensiones y Compuertas de Seguridad Ofensiva (Red Team)

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_testing_calidad_y_seguridad_001.md` / `.agent/skills/security-audit/SKILL.md`

---

## 1. Contexto

Dejar la escritura de pruebas automatizadas y las auditorías de seguridad para el final del proyecto genera deuda técnica oculta, vulnerabilidades en producción y regresiones silenciosas cuando múltiples agentes de IA editan el repositorio a alta velocidad.

## 2. Decisión

Instaurar la **Ley de Co-Creación 1:1 Obligatoria** y una arquitectura de validación en **3 Compuertas Deterministas (*Fast Gate*, *Main Gate*, *Deep Gate*)** respaldada por el **Poder de Veto del Agente 10 (`10-cybersecurity-redteam-auditor`)**:

1. **Co-Creación 1:1 en 5 Dimensiones:** Ningún servicio de dominio o endpoint se fusiona a `master` sin incluir en el mismo commit:
   - Tests unitarios y basados en propiedades (`Hypothesis`) en `tests/unit/`.
   - Tests de paridad matemática contra `OppyTec-Legacy`.
   - Tests de arquitectura de Caja Blanca en `tests/architecture/`.
   - Tests de integración con contenedores reales en `tests/integration/`.
   - Vectores de seguridad ofensiva en `tests/security_redteam/test_01..11_*.py`.
2. **Las 3 Compuertas de Calidad (*Quality Gates*):**
   - **Fast Gate (`< 15s`):** `ruff`, `mypy --strict`, `eslint`, `tsc --noEmit`, `knip`, `tests/architecture/` y `tests/smoke/` + verificación anti-trampa `SHA-256` (`scripts/harness.py verify-evals`).
   - **Main Gate (`< 3 min`):** Suite unitaria/integración de radio de impacto vía `Graphify`, paridad de migraciones Alembic y vectores Red Team.
   - **Deep Gate (`< 12 min`):** Escaneo SAST/SCA/DAST completo (`Semgrep`, `Trivy`, `Gitleaks`, `pip-audit`, `pnpm audit`, fuzzing OpenAPI con `Schemathesis` y prueba de carga `Locust` a `500 RPS`).
3. **Candado Anti-Reward-Hacking:** Los archivos en `.agent/rules/`, `.agent/evals/` y `tests/architecture/` están protegidos contra modificaciones oportunistas mediante firmas `SHA-256`.

## 3. Consecuencias

- **Positivas:**
  - Detección de errores arquitectónicos o de tipado en menos de 15 segundos antes de entrar al *Merge Train*.
  - Certificación continua contra los 11 vectores de ataque más críticos en plataformas SaaS multi-tenant.
- **Negativas / Trade-offs:**
  - Ningún agente puede dar por terminada una tarea si falla cualquiera de los 10 criterios de `.agent/evals/rubric_10_criteria.yaml`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_module_test_parity.py` y `scripts/harness.py verify-evals`.
- **Invariante Verificada:** Verifica automáticamente que por cada módulo en `src/modules/<mod>/` existan sus correspondientes pruebas en `tests/unit/<mod>/` y que los hashes `SHA-256` de `.agent/evals/eval_hashes.sha256` permanezcan intactos.
