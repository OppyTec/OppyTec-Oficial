# Gestión de Eventos, Salones, Banquetes y Consumo de Inventario

> Audiencia: Clientes, gerentes de banquetes, directores de operaciones, administradores de negocio, soporte y asistente OppyFy (Capa 3A). Sin detalles técnicos de persistencia ni código fuente.

## Resumen Ejecutivo

El módulo de Gestión de Eventos, Salones y Banquetes de OppyTec v2.0 proporciona a establecimientos gastronómicos, hoteles y centros de eventos una solución integral para la planificación comercial, reserva de espacios físicos, costeo culinario, asignación de personal y consumo automatizado de inventario.

El sistema erradica las tradicionales pérdidas por desabastecimiento o sobreventa gracias a un motor de disponibilidad temporal que impide el solapamiento de salones (*anti-overbooking*), una proyección analítica de faltantes que alerta sobre descalces de insumos antes de la fecha del banquete, el concepto pionero de **Stock Comprometido** (que reserva insumos para eventos futuros sin distorsionar la operación cotidiana), y un mecanismo de ejecución transaccional que rebaja automáticamente del inventario los ingredientes exactos (insumos directos, recetas gastronómicas y combos) al momento del servicio.

---

## Reglas de Negocio Fundamentales

### 1. Espacios Físicos y Salones
- **Catálogo de Salones:** Cada salón o recinto cuenta con un nombre identificatorio, capacidad máxima de comensales, notas técnicas y una codificación cromática para su reconocimiento visual en calendarios y tarjetas.
- **Estructura Tarifaria e IVA:** El sistema maneja precios con desagregación fiscal:
  - $\text{Precio Bruto} = \text{Precio Neto} \times (1 + \frac{\text{IVA Porcentaje}}{100})$.
  - Por defecto se aplica la alícuota general de IVA (19%), manteniendo el recálculo bidireccional y transparente en la configuración de cada recinto.
- **Estados Operativos e Higiénicos:** Un salón presenta en todo momento un estado operativo visible:
  - 🟢 **Limpio:** Listo para ser ocupado y recibir eventos.
  - 🔵 **En Uso:** Ocupado actualmente con una actividad en desarrollo.
  - 🟡 **Mantenimiento:** Inhabilitado temporalmente por reparaciones o acondicionamiento.
  - 🔴 **Sucio:** Requiere sanitización y montaje antes de admitir un nuevo servicio.
- **Vinculación con Áreas Operativas:** Un salón puede estar adscrito a una o múltiples áreas operativas (por ejemplo: "Salón Los Robles" vinculado a "Cocina Principal" y "Barra Terraza"), facilitando el filtrado selectivo y la delegación de responsabilidades.

### 2. Ciclo de Vida de los Eventos y Transiciones de Estado
Todo evento transita por un flujo de estados claramente definido:
- **Agendado (`AGENDADO`):** Evento confirmado y programado en el calendario para una fecha y franja horaria específicas. Reserva el salón e incrementa el stock comprometido de los insumos requeridos.
- **En Curso (`EN_CURSO`):** El evento está llevándose a cabo en la franja horaria actual.
- **Finalizado / Ejecutado (`EJECUTADO`):** El servicio se ha cumplido y se ha gatillado la ejecución de consumo. En este punto, los insumos, recetas y combos asignados se deducen irreversiblemente del inventario físico, liberando el stock comprometido y generando los asientos correspondientes en el libro mayor de Kardex.
- **Cancelado (`CANCELADO`):** Evento anulado por el cliente o la administración. Se libera inmediatamente la reserva del salón y se revoca la reserva de stock comprometido, devolviendo la disponibilidad libre a las bodegas.

### 3. Política Anti-Overbooking y Disponibilidad Temporal
- **Exclusión Temporal Estricta:** No es posible registrar ni reactivar dos eventos en el mismo salón cuyas franjas horarias se superpongan en la misma fecha calendario.
  - Dos eventos $A$ y $B$ colisionan si:
    $$\text{Fecha}_A = \text{Fecha}_B \quad \text{y} \quad \text{HoraInicio}_A < \text{HoraFin}_B \quad \text{y} \quad \text{HoraFin}_A > \text{HoraInicio}_B$$
