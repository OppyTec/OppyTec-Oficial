---
spec_id: ENG-RECIPES-AND-COMBOS
title: "Recetas, Combos Dinámicos y Grupos de Opciones Polimórficos"
audience: engineering_internal
domain_module: recipes
paired_spec: specs/business-domain/recipes-and-combos.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.95)"
last_verified_phase: "Fase 7"
---

# Recetas, Costeo y Combos Dinámicos con Grupos de Opciones Polimórficos — Especificación de Ingeniería

## Contrato Técnico

### 1. Arquitectura de Dominio DDD (`oppytec-backend/src/modules/recipes/`)

#### A. Capa de Dominio (`domain/`)
- **Value Objects Inmutables con Precisión `Decimal`:**
  - `ServingYield`: Valida porciones $> 0$, calcula costo unitario por porción dividiendo costo total por porciones usando `ROUND_HALF_UP`.
  - `IngredientQuantity`: Modela cantidad física neta y merma técnica porcentual ($0 \le m < 100$). Calcula la cantidad bruta requerida:
    $$\text{gross\_quantity} = \text{net\_quantity} \times \left(1 + \frac{\text{waste\_pct}}{100}\right)$$
  - `DynamicCostSummary`: Estructura tripartita inmutable que agrupa:
    - $\text{costo\_base}$: Costo con las opciones marcadas como `es_opcion_default = True`.
    - $\text{costo\_maximo}$ (Worst-Case): Combinación más desfavorable para blindaje de margen.
    - $\text{costo\_minimo}$ (Best-Case): Combinación más económica permitida.
    - Invariante analítica: $0 \le C_{\min} \le C_{\text{base}} \le C_{\max}$.
  - `OptionSelectionRule`: Valida cardinalidad $[min, max]$, obligatoriedad de al menos una opción default cuando $min \ge 1$, y restricción de repetición (`permite_repetir = False`).
- **Algoritmo de Detección Anti-Ciclos en Sub-Recetas (`check_recipe_cycles` / `would_create_cycle`):**
  - Implementado mediante recorrido DFS en Grafo Acíclico Dirigido (DAG).
  - Utiliza `path_set` para el rastreo de ancestros en la pila de recursión y `visited_safe` para memoización y poda de ramas verificadas.
  - Soporta grafos diamante (múltiples caminos hacia un mismo ingrediente o sub-receta común sin bucle).
  - Detecta y bloquea: auto-referencia directa ($A \to A$), ciclos cortos ($A \to B \to A$) y ciclos profundos ($A \to B \to C \to D \to A$).
  - Lanza `RecipeCycleError` con la secuencia exacta de nodos que conforman el ciclo.

#### B. Capa de Aplicación (`application/`)
- `RecipeService`:
  - Creación y actualización atómica de recetas, vinculación de ingredientes fijos y asociación con grupos de opciones.
  - Auto-detección del flag `es_dinamica` (se activa automáticamente si la receta posee al menos un grupo de opciones).
  - Cálculo transaccional de escandallo: resuelve costos unitarios PPP desde el inventario (`stock_items` / `registro_stock`) y desciende recursivamente sobre el árbol de sub-recetas.
  - Generación de ficha técnica operativa con escalamiento lineal de porciones y consolidación de los 14 alérgenos normados.
- `ComboService`:
  - Creación y mantenimiento de paquetes promocionales (estáticos y dinámicos).
  - Auto-detección del flag `es_dinamico`.
  - Cálculo reactivo de disponibilidad teórica de stock contrastando componentes fijos contra saldos de bodega.
- `OptionGroupService`:
  - Administración de biblioteca corporativa de grupos de opciones y creación ágil in-situ.
  - Validación de integridad: `OptionGroupInUseError` impide eliminar grupos asociados a recetas o combos activos.
- `RecipeCostSimulatorService`:
  - Simulación interactiva de costos y precios finales ante selecciones específicas de opciones y recargos emitidas por el POS o frontend.

