# 📋 PLAN MAESTRO DE CONTROL Y EJECUCIÓN: MÓDULO DE GESTIÓN — RECETAS Y COMBOS DINÁMICOS CON GRUPOS DE OPCIONES POLIMÓRFICOS (`/gestion?tab=recetas`, `/gestion?tab=combos`)

> **Regla de Gobernanza Inviolable:** Este documento es el tablero de control de ejecución estricto de la refactorización de Recetas, Combos y Opciones de OppyTec v2.0.  
> Cada paso debe ser **100% corroborado y aprobado** antes de pasar al siguiente.  
> **Solo cuando se finalicen todos los pasos**, este documento podrá ser archivado o marcado como completado.  
> **Fuentes de Verdad Históricas (100% Solo Lectura):**  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Gestion/` (`RecetaDialog.tsx`, `ComboDialog.tsx`, `GrupoOpcionesDialog.tsx`, `GrupoOpcionesSeccion.tsx`, `CategoriaRecetaSeccion.tsx`, `CategoriaComboSeccion.tsx`, `RecetaDetalleDialog.tsx`, `types.ts`, `useGestion.ts`)  
> - `OppyTec-Legacy/OppyTec_Backend/src/operations/routers/` (`recipe_router.py`, `combo_router.py`, `grupo_opciones_router.py`)  
> - `OppyTec-Legacy/OppyTec_Backend/src/operations/services/` (`combo_service.py`, `grupo_opciones_service.py`)  
> - `OppyTec-Legacy/OppyTec_Backend/tests/dummy-data/` (`recetas.md`, `combos.md`, `Grupo-Opciones.md`)  
> **Destinos de Construcción en OppyTec v2.0:**  
> - Backend: `oppytec-backend/src/modules/recipes/` (DDD: Domain, Application, Infrastructure, Presentation)  
> - Base de Datos: Migración Alembic `0008` (`0008_tenant_recipes_combos_dynamic_option_groups.py` correlativo tras 0007)  
> - Frontend: `oppytec-frontend/src/features/gestion/` (`recetas/`, `combos/`, `options/`, `hooks/`, `types.ts`, `GestionPage.tsx`)  
> **Alcance de Certificación:** Se cubren rigurosamente las **Etapas 1 a 4 del DAG**. La **Etapa 5 (Playwright E2E)** queda desacoplada y omitida para fases posteriores por requerimiento explícito.

---

## 📊 Estado General del Proyecto

- [x] **Fase 1:** Arquitectura de Dominio DDD, Esquemas PostgreSQL `tenant_*` y Migración Alembic 0008 (Modelos polimórficos de Recetas/Combos con Grupos de Opciones integrados) — **COMPLETADO**
- [x] **Fase 2:** Motor Backend FastAPI, Escandallos Dinámicos & Transaccionalidad (Cálculo de costos Worst-Case/Default, Árbol de sub-recetas, Endpoints RFC 7807, RBAC 3 niveles `recipes.*`) — **COMPLETADO**
- [x] **Fase 3:** Frontend Feature Core & Hooks Reactivos (`types.ts`, `useRecetas.ts`, `useCombos.ts`, `useGruposOpciones.ts`, TanStack Query v5 + WebSockets realtime) — **COMPLETADO**
- [x] **Fase 4:** Vistas de Gestión Integradas en `/gestion` (Reestructuración de Tabs: eliminación de pestaña aislada `grupos-opciones`, incorporación de badges ⚡ `Dinámica`/`Fija`, tablas multidimensionales y Mobile-First táctil) — **COMPLETADO**
- [x] **Fase 5:** Modales Operativos Especializados (`RecetaDialog.tsx` con tabs de Ingredientes Fijos y Opciones Dinámicas, `ComboDialog.tsx`, `OptionGroupSelectorModal.tsx` in-situ y `RecetaDetalleModal.tsx`) — **COMPLETADO**
- [x] **Fase 6:** Asistente de Escandallo y Preparación (Árbol de costos en tiempo real, desglose de márgenes brutos/netos, ficha técnica imprimible y alérgenos de insumos) — **COMPLETADO**
- [x] **Fase 7:** Capas Cruzadas, i18n 100% `es`/`en` (`recipes.json`), Multi-Moneda FX con `Decimal`, Observabilidad OpenTelemetry, Testing 5D (Vitest + Pytest), Bóvedas OpenSpec y Sincronización Graphify — **COMPLETADO (100%)**

---

## 🔍 Detalle y Criterios de Aceptación por Fase

---

### [x] FASE 1: Arquitectura de Dominio DDD, Esquemas PostgreSQL `tenant_*` y Migración Alembic 0008 (Completado)
- [x] **1.1** Modelado de Persistencia Multi-Tenant en `oppytec-backend/src/modules/recipes/infrastructure/models.py`:
  - Todas las tablas deben heredar estrictamente de `TenantBase` para residir en esquemas dinámicos `tenant_*` aislados por cliente.
  - **Tabla `recetas`:**
    - Campos: `id` (BigInteger PK), `codigo` (`String(64)` unique), `nombre` (`String(180)`), `descripcion` (`Text` nullable), `categoria_receta_id` (FK `categorias_recetas.id` nullable), `es_subreceta` (`Boolean` default `False`), `es_dinamica` (`Boolean` default `False`), `porciones_rendimiento` (`Numeric(12, 4)` default `1.0000`), `costo_total_calculado` (`Numeric(14, 2)` default `0.00`), `precio_venta_neto` (`Numeric(14, 2)` default `0.00`), `precio_venta_bruto` (`Numeric(14, 2)` default `0.00`), `iva_porcentaje` (`Numeric(5, 2)` default `19.00`), `iva_incluido` (`Boolean` default `True`), `imagen_url` (`String(512)` nullable), `preparacion` (`Text` nullable), `video_url` (`String(512)` nullable), `documento_url` (`String(512)` nullable), `tiempo_preparacion_minutos` (`Integer` nullable), `AuditTimestampsMixin`, `SoftDeleteMixin`, `TranslatableI18nMixin`.
    - Índices: `(codigo)`, `(nombre)`, `(categoria_receta_id)`, `(es_dinamica)`.
  - **Tabla `receta_ingredientes` (Ingredientes Fijos del Escandallo):**
    - Campos: `id` (BigInteger PK), `receta_id` (FK `recetas.id` ON DELETE CASCADE), `producto_id` (FK `productos.id` nullable), `subreceta_id` (FK `recetas.id` nullable), `cantidad_receta` (`Numeric(12, 4)`), `porcentaje_merma` (`Numeric(6, 2)` default `0.00`), `bodega_consumo_id` (FK `bodegas.id` nullable), `notas` (`String(255)` nullable), `AuditTimestampsMixin`.
    - Restricción de integridad: `CHECK ((producto_id IS NOT NULL AND subreceta_id IS NULL) OR (producto_id IS NULL AND subreceta_id IS NOT NULL))`.
  - **Tabla `grupos_opciones` (Biblioteca de Modificadores Dinámicos):**
    - Entidad reutilizable o creada in-situ para recetas o combos.
    - Campos: `id` (BigInteger PK), `nombre` (`String(120)`), `descripcion` (`Text` nullable), `seleccion_minima` (`Integer` default `1`), `seleccion_maxima` (`Integer` default `1`), `permite_repetir` (`Boolean` default `False`), `AuditTimestampsMixin`, `SoftDeleteMixin`, `TranslatableI18nMixin`.
  - **Tabla `grupo_opciones_items` (Opciones Específicas Seleccionables):**
    - Campos: `id` (BigInteger PK), `grupo_id` (FK `grupos_opciones.id` ON DELETE CASCADE), `producto_id` (FK `productos.id` nullable), `receta_id` (FK `recetas.id` nullable para sub-recetas / platos completos), `cantidad` (`Numeric(12, 4)` default `1.0000` porción o peso), `es_opcion_default` (`Boolean` default `False` para cálculo de escandallo base), `recargo_precio` (`Numeric(14, 2)` default `0.00` recargo bruto adicional si se elige), `orden` (`Integer` default `0`), `AuditTimestampsMixin`.
    - Restricción polimórfica: `CHECK ((producto_id IS NOT NULL AND receta_id IS NULL) OR (producto_id IS NULL AND receta_id IS NOT NULL))`.
  - **Tabla asociativa `receta_grupos_opciones`:**
    - Enlace Many-to-Many entre `recetas` y `grupos_opciones` que habilita **Recetas Dinámicas**.
    - Campos: `id` (BigInteger PK), `receta_id` (FK `recetas.id` ON DELETE CASCADE), `grupo_id` (FK `grupos_opciones.id` ON DELETE CASCADE), `orden` (`Integer` default `0`), `es_requerido` (`Boolean` default `True`), `AuditTimestampsMixin`.
    - Restricción: `UNIQUE(receta_id, grupo_id)`.
  - **Tabla `combos`:**
    - Promociones y paquetes gastronómicos comercializables.
    - Campos: `id` (BigInteger PK), `codigo` (`String(64)` unique), `nombre` (`String(180)`), `descripcion` (`Text` nullable), `categoria_combo_id` (FK `categorias_combos.id` nullable), `es_dinamico` (`Boolean` default `False`), `precio_venta_neto` (`Numeric(14, 2)` default `0.00`), `precio_venta_bruto` (`Numeric(14, 2)` default `0.00`), `iva_porcentaje` (`Numeric(5, 2)` default `19.00`), `iva_incluido` (`Boolean` default `True`), `costo_total_calculado` (`Numeric(14, 2)` default `0.00`), `imagen_url` (`String(512)` nullable), `AuditTimestampsMixin`, `SoftDeleteMixin`, `TranslatableI18nMixin`.
  - **Tabla `combo_items` (Componentes Fijos del Combo):**
    - Campos: `id` (BigInteger PK), `combo_id` (FK `combos.id` ON DELETE CASCADE), `producto_id` (FK `productos.id` nullable), `receta_id` (FK `recetas.id` nullable), `cantidad` (`Numeric(12, 4)` default `1.0000`), `AuditTimestampsMixin`.
    - Restricción: `CHECK ((producto_id IS NOT NULL AND receta_id IS NULL) OR (producto_id IS NULL AND receta_id IS NOT NULL))`.
  - **Tabla asociativa `combo_grupos_opciones`:**
    - Enlace Many-to-Many entre `combos` y `grupos_opciones` que habilita **Combos Dinámicos**.
    - Campos: `id` (BigInteger PK), `combo_id` (FK `combos.id` ON DELETE CASCADE), `grupo_id` (FK `grupos_opciones.id` ON DELETE CASCADE), `orden` (`Integer` default `0`), `es_requerido` (`Boolean` default `True`), `AuditTimestampsMixin`.
    - Restricción: `UNIQUE(combo_id, grupo_id)`.
  - **Tablas de Categorías Especializadas:**
    - `categorias_recetas`: `id`, `nombre`, `color`, `icono`, `orden`, `AuditTimestampsMixin`, `SoftDeleteMixin`.
    - `categorias_combos`: `id`, `nombre`, `color`, `icono`, `orden`, `AuditTimestampsMixin`, `SoftDeleteMixin`.
- [x] **1.2** Migración Correlativa Lineal Alembic `0008`:
  - Archivo: `oppytec-backend/alembic/versions/0008_tenant_recipes_combos_dynamic_option_groups.py`.
  - `down_revision = "0007_public_system_plans_extension_and_saas_policy"`.
  - Iteración segura e idempotente sobre todos los esquemas `tenant_*` existentes y plantilla `tenant_base`.
  - Creación de índices compuestos, claves foráneas `ON DELETE CASCADE` / `RESTRICT` y checks relacionales.
- [x] **1.3** Primitivas de Dominio DDD y Algoritmos de Escandallo (`domain/`):
  - Ubicación: `oppytec-backend/src/modules/recipes/domain/`.
  - Value Objects inmutables con precisión `Decimal`:
    - `ServingYield`: porciones con validación $> 0$ y cálculo de costo unitario por porción.
    - `IngredientQuantity`: cantidad física y factor de merma porcentual ($0 \le m < 100$).
    - `DynamicCostSummary`: estructura de costo tripartito:
      - $\text{Costo Base}$ (calculado con las opciones marcadas como `es_opcion_default`).
      - $\text{Costo Máximo}$ (escenario más desfavorable o *worst-case* para protección de márgenes).
      - $\text{Costo Mínimo}$ (escenario más económico).
  - Algoritmo de Detección Anti-Recursión Cíclica en Subrecetas (`check_recipe_cycles`): grafo acíclico dirigido (DAG) que impide que la Receta A contenga a la Receta B si B ya contiene a A.

---

### [x] FASE 2: Motor Backend FastAPI, Escandallos Dinámicos & Transaccionalidad (Completado)
- [x] **2.1** Servicios de Aplicación Transaccionales (`application/`):
  - `RecipeService`:
    - Creación y edición atómica de recetas con sus ingredientes fijos y vinculación de grupos de opciones.
    - Detección automática del flag `es_dinamica` (se activa automáticamente si la receta posee al menos un grupo de opciones asociado).
    - Cálculo transaccional de escandallo: consulta de costo unitario PPP vigente de cada insumo desde `stock_items` / `registro_stock` y resolución recursiva de sub-recetas.
    - Cálculo de margen neto y margen bruto en base al precio de venta y costo de escandallo.
  - `ComboService`:
    - Creación y edición de combos fijos y combos dinámicos.
    - Detección automática del flag `es_dinamico`.
    - Cálculo de disponibilidad teórica de stock en base a bodegas de consumo asignadas.
  - `OptionGroupService`:
    - Gestión de grupos de opciones: creación rápida in-situ (vinculada al vuelo a una receta o combo) o creación en biblioteca general.
    - Validación de reglas de cardinalidad: $1 \le \text{seleccion\_minima} \le \text{seleccion\_maxima}$.
    - Verificación de consistencia: al menos un ítem debe estar marcado como `es_opcion_default = True` en cada grupo obligatorio.
  - `RecipeCostSimulatorService`:
    - Simulación en vivo de costos ante combinaciones elegidas por el usuario.
    - Endpoint para consumo del POS o Frontend que calcula el impacto financiero antes de emitir la venta.
- [x] **2.2** Presentación REST y Enrutador FastAPI (`presentation/router.py`):
  - Todos los endpoints con respuestas normalizadas **RFC 7807** (`ProblemDetails`).
  - **Endpoints de Recetas:**
    - `GET /api/v1/recipes`: Listar recetas con filtros por tipo (`todas`, `estaticas`, `dinamicas`, `subrecetas`), categoría, área operativa y búsqueda.
    - `GET /api/v1/recipes/{id}`: Detalle completo con ingredientes fijos, grupos de opciones, cálculo de escandallo y árbol de subrecetas.
    - `POST /api/v1/recipes`: Crear receta (estática o dinámica).
    - `PUT /api/v1/recipes/{id}`: Actualizar receta y regenerar asientos de escandallo.
    - `DELETE /api/v1/recipes/{id}`: Soft-delete con verificación de uso en combos o sub-recetas.
    - `POST /api/v1/recipes/{id}/simulate-cost`: Simular costo ante una selección particular de opciones dinámicas.
    - `GET /api/v1/recipes/categories`: Listar y gestionar categorías de recetas.
  - **Endpoints de Combos:**
    - `GET /api/v1/combos`: Listar combos con disponibilidad de inventario y estado.
    - `GET /api/v1/combos/{id}`: Detalle completo de combo (ítems fijos + grupos de opciones).
    - `POST /api/v1/combos`: Crear combo promocional.
    - `PUT /api/v1/combos/{id}`: Actualizar combo.
    - `DELETE /api/v1/combos/{id}`: Soft-delete de combo.
    - `GET /api/v1/combos/categories`: Listar y gestionar categorías de combos.
  - **Endpoints de Grupos de Opciones:**
    - `GET /api/v1/recipes/option-groups`: Listar biblioteca de grupos de opciones del tenant.
    - `POST /api/v1/recipes/option-groups`: Crear nuevo grupo de opciones con sus ítems.
    - `PUT /api/v1/recipes/option-groups/{id}`: Actualizar grupo e ítems.
    - `DELETE /api/v1/recipes/option-groups/{id}`: Eliminar grupo (con validación de uso en recetas o combos activos).
- [x] **2.3** Matriz de Seguridad y Guardias RBAC de 3 Niveles:
  - `recipes.recipe.read`: Consulta de recetas y fichas técnicas.
  - `recipes.recipe.write`: Creación y edición de recetas e ingredientes.
  - `recipes.recipe.delete`: Eliminación de recetas.
  - `recipes.recipe.costs`: Visualización de costos PPP y márgenes confidenciales.
  - `recipes.combo.read`: Consulta de combos promocionales.
  - `recipes.combo.write`: Creación y edición de combos.
  - `recipes.combo.delete`: Eliminación de combos.
  - `recipes.options.manage`: Gestión de biblioteca de grupos de opciones.
- [x] **2.4** Notificaciones en Tiempo Real (WebSocket Zero-Polling):
  - Emisión de eventos Redis Pub/Sub hacia `/api/v1/ws/realtime`:
    - `recipes.recipe.updated`: Refresco instantáneo de tablas de recetas.
    - `recipes.combo.updated`: Refresco de disponibilidad y precios de combos.
    - `recipes.cost.recalculated`: Notificación ante fluctuaciones de PPP que alteren el costo de escandallo.

---

### [x] FASE 3: Frontend Feature Core & Hooks Reactivos en React 19 (Completado)
- [x] **3.1** Contratos TypeScript de Dominio en `oppytec-frontend/src/features/gestion/types.ts`:
  - `Receta`: id, codigo, nombre, descripcion, es_subreceta, es_dinamica, porciones, costo_total, costo_porcion, precio_neto, precio_bruto, margen_neto, margen_bruto, ingredientes_fijos (`IngredienteFijo[]`), grupos_opciones (`RecetaGrupoOpcion[]`).
  - `IngredienteFijo`: id, producto_id, subreceta_id, nombre, unidad, cantidad, merma_pct, costo_unitario, costo_total.
  - `GrupoOpciones`: id, nombre, descripcion, min_selecciones, max_selecciones, permite_repetir, items (`GrupoOpcionesItem[]`).
  - `GrupoOpcionesItem`: id, producto_id, receta_id, type (`"producto"` | `"subreceta"`), nombre, cantidad_porcion, es_default, recargo_precio, costo_referencial.
  - `Combo`: id, codigo, nombre, es_dinamico, items_fijos (`ComboItemFijo[]`), grupos_opciones (`ComboGrupoOpcion[]`), precio_neto, precio_bruto, costo_base, margen_pct.
  - `DynamicCostResult`: desglose de costos dinámicos (costo base default, costo peor caso, costo mejor caso, desglose de opciones).
- [x] **3.2** Hook de Gestión de Recetas `useRecetas.ts`:
  - Consumo reactivo con TanStack Query v5 (`useQuery`, `useMutation`).
  - Filtrado en memoria o servidor: búsqueda predictiva, filtro por categoría, filtro de tipo (`Todas`, `Solo Estáticas`, `Solo Dinámicas`, `Sub-recetas`).
  - Invalidador quirúrgico de cache ante eventos WebSocket `recipes.recipe.updated`.
- [x] **3.3** Hook de Gestión de Combos `useCombos.ts`:
  - Carga paginada de combos con cálculo reactivo de disponibilidad según inventario.
  - Filtro por categorías de combos y buscador rápido.
  - Mutaciones optimistas para crear, editar y eliminar combos.
- [x] **3.4** Hook de Biblioteca de Opciones `useGruposOpciones.ts`:
  - Cache compartido de grupos de opciones para auto-completado y reutilización en modales.
  - Creación optimista in-situ de nuevos grupos sin salir del formulario de la receta.

---

### [x] FASE 4: Vistas de Gestión Integradas en `/gestion` (Completado)
- [x] **4.1** Reestructuración de Navegación en `GestionPage.tsx`:
  - Simplificación y ordenamiento jerárquico de pestañas:
    1. **Pestaña 1:** `Insumos & Productos` (`/gestion?tab=productos`).
    2. **Pestaña 2:** `Recetas & Escandallos` (`/gestion?tab=recetas`).
    3. **Pestaña 3:** `Combos & Promociones` (`/gestion?tab=combos`).
  - **Eliminación definitiva de la pestaña aislada `grupos-opciones`:** ya no existe como sección separada en la navegación principal; ahora reside de forma orgánica como componente integral dentro de Recetas y Combos.
- [x] **4.2** Vista de Recetas (`/gestion?tab=recetas`):
  - Componente `SectionHeader` centrado:
    - Título: `"Recetas y Fichas Técnicas"`.
    - Subtítulo: `"Escandallos gastronómicos, sub-recetas y opciones dinámicas"`.
    - Ícono: `ChefHat` de `lucide-react`.
    - Color identificador: `#f59e0b` (ámbar gastronómico / dorado culinary).
  - Barra de herramientas unificada (`RecetasToolbar.tsx`):
    - Buscador reactivo por nombre, código o ingrediente constituyente.
    - Selector de categorías de recetas con badges temáticos.
    - Toggle de filtro de tipo:
      - 🔘 `Todas`
      - ⚡ `Dinámicas` (con opciones personalizables)
      - 📜 `Estáticas` (fórmulas fijas)
      - 🥣 `Sub-recetas` (preparaciones intermedias para otras recetas)
    - Botón primario: `"+ Nueva Receta"`.
    - Botón secundario: `"Categorías de Recetas"`.
  - Tabla de Recetas Multidimensional (`RecetasTable.tsx`):
    - **Badge identificador:** ⚡ `Dinámica` (púrpura) o 📜 `Fija` (azul pizarra).
    - **Ficha Técnica & Código:** Nombre, porciones de rendimiento y categoría.
    - **Estructura de Insumos:** Indicador de $N$ ingredientes fijos $+ M$ grupos de opciones dinámicos.
    - **Costo Escandallo:** Costo base por porción y costo total valorizado al PPP.
    - **Precios & Margen:** Precio de venta neto/bruto y porcentaje de margen de ganancia con semáforo visual (🟢 $\ge 65\%$, 🟡 $40-64\%$, 🔴 $< 40\%$).
    - **Acciones Rápidas:** Ver Ficha Técnica (`Eye`), Editar (`Pencil`), Duplicar (`Copy`), Eliminar (`Trash2`).
