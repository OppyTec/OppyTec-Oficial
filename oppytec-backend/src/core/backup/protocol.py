"""
oppytec-backend/src/core/backup/protocol.py
Puertos y contratos tipados para las 4 Capas de Respaldo (`3-2-1-1-0`).
Exige extensión `.sql.zst.age` y checksum `SHA-256` obligatorio (prohibidos dumps `.sql` en texto plano).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from src.core.database import validate_tenant_schema_name

BACKUP_FILENAME_REGEX: re.Pattern[str] = re.compile(
    r"^(public|tenant_[a-z0-9_]+)_\d{8}T\d{6}Z\.sql\.zst\.age$"
)


def validate_backup_artifact_filename(filename: str) -> str:
    """
    Valida que el nombre del artefacto de respaldo cumpla estrictamente
    `^(public|tenant_[a-z0-9_]+)_<YYYYMMDDTHHMMSSZ>.sql.zst.age$`.
    Rechaza cualquier archivo `.sql`, `.dump` o `.gz` sin cifrado `age`.
    """
    cleaned = filename.strip()
    if not BACKUP_FILENAME_REGEX.match(cleaned):
        raise ValueError(
            f"UnencryptedOrInvalidBackupArtifactError: '{filename}' no cumple el formato obligatorio "
            "'<public|tenant_slug>_<YYYYMMDDTHHMMSSZ>.sql.zst.age'."
        )
    return cleaned


def build_backup_artifact_filename(
    scope: str,
    timestamp_utc: datetime | None = None,
) -> str:
    """Construye el nombre canónico `.sql.zst.age` para `public` o un `tenant_<slug>`."""
    cleaned_scope = scope.strip()
    if cleaned_scope != "public":
        cleaned_scope = validate_tenant_schema_name(cleaned_scope)
    ts = (timestamp_utc or datetime.now(UTC)).astimezone(UTC)
    ts_str = ts.strftime("%Y%m%dT%H%M%SZ")
    return validate_backup_artifact_filename(f"{cleaned_scope}_{ts_str}.sql.zst.age")


@dataclass(frozen=True)
class BackupArtifactManifest:
    """Manifiesto inmutable verificable por `SHA-256` de un artefacto `.sql.zst.age`."""

    scope: str
    layer_name: str
    artifact_filename: str
    object_uri: str
    size_bytes: int
    sha256_checksum: str
    created_at_iso: str

    def __post_init__(self) -> None:
        validate_backup_artifact_filename(self.artifact_filename)
        if self.size_bytes <= 0:
            raise ValueError("BackupArtifactManifest.size_bytes must be > 0")
        if len(self.sha256_checksum) != 64:
            raise ValueError("BackupArtifactManifest.sha256_checksum must be a 64-char hex digest")


@runtime_checkable
class BackupLayerPort(Protocol):
    """Puerto estructural (`Protocol`) implementado por las 4 Capas de Respaldo."""

    layer_name: str

    def store_encrypted_artifact(
        self,
        scope: str,
        artifact_filename: str,
        encrypted_payload: bytes,
    ) -> BackupArtifactManifest:
        """Almacena el payload cifrado `.sql.zst.age` y devuelve su manifiesto con `SHA-256`."""
        ...

    def retrieve_encrypted_artifact(self, object_uri: str) -> bytes:
        """Recupera los bytes cifrados `.sql.zst.age` desde la capa de almacenamiento."""
        ...
