"""
Pruebas unitarias 1:1 para `src/modules/identity/` y `src/core/bootstrap.py`.
Verifica separación `PublicBase` vs `TenantBase`, `SoftDeleteMixin` y semilla del SuperUser Génesis.
"""
from __future__ import annotations

import pytest

from src.core.bootstrap import (
    GLOBAL_BASE_ROLES,
    TENANT_BASE_ROLES,
    build_genesis_superuser_manifest,
    verify_genesis_password,
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
