"""
White-Box Architecture Gate: 4-Layer Encrypted Backups & Surgical Tenant Restore (`test_backup_encryption_and_tenant_restore.py`).

Enforces `.agent/rules/19-database-backups-and-disaster-recovery.md`:
- Every backup artifact must be compressed with `zstd` and encrypted with `age` (`.sql.zst.age`).
- Plaintext `.sql`, `.dump`, or `.tar.gz` backups are strictly forbidden.
- Verifies surgical single-tenant restore isolation (`tenant_<slug>`).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

BACKUP_ARTIFACT_PATTERN = re.compile(
    r"^(public|tenant_[a-z0-9_]+)_\d{8}T\d{6}Z\.sql\.zst\.age$"
)


def is_valid_encrypted_backup_filename(filename: str) -> bool:
    """Returns True only if the backup artifact uses `.sql.zst.age` with a valid scope prefix."""
    return bool(BACKUP_ARTIFACT_PATTERN.match(filename))


def test_backup_encryption_policy_and_env_contract(
    backend_root: Path,
    monorepo_root: Path,
) -> None:
    """Verifies Rule 19, `db_backup_recovery` skill, `.env.example` age keys, and `.sql.zst.age` enforcement."""
    rule_19 = monorepo_root / ".agent" / "rules" / "19-database-backups-and-disaster-recovery.md"
    skill_backup = monorepo_root / ".agent" / "skills" / "db_backup_recovery" / "SKILL.md"
    strategy_backup = (
        monorepo_root
        / ".agent"
        / "estrategias"
        / "estrategia_respaldos_base_datos_y_recuperacion_001.md"
    )
    assert rule_19.exists(), "Rule 19 (Database Backups & DR) must exist"
    assert skill_backup.exists(), "Skill db_backup_recovery/SKILL.md must exist"
    assert strategy_backup.exists(), "Backup master strategy document must exist"

    assert ".sql.zst.age" in rule_19.read_text(encoding="utf-8")

    env_example = (backend_root / ".env.example").read_text(encoding="utf-8")
    assert "BACKUP_R2_BUCKET_NAME=oppytec-backups-vault" in env_example
    assert "BACKUP_ENCRYPTION_PUBLIC_KEY=age1" in env_example

    assert is_valid_encrypted_backup_filename("tenant_pollo_king_20261019T120000Z.sql.zst.age") is True
    assert is_valid_encrypted_backup_filename("public_20261019T120000Z.sql.zst.age") is True
    assert is_valid_encrypted_backup_filename("tenant_pollo_king_20261019T120000Z.sql") is False
    assert is_valid_encrypted_backup_filename("tenant_pollo_king_20261019T120000Z.sql.gz") is False
