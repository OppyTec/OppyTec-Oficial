---
spec_id: ENG-TENANCY-AND-PLANS
title: "Empresas, Restaurantes, Planes y Cuotas Paramétricas"
audience: engineering_internal
domain_module: tenancy
paired_spec: specs/business-domain/tenancy-and-plans.business.spec.md
jev_system1_evaluation: "No (Jev.boolean, umbral 0.90)"
last_verified_phase: "Plan Maestro Admin"
---

# Empresas, Restaurantes, Planes y Cuotas Paramétricas — Especificación de Ingeniería

## 1. Contrato de Datos y Persistencia Relacional

### 1.1 Jerarquía Estricta en Esquema `public`
La arquitectura de multi-tenancy se organiza jerárquicamente en el esquema de control `public`:
- `public.holdings`: Agrupación corporativa con `holding_id` (UUIDv4 o slug corporativo), `name`, `plan_slug`, `max_active_users`, `max_storage_mb`, y columnas de excepción `custom_max_products_override`, `custom_max_suppliers_override`, `custom_max_recipes_override`, `custom_max_combos_override`.
- `public.legal_entities`: Razón social con `entity_id`, `holding_id` (FK), `tax_id` (RUT con validación módulo 11), `legal_name`, `legal_address`.
- `public.tenants`: Local gastronómico con `tenant_id`, `holding_id` (FK), `legal_entity_id` (FK `UNIQUE`, forzando cardinalidad 1:1 estricta), `slug`, `schema_name` (`tenant_<slug>`), `display_name`, `base_currency` (`CLP`, `USD`, `EUR`, `BRL`), `enabled_modules` (JSON array de strings), y columnas de excepción `custom_max_users_override`, `custom_max_products_override`, `custom_max_suppliers_override`, `custom_max_recipes_override`, `custom_max_combos_override`, `custom_storage_mb_override`.
- `public.system_plans`: Planes comerciales globales con `slug` (`PK`), `name`, `max_active_users`, `max_products`, `max_suppliers`, `max_recipes`, `max_combos`, `max_storage_mb`, `included_modules` (JSON array), `price_clp`, `price_usd`, `price_eur`, `price_brl` en precisión `Numeric(18, 4)`.

### 1.2 Migración Correlativa de Alembic
- La migración `alembic/versions/0003_public_plans_quotas_and_tenant_capacity_overrides.py` extiende las tablas `system_plans`, `holdings` y `tenants` con las cuotas paramétricas y overrides correspondientes, manteniendo compatibilidad hacia atrás con valores por defecto.

## 2. Invariantes Arquitectónicas

1. **Aislamiento Multi-Schema Físico:** Cada tenant reside en su propio esquema `tenant_<slug>`. Las sesiones se configuran con `SET LOCAL search_path = tenant_<slug>, public` y se resetean incondicionalmente con `RESET search_path` al devolver la conexión al pool.
2. **Cardinalidad 1:1 LegalEntity $\leftrightarrow$ Tenant:** Una razón social pertenece a un único local y viceversa (`UNIQUE(legal_entity_id)`).
3. **Precedencia de Overrides:** El límite efectivo para cualquier recurso se resuelve mediante la función de dominio determinista:
   $$\text{effective\_limit} = \text{tenant\_override} \;\gg\; \text{holding\_override} \;\gg\; \text{plan\_limit}$$
4. **Liberación Inmediata por Soft-Delete:** Para los recursos contables (`users`, `products`, `suppliers`, `recipes`, `combos`), la condición `is_deleted = True` excluye inmediatamente al registro del conteo activo:
   $$\text{active\_count} = \sum_{r \in \text{resources}} [r.\text{is\_deleted} = \text{False}]$$
5. **Alineación con RBAC de 2 Niveles:** La lista `included_modules` del plan filtra de manera determinista los permisos requeridos (`compute_effective_permissions`) evaluando tokens con prefijo de submódulo (`<modulo>.<submodulo>`), permitiendo habilitar funciones puntuales como `operations.consumption_log` bloqueando el resto del módulo.

## 3. Matriz del Semáforo de Salud de Cuotas

