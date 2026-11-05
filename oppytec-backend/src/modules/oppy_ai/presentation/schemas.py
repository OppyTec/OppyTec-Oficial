"""
oppytec-backend/src/modules/oppy_ai/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para el Asistente `OppyFy`:
- Consultas conversacionales medidas (`/api/v1/oppyfy/chat`)
- Traspaso a nuevo hilo al 5% (`/api/v1/oppyfy/threads/{thread_id}/rollover`)
- Catálogo y concesiones RBAC propias editables (`/api/v1/oppyfy/rbac/domains`, `/api/v1/oppyfy/rbac/grants`)
- Billetera de créditos y cupos de trabajadores (`/api/v1/oppyfy/wallets/me`, `/api/v1/oppyfy/wallets/{user_id}`)
- Telemetría FinOps de consumo de tokens (`/api/v1/platform-admin/token-consumption`)
- CRUD de paquetes de créditos IA independientes (`/api/v1/platform-admin/ai-packs`)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


# ============================================================================
# 1. CHAT & CONTEXT HEALTH SCHEMAS
# ============================================================================


class OppyfyChatRequest(BaseModel):
    """Consulta de un trabajador del Tenant hacia `OppyFy`."""

    model_config = ConfigDict(extra="forbid")

    prompt_text: str = Field(..., min_length=2, max_length=2000)
    target_subdomain_slug: str = Field(default="recipes_kitchen", min_length=2, max_length=64)
    can_view_costs: bool = False
    prior_thread_tokens: int = Field(default=0, ge=0, le=500000)
    remaining_credits: Decimal = Field(default=Decimal("50.00"), ge=Decimal("0"))
    estimated_credit_cost: Decimal = Field(default=Decimal("1.00"), gt=Decimal("0"))
    thread_id: uuid.UUID | None = None

    @field_validator("prompt_text", "target_subdomain_slug")
    @classmethod
    def _sanitize_chat_fields(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="oppyfy_prompt")


class OppyfyChatResponse(BaseModel):
    """Respuesta de `OppyFy` con estado RBAC, créditos descontados y salud de contexto."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    status_code: str
    subdomain_slug: str
    answer_text: str
    credits_deducted: Decimal
    remaining_credits: Decimal
    context_usage_percent: Decimal
    requires_new_thread: bool
    tool_executed: str | None = None
    tool_payload: dict[str, Any] | None = None
    trace_id: str | None = None
    message_id: str | None = None


# ============================================================================
# 2. THREAD ROLLOVER SCHEMAS
# ============================================================================


class OppyfyThreadRolloverRequest(BaseModel):
    """Solicitud de rollover hacia un hilo fresco al 5%."""

    model_config = ConfigDict(extra="forbid")

    summary_notes: str | None = Field(default=None, max_length=1000)
    prior_thread_tokens: int = Field(default=8000, ge=0)

    @field_validator("summary_notes")
    @classmethod
    def _sanitize_notes(cls, value: str | None) -> str | None:
        if value:
            return sanitize_text_input(value, field_name="rollover_notes")
        return value


class OppyfyThreadRolloverResponse(BaseModel):
    """Respuesta del traspaso a nuevo hilo fresco al 5% con resumen inteligente."""

    model_config = ConfigDict(extra="forbid")

    new_thread_id: uuid.UUID
    previous_thread_id: uuid.UUID
    fresh_context_usage_percent: Decimal
    summary_artifact: str
    message: str


# ============================================================================
# 3. RBAC DOMAINS & SUBDOMAINS SCHEMAS
# ============================================================================


class OppyfySubdomainItemSchema(BaseModel):
    """Sub-dominio individual dentro de un dominio."""

    model_config = ConfigDict(extra="forbid")

    subdomain_key: str = Field(..., min_length=2, max_length=100)
    name_es: str = Field(..., min_length=2, max_length=150)
    name_en: str = Field(default="", max_length=150)
    allowed_tool_functions: list[str] = Field(default_factory=list)
    can_view_costs_default: bool = False
    is_active: bool = True


class OppyfyDomainCreateRequest(BaseModel):
    """Creación o actualización de un dominio de conocimiento de `OppyFy`."""

    model_config = ConfigDict(extra="forbid")

    domain_key: str = Field(..., min_length=2, max_length=100)
    name_es: str = Field(..., min_length=2, max_length=150)
    name_en: str = Field(default="", max_length=150)
    icon: str = Field(default="BrainCircuit", max_length=50)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0)
    subdomains: list[OppyfySubdomainItemSchema] = Field(default_factory=list)

    @field_validator("domain_key", "name_es")
    @classmethod
    def _sanitize_domain_fields(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="domain_field")


