# Proyecciones de Stock, Quiebres y Autonomía Operativa

> Audiencia: administradores de restaurante, chefs ejecutivos, gerentes de operaciones, producto y soporte. Sin detalles técnicos internos de implementación.

## Resumen
El módulo de Proyección simula día a día la curva futura de existencias para cada insumo y producto del local gastronómico, anticipando con precisión cuándo ocurrirá un quiebre de stock o cuándo se perforará el stock mínimo de seguridad. A través del motor de proyección basado en consumo diario promedio, rotación de lotes por caducidad (FEFO) y requerimientos de eventos o banquetes agendados, el sistema calcula los días de autonomía restante y emite recomendaciones preventivas de traspaso entre bodegas y órdenes de reposición antes de que se produzca una rotura de cocina o salón.

## Reglas de Negocio

### 1. Horizontes Temporales de Proyección
- El usuario puede proyectar las existencias en ventanas temporales estandarizadas de **7, 15, 30, 60 y 90 días**.
- Para operaciones diarias de cocina y perecibles, la ventana estándar de 7 o 15 días permite evitar mermas por vencimiento.
- Para insumos secos, congelados y compras a escala con proveedores distantes, los horizontes de 30 a 90 días facilitan la negociación por volumen y la planificación financiera.

### 2. Días de Autonomía y Cálculo de Consumo
- **Tasa Diaria de Consumo:** Se calcula analizando el ritmo histórico de salidas de inventario de los últimos 30 días, ponderando el ritmo real de preparación y venta.
- **Días de Autonomía:** Representa la cantidad de días que el stock actual puede sostener las operaciones sin nuevas compras ni traspasos, calculada como el stock disponible dividido por la tasa de consumo diario.
- **Fecha de Quiebre Proyectado:** El día calendario exacto en el que el stock proyectado llegará a cero o se agotará completamente.

### 3. Semáforo de Urgencia Operativa
Cada insumo recibe un estado semafórico claro e intuitivo según la cercanía del quiebre proyectado dentro del horizonte seleccionado:
- **Crítico (Rojo):** Insumo que sufrirá quiebre de stock en menos de 7 días, o cuyo stock actual ya se encuentra por debajo del stock mínimo de seguridad. Requiere acción inmediata del encargado de compras o traspaso urgente.
- **Advertencia / Warning (Ámbar):** Insumo que alcanzará su punto de reorden o stock mínimo entre el día 8 y el día 15 del horizonte. Permite planificar pedidos regulares de abastecimiento.
- **Normal (Verde):** Insumo con autonomía suficiente superior a 15 días, con cobertura garantizada durante la ventana proyectada sin necesidad de reorden prematura.

### 4. Simulación FEFO y Demanda de Eventos
- **Primero en Vencer, Primero en Salir (FEFO):** La proyección descuenta primero los lotes más próximos a vencer. Si un lote no alcanzará a ser consumido antes de su fecha de caducidad, el sistema registra una pérdida proyectada por merma y acelera la fecha estimada de quiebre de stock.
- **Deducción de Eventos Agendados:** Si existen banquetes, matrimonios o reservas corporativas confirmadas en fechas futuras, el sistema deduce automáticamente las raciones requeridas según la ficha técnica de las recetas asociadas al banquete.

### 5. Recomendaciones de Traspaso Preventivo entre Bodegas
- Cuando una bodega (por ejemplo, Cocina Principal) presenta riesgo de quiebre crítico en los próximos días, pero otra bodega del mismo local (por ejemplo, Bodega Central) dispone de existencias con más de 20 días de autonomía, el sistema recomienda una transferencia interna preventiva.
- La sugerencia indica: bodega de origen, bodega de destino, cantidad exacta a transferir y días de autonomía recuperados en la bodega receptora, evitando compras de emergencia a precios desfavorables.

### 6. Integración con el Asistente Inteligente OppyFy
- El asistente de inteligencia artificial OppyFy cuenta con la capacidad de responder consultas de lenguaje natural sobre el estado de proyección:
  - *¿Qué productos quebrarán esta semana en Cocina Principal?*
  - *¿Cuántos días de autonomía le quedan al Lomo Vetado y al Salmón?*
  - *¿Existen sugerencias de traspaso preventivo entre bodegas para hoy?*
- El asistente responde con datos concretos, alertas preventivas y acciones recomendadas, respetando los permisos de seguridad y redactando automáticamente los valores monetarios de costo si el usuario no tiene privilegios financieros autorizados.

## Escenarios de Uso
- **Planificación Semanal del Chef:** El lunes por la mañana, el chef ejecutivo consulta a OppyFy cuáles son los insumos con quiebre projected en los próximos 5 días; el sistema destaca el Lomo Vetado (autonomía de 4 días) y sugiere transferir 15 kg desde la Bodega Central.
- **Prevención de Quiebre en Evento Corporativo:** Una reserva para 120 comensales programada para el sábado revela un déficit proyectado de Salmón de 11.5 kg; la alerta preventiva gatilla la orden de compra el martes con 48 horas de holgura.
- **Optimización de Capital de Trabajo:** El administrador filtra por insumos en estado verde con más de 60 días de autonomía, decidiendo pausar las compras de arroz y harina para liberar liquidez de caja.

## Documento técnico par
Para los contratos técnicos de base de datos relacional, enrutadores de servicios, modelos de datos, endpoints REST, eventos en tiempo real, hooks de React y pruebas automatizadas, consultar:
- `projections-and-stockouts.code.spec.md` (alias: `projection.spec.md`)