- [x] **4.3** Vista de Combos (`/gestion?tab=combos`):
  - Componente `SectionHeader` centrado:
    - Título: `"Combos y Promociones"`.
    - Subtítulo: `"Menús completos, paquetes y combos dinámicos comercializables"`.
    - Ícono: `Boxes` de `lucide-react`.
    - Color identificador: `#ec4899` (rosa/magenta promocional).
  - Barra de herramientas y tabla con desglose de ítems fijos y grupos configurables.
- [x] **4.4** Adaptabilidad Mobile-First Táctil:
  - Tarjetas colapsables optimizadas para tablet de cocina y smartphone con touch targets $\ge 44\text{px}$.
  - Despliegue interactivo del desglose de opciones y porciones al tocar la tarjeta.

---

### [x] FASE 5: Modales Operativos Especializados (Completado)
- [x] **5.1** Modal Maestro de Recetas `RecetaDialog.tsx` (Re-arquitectura Completa):
  - Formulario estructurado en 3 pasos / pestañas internas:
    - **Pestaña 1: Información General:**
      - Nombre de la receta, código interno / SKU, categoría y descripción.
      - Rendimiento en porciones (default 1).
      - Modalidad: Toggle selector `"Receta Estática (Ingredientes Fijos)"` vs `"Receta Dinámica (Con Opciones del Cliente)"`.
      - Precios de venta (Neto, IVA %, Bruto) y cálculo de margen en tiempo real contra el escandallo.
      - Foto principal, galería multimedia, tiempo de elaboración, video y documento PDF de procedimiento.
    - **Pestaña 2: Ingredientes Fijos (Escandallo Base):**
      - Tabla de insumos que componen la receta obligatoriamente.
      - Selector con búsqueda reactiva de `Productos` de bodega o `Sub-recetas` previas.
      - Ingreso de cantidad, unidad de medida, merma técnica (%) y cálculo automático del costo unitario PPP.
    - **Pestaña 3: Componentes Dinámicos ("Receta Dinámica"):**
      - Activada automáticamente al añadir grupos o marcar la receta como dinámica.
      - Botón `"+ Agregar Grupo de Opciones"`:
        - Opción A: Crear grupo nuevo in-situ (ej: "Elección de Guarnición").
        - Opción B: Seleccionar grupo preexistente de la biblioteca (ej: "Acompañamientos Clásicos").
      - Configuración de cardinalidad por grupo: Mínimo (ej: 1) y Máximo (ej: 1) de elecciones permitidas.
      - Configuración de opciones dentro del grupo:
        - Selección del producto o sub-receta.
        - Cantidad de la porción (ej: 200g de Puré o 150g de Arroz).
        - Checkbox `"Opción por Defecto"` (determina el costo base de la receta).
        - Campo `"Recargo Adicional"` (+$$$) para opciones premium (ej: Costillar +$1.000).
    - **Panel Lateral Flotante de Escandallo en Vivo:**
      - Resumen de costos en tiempo real:
        - Costo Insumos Fijos.
        - Costo Opciones Base (Default).
        - **Costo Escandallo Total Base.**
        - **Costo Peor Escenario (Worst-case).**
        - Margen % Proyectado.
