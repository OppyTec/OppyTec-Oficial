# ADR-013: Motor Global de Decisiones y Enrutamiento `JEV` (Sistema 1 — Baja Latencia y Cero Desperdicio de Tokens)

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_motor_decisiones_jev_system1_001.md` / `.agent/skills/jev-decision-engine/SKILL.md`

---

## 1. Contexto

Utilizar modelos fundacionales pesados y costosos (Sistema 2, con segundos de latencia y miles de tokens de razonamiento) para tareas operativas repetitivas como clasificar la intención de un mensaje, decidir si una cadena es una marca comercial propia, enrutar qué herramienta de código duro ejecutar o puntuar anomalías en facturas encarece innecesariamente la operación y degrada la experiencia de usuario.

## 2. Decisión

Integrar a **`JEV` (`JevDecisionEngine` en `oppytec-backend/src/core/jev/`)** como el **Motor Global de Decisiones Sistema 1** de toda la plataforma OppyTec v2.0 y del arnés multi-agente:

1. **Tres Primitivas Deterministas de Baja Latencia (`70 ms – 500 ms`):**
   - `jev.boolean(prompt, context) -> JevBooleanResult(value: bool, confidence: Decimal)`: Decisiones binarias con umbral de confianza (ej. filtro de Prompt Injection, detección de nombre propio comercial como `"Pollo King"`).
   - `jev.choice(prompt, options, context) -> JevChoiceResult(selected: str, confidence: Decimal)`: Clasificación y enrutamiento cerrado entre opciones predefinidas (ej. selección de herramienta en código duro de `OppyFy`, mapeo de categorías de productos en importación Excel).
   - `jev.score(prompt, rubric, context) -> JevScoreResult(score: Decimal, breakdown: dict)`: Puntuación numérica calibrada `[0.0000, 1.0000]` (ej. nivel de riesgo de anomalía en precios de factura o pre-evaluación de calidad en el arnés).
2. **Compuerta Arquitectónica Obligatoria (*"¿Lo puede hacer JEV (Sí/No)?"*):**
   - Todo archivo de especificación técnica en `specs/engineering-code/*.code.spec.md` debe incluir el bloque `jev_system1_evaluation` evaluando qué decisiones del módulo se delegan a `JEV` antes de permitir el uso de un LLM pesado (Sistema 2).
3. **Fallback Determinista y Telemetría Unificada:**
   - Si la confianza devuelta por `JEV` es inferior al umbral configurado (`confidence < threshold`) o el servicio presenta timeout, `fallback_policy.py` aplica una regla determinista segura (*Fail-Closed* en seguridad, escalamiento controlado en clasificación) y registra la llamada en `public.llm_request_logs`.

## 3. Consecuencias

- **Positivas:**
  - Reducción superior al `80%` en consumo de tokens y latencia sub-segundo en clasificación, moderación y enrutamiento.
  - Contrato uniforme y tipado (`Pydantic v2` + `Decimal`) para todos los módulos del backend.
- **Negativas / Trade-offs:**
  - `JEV` está diseñado exclusivamente para decisiones acotadas (`Boolean`, `Choice`, `Score`); nunca debe usarse para redactar texto libre extenso.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca:** `oppytec-backend/tests/architecture/test_jev_system1_enforcement.py`.
- **Invariante Verificada:** Verifica que ningún módulo fuera de `src/core/jev/` y `src/modules/oppy_ai/` instancie clientes de LLMs directamente sin pasar por `JevDecisionEngine` y que todas las especificaciones `.code.spec.md` contengan su bloque `jev_system1_evaluation`.
