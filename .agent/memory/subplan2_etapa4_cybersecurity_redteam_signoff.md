# Dictamen Oficial de Ciberseguridad y Red Team (Etapa 4 - Sub-Plan 2)
**Dominio**: Switch Maestro de Mock Data, Presets Gastronómicos Multi-Tenant y Factory Reset  
**Auditor**: Agente 10 (Auditor de Ciberseguridad y Red Team)  
**Fecha de Auditoría**: 2026-11-05  
**Estado de Veto**: **APROBADO SIN RESERVAS (VETO NO EJERCIDO)**

---

## 1. Alcance y Superficie de Ataque Auditada

Se realizó una auditoría de seguridad ofensiva (Red Team) y defensiva sobre los nuevos componentes y endpoints del Sub-Plan 2:
- **Endpoints Auditados**:
  - `GET /api/v1/platform-admin/sandbox/mock-data/presets` y `/api/v1/platform-admin/sandbox/presets`
  - `GET /api/v1/platform-admin/sandbox/mock-data/presets/{preset_id}` y `/api/v1/platform-admin/sandbox/presets/{preset_id}`
  - `POST /api/v1/platform-admin/sandbox/mock-data/reset`
- **Componentes y Guardias**:
  - `oppytec-backend/src/modules/tenancy/presentation/sandbox_router.py`
  - `oppytec-backend/src/modules/tenancy/application/sandbox_service.py`
  - `oppytec-backend/src/core/guards/rbac_dependencies.py`
  - `oppytec-backend/src/core/exceptions.py`
- **Suites de Verificación Ejecutadas**:
  - `oppytec-backend/tests/unit/test_platform_admin_sandbox.py` (23 tests, 100% OK)
  - `oppytec-backend/tests/unit/test_sandbox_observability_and_environments.py` (16 tests, 100% OK)
  - Suites Vitest en frontend: 4 archivos, 66 tests (100% OK)

---

## 2. Matriz de Vectores de Ataque Auditados

| Vector / Control | Evaluación Red Team | Comportamiento Observado / Código RFC 7807 | Estado |
|---|---|---|---|
| **V1. Anti-IDOR y Autorización Global (Tenant Token Probe)** | Intento de consultar o resetear presets usando un token de inquilino regular (`is_global_staff=False`). | Interceptado de inmediato por `RequireGlobalPermission`. Rechazado con `HTTP 403 Forbidden` (`GLOBAL_STAFF_REQUIRED`). Ningún dato de configuración global ni capacidad de reset es accesible para tenants. | **COMPLIANT** |
| **V2. Escalamiento de Privilegios RBAC (Read-Only to Destructive)** | Intento de invocar `POST /mock-data/reset` con token global de solo lectura (`platform_admin.sandbox.access`). | Rechazado con `HTTP 403 Forbidden` (`INSUFFICIENT_PERMISSIONS`). El endpoint de reset exige estrictamente `platform_admin.sandbox.manage`. | **COMPLIANT** |
| **V3. Guardrail Fail-Fast en Producción** | Intento de invocar `POST /mock-data/reset` en entorno canónico `production`. | Bloqueo absoluto e incondicional en primera instancia mediante `_enforce_sandbox_environment_guard`. Retorna `HTTP 403 Forbidden` (`PRODUCTION_MUTATION_FORBIDDEN`). Cero escritura en base de datos productiva. | **COMPLIANT** |
| **V4. Guardrail en Staging** | Intento de invocar `POST /mock-data/reset` en `staging` sin confirmación explícita de staging. | Rechazado con `HTTP 400 Bad Request` (`STAGING_CONFIRMATION_REQUIRED`). Exige `confirmStagingAction=true` o cabecera `X-Sandbox-Confirm-Staging: true`. | **COMPLIANT** |
| **V5. Aislamiento Estricto de Esquemas (Anti-Contaminación)** | Intento de resetear `public`, o esquemas no autorizados fuera del patrón sandbox. | Rechazado con `HTTP 400 Bad Request` (`ISOLATED_SCHEMA_REQUIRED`). Solo permite esquemas que comiencen con `tenant_qa_`, `tenant_sandbox_`, `tenant_test_`, `tenant_integration_` o los canónicos aislados autorizados. | **COMPLIANT** |
| **V6. Requerimiento de Confirmación de Reset** | Intento de invocar `POST /mock-data/reset` omitiendo o enviando `confirmReset=false`. | Rechazado con `HTTP 400 Bad Request` (`RESET_CONFIRMATION_REQUIRED`). Requiere explícitamente confirmación de reseteo. | **COMPLIANT** |
| **V7. Inmutabilidad de Auditoría AI / FinOps** | Verificación de que Factory Reset no altere ni purgue `public.llm_request_logs` ni registros de trazabilidad. | Auditado en `test_factory_reset_preserves_public_llm_request_logs`: la purga solo impacta entidades sintéticas del esquema tenant aislado; las tablas de auditoría append-only y finops permanecen intactas e inmutables. | **COMPLIANT** |
| **V8. Anti-Reward-Hacking & Integridad de Evals** | Inspección de diffs en `scripts/harness.py`, `rbac_dependencies.py`, `exceptions.py` y archivos de test. | No hay relajación ni bypass de aserciones de prueba. `scripts/harness.py` únicamente indexó nuevos nodos en Graphify. Se agregaron aserciones más estrictas para verificar denegación a tokens de inquilinos en reset y preset ID. | **COMPLIANT** |

---

## 3. Dictamen Oficial de Ciberseguridad y Decisión de Veto

- **Dictamen**: **CERTIFICACIÓN DE SEGURIDAD APROBADA (SIGN-OFF COMPLETO)**.
- **Poder de Veto**: **NO EJERCIDO**.
- **Observaciones**:
  1. Todos los endpoints cuentan con validación estricta de autorización global y RBAC de 3 niveles.
  2. Los guardrails de entorno son a prueba de fallos (Fail-Fast) e impiden cualquier daño accidental o malicioso en producción o staging.
  3. No se detectó ninguna vulnerabilidad de IDOR, inyección ni bypass de autenticación.
- **Autorización de Traspaso**: Habilitado el paso a la Etapa 5 (Documentación OpenSpec, Graphify y Cierre) del Sub-Plan 2.
