"""
oppytec-backend/src/modules/oppy_ai/presentation/schemas.py
Esquemas Pydantic v2 (`extra="forbid"`, `Decimal` exclusivo) para el Asistente `OppyFy`:
- Consultas conversacionales medidas (`/api/v1/oppyfy/chat`)
- Catálogo y concesiones RBAC propias editables (`/api/v1/oppyfy/rbac/domains`)
- Billetera de paquetes de créditos sin caducidad (`/api/v1/oppyfy/credits/wallet`)
- Telemetría de solicitudes LLM (`/api/v1/oppyfy/telemetry/logs`)
"""
# mypy: disable-error-code="explicit-any"
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.guards.xss_sanitizer import sanitize_text_input


class OppyfyChatRequest(BaseModel):
    """Consulta de un trabajador del Tenant hacia `OppyFy`."""

    model_config = ConfigDict(extra="forbid")

    prompt_text: str = Field(..., min_length=2, max_length=2000)
    target_subdomain_slug: str = Field(default="recipes_kitchen", min_length=2, max_length=64)
    can_view_costs: bool = False
    prior_thread_tokens: int = Field(default=0, ge=0, le=500000)
    remaining_credits: Decimal = Field(default=Decimal("50.00"), ge=Decimal("0"))
    estimated_credit_cost: Decimal = Field(default=Decimal("1.00"), gt=Decimal("0"))

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


class OppyfyDomainItemResponse(BaseModel):
    """Sub-dominio del árbol RBAC propio y editable de `OppyFy`."""

    model_config = ConfigDict(extra="forbid")

    domain_slug: str
    subdomain_slug: str
    display_name: str
    supports_cost_redaction: bool


class OppyfyWalletResponse(BaseModel):
    """Estado de la billetera de paquetes de créditos sin caducidad del trabajador."""

    model_config = ConfigDict(extra="forbid")

    user_id: int
    is_oppyfy_enabled: bool
    assigned_credits_balance: Decimal
    consumed_credits_total: Decimal
    remaining_credits: Decimal


class OppyfyTelemetryLogItemResponse(BaseModel):
    """Registro de telemetría inmutable de `public.llm_request_logs`."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    caller_feature: str
    model_name: str
    total_tokens: int
    estimated_cost_usd: Decimal
    credits_deducted: Decimal
