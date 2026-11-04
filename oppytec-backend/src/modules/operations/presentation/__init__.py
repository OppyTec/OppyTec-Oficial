"""Capas de presentación (`router.py`, `router_approvals.py`, `router_actividades.py`, `schemas.py`) del módulo `operations`."""
from __future__ import annotations

from src.modules.operations.presentation.router import router
from src.modules.operations.presentation.router_actividades import router as actividades_router
from src.modules.operations.presentation.router_approvals import router as approvals_router

__all__ = ["router", "approvals_router", "actividades_router"]
