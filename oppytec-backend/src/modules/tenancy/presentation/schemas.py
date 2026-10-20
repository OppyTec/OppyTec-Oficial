"""
oppytec-backend/src/modules/tenancy/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`) para Holdings, Tenants, Cupos de Usuarios (`Seats`) y Almacenamiento R2 (`Storage`).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


class HoldingCreateRequest(BaseModel):
    """Solicitud de alta de un Holding empresarial en `public.holdings`."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, max_length=150)
    plan_slug: str = Field(default="pro", pattern=r"^[a-z0-9_-]+$")
    max_active_users: int = Field(default=25, ge=1, le=10000)
    max_storage_mb: int = Field(default=2048, ge=64, le=1048576)

    @field_validator("name")
    @classmethod
    def _sanitize_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="name")


class HoldingResponse(BaseModel):
    """Respuesta de un Holding empresarial registrado."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str
    name: str
    plan_slug: str
    max_active_users: int
    max_storage_mb: int


class TenantCreateRequest(BaseModel):
    """Solicitud de alta y aprovisionamiento de una sucursal (`tenant_*`)."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(..., min_length=2, max_length=120)
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_]+$")
    display_name: str = Field(..., min_length=2, max_length=150)
    base_currency: str = Field(default="CLP", min_length=3, max_length=3)

    @field_validator("display_name")
    @classmethod
    def _sanitize_display_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="display_name")


class TenantResponse(BaseModel):
    """Respuesta con esquema PostgreSQL aprovisionado para la sucursal."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    holding_id: str
    schema_name: str
    display_name: str
    base_currency: str


class SeatQuotaStatusResponse(BaseModel):
    """Estado de cupos de usuarios activos (`is_deleted == False`) frente al límite del plan."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str
    active_non_deleted_users: int
    soft_deleted_historical_users: int
    effective_max_users: int
    remaining_seats: int
    can_create_or_restore: bool


class StorageQuotaStatusResponse(BaseModel):
    """Estado de cuota de almacenamiento multimedia en Cloudflare R2 (`max_storage_mb`)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    current_used_bytes: int
    effective_max_storage_mb: int
    effective_max_storage_bytes: int
    remaining_bytes: int
    allowed: bool


class LegalEntityCreateRequest(BaseModel):
    """Solicitud de alta de una Entidad Legal (RUT/Tax ID) asociada a un Holding."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(..., min_length=2, max_length=120)
    tax_id: str = Field(..., min_length=3, max_length=50)
    legal_name: str = Field(..., min_length=2, max_length=200)

    @field_validator("legal_name")
    @classmethod
    def _sanitize_legal_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="legal_name")


class LegalEntityResponse(BaseModel):
    """Respuesta de una Entidad Legal registrada."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str
    holding_id: str
    tax_id: str
    legal_name: str


class TenancyDashboardSummaryResponse(BaseModel):
    """Conteo consolidado de recursos globales para el Dashboard de Administración."""

    model_config = ConfigDict(extra="forbid")

    holdings: int = 0
    legal_entities: int = 0
    tenants: int = 0
    users: int = 1

