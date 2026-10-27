"""
oppytec-backend/src/modules/tenancy/presentation/schemas_platform_admin.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` estricto) para:
- Administración de Planes Comerciales (`/api/v1/platform-admin/plans`).
- Política Global de Conversión SaaS & FinOps (`/api/v1/platform-admin/ai-credits/policy`).
- Consola FinOps de Consumo de Tokens & Créditos (`/api/v1/platform-admin/token-consumption`).
- Modales de Ajuste de Cupos de Créditos IA (`/ai-credits`).
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input

# ============================================================================
# 1. POLÍTICA GLOBAL SAAS (CONVERSIÓN TOKENS A CRÉDITOS & PRECIOS EXTRA)
# ============================================================================


class SaaSAIPolicyResponse(BaseModel):
    """Configuración activa de la política global de créditos de IA."""

    model_config = ConfigDict(extra="forbid")

    tokens_per_credit: int
    default_monthly_credits: int
    credit_price_clp: Decimal
    credit_price_usd: Decimal
    updated_at: datetime
    updated_by: int | None = None


class SaaSAIPolicyUpdateRequest(BaseModel):
    """Actualización atómica de la política global de créditos de IA."""

    model_config = ConfigDict(extra="forbid")

    tokens_per_credit: int | None = Field(default=None, gt=0)
    default_monthly_credits: int | None = Field(default=None, ge=0)
    credit_price_clp: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    credit_price_usd: Decimal | None = Field(default=None, ge=Decimal("0.0000"))


# ============================================================================
# 2. CATÁLOGO Y ADMINISTRACIÓN DE PLANES COMERCIALES
# ============================================================================


class SystemPlanDetailResponse(BaseModel):
    """Detalle completo de un Plan Comercial con cuotas paramétricas y métricas activas."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    tier: int
    monthly_ai_credits: int
    description: str | None = None
    is_popular: bool = False
    is_active: bool = True
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
    active_clients_count: int = 0


class SystemPlanCreateRequest(BaseModel):
    """Creación de un nuevo Plan Comercial con validaciones anti-XSS y cuotas paramétricas."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    tier: int = Field(default=1, ge=1)
    monthly_ai_credits: int = Field(default=1000, ge=0)
    is_popular: bool = False
    is_active: bool = True
    max_active_users: int = Field(default=10, ge=1)
    max_products: int = Field(default=500, ge=0)
    max_suppliers: int = Field(default=20, ge=0)
    max_recipes: int = Field(default=0, ge=0)
    max_combos: int = Field(default=0, ge=0)
    max_storage_mb: int = Field(default=1024, ge=100)
    included_modules: list[str] = Field(default_factory=list)
    anchor_currency: str = Field(default="CLP", max_length=10)
    price_clp: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    price_usd: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    price_eur: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    price_brl: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    auto_convert_fx: bool = True

    @field_validator("slug", "name", "description")
    @classmethod
    def _sanitize_text_fields(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name=info.field_name)


class SystemPlanUpdateRequest(BaseModel):
    """Actualización de un Plan Comercial existente."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    tier: int | None = Field(default=None, ge=1)
    monthly_ai_credits: int | None = Field(default=None, ge=0)
    is_popular: bool | None = None
    is_active: bool | None = None
    max_active_users: int | None = Field(default=None, ge=1)
    max_products: int | None = Field(default=None, ge=0)
    max_suppliers: int | None = Field(default=None, ge=0)
    max_recipes: int | None = Field(default=None, ge=0)
    max_combos: int | None = Field(default=None, ge=0)
    max_storage_mb: int | None = Field(default=None, ge=100)
    included_modules: list[str] | None = None
    price_clp: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    price_usd: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    price_eur: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    price_brl: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    auto_convert_fx: bool | None = None

    @field_validator("name", "description")
    @classmethod
    def _sanitize_update_texts(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        return sanitize_text_input(value, field_name=info.field_name)


# ============================================================================
# 3. MODALES DE AJUSTE DE CUPOS DE CRÉDITOS IA
# ============================================================================


class HoldingCreditsUpdateRequest(BaseModel):
    """Ajuste de cuota mensual y modo de bolsa de créditos a nivel de Holding."""

    model_config = ConfigDict(extra="forbid")

    monthly_credits: int = Field(..., ge=0)
    distribution_mode: Literal["shared", "per_tenant"] = "shared"


class TenantCreditsUpdateRequest(BaseModel):
    """Ajuste de cuota mensual individual de créditos para una sucursal (Tenant)."""

    model_config = ConfigDict(extra="forbid")

    monthly_credits: int = Field(..., ge=0)


class CreditQuotaAdjustmentResponse(BaseModel):
    """Confirmación del ajuste de cupo de créditos."""

    model_config = ConfigDict(extra="forbid")

    target_id: str
    target_type: Literal["holding", "tenant"]
    monthly_credits: int
    distribution_mode: str | None = None
    message: str = "Cuota de créditos de IA actualizada exitosamente"


# ============================================================================
# 4. CONSOLA FINOPS DE CONSUMO DE TOKENS & CRÉDITOS
# ============================================================================


class TokenLogItemResponse(BaseModel):
    """Registro individual de telemetría de llamada a IA."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime
    holding_id: str
    holding_name: str
    tenant_id: str
    tenant_name: str
    user_id: int
    user_name: str
    caller_feature: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: Decimal
    estimated_cost_clp: Decimal
    credits_deducted: Decimal
    request_duration_ms: int
    api_success: bool
    error_message: str | None = None


class TenantGroupResponse(BaseModel):
    """Grupo acumulado de consumo de una sucursal / tenant."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    tenant_name: str
    total_requests: int
    total_tokens: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal
    estimated_cost_clp: Decimal
    monthly_credit_limit: int
    credits_used: int
    credits_remaining: int
    credit_usage_pct: Decimal
    logs: list[TokenLogItemResponse]


class HoldingGroupResponse(BaseModel):
    """Grupo acumulado de consumo de un Holding corporativo."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str
    holding_name: str
    total_requests: int
    total_tokens: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal
    estimated_cost_clp: Decimal
    monthly_credit_limit: int
    credit_distribution_mode: str
    credits_used: int
    credits_remaining: int
    credit_usage_pct: Decimal
    tenants: list[TenantGroupResponse]


class TokenConsumptionSummaryResponse(BaseModel):
    """Resumen consolidado para la Consola FinOps de consumo de tokens y créditos."""

    model_config = ConfigDict(extra="forbid")

    holdings: list[HoldingGroupResponse]
    logs: list[TokenLogItemResponse]
    total_records: int
    total_tokens_all: int
    total_cost_usd_all: Decimal
    total_cost_clp_all: Decimal
    total_credits_used_all: int
    tokens_per_credit: int
    page: int
    page_size: int