- **Validación de Capacidad:** Si la cantidad de invitados declarada excede la capacidad máxima del salón asignado, el sistema emite una advertencia preventiva de aforo antes de confirmar la reserva.
- **Eventos sin Salón Físico:** Se admiten eventos de catering o servicios externos que no reservan un salón interno del establecimiento (`salon_id = NULL`), operando únicamente con lugar de entrega referencial y consumo de insumos.

### 4. Planificación Gastronómica y Desglose BOM (Bill of Materials)
Cada evento consolida sus requerimientos culinarios a través de tres vías complementarias:
1. **Insumos Directos:** Artículos individuales solicitados a una bodega específica (por ejemplo: botellas de vino de guarda, hielos, servilletas).
2. **Recetas Gastronómicas:** Platos del catálogo culinario con su multiplicador de porciones (por ejemplo: 150 porciones de "Filete con Salsa de Champiñones"). El sistema desglosa automáticamente los ingredientes brutos requeridos considerando mermas técnicas de elaboración.
3. **Combos y Paquetes Comerciales:** Conjuntos promocionales que integran múltiples productos y preparaciones bajo una sola unidad comercial.
El consolidado total de materias primas conforma la **Lista de Requisición de Bodega** para el evento.

### 5. Asignación de Brigada y Personal
- Todo evento cuenta con un **Encargado General** responsable del protocolo y la ejecución del servicio.
- Es posible asignar una **Brigada de Trabajadores** (cocineros, jefes de salón, garzones, bartenders) con roles operacionales específicos y notas de coordinación interna.

### 6. Stock Comprometido, Disponibilidad Real y Alertas de Quiebre
- **El Concepto de Stock Comprometido:** Los insumos requeridos por eventos agendados futuros no pueden considerarse disponibles para la venta regular en carta o buffet del día a día.
- **Ecuaciones de Existencia:**
  - $\text{Stock Físico Actual} = \text{Saldo contable en bodega (Kardex)}$.
  - $\text{Stock Comprometido} = \sum_{\text{eventos futuros agendados}} \text{Demanda BOM consolidada}$.
  - $\text{Stock Disponible Real} = \max(0, \text{Stock Físico Actual} - \text{Stock Comprometido})$.
- **Semáforo de Alertas de Abastecimiento:**
  - 🔴 **CRÍTICA (`CRITICAL`):** Evento agendado en las próximas 48 horas con insumos en déficit o stock insuficiente en bodega. Exige compra urgente.
  - 🟡 **ADVERTENCIA (`WARNING`):** Evento agendado dentro de los próximos 14 días con proyección de faltante respecto al stock actual. Permite planificar el abastecimiento con proveedores.
- **Descarga de Pedido Sugerido:** La vista de faltantes consolida la brecha neta ($\text{Faltante} = \text{Necesario} - \text{Disponible}$) y permite exportar directamente un archivo CSV/Excel listo para enviar a la central de compras.

### 7. Ejecución de Eventos y Consumo de Inventario
- La ejecución de un evento es un acto transaccional definitivo que rebaja de forma automática e inmutable las existencias físicas de las bodegas adscritas.
- Cada ingrediente se valora al Costo Promedio Ponderado (PPP) vigente al instante de la ejecución.
- El evento queda sellado con el indicador `ejecutado = True` y su fecha/hora exacta de cierre, impidiendo alteraciones posteriores en sus insumos o cantidades.

### 8. Política de Reversibilidad y Compensación
- Si un evento ejecutado debe anularse excepcionalmente (por ejemplo: evento suspendido de emergencia tras iniciar el montaje sin llegar a consumir las materias primas perecibles), el sistema **nunca borra ni altera** los asientos históricos del Kardex.
- En su lugar, genera una transacción de compensación formal que reingresa exactamente el mismo volumen de insumos al inventario al mismo costo PPP original, dejando trazabilidad auditable del motivo y del usuario autorizante.

