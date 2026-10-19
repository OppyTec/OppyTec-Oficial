# Permisos, Cupos de Usuarios y Auditoría

> Audiencia: clientes, producto y soporte. Sin detalles técnicos.

## Resumen
Cada persona ve y hace solo lo que su rol permite y su plan incluye. Los usuarios tienen jerarquía: nadie puede modificar a un superior. Todo cambio queda registrado en dos libros de auditoría.

## Reglas de negocio
- Un permiso efectivo existe solo si el plan lo incluye y el rol (o un permiso temporal) lo otorga y no hay una negación explícita.
- Nadie puede crear, editar ni eliminar a alguien de rango igual o superior.
- El cupo de usuarios activos del plan se respeta; los usuarios eliminados liberan cupo.
- Se puede suspender el acceso de un cliente de inmediato.
- Cada acción sensible queda registrada con quién, cuándo y qué cambió.

## Escenarios
- Un administrador de restaurante intenta editar al dueño y el sistema lo rechaza.
- El cliente alcanza su cupo y debe dar de baja a alguien o subir de plan.

## Documento técnico par
Equivalente para desarrolladores: `rbac-quotas-and-audit.code.spec.md`.