class OppyfySubdomainDetailResponse(BaseModel):
    """Detalle de un subdominio en la respuesta."""

    model_config = ConfigDict(extra="forbid")

    id: int
    subdomain_key: str
    name_es: str
    name_en: str
    allowed_tool_functions: list[str]
    can_view_costs_default: bool
    is_active: bool


class OppyfyDomainTreeResponse(BaseModel):
    """Árbol completo de dominios y subdominios por tenant."""

    model_config = ConfigDict(extra="forbid")

    id: int
    domain_key: str
    name_es: str
    name_en: str
    icon: str
    is_active: bool
    sort_order: int
    subdomains: list[OppyfySubdomainDetailResponse] = Field(default_factory=list)


class OppyfyDomainItemResponse(BaseModel):
    """Compatibilidad: sub-dominio plano del árbol RBAC de `OppyFy`."""

    model_config = ConfigDict(extra="forbid")

    domain_slug: str
    subdomain_slug: str
    display_name: str
    supports_cost_redaction: bool


# ============================================================================
# 4. RBAC GRANTS SCHEMAS
# ============================================================================


class OppyfyGrantCreateRequest(BaseModel):
    """Otorgamiento de permisos temporales o permanentes a un trabajador."""

    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(..., gt=0)
    subdomain_id: int = Field(..., gt=0)
    subdomain_slug: str = Field(..., min_length=2, max_length=100)
    can_query: bool = True
    can_view_costs: bool = False
    expires_at: datetime | None = None
    max_prompts: int | None = Field(default=None, gt=0)
    temp_credit_ceiling: Decimal | None = Field(default=None, ge=Decimal("0.00"))


class OppyfyGrantResponse(BaseModel):
    """Detalle de la concesión de permiso RBAC creada."""

    model_config = ConfigDict(extra="forbid")

    grant_id: uuid.UUID
    user_id: int
    subdomain_id: int
    subdomain_slug: str
    can_query: bool
    can_view_costs: bool
    expires_at: datetime | None
    max_prompts: int | None
    temp_credit_ceiling: Decimal | None
    is_active: bool


# ============================================================================
# 5. WALLET SCHEMAS
# ============================================================================


class OppyfyWalletPatchRequest(BaseModel):
    """Gestión de cupo y activación de créditos de un trabajador."""

    model_config = ConfigDict(extra="forbid")

    assigned_credit_ceiling: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    is_oppyfy_enabled: bool | None = None


class OppyfyWalletResponse(BaseModel):
    """Estado de la billetera de créditos sin caducidad del trabajador."""

    model_config = ConfigDict(extra="forbid")

    user_id: int
    is_oppyfy_enabled: bool
    assigned_credits_balance: Decimal
    consumed_credits_total: Decimal
    remaining_credits: Decimal


# ============================================================================
# 6. PLATFORM ADMIN: AI CREDIT PACKS SCHEMAS
# ============================================================================


class AiCreditPackCreateRequest(BaseModel):
    """Creación o edición de un Paquete de Créditos IA en Platform Admin."""

    model_config = ConfigDict(extra="forbid")

    pack_name: str = Field(..., min_length=3, max_length=120)
    credits_amount: Decimal = Field(..., gt=Decimal("0.00"))
    price_clp: Decimal = Field(..., ge=Decimal("0.00"))
    price_usd: Decimal = Field(..., ge=Decimal("0.00"))
    bonus_credits: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    is_popular: bool = False
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0)
    plan_tier_discounts: dict[str, Decimal] = Field(default_factory=dict)

    @field_validator("pack_name")
    @classmethod
    def _sanitize_name(cls, value: str) -> str:
        return sanitize_text_input(value, field_name="pack_name")


class AiCreditPackResponse(BaseModel):
    """Respuesta de Paquete de Créditos IA."""

    model_config = ConfigDict(extra="forbid")

    id: int
    pack_name: str
    credits_amount: Decimal
    bonus_credits: Decimal
    total_credits: Decimal
    price_clp: Decimal
    price_usd: Decimal
    is_popular: bool
    is_active: bool
    sort_order: int
    plan_tier_discounts: dict[str, Decimal]


class AiCreditPackQuoteResponse(BaseModel):
    """Cotización de compra de paquete con descuentos de plan SaaS aplicados."""

    model_config = ConfigDict(extra="forbid")

    pack_id: int
    pack_name: str
    base_plan_tier: str
    original_price_usd: Decimal
    original_price_clp: Decimal
    discount_pct: Decimal
    final_price_usd: Decimal
    final_price_clp: Decimal
    total_credits: Decimal


