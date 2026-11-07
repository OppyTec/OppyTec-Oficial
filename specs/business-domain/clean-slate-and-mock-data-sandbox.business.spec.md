# Clean Slate y Bóveda de Datos de Prueba — Especificación Funcional de Negocio

> Audiencia: Gerentes de Operaciones, Directores de Franquicias Gastronómicas, Administradores de Plataforma y Auditores de Negocio. Libre de código y tecnicismos internos.

---

## 1. Visión y Propuesta de Valor para el Negocio Gastronómico

En la industria de la hospitalidad y la gastronomía comercial, la adopción de una plataforma de gestión operativa, control de inventario y escandallo de recetas exige un nivel absoluto de certeza sobre la veracidad de los datos. Cuando una cadena de restaurantes, una franquicia o un operador independiente inicia sus actividades en el sistema, es imperativo que su espacio de trabajo comience en un **Estado Base Virgen (*Clean Slate*)**, completamente limpio de transacciones ficticias, holdings de ejemplo o catálogos ajenos a su realidad comercial.

Históricamente, los sistemas de demostración solían mezclar datos de prueba en las vistas operativas para que la pantalla no luciera vacía. No obstante, en un entorno gastronómico profesional, esta práctica genera:
1. **Riesgo de Confusión Operativa:** Un jefe de cocina o bodeguero podría asumir que ciertos insumos, lotes de caducidad o costos teóricos mostrados en pantalla corresponden a inventario real de su sucursal.
2. **Distorsión en Informes y Auditorías:** Estadísticas de mermas, pedidos sugeridos y variaciones de costos (*Food Cost*) contaminadas por ventas o compras simuladas.
3. **Falta de Preparación para la Puesta en Marcha:** La incapacidad de validar la experiencia real de un restaurante recién inaugurado que aún no ingresa su primera factura de compra o su primera recepción de mercadería.

La arquitectura funcional de **Clean Slate y Bóveda de Respaldo Maestro** resuelve de raíz este desafío, estableciendo tres pilares de valor comercial:

- **Lienzo Virgen Soberano por Defecto:** Al iniciar el sistema en modo operativo, la plataforma presenta un estado pulcro con cero restaurantes, cero insumos ficticios, cero recetas inventadas y cero transacciones financieras residuales.
- **Estados Vacíos Legítimos (*Empty States*) con Guía de Incorporación:** Cada pantalla vacía no representa un fallo, sino una oportunidad de bienvenida comercial con explicaciones claras, íconos temáticos y botones de acción directa para guiar al usuario en la creación de su primer insumo, proveedor o receta.
- **Bóveda Maestra de Datos de Prueba Aislada:** Todos los escenarios enriquecidos de simulación (Alta Cocina, Buffet de Hotel, Cocina Oculta y Cadena de Comida Rápida) quedan resguardados en una bóveda documental segura, disponible bajo demanda exclusiva en el Laboratorio de Simulación para capacitación, auditoría de procesos y demostraciones comerciales.

---

## 2. Los Tres Componentes Clave del Modelo de Negocio

### 2.1. El Superusuario Génesis Inicial
El aprovisionamiento de una nueva plataforma requiere una figura de gobernanza soberana. El **Superusuario Génesis** es la entidad de control global que inicializa el sistema con:
- Acceso exclusivo al portal de administración global.
- Configuración canónica de los módulos de la aplicación (Catálogo, Inventario, Recetas, Compras, Operaciones, Analítica y Asistente Inteligente).
- Definición de los planes comerciales y catálogo de capacidades del servicio.
- Habilitación de modelos fundacionales de inteligencia analítica para optimización de inventarios.
- Capacidad para crear la primera empresa holding, dar de alta la primera razón social y registrar al administrador comercial del primer cliente.

### 2.2. Estados Vacíos Legítimos (*Empty States*)
En una plataforma gastronómica en producción, las vistas sin datos reflejan el estado natural de un negocio en sus etapas iniciales:
- **Bodega e Inventario:** Si no se han registrado compras, la bodega muestra un panel instructivo informando que no hay existencias activas, invitando a cargar la primera factura electrónica o realizar la recepción de insumos.
- **Alertas de Caducidad:** Un inventario sin alertas no es una anomalía, sino el estado ideal de una cocina que no registra productos vencidos ni en riesgo crítico.
- **Escandallo y Recetas:** La carta de preparaciones presenta un botón destacado para definir los ingredientes maestros y rendimientos de porción.
- **Finanzas y Consumo:** Los tableros analíticos reflejan contadores en cero exacto, garantizando a los auditores financieros que no existen cargos fantasma ni movimientos ocultos.

