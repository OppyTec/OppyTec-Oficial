"""Motor de Respaldos en 4 Capas (`.sql.zst.age`) y Restauración Quirúrgica por Tenant (`tenant_<slug>`)."""
from __future__ import annotations

from src.core.backup.crypto_stream import (
    compress_and_encrypt_sql_dump,
    decrypt_and_decompress_sql_dump,
)
from src.core.backup.neon_pitr_adapter import NeonPitrBackupAdapter
from src.core.backup.protocol import (
    BACKUP_FILENAME_REGEX,
    BackupArtifactManifest,
    BackupLayerPort,
    build_backup_artifact_filename,
    validate_backup_artifact_filename,
)
from src.core.backup.r2_vault_adapter import R2VaultBackupAdapter
from src.core.backup.secondary_vps_adapter import (
    LocalOfficePullAdapter,
    SecondaryVpsBackupAdapter,
    SurgicalTenantRestoreEngine,
)

__all__ = [
    "BACKUP_FILENAME_REGEX",
    "BackupArtifactManifest",
    "BackupLayerPort",
    "LocalOfficePullAdapter",
    "NeonPitrBackupAdapter",
    "R2VaultBackupAdapter",
    "SecondaryVpsBackupAdapter",
    "SurgicalTenantRestoreEngine",
    "build_backup_artifact_filename",
    "compress_and_encrypt_sql_dump",
    "decrypt_and_decompress_sql_dump",
    "validate_backup_artifact_filename",
]
