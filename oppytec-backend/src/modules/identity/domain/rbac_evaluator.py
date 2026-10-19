"""
oppytec-backend/src/modules/identity/domain/rbac_evaluator.py
Motor matemático puro de evaluación RBAC Dual de 3 niveles (`<modulo>.<submodulo>.<funcion>`):
- Ecuación de Acceso Efectivo: M_Plan ∩ ((P_Rol U P_TempAllow) \\ P_ExplicitDeny)
- Las 3 Leyes de Delegación Jerárquica (`hierarchy_rank`: R solo delega a > R, excepto Rank 0)
- Evaluación de vigencia y cupo de usos de concesiones temporales Just-In-Time (JIT)
- Construcción determinista de la huella forense `AuthorizationLineage`.
Cero dependencias de infraestructura (`fastapi`, `sqlalchemy`, `redis`, `httpx`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

GrantEffectType = Literal["ALLOW", "DENY"]
AuthorizedViaType = Literal[
    "GOD_SUPERUSER",
    "HOLDING_OWNER_PLAN_CEILING",
    "ROLE_PERMISSION",
    "TEMPORARY_JIT_GRANT",
    "DENIED_EXPLICIT",
    "DENIED_MODULE_NOT_IN_PLAN",
    "DENIED_MISSING_PERMISSION",
]

THREE_LEVEL_PERMISSION_REGEX: re.Pattern[str] = re.compile(
    r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$"
)
TENANT_DELEGATION_PERMISSION: str = "settings.rbac.delegate_subordinates"
GLOBAL_DELEGATION_PERMISSION: str = "platform_security.rbac.delegate_subordinates"


def is_valid_three_level_permission(permission_code: str) -> bool:
    """Verifica que `permission_code` cumpla estrictamente `<modulo>.<submodulo>.<funcion>`."""
    return bool(THREE_LEVEL_PERMISSION_REGEX.match(permission_code.strip()))


def extract_permission_module(permission_code: str) -> str:
    """Extrae el segmento `<modulo>` de un código de permiso de 3 niveles."""
    cleaned = permission_code.strip()
    if not is_valid_three_level_permission(cleaned):
        raise ValueError(
            f"Invalid 3-level RBAC permission '{permission_code}'. Expected '<modulo>.<submodulo>.<funcion>'."
        )
    return cleaned.split(".", 1)[0]


@dataclass(frozen=True)
class PermissionGrantSpec:
    """Especificación inmutable de una concesión temporal Just-In-Time (JIT) o denegación explícita."""

    grant_id: str
    user_id: int
    permission_code: str
    effect: GrantEffectType
    granted_by_user_id: int
    reason: str
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    max_uses: int | None = None
    used_count: int = 0
    is_revoked: bool = False


@dataclass(frozen=True)
class AuthorizationLineage:
    """Huella forense de autorización que registra exactamente cómo se concedió o denegó el permiso."""

    authorized_via: AuthorizedViaType
    permission_code: str
    actor_user_id: int
    role_slug: str | None = None
    grant_id: str | None = None
    granted_by_user_id: int | None = None
    expires_at_iso: str | None = None
    grant_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serializa el linaje forense para persistencia en `audit_activity_log.authorization_lineage`."""
        return {
            "authorized_via": self.authorized_via,
            "permission_code": self.permission_code,
            "actor_user_id": self.actor_user_id,
            "role_slug": self.role_slug,
            "grant_id": self.grant_id,
            "granted_by_user_id": self.granted_by_user_id,
            "expires_at_iso": self.expires_at_iso,
            "grant_reason": self.grant_reason,
        }


@dataclass(frozen=True)
class AuthorizationDecision:
    """Resultado determinista de evaluar un permiso de 3 niveles."""

    allowed: bool
    reason_code: str
    lineage: AuthorizationLineage
    consumed_jit_grant_id: str | None = None


def is_grant_currently_active(
    grant: PermissionGrantSpec,
    now: datetime | None = None,
) -> bool:
    """
    Evalúa si un `PermissionGrantSpec` está activo en el instante `now`:
    - No revocado (`is_revoked == False`)
    - Si tiene `starts_at`, `starts_at <= now`
    - Si tiene `expires_at`, `expires_at > now`
    - Si tiene `max_uses`, `used_count < max_uses`
    """
    if grant.is_revoked:
        return False
    ref_now = now or datetime.now(UTC)
    if grant.starts_at is not None and ref_now < grant.starts_at:
        return False
    if grant.expires_at is not None and ref_now >= grant.expires_at:
        return False
    return not (grant.max_uses is not None and grant.used_count >= grant.max_uses)


