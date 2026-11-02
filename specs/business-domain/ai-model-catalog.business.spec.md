# Catálogo de Modelos de Inteligencia Artificial y Motores JEV

> Audiencia: Administradores de negocio, directores de tecnología, producto, soporte comercial y clientes de OppyTec v2.0. Sin detalles técnicos internos de programación ni comandos de base de datos.

## Resumen Ejecutivo

El Catálogo de Modelos de Inteligencia Artificial y Motores JEV centraliza la definición, tarificación, rendimiento y ciclo de vida de todos los motores cognitivos que impulsan las capacidades inteligentes de OppyTec v2.0 (el asistente operativo OppyFy, los clasificadores automáticos de facturas, los enrutadores de herramientas de inventario y los servicios de vectorización semántica).

La plataforma opera bajo una arquitectura cognitiva híbrida y eficiente:
1. **Motores de Sistema 1 (JEV):** Motores especializados de decisión lógica ultrarrápida (clasificación, validación de reglas e inferencia determinista) con latencias mínimas (inferiores a 100 ms) y costos prácticamente nulos, optimizando más del 99% de las micro-decisiones repetitivas.
2. **Modelos de Sistema 2 (LLM):** Modelos generativos avanzados provistos por proveedores líderes (Google DeepMind, Anthropic, OpenAI) orientados a tareas complejas de razonamiento estratégico, síntesis documental y atención asistida por conversación.
3. **Modelos de Vectorización (Embeddings):** Motores dedicados a la conversión de documentación funcional y memorias operativas en representaciones vectoriales para búsqueda contextual en el espacio de trabajo.

La correcta administración de este catálogo garantiza que la tarificación por millón de tokens en dólares (USD) refleje con exactitud matemática el gasto incurrido y proteja la rentabilidad en la deducción de créditos de cada local gastronómico.

---

## Reglas de Negocio

### 1. Niveles de Motores Cognitivos (`engine_tier`)
Cada motor registrado en el catálogo pertenece estrictamente a uno de los tres niveles operativos reconocidos por la plataforma:
- **`SYSTEM_1_JEV`:** Motores de decisión rápida propios de OppyTec. Ejecutan verificaciones binarias, selección de herramientas operativas y asignación de intenciones con latencia P95 de 50 ms a 150 ms y costo por millón de tokens de valor cero o marginal.
- **`SYSTEM_2_LLM`:** Modelos de lenguaje generativo de razonamiento profundo para conversaciones operativas y generación estructurada, con latencias P95 entre 600 ms y 2500 ms.
- **`EMBEDDING`:** Modelos de generación vectorial para memoria semántica y consulta de la documentación funcional de la plataforma.

### 2. Estructura de Atributos de Cada Modelo
Cada registro del catálogo contiene las siguientes dimensiones fundamentales de negocio:
- **Identificador Técnico (`slug` / `model_slug`):** Clave única, inmutable y normalizada en minúsculas (por ejemplo: `gemini-3.8-flash`, `gemini-4-argon`, `claude-3-7-sonnet`, `jev-fast-classifier`, `text-embedding-004`).
- **Nombre Desplegable (`display_name`):** Denominación comercial legible para paneles de control y selectores administrativos (por ejemplo: *"Gemini 3.8 Flash"*, *"Claude 3.7 Sonnet"*, *"Clasificador Rápido JEV"*).
- **Proveedor del Motor (`provider`):** Identificación de la entidad tecnológica o infraestructura proveedora (por ejemplo: `Google DeepMind`, `Anthropic`, `OpenAI`, `JEV Internal`).
- **Nivel de Motor (`engine_tier`):** Categoría operativa descrita (`SYSTEM_1_JEV`, `SYSTEM_2_LLM`, `EMBEDDING`).
- **Costos Tarifarios por Millón de Tokens (USD):**
  - *Costo de Entrada (`input_cost_per_1m_usd`):* Tarifa cobrada por el procesamiento de tokens de entrada enviados al modelo.
  - *Costo de Tokens en Caché (`cached_cost_per_1m_usd`):* Tarifa reducida aplicada cuando los tokens de entrada son reutilizados desde la memoria caché del proveedor.
  - *Costo de Salida (`output_cost_per_1m_usd`):* Tarifa aplicada por cada millón de tokens de texto o respuesta generados por el modelo.
  - *Costo de Vectorización (`embedding_cost_per_1m_usd`):* Tarifa aplicada por la generación de vectores para búsqueda semántica.
- **Métricas de Rendimiento y Calidad:**
  - *Latencia P95 Objetivo (`latency_p95_ms`):* Cota de tiempo esperada en milisegundos para el 95% de las solicitudes atendidas (por ejemplo: 50 ms para JEV, 800 ms para LLMs rápidos).
  - *Umbral Mínimo de Confianza (`min_confidence_score`):* Nivel de certeza estadística requerido (valor numérico entre 0.00 y 1.00) aplicable a motores JEV para aceptar automáticamente una clasificación sin requerir escalamiento a un modelo generativo.
  - *Capacidad Máxima de Contexto (`max_context_tokens`):* Límite superior de tokens utilizables simultáneamente en una sesión de consulta (por ejemplo: 1.000.000 tokens).
- **Banderas Operativas de Estado:**
  - *Habilitado (`is_enabled`):* Interruptor general que autoriza o suspende el despacho de tráfico al modelo.
  - *Predeterminado (`is_default`):* Marca que señala al modelo principal seleccionado para procesar solicitudes en su nivel correspondiente.
  - *Contingencia / Respaldo (`is_fallback`):* Marca que designa al modelo secundario que asume automáticamente las consultas si el modelo predeterminado sufre caídas de servicio o saturación.
- **Descripción Funcional (`description`):** Resumen explicativo sobre la especialidad, capacidades y recomendaciones de uso del modelo en el ecosistema OppyTec.

