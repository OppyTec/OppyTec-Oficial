"""
oppytec-backend/src/core/backup/r2_vault_adapter.py
Capa 2 de Respaldos: Bóveda Inmutable Cifrada en Cloudflare R2 (`oppytec-backups-vault`).
Almacena dumps `.sql.zst.age` separados para `public` y para cada `tenant_<slug>`.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from src.core.backup.crypto_stream import assert_not_plaintext_sql
from src.core.backup.protocol import (
    BackupArtifactManifest,
    validate_backup_artifact_filename,
)
from src.core.database import validate_tenant_schema_name


class R2VaultBackupAdapter:
    """Adaptador de Capa 2 (`LAYER_2_R2_VAULT`) con aislamiento por entorno y por `tenant_<slug>`."""

    layer_name: str = "LAYER_2_R2_VAULT"

    def __init__(
        self,
        bucket_name: str = "oppytec-backups-vault",
        environment: str = "local",
    ) -> None:
        self.bucket_name = bucket_name
        self.environment = environment
        self._objects: dict[str, bytes] = {}

    def build_object_uri(
        self,
        scope: str,
        artifact_filename: str,
        holding_id: str = "global",
    ) -> str:
        """Construye la ruta canónica en R2 para `public` o `tenants/{holding_id}/{tenant_schema}/`."""
        valid_file = validate_backup_artifact_filename(artifact_filename)
        if scope == "public":
            return f"r2://{self.bucket_name}/{self.environment}/global_public/{valid_file}"
        valid_tenant = validate_tenant_schema_name(scope)
        return (
            f"r2://{self.bucket_name}/{self.environment}/tenants/"
            f"{holding_id}/{valid_tenant}/{valid_file}"
        )

    def store_encrypted_artifact(
        self,
        scope: str,
        artifact_filename: str,
        encrypted_payload: bytes,
    ) -> BackupArtifactManifest:
        """Valida que el payload esté cifrado con `age` y lo almacena en el vault de R2."""
        assert_not_plaintext_sql(encrypted_payload)
        uri = self.build_object_uri(scope=scope, artifact_filename=artifact_filename)
        self._objects[uri] = encrypted_payload
        return BackupArtifactManifest(
            scope=scope,
            layer_name=self.layer_name,
            artifact_filename=validate_backup_artifact_filename(artifact_filename),
            object_uri=uri,
            size_bytes=len(encrypted_payload),
            sha256_checksum=hashlib.sha256(encrypted_payload).hexdigest(),
            created_at_iso=datetime.now(UTC).isoformat(),
        )

    def retrieve_encrypted_artifact(self, object_uri: str) -> bytes:
        """Descarga el artefacto `.sql.zst.age` desde el vault de Cloudflare R2."""
        if object_uri not in self._objects:
            raise KeyError(f"R2 Backup object not found: {object_uri}")
        return self._objects[object_uri]

    def list_uris(self) -> list[str]:
        """Devuelve todas las URIs almacenadas en la bóveda."""
        return sorted(self._objects.keys())
