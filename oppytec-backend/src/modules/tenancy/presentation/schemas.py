"""
oppytec-backend/src/modules/tenancy/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`) para Holdings, Entidades Legales, Tenants,
Planes Comerciales con Cuotas Paramétricas, Usuarios Clientes, Impersonación de Soporte y Resumen de Cuotas.
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input
from src.modules.tenancy.domain.quotas import QuotaHealthStatus, QuotaResourceType


class HoldingCreateRequest(BaseModel):
    """Solicitud de alta de un Holding empresarial en `public.holdings`."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, max_length=150)
    plan_slug: str = Field(default="basic", pattern=r"^[a-z0-9_-]+$")
    max_active_users: int = Field(default=25, ge=1, le=10000)
    max_storage_mb: int = Field(default=2048, ge=64, le=1048576)
    custom_max_users_override: int | None = Field(default=None, ge=1, le=100000)
    custom_max_products_override: int | None = Field(default=None, ge=0, le=1000000)
    custom_max_suppliers_override: int | None = Field(default=None, ge=0, le=100000)
    custom_max_recipes_override: int | None = Field(default=None, ge=0, le=100000)
    custom_max_combos_override: int | None = Field(default=None, ge=0, le=100000)
    custom_storage_mb_override: int | None = Field(default=None, ge=64, le=1048576)

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
    custom_max_users_override: int | None = None
    custom_max_products_override: int | None = None
    custom_max_suppliers_override: int | None = None
    custom_max_recipes_override: int | None = None
    custom_max_combos_override: int | None = None
    custom_storage_mb_override: int | None = None


class TenantCreateRequest(BaseModel):
    """Solicitud de alta y aprovisionamiento de una sucursal (`tenant_*`)."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(..., min_length=2, max_length=120)
    legal_entity_id: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_]+$")
    display_name: str = Field(..., min_length=2, max_length=150)
    base_currency: str = Field(default="CLP", min_length=3, max_length=3)
    enabled_modules: list[str] | None = Field(default=None)
    custom_max_users_override: int | None = Field(default=None, ge=1, le=100000)
    custom_max_products_override: int | None = Field(default=None, ge=0, le=1000000)
    custom_max_suppliers_override: int | None = Field(default=None, ge=0, le=100000)
    custom_max_recipes_override: int | None = Field(default=None, ge=0, le=100000)
    custom_max_combos_override: int | None = Field(default=None, ge=0, le=100000)
    custom_storage_mb_override: int | None = Field(default=None, ge=64, le=1048576)

    @field_validator("display_name")
    @classmethod
    def _sanitize_display_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="display_name")


class TenantResponse(BaseModel):
    """Respuesta con esquema PostgreSQL aprovisionado para la sucursal."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    holding_id: str
    legal_entity_id: str | None = None
    schema_name: str
    display_name: str
    base_currency: str
    enabled_modules: list[str] = Field(default_factory=list)
    custom_max_users_override: int | None = None
    custom_max_products_override: int | None = None
    custom_max_suppliers_override: int | None = None
    custom_max_recipes_override: int | None = None
    custom_max_combos_override: int | None = None
    custom_storage_mb_override: int | None = None


class TenantModulesAndQuotasUpdateRequest(BaseModel):
    """Solicitud de actualización de módulos/submódulos y overrides de capacidad de un Tenant."""

    model_config = ConfigDict(extra="forbid")

    enabled_modules: list[str] = Field(default_factory=list)
    custom_max_users_override: int | None = Field(default=None, ge=1, le=100000)
    custom_max_products_override: int | None = Field(default=None, ge=0, le=1000000)
    custom_max_suppliers_override: int | None = Field(default=None, ge=0, le=100000)
    custom_max_recipes_override: int | None = Field(default=None, ge=0, le=100000)
    custom_max_combos_override: int | None = Field(default=None, ge=0, le=100000)
    custom_storage_mb_override: int | None = Field(default=None, ge=64, le=1048576)


class SystemPlanUpsertRequest(BaseModel):
    """Solicitud de creación o actualización de un Plan Comercial (`public.system_plans`)."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=2, max_length=120)
    max_active_users: int = Field(default=5, ge=1, le=100000)
    max_products: int = Field(default=500, ge=0, le=1000000)
    max_suppliers: int = Field(default=20, ge=0, le=100000)
    max_recipes: int = Field(default=0, ge=0, le=100000)
    max_combos: int = Field(default=0, ge=0, le=100000)
    max_storage_mb: int = Field(default=512, ge=64, le=1048576)
    included_modules: list[str] = Field(default_factory=list)
    anchor_currency: Literal["CLP", "USD", "EUR", "BRL"] = "CLP"
    price_clp: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    price_usd: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    price_eur: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    price_brl: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    auto_convert_fx: bool = True

    @field_validator("name")
    @classmethod
    def _sanitize_plan_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="name")


class SystemPlanResponse(BaseModel):
    """Respuesta de un Plan Comercial con sus 6 cuotas paramétricas y precios multi-moneda `Decimal`."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    max_active_users: int
    max_products: int
    max_suppliers: int
    max_recipes: int
    max_combos: int
    max_storage_mb: int
    included_modules: list[str]
    anchor_currency: str = "CLP"
    price_clp: Decimal
    price_usd: Decimal
    price_eur: Decimal
    price_brl: Decimal
    auto_convert_fx: bool = True


