"""
White-Box Architecture Gate: Multi-Agent Harness & Smart Merge Integrity (`test_harness_and_merge_integrity.py`).

Enforces `.agent/rules/10-git-worktrees-and-smart-merge.md`:
1. Zero unresolved Git merge conflict markers (`<<<<<<< `, `>>>>>>> `) in repository source files.
2. Valid JSON structure in `.agent/memory/claims_registry.json`.
3. 100% SHA-256 anti-reward-hacking integrity via `verify_anti_cheating_hashes()` in `scripts/harness.py`.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

CONFLICT_PREFIXES: tuple[str, ...] = ("<<<<<<< ", ">>>>>>> ")


def test_zero_git_merge_conflict_markers(monorepo_root: Path) -> None:
    """Scans tracked/source files in `oppytec-backend/`, `specs/`, and `.agent/` for conflict markers."""
    scan_roots = [
        monorepo_root / "oppytec-backend" / "src",
        monorepo_root / "oppytec-backend" / "tests",
        monorepo_root / "specs",
        monorepo_root / ".agent" / "rules",
    ]
    self_path = Path(__file__).resolve()
    conflicts: list[str] = []

    for root in scan_roots:
        if not root.exists():
            continue
        for file_path in root.rglob("*"):
            if not file_path.is_file() or file_path.resolve() == self_path:
                continue
            if file_path.suffix not in {".py", ".md", ".yaml", ".yml", ".json", ".toml"}:
                continue
            for lineno, line in enumerate(
                file_path.read_text(encoding="utf-8", errors="ignore").splitlines(),
                start=1,
            ):
                if line.startswith(CONFLICT_PREFIXES) or line.strip() == "=" * 7:
                    conflicts.append(f"{file_path.relative_to(monorepo_root)}:{lineno}")

    assert not conflicts, f"Unresolved Git conflict markers found: {conflicts}"


def test_claims_registry_valid_json_and_anti_cheating_hashes(
    monorepo_root: Path,
) -> None:
    """Verifies `claims_registry.json` schema and SHA-256 lock via `scripts/harness.py`."""
    claims_path = monorepo_root / ".agent" / "memory" / "claims_registry.json"
    assert claims_path.exists(), ".agent/memory/claims_registry.json must exist"

    claims_data = json.loads(claims_path.read_text(encoding="utf-8"))
    assert claims_data.get("version") == "2.0.0"
    assert isinstance(claims_data.get("active_claims"), list)

    harness_path = monorepo_root / "scripts" / "harness.py"
    assert harness_path.exists(), "scripts/harness.py must exist"

    spec = importlib.util.spec_from_file_location("oppytec_harness", harness_path)
    assert spec is not None and spec.loader is not None
    harness_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness_mod)

    assert harness_mod.verify_anti_cheating_hashes() is True
