---
spec_id: ENG-RBAC-QUOTAS-AND-AUDIT
title: "Permisos, Control Granular de Módulos, Cupos de Usuarios y Auditoría"
audience: engineering_internal
domain_module: identity
paired_spec: specs/business-domain/rbac-quotas-and-audit.business.spec.md
jev_system1_evaluation: "Sí (Jev.score, umbral 0.85)"
last_verified_phase: "Plan Maestro Admin"
---

# Permisos, Control Granular de Módulos, Cupos de Usuarios y Auditoría — Especificación de Ingeniería

## 1. Contrato Técnico y Ecuación de Permisos Efectivos

### 1.1 Ecuación de Permisos Efectivos con Soporte de Submódulos
El conjunto de permisos efectivos para un usuario en el contexto de su Tenant y Plan se calcula formalmente como:
$$P_{\text{efectivo}} = M_{\text{Plan}} \cap \Big( (P_{\text{Rol}} \cup P_{\text{Temporal}}) \setminus P_{\text{Deny}} \Big)$$

Donde cada permiso posee la estructura jerárquica de 3 niveles:
$$\langle\text{modulo}\rangle.\langle\text{submodulo}\rangle.\langle\text{funcion}\rangle$$

Para respetar planes con habilitación parcial de submódulos (como el Plan Básico con `operations.consumption_log`), el evaluador extrae el prefijo de submódulo (`extract_permission_submodule_prefix`) permitiendo machear tokens tanto a nivel de raíz de módulo (`catalog`) como a nivel granular (`operations.consumption_log`).

### 1.2 Leyes de Rango Jerárquico (`hierarchy_rank`)
Cada rol posee un entero `hierarchy_rank` donde un valor numérico menor denota mayor poder de decisión:
1. **Ley de No-Operabilidad:** Un actor con rango $R_A$ no puede crear, modificar, suspender ni eliminar a un usuario con rango $R_U \le R_A$.
2. **Ley de No-Escalamiento:** Un actor con rango $R_A$ no puede asignar a ningún usuario un rol con rango $R_{\text{nuevo}} < R_A$.
3. **Inviolabilidad de Propietario:** El rol `propietario` (`hierarchy_rank = 0`) es el techo de autoridad dentro del Tenant y sólo puede ser administrado por un SuperUser Global (`public.global_users`).

### 1.3 Gobernanza de Cupos de Asientos y Soft-Delete
- El techo de usuarios activos se resuelve deterministamente por `resolve_effective_max_users(plan, holding_override, tenant_override)`.
- La condición `is_deleted = True` marca la baja lógica en base de datos e inmediatamente:
  - Revoca todos los tokens JWT activos en Redis mediante el *Kill-Switch*.
  - Excluye al usuario de la sumatoria de asientos activos, liberando el cupo para una nueva creación.
  - Almacena el snapshot forense inalterable en `public.global_audit_log` y en `tenant_*.audit_log`.

### 1.4 Permisos Canónicos de Administración de Plataforma y Protección Declarativa
Las 4 vistas administrativas del panel global (`platform-admin`) operan con permisos canónicos de 3 niveles:
- `platform_admin.holdings.manage`: Alta, edición y eliminación de Holdings.
- `platform_admin.legal_entities.manage`: Alta, edición y eliminación de Sociedades Tributarias.
- `platform_admin.tenants.provision`: Aprovisionamiento de Tenants, gestión de módulos y modo soporte / impersonación.
- `platform_admin.client_users.manage`: Alta, edición y soft-delete (archivo) de usuarios clientes.
- **Enforcement en Frontend:** Los botones de mutación se encuentran encapsulados en `<Can perform="...">`; si la política RBAC activa no otorga el token, el elemento no se renderiza en el DOM, impidiendo bypasses visuales.

## 2. Invariantes

- Prohibido realizar borrado físico (`DELETE`) en tablas de usuarios o auditoría.
- Cada request valida en tiempo constante ($O(1)$) en Redis si el token JWT o el `user_id` fue revocado.
- Si un request intenta exceder el cupo activo, el sistema aborta de forma determinista con `HTTP 409 Conflict` (`QuotaExceededError`).

## 3. Evaluación JEV Sistema 1

jev_system1_evaluation: «¿Lo puede hacer JEV (Sí/No)?» → **Sí**.
- Primitiva: `Jev.score`
- Umbral de confianza: `0.85` (bajo umbral → revisión humana / camino determinista).
- Justificación: JEV puede calcular scores de riesgo ante patrones de acceso anómalos o solicitudes de elevación JIT; sin embargo, la decisión estricta de autorización booleana permanece 100% determinista bajo la ecuación formal.

## 4. Pruebas (Co-Creación 1:1)

- `oppytec-backend/tests/architecture/test_rbac_and_audit_coverage.py`
- `oppytec-backend/tests/unit/domain/test_rbac_evaluator.py`
- `oppytec-backend/tests/unit/test_plan_basico_quotas_and_admin_provisioning.py` (valida el techo de 2 niveles y liberación por soft-delete).
- `oppytec-backend/tests/unit/test_tenancy_admin_audit_and_redis_killswitch.py` (valida exigencia de permisos canónicos y revocación en Redis).
- `oppytec-frontend/src/features/platform-admin/AdminManagementViews.test.tsx` (valida veto visual de botones `<Can>` ante roles no autorizados).
