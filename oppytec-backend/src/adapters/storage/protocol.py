"""
oppytec-backend/src/adapters/storage/protocol.py
Contrato (`StoragePort`), modelos de datos (`OptimizedMediaPair`, `StoredMediaKeys`)
y validación estricta de llaves Multi-Tenant en Cloudflare R2 (`is_valid_r2_media_key`).
Cumple `.agent/rules/18-media-storage-r2-and-quota-governance.md`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

MediaVariantType = Literal["thumb", "display"]

R2_MEDIA_KEY_PATTERN: re.Pattern[str] = re.compile(
    r"^(local|preview|ci|staging|production)/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/[a-z_]+/[a-zA-Z0-9_-]+/(thumb|display)\.webp$"
)


def is_valid_r2_media_key(object_key: str) -> bool:
    """
    Valida que una llave de objeto de Cloudflare R2 aísle estrictamente por
    `{env}/{holding_id}/{tenant_id}/{category}/{entity_id}/(thumb|display).webp`
    y no contenga secuencias de escape (`..`).
    """
    if ".." in object_key or object_key.startswith("/"):
        return False
    return bool(R2_MEDIA_KEY_PATTERN.match(object_key))


def build_r2_media_object_key(
    *,
    environment: str,
    holding_id: str,
    tenant_id: str,
    category: str,
    entity_id: str,
    variant: MediaVariantType,
) -> str:
    """
    Construye una llave de objeto canónica y verifica que cumpla `R2_MEDIA_KEY_PATTERN`.
    Garantiza 0% de colisiones entre Tenants aunque suban archivos con el mismo nombre.
    """
    candidate = f"{environment}/{holding_id}/{tenant_id}/{category}/{entity_id}/{variant}.webp"
    if not is_valid_r2_media_key(candidate):
        raise ValueError(
            f"Invalid R2 media object key '{candidate}'. "
            "Must match '{env}/{holding_id}/{tenant_id}/{category}/{entity_id}/(thumb|display).webp'."
        )
    return candidate


@dataclass(frozen=True)
class OptimizedMediaPair:
    """Par inmutable de imágenes WebP optimizadas en memoria (sin EXIF/GPS) con hash SHA-256."""

    sha256_hash: str
    thumb_bytes: bytes
    display_bytes: bytes
    thumb_width: int
    thumb_height: int
    display_width: int
    display_height: int

    @property
    def total_size_bytes(self) -> int:
        """Tamaño total real en bytes de `thumb.webp` + `display.webp` para control de cuota MB."""
        return len(self.thumb_bytes) + len(self.display_bytes)


@dataclass(frozen=True)
class StoredMediaKeys:
    """Llaves y URLs resultantes tras almacenar un `OptimizedMediaPair` en R2 o almacenamiento local."""

    thumb_object_key: str
    display_object_key: str
    thumb_url: str
    display_url: str
    sha256_hash: str
    total_size_bytes: int


@runtime_checkable
class StoragePort(Protocol):
    """Puerto de almacenamiento asíncrono para activos visuales Multi-Tenant."""

    async def store_media_pair(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        category: str,
        entity_id: str,
        media_pair: OptimizedMediaPair,
    ) -> StoredMediaKeys:
        """Almacena `thumb.webp` y `display.webp` bajo el prefijo aislado del Tenant."""
        ...

    async def delete_media_pair(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        thumb_object_key: str,
        display_object_key: str,
    ) -> bool:
        """Elimina físicamente ambas variantes `.webp` verificando que pertenezcan al Tenant."""
        ...

    def generate_presigned_url(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        object_key: str,
        ttl_seconds: int = 300,
    ) -> str:
        """Genera una URL firmada temporal (`TTL = 300s`) validando aislamiento por Tenant."""
        ...
