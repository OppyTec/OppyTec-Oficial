"""
White-Box Architecture Gate: Alembic Correlative Integrity (`test_alembic_integrity.py`).

Enforces Criterion 5 of `.agent/evals/rubric_10_criteria.yaml` and `.agent/rules/06-alembic-and-schema-governance.md`:
- Every migration in `oppytec-backend/alembic/versions/` must match `^\\d{4}_(public|tenant)_[a-z0-9_]+\\.py$`.
- Strict linear sequence `0001..NNNN` without duplicate prefixes or gaps.
- Single head (no `down_revision` tuple/list from `alembic merge heads`).
- Mandatory `migration_scope` (`"public"` or `"tenant"`) and non-empty `downgrade()` body.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

MIGRATION_FILENAME_PATTERN = re.compile(r"^(\d{4})_(public|tenant)_[a-z0-9_]+\.py$")


def validate_migration_ast(source_code: str, filename: str) -> list[str]:
    """Validates a single Alembic migration file's AST for OppyTec governance rules."""
    errors: list[str] = []
    match = MIGRATION_FILENAME_PATTERN.match(filename)
    if not match:
        errors.append(
            f"{filename}: filename does not match '^\\d{{4}}_(public|tenant)_[a-z0-9_]+\\.py$'"
        )
        expected_scope = None
    else:
        expected_scope = match.group(2)

    tree = ast.parse(source_code, filename=filename)
    has_migration_scope = False
    has_valid_downgrade = False

    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets: list[str] = []
            value_node = node.value
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets = [node.target.id]

            if "down_revision" in targets and isinstance(value_node, (ast.Tuple, ast.List, ast.Set)):
                errors.append(f"{filename}: merge_heads detected (down_revision is a sequence)")

            if "migration_scope" in targets and isinstance(value_node, ast.Constant):
                has_migration_scope = True
                if value_node.value not in ("public", "tenant"):
                    errors.append(f"{filename}: invalid migration_scope={value_node.value!r}")
                elif expected_scope and value_node.value != expected_scope:
                    errors.append(
                        f"{filename}: migration_scope={value_node.value!r} mismatches filename scope '{expected_scope}'"
                    )

        elif isinstance(node, ast.FunctionDef) and node.name == "downgrade":
            non_doc_stmts = [
                stmt
                for stmt in node.body
                if not (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Constant)
                    and isinstance(stmt.value.value, str)
                )
            ]
            meaningful_stmts = [
                stmt
                for stmt in non_doc_stmts
                if not isinstance(stmt, ast.Pass)
                and not (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value is Ellipsis
                )
            ]
            if meaningful_stmts:
                has_valid_downgrade = True
            else:
                errors.append(f"{filename}: downgrade() cannot be empty or pass-only")

    if not has_migration_scope:
        errors.append(f"{filename}: missing mandatory 'migration_scope' declaration")
    if not has_valid_downgrade:
        errors.append(f"{filename}: missing non-empty 'def downgrade()' implementation")

    return errors


def test_alembic_versions_correlative_and_reversible(
    backend_root: Path,
    monorepo_root: Path,
) -> None:
    """Verifies Alembic rule governance and all existing migrations in `alembic/versions/`."""
    rule_path = monorepo_root / ".agent" / "rules" / "06-alembic-and-schema-governance.md"
    assert rule_path.exists(), "Rule 06 (Alembic governance) must exist"

    versions_dir = backend_root / "alembic" / "versions"
    if not versions_dir.exists():
        return

    migration_files = sorted(
        f for f in versions_dir.glob("*.py") if f.name != "__init__.py"
    )
    if not migration_files:
        return

    all_errors: list[str] = []
    numbers: list[int] = []

    for mig_file in migration_files:
        source = mig_file.read_text(encoding="utf-8")
        all_errors.extend(validate_migration_ast(source, mig_file.name))
        m = MIGRATION_FILENAME_PATTERN.match(mig_file.name)
        if m:
            numbers.append(int(m.group(1)))

    expected_numbers = list(range(1, len(numbers) + 1))
    if numbers != expected_numbers:
        all_errors.append(
            f"Correlative sequence broken: found prefixes {numbers}, expected {expected_numbers}"
        )

    assert not all_errors, "Alembic integrity violations:\n" + "\n".join(all_errors)


def test_alembic_validator_rejects_merge_heads_and_empty_downgrade() -> None:
    """Self-test verifying `validate_migration_ast` catches invalid migrations."""
    valid_migration = (
        'revision = "0001_public_genesis"\n'
        "down_revision = None\n"
        'migration_scope = "public"\n\n'
        "def upgrade() -> None:\n"
        "    op.create_table('holdings')\n\n"
        "def downgrade() -> None:\n"
        "    op.drop_table('holdings')\n"
    )
    assert validate_migration_ast(valid_migration, "0001_public_genesis.py") == []

    invalid_migration = (
        'revision = "0002_bad"\n'
        'down_revision = ("0001a", "0001b")\n\n'
        "def downgrade() -> None:\n"
        "    pass\n"
    )
    errs = validate_migration_ast(invalid_migration, "bad_name.py")
    assert len(errs) >= 3
