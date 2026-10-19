"""
oppytec-backend/src/core/backup/secondary_vps_adapter.py
Capa 3 (VPS Secundario Multi-Nube), Capa 4 (Bóveda Local Pull-Only en Oficina) y
Motor de Restauración Quirúrgica por Tenant (`SurgicalTenantRestoreEngine`).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from src.core.backup.crypto_stream import (
    assert_not_plaintext_sql,
    compress_and_encrypt_sql_dump,
    decrypt_and_decompress_sql_dump,
)
from src.core.backup.protocol import (
    BackupArtifactManifest,
    build_backup_artifact_filename,
    validate_backup_artifact_filename,
)
from src.core.database import validate_tenant_schema_name


class SecondaryVpsBackupAdapter:
    """Adaptador de Capa 3 (`LAYER_3_SECONDARY_VPS`), activable por configuración (`BACKUP_SECONDARY_VPS_ENABLED`)."""

    layer_name: str = "LAYER_3_SECONDARY_VPS"

    def __init__(
        self,
        enabled: bool = False,
        endpoint: str = "vps-backup.oppytec.internal",
    ) -> None:
        self.enabled = enabled
        self.endpoint = endpoint
        self._storage: dict[str, bytes] = {}

    def store_encrypted_artifact(
        self,
        scope: str,
        artifact_filename: str,
        encrypted_payload: bytes,
    ) -> BackupArtifactManifest:
        """Almacena la réplica cifrada en el VPS secundario."""
        valid_name = validate_backup_artifact_filename(artifact_filename)
        assert_not_plaintext_sql(encrypted_payload)
        uri = f"vps://{self.endpoint}/{scope}/{valid_name}"
        self._storage[uri] = encrypted_payload
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
        """Recupera el artefacto cifrado desde el VPS secundario."""
        if object_uri not in self._storage:
            raise KeyError(f"Secondary VPS artifact not found: {object_uri}")
        return self._storage[object_uri]


class LocalOfficePullAdapter:
    """
    Adaptador de Capa 4 (`LAYER_4_LOCAL_OFFICE_PULL`):
    Descarga en modo Pull-Only los archivos `.sql.zst.age` hacia el almacenamiento fuera de nube.
    """

    layer_name: str = "LAYER_4_LOCAL_OFFICE_PULL"

    def __init__(self) -> None:
        self._vault: dict[str, bytes] = {}
        self.last_local_pull_at: str | None = None

    def store_encrypted_artifact(
        self,
        scope: str,
        artifact_filename: str,
        encrypted_payload: bytes,
    ) -> BackupArtifactManifest:
        """Guarda una copia cifrada inmutable en la bóveda local de oficina."""
        valid_name = validate_backup_artifact_filename(artifact_filename)
        assert_not_plaintext_sql(encrypted_payload)
        uri = f"local-office://vault/{scope}/{valid_name}"
        self._vault[uri] = encrypted_payload
        self.last_local_pull_at = datetime.now(UTC).isoformat()
        return BackupArtifactManifest(
            scope=scope,
            layer_name=self.layer_name,
            artifact_filename=valid_name,
            object_uri=uri,
            size_bytes=len(encrypted_payload),
            sha256_checksum=hashlib.sha256(encrypted_payload).hexdigest(),
            created_at_iso=self.last_local_pull_at,
        )

    def retrieve_encrypted_artifact(self, object_uri: str) -> bytes:
        """Recupera un archivo `.sql.zst.age` desde la bóveda local de oficina."""
        if object_uri not in self._vault:
            raise KeyError(f"Local office artifact not found: {object_uri}")
        return self._vault[object_uri]


@dataclass(frozen=True)
class SurgicalRestoreReport:
    """Resultado auditable de una restauración quirúrgica de un único `tenant_<slug>`."""

    restored_tenant_schema: str
    safety_snapshot_manifest: BackupArtifactManifest
    restored_rows_count: int
    untouched_schemas: tuple[str, ...]


class SurgicalTenantRestoreEngine:
    """
    Motor de restauración quirúrgica por Tenant (`tenant_<slug>`).
    Garantiza que restaurar `tenant_a` tome primero un `pre_restore_safety_snapshot`
    y jamás modifique ni una sola fila de `tenant_b` ni de `public`.
    """

    def __init__(self, public_key: str) -> None:
        self.public_key = public_key

    def restore_single_tenant(
        self,
        cluster_state: dict[str, dict[str, list[dict[str, object]]]],
        target_tenant_schema: str,
        encrypted_backup: bytes,
        expected_sha256: str,
        safety_layer: LocalOfficePullAdapter,
    ) -> SurgicalRestoreReport:
        """
        Restaura únicamente `target_tenant_schema` dentro de `cluster_state` verificando:
        1. Validación estricta del nombre `tenant_<slug>` (bloquea `public` u otros nombres).
        2. Creación de un `pre_restore_safety_snapshot` cifrado `.sql.zst.age` antes de sobrescribir.
        3. Inmutabilidad absoluta del resto de esquemas (`public`, `tenant_b`, etc.).
        """
        valid_target = validate_tenant_schema_name(target_tenant_schema)
        other_schemas_before = {
            schema: repr(tables)
            for schema, tables in cluster_state.items()
            if schema != valid_target
        }

        # 1. Generar snapshot de seguridad previo a la restauración
        current_tenant_data = repr(cluster_state.get(valid_target, {})).encode("utf-8")
        safety_cipher, _ = compress_and_encrypt_sql_dump(current_tenant_data, self.public_key)
        safety_filename = build_backup_artifact_filename(valid_target)
        safety_manifest = safety_layer.store_encrypted_artifact(
            scope=valid_target,
            artifact_filename=safety_filename,
            encrypted_payload=safety_cipher,
        )

        # 2. Desencriptar y verificar el dump del tenant objetivo
        decrypted_sql = decrypt_and_decompress_sql_dump(
            encrypted_payload=encrypted_backup,
            recipient_key=self.public_key,
            expected_sha256=expected_sha256,
        ).decode("utf-8")

        if f'SET LOCAL search_path TO "{valid_target}"' not in decrypted_sql:
            raise ValueError(
                f"CrossTenantRestoreViolation: El respaldo no pertenece al esquema '{valid_target}'."
            )

        # 3. Aplicar datos exclusivamente en `valid_target`
        restored_rows: list[dict[str, object]] = []
        for line in decrypted_sql.splitlines():
            if line.startswith("-- ROW:"):
                payload_text = line.removeprefix("-- ROW:").strip()
                restored_rows.append({"raw": payload_text})

        cluster_state[valid_target] = {"restored_items": restored_rows}

        # 4. Verificación post-condición: ningún otro esquema fue tocado
        for schema, snapshot_repr in other_schemas_before.items():
            if repr(cluster_state.get(schema)) != snapshot_repr:
                raise RuntimeError(f"TenantIsolationBreach: schema '{schema}' was altered!")

        return SurgicalRestoreReport(
            restored_tenant_schema=valid_target,
            safety_snapshot_manifest=safety_manifest,
            restored_rows_count=len(restored_rows),
            untouched_schemas=tuple(sorted(other_schemas_before.keys())),
        )
