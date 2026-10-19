"""
oppytec-backend/src/core/guards/xss_sanitizer.py
Sanitizador y bloqueador determinista de vectores de inyección en entradas de texto y rutas:
- Políglotas XSS (`<script`, `javascript:`, `onerror=`, `onload=`, `<iframe`, `<svg`, `data:text/html`)
- Server-Side Template Injection / SSTI (`{{`, `{%`, `${`)
- SQL Injection clásico / apilado (`UNION SELECT`, `' OR '1'='1`, `; DROP TABLE`, `--`)
- Path Traversal / LFI (`../`, `..\\`, `/etc/passwd`, bytes nulos `\x00`).
"""
from __future__ import annotations

import html
import re
from urllib.parse import unquote

from src.core.exceptions import SecurityValidationError

XSS_POLYGLOT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"<\s*/?\s*script\b", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"vbscript\s*:", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
    re.compile(r"\bon(?:error|load|click|mouseover|focus|toggle|submit)\s*=", re.IGNORECASE),
    re.compile(r"<\s*(?:iframe|object|embed|svg|math|meta|link|style|base)\b", re.IGNORECASE),
)

SSTI_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\{\{.*?\}\}", re.DOTALL),
    re.compile(r"\{%.*?%\}", re.DOTALL),
    re.compile(r"\$\{[^{}]+\}"),
)

SQLI_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bunion\s+(?:all\s+)?select\b", re.IGNORECASE),
    re.compile(r"(?:'|\"|\b)\s*or\s+['\"]?1['\"]?\s*=\s*['\"]?1", re.IGNORECASE),
    re.compile(r";\s*(?:drop|delete|truncate|alter|update|insert)\s+", re.IGNORECASE),
    re.compile(r"\b(?:pg_sleep|waitfor\s+delay|information_schema)\b", re.IGNORECASE),
)

PATH_TRAVERSAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|[/\\])\.\.(?:[/\\]|$)"),
    re.compile(r"\.\.[/\\]"),
    re.compile(r"(?:/etc/passwd|/etc/shadow|/proc/self|c:\\windows\\system32)", re.IGNORECASE),
)


def validate_no_path_traversal(path_str: str, *, field_name: str = "path") -> str:
    """
    Verifica que una ruta o identificador de archivo no contenga secuencias de escape `..`,
    bytes nulos `\x00` ni rutas absolutas del sistema operativo (`/etc/passwd`).
    """
    if "\x00" in path_str:
        raise SecurityValidationError(
            f"Null byte detected in '{field_name}'.",
            i18n_key="security:errors.null_byte_blocked",
            error_code="NULL_BYTE_INJECTION",
        )
    decoded = unquote(unquote(path_str)).strip()
    if "\x00" in decoded:
        raise SecurityValidationError(
            f"Encoded null byte detected in '{field_name}'.",
            i18n_key="security:errors.null_byte_blocked",
            error_code="NULL_BYTE_INJECTION",
        )
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern.search(path_str) or pattern.search(decoded):
            raise SecurityValidationError(
                f"Path traversal or LFI attempt blocked in '{field_name}'.",
                i18n_key="security:errors.path_traversal_blocked",
                error_code="PATH_TRAVERSAL_BLOCKED",
            )
    return path_str.strip()


def sanitize_text_input(
    value: str,
    *,
    field_name: str = "input",
    block_polyglots: bool = True,
    escape_html: bool = False,
) -> str:
    """
    Inspecciona una cadena de entrada contra políglotas XSS, SSTI, SQLi y LFI/Path Traversal.
    - Si `block_polyglots=True` (por defecto), lanza `SecurityValidationError` (HTTP 422) ante cualquier vector.
    - Si `block_polyglots=False`, neutraliza/escapa las etiquetas HTML y plantillas peligrosas.
    """
    if "\x00" in value:
        raise SecurityValidationError(
            f"Null byte injection blocked in '{field_name}'.",
            i18n_key="security:errors.null_byte_blocked",
            error_code="NULL_BYTE_INJECTION",
        )

    decoded = unquote(value)

    for pattern in XSS_POLYGLOT_PATTERNS:
        if block_polyglots and (pattern.search(value) or pattern.search(decoded)):
            raise SecurityValidationError(
                f"XSS polyglot payload blocked in '{field_name}'.",
                i18n_key="security:errors.xss_payload_blocked",
                error_code="XSS_PAYLOAD_BLOCKED",
            )

    for pattern in SSTI_PATTERNS:
        if block_polyglots and (pattern.search(value) or pattern.search(decoded)):
            raise SecurityValidationError(
                f"Server-Side Template Injection (SSTI) payload blocked in '{field_name}'.",
                i18n_key="security:errors.ssti_payload_blocked",
                error_code="SSTI_PAYLOAD_BLOCKED",
            )

    for pattern in SQLI_PATTERNS:
        if block_polyglots and (pattern.search(value) or pattern.search(decoded)):
            raise SecurityValidationError(
                f"SQL Injection pattern blocked in '{field_name}'.",
                i18n_key="security:errors.sqli_payload_blocked",
                error_code="SQLI_PAYLOAD_BLOCKED",
            )

    for pattern in PATH_TRAVERSAL_PATTERNS:
        if block_polyglots and (pattern.search(value) or pattern.search(decoded)):
            raise SecurityValidationError(
                f"Path traversal pattern blocked in '{field_name}'.",
                i18n_key="security:errors.path_traversal_blocked",
                error_code="PATH_TRAVERSAL_BLOCKED",
            )

    cleaned = value.strip()
    if escape_html or not block_polyglots:
        return html.escape(cleaned, quote=True)
    return cleaned