#### C. Capa de Infraestructura y Persistencia Multi-Tenant (`infrastructure/`)
- **Aislamiento Multi-Tenant:**
  Todas las entidades heredan estrictamente de `TenantBase` para su particionamiento en esquemas dinámicos `tenant_*`.
- **Modelos de Persistencia (SQLAlchemy Core/ORM):**
  - `recetas`: Identificador `id` (BigInteger PK), `codigo` (`String(64)` unique), `nombre` (`String(180)`), `categoria_receta_id` (FK `categorias_recetas.id`), `es_subreceta` (Boolean), `es_dinamica` (Boolean), `porciones_rendimiento` (`Numeric(12, 4)`), `costo_total_calculado` (`Numeric(14, 2)`), `precio_venta_neto` (`Numeric(14, 2)`), `precio_venta_bruto` (`Numeric(14, 2)`), `iva_porcentaje` (`Numeric(5, 2)` default 19.00), `iva_incluido` (Boolean), `imagen_url`, `preparacion` (Text), `tiempo_preparacion_minutos` (Integer), `AuditTimestampsMixin`, `SoftDeleteMixin`.
  - `receta_ingredientes`: `id` (PK), `receta_id` (FK `recetas.id` ON DELETE CASCADE), `producto_id` (FK `productos.id` nullable), `subreceta_id` (FK `recetas.id` nullable), `cantidad_receta` (`Numeric(12, 4)`), `porcentaje_merma` (`Numeric(6, 2)`), `bodega_consumo_id` (FK `bodegas.id` nullable).
    - Restricción XOR polimórfica: `CHECK ((producto_id IS NOT NULL AND subreceta_id IS NULL) OR (producto_id IS NULL AND subreceta_id IS NOT NULL))`.
  - `grupos_opciones`: `id` (PK), `nombre` (`String(120)`), `descripcion`, `seleccion_minima` (Integer), `seleccion_maxima` (Integer), `permite_repetir` (Boolean), `AuditTimestampsMixin`, `SoftDeleteMixin`.
  - `grupo_opciones_items`: `id` (PK), `grupo_id` (FK `grupos_opciones.id` ON DELETE CASCADE), `producto_id` (FK nullable), `receta_id` (FK nullable), `cantidad` (`Numeric(12, 4)`), `es_opcion_default` (Boolean), `recargo_precio` (`Numeric(14, 2)`), `orden` (Integer).
    - Restricción XOR polimórfica: `CHECK ((producto_id IS NOT NULL AND receta_id IS NULL) OR (producto_id IS NULL AND receta_id IS NOT NULL))`.
  - `receta_grupos_opciones`: `id` (PK), `receta_id` (FK `recetas.id` ON DELETE CASCADE), `grupo_id` (FK `grupos_opciones.id` ON DELETE CASCADE), `orden` (Integer), `es_requerido` (Boolean), `UNIQUE(receta_id, grupo_id)`.
  - `combos`: `id` (PK), `codigo` (`String(64)` unique), `nombre` (`String(180)`), `categoria_combo_id` (FK), `es_dinamico` (Boolean), `precio_venta_neto` (`Numeric(14, 2)`), `precio_venta_bruto` (`Numeric(14, 2)`), `costo_total_calculado` (`Numeric(14, 2)`), `imagen_url`, `AuditTimestampsMixin`, `SoftDeleteMixin`.
  - `combo_items`: `id` (PK), `combo_id` (FK `combos.id` ON DELETE CASCADE), `producto_id` (FK nullable), `receta_id` (FK nullable), `cantidad` (`Numeric(12, 4)`).
    - Restricción XOR polimórfica: `CHECK ((producto_id IS NOT NULL AND receta_id IS NULL) OR (producto_id IS NULL AND receta_id IS NOT NULL))`.
  - `combo_grupos_opciones`: `id` (PK), `combo_id` (FK `combos.id` ON DELETE CASCADE), `grupo_id` (FK `grupos_opciones.id` ON DELETE CASCADE), `orden` (Integer), `es_requerido` (Boolean), `UNIQUE(combo_id, grupo_id)`.
  - `categorias_recetas` y `categorias_combos`: `id` (PK), `nombre` (`String(100)`), `color` (`String(32)`), `icono` (`String(64)`), `orden` (Integer), `AuditTimestampsMixin`, `SoftDeleteMixin`.