# ============================================================================
# 7. TELEMETRY & CONSUMPTION SCHEMAS
# ============================================================================


class OppyfyTelemetryLogItemResponse(BaseModel):
    """Registro de telemetría inmutable de `public.llm_request_logs`."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    caller_feature: str
    model_name: str
    total_tokens: int
    estimated_cost_usd: Decimal
    credits_deducted: Decimal


# ============================================================================
# 8. AI MODEL TARIFFS SCHEMAS
# ============================================================================


class AiModelTariffResponse(BaseModel):
    """Tarifa configurada para un modelo IA en el panel Platform Admin."""

    model_config = ConfigDict(extra="forbid")

    model_slug: str
    engine_tier: str
    input_cost_per_1m_usd: Decimal
    cached_cost_per_1m_usd: Decimal
    output_cost_per_1m_usd: Decimal
    embedding_cost_per_1m_usd: Decimal
    is_enabled: bool


class AiModelTariffUpdateRequest(BaseModel):
    """Actualización dinámica de tarifa para un modelo de IA en Platform Admin."""

    model_config = ConfigDict(extra="forbid")

    engine_tier: str | None = None
    input_cost_per_1m_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
    cached_cost_per_1m_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
    output_cost_per_1m_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
    embedding_cost_per_1m_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_enabled: bool | None = None


# ============================================================================
# 9. AI MODEL CATALOG & JEV ENGINES SCHEMAS
# ============================================================================


VALID_ENGINE_TIERS = ("SYSTEM_1_JEV", "SYSTEM_2_LLM", "EMBEDDING")


class AiModelConfigCreateRequest(BaseModel):
    """Alta de configuración para un modelo cognitivo o motor JEV en Platform Admin."""

    model_config = ConfigDict(extra="forbid")

    model_slug: str = Field(
        ...,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$",
        description="Slug único del modelo en minúsculas y caracteres alfanuméricos.",
    )
    display_name: str = Field(..., min_length=2, max_length=128)
    provider: str = Field(..., min_length=2, max_length=64)
    engine_tier: str = Field(default="SYSTEM_2_LLM")
    input_cost_per_1m_usd: Decimal = Field(default=Decimal("0.000000"), ge=Decimal("0.000000"))
    cached_cost_per_1m_usd: Decimal = Field(default=Decimal("0.000000"), ge=Decimal("0.000000"))
    output_cost_per_1m_usd: Decimal = Field(default=Decimal("0.000000"), ge=Decimal("0.000000"))
    embedding_cost_per_1m_usd: Decimal = Field(default=Decimal("0.000000"), ge=Decimal("0.000000"))
    latency_p95_ms: int = Field(default=100, ge=0)
    min_confidence_score: Decimal | None = Field(
        default=None,
        ge=Decimal("0.0000"),
        le=Decimal("1.0000"),
    )
    max_context_tokens: int = Field(default=128000, ge=0)
    is_enabled: bool = True
    is_default: bool = False
    is_fallback: bool = False
    description: str = Field(default="", max_length=1000)

    @field_validator(
        "input_cost_per_1m_usd",
        "cached_cost_per_1m_usd",
        "output_cost_per_1m_usd",
        "embedding_cost_per_1m_usd",
        "min_confidence_score",
        mode="before",
    )
    @classmethod
    def _validate_decimal_no_float(cls, v: Any) -> Any:
        if isinstance(v, float):
            raise ValueError("Float type is strictly forbidden. Use Decimal or string representation.")
        return v

    @field_validator("engine_tier")
    @classmethod
    def _validate_engine_tier(cls, v: str) -> str:
        if v not in VALID_ENGINE_TIERS:
            raise ValueError(f"Invalid engine_tier '{v}'. Must be one of {VALID_ENGINE_TIERS}.")
        return v

    @field_validator("model_slug")
    @classmethod
    def _normalize_slug(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("display_name", "provider", "description")
    @classmethod
    def _sanitize_fields(cls, v: str) -> str:
        return sanitize_text_input(v, field_name="ai_model_meta")


class AiModelConfigUpdateRequest(BaseModel):
    """Modificación de configuración para un modelo cognitivo o motor JEV en Platform Admin."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=2, max_length=128)
    provider: str | None = Field(default=None, min_length=2, max_length=64)
    engine_tier: str | None = None
    input_cost_per_1m_usd: Decimal | None = Field(default=None, ge=Decimal("0.000000"))
    cached_cost_per_1m_usd: Decimal | None = Field(default=None, ge=Decimal("0.000000"))
    output_cost_per_1m_usd: Decimal | None = Field(default=None, ge=Decimal("0.000000"))
    embedding_cost_per_1m_usd: Decimal | None = Field(default=None, ge=Decimal("0.000000"))
    latency_p95_ms: int | None = Field(default=None, ge=0)
    min_confidence_score: Decimal | None = Field(
        default=None,
        ge=Decimal("0.0000"),
        le=Decimal("1.0000"),
    )
    max_context_tokens: int | None = Field(default=None, ge=0)
    is_enabled: bool | None = None
    is_default: bool | None = None
    is_fallback: bool | None = None
    description: str | None = Field(default=None, max_length=1000)

    @field_validator(
        "input_cost_per_1m_usd",
        "cached_cost_per_1m_usd",
        "output_cost_per_1m_usd",
        "embedding_cost_per_1m_usd",
        "min_confidence_score",
        mode="before",
    )
    @classmethod
    def _validate_decimal_no_float(cls, v: Any) -> Any:
        if isinstance(v, float):
            raise ValueError("Float type is strictly forbidden. Use Decimal or string representation.")
        return v

    @field_validator("engine_tier")
    @classmethod
    def _validate_engine_tier(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_ENGINE_TIERS:
            raise ValueError(f"Invalid engine_tier '{v}'. Must be one of {VALID_ENGINE_TIERS}.")
        return v

    @field_validator("display_name", "provider", "description")
    @classmethod
    def _sanitize_fields(cls, v: str | None) -> str | None:
        if v is not None:
            return sanitize_text_input(v, field_name="ai_model_meta")
        return v


class AiModelConfigResponse(BaseModel):
    """Representación completa de configuración de un modelo de IA o motor JEV."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    model_slug: str
    display_name: str
    provider: str
    engine_tier: str
    input_cost_per_1m_usd: Decimal
    cached_cost_per_1m_usd: Decimal
    output_cost_per_1m_usd: Decimal
    embedding_cost_per_1m_usd: Decimal
    latency_p95_ms: int
    min_confidence_score: Decimal | None = None
    max_context_tokens: int
    is_enabled: bool
    is_default: bool
    is_fallback: bool
    description: str = ""
    is_deleted: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AiModelConfigListResponse(BaseModel):
    """Listado paginado/completo de modelos del catálogo AI."""

    model_config = ConfigDict(extra="forbid")

    items: list[AiModelConfigResponse]
    total: int


class AiModelDeleteResponse(BaseModel):
    """Respuesta estructurada ante deshabilitación/baja lógica por preservación de telemetría."""

    model_config = ConfigDict(extra="forbid")

    action: str
    model_slug: str
    is_enabled: bool
    historical_telemetry_logs_preserved: int
    message: str


# Aliases de compatibilidad con spec técnica
AiModelCatalogResponse = AiModelConfigResponse
AiModelCreateRequest = AiModelConfigCreateRequest
AiModelUpdateRequest = AiModelConfigUpdateRequest


# ============================================================================
# 8. RLHF & OBSERVABILITY FEEDBACK SCHEMAS
# ============================================================================


class AIChatFeedbackCreateRequest(BaseModel):
    """Solicitud de feedback humano sobre una interacción del chat de OppyFy."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    message_id: str = Field(..., min_length=1, max_length=128)
    trace_id: str = Field(..., min_length=1, max_length=64)
    feedback_type: Literal["positive", "negative"]
    failure_category: (
        Literal["hallucination", "incomplete", "math_error", "bad_formatting", "other"]
        | None
    ) = None
    user_correction: str | None = Field(default=None, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)

    @field_validator("user_correction")
    @classmethod
    def _sanitize_correction(cls, value: str | None) -> str | None:
        if value:
            return sanitize_text_input(value, field_name="user_correction")
        return value

    @field_validator("failure_category")
    @classmethod
    def _validate_failure_category(
        cls, value: str | None, info: Any
    ) -> str | None:
        # Note: If feedback_type is 'positive', failure_category should be None
        return value


class AIChatFeedbackResponse(BaseModel):
    """Respuesta estructurada de un registro de feedback persistido."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None = None
    message_id: str
    trace_id: str
    feedback_type: str
    failure_category: str | None = None
    user_correction: str | None = None
    rating: int | None = None
    created_at: datetime


class AIChatFeedbackListResponse(BaseModel):
    """Listado paginado de feedback con métricas agregadas de satisfacción."""

    model_config = ConfigDict(extra="forbid")

    items: list[AIChatFeedbackResponse]
    total: int
    positive_count: int
    negative_count: int
    satisfaction_rate_percent: Decimal

