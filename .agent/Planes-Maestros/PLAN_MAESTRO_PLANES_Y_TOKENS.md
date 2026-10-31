# 📋 PLAN MAESTRO DE CONTROL Y EJECUCIÓN: ADMINISTRACIÓN DE PLANES COMERCIALES, POLÍTICA SAAS Y MONITOREO FINOPS DE TOKENS IA (`/admin/plans`, `/admin/token-consumption`)

> **Regla de Gobernanza:** Este documento es el tablero de control de ejecución estricto de la Administración de Planes Comerciales, la Política Global de Conversión de Créditos de IA y la Consola FinOps de Consumo de Tokens de OppyTec v2.0.  
> Cada paso debe ser **100% corroborado y aprobado** antes de pasar al siguiente.  
> **Solo cuando se finalicen todos los pasos**, este documento podrá ser archivado o eliminado, no antes.  
> **Fuentes de Verdad Históricas (100% Solo Lectura):**  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Admin/PlansPage.tsx` (Catálogo de Planes Comerciales, Tiers, Cuotas, y Card Colapsable del Conversor de Créditos & Política SaaS)  
> - `OppyTec-Legacy/OppyTec_Frontend/src/pages/Admin/TokenConsumptionPage.tsx` (Consola FinOps, KPIs, Selector Dual Créditos vs Tokens, Acordeón Jerárquico Holding $\to$ Tenant $\to$ Logs, y Modales de Ajuste de Cupos)  
> - `OppyTec-Legacy/OppyTec_Backend/alembic/versions/c9d0e1f2a3b4_add_system_plans_table.py` (Esquema DDL de Planes Comerciales)  
> - `OppyTec-Legacy/OppyTec_Backend/openspec/specs/architecture/subscription-and-licensing.md` (Especificación formal de Planes, Tiers y Licencias)  
> **Destinos de Construcción en OppyTec v2.0:**  
> - Frontend: `oppytec-frontend/src/features/platform-admin/` (`plans/`, `tokens/`, `hooks/`, `types.ts`, `AdminPlansPage.tsx`, `TokenConsumptionPage.tsx`)  
> - Backend: `oppytec-backend/src/modules/tenancy/` y `oppytec-backend/src/modules/oppy_ai/` (Esquema `public`, DTOs Pydantic v2, Endpoints REST RFC 7807, Gobernanza FinOps y Auditoría de Tokens)  

---

## 📊 Estado General del Proyecto

- [x] **Fase 1:** Arquitectura de Persistencia, Esquemas PostgreSQL `public` y Migración Alembic Correlativa (Extensión de `public.system_plans` con `monthly_ai_credits`, `tier`, `is_popular`, `is_active`, `description` + Tabla `public.saas_ai_policy_config` para conversión dinámica de tokens a créditos) — **COMPLETADA**
- [x] **Fase 2:** Motor Backend FastAPI & Transaccionalidad FinOps (Endpoints REST RFC 7807 bajo `/api/v1/platform-admin/plans`, `/api/v1/platform-admin/ai-credits/policy`, `/api/v1/platform-admin/token-consumption` con agregación por Holding/Tenant desde `public.llm_request_logs` y mutación atómica de cupos) — **COMPLETADA**
- [x] **Fase 3:** Frontend Feature Core & Hooks Reactivos (`types.ts`, `useAdminPlans.ts`, `useSaaSQuotaPolicy.ts`, `useTokenConsumption.ts`, TanStack Query v5 + WebSockets realtime zero-polling) — **COMPLETADA**
- [x] **Fase 4:** Vista 1 — Catálogo de Planes Comerciales & Política SaaS (`/admin/plans`): Réplica exacta y modernizada de `PlansPage` de Legacy, Cabecera con selector, Card colapsable animada del Conversor de Créditos y Simulación de Márgenes (>95%), Catálogo de tarjetas con Tiers, badges `Popular` y modal de Crear/Editar con auto-slug — **COMPLETADA**
- [x] **Fase 5:** Vista 2 — Consola FinOps de Consumo de Tokens & Créditos (`/admin/token-consumption`): Réplica exacta y modernizada de `TokenConsumptionPage` de Legacy, 4 Tarjetas KPI, Toggle Dual (*Ver en Créditos* vs *Ver en Tokens*), Buscador en vivo, Filtros de modelo/estado y Popover persistido de columnas opcionales — **COMPLETADA**
- [x] **Fase 6:** Acordeón Jerárquico de 3 Niveles (Holding $\to$ Tenant $\to$ Logs de Tokens), Paginador Canónico `TablePagination` y Modales de Ajuste de Cupos de Créditos por Holding y Tenant — **COMPLETADA**
- [x] **Fase 7:** Integración con Navegación, Enrutamiento en `router.tsx` y Sidebar de Administración (`AdminSidebar.tsx`) — **COMPLETADA**
- [x] **Fase 8:** Capas Cruzadas: i18n 100% `es`/`en` (`platform_admin.json`), Multi-Moneda FX con `Decimal`, Observabilidad OpenTelemetry, Testing 5D (Vitest + Pytest) y Certificación de Calidad — **COMPLETADA**

---

## 🔍 Detalle y Criterios de Aceptación por Fase

---

### [x] FASE 1: Arquitectura de Persistencia, Esquemas PostgreSQL `public` y Migración Alembic Correlativa — ✅ 100% COMPLETADA
- [x] **1.1** Extensión del Modelo `SystemPlan` en `oppytec-backend/src/modules/tenancy/infrastructure/models.py`:
  - Enriquecer la entidad `public.system_plans` asegurando paridad con Legacy y V2:
    - `description`: `Text` nullable (descripción comercial del plan).
    - `monthly_ai_credits`: `Integer` default `1000` (cuota base mensual de créditos OppyFy).
    - `tier`: `SmallInteger` default `1` (orden jerárquico del plan comercial).
    - `is_popular`: `Boolean` default `False` (destacado visual con badge dorado `Popular`).
    - `is_active`: `Boolean` default `True` (disponibilidad comercial para contratación).
  - Preservar las cuotas paramétricas ya existentes en V2 (`max_active_users`, `max_products`, `max_suppliers`, `max_recipes`, `max_combos`, `max_storage_mb`, `included_modules`) y precios multi-moneda (`price_clp`, `price_usd`, `price_eur`, `price_brl`).
- [x] **1.2** Modelo de Política Global de Conversión SaaS (`public.saas_ai_policy_config`):
  - Ubicación: `oppytec-backend/src/modules/tenancy/infrastructure/models.py` o `modules/oppy_ai/infrastructure/models.py`.
  - Campos:
    - `id`: `Integer` PK (registro único singleton `id=1`).
    - `tokens_per_credit`: `Integer` default `1000` (tasa técnica base: 1 crédito = 1.000 tokens).
    - `default_monthly_credits`: `Integer` default `2000` (cuota base mensual estándar por local).
    - `credit_price_clp`: `Numeric(14, 2)` default `Decimal("15.00")` (precio de venta extra CLP).
    - `credit_price_usd`: `Numeric(14, 4)` default `Decimal("0.0150")` (precio de venta extra USD).
    - `updated_at`: `DateTime(timezone=True)` con `now()`.
    - `updated_by`: `Integer` FK `public.users.id` nullable.
- [x] **1.3** Migración Alembic Correlativa Lineal:
  - Generar migración correlativa para el alcance `public`: `oppytec-backend/alembic/versions/0007_public_system_plans_extension_and_saas_policy.py`.
  - `down_revision = "0006_tenant_approval_requests_and_notification_matrix"`.
  - Adición idempotente de columnas y creación de `saas_ai_policy_config` con seed inicial de datos predeterminados.
- [x] **1.4** Dominio y Value Objects DDD (`domain/`):
  - `PlanTier`: Value Object numérico con validación $> 0$.
  - `TokenCreditConversionRate`: Conversor determinista bidireccional entre tokens brutos y créditos de IA usando exclusivamente `Decimal` (cero `float`).
  - `SimulatedProfitMargin`: Cálculo de costos reales de API vs valor comercial y margen bruto ($> 95\%$).

---

### [x] FASE 2: Motor Backend FastAPI & Transaccionalidad FinOps — ✅ 100% COMPLETADA
- [x] **2.1** Servicios de Aplicación (`application/`):
  - `SaaSPolicyService`:
    - `get_policy_config()`: Obtiene la tasa de conversión y precios unitarios vigentes.
    - `update_policy_config(payload, actor_id)`: Actualización atómica de la política con emisión de evento de auditoría y notificación WebSocket.
  - `AdminPlansService`:
    - `list_plans()`: Listado de planes ordenados por `tier ASC`, incluyendo recuento dinámico de clientes activos contratándolo.
    - `create_plan(payload, actor_id)`: Validación de unicidad de `slug` y persistencia con cuotas paramétricas y créditos IA.
    - `update_plan(slug, payload, actor_id)`: Actualización segura de cuotas, precios y módulos.
    - `delete_plan(slug, actor_id)`: Bloqueo de eliminación si existen Holdings o Tenants activos contratándolo (HTTP 409 Conflict).
  - `TokenConsumptionAggregatorService`:
    - Agregación eficiente desde `public.llm_request_logs` cruzando con `public.holdings` y `public.tenants`:
      - Agrupación jerárquica: `Holdings -> Tenants -> Logs`.
      - Métricas acumuladas: `total_requests`, `total_tokens`, `input_tokens`, `output_tokens`, `estimated_cost_usd` y `estimated_cost_clp` (usando `fx_service.py`).
      - Cálculo de créditos consumidos (`tokens / tokens_per_credit`), créditos restantes y porcentaje de uso (`credit_usage_pct`).
    - Filtros server-side: modelo de IA (`model_name`), estado (`api_success`), búsqueda por holding/tenant/usuario, ordenación y paginación.
  - `CreditQuotaAdjustmentService`:
    - `update_holding_credit_quota(holding_id, monthly_credits, distribution_mode)`: Actualización de cuota mensual y modo de bolsa (`shared` vs `per_tenant`).
    - `update_tenant_credit_quota(tenant_id, monthly_credits)`: Ajuste individual de cuota para una sucursal específica.
- [x] **2.2** Presentación REST y Enrutadores FastAPI:
  - Endpoints bajo `/api/v1/platform-admin/plans`:
    - `GET /api/v1/platform-admin/plans`: Listar catálogo de planes comerciales.
    - `POST /api/v1/platform-admin/plans`: Crear nuevo plan comercial.
    - `PUT /api/v1/platform-admin/plans/{slug}`: Actualizar plan comercial existente.
    - `DELETE /api/v1/platform-admin/plans/{slug}`: Eliminar plan (con validación de clientes activos).
  - Endpoints bajo `/api/v1/platform-admin/ai-credits/policy`:
    - `GET /api/v1/platform-admin/ai-credits/policy`: Obtener política global de conversión y cuotas.
    - `PUT /api/v1/platform-admin/ai-credits/policy`: Actualizar política global (requiere `platform_admin.plans.manage`).
  - Endpoints bajo `/api/v1/platform-admin/token-consumption`:
    - `GET /api/v1/platform-admin/token-consumption`: Consulta jerárquica agregada de consumo FinOps con paginación y filtros.
    - `PATCH /api/v1/platform-admin/holdings/{id}/ai-credits`: Ajustar cupo de créditos de Holding.
    - `PATCH /api/v1/platform-admin/tenants/{id}/ai-credits`: Ajustar cupo de créditos de Tenant individual.
- [x] **2.3** Seguridad y Guardias RBAC de 3 Niveles:
  - Guardias estrictas para SuperUser / Global Admin:
    - `platform_admin.plans.read`: Consulta de planes y políticas.
    - `platform_admin.plans.manage`: Creación, edición y eliminación de planes y política SaaS.
    - `platform_admin.tokens.read`: Auditoría y visualización de consumo FinOps de IA.
    - `platform_admin.tokens.manage_quotas`: Ajuste manual de cuotas de créditos a clientes.
- [x] **2.4** Emisión de Eventos Realtime WebSocket:
  - Publicación en Redis Pub/Sub hacia `/api/v1/ws/realtime`:
    - `saas.policy_updated`: Emisión de nueva tasa de conversión de créditos.
    - `saas.plan_changed`: Creación o modificación de planes.
    - `oppyfy.quota_adjusted`: Ajuste en caliente de cuotas de créditos para holding o tenant.
    - `oppyfy.token_consumed`: Actualización en vivo de contadores de tokens sin polling.

---

### [x] FASE 3: Frontend Feature Core & Hooks Reactivos — COMPLETADA
- [x] **3.1** Contratos TypeScript en `oppytec-frontend/src/features/platform-admin/types.ts`:
  - `SystemPlan`, `SystemPlanCreateRequest`, `SystemPlanUpdateRequest`.
  - `SaaSAIPolicy`, `SaaSAIPolicyUpdateRequest`.
  - `TokenLogItem`, `TenantGroup`, `HoldingGroup`.
  - `TokenConsumptionResponse`, `CreditQuotaAdjustmentResponse`.
  - Catálogo enriquecido de módulos `SYSTEM_MODULE_CATALOG` (`core`, `pos`, `inventory`, `kitchen`, etc.).
  - Mocks resilientes de contingencia (`MOCK_SYSTEM_PLANS`, `MOCK_SAAS_POLICY`, `MOCK_TOKEN_CONSUMPTION`).
- [x] **3.2** Hook Reactivo de Planes `useAdminPlans.ts`:
  - TanStack Query v5 para carga reactiva de `/api/v1/platform-admin/plans`.
  - Mutaciones completas `createPlan`, `updatePlan`, `deletePlan` con captura y reporte de bloqueo 409 (clientes activos).
  - Suscripción a eventos WebSocket `saas.plan_changed` y sincronización multiventana `admin_plans_changed`.
- [x] **3.3** Hook de Política Global SaaS `useSaaSQuotaPolicy.ts`:
  - Consulta y actualización de política vía `/api/v1/platform-admin/ai-credits/policy`.
  - Métodos utilitarios puros: `simulateTokensMonthly(credits, tokensPerCredit)` y `calculateCommercialMargin(costUsd, packPriceClp, fxRateClpPerUsd)`.
- [x] **3.4** Hook de Consumo de Tokens FinOps `useTokenConsumption.ts`:
  - Carga jerárquica de logs y agregados FinOps (`/api/v1/platform-admin/token-consumption`).
  - Modo dual de visualización (`viewMode = "credits" | "tokens"`).
  - Mutaciones `updateHoldingCredits` y `updateTenantCredits`.
  - Escucha de eventos WebSocket `oppyfy.token_consumed` y `oppyfy.quota_adjusted` para invalidación reactiva.
- [x] **3.5** Pruebas Unitarias de Hooks (`__tests__/platformAdminHooks.test.ts`):
  - 27/27 tests pasando en Vitest (cálculos de conversión, márgenes, mutaciones, fallback y eventos).
  - 0 errores en `tsc --noEmit`.

---

### [x] FASE 4: Vista 1 — Catálogo de Planes Comerciales & Política SaaS (`/admin/plans`) — COMPLETADA
- [x] **4.1** Modularización y Desacople Arquitectónico:
  - Creado `oppytec-frontend/src/features/platform-admin/plans/PlansPage.tsx` desacoplado del monolito `AdminManagementViews.tsx`.
  - Re-exportado en `plans/index.ts` y expuesto en `features/platform-admin/index.tsx`.
  - Conectada ruta canónica `/admin/plans` en `router.tsx`.
- [x] **4.2** Cabecera Canónica y Controles Superiores:
  - Título `"Catálogo de Planes Comerciales & Política SaaS"`, badge con icono `Sparkles`, subtítulo descriptivo.
  - Botones de acción: `"Ocultar/Abrir Política IA"` (`Calculator`), `"Actualizar"` (`RefreshCw`), `"Crear Plan"` (`Plus`, primario).
- [x] **4.3** Card Colapsable del Conversor de Créditos & Política Global (SaaS Policy):
  - Animación fluida de apertura/cierre con `framer-motion` (`AnimatePresence`).
  - Inputs reactivos:
    - *Tokens por 1 Crédito:* Con badge `Tasa Base` y nota explicativa ("1.000 tokens ≈ 750 palabras en español").
    - *Créditos Base Mensuales:* Con cálculo automático de tokens equivalentes por mes.
    - *Precio Venta Pack Extra en CLP y USD:* Con simulación de pack de 1.000 créditos.
  - **Barra de Rentabilidad & Márgenes:** Costo real API Google USD vs valor comercial sugerido CLP y badge verde `Margen Bruto Estimado > 95%`.
  - Botón `"Guardar Política de Conversión"` con estado `isSavingPolicy` y feedback toast.
- [x] **4.4** Catálogo Visual de Planes Comerciales:
  - Grid de tarjetas comerciales con diseño premium idéntico a Legacy:
    - Badge dorado `Popular` (`Sparkles`) y badges de estado `Activo` (esmeralda) / `Inactivo`.
    - Tier jerárquico (`Tier 1`, `Tier 2`, etc.).
    - Precios destacados en formato multi-moneda (`formatCurrency` / `toLocaleString("es-CL")`).
    - Cuota mensual de créditos de IA con icono `Coins` / `Sparkles`.
    - Lista de módulos incluidos como chips interactivos.
    - Botones de acción: `"Editar Plan"` (`Edit3`) y `"Eliminar Plan"` (`Trash2`).
- [x] **4.5** Modales Interactivos:
  - **Modal Crear / Editar Plan (`Dialog`):**
    - Nombre del plan con auto-slug automático en modo creación.
    - Tier numérico, checkboxes `Activo` y `Popular`.
    - Precios CLP y USD, cuota mensual de créditos de IA.
    - Selector jerárquico de módulos con buscador en vivo, botón `"Seleccionar Todos"` y `"Deseleccionar Todos"`.
  - **Modal de Confirmación de Eliminación:**
    - Alerta de seguridad y bloqueo preventivo si el plan tiene clientes activos contratándolo.
- [x] **4.6** Suite de Pruebas Unitarias Vitest:
  - 15/15 tests passing en `PlansPage.test.tsx` (total 42/42 en la suite `platform-admin`).

---

### [x] FASE 5: Vista 2 — Consola FinOps de Consumo de Tokens & Créditos (`/admin/token-consumption`) — COMPLETADA
- [x] **5.1** Creación del Componente Modular:
  - Ubicación: `oppytec-frontend/src/features/platform-admin/tokens/TokenConsumptionPage.tsx`.
  - Re-exportado en `tokens/index.ts` y expuesto en `features/platform-admin/index.tsx`.
  - Conectada ruta canónica `/admin/token-consumption` en `router.tsx`.
- [x] **5.2** Cabecera y Controles Superiores:
  - Pre-título FinOps `Coins` + `"Monetización & Consumo de IA SaaS"`.
  - Título `"Consumo & Sistema de Créditos IA"`, badge con tasa activa (`1 Cr = X Tokens`).
  - Botón `"Configurar Planes & Política"` con enlace directo a `/admin/plans`.
  - Botón `"Actualizar"` (`RefreshCw`) con indicador de carga y notificación toast.
- [x] **5.3** 4 Tarjetas KPI Resumen:
  1. *Solicitudes Totales:* Conteo global de llamadas cognitivas (`Database`).
  2. *Consumo Global:* Dinámico según el toggle (*Créditos Consumidos* `Coins` vs *Tokens Consumidos* `Cpu`).
  3. *Costo Real API:* Monto en USD y valor equivalente en CLP calculado con el factor FX oficial (`DollarSign`).
  4. *Holdings Activos:* Cantidad de grupos empresariales con consumo registrado (`Building2`).
- [x] **5.4** Barra de Herramientas, Filtros y Toggle Dual:
  - Buscador predictivo en tiempo real con debounce por Holding, Tenant, Usuario o Modelo.
  - **Toggle Dual:** Switch estético para conmutar entre *"Ver en Créditos"* (`credits`) y *"Ver en Tokens"* (`tokens`).
  - Filtro por Modelo de IA (`gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-embedding-001`, `all`).
  - Filtro por Estado de API (Exitosos 200 vs Con Error).
  - **Popover de Columnas Opcionales:** Checkboxes persistidos en `localStorage` (`oppy_token_consumption_cols`) para mostrar/ocultar columnas (`total_tokens`, `request_duration_ms`, `api_success`, `error_message`, `created_at`, `tenant_name`).
- [x] **5.5** Suite de Pruebas Unitarias Vitest:
  - 14/14 tests passing en `TokenConsumptionPage.test.tsx` (total 56/56 en la suite `platform-admin`).

---

### [x] FASE 6: Acordeón Jerárquico de 3 Niveles, Paginador Canónico y Modales de Ajuste de Cupos — COMPLETADA
- [x] **6.1** Tabla Jerárquica Desplegable (3 Niveles):
  - **Nivel 1 — Holding Group:**
    - Fila principal con botón expandir/colapsar (`ChevronDown` / `ChevronUp`), nombre del holding, total de solicitudes, consumo, costo USD/CLP.
    - Barra de progreso visual del cupo mensual de créditos (`credit_usage_pct`) con código de color (verde $<70\%$, ámbar $70-90\%$, rojo pulsante $>90\%$) y `data-testid="holding-progress-bar"`.
    - Botón de acción rápida: Editar cupo del Holding (`Edit3` / `Settings2`).
  - **Nivel 2 — Tenant Group (Sucursal / Local):**
    - Despliegue anidado de locales pertenecientes al holding.
    - Consumo individual por local, porcentaje de uso respecto a la cuota asignada con barra de progreso (`data-testid="tenant-progress-bar"`).
    - Botón de ajuste de cupo individual para la sucursal (`Edit3`).
  - **Nivel 3 — Logs de Transacciones Inmutables:**
    - Tabla detallada de llamadas API individuales de cada tenant:
      - Usuario (nombre y avatar/iniciales), Caller (`oppyfy_chat`, `recetas_escandallo`, etc.).
      - Modelo LLM con badge distintivo.
      - Tokens de entrada / salida / total (o créditos equivalentes según `viewMode`).
      - Duración en milisegundos (`Clock`).
      - Estado API: Checkmark verde `200` o Cruz roja de error con tooltip del mensaje de excepción.
      - Costo estimado unitario en USD.
- [x] **6.2** Integración Obligatoria del Paginador Canónico (`TablePagination`):
  - Integrar [`TablePagination`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/shared/components/ui/TablePagination.tsx) al pie de la consola FinOps:
    - Opciones de tamaño de página: `pageSizeOptions={[15, 30, 50, 100]}`.
    - Conteo exacto y etiqueta `itemLabel="registros de consumo"`.
    - Navegación elíptica completa y scroll suave al cambiar de página.
- [x] **6.3** Modales Interactivos de Ajuste de Cupos:
  - **Modal de Cupo de Holding:** Ajuste de cuota mensual, validación contra negativos y selección del modo de bolsa (`shared`: compartida vs `per_tenant`: asignación fija).
  - **Modal de Cupo de Tenant:** Ajuste de cupo específico para un restaurante o local individual con validación contra valores negativos y spinner `Loader2`.
  - 20/20 tests passing en `TokenConsumptionPage.test.tsx` (total 62/62 en la suite `platform-admin`).

---

### [x] FASE 7: Integración con Navegación, Rutas del `router.tsx` y Sidebar de Administración — COMPLETADA
- [x] **7.1** Conexión de Rutas en `oppytec-frontend/src/app/router.tsx`:
  - Conectar `/admin/plans` directamente a [`PlansPage.tsx`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/features/platform-admin/plans/PlansPage.tsx).
  - Conectar `/admin/token-consumption` directamente a [`TokenConsumptionPage.tsx`](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code2/oppytec-frontend/src/features/platform-admin/tokens/TokenConsumptionPage.tsx), sustituyendo el `AdminPlaceholderView`.
- [x] **7.2** Menú de Navegación en `AdminSidebar.tsx`:
  - Verificar y asegurar que los ítems *"Planes Comerciales"* (`Layers`) y *"Consumo de Tokens IA"* (`Coins` / `Cpu`) cuenten con enlace activo, estado visual seleccionado y badges informativos (`SaaS` y `FinOps`).
- [x] **7.3** Exportaciones Limpias:
  - Centralizar exportaciones en `oppytec-frontend/src/features/platform-admin/index.tsx`.
  - 8/8 tests passing en `AdminNavigation.test.tsx` (total 70/70 en la suite `platform-admin`).

---

### [x] FASE 8: Capas Cruzadas, i18n, FX, Observabilidad, Testing 5D & E2E — COMPLETADA
- [x] **8.1** Cobertura de Internacionalización (i18n 100% `es`/`en`):
  - Enriquecer `oppytec-frontend/src/shared/i18n/locales/es/platform_admin.json` y `locales/en/platform_admin.json`:
    - Claves completas para el conversor SaaS, métricas de márgenes, tarjetas de planes, modales y advertencias.
    - Claves para la consola FinOps, KPIs, toggle dual, acordeón jerárquico y modales de ajuste de cupos.
    - 0 textos en duro en vistas JSX (`PlansPage.tsx` y `TokenConsumptionPage.tsx` 100% integrados con `useTranslation`).
- [x] **8.2** Multi-Moneda FX con Precisión `Decimal`:
  - Conversión dinámica de costos de API en USD a moneda local (CLP) usando `useCurrencyFormatter` y `fx_service.py` con el tipo de cambio oficial del BCCh.
  - Cero uso de `float` en backend y frontend para costos y balances.
- [x] **8.3** Observabilidad OpenTelemetry & Sentry:
  - Spans OpenTelemetry en operaciones administrativas: `platform_admin.plans.upsert`, `platform_admin.plans.delete`, `platform_admin.policy.update`, `platform_admin.tokens.quota_adjust`.
  - Captura en Sentry ante fallos de sincronización de política SaaS o desbordamiento de cuota.
- [x] **8.4** Suite de Pruebas Automatizadas 5D:
  - **Backend (Pytest):** 39/39 pruebas aprobadas (CRUD de planes, restricciones de clientes activos, política de conversión, agregación jerárquica de tokens y observabilidad OTel).
  - **Frontend (Vitest):** 70/70 pruebas unitarias aprobadas en `src/features/platform-admin/` (`PlansPage.test.tsx`, `TokenConsumptionPage.test.tsx`, `platformAdminHooks.test.ts`, `AdminNavigation.test.tsx`, `AdminManagementViews.test.tsx`).
  - **TypeScript:** `npm --prefix oppytec-frontend run typecheck` $\rightarrow$ **0 errores**.
- [x] **8.5** Sincronización del Grafo AST y Verificación de Calidad:
  - Ejecutar `python scripts/harness.py sync-graph` para indexar los nuevos modelos, endpoints y componentes en `docs/architecture/graphify/graph.json` (95 nodos, 116 aristas).
  - Ejecutar `python scripts/harness.py verify-evals` para validar el 100% de cumplimiento de rúbricas.

---

## 🏆 Certificación de Cierre — Quality Gate 5D

| Dimensión de Calidad | Criterio de Verificación | Resultado Esperado | Certificación |
|---|---|---|---|
| **D1: Dominio & Lógica** | Agregación FinOps exacta, conversión determinista con `Decimal`, validación de planes activos | 100% Pytest OK (39/39) | [x] CERTIFICADO |
| **D2: Contratos & Tipos** | DTOs Pydantic v2 en FastAPI, RFC 7807 ProblemDetails, tipado estricto TS en hooks y componentes | 0 Errores TS | [x] CERTIFICADO |
| **D3: Componentes & Hooks** | Renderizado del conversor SaaS colapsable, catálogo de planes, consola FinOps y acordeón jerárquico | 100% Vitest OK (70/70) | [x] CERTIFICADO |
| **D4: Trazabilidad & Métricas** | Spans OpenTelemetry (`platform_admin.plans.*`, `platform_admin.tokens.*`) y telemetría de cuotas | OTel Spans Verificados | [x] CERTIFICADO |
| **D5: Multi-Tenant & RBAC** | Aislamiento SuperUser, control de 3 niveles (`platform_admin.*`), emisión WebSocket zero-polling | Guardias RBAC Validadas | [x] CERTIFICADO |

---

## 🎯 Protocolo de Ejecución y Traspaso entre Agentes

| Etapa | Agente Líder | Tareas a Cargo | Entregables Principales |
| :---: | :--- | :--- | :--- |
| **Etapa 1** | `02-software-architect` & `03-database-alembic` | FASE 1: DDL `public`, Alembic `0007`, Modelos | Modelos SQLAlchemy, Migración `0007`, Value Objects |
| **Etapa 2** | `04-backend-senior-dev` | FASE 2: Endpoints REST FastAPI y Agregación FinOps | Routers `/platform-admin/plans`, `/policy`, `/token-consumption` |
| **Etapa 2** | `05-frontend-senior-dev` | FASE 3, 4, 5, 6, 7: UI React 19, Hooks, Acordeón y Paginador | `PlansPage.tsx`, `TokenConsumptionPage.tsx`, Hooks y Paginación |
| **Etapa 3** | `07-i18n-fx` & `08-environments-observability` | FASE 8: i18n 100%, Multi-Moneda FX, OpenTelemetry | `platform_admin.json` (es/en), Trazas OTel, Sentry |
| **Etapa 4** | `09-qa-test` & `10-security-redteam` | FASE 8: Testing 5D, SAST/DAST, Paridad Matemática | Tests Pytest + Vitest, Auditoría Kali, 0 Vulnerabilidades |
| **Etapa 4** | `11-git-arbiter` & `12-tech-writer` | Cierre: Merge Train, OpenSpec, Graphify & Archify | Smart Merge, Bóvedas OpenSpec, Grafo AST sincronizado |
| **Etapa 5** | `13-browser-e2e-playwright` | FASE 8: Certificación E2E en Navegador Real (Desacoplada) | Reporte Playwright HTML, Video y Traza de Navegación |

> **Nota Final:** Toda modificación de código debe ejecutarse previa consulta de Graphify (`python scripts/harness.py nav "<símbolo>"`) y concluir con la sincronización obligatoria `python scripts/harness.py sync-graph`.
