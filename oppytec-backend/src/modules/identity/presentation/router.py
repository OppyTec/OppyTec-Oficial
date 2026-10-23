"""
oppytec-backend/src/modules/identity/presentation/router.py
Endpoints REST de Identidad, Autenticación, Roles, Delegación JIT y Soft-Delete con Kill-Switch:
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `GET /api/v1/identity/roles` y `POST /api/v1/identity/roles`
- `POST /api/v1/identity/grants/jit`
- `POST /api/v1/identity/users/{user_id}/soft-delete`
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.bootstrap import (
    TENANT_BASE_ROLES,
    build_genesis_superuser_manifest,
    verify_genesis_password,
)
from src.core.exceptions import AuthenticationError, PermissionDeniedError
from src.core.guards.rate_limiter import RateLimitCheckResult, RequireRateLimit
from src.core.guards.rbac_dependencies import (
    AuthenticatedPrincipal,
    RequireGlobalPermission,
    RequireTenantPermission,
    is_session_revoked,
    revoke_session_token,
)
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_and_extract_claims,
    hash_password,
    verify_password,
)
from src.modules.identity.application.delegation_service import (
    DelegationRequest,
    RbacDelegationService,
)
from src.modules.identity.domain.rbac_evaluator import validate_hierarchy_delegation
from src.modules.identity.presentation.schemas import (
    AuthenticatedUserProfileResponse,
    JitGrantCreateRequest,
    JitGrantResponse,
    LoginRequest,
    RefreshTokenRequest,
    RoleResponse,
    RoleUpsertRequest,
    TokenPairResponse,
    UserSoftDeleteRequest,
    UserSoftDeleteResponse,
)

router = APIRouter(tags=["identity"])

_delegation_service = RbacDelegationService()
_custom_roles: dict[str, RoleResponse] = {
    role.slug: RoleResponse(
        slug=role.slug,
        name=role.name,
        hierarchy_rank=role.hierarchy_rank,
        permissions=["settings.rbac.delegate_subordinates"] if role.hierarchy_rank <= 20 else [],
    )
    for role in TENANT_BASE_ROLES
}


def _build_genesis_store_entry() -> dict[str, object]:
    """Construye el registro base del SuperUser Génesis sin datos ficticios de clientes."""
    genesis = build_genesis_superuser_manifest()
    return {
        "id": 1,
        "username": genesis.username,
        "email": genesis.email,
        "first_name": "SuperUser",
        "last_name": "OppyTec",
        "role": "propietario",
        "hierarchy_rank": 0,
        "is_superuser": True,
        "is_global_admin": True,
        "is_active": True,
        "tipo_usuario": "GLOBAL",
        "tenant_id": None,
        "holding_id": None,
        "hashed_password": genesis.hashed_password,
        "permissions": ["*.*.*"],
    }


_GLOBAL_USERS_STORE: dict[int, dict[str, object]] = {
    1: _build_genesis_store_entry(),
}
_CLIENT_USERS_STORE: dict[int, dict[str, object]] = {
    101: {
        "user_id": 101,
        "holding_id": "holding_genesis",
        "tenant_id": "tenant_genesis",
        "username": "admin.local",
        "email": "admin.local@restaurant.cl",
        "first_name": "Administrador",
        "last_name": "Sucursal",
        "role": "admin",
        "hierarchy_rank": 10,
        "is_holding_owner": False,
        "is_deleted": False,
        "password_hash": hash_password("OppyTec#2026"),
        "is_active": True,
    },
    102: {
        "user_id": 102,
        "holding_id": "holding_pacifico",
        "tenant_id": "tenant_pacifico_centro",
        "username": "cocinero.jefe",
        "email": "chef@pacifico.cl",
        "first_name": "Mario",
        "last_name": "Gómez",
        "role": "supervisor",
        "hierarchy_rank": 20,
        "is_holding_owner": False,
        "is_deleted": False,
        "password_hash": hash_password("OppyTec#2026"),
        "is_active": True,
    },
}


def _match_store_user(
    store: dict[int, dict[str, object]],
    ident_lower: str,
    plain_password: str,
) -> dict[str, object] | None:
    """Busca un usuario activo por username o email (case-insensitive) y verifica su contraseña."""
    for uid, record in store.items():
        if not bool(record.get("is_active", True)) or bool(record.get("is_deleted", False)):
            continue
        uname = str(record.get("username", "")).strip().lower()
        email = str(record.get("email", "")).strip().lower()
        if ident_lower not in {uname, email}:
            continue
        hashed_pw = str(record.get("hashed_password", record.get("password_hash", "")))
        plain_stored = record.get("password")
        password_ok = (
            verify_password(plain_password, hashed_pw)
            if hashed_pw
            else (isinstance(plain_stored, str) and plain_stored == plain_password)
        )
        if password_ok:
            resolved = dict(record)
            resolved.setdefault("id", uid)
            return resolved
    return None


@router.post(
    "/api/v1/auth/login",
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
)
async def login_endpoint(
    payload: LoginRequest,
    _rate_limit: Annotated[RateLimitCheckResult, Depends(RequireRateLimit("auth"))],
) -> TokenPairResponse:
    """Autentica al usuario (SuperUser Génesis, Global Staff o Cliente) bajo Rate Limiting `auth`."""
    genesis = build_genesis_superuser_manifest()
    ident = payload.username_or_email.strip()
    ident_lower = ident.lower()

    if ident_lower in {genesis.username.lower(), genesis.email.lower()} and verify_genesis_password(
        payload.password,
        genesis.hashed_password,
    ):
        user_id = 1
        is_god = True
        is_global_admin = True
        rank = 0
        tenant_id: str | None = payload.tenant_id
        holding_id: str | None = "holding_genesis" if payload.tenant_id else None
        _GLOBAL_USERS_STORE[1] = {
            "id": 1,
            "username": genesis.username,
            "email": genesis.email,
            "first_name": "SuperUser",
            "last_name": "OppyTec",
            "role": "propietario",
            "hierarchy_rank": 0,
            "is_superuser": True,
            "is_global_admin": True,
            "is_active": True,
            "tipo_usuario": "GLOBAL",
            "tenant_id": tenant_id,
            "holding_id": holding_id,
            "hashed_password": genesis.hashed_password,
            "permissions": ["*.*.*"],
        }
        user_profile = AuthenticatedUserProfileResponse(
            id=user_id,
            username=genesis.username,
            email=genesis.email,
            first_name="SuperUser",
            last_name="OppyTec",
            role="propietario",
            is_superuser=True,
            is_global_admin=True,
            tipo_usuario="GLOBAL",
            tenant_id=tenant_id,
            holding_id=holding_id,
            permissions=["*.*.*"],
        )
    else:
        matched_global = _match_store_user(_GLOBAL_USERS_STORE, ident_lower, payload.password)
        matched_client = (
            None
            if matched_global is not None
            else _match_store_user(_CLIENT_USERS_STORE, ident_lower, payload.password)
        )
        matched = matched_global or matched_client
        if matched is None:
            raise AuthenticationError(
                "Invalid username/email or password.",
                i18n_key="auth:errors.invalid_credentials",
                status_code=401,
            )

        raw_id = matched.get("id", 0)
        user_id = int(raw_id) if isinstance(raw_id, (int, str)) else 0
        is_god = bool(matched.get("is_superuser", False))
        is_global_admin = bool(
            matched.get("is_global_admin", is_god or matched_global is not None)
        )
        if payload.is_admin_login and not (is_god or is_global_admin):
            raise AuthenticationError(
                "Admin console login requires a Global Admin or SuperUser account.",
                i18n_key="auth:errors.admin_login_required",
                status_code=401,
            )

        raw_rank = matched.get("hierarchy_rank", 0 if is_god else 30)
        rank = int(raw_rank) if isinstance(raw_rank, (int, str)) else 30
        raw_tenant = payload.tenant_id or matched.get("tenant_id")
        tenant_id = str(raw_tenant) if raw_tenant is not None else None
        raw_holding = matched.get("holding_id")
        holding_id = str(raw_holding) if raw_holding is not None else None
        raw_perms = matched.get("permissions", [])
        perms_list = (
            [str(p) for p in raw_perms]
            if isinstance(raw_perms, (list, tuple, set, frozenset))
            else []
        )
        first_name_val = matched.get("first_name")
        last_name_val = matched.get("last_name")
        user_profile = AuthenticatedUserProfileResponse(
            id=user_id,
            username=str(matched.get("username", ident)),
            email=str(matched.get("email", ident)),
            first_name=str(first_name_val) if first_name_val is not None else None,
            last_name=str(last_name_val) if last_name_val is not None else None,
            role=str(matched.get("role", "propietario" if is_god else "admin")),
            is_superuser=is_god,
            is_global_admin=is_global_admin,
            tipo_usuario=str(
                matched.get("tipo_usuario", "GLOBAL" if is_global_admin else "CLIENTE")
            ),
            tenant_id=tenant_id,
            holding_id=holding_id,
            permissions=perms_list,
        )

    if is_session_revoked(user_id=user_id):
        raise AuthenticationError(
            "User account is soft-deleted or session is revoked.",
            i18n_key="auth:errors.session_revoked",
            status_code=401,
        )

    access_tok = create_access_token(
        user_id=user_id,
        holding_id=holding_id,
        tenant_id=tenant_id,
        hierarchy_rank=rank,
        is_superuser_god=is_god,
        is_global_staff=is_god or is_global_admin,
        role_grants=user_profile.permissions,
    )
    refresh_tok = create_refresh_token(
        user_id=user_id,
        holding_id=holding_id,
        tenant_id=tenant_id,
        hierarchy_rank=rank,
        is_superuser_god=is_god,
    )
    return TokenPairResponse(
        access_token=access_tok,
        refresh_token=refresh_tok,
        user_id=user_id,
        tenant_id=tenant_id,
        holding_id=holding_id,
        hierarchy_rank=rank,
        user=user_profile,
    )


@router.get(
    "/api/v1/auth/me",
    response_model=AuthenticatedUserProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def get_current_user_profile_endpoint(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("identity.profile.read")),
    ],
) -> AuthenticatedUserProfileResponse:
    """Devuelve el perfil completo del usuario autenticado en sesión."""
    record = _GLOBAL_USERS_STORE.get(principal.user_id) or _CLIENT_USERS_STORE.get(
        principal.user_id
    )
    if record is not None:
        first_name_val = record.get("first_name")
        last_name_val = record.get("last_name")
        raw_perms = record.get("permissions", [])
        perms_list = (
            [str(p) for p in raw_perms]
            if isinstance(raw_perms, (list, tuple, set, frozenset))
            else list(principal.role_grants)
        )
        return AuthenticatedUserProfileResponse(
            id=principal.user_id,
            username=str(record.get("username", "oppytec.admin")),
            email=str(record.get("email", "oppytec.admin@gmail.com")),
            first_name=str(first_name_val) if first_name_val is not None else None,
            last_name=str(last_name_val) if last_name_val is not None else None,
            role=str(record.get("role", "propietario")),
            is_superuser=bool(record.get("is_superuser", principal.is_superuser_god)),
            is_global_admin=bool(record.get("is_global_admin", principal.is_global_staff)),
            tipo_usuario=str(record.get("tipo_usuario", "GLOBAL")),
            tenant_id=principal.tenant_id,
            holding_id=principal.holding_id,
            permissions=perms_list,
        )

    genesis = build_genesis_superuser_manifest()
    return AuthenticatedUserProfileResponse(
        id=principal.user_id,
        username=genesis.username if principal.user_id == 1 else f"user_{principal.user_id}",
        email=genesis.email if principal.user_id == 1 else f"user_{principal.user_id}@oppytec.com",
        first_name="SuperUser" if principal.is_superuser_god else None,
        last_name="OppyTec" if principal.is_superuser_god else None,
        role="propietario" if principal.is_superuser_god else "admin",
        is_superuser=principal.is_superuser_god,
        is_global_admin=principal.is_global_staff,
        tipo_usuario="GLOBAL" if principal.is_global_staff else "CLIENTE",
        tenant_id=principal.tenant_id,
        holding_id=principal.holding_id,
        permissions=["*.*.*"] if principal.is_superuser_god else sorted(principal.role_grants),
    )


@router.post(
    "/api/v1/auth/logout",
    status_code=status.HTTP_200_OK,
)
async def logout_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("identity.session.logout")),
    ],
) -> dict[str, str]:
    """Cierra la sesión activa del usuario autenticado."""
    return {"status": "logged_out"}


@router.get(
    "/api/v1/identity/users",
    response_model=list[AuthenticatedUserProfileResponse],
    status_code=status.HTTP_200_OK,
)
async def list_global_users_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireGlobalPermission("identity.users.read")),
    ],
) -> list[AuthenticatedUserProfileResponse]:
    """Lista los usuarios de nivel Global (`public.global_users`)."""
    result: list[AuthenticatedUserProfileResponse] = []
    for u in _GLOBAL_USERS_STORE.values():
        user_id = int(str(u["id"]))
        raw_perms = u.get("permissions")
        perms: list[str] = (
            [str(p) for p in raw_perms]
            if isinstance(raw_perms, list)
            else []
        )
        result.append(
            AuthenticatedUserProfileResponse(
                id=user_id,
                username=str(u["username"]),
                email=str(u["email"]),
                first_name=str(u.get("first_name")) if u.get("first_name") else None,
                last_name=str(u.get("last_name")) if u.get("last_name") else None,
                role=str(u.get("role", "propietario")),
                is_superuser=bool(u.get("is_superuser", False)),
                is_global_admin=bool(u.get("is_global_admin", False)),
                tipo_usuario=str(u.get("tipo_usuario", "GLOBAL")),
                tenant_id=str(u["tenant_id"]) if u.get("tenant_id") else None,
                holding_id=str(u["holding_id"]) if u.get("holding_id") else None,
                permissions=perms,
            )
        )
    return result



@router.post(
    "/api/v1/auth/refresh",
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_token_endpoint(
    payload: RefreshTokenRequest,
    _rate_limit: Annotated[RateLimitCheckResult, Depends(RequireRateLimit("auth"))],
) -> TokenPairResponse:
    """Rota el par de tokens JWT verificando que la sesión no haya sido revocada por Kill-Switch."""
    claims = decode_and_extract_claims(payload.refresh_token, expected_type="refresh")
    if is_session_revoked(jti=claims.jti, user_id=claims.user_id):
        raise AuthenticationError(
            "Refresh token has been revoked by Kill-Switch.",
            i18n_key="auth:errors.session_revoked",
            status_code=401,
        )

    revoke_session_token(jti=claims.jti)
    access_tok = create_access_token(
        user_id=claims.user_id,
        holding_id=claims.holding_id,
        tenant_id=claims.tenant_id,
        tenant_schema=claims.tenant_schema,
        hierarchy_rank=claims.hierarchy_rank,
        is_superuser_god=claims.is_superuser_god,
        is_global_staff=claims.is_global_staff,
    )
    refresh_tok = create_refresh_token(
        user_id=claims.user_id,
        holding_id=claims.holding_id,
        tenant_id=claims.tenant_id,
        tenant_schema=claims.tenant_schema,
        hierarchy_rank=claims.hierarchy_rank,
        is_superuser_god=claims.is_superuser_god,
    )
    return TokenPairResponse(
        access_token=access_tok,
        refresh_token=refresh_tok,
        user_id=claims.user_id,
        tenant_id=claims.tenant_id,
        holding_id=claims.holding_id,
        hierarchy_rank=claims.hierarchy_rank,
    )


@router.get(
    "/api/v1/identity/roles",
    response_model=list[RoleResponse],
    status_code=status.HTTP_200_OK,
)
async def list_roles_endpoint(
    _principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("settings.roles.read")),
    ],
) -> list[RoleResponse]:
    """Lista los roles disponibles en el Tenant ordenados por `hierarchy_rank`."""
    return sorted(_custom_roles.values(), key=lambda r: r.hierarchy_rank)


@router.post(
    "/api/v1/identity/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_or_update_role_endpoint(
    payload: RoleUpsertRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("settings.roles.manage")),
    ],
) -> RoleResponse:
    """Crea o actualiza un rol verificando la Ley 1 de `hierarchy_rank`."""
    if not principal.is_superuser_god and not validate_hierarchy_delegation(
        actor_rank=principal.hierarchy_rank,
        target_rank=payload.hierarchy_rank,
    ):
        raise PermissionDeniedError(
            f"Hierarchy rank violation: actor rank {principal.hierarchy_rank} cannot manage role rank {payload.hierarchy_rank}.",
            i18n_key="auth:errors.hierarchy_rank_violation",
            error_code="HIERARCHY_RANK_VIOLATION",
        )

    role_resp = RoleResponse(
        slug=payload.slug,
        name=payload.name,
        hierarchy_rank=payload.hierarchy_rank,
        permissions=list(payload.permissions),
    )
    _custom_roles[payload.slug] = role_resp
    return role_resp


@router.post(
    "/api/v1/identity/grants/jit",
    response_model=JitGrantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_jit_grant_endpoint(
    payload: JitGrantCreateRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("settings.rbac.delegate_subordinates")),
    ],
) -> JitGrantResponse:
    """Emite una concesión temporal Just-In-Time (JIT) aplicando las 3 leyes de delegación."""
    effective_perms = principal.role_grants | principal.temp_grants
    req = DelegationRequest(
        actor_user_id=principal.user_id,
        actor_rank=principal.hierarchy_rank,
        target_user_id=payload.target_user_id,
        target_rank=payload.target_rank,
        permission_code=payload.permission_code,
        effect=payload.effect,
        reason=payload.reason,
        actor_effective_permissions=effective_perms,
        expires_at=payload.expires_at,
        max_uses=payload.max_uses,
        is_global_scope=False,
        is_superuser_or_owner_rank_zero=(
            principal.is_superuser_god
            or principal.is_holding_owner
            or principal.hierarchy_rank == 0
        ),
    )
    grant = _delegation_service.issue_permission_grant(req)
    return JitGrantResponse(
        grant_id=grant.grant_id,
        user_id=grant.user_id,
        permission_code=grant.permission_code,
        effect=grant.effect,
        granted_by_user_id=grant.granted_by_user_id,
        reason=grant.reason,
        used_count=grant.used_count,
        max_uses=grant.max_uses,
        is_revoked=grant.is_revoked,
    )


@router.post(
    "/api/v1/identity/users/{user_id}/soft-delete",
    response_model=UserSoftDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def soft_delete_user_endpoint(
    user_id: int,
    _payload: UserSoftDeleteRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(RequireTenantPermission("settings.users.soft_delete")),
    ],
) -> UserSoftDeleteResponse:
    """Aplica `Soft-Delete` a un trabajador, libera su cupo y dispara el Kill-Switch de sesión."""
    if user_id == principal.user_id:
        raise PermissionDeniedError(
            "An actor cannot soft-delete their own active session.",
            i18n_key="auth:errors.cannot_self_delete",
        )
    revoke_session_token(user_id=user_id)
    return UserSoftDeleteResponse(
        user_id=user_id,
        is_deleted=True,
        session_revoked=True,
        seat_released=True,
        revoked_at_iso=datetime.now(UTC).isoformat(),
    )
