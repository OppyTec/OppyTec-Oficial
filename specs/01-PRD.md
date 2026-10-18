# 01-PRD.md — Product Requirements Document (PRD)

> **Documento:** Requerimientos de Producto, Modelo Comercial SaaS y Especificación Funcional  
> **Proyecto:** OppyTec SaaS v2.0  
> **Estado:** Actualizado y Sincronizado con las 16 Estrategias Maestras (`.agent/estrategias/`)  
> **Fecha:** Octubre 2026  

---

## 1. Resumen Ejecutivo y Problema a Resolver

### 1.1 Contexto de Mercado
Los establecimientos gastronómicos, hoteleros y de retail alimentario (restaurantes, bares, hoteles, cafeterías, centros de eventos y cadenas multilocales estructuradas en Holdings) enfrentan una fuga constante de rentabilidad atribuible a:
1. **Falta de visibilidad en tiempo real del stock y vencimientos (FEFO):** El desfase entre compras, ventas, eventos y consumos genera quiebres de inventario o pérdida de perecibles.
2. **Descontrol en mermas y desperdicios:** Inexistencia de registros auditables y umbrales de autorización que permitan aislar causas y responsabilidades.
3. **Escandallos y recetas desactualizados:** Los costos de los insumos fluctúan en cada factura y las cartas no reflejan el costo real en 3 capas de unidades ni el margen de contribución.
4. **Fricción en abastecimiento, recepción y carga de catálogo:** Cotejo manual lento de planillas Excel y facturas de proveedores sin detección de desvíos de precios ni tiempos de demora (*lead times*).
5. **Complejidad en Holdings Multilocales e Internacionales:** Necesidad de que propietarios y trabajadores autorizados operen en múltiples sucursales de un mismo Holding (ej. Hotel + Restaurante del Hotel), en múltiples idiomas (`i18n`) y divisas (`FX`), manteniendo cada sucursal aislada en sus datos.

### 1.2 La Propuesta de Valor de OppyTec v2.0
OppyTec v2.0 es una plataforma SaaS B2B Multi-Tenant diseñada bajo filosofía ***Mobile-First, Then Web*** que unifica:
- **Gobernanza Multi-Tenant de Grado Bancario:** Jerarquía `Holding -> Entidad Legal (1:1) -> Tenant (Esquema PostgreSQL propio)` administrada desde el panel global de OppyTec.
- **RBAC Dual de Mínimo Privilegio en 3 Niveles (`<modulo>.<submodulo>.<funcion>`):** Con delegación jerárquica, permisos temporales con caducidad automática (JIT), acceso transversal entre Tenants del mismo Holding y auditoría forense inmutable de quién hizo qué y quién otorgó cada permiso.
- **Gestión de Catálogo en 3 Capas de Unidades, Inventario Multi-Bodega, Recetas/Escandallos, Mermas, Buffet/Eventos, Compras y Facturas IA:** Con paridad matemática 100% respecto a `OppyTec-Legacy` e impulsada por el motor de decisiones rápidas **`JEV (Sistema 1)`**.
- **Asistente Inteligente `OppyFy` (Marca Configurable):** Con RAG en 3 Capas, Agente Enrutador de funciones en código duro sobre el negocio del cliente, **Panel RBAC Exclusivo con Dominios y Sub-dominios 100% editables por cada cliente**, medidor de `% de contexto` anti-alucinación y **Paquetes de Créditos independientes del plan, acumulables (`1.000 + 10.000 = 11.000`) y sin caducidad**.
- **Experiencia Global Nativa (`i18n` + Multi-Moneda `FX`):** Selector de Idioma con banderas SVG (`🇪🇸 Español` / `🇺🇸 Inglés` + idiomas futuros) con traducción dinámica de productos/cargos protegiendo nombres propios (`"Pollo King"`), junto a un Selector de Moneda independiente (`CLP`, `USD`, `EUR`, `BRL`) conectado a tasas oficiales de Bancos Centrales (`BCCh` y `BCE`).

---

## 2. Los Dos Universos de Usuarios y Personas del Sistema

### 2.1 Universo 1: Trabajadores Globales de OppyTec (Esquema `public`)
- **SuperUser Génesis ("Dios"):** Primer usuario global del sistema (`oppytec.admin@gmail.com` / `oppytec.admin`), con acceso total a la Administración del Sistema OppyTec.
- **Roles Globales Base (y Personalizados):** `superuser (Rank 0)`, `admin (Rank 10)`, `supervisor (Rank 20)`, `developer (Rank 30)` + cualquier rol adicional que el SuperUser cree.
- **Regla de Cupo:** Creación libre de trabajadores de OppyTec (**sin límite de cupo**), con soporte obligatorio de `soft-delete` y auditoría inmutable.
- **Capacidades Exclusivas en `platform-admin`:**
  - Crear y gestionar **Holdings**, **Entidades Legales**, **Tenants** y **Módulos** (`sales`, `inventory`, `accounting`, etc.).
  - Crear y editar **Planes Comerciales** definiendo libremente la cantidad de trabajadores (`max_active_users`), la memoria de imágenes en R2 (`max_storage_mb`) y los precios multi-moneda.
  - Operar las **2 Vistas FinOps de Monitoreo de IA (`public.llm_request_logs`)** (gasto real en dinero por modelo y por Tenant), la **Consola FX de Bancos Centrales** (monitoreo, historial y corrección manual de tasas), la **Consola de Respaldos en 4 Capas** y el **Centro de Observabilidad de 13 Sub-Vistas** con filtro por `Environment`.

