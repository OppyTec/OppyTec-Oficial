# Permisos, Control Granular de Módulos, Cupos de Usuarios y Auditoría

> Audiencia: clientes, administradores de negocio, producto y soporte. Sin detalles técnicos internos.

## Resumen
Cada integrante del equipo gastronómico ve y opera exactamente lo que su cargo permite y lo que el plan comercial contratado habilita. El sistema incorpora control granular a nivel de módulo y subfunción, jerarquía estricta de rangos para evitar abusos internos, administración de cupos activos con liberación inmediata al dar de baja personal, y un libro doble de auditoría inmutable.

## Reglas de Negocio

### 1. Control de Acceso por Plan y por Rol
- **Filtro de Plan:** Una persona solo puede acceder a una función si el plan de su restaurante la tiene habilitada. El sistema permite habilitar submódulos puntuales (como registro de consumo táctil) mientras mantiene inactivos módulos que no corresponden al plan contratado.
- **Permiso Efectivo:** Para ejecutar cualquier acción se requiere que el plan la contemple, que el rol del usuario (o un permiso temporal asignado) la autorice, y que no exista una restricción explícita.
- **Principio de Mínimo Privilegio:** Cada colaborador tiene acceso acotado a sus tareas (ej. cajeros solo registran cobros y consumos, cocineros registran mermas e inventario, jefes de local administran pedidos).

### 2. Jerarquía de Cargos Inviolable
- Cada cargo tiene un nivel jerárquico establecido: Dueño o Propietario en la cima, seguido de Administradores de Local, Supervisores o Contadores, y Personal Operativo.
- **Ley de Protección de Rangos:** Ningún usuario puede crear, modificar, suspender ni dar de baja a otro usuario que tenga un rango igual o superior al suyo.
- Los dueños de empresa siempre conservan el control superior de sus locales.

### 3. Cupos de Usuarios y Liberación Inmediata por Baja Lógica
- Cada empresa o local cuenta con una cantidad máxima de usuarios activos según su plan o excepción comercial.
- **Baja y Liberación de Cupo:** Cuando un trabajador deja el local y es dado de baja, pasa al archivo histórico. En ese mismo instante el cupo activo se desocupa y queda disponible para registrar a un reemplazo.
- **Cierre Instantáneo de Acceso:** La baja de un trabajador revoca de inmediato sus credenciales activas para proteger las instalaciones del local.

### 4. Permisos Temporales para Situaciones Extraordinarias
- Se pueden otorgar autorizaciones especiales con límite de tiempo para que un trabajador cubra un turno extraordinario o ejecute una tarea específica sin necesidad de ascenderlo permanentemente de cargo.
- Al vencer el plazo, el permiso expira de forma automática.

### 5. Doble Registro de Auditoría Inmutable
- Cada operación relevante (creación de insumos, ajustes de bodega, mermas, modificaciones de roles o bajas de personal) queda asentada en un registro permanente que responde con precisión a tres preguntas: ¿Quién lo hizo?, ¿En qué momento exacto ocurrió? y ¿Qué valores cambiaron antes y después?

### 6. Blindaje de Acciones de Administración Global (Panel de Plataforma)
- Las operaciones sobre la infraestructura comercial (creación y modificación de holdings, entidades legales, aprovisionamiento de restaurantes, archivo de usuarios clientes y asistencia técnica acompañada) están restringidas exclusivamente al personal con facultades de administración de plataforma.
- **Protección Visual y Operativa:** Si un colaborador de local o un usuario sin el permiso requerido ingresa al panel, las opciones y botones de modificación no se despliegan en pantalla, garantizando que nadie pueda alterar recursos fuera de su ámbito de atribuciones.

## Escenarios de Negocio

### Escenario 1: Plan Básico con acceso exclusivo a registro de consumo
Un local gastronómico opera con Plan Básico. El rol de cocinero tiene asignado registrar consumos de cocina y preparar buffet. Dado que el Plan Básico solo incluye el registro de consumo táctil de insumos y no incluye buffet comercial ni punto de venta, el sistema permite fluidamente el consumo táctil y mantiene inactivo el acceso a buffet, protegiendo la coherencia comercial del plan.

### Escenario 2: Intento de modificación jerárquica no permitida
Un administrador de turno intenta cambiar la contraseña o desactivar la cuenta del propietario de la empresa. El sistema rechaza la acción de forma automática informando que no es posible operar sobre un cargo de mayor jerarquía.

### Escenario 3: Rotación de personal en fin de semana
Un restaurante con cupo completo de 5 trabajadores debe incorporar con urgencia a un reemplazo el sábado en la noche. El administrador da de baja al trabajador ausente y de inmediato el sistema le permite dar de alta al nuevo personal de turno sin tener que solicitar ampliaciones extraordinarias.

## Documento Técnico Par
Especificación detallada de evaluación booleana, rangos, esquemas y pruebas para el equipo de ingeniería: `rbac-quotas-and-audit.code.spec.md`.
