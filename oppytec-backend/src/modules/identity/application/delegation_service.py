"""
oppytec-backend/src/modules/identity/application/delegation_service.py
Servicio de aplicación para otorgar, revocar y consumir permisos temporales Just-In-Time (JIT)
cumpliendo las 3 leyes de `hierarchy_rank` y registrando el motivo obligatorio (>= 10 caracteres).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from src.core.exceptions import PermissionDeniedError
from src.modules.identity.domain.rbac_evaluator import (
    GrantEffectType,
    PermissionGrantSpec,
    can_delegate_permission,
    is_grant_currently_active,
)


@dataclass(frozen=True)
class DelegationRequest:
    """Solicitud tipada para otorgar un permiso temporal JIT o una restricción `DENY`."""

    actor_user_id: int
    actor_rank: int
    target_user_id: int
    target_rank: int
    permission_code: str
    effect: GrantEffectType
    reason: str
    actor_effective_permissions: frozenset[str]
    expires_at: datetime | None = None
    max_uses: int | None = None
    is_global_scope: bool = False
    is_superuser_or_owner_rank_zero: bool = False


class RbacDelegationService:
    """
    Coordina la delegación jerárquica y el ciclo de vida de permisos JIT (`PermissionGrantSpec`),
    incluyendo autodestrucción al alcanzar `max_uses`.
    """

    def __init__(self) -> None:
        self._grants_by_id: dict[str, PermissionGrantSpec] = {}

    def issue_permission_grant(
        self,
        request: DelegationRequest,
        *,
        now: datetime | None = None,
    ) -> PermissionGrantSpec:
        """
        Valida las 3 leyes de delegación jerárquica y el motivo obligatorio (>= 10 caracteres)
        antes de emitir el `PermissionGrantSpec`.
        """
        cleaned_reason = request.reason.strip()
        if len(cleaned_reason) < 10:
            raise PermissionDeniedError(
                "Temporary permission grant reason must contain at least 10 characters.",
                i18n_key="auth:errors.grant_reason_too_short",
            )
        if request.max_uses is not None and request.max_uses < 1:
            raise PermissionDeniedError(
                "Temporary permission max_uses must be >= 1 when specified.",
                i18n_key="auth:errors.invalid_grant_max_uses",
            )

        allowed, reason_code = can_delegate_permission(
            actor_rank=request.actor_rank,
            target_rank=request.target_rank,
            permission_to_grant=request.permission_code,
            actor_effective_permissions=request.actor_effective_permissions,
            is_global_scope=request.is_global_scope,
            is_superuser_or_owner_rank_zero=request.is_superuser_or_owner_rank_zero,
        )
        if not allowed:
            raise PermissionDeniedError(
                f"Delegation denied ({reason_code}): actor rank {request.actor_rank} cannot grant "
                f"'{request.permission_code}' to target rank {request.target_rank}.",
                i18n_key="auth:errors.delegation_forbidden",
                error_code=reason_code,
            )

        issued_now = now or datetime.now(UTC)
        grant_id = str(uuid.uuid4())
        grant = PermissionGrantSpec(
            grant_id=grant_id,
            user_id=request.target_user_id,
            permission_code=request.permission_code.strip(),
            effect=request.effect,
            granted_by_user_id=request.actor_user_id,
            reason=cleaned_reason,
            starts_at=issued_now,
            expires_at=request.expires_at,
            max_uses=request.max_uses,
            used_count=0,
            is_revoked=False,
        )
        self._grants_by_id[grant_id] = grant
        return grant

    def consume_grant_use(
        self,
        grant_id: str,
        *,
        now: datetime | None = None,
    ) -> PermissionGrantSpec:
        """
        Incrementa `used_count` de un permiso JIT tras completar la acción autorizada.
        Si alcanza `max_uses`, marca `is_revoked = True` automáticamente.
        """
        grant = self._grants_by_id.get(grant_id)
        if grant is None:
            raise PermissionDeniedError(
                f"Permission grant '{grant_id}' does not exist.",
                i18n_key="auth:errors.grant_not_found",
            )
        if not is_grant_currently_active(grant, now=now):
            raise PermissionDeniedError(
                f"Permission grant '{grant_id}' is expired or revoked.",
                i18n_key="auth:errors.grant_expired_or_revoked",
            )
        new_used_count = grant.used_count + 1
        auto_revoke = grant.max_uses is not None and new_used_count >= grant.max_uses
        updated = replace(
            grant,
            used_count=new_used_count,
            is_revoked=grant.is_revoked or auto_revoke,
        )
        self._grants_by_id[grant_id] = updated
        return updated

    def revoke_grant(self, grant_id: str) -> PermissionGrantSpec:
        """Revoca inmediatamente una concesión temporal por su `grant_id`."""
        grant = self._grants_by_id.get(grant_id)
        if grant is None:
            raise PermissionDeniedError(
                f"Permission grant '{grant_id}' does not exist.",
                i18n_key="auth:errors.grant_not_found",
            )
        updated = replace(grant, is_revoked=True)
        self._grants_by_id[grant_id] = updated
        return updated

    def list_user_grants(self, user_id: int) -> tuple[PermissionGrantSpec, ...]:
        """Devuelve todas las concesiones registradas para un `user_id`."""
        return tuple(g for g in self._grants_by_id.values() if g.user_id == user_id)
