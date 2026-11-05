"""
Pruebas unitarias 1:1 para `src/modules/identity/` y `src/core/bootstrap.py`.
Verifica separación `PublicBase` vs `TenantBase`, `SoftDeleteMixin` y semilla del SuperUser Génesis.
"""
from __future__ import annotations

import pytest
from starlette.requests import Request

from src.core.bootstrap import (
    GLOBAL_BASE_ROLES,
    TENANT_BASE_ROLES,
    build_genesis_superuser_manifest,
    verify_genesis_password,
)
from src.core.exceptions import AuthenticationError
from src.core.guards.rate_limiter import RateLimitCheckResult
from src.core.guards.rbac_dependencies import (
    RequireHoldingPermission,
    decode_access_token,
)
from src.modules.identity.infrastructure.models import (
    Cargo,
    GlobalPermission,
    GlobalRole,
    GlobalUser,
    Permission,
    Role,
    UserPermissionGrant,
)
from src.modules.identity.presentation.router import login_endpoint
from src.modules.identity.presentation.schemas import LoginRequest
from src.shared.models_base import PublicBase, TenantBase

pytestmark = pytest.mark.unit


def test_identity_models_schema_separation_and_soft_delete() -> None:
    """Verifica que `GlobalUser`/`GlobalRole` pertenezcan a `public` y `Role`/`Cargo` a `TenantBase`."""
    assert GlobalUser.__table__.schema == "public"
    assert GlobalRole.__table__.schema == "public"
    assert GlobalPermission.__table__.schema == "public"
    assert "public.global_users" in PublicBase.metadata.tables

    assert Role.__table__.schema is None
    assert Cargo.__table__.schema is None
    assert Permission.__table__.schema is None
    assert "roles" in TenantBase.metadata.tables
    assert "user_permission_grants" in TenantBase.metadata.tables

    user = GlobalUser(
        email="worker@oppytec.com",
        username="worker.oppy",
        hashed_password="argon2_hashed_value",
    )
    user.mark_soft_deleted(by_user_id=1)
    assert user.is_deleted is True
    assert user.deleted_by == 1
    assert user.deleted_at is not None

    user.restore_soft_deleted()
    assert user.is_deleted is False
    assert user.deleted_by is None
    assert user.deleted_at is None


def test_genesis_bootstrap_reads_settings_and_hashes_password() -> None:
    """Verifica que el bootstrapper Génesis hashee la contraseña con Argon2id y defina los roles base."""
    manifest = build_genesis_superuser_manifest()
    assert manifest.email == "oppytec.admin@gmail.com"
    assert manifest.username == "oppytec.admin"
    assert manifest.is_superuser_god is True
    assert manifest.hashed_password != "OppyTec_Genesis_Local_Safe_Pass_2026!"
    assert verify_genesis_password(
        "OppyTec_Genesis_Local_Safe_Pass_2026!",
        manifest.hashed_password,
    )

    global_slugs = [r.slug for r in GLOBAL_BASE_ROLES]
    assert global_slugs == ["superuser", "admin", "supervisor", "developer"]

    tenant_slugs = [r.slug for r in TENANT_BASE_ROLES]
    assert tenant_slugs == ["propietario", "superuser", "admin", "supervisor", "cajero"]

    jit_grant = UserPermissionGrant(
        user_id=7,
        permission_code="inventory.mermas.approve",
        effect="ALLOW",
        granted_by_user_id=1,
        reason="Delegación temporal turno noche",
    )
    assert jit_grant.permission_code == "inventory.mermas.approve"


@pytest.mark.asyncio
async def test_client_holding_owner_login_passwords_and_holding_access() -> None:
    """
    Verifica que el usuario cliente 101 (admin.local@restaurant.cl) pueda iniciar sesión
    con cualquiera de las contraseñas autorizadas ('oppytec2026', 'OppyTec#2026', 'oppytec.2026'),
    obteniendo el rol 'propietario', 'is_holding_owner=True', permisos 'holding.*.*' y
    acceso exitoso a RequireHoldingPermission('holding.hub.view').
    """
    rl = RateLimitCheckResult(
        allowed=True,
        profile="auth",
        namespaced_key="test-client-login",
        limit=20,
        remaining=19,
        retry_after_seconds=0,
    )

    valid_passwords = ["oppytec2026", "OppyTec#2026", "oppytec.2026"]
    guard = RequireHoldingPermission("holding.hub.view")

    for password in valid_passwords:
        req = LoginRequest(
            username_or_email="admin.local@restaurant.cl",
            password=password,
        )
        token_pair = await login_endpoint(payload=req, _rate_limit=rl)
        assert token_pair.user_id == 101
        assert token_pair.holding_id == "holding_genesis"
        assert token_pair.user.role == "propietario"
        assert "holding.*.*" in token_pair.user.permissions

        claims = decode_access_token(token_pair.access_token)
        assert claims.is_holding_owner is True
        assert claims.holding_id == "holding_genesis"

        # Validar autorización ante RequireHoldingPermission
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {token_pair.access_token}".encode("utf-8"))],
        }
        principal = await guard(Request(scope))
        assert principal.user_id == 101
        assert principal.is_holding_owner is True
        assert principal.holding_id == "holding_genesis"

    # Validar que una contraseña incorrecta sea rechazada con 401
    with pytest.raises(AuthenticationError):
        bad_req = LoginRequest(
            username_or_email="admin.local@restaurant.cl",
            password="incorrect_password_123",
        )
        await login_endpoint(payload=bad_req, _rate_limit=rl)
