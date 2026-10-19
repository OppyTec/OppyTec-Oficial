"""
oppytec-backend/src/adapters/storage/r2_storage.py
Adaptador de almacenamiento Cloudflare R2 con aislamiento estricto por
`{env}/{holding_id}/{tenant_id}/{category}/{entity_id}/(thumb|display).webp`.
Previene colisiones entre Tenants y soporta generación de URLs firmadas temporales (`TTL = 300s`).
"""
from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

from src.adapters.storage.protocol import (
    OptimizedMediaPair,
    StoredMediaKeys,
    build_r2_media_object_key,
    is_valid_r2_media_key,
)
from src.core.config import Settings, get_settings
from src.core.exceptions import CrossTenantAccessError


class R2MediaStorageAdapter:
    """
    Adaptador de Cloudflare R2 que garantiza que todas las llaves cumplan `is_valid_r2_media_key`
    y que ningún Tenant pueda leer, sobrescribir ni eliminar objetos fuera de su propio prefijo.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings: Settings = settings or get_settings()
        self._objects: dict[str, bytes] = {}

    @property
    def bucket_name(self) -> str:
        """Nombre del bucket R2 configurado para el entorno actual."""
        return self._settings.R2_MEDIA_BUCKET_NAME

    def _expected_tenant_prefix(self, holding_id: str, tenant_id: str) -> str:
        return f"{self._settings.ENVIRONMENT}/{holding_id}/{tenant_id}/"

    def _assert_key_belongs_to_tenant(
        self,
        *,
        object_key: str,
        holding_id: str,
        tenant_id: str,
    ) -> None:
        if not is_valid_r2_media_key(object_key):
            raise ValueError(f"Invalid R2 media key format: '{object_key}'")
        expected_prefix = self._expected_tenant_prefix(holding_id, tenant_id)
        if not object_key.startswith(expected_prefix):
            raise CrossTenantAccessError(
                f"Cross-tenant storage access blocked: key '{object_key}' does not belong "
                f"to prefix '{expected_prefix}'.",
                i18n_key="storage:errors.cross_tenant_key_forbidden",
            )

    async def store_media_pair(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        category: str,
        entity_id: str,
        media_pair: OptimizedMediaPair,
    ) -> StoredMediaKeys:
        """Almacena `thumb.webp` y `display.webp` bajo `{env}/{holding_id}/{tenant_id}/{category}/{entity_id}/`."""
        env = self._settings.ENVIRONMENT
        thumb_key = build_r2_media_object_key(
            environment=env,
            holding_id=holding_id,
            tenant_id=tenant_id,
            category=category,
            entity_id=entity_id,
            variant="thumb",
        )
        display_key = build_r2_media_object_key(
            environment=env,
            holding_id=holding_id,
            tenant_id=tenant_id,
            category=category,
            entity_id=entity_id,
            variant="display",
        )
        self._objects[thumb_key] = media_pair.thumb_bytes
        self._objects[display_key] = media_pair.display_bytes

        base_url = self._settings.R2_PUBLIC_URL.rstrip("/")
        version_tag = media_pair.sha256_hash[:16]
        return StoredMediaKeys(
            thumb_object_key=thumb_key,
            display_object_key=display_key,
            thumb_url=f"{base_url}/{thumb_key}?v={version_tag}",
            display_url=f"{base_url}/{display_key}?v={version_tag}",
            sha256_hash=media_pair.sha256_hash,
            total_size_bytes=media_pair.total_size_bytes,
        )

    async def delete_media_pair(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        thumb_object_key: str,
        display_object_key: str,
    ) -> bool:
        """Elimina ambas variantes `.webp` tras verificar que pertenecen al `holding_id` y `tenant_id`."""
        self._assert_key_belongs_to_tenant(
            object_key=thumb_object_key,
            holding_id=holding_id,
            tenant_id=tenant_id,
        )
        self._assert_key_belongs_to_tenant(
            object_key=display_object_key,
            holding_id=holding_id,
            tenant_id=tenant_id,
        )
        removed_thumb = self._objects.pop(thumb_object_key, None) is not None
        removed_display = self._objects.pop(display_object_key, None) is not None
        return removed_thumb or removed_display

    def get_object_bytes(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        object_key: str,
    ) -> bytes | None:
        """Obtiene los bytes almacenados verificando aislamiento estricto de Tenant."""
        self._assert_key_belongs_to_tenant(
            object_key=object_key,
            holding_id=holding_id,
            tenant_id=tenant_id,
        )
        return self._objects.get(object_key)

    def generate_presigned_url(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        object_key: str,
        ttl_seconds: int = 300,
    ) -> str:
        """Genera una URL firmada HMAC-SHA256 con expiración corta (`ttl_seconds=300`)."""
        self._assert_key_belongs_to_tenant(
            object_key=object_key,
            holding_id=holding_id,
            tenant_id=tenant_id,
        )
        expires_at = int(time.time()) + max(1, min(ttl_seconds, 3600))
        secret = self._settings.R2_SECRET_ACCESS_KEY.get_secret_value().encode("utf-8")
        canonical = f"{self.bucket_name}:{object_key}:{expires_at}".encode()
        signature = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
        query = urlencode(
            {
                "X-Amz-Expires": str(ttl_seconds),
                "X-Oppy-Expires-At": str(expires_at),
                "X-Amz-Signature": signature,
            }
        )
        base_url = self._settings.R2_PUBLIC_URL.rstrip("/")
        return f"{base_url}/{object_key}?{query}"
