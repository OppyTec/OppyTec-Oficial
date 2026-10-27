# Recetas, Escandallos Gastronómicos y Combos Dinámicos

> Audiencia: Clientes, directores de operaciones gastronómicas, administradores de negocio, soporte y asistente OppyFy (Capa 3A). Sin detalles técnicos de persistencia ni código fuente.

## Resumen Ejecutivo

El módulo de Gestión de Recetas, Escandallos y Combos constituye el núcleo operativo de control de costos, estandarización culinaria y maximización de rentabilidad de OppyTec v2.0. Cada plato, preparación intermedia o paquete promocional cuenta con una formulación precisa y estructurada que vincula ingredientes de bodega, mermas técnicas, tiempos de elaboración e información de alérgenos. El sistema calcula en tiempo real el costo unitario por porción, los márgenes comerciales brutos y netos con respecto a los precios de venta, y proporciona protección financiera frente a fluctuaciones en los costos de adquisición de insumos.

La arquitectura funcional distingue con claridad entre preparaciones estáticas (fórmulas fijas de ingredientes) y preparaciones dinámicas (platos y combos personalizables por el comensal mediante grupos de modificadores y elecciones guiadas), incorporando un motor de simulación de costos que proyecta el costo base, el costo mínimo y el peor escenario financiero posible (*worst-case*) antes de confirmar una comanda o venta.

---

## Reglas de Negocio Fundamentales

### 1. Tipología de Preparaciones y Estructura Gastronómica
- **Recetas Estáticas (Fórmulas Fijas):** Preparaciones culinarias compuestas por una lista invariable de insumos de inventario y sub-recetas previas. Cada ingrediente define su cantidad neta requerida y su porcentaje de merma técnica por manipulación o cocción.
- **Recetas Dinámicas (Con Opciones del Cliente):** Platos donde el comensal elige entre diferentes alternativas operativas (por ejemplo, tipo de guarnición, variedad de salsa, proteína principal o punto de cocción). Se activan automáticamente al incorporar al menos un grupo de opciones a la receta.
- **Sub-recetas (Bases Culinarias Intermedias):** Preparaciones intermedias no comercializadas directamente al público (por ejemplo: caldos base, masas madre, salsas reducidas o marinados) que se utilizan como ingredientes constitutivos dentro de otras recetas finales.
- **Combos y Paquetes Promocionales:** Conjuntos de productos, platos y bebidas que se comercializan bajo un precio unificado y promocional. Pueden ser estáticos (componentes fijos predeterminados) o dinámicos (con selecciones a gusto del cliente, como bebida a elección o postre opcional).

### 2. Escandallo Gastronómico, Costos y Rendimiento
- **Rendimiento de Porciones:** Toda receta especifica cuántas raciones o porciones produce su formulación (con un valor mínimo superior a cero). El costo total de elaboración se divide exactamente entre este rendimiento para determinar el costo unitario por porción.
- **Valorización al Costo Promedio Ponderado:** Cada ingrediente se valoriza instantáneamente utilizando el costo promedio ponderado vigente en el libro mayor de inventario. Cuando se registran nuevas compras de insumos que modifican el costo promedio, todos los escandallos dependientes actualizan sus costos de porción y márgenes proyectados de forma inmediata.
- **Factor de Merma Técnica:** El sistema aplica el porcentaje de merma ($0\% \le \text{merma} < 100\%$) sobre cada ingrediente para calcular la cantidad bruta real consumida de inventario y su costo correspondiente:
  $$\text{Cantidad Bruta} = \text{Cantidad Neta} \times \left(1 + \frac{\text{Porcentaje Merma}}{100}\right)$$
- **Prohibición de Ciclos en Preparaciones:** Una receta no puede contenerse a sí misma ni directa ni indirectamente dentro de su árbol de sub-recetas (por ejemplo, si la Masa A utiliza el Relleno B, el Relleno B no puede contener la Masa A). El sistema valida la integridad de la estructura antes de guardar cualquier cambio.