- **Migración Alembic Correlativa Lineal 0008:**
  - Archivo: `oppytec-backend/alembic/versions/0008_tenant_recipes_combos_dynamic_option_groups.py`.
  - Predecesora lineal: `0007_public_system_plans_extension_and_saas_policy`.
  - Despliegue seguro sobre esquemas dinámicos de clientes y esquema base de plantilla `tenant_base`.

#### D. Capa de Presentación REST (`presentation/router.py`)
- Respuestas normalizadas **RFC 7807** (`ProblemDetails`) con códigos de estado semánticos:
  - `400 Bad Request`: Infracción de cardinalidad, merma técnica fuera de rango o cantidad menor o igual a cero.
  - `403 Forbidden`: Intento de acceso cross-tenant (IDOR) o falta de privilegios RBAC.
  - `404 Not Found`: Receta, combo o grupo de opciones no encontrado.
  - `409 Conflict`: Detección de ciclo de recursión en subrecetas (`RECIPE_CYCLE_DETECTED`).
  - `422 Unprocessable Entity`: Fallo de validación estructural o incompatibilidad de tipos.
- **Rutas Principales:**
  - `GET /api/v1/recipes`, `POST /api/v1/recipes`, `GET /api/v1/recipes/{id}`, `PUT /api/v1/recipes/{id}`, `DELETE /api/v1/recipes/{id}`.
  - `POST /api/v1/recipes/{id}/simulate-cost`: Simulación de costo en vivo ante selecciones específicas.
  - `GET /api/v1/recipes/{id}/kitchen-sheet`: Ficha técnica escalable para cocina.
  - `GET /api/v1/recipes/categories`, `POST /api/v1/recipes/categories`.
  - `GET /api/v1/combos`, `POST /api/v1/combos`, `GET /api/v1/combos/{id}`, `PUT /api/v1/combos/{id}`, `DELETE /api/v1/combos/{id}`.
  - `GET /api/v1/combos/categories`, `POST /api/v1/combos/categories`.
  - `GET /api/v1/recipes/option-groups`, `POST /api/v1/recipes/option-groups`, `PUT /api/v1/recipes/option-groups/{id}`, `DELETE /api/v1/recipes/option-groups/{id}`.

---

### 2. Notificaciones en Tiempo Real (WebSocket Zero-Polling)

- Publicación asíncrona mediante Redis Pub/Sub hacia el canal `/api/v1/ws/realtime`:
  - `recipes.recipe.updated`: Emitido tras mutaciones de recetas para invalidar caches de TanStack Query `["recipes"]`.
  - `recipes.combo.updated`: Emitido ante creación, edición o borrado de combos para refrescar `["combos"]`.
  - `recipes.cost.recalculated`: Emitido cuando una transacción de inventario altera el PPP de insumos utilizados en recetas.

---

### 3. Matriz RBAC de 3 Niveles

- `recipes.recipe.read`: Lectura de recetas, visualización de ingredientes y fichas técnicas.
- `recipes.recipe.write`: Creación, actualización y duplicación de recetas e ingredientes.
- `recipes.recipe.delete`: Eliminación y desactivación lógica de recetas.
- `recipes.recipe.costs`: Visualización de costos PPP, márgenes brutos/netos y paneles financieros de escandallo.
- `recipes.combo.read`: Lectura y visualización de catálogo de combos.
- `recipes.combo.write`: Creación y actualización de paquetes de combos y promociones.
- `recipes.combo.delete`: Eliminación de combos.
- `recipes.options.manage`: Creación, edición y administración de biblioteca de grupos de opciones.

