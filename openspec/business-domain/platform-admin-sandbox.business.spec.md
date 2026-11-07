# Lab & QA Sandbox — Consola de Pruebas, Simulación y QA de Plataforma

> Audiencia: Administradores de Plataforma, Líderes de QA, Ingenieros de Soporte y Auditores Operacionales. Libre de tecnicismos internos y código de bajo nivel.

## 1. Resumen y Propuesta de Valor Operativo

En una plataforma multi-inquilino de misión crítica para la industria gastronómica como **OppyTec v2.0**, verificar nuevas funcionalidades, validar la integridad de flujos punta a punta y simular escenarios extremos de operación (vencimiento masivo de insumos perecibles, altas cargas de comandeo o fallas en integraciones tributarias) no debe comprometer bajo ninguna circunstancia la continuidad ni la pureza de los datos reales de los restaurantes clientes.

La consola **Lab & QA Sandbox** provee un entorno centralizado de experimentación, calidad y simulación controlada dentro del portal de administración de la plataforma (`/admin/sandbox`), permitiendo a los operadores técnicos y especialistas de aseguramiento de calidad:

1. **Generar Datos de Prueba Realistas en Segundos:** Inyectar catálogos completos de prueba (Holdings, Locales, Insumos con mermas, Lotes con caducidad FEFO, Recetas compuestas, Facturas electrónicas y Usuarios de staff) sin intervención manual.
2. **Prevenir Contaminación Operacional:** Garantizar que las operaciones de prueba ocurran en modo de simulación analítica (*Dry-Run*) o queden estrictamente confinadas en esquemas de base de datos aislados (`tenant_qa_*`, `tenant_sandbox_*`).
3. **Consola Dinámica y Extensible de Pruebas Playwright:** Disponer de un catálogo dinámico y extensible de pruebas de extremo a extremo clasificado en los 7 dominios de la plataforma gastronómica, con métricas de cobertura y ejecución granular en tiempo real.
4. **Supervisión de Pruebas con Streaming en Vivo y Evidencia Visual:** Lanzar suites completas o pruebas puntuales y observar en vivo cada paso ejecutado, duraciones milimétricas y capturas de pantalla forenses de las interfaces directamente en la consola interactiva.
5. **Viajar en el Tiempo con Motor FEFO y Time-Travel:** Desplazar interactivamente el reloj operacional desde 30 días en el pasado (auditoría forense) hasta 60 días en el futuro (proyección analítica preventiva) para evaluar con exactitud matemática el impacto financiero de las mermas por vencimiento de productos perecibles, validando el comportamiento preventivo de las alertas antes de que ocurran en el restaurante real.
6. **Clasificación Automática mediante Semáforo FEFO de 4 Estados:** Evaluar cada lote contra la regla de oro gastronómica (*First-Expired, First-Out*), categorizándolo en estados Canónicos (`OPTIMAL`, `WARNING`, `CRITICAL`, `EXPIRED`) con códigos de color normalizados y protocolos de acción operativa inmediata.
7. **Probar Escenarios de Demostración Calibrados en 1 Clic:** Alternar instantáneamente entre tres arquetipos de inventario predefinidos (`HEALTHY`, `WARNING`, `CRITICAL`) con distribuciones porcentuales rigurosamente calibradas para auditorías, capacitaciones comerciales y pruebas de contingencia.
8. **Acción Quirúrgica de Sincronización a Hoy:** Recalibrar en un solo clic lotes sintéticos desfasados tras pausas operacionales prolongadas, alineando la vida útil de insumos de bodega y porciones de buffet sin destruir el inventario base y restableciendo el desfase a cero.
9. **Garantizar Seguridad y Blindaje Multi-Entorno:** Aplicar políticas estrictas de protección que bloquean mutaciones destructivas en entornos productivos y exigen confirmación reforzada en entornos de pre-producción (*Staging*).
10. **Alternar entre Modo Demo y Base Limpia (Switch Maestro):** Seleccionar reactivamente entre un modo guiado para demostraciones comerciales (*Demo*) y un modo estricto de base virgen (*Clean*) para verificar estados vacíos reales (*Empty States*).
11. **Aplicar Presets Gastronómicos Especializados:** Cargar arquetipos de industria predefinidos (Comida Rápida, Carnes Angus, Hotel Buffet o Base Limpia) con datos consistentes.
12. **Restablecer Estado Canónico en 1 Clic (Factory Reset):** Purgar cualquier dato residual o mutación de prueba para regresar de inmediato al estado de fábrica sin reinstalaciones.
13. **Aislamiento Total de Saldos y FinOps:** Asegurar que las pruebas y simulaciones de inteligencia artificial operen con costo cero para clientes reales, sin alterar balances de billeteras comerciales ni polucionar las bitácoras de auditoría de producción.