- [x] **5.2** Modal Maestro de Combos `ComboDialog.tsx` (Re-arquitectura Completa):
  - Selección de categoría de combo, nombre, precio e imagen.
  - Bloque 1: Insumos o recetas fijas que incluye siempre el combo.
  - Bloque 2: Grupos de opciones dinámicos (ej: 1 Sandwich a elección + 1 Bebida a elección).
  - Cálculo de ahorro para el cliente respecto a la compra por separado.
- [x] **5.3** Modal Asistente de Biblioteca de Opciones `OptionGroupSelectorModal.tsx`:
  - Diálogo modal accesible para explorar, crear y editar grupos de opciones al vuelo sin abandonar la pantalla de Receta o Combo.
- [x] **5.4** Modal de Ficha Técnica Gastronómica `RecetaDetalleModal.tsx`:
  - Vista limpia para visualización de cocina: ingredientes con cantidades escaladas según el número de porciones solicitadas, instrucciones de preparación y visualizador de video/documento.

---

### [x] FASE 6: Asistente de Escandallo y Preparación (Completado)
- [x] **6.1** Ficha Técnica Imprimible / Exportable (PDF / Ticket Cocina):
  - Generación de ficha técnica de cocina con cantidades netas y brutas (aplicando factor de merma).
  - Escalamiento dinámico: el usuario ingresa por ejemplo "50 porciones" y la tabla recalcula al instante todos los gramos y litros requeridos.
  - Botón de impresión y estilos CSS `@media print` optimizados para A4 y ticket térmico de cocina.
