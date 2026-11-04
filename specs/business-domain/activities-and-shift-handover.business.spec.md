# Panel de Actividades, Bitácora Operativa, Tareas y Traspaso de Turno

> Audiencia: Dueños de restaurantes, chefs ejecutivos, administradores gastronómicos, jefes de sala, líderes de brigada y asistente inteligente OppyFy (Capa 3A). Documento conceptual y de negocio sin detalles técnicos de persistencia ni código fuente.

---

## 1. Resumen Ejecutivo y Visión Operacional

En la industria gastronómica y de hospitalidad, la continuidad operacional entre turnos (apertura, turno intermedio y cierre) es uno de los puntos más críticos y propensos a errores. Tradicionalmente, la comunicación de incidencias se ha realizado a través de cuadernos de bitácora en papel que se manchan o extravían, chats informales de mensajería instantánea donde la información sensible queda dispersa y sin trazabilidad, o instrucciones verbales que se olvidan cuando una brigada entrega el servicio a la siguiente.

Las consecuencias de una entrega de turno deficiente son cuantiosas:
- Máquinas y cámaras de refrigeración apagadas o con fallas no reportadas a tiempo.
- Quiebres de stock descubiertos en pleno rush de almuerzo o cena porque el turno saliente no informó el agotamiento de un insumo clave o la merma de una preparación base.
- Rutinas higiénicas de apertura y cierre inconclusas que arriesgan multas sanitarias y degradan la calidad del producto.
- Horarios desactualizados, infracciones a las normativas de jornada laboral (como el descanso obligatorio entre turnos o el exceso de la jornada semanal legal) y ausentismo no coordinado.

El **Panel de Actividades de OppyTec v2.0** resuelve estos dolores mediante una tríada operacional integrada y unificada:
1. **Muro y Bitácora de Novedades (Notas de Turno):** Canal formal y centralizado que separa de forma hermética las comunicaciones de equipo (con confirmación de lectura y mención de cargos) de los apuntes privados del colaborador.
2. **Tablero y Listas de Control (Tareas Operativas):** Gestión de rutinas de apertura y cierre con validación inmutable que impide dejar tareas incompletas sin una justificación registrada.
3. **Cuadrante Semanal de Turnos (Horarios y Asignación):** Planificación visual de dotación con alertas preventivas de descanso laboral y herramientas de clonación ágil de semanas tipo.
4. **Sinergia Inteligente de Cierre de Turno (Minuta OppyFy):** Consolidación automatizada por inteligencia artificial que sintetiza los cuatro aspectos vitales de la jornada (incidentes, producción/stock, tareas inconclusas y dotación efectiva), entregando un reporte ejecutivo para el Chef Ejecutivo o Administrador en segundos.

---

## 2. Dolor del Negocio Gastronómico y Casos de Uso Críticos

### A. El "Teléfono Descompuesto" en el Cambio de Guardia
- **Dolor:** El turno noche finalizó a las 02:00 AM tras una jornada exhaustiva. La cortadora de fiambres sufrió un desperfecto eléctrico y la merluza fresca del día se agotó. El equipo diurno que ingresa a las 08:00 AM se entera del incidente cuando un cliente pide el plato en el almuerzo.
- **Solución OppyTec:** El encargado nocturno publica una nota de equipo categorizada como *Incidente* con mención al Chef y al Responsable de Mantenimiento. Al entrar, el equipo matutino visualiza la alerta destacada y debe marcarla como leída, garantizando que nadie inicie el turno a ciegas.

### B. Rutinas Incompletas sin Responsable Claro
- **Dolor:** En las inspecciones matutinas, la trampa de grasa sigue sucia o el registro de temperaturas de cámaras de frío está en blanco. Al consultar a los colaboradores, todos asumen que "le tocaba a otro".
- **Solución OppyTec:** Las rutinas de apertura y cierre se generan desde plantillas estandarizadas. Si un colaborador marca una tarea como incompleta, el sistema le exige de forma obligatoria detallar el motivo (por ejemplo: "Falta insumo desengrasante en bodega central"). Queda constancia transparente de quién reportó y por qué.

