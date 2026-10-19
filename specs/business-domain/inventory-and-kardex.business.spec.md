# Inventario y Kardex

> Audiencia: clientes, producto y soporte. Sin detalles técnicos.

## Resumen
El inventario muestra cuánto hay de cada ingrediente y el Kardex deja la historia completa de entradas y salidas con su costo.

## Reglas de negocio
- Cada movimiento queda registrado en orden cronológico y no se puede borrar.
- El saldo y el costo promedio se recalculan con cada movimiento.
- No se permite dejar el stock en negativo salvo configuración explícita.
- Los saldos se actualizan en vivo en todas las pantallas.

## Escenarios
- Dos cocineros descuentan el mismo ingrediente a la vez y el saldo final es correcto.
- Se consulta el historial de un ingrediente para explicar una diferencia.

## Documento técnico par
Equivalente para desarrolladores: `inventory-and-kardex.code.spec.md`.