- [x] **6.2** Trazabilidad de Alérgenos:
  - Consolidación automática de alérgenos heredados desde los insumos del catálogo (14 alérgenos normados: gluten, lácteos, frutos secos, mariscos, etc.) para visualización en la ficha técnica y comanda de cocina.
  - Componente reusable `AllergenBadge.tsx` con badges bilingües, íconos Lucide, tooltips y advertencias sanitarias de contaminación cruzada.

---

### [x] FASE 7: Capas Cruzadas, i18n, FX, Observabilidad, Testing 5D & Sincronización Graphify (Completado)
- [x] **7.1** Cobertura de Internacionalización (i18n 100% `es`/`en` y 0 Strings Hardcodeadas):
  - Actualización de `oppytec-frontend/src/shared/i18n/locales/es/recipes.json` y `en/recipes.json`:
    - Claves completas para recetas, combos, grupos de opciones, escandallos, tipos de ingredientes y alertas de margen.
  - Verificación estricta de 0 textos quemados en español o inglés en JSX y atributos accesibles.
- [x] **7.2** Multi-Moneda FX con Precisión `Decimal`:
  - Cálculos de escandallos, costos de porción, recargos y precios de combos procesados estrictamente con `Decimal` en backend y formateadores precisos en frontend (`formatMoney`, `MoneyBadge`).
  - Prohibido el uso de `float` en cálculos financieros críticos.