### C. Sobrecarga Laboral y Conflictos de Turnos
- **Dolor:** Horarios confeccionados en planillas de cálculo donde no se detectan turnos dobles encubiertos, asignando a un garzón el cierre de medianoche y la apertura matutina del día siguiente, vulnerando el descanso legal de 12 horas consecutivas o excediendo el límite legal de 40 horas semanales.
- **Solución OppyTec:** El planificador de horarios evalúa de forma preventiva los descansos mínimos y la carga horaria acumulada de cada miembro de la brigada, alertando al administrador antes de publicar o modificar los turnos.

---

## 3. Reglas de Negocio Fundamentales

### Regla 1: Bipolaridad de la Bitácora (Notas de Equipo vs. Notas Personales)
- **Notas de Equipo:** Son públicas para todos los colaboradores de la sucursal o del área operativa seleccionada. Permiten adjuntar fotografías de evidencia, etiquetar insumos y recetas, y mencionar a colaboradores específicos.
  - **Confirmación de Lectura Idempotente:** Cada colaborador puede pulsar "Marcar como leído". El sistema contabiliza de forma transparente cuántos y cuáles miembros de la brigada han tomado conocimiento de la novedad.
- **Notas Personales:** Son privadas y confidenciales para el colaborador que las registra. Ningún compañero ni superior puede acceder a los apuntes personales de otro miembro de la brigada.

### Regla 2: Categorización Operativa de Novedades
Toda nota de equipo debe pertenecer a una categoría operacional estandarizada para facilitar su filtrado y priorización:
- 🔴 **Incidente:** Desperfectos mecánicos, cortes de suministro, quejas graves de clientes, accidentes menores.
- 🟡 **Stock:** Alertas de existencias críticas, insumos no conformes o entregas pendientes de proveedores.
- 🔵 **Producción:** Lotes de mise en place elaborados, cambios en el menú del día o mermas excepcionales.
- 🟢 **Servicio:** Reservas especiales, requerimientos VIP, notas de montaje para el personal de salón.
- ⚪ **General:** Comunicados organizacionales y felicitaciones al equipo.

### Regla 3: Tareas Operativas y Regla Inviolable de Justificación de Tareas Incompletas
- Las tareas transitan por un ciclo de vida con cuatro estados: *Pendiente*, *En Progreso*, *Completada* e *Incompleta*.
- Cuentan con semáforo de urgencia de tres niveles: *Alta* (rojo), *Media* (ámbar) y *Baja* (esmeralda).
- **Invariante Inviolable de Incompletitud:** Bajo ninguna circunstancia se permite marcar una tarea como *Incompleta* sin registrar un texto explicativo fundado. El sistema rechaza cualquier intento de guardar una tarea incompleta sin justificación, asegurando que la administración conozca las causas objetivas de los descalces operacionales.
- **Plantillas de Rutina:** Los jefes de cocina y administradores pueden definir plantillas maestras (por ejemplo: "Apertura Cocina Caliente", "Cierre Salón y Cajas", "Desinfección Semanal de Campanas") y aplicarlas en lote para una fecha específica con un solo clic.

### Regla 4: Cuadrante de Horarios y Guardián Laboral Preventivo
- **Vista Cuadrante:** Permite visualizar los siete días de la semana (lunes a domingo) contra la dotación activa de personal, organizados por su cargo gastronómico.
- **Clonación Semanal:** Capacidad de clonar íntegramente la grilla de turnos de una semana previa hacia una semana destino, reduciendo el tiempo de planificación administrativa a segundos.
- **Guardián de Legislación Laboral (Legal Guard):**
  - **Descanso Mínimo Interjornada:** El sistema comprueba que medien al menos 12 horas continuas de descanso entre el fin del turno de una jornada y el inicio del turno siguiente del mismo colaborador. Si no se cumple, se genera una advertencia crítica.
  - **Jornada Semanal Legal:** El sistema acumula las horas efectivas programadas para el colaborador en la semana calendario y emite una alerta si la suma proyectada sobrepasa el marco legal vigente (40 horas semanales).