### 2.2 Universo 2: Usuarios Clientes (Holdings y Esquemas `tenant_*`)

| Persona / Perfil | Rol Base en el Cliente | Objetivos y Capacidades en OppyTec v2.0 |
|---|---|---|
| **Carlos — Propietario de Holding** | `propietario (Rank 0)` | Asociado a **1 Holding** y a **1 o varios Tenants** de ese Holding. Tiene todos los accesos habilitados dentro de los módulos contratados en su plan. Puede crear a otros `propietarios`, crear todos los roles que desee, otorgar acceso transversal a sus trabajadores hacia otros Tenants de su mismo Holding, administrar el **Panel RBAC Editable de `OppyFy`**, repartir créditos de `OppyFy` y auditar toda la actividad y prompts de sus empleados. |
| **Marcela — Administradora / Gerente** | `superuser (Rank 5)` / `admin (Rank 10)` | Gestiona el catálogo, compras, recepción de facturas, aprobación de mermas y personal subordinado (bajo la ley de rango estricto y techo de concesión), pudiendo operar en el Hotel y en el Restaurante del mismo Holding con una sola cuenta. |
| **Esteban — Jefe de Cocina / Supervisor** | `supervisor (Rank 20)` / `contador (Rank 20)` | Administra escandallos, conteos físicos, eventos/buffet, turnos o finanzas según los módulos y sub-módulos asignados, recibiendo permisos temporales JIT cuando requiere realizar una tarea extraordinaria que caduca al finalizar. |
| **Javier — Cajero / Operador / Cocinero** | `cajero (Rank 30)` / `usuario (Rank 30)` | Opera desde celular, tablet o caja registrando consumos, ventas POS, conteos o comandos de voz manos libres bajo el principio de mínimo privilegio. |

---

## 3. Reglas Comerciales de Jerarquía, Planes, Cuotas y Add-Ons

### 3.1 Reglas de Cardinalidad Corporativa (`public`)
1. **Holding $\to$ Entidad Legal $\to$ Tenant:**
   - `1 Holding` tiene `1` (o más) `Entidades Legales`.
   - `1 Holding` puede agrupar **varios Tenants**, pero `1 Tenant` pertenece exactamente a **1 Holding**.
   - `1 Tenant` tiene **1 Entidad Legal** y `1 Entidad Legal` tiene **1 Tenant** (relación estricta `1:1`).
   - Cada `Tenant` posee su propio `schema_name` único en PostgreSQL, aislando físicamente toda su operación.
2. **Módulos por Plan (`public.tenant_modules`):**
   - Cada Tenant tiene módulos habilitados o deshabilitados según su plan contratado (`sales`, `inventory`, `accounting`, `recipes`, `purchases`, `operations`, `analytics`, etc.).

### 3.2 Las 3 Cuotas y Palancas Comerciales Editables
1. **Cupo de Trabajadores Activos por Plan (`max_active_users` + `Soft-Delete`):**
   - El Propietario puede crear trabajadores (y distribuir sus roles como desee: ej. 2 `admin`, 3 `supervisor`, 5 `cajero`) hasta alcanzar el límite `max_active_users` del plan contratado (100% editable por el SuperUser).
   - **Regla del `Soft-Delete`:** Cuando un trabajador se retira y el Propietario lo elimina (`is_deleted = true`), su sesión se corta en el acto en Redis, su historial de auditoría se conserva para siempre, **y el trabajador en `soft-delete` deja de contar como activo, liberando su cupo inmediatamente** para contratar al nuevo reemplazo.
2. **Cuota de Memoria de Imágenes en Cloudflare R2 (`max_storage_mb`):**
   - Cada imagen subida se aísla bajo `{env}/{holding_id}/{tenant_id}/...` (cero colisiones aunque dos clientes suban *"Coca Cola Lata 350 cc"*), se optimiza automáticamente a `thumb.webp` + `display.webp` y descuenta de la cuota `max_storage_mb` del plan. Al borrar o reemplazar una imagen, se elimina el archivo huérfano de R2 y se libera la memoria en el acto.
3. **Paquetes de Créditos de `OppyFy` (Independientes del Plan, Acumulables y Sin Caducidad):**
   - Se venden por separado de cualquier plan y pueden comprarse en cualquier momento.
   - **Acumulación sin caducidad:** Si al cliente le quedan `1.000 créditos` y compra un paquete de `10.000`, su saldo pasa a **`11.000 créditos` sin fecha de vencimiento mensual**.
   - El Propietario decide qué trabajadores pueden usar `OppyFy`, cuántos créditos puede gastar cada uno y audita el log completo de prompts enviados.