- [x] **7.3** Instrumentación de Observabilidad (OpenTelemetry & Sentry):
  - Spans OpenTelemetry en: `recipe.escandallo.calculate`, `recipe.cycle_detection.run`, `recipe.kitchen_sheet.generate`, `combo.availability.check`.
  - Contextualización de trazas con `tenant_id`, `recipe_id`, `combo_id`, `is_dynamic` y `allergen_count` con PII scrubbing automático.
- [x] **7.4** Suite de Pruebas Automatizadas 5D (Backend & Frontend):
  - **Backend (Pytest):**
    - `tests/modules/recipes/test_escandallo_invariants.py`: verificar paridad matemática de escandallo, fórmulas con merma y orden de costos ($C_{\min} \le C_{\text{base}} \le C_{\max}$).
    - `tests/modules/recipes/test_recipe_cycle_detection.py`: verificar que un intento de autorreferencia o ciclo indirecto en sub-recetas lance un error 400/422 controlado.
    - `tests/modules/recipes/test_dynamic_options_rules.py`: verificar cumplimiento de límites de selección mín/máx y recargos.
    - `tests/security_redteam/test_13_recipes_combos_offensive_security_and_rbac.py`: auditoría de seguridad de 11 vectores Kali, control de acceso de 3 niveles y prevención de IDOR cross-tenant (100% verde, 22 tests).
  - **Frontend (Vitest):**
    - `useRecetas.test.ts`, `useCombos.test.ts`, `useGruposOpciones.test.ts`: pruebas de hooks y cache.
    - `RecetasTable.test.tsx`, `CombosTable.test.tsx`: pruebas de renderizado, filtrado y badges dinámicos.
    - `RecetaDialog.test.tsx`: pruebas del formulario de 3 pasos, adición de ingredientes fijos y configuración de grupos de opciones dinámicos.
