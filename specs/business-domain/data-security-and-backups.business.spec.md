# Seguridad de Datos y Respaldos

> Audiencia: clientes, producto y soporte. Sin detalles técnicos.

## Resumen
Los datos del cliente se protegen con cifrado y copias de respaldo en cuatro lugares, pudiendo restaurar un solo restaurante.

## Reglas de negocio
- Las copias van cifradas y en cuatro ubicaciones.
- Se puede restaurar un único restaurante sin afectar a los demás.
- Las contraseñas y llaves nunca se guardan en texto visible.

## Escenarios
- Un cliente borra datos por error y se recupera solo su restaurante.
- Se verifica que la última copia está íntegra.

## Documento técnico par
Equivalente para desarrolladores: `data-security-and-backups.code.spec.md`.
