"""
oppytec-backend/src/core/guards/file_magic_guard.py
Guardia de seguridad binaria para subida de archivos e importación de planillas:
- Inspección de Magic Bytes reales (`%PDF-`, PNG, WEBP, JPEG, `.xlsx` ZIP).
- Rechazo de ejecutables camuflados (`MZ`, `\x7fELF`, `<?php`, `<script`, `#!`).
- Protección anti-Zip Bomb en archivos `.xlsx` / `.zip` (tamaño descomprimido máximo 25 MB, ratio <= 50x, cero `..` en entradas).
- Sanitización de celdas Excel/CSV contra Formula Injection / DDE (`=`, `+`, `-`, `@`, `\t`, `\r`).
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from src.core.exceptions import SecurityValidationError

DEFAULT_MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB
MAX_ZIP_UNCOMPRESSED_BYTES: int = 25 * 1024 * 1024  # 25 MB
MAX_ZIP_COMPRESSION_RATIO: int = 50
MAX_ZIP_ENTRIES: int = 2000

ALLOWED_MIME_BY_EXTENSION: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

FORBIDDEN_EXECUTABLE_SIGNATURES: tuple[bytes, ...] = (
    b"MZ",
    b"\x7fELF",
    b"<?php",
    b"<script",
    b"#!/",
)

DANGEROUS_DDE_PATTERNS: tuple[str, ...] = (
    "=cmd|",
    "=powershell",
    "=importxml",
    "=importdata",
    "=importfeed",
    "=importhtml",
    "=importrange",
    "=hyperlink(",
    "+cmd|",
    "-cmd|",
    "@sum(1+1)*cmd|",
)

FORMULA_PREFIX_CHARS: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")


def detect_magic_mime_type(content: bytes) -> str | None:
    """Detecta el tipo MIME real inspeccionando los primeros bytes binarios (Magic Bytes)."""
    if len(content) < 4:
        return None
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"PK\x03\x04"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return None


def _inspect_xlsx_zip_safety(content: bytes) -> None:
    """Inspecciona un contenedor ZIP/XLSX contra Zip Bombs, entradas excesivas y Path Traversal."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            infos = zf.infolist()
            if not infos:
                raise SecurityValidationError(
                    "Uploaded XLSX/ZIP archive is empty.",
                    i18n_key="security:errors.empty_archive",
                    error_code="EMPTY_ZIP_ARCHIVE",
                )
            if len(infos) > MAX_ZIP_ENTRIES:
                raise SecurityValidationError(
                    f"Archive contains too many entries ({len(infos)} > {MAX_ZIP_ENTRIES}).",
                    i18n_key="security:errors.zip_bomb_detected",
                    error_code="ZIP_BOMB_TOO_MANY_ENTRIES",
                )

            total_uncompressed = 0
            total_compressed = 0
            for info in infos:
                normalized_name = info.filename.replace("\\", "/")
                if (
                    normalized_name.startswith("/")
                    or ".." in normalized_name.split("/")
                    or "\x00" in normalized_name
                ):
                    raise SecurityValidationError(
                        f"Unsafe path traversal entry '{info.filename}' inside archive.",
                        i18n_key="security:errors.archive_path_traversal",
                        error_code="ZIP_PATH_TRAVERSAL",
                    )
                total_uncompressed += max(0, info.file_size)
                total_compressed += max(1, info.compress_size)
                if total_uncompressed > MAX_ZIP_UNCOMPRESSED_BYTES:
                    raise SecurityValidationError(
                        f"Zip Bomb detected: uncompressed size exceeds {MAX_ZIP_UNCOMPRESSED_BYTES} bytes.",
                        i18n_key="security:errors.zip_bomb_detected",
                        error_code="ZIP_BOMB_DETECTED",
                    )
                entry_ratio = info.file_size // max(1, info.compress_size)
                if info.file_size > 1024 * 1024 and entry_ratio > MAX_ZIP_COMPRESSION_RATIO:
                    raise SecurityValidationError(
                        f"Zip Bomb detected: compression ratio {entry_ratio}x exceeds {MAX_ZIP_COMPRESSION_RATIO}x.",
                        i18n_key="security:errors.zip_bomb_detected",
                        error_code="ZIP_BOMB_RATIO_EXCEEDED",
                    )

            overall_ratio = total_uncompressed // max(1, total_compressed)
            if total_uncompressed > 1024 * 1024 and overall_ratio > MAX_ZIP_COMPRESSION_RATIO:
                raise SecurityValidationError(
                    f"Zip Bomb detected: archive ratio {overall_ratio}x exceeds {MAX_ZIP_COMPRESSION_RATIO}x.",
                    i18n_key="security:errors.zip_bomb_detected",
                    error_code="ZIP_BOMB_RATIO_EXCEEDED",
                )
    except zipfile.BadZipFile as exc:
        raise SecurityValidationError(
            "Corrupted or invalid XLSX/ZIP container.",
            i18n_key="security:errors.corrupted_xlsx_archive",
            error_code="CORRUPTED_XLSX_ARCHIVE",
        ) from exc