- [x] **7.5** Verificación de Compilación y Calidad:
  - Chequeo de tipos estático: `pnpm tsc --noEmit` $\rightarrow$ **0 errores**.
  - Linter: `pnpm lint` $\rightarrow$ **0 issues**.
  - Build de producción: `pnpm build` $\rightarrow$ **Éxito**.
- [x] **7.6** Sincronización del Grafo AST y Verificación de Calidad:
  - Ejecutar `python scripts/harness.py sync-graph` para indexar todos los nuevos modelos, routers y componentes en `docs/architecture/graphify/graph.json`.
  - Ejecutar `python scripts/harness.py verify-evals` para validar integridad y ausencia de reward-hacking.

---

## 🎯 Protocolo de Ejecución y Traspaso entre Agentes

| Etapa | Agente Líder | Tareas a Cargo | Entregables Principales |
| :---: | :--- | :--- | :--- |
| **Etapa 1** | `02-software-architect` & `03-database-alembic` | FASE 1: DDL `tenant_*`, Alembic `0005`, DDD Escandallo Polimórfico | Modelos SQLAlchemy, Migración `0005`, Value Objects de Dominio |
| **Etapa 2** | `04-backend-senior-dev` | FASE 2 & FASE 6: Servicios de Aplicación, Escandallo y Router REST | Routers FastAPI, Servicios transaccionales, Guards RBAC |
| **Etapa 2** | `05-frontend-senior-dev` | FASE 3, 4, 5: UI React 19, Vistas de Gestión y Modales Especializados | `RecetasTable`, `CombosTable`, `RecetaDialog`, `ComboDialog` |
| **Etapa 3** | `07-i18n-fx` & `08-environments-observability` | FASE 7: i18n 100%, Multi-Moneda FX, OpenTelemetry | `recipes.json` (es/en), Spans OTel, Sentry |
| **Etapa 4** | `09-qa-test` & `10-security-redteam` | FASE 7: Testing 5D, SAST/DAST, Paridad Matemática de Escandallo | Tests Pytest + Vitest, Auditoría Kali, 0 Vulnerabilidades |
| **Etapa 4** | `11-git-arbiter` & `12-tech-writer` | Cierre: Merge Train, OpenSpec, Graphify & Archify | Smart Merge, Bóvedas OpenSpec, Grafo AST sincronizado |

> **Nota Final:** Toda modificación de código debe ejecutarse previa consulta de Graphify (`python scripts/harness.py nav "<símbolo>"`) y concluir con la sincronización obligatoria `python scripts/harness.py sync-graph`.