def compute_effective_permissions(
    *,
    plan_enabled_modules: frozenset[str] | set[str],
    role_permissions: frozenset[str] | set[str],
    grants: tuple[PermissionGrantSpec, ...] | list[PermissionGrantSpec] = (),
    is_holding_owner: bool = False,
    is_superuser_god: bool = False,
    all_catalog_permissions: frozenset[str] | set[str] = frozenset(),
    now: datetime | None = None,
) -> frozenset[str]:
    """
    Resuelve matemáticamente el conjunto de permisos efectivos de 3 niveles:
    Acceso Efectivo = M_Plan ∩ ((P_Rol U P_TempAllow) \\ P_ExplicitDeny).
    - Si `is_superuser_god=True` (en `public`), posee todos los permisos válidos sin restricción de plan.
    - Si `is_holding_owner=True` (`propietario`), parte con todos los permisos del catálogo (`*`),
      pero sigue gobernado por el techo comercial `M_Plan` y por eventuales `DENY` explícitos.
    """
    ref_now = now or datetime.now(UTC)
    valid_role_perms = {p for p in role_permissions if is_valid_three_level_permission(p)}
    valid_catalog = {p for p in all_catalog_permissions if is_valid_three_level_permission(p)}

    if is_superuser_god:
        base_universe = valid_role_perms | valid_catalog
        for g in grants:
            if is_valid_three_level_permission(g.permission_code) and is_grant_currently_active(g, ref_now):
                base_universe.add(g.permission_code)
        return frozenset(base_universe)

    temp_allow: set[str] = set()
    explicit_deny: set[str] = set()
    for grant in grants:
        if not is_valid_three_level_permission(grant.permission_code):
            continue
        if not is_grant_currently_active(grant, ref_now):
            continue
        if grant.effect == "DENY":
            explicit_deny.add(grant.permission_code)
        elif grant.effect == "ALLOW":
            temp_allow.add(grant.permission_code)

    candidate_pool = (valid_catalog | valid_role_perms | temp_allow) if is_holding_owner else (valid_role_perms | temp_allow)
    after_deny = candidate_pool - explicit_deny

    enabled_modules = {m.strip() for m in plan_enabled_modules if m.strip()}
    effective = {
        perm
        for perm in after_deny
        if extract_permission_module(perm) in enabled_modules
    }
    return frozenset(effective)


