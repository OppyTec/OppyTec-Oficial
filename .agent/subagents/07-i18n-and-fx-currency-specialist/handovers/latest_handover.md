# Reporte de Traspaso (`Handover`) — Agente 07: Especialista en i18n y Multi-Moneda FX

- **Fecha UTC:** 2026-11-05T01:15:00Z
- **Agente:** `07-i18n-and-fx-currency-specialist`
- **Fase / Hito:** Etapa 3 del Plan Maestro de LLM Evals y Observabilidad Langfuse (Fase 6: Paridad Bilingüe, Regla "Pollo King", i18n Frontend y Multi-Moneda FX).
- **Estado de Certificación:** `STAGE_3_I18N_AND_FX_CERTIFIED` (16/16 tests passing en `test_bilingual_parity.py`, 100% simetría en claves frontend, 0 violaciones de marcas gastronómicas, 0 floats en cálculo y triangulación cambiaria).

---

## 1. Completed (Qué se implementó y certificó)

1. **Golden Dataset Gastronómico Bilingüe (50 Casos 1:1)**:
   - Creados `oppytec-backend/tests/ai_evals/datasets/gastronomic_golden_dataset.json` (Español canónico) y `oppytec-backend/tests/ai_evals/datasets/gastronomic_golden_dataset_en.json` (Inglés profesional gastronómico espejo).
   - Cobertura de los 5 dominios estratégicos (10 casos cada uno):
     * Dominio 1: Banquetes y Escalabilidad de Porciones (`EVAL-GASTRO-001` a `010`).
     * Dominio 2: Mermas, Costeo y Rendimiento de Recetas (`EVAL-GASTRO-011` a `020`).
     * Dominio 3: Stock y Política FEFO Estricta (`EVAL-GASTRO-021` a `030`).
     * Dominio 4: Facturación, Proveedores y Órdenes de Compra (`EVAL-GASTRO-031` a `040`).
     * Dominio 5: Muro de Fuego de Privacidad y Consultas sobre OppyTec (`EVAL-GASTRO-041` a `050`).

2. **Invarianza Estricta de Marcas ("Pollo King" & "Cevichería Central")**:
   - Validación inmutable de que "Pollo King" y "Cevichería Central" nunca se traduzcan en prompts, ground truths ni entidades requeridas en inglés (PROHIBIDO "King Chicken", "Chicken King", "Rey Pollo", "Central Ceviche").

3. **Suite de Pruebas de Paridad Bilingüe (`oppytec-backend/tests/ai_evals/test_bilingual_parity.py`)**:
   - `TestGoldenDatasetStructuralParity`: verifica existencia, 50 casos exactos, secuencia correlativa de IDs, alineación de categorías y criterios de evaluación.
   - `TestProtectedBrandInvariance`: verificación de cero traducciones prohibidas y presencia simétrica de marcas comerciales protegidas.
   - `TestBilingualTokenAndLengthParity`: ratio de tokens/palabras dentro de los rangos de naturalidad lingüística (0.60 a 1.45 por caso, promedio 0.80 a 1.15).
   - `TestMultiCurrencyFxTokenTelemetry`:
     * Cálculo de costos de tokens con 0% float y 100% `Decimal` (`Decimal("0.000001")` para USD y `Decimal("0.01")` para CLP).
     * Conversión y triangulación multi-moneda (`USD`, `CLP`, `EUR`) utilizando tasas del Banco Central de Chile (BCCh) y Banco Central Europeo (BCE Frankfurter).
   - `TestFrontendI18nSynchronization`:
     * Simetría al 100% de claves entre `locales/es/oppyfy.json` y `locales/en/oppyfy.json`.
     * Preservación de "Pollo King" en frontend.
     * Validación de variables de interpolación (`{{brandName}}`, `{{credits}}`, `{{count}}`, `{{ms}}`).

4. **Resultados de Verificación**:
   - `oppytec-backend/.venv/bin/pytest oppytec-backend/tests/ai_evals/test_bilingual_parity.py`: **16/16 passed** (0 warnings).
   - `oppytec-frontend`: **6 suites, 70 passed** en `src/features/oppyfy`.

---

## 2. Friction & Failures (Dificultades y Resoluciones)

- **Fricción 1:** Al correr pytest directamente en el shell se detectó `pytest: command not found` debido a que el entorno virtual del backend se aloja en `oppytec-backend/.venv/bin/pytest`.
  * **Solución:** Se invocó el binario específico del virtualenv de Python 3.14 (`oppytec-backend/.venv/bin/pytest`), ejecutándose sin problemas.
- **Fricción 2:** Advertencia de deprecación de Pytest 10 (`PytestRemovedIn10Warning`) en fixtures con `scope="class"` definidas como métodos de instancia.
  * **Solución:** Se decoraron las fixtures de clase con `@classmethod` y argumento `cls`, eliminando el 100% de advertencias.

---

## 3. Next Exact Action

Entregar resultados de la Etapa 3 al Orquestador y continuar la coordinación con:
1. **Agente 06 (`06-ai-oppyfy-and-jev-engineer`)**: Ejecución de las suites de DeepEval / Ragas contra los datasets generados.
2. **Agente 08 (`08-environments-and-observability-engineer`)**: Finalización de la integración de Langfuse con OpenTelemetry Tempo/Grafana.
3. Paso coordinado hacia la **Etapa 4** (QA Parity, Cybersecurity Red Team, Git Arbiter y Tech Writer OpenSpec).