---

## 2. Las 3 Pestañas Operativas del Sandbox

La consola Lab & QA Sandbox se estructura en tres herramientas complementarias accesibles mediante una navegación por pestañas unificada:

### 2.1 Pestaña 1: Generador de Datos Sintéticos (`Mock Data`)
Permite poblar esquemas de prueba con volumen y relaciones de negocio consistentes:
- **Configuración de la Generación:**
  - *Esquema Destino:* Selección del esquema inquilino objetivo (`tenant_genesis`, `tenant_qa_lab`, etc.).
  - *Volumen de Datos:* Control paramétrico de cantidad de entidades a generar (lotes, insumos, recetas, facturas).
  - *Modo Simulación (Dry-Run):* Activado por defecto para calcular y proyectar el impacto antes de persistir cualquier registro.
  - *Limpieza Previa (Wipe Existing):* Opción de purgar registros de prueba existentes antes de la nueva inyección.
- **Resumen de Entidades Generadas:**
  - Contador detallado de insumos creados, lotes inicializados, recetas ensambladas y facturas simuladas.
  - Tiempos de procesamiento e identificador de correlación para auditoría técnica.

### 2.2 Pestaña 2: Ejecutor Dinámico de Pruebas E2E (`Playwright Runner`)
Proporciona una consola interactiva avanzada para el lanzamiento, monitoreo y observabilidad de pruebas browser sobre la plataforma:
- **Catálogo Dinámico Desacoplado:** Las pruebas ya no residen en listas fijas de la interfaz; la consola consulta dinámicamente el catálogo clasificado en 7 dominios de negocio.
- **Header de Métricas Globales:**
  - Total de pruebas en catálogo.
  - Barra visual interactiva con el porcentaje global de cobertura automatizada.
  - Contadores desagregados por estado de madurez: Listas para ejecución (*Ready*), En desarrollo activo (*In Progress*) y Planificadas en hoja de ruta (*Planned*).
  - Botón de disparo maestro para correr en un clic todas las pruebas listas de la plataforma.
- **Selector de Modo y Velocidad de Ejecución:**
  - *Modo Demostración Humana en Vivo (Live Demo):* Introduce una pausa configurable de 500 milisegundos entre acciones de navegación e interacción, permitiendo auditorías visuales y presentaciones ejecutivas a clientes.
  - *Modo CI Optimizado:* Ejecución a velocidad máxima sin esperas artificiales para validaciones continuas de laboratorio.
  - *Selector de Navegador:* Capacidad de conmutar entre los motores de navegación Chromium, Firefox y WebKit.
- **Agrupación Colapsable por Dominio:**
  - Siete acordeones independientes que resumen el progreso de cada área funcional.
  - Botón para disparar de forma exclusiva la suite del dominio seleccionado.
  - Tarjetas detalladas para cada caso de prueba con etiquetas temáticas, tiempo estimado y botón de disparo individual.
- **Terminal de Observabilidad y Streaming en Tiempo Real:**
  - Consola de terminal reactiva con actualización instantánea paso a paso.
  - Clasificación de eventos por niveles semánticos (pasos operativos, aserciones verificadas, advertencias y fallos).
  - Vínculos directos a capturas visuales generadas automáticamente en puntos de inspección clave.
  - Resumen final con duraciones acumuladas y tasa de éxito de la corrida.

### 2.3 Pestaña 3: Simulador Temporal de Envejecimiento FEFO (`FEFO Dates`)
Simula el envejecimiento e impacto financiero de las existencias para auditoría preventiva de pérdidas:
- **Control de Desplazamiento Time-Travel:**
  - Desplazamiento interactivo continuo desde -30 días (auditoría forense) hasta +60 días (proyección prospectiva).
  - Visualización en tiempo real con cero retardo perceptual (*Zero-Lag Projections*).
- **Tarjetas de Escenarios Calibrados:**
  - Acceso directo a tres escenarios canónicos: `HEALTHY` (Saludable, 0% merma), `WARNING` (Atención preventiva, ~15% riesgo) y `CRITICAL` (Rotura de frío / contingencia, ~42.5% riesgo).
