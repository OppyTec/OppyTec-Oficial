# ADR-006: RBAC Jerárquico Dual en 3 Niveles, Gestión de Cupos con `Soft-Delete` y Auditoría Forense

- **Estado:** Aprobado e Inmutable
- **Fecha:** 2026-10-19
- **Estrategia de Referencia:** `.agent/estrategias/estrategia_rbac_y_auditoria_001.md` / `.agent/skills/rbac-permission-guard/SKILL.md`

---

## 1. Contexto

En `OppyTec-Legacy`, el rol `admin` poseía privilegios casi idénticos al propietario del negocio, no existía separación formal entre el personal interno de OppyTec y los empleados de los clientes, y si un trabajador operaba en dos locales del mismo dueño había que duplicar su usuario. Además, al desvincular a un empleado se perdía la trazabilidad histórica o no se liberaba inmediatamente su cupo contratado.

## 2. Decisión

Establecer una arquitectura de **Control de Acceso Basado en Roles (RBAC) Dual y Jerárquico en 3 Niveles (`<modulo>.<submodulo>.<funcion>`)** junto con **Cupos Comerciales por Plan y Auditoría Forense Inmutable**:

1. **Separación Estricta de Dos Áreas RBAC del ERP:**
   - **Área 1 — Trabajadores de OppyTec (`public`):** Gobernada por el **SuperUser Génesis (`oppytec.admin`, Rank 0)** y roles de plataforma (`platform_admin`, `support_agent`, `billing_ops`). **Exentos de límite de cupos.**
   - **Área 2 — Trabajadores del Cliente (`Holding` / `tenant_*`):** Gobernada por el Propietario del Holding (`holding_owner`, Rank 10) con acceso transversal multi-sucursal sin duplicar cuentas, Administrador de Tenant (`tenant_admin`, Rank 20) y roles operativos personalizables (`Rank 30+`).
2. **Regla Anti-Escalamiento de Privilegios:** Ningún usuario puede crear, modificar ni asignar un rol cuyo `hierarchy_rank` sea menor o igual al suyo propio (`actor.rank < target.rank`), ni otorgar permisos que él mismo no posea.
3. **Gestión de Cupos y `Soft-Delete` con Kill-Switch en Redis:**
   - Solo los usuarios con `is_active = True` y `deleted_at IS NULL` consumen cupo del plan contratado (`max_users_quota`).
   - Al aplicar `soft-delete` a un trabajador, en la misma transacción se revoca su sesión activa mediante un *Kill-Switch* en Redis (`revoked_sessions:{env}:{user_id}`), se conserva intacto el historial forense de sus operaciones pasadas y **se libera su cupo en el acto**.
4. **Permisos Temporales JIT (*Just-In-Time*):** Todo acceso de soporte técnico o delegación temporal requiere expiración automática (`expires_at`) y motivo obligatorio.

## 3. Consecuencias

- **Positivas:**
  - Trazabilidad contable y forense inmutable (`AuditService` con `before_state` y `after_state` redactando PII/secretos).
  - Control comercial exacto de asientos activos por suscripción sin fricción operativa para el dueño del restaurante.
- **Negativas / Trade-offs:**
  - Todo endpoint de la API debe declarar explícitamente su dependencia `require_permission("<modulo>.<submodulo>.<funcion>")`.

## 4. Verificación Determinista en Tests

- **Suite de Caja Blanca y Red Team:** `oppytec-backend/tests/architecture/test_rbac_and_audit_coverage.py`, `test_02_rbac_privilege_escalation.py` y `test_03_user_quota_bypass_and_soft_delete.py`.
- **Invariante Verificada:** El 100% de las rutas FastAPI (salvo `/health` y login público) tienen guardia RBAC verificada por AST; ataques concurrentes de creación de usuarios nunca superan `max_users_quota`.