### Regla 5: Minuta Ejecutiva y Síntesis OppyFy de Cierre de Turno
Al finalizar la jornada o el turno de servicio, el sistema ofrece una herramienta de síntesis inteligente asistida por OppyFy:
- Consolida las notas registradas durante el turno, las tareas resueltas y las tareas que quedaron incompletas con sus motivos.
- Resume la dotación efectiva de colaboradores presentes.
- Estructura un informe en cuatro puntos clave:
  1. **Incidentes Críticos:** Qué falló o qué contingencia requirió atención.
  2. **Producción y Almacén:** Qué insumos o elaboraciones requieren reposición urgente.
  3. **Tareas Incompletas y Justificaciones:** Qué quedó pendiente para el siguiente turno y por qué.
  4. **Dotación y Horarios:** Resumen de personal asignado y cobertura de áreas.
- Permite al encargado copiar la minuta formateada para compartirla por canales gerenciales o guardarla directamente como una nota destacada en la bitácora de equipo.

---

## 4. Roles de Brigada y Matriz de Acceso al Negocio

| Rol Gastronómico | Notas de Turno | Tareas Operativas | Cuadrante de Horarios | Minuta OppyFy |
| :--- | :--- | :--- | :--- | :--- |
| **Chef Ejecutivo / Administrador** | Crea, edita, elimina notas; revisa lecturas de la brigada. | Define plantillas maestras, asigna tareas y supervisa checklists. | Planifica turnos, clona semanas y supervisa alertas laborales. | Genera, revisa y aprueba minutas de cierre de turno. |
| **Jefe de Partida / Sous Chef** | Reporta incidentes de cocina, avances de producción y stock. | Ejecuta tareas de mise en place; justifica tareas incompletas. | Visualiza cuadrante de cocina y turnos de su brigada. | Consulta resumen de producción e incidentes de su área. |
| **Cocinero / Steward** | Consulta bitácora de cocina; marca novedades como leídas. | Marca tareas asignadas como completadas o incompletas con nota. | Consulta sus propios horarios y descansos asignados. | N/A (Consumo pasivo a través de instrucciones de su jefe). |
| **Jefe de Salón / Maître** | Reporta novedades de salón, mesas VIP y roturas de vajilla. | Asigna checklists de apertura de salón y montaje de mesas. | Supervisa horarios de garzones, barman y anfitriones. | Revisa minuta de servicio para traspaso a turno noche. |
| **Garzón / Bartender / Cajero** | Consulta notas de servicio; crea notas personales privadas. | Cumple checklist de apertura de estación y cierre de caja. | Consulta su horario personal de trabajo en vista móvil. | N/A. |

---

## 5. Valor Comercial y Operacional

1. **Eliminación del Error Humano en Traspasos:** Garantiza que el 100% de los incidentes y quiebres de insumos queden documentados formalmente con fecha, hora, autor y confirmación de lectura.
2. **Cero Ambigüedad en el Cumplimiento:** La exigencia ineludible de justificar tareas incompletas destapa cuellos de botella reales en la operación (falta de herramientas, proveedores retrasados o falta de dotación) en lugar de ocultar la inejecución.
3. **Cumplimiento Normativo y Clima Laboral:** Las alertas preventivas de descanso insuficiente y jornada semanal protegen al negocio de multas de la autoridad laboral y cuidan la salud del personal de cocina y salón.
4. **Agilidad en la Gestión Diaria:** Reducción de más de un 80% en el tiempo dedicado a redactar informes de cambio de turno gracias a la consolidación inteligente de OppyFy.
