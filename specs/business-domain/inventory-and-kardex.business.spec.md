# Inventario, Kardex y Trazabilidad Histórica

> Audiencia: clientes, administradores de negocio, producto y soporte. Sin detalles técnicos internos.

## Resumen
El inventario muestra las existencias físicas y disponibles de cada ingrediente e insumo del local gastronómico u hotelero. El Kardex constituye el libro mayor inmutable de la empresa, registrando cada entrada, salida, merma, compra, traslado y ajuste con su costo promedio ponderado exacto. El módulo de Historial de Kardex proporciona una consola centralizada de auditoría visual con trazabilidad multidimensional, filtros de búsqueda predictiva, comparativa de saldos antes y después de cada recuento, anonimización para protección de privacidad y exportación certificada a hojas de cálculo.

## Reglas de Negocio

### 1. Invariantes del Libro Mayor y Saldos
- Cada movimiento queda asentado en estricto orden cronológico en un registro histórico permanente que no se puede borrar ni alterar.
- El saldo disponible y el costo promedio ponderado se recalculan con cada transacción de forma aritmética exacta.
- No se permite que las existencias queden en valores negativos ante movimientos de consumo, venta, salida o traslado.
- Los saldos se actualizan en vivo en todas las pantallas operativas mediante notificación inmediata sin recargar la página.
- Los traslados entre bodegas descuentan existencias en el origen y aumentan en el destino de manera simultánea, atómica e indivisible.
- Las existencias bajo mínimo y los lotes caducados o próximos a vencer activan alertas inmediatas en tiempo real (especificación dedicada: `inventory-alerts.business.spec.md`).

### 2. Recuentos Físicos Ciegos y Conciliaciones
- En la toma física ciega, el personal registra las existencias reales encontradas en estanterías sin visualizar el stock teórico del sistema para evitar sesgos y alteraciones operativas.
- Toda diferencia entre existencias físicas y teóricas genera un acta formal de discrepancia valorizada al costo promedio ponderado, la cual requiere revisión y aprobación administrativa antes de aplicar ajustes al inventario.

### 3. Consola de Historial y Auditoría de Movimientos
- **Acceso Centralizado:** La pantalla de Historial reúne todas las transacciones históricas de almacenes y cocinas en una tabla comprensiva y paginada.
- **Filtros Multi-Criterio de Alta Precisión:**
  - **Filtro por Bodega:** Permite aislar los movimientos de un almacén o área específica (Bodega Central, Cocina, Barra, Pastelería) o consultar la totalidad del negocio.
  - **Filtro por Producto:** Búsqueda y selección de insumos específicos con persistencia de enlace de navegación para auditorías compartidas.
  - **Filtro por Tipo de Movimiento:** Catálogo de eventos operativos que incluye conteos, consumos de recetas, mermas por descarte, compras a proveedores, ventas, ajustes positivos y negativos, transferencias inter-bodega, reversiones y ajustes de auditoría.
  - **Rango de Fechas Accesible:** Selectores Desde y Hasta con formato de fecha latinoamericano y validación de períodos.
  - **Búsqueda Predictiva de Personal:** Permite localizar al instante las operaciones registradas por un colaborador ingresando parte de su nombre, con opción de borrado rápido.
  - **Limpieza Instantánea de Filtros:** Un botón dedicado restablece todos los criterios de búsqueda al estado inicial con un solo toque.

### 4. Trazabilidad Visual y Semántica de la Información
- **Semáforo Cromático por Naturaleza de Operación:**
  - Verde: Entradas de mercadería, compras a proveedores y ajustes favorables de inventario.
  - Rojo: Consumos de producción, mermas por descarte, salidas operativas y ajustes desfavorables.
  - Azul / Cian: Traslados de insumos entre bodegas.
  - Púrpura / Índigo: Recuentos físicos periódicos y ajustes de auditoría.
  - Ámbar: Operaciones de reversión y restauración de movimientos anteriores.
- **Dirección de Traslados:** Los movimientos entre almacenes identifican visualmente si el registro corresponde a la salida desde el almacén emisor (flecha saliente) o a la recepción en el almacén receptor (flecha entrante).
- **Comparativa de Existencias (Antes y Después):** En los movimientos derivados de recuentos y cuadraturas físicas, la tabla expone la transición exacta entre el saldo previo teórico y el saldo auditado final (por ejemplo: "10.000 kg → 8.500 kg"), facilitando la detección de mermas no declaradas.
- **Estampado Temporal Local:** Todas las marcas temporales se presentan de forma clara en la zona horaria del local (fecha y hora exacta en formato legible).

### 5. Privacidad y Gobernanza de Acceso
- **Anonimización por Perfil:** Para proteger la privacidad del personal base de operaciones, los usuarios con roles operativos sin permisos de auditoría gerencial visualizan la autoría bajo la etiqueta genérica de "Operador Autorizado", mientras que los administradores y auditores tienen visibilidad del nombre completo del responsable.
- **Protección de Purga:** La eliminación o depuración de registros históricos está bloqueada para todos los roles ordinarios y queda estrictamente reservada para el Propietario de la cuenta empresarial, emitiendo una constancia indeleble de auditoría de seguridad.

### 6. Exportación Segura de Informes
- El sistema permite generar y descargar de forma inmediata informes en formato de hoja de cálculo CSV con los nueve campos canónicos de auditoría: fecha y hora, bodega, producto, tipo de movimiento, cantidad, unidad de medida, usuario responsable, motivo o notas y saldo resultante.
- Los archivos exportados incorporan codificación universal para apertura transparente en cualquier programa de planillas de cálculo e incluyen mecanismos de neutralización contra inyección de fórmulas no autorizadas.

## Escenarios de Uso
- **Auditoría de Mermas de Fin de Semana:** El jefe de operaciones filtra los movimientos de tipo "Merma" ocurridos entre el viernes y el domingo en la "Bodega Central"; identifica tres descartes por vencimiento y revisa las notas de justificación dejadas por el encargado de turno.
- **Revisión de Cuadratura de Inventario:** El contralor selecciona un recuento reciente de camarones y verifica en la columna de cantidad la transición visual de 25 kg teóricos a 22 kg reales tras la aprobación del acta de discrepancia.
- **Conciliación de Traslados entre Cocina y Bar:** El supervisor busca el insumo "Crema de Leche" y comprueba que la salida desde Bodega Central y la entrada a Pastelería poseen el mismo identificador de traslado y fueron registradas de forma simultánea.
- **Exportación de Libro Diario para Contabilidad:** La gerencia aplica un filtro por el mes anterior y descarga el informe CSV para cruzar los consumos y compras contra el sistema de gestión financiera del local.

## Documento técnico par
Equivalente para desarrolladores: `inventory-and-kardex.code.spec.md`.
