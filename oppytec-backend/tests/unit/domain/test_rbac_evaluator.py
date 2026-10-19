"""Pruebas del evaluador RBAC Dual de 3 niveles (M_Plan ∩ ((P_Rol U P_Temp) \\ DENY))."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.modules.identity.domain.rbac_evaluator import (
    PermissionGrantSpec,
    compute_effective_permissions,
    evaluate_permission_access,
    is_grant_currently_active,
    is_valid_three_level_permission,
)

pytestmark = pytest.mark.unit

NOW = datetime(2030, 1, 1, tzinfo=UTC)


def _grant(effect: str, code: str = "inventory.kardex.read", **kw: object) -> PermissionGrantSpec:
    base: dict[str, object] = {
        "grant_id": "g1", "user_id": 5, "permission_code": code, "effect": effect,
        "granted_by_user_id": 1, "reason": "motivo suficiente",
    }
    base.update(kw)
    return PermissionGrantSpec(**base)  # type: ignore[arg-type]


def test_three_level_validation() -> None:
    """Solo `<modulo>.<submodulo>.<funcion>` es válido."""
    assert is_valid_three_level_permission("inventory.kardex.read")
    assert not is_valid_three_level_permission("inventory.kardex")
    assert not is_valid_three_level_permission("Inventory.Kardex.Read")


def test_role_permission_allowed_and_plan_ceiling_blocks() -> None:
    """El techo del plan bloquea permisos de módulos no contratados."""
    ok = evaluate_permission_access(
        actor_user_id=5, required_permission="inventory.kardex.read",
        plan_enabled_modules={"inventory"}, role_permissions={"inventory.kardex.read"}, now=NOW,
    )
    blocked = evaluate_permission_access(
        actor_user_id=5, required_permission="inventory.kardex.read",
        plan_enabled_modules={"recipes"}, role_permissions={"inventory.kardex.read"}, now=NOW,
    )
    assert ok.allowed and not blocked.allowed


def test_explicit_deny_overrides_role_and_expired_grant_ignored() -> None:
    """DENY explícito vence al rol; un grant expirado no cuenta."""
    perms = compute_effective_permissions(
        plan_enabled_modules={"inventory"}, role_permissions={"inventory.kardex.read"},
        grants=[_grant("DENY")], now=NOW,
    )
    assert "inventory.kardex.read" not in perms
    expired = _grant("ALLOW", code="inventory.kardex.write", expires_at=NOW - timedelta(hours=1))
    assert not is_grant_currently_active(expired, NOW)
    perms2 = compute_effective_permissions(
        plan_enabled_modules={"inventory"}, role_permissions=set(), grants=[expired], now=NOW,
    )
    assert not perms2


def test_superuser_god_bypasses_plan() -> None:
    """El SuperUser tiene todo el catálogo sin techo de plan."""
    perms = compute_effective_permissions(
        plan_enabled_modules=set(), role_permissions=set(), is_superuser_god=True,
        all_catalog_permissions={"inventory.kardex.read"}, now=NOW,
    )
    assert perms == frozenset({"inventory.kardex.read"})


def test_invalid_permission_raises() -> None:
    """Un código mal formado lanza ValueError."""
    with pytest.raises(ValueError):
        evaluate_permission_access(
            actor_user_id=1, required_permission="bad", plan_enabled_modules=set(), role_permissions=set(),
        )


@given(deny=st.booleans())
def test_deny_always_wins(deny: bool) -> None:
    """Propiedad: con DENY activo jamás se concede el acceso."""
    grants = [_grant("DENY")] if deny else []
    dec = evaluate_permission_access(
        actor_user_id=5, required_permission="inventory.kardex.read", plan_enabled_modules={"inventory"},
        role_permissions={"inventory.kardex.read"}, grants=grants, now=NOW,
    )
    assert dec.allowed is (not deny)
