"""
White-Box Architecture Gate: 12-Subagent Squad & Master Strategy Coverage (`test_subagent_strategy_coverage.py`).

Enforces `.agent/rules/20-multiagent-squad-and-self-healing-loops.md`:
- All 12 specialized sub-agents (`01..12-*`) must exist in `.agent/subagents/` with:
  - `prompt.md`
  - `knowledge.md`
  - `handovers/latest_handover.md`
- All 17 master strategies (`estrategia_*_001.md`) in `.agent/estrategias/` must exist.
- All 23 immutable rules (`00..22-*.md`) in `.agent/rules/` must exist.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

EXPECTED_SUBAGENTS: tuple[str, ...] = (
    "01-orchestrator-pm",
    "02-software-architect",
    "03-database-alembic-and-backup-engineer",
    "04-backend-senior-dev",
    "05-frontend-senior-dev",
    "06-ai-oppyfy-and-jev-engineer",
    "07-i18n-and-fx-currency-specialist",
    "08-environments-and-observability-engineer",
    "09-qa-parity-and-test-engineer",
    "10-cybersecurity-redteam-auditor",
    "11-git-worktree-merge-arbiter",
    "12-tech-writer-openspec-archify",
)


def test_twelve_subagents_and_strategies_complete(monorepo_root: Path) -> None:
    """Verifies that all 12 subagents, 17 strategies, and 23 rules are present."""
    agent_dir = monorepo_root / ".agent"
    subagents_dir = agent_dir / "subagents"

    for subagent_name in EXPECTED_SUBAGENTS:
        folder = subagents_dir / subagent_name
        assert folder.is_dir(), f"Missing subagent directory: {folder}"
        assert (folder / "prompt.md").is_file(), f"Missing prompt.md in {subagent_name}"
        assert (folder / "knowledge.md").is_file(), f"Missing knowledge.md in {subagent_name}"
        assert (
            folder / "handovers" / "latest_handover.md"
        ).is_file(), f"Missing handovers/latest_handover.md in {subagent_name}"

    strategies = sorted((agent_dir / "estrategias").glob("estrategia_*_001.md"))
    assert len(strategies) == 17, f"Expected 17 master strategies, found {len(strategies)}"

    rules = sorted((agent_dir / "rules").glob("*.md"))
    assert len(rules) == 23, f"Expected 23 immutable rules (00..22), found {len(rules)}"
