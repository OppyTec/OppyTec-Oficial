"""
oppytec-backend/src/modules/oppy_ai/infrastructure/models.py
Modelos SQLAlchemy 2.0 del Asistente `OppyFy` y Motor `JEV`:
- `PublicBase` (`public`): `LlmRequestLog`, `AudioRequestLog`, `AiModelConfig`,
  `AiCreditPackage`, `SpecSyncMetadata`, `SpecChunk` (indexa exclusivamente `specs/business-domain/`).
- `TenantBase` (`tenant_*`): `OppyfyDomain`, `OppyfySubdomain`, `OppyfyPermissionGrant`,
  `OppyfyWorkerCreditWallet`, `OppyfyPromptAuditLog`, `TenantDocument`, `DocumentChunk`,
  `TenantAiMemory`, `AiChatThread`, `AiChatMessage`.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

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
    output_cost_per_1m_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
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


class OppyfyDomain(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """Dominio de conocimiento de `OppyFy` 100% editable por el Propietario del local (`tenant_*`)."""

    __tablename__ = "oppyfy_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OppyfySubdomain(TenantBase, AuditTimestampsMixin, SoftDeleteMixin, TranslatableI18nMixin):
    """
    Sub-dominio editable por el cliente en `OppyFy` vinculado a herramientas de código duro
    y documentos privados del restaurante/hotel.
    """

    __tablename__ = "oppyfy_subdomains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("oppyfy_domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    bound_tool_codes: Mapped[list[str]] = mapped_column(
        JSONDictType,
        default=list,
        nullable=False,
    )


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
    subdomain_id: Mapped[int] = mapped_column(
        Integer,
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
    user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True, index=True)
    effect: Mapped[str] = mapped_column(String(16), default="ALLOW", nullable=False)
    can_view_costs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    max_prompts: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    used_prompts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    temp_credit_ceiling: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        default=None,
        nullable=True,
    )


class OppyfyWorkerCreditWallet(TenantBase, AuditTimestampsMixin):
    """Billetera de créditos de `OppyFy` asignada por el Propietario a cada trabajador del local."""

    __tablename__ = "oppyfy_worker_credit_wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    allocated_credits: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    consumed_credits: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    is_oppyfy_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


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
    subdomain_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    decision_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    credits_consumed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
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
        Integer,
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
        Integer,
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
