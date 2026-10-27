# Conocimiento de Dominio: Testing 5D, Invariantes Matemáticas con Hypothesis y Detección de Ciclos DAG (`recipes`)

## 1. Metodología de Testing en 5 Dimensiones (5D Testing)

El módulo de Recetas, Escandallos y Combos (`oppytec-backend/src/modules/recipes`) y su interfaz reactiva en `oppytec-frontend/src/features/gestion` están certificados bajo una estrategia de 5 dimensiones:

1. **Pruebas Unitarias de Dominio (1D):**
   - Value Objects inmutables con precisión estricta `Decimal` (`PRECISION_COST = 0.0001`, `PRECISION_MONEY = 0.01`, `PRECISION_QUANTITY = 0.0001`): `ServingYield`, `IngredientQuantity`, `DynamicCostSummary`, `OptionSelectionRule`.
   - Prohibición estricta de binarios flotantes IEEE 754 mediante guardias `_ensure_strict_decimal` que levantan `TypeError` ante `float`.
2. **Pruebas de Integración y Servicios Transaccionales (2D):**
   - `RecipeService`, `ComboService`, `OptionGroupService` y `RecipeCostSimulatorService`.
   - Validación atómica de creación, actualización y borrado de recetas con control de integridad referencial polimórfica (XOR producto/subreceta) y protección de eliminación en uso (`OptionGroupInUseError`).
3. **Pruebas Basadas en Propiedades Matemáticas con Hypothesis (3D):**
   - Generación pseudo-aleatoria de millones de permutaciones numéricas acotadas para verificar invariantes analíticas sin casos borde desatendidos:
     - **Invariante Tripartita de Costos:** $0 \le C_{\min} \le C_{\text{base}} \le C_{\max}$.
     - **Invariante de Márgenes Inversos:** $\text{margen}_{\text{mejor}} \ge \text{margen}_{\text{base}} \ge \text{margen}_{\text{peor}}$.
     - **Invariante de Food Cost %:** $\text{FC}_{\text{mejor}} \le \text{FC}_{\text{base}} \le \text{FC}_{\text{peor}}$.
     - **Complementariedad Financiera:** $\text{Margen } \% + \text{Food Cost } \% = 100\%$ (tolerancia $\pm 0.02\%$ por cuantización independiente).
     - **Exactitud de Merma Técnica:** $\text{gross\_qty} = \text{net\_qty} \times (1 + \frac{\text{waste\_pct}}{100})$.
     - **Escalamiento Lineal de Porciones:** Para cualquier ración solicitada $S$, la cantidad neta y bruta escala estrictamente por $k = S / Y$ preservando merma técnica y alérgenos consolidados.
     - **Cero Pérdidas por Coma Flotante:** Cero derivas numéricas ante sumas continuas o divisiones periódicas con `ROUND_HALF_UP`.
4. **Algoritmos de Grafos Dirigidos Acíclicos (DAG) & Prevención de Ciclos (4D):**
   - Recorrido DFS con marcas de ruta (`path_set`) y podas de nodos seguros (`visited_safe`).
   - Aceptación garantizada de diamantes simples y diamantes anidados (múltiples referencias al mismo insumo o subreceta base sin bucles cerrados).
   - Detección y rechazo de auto-referencias directas ($A \to A$), ciclos cortos ($A \to B \to A$) y ciclos profundos ($A \to B \to C \to D \to A$).
   - Detección de ciclos internos en sub-ramas no adyacentes a la receta raíz.
   - Operaciones predictivas `would_create_cycle` y mapeo global `find_all_cycles`.
5. **Contratos, Reglas de Opciones Dinámicas & Simulación en Vivo (5D):**
   - Cardinalidad de selección de grupos dinámicos $[min, max]$.
   - Obligatoriedad de opciones por defecto en grupos requeridos ($min \ge 1 \implies \ge 1$ opción con `es_opcion_default=True`).
   - Restricción de repetición (`permite_repetir`): bloqueo ante selecciones duplicadas no permitidas.
   - Recargos de precios (`recargo_precio \ge 0`), impacto en precio neto, bruto con IVA y simulación de comandas POS sin alterar el escandallo base.

---

## 2. Métricas de Ejecución Automatizada

- **Backend Pytest (`oppytec-backend/tests/modules/recipes/`):**
  - Total: **125 tests**, 100% PASSED (0 fallos, 0 errores).
  - Tiempo de ejecución: **~4.3 segundos**.
  - Suites:
    1. `test_escandallo_invariants.py`: 14 tests (Hypothesis + Decimal + Ficha Técnica).
    2. `test_recipe_cycle_detection.py`: 21 tests (DAG, Diamantes, Ciclos $A \to B \to C \to D \to A$).
    3. `test_dynamic_options_rules.py`: 15 tests (Cardinalidad, Defaults, Recargos, Repetición).
    4. `test_recipes_application_and_api.py`: 40 tests (CRUD, RBAC 3 niveles, ProblemDetails RFC 7807).
    5. `test_domain_and_cycles.py`: 21 tests (Value Objects puros, entidades de dominio).
    6. `test_recipes_models_and_migration.py`: 8 tests (Modelos SQLAlchemy y migración Alembic 0008).
    7. `test_recipes_observability.py`: 6 tests (Spans OpenTelemetry y PII scrubbing).

- **Frontend Vitest (`oppytec-frontend/src/features/gestion/`):**
  - Total: **205 tests**, 100% PASSED (18 archivos de test).
  - Tiempo de ejecución: **~11 segundos**.
  - TypeScript: `pnpm --dir oppytec-frontend exec tsc --noEmit` $\rightarrow$ **0 errores**.
  - Build de Producción: `pnpm --dir oppytec-frontend run build` $\rightarrow$ **Vite build completado en 6.89s**.
