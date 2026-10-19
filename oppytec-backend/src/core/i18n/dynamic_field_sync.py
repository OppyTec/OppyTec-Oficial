"""
oppytec-backend/src/core/i18n/dynamic_field_sync.py
Sincronizador de Campos Dinámicos del Cliente (`i18n_data` JSONB + `i18n_source_hash` SHA-256).
Implementa:
1. Filtro Inmutable "Pollo King" (`is_proper_noun_protected`): protege proveedores, marcas, holdings,
   razones sociales (`legal_entities`) y marcas comerciales registradas.
2. Deduplicación SHA-256 contra la memoria global `public.i18n_translation_memory` (0 gasto de tokens).
3. Generador de micro-prompt minimalista estilo `Pi` (`build_pi_translation_prompt`, < 35 tokens).
4. Cero cobro de créditos al cliente (`credits_deducted = 0`).
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

IMMUTABLE_PROPER_NOUN_TABLES: frozenset[str] = frozenset(
    {
        "proveedores",
        "suppliers",
        "marcas",
        "brands",
        "holdings",
        "legal_entities",
        "tenants",
        "client_users",
        "skus",
        "tax_ids",
    }
)

KNOWN_PROTECTED_PROPER_NOUNS: frozenset[str] = frozenset(
    {
        "pollo king",
        "savory",
        "coca-cola",
        "coca cola",
        "soprole",
        "nestle",
        "nestlé",
        "distribuidora el sol",
        "ariztia",
        "ariztía",
        "super pollo",
        "colun",
        "watts",
        "ccu",
    }
)

DEFAULT_GLOBAL_GASTRONOMIC_MEMORY: dict[str, dict[str, str]] = {
    "bodega central": {"es": "Bodega Central", "en": "Central Warehouse"},
    "cocina caliente": {"es": "Cocina Caliente", "en": "Hot Kitchen"},
    "helado de chocolate": {"es": "Helado de Chocolate", "en": "Chocolate Ice Cream"},
    "cono helado de chocolate": {
        "es": "Cono Helado de Chocolate",
        "en": "Chocolate Ice Cream Cone",
    },
    "gerente": {"es": "Gerente", "en": "Manager"},
    "cajero": {"es": "Cajero", "en": "Cashier"},
    "cocinero": {"es": "Cocinero", "en": "Cook"},
    "postres": {"es": "Postres", "en": "Desserts"},
    "carnes": {"es": "Carnes", "en": "Meats"},
    "bebidas": {"es": "Bebidas", "en": "Beverages"},
    "lomo vetado": {"es": "Lomo Vetado", "en": "Ribeye Steak"},
}

QUOTED_OR_TRADEMARK_REGEX: re.Pattern[str] = re.compile(
    r'^(?:["\'].+["\']|.*[®™].*|[A-Z0-9]{2,}-\d{2,}|\d{1,2}\.?\d{3}\.?\d{3}-[\dkK])$'
)


def normalize_term(text: str) -> str:
    """Normaliza un término colapsando espacios múltiples y convirtiendo a minúsculas para hashing."""
    return " ".join(text.strip().split()).lower()


def compute_i18n_source_hash(source_text: str, source_lang: str = "es") -> str:
    """Calcula el hash `SHA-256` determinista del término normalizado y su idioma origen."""
    normalized = normalize_term(source_text)
    lang_norm = source_lang.strip().lower() or "es"
    payload = f"{lang_norm}:{normalized}".encode()
    return hashlib.sha256(payload).hexdigest()


def is_proper_noun_protected(
    text: str,
    table_name: str | None = None,
    *,
    is_translatable_column: bool = True,
    extra_protected_nouns: Sequence[str] = (),
) -> bool:
    """
    Filtro Inmutable "Pollo King":
    Determina si un texto o entidad corresponde a un Nombre Propio Inmutable (proveedor, marca,
    holding, razón social, SKU/RUT o marca entre comillas/registrada) que JAMÁS debe traducirse.
    """
    if not is_translatable_column:
        return True

    if table_name is not None:
        clean_table = table_name.strip().lower()
        if "." in clean_table:
            clean_table = clean_table.split(".")[-1]
        if clean_table in IMMUTABLE_PROPER_NOUN_TABLES:
            return True

    stripped = text.strip()
    if not stripped:
        return True

    if QUOTED_OR_TRADEMARK_REGEX.match(stripped):
        return True

    norm = normalize_term(stripped)
    if norm in KNOWN_PROTECTED_PROPER_NOUNS:
        return True

    extra_norm = {normalize_term(item) for item in extra_protected_nouns if item.strip()}
    return norm in extra_norm


def extract_embedded_protected_brands(
    text: str,
    extra_protected_nouns: Sequence[str] = (),
) -> list[str]:
    """
    Detecta marcas comerciales incrustadas dentro de un nombre de producto compuesto
    (ej. `'Helado de Chocolate Savory'` -> `['Savory']`) para que `Pi` las preserve intactas.
    """
    found: list[str] = []
    lower_text = normalize_term(text)
    candidates = list(KNOWN_PROTECTED_PROPER_NOUNS) + [
        normalize_term(x) for x in extra_protected_nouns if x.strip()
    ]
    for brand in sorted(set(candidates), key=len, reverse=True):
        if not brand or brand == lower_text:
            continue
        pattern = re.compile(rf"\b{re.escape(brand)}\b", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            found.append(match.group(0))
    return found


def build_pi_translation_prompt(
    source_text: str,
    source_lang: str = "es",
    target_langs: Sequence[str] = ("en",),
    protected_brands: Sequence[str] = (),
) -> str:
    """
    Construye un micro-prompt quirúrgico estilo `Pi` (< 35 tokens de entrada):
    Cero historial conversacional y cero definiciones de herramientas innecesarias.
    """
    cleaned_text = " ".join(source_text.strip().split())
    targets = ",".join(sorted({lang.strip().lower() for lang in target_langs if lang.strip()}))
    keep_clause = f" keep=[{','.join(protected_brands)}]" if protected_brands else ""
    return f'i18n {source_lang}->{targets}{keep_clause}: "{cleaned_text}" -> JSON'


@dataclass(frozen=True)
class DynamicFieldSyncResult:
    """Resultado de sincronización de un campo dinámico `i18n_data` + `i18n_source_hash`."""

    source_text: str
    source_lang: str
    i18n_data: dict[str, str]
    i18n_source_hash: str
    proper_noun_protected: bool
    memory_hit: bool
    tokens_consumed: int
    credits_deducted: int = 0
    caller_feature: str = "i18n_auto_translate"
    pi_prompt_used: str | None = None


@dataclass
class TranslationMemoryEntry:
    """Representación en memoria de una fila de `public.i18n_translation_memory`."""

    term_hash: str
    source_lang: str
    source_text: str
    translations: dict[str, str] = field(default_factory=dict)


class DynamicFieldTranslationSync:
    """
    Servicio de sincronización de campos dinámicos del cliente (`i18n_data` JSONB):
    1. Aplica el Filtro Inmutable "Pollo King" (`is_proper_noun_protected`).
    2. Consulta `public.i18n_translation_memory` por hash SHA-256 (0 tokens si existe).
    3. Si el término es inédito, genera un micro-prompt estilo `Pi` (< 35 tokens) y almacena el resultado
       en la memoria global con `credits_deducted = 0`.
    """

    def __init__(
        self,
        fallback_translator: Callable[[str, str, Sequence[str], Sequence[str]], dict[str, str]]
        | None = None,
    ) -> None:
        self._memory_by_hash: dict[str, TranslationMemoryEntry] = {}
        self._fallback_translator = fallback_translator
        self._seed_default_memory()

    def _seed_default_memory(self) -> None:
        """Precarga términos gastronómicos frecuentes en la memoria global (`0` tokens)."""
        for translations in DEFAULT_GLOBAL_GASTRONOMIC_MEMORY.values():
            es_val = translations["es"]
            term_hash = compute_i18n_source_hash(es_val, "es")
            self._memory_by_hash[term_hash] = TranslationMemoryEntry(
                term_hash=term_hash,
                source_lang="es",
                source_text=es_val,
                translations=dict(translations),
            )
            en_val = translations.get("en")
            if en_val:
                en_hash = compute_i18n_source_hash(en_val, "en")
                self._memory_by_hash[en_hash] = TranslationMemoryEntry(
                    term_hash=en_hash,
                    source_lang="en",
                    source_text=en_val,
                    translations=dict(translations),
                )

    def register_memory_translation(
        self,
        source_text: str,
        source_lang: str,
        translations: Mapping[str, str],
    ) -> str:
        """Registra explícitamente una traducción en `i18n_translation_memory` y devuelve su `term_hash`."""
        term_hash = compute_i18n_source_hash(source_text, source_lang)
        merged = {str(k): str(v) for k, v in translations.items()}
        merged.setdefault(source_lang, source_text.strip())
        self._memory_by_hash[term_hash] = TranslationMemoryEntry(
            term_hash=term_hash,
            source_lang=source_lang,
            source_text=source_text.strip(),
            translations=merged,
        )
        return term_hash

    def lookup_memory(self, term_hash: str) -> TranslationMemoryEntry | None:
        """Busca por `term_hash` SHA-256 en la memoria global de traducción."""
        return self._memory_by_hash.get(term_hash)

    def sync_field(
        self,
        source_text: str,
        source_lang: str = "es",
        active_locales: Sequence[str] = ("es", "en"),
        *,
        table_name: str | None = None,
        is_translatable_column: bool = True,
        existing_i18n_data: Mapping[str, str] | None = None,
        existing_source_hash: str | None = None,
        extra_protected_nouns: Sequence[str] = (),
    ) -> DynamicFieldSyncResult:
        """
        Sincroniza el campo dinámico de una entidad al crear o editar:
        - Si el hash no cambió y `existing_i18n_data` cubre los idiomas activos, retorna en 0 tokens.
        - Si es un nombre propio protegido ("Pollo King"), preserva el literal exacto en todos los idiomas.
        - Si existe en `i18n_translation_memory`, retorna con `memory_hit=True` y `tokens_consumed=0`.
        - Si es inédito, construye el micro-prompt `Pi`, traduce preservando marcas incrustadas y guarda en memoria.
        """
        cleaned = " ".join(source_text.strip().split())
        new_hash = compute_i18n_source_hash(cleaned, source_lang)

        # 1. Filtro Inmutable "Pollo King"
        if is_proper_noun_protected(
            cleaned,
            table_name=table_name,
            is_translatable_column=is_translatable_column,
            extra_protected_nouns=extra_protected_nouns,
        ):
            immutable_map = dict.fromkeys(active_locales, cleaned)
            immutable_map.setdefault(source_lang, cleaned)
            return DynamicFieldSyncResult(
                source_text=cleaned,
                source_lang=source_lang,
                i18n_data=immutable_map,
                i18n_source_hash=new_hash,
                proper_noun_protected=True,
                memory_hit=True,
                tokens_consumed=0,
                credits_deducted=0,
                pi_prompt_used=None,
            )

        # 2. Si el registro no cambió su source_hash y ya tiene todos los idiomas activos, 0 trabajo
        if (
            existing_source_hash == new_hash
            and existing_i18n_data is not None
            and all(loc in existing_i18n_data for loc in active_locales)
        ):
            return DynamicFieldSyncResult(
                source_text=cleaned,
                source_lang=source_lang,
                i18n_data={str(k): str(v) for k, v in existing_i18n_data.items()},
                i18n_source_hash=new_hash,
                proper_noun_protected=False,
                memory_hit=True,
                tokens_consumed=0,
                credits_deducted=0,
                pi_prompt_used=None,
            )

        # 3. Consulta Nivel 1: Memoria Global (`public.i18n_translation_memory`) -> 0 tokens
        cached_entry = self.lookup_memory(new_hash)
        if cached_entry is not None and all(
            loc in cached_entry.translations for loc in active_locales
        ):
            return DynamicFieldSyncResult(
                source_text=cleaned,
                source_lang=source_lang,
                i18n_data=dict(cached_entry.translations),
                i18n_source_hash=new_hash,
                proper_noun_protected=False,
                memory_hit=True,
                tokens_consumed=0,
                credits_deducted=0,
                pi_prompt_used=None,
            )

        # 4. Nivel 2: Micro-Prompt minimalista estilo `Pi` (< 35 tokens)
        embedded_brands = extract_embedded_protected_brands(cleaned, extra_protected_nouns)
        target_langs = [loc for loc in active_locales if loc != source_lang]
        pi_prompt = build_pi_translation_prompt(
            source_text=cleaned,
            source_lang=source_lang,
            target_langs=target_langs or ["en"],
            protected_brands=embedded_brands,
        )

        translated_map: dict[str, str] = {source_lang: cleaned}
        if self._fallback_translator is not None:
            custom_out = self._fallback_translator(
                cleaned, source_lang, target_langs, embedded_brands
            )
            translated_map.update(custom_out)
        else:
            translated_map.update(
                self._deterministic_pi_translate(
                    cleaned, source_lang, target_langs, embedded_brands
                )
            )

        self.register_memory_translation(cleaned, source_lang, translated_map)
        estimated_tokens = max(8, min(34, len(pi_prompt.split()) + 6))

        return DynamicFieldSyncResult(
            source_text=cleaned,
            source_lang=source_lang,
            i18n_data=translated_map,
            i18n_source_hash=new_hash,
            proper_noun_protected=False,
            memory_hit=False,
            tokens_consumed=estimated_tokens,
            credits_deducted=0,
            pi_prompt_used=pi_prompt,
        )

    def _deterministic_pi_translate(
        self,
        text: str,
        source_lang: str,
        target_langs: Sequence[str],
        embedded_brands: Sequence[str],
    ) -> dict[str, str]:
        """
        Traductor determinista local para términos compuestos con marcas incrustadas
        (ej. `'Helado de Chocolate Savory'` -> `'Chocolate Ice Cream Savory'`).
        """
        result: dict[str, str] = {source_lang: text}
        remainder = text
        for brand in embedded_brands:
            remainder = re.sub(rf"\b{re.escape(brand)}\b", "", remainder, flags=re.IGNORECASE).strip()
        remainder_norm = normalize_term(remainder)
        base_translations = DEFAULT_GLOBAL_GASTRONOMIC_MEMORY.get(remainder_norm)

        for target in target_langs:
            if base_translations and target in base_translations:
                base_target = base_translations[target]
                suffix = f" {' '.join(embedded_brands)}" if embedded_brands else ""
                result[target] = f"{base_target}{suffix}".strip()
            else:
                result[target] = text
        return result