- **Matriz de Lotes y Valorización de Riesgo Financiero:**
  - Distribución de lotes clasificados en los cuatro estados del semáforo FEFO: Óptimo, Advertencia, Crítico y Caducado.
  - Pérdida monetaria calculada de forma pura multiplicando cantidad, costo unitario y tasa de riesgo según estado sanitario.
  - Doble valorización monetaria en moneda nacional (CLP) y contravalor internacional (USD) con tasa de cambio en vivo.
- **Acción Quirúrgica de Sincronización:**
  - Botón "Sincronizar fechas a Hoy" para restaurar la vigencia operativa de lotes vencidos en entornos de prueba.
- **Protección y Modo de Ejecución:**
  - Simulación no destructiva (*Dry-Run*) activa por defecto.
  - Guardrail de seguridad que exige confirmación explícita para aplicar desplazamientos reales sobre la base de datos de pruebas.

---

## 3. Switch Maestro de Mock Data y Presets Gastronómicos Canónicos

### 3.1 Switch Maestro Reactivo (Modo 'Demo' vs Modo 'Clean')
Para asegurar pruebas confiables sin ambigüedades operativas, la cabecera de la herramienta Mock Data incorpora un interruptor maestro global:
- **Modo Demo (Demostración Guiada y Ventas):**
  - Mantiene activos datos sintéticos enriquecidos y estructurados.
  - Diseñado para presentaciones comerciales, capacitación de usuarios y demostraciones guiadas sin requerir configuración inicial.
  - Proporciona continuidad ante contingencias de red, simulando flujos completos de venta, stock y recetas.
- **Modo Clean (Base Limpia / Verificación de Estados Vacíos):**
  - Suprime incondicionalmente cualquier dato simulado o de respaldo.
  - Si un módulo o local carece de registros, la interfaz expone con total fidelidad los estados vacíos auténticos (*Empty States*).
  - Indispensable para auditar el flujo de incorporación (*Onboarding*) de clientes nuevos, validar primeros pasos y certificar que no existen registros fantasma.
  - Reactividad inmediata: el cambio de modo se propaga automáticamente a través de todas las vistas y pestañas abiertas del navegador.

### 3.2 Los 4 Presets Gastronómicos Canónicos Multi-Tenant
El Sandbox provee cuatro configuraciones canónicas listas para aplicar en esquemas aislados:

1. **Pollo King & Comida Rápida (`fast-food-pollo-king`):**
   - **Enfoque:** Cadena de restaurantes de comida rápida orientada a volumen alto, freidoras industriales y packaging descartable.
   - **Estructura:** Holding Pollo King Chile con locales en centros comerciales y bodegas de frío (-18°C), freidoras y descartables.
   - **Catálogo & Lotes:** Trutro de pollo IQF, pechugas marinadas, papas prefritas, pan brioche y baldes de cartón. Incluye lotes con alertas críticas a 48 horas de caducidad.
   - **Escandallo:** Fichas técnicas para Bucket Familiar 12 Piezas Crispy y Hamburguesas de doble pollo.
2. **Carnes Angus & Cava (`carnes-angus-cava`):**
   - **Enfoque:** Restaurante Steakhouse de alta gama con maduración en seco y cava subterránea de vinos finos.
   - **Estructura:** Grupo Gastronómico Corte & Cava con cámaras de maduración Dry-Aged, cava climatizada, parrilla al carbón y barra de coctelería.
   - **Catálogo & Lotes:** Cortes Tomahawk Angus, Lomo Vetado, Entraña Black Series, vinos Cabernet Sauvignon Reserva Maipo y destilados añejos.
   - **Escandallo:** Trazabilidad de faena, días de maduración y mermas por desposte y limpieza de grasa (5% a 12%).
3. **Hotel & Desayuno Buffet (`hotel-desayuno-buffet`):**
   - **Enfoque:** Operación de hospitalidad y salones de eventos con servicio de desayuno buffet masivo de alta rotación.
   - **Estructura:** Grand Hotel Andes & Resorts con talleres de panadería/repostería artesanal, cámara de lácteos y estaciones de comedor.
   - **Catálogo & Lotes:** Huevos grado A, mantequilla en bloque, leche UHT, harina pastelera, café colombiano y fiambres seleccionados.
   - **Escandallo:** Control estricto de insumos perecibles rápidos (72 horas) y cálculo de consumo por huésped proyectado (*Pax*).
