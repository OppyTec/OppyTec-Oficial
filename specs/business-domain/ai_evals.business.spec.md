# Evaluación Sistemática de Calidad y Observabilidad de IA (AI Evals & Trazabilidad)

> **Audiencia:** Dueños de restaurantes y hoteles, directores de operaciones, administradores de alimentos y bebidas, gerencia de compras y soporte de producto. Documento de negocio sin tecnicismos de programación interna.

---

## Resumen Ejecutivo

OppyFy es el asistente inteligente que guía las operaciones críticas diarias de restaurantes, hoteles y banquetes en OppyTec v2.0. Dado que el personal de cocina, bodega y finanzas confía en el asistente para calcular compras masivas de insumos, verificar fechas de caducidad (FEFO), detectar mermas anómalas y conciliar facturas de proveedores, **la confiabilidad de la inteligencia artificial no puede dejarse al azar**.

La **Evaluación Sistemática de Calidad (AI Evals)** y la **Observabilidad Continua** constituyen la garantía operativa de que OppyFy entrega respuestas fidedignas, matemáticamente exactas y apegadas estrictamente a la realidad de cada establecimiento, erradicando alucinaciones que comprometan la rentabilidad, la higiene o la inocuidad alimentaria del negocio.

---

## Principios y Reglas de Negocio

### 1. Honestidad Epistémica Gastronómica Inviolable
- **Cero Suposiciones en Inventario y Alérgenos:** Si un colaborador pregunta por un ingrediente, lote o producto que no se encuentra registrado en el almacén del establecimiento, OppyFy tiene la instrucción obligatoria de declarar de forma explícita y transparente que el ítem **no existe en el inventario del local**.
- **Prohibición Tajante de Cantidades Ficticias:** OppyFy jamás inventa cantidades, rendimientos, proveedores o fechas estimadas. Ante la falta de información empírica, solicita la aclaración humana o la creación del registro correspondiente en el catálogo de productos.
- **Tolerancia Cero en Seguridad Alimentaria:** La tasa de alucinación permitida en recetas, declaración de alérgenos (gluten, lactosa, mariscos, frutos secos) y costos monetarios de insumos es **estrictamente 0.00**.

### 2. Estándares y Acuerdos de Nivel de Servicio (SLAs de Calidad IA)
Para autorizar cualquier actualización en el cerebro de OppyFy, el sistema es sometido a una rigurosa batería de pruebas gastronómicas reales (*Golden Dataset Gastronómico*) donde debe cumplir y superar los siguientes umbrales mínimos:

| Indicador de Calidad | Meta Operativa Mínima | Significado para el Restaurante |
|---|---|---|
| **Fidelidad al Contexto (*Faithfulness*)** | $\ge 85\%$ (0.85) | El 100% de los datos afirmados por el asistente se desprenden exclusivamente de las recetas, facturas y stock real del restaurante. |
| **Pertinencia de la Respuesta (*Answer Relevance*)** | $\ge 85\%$ (0.85) | La respuesta resuelve de forma directa, útil y concisa la duda planteada por el cocinero, bodeguero o administrador, sin divagaciones. |
| **Precisión de Contexto y Herramientas (*Context Precision*)** | $\ge 80\%$ (0.80) | El asistente invoca con exactitud las funciones operativas de inventario, mermas o compras requeridas por la consulta. |
| **Tasa Máxima de Alucinación (*Hallucination Rate*)** | $\le 5\%$ (0.05) global / **$0.00\%$ crítica** | Máxima protección contra afirmaciones falsas; tolerancia 0% en recetas, costos unitarios, alérgenos y fechas de caducidad. |

### 3. Preservación Inmutable de Proveedores y Marcas ("Pollo King")
- Los nombres comerciales de establecimientos, marcas registradas y proveedores locales (como por ejemplo el proveedor oficial **"Pollo King"** o la marca de la casa) son tratados como identidades fidedignas inmutables.
- OppyFy tiene estrictamente prohibido alterar, traducir o deformar dichos nombres comerciales (por ejemplo, jamás traducirá *"Pollo King"* como *"King Chicken"* ni *"Rey Pollo"* en consultas o reportes en inglés u otros idiomas).

