"""
oppytec-backend/src/adapters/storage/image_optimizer.py
Pipeline de optimización de imágenes en memoria con `Pillow`:
- Verifica Magic Bytes reales (JPEG, PNG, WebP) y rechaza SVG / ejecutables (prevención XSS/RCE).
- Limpia el 100% de metadatos EXIF/GPS reconstituyendo píxeles limpios (ISO/IEC 27001).
- Genera `thumb.webp` (máx. 256x256 px) y `display.webp` (máx. 1024x1024 px).
- Calcula `sha256_hash` determinista y `total_size_bytes`.
"""
from __future__ import annotations

import hashlib
import io

from PIL import Image

from src.adapters.storage.protocol import OptimizedMediaPair

THUMB_MAX_DIMENSION: int = 256
DISPLAY_MAX_DIMENSION: int = 1024
THUMB_WEBP_QUALITY: int = 80
DISPLAY_WEBP_QUALITY: int = 85

JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
RIFF_MAGIC = b"RIFF"
WEBP_MAGIC = b"WEBP"


def validate_image_magic_bytes(raw_bytes: bytes) -> str:
    """
    Inspecciona los primeros bytes binarios reales para admitir solo JPEG, PNG o WebP.
    Rechaza explícitamente archivos `.svg`, HTML o scripts disfrazados de imagen.
    """
    if len(raw_bytes) < 12:
        raise ValueError("InvalidImageMagicBytes: Image payload is too small (< 12 bytes).")
    header_lower = raw_bytes[:256].lstrip().lower()
    if header_lower.startswith((b"<svg", b"<?xml", b"<!doctype", b"<html", b"<script")):
        raise ValueError("ForbiddenSvgOrHtmlUpload: SVG and HTML uploads are strictly forbidden.")
    if raw_bytes.startswith(JPEG_MAGIC):
        return "JPEG"
    if raw_bytes.startswith(PNG_MAGIC):
        return "PNG"
    if raw_bytes[:4] == RIFF_MAGIC and raw_bytes[8:12] == WEBP_MAGIC:
        return "WEBP"
    raise ValueError(
        "InvalidImageMagicBytes: Unsupported file signature; only JPEG, PNG, and WebP are allowed."
    )


def _strip_exif_and_normalize(source_image: Image.Image) -> Image.Image:
    """
    Crea una nueva imagen en memoria copiando únicamente la matriz de píxeles (`RGBA` o `RGB`),
    descartando cualquier cabecera EXIF, GPS, ICC o comentario embebido.
    """
    target_mode = "RGBA" if source_image.mode in ("RGBA", "LA", "P") else "RGB"
    converted = source_image.convert(target_mode)
    clean_img = Image.new(target_mode, converted.size)
    clean_img.putdata(list(converted.getdata()))
    return clean_img


def _encode_resized_webp(
    clean_image: Image.Image,
    max_dimension: int,
    quality: int,
) -> tuple[bytes, int, int]:
    """Redimensiona preservando relación de aspecto (`LANCZOS`) y codifica a `.webp` sin EXIF."""
    working = clean_image.copy()
    working.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    working.save(buffer, format="WEBP", quality=quality, method=4)
    webp_bytes = buffer.getvalue()
    return webp_bytes, working.width, working.height


def optimize_image_to_webp_pair(raw_bytes: bytes) -> OptimizedMediaPair:
    """
    Procesa los bytes de una imagen original validando Magic Bytes, eliminando metadatos EXIF/GPS
    y generando en memoria el par `thumb.webp` (256px) + `display.webp` (1024px).
    """
    validate_image_magic_bytes(raw_bytes)
    with Image.open(io.BytesIO(raw_bytes)) as opened:
        opened.load()
        clean_img = _strip_exif_and_normalize(opened)

    thumb_bytes, thumb_w, thumb_h = _encode_resized_webp(
        clean_img,
        max_dimension=THUMB_MAX_DIMENSION,
        quality=THUMB_WEBP_QUALITY,
    )
    display_bytes, disp_w, disp_h = _encode_resized_webp(
        clean_img,
        max_dimension=DISPLAY_MAX_DIMENSION,
        quality=DISPLAY_WEBP_QUALITY,
    )
    digest = hashlib.sha256(thumb_bytes + display_bytes).hexdigest()

    return OptimizedMediaPair(
        sha256_hash=digest,
        thumb_bytes=thumb_bytes,
        display_bytes=display_bytes,
        thumb_width=thumb_w,
        thumb_height=thumb_h,
        display_width=disp_w,
        display_height=disp_h,
    )