---

### 4. Observabilidad OpenTelemetry & Sentry

- **Spans Instrumentados:**
  - `recipe.escandallo.calculate`: Tiempo de cómputo del árbol de costos y resolución PPP.
  - `recipe.cycle_detection.run`: Duración de la verificación DFS del DAG de dependencias.
  - `recipe.kitchen_sheet.generate`: Generación y escalamiento de porciones culinarias.
  - `combo.availability.check`: Cálculo de existencias disponibles para combos.
- **Atributos de Contexto y Anonimización:**
  - Registro de `tenant_id`, `recipe_id`, `combo_id`, `is_dynamic` y `allergen_count`.
  - Sanitización estricta de datos personales sensibles (PII Scrubbing).

---

### 5. Interfaz Frontend React 19 (`oppytec-frontend/src/features/gestion/`)

- **Estructura Arquitectónica:**
  - `types.ts`: Contratos canónicos `Receta`, `IngredienteFijo`, `GrupoOpciones`, `GrupoOpcionesItem`, `Combo`, `DynamicCostResult`, `FichaTecnica`.
  - Hooks reactivos: `useRecetas.ts`, `useCombos.ts`, `useGruposOpciones.ts`.
  - Vistas: `GestionPage.tsx`, `GestionTabNav.tsx`, `RecetasView.tsx`, `CombosView.tsx`.
  - Componentes de presentación: `RecetasTable.tsx`, `CombosTable.tsx`, `RecetasToolbar.tsx`, `CombosToolbar.tsx`, `RecetaMobileCard.tsx`, `ComboMobileCard.tsx`.
  - Modales:
    - `RecetaDialog.tsx`: Asistente en 3 pestañas (General, Ingredientes Fijos, Opciones Dinámicas) con panel lateral flotante de escandallo en vivo ($C_{\text{base}}$, $C_{\max}$, márgenes).
    - `ComboDialog.tsx`: Formulario de configuración de paquetes fijos y grupos configurables.
    - `OptionGroupSelectorModal.tsx`: Explorador y creador in-situ de grupos de opciones.
    - `RecetaDetalleModal.tsx`: Visualizador de ficha técnica escalable e imprimible con estilos `@media print`.
    - `AllergenBadge.tsx`: Visualización de los 14 alérgenos alimentarios con tooltips bilingües.
- **Internacionalización y Multi-Moneda FX:**
  - Namespace bilingüe `src/shared/i18n/locales/{es,en}/recipes.json` con 100% de cobertura y cero cadenas hardcodeadas.
  - Multi-Moneda FX mediante `currencyEngine.ts` con escalamiento de $10^8$ `BigInt` (CLP, USD, EUR, BRL, UF) y componentes `MoneyBadge` y `formatMoney`.

---

## Invariantes

1. **Cero Coma Flotante IEEE 754:**
   Todos los cálculos monetarios, de escandallo, márgenes y cantidades operan con precisión `Decimal` en backend y enteros escalados $10^8$ `BigInt` en frontend.
2. **Grafo Acíclico Dirigido en Sub-Recetas:**
   Queda estrictamente prohibida cualquier dependencia circular en el grafo de recetas ($A \to \dots \to A$).
3. **Invariante Tripartita de Costos:**
   Para toda receta o combo dinámico: $0 \le C_{\min} \le C_{\text{base}} \le C_{\max}$.
4. **Rendimiento de Porciones Estricto:**
   $\text{porciones\_rendimiento} > 0$.
5. **Rango de Merma Técnica:**
   $0\% \le \text{porcentaje\_merma} < 100\%$.
6. **Cardinalidad Válida de Opciones:**
   $1 \le \text{seleccion\_minima} \le \text{seleccion\_maxima}$.
7. **Opción por Defecto Obligatoria:**
   Todo grupo de opciones con $\text{seleccion\_minima} \ge 1$ debe contener al menos un ítem con $\text{es\_opcion\_default} = \text{True}$.
