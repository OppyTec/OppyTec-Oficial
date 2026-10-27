"""
oppytec-backend/src/modules/tenancy/infrastructure/models.py
Modelos SQLAlchemy 2.0 de Jerarquía Corporativa (`Holding -> LegalEntity 1:1 -> Tenant`),
Planes Multi-Moneda (`Decimal`), Usuarios Clientes, Memoria `i18n`, Tasas `FX`, Backups y Cuotas R2.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
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


class SystemPlan(PublicBase, AuditTimestampsMixin, TranslatableI18nMixin):
    """Plan comercial editable por SuperUser con cuotas paramétricas de capacidad y precios `Decimal`."""

    __tablename__ = "system_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None, nullable=True)
    monthly_ai_credits: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    tier: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_active_users: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_products: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    max_suppliers: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    max_recipes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_combos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_storage_mb: Mapped[int] = mapped_column(Integer, default=1024, nullable=False)
    included_modules: Mapped[list[str]] = mapped_column(
        JSONDictType,
        default=list,
        nullable=False,
    )
    anchor_currency: Mapped[str] = mapped_column(String(10), default="CLP", nullable=False)
    price_clp: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    price_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    price_eur: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    price_brl: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    auto_convert_fx: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SaaSAIPolicyConfig(PublicBase, AuditTimestampsMixin):
    """
    Configuración global de conversión de tokens de LLM a créditos de IA y precios unitarios.
    Registro único singleton (id=1) en el esquema `public`.
    """

    __tablename__ = "saas_ai_policy_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    tokens_per_credit: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    default_monthly_credits: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    credit_price_clp: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("15.00"),
        nullable=False,
    )
    credit_price_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        default=Decimal("0.0150"),
        nullable=False,
    )
    updated_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("public.global_users.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
    )


class Holding(PublicBase, AuditTimestampsMixin):
    """Grupo empresarial cliente (nombre propio inmutable `translatable = False`) y billetera `ai_credit_balance`."""

    __tablename__ = "holdings"
    translatable: ClassVar[bool] = False

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    nombre: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public.system_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    custom_max_users_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    custom_max_products_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    custom_max_suppliers_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    custom_max_recipes_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    custom_max_combos_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    custom_storage_mb_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    ai_credit_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LegalEntity(PublicBase, AuditTimestampsMixin):
    """Razón social / RUT tributario dentro de un Holding (nombre propio inmutable `translatable = False`)."""

    __tablename__ = "legal_entities"
    translatable: ClassVar[bool] = False

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    holding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public.holdings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tax_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_address: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Tenant(PublicBase, AuditTimestampsMixin):
    """
    Sucursal operativa con esquema PostgreSQL propio (`schema_name UNIQUE`)
    y relación estricta `1:1` con `LegalEntity` (`legal_entity_id UNIQUE`).
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    holding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public.holdings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    legal_entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public.legal_entities.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    schema_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    nombre_comercial: Mapped[str] = mapped_column(String(180), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(10), default="CLP", nullable=False)
    custom_max_users_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    custom_max_products_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    custom_max_suppliers_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    custom_max_recipes_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    custom_max_combos_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    custom_storage_mb_override: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AppModule(PublicBase, AuditTimestampsMixin, TranslatableI18nMixin):
    """Catálogo maestro de módulos de negocio (`sales`, `inventory`, `accounting`, etc.)."""

    __tablename__ = "app_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_core: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TenantModule(PublicBase, AuditTimestampsMixin):
    """Estado de habilitación lógica (`is_enabled`) de un módulo para un `Tenant` específico."""

    __tablename__ = "tenant_modules"
    __table_args__ = (UniqueConstraint("tenant_id", "module_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public.tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module_slug: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.app_modules.slug", ondelete="CASCADE"),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ClientUser(PublicBase, AuditTimestampsMixin, SoftDeleteMixin):
    """
    Identidad única de usuario cliente a nivel `Holding`.
    El borrado lógico (`is_deleted = True`) libera inmediatamente un cupo en `max_active_users`.
    """

    __tablename__ = "client_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    holding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public.holdings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="es", nullable=False)
    preferred_currency: Mapped[str] = mapped_column(String(10), default="CLP", nullable=False)
    is_holding_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ClientUserTenantAccess(PublicBase, AuditTimestampsMixin):
    """Acceso transversal que autoriza a un `ClientUser` a operar en 1 o N Tenants del mismo Holding."""

    __tablename__ = "client_user_tenant_access"
    __table_args__ = (UniqueConstraint("user_id", "tenant_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("public.client_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    holding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public.holdings.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public.tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    granted_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)


class I18nTranslationMemory(PublicBase, AuditTimestampsMixin):
    """Memoria global de traducción (`public.i18n_translation_memory`) para evitar llamadas LLM redundantes."""

    __tablename__ = "i18n_translation_memory"

    term_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_lang: Mapped[str] = mapped_column(String(10), default="es", nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translations: Mapped[dict[str, str]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )


class FxCurrentRate(PublicBase, AuditTimestampsMixin):
    """Tasa cambiaria institucional vigente (`NUMERIC(18, 8)`) desde BCCh / BCE Frankfurter."""

    __tablename__ = "fx_current_rates"
    __table_args__ = (UniqueConstraint("base_currency", "quote_currency"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    quote_currency: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source_provider: Mapped[str] = mapped_column(String(32), default="BCCH", nullable=False)
    is_manual_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class FxRateHistory(PublicBase, AuditTimestampsMixin):
    """Serie histórica inmutable de tasas cambiarias (`NUMERIC(18, 8)`)."""

    __tablename__ = "fx_rate_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    quote_currency: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FxAuditLog(PublicBase, AuditTimestampsMixin):
    """Auditoría de anomalías cambiarias (> 8%) y overrides manuales del SuperUser."""

    __tablename__ = "fx_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    currency_pair: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    previous_rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    new_rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    variation_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    action_taken: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)


class BackupExecutionLog(PublicBase, AuditTimestampsMixin):
    """Registro de ejecución de respaldos de las 4 Capas (`.sql.zst.age`) y verificación `SHA-256`."""

    __tablename__ = "backup_execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    scope: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    layer_name: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    object_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED", nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(64), default="system", nullable=False)


class TenantMediaAsset(TenantBase, AuditTimestampsMixin):
    """Inventario de imágenes optimizadas (`thumb.webp` + `display.webp`) para control de cuota MB en R2."""

    __tablename__ = "tenant_media_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
    )
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    thumb_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    display_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reference_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