def evaluate_permission_access(
    *,
    actor_user_id: int,
    required_permission: str,
    plan_enabled_modules: frozenset[str] | set[str],
    role_permissions: frozenset[str] | set[str],
    grants: tuple[PermissionGrantSpec, ...] | list[PermissionGrantSpec] = (),
    role_slug: str | None = None,
    is_holding_owner: bool = False,
    is_superuser_god: bool = False,
    now: datetime | None = None,
) -> AuthorizationDecision:
    """
    Evalúa si el usuario tiene acceso a `required_permission` (`<modulo>.<submodulo>.<funcion>`)
    y genera el `AuthorizationLineage` exacto para auditoría forense.
    """
    cleaned_perm = required_permission.strip()
    if not is_valid_three_level_permission(cleaned_perm):
        raise ValueError(
            f"Invalid 3-level permission '{required_permission}'. Expected '<modulo>.<submodulo>.<funcion>'."
        )

    if is_superuser_god:
        return AuthorizationDecision(
            allowed=True,
            reason_code="ALLOWED_SUPERUSER_GOD",
            lineage=AuthorizationLineage(
                authorized_via="GOD_SUPERUSER",
                permission_code=cleaned_perm,
                actor_user_id=actor_user_id,
                role_slug=role_slug or "superuser",
            ),
        )

    ref_now = now or datetime.now(UTC)
    module_slug = extract_permission_module(cleaned_perm)
    enabled_modules = {m.strip() for m in plan_enabled_modules if m.strip()}

    # Paso 1: Techo Comercial del Plan (aplica incluso al Propietario del Holding)
    if module_slug not in enabled_modules:
        return AuthorizationDecision(
            allowed=False,
            reason_code="MODULE_NOT_ENABLED_IN_PLAN",
            lineage=AuthorizationLineage(
                authorized_via="DENIED_MODULE_NOT_IN_PLAN",
                permission_code=cleaned_perm,
                actor_user_id=actor_user_id,
                role_slug=role_slug,
            ),
        )

    # Paso 2: Denegación Explícita prevalece siempre sobre Rol, JIT o Propietario
    for grant in grants:
        if (
            grant.permission_code == cleaned_perm
            and grant.effect == "DENY"
            and is_grant_currently_active(grant, ref_now)
        ):
            return AuthorizationDecision(
                allowed=False,
                reason_code="EXPLICIT_DENY_GRANT",
                lineage=AuthorizationLineage(
                    authorized_via="DENIED_EXPLICIT",
                    permission_code=cleaned_perm,
                    actor_user_id=actor_user_id,
                    role_slug=role_slug,
                    grant_id=grant.grant_id,
                    granted_by_user_id=grant.granted_by_user_id,
                    expires_at_iso=grant.expires_at.isoformat() if grant.expires_at else None,
                    grant_reason=grant.reason,
                ),
            )

    # Paso 3: Concesión Temporal JIT activa (registra trazabilidad forense de quién lo otorgó)
    for grant in grants:
        if (
            grant.permission_code == cleaned_perm
            and grant.effect == "ALLOW"
            and is_grant_currently_active(grant, ref_now)
        ):
            return AuthorizationDecision(
                allowed=True,
                reason_code="ALLOWED_TEMPORARY_JIT_GRANT",
                lineage=AuthorizationLineage(
                    authorized_via="TEMPORARY_JIT_GRANT",
                    permission_code=cleaned_perm,
                    actor_user_id=actor_user_id,
                    role_slug=role_slug,
                    grant_id=grant.grant_id,
                    granted_by_user_id=grant.granted_by_user_id,
                    expires_at_iso=grant.expires_at.isoformat() if grant.expires_at else None,
                    grant_reason=grant.reason,
                ),
                consumed_jit_grant_id=grant.grant_id,
            )

    # Paso 4: Permiso permanente del Rol
    if cleaned_perm in role_permissions:
        return AuthorizationDecision(
            allowed=True,
            reason_code="ALLOWED_ROLE_PERMISSION",
            lineage=AuthorizationLineage(
                authorized_via="ROLE_PERMISSION",
                permission_code=cleaned_perm,
                actor_user_id=actor_user_id,
                role_slug=role_slug,
            ),
        )

    # Paso 5: Propietario del Holding dentro de módulos habilitados en el Plan
    if is_holding_owner:
        return AuthorizationDecision(
            allowed=True,
            reason_code="ALLOWED_HOLDING_OWNER_WITHIN_PLAN",
            lineage=AuthorizationLineage(
                authorized_via="HOLDING_OWNER_PLAN_CEILING",
                permission_code=cleaned_perm,
                actor_user_id=actor_user_id,
                role_slug=role_slug or "propietario",
            ),
        )

    return AuthorizationDecision(
        allowed=False,
        reason_code="MISSING_PERMISSION",
        lineage=AuthorizationLineage(
            authorized_via="DENIED_MISSING_PERMISSION",
            permission_code=cleaned_perm,
            actor_user_id=actor_user_id,
            role_slug=role_slug,
        ),
    )


def validate_hierarchy_delegation(
    *,
    actor_rank: int,
    target_rank: int,
) -> bool:
    """
    Ley 1 de Delegación Jerárquica (`hierarchy_rank`):
    - Un usuario con rango `R > 0` solo puede administrar/delegar a usuarios o roles con rango `> R`.
    - Excepción única: `Rank 0` (`superuser` en OppyTec o `propietario` en cliente) puede gestionar `Rank >= 0`.
    """
    if actor_rank < 0 or target_rank < 0:
        raise ValueError("Hierarchy rank cannot be negative.")
    if actor_rank == 0:
        return True
    return actor_rank < target_rank