class ClientUserCreateRequest(BaseModel):
    """Solicitud de creación de un Usuario Cliente asignado a un Holding y 1..N Tenants."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(..., min_length=2, max_length=120)
    tenant_id: str = Field(..., min_length=2, max_length=120)
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(default="Operador", min_length=1, max_length=100)
    last_name: str = Field(default="Cliente", min_length=1, max_length=100)
    role_slug: Literal["propietario", "superuser", "admin", "supervisor", "cajero"] = "admin"
    is_holding_owner: bool = False

    @field_validator("first_name", "last_name")
    @classmethod
    def _sanitize_person_names(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="person_name")


class ClientUserAdminResponse(BaseModel):
    """Respuesta de un Usuario Cliente registrado en el Holding/Tenant."""

    model_config = ConfigDict(extra="forbid")

    user_id: int
    holding_id: str
    tenant_id: str
    username: str
    email: str
    first_name: str
    last_name: str
    role_slug: str
    hierarchy_rank: int
    is_holding_owner: bool
    is_deleted: bool = False


class AdminImpersonateRequest(BaseModel):
    """Solicitud auditada de soporte para 'Entrar como Local' (`Impersonation`)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(..., min_length=2, max_length=120)
    reason: str = Field(
        default="Soporte técnico e inspección operativa autorizada",
        min_length=5,
        max_length=250,
    )

    @field_validator("reason")
    @classmethod
    def _sanitize_reason(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="reason")


class AdminImpersonateResponse(BaseModel):
    """Respuesta con token temporal de soporte acotado al `tenant_id` objetivo."""

    model_config = ConfigDict(extra="forbid")

    access_token: str
    tenant_id: str
    holding_id: str
    schema_name: str
    impersonated_by_user_id: int
    reason: str


class SeatQuotaStatusResponse(BaseModel):
    """Estado de cupos de usuarios activos (`is_deleted == False`) frente al límite del plan."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str
    active_non_deleted_users: int
    soft_deleted_historical_users: int
    effective_max_users: int
    remaining_seats: int
    usage_percentage: Decimal = Field(default=Decimal("0.00"))
    can_create_or_restore: bool


class StorageQuotaStatusResponse(BaseModel):
    """Estado de cuota de almacenamiento multimedia en Cloudflare R2 (`max_storage_mb`)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    current_used_bytes: int
    effective_max_storage_mb: int
    effective_max_storage_bytes: int
    remaining_bytes: int
    usage_percentage: Decimal = Field(default=Decimal("0.00"))
    allowed: bool


class ResourceQuotaItemResponse(BaseModel):
    """Estado individual de una cuota de capacidad con semáforo (`NORMAL`/`WARNING`/`CRITICAL`/`OVER_QUOTA`)."""

    model_config = ConfigDict(extra="forbid")

    resource_type: QuotaResourceType
    active_count: int
    soft_deleted_count: int
    effective_max_limit: int
    remaining_capacity: int
    usage_percentage: Decimal
    status: QuotaHealthStatus
    allowed: bool


class TenantQuotaSummaryResponse(BaseModel):
    """Resumen consolidado de las 6 cuotas de capacidad del Plan + Overrides para la UI del cliente."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str
    tenant_id: str
    plan_slug: str
    resources: dict[QuotaResourceType, ResourceQuotaItemResponse]


class LegalEntityCreateRequest(BaseModel):
    """Solicitud de alta de una Entidad Legal (RUT/Tax ID) asociada a un Holding."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(..., min_length=2, max_length=120)
    tax_id: str = Field(..., min_length=3, max_length=50)
    legal_name: str = Field(..., min_length=2, max_length=200)
    legal_address: str | None = Field(default=None, max_length=255)

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
    legal_address: str | None = None
    is_active: bool = True


class TenancyDashboardSummaryResponse(BaseModel):
    """Conteo consolidado de recursos globales para el Dashboard de Administración."""

    model_config = ConfigDict(extra="forbid")

    holdings: int = 0
    legal_entities: int = 0
    tenants: int = 0
    users: int = 1
    plans: int = 3
    client_users: int = 0