### 9. Minutas de Producción y Actas Operativas
- El sistema genera minutas descargables compatibles con Excel que estructuran:
  1. Ficha general del evento (cliente, recinto, fecha, brigada).
  2. Plan de producción culinaria (platos, recetas y porciones).
  3. Despacho consolidado de bodegas (artículos, cantidades, bodegas de origen).
  4. Sección de firmas de recepción conforme para control de pérdidas.

---

## Escenarios Operativos de Negocio

### Escenario A: Reserva de Banquete de Graduación con Salón y Recetas
1. La coordinadora de eventos recibe una solicitud para la "Cena de Graduación Colegio San Andrés" el 15 de diciembre, de 19:00 a 02:00 hrs, para 180 personas.
2. Ingresa al modal "Nuevo Evento", selecciona el "Salón Roble" (capacidad 200 personas), define horario y brigada de 8 garzones y 1 encargado.
3. En la pestaña gastronómica agrega:
   - Receta "Medallón de Lomo al Vino Tinto": 180 porciones.
   - Receta "Postre Suspiro Limeño": 180 porciones.
   - Insumo directo: 45 botellas de Vino Reserva de la "Bodega Principal".
4. El sistema corrobora que el "Salón Roble" no tiene reservas que colisionen en ese horario y agenda el evento exitosamente en el calendario con color institucional burdeo.

### Escenario B: Detección Preventiva de Quiebre y Pedido Sugerido
1. El jefe de compras abre el módulo de Eventos al inicio de la semana y visualiza el banner superior de alerta ámbar: *"Se han detectado 3 insumos con quiebre proyectado para eventos de los próximos 7 días"*.
2. Abre el diálogo de "Resumen de Faltantes":
   - Lomo Liso: Necesario 45 kg, Disponible 15 kg $\to$ Faltante: 30 kg.
   - Vino Reserva: Necesario 45 botellas, Disponible 20 botellas $\to$ Faltante: 25 botellas.
3. Presiona *"Descargar Pedido Sugerido"*, obtiene la planilla Excel consolidada y emite la orden de compra al frigorífico y distribuidora con 5 días de anticipación, garantizando abastecimiento sin sorpresas.

### Escenario C: Ejecución del Servicio y Rebaje Inmutable en Bodega
1. Finalizado el banquete, el encargado de operaciones accede al evento en la pestaña "Próximos" y hace clic en la acción rápida *"Ejecutar Consumo"*.
2. El sistema despliega el resumen de insumos que serán rebajados de Kardex.
3. Al confirmar, el sistema realiza el asiento transaccional de consumo, rebajando los 45 kg de lomo y las botellas de vino a sus respectivos costos PPP.
4. El evento pasa automáticamente a la pestaña "Historial / Finalizados" con insignia verde esmeralda y el stock comprometido se libera.

### Escenario D: Reversión Controlada de Evento Ejecutado
1. Por una falla eléctrica en el sector, un banquete que había sido marcado como ejecutado al inicio de la jornada debió ser reubicado en otra sucursal sin utilizar las botellas de licor de bodega.
2. Con permiso de supervisor, el administrador pulsa *"Revertir Consumo"*, declara el motivo: *"Corte de suministro eléctrico comunal - Insumos reingresados a bodega"*.
3. El sistema asienta un movimiento compensatorio en Kardex y devuelve el evento al estado cancelado, preservando intacta la auditoría contable.

---

## Documento Técnico Par

Para la especificación técnica de ingeniería, modelos de datos PostgreSQL, contratos DDD, esquemas Pydantic, endpoints REST RFC 7807, WebSockets y suites de pruebas automatizadas, consulte:  
$\to$ [`specs/engineering-code/events.code.spec.md`](../engineering-code/events.code.spec.md).