---

## 4. Alcance Funcional Completo de la Refactorización v2.0 (Paridad con Legacy + Evoluciones)

Todos los módulos existentes en `OppyTec-Legacy` se refactorizan manteniendo el **100% de sus reglas y fórmulas matemáticas de negocio** y sumando los estándares de OppyTec v2.0:

1. **Catálogo Maestro, 3 Capas de Unidades e Importador Excel IA (`catalog`):**
   - Wizard de 4 pasos con autoguardado de borrador, agrupación por **Categoría**, **Familia de Productos** y **Etiquetas (`#tags`)**, conversión exacta en 3 capas (`Compra -> Envase -> Receta`), e **Importador Masivo de Excel/CSV en 5 etapas** impulsado por `JEV (Sistema 1)`.
2. **Inventario Multi-Bodega, Áreas Operativas, Kardex, Conteos y Mermas (`inventory`):**
   - Movimientos atómicos en `registro_stock` (`entrada`, `salida`, `consumo`, `merma`, `ajuste`, `transferencia`, `reversion`), alertas de vencimiento FEFO, conteos físicos y **Gestión de Mermas** con umbral de aprobación gerencial, KPIs por producto/receta/categoría y Heatmap 7x24.
3. **Recetas / Escandallos, Sub-Recetas, Combos y Grupos de Opciones (`recipes`):**
   - Costeo promedio ponderado recursivo con `Decimal`, factor de merma, simulador de precios/márgenes multi-moneda y documentos/videos de preparación.
4. **Abastecimiento, Órdenes de Compra, Proveedores y Facturas IA (`procurement`):**
   - Presupuestos de compra con reinicio mensual, doble autorización opcional, métricas de cumplimiento y demora (*lead time*) de proveedores, incidencias en recepción y **procesamiento inteligente de facturas PDF/imagen** (protegido con validación binaria *Magic Bytes*).
5. **Operaciones, Consumo/Ventas POS, Manos Libres por Voz, Buffet, Eventos y Actividades (`operations`):**
   - Descuento atómico de ingredientes con bloqueo canónico (`ORDER BY producto_id ASC FOR UPDATE`), sesiones y estaciones de Buffet con plantillas y recortes visuales, gestión de Eventos y Salones, comandos de voz manos libres (Silero VAD / Alexa), Notas personales/de equipo, Tareas con urgencia y Turnos/Horarios del personal.
6. **Paneles Ejecutivos, Informes y Proyecciones (`analytics`):**
   - Resumen General, Resumen Ejecutivo, Control de Pérdidas, Eficiencia Operacional, Visión Financiera y Proyecciones con latencia $P_{95} \le 800\text{ ms}$.
7. **Asistente Inteligente `OppyFy` (`oppy_ai`):**
   - Tutor de plataforma (sobre `specs/business-domain/`, **prohibido revelar ingeniería interna**) + Consultor operativo del negocio del cliente (invocando funciones en código duro para ventas, stock, demoras y factibilidad de eventos + generación de tablas y gráficos en el Split-View Canvas), con medidor de `% de contexto` y Panel RBAC propio con Dominios y Sub-dominios editables por cada cliente.

---

## 5. Criterios de Aceptación Globales (Definition of Done)

Para considerar cualquier módulo de OppyTec v2.0 como **"Terminado" (Done)**:
1. **Paridad Matemática 100% con Legacy:** Los cálculos de unidades, costos, escandallos, mermas y Kardex coinciden exactamente con `OppyTec-Legacy` usando `Decimal` (cero `float`), certificado por `Hypothesis` y el Agente 09.
2. **RBAC de 3 Niveles y Auditoría Forense:** 100% de rutas protegidas por `<modulo>.<submodulo>.<funcion>` y toda mutación registrada con su `authorization_lineage`.
3. **Evaluación `JEV` e `i18n` + `FX` al 100%:** Todo módulo evalúa *"¿Lo puede hacer JEV (Sí/No)?"*, tiene `0` strings quemados (paridad 1:1 en JSONs `es`/`en` + traducción dinámica `*_i18n` protegiendo nombres propios como `"Pollo King"`) y formatea montos con el selector Multi-Moneda.
4. **Fidelidad Visual Legacy (3 Temas) y *Mobile-First*:** Funciona de forma nativa en móvil (`< 768px`, targets $\ge 44\text{px}$, `<AdaptiveDataView />`, `<ResponsiveDialog />`), tablet y desktop en los 3 temas (`light`, `dark`, `ocean-blue`).
5. **Telemetría y Seguridad Aprobadas:** 100% de llamadas IA registradas en `public.llm_request_logs`, trazas `X-Trace-ID` en OpenTelemetry y sello `SECURITY_APPROVED` del Agente 10 (0 hallazgos en Semgrep, Trivy y los 11 vectores Red Team).