4. **Base Virgen / Clean Slate (`clean-slate`):**
   - **Enfoque:** Entorno completamente estéril con cero insumos, cero lotes FEFO, cero recetas y cero transacciones.
   - **Propósito:** Evaluar pantallas de estado vacío, botones de creación inicial y verificar que no existan datos residuales.

### 3.3 Acción Factory Reset (1 Clic)
- **Propósito:** Permite restablecer con un solo clic el esquema de prueba seleccionado a su estado de fábrica original.
- **Seguridad:** Solicita confirmación dialogal explícita previa a la ejecución destructiva para evitar purgas no deseadas.
- **Ejecución Idempotente:** Elimina las mutaciones acumuladas en las tablas transaccionales del esquema aislado y vuelve a sembrar las entidades canónicas del preset elegido.
- **Blindaje:** Bloqueado de manera absoluta en entornos de producción.

---

## 4. Consola Dinámica de Pruebas Playwright: Dominios, Cobertura y Madurez

### 4.1 Principio de Descubrimiento Dinámico y Cero Código en Frontend
A diferencia de sistemas rígidos que exigen modificar componentes de interfaz cada vez que se agrega una prueba, la Consola de Sandbox opera bajo el principio de **incorporación dinámica sin código en la interfaz**:
- El catálogo de pruebas es consultado reactivamente por la interfaz de usuario.
- Los especialistas de automatización pueden registrar nuevos escenarios de prueba, ajustar duraciones estimadas o alterar estados de madurez en el núcleo del sistema, y la consola de administración los refleja de manera instantánea, agrupándolos bajo el dominio correspondiente y recalculando los indicadores de cobertura.

### 4.2 Los 7 Dominios de Negocio Evaluados
Las pruebas automatizadas de la plataforma cubren el ciclo operativo integral del negocio gastronómico a través de siete dominios canónicos:

1. **`tenancy` (Aislamiento de Inquilinos, Holdings y Sucursales):**
   - Evalúa el ciclo de vida de organizaciones gastronómicas: alta de holdings, creación de sedes locales, asignación de planes SaaS y estricto aislamiento de datos para evitar cualquier fuga de información entre restaurantes competidores.
2. **`auth_rbac` (Seguridad, Identidad y Control de Acceso):**
   - Verifica la matriz jerárquica de permisos en tres niveles (módulo, submódulo y acción permitida).
   - Audita que cajeros, meseros, cocineros y administradores accedan estrictamente a las funciones asignadas, bloqueando intentos de elevación de privilegios o suplantación de identidad.
3. **`inventory` (Gestión de Inventario FEFO y Lotes Perecibles):**
   - Valida la regla de oro gastronómica: primero en caducar, primero en ser consumido (*FEFO*).
   - Audita alertas preventivas de vencimiento, seguimiento de temperaturas en bodegas frías y mermas por caducidad con segregación de autorizaciones.
4. **`recipes` (Escandallo Recursivo y Fichas Técnicas):**
   - Evalúa el costeo matemático de platos y preparaciones intermedias (sub-recetas culinarias).
   - Monitorea mermas por cocción y desposte, verificación de alérgenos obligatorios y rentabilidad porcentual por menú.
5. **`procurement` (Abastecimiento, Balanza y Facturación Tributaria):**
   - Audita el flujo de compras a proveedores: emisión de órdenes, pesaje obligatorio en muelle de recepción con balanza digital, conciliación contra documentos tributarios electrónicos oficiales (facturas electrónicas) y extracción óptica de datos.
6. **`finops` (Gobernanza Financiera de IA y Créditos OppyFy):**
   - Supervisa el consumo transparente y atómico de saldo de inteligencia artificial en las consultas del asistente OppyFy.
   - Verifica la auditoría inmutable de solicitudes, cuotas asignadas a cada inquilino y bloqueo inmediato ante saldo insuficiente, con certificación formal de costo cero y cero impacto en billeteras de clientes comerciales de producción.
7. **`pos` (Punto de Venta, Comandas y Modalidades de Servicio):**
   - Evalúa la velocidad de facturación en barra y salón, despacho continuo de comandas a pantallas de cocina (*KDS*), sincronización del modo Buffet, modo Manos Libres y despacho de pedidos a domicilio.