El estado de salud de cada una de las 6 cuotas se calcula mediante `compute_quota_health_status`:
- **`NORMAL`:** $\text{percentage} < 80.00\%$
- **`WARNING`:** $80.00\% \le \text{percentage} < 95.00\%$
- **`CRITICAL`:** $95.00\% \le \text{percentage} < 100.00\%$
- **`OVER_QUOTA`:** $\text{effective\_max\_limit} \le 0 \lor \text{active\_count} \ge \text{effective\_max\_limit}$ (Retorna `HTTP 409 Conflict` con código `QuotaExceededError`).

## 4. Endpoints de la API REST de Tenancy y Administración

- `GET /api/v1/tenancy/plans`: Listado de planes comerciales y sus cuotas paramétricas.
- `POST /api/v1/tenancy/plans`: Alta y actualización de planes comerciales con cuotas y tarifas multi-moneda.
- `GET /api/v1/tenancy/holdings`: Listado de Holdings registrados en la plataforma.
- `POST /api/v1/tenancy/holdings`: Creación de Holdings con vinculación de plan y cuotas corporativas.
- `GET /api/v1/tenancy/legal-entities`: Listado de Entidades Legales (RUTs).
- `POST /api/v1/tenancy/legal-entities`: Alta de Entidad Legal vinculada a un Holding.
- `GET /api/v1/tenancy/tenants`: Listado de Tenants con su razón social y estado de módulos.
- `POST /api/v1/tenancy/tenants`: Creación de Tenant con aprovisionamiento de esquema `tenant_<slug>`.
- `PUT /api/v1/tenancy/tenants/{tenant_id}/modules-and-quotas`: Actualización de módulos habilitados y overrides de capacidad.
- `GET /api/v1/tenancy/client-users`: Listado de usuarios del Holding o Tenant con estado de baja lógica.
- `POST /api/v1/tenancy/client-users`: Alta de usuario cliente con verificación estricta de cupo `max_active_users`.
- `POST /api/v1/tenancy/client-users/{user_id}/soft-delete`: Baja lógica con revocación de tokens y liberación inmediata de cupo.
- `POST /api/v1/tenancy/admin/impersonate`: Emisión de token de soporte scoped con trazabilidad en auditoría ("Entrar como Local").
- `GET /api/v1/tenancy/quotas/summary`: Resumen consolidado del estado y semáforo de las 6 cuotas de capacidad del Tenant.
- `GET /api/v1/tenancy/quotas/seats`: Estado detallado de cupos de usuarios y trabajadores en soft-delete.
- `GET /api/v1/tenancy/quotas/storage`: Estado de cuota de almacenamiento Cloudflare R2 en MB y porcentaje.
- `GET /api/v1/tenancy/admin/dashboard-summary`: Métricas y conteos reales para el Shell del Panel Administrador.

## 5. Arquitectura Frontend: 4 Vistas Administrativas, i18n y Guardias RBAC

Las 4 vistas operativas se ubican en `oppytec-frontend/src/features/platform-admin/AdminManagementViews.tsx` y se montan en el enrutador SPA (`/admin/holdings`, `/admin/legal-entities`, `/admin/tenants`, `/admin/client-users`):
1. **`AdminHoldingsView`:** Tabla y modal de creación de Holdings con overrides de capacidad corporativa. Protegida con `platform_admin.holdings.manage`.
2. **`AdminLegalEntitiesView`:** Tabla y modal de sociedades con validación de RUT chileno (módulo 11) y asignación 1:1. Protegida con `platform_admin.legal_entities.manage`.
3. **`AdminTenantsView`:** Tabla y modal de aprovisionamiento con selector interactivo del árbol de módulos SaaS (`SAAS_MODULE_TREE`), botón rápido para los 10 módulos del Plan Básico (`PLAN_BASICO_10_MODULE_SLUGS`) y asignación de base de datos `tenant_<slug>`. Protegida con `platform_admin.tenants.provision`.
4. **`AdminClientUsersView`:** Tabla de usuarios clientes con estado `is_deleted` ("Activo" / "Liberado"), modal de creación con validación de cupo `max_active_users`, botón "Archivar" (soft-delete que libera el cupo inmediatamente) y botón "Entrar" (impersonación de soporte técnico). Protegida con `platform_admin.client_users.manage`.

