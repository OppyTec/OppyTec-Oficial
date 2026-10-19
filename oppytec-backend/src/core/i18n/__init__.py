"""
oppytec-backend/src/core/i18n/__init__.py
Exportaciones públicas del motor de Internacionalización (`i18n`) Estático y Dinámico.
"""
from __future__ import annotations

from src.core.i18n.dynamic_field_sync import (
     IMMUTABLE_PROPER_NOUN_TABLES,
    KNOWN_PROTECTED_PROPER_NOUNS,
    DynamicFieldSyncResult,
    DynamicFieldTranslationSync,
    TranslationMemoryEntry,
    build_pi_translation_prompt,
    compute_i18n_source_hash,
    extract_embedded_protected_brands,
    is_proper_noun_protected,
    normalize_term,
)
from src.core.i18n.translator import (
    DEFAULT_LANGUAGE,
    FUTURE_SCALABLE_LANGUAGES,
    SUPPORTED_LANGUAGES,
    I18nCatalogTranslator,
    SupportedLanguage,
    flatten_catalog_dict,
    get_translator,
    interpolate_template,
    resolve_language,
    t,
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "FUTURE_SCALABLE_LANGUAGES",
    "IMMUTABLE_PROPER_NOUN_TABLES",
    "KNOWN_PROTECTED_PROPER_NOUNS",
    "SUPPORTED_LANGUAGES",
    "DynamicFieldSyncResult",
    "DynamicFieldTranslationSync",
    "I18nCatalogTranslator",
    "SupportedLanguage",
    "TranslationMemoryEntry",
    "build_pi_translation_prompt",
    "compute_i18n_source_hash",
    "extract_embedded_protected_brands",
    "flatten_catalog_dict",
    "get_translator",
    "interpolate_template",
    "is_proper_noun_protected",
    "normalize_term",
    "resolve_language",
    "t",
]
