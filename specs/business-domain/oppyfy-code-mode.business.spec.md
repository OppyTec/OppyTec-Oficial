# OppyFy Code Mode: Inteligencia Operativa y Ahorro Eficiente de Tokens

> Audiencia: Propietarios de restaurantes y cadenas hoteleras, administradores de locales, directores de operaciones gastronómicas, equipos de producto y soporte comercial. Documento de dominio de negocio sin tecnicismos de código fuente interno ni estructuras de bases de datos.

---

## 1. Resumen Ejecutivo y Propósito de Negocio

En la gestión diaria de restaurantes, hoteles y servicios de banquetería, las decisiones operativas requieren analizar grandes volúmenes de datos: existencias de cientos de materias primas en múltiples bodegas, movimientos diarios de mermas, órdenes de compra a diversos proveedores y recetas con múltiples ingredientes.

Tradicionalmente, cuando un asistente de inteligencia artificial analiza este tipo de consultas operativas, se produce un fenómeno conocido como *desperdicio de tokens*: el sistema debe descargar y transferir cientos de filas de información cruda hacia el modelo de inteligencia artificial solo para que este sume dos columnas o encuentre los tres productos más críticos. Esto encarece enormemente las facturas mensuales de inteligencia artificial, agota con rapidez los paquetes de créditos del local y genera esperas prolongadas de más de diez segundos por respuesta.

**OppyFy Code Mode** transforma radicalmente este modelo operativo. En lugar de transferir cientos de registros no procesados a través de internet, OppyFy ejecuta el filtrado, los cálculos matemáticos y las consolidaciones en una sala de procesamiento segura y cerrada dentro del propio sistema, entregando al usuario únicamente la síntesis final limpia, clara y estructurada.

---

## 2. Pilares de Valor para el Restaurante y la Cadena Gastronómica

### 2.1 Ahorro Radical de Costos Operativos (Reducción Superior al 90% en Consumo de Créditos)
- **Eliminación del Tráfico Innecesario:** Al procesar y agrupar la información internamente antes de generar la respuesta, las consultas complejas de inventario o mermas que antes requerían decenas de miles de tokens de procesamiento ahora se resuelven utilizando menos de una décima parte de los créditos.
- **Economía Sustentable a Gran Escala:** Una franquicia gastronómica con decenas de locales que realiza cientos de preguntas analíticas al día experimenta un ahorro acumulado de entre el 90% y el 99.7% en el consumo de créditos de inteligencia artificial, permitiendo operar asistentes avanzados sin sorpresas presupuestarias.

### 2.2 Respuestas Rápidas en un Solo Turno (Cero Esperas Acumuladas)
- **Análisis Instantáneo sin Viajes Redondos:** En lugar de realizar múltiples llamadas intermedias ("consultar productos", "esperar respuesta", "consultar precios", "esperar respuesta", "calcular totales"), OppyFy resuelve consultas analíticas compuestas en un único turno unificado.
- **Agilidad en Servicio y Cocina:** Preguntas cruciales durante el turno operativo (por ejemplo: *"¿Cuáles fueron los cinco insumos con mayor merma en la última semana y qué porcentaje representan del total registrado?"*) se responden en menos de dos segundos, permitiendo tomar medidas correctivas inmediatas sin retrasar el despacho de comandas.

### 2.3 Confidencialidad Absoluta de Costos Financieros Garantizada por Roles (RBAC)
- **Segregación Estricta de la Información Sensible:** No todos los colaboradores deben tener acceso a los márgenes comerciales o a los precios pactados con los proveedores. OppyFy respeta de forma estricta los privilegios asignados al rol de cada trabajador.
- **Protección Automática en el Origen:** Si un encargado de bodega, copero o ayudante de cocina consulta el estado de las existencias o el historial de desperdicios, el sistema purga y oculta de forma irrevocable cualquier dato monetario (precios de compra, costos unitarios, márgenes y valorizaciones). El colaborador recibe los kilogramos, unidades, lotes y fechas de vencimiento, mientras los datos financieros permanecen estrictamente confidenciales.
- **Acceso Exclusivo para la Gerencia:** Solo los usuarios con permisos financieros explícitos otorgados por la administración del local pueden visualizar costos reales, costos teóricos y desvíos de precios.