### Componentes Genéricos de Soporte
- **`DynamicAdminTable` (`oppytec-frontend/src/shared/components/admin/DynamicAdminTable.tsx`):** Tabla con ordenamiento, filtrado en vivo, columnas configurables, soporte de permisos declarativos (`createPermission`, `editPermission`, `deletePermission`) e integración con `translateKey`.
- **`DynamicAdminForm` (`oppytec-frontend/src/shared/components/admin/DynamicAdminForm.tsx`):** Renderizador declarativo de formularios con soporte de tipos `text`, `number`, `select`, `multiselect`, `checkbox` y botón de submit accesible (`${testId}-submit-btn`).
- **`QuotaProgressIndicator` (`oppytec-frontend/src/shared/components/ui/QuotaProgressIndicator.tsx`):** Semáforo visual reactivo de 4 estados (NORMAL, WARNING, CRITICAL, OVER_QUOTA).

### Paridad i18n 1:1
- Todas las cadenas visibles de las 4 vistas residen en `locales/es/platform_admin.json` y `locales/en/platform_admin.json` bajo las secciones `holdings`, `legal_entities`, `tenants_view`, `client_users` y `table_common`, garantizando 0 cadenas hardcodeadas en JSX.

## 6. Evaluación JEV Sistema 1

jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **No**.
- Primitiva: `Jev.boolean`
- Umbral de confianza: `0.90` (camino determinista obligatorio).
- Justificación: El aprovisionamiento de tenants, entidades legales, planes comerciales y el cálculo de semáforo de cuotas son operaciones puramente aritméticas y de seguridad transaccional (`Decimal` y locks de base de datos) que no admiten variabilidad probabilística de modelos de lenguaje.

## 7. Pruebas y Verificación Co-Creación 1:1

- `oppytec-frontend/src/features/platform-admin/AdminManagementViews.test.tsx`:
  - Alta y persistencia de Holdings en tabla interactiva.
  - Registro de Entidades Legales con validación de RUT chileno.
  - Aprovisionamiento de Tenants con selector del árbol de módulos SaaS y Plan Básico.
  - Soft-delete (archivo) de usuarios clientes con liberación inmediata de cupo y cambio visual de estado.
  - Aplicación estricta de veto RBAC `<Can>` ocultando botones de mutación y soporte a usuarios sin permisos `platform_admin.*`.
- `oppytec-backend/tests/unit/test_tenancy_admin_audit_and_redis_killswitch.py`:
  - Exigencia de permisos RBAC de 3 niveles (`platform_admin.holdings.manage`, etc.) en endpoints de tenancy.
  - Revocación de tokens en Redis y liberación de asientos tras soft-delete.
  - Registro forense en auditoría de la acción de impersonación ("Entrar como Local").
- `oppytec-backend/tests/unit/test_plan_basico_quotas_and_admin_provisioning.py`:
  - `test_two_level_submodule_rbac_ceiling_for_plan_basico`: Aislamiento RBAC a nivel de submódulo para Plan Básico.
  - `test_multi_resource_capacity_quotas_semaphore_and_soft_delete_release`: Semáforo 80/95/100%, precedencia de overrides y liberación inmediata por soft-delete.
  - `test_admin_provisioning_plans_holdings_tenants_client_users_and_impersonation`: Flujo completo E2E de aprovisionamiento en `platform-admin`, alta de planes, holdings, RUTs, tenants, usuarios clientes y token de soporte de impersonación.
- `oppytec-backend/tests/architecture/test_alembic_integrity.py`: Validación de la cadena correlativa lineal con la migración `0003`.
- `oppytec-frontend/src/App.test.tsx`: Validación de componentes UI `AdminPlansView`, `AdminHoldingsView`, `AdminLegalEntitiesView`, `AdminTenantsView`, `AdminClientUsersView` y `QuotaProgressIndicator`.
