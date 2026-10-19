---
title: "Bitácora Fase 5: UI React 19 Mobile-First, ADN Visual Legacy (3 Temas), i18n con Banderas SVG, Multi-Moneda FX, OppyFy y 13 Sub-Vistas de Observabilidad"
phase: "Fase 5"
date: "2026-10-19"
author_agent: "12-tech-writer-openspec-archify"
tags:
  - bitacora
  - fase-5
  - react-19
  - mobile-first
  - legacy-dna
  - i18n
  - fx-currency
  - websockets
  - oppyfy
  - observabilidad
---

# 📓 Bitácora Fase 5: Cómo Se Construyó la Experiencia Visual en React 19 (*Mobile-First*), Conservando el ADN de Legacy y Conectada en Tiempo Real

> **Resumen en simple para personas:**  
> En la **Fase 5**, el Escuadrón construyó la interfaz completa de **OppyTec v2.0 en React 19 (`oppytec-frontend/`)** bajo una arquitectura **Feature-Driven sin acoplamiento cruzado** (`features/* -> shared/*`, con `0` importaciones entre módulos de negocio). La nueva interfaz respeta al 100% el **ADN Visual de OppyTec-Legacy** —conservando sus **3 temas icónicos (`light`, `dark`, `ocean-blue`)**, su paleta de 42 colores semánticos, sus 49 íconos vectoriales y efectos *glassmorphism*—, pero rediseñada desde cero bajo filosofía ***Mobile-First*** para que un chef, bodeguero o administrador pueda operar con una sola mano desde el teléfono en plena cocina, o en pantallas panorámicas de escritorio.

---

## 1. ¿Qué Construyó Cada Agente del Escuadrón en la Fase 5?

### 🎨 Agente 05 (`05-frontend-senior-dev`) — ADN Visual Legacy, *Mobile-First*, `<Can>`, `<HoldingTenantSwitcher />` y WebSockets Zero-Polling
1. **Conservación del ADN Visual Legacy y los 3 Temas (`light`, `dark`, `ocean-blue`):**
   - **Tema `ocean-blue` (Identidad Clásica OppyTec):** Conserva los degradados profundos oceánicos, tarjetas traslúcidas (*glassmorphism*) y acentos cian/esmeralda de alta legibilidad en cocinas con poca luz.
   - **Tema `dark` (Alto Contraste Nocturno):** Optimizado para turnos nocturnos e inventarios prolongados sin fatiga ocular.
   - **Tema `light` (Oficina y Contabilidad):** Máxima nitidez para conciliación de facturas, auditoría forense y reportes ejecutivos.
2. **Ergonomía *Mobile-First* para Terreno (Cocina y Bodega):**
   - Áreas táctiles mínimas de `48x48px`, barra de navegación inferior (`MobileBottomNav`) para el pulgar, tablas adaptativas (`ResponsiveDataTable`) que se transforman automáticamente en tarjetas accionables en pantallas móviles y teclado numérico rápido (`KitchenWasteRegistrationQuickPad`) para registrar mermas o consumos de buffet en segundos.
3. **Guardia Declarativo `<Can>` y Conmutador Multi-Sucursal `<HoldingTenantSwitcher />`:**
   - **`<Can perform="modulo.submodulo.funcion">`:** Evalúa en memoria la matriz RBAC de 3 niveles del usuario autenticado (intersección entre el Plan del Holding, permisos del rol, permisos temporales JIT y denegaciones explícitas), ocultando o deshabilitando botones no autorizados sin parpadeos.
   - **`<HoldingTenantSwitcher />`:** Permite a dueños de Holdings gastronómicos cambiar de Entidad Legal (`1:1` con Tenant) y de sucursal en un clic, limpiando la caché de consultas y reconectando el canal WebSocket al nuevo `tenant_<slug>` instantáneamente.
4. **Tiempo Real sin *Polling* (`useRealtimeSync` + WebSockets + TanStack Query v5):**
   - Prohibido el uso de `setInterval` o *polling* HTTP. El hook `useRealtimeSync` mantiene una única conexión WebSocket autenticada (`/api/v1/ws/realtime`) suscrita a Redis Pub/Sub + Streams (`XADD`/`XRANGE`). Cuando cambia el stock en el Kardex, llega una alerta o se revoca un permiso, TanStack Query v5 invalida quirúrgicamente solo las llaves afectadas y recupera eventos perdidos tras micro-cortes de Wi-Fi usando `last_event_id`.

### 🌍 Agente 07 (`07-i18n-and-fx-currency-specialist`) — `LanguageFlagSelector` con Banderas SVG, 11 Namespaces `i18n` y `CurrencySelector` Multi-Moneda FX
1. **Selector de Idioma con Banderas SVG (`LanguageFlagSelector`) y 11 Namespaces JSON (`es`/`en`):**
   - Selector instantáneo con banderas vectoriales SVG (`🇪🇸 ES` / `🇺🇸 EN`) sin recargar la página.
   - El 100% de los textos de la interfaz proviene de **11 namespaces JSON** (`common`, `auth`, `rbac_audit`, `catalog`, `inventory`, `recipes`, `procurement`, `operations`, `analytics`, `oppyfy`, `platform_admin`), con paridad exacta de claves verificada por tests de arquitectura.
   - **Protección de Nombres Propios (`"Pollo King"`):** El traductor dinámico en la UI respeta el glosario inmutable del restaurante para que marcas propias y nombres de platos de autor jamás se traduzcan erróneamente.
