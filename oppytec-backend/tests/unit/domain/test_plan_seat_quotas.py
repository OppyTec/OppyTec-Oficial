"""Cupos de usuarios del plan: soft-delete libera cupo, precedencia de overrides, cardinalidad."""
from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.modules.tenancy.domain.quotas import (
    ClientUserSeatState,
    evaluate_seat_quota_for_new_or_restored_user,
    resolve_effective_max_users,
)

pytestmark = pytest.mark.unit


def test_override_precedence() -> None:
    """tenant > holding > plan."""
    assert resolve_effective_max_users(plan_max_active_users=5, holding_override=8, tenant_override=12) == 12
    assert resolve_effective_max_users(plan_max_active_users=5, holding_override=8) == 8
    assert resolve_effective_max_users(plan_max_active_users=5) == 5


@given(active=st.integers(0, 30), deleted=st.integers(0, 30), plan=st.integers(1, 30))
def test_soft_deleted_never_consume_seats(active: int, deleted: int, plan: int) -> None:
    """Solo los activos consumen cupo; los eliminados lógicamente no."""
    users = [ClientUserSeatState(i, "h1", False) for i in range(active)]
    users += [ClientUserSeatState(1000 + i, "h1", True) for i in range(deleted)]
    ev = evaluate_seat_quota_for_new_or_restored_user(existing_users=users, plan_max_active_users=plan)
    assert ev.allowed is (active < plan)
    assert ev.active_non_deleted_users == active
    assert ev.soft_deleted_users == deleted
    assert ev.remaining_seats == max(0, plan - active)
