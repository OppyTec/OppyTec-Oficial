"""
oppytec-backend/src/core/guards/rbac_dependencies.py
Guardias de autorización RBAC Dual de 3 niveles (`<modulo>.<submodulo>.<funcion>`) para FastAPI:
- `AuthenticatedPrincipal`: Principal inmutable con linaje forense y contexto Multi-Tenant.
- `RequireGlobalPermission`: Guardia para el Plano Global (`public.*`, Consola OppyTec).
- `RequireTenantPermission`: Guardia para el Plano Cliente (`tenant_*`, bloqueo anti-IDOR Cross-Tenant/Holding).
- Registro en memoria + Kill-Switch de revocación instantánea de sesiones (`jti` / `user_id`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Request

from src.core.exceptions import (
    AuthenticationError,
    CrossTenantAccessError,
    PermissionDeniedError,
)
from src.core.security import TenantJwtClaims, decode_access_token
from src.modules.identity.domain.rbac_evaluator import (
    THREE_LEVEL_PERMISSION_REGEX,
    evaluate_effective_permission,
    is_valid_three_level_permission,
)

_REVOKED_JTIS: set[str] = set()
_REVOKED_USER_IDS: set[int] = set()


def revoke_session_token(
    *,
    jti: str | None = None,
    user_id: int | None = None,
) -> None:
    """Registra la revocación inmediata de un `jti` o `user_id` en el Kill-Switch en memoria."""
    if jti:
        _REVOKED_JTIS.add(jti.strip())
    if user_id is not None:
        _REVOKED_USER_IDS.add(int(user_id))


def restore_revoked_user_session(user_id: int) -> None:
    """Limpia la revocación de `user_id` cuando un trabajador es restaurado de `soft-delete`."""
    _REVOKED_USER_IDS.discard(int(user_id))


def clear_revoked_sessions() -> None:
    """Limpia el registro de sesiones revocadas (útil para aislamiento entre tests)."""
    _REVOKED_JTIS.clear()
    _REVOKED_USER_IDS.clear()


def is_session_revoked(*, jti: str = "", user_id: int | None = None) -> bool:
    """Verifica en `< 1 ms` si el token `jti` o el `user_id` están revocados por Kill-Switch."""
    if jti and jti in _REVOKED_JTIS:
        return True
    return user_id is not None and int(user_id) in _REVOKED_USER_IDS


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Principal autenticado y autorizado tras superar el guardia RBAC de 3 niveles."""

    user_id: int
    tenant_id: str | None
    holding_id: str | None
    is_global_staff: bool
    hierarchy_rank: int
    contracted_modules: frozenset[str] = field(default_factory=frozenset)
    role_grants: frozenset[str] = field(default_factory=frozenset)
    temp_grants: frozenset[str] = field(default_factory=frozenset)
    explicit_denies: frozenset[str] = field(default_factory=frozenset)
    accessible_tenants: frozenset[str] = field(default_factory=frozenset)
    is_superuser_god: bool = False
    is_holding_owner: bool = False
    jti: str = ""
    authorization_lineage: dict[str, object] = field(default_factory=dict)


def _extract_bearer_claims(request: Request) -> TenantJwtClaims:
    """Extrae y decodifica el token Bearer de `Authorization`, verificando también el Kill-Switch."""
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise AuthenticationError(
            "Missing or malformed Authorization Bearer header.",
            i18n_key="auth:errors.missing_bearer_token",
            status_code=401,
        )
    token = auth_header[7:].strip()
    if not token:
        raise AuthenticationError(
            "Empty Bearer token.",
            i18n_key="auth:errors.empty_bearer_token",
            status_code=401,
        )

    claims = decode_access_token(token)
    if bool(claims.raw_payload.get("is_deleted", False)) or is_session_revoked(
        jti=claims.jti,
        user_id=claims.user_id,
    ):
        raise AuthenticationError(
            "Session has been revoked by Kill-Switch (user soft-deleted or token invalidated).",
            i18n_key="auth:errors.session_revoked",
            status_code=401,
            error_code="SESSION_REVOKED_KILLSWITCH",
        )
    return claims


