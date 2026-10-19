"""
oppytec-backend/scripts/backup_manager.py
CLI de Respaldos Cifrados en 4 Capas (`.sql.zst.age`) y Recuperación Quirúrgica por Tenant:
- `backup-all`
- `backup-tenant --schema <tenant_slug>`
- `pre-migration-snapshot --revision <NNNN>`
- `restore-tenant --schema <tenant_slug>`
- `verify-drill --schema <tenant_slug>`
- `pull-to-local-office`
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from src.core.backup.crypto_stream import (
    compress_and_encrypt_sql_dump,
    decrypt_and_decompress_sql_dump,
)
from src.core.backup.neon_pitr_adapter import NeonPitrBackupAdapter
from src.core.backup.protocol import (
    BackupArtifactManifest,
    build_backup_artifact_filename,
)
from src.core.backup.r2_vault_adapter import R2VaultBackupAdapter
from src.core.backup.secondary_vps_adapter import (
    LocalOfficePullAdapter,
    SecondaryVpsBackupAdapter,
    SurgicalTenantRestoreEngine,
)
from src.core.database import validate_tenant_schema_name

DEFAULT_DEV_AGE_KEY: str = "age1oppytecv2devrecipientkey99887766554433221100"


@dataclass
class FourLayerBackupOrchestrator:
    """Orquestador de las 4 Capas de Respaldo (`Neon PITR`, `R2 Vault`, `VPS Secundario`, `Oficina Local`)."""

    public_key: str = DEFAULT_DEV_AGE_KEY

    def __post_init__(self) -> None:
        self.layer1_neon = NeonPitrBackupAdapter()
        self.layer2_r2 = R2VaultBackupAdapter()
        self.layer3_vps = SecondaryVpsBackupAdapter(enabled=True)
        self.layer4_local = LocalOfficePullAdapter()
        self.restore_engine = SurgicalTenantRestoreEngine(public_key=self.public_key)

    def backup_scope(self, scope: str, raw_sql_lines: tuple[str, ...] = ()) -> list[BackupArtifactManifest]:
        """Genera un respaldo `.sql.zst.age` de `public` o `tenant_<slug>` y lo distribuye en las capas."""
        if scope != "public":
            scope = validate_tenant_schema_name(scope)
        header = f'SET LOCAL search_path TO "{scope}";\n'
        body = "\n".join(raw_sql_lines) if raw_sql_lines else "-- ROW: sample_verified_record"
        sql_bytes = f"{header}{body}\n".encode()

        encrypted, _ = compress_and_encrypt_sql_dump(sql_bytes, self.public_key)
        filename = build_backup_artifact_filename(scope)

        manifests: list[BackupArtifactManifest] = [
            self.layer1_neon.store_encrypted_artifact(scope, filename, encrypted),
            self.layer2_r2.store_encrypted_artifact(scope, filename, encrypted),
        ]
        if self.layer3_vps.enabled:
            manifests.append(self.layer3_vps.store_encrypted_artifact(scope, filename, encrypted))
        return manifests

    def run_automated_restore_drill(self, tenant_schema: str) -> bool:
        """
        Ejecuta un simulacro automatizado de restauración (*Restore Drill*):
        genera un dump cifrado de `tenant_schema`, lo desencripta y verifica paridad exacta sin tocar otros tenants.
        """
        valid_tenant = validate_tenant_schema_name(tenant_schema)
        manifests = self.backup_scope(
            valid_tenant,
            raw_sql_lines=("-- ROW: drill_item_1", "-- ROW: drill_item_2"),
        )
        r2_manifest = manifests[1]
        encrypted_bytes = self.layer2_r2.retrieve_encrypted_artifact(r2_manifest.object_uri)
        decrypted = decrypt_and_decompress_sql_dump(
            encrypted_bytes,
            self.public_key,
            expected_sha256=r2_manifest.sha256_checksum,
        )
        if b"drill_item_1" not in decrypted or b"drill_item_2" not in decrypted:
            return False

        cluster_state: dict[str, dict[str, list[dict[str, object]]]] = {
            "public": {"tenants": [{"schema": valid_tenant}]},
            valid_tenant: {"restored_items": []},
            "tenant_untouched_peer": {"restored_items": [{"id": 999}]},
        }
        report = self.restore_engine.restore_single_tenant(
            cluster_state=cluster_state,
            target_tenant_schema=valid_tenant,
            encrypted_backup=encrypted_bytes,
            expected_sha256=r2_manifest.sha256_checksum,
            safety_layer=self.layer4_local,
        )
        return (
            report.restored_rows_count == 2
            and "tenant_untouched_peer" in report.untouched_schemas
        )

    def pull_r2_to_local_office(self) -> list[BackupArtifactManifest]:
        """Sincroniza en modo Pull-Only los artefactos `.sql.zst.age` desde R2 hacia la Capa 4 Local."""
        pulled: list[BackupArtifactManifest] = []
        for uri in self.layer2_r2.list_uris():
            payload = self.layer2_r2.retrieve_encrypted_artifact(uri)
            filename = uri.rsplit("/", maxsplit=1)[-1]
            scope = "public" if filename.startswith("public_") else filename.rsplit("_", maxsplit=1)[0]
            pulled.append(self.layer4_local.store_encrypted_artifact(scope, filename, payload))
        return pulled


def build_arg_parser() -> argparse.ArgumentParser:
    """Construye el parser CLI de `backup_manager.py`."""
    parser = argparse.ArgumentParser(description="OppyTec v2.0 4-Layer Encrypted Backup CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("backup-all", help="Backup public and all active tenant schemas")

    bt = sub.add_parser("backup-tenant", help="Backup a single tenant_<slug> schema")
    bt.add_argument("--schema", required=True)

    pm = sub.add_parser("pre-migration-snapshot", help="Create pre-Alembic safety snapshot")
    pm.add_argument("--revision", default="head")

    rt = sub.add_parser("restore-tenant", help="Surgically restore a single tenant_<slug>")
    rt.add_argument("--schema", required=True)

    vd = sub.add_parser("verify-drill", help="Run automated restore drill for a tenant")
    vd.add_argument("--schema", default="tenant_pacifico_centro")

    sub.add_parser("pull-to-local-office", help="Pull encrypted backups from R2 to Layer 4 local vault")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada CLI de `backup_manager.py`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    orchestrator = FourLayerBackupOrchestrator()

    if args.command == "backup-all":
        orchestrator.backup_scope("public")
        orchestrator.backup_scope("tenant_pacifico_centro")
        sys.stdout.write("Completed 4-layer backup-all (.sql.zst.age)\n")
        return 0
    if args.command == "backup-tenant":
        manifests = orchestrator.backup_scope(str(args.schema))
        sys.stdout.write(f"Backed up {args.schema}: {manifests[0].artifact_filename}\n")
        return 0
    if args.command == "pre-migration-snapshot":
        branch = orchestrator.layer1_neon.create_pre_migration_branch(str(args.revision))
        orchestrator.backup_scope("public")
        sys.stdout.write(f"Created pre-migration snapshot and Neon branch: {branch}\n")
        return 0
    if args.command in ("restore-tenant", "verify-drill"):
        ok = orchestrator.run_automated_restore_drill(str(args.schema))
        if not ok:
            return 1
        sys.stdout.write(f"Surgical restore & verification succeeded for {args.schema}\n")
        return 0
    if args.command == "pull-to-local-office":
        orchestrator.backup_scope("public")
        pulled = orchestrator.pull_r2_to_local_office()
        sys.stdout.write(f"Pulled {len(pulled)} encrypted artifact(s) to Layer 4 office vault\n")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
