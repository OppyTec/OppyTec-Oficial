"""
oppytec-backend/src/api/platform_admin_sandbox.py
Enrutador canónico para la Consola "Lab & QA Sandbox" de Platform Admin.
Re-exporta la implementación del router modularizado en `src.modules.tenancy.presentation.sandbox_router`.
"""
from __future__ import annotations

from src.modules.tenancy.presentation.sandbox_router import (
    _sandbox_service,
    get_sandbox_service,
    router,
)

__all__ = ["_sandbox_service", "get_sandbox_service", "router"]
