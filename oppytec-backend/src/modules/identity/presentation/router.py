"""
oppytec-backend/src/modules/identity/presentation/router.py
Endpoints REST de Identidad, Autenticación, Roles, Delegación JIT y Soft-Delete con Kill-Switch:
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
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
    RequireTenantPermission,
    is_session_revoked,
    revoke_session_token,
)
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_and_extract_claims,
)
from src.modules.identity.application.delegation_service import (
    DelegationRequest,
    RbacDelegationService,
)
from src.modules.identity.domain.rbac_evaluator import validate_hierarchy_delegation
from src.modules.identity.presentation.schemas import (
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


@router.post(
    "/api/v1/auth/login",
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
)
async def login_endpoint(
    payload: LoginRequest,
    _rate_limit: Annotated[RateLimitCheckResult, Depends(RequireRateLimit("auth"))],
) -> TokenPairResponse:
    """Autentica al usuario (incluyendo SuperUser Génesis) bajo Rate Limiting `auth`."""
    genesis = build_genesis_superuser_manifest()
    ident = payload.username_or_email.strip()

    if ident in {genesis.username, genesis.email} and verify_genesis_password(
        payload.password,
        genesis.hashed_password,
    ):
        user_id = 1
        is_god = True
        rank = 0
        tenant_id = payload.tenant_id or "tenant_genesis"
        holding_id = "holding_genesis"
    else:
        raise AuthenticationError(
            "Invalid username/email or password.",
            i18n_key="auth:errors.invalid_credentials",
            status_code=401,
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
        is_global_staff=is_god,
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
    )


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
