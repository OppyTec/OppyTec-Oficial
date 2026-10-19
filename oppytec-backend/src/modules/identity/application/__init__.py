"""
oppytec-backend/src/modules/identity/application/__init__.py
Servicios de aplicación para delegación jerárquica RBAC, permisos JIT y Kill-Switch de sesión en Redis.
"""
from __future__ import annotations

from src.modules.identity.application.delegation_service import (
    DelegationRequest,
    RbacDelegationService,
)
from src.modules.identity.application.session_killswitch import (
    SessionKillSwitchResult,
    SessionKillSwitchService,
)

__all__ = [
    "DelegationRequest",
    "RbacDelegationService",
    "SessionKillSwitchResult",
    "SessionKillSwitchService",
]
