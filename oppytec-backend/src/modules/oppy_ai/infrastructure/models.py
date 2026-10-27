"""
oppytec-backend/src/modules/oppy_ai/infrastructure/models.py
Modelos SQLAlchemy 2.0 del Asistente `OppyFy` y Motor `JEV`:
- `PublicBase` (`public`): `LlmRequestLog`, `AudioRequestLog`, `AiModelConfig`,
  `AiCreditPackage`, `AiCreditPack`, `SpecSyncMetadata`, `SpecChunk` (indexa exclusivamente `specs/business-domain/`).
- `TenantBase` (`tenant_*`): `OppyfyDomain`, `OppyfySubdomain`, `OppyfyPermissionGrant`,
  `OppyfyWorkerCreditWallet`, `OppyfyPromptAuditLog`, `OppyfyRbacAuditLog`, `TenantDocument`, `DocumentChunk`,
  `TenantAiMemory`, `AiChatThread`, `AiChatMessage`.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models_base import (
    AuditTimestampsMixin,
    JSONDictType,
    PublicBase,
    TenantBase,
    TranslatableI18nMixin,
)
from src.shared.soft_delete_mixin import SoftDeleteMixin


class LlmRequestLog(PublicBase):
    """
    Registro estricto y sin excepción de toda llamada a IA (`SYSTEM_1_JEV`, `SYSTEM_2_LLM`, `EMBEDDING`).
    Tabla Append-Only en `public.llm_request_logs`.
    """

    __tablename__ = "llm_request_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    holding_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    tenant_schema: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        default=None,
        nullable=True,
    )
    engine_tier: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    caller_feature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 6),
        default=Decimal("0.000000"),
        nullable=False,
    )
    provider_cost_clp: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    credits_deducted: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    request_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    api_success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)


class AudioRequestLog(PublicBase):
    """Telemetría de interacciones por voz (`STT`/`TTS`) con costos en `Decimal`."""

    __tablename__ = "audio_request_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    holding_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    provider_cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    credits_deducted: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class AiModelConfig(PublicBase, AuditTimestampsMixin):
    """Configuración y tarifas por millón de tokens (`Decimal`) de los modelos IA habilitados."""

    __tablename__ = "ai_model_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    engine_tier: Mapped[str] = mapped_column(String(32), default="SYSTEM_2_LLM", nullable=False)
    input_cost_per_1m_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    cached_cost_per_1m_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        default=Decimal("0.000000"),
        nullable=False,
    )
    output_cost_per_1m_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    embedding_cost_per_1m_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        default=Decimal("0.000000"),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AiCreditPackage(PublicBase, AuditTimestampsMixin, TranslatableI18nMixin):
    """
    Paquete de créditos de `OppyFy` comprable en cualquier momento, acumulable (`1000 + 10000 = 11000`)
    y sin fecha de vencimiento por defecto (`expires_in_days = None`).
    """

    __tablename__ = "ai_credit_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    price_clp: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    price_usd: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    expires_in_days: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AiCreditPack(PublicBase, AuditTimestampsMixin):
    """Paquetes de créditos IA independientes configurables por el Superadmin en el Panel Platform Admin."""

    __tablename__ = "ai_credit_packs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pack_name: Mapped[str] = mapped_column(String(120), nullable=False)
    credits_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    price_clp: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    price_usd: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class SpecSyncMetadata(PublicBase, AuditTimestampsMixin):
    """Control de sincronización de documentos de la bóveda funcional `specs/business-domain/`."""

    __tablename__ = "spec_sync_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_rel_path: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    module_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class SpecChunk(PublicBase, AuditTimestampsMixin):
    """
    Fragmento vectorizado (`768` dimensiones) de la bóveda pública de negocio (`specs/business-domain/`)
    para la Capa 1 del RAG de `OppyFy`.
    """

    __tablename__ = "spec_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    spec_metadata_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("public.spec_sync_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[list[Decimal]] = mapped_column(
        JSONDictType,
        default=list,
        nullable=False,
    )
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OppyfyDomain(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Dominio de conocimiento de `OppyFy` 100% editable por el Propietario del local (`tenant_*`)."""

    __tablename__ = "oppyfy_domains"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    domain_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name_es: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), default="", nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="BrainCircuit", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    @property
    def slug(self) -> str:
        return self.domain_key

    @slug.setter
    def slug(self, value: str) -> None:
        self.domain_key = value

    @property
    def name(self) -> str:
        return self.name_es

    @name.setter
    def name(self, value: str) -> None:
        self.name_es = value

    @property
    def is_enabled(self) -> bool:
        return self.is_active

    @is_enabled.setter
    def is_enabled(self, value: bool) -> None:
        self.is_active = value

    def __init__(self, **kwargs: Any) -> None:
        if "slug" in kwargs and "domain_key" not in kwargs:
            kwargs["domain_key"] = kwargs.pop("slug")
        if "name" in kwargs and "name_es" not in kwargs:
            name_val = kwargs.pop("name")
            kwargs["name_es"] = name_val
            if "name_en" not in kwargs:
                kwargs["name_en"] = name_val
        if "is_enabled" in kwargs and "is_active" not in kwargs:
            kwargs["is_active"] = kwargs.pop("is_enabled")
        super().__init__(**kwargs)