class RequireGlobalPermission:
    """
    Dependencia FastAPI que exige un permiso global de 3 niveles (`<modulo>.<submodulo>.<funcion>`)
    en el Plano Global (`public.*`).
    """

    def __init__(self, permission_code: str, fallback_permission: str | None = None) -> None:
        cleaned = permission_code.strip()
        if not THREE_LEVEL_PERMISSION_REGEX.match(cleaned):
            raise ValueError(
                f"Invalid 3-level RBAC permission '{permission_code}'. "
                "Expected '<modulo>.<submodulo>.<funcion>'."
            )
        self.permission_code: str = cleaned
        if fallback_permission is not None:
            cleaned_fb = fallback_permission.strip()
            if not THREE_LEVEL_PERMISSION_REGEX.match(cleaned_fb):
                raise ValueError(
                    f"Invalid 3-level fallback RBAC permission '{fallback_permission}'. "
                    "Expected '<modulo>.<submodulo>.<funcion>'."
                )
            self.fallback_permission: str | None = cleaned_fb
        else:
            self.fallback_permission = None

    async def __call__(self, request: Request) -> AuthenticatedPrincipal:
        if not is_valid_three_level_permission(self.permission_code):
            raise PermissionDeniedError(
                f"Invalid 3-level permission format '{self.permission_code}'.",
                i18n_key="auth:errors.invalid_permission_format",
            )

        claims = _extract_bearer_claims(request)
        if not claims.is_global_staff and not claims.is_superuser_god:
            raise PermissionDeniedError(
                "Global platform permission required; tenant-scoped token cannot access global plane.",
                i18n_key="auth:errors.global_staff_required",
                error_code="GLOBAL_STAFF_REQUIRED",
            )

        if claims.is_superuser_god or (claims.is_global_staff and claims.hierarchy_rank == 0):
            lineage: dict[str, object] = {
                "authorized_via": "GOD_SUPERUSER",
                "permission_code": self.permission_code,
                "actor_user_id": claims.user_id,
            }
        else:
            decision = evaluate_effective_permission(
                required_permission=self.permission_code,
                contracted_modules=(
                    claims.contracted_modules if claims.contracted_modules_explicit else None
                ),
                role_grants=claims.role_grants,
                temp_grants=claims.temp_grants,
                explicit_denies=claims.explicit_denies,
                actor_user_id=claims.user_id,
                is_holding_owner=False,
                is_superuser_god=claims.is_superuser_god,
            )
            if not decision.allowed and self.fallback_permission:
                fallback_decision = evaluate_effective_permission(
                    required_permission=self.fallback_permission,
                    contracted_modules=(
                        claims.contracted_modules if claims.contracted_modules_explicit else None
                    ),
                    role_grants=claims.role_grants,
                    temp_grants=claims.temp_grants,
                    explicit_denies=claims.explicit_denies,
                    actor_user_id=claims.user_id,
                    is_holding_owner=False,
                    is_superuser_god=claims.is_superuser_god,
                )
                if fallback_decision.allowed:
                    decision = fallback_decision
            if not decision.allowed:
                raise PermissionDeniedError(
                    f"Global permission '{self.permission_code}' denied ({decision.reason_code}).",
                    i18n_key="auth:errors.permission_denied",
                    error_code=decision.reason_code,
                )
            lineage = decision.lineage.to_dict()

        principal = AuthenticatedPrincipal(
            user_id=claims.user_id,
            tenant_id=claims.tenant_id,
            holding_id=claims.holding_id,
            is_global_staff=True,
            hierarchy_rank=claims.hierarchy_rank,
            contracted_modules=claims.contracted_modules,
            role_grants=claims.role_grants,
            temp_grants=claims.temp_grants,
            explicit_denies=claims.explicit_denies,
            accessible_tenants=claims.accessible_tenants,
            is_superuser_god=claims.is_superuser_god,
            is_holding_owner=claims.is_holding_owner,
            jti=claims.jti,
            authorization_lineage=lineage,
        )
        request.state.principal = principal
        return principal


