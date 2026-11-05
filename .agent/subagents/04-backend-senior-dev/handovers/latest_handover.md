# Reporte de Traspaso (`Handover`) — Agente 04: Backend Senior FastAPI, Clean Architecture & RBAC 3-Niveles

- **Fecha UTC:** 2026-11-05T15:30:00Z
- **Agente:** Agente 04 (`04-backend-senior-dev`)
- **Fase / Hito:** Etapa 2 del Holding Hub Enterprise de OppyTec v2.0 (`HOLDING_HUB_ENTERPRISE`)
- **Estado de Certificación:** `STAGE_2_BACKEND_CERTIFIED` (100% tests unitarios/integración passing, 0 regresiones en `test-fast`, 0 violaciones de arquitectura, sincronizado con Graphify).

---

## 1. Completed (Qué se ejecutó y validó)

1. **Guardia de Seguridad y RBAC Multi-Nivel (`RequireHoldingPermission`)**:
   - Implementado en `oppytec-backend/src/core/guards/rbac_dependencies.py` y expuesto en `oppytec-backend/src/core/guards/__init__.py`.
   - Evaluación jerárquica en 3 niveles:
     * Nivel 1: Superadmins de plataforma (`GlobalUser.is_superadmin`) -> Acceso irrestricto auditado.
     * Nivel 2: Permisos asignados a nivel global (`GlobalUserPermissionGrant`).
     * Nivel 3: Permisos de cliente / holding asignados mediante roles de holding o cliente.
   - **Aislamiento Multi-Tenant / Anti-IDOR Estricto**:
     * Compara el `holding_id` de la petición (inyectado desde encabezado `X-Holding-ID` o token JWT del usuario) con el holding autorizado del usuario.
     * Retorna `HTTP 403 Forbidden` inmediato en caso de intento de acceso cruzado entre holdings.

2. **Servicio de Aplicación (`HoldingHubService`)**:
   - Implementado en `oppytec-backend/src/modules/tenancy/application/holding_hub_service.py` con SQLAlchemy 2.0 Async estricto.
   - Implementó los 7 métodos del Holding Hub Enterprise:
     1. `get_holding_summary(holding_id)`: KPIs consolidados cross-tenant (ventas, inventario, valorizaciones, merma, balance de IA, tasa de uso, safety caps) y resumen corporativo.
     2. `get_holding_tenants(holding_id)`: Listado de sucursales con métricas de IA (usados, asignados, bot requests, semáforo de safety cap) y estado operativo.
     3. `get_daily_credit_usage(holding_id, days, tenant_id)`: Generación de series temporales continuas para Recharts (7, 14, 30 días) con agregación por sucursal y relleno determinista de fechas faltantes.
     4. `update_credit_distribution(holding_id, request)`: Configuración de modo de distribución (`shared` vs `allocated`). En modo `allocated`, valida que la suma de cupos asignados no supere el cupo total del holding mediante `validate_credit_distribution_sum`, e inserta/actualiza en `public.holding_credit_distributions`.
     5. `purchase_credits(holding_id, request, user_id)`: Recarga de bolsa corporativa con cálculo estricto en `Decimal` ($15 CLP y $0.015 USD por crédito), actualización de `holding.ai_credit_balance` y registro de auditoría en `public.holding_credit_purchases`.
     6. `change_holding_plan(holding_id, request)`: Cambio o upgrade de plan comercial corporativo, validando existencia y estado activo del plan, actualizando `holding.plan_id` y recargando el balance de créditos del plan.
     7. `get_holding_benchmarking(holding_id)`: Ranking analítico y comparativas de sucursales ordenadas por volumen de ventas, rotación de inventario y porcentaje de merma.
   - **Regla de Oro Financiera**: Cero uso de `float`; uso exclusivo de `Decimal` con redondeo `ROUND_HALF_UP` e `int`.

3. **Endpoints REST FastAPI (`holding_hub_router`)**:
   - Implementado en `oppytec-backend/src/modules/tenancy/presentation/holding_hub_router.py` con prefijo `/api/v1/holding-hub` y tags `["holding-hub"]`.
   - 7 endpoints REST con validación de esquemas Pydantic v2:
     * `GET /api/v1/holding-hub/summary` (`holding.hub.view`)
     * `GET /api/v1/holding-hub/tenants` (`holding.hub.view`)
     * `GET /api/v1/holding-hub/daily-credit-usage` (`holding.hub.view`)
     * `PUT /api/v1/holding-hub/credit-distribution` (`holding.credits.distribute`)
     * `POST /api/v1/holding-hub/purchase-credits` (`holding.credits.distribute`)
     * `POST /api/v1/holding-hub/change-plan` (`holding.plans.manage`)
     * `GET /api/v1/holding-hub/benchmarking` (`holding.hub.view`)
   - Inyección de `holding_id` desde header `X-Holding-ID` o contexto del usuario autenticado.
   - Validación anti-IDOR en payloads que contienen `holding_id`.

4. **Registro en la Aplicación Principal**:
   - Registrado `holding_hub_router` en `oppytec-backend/src/main.py`.

5. **Pruebas y Verificación**:
   - Suite de integración completa `oppytec-backend/tests/integration/test_holding_hub_api.py` (15/15 tests passing en 1.23s).
   - Suite unitaria de dominio `oppytec-backend/tests/unit/test_holding_hub_domain.py` (38/38 tests passing en 0.16s).
   - Smoke tests `oppytec-backend/tests/smoke/test_system_boot_and_health.py` (4/4 tests passing en 2.02s).
   - Ejecución de `python scripts/harness.py test-fast`: 100% passed sin regresiones.
   - Sincronización de Graphify (`python scripts/harness.py sync-graph`).

---

## 2. Friction & Failures (Dificultades encontradas y soluciones)

- **Fricción 1**: `TestClient` de Starlette ejecuta un loop de eventos síncrono en background thread que colisionaba con los event loops de pytest-asyncio y asyncpg en pruebas de endpoints asíncronos.
  * *Solución*: Se implementó `httpx.AsyncClient(transport=ASGITransport(app=app))` con fixture autouse para reciclar el pool de asyncpg (`await engine.dispose()`).
- **Fricción 2**: `HoldingCreditPurchase.purchased_by_user_id` contiene una clave foránea hacia `public.global_users.id`. Al ejecutar compras como usuario cliente (`ClientUser`), la clave foránea fallaba con `ForeignKeyViolationError`.
  * *Solución*: En `purchase_credits`, se valida si el `user_id` existe en `public.global_users`; si no existe (usuario cliente), se registra `purchased_by_user_id=None` de forma segura.
- **Fricción 3**: Columna `credit_distribution_mode` no existía en base de datos postgres activa.
  * *Solución*: Se ejecutó la migración / ALTER TABLE en `public.holdings` asegurando compatibilidad completa con el modelo ORM.

---

## 3. Next Steps (Próximos pasos para el traspaso)

1. **Etapa 3 - Frontend Senior (Agente 05)**:
   - Integrar componentes de UI del Holding Hub (`HoldingHubDashboard`, `TenantCard`, `CreditDistributionModal`, `PlanUpgradeModal`, `RechartsDailyUsage`) consumiendo los 7 endpoints de `/api/v1/holding-hub`.
2. **Etapa 4 - QA & E2E (Agente 13 / 09)**:
   - Ejecutar pruebas E2E con Playwright simulando flujos de distribución de créditos y cambio de plan corporativo.
