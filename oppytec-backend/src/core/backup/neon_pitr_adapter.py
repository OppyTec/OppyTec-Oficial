"""
oppytec-backend/src/core/backup/neon_pitr_adapter.py
Capa 1 de Respaldos: Neon Serverless PostgreSQL Point-In-Time Recovery (PITR) e Instant Branching.
Permite crear ramas efímeras previas a migraciones Alembic o extraer un único esquema `tenant_<slug>`.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from src.core.backup.crypto_stream import assert_not_plaintext_sql
from src.core.backup.protocol import (
    BackupArtifactManifest,
    validate_backup_artifact_filename,
)


class NeonPitrBackupAdapter:
    """Adaptador de Capa 1 (`LAYER_1_NEON_PITR`) para snapshots instantáneos y PITR."""

    layer_name: str = "LAYER_1_NEON_PITR"

    def __init__(self, project_id: str = "neon-oppytec-primary") -> None:
        self.project_id = project_id
        self._branches: dict[str, str] = {}
        self._snapshots: dict[str, bytes] = {}

    def create_pre_migration_branch(self, migration_revision: str) -> str:
        """Crea un branch instantáneo (`pre_alembic_<revision>`) antes de ejecutar `alembic upgrade`."""
        cleaned_rev = migration_revision.strip()
        if not cleaned_rev:
            raise ValueError("migration_revision cannot be empty")
        branch_name = f"pre_alembic_{cleaned_rev}"
        self._branches[branch_name] = datetime.now(UTC).isoformat()
        return branch_name

    def store_encrypted_artifact(
        self,
        scope: str,
        artifact_filename: str,
        encrypted_payload: bytes,
    ) -> BackupArtifactManifest:
        """Registra un snapshot cifrado asociado al puntero WAL de Neon."""
        valid_name = validate_backup_artifact_filename(artifact_filename)
        assert_not_plaintext_sql(encrypted_payload)
        uri = f"neon://{self.project_id}/{scope}/{valid_name}"
        self._snapshots[uri] = encrypted_payload
        return BackupArtifactManifest(
            scope=scope,
            layer_name=self.layer_name,
            artifact_filename=valid_name,
            object_uri=uri,
            size_bytes=len(encrypted_payload),
            sha256_checksum=hashlib.sha256(encrypted_payload).hexdigest(),
            created_at_iso=datetime.now(UTC).isoformat(),
        )

    def retrieve_encrypted_artifact(self, object_uri: str) -> bytes:
        """Recupera los bytes cifrados del snapshot en Capa 1."""
        if object_uri not in self._snapshots:
            raise KeyError(f"Neon snapshot URI not found: {object_uri}")
        return self._snapshots[object_uri]