2. **Selector de Moneda (`CurrencySelector`) y Formateo `Decimal` Sin Punto Flotante:**
   - Permite alternar la visualización financiera entre `CLP`, `USD`, `EUR` y `BRL` mostrando el sello de tasa oficial (`FxRateBadge`) obtenida del **Banco Central de Chile (BCCh)** y **Banco Central Europeo (BCE Frankfurter)**, operando siempre sobre cadenas `Decimal` exactas para evitar errores de redondeo.

### 🤖 Agente 06 (`06-ai-oppyfy-and-jev-engineer`) — Espacio de Trabajo `OppyFy`, RBAC Editable por Cliente y Billetera de Créditos
1. **Workspace Conversacional `OppyFy` (`OppyFyAssistantWorkspace`):**
   - Chat en streaming conectado al RAG de 3 capas (que consulta únicamente `specs/business-domain/` y los datos autorizados del restaurante, con **0% de acceso a código fuente**).
   - Muestra el distintivo de velocidad y confianza del motor **`JEV` (Sistema 1)** (`JevSystem1ConfidenceBadge`) cuando una consulta rápida es resuelta sin gastar tokens pesados.
2. **Panel de Permisos de IA (`OppyFyRbacSubdomainConfig`) y Billetera Acumulable (`CreditWalletTopupView`):**
   - El dueño del restaurante puede activar o apagar con interruptores simples qué sub-dominios puede consultar cada rol en `OppyFy` (costos de recetas, compras, inventario, mermas).
   - Visualización en vivo del saldo de créditos IA (donde los paquetes comprados **se acumulan y jamás caducan**) y tabla FinOps de consumo por modelo.

### 🔭 Agente 08 (`08-environments-and-observability-engineer`) — Consola `platform-admin` y las 13 Sub-Vistas de Observabilidad 4-Pilares
1. **Hub de Observabilidad de 13 Sub-Vistas (`Observability13SubViewsHub`) para el SuperUser de OppyTec:**
   - Integra en una sola consola administrativa (`feature:platform-admin`) las **13 sub-vistas operativas** alimentadas por los 4 pilares (`OpenTelemetry`, `Grafana LGTM`, `Sentry/GlitchTip` y `Umami`):
     1. Estado Global de los 5 Entornos (`local`, `preview`, `ci`, `staging`, `production`) y semáforo `ENV_NAMESPACE`.
     2. Latencia HTTP `p50`/`p95`/`p99` por módulo DDD (`OpenTelemetry` + `Prometheus`).
     3. Explorador de Trazas Distribuidas E2E (`Tempo`: Frontend $\to$ FastAPI $\to$ PostgreSQL/Redis).
     4. Caudal de Logs Estructurados JSON con verificación de `0%` PII (`Loki`).
     5. Salud del Pool PostgreSQL Multi-Schema y auditoría de `SET LOCAL` / `RESET search_path`.
     6. Estado del *Circuit Breaker* de Redis (`< 50ms`), canales Pub/Sub y Streams WebSocket activos.
     7. Radar de Excepciones y *Crash-Free Sessions* (`Sentry` / `GlitchTip`).
     8. Analítica de Producto Ética sin Cookies y Embudo de Adopción por Módulo (`Umami`).
     9. Telemetría FinOps de IA (`llm_request_logs`: tokens, latencia, tasa de ahorro `JEV` Sistema 1 y créditos por Holding).
     10. Monitor de Cuotas de Almacenamiento Cloudflare R2 (`.webp` dual y porcentaje de MB por Plan).
     11. Salud de Sincronización Cambiaria FX (`BCCh` + `BCE Frankfurter` y alertas de variación `> 8%`).
     12. Estado de la Bóveda de Respaldos en 4 Capas (`.sql.zst.age`) y disparador de restauración quirúrgica por Tenant (`restore-tenant`).
     13. Monitor de Seguridad Defensiva (bloqueos de *Rate Limiter*, rechazos *Magic Bytes* y alertas de auditoría).

---

## 2. Mapa AST del Frontend en Graphify (`v2_phase5_frontend_graph.json`)

El **Agente 12 (`12-tech-writer-openspec-archify`)** generó el snapshot determinista del grafo AST del frontend en:
- [`docs/architecture/graphify/v2_phase5_frontend_graph.json`](../../architecture/graphify/v2_phase5_frontend_graph.json)

Este grafo certifica que los **10 módulos de negocio en `oppytec-frontend/src/features/`** (`auth`, `rbac-and-audit`, `catalog`, `inventory`, `recipes`, `procurement`, `operations`, `analytics`, `oppyfy`, `platform-admin`) dependen exclusivamente de los **5 núcleos compartidos en `src/shared/`** (`i18n`, `currency`, `auth`, `realtime`, `components`), manteniendo **0 importaciones cruzadas entre features**.

---

## 3. ¿Qué Sigue Ahora? (Rumbo a la Fase 6: Certificación Final y Go-Live)
- Consolidar la Fase 5 en el *Smart Merge Train* y pasar a la **Fase 6 (`specs/06-IMPLEMENTATION-PLAN.md`)**: pruebas E2E integrales, certificación final de paridad matemática con `OppyTec-Legacy`, auditoría completa de los 5 mapas de `Archify` y preparación del despliegue productivo.
