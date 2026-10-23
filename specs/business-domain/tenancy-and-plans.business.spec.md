# Empresas, Restaurantes, Planes y Cuotas Paramétricas

> Audiencia: clientes, administradores de negocio, producto y soporte. Sin detalles técnicos internos.

## Resumen
Cada cliente es una empresa (Holding) que agrupa una o más razones sociales (Entidades Legales). Cada entidad legal opera exactamente un restaurante o local gastronómico completamente aislado de los demás. El plan comercial contratado define los módulos operativos habilitados y fija 6 cuotas de capacidad paramétricas que pueden ser ampliadas de forma personalizada mediante excepciones por empresa o por local.

## Reglas de Negocio

### 1. Jerarquía Corporativa y Aislamiento Estricto
- **Empresa (Holding):** Agrupa los locales de una misma marca o consorcio gastronómico.
- **Razón Social (Entidad Legal):** Cada entidad legal opera exactamente un restaurante y un restaurante pertenece a una única razón social (relación uno a uno estricta).
- **Aislamiento Total:** La información de inventario, costos, recetas, compras y ventas de un restaurante jamás es visible para otro restaurante, garantizando estricta privacidad comercial entre sucursales y franquicias.
- **Acceso del Propietario:** El dueño o director de la empresa puede consolidar la visión de todos sus locales desde un selector unificado sin mezclar datos operacionales.

### 2. El Plan Básico ("Núcleo Base de Control de Inventario")
El Plan Básico de OppyTec está diseñado para locales que buscan ordenar y controlar sus existencias de insumos y mermas de forma ágil y rigurosa. Incluye exactamente los siguientes 10 módulos y funciones operativas:
1. **Inicio:** Panel adaptativo con métricas esenciales de operación y accesos rápidos.
2. **Registro de Consumo:** Registro táctil directo de insumos utilizados en cocina o barra sin necesidad de punto de venta complejo.
3. **Registro de Stock:** Ingreso directo de existencias y recepciones rápidas a bodega.
4. **Gestión de Productos:** Catálogo de insumos y artículos con conversión en 3 niveles de unidades (compra, almacenamiento y consumo).
5. **Gestión de Mermas:** Registro estricto de pérdidas por vencimiento, rotura o descarte con justificación obligatoria.
6. **Recuento Unificado:** Conteo físico de existencias periódicas e historial de recuentos comparativos.
7. **Notificaciones:** Bandeja centralizada de avisos operacionales para el equipo de turno.
8. **Alertas Preventivas:** Notificaciones automáticas de stock mínimo crítico, vencimientos próximos y anomalías de consumo.
9. **Historial de Movimientos:** Libro mayor de trazabilidad inmutable de todas las entradas y salidas de bodega.
10. **Usuarios y Roles:** Control de acceso, asignación de cargos operativos y delegación de tareas.

*Nota de exclusión del Plan Básico:* Los módulos avanzados de escandallos y recetas complejas, combos, buffet inteligente y punto de venta comercial quedan reservados para planes superiores (como Esencial o Corporativo) o habilitación personalizada.

### 3. Las 6 Cuotas Paramétricas de Capacidad
Cada plan comercial establece límites numéricos claros para 6 recursos fundamentales:
1. **Usuarios Activos:** Cantidad máxima de trabajadores que pueden tener cuenta habilitada simultáneamente.
2. **Productos e Insumos:** Catálogo máximo de artículos e ingredientes dados de alta en el sistema.
3. **Proveedores:** Directorio máximo de proveedores comerciales habilitados.
4. **Recetas y Escandallos:** Fichas técnicas de platos y preparaciones (fijado en 0 para el Plan Básico).
5. **Combos y Promociones:** Agrupaciones y menús comerciales (fijado en 0 para el Plan Básico).
6. **Almacenamiento Multimedia:** Espacio total en megabytes asignado para fotografías de insumos, comprobantes y respaldos.

### 4. Jerarquía de Excepciones (Overrides) y Flexibilidad Comercial
- Para responder a necesidades puntuales de un cliente sin obligarlo a cambiar de plan completo, OppyTec permite asignar cuotas especiales adicionales:
  - **Prioridad 1:** Límite personalizado por Restaurante (Sucursal).
  - **Prioridad 2:** Límite personalizado por Empresa (Holding).
  - **Prioridad 3:** Límite base del Plan contratado.
- Si un local cuenta con una excepción personalizada de productos o proveedores, dicha cuota prevalece sobre la cuota general del plan.