### 3. Grupos de Opciones y Modificadores Dinámicos
- **Biblioteca de Opciones Reutilizable e In-Situ:** Los grupos de modificadores pueden seleccionarse desde la biblioteca corporativa del local (ejemplo: "Acompañamientos Tradicionales") o crearse de manera ágil in-situ mientras se elabora la receta o combo.
- **Reglas de Cardinalidad (Mínimo y Máximo de Elecciones):**
  - Cada grupo define cuántas elecciones debe realizar el comensal como mínimo y cuántas como máximo.
  - La cardinalidad mínima no puede ser menor a uno en grupos obligatorios y no puede superar a la cardinalidad máxima ($1 \le \text{mínimo} \le \text{máximo}$).
- **Opción por Defecto Obligatoria:** Todo grupo de opciones de carácter obligatorio debe contar con al menos una opción marcada como opción predeterminada (*default*). Esta opción base establece el costo referencial para el cálculo del escandallo estándar y la fijación del precio de lista.
- **Recargos de Precio (+$$$):** Las opciones de mayor costo relativo (por ejemplo, sustituir papas fritas por ensalada de salmón) pueden incorporar un recargo de precio adicional que se suma automáticamente al precio de venta del plato.
- **Control de Repetición:** Cada grupo estipula si el cliente puede repetir la misma alternativa dentro de una selección múltiple (por ejemplo, elegir dos bolas del mismo sabor de helado) o si cada elección debe ser única y diferente.

### 4. Tripartición de Costos y Semáforo de Rentabilidad
- **Modelo de Tres Escenarios de Costo:**
  Para toda preparación dinámica, el sistema calcula y exhibe tres métricas financieras simultáneas:
  1. **Costo Base:** Determinado por los ingredientes fijos más las opciones por defecto de cada grupo.
  2. **Costo Máximo (Peor Escenario / Worst-Case):** Determinado por la combinación de opciones que genera el costo de insumos más alto posible dentro de los límites de selección permitidos. Permite a la gerencia fijar precios de venta que protejan el margen bruto aun cuando el cliente elija las opciones más costosas.
  3. **Costo Mínimo (Mejor Escenario):** Determinado por la combinación más económica permitida.
- **Semáforo Visual de Margen Comercial:**
  En todas las tablas y fichas técnicas se despliega un indicador visual del margen porcentual proyectado:
  - 🟢 **Verde (Margen Saludable):** Margen comercial bruto igual o superior al $65\%$.
  - 🟡 **Amarillo (Margen en Observación):** Margen comercial entre $40\%$ y $64\%$.
  - 🔴 **Rojo (Margen Crítico):** Margen comercial inferior al $40\%$, requiriendo revisión de costos o ajuste de precio de venta.

### 5. Ficha Técnica Gastronómica, Escalamiento y Alérgenos
- **Ficha Técnica Operativa:** Documento integral de cocina que detalla cantidades netas, porcentajes de merma, cantidades brutas requeridas, instrucciones paso a paso de preparación, tiempo de cocción y tiempos de reposo.
- **Escalamiento Dinámico de Raciones:** El usuario puede ingresar cualquier volumen de servicio requerido (por ejemplo: "Preparar 80 porciones para banquete") y el sistema multiplica proporcionalmente todos los gramos, litros y unidades de insumo preservando las mermas técnicas.
- **Trazabilidad Automática de Alérgenos:** El sistema consolida automáticamente los alérgenos normados (14 alérgenos estándar: cereales con gluten, crustáceos, huevos, pescado, maní, soja, leche, frutos de cáscara, apio, mostaza, sésamo, sulfitos, altramuces y moluscos) heredados desde los insumos del catálogo, presentándolos con insignias bilingües y advertencias sanitarias de contaminación cruzada.
- **Impresión y Exportación:** Formato de salida con estilos adaptados para impresión en hoja tamaño carta/A4 y para ticket térmico de comanda de cocina.

