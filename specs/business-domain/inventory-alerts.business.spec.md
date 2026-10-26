# Alertas de Inventario, Stock Crítico y Vencimientos

> Audiencia: clientes, administradores de negocio, producto y soporte. Sin detalles técnicos internos.

## Resumen
El módulo de Alertas monitorea de forma continua las existencias del local gastronómico, identificando al instante insumos agotados, productos por debajo del stock mínimo de seguridad, lotes caducados y alimentos próximos a vencer bajo el criterio FEFO (primero en vencer, primero en salir). Integra un indicador visual interactivo en el menú principal, filtros por almacén o área de cocina, barras de salud de existencias y botones de acción rápida para reabastecimiento o baja por merma.

## Reglas de Negocio

### 1. Monitoreo Inteligente de Existencias Críticas
- **Insumos Agotados:** Todo insumo cuyo saldo disponible llega a cero o menos se marca en estado de quiebre absoluto. Requiere atención inmediata del área de compras.
- **Stock Bajo Mínimo:** Cuando las existencias se encuentran por encima de cero pero por debajo o igual al nivel mínimo de seguridad configurado, el sistema genera una alerta preventiva con una barra visual del porcentaje de salud del stock.
- **Salud del Inventario:** El porcentaje de cobertura muestra cuánto resta para alcanzar el nivel óptimo, ayudando al personal a priorizar pedidos antes de que ocurra una rotura operativa.

### 2. Control de Vencimientos y Rotación FEFO
- **Lotes Vencidos:** Cualquier lote cuya fecha de caducidad sea anterior al día actual y mantenga saldo disponible genera una alerta roja crítica.
  - Para estos productos se recomienda realizar una baja inmediata de inventario (Merma) para evitar riesgos sanitarios en cocina o salón.
  - La tarjeta de alerta incluye un acceso directo a la gestión de mermas que preselecciona el producto para agilizar el trámite.
- **Próximos a Vencer (Ventana de Urgencia):** Productos cuya fecha de vencimiento se encuentre dentro de la ventana de aviso configurada (por defecto los próximos 30 días).
  - Muestra la fecha exacta y los días restantes en tiempo relativo (por ejemplo, "vence en 3 días").
  - Permite al chef o supervisor priorizar su uso en preparaciones del menú del día antes de que caduquen.

### 3. Vistas Operativas y Experiencia de Usuario
- **Modo Tarjetas:** Vista visual y compacta diseñada para tablets y pantallas táctiles de cocina, con indicadores cromáticos claros (rojo para agotados y vencidos, amarillo/ámbar para niveles bajos o advertencias preventivas).
- **Modo Listado:** Tabla detallada para administradores que reúne insumos críticos con sus cantidades disponibles, umbrales mínimos, barras animadas de salud y accesos operativos.
- **Filtros por Bodega y Área:** Los encargados pueden segmentar la información por almacén físico (Bodega Central, Cocina Fría, Barra, Pastelería) o área operativa.

### 4. Flujo Ágil de Reposición y Carrito de Compras
- **Carrito de Compras Morado:** Desde la misma vista de alertas, un clic en el icono del carrito agrega el producto al pedido de compra pendiente, valorizado a su costo promedio ponderado.
- El sistema confirma la acción con una notificación inmediata y actualiza el contador de compras sin interrumpir la revisión de alertas.

### 5. Indicador Reactivo en el Menú Lateral
- El icono de Alertas en el menú principal exhibe un distintivo numérico con el total de alertas activas.
- **Pulso Crítico:** Si existen productos agotados o lotes vencidos, el distintivo parpadea en color rojo para llamar la atención del encargado del turno.
- **Aviso Preventivo:** Si solo existen alertas de vencimiento próximo, el distintivo se muestra en color ámbar sin parpadeo.
- Las actualizaciones se reflejan de forma instantánea en todas las pantallas del local sin necesidad de recargar la página.

## Escenarios de Uso
- Un cocinero revisa el panel de alertas al iniciar el turno matutino, nota que el queso mozzarella vence en 48 horas y decide sugerir una pizza especial en el menú del día.
- El encargado de bodega visualiza 3 insumos bajo mínimo; con tres clics los añade al carrito de compras para generar la orden del día al proveedor.
- El supervisor detecta un lote de yogurt caducado el día anterior, hace clic en "Reportar Merma" y el sistema abre la ventana de baja con los datos precompletados para su firma y descarte formal.

## Documento técnico par
Equivalente para desarrolladores: `inventory-alerts.code.spec.md`.