### 4. Ciclo de Retroalimentación Humana en Pantalla (Feedback 👍 / 👎)
Cada respuesta generada por OppyFy en el espacio de trabajo de chat incluye mecanismos directos para que el personal califique la utilidad y veracidad del asistente:
- 👍 **Aprobación Rápida (Pulgar Arriba):** Registra la satisfacción del operador, validando que el consejo o cálculo fue acertado en la operación diaria.
- 👎 **Reporte de Falla (Pulgar Abajo) con Categorización Operativa:** Al marcar pulgar abajo, se despliega una ventana interactiva accesible donde el usuario identifica la naturaleza del problema entre cinco categorías claras:
  1. **Alucinación / Dato Falso:** El asistente mencionó existencias, recetas o datos que no coinciden con la realidad del local.
  2. **Error de Cálculo / Matemático:** La multiplicación de porciones, la merma o la suma de costos presentó una discrepancia numérica.
  3. **Información Incompleta:** Omitió ingredientes, pasos de la receta o datos clave solicitados.
  4. **Formato o Tono Inadecuado:** La respuesta fue excesivamente larga, desordenada o difícil de leer en el ritmo acelerado del servicio.
  5. **Otro / Observación Libre:** Cualquier otra situación anómala en la interacción.
- **Sugerencia de Corrección:** El usuario puede ingresar opcionalmente la respuesta que debió entregar el asistente, aportando conocimiento empírico del restaurante para la mejora continua del modelo.

### 5. Aislamiento Estricto por Establecimiento y Protección de Datos
- Cada establecimiento u hotel opera en un entorno herméticamente aislado. El asistente de un restaurante jamás conoce, compara ni revela inventarios, recetas, márgenes o costos de ningún otro establecimiento del grupo o de la plataforma.
- Toda la telemetría de monitoreo oculta y elimina automáticamente cualquier información sensible (correos personales, teléfonos de clientes, RUT/DNI o datos de tarjetas bancarias) antes de registrar las estadísticas de rendimiento.

---

## Escenarios de Negocio

### Escenario 1: Solicitud de Insumos para Banquete de 140 Personas
1. El chef ejecutivo consulta: *"Necesito preparar Risotto de Hongos para 140 comensales. La receta rinde 4 porciones y requiere 320g de arroz arborio y 200g de setas frescas con 10% de merma. ¿Cuánto insumo bruto pido al almacén?"*.
2. OppyFy ejecuta las funciones de costeo y factor de escala (35x).
3. Responde indicando exactamente: **11.20 kg de arroz arborio** y **7.78 kg de setas frescas brutas** (calculando con exactitud la merma).
4. El chef califica la respuesta con 👍 (pulgar arriba); el sistema registra la métrica de satisfacción y confirma la consistencia matemática del cálculo.

### Escenario 2: Detección y Reporte de Ingrediente no Registrado (Honestidad Epistémica)
1. Un pastelero consulta a OppyFy: *"¿Cuántos kilos de harina de almendras nos quedan en la bodega de secos?"*.
2. OppyFy consulta las existencias del local y constata que la harina de almendras no está registrada en el catálogo.
3. En lugar de especular o decir "quedan pocos paquetes", el asistente responde con honestidad epistémica: *"La harina de almendras no se encuentra registrada en el inventario de este local. Por favor comunícate con el encargado de bodega si deseas dar de alta este insumo"*.
4. El personal no incurre en errores de producción por información ficticia.

### Escenario 3: Detección de Discrepancia en Factura y Reporte 👎
1. El encargado de compras pide comparar una factura reciente del proveedor "Pollo King" con la orden de compra aprobada.
2. OppyFy detecta un incremento no pactado del 12% en el kilo de pechuga deshuesada, pero en el texto omite la fecha de recepción de la mercadería.
3. El usuario marca 👎 y selecciona la categoría **"Información Incompleta"**, comentando: *"Faltó incluir la fecha de la guía de despacho asociada"*.
4. El equipo de mejora continua recibe la alerta de satisfacción para ajustar la plantilla de respuesta en el módulo de compras.

---

## Documento Técnico Par

Para detalles de implementación técnica, diagramas de arquitectura DDD, contratos de interfaces y suites automatizadas de pruebas en código, consultar:  
👉 [`specs/engineering-code/ai_evals.code.spec.md`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/specs/engineering-code/ai_evals.code.spec.md).
