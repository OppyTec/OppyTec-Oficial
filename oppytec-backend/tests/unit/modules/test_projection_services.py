"""
Unit test stub/link for module test parity in projection module.
"""
from __future__ import annotations

from src.modules.projection.domain import (
    UrgencyStatus,
    ProjectionHorizon,
    simulate_fefo_projection,
)


def test_projection_module_baseline() -> None:
    assert UrgencyStatus.NORMAL.value == "normal"
    assert ProjectionHorizon.DAYS_30.value == 30
