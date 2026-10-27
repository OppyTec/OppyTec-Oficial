# Asistente Inteligente OppyFy y Gobernanza de IA

> Audiencia: Clientes, propietarios de restaurantes y hoteles, administradores de negocio, equipos de producto y soporte comercial. Sin detalles técnicos internos de programación.

## Resumen Ejecutivo

OppyFy es el copiloto operativo y estratégico inteligente de OppyTec v2.0 para locales gastronómicos y hoteleros. El asistente asiste al personal de cocina, bodega, compras, eventos y administración respondiendo preguntas operativas mediante texto y voz, consultando las especificaciones funcionales del sistema y calculando en tiempo real el estado del negocio (existencias, rotación de insumos, factibilidad de banquetes, mermas y desvíos de precios de proveedores).

OppyFy opera bajo principios estrictos de seguridad de la información, protección de costos financieros, economía sustentable de créditos sin caducidad y gobernanza granular delegada en el dueño de cada local.

---

## Reglas de Negocio

### 1. Doble Misión Operativa y Cortafuegos de Privacidad
- **Misión de Conocimiento Funcional (Cómo funciona OppyTec):** OppyFy responde dudas sobre el uso de la plataforma, normas de rotación de insumos, fórmulas de costos y buenas prácticas operativas consultando únicamente la documentación funcional oficial para clientes. No tiene acceso a código fuente ni a la ingeniería interna del sistema.
- **Misión Operativa del Restaurante (Inteligencia del Local):** OppyFy consulta las existencias, compras, recetas y eventos del local únicamente a través de funciones predefinidas de negocio y jamás genera consultas arbitrarias a la base de datos.
- **Aislamiento Estricto por Restaurante:** Cada local u hotel accede exclusivamente a sus propios datos de inventario y pedidos. Bajo ninguna circunstancia un establecimiento puede acceder o deducir información de otro restaurante.
- **Preservación Inmutable de Marcas y Proveedores:** El nombre comercial de insumos, proveedores y marcas registradas (como el proveedor "Pollo King") se mantiene intacto y fidedigno sin alteraciones terminológicas en todas las respuestas del asistente.

### 2. Medidor Semafórico de Contexto y Rollover Anti-Alucinación
Para garantizar respuestas precisas y evitar que las conversaciones extensas degraden la calidad o provoquen errores en cálculos numéricos (*Context Rot*), OppyFy dispone de un indicador visual circular de salud del contexto:
- 🟢 **Zona Verde (Uso inferior al 65%):** Conversación fluida con capacidad plena para incorporar nuevos datos e historial reciente.
- 🟡 **Zona Ámbar (Uso entre el 66% y el 85%):** Advertencia preventiva recomendando enfocar las preguntas o considerar el inicio de un nuevo hilo temático.
- 🔴 **Zona Roja (Uso superior al 85%):** Bloqueo automático preventivo de nuevos mensajes crudos para proteger la exactitud de las respuestas. En este estado, el sistema habilita el botón interactivo **«Continuar en Hilo Fresco con Resumen Inteligente»**.
- **Traspaso Asistido a Hilo Fresco:** Al pulsar el botón, OppyFy sintetiza de forma estructurada los acuerdos, números y datos clave de la sesión, abriendo un nuevo hilo de trabajo limpio con solo un 5% de contexto consumido, preservando la continuidad del trabajo sin degradación.

### 3. Economía de Créditos: Acumulables y Sin Vencimiento
- **Independencia del Plan de Suscripción:** A diferencia de las cuotas de usuarios o bodegas del plan mensual, los paquetes de créditos de IA funcionan como saldo propio del restaurante.
- **Acumulación Aritmética Permanente:** Los créditos comprados mediante paquetes de recarga (por ejemplo, 1.000, 5.000 o 20.000 créditos) se suman directamente al saldo existente (1.000 + 10.000 = 11.000) y **jamás caducan al cierre de mes**.
- **Consumo Proporcional por Consulta:** Cada interacción descuenta créditos según el nivel de procesamiento requerido (clasificación rápida de intención, consulta documental o ejecución de reportes operativos complejos). Si el saldo de créditos del restaurante o del trabajador se agota, OppyFy suspende las consultas informando al usuario la necesidad de recarga sin interrumpir las demás funciones del restaurante.

