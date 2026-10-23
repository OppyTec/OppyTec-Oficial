# Reporte de Traspaso (`Handover`) — Agente 04: Programador Senior Backend, RBAC Dual y Almacenamiento R2

- **Fecha UTC:** 2026-10-22T20:40:00Z
- **Fase:** Auditoría del Plan Maestro — Módulo Tenancy, Cuotas Paramétricas, RBAC 3-Niveles y Kill-Switch Redis
- **Rama / Worktree:** `master`

## 1. Completed (Qué se auditó y corrigió)
1. **Auditoría de Schemas y Endpoints REST en `oppytec-backend/src/modules/tenancy/presentation/`:**
   - Verificados todos los esquemas `*Request`: `HoldingCreateRequest`, `TenantCreateRequest`, `TenantModulesAndQuotasUpdateRequest`, `SystemPlanUpsertRequest`, `ClientUserCreateRequest`, `AdminImpersonateRequest`, `LegalEntityCreateRequest`.
   - Se certificó que el 100% implementan `model_config = ConfigDict(extra="forbid")`, rechazando parámetros no declarados con HTTP 422 (`extra_forbidden`).
2. **Aplicación Estricta de RBAC de 3 Niveles (`<modulo>.<submodulo>.<funcion>`):**
   - Todos los endpoints administrativos aplican `RequireGlobalPermission`:
     - `tenancy.plans.read` en `GET /api/v1/tenancy/plans`
     - `tenancy.plans.manage` en `POST /api/v1/tenancy/plans`
     - `tenancy.holdings.create` en `POST /api/v1/tenancy/holdings`
     - `tenancy.holdings.read` en `GET /api/v1/tenancy/holdings`
     - `tenancy.tenants.provision` en `POST /api/v1/tenancy/tenants` y `PUT /api/v1/tenancy/tenants/{tenant_id}/modules-and-quotas`
     - `tenancy.tenants.read` en `GET /api/v1/tenancy/tenants`
     - `tenancy.legal_entities.create` en `POST /api/v1/tenancy/legal-entities`
     - `tenancy.legal_entities.read` en `GET /api/v1/tenancy/legal-entities`
     - `tenancy.client_users.read` en `GET /api/v1/tenancy/client-users`
     - `tenancy.client_users.create` en `POST /api/v1/tenancy/client-users`
     - `tenancy.client_users.manage` en `POST /api/v1/tenancy/client-users/{user_id}/soft-delete` y `POST /api/v1/tenancy/client-users/{user_id}/restore`
     - `tenancy.tenants.impersonate` en `POST /api/v1/tenancy/admin/impersonate`
     - `tenancy.dashboard.read` en `GET /api/v1/tenancy/dashboard/summary`
   - Los endpoints de consulta de cuotas de sucursal aplican `RequireTenantPermission`:
     - `tenancy.quotas.read` en `GET /api/v1/tenancy/quotas/seats` y `GET /api/v1/tenancy/quotas/summary`
     - `tenancy.storage_quotas.read` en `GET /api/v1/tenancy/quotas/storage`
3. **Cero Float y Precisión Decimal en Cuotas e Impersonación:**
   - Se eliminaron los literales `float` (`100.0` -> `Decimal("100.00")`) en `record_quota_semaphore_metric` dentro de `router.py`.
   - Se incorporó `usage_percentage: Decimal = Field(default=Decimal("0.00"))` en `SeatQuotaStatusResponse` y `StorageQuotaStatusResponse`, garantizando paridad con `ResourceQuotaItemResponse`.
   - El endpoint `/api/v1/tenancy/admin/impersonate` emite tokens válidos con `hierarchy_rank=0`, `is_superuser_god=True`, `schema_name` exacto y trazabilidad forense.
4. **Soft-Delete Inmediato con Kill-Switch Redis:**
   - En `POST /api/v1/tenancy/client-users/{user_id}/soft-delete`, se liberan cupos en el acto (`is_deleted=True`), se bloquea auto-eliminación (`cannot_self_delete` -> HTTP 403), se revoca en memoria `< 1ms` (`revoke_session_token`) y se persiste asíncronamente en Redis (`session:killswitch:client:user_{user_id}`) mediante `SessionKillSwitchService(get_redis_client())` con fallback seguro de `RedisCircuitBreaker`.
   - En `POST /api/v1/tenancy/client-users/{user_id}/restore`, se valida que existan cupos libres antes de restaurar y se limpian las marcas de revocación en memoria y Redis (`clear_revocation_on_restore`).
5. **Verificación y Pruebas Automatizadas:**
   - Creada suite unitaria `oppytec-backend/tests/unit/test_tenancy_admin_audit_and_redis_killswitch.py` (4/4 tests pasando).
   - Suite completa de 192 tests pasando al 100% (`pytest tests/` en 8.28s).
   - Calidad de código: `ruff check` 0 errores, `mypy src/modules/tenancy tests/unit/test_tenancy_admin_audit_and_redis_killswitch.py` 0 errores en 13 archivos tipados estrictamente.

## 2. Friction & Failures (Qué cuidar)
- En `get_storage_quota_status_endpoint`, `plan_max_storage_mb=1024` es el contrato esperado por las pruebas E2E de aprovisionamiento de sucursal (`test_e2e_01_genesis_holding_and_tenant_onboarding.py`). Los overrides deben pasar mediante `holding_storage_override_mb` o `tenant_storage_override_mb`.
- En `TenantCapacityQuotaService`, se definió el alias `evaluate = evaluate_resource` para compatibilidad de interfaz fluida entre servicios y tests.

## 3. Next Exact Action (Siguiente paso exacto)
- Notificar al Orquestador (Agente 01) la superación con éxito de la auditoría de Tenancy y Cuotas del Plan Maestro con 192/192 tests en verde.