def can_delegate_permission(
    *,
    actor_rank: int,
    target_rank: int,
    permission_to_grant: str,
    actor_effective_permissions: frozenset[str] | set[str],
    is_global_scope: bool = False,
    is_superuser_or_owner_rank_zero: bool = False,
) -> tuple[bool, str]:
    """
    Verifica las 3 Leyes Matemáticas de No-Escalamiento (*Bounded Delegation*):
    1. Ley 1 (Rango Estricto Inferior): `actor_rank < target_rank` (o `actor_rank == 0`).
    2. Ley 2 (Techo de Concesión / Grant Ceiling): El delegador debe poseer activamente `permission_to_grant`.
    3. Ley 3 (Capacidad de Delegación Explícita): Si `actor_rank > 0`, debe poseer
       `settings.rbac.delegate_subordinates` (tenant) o `platform_security.rbac.delegate_subordinates` (global).
    """
    if not is_valid_three_level_permission(permission_to_grant):
        return False, "INVALID_THREE_LEVEL_PERMISSION_FORMAT"

    if not validate_hierarchy_delegation(actor_rank=actor_rank, target_rank=target_rank):
        return False, "HIERARCHY_RANK_VIOLATION"

    delegation_cap = (
        GLOBAL_DELEGATION_PERMISSION if is_global_scope else TENANT_DELEGATION_PERMISSION
    )
    if (
        actor_rank > 0
        and not is_superuser_or_owner_rank_zero
        and delegation_cap not in actor_effective_permissions
    ):
        return False, "MISSING_DELEGATION_CAPABILITY"

    if (
        not is_superuser_or_owner_rank_zero
        and permission_to_grant not in actor_effective_permissions
    ):
        return False, "GRANT_CEILING_EXCEEDED"

    return True, "DELEGATION_ALLOWED"


def evaluate_effective_permission(
    *,
    required_permission: str,
    contracted_modules: frozenset[str] | set[str] | None = None,
    role_grants: frozenset[str] | set[str] | None = None,
    temp_grants: frozenset[str] | set[str] | tuple[PermissionGrantSpec, ...] | list[PermissionGrantSpec] = frozenset(),
    explicit_denies: frozenset[str] | set[str] = frozenset(),
    actor_user_id: int = 0,
    is_holding_owner: bool = False,
    is_superuser_god: bool = False,
    now: datetime | None = None,
) -> AuthorizationDecision:
    """
    Evalúa la ecuación de acceso efectivo M_Plan ∩ ((P_Rol U P_TempAllow) \\ P_ExplicitDeny)
    aceptando tanto cadenas de permisos en `temp_grants`/`explicit_denies` como objetos `PermissionGrantSpec`.
    """
    normalized_grants: list[PermissionGrantSpec] = []
    for deny_code in explicit_denies:
        normalized_grants.append(
            PermissionGrantSpec(
                grant_id=f"explicit-deny-{deny_code}",
                user_id=actor_user_id,
                permission_code=deny_code,
                effect="DENY",
                granted_by_user_id=0,
                reason="Explicit deny in principal claims",
            )
        )
    for item in temp_grants:
        if isinstance(item, PermissionGrantSpec):
            normalized_grants.append(item)
        else:
            normalized_grants.append(
                PermissionGrantSpec(
                    grant_id=f"temp-allow-{item}",
                    user_id=actor_user_id,
                    permission_code=str(item),
                    effect="ALLOW",
                    granted_by_user_id=0,
                    reason="Temporary JIT allow in principal claims",
                )
            )

    resolved_roles = frozenset(role_grants) if role_grants is not None else frozenset()
    if contracted_modules is None:
        inferred_modules = {
            extract_permission_module(p)
            for p in resolved_roles
            if is_valid_three_level_permission(p)
        } | {
            extract_permission_module(g.permission_code)
            for g in normalized_grants
            if is_valid_three_level_permission(g.permission_code)
        }
        resolved_modules: frozenset[str] | set[str] = inferred_modules
    else:
        resolved_modules = contracted_modules

    return evaluate_permission_access(
        actor_user_id=actor_user_id,
        required_permission=required_permission,
        plan_enabled_modules=resolved_modules,
        role_permissions=resolved_roles,
        grants=normalized_grants,
        is_holding_owner=is_holding_owner,
        is_superuser_god=is_superuser_god,
        now=now,
    )
