"""
oppytec-backend/src/adapters/storage/__init__.py
Adaptadores de almacenamiento de imágenes y documentos en Cloudflare R2 y disco local aislado por entorno.
"""
from __future__ import annotations

from src.adapters.storage.image_optimizer import optimize_image_to_webp_pair
from src.adapters.storage.local_storage import LocalMediaStorageAdapter
from src.adapters.storage.protocol import (
    R2_MEDIA_KEY_PATTERN,
    OptimizedMediaPair,
    StoragePort,
    StoredMediaKeys,
    build_r2_media_object_key,
    is_valid_r2_media_key,
)
from src.adapters.storage.r2_storage import R2MediaStorageAdapter

__all__ = [
    "R2_MEDIA_KEY_PATTERN",
    "LocalMediaStorageAdapter",
    "OptimizedMediaPair",
    "R2MediaStorageAdapter",
    "StoragePort",
    "StoredMediaKeys",
    "build_r2_media_object_key",
    "is_valid_r2_media_key",
    "optimize_image_to_webp_pair",
]