### 3. Matriz de Control de Acceso RBAC de 3 Niveles
La seguridad y gobernanza del catálogo se rige bajo el principio de mínimo privilegio en tres niveles de permisos:
- **`platform_admin.ai_models.read` (Lectura Global Abierta):**
  - Permiso otorgado a todo el personal global, trabajadores de soporte técnico, auditores y especialistas de producto de OppyTec v2.0 autenticados.
  - Permite visualizar el catálogo completo, auditar tarifas vigentes, consultar métricas de latencia y entender la distribución de modelos en servicio.
- **`platform_admin.ai_models.create` (Alta Exclusiva de Administrador):**
  - Restringido a administradores globales de la plataforma.
  - Permite dar de alta nuevos motores cognitivos y modelos LLM, definiendo sus costos, proveedor, capacidades y límites de contexto.
- **`platform_admin.ai_models.update` (Modificación de Tarifas y Parámetros en Caliente):**
  - Restringido a administradores globales de la plataforma.
  - Permite ajustar tarifas por millón de tokens ante variaciones de precios de los proveedores, cambiar latencias estimadas, redefinir el modelo predeterminado y conmutar el estado de activación sin necesidad de reiniciar la aplicación.
- **`platform_admin.ai_models.delete` (Retiro y Desactivación de Modelos):**
  - Restringido a administradores globales de la plataforma.
  - Gobierna el ciclo de vida de retiro de modelos, haciendo cumplir las reglas de integridad referencial histórica.

### 4. Invariante de Protección Financiera: Baja Lógica Obligatoria (Soft Delete)
Para proteger la integridad de las finanzas y la trazabilidad de los costos facturados a los locales gastronómicos:
- **Modelos con Historial de Telemetría:** Si un modelo ya cuenta con solicitudes registradas en la bitácora de telemetría de Sistema 1 (JEV) o Sistema 2 (LLM/Embeddings), **queda terminantemente prohibida su eliminación física o borrado permanente**.
- **Comportamiento ante Intento de Eliminación:** Cualquier acción de borrado sobre un modelo con historial de consumo se convierte de manera forzosa en una **baja lógica** (`is_enabled = Falso`), archivando el modelo e impidiendo nuevas invocaciones futuras.
- **Preservación Inmutable de Bitácoras:** El registro histórico y las tarifas históricas aplicadas en cada consulta pasada permanecen intactos, asegurando que los reportes de margen bruto, consumo de créditos y auditorías financieras no presenten desvíos ni inconsistencias.
- **Eliminación Física Condicional:** Solo en el caso excepcional de un modelo recién dado de alta por error que jamás haya procesado ninguna llamada en telemetría (cero registros de consumo asociados), el sistema admitirá la eliminación física completa.

### 5. Invariantes de Modelo Predeterminado y Contingencia
- **Exactamente un Predeterminado por Nivel:** En cada nivel cognitivo (`SYSTEM_1_JEV`, `SYSTEM_2_LLM`, `EMBEDDING`) debe existir en todo momento exactamente un modelo con la bandera `is_default = Verdadero`.
- **Protección contra Desactivación del Predeterminado:** No es posible desactivar (`is_enabled = Falso`) ni dar de baja lógica al modelo predeterminado en servicio. Para desactivarlo, el administrador debe primero promover otro modelo activo a la categoría de predeterminado.
- **Modelo de Contingencia:** En caso de que se configure un modelo de respaldo (`is_fallback = Verdadero`), este debe estar habilitado y no puede ser el mismo modelo predeterminado del mismo nivel.

---

## Escenarios de Negocio

### Escenario 1: Incorporación de una Versión LLM Más Económica y Transición Fluida
1. El proveedor Google DeepMind lanza una nueva versión de modelo generativo con un costo 30% inferior y menor latencia.
2. Un administrador de plataforma con permiso `platform_admin.ai_models.create` da de alta el identificador `gemini-3.8-flash` con sus tarifas por millón de tokens actualizadas y latencia P95 de 750 ms.
3. El administrador verifica la operatividad y luego ejecuta una actualización marcando el nuevo modelo como `is_default = Verdadero`.
4. El sistema asigna el nuevo modelo predeterminado y desmarca automáticamente al anterior, permitiendo que todas las consultas de OppyFy adopten la nueva tarifa reducida de forma inmediata sin interrupción de servicio.

### Escenario 2: Retiro de un Modelo Antiguo con Historial de Consumo (Baja Lógica)
1. El equipo directivo decide descontinuar un modelo antiguo que ya procesó miles de consultas durante los meses previos.
2. El administrador selecciona la opción de eliminar dicho modelo.
3. El sistema inspecciona los registros históricos de telemetría y detecta que el modelo posee registros de consumo asociados.
4. En lugar de borrar el registro, el sistema aplica la baja lógica desactivando el modelo (`is_enabled = Falso`), notificando al administrador que el modelo ha sido archivado para salvaguardar la trazabilidad financiera histórica.

### Escenario 3: Consulta del Catálogo por Personal de Soporte Técnico
1. Un especialista del equipo de soporte de OppyTec con permiso `platform_admin.ai_models.read` recibe una consulta de un cliente sobre los costos de procesamiento de su menú.
2. El especialista ingresa al visor del catálogo y revisa los valores vigentes de costo de entrada, salida y tokens en caché.
3. La interfaz le permite visualizar la información en modo de solo lectura, manteniendo ocultos y deshabilitados los botones de edición y eliminación para resguardar la seguridad operativa.

---

## Documento Técnico Par

Especificación técnica de ingeniería con contratos de datos, puertos DDD, endpoints REST, esquemas Pydantic y pruebas de integración: `ai-model-catalog.code.spec.md`.
