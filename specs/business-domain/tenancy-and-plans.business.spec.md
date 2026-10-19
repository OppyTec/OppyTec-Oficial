# Empresas, Restaurantes y Planes

> Audiencia: clientes, producto y soporte. Sin detalles técnicos.

## Resumen
Cada cliente es una empresa (Holding) con una o más entidades legales; cada entidad legal opera exactamente un restaurante aislado. El plan contratado define qué módulos y cuántos usuarios puede usar.

## Reglas de negocio
- Una entidad legal tiene un único restaurante y un restaurante pertenece a una única entidad legal.
- Los datos de un restaurante jamás son visibles para otro restaurante.
- El plan contratado fija los módulos habilitados y el cupo de usuarios.
- Solo el equipo de OppyTec crea empresas y asigna planes.

## Escenarios
- Una cadena con 3 razones sociales recibe 3 restaurantes separados bajo una misma empresa.
- Si el cliente sube de plan, los módulos nuevos aparecen sin perder información.

## Documento técnico par
Equivalente para desarrolladores: `tenancy-and-plans.code.spec.md`.