class OppyfySubdomain(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """
    Sub-dominio editable por el cliente en `OppyFy` vinculado a herramientas de código duro
    y documentos privados del restaurante/hotel.
    """

    __tablename__ = "oppyfy_subdomains"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    domain_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("oppyfy_domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subdomain_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name_es: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), default="", nullable=False)
    module_slug: Mapped[str] = mapped_column(String(100), default="oppy_ai", nullable=False, index=True)
    allowed_tool_functions: Mapped[list[str]] = mapped_column(
        JSONDictType,
        default=list,
        nullable=False,
    )
    can_view_costs_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def slug(self) -> str:
        return self.subdomain_key

    @slug.setter
    def slug(self, value: str) -> None:
        self.subdomain_key = value

    @property
    def name(self) -> str:
        return self.name_es

    @name.setter
    def name(self, value: str) -> None:
        self.name_es = value

    @property
    def bound_tool_codes(self) -> list[str]:
        return self.allowed_tool_functions

    @bound_tool_codes.setter
    def bound_tool_codes(self, value: list[str]) -> None:
        self.allowed_tool_functions = value

    def __init__(self, **kwargs: Any) -> None:
        if "slug" in kwargs and "subdomain_key" not in kwargs:
            kwargs["subdomain_key"] = kwargs.pop("slug")
        if "name" in kwargs and "name_es" not in kwargs:
            name_val = kwargs.pop("name")
            kwargs["name_es"] = name_val
            if "name_en" not in kwargs:
                kwargs["name_en"] = name_val
        if "bound_tool_codes" in kwargs and "allowed_tool_functions" not in kwargs:
            kwargs["allowed_tool_functions"] = kwargs.pop("bound_tool_codes")
        super().__init__(**kwargs)


class OppyfyPermissionGrant(TenantBase, AuditTimestampsMixin):
    """
    Permiso granular sobre un sub-dominio de `OppyFy` con soporte de caducidad automática
    por fecha/hora (`expires_at`), cantidad de consultas (`max_prompts`) o tope de créditos (`temp_credit_ceiling`).
    """

    __tablename__ = "oppyfy_permission_grants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    subdomain_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("oppyfy_subdomains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        default=None,
        nullable=True,
    )
    effect: Mapped[str] = mapped_column(String(16), default="ALLOW", nullable=False)
    can_query: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_view_costs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    max_prompts: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    prompts_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    temp_credit_ceiling: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        default=None,
        nullable=True,
    )
    temp_credits_used: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    @property
    def used_prompts(self) -> int:
        return self.prompts_used

    @used_prompts.setter
    def used_prompts(self, value: int) -> None:
        self.prompts_used = value

    def __init__(self, **kwargs: Any) -> None:
        if "used_prompts" in kwargs and "prompts_used" not in kwargs:
            kwargs["prompts_used"] = kwargs.pop("used_prompts")
        super().__init__(**kwargs)