### 2.3. La Bóveda de Respaldo Maestro de Datos de Prueba
Para preservar el valor del entrenamiento y las pruebas comerciales sin arriesgar la operación real, la plataforma dispone de una **Bóveda Maestra de Respaldo** que contiene:
- **22 Dominios de Negocio Estructurados:** Catálogos completos de insumos perecibles con mermas operativas, órdenes de compra con proveedores calificados, facturas tributarias de muestra, árboles de recetas compuestas y configuraciones de turnos.
- **4 Presets Gastronómicos Especializados:**
  1. *Restaurante de Alta Cocina:* Carnes premium, vinos de guarda y mermas controladas por gramaje.
  2. *Hotel Buffet:* Volúmenes masivos de insumos, porcionamiento matutino y bandejas de reposición continua.
  3. *Cocina Oculta (Dark Kitchen):* Preparaciones orientadas a despacho rápido, envases descartables y altos flujos de comandas.
  4. *Cadena de Comida Rápida:* Estandarización de combos, inventarios de alta rotación y tiempos críticos de entrega.
- **Operaciones de Control en un Clic:**
  - *Descargar Bóveda Documental:* Permite a los analistas de negocio exportar el archivo de respaldo maestro para auditoría externa o migración de ambientes de laboratorio.
  - *Restablecer Estado Virgen (Purga Total):* Limpia en un instante cualquier escenario de prueba inyectado, regresando al estado de lienzo limpio sin alterar las credenciales de administración.
  - *Restaurar Demostración:* Activa de forma inmediata el entorno enriquecido para presentaciones comerciales o capacitaciones de nuevos franquiciados.

---

## 3. Matriz de Comportamiento Operativo: Modo Limpio vs Modo Demostración

| Dimensión Funcional | Modo Virgen (*Clean Slate*) | Modo Demostración (*Demo*) |
|---|---|---|
| **Propósito de Uso** | Operación real de restaurantes, auditoría fiscal, alta de clientes nuevos | Capacitación de personal, ventas ejecutivas, demostraciones guiadas |
| **Listado de Clientes y Holdings** | Exactamente cero clientes; el sistema aguarda el registro de la primera empresa | Presenta grupos gastronómicos de ejemplo con múltiples sucursales |
| **Catálogo de Insumos y Recetas** | Pantallas de bienvenida con botones de creación manual o importación masiva | Cientos de ingredientes precargados con recetas multinivel y combos |
| **Control de Existencias y Lotes** | Cero existencias registradas; indicadores en balance neutro | Lotes con semáforos de frescura (verde, amarillo y rojo) para simulación |
| **Billetera de Inteligencia y Créditos** | Cero créditos consumidos ficticiamente; saldo limpio acorde al plan suscrito | Métricas de demostración para ilustrar el consumo de consultas avanzadas |
| **Indicadores Financieros y Costos** | Saldos en cero exacto en la moneda local configurada | Indicadores simulados de ventas y márgenes calculados con rigor monetario |

---

## 4. Criterios de Aceptación Funcional

1. **Garantía de Lienzo Virgen en el Primer Inicio:** Al acceder por primera vez a la plataforma como administrador, no debe existir ningún restaurante, insumo ni registro de compra precargado.
2. **Preservación Inviolable del Superusuario:** El proceso de purga o restablecimiento a estado virgen nunca debe inhabilitar ni desconfigurar la cuenta del Superusuario de la plataforma.
3. **Consistencia de Estados Vacíos:** Ningún panel del sistema debe presentar errores visuales, textos incompletos o valores indeterminados ante la ausencia de registros; cada módulo debe presentar un mensaje orientador en el idioma preferido del usuario.
4. **Independencia de la Bóveda de Prueba:** La descarga o activación de los datos de prueba debe gestionarse de forma explícita y aislada, asegurando que un operador no pueda activar el modo de demostración por descuido en un restaurante en marcha.
5. **Neutralidad Monetaria:** Los tableros financieros en modo virgen deben reportar balance neutro exacto, eliminando cualquier cifra pre-programada.
