"""
oppytec-backend/src/core/sandbox/models.py
Modelos y estructuras de datos tipadas para el motor de ejecución aislado (CodeModeSandboxRunner).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.core.exceptions import OppyTecError, PermissionDeniedError

TENANT_SCHEMA_REGEX = re.compile(r"^tenant_[a-z0-9_]{1,64}$")


class SandboxError(OppyTecError):
    """Excepción base para fallos dentro del sandbox de ejecución de Code Mode."""

    default_status_code = 400
    default_error_code = "SANDBOX_ERROR"
    default_i18n_key = "sandbox:errors.execution_error"
    default_title = "Sandbox Execution Error"


class SandboxSecurityError(SandboxError):
    """Violación de seguridad o intento de escape del sandbox."""

    default_status_code = 422
    default_error_code = "SANDBOX_SECURITY_VIOLATION"
    default_i18n_key = "sandbox:errors.security_violation"
    default_title = "Sandbox Security Violation"


class SandboxTimeoutError(SandboxError):
    """Límite de tiempo de cómputo del script excedido (Watchdog timeout)."""

    default_status_code = 504
    default_error_code = "SANDBOX_TIMEOUT_EXCEEDED"
    default_i18n_key = "sandbox:errors.timeout_exceeded"
    default_title = "Sandbox Timeout Exceeded"


class SandboxExecutionError(SandboxError):
    """Error en tiempo de ejecución del script de usuario."""

    default_status_code = 400
    default_error_code = "SANDBOX_SCRIPT_FAILED"
    default_i18n_key = "sandbox:errors.script_failed"
    default_title = "Sandbox Script Failed"


@dataclass(frozen=True)
class SandboxContext:
    """
    Contexto inmutable inyectado en el runtime del Sandbox.
    Asegura linaje de usuario, pertenencia estricta a un único `tenant_*`
    y permisos RBAC de 3 niveles (`<modulo>.<submodulo>.<funcion>`).
    """

    tenant_id: str
    user_id: int
    role_ids: tuple[int, ...] = field(default_factory=tuple)
    hierarchy_rank: int = 1
    permissions: frozenset[str] = field(default_factory=frozenset)
    can_view_costs: bool = False
    is_superuser_god: bool = False
    holding_id: str | None = None
    extra_env: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        raw = self.tenant_id.strip()
        normalized = raw if raw.startswith("tenant_") else f"tenant_{raw}"
        if not TENANT_SCHEMA_REGEX.match(normalized):
            raise SandboxSecurityError(
                f"Esquema de tenant inválido: '{self.tenant_id}'. Debe cumplir formato 'tenant_[a-z0-9_]+'.",
                i18n_key="sandbox:errors.invalid_tenant_format",
            )
        # Inyección inmutable del tenant_id normalizado
        object.__setattr__(self, "tenant_id", normalized)

    def has_permission(self, permission_code: str) -> bool:
        """Verifica si el usuario cuenta con el permiso RBAC de 3 niveles."""
        if self.is_superuser_god:
            return True

        perm = permission_code.strip()
        if (
            perm in self.permissions
            or "*" in self.permissions
            or "*." in self.permissions
            or "*.*" in self.permissions
            or "*.*.*" in self.permissions
        ):
            return True

        parts = perm.split(".")
        if len(parts) >= 2:
            module = parts[0]
            submod = f"{parts[0]}.{parts[1]}"
            if (
                module in self.permissions
                or submod in self.permissions
                or f"{module}.*" in self.permissions
                or f"{submod}.*" in self.permissions
            ):
                return True

        return False

    def check_permission_or_raise(self, permission_code: str) -> None:
        """Lanza `PermissionDeniedError` si el usuario carece del permiso requerido."""
        if not self.has_permission(permission_code):
            raise PermissionDeniedError(
                f"Acceso denegado: Se requiere el permiso RBAC '{permission_code}'.",
                i18n_key="auth:errors.permission_denied",
            )


@dataclass(frozen=True)
class SandboxExecutionResult:
    """Resultado inmutable de la ejecución de un script en el sandbox."""

    success: bool
    result: object = None
    stdout: str = ""
    execution_time_ms: float = 0.0
    error: str | None = None
    error_code: str | None = None
    raw_tokens_estimate: int = 0
    final_tokens_estimate: int = 0
    tokens_saved_estimate: int = 0