### 2.4 Aislamiento Hermético Entre Restaurantes y Sucursales (Cero Filtración de Datos)
- **Privacidad Inviolable por Establecimiento:** Cada restaurante, sucursal u hotel opera en un entorno estrictamente aislado. Las preguntas y análisis de un local jamás tienen acceso ni pueden inferir datos de otros establecimientos o de marcas competidoras.
- **Gobernanza para Grupos Gastronómicos:** En holdings empresariales con múltiples marcas, la administración central puede consolidar métricas globales autorizadas sin que los locales individuales pierdan su independencia de datos.

### 2.5 Transparencia Total y Auditoría FinOps del Ahorro
- **Medidor de Ahorro en Tiempo Real:** Cada respuesta analítica procesada mediante Code Mode calcula y reporta el ahorro neto de tokens obtenido frente a la modalidad tradicional.
- **Control Gerencial:** El propietario del negocio puede auditar en todo momento en su consola de administración el historial de consultas, los créditos ahorrados y el rendimiento financiero del asistente inteligente.

---

## 3. Escenarios de Uso Operativo en el Restaurante

### Escenario 1: Control de Mermas por un Encargado de Cocina (Sin Acceso a Costos Financieros)
1. **Situación:** Durante el cierre del turno vespertino, el jefe de turno de cocina desea conocer qué insumos perecibles tuvieron mayor desperdicio para ajustar la producción del día siguiente.
2. **Consulta a OppyFy:** *"Dime los 4 ingredientes con más mermas registradas hoy en el turno de tarde y la razón principal indicada por los cocineros"*.
3. **Comportamiento de OppyFy Code Mode:**
   - Verifica los permisos del colaborador: tiene acceso a registrar y consultar mermas, pero no tiene permiso de visualización de costos.
   - En una única operación en memoria, recopila los registros de merma del turno, los agrupa por ingrediente, suma los kilogramos perdidos y ordena los mayores incidentes.
   - Aplica el filtro de confidencialidad: suprime automáticamente cualquier valorización monetaria.
4. **Resultado para el Usuario:** El colaborador recibe una lista clara indicando los kilogramos exactos de tomate, pechuga de pollo y crema mermados junto con las razones operativas (ejemplo: vencimiento o error de cocción), sin exponer los costos de compra del restaurante. Se ahorran más de dos mil tokens en una sola consulta.

### Escenario 2: Análisis de Rentabilidad de Recetas por el Propietario (Acceso Pleno a Costos)
1. **Situación:** El dueño del restaurante necesita revisar el impacto del aumento de precios de los lácteos en los platos más vendidos de la carta antes de fijar el menú de temporada.
2. **Consulta a OppyFy:** *"Calcula el costo actual de los 5 platos de pasta más vendidos y compáralo con el costo teórico de la receta original"*.
3. **Comportamiento de OppyFy Code Mode:**
   - Verifica que el usuario es Administrador General con credenciales financieras habilitadas.
   - Cruza en memoria las recetas, los ingredientes, las últimas compras registradas y el volumen de ventas recientes.
   - Calcula los costos teóricos, los costos reales y la brecha porcentual en un único paso de procesamiento.
4. **Resultado para el Usuario:** El Canvas lateral de OppyFy despliega una tabla comparativa con los costos unitarios, márgenes brutos y alertas de desvío, permitiendo ajustar los precios de carta al instante.

### Escenario 3: Estimación de Abastecimiento Semanal para Banquetes y Eventos
1. **Situación:** El coordinador de eventos de un hotel boutique tiene confirmadas dos bodas y una cena de gala para el fin de semana, sumando trescientos comensales.
2. **Consulta a OppyFy:** *"¿Qué insumos de carnes y vinos nos faltan para cubrir los banquetes del sábado y cuánto stock de seguridad nos quedará en bodega?"*.
3. **Comportamiento de OppyFy Code Mode:**
   - Multiplica los comensales por las fichas técnicas de los menús pactados.
   - Descuenta las existencias actuales de las bodegas centrales y de frío.
   - Genera una lista consolidada con las cantidades exactas requeridas para reabastecimiento.
4. **Resultado para el Usuario:** OppyFy presenta la propuesta de compra consolidada en el panel interactivo, lista para ser convertida en borrador de orden de compra con un solo toque y sin demoras de procesamiento.
