"""
oppytec-backend/src/modules/tenancy/application/storage_quota_service.py
Gestor de Cuota de Memoria en Cloudflare R2 (`max_storage_mb`) con:
- Deduplicación inteligente Intra-Tenant por `sha256_hash` (`reference_count`).
- Descuento y liberación instantánea de bytes al reemplazar o eliminar imágenes (`reference_count == 0`).
- Cero archivos huérfanos ("Archivos Zombis") en Cloudflare R2.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, replace

from src.adapters.storage.protocol import OptimizedMediaPair, StoragePort, StoredMediaKeys
from src.core.exceptions import StorageQuotaExceededError
from src.modules.tenancy.domain.quotas import (
    StorageQuotaEvaluation,
    evaluate_storage_quota_bytes,
)


@dataclass(frozen=True)
class MediaLedgerEntry:
    """Registro del libro mayor `tenant_media_assets` con conteo de referencias para deduplicación."""

    asset_id: str
    holding_id: str
    tenant_id: str
    category: str
    entity_id: str
    sha256_hash: str
    thumb_object_key: str
    display_object_key: str
    thumb_url: str
    display_url: str
    total_size_bytes: int
    reference_count: int
    uploaded_by_user_id: int


class StorageQuotaService:
    """
    Controla el uso de memoria de imágenes y archivos por Tenant:
    1. Si el mismo Tenant sube una imagen con idéntico `sha256_hash`, reutiliza el activo existente,
       incrementa `reference_count` y consume `0` bytes adicionales de su cuota.
    2. Si sube una imagen nueva, verifica `current_used_bytes + new_bytes <= max_storage_mb * 1024 * 1024`.
    3. Al reemplazar o eliminar una imagen, decrementa `reference_count` y, si llega a `0`,
       elimina físicamente `thumb.webp` y `display.webp` de R2 liberando sus bytes en el acto.
    """

    def __init__(
        self,
        *,
        storage_adapter: StoragePort,
        plan_max_storage_mb: int,
        holding_storage_override_mb: int | None = None,
        tenant_storage_override_mb: int | None = None,
    ) -> None:
        self._storage = storage_adapter
        self._plan_max_storage_mb = plan_max_storage_mb
        self._holding_override_mb = holding_storage_override_mb
        self._tenant_override_mb = tenant_storage_override_mb
        self._assets_by_tenant_and_hash: dict[tuple[str, str], MediaLedgerEntry] = {}

    def get_tenant_used_bytes(self, tenant_id: str) -> int:
        """Suma los bytes únicos (`reference_count > 0`) ocupados actualmente por el `tenant_id`."""
        return sum(
            entry.total_size_bytes
            for (t_id, _), entry in self._assets_by_tenant_and_hash.items()
            if t_id == tenant_id and entry.reference_count > 0
        )

    def evaluate_tenant_storage(
        self,
        *,
        tenant_id: str,
        new_bytes: int = 0,
    ) -> StorageQuotaEvaluation:
        """Evalúa el estado actual o proyectado de la cuota de almacenamiento del Tenant."""
        current_bytes = self.get_tenant_used_bytes(tenant_id)
        return evaluate_storage_quota_bytes(
            current_used_bytes=current_bytes,
            new_bytes=new_bytes,
            plan_max_storage_mb=self._plan_max_storage_mb,
            holding_storage_override_mb=self._holding_override_mb,
            tenant_storage_override_mb=self._tenant_override_mb,
        )

    async def upload_or_deduplicate_media(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        category: str,
        entity_id: str,
        media_pair: OptimizedMediaPair,
        uploaded_by_user_id: int,
        previous_sha256_hash: str | None = None,
    ) -> MediaLedgerEntry:
        """
        Sube un `OptimizedMediaPair` aplicando deduplicación SHA-256 intra-tenant,
        validación estricta de cuota MB y recolección de basura si reemplaza una imagen anterior.
        """
        dedup_key = (tenant_id, media_pair.sha256_hash)
        existing = self._assets_by_tenant_and_hash.get(dedup_key)

        if existing is not None and existing.reference_count > 0:
            if previous_sha256_hash == media_pair.sha256_hash:
                return existing
            incremented = replace(existing, reference_count=existing.reference_count + 1)
            self._assets_by_tenant_and_hash[dedup_key] = incremented
            if previous_sha256_hash is not None:
                await self.release_media_reference(
                    holding_id=holding_id,
                    tenant_id=tenant_id,
                    sha256_hash=previous_sha256_hash,
                )
            return incremented

        # Calcular bytes liberables si se está reemplazando una imagen de referencia única
        reclaimable_bytes = 0
        if previous_sha256_hash is not None:
            prev_entry = self._assets_by_tenant_and_hash.get((tenant_id, previous_sha256_hash))
            if prev_entry is not None and prev_entry.reference_count == 1:
                reclaimable_bytes = prev_entry.total_size_bytes

        current_bytes = max(0, self.get_tenant_used_bytes(tenant_id) - reclaimable_bytes)
        quota_eval = evaluate_storage_quota_bytes(
            current_used_bytes=current_bytes,
            new_bytes=media_pair.total_size_bytes,
            plan_max_storage_mb=self._plan_max_storage_mb,
            holding_storage_override_mb=self._holding_override_mb,
            tenant_storage_override_mb=self._tenant_override_mb,
        )
        if not quota_eval.allowed:
            raise StorageQuotaExceededError(
                f"Storage quota exceeded for tenant '{tenant_id}': "
                f"projected {quota_eval.projected_used_bytes} bytes > max {quota_eval.effective_max_storage_bytes} bytes.",
                i18n_key="storage:errors.plan_quota_exceeded",
                context={
                    "current_used_bytes": current_bytes,
                    "new_bytes": media_pair.total_size_bytes,
                    "max_storage_mb": quota_eval.effective_max_storage_mb,
                },
            )

        stored: StoredMediaKeys = await self._storage.store_media_pair(
            holding_id=holding_id,
            tenant_id=tenant_id,
            category=category,
            entity_id=entity_id,
            media_pair=media_pair,
        )
        entry = MediaLedgerEntry(
            asset_id=str(uuid.uuid4()),
            holding_id=holding_id,
            tenant_id=tenant_id,
            category=category,
            entity_id=entity_id,
            sha256_hash=media_pair.sha256_hash,
            thumb_object_key=stored.thumb_object_key,
            display_object_key=stored.display_object_key,
            thumb_url=stored.thumb_url,
            display_url=stored.display_url,
            total_size_bytes=media_pair.total_size_bytes,
            reference_count=1,
            uploaded_by_user_id=uploaded_by_user_id,
        )
        self._assets_by_tenant_and_hash[dedup_key] = entry

        if previous_sha256_hash is not None and previous_sha256_hash != media_pair.sha256_hash:
            await self.release_media_reference(
                holding_id=holding_id,
                tenant_id=tenant_id,
                sha256_hash=previous_sha256_hash,
            )

        return entry

    async def release_media_reference(
        self,
        *,
        holding_id: str,
        tenant_id: str,
        sha256_hash: str,
    ) -> bool:
        """
        Decrementa `reference_count` de un activo del Tenant.
        Si `reference_count` llega a `0`, borra físicamente los objetos de R2 y libera los bytes.
        """
        dedup_key = (tenant_id, sha256_hash)
        entry = self._assets_by_tenant_and_hash.get(dedup_key)
        if entry is None or entry.reference_count <= 0:
            return False

        if entry.reference_count > 1:
            self._assets_by_tenant_and_hash[dedup_key] = replace(
                entry,
                reference_count=entry.reference_count - 1,
            )
            return False

        await self._storage.delete_media_pair(
            holding_id=holding_id,
            tenant_id=tenant_id,
            thumb_object_key=entry.thumb_object_key,
            display_object_key=entry.display_object_key,
        )
        del self._assets_by_tenant_and_hash[dedup_key]
        return True
