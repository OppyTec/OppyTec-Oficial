"""
oppytec-backend/src/shared/models_base.py
DeclarativeBase separada (`PublicBase` con `schema="public"` vs `TenantBase` dinámico),
`AuditTimestampsMixin` y `TranslatableI18nMixin` con protección de nombres propios ("Pollo King").
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Regla "Pollo King": Tablas de nombres propios / marcas comerciales que JAMÁS se traducen.
NON_TRANSLATABLE_PROPER_NOUN_TABLES: frozenset[str] = frozenset(
    {
        "proveedores",
        "marcas",
        "holdings",
        "legal_entities",
    }
)

JSONDictType = JSON().with_variant(JSONB(), "postgresql")


def is_table_proper_noun_immutable(table_name: str) -> bool:
    """Devuelve `True` si la tabla contiene nombres propios inmutables que no deben traducirse."""
    return table_name.strip().lower() in NON_TRANSLATABLE_PROPER_NOUN_TABLES


class PublicBase(DeclarativeBase):
    """
    Clase base declarativa exclusiva para el esquema global `public`
    (Holdings, Entidades Legales, Tenants, Planes, RBAC Global, FinOps IA, Memoria i18n, FX y Backups).
    """

    metadata = MetaData(schema="public", naming_convention=NAMING_CONVENTION)


class TenantBase(DeclarativeBase):
    """
    Clase base declarativa para los esquemas dinámicos `tenant_<slug>`.
    No fija `schema` en `MetaData` para operar limpiamente sobre `SET LOCAL search_path`.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class AuditTimestampsMixin:
    """Mixin transversal de trazabilidad temporal (`created_at`, `updated_at` en UTC)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )


class TranslatableI18nMixin:
    """
    Mixin para entidades conceptuales editables por el cliente (`productos`, `categorias`,
    `familias_producto`, `bodegas`, `areas_operativas`, `recetas`, `roles`, `cargos`).
    Almacena traducciones dinámicas en `i18n_data` (`{"es": "...", "en": "..."}`) y el hash
    SHA-256 del texto fuente para invalidar traducciones obsoletas sin re-traducir en cada lectura.
    """

    translatable: ClassVar[bool] = True

    i18n_data: Mapped[dict[str, str]] = mapped_column(
        JSONDictType,
        default=dict,
        nullable=False,
    )
    i18n_source_hash: Mapped[str | None] = mapped_column(
        String(64),
        default=None,
        nullable=True,
    )

    def set_localized_text(self, lang: str, text_value: str, *, is_source: bool = False) -> None:
        """
        Registra o actualiza una traducción en `i18n_data`.
        Si la entidad tiene `translatable = False` (ej. `"Pollo King"`), bloquea la traducción.
        """
        table_name = getattr(self, "__tablename__", "")
        if not self.translatable or is_table_proper_noun_immutable(str(table_name)):
            raise ValueError(
                f"ProperNounImmutabilityError: La entidad '{table_name}' contiene nombres propios "
                "inmutables (regla 'Pollo King') y no admite traducción por idioma."
            )
        updated = dict(self.i18n_data or {})
        updated[lang] = text_value
        self.i18n_data = updated
        if is_source:
            self.i18n_source_hash = hashlib.sha256(text_value.encode("utf-8")).hexdigest()

    def get_localized_text(self, lang: str, fallback_text: str) -> str:
        """Devuelve el texto en el idioma solicitado (`es`/`en`) o el texto base si no existe."""
        if not self.i18n_data:
            return fallback_text
        return self.i18n_data.get(lang) or self.i18n_data.get("es") or fallback_text