class RequireTenantPermission:
    """
    Dependencia FastAPI que exige un permiso de 3 niveles (`<modulo>.<submodulo>.<funcion>`)
    en el Plano Cliente (`tenant_*`), validando aislamiento estricto de `X-Tenant-ID` / `tenant_id`.
    """

    def __init__(self, permission_code: str, fallback_permission: str | None = None) -> None:
        cleaned = permission_code.strip()
        if not THREE_LEVEL_PERMISSION_REGEX.match(cleaned):
            raise ValueError(
                f"Invalid 3-level RBAC permission '{permission_code}'. "
                "Expected '<modulo>.<submodulo>.<funcion>'."
            )
        self.permission_code: str = cleaned
        if fallback_permission is not None:
            cleaned_fb = fallback_permission.strip()
            if not THREE_LEVEL_PERMISSION_REGEX.match(cleaned_fb):
                raise ValueError(
                    f"Invalid 3-level fallback RBAC permission '{fallback_permission}'. "
                    "Expected '<modulo>.<submodulo>.<funcion>'."
                )
            self.fallback_permission: str | None = cleaned_fb
        else:
            self.fallback_permission = None

    async def __call__(self, request: Request) -> AuthenticatedPrincipal:
        if not is_valid_three_level_permission(self.permission_code):
            raise PermissionDeniedError(
                f"Invalid 3-level permission format '{self.permission_code}'.",
                i18n_key="auth:errors.invalid_permission_format",
            )

        claims = _extract_bearer_claims(request)
        header_tenant_id = request.headers.get("X-Tenant-ID", "").strip()
        effective_tenant_id = header_tenant_id or (claims.tenant_id or "")

        if not claims.is_superuser_god:
            if not effective_tenant_id:
                raise PermissionDeniedError(
                    "Missing tenant context (neither X-Tenant-ID header nor token tenant_id provided).",
                    i18n_key="tenancy:errors.missing_tenant_context",
                )
            if (
                header_tenant_id
                and claims.accessible_tenants
                and header_tenant_id not in claims.accessible_tenants
            ) or (
                header_tenant_id
                and not claims.accessible_tenants
                and claims.tenant_id is not None
                and header_tenant_id != claims.tenant_id
            ):
                raise CrossTenantAccessError(
                    f"Cross-tenant access denied: user {claims.user_id} is not authorized for tenant '{header_tenant_id}'.",
                    i18n_key="tenancy:errors.cross_tenant_forbidden",
                )

        decision = evaluate_effective_permission(
            required_permission=self.permission_code,
            contracted_modules=(
                claims.contracted_modules if claims.contracted_modules_explicit else None
            ),
            role_grants=claims.role_grants,
            temp_grants=claims.temp_grants,
            explicit_denies=claims.explicit_denies,
            actor_user_id=claims.user_id,
            is_holding_owner=claims.is_holding_owner,
            is_superuser_god=claims.is_superuser_god,
        )
        if not decision.allowed and self.fallback_permission:
            fallback_decision = evaluate_effective_permission(
                required_permission=self.fallback_permission,
                contracted_modules=(
                    claims.contracted_modules if claims.contracted_modules_explicit else None
                ),
                role_grants=claims.role_grants,
                temp_grants=claims.temp_grants,
                explicit_denies=claims.explicit_denies,
                actor_user_id=claims.user_id,
                is_holding_owner=claims.is_holding_owner,
                is_superuser_god=claims.is_superuser_god,
            )
            if fallback_decision.allowed:
                decision = fallback_decision
        if not decision.allowed:
            raise PermissionDeniedError(
                f"Tenant permission '{self.permission_code}' denied ({decision.reason_code}).",
                i18n_key="auth:errors.permission_denied",
                error_code=decision.reason_code,
            )

        principal = AuthenticatedPrincipal(
            user_id=claims.user_id,
            tenant_id=effective_tenant_id or claims.tenant_id,
            holding_id=claims.holding_id,
            is_global_staff=claims.is_global_staff,
            hierarchy_rank=claims.hierarchy_rank,
            contracted_modules=claims.contracted_modules,
            role_grants=claims.role_grants,
            temp_grants=claims.temp_grants,
            explicit_denies=claims.explicit_denies,
            accessible_tenants=claims.accessible_tenants,
            is_superuser_god=claims.is_superuser_god,
            is_holding_owner=claims.is_holding_owner,
            jti=claims.jti,
            authorization_lineage=decision.lineage.to_dict(),
        )
        request.state.principal = principal
        return principal
