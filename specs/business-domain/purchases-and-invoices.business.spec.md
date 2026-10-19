# Compras, Proveedores y Facturas

> Audiencia: clientes, producto y soporte. Sin detalles técnicos.

## Resumen
Gestión de proveedores, órdenes de compra y facturas, que alimentan el inventario y los costos.

## Reglas de negocio
- Una factura recibida genera entradas de inventario.
- El costo de compra actualiza el costo del ingrediente.
- Se pueden registrar facturas en distintas monedas.

## Escenarios
- Se recibe una factura en dólares y se convierte a pesos con el tipo de cambio del día.
- Se sube la foto de una factura y el asistente propone las líneas.

## Documento técnico par
Equivalente para desarrolladores: `purchases-and-invoices.code.spec.md`.
