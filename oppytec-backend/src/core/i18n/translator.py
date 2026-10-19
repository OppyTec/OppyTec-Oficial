"""
oppytec-backend/src/core/i18n/translator.py
Motor de Internacionalización Estática para Backend (FastAPI, Notificaciones, Correos y PDFs).
Resuelve el idioma activo desde `Accept-Language` o preferencia del usuario (`es`, `en`, fallback a `es`)
y ejecuta interpolación determinista `{{variable}}` sobre los catálogos JSON en memoria.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Literal

SupportedLanguage = Literal["es", "en"]
SUPPORTED_LANGUAGES: tuple[SupportedLanguage, ...] = ("es", "en")
FUTURE_SCALABLE_LANGUAGES: tuple[str, ...] = ("pt", "fr", "it", "de")
DEFAULT_LANGUAGE: SupportedLanguage = "es"

INTERPOLATION_PATTERN: re.Pattern[str] = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
LOCALES_ROOT: Path = Path(__file__).resolve().parent / "locales"


def _normalize_lang_tag(raw_tag: str) -> SupportedLanguage | None:
    """Extrae el código ISO primario (`es` o `en`) desde una etiqueta BCP-47 como `en-US` o `es_CL`."""
    cleaned = raw_tag.strip().lower().replace("_", "-")
    if not cleaned:
        return None
    primary = cleaned.split("-")[0]
    if primary == "es":
        return "es"
    if primary == "en":
        return "en"
    return None


def resolve_language(
    accept_language: str | None = None,
    user_preferred_language: str | None = None,
) -> SupportedLanguage:
    """
    Resuelve el idioma activo priorizando `user_preferred_language` si es válido,
    luego la cabecera HTTP `Accept-Language` (con pesos `q=`), y fallback determinista a `es`.
    """
    if user_preferred_language:
        preferred = _normalize_lang_tag(user_preferred_language)
        if preferred is not None:
            return preferred

    if not accept_language:
        return DEFAULT_LANGUAGE

    candidates: list[tuple[int, int, SupportedLanguage]] = []
    for index, raw_part in enumerate(accept_language.split(",")):
        part = raw_part.strip()
        if not part:
            continue
        segments = [seg.strip() for seg in part.split(";")]
        lang_code = _normalize_lang_tag(segments[0])
        if lang_code is None:
            continue
        q_milli = 1000
        for param in segments[1:]:
            if param.lower().startswith("q="):
                q_str = param[2:].strip()
                try:
                    # Convertimos q-weight (0.000..1.000) a entero en milésimas sin depender de float impreciso
                    if "." in q_str:
                        whole, frac = q_str.split(".", 1)
                        frac_padded = (frac + "000")[:3]
                        q_milli = int(whole or "0") * 1000 + int(frac_padded)
                    else:
                        q_milli = int(q_str) * 1000
                except ValueError:
                    q_milli = 0
        if q_milli > 0:
            candidates.append((q_milli, -index, lang_code))

    if not candidates:
        return DEFAULT_LANGUAGE

    candidates.sort(reverse=True)
    return candidates[0][2]


def flatten_catalog_dict(data: Mapping[str, object], prefix: str = "") -> dict[str, str]:
    """Aplana recursivamente un diccionario JSON anidado a rutas separadas por punto (`a.b.c`)."""
    flattened: dict[str, str] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            nested_map = {str(k): v for k, v in value.items()}
            flattened.update(flatten_catalog_dict(nested_map, full_key))
        else:
            flattened[full_key] = str(value)
    return flattened


def interpolate_template(template: str, params: Mapping[str, object] | None = None) -> str:
    """Reemplaza determinísticamente todos los marcadores `{{variable}}` con los valores de `params`."""
    if not params:
        return template

    def _replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in params:
            return str(params[var_name])
        return match.group(0)

    return INTERPOLATION_PATTERN.sub(_replacer, template)


class I18nCatalogTranslator:
    """
    Traductor en memoria para catálogos JSON por idioma y namespace (`common`, `errors`, etc.).
    """

    def __init__(self, locales_dir: Path | None = None) -> None:
        self._locales_dir = locales_dir or LOCALES_ROOT
        self._catalogs: dict[SupportedLanguage, dict[str, dict[str, str]]] = {
            "es": {},
            "en": {},
        }
        self.reload()

    def reload(self) -> None:
        """Carga en memoria todos los archivos `locales/{es,en}/*.json`."""
        for lang in SUPPORTED_LANGUAGES:
            lang_dir = self._locales_dir / lang
            self._catalogs[lang] = {}
            if not lang_dir.exists():
                continue
            for json_file in sorted(lang_dir.glob("*.json")):
                namespace = json_file.stem
                raw_data = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(raw_data, Mapping):
                    typed_map = {str(k): v for k, v in raw_data.items()}
                    self._catalogs[lang][namespace] = flatten_catalog_dict(typed_map)

    def translate(
        self,
        key: str,
        lang: str | None = None,
        namespace: str = "common",
        params: Mapping[str, object] | None = None,
    ) -> str:
        """
        Obtiene la traducción para `key` (soporta `namespace:dot.key` o `dot.key` con `namespace`).
        Si no existe en el idioma solicitado, hace fallback a `es` y finalmente devuelve la llave.
        """
        resolved_lang = resolve_language(user_preferred_language=lang)
        target_ns = namespace
        target_key = key
        if ":" in key:
            target_ns, target_key = key.split(":", 1)

        template = self._catalogs.get(resolved_lang, {}).get(target_ns, {}).get(target_key)
        if template is None:
            template = self._catalogs.get(DEFAULT_LANGUAGE, {}).get(target_ns, {}).get(target_key)
        if template is None:
            return key
        return interpolate_template(template, params)


@lru_cache(maxsize=1)
def get_translator() -> I18nCatalogTranslator:
    """Devuelve la instancia singleton de `I18nCatalogTranslator`."""
    return I18nCatalogTranslator()


def t(
    key: str,
    lang: str | None = None,
    namespace: str = "common",
    params: Mapping[str, object] | None = None,
) -> str:
    """Atajo funcional para traducir llaves estáticas (`t('common:actions.save', lang='en')`)."""
    return get_translator().translate(key=key, lang=lang, namespace=namespace, params=params)