class OppyfyWorkerCreditWallet(TenantBase, AuditTimestampsMixin):
    """Billetera de créditos de `OppyFy` asignada por el Propietario a cada trabajador del local."""

    __tablename__ = "oppyfy_worker_credit_wallets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    is_oppyfy_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_credit_ceiling: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=True,
    )
    credits_spent_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    balance_override: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        default=None,
        nullable=True,
    )

    @property
    def allocated_credits(self) -> Decimal:
        return self.assigned_credit_ceiling if self.assigned_credit_ceiling is not None else Decimal("0.00")

    @allocated_credits.setter
    def allocated_credits(self, value: Decimal) -> None:
        self.assigned_credit_ceiling = value

    @property
    def consumed_credits(self) -> Decimal:
        return self.credits_spent_total

    @consumed_credits.setter
    def consumed_credits(self, value: Decimal) -> None:
        self.credits_spent_total = value

    def __init__(self, **kwargs: Any) -> None:
        if "allocated_credits" in kwargs and "assigned_credit_ceiling" not in kwargs:
            kwargs["assigned_credit_ceiling"] = kwargs.pop("allocated_credits")
        if "consumed_credits" in kwargs and "credits_spent_total" not in kwargs:
            kwargs["credits_spent_total"] = kwargs.pop("consumed_credits")
        super().__init__(**kwargs)


class OppyfyPromptAuditLog(TenantBase):
    """
    Bitácora inmutable Append-Only de prompts enviados por trabajadores a `OppyFy`,
    incluyendo rechazos por falta de permisos (`BLOCKED_UNAUTHORIZED_PROMPT`).
    """

    __tablename__ = "oppyfy_prompt_audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ALLOWED", nullable=False, index=True)
    resolved_domain: Mapped[str | None] = mapped_column(String(100), default=None, nullable=True, index=True)
    resolved_tools: Mapped[list[str]] = mapped_column(
        JSONDictType,
        default=list,
        nullable=False,
    )
    tokens_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credits_deducted: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    @property
    def decision_status(self) -> str:
        return self.status

    @decision_status.setter
    def decision_status(self, value: str) -> None:
        self.status = value

    @property
    def credits_consumed(self) -> Decimal:
        return self.credits_deducted

    @credits_consumed.setter
    def credits_consumed(self, value: Decimal) -> None:
        self.credits_deducted = value

    @property
    def subdomain_slug(self) -> str:
        return self.resolved_domain or ""

    @subdomain_slug.setter
    def subdomain_slug(self, value: str) -> None:
        self.resolved_domain = value

    def __init__(self, **kwargs: Any) -> None:
        if "decision_status" in kwargs and "status" not in kwargs:
            kwargs["status"] = kwargs.pop("decision_status")
        if "credits_consumed" in kwargs and "credits_deducted" not in kwargs:
            kwargs["credits_deducted"] = kwargs.pop("credits_consumed")
        if "subdomain_slug" in kwargs and "resolved_domain" not in kwargs:
            kwargs["resolved_domain"] = kwargs.pop("subdomain_slug")
        super().__init__(**kwargs)


class OppyfyRbacAuditLog(TenantBase):
    """
    Bitácora inmutable Append-Only de cambios y asignaciones RBAC en `OppyFy`.
    """

    __tablename__ = "oppyfy_rbac_audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )


class TenantDocument(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Documento o manual privado subido por el cliente para el RAG de su local."""

    __tablename__ = "tenant_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    subdomain_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("oppyfy_subdomains.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(String(512), nullable=False)


class DocumentChunk(TenantBase, AuditTimestampsMixin):
    """Fragmento vectorizado de un `TenantDocument` vinculado a `oppyfy_subdomain_id`."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenant_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    oppyfy_subdomain_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("oppyfy_subdomains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)


class TenantAiMemory(TenantBase, AuditTimestampsMixin):
    """Memoria episódica/semántica del local (patrón Mem0 con `agent_affinity`)."""

    __tablename__ = "tenant_ai_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True, index=True)
    agent_affinity: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    memory_fact: Mapped[str] = mapped_column(Text, nullable=False)


class AiChatThread(TenantBase, AuditTimestampsMixin, SoftDeleteMixin):
    """Hilo de conversación con `OppyFy` y medidor de uso de ventana de contexto (`context_usage_percent`)."""

    __tablename__ = "ai_chat_threads"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    context_usage_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
    )


class AiChatMessage(TenantBase, AuditTimestampsMixin):
    """Mensaje individual (`user` | `assistant` | `tool`) dentro de un `AiChatThread`."""

    __tablename__ = "ai_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ai_chat_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
