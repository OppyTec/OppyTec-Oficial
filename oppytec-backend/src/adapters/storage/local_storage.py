"""
oppytec-backend/src/adapters/storage/local_storage.py
Adaptador de almacenamiento en disco local para entornos `local` y `ci`,
aislado por `ENV_NAMESPACE` y estructura `{env}/{holding_id}/{tenant_id}/{category}/{entity_id}/`.
"""
from __future__ import annotations

import hashlib
import hmac
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode

from src.adapters.storage.protocol import (
    OptimizedMediaPair,
    StoredMediaKeys,
    build_r2_media_object_key,
    is_valid_r2_media_key,
)
from src.core.config import Settings, get_settings
from src.core.exceptions import CrossTenantAccessError


class LocalMediaStorageAdapter:
    """
    Almacenamiento local aislado por `ENV_NAMESPACE` que mantiene paridad 1:1
    con las llaves `{env}/{holding_id}/{tenant_id}/{category}/{entity_id}/(thumb|display).webp`.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings: Settings = settings or get_settings()
        default_root = (
            Path(tempfile.gettempdir())
            / "oppytec_media_local"
            / self._settings.ENV_NAMESPACE
        )
        self._base_dir: Path = (base_dir or default_root).resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        """Directorio raíz aislado por `ENV_NAMESPACE`."""
        return self._base_dir

    def _resolve_safe_path(
        self,
        *,
        object_key: str,
        holding_id: str,
        tenant_id: str,
    ) -> Path:
        if not is_valid_r2_media_key(object_key):
            raise ValueError(f"Invalid media object key format: '{object_key}'")
        expected_prefix = f"{self._settings.ENVIRONMENT}/{holding_id}/{tenant_id}/"
        if not object_key.startswith(expected_prefix):
            raise CrossTenantAccessError(
                f"Cross-tenant local storage access blocked for key '{object_key}'.",
                i18n_key="storage:errors.cross_tenant_key_forbidden",
            )
        target = (self._base_dir / object_key).resolve()
        if not target.is_relative_to(self._base_dir):
            raise ValueError(f"Path traversal attempt detected for key '{object_key}'.")
        return target

    async def store_media_pair(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        category: str,
        entity_id: str,
        media_pair: OptimizedMediaPair,
    ) -> StoredMediaKeys:
        """Escribe `thumb.webp` y `display.webp` en el directorio aislado del Tenant."""
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
        thumb_path = self._resolve_safe_path(
            object_key=thumb_key,
            holding_id=holding_id,
            tenant_id=tenant_id,
        )
        display_path = self._resolve_safe_path(
            object_key=display_key,
            holding_id=holding_id,
            tenant_id=tenant_id,
        )
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(media_pair.thumb_bytes)
        display_path.write_bytes(media_pair.display_bytes)

        version_tag = media_pair.sha256_hash[:16]
        ns = self._settings.ENV_NAMESPACE
        return StoredMediaKeys(
            thumb_object_key=thumb_key,
            display_object_key=display_key,
            thumb_url=f"/static/media/{ns}/{thumb_key}?v={version_tag}",
            display_url=f"/static/media/{ns}/{display_key}?v={version_tag}",
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
        """Elimina del disco local ambas variantes `.webp` verificando pertenencia al Tenant."""
        thumb_path = self._resolve_safe_path(
            object_key=thumb_object_key,
            holding_id=holding_id,
            tenant_id=tenant_id,
        )
        display_path = self._resolve_safe_path(
            object_key=display_object_key,
            holding_id=holding_id,
            tenant_id=tenant_id,
        )
        removed = False
        if thumb_path.exists():
            thumb_path.unlink()
            removed = True
        if display_path.exists():
            display_path.unlink()
            removed = True
        return removed

    def generate_presigned_url(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        object_key: str,
        ttl_seconds: int = 300,
    ) -> str:
        """Genera una URL firmada local con TTL verificando aislamiento por Tenant."""
        self._resolve_safe_path(
            object_key=object_key,
            holding_id=holding_id,
            tenant_id=tenant_id,
        )
        expires_at = int(time.time()) + max(1, min(ttl_seconds, 3600))
        secret = self._settings.SECRET_KEY.get_secret_value().encode("utf-8")
        signature = hmac.new(
            secret,
            f"{self._settings.ENV_NAMESPACE}:{object_key}:{expires_at}".encode(),
            hashlib.sha256,
        ).hexdigest()
        query = urlencode({"expires": str(expires_at), "sig": signature})
        return f"/static/media/{self._settings.ENV_NAMESPACE}/{object_key}?{query}"
