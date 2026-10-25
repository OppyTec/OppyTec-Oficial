# Inventario y Kardex

> Audiencia: clientes, producto y soporte. Sin detalles técnicos.

## Resumen
El inventario muestra cuánto hay de cada ingrediente y el Kardex deja la historia completa de entradas y salidas con su costo promedio ponderado. Incluye terminal de stock con semáforos de reposición, recuentos físicos ciegos y actas de conciliación de auditoría.

## Reglas de negocio
- Cada movimiento queda registrado en orden cronológico y no se puede borrar ni alterar.
- El saldo y el costo promedio ponderado se recalculan con cada movimiento de forma exacta.
- No se permite dejar el stock en negativo en movimientos de salida o consumo.
- Los saldos se actualizan en vivo en todas las pantallas operativas mediante notificación inmediata.
- En la toma física ciega, el personal registra existencias reales sin ver el stock del sistema para evitar sesgos.
- Toda diferencia entre existencias físicas y teóricas genera un acta de discrepancia que requiere aprobación antes de ajustar saldos.
- Los traslados entre bodegas descuentan en origen y aumentan en destino de forma simultánea e indivisible.

## Escenarios
- Dos cocineros descuentan el mismo ingrediente a la vez y el saldo final es correcto.
- Se realiza un recuento de fin de mes a ciegas, se detecta un faltante valorizado y el administrador lo aprueba para ajustar el inventario.
- Se traslada mercadería entre dos bodegas y ambas reflejan el cambio en el mismo instante.

## Documento técnico par
Equivalente para desarrolladores: `inventory-and-kardex.code.spec.md`.
