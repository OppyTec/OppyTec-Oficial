# ADR-011: Arquitectura Bipartita de OpenSpec (`business-domain` vs `engineering-code`) Lista para RAG Seguro

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_openspec_negocio_vs_codigo_001.md` / `.agent/skills/openspec-sync/SKILL.md`

---

## 1. Contexto

En los sistemas donde una única especificación técnica mezcla reglas funcionales de negocio con nombres de tablas SQL, rutas internas de archivos, algoritmos de seguridad y secretos de infraestructura, indexar esa documentación en el motor RAG del asistente de IA para clientes (`OppyFy`) expone la propiedad intelectual y la superficie de ataque interna ante ataques de *Prompt Injection*.

## 2. Decisión

Dividir las especificaciones de **OpenSpec (`specs/openspec.config.yaml`)** en **2 Bóvedas Físicamente Separadas con Paridad Espejo 1:1**:

1. **Bóveda 1 — Dominio de Negocio (`specs/business-domain/*.business.spec.md`):**
   - Explica las reglas funcionales del ERP gastronómico/hotelero, flujos de usuario, fórmulas conceptuales y casos de uso en lenguaje de negocio.
   - **Regla de Pureza:** Contiene **0% de código Python/TypeScript, 0% de DDL/SQL, 0% de nombres de tablas internas y 0% de rutas del servidor**.
   - **Consumidor RAG:** Es la **única bóveda autorizada (`rag_exposure: client_safe`)** para ser vectorizada e ingerida por el asistente **`OppyFy`**.
2. **Bóveda 2 — Ingeniería y Código (`specs/engineering-code/*.code.spec.md`):**
   - Espejo técnico 1:1 de cada archivo de negocio (mismo prefijo de nombre) + contratos internos de infraestructura (`multi-agent-git-harness.code.spec.md`).
   - Contiene contratos exactos de API, modelos SQLAlchemy, índices PostgreSQL, invariantes de concurrencia y la sección obligatoria **`jev_system1_evaluation`** (*"¿Lo puede hacer JEV (Sí/No)?"*).
   - **Bloqueo RAG (`rag_exposure: forbidden_internal_only`):** Físicamente excluida del pipeline de ingesta RAG de `OppyFy`.

## 3. Consecuencias

- **Positivas:**
  - Inmunidad estructural contra la filtración de arquitectura interna, nombres de tablas o rutas de código a través del asistente de IA.
  - Sincronización determinista entre las reglas de negocio que lee el cliente y los contratos técnicos que implementan los 12 agentes.
- **Negativas / Trade-offs:**
  - Todo cambio funcional requiere actualizar simultáneamente el par espejo `.business.spec.md` y `.code.spec.md`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca y Red Team:** `oppytec-backend/tests/architecture/test_openspec_bipartition_and_sync.py` y `oppytec-backend/tests/security_redteam/test_11_oppyfy_rag_prompt_injection_and_credit_drain.py`.
- **Invariante Verificada:** Falla el *Fast Gate* si falta el par espejo entre `specs/business-domain/` y `specs/engineering-code/`, si un archivo `.business.spec.md` contiene bloques de código SQL/Python o rutas `src/`, o si un `.code.spec.md` omite la evaluación `jev_system1_evaluation`.
