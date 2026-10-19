"""Modelos base y utilidades compartidas de persistencia sin acoplamiento de negocio."""
from __future__ import annotations

from src.shared.models_base import (
    NON_TRANSLATABLE_PROPER_NOUN_TABLES,
    AuditTimestampsMixin,
    PublicBase,
    TenantBase,
    TranslatableI18nMixin,
    is_table_proper_noun_immutable,
)
from src.shared.pagination import PaginatedResponse, PaginationParams
from src.shared.soft_delete_mixin import SoftDeleteMixin
from src.shared.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork

__all__ = [
    "NON_TRANSLATABLE_PROPER_NOUN_TABLES",
    "AbstractUnitOfWork",
    "AuditTimestampsMixin",
    "PaginatedResponse",
    "PaginationParams",
    "PublicBase",
    "SoftDeleteMixin",
    "SqlAlchemyUnitOfWork",
    "TenantBase",
    "TranslatableI18nMixin",
    "is_table_proper_noun_immutable",
]