### 4.3 Estados de Madurez Operacional de las Pruebas
Cada prueba en el catálogo expone un estado de madurez estandarizado:
- **`ready` (Lista para Ejecución 🟢):**
  - La prueba se encuentra completamente construida, probada y lista para su ejecución interactiva.
  - Permite ser lanzada de forma individual o como parte de corridas por lote.
- **`in_progress` (En Desarrollo Activo 🟡):**
  - La prueba está asignada y en construcción por el especialista en automatización de navegadores reales.
  - La interfaz muestra un indicador distintivo con advertencia de desarrollo en curso, evitando falsos reportes de error por pruebas incompletas.
- **`planned` (Planificada en Hoja de Ruta ⚪):**
  - Escenario identificado y documentado en la hoja de ruta de calidad de la plataforma.
  - Expone el alcance proyectado, las etiquetas funcionales y la duración estimada, permitiendo a los directores técnicos medir la brecha de cobertura pendiente.

### 4.4 Métricas de Cobertura y Fórmulas de Consistencia
La consola de calidad garantiza consistencia matemática estricta en sus indicadores:
- **Conservación de Conteos:**
  El total de pruebas del catálogo equivale exactamente a la suma de pruebas listas, en progreso y planificadas.
- **Cálculo Determinista de Cobertura:**
  El porcentaje de cobertura automatizada refleja la proporción de pruebas listas frente al total del catálogo:
  $$\text{Porcentaje de Cobertura} = \frac{\text{Pruebas Listas}}{\text{Total de Pruebas}} \times 100$$
  Este valor se actualiza en tiempo real conforme los especialistas de calidad completan la implementación de nuevos escenarios.
- **Resumen por Dominio:**
  Cada uno de los 7 dominios expone su propio conteo de pruebas listas sobre su total particular, permitiendo identificar rápidamente áreas funcionales que requieren mayor esfuerzo de automatización.

### 4.5 Modos y Alcance de Ejecución
- **Modos de Velocidad:**
  - *Demostración Humana en Vivo (Live Demo):* Intercala retardos de 500 milisegundos entre acciones de navegación e interacción, permitiendo que auditores, evaluadores o clientes sigan visualmente el comportamiento de la plataforma en la pantalla.
  - *Modo CI Optimizado:* Ejecuta las pruebas a velocidad de máquina sin esperas artificiales, ideal para ciclos de regresión rápida en laboratorio.
- **Alcances de Disparo:**
  - *Global (`all`):* Ejecuta la totalidad de pruebas en estado listo de los 7 dominios.
  - *Por Dominio (`domain`):* Ejecuta únicamente la suite perteneciente al área funcional seleccionada.
  - *Individual (`test`):* Ejecuta quirúrgicamente un caso de prueba puntual para depuración rápida de comportamientos específicos.

### 4.6 Terminal de Observabilidad en Vivo y Evidencia Forense
- **Streaming de Pasos en Vivo:** Cada acción efectuada por el ejecutor de pruebas emite un evento instantáneo hacia la terminal de la consola, indicando el paso actual, el mensaje descriptivo, la duración en milisegundos y el estado de la aserción.
- **Capturas Visuales de Evidencia:** En aserciones clave o ante discrepancias visuales, el sistema genera capturas de pantalla de la interfaz y las vincula directamente en la bitácora de la terminal, facilitando el análisis visual inmediato sin requerir descarga de archivos pesados.

---

## 5. Motor de Simulación Temporal FEFO y Time-Travel

El **Simulador FEFO y Motor de Time-Travel** implementa una suite de capacidades avanzadas para la gestión predictiva de existencias y control de mermas bajo la norma gastronómica FEFO (*First-Expired, First-Out*).

### 5.1 Regla de Oro Gastronómica y Semáforo FEFO de 4 Estados Canónicos
Para eliminar ambigüedades en la manipulación culinaria y la programación de compras, el sistema clasifica automáticamente cada lote evaluado en cuatro estados canónicos disjuntos y exhaustivos en función de los días restantes de vida útil proyectada:

