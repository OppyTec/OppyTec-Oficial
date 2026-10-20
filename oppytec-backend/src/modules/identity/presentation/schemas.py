"""
oppytec-backend/src/modules/identity/presentation/schemas.py
Esquemas Pydantic v2 estrictos (`extra="forbid"`) para autenticación, roles, delegación JIT y Soft-Delete.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión para `/api/v1/auth/login`."""

    model_config = ConfigDict(extra="forbid")

    username_or_email: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=4, max_length=256)
    tenant_id: str | None = Field(default=None, max_length=64)
    is_admin_login: bool = Field(default=False)

    @field_validator("username_or_email")
    @classmethod
    def _sanitize_username(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="username_or_email")


class RefreshTokenRequest(BaseModel):
    """Solicitud de rotación de token para `/api/v1/auth/refresh`."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., min_length=16)


class AuthenticatedUserProfileResponse(BaseModel):
    """Perfil del usuario autenticado (SuperUser Génesis, Global Staff o Trabajador de Tenant)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    role: str = "propietario"
    is_superuser: bool = False
    is_global_admin: bool = False
    tipo_usuario: str = "GLOBAL"
    tenant_id: str | None = None
    holding_id: str | None = None
    permissions: list[str] = Field(default_factory=list)


class TokenPairResponse(BaseModel):
    """Par de tokens JWT emitidos tras login o refresh."""

    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int = 1800
    user_id: int
    tenant_id: str | None = None
    holding_id: str | None = None
    hierarchy_rank: int
    user: AuthenticatedUserProfileResponse | None = None


class RoleUpsertRequest(BaseModel):
    """Creación o actualización de un rol con rango jerárquico."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9_]+$")
    name: str = Field(..., min_length=2, max_length=120)
    hierarchy_rank: int = Field(..., ge=0, le=1000)
    permissions: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _sanitize_role_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="name")


class RoleResponse(BaseModel):
    """Representación de un rol en el plano activo."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    hierarchy_rank: int
    permissions: list[str]


class JitGrantCreateRequest(BaseModel):
    """Solicitud de concesión temporal Just-In-Time (JIT) o restricción `DENY`."""

    model_config = ConfigDict(extra="forbid")

    target_user_id: int = Field(..., gt=0)
    target_rank: int = Field(..., ge=0, le=1000)
    permission_code: str = Field(
        ...,
        pattern=r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$",
    )
    effect: Literal["ALLOW", "DENY"] = "ALLOW"
    reason: str = Field(..., min_length=10, max_length=500)
    expires_at: datetime | None = None
    max_uses: int | None = Field(default=None, ge=1, le=1000)

    @field_validator("reason")
    @classmethod
    def _sanitize_reason(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="reason")


class JitGrantResponse(BaseModel):
    """Concesión temporal JIT emitida con trazabilidad forense."""

    model_config = ConfigDict(extra="forbid")

    grant_id: str
    user_id: int
    permission_code: str
    effect: Literal["ALLOW", "DENY"]
    granted_by_user_id: int
    reason: str
    used_count: int
    max_uses: int | None = None
    is_revoked: bool


class UserSoftDeleteRequest(BaseModel):
    """Solicitud de baja lógica (`Soft-Delete`) de un trabajador con liberación de cupo."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="Baja operativa de trabajador", min_length=5, max_length=300)

    @field_validator("reason")
    @classmethod
    def _sanitize_delete_reason(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="reason")


class UserSoftDeleteResponse(BaseModel):
    """Resultado de aplicar `Soft-Delete` y ejecutar el Kill-Switch de sesión."""

    model_config = ConfigDict(extra="forbid")

    user_id: int
    is_deleted: bool
    session_revoked: bool
    seat_released: bool
    revoked_at_iso: str