### 5. Regla Universal de Liberación por Archivo (Baja Lógica)
- Cuando un trabajador deja la empresa o un producto queda descontinuado y se da de baja, el elemento pasa al archivo histórico.
- **Efecto Inmediato:** El cupo activo que ocupaba queda libre de inmediato para ingresar un nuevo trabajador o insumo.
- **Trazabilidad Garantizada:** La baja jamás borra el historial de auditoría ni los registros pasados en el libro mayor de bodega.

### 6. Semáforo de Salud y Prevención de Bloqueos
El sistema acompaña al usuario y a los administradores con un indicador visual preventivo de 4 estados:
- 🟢 **Saludable (Normal):** Uso inferior al 80% de la capacidad disponible.
- 🟡 **Preventivo (Advertencia):** Uso entre 80% y 94% de la capacidad. Se sugiere revisar artículos obsoletos o planificar ampliación.
- 🔴 **Crítico:** Uso entre 95% y 99% de la capacidad. Alerta prioritaria de cupo casi agotado.
- ⛔ **Cupo Agotado o No Incluido:** Uso al 100% o capacidad fijada en 0 por el plan. Se bloquea la creación de nuevos elementos hasta archivar existencias o ampliar la cuota, informando la causa clara al usuario.

### 7. Asistencia y Soporte con Acompañamiento ("Entrar como Local")
- Los administradores de soporte global de OppyTec disponen de una función de impersonación segura para ingresar temporalmente a la vista de un local específico y prestar asistencia técnica directa ante configuraciones de inventario, con registro estricto en la bitácora de auditoría.

### 8. Panel de Administración de Plataforma y sus 4 Vistas Operativas
Para la gestión centralizada de clientes y recursos de la nube SaaS, los administradores de plataforma cuentan con 4 vistas operativas gobernadas bajo el principio de mínimo privilegio:
1. **Gestión de Empresas Matrices (Holdings):** Visión global de marcas gastronómicas, vinculación al plan comercial base y configuración de excepciones de capacidad corporativas.
2. **Gestión de Sociedades Tributarias (Entidades Legales):** Registro de razones sociales e identificación fiscal (RUT verificado bajo norma oficial), manteniendo relación uno a uno estricta con cada restaurante.
3. **Aprovisionamiento de Restaurantes y Sucursales (Locales):** Creación de sucursales aisladas, activación guiada de módulos mediante el árbol oficial de funciones (con selector directo de los 10 módulos del Plan Básico), selección de moneda principal y cuotas personalizadas.
4. **Directorio de Usuarios Clientes:** Supervisión de cuentas operativas, validación estricta de cupos de personal, botón de archivo (baja lógica) con liberación inmediata de vacantes y botón de asistencia técnica ("Entrar como Local").
- **Protección de Acceso por Roles:** Las acciones de alta, edición, baja y soporte están protegidas contra accesos no autorizados; el personal sin facultades de administración global no visualiza botones ni controles que no le correspondan.
- **Experiencia Multilingüe Completa:** Todas las tablas, etiquetas de estado, formularios y diálogos de confirmación están adaptados al idioma elegido (español o inglés) sin textos mixtos ni términos sin traducir.

## Escenarios de Negocio

### Escenario 1: Cadena gastronómica con sucursal de alta rotación
Una cadena opera bajo un mismo Holding con 4 locales. Uno de los locales maneja una carta más extensa. El equipo de OppyTec le otorga una excepción de 800 productos a ese local en particular, mientras los otros 3 locales continúan con el límite estándar de 500 productos de su plan, sin fricción ni necesidad de migraciones complejas.

### Escenario 2: Restaurante en Plan Básico que alcanza su cupo de personal
Un local en Plan Básico con cupo para 5 usuarios activos despide a un ayudante de cocina e incorpora a uno nuevo. El administrador del local archiva al trabajador saliente; en ese mismo instante el semáforo de usuarios vuelve a mostrar 4 de 5 activos, permitiendo registrar al nuevo colaborador inmediatamente sin errores de sobrecupo.

### Escenario 3: Intento de alta de recetas en Plan Básico
Un local con Plan Básico intenta acceder a la creación de escandallos y fichas técnicas. Dado que la cuota de recetas de su plan es 0 y el módulo no forma parte de su núcleo base, el sistema le indica de forma transparente que su plan actual está enfocado en control de stock y mermas, invitándolo a consultar por una ampliación de plan o un add-on personalizado.

## Documento Técnico Par
Especificación detallada de arquitectura, modelos y servicios para el equipo de ingeniería: `tenancy-and-plans.code.spec.md`.