### 6. Experiencia de Usuario y Navegación en `/gestion`
- **Reestructuración de Pestañas Unificadas:**
  La pantalla central de gestión unifica la operación en tres pestañas jerárquicas:
  1. `Insumos & Productos`: Maestro de artículos de bodega y compras.
  2. `Recetas & Escandallos`: Catálogo de fórmulas, sub-recetas y fichas técnicas culinarias.
  3. `Combos & Promociones`: Paquetes y menús promocionales comercializables.
  *Se eliminan las pestañas aisladas de grupos de opciones, integrando su administración directamente en las pantallas y modales de recetas y combos.*
- **Indicadores Visuales y Filtros Rápidos:**
  - Insignia distintiva: ⚡ `Dinámica` (color púrpura gastronómico) o 📜 `Fija` (color azul pizarra).
  - Filtro por tipo: `Todas`, `Dinámicas`, `Estáticas` y `Sub-recetas`.
  - Búsqueda predictiva por nombre de plato, código interno o ingredientes constitutivos.
- **Operación Táctil Mobile-First:**
  Tarjetas colapsables optimizadas para tabletas de cocina y teléfonos inteligentes con botones y áreas de toque con tamaño mínimo de 44 píxeles para uso con guantes o dedos mojados.

---

## Escenarios Operativos de Negocio

### Escenario A: Creación de Plato Principal con Guarnición Dinámica
1. El chef ejecutivo crea la receta "Lomo Saltado Clásico" con rendimiento de 1 porción y precio de venta de \$12.500.
2. Agrega los ingredientes fijos: 200g de Lomo Liso (merma 5%), 80g de Cebolla Morada (merma 10%), 80g de Tomate y condimentos.
3. Añade el grupo de opciones "Elección de Acompañamiento" (mínimo 1, máximo 1):
   - Opción 1: Arroz Blanco 150g (marcada como Opción por Defecto, costo \$180, sin recargo).
   - Opción 2: Papas Fritas Rústicas 200g (costo \$350, recargo \$500).
   - Opción 3: Risotto de Champiñones 180g (costo \$950, recargo \$1.500).
4. El sistema calcula en vivo:
   - Costo Insumos Fijos: \$3.850.
   - Costo Base (con Arroz): \$4.030 (Margen: 67.8% 🟢).
   - Costo Máximo Peor Escenario (con Risotto): \$4.800 (Margen con recargo: 65.7% 🟢).
5. El plato queda registrado con insignia ⚡ Dinámica y su escandallo queda blindado ante variaciones del comensal.

### Escenario B: Alerta y Actualización Automática ante Alza de Precios
1. El departamento de adquisiciones registra una factura donde el precio del kilogramo de Queso Mozzarella sube un 25%.
2. El sistema actualiza de inmediato el costo promedio ponderado en el libro mayor.
3. El panel de recetas detecta qué preparaciones contienen Queso Mozzarella y recalculan sus márgenes.
4. La "Pizza Cuatro Quesos" transiciona de margen verde (66%) a amarillo (58%), emitiendo una notificación visual al administrador para sugerir revisión de precios.

### Escenario C: Preparación Masiva de Banquetería
1. Para un evento corporativo de fin de semana, el jefe de cocina abre la ficha técnica del "Pollo al Curry con Verduras".
2. Ingresa en el escalador: 120 porciones.
3. El sistema proyecta la lista consolidada de compras necesarias expresada en kilogramos brutos (incluyendo mermas), desglosa los alérgenos presentes (lácteos y mostaza) y emite la ficha técnica para los asistentes de cocina.

---

## Documento Técnico Par

Para los contratos técnicos de persistencia de base de datos, enrutadores de servicios, estructuras de datos, eventos en tiempo real y pruebas automatizadas, consultar:
- `recipes-and-combos.code.spec.md`