| Estado Canónico | Días Restantes ($D_{\text{rem}}$) | Semáforo Visual | Tasa de Riesgo ($\lambda$) | Protocolo Operativo Gastronómico |
| :--- | :---: | :---: | :---: | :--- |
| **`OPTIMAL`** | $\ge 15\text{ días}$ | Verde Esmeralda (`#10b981`) | $0.00$ ($0\%$) | Frescura óptima garantizada. Rotación estándar bajo política FIFO/FEFO sin acción requerida. |
| **`WARNING`** | $7\text{ a }14\text{ días}$ | Ámbar / Amarillo (`#f59e0b`) | $0.00$ ($0\%$) | Ventana de atención preventiva. Priorización en programación de producción, escandallo y minutas. |
| **`CRITICAL`** | $1\text{ a }6\text{ días}$ | Naranja Carmín (`#f97316`) | $0.75$ ($75\%$) | Riesgo inminente de caducidad (24h a 144h). Acción quirúrgica: congelado, pase forzado a menú del día, rebaja de buffet o traspaso urgente. |
| **`EXPIRED`** | $\le 0\text{ días}$ | Rojo Escarlata (`#ef4444`) | $1.00$ ($100\%$) | Vencimiento sanitario cumplido. Bloqueo automático para despacho según normas sanitarias HACCP. Retiro físico obligatorio y merma total. |

### 5.2 Cuantificación Financiera de Merma (*Merma Risk Math*)
El impacto financiero del vencimiento no se estima de forma arbitraria; se calcula con rigor contable evaluando la pérdida monetaria estimada de cada lote:
$$\text{Pérdida por Lote} = \text{Cantidad de Stock} \times \text{Costo Unitario} \times \lambda(\text{Estado})$$
donde la tasa de riesgo $\lambda$ aplica:
- $0\%$ para lotes en estado `OPTIMAL` y `WARNING` (pérdida nula).
- $75\%$ para lotes en estado `CRITICAL` (probabilidad alta de no absorción en cocina sin intervención).
- $100\%$ para lotes en estado `EXPIRED` (pérdida efectiva y desecho obligatorio).

El riesgo total consolidado se computa en la moneda base del local (CLP) y se convierte simultáneamente a la divisa de referencia (USD) según el tipo de cambio bancario vigente, permitiendo análisis financiero a nivel de holding internacional.

### 5.3 Los 3 Escenarios Preconfigurados de Demostración
Para facilitar auditorías, capacitaciones y pruebas comerciales de alta fidelidad, la consola provee tres escenarios calibrados matemáticamente con un clic:

1. **Escenario Saludable (`HEALTHY`):**
   - *Distribución:* 90% Óptimo, 10% Advertencia, 0% Crítico, 0% Caducado.
   - *Riesgo Financiero:* $0\text{ CLP}$ ($0.0\%$).
   - *Desplazamiento sugerido:* $0\text{ días}$.
   - *Propósito:* Representa un local con rotación perfecta, abastecimiento justo a tiempo y control de calidad impecable.
2. **Escenario Advertencia Fin de Semana (`WARNING`):**
   - *Distribución:* 50% Óptimo, 30% Advertencia, 20% Crítico ($\le 48\text{h}$), 0% Caducado.
   - *Riesgo Financiero:* Controlado ($\approx 15\%$ de merma proyectada).
   - *Desplazamiento sugerido:* $+7\text{ días}$.
   - *Propósito:* Simula existencias perecibles acumuladas tras un fin de semana o feriado largo, requiriendo reasignación a recetas del día.
3. **Escenario Crítico / Rotura de Frío (`CRITICAL`):**
   - *Distribución:* 25% Óptimo, 25% Advertencia, 35% Crítico, 15% Caducado.
   - *Riesgo Financiero:* Elevado ($\approx 42.5\%$ de merma proyectada).
   - *Desplazamiento sugerido:* $+18\text{ días}$.
   - *Propósito:* Simula una contingencia térmica (cámara frigorífica apagada) o auditoría forense con pérdidas reales cuantificables.

### 5.4 Control de Time-Travel y Proyección de Cero Retardo (*Zero-Lag*)
- **Rango Temporal:** Permite viajar entre $-30$ días (pasado) y $+60$ días (futuro) con paso de 1 día.
- **Auditoría Forense Retrospectiva ($-30$ a $-1$ días):** Permite verificar retrospectivamente el estado de los lotes en fechas pasadas para resolver disputas de recepción de mercadería o auditorías de descarte.
- **Proyección Prospectiva ($+1$ a $+60$ días):** Permite planificar menús, anticipar alertas de caducidad y proyectar mermas futuras.
- **Evaluación Inmediata en Cliente (*Zero-Lag*):** Al mover el control deslizante, la proyección se recalcula instantáneamente en memoria local a 60 cuadros por segundo, complementándose con validación analítica asíncrona hacia el servicio central.