8. **Aislamiento Multi-Tenant e Inmunidad IDOR:**
   Acceso restringido al esquema del tenant autenticado; cualquier consulta a recursos de otro tenant resulta en HTTP 403 `CrossTenantAccessError`.

---

## Evaluación JEV Sistema 1

jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- **Primitiva:** `Jev.boolean`
- **Umbral de confianza:** `0.95` (bajo umbral → revisión humana / camino determinista).
- **Justificación:** Los cálculos de escandallo gastronómico, márgenes brutos/netos, resolución de precios, validaciones de cardinalidad y algoritmos de prevención de ciclos en grafos DAG son operaciones matemáticas y de integridad referencial puramente deterministas. No admiten inferencia heurística ni aproximaciones no verificadas.

---

## Pruebas (Co-Creación 1:1)

### Backend (Pytest)
- `oppytec-backend/tests/modules/recipes/test_escandallo_invariants.py`: Invariantes matemáticas de escandallo con Hypothesis, verificación de orden tripartito $C_{\min} \le C_{\text{base}} \le C_{\max}$ y fórmulas de merma técnica.
- `oppytec-backend/tests/modules/recipes/test_recipe_cycle_detection.py`: Algoritmo DAG de detección de ciclos, aceptación de diamantes y rechazo de autorreferencias $A \to B \to C \to A$.
- `oppytec-backend/tests/modules/recipes/test_dynamic_options_rules.py`: Validación de cardinalidad mín/máx, opciones por defecto y recargos.
- `oppytec-backend/tests/modules/recipes/test_recipes_application_and_api.py`: CRUD transaccional de recetas, combos y opciones con respuestas RFC 7807.
- `oppytec-backend/tests/modules/recipes/test_domain_and_cycles.py`: Pruebas de Value Objects puros y validaciones de dominio.
- `oppytec-backend/tests/modules/recipes/test_recipes_models_and_migration.py`: Modelos SQLAlchemy y ejecución de migración Alembic 0008.
- `oppytec-backend/tests/modules/recipes/test_recipes_observability.py`: Verificación de spans OpenTelemetry y scrubbing de datos sensibles.
- `oppytec-backend/tests/security_redteam/test_13_recipes_combos_offensive_security_and_rbac.py`: 22 pruebas de seguridad ofensiva Kali, validación RBAC de 3 niveles y blindaje contra IDOR cross-tenant.

### Frontend (Vitest)
- `oppytec-frontend/src/features/gestion/__tests__/RecetasTable.test.tsx`: Renderizado multidimensional, semáforos de margen y badges dinámicos.
- `oppytec-frontend/src/features/gestion/__tests__/CombosTable.test.tsx`: Desglose de componentes fijos y dinámicos, disponibilidad y precios.
- `oppytec-frontend/src/features/gestion/__tests__/RecetaDialog.test.tsx`: Formulario de 3 pestañas, agregado de insumos y panel de escandallo en vivo.
- `oppytec-frontend/src/features/gestion/__tests__/RecetaComboModals.test.tsx`: Flujos de modales combinados y selectores in-situ.
- `oppytec-frontend/src/features/gestion/__tests__/FichaTecnicaAllergens.test.tsx`: Escalamiento de porciones y presentación de los 14 alérgenos.
- `oppytec-frontend/src/features/gestion/__tests__/RecipesI18nAndFx.test.tsx`: Cobertura i18n 100% `es`/`en` y cálculos FX en punto fijo.
- `oppytec-frontend/src/features/gestion/hooks/__tests__/useRecetas.test.ts`: Hook reactivo de recetas y TanStack Query cache.
- `oppytec-frontend/src/features/gestion/hooks/__tests__/useCombos.test.ts`: Hook reactivo de combos.
- `oppytec-frontend/src/features/gestion/hooks/__tests__/useGruposOpciones.test.ts`: Hook de biblioteca de grupos de opciones.