### 4. Panel de Gobernanza y RBAC Exclusivo de OppyFy
El Propietario o Administrador General del local dispone de una consola de gobernanza exclusiva dentro de OppyFy, independiente de los roles y pantallas tradicionales del software:
- **Árbol de Dominios y Subdominios Personalizable:** Cada restaurante puede crear, renombrar, reordenar y activar o desactivar dominios temáticos de consulta (por ejemplo: "Inventario y Almacenes", "Abastecimiento y Proveedores", "Banquetes y Producción", "Mermas y Rendimientos").
- **Protección Automática de Costos Financieros:** Los permisos de cada subdominio cuentan con una casilla de visualización de costos. Si un trabajador (por ejemplo, un ayudante de cocina o un bodeguero) tiene permiso para consultar stock pero no para ver valores monetarios, el sistema oculta automáticamente precios de compra, márgenes y costos unitarios de las respuestas y tablas analíticas.
- **Permisos Temporales con Triple Caducidad:** El administrador puede otorgar acceso temporal a un colaborador bajo cualquiera de tres condiciones automáticas de expiración (lo que ocurra primero):
  1. *Por Fecha y Hora:* Vencimiento en un día y hora determinados (útil para reemplazos de turno o auditorías externas).
  2. *Por Límite de Consultas:* Límite máximo de preguntas autorizadas (por ejemplo, permitir hasta 5 preguntas operativas).
  3. *Por Tope de Créditos:* Monto máximo de créditos IA asignados para esa tarea puntual.
- **Billetera y Cupos por Trabajador:** El administrador puede fijar un tope mensual o saldo individual a cada colaborador para asegurar que un solo usuario no consuma la totalidad de los créditos del negocio.

### 5. Visor de Auditoría de Consultas (Audit Log)
- Toda consulta formulada a OppyFy queda registrada en una bitácora inmutable accesible para la gerencia del local.
- La bitácora exhibe la fecha y hora, el usuario que consultó, el texto del mensaje, el subdominio asignado, si la consulta fue permitida o bloqueada por permisos, y los créditos descontados.
- Las consultas que intentan acceder a información no autorizada quedan registradas con la etiqueta de «Consulta Bloqueada por Permisos», facilitando la revisión preventiva de seguridad interna.

### 6. Espacio de Trabajo con Pantalla Dividida (Split-View Canvas)
- Cuando una respuesta de OppyFy incluye tablas detalladas de existencias, comparativas de precios de proveedores o gráficos de costos de recetas, la información se proyecta en un panel lateral interactivo (Canvas).
- Desde el Canvas, los responsables pueden ordenar columnas, descargar los datos en formato de hoja de cálculo o generar borradores de órdenes de compra con un solo toque.

---

## Escenarios de Uso

### Escenario 1: Consulta de Rotación FEFO por un Jefe de Cocina
1. El jefe de cocina pregunta a OppyFy: *"¿Qué productos lácteos y carnes vencen en los próximos 5 días en la Bodega de Fríos?"*.
2. OppyFy verifica que el colaborador tiene permiso en el subdominio de inventario.
3. El asistente consulta las existencias con vencimiento próximo y despliega en el Canvas una lista ordenada por fecha de caducidad más próxima (criterio FEFO).
4. Como el usuario no tiene permiso de visualización de costos, la tabla muestra lotes, kilos y fechas de caducidad, omitiendo precios de compra.
5. El medidor de contexto avanza ligeramente en la zona verde y se descuenta el consumo exacto de la billetera del colaborador.

### Escenario 2: Simulación de Factibilidad para Banquete de 150 Personas
1. La encargada de eventos consulta: *"¿Tenemos insumos suficientes en almacén para preparar 150 porciones de Pollo al Horno con papas rústicas para este sábado?"*.
2. OppyFy evalúa los ingredientes de la receta contra el inventario disponible en tiempo real.
3. El asistente responde informando que hay suficiente pechuga del proveedor "Pollo King", pero detecta un faltante de 12 kg de papas rústicas.
4. OppyFy ofrece la opción de crear un borrador de pedido de compra sugerido por la cantidad faltante para revisión del área de adquisiciones.

### Escenario 3: Rollover Asistido tras Conversación Extensa
1. El administrador ha realizado múltiples análisis de mermas y costos a lo largo de su turno.
2. El medidor circular de contexto alcanza el 86% y cambia a color rojo, bloqueando el envío de nuevas preguntas para evitar respuestas inexactas.
3. El sistema muestra la advertencia y habilita el botón «Continuar en Hilo Fresco con Resumen Inteligente».
4. El administrador pulsa el botón; OppyFy genera un resumen con los tres desvíos de merma acordados y los números clave, abriendo un nuevo chat al 5% de capacidad para continuar trabajando fluidamente.

---

## Documento técnico par
Equivalente para desarrolladores y arquitectos: `oppy-ai-and-voice.code.spec.md`.