### 5.5 Acción Quirúrgica "Sincronizar fechas a Hoy"
- **El Problema Operativo Resuelto:**
  Cuando un entorno de prueba o staging permanece inactivo durante semanas, los lotes sintéticos previamente generados envejecen respecto al calendario real, ocasionando que la totalidad de existencias figure como vencida (`EXPIRED`) y bloqueando las pruebas funcionales de venta y recetas.
- **Mecanismo Quirúrgico:**
  1. Identifica los lotes con caducidad vencida ($\le 0\text{ días}$).
  2. Reasigna una nueva vida útil activa garantizada: $20\text{ a }29\text{ días}$ para insumos estándar de bodega y $4\text{ días}$ para preparaciones y buffet (ciclos de 72 horas).
  3. Restablece el desplazamiento temporal a $0\text{ días}$ (Presente).
  4. Preserva intactas las cantidades de stock, costos unitarios, trazabilidad de insumos y recetas del local, sin necesidad de destruir ni resembrar la base de datos.

---

## 6. Políticas de Protección y Gobernanza de Entornos

Para salvaguardar la confianza de los clientes y la integridad operativa del ecosistema, el Sandbox implementa una matriz de protección inmutable según el entorno en ejecución:

| Entorno | Lectura y Simulación Analítica | Desplazamiento Físico FEFO / Mock Data | Sincronización a Hoy | Guardrail de Seguridad |
| :--- | :--- | :--- | :--- | :--- |
| **Local / Preview / CI** | Permitida libremente | Permitida en esquemas aislados | Permitida en esquemas aislados | Confinamiento en esquemas autorizados |
| **Staging** | Permitida | Requiere confirmación explícita | Requiere confirmación explícita | Modal de confirmación obligatoria |
| **Producción** | Permitida (Solo cálculo) | **BLOQUEO TOTAL INCONDICIONAL** | **BLOQUEO TOTAL INCONDICIONAL** | Rechazo HTTP 403 incondicional ante mutaciones |

### 6.1 Reglas Inviolables de Aislamiento
1. **Esquemas de Base de Datos Exclusivos para Laboratorio:**
   Las pruebas automatizadas, desplazamientos de fechas y la inyección de datos de prueba operan exclusivamente sobre inquilinos de laboratorio autorizados (`tenant_qa_lab`, `tenant_genesis`, `tenant_sandbox_fefo` o esquemas prefijados con `tenant_qa_*`, `tenant_sandbox_*`).
2. **Prohibición Absoluta sobre Inquilinos Comerciales:**
   Cualquier intento de disparar desplazamientos de fechas, sincronizaciones o purgas apuntando a esquemas reales de clientes de producción es rechazado de inmediato antes de cualquier ejecución con código de error de esquema no aislado.
3. **Blindaje de Créditos y Telemetría de Inteligencia Artificial:**
   El motor de simulación FEFO opera 100% en memoria en modo simulación. Cero llamadas a modelos generativos son emitidas, cero créditos son debitados de las billeteras comerciales y cero registros contaminan las bitácoras analíticas de producción ($\Delta \text{Balance} = 0$).
4. **Hermeticidad RAG y Anti-Contaminación de Índices:**
   Las fechas proyectadas o desplazadas en esquemas de laboratorio nunca se indexan en memorias semánticas ni en bases vectoriales de clientes reales, garantizando que el asistente de cocina jamás recupere información desfasada o ficticia.

---

## 7. Control de Acceso y Permisos de Usuario

El acceso al Sandbox está restringido por el sistema de roles y privilegios de tres niveles de OppyTec:
- **`platform_admin.sandbox.access`**: Permiso de lectura y supervisión. Permite acceder a las vistas, consultar el catálogo dinámico de pruebas, revisar métricas de cobertura, explorar presets, ejecutar simulaciones analíticas FEFO no destructivas y observar ejecuciones anteriores en modo sólo-lectura.
- **`platform_admin.sandbox.manage`**: Permiso operativo avanzado. Habilita la inyección de datos sintéticos, la ejecución de Factory Reset, el disparo interactivo de pruebas Playwright en cualquiera de sus alcances, la aplicación de desplazamientos físicos de fechas FEFO y la ejecución de la sincronización quirúrgica a hoy en esquemas de prueba autorizados.