def validate_file_magic_bytes(
    content: bytes,
    filename: str,
    allowed_types: frozenset[str] | set[str] | None = None,
    max_size_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> str:
    """
    Valida que el archivo `content` no esté vacío, no exceda `max_size_bytes`,
    no contenga firmas ejecutables y que sus Magic Bytes coincidan con la extensión declarada.
    Devuelve el MIME type verificado.
    """
    if not content:
        raise SecurityValidationError(
            "Uploaded file cannot be empty.",
            i18n_key="security:errors.empty_file",
            error_code="EMPTY_FILE_UPLOAD",
        )
    if len(content) > max_size_bytes:
        raise SecurityValidationError(
            f"Uploaded file size ({len(content)} bytes) exceeds limit ({max_size_bytes} bytes).",
            i18n_key="security:errors.file_too_large",
            error_code="FILE_TOO_LARGE",
            status_code=413,
        )

    cleaned_name = filename.strip()
    if not cleaned_name or ".." in cleaned_name or "/" in cleaned_name or "\\" in cleaned_name:
        raise SecurityValidationError(
            f"Invalid or unsafe filename '{filename}'.",
            i18n_key="security:errors.invalid_filename",
            error_code="UNSAFE_FILENAME",
        )

    head_sample = content[:64].lstrip()
    for bad_sig in FORBIDDEN_EXECUTABLE_SIGNATURES:
        if content.startswith(bad_sig) or head_sample.lower().startswith(bad_sig.lower()):
            raise SecurityValidationError(
                "Executable or script payload detected in uploaded file.",
                i18n_key="security:errors.executable_payload_blocked",
                error_code="EXECUTABLE_SPOOFING_BLOCKED",
            )

    ext = Path(cleaned_name).suffix.lower()
    expected_mime = ALLOWED_MIME_BY_EXTENSION.get(ext)
    if expected_mime is None:
        raise SecurityValidationError(
            f"Unsupported file extension '{ext}'.",
            i18n_key="security:errors.unsupported_file_extension",
            error_code="UNSUPPORTED_FILE_EXTENSION",
        )

    detected_mime = detect_magic_mime_type(content)
    if detected_mime is None or detected_mime != expected_mime:
        raise SecurityValidationError(
            f"File Magic Bytes mismatch for '{cleaned_name}': expected '{expected_mime}', got '{detected_mime}'.",
            i18n_key="security:errors.magic_bytes_mismatch",
            error_code="FILE_MAGIC_BYTES_MISMATCH",
        )

    if allowed_types is not None and detected_mime not in allowed_types and ext not in allowed_types:
        raise SecurityValidationError(
            f"File type '{detected_mime}' is not allowed for this endpoint.",
            i18n_key="security:errors.file_type_not_allowed",
            error_code="FILE_TYPE_NOT_ALLOWED",
        )

    if detected_mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        _inspect_xlsx_zip_safety(content)

    return detected_mime


def sanitize_spreadsheet_cell(
    value: str,
    *,
    reject_dde_payloads: bool = True,
) -> str:
    """
    Neutraliza vectores de CSV / Excel Formula Injection (`=`, `+`, `-`, `@`, `\t`, `\r`).
    Si detecta un payload DDE malicioso (`=cmd|`, `=IMPORTXML`, etc.) y `reject_dde_payloads=True`,
    lanza `SecurityValidationError`; en caso contrario antepone comilla simple `'`.
    """
    if not value:
        return value

    lower_trimmed = value.strip().lower()
    for dde_pattern in DANGEROUS_DDE_PATTERNS:
        if lower_trimmed.startswith(dde_pattern) or dde_pattern in lower_trimmed:
            if reject_dde_payloads:
                raise SecurityValidationError(
                    "Malicious spreadsheet formula/DDE injection payload rejected.",
                    i18n_key="security:errors.csv_formula_injection_blocked",
                    error_code="CSV_FORMULA_INJECTION_BLOCKED",
                )
            return f"'{value}"

    if value.startswith(FORMULA_PREFIX_CHARS):
        return f"'{value}"
    return value


@dataclass(frozen=True)
class ValidatedUploadPayload:
    """Archivo subido cuyos Magic Bytes y límites de tamaño ya fueron verificados."""

    filename: str
    mime_type: str
    content: bytes
    size_bytes: int


class RequireSafeFileUpload:
    """Dependencia FastAPI que valida `UploadFile` mediante `validate_file_magic_bytes`."""

    def __init__(
        self,
        *,
        allowed_types: frozenset[str] | set[str] | None = None,
        max_size_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    ) -> None:
        self.allowed_types = frozenset(allowed_types) if allowed_types is not None else None
        self.max_size_bytes = max_size_bytes

    async def __call__(self, file: UploadFile) -> ValidatedUploadPayload:
        raw_bytes = await file.read(self.max_size_bytes + 1)
        fname = file.filename or "upload.bin"
        verified_mime = validate_file_magic_bytes(
            content=raw_bytes,
            filename=fname,
            allowed_types=self.allowed_types,
            max_size_bytes=self.max_size_bytes,
        )
        return ValidatedUploadPayload(
            filename=fname,
            mime_type=verified_mime,
            content=raw_bytes,
            size_bytes=len(raw_bytes),
        )
